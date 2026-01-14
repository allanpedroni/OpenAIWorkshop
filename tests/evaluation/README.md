# Agent Evaluation Framework

This directory contains a comprehensive evaluation framework for AI agents using the **Azure AI Foundry Evaluation SDK** with **LLM-as-Judge** capabilities.

## 📋 Overview

The evaluation framework tests agent performance across multiple dimensions:

### Evaluation Types

| Type | Description |
|------|-------------|
| **Process-Based** | Evaluates HOW the agent works (tool calls, reasoning steps) |
| **Goal-Based** | Evaluates WHAT the agent achieves (outcome quality) |

### LLM-as-Judge Evaluators (Azure AI Foundry)

| Evaluator | Type | Description |
|-----------|------|-------------|
| `IntentResolutionEvaluator` | Goal | Did the agent correctly identify user intent? |
| `TaskAdherenceEvaluator` | Goal | Did the response follow the assigned task? |
| `ToolCallAccuracyEvaluator` | Process | Were the correct tools called? |
| `CoherenceEvaluator` | Quality | Is the response logically coherent? |
| `FluencyEvaluator` | Quality | Is the language natural? |
| `RelevanceEvaluator` | Quality | Is the response relevant? |

### Fallback Metrics (No LLM Required)

| Metric | Description |
|--------|-------------|
| **Tool Recall/Precision/F1** | Rule-based tool call accuracy |
| **Keyword Coverage** | Simple keyword matching for outcomes |

## 🆕 Standalone Setup (Recommended)

The evaluation module runs **independently** from the applications folder.

### Prerequisites

1. **MCP Server** running at `http://localhost:8000/mcp`
2. **Azure OpenAI** credentials (gpt-4.1 or gpt-4o recommended for LLM judges)
3. **uv** package manager

### Quick Start

```bash
# Navigate to evaluation folder
cd tests/evaluation

# Install dependencies (first time only)
$env:UV_LINK_MODE="copy"  # Windows only, for OneDrive compatibility
uv sync

# Run quick comparison (3 test cases, ~1 min)
uv run pytest test_agent_comparison.py::TestAgentComparison::test_quick_comparison -v -s

# Run full comparison with LLM judges
uv run pytest test_scenario_evaluation.py::TestAgentComparison -v -s

# Test LLM judge directly
uv run python llm_judge_evaluator.py
```

### Configuration

Edit `.env` file in `tests/evaluation/` to configure:

```bash
# Azure OpenAI for agents
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5.2-chat

# LLM Judge (use gpt-4.1 for compatibility with azure-ai-evaluation SDK)
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
LLM_JUDGE_DEPLOYMENT=gpt-4.1
USE_REASONING_MODEL=false  # Set true for o-series models

# MCP Server
MCP_SERVER_URI=http://localhost:8000/mcp

# Evaluation settings
EVAL_USE_LLM_JUDGE=true
EVAL_QUICK_TEST_COUNT=3
```

---

## 🧠 LLM-as-Judge Feature

Instead of simple keyword matching, the framework uses Azure AI Foundry's LLM-based evaluators:

```python
from llm_judge_evaluator import LLMJudgeEvaluator, ToolCall, ToolDefinition

evaluator = LLMJudgeEvaluator()

result = await evaluator.evaluate(
    query="What is my invoice total?",
    response="Your invoice total is $542.50...",
    tool_calls=[ToolCall(name="get_customer_invoices", arguments={"customer_id": 123})],
    tool_definitions=[ToolDefinition(name="get_customer_invoices", description="Get invoices")]
)

print(f"Intent Resolution: {result.intent_resolution_score}/5 - {result.intent_resolution_result}")
print(f"Task Adherence: {result.task_adherence_score}/5 - {result.task_adherence_result}")
print(f"Tool Accuracy: {result.tool_call_accuracy_score}/5 - {result.tool_call_accuracy_result}")
```

### Multi-Turn Support

Azure AI Foundry evaluators support full conversation history:

```python
from llm_judge_evaluator import ConversationMessage

conversation = [
    ConversationMessage(role="user", content="What's my account status?"),
    ConversationMessage(role="assistant", content="Let me check...", tool_calls=[...]),
    ConversationMessage(role="tool", content='{"status": "active"}', tool_call_id="call_1"),
    ConversationMessage(role="assistant", content="Your account is active."),
]

result = await evaluator.evaluate(
    query="What's my account status?",
    response="Your account is active.",
    conversation=conversation,
    system_prompt="You are a helpful customer service agent."
)
```

---

## 🔄 Agent Comparison

The framework compares **single_agent** vs **reflection_agent**:

| Agent | Description | Expected Performance |
|-------|-------------|---------------------|
| **single_agent** | Direct LLM response | Faster, baseline quality |
| **reflection_agent** | Primary + Reviewer pattern | Slower, higher quality |

### Sample Output

```
══════════════════════════════════════════════════════════════════════
AGENT COMPARISON REPORT: single_agent vs reflection_agent
══════════════════════════════════════════════════════════════════════
Test Cases: 3

Metric                            single_agent reflection_agent       Diff
----------------------------------------------------------------------
avg_execution_time                       6.043          12.338     +6.295
avg_response_length                    936.667        1127.667   +191.000
success_rate                             1.000           1.000      0.000
----------------------------------------------------------------------
```

---

## 🚀 Legacy Quick Start (from applications folder)

### Run Unit Tests (No external dependencies)

```bash
# From the applications folder (recommended for uv)
cd agentic_ai/applications
uv run python -m pytest ../../tests/test_agent_evaluation.py -v -m "unit"
```

### Run Integration Tests (Requires MCP server + Azure OpenAI)

1. **Start MCP server:**
```bash
cd mcp && uv run python mcp_service.py
```

2. **Start Backend:**
```bash
cd agentic_ai/applications && uv run python backend.py
```

3. **Run evaluation tests:**
```bash
cd agentic_ai/applications
uv run python -m pytest ../../tests/test_agent_evaluation.py -v -m "evaluation and integration"
```

### Run Full Evaluation Pipeline

```bash
cd agentic_ai/applications

# Run with AI-assisted evaluation
uv run python -m tests.evaluation.agent_evaluator \
    --test-data ../../tests/evaluation/test_data.jsonl \
    --agent-module agents.agent_framework.single_agent \
    --output ../../tests/evaluation/results.json

# Run without AI evaluation (faster, no extra API costs)
uv run python -m tests.evaluation.agent_evaluator \
    --test-data ../../tests/evaluation/test_data.jsonl \
    --no-ai-eval
```

## 📁 Files

| File | Description |
|------|-------------|
| `llm_judge_evaluator.py` | **NEW** LLM-as-Judge evaluator using Azure AI Foundry SDK |
| `agent_runner.py` | Generic agent test runner that works with any agent |
| `test_scenario_evaluation.py` | Scenario-based evaluation with dual metrics |
| `test_agent_comparison.py` | Agent comparison tests (single vs reflection) |
| `agent_evaluator.py` | Core evaluation module with AgentRunner and AgentEvaluator |
| `test_data.jsonl` | Test dataset with Contoso Communications scenarios |
| `pyproject.toml` | Standalone dependencies |
| `.env` | Environment configuration |

## 📊 Test Data Format

Test cases are stored in JSONL format:

```json
{
    "query": "What's my billing summary?",
    "customer_id": "251",
    "expected_intent": "billing_inquiry",
    "expected_tools": ["get_billing_summary", "get_customer_detail"],
    "ground_truth": "The agent should retrieve and present the customer's billing summary.",
    "category": "billing",
    "complexity": "low"
}
```

### Categories Covered

- **billing** - Invoice, payment, and balance queries
- **technical_support** - Service issues, data usage, connectivity
- **products** - Plan upgrades, international roaming
- **security** - Account lockout, authentication issues
- **promotions** - Discounts, loyalty rewards
- **support** - Support tickets, order returns

## 🎯 Evaluation Thresholds

Default thresholds (configurable in `EvaluationThresholds`):

| Metric | Threshold | Description |
|--------|-----------|-------------|
| Tool Call Accuracy | 0.5 | F1 score for tool calls (lower to account for agent using tool subsets) |
| Groundedness | 0.7 | Normalized score (1-5 scale) |
| Relevance | 0.8 | Normalized score (1-5 scale) |
| Coherence | 0.8 | Normalized score (1-5 scale) |
| Fluency | 0.8 | Normalized score (1-5 scale) |

## 🔧 CI/CD Integration

The evaluation runs automatically in CI/CD:

1. **On PR** (changes to `agentic_ai/agents/**`): Unit tests only
2. **On workflow_call**: Full integration tests against deployed services
3. **Manual trigger**: Optional full evaluation with AI metrics

### GitHub Actions Workflow

```yaml
# Trigger evaluation manually
gh workflow run agent-evaluation.yml \
    -f environment=dev \
    -f run_full_evaluation=true \
    -f include_ai_evaluation=true
```

## 📈 Sample Output

```
============================================================
EVALUATION SUMMARY
============================================================
Total Tests:      10
Passed:           8
Failed:           2
Pass Rate:        80.0%
Avg Tool F1:      0.85
Avg Exec Time:    1523ms

By Category:
  billing: 3/3 (100%)
  technical_support: 2/2 (100%)
  products: 1/2 (50%)
  security: 1/1 (100%)
  promotions: 1/2 (50%)
============================================================
```

## 🔗 Related Documentation

- [Azure AI Evaluation SDK](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/agent-evaluate-sdk)
- [Contoso Communications Scenario](../../SCENARIO.md)
- [Microsoft Agent Framework](../agentic_ai/agents/agent_framework/README.md)
