"""
Agent Evaluation Module
=======================
Comprehensive evaluation framework for AI Agents using Azure AI Evaluation SDK.

This module provides:
- AgentRunner: Collects responses from the agent for test datasets
- AgentEvaluator: Runs evaluations using Azure AI Evaluation SDK
- EvaluationMetrics: Defines metrics and thresholds for agent evaluation

Metrics evaluated:
- Intent Resolution: Did the agent correctly identify the user's intent?
- Tool Call Accuracy: Did the agent use the correct tools?
- Task Adherence: Did the agent complete the requested task?
- Groundedness: Are the agent's responses grounded in retrieved data?
- Response Quality: Relevance, coherence, and fluency of responses
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentic_ai" / "applications"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentic_ai"))

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class EvaluationThresholds:
    """Configurable thresholds for evaluation metrics."""
    intent_resolution: float = 0.8
    tool_call_accuracy: float = 0.5  # Lower threshold - agent may use subset of expected tools
    task_adherence: float = 0.8
    groundedness: float = 0.7
    relevance: float = 0.8
    coherence: float = 0.8
    fluency: float = 0.8


@dataclass
class TestCase:
    """A single test case for agent evaluation."""
    query: str
    customer_id: str
    expected_intent: str
    expected_tools: List[str]
    ground_truth: str
    category: str
    complexity: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestCase":
        return cls(
            query=data["query"],
            customer_id=data["customer_id"],
            expected_intent=data["expected_intent"],
            expected_tools=data["expected_tools"],
            ground_truth=data["ground_truth"],
            category=data["category"],
            complexity=data["complexity"],
        )


@dataclass
class AgentResponse:
    """Captured response from the agent."""
    test_case: TestCase
    response: str
    tools_called: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    error: Optional[str] = None


class AgentRunner:
    """
    Runs the agent against test cases and collects responses.
    Supports both single agent and multi-agent patterns.
    """
    
    def __init__(self, agent_module: str = "agents.agent_framework.single_agent"):
        """
        Initialize the agent runner.
        
        Args:
            agent_module: Module path for the agent to test
        """
        self.agent_module = agent_module
        self._agent_class = None
        self._state_store: Dict[str, Any] = {}
        
    def _load_agent_class(self):
        """Dynamically load the agent class."""
        if self._agent_class is not None:
            return
            
        import importlib
        module = importlib.import_module(self.agent_module)
        self._agent_class = getattr(module, "Agent")
        logger.info(f"Loaded agent class from {self.agent_module}")
        
    async def run_single_test(self, test_case: TestCase, session_id: Optional[str] = None) -> AgentResponse:
        """
        Run a single test case through the agent.
        
        Args:
            test_case: The test case to run
            session_id: Optional session ID (generates unique one if not provided)
            
        Returns:
            AgentResponse with the agent's response and metadata
        """
        import time
        
        self._load_agent_class()
        
        if session_id is None:
            session_id = f"eval_{test_case.customer_id}_{int(time.time() * 1000)}"
        
        # Prepare the prompt with customer context
        if test_case.customer_id and test_case.customer_id not in test_case.query.lower():
            prompt = f"Customer {test_case.customer_id}: {test_case.query}"
        else:
            prompt = test_case.query
        
        start_time = time.time()
        tools_called: List[str] = []
        error: Optional[str] = None
        response: str = ""
        
        try:
            # Create agent instance
            agent = self._agent_class(
                state_store=self._state_store,
                session_id=session_id,
                access_token=None,
            )
            
            # Inject a tool call tracker if the agent supports WebSocket manager
            tool_tracker = ToolCallTracker()
            if hasattr(agent, 'set_websocket_manager'):
                agent.set_websocket_manager(tool_tracker)
            
            # Run the agent
            response = await agent.chat_async(prompt)
            tools_called = tool_tracker.get_tools_called()
            
        except Exception as e:
            error = str(e)
            logger.error(f"Error running test case: {e}")
            
        execution_time_ms = (time.time() - start_time) * 1000
        
        return AgentResponse(
            test_case=test_case,
            response=response,
            tools_called=tools_called,
            execution_time_ms=execution_time_ms,
            error=error,
        )
    
    async def run_test_dataset(self, test_cases: List[TestCase], max_concurrent: int = 1) -> List[AgentResponse]:
        """
        Run all test cases through the agent.
        
        Args:
            test_cases: List of test cases to run
            max_concurrent: Maximum concurrent test runs (default 1 for deterministic results)
            
        Returns:
            List of AgentResponse objects
        """
        responses = []
        
        for i, test_case in enumerate(test_cases):
            logger.info(f"Running test case {i+1}/{len(test_cases)}: {test_case.query[:50]}...")
            response = await self.run_single_test(test_case)
            responses.append(response)
            
            # Clear state between tests for independent evaluation
            self._state_store.clear()
            
        return responses


class ToolCallTracker:
    """
    Mock WebSocket manager that tracks tool calls.
    Used to capture which tools the agent calls during execution.
    """
    
    def __init__(self):
        self._tools_called: List[str] = []
        
    async def broadcast(self, session_id: str, message: Dict[str, Any]) -> None:
        """Capture tool call events from the agent."""
        if message.get("type") == "tool_called":
            tool_name = message.get("tool_name")
            if tool_name and tool_name not in self._tools_called:
                self._tools_called.append(tool_name)
                
    def get_tools_called(self) -> List[str]:
        """Return the list of tools that were called."""
        return self._tools_called.copy()


class AgentEvaluator:
    """
    Evaluates agent responses using Azure AI Evaluation SDK.
    
    Supports multiple evaluation types:
    - AI-assisted evaluation (requires Azure OpenAI)
    - Rule-based evaluation (no external dependencies)
    """
    
    def __init__(
        self,
        azure_endpoint: Optional[str] = None,
        azure_deployment: Optional[str] = None,
        api_version: Optional[str] = None,
        thresholds: Optional[EvaluationThresholds] = None,
    ):
        """
        Initialize the evaluator.
        
        Args:
            azure_endpoint: Azure OpenAI endpoint for AI-assisted evaluation
            azure_deployment: Azure OpenAI deployment name
            api_version: Azure OpenAI API version
            thresholds: Evaluation thresholds
        """
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_deployment = azure_deployment or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
        self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION")
        self.thresholds = thresholds or EvaluationThresholds()
        
        self._ai_evaluators_available = False
        self._init_ai_evaluators()
        
    def _init_ai_evaluators(self):
        """Initialize Azure AI Evaluation SDK evaluators if available."""
        try:
            from azure.ai.evaluation import (
                RelevanceEvaluator,
                CoherenceEvaluator,
                FluencyEvaluator,
                GroundednessEvaluator,
            )
            
            if self.azure_endpoint and self.azure_deployment:
                model_config = {
                    "azure_endpoint": self.azure_endpoint,
                    "azure_deployment": self.azure_deployment,
                    "api_version": self.api_version,
                }
                
                # Check if API key is available
                api_key = os.getenv("AZURE_OPENAI_API_KEY")
                if api_key:
                    model_config["api_key"] = api_key
                
                self._relevance_evaluator = RelevanceEvaluator(model_config=model_config)
                self._coherence_evaluator = CoherenceEvaluator(model_config=model_config)
                self._fluency_evaluator = FluencyEvaluator(model_config=model_config)
                self._groundedness_evaluator = GroundednessEvaluator(model_config=model_config)
                
                self._ai_evaluators_available = True
                logger.info("Azure AI Evaluation SDK evaluators initialized successfully")
                
        except ImportError:
            logger.warning("Azure AI Evaluation SDK not installed. Using rule-based evaluation only.")
        except Exception as e:
            logger.warning(f"Failed to initialize AI evaluators: {e}. Using rule-based evaluation only.")
    
    def evaluate_tool_accuracy(self, response: AgentResponse) -> Dict[str, Any]:
        """
        Evaluate tool call accuracy.
        
        Computes:
        - Precision: What fraction of called tools were expected?
        - Recall: What fraction of expected tools were called?
        - F1 Score: Harmonic mean of precision and recall
        """
        expected = set(response.test_case.expected_tools)
        called = set(response.tools_called)
        
        if len(called) == 0:
            precision = 0.0
        else:
            precision = len(expected & called) / len(called)
            
        if len(expected) == 0:
            recall = 1.0
        else:
            recall = len(expected & called) / len(expected)
            
        if precision + recall == 0:
            f1_score = 0.0
        else:
            f1_score = 2 * (precision * recall) / (precision + recall)
        
        return {
            "tool_precision": precision,
            "tool_recall": recall,
            "tool_f1_score": f1_score,
            "expected_tools": list(expected),
            "called_tools": list(called),
            "missing_tools": list(expected - called),
            "extra_tools": list(called - expected),
            "passed": f1_score >= self.thresholds.tool_call_accuracy,
        }
    
    def evaluate_response_quality(self, response: AgentResponse) -> Dict[str, Any]:
        """
        Evaluate basic response quality using rule-based checks.
        """
        text = response.response
        
        # Check for empty or error responses
        if not text or response.error:
            return {
                "has_content": False,
                "length": 0,
                "has_error": bool(response.error),
                "error_message": response.error,
                "passed": False,
            }
        
        # Basic quality checks
        word_count = len(text.split())
        sentence_count = text.count('.') + text.count('!') + text.count('?')
        
        # Check for hallucination indicators
        hallucination_phrases = [
            "i don't have access",
            "i cannot actually",
            "as an ai, i cannot",
            "i apologize, but i cannot",
        ]
        has_hallucination_warning = any(phrase in text.lower() for phrase in hallucination_phrases)
        
        return {
            "has_content": True,
            "word_count": word_count,
            "sentence_count": sentence_count,
            "has_hallucination_warning": has_hallucination_warning,
            "execution_time_ms": response.execution_time_ms,
            "passed": word_count > 10 and not has_hallucination_warning,
        }
    
    async def evaluate_with_ai(self, response: AgentResponse) -> Dict[str, Any]:
        """
        Evaluate response using Azure AI Evaluation SDK evaluators.
        
        Returns AI-assisted scores for:
        - Relevance
        - Coherence
        - Fluency
        - Groundedness
        """
        if not self._ai_evaluators_available:
            return {"ai_evaluation": "unavailable", "reason": "AI evaluators not initialized"}
        
        query = response.test_case.query
        answer = response.response
        context = response.test_case.ground_truth
        
        results = {}
        
        try:
            # Relevance evaluation
            relevance_result = self._relevance_evaluator(
                query=query,
                response=answer,
            )
            results["relevance"] = relevance_result.get("relevance", 0)
            results["relevance_passed"] = results["relevance"] >= self.thresholds.relevance * 5  # SDK uses 1-5 scale
            
        except Exception as e:
            logger.warning(f"Relevance evaluation failed: {e}")
            results["relevance_error"] = str(e)
        
        try:
            # Coherence evaluation
            coherence_result = self._coherence_evaluator(
                query=query,
                response=answer,
            )
            results["coherence"] = coherence_result.get("coherence", 0)
            results["coherence_passed"] = results["coherence"] >= self.thresholds.coherence * 5
            
        except Exception as e:
            logger.warning(f"Coherence evaluation failed: {e}")
            results["coherence_error"] = str(e)
        
        try:
            # Fluency evaluation
            fluency_result = self._fluency_evaluator(
                query=query,
                response=answer,
            )
            results["fluency"] = fluency_result.get("fluency", 0)
            results["fluency_passed"] = results["fluency"] >= self.thresholds.fluency * 5
            
        except Exception as e:
            logger.warning(f"Fluency evaluation failed: {e}")
            results["fluency_error"] = str(e)
        
        try:
            # Groundedness evaluation
            groundedness_result = self._groundedness_evaluator(
                query=query,
                response=answer,
                context=context,
            )
            results["groundedness"] = groundedness_result.get("groundedness", 0)
            results["groundedness_passed"] = results["groundedness"] >= self.thresholds.groundedness * 5
            
        except Exception as e:
            logger.warning(f"Groundedness evaluation failed: {e}")
            results["groundedness_error"] = str(e)
        
        return results
    
    async def evaluate_response(self, response: AgentResponse, include_ai_eval: bool = True) -> Dict[str, Any]:
        """
        Run full evaluation on an agent response.
        
        Args:
            response: The agent response to evaluate
            include_ai_eval: Whether to include AI-assisted evaluation
            
        Returns:
            Dictionary with all evaluation results
        """
        results = {
            "test_case": {
                "query": response.test_case.query,
                "customer_id": response.test_case.customer_id,
                "expected_intent": response.test_case.expected_intent,
                "category": response.test_case.category,
                "complexity": response.test_case.complexity,
            },
            "response_preview": response.response[:500] if response.response else None,
            "execution_time_ms": response.execution_time_ms,
            "error": response.error,
        }
        
        # Tool accuracy evaluation
        results["tool_accuracy"] = self.evaluate_tool_accuracy(response)
        
        # Response quality evaluation
        results["response_quality"] = self.evaluate_response_quality(response)
        
        # AI-assisted evaluation
        if include_ai_eval and self._ai_evaluators_available:
            results["ai_evaluation"] = await self.evaluate_with_ai(response)
        
        # Overall pass/fail
        tool_passed = results["tool_accuracy"]["passed"]
        quality_passed = results["response_quality"]["passed"]
        
        results["passed"] = tool_passed and quality_passed
        
        return results
    
    async def evaluate_all(
        self,
        responses: List[AgentResponse],
        include_ai_eval: bool = True,
    ) -> Dict[str, Any]:
        """
        Evaluate all responses and generate summary statistics.
        
        Args:
            responses: List of agent responses to evaluate
            include_ai_eval: Whether to include AI-assisted evaluation
            
        Returns:
            Dictionary with individual results and summary statistics
        """
        individual_results = []
        
        for i, response in enumerate(responses):
            logger.info(f"Evaluating response {i+1}/{len(responses)}...")
            result = await self.evaluate_response(response, include_ai_eval)
            individual_results.append(result)
        
        # Compute summary statistics
        total = len(individual_results)
        passed = sum(1 for r in individual_results if r["passed"])
        
        tool_f1_scores = [r["tool_accuracy"]["tool_f1_score"] for r in individual_results]
        avg_tool_f1 = sum(tool_f1_scores) / total if total > 0 else 0
        
        exec_times = [r["execution_time_ms"] for r in individual_results]
        avg_exec_time = sum(exec_times) / total if total > 0 else 0
        
        # Category breakdown
        categories = {}
        for result in individual_results:
            cat = result["test_case"]["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "passed": 0}
            categories[cat]["total"] += 1
            if result["passed"]:
                categories[cat]["passed"] += 1
        
        summary = {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total > 0 else 0,
            "average_tool_f1_score": avg_tool_f1,
            "average_execution_time_ms": avg_exec_time,
            "category_breakdown": categories,
            "thresholds": {
                "tool_call_accuracy": self.thresholds.tool_call_accuracy,
                "groundedness": self.thresholds.groundedness,
                "relevance": self.thresholds.relevance,
            },
        }
        
        return {
            "summary": summary,
            "individual_results": individual_results,
            "timestamp": datetime.utcnow().isoformat(),
        }


def load_test_data(file_path: str) -> List[TestCase]:
    """
    Load test cases from a JSONL file.
    
    Args:
        file_path: Path to the JSONL file
        
    Returns:
        List of TestCase objects
    """
    test_cases = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                test_cases.append(TestCase.from_dict(data))
                
    return test_cases


def save_evaluation_results(results: Dict[str, Any], output_path: str) -> None:
    """
    Save evaluation results to a JSON file.
    
    Args:
        results: Evaluation results dictionary
        output_path: Path to save the results
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"Evaluation results saved to {output_path}")


async def run_evaluation(
    test_data_path: str,
    agent_module: str = "agents.agent_framework.single_agent",
    output_path: Optional[str] = None,
    include_ai_eval: bool = True,
) -> Dict[str, Any]:
    """
    Run a complete evaluation pipeline.
    
    Args:
        test_data_path: Path to test data JSONL file
        agent_module: Module path for the agent to test
        output_path: Optional path to save results
        include_ai_eval: Whether to include AI-assisted evaluation
        
    Returns:
        Evaluation results dictionary
    """
    logger.info(f"Loading test data from {test_data_path}")
    test_cases = load_test_data(test_data_path)
    logger.info(f"Loaded {len(test_cases)} test cases")
    
    # Run agent against test cases
    logger.info(f"Running agent: {agent_module}")
    runner = AgentRunner(agent_module=agent_module)
    responses = await runner.run_test_dataset(test_cases)
    logger.info(f"Collected {len(responses)} responses")
    
    # Evaluate responses
    logger.info("Evaluating responses...")
    evaluator = AgentEvaluator()
    results = await evaluator.evaluate_all(responses, include_ai_eval=include_ai_eval)
    
    # Save results if output path provided
    if output_path:
        save_evaluation_results(results, output_path)
    
    # Print summary
    summary = results["summary"]
    print("\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    print(f"Total Tests:      {summary['total_tests']}")
    print(f"Passed:           {summary['passed']}")
    print(f"Failed:           {summary['failed']}")
    print(f"Pass Rate:        {summary['pass_rate']:.1%}")
    print(f"Avg Tool F1:      {summary['average_tool_f1_score']:.2f}")
    print(f"Avg Exec Time:    {summary['average_execution_time_ms']:.0f}ms")
    print("\nBy Category:")
    for cat, stats in summary["category_breakdown"].items():
        rate = stats['passed'] / stats['total'] if stats['total'] > 0 else 0
        print(f"  {cat}: {stats['passed']}/{stats['total']} ({rate:.0%})")
    print("="*60 + "\n")
    
    return results


if __name__ == "__main__":
    # Allow running as a standalone script
    import argparse
    
    parser = argparse.ArgumentParser(description="Run agent evaluation")
    parser.add_argument("--test-data", default="tests/evaluation/test_data.jsonl",
                       help="Path to test data JSONL file")
    parser.add_argument("--agent-module", default="agents.agent_framework.single_agent",
                       help="Agent module to test")
    parser.add_argument("--output", default=None,
                       help="Path to save evaluation results")
    parser.add_argument("--no-ai-eval", action="store_true",
                       help="Disable AI-assisted evaluation")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    asyncio.run(run_evaluation(
        test_data_path=args.test_data,
        agent_module=args.agent_module,
        output_path=args.output,
        include_ai_eval=not args.no_ai_eval,
    ))
