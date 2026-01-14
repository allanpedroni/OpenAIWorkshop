"""
Agent Comparison Tests

This module compares the performance of different agent implementations
(single_agent vs reflection_agent) using the same test dataset.

Usage:
    # Run from tests/evaluation folder:
    uv run pytest test_agent_comparison.py -v

    # Run with detailed comparison report:
    uv run pytest test_agent_comparison.py -v -s --tb=short

    # Run quick comparison (fewer test cases):
    uv run pytest test_agent_comparison.py -v -k "quick"
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv

# ═══════════════════════════════════════════════════════════════════════════════
# PATH SETUP
# ═══════════════════════════════════════════════════════════════════════════════

# Add paths for imports
_eval_dir = Path(__file__).parent.resolve()
_tests_dir = _eval_dir.parent
_workspace_root = _tests_dir.parent
_agentic_ai_dir = _workspace_root / "agentic_ai"

# Add paths for agent imports
sys.path.insert(0, str(_agentic_ai_dir))
sys.path.insert(0, str(_tests_dir))

# Load environment from evaluation folder
load_dotenv(_eval_dir / ".env")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class AgentResult:
    """Result from a single agent run."""
    
    agent_name: str
    query: str
    response: str
    tools_called: list[str]
    execution_time: float
    error: str | None = None
    
    @property
    def success(self) -> bool:
        return self.error is None and bool(self.response)


@dataclass
class ComparisonMetrics:
    """Comparison metrics between two agents."""
    
    agent_a: str
    agent_b: str
    test_count: int
    agent_a_metrics: dict[str, float] = field(default_factory=dict)
    agent_b_metrics: dict[str, float] = field(default_factory=dict)
    differences: dict[str, float] = field(default_factory=dict)
    
    def to_report(self) -> str:
        """Generate a formatted comparison report."""
        lines = [
            "═" * 70,
            f"AGENT COMPARISON REPORT: {self.agent_a} vs {self.agent_b}",
            "═" * 70,
            f"Test Cases: {self.test_count}",
            "",
            f"{'Metric':<30} {self.agent_a:>15} {self.agent_b:>15} {'Diff':>10}",
            "-" * 70,
        ]
        
        all_metrics = set(self.agent_a_metrics.keys()) | set(self.agent_b_metrics.keys())
        for metric in sorted(all_metrics):
            a_val = self.agent_a_metrics.get(metric, 0)
            b_val = self.agent_b_metrics.get(metric, 0)
            diff = self.differences.get(metric, b_val - a_val)
            diff_str = f"+{diff:.3f}" if diff > 0 else f"{diff:.3f}"
            lines.append(f"{metric:<30} {a_val:>15.3f} {b_val:>15.3f} {diff_str:>10}")
        
        lines.extend(["-" * 70, ""])
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT RUNNER
# ═══════════════════════════════════════════════════════════════════════════════


class AgentComparisonRunner:
    """Runs and compares multiple agent implementations."""
    
    def __init__(self):
        self.mcp_server_uri = os.getenv("MCP_SERVER_URI", "http://localhost:8000/mcp")
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-03-01-preview")
        
        # Agent module paths
        self.single_agent_module = os.getenv(
            "SINGLE_AGENT_MODULE", 
            "agents.agent_framework.single_agent"
        )
        self.reflection_agent_module = os.getenv(
            "REFLECTION_AGENT_MODULE",
            "agents.agent_framework.multi_agent.reflection_agent"
        )
    
    async def _run_single_agent(self, query: str, session_id: str | None = None) -> AgentResult:
        """Run the single agent implementation."""
        from agents.agent_framework.single_agent import Agent
        
        start_time = time.time()
        tools_called = []
        error = None
        response = ""
        
        # Use unique session ID for isolation
        if session_id is None:
            session_id = f"eval_single_{int(time.time() * 1000)}"
        
        state_store: dict[str, Any] = {}
        
        try:
            # Create agent instance
            agent = Agent(state_store=state_store, session_id=session_id)
            
            # Run the agent
            response = await agent.chat_async(query)
            
            # Try to extract tool calls from chat history if available
            if hasattr(agent, 'chat_history'):
                for entry in agent.chat_history:
                    if isinstance(entry, dict) and 'tool_calls' in entry:
                        for tc in entry.get('tool_calls', []):
                            if isinstance(tc, dict):
                                tools_called.append(tc.get('name', str(tc)))
                            else:
                                tools_called.append(str(tc))
                
        except Exception as e:
            error = str(e)
            response = ""
        
        return AgentResult(
            agent_name="single_agent",
            query=query,
            response=response,
            tools_called=tools_called,
            execution_time=time.time() - start_time,
            error=error
        )
    
    async def _run_reflection_agent(self, query: str, session_id: str | None = None) -> AgentResult:
        """Run the reflection agent implementation."""
        from agents.agent_framework.multi_agent.reflection_agent import Agent
        
        start_time = time.time()
        tools_called = []
        error = None
        response = ""
        
        # Use unique session ID for isolation
        if session_id is None:
            session_id = f"eval_reflection_{int(time.time() * 1000)}"
        
        state_store: dict[str, Any] = {}
        
        try:
            # Create agent instance
            agent = Agent(state_store=state_store, session_id=session_id)
            
            # Run the agent
            response = await agent.chat_async(query)
            
            # Try to extract tool calls from chat history if available
            if hasattr(agent, 'chat_history'):
                for entry in agent.chat_history:
                    if isinstance(entry, dict) and 'tool_calls' in entry:
                        for tc in entry.get('tool_calls', []):
                            if isinstance(tc, dict):
                                tools_called.append(tc.get('name', str(tc)))
                            else:
                                tools_called.append(str(tc))
                
        except Exception as e:
            error = str(e)
            response = ""
        
        return AgentResult(
            agent_name="reflection_agent",
            query=query,
            response=response,
            tools_called=tools_called,
            execution_time=time.time() - start_time,
            error=error
        )
    
    async def run_comparison(
        self,
        queries: list[str],
        expected_tools: list[list[str]] | None = None
    ) -> ComparisonMetrics:
        """Run both agents on a list of queries and compare results."""
        
        single_results: list[AgentResult] = []
        reflection_results: list[AgentResult] = []
        
        for i, query in enumerate(queries):
            print(f"\n[{i+1}/{len(queries)}] Testing: {query[:50]}...")
            
            # Run both agents
            single_result = await self._run_single_agent(query)
            single_results.append(single_result)
            print(f"  Single Agent: {single_result.execution_time:.2f}s, "
                  f"tools={len(single_result.tools_called)}, "
                  f"success={single_result.success}")
            
            reflection_result = await self._run_reflection_agent(query)
            reflection_results.append(reflection_result)
            print(f"  Reflection Agent: {reflection_result.execution_time:.2f}s, "
                  f"tools={len(reflection_result.tools_called)}, "
                  f"success={reflection_result.success}")
        
        # Calculate metrics
        metrics = ComparisonMetrics(
            agent_a="single_agent",
            agent_b="reflection_agent",
            test_count=len(queries)
        )
        
        # Calculate single agent metrics
        metrics.agent_a_metrics = self._calculate_metrics(single_results, expected_tools)
        
        # Calculate reflection agent metrics
        metrics.agent_b_metrics = self._calculate_metrics(reflection_results, expected_tools)
        
        # Calculate differences (reflection - single)
        for key in metrics.agent_a_metrics:
            metrics.differences[key] = (
                metrics.agent_b_metrics.get(key, 0) - 
                metrics.agent_a_metrics.get(key, 0)
            )
        
        return metrics
    
    def _calculate_metrics(
        self,
        results: list[AgentResult],
        expected_tools: list[list[str]] | None = None
    ) -> dict[str, float]:
        """Calculate aggregate metrics from results."""
        if not results:
            return {}
        
        metrics = {}
        
        # Success rate
        success_count = sum(1 for r in results if r.success)
        metrics["success_rate"] = success_count / len(results)
        
        # Average execution time
        metrics["avg_execution_time"] = sum(r.execution_time for r in results) / len(results)
        
        # Average response length
        metrics["avg_response_length"] = sum(len(r.response) for r in results) / len(results)
        
        # Average tools called
        metrics["avg_tools_called"] = sum(len(r.tools_called) for r in results) / len(results)
        
        # Tool accuracy (if expected tools provided)
        if expected_tools and len(expected_tools) == len(results):
            tool_accuracies = []
            for result, expected in zip(results, expected_tools):
                if not expected:
                    continue
                called_set = set(result.tools_called)
                expected_set = set(expected)
                if expected_set:
                    accuracy = len(called_set & expected_set) / len(expected_set)
                    tool_accuracies.append(accuracy)
            
            if tool_accuracies:
                metrics["tool_accuracy"] = sum(tool_accuracies) / len(tool_accuracies)
        
        return metrics


# ═══════════════════════════════════════════════════════════════════════════════
# TEST DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════


def load_test_data(count: int | None = None) -> tuple[list[str], list[list[str]], list[str]]:
    """Load test data from test_data.jsonl.
    
    Returns:
        Tuple of (queries, expected_tools, ground_truths)
    """
    test_data_file = _eval_dir / "test_data.jsonl"
    queries = []
    expected_tools = []
    ground_truths = []
    
    with open(test_data_file, "r") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            queries.append(data["query"])
            expected_tools.append(data.get("expected_tools", []))
            ground_truths.append(data.get("ground_truth", ""))
            
            if count and len(queries) >= count:
                break
    
    return queries, expected_tools, ground_truths


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def comparison_runner():
    """Create an agent comparison runner."""
    return AgentComparisonRunner()


class TestAgentComparison:
    """Tests that compare single_agent vs reflection_agent."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_quick_comparison(self, comparison_runner):
        """Quick comparison using 3 test cases."""
        quick_count = int(os.getenv("EVAL_QUICK_TEST_COUNT", "3"))
        queries, expected_tools, _ = load_test_data(count=quick_count)
        
        metrics = await comparison_runner.run_comparison(queries, expected_tools)
        
        print("\n" + metrics.to_report())
        
        # Both agents should have some level of success
        assert metrics.agent_a_metrics.get("success_rate", 0) >= 0.5, \
            "Single agent success rate too low"
        assert metrics.agent_b_metrics.get("success_rate", 0) >= 0.5, \
            "Reflection agent success rate too low"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_comparison(self, comparison_runner):
        """Full comparison using all test cases."""
        queries, expected_tools, _ = load_test_data()
        
        metrics = await comparison_runner.run_comparison(queries, expected_tools)
        
        print("\n" + metrics.to_report())
        
        # Store results for analysis
        results_file = _eval_dir / "comparison_results.json"
        with open(results_file, "w") as f:
            json.dump({
                "agent_a": metrics.agent_a,
                "agent_b": metrics.agent_b,
                "test_count": metrics.test_count,
                "agent_a_metrics": metrics.agent_a_metrics,
                "agent_b_metrics": metrics.agent_b_metrics,
                "differences": metrics.differences
            }, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")
        
        # Basic assertions
        assert metrics.test_count > 0, "No tests were run"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_execution_time_comparison(self, comparison_runner):
        """Compare execution times between agents."""
        queries, expected_tools, _ = load_test_data(count=3)
        
        metrics = await comparison_runner.run_comparison(queries, expected_tools)
        
        single_time = metrics.agent_a_metrics.get("avg_execution_time", 0)
        reflection_time = metrics.agent_b_metrics.get("avg_execution_time", 0)
        
        print(f"\nExecution Time Comparison:")
        print(f"  Single Agent:     {single_time:.2f}s")
        print(f"  Reflection Agent: {reflection_time:.2f}s")
        print(f"  Difference:       {reflection_time - single_time:.2f}s")
        
        # Reflection agent is expected to take longer (more LLM calls)
        # Just verify times are reasonable
        assert single_time > 0, "Single agent should have non-zero execution time"
        assert reflection_time > 0, "Reflection agent should have non-zero execution time"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_response_quality_comparison(self, comparison_runner):
        """Compare response quality metrics between agents."""
        queries, expected_tools, _ = load_test_data(count=3)
        
        metrics = await comparison_runner.run_comparison(queries, expected_tools)
        
        print("\nResponse Quality Comparison:")
        print(f"  Single Agent Response Length:     {metrics.agent_a_metrics.get('avg_response_length', 0):.0f}")
        print(f"  Reflection Agent Response Length: {metrics.agent_b_metrics.get('avg_response_length', 0):.0f}")
        
        # Both should produce responses
        assert metrics.agent_a_metrics.get("avg_response_length", 0) > 0
        assert metrics.agent_b_metrics.get("avg_response_length", 0) > 0


class TestSingleAgentOnly:
    """Tests for single agent in isolation."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_single_agent_basic(self, comparison_runner):
        """Test single agent with a basic query."""
        result = await comparison_runner._run_single_agent(
            "Hello, I need help with my account"
        )
        
        assert result.success, f"Single agent failed: {result.error}"
        assert len(result.response) > 0, "Response should not be empty"
        print(f"\nSingle Agent Response: {result.response[:200]}...")


class TestReflectionAgentOnly:
    """Tests for reflection agent in isolation."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_reflection_agent_basic(self, comparison_runner):
        """Test reflection agent with a basic query."""
        result = await comparison_runner._run_reflection_agent(
            "Hello, I need help with my account"
        )
        
        assert result.success, f"Reflection agent failed: {result.error}"
        assert len(result.response) > 0, "Response should not be empty"
        print(f"\nReflection Agent Response: {result.response[:200]}...")


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """Run comparison directly without pytest."""
    async def main():
        runner = AgentComparisonRunner()
        queries, expected_tools, _ = load_test_data(count=3)
        
        print("Running Agent Comparison...")
        print(f"Comparing: single_agent vs reflection_agent")
        print(f"Test cases: {len(queries)}")
        
        metrics = await runner.run_comparison(queries, expected_tools)
        print(metrics.to_report())
    
    asyncio.run(main())
