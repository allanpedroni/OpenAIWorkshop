"""
LLM-as-Judge Evaluator using Azure AI Foundry Evaluation SDK.

This module provides LLM-based evaluation for AI agents, replacing simple
keyword matching with sophisticated AI-assisted judgment.

Azure AI Foundry Evaluators Used:
---------------------------------
AGENT-SPECIFIC (Process Evaluation):
- IntentResolutionEvaluator: Did the agent correctly identify user intent?
- TaskAdherenceEvaluator: Did the response follow the assigned task/system prompt?
- ToolCallAccuracyEvaluator: Were the correct tools called with proper arguments?

QUALITY METRICS (System Evaluation):
- CoherenceEvaluator: Is the response logically coherent?
- FluencyEvaluator: Is the response well-written?
- RelevanceEvaluator: Is the response relevant to the query?
- ResponseCompletenessEvaluator: Does the response fully address the query?

MULTI-TURN SUPPORT:
- Azure AI Foundry supports conversation format with messages list
- Each message has role (system/user/assistant/tool), content, and optional tool_calls
- Evaluators understand conversation context and tool interactions

Reference: https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/agent-evaluate-sdk
"""

import os
import json
import asyncio
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from dotenv import load_dotenv

# Load environment from evaluation folder
_eval_dir = Path(__file__).parent
load_dotenv(_eval_dir / ".env")

# Azure AI Evaluation imports
try:
    from azure.ai.evaluation import (
        IntentResolutionEvaluator,
        TaskAdherenceEvaluator,
        ToolCallAccuracyEvaluator,
        CoherenceEvaluator,
        FluencyEvaluator,
        RelevanceEvaluator,
        # ResponseCompletenessEvaluator,  # May not be available in all versions
    )
    EVALUATORS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Azure AI Evaluation SDK not fully available: {e}")
    EVALUATORS_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ToolCall:
    """Represents a tool call made by the agent."""
    name: str
    arguments: dict = field(default_factory=dict)
    tool_call_id: str = ""
    result: Optional[dict] = None


@dataclass
class ConversationMessage:
    """A message in the conversation (OpenAI-style format)."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: Optional[str] = None  # For tool response messages
    timestamp: Optional[str] = None


@dataclass
class ToolDefinition:
    """Definition of a tool available to the agent."""
    name: str
    description: str
    parameters: dict = field(default_factory=dict)


@dataclass
class EvaluationInput:
    """Input data for LLM-judge evaluation."""
    query: str  # User query or conversation history
    response: str  # Agent's final response
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_definitions: list[ToolDefinition] = field(default_factory=list)
    system_prompt: str = ""  # Agent's system prompt for TaskAdherence
    conversation: list[ConversationMessage] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """Result from LLM-judge evaluation."""
    # Intent Resolution
    intent_resolution_score: Optional[float] = None
    intent_resolution_result: Optional[str] = None  # "pass" or "fail"
    intent_resolution_reason: Optional[str] = None
    
    # Task Adherence
    task_adherence_score: Optional[float] = None
    task_adherence_result: Optional[str] = None
    task_adherence_reason: Optional[str] = None
    
    # Tool Call Accuracy
    tool_call_accuracy_score: Optional[float] = None
    tool_call_accuracy_result: Optional[str] = None
    tool_call_accuracy_reason: Optional[str] = None
    
    # Quality Metrics
    coherence_score: Optional[float] = None
    fluency_score: Optional[float] = None
    relevance_score: Optional[float] = None
    
    # Solution Accuracy (custom evaluator using ground truth + rubric)
    solution_accuracy_score: Optional[float] = None
    solution_accuracy_reason: Optional[str] = None
    
    # Overall
    overall_pass: bool = False
    evaluation_time: float = 0.0
    errors: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════


def get_model_config() -> dict:
    """Get Azure OpenAI model configuration for evaluators."""
    return {
        "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "api_key": os.getenv("AZURE_OPENAI_KEY"),
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        "azure_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
    }


def _safe_float(value: any) -> Optional[float]:
    """Safely convert SDK output to float, handling string values."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            # Could be "pass" or "fail" - not a numeric score
            return None
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# SOLUTION ACCURACY EVALUATOR (Custom LLM-as-Judge)
# ═══════════════════════════════════════════════════════════════════════════════

SOLUTION_ACCURACY_PROMPT = """You are an expert evaluator assessing how well an AI agent's response addresses a customer service scenario.

## Ground Truth Solution
This is the ideal/expected solution for the scenario:
{ground_truth}

## Scoring Rubric
{scoring_rubric}

## Agent's Response
{agent_response}

## Your Task
Compare the agent's response against the ground truth solution using the scoring rubric.
Consider:
1. Does the response correctly identify the root cause/issue?
2. Does it provide accurate information (numbers, facts, policies)?
3. Does it offer appropriate solutions or next steps?
4. Does it address the customer's actual needs?

Provide your evaluation in this exact format:
SCORE: [1-5]
REASON: [One paragraph explaining why you gave this score, referencing specific parts of the rubric]
"""


class SolutionAccuracyEvaluator:
    """
    Custom evaluator that scores agent responses against ground truth solutions
    using a scoring rubric. This provides domain-specific accuracy evaluation.
    """
    
    def __init__(self, model_config: Optional[dict] = None):
        self.model_config = model_config or get_model_config()
        self._client = None
        
    def _get_client(self):
        """Lazily initialize the Azure OpenAI client."""
        if self._client is None:
            try:
                from openai import AzureOpenAI
                self._client = AzureOpenAI(
                    azure_endpoint=self.model_config["azure_endpoint"],
                    api_key=self.model_config["api_key"],
                    api_version=self.model_config["api_version"],
                )
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}")
        return self._client
    
    async def evaluate(
        self,
        agent_response: str,
        ground_truth: str,
        scoring_rubric: str,
    ) -> tuple[Optional[float], Optional[str]]:
        """
        Evaluate agent response against ground truth using the rubric.
        
        Returns:
            (score, reason) tuple where score is 1-5 or None on error
        """
        if not ground_truth or not scoring_rubric:
            return None, "No ground truth or rubric provided"
        
        client = self._get_client()
        if not client:
            return None, "OpenAI client not available"
        
        prompt = SOLUTION_ACCURACY_PROMPT.format(
            ground_truth=ground_truth,
            scoring_rubric=scoring_rubric,
            agent_response=agent_response,
        )
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=self.model_config["azure_deployment"],
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=500,
                )
            )
            
            content = response.choices[0].message.content
            
            # Parse response
            score = None
            reason = None
            
            for line in content.split("\n"):
                if line.startswith("SCORE:"):
                    try:
                        score = float(line.replace("SCORE:", "").strip())
                    except ValueError:
                        pass
                elif line.startswith("REASON:"):
                    reason = line.replace("REASON:", "").strip()
            
            # If reason spans multiple lines, get the rest
            if "REASON:" in content:
                reason_start = content.find("REASON:") + len("REASON:")
                reason = content[reason_start:].strip()
            
            return score, reason
            
        except Exception as e:
            return None, f"Evaluation error: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# LLM JUDGE EVALUATOR
# ═══════════════════════════════════════════════════════════════════════════════


class LLMJudgeEvaluator:
    """
    Evaluates agents using Azure AI Foundry's LLM-as-judge evaluators.
    
    This replaces simple keyword matching with sophisticated AI-assisted judgment
    that can understand context, intent, and quality of responses.
    
    Example usage:
        evaluator = LLMJudgeEvaluator()
        
        result = await evaluator.evaluate(
            query="What's my invoice total?",
            response="Your invoice total is $150.00",
            tool_calls=[ToolCall(name="get_customer_invoices", arguments={"customer_id": 1})],
            tool_definitions=[ToolDefinition(
                name="get_customer_invoices",
                description="Get invoices for a customer"
            )]
        )
        
        print(f"Intent Resolution: {result.intent_resolution_result}")
        print(f"Tool Accuracy: {result.tool_call_accuracy_result}")
    """
    
    def __init__(
        self,
        model_config: Optional[dict] = None,
        use_reasoning_model: bool = False,  # Set True for o-series models
        enable_agent_evaluators: bool = True,
        enable_quality_evaluators: bool = True,
    ):
        """
        Initialize LLM Judge evaluator.
        
        Args:
            model_config: Azure OpenAI configuration (uses env vars if None)
            use_reasoning_model: Set True if using o-series reasoning models
            enable_agent_evaluators: Enable IntentResolution, TaskAdherence, ToolCallAccuracy
            enable_quality_evaluators: Enable Coherence, Fluency, Relevance
        """
        self.model_config = model_config or get_model_config()
        self.use_reasoning_model = use_reasoning_model
        self.enable_agent_evaluators = enable_agent_evaluators
        self.enable_quality_evaluators = enable_quality_evaluators
        
        self._evaluators: dict = {}
        self._initialized = False
        
        # Custom solution accuracy evaluator (always available)
        self._solution_evaluator = SolutionAccuracyEvaluator(self.model_config)
    
    def _init_evaluators(self):
        """Lazily initialize evaluators."""
        if self._initialized or not EVALUATORS_AVAILABLE:
            return
        
        try:
            if self.enable_agent_evaluators:
                # Agent-specific evaluators (support reasoning models)
                eval_kwargs = {"model_config": self.model_config}
                if self.use_reasoning_model:
                    eval_kwargs["is_reasoning_model"] = True
                
                self._evaluators["intent_resolution"] = IntentResolutionEvaluator(**eval_kwargs)
                self._evaluators["task_adherence"] = TaskAdherenceEvaluator(**eval_kwargs)
                self._evaluators["tool_call_accuracy"] = ToolCallAccuracyEvaluator(**eval_kwargs)
            
            if self.enable_quality_evaluators:
                # Quality evaluators (don't use reasoning model for efficiency)
                quality_config = {"model_config": self.model_config}
                self._evaluators["coherence"] = CoherenceEvaluator(**quality_config)
                self._evaluators["fluency"] = FluencyEvaluator(**quality_config)
                self._evaluators["relevance"] = RelevanceEvaluator(**quality_config)
            
            self._initialized = True
            print(f"✅ Initialized {len(self._evaluators)} LLM-judge evaluators")
        
        except Exception as e:
            print(f"⚠️ Error initializing evaluators: {e}")
            self._initialized = True  # Don't retry
    
    def _format_tool_calls(self, tool_calls: list[ToolCall]) -> list[dict]:
        """Format tool calls for Azure AI Evaluation SDK."""
        return [
            {
                "type": "tool_call",
                "tool_call_id": tc.tool_call_id or f"call_{i}",
                "name": tc.name,
                "arguments": tc.arguments
            }
            for i, tc in enumerate(tool_calls)
        ]
    
    def _format_tool_definitions(self, tool_definitions: list[ToolDefinition]) -> list[dict]:
        """Format tool definitions for Azure AI Evaluation SDK."""
        return [
            {
                "name": td.name,
                "description": td.description,
                "parameters": td.parameters or {
                    "type": "object",
                    "properties": {},
                }
            }
            for td in tool_definitions
        ]
    
    def _format_conversation_query(
        self,
        query: str,
        system_prompt: str,
        conversation: list[ConversationMessage]
    ) -> list[dict]:
        """
        Format conversation history as query for multi-turn evaluation.
        
        Azure AI Foundry expects query as a list of OpenAI-style messages
        for multi-turn evaluation.
        """
        messages = []
        
        # System message first (required)
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        else:
            messages.append({
                "role": "system",
                "content": "You are a helpful customer service agent."
            })
        
        # Add conversation history
        for msg in conversation:
            message = {
                "role": msg.role,
                "createdAt": msg.timestamp or datetime.now().isoformat() + "Z",
            }
            
            if msg.role == "tool":
                message["content"] = [{"type": "tool_result", "tool_result": msg.content}]
                if msg.tool_call_id:
                    message["tool_call_id"] = msg.tool_call_id
            elif msg.tool_calls:
                message["content"] = [
                    {
                        "type": "tool_call",
                        "tool_call_id": tc.tool_call_id or f"call_{i}",
                        "name": tc.name,
                        "arguments": tc.arguments
                    }
                    for i, tc in enumerate(msg.tool_calls)
                ]
            else:
                message["content"] = [{"type": "text", "text": msg.content}]
            
            messages.append(message)
        
        # Final user query if not already in conversation
        if not conversation or conversation[-1].role != "user":
            messages.append({
                "role": "user",
                "createdAt": datetime.now().isoformat() + "Z",
                "content": [{"type": "text", "text": query}]
            })
        
        return messages
    
    async def evaluate(
        self,
        query: str,
        response: str,
        tool_calls: Optional[list[ToolCall]] = None,
        tool_definitions: Optional[list[ToolDefinition]] = None,
        system_prompt: str = "",
        conversation: Optional[list[ConversationMessage]] = None,
        ground_truth_solution: str = "",
        scoring_rubric: str = "",
    ) -> EvaluationResult:
        """
        Evaluate agent response using LLM judges.
        
        Args:
            query: The user's query
            response: The agent's response
            tool_calls: List of tools the agent called
            tool_definitions: Available tool definitions
            system_prompt: Agent's system prompt
            conversation: Full conversation history for multi-turn
            ground_truth_solution: The ideal/expected solution for the scenario
            scoring_rubric: Criteria for evaluating solution accuracy (1-5 scale)
            
        Returns:
            EvaluationResult with scores, pass/fail, and reasons
        """
        import time
        start_time = time.time()
        
        result = EvaluationResult()
        
        if not EVALUATORS_AVAILABLE:
            result.errors.append("Azure AI Evaluation SDK not available")
            return result
        
        self._init_evaluators()
        
        # Format inputs
        formatted_tool_calls = self._format_tool_calls(tool_calls or [])
        formatted_tool_defs = self._format_tool_definitions(tool_definitions or [])
        
        # Use conversation format for multi-turn if provided
        if conversation:
            formatted_query = self._format_conversation_query(
                query, system_prompt, conversation
            )
        else:
            formatted_query = query
        
        # Run evaluators (they're synchronous, so we run in executor)
        loop = asyncio.get_event_loop()
        
        # Intent Resolution
        if "intent_resolution" in self._evaluators:
            try:
                intent_result = await loop.run_in_executor(
                    None,
                    lambda: self._evaluators["intent_resolution"](
                        query=formatted_query,
                        response=response,
                    )
                )
                result.intent_resolution_score = _safe_float(intent_result.get("intent_resolution"))
                result.intent_resolution_result = intent_result.get("intent_resolution_result")
                result.intent_resolution_reason = intent_result.get("intent_resolution_reason")
            except Exception as e:
                result.errors.append(f"IntentResolution error: {e}")
        
        # Task Adherence
        if "task_adherence" in self._evaluators:
            try:
                task_result = await loop.run_in_executor(
                    None,
                    lambda: self._evaluators["task_adherence"](
                        query=formatted_query,
                        response=response,
                    )
                )
                result.task_adherence_score = _safe_float(task_result.get("task_adherence"))
                result.task_adherence_result = task_result.get("task_adherence_result")
                result.task_adherence_reason = task_result.get("task_adherence_reason")
            except Exception as e:
                result.errors.append(f"TaskAdherence error: {e}")
        
        # Tool Call Accuracy (only if tool_calls provided)
        if "tool_call_accuracy" in self._evaluators and formatted_tool_calls:
            try:
                tool_result = await loop.run_in_executor(
                    None,
                    lambda: self._evaluators["tool_call_accuracy"](
                        query=query,  # Simple string for tool accuracy
                        tool_calls=formatted_tool_calls,
                        tool_definitions=formatted_tool_defs,
                    )
                )
                result.tool_call_accuracy_score = _safe_float(tool_result.get("tool_call_accuracy"))
                result.tool_call_accuracy_result = tool_result.get("tool_call_accuracy_result")
                result.tool_call_accuracy_reason = str(tool_result.get("details", ""))
            except Exception as e:
                result.errors.append(f"ToolCallAccuracy error: {e}")
        
        # Quality Metrics
        if "coherence" in self._evaluators:
            try:
                coh_result = await loop.run_in_executor(
                    None,
                    lambda: self._evaluators["coherence"](
                        query=query,
                        response=response,
                    )
                )
                result.coherence_score = _safe_float(coh_result.get("coherence"))
            except Exception as e:
                result.errors.append(f"Coherence error: {e}")
        
        if "fluency" in self._evaluators:
            try:
                flu_result = await loop.run_in_executor(
                    None,
                    lambda: self._evaluators["fluency"](
                        query=query,
                        response=response,
                    )
                )
                result.fluency_score = _safe_float(flu_result.get("fluency"))
            except Exception as e:
                result.errors.append(f"Fluency error: {e}")
        
        if "relevance" in self._evaluators:
            try:
                rel_result = await loop.run_in_executor(
                    None,
                    lambda: self._evaluators["relevance"](
                        query=query,
                        response=response,
                    )
                )
                result.relevance_score = _safe_float(rel_result.get("relevance"))
            except Exception as e:
                result.errors.append(f"Relevance error: {e}")
        
        # Solution Accuracy (custom evaluator with ground truth + rubric)
        if ground_truth_solution and scoring_rubric:
            try:
                score, reason = await self._solution_evaluator.evaluate(
                    agent_response=response,
                    ground_truth=ground_truth_solution,
                    scoring_rubric=scoring_rubric,
                )
                result.solution_accuracy_score = score
                result.solution_accuracy_reason = reason
            except Exception as e:
                result.errors.append(f"SolutionAccuracy error: {e}")
        
        # Determine overall pass
        passes = []
        if result.intent_resolution_result:
            passes.append(result.intent_resolution_result == "pass")
        if result.task_adherence_result:
            passes.append(result.task_adherence_result == "pass")
        if result.tool_call_accuracy_result:
            passes.append(result.tool_call_accuracy_result == "pass")
        # Solution accuracy: pass if score >= 3 (Adequate or better)
        if result.solution_accuracy_score is not None:
            passes.append(result.solution_accuracy_score >= 3)
        
        result.overall_pass = all(passes) if passes else False
        result.evaluation_time = time.time() - start_time
        
        return result
    
    def evaluate_sync(self, **kwargs) -> EvaluationResult:
        """Synchronous wrapper for evaluate()."""
        return asyncio.run(self.evaluate(**kwargs))


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


async def evaluate_agent_response(
    query: str,
    response: str,
    tool_calls: Optional[list[str]] = None,  # Just tool names for simplicity
    tool_definitions: Optional[list[dict]] = None,
) -> EvaluationResult:
    """
    Simple function to evaluate an agent response.
    
    Args:
        query: User's query
        response: Agent's response
        tool_calls: List of tool names that were called
        tool_definitions: List of {name, description} dicts
    
    Returns:
        EvaluationResult with scores and pass/fail
    """
    evaluator = LLMJudgeEvaluator()
    
    # Convert simple tool names to ToolCall objects
    tc_objects = [ToolCall(name=name) for name in (tool_calls or [])]
    
    # Convert simple dicts to ToolDefinition objects
    td_objects = [
        ToolDefinition(
            name=td.get("name", ""),
            description=td.get("description", "")
        )
        for td in (tool_definitions or [])
    ]
    
    return await evaluator.evaluate(
        query=query,
        response=response,
        tool_calls=tc_objects,
        tool_definitions=td_objects,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════════════════════════════


async def demo():
    """Demo the LLM judge evaluator."""
    print("=" * 80)
    print("LLM-as-Judge Evaluator Demo")
    print("=" * 80)
    
    if not EVALUATORS_AVAILABLE:
        print("\n❌ Azure AI Evaluation SDK not available.")
        print("Install with: pip install azure-ai-evaluation")
        return
    
    # Check required environment variables
    required_vars = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_KEY"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        print(f"\n⚠️ Missing environment variables: {missing}")
        print("Set these in tests/evaluation/.env")
        return
    
    evaluator = LLMJudgeEvaluator(
        enable_agent_evaluators=True,
        enable_quality_evaluators=True,
    )
    
    # Test case: Customer asks about invoice
    print("\n📋 Test Case: Invoice Query")
    print("-" * 40)
    
    result = await evaluator.evaluate(
        query="What is my current invoice total for account 123?",
        response="Based on your account records, your current invoice total is $542.50. This includes your monthly subscription fee of $99.99, data overage charges of $42.51, and equipment rental of $400.00.",
        tool_calls=[
            ToolCall(
                name="get_customer_invoices",
                arguments={"customer_id": 123}
            )
        ],
        tool_definitions=[
            ToolDefinition(
                name="get_customer_invoices",
                description="Retrieves invoice details for a customer account"
            ),
            ToolDefinition(
                name="get_customer_detail",
                description="Gets customer profile information"
            ),
        ],
    )
    
    print(f"\n🎯 Intent Resolution:")
    print(f"   Score: {result.intent_resolution_score}/5")
    print(f"   Result: {result.intent_resolution_result}")
    print(f"   Reason: {result.intent_resolution_reason}")
    
    print(f"\n📋 Task Adherence:")
    print(f"   Score: {result.task_adherence_score}/5")
    print(f"   Result: {result.task_adherence_result}")
    print(f"   Reason: {result.task_adherence_reason}")
    
    print(f"\n🔧 Tool Call Accuracy:")
    print(f"   Score: {result.tool_call_accuracy_score}/5")
    print(f"   Result: {result.tool_call_accuracy_result}")
    
    print(f"\n✨ Quality Metrics:")
    print(f"   Coherence: {result.coherence_score}/5")
    print(f"   Fluency: {result.fluency_score}/5")
    print(f"   Relevance: {result.relevance_score}/5")
    
    print(f"\n{'✅ OVERALL PASS' if result.overall_pass else '❌ OVERALL FAIL'}")
    print(f"⏱️ Evaluation time: {result.evaluation_time:.2f}s")
    
    if result.errors:
        print(f"\n⚠️ Errors: {result.errors}")


if __name__ == "__main__":
    asyncio.run(demo())
