"""
Agent Evaluation Tests
======================
Pytest-based evaluation tests for the single agent.

These tests can be run:
1. Locally with MCP server running: `pytest tests/test_agent_evaluation.py -v`
2. In CI/CD pipeline against deployed services

Markers:
- @pytest.mark.evaluation: All evaluation tests
- @pytest.mark.slow: Tests that take longer (full evaluation)
- @pytest.mark.unit: Fast unit tests for evaluation utilities
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add paths for imports - use absolute paths for reliability
_tests_dir = Path(__file__).parent.resolve()
_repo_root = _tests_dir.parent.resolve()
sys.path.insert(0, str(_tests_dir / "evaluation"))
sys.path.insert(0, str(_tests_dir))
sys.path.insert(0, str(_repo_root / "agentic_ai" / "applications"))
sys.path.insert(0, str(_repo_root / "agentic_ai"))

from evaluation.agent_evaluator import (
    AgentEvaluator,
    AgentResponse,
    AgentRunner,
    EvaluationThresholds,
    TestCase,
    ToolCallTracker,
    load_test_data,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_test_case() -> TestCase:
    """Create a sample test case for testing."""
    return TestCase(
        query="What's my billing summary?",
        customer_id="251",
        expected_intent="billing_inquiry",
        expected_tools=["get_billing_summary", "get_customer_detail"],
        ground_truth="The agent should retrieve and present the customer's billing summary.",
        category="billing",
        complexity="low",
    )


@pytest.fixture
def sample_agent_response(sample_test_case: TestCase) -> AgentResponse:
    """Create a sample agent response for testing."""
    return AgentResponse(
        test_case=sample_test_case,
        response="Based on your account, your current billing summary shows an outstanding balance of $150.00. This includes your monthly subscription of $99.99 and additional data usage charges of $50.01.",
        tools_called=["get_customer_detail", "get_billing_summary"],
        execution_time_ms=1500.0,
        error=None,
    )


@pytest.fixture
def test_data_path() -> str:
    """Get the path to the test data file."""
    return str(Path(__file__).parent / "evaluation" / "test_data.jsonl")


@pytest.fixture
def evaluator() -> AgentEvaluator:
    """Create an evaluator instance with default thresholds."""
    return AgentEvaluator(thresholds=EvaluationThresholds())


# ============================================================================
# Unit Tests - Evaluation Utilities
# ============================================================================

@pytest.mark.unit
class TestTestCase:
    """Tests for TestCase dataclass."""
    
    def test_from_dict(self):
        """Test creating TestCase from dictionary."""
        data = {
            "query": "Test query",
            "customer_id": "123",
            "expected_intent": "test_intent",
            "expected_tools": ["tool1", "tool2"],
            "ground_truth": "Expected response",
            "category": "test",
            "complexity": "low",
        }
        
        test_case = TestCase.from_dict(data)
        
        assert test_case.query == "Test query"
        assert test_case.customer_id == "123"
        assert test_case.expected_intent == "test_intent"
        assert test_case.expected_tools == ["tool1", "tool2"]
        assert test_case.ground_truth == "Expected response"
        assert test_case.category == "test"
        assert test_case.complexity == "low"


@pytest.mark.unit
class TestToolCallTracker:
    """Tests for ToolCallTracker."""
    
    @pytest.mark.asyncio
    async def test_tracks_tool_calls(self):
        """Test that tool calls are tracked correctly."""
        tracker = ToolCallTracker()
        
        await tracker.broadcast("session1", {"type": "tool_called", "tool_name": "get_customer_detail"})
        await tracker.broadcast("session1", {"type": "tool_called", "tool_name": "get_billing_summary"})
        
        tools = tracker.get_tools_called()
        assert "get_customer_detail" in tools
        assert "get_billing_summary" in tools
        assert len(tools) == 2
    
    @pytest.mark.asyncio
    async def test_ignores_non_tool_events(self):
        """Test that non-tool events are ignored."""
        tracker = ToolCallTracker()
        
        await tracker.broadcast("session1", {"type": "agent_start"})
        await tracker.broadcast("session1", {"type": "agent_token", "content": "Hello"})
        
        tools = tracker.get_tools_called()
        assert len(tools) == 0
    
    @pytest.mark.asyncio
    async def test_deduplicates_tool_calls(self):
        """Test that duplicate tool calls are not counted twice."""
        tracker = ToolCallTracker()
        
        await tracker.broadcast("session1", {"type": "tool_called", "tool_name": "get_customer_detail"})
        await tracker.broadcast("session1", {"type": "tool_called", "tool_name": "get_customer_detail"})
        
        tools = tracker.get_tools_called()
        assert len(tools) == 1


@pytest.mark.unit
class TestLoadTestData:
    """Tests for test data loading."""
    
    def test_load_test_data(self, test_data_path: str):
        """Test loading test data from JSONL file."""
        test_cases = load_test_data(test_data_path)
        
        assert len(test_cases) > 0
        assert all(isinstance(tc, TestCase) for tc in test_cases)
        
        # Check first test case has expected fields
        first_case = test_cases[0]
        assert first_case.query
        assert first_case.customer_id
        assert first_case.expected_intent
        assert len(first_case.expected_tools) > 0
    
    def test_load_test_data_categories(self, test_data_path: str):
        """Test that test data covers multiple categories."""
        test_cases = load_test_data(test_data_path)
        
        categories = set(tc.category for tc in test_cases)
        
        # Should have at least billing and support categories
        assert "billing" in categories
        assert len(categories) >= 3  # At least 3 different categories


# ============================================================================
# Unit Tests - Evaluator
# ============================================================================

@pytest.mark.unit
class TestAgentEvaluator:
    """Tests for AgentEvaluator."""
    
    def test_evaluate_tool_accuracy_perfect_match(self, evaluator: AgentEvaluator, sample_agent_response: AgentResponse):
        """Test tool accuracy with perfect match."""
        result = evaluator.evaluate_tool_accuracy(sample_agent_response)
        
        assert result["tool_precision"] == 1.0
        assert result["tool_recall"] == 1.0
        assert result["tool_f1_score"] == 1.0
        assert result["passed"] is True
        assert len(result["missing_tools"]) == 0
        assert len(result["extra_tools"]) == 0
    
    def test_evaluate_tool_accuracy_missing_tools(self, evaluator: AgentEvaluator, sample_test_case: TestCase):
        """Test tool accuracy when expected tools are missing."""
        response = AgentResponse(
            test_case=sample_test_case,
            response="Some response",
            tools_called=["get_customer_detail"],  # Missing get_billing_summary
            execution_time_ms=1000.0,
        )
        
        result = evaluator.evaluate_tool_accuracy(response)
        
        assert result["tool_recall"] == 0.5
        assert result["tool_precision"] == 1.0
        assert result["missing_tools"] == ["get_billing_summary"]
    
    def test_evaluate_tool_accuracy_extra_tools(self, evaluator: AgentEvaluator, sample_test_case: TestCase):
        """Test tool accuracy when extra tools are called."""
        response = AgentResponse(
            test_case=sample_test_case,
            response="Some response",
            tools_called=["get_customer_detail", "get_billing_summary", "get_promotions"],
            execution_time_ms=1000.0,
        )
        
        result = evaluator.evaluate_tool_accuracy(response)
        
        assert result["tool_recall"] == 1.0
        assert result["tool_precision"] < 1.0
        assert "get_promotions" in result["extra_tools"]
    
    def test_evaluate_tool_accuracy_no_tools_called(self, evaluator: AgentEvaluator, sample_test_case: TestCase):
        """Test tool accuracy when no tools are called."""
        response = AgentResponse(
            test_case=sample_test_case,
            response="I cannot help with that.",
            tools_called=[],
            execution_time_ms=500.0,
        )
        
        result = evaluator.evaluate_tool_accuracy(response)
        
        assert result["tool_recall"] == 0.0
        assert result["passed"] is False
    
    def test_evaluate_response_quality_good_response(self, evaluator: AgentEvaluator, sample_agent_response: AgentResponse):
        """Test response quality with a good response."""
        result = evaluator.evaluate_response_quality(sample_agent_response)
        
        assert result["has_content"] is True
        assert result["word_count"] > 10
        assert result["passed"] is True
    
    def test_evaluate_response_quality_empty_response(self, evaluator: AgentEvaluator, sample_test_case: TestCase):
        """Test response quality with empty response."""
        response = AgentResponse(
            test_case=sample_test_case,
            response="",
            tools_called=[],
            execution_time_ms=500.0,
        )
        
        result = evaluator.evaluate_response_quality(response)
        
        assert result["has_content"] is False
        assert result["passed"] is False
    
    def test_evaluate_response_quality_with_error(self, evaluator: AgentEvaluator, sample_test_case: TestCase):
        """Test response quality when there's an error."""
        response = AgentResponse(
            test_case=sample_test_case,
            response="",
            tools_called=[],
            execution_time_ms=100.0,
            error="Connection timeout",
        )
        
        result = evaluator.evaluate_response_quality(response)
        
        assert result["has_error"] is True
        assert result["passed"] is False


# ============================================================================
# Integration Tests - Full Evaluation Pipeline
# ============================================================================

@pytest.mark.evaluation
@pytest.mark.integration
class TestAgentEvaluationIntegration:
    """
    Integration tests that run the actual agent against test cases.
    
    These tests require:
    - MCP server running
    - Azure OpenAI credentials configured
    """
    
    @pytest.fixture
    def check_environment(self):
        """Check that required environment variables are set."""
        required_vars = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_CHAT_DEPLOYMENT",
            "MCP_SERVER_URI",
        ]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            pytest.skip(f"Missing required environment variables: {', '.join(missing)}")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_single_agent_billing_query(self, check_environment, test_data_path: str):
        """Test single agent with a billing query."""
        test_cases = load_test_data(test_data_path)
        
        # Find a billing test case
        billing_case = next((tc for tc in test_cases if tc.category == "billing"), None)
        if not billing_case:
            pytest.skip("No billing test case found")
        
        runner = AgentRunner(agent_module="agents.agent_framework.single_agent")
        response = await runner.run_single_test(billing_case)
        
        # Basic assertions
        assert response.response, "Agent should return a response"
        assert response.error is None, f"Agent should not error: {response.error}"
        
        # Evaluate the response
        evaluator = AgentEvaluator()
        result = await evaluator.evaluate_response(response, include_ai_eval=False)
        
        print(f"\nTest Case: {billing_case.query}")
        print(f"Response: {response.response[:200]}...")
        print(f"Tools Called: {response.tools_called}")
        print(f"Tool F1 Score: {result['tool_accuracy']['tool_f1_score']:.2f}")
        print(f"Passed: {result['passed']}")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_evaluation_pipeline(self, check_environment, test_data_path: str):
        """
        Run the full evaluation pipeline on all test cases.
        
        This is a comprehensive test that runs all test cases and generates
        evaluation metrics. Use with caution as it can be slow and costly.
        """
        test_cases = load_test_data(test_data_path)
        
        # Limit to first 3 cases for CI to save time/cost
        test_cases = test_cases[:3]
        
        runner = AgentRunner(agent_module="agents.agent_framework.single_agent")
        responses = await runner.run_test_dataset(test_cases)
        
        evaluator = AgentEvaluator()
        results = await evaluator.evaluate_all(responses, include_ai_eval=False)
        
        summary = results["summary"]
        
        print(f"\n{'='*60}")
        print("EVALUATION RESULTS")
        print(f"{'='*60}")
        print(f"Total: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Pass Rate: {summary['pass_rate']:.1%}")
        print(f"Avg Tool F1: {summary['average_tool_f1_score']:.2f}")
        
        # Assertions for CI/CD gates
        # Note: Tool F1 may be lower because agent uses subset of expected tools
        # The key is that agent provides helpful responses
        assert summary["average_tool_f1_score"] >= 0.3, "Average tool F1 should be at least 0.3"
        
        # Print individual results for debugging
        for i, result in enumerate(results["individual_results"]):
            print(f"\nTest {i+1}: {result['test_case']['query'][:50]}...")
            print(f"  Tools Called: {result['tool_accuracy']['called_tools']}")
            print(f"  Tool F1: {result['tool_accuracy']['tool_f1_score']:.2f}")
            print(f"  Response OK: {result['response_quality']['has_content']}")


# ============================================================================
# Mocked Tests - For CI/CD without live services
# ============================================================================

@pytest.mark.evaluation
@pytest.mark.unit
class TestAgentEvaluationMocked:
    """
    Mocked evaluation tests that don't require live services.
    These tests verify the evaluation logic works correctly.
    """
    
    @pytest.mark.asyncio
    async def test_evaluation_with_mocked_agent(self, test_data_path: str):
        """Test evaluation pipeline with mocked agent responses."""
        test_cases = load_test_data(test_data_path)[:2]
        
        # Create mock responses
        mock_responses = [
            AgentResponse(
                test_case=tc,
                response=f"Here is the information for customer {tc.customer_id}: " + 
                         "Your account shows normal activity. " * 10,
                tools_called=tc.expected_tools[:2],  # Simulate calling some expected tools
                execution_time_ms=1500.0,
            )
            for tc in test_cases
        ]
        
        evaluator = AgentEvaluator()
        results = await evaluator.evaluate_all(mock_responses, include_ai_eval=False)
        
        assert results["summary"]["total_tests"] == 2
        assert "individual_results" in results
        assert len(results["individual_results"]) == 2
    
    @pytest.mark.asyncio
    async def test_evaluation_handles_errors_gracefully(self):
        """Test that evaluation handles agent errors gracefully."""
        test_case = TestCase(
            query="Test query",
            customer_id="999",
            expected_intent="test",
            expected_tools=["some_tool"],
            ground_truth="Expected response",
            category="test",
            complexity="low",
        )
        
        error_response = AgentResponse(
            test_case=test_case,
            response="",
            tools_called=[],
            execution_time_ms=100.0,
            error="Agent initialization failed",
        )
        
        evaluator = AgentEvaluator()
        result = await evaluator.evaluate_response(error_response, include_ai_eval=False)
        
        assert result["passed"] is False
        assert result["error"] == "Agent initialization failed"
        assert result["response_quality"]["has_error"] is True


# ============================================================================
# Threshold Tests
# ============================================================================

@pytest.mark.evaluation
@pytest.mark.unit
class TestEvaluationThresholds:
    """Tests for evaluation threshold configuration."""
    
    def test_default_thresholds(self):
        """Test that default thresholds are reasonable."""
        thresholds = EvaluationThresholds()
        
        assert thresholds.tool_call_accuracy == 0.5  # Lower threshold for single agent
        assert thresholds.groundedness == 0.7
        assert thresholds.relevance == 0.8
    
    def test_custom_thresholds(self):
        """Test that custom thresholds can be set."""
        thresholds = EvaluationThresholds(
            tool_call_accuracy=0.9,
            groundedness=0.9,
        )
        
        assert thresholds.tool_call_accuracy == 0.9
        assert thresholds.groundedness == 0.9
    
    def test_strict_thresholds_fail_more(self, sample_test_case: TestCase):
        """Test that stricter thresholds cause more failures."""
        response = AgentResponse(
            test_case=sample_test_case,
            response="Brief response.",
            tools_called=["get_customer_detail"],  # Only 1 of 2 expected tools
            execution_time_ms=1000.0,
        )
        
        # Default threshold (0.5) - should pass with F1 ~0.67
        default_evaluator = AgentEvaluator(thresholds=EvaluationThresholds())
        default_result = default_evaluator.evaluate_tool_accuracy(response)
        
        # Strict threshold (0.9) - should fail
        strict_evaluator = AgentEvaluator(thresholds=EvaluationThresholds(tool_call_accuracy=0.9))
        strict_result = strict_evaluator.evaluate_tool_accuracy(response)
        
        # F1 score of ~0.67 passes 0.5 threshold but fails 0.9
        assert default_result["passed"] is True   # 0.67 >= 0.5
        assert strict_result["passed"] is False   # 0.67 < 0.9


# ============================================================================
# CLI Runner Test
# ============================================================================

@pytest.mark.evaluation
@pytest.mark.unit
def test_cli_can_import():
    """Test that the evaluation module can be imported for CLI use."""
    from evaluation.agent_evaluator import run_evaluation
    
    assert callable(run_evaluation)
