# AI Agent Evaluation Framework

A comprehensive evaluation system for testing AI agents in customer support scenarios. This framework provides both **local evaluation** with custom metrics and **remote evaluation** via Azure AI Foundry with LLM-as-judge capabilities.

---

## Table of Contents

1. [Evaluation Methodology](#evaluation-methodology)
   - [Why Evaluate AI Agents?](#why-evaluate-ai-agents)
   - [Single-Turn vs Multi-Turn Evaluation](#single-turn-vs-multi-turn-evaluation)
   - [Built-in vs Custom Evaluators](#built-in-vs-custom-evaluators)
2. [Metrics Deep Dive](#metrics-deep-dive)
   - [Single-Turn Metrics (Tool-Focused)](#single-turn-metrics-tool-focused)
   - [Multi-Turn Metrics (Outcome-Focused)](#multi-turn-metrics-outcome-focused)
3. [Setup Guide](#setup-guide)
   - [Prerequisites](#prerequisites)
   - [Step 1: Environment Setup](#step-1-environment-setup)
   - [Step 2: Azure Configuration](#step-2-azure-configuration)
   - [Step 3: Start Services](#step-3-start-services)
4. [Running Evaluations](#running-evaluations)
   - [Local Evaluation](#local-evaluation)
   - [Remote Evaluation (Azure AI Foundry)](#remote-evaluation-azure-ai-foundry)
   - [Comparing Agents](#comparing-agents)
5. [CI/CD Integration](#cicd-integration)
   - [Architecture Decision](#architecture-decision)
   - [What Runs in CI](#what-runs-in-ci)
   - [Where Results Appear](#where-results-appear)
6. [Interpreting Results](#interpreting-results)
7. [Extending the Framework](#extending-the-framework)
8. [Troubleshooting](#troubleshooting)

---

## Evaluation Methodology

### Why Evaluate AI Agents?

AI agents that use tools (APIs, databases, external services) require evaluation that goes beyond traditional NLP metrics. Unlike simple chatbots, agents must:

1. **Choose the right tools** - Select appropriate APIs for each task
2. **Use tools correctly** - Pass correct parameters and handle responses
3. **Maintain context** - Remember information across conversation turns
4. **Achieve outcomes** - Actually solve the customer's problem
5. **Communicate effectively** - Provide clear, helpful responses

This framework addresses all these dimensions through a combination of **rule-based metrics** (deterministic, fast) and **LLM-as-judge evaluators** (semantic understanding, nuanced assessment).

### Single-Turn vs Multi-Turn Evaluation

We use fundamentally different evaluation strategies for single-turn and multi-turn conversations because they measure different capabilities:

#### Single-Turn Evaluation (Tool-Focused)

**Rationale**: In a single exchange, the agent must immediately demonstrate correct tool selection and usage. There's no opportunity for course correction, so we heavily weight tool-level accuracy.

```
┌─────────────────────────────────────────────────────────────┐
│ SINGLE-TURN WEIGHTS                                         │
├─────────────────────────────────────────────────────────────┤
│ Tool Behavior (recall, precision, efficiency)     │  10%   │
│ Tool Call Accuracy (LLM-judge)                    │  15%   │
│ Task Adherence (LLM-judge)                        │  10%   │
│ Completeness (success criteria met)               │  10%   │
│ Response Quality - LLM                            │  10%   │
│ Response Quality - Basic                          │   5%   │
│ Grounded Accuracy                                 │  10%   │
│ Intent Resolution                                 │  10%   │
│ Coherence                                         │   5%   │
│ Fluency                                           │   5%   │
│ Relevance                                         │   5%   │
│ Solution Accuracy                                 │  10%   │  ← Ground truth match
└─────────────────────────────────────────────────────────────┘
```

**Use cases**: Quick lookups, simple queries, one-shot requests

#### Multi-Turn Evaluation (Outcome-Focused)

**Rationale**: In multi-turn conversations, what matters is the **final outcome**, not the path taken. An agent might take different tool sequences across turns but still successfully resolve the customer's issue. Penalizing intermediate tool choices would be counterproductive.

```
┌─────────────────────────────────────────────────────────────┐
│ MULTI-TURN WEIGHTS                                          │
├─────────────────────────────────────────────────────────────┤
│ Solution Accuracy                                 │  30%   │  ← Did we solve it?
│ Task Adherence                                    │  20%   │  ← Proper procedure?
│ Intent Resolution                                 │  20%   │  ← All intents handled?
│ Coherence                                         │  10%   │  ← Logical conversation?
│ Fluency                                           │  10%   │  ← Quality communication?
│ Relevance                                         │  10%   │  ← Stayed on topic?
├─────────────────────────────────────────────────────────────┤
│ ❌ Tool metrics EXCLUDED - we care about outcomes           │
└─────────────────────────────────────────────────────────────┘
```

**Use cases**: Complex problem resolution, account changes requiring multiple steps, escalation flows

### Built-in vs Custom Evaluators

We combine two types of evaluators to get the best of both worlds:

#### Azure AI Foundry Built-in Evaluators

**Why use them:**
- ✅ Industry-standard LLM-as-judge implementations
- ✅ Consistent with Azure AI Foundry portal metrics
- ✅ Maintained and improved by Microsoft
- ✅ 1-5 scale matching portal visualization

| Evaluator | What it Measures |
|-----------|------------------|
| `IntentResolutionEvaluator` | Did the agent understand the customer's intent? |
| `TaskAdherenceEvaluator` | Did the agent follow proper procedures? |
| `ToolCallAccuracyEvaluator` | Were tool calls correct and appropriate? |
| `CoherenceEvaluator` | Was the response logically structured? |
| `FluencyEvaluator` | Was the language natural and grammatically correct? |
| `RelevanceEvaluator` | Was the response relevant to the question? |

#### Custom Evaluators

**Why we need them:**
- 🔧 Domain-specific logic (e.g., billing-specific success criteria)
- 🎯 Ground truth matching against expected solutions
- ⚡ Deterministic rules (fast, no API calls needed)
- 📊 Tool behavior metrics unique to our agent patterns

| Evaluator | What it Measures | Why Custom? |
|-----------|------------------|-------------|
| `ToolBehaviorEvaluator` | Recall, precision, efficiency of tool usage | Requires domain knowledge of expected tools |
| `CompletenessEvaluator` | Success criteria satisfaction | Maps criteria to specific tool requirements |
| `GroundedAccuracyEvaluator` | Response grounded in tool outputs | Needs access to tool call results |
| `SolutionAccuracyEvaluator` | Match against ground truth | Uses scenario-specific rubrics |

#### Score Scale: 1-5

All metrics use a **1-5 scale** with a **threshold of 3** for pass/fail:

```
Score   Meaning              Pass?
─────   ─────────────────    ─────
  5     Excellent            ✓
  4     Good                 ✓
  3     Acceptable           ✓ (threshold)
  2     Below expectations   ✗
  1     Poor                 ✗
```

This matches the Azure AI Foundry portal visualization, making local and remote evaluation results directly comparable.

---

## Metrics Deep Dive

### Single-Turn Metrics (Tool-Focused)

#### 1. Tool Behavior (10%)
Combines three sub-metrics:
- **Recall** (50%): Fraction of required tools actually used
- **Precision** (30%): Fraction of used tools that were relevant
- **Efficiency** (20%): Required tools / total tools used

```python
# Example: Required [get_billing_summary], Used [get_billing_summary, get_customer_detail]
recall = 1.0      # 1/1 required tools used
precision = 0.5   # 1/2 used tools were in expected set
efficiency = 0.5  # 1/2 ratio
```

#### 2. Tool Call Accuracy (15%) - LLM Judge
Azure AI Foundry's `ToolCallAccuracyEvaluator` assesses:
- Were the correct tools selected?
- Were parameters passed correctly?
- Was the sequence appropriate?

#### 3. Task Adherence (10%) - LLM Judge
Evaluates whether the agent followed proper procedures and policies.

#### 4. Completeness (10%)
Checks if scenario-specific success criteria were met:
```python
TOOL_CRITERIA_MAP = {
    "must_access_billing": ["get_billing_summary", "get_subscription_detail"],
    "must_check_security_logs": ["get_security_logs"],
    "must_check_promotions": ["get_eligible_promotions"],
}
```

#### 5. Response Quality (15% total)
- **LLM-based** (10%): Semantic quality assessment
- **Basic** (5%): Length, formatting, structure checks

#### 6. Grounded Accuracy (10%)
Verifies response is consistent with tool outputs (no hallucination).

#### 7. Intent Resolution (10%) - LLM Judge
Did the agent correctly understand what the customer wanted?

#### 8-10. Coherence, Fluency, Relevance (5% each)
Standard NLG quality metrics via Azure AI Foundry evaluators.

#### 11. Solution Accuracy (10%)
Compares agent response against expected ground truth solution.

### Multi-Turn Metrics (Outcome-Focused)

For multi-turn conversations, we **exclude tool-level metrics** and focus on outcomes:

| Metric | Weight | Rationale |
|--------|--------|-----------|
| Solution Accuracy | 30% | The ultimate measure - did we solve the problem? |
| Task Adherence | 20% | Did we follow proper procedures throughout? |
| Intent Resolution | 20% | Were all customer intents (across turns) resolved? |
| Coherence | 10% | Was the overall conversation logical and consistent? |
| Fluency | 10% | Was communication quality maintained? |
| Relevance | 10% | Did responses stay relevant across all turns? |

**Why exclude tool metrics for multi-turn?**

Consider a billing dispute that spans 3 turns:
1. Customer asks about high bill → Agent retrieves billing summary
2. Customer asks about specific charge → Agent gets usage data  
3. Customer requests payment plan → Agent records payment

Evaluating tool accuracy at each turn is misleading because:
- The "expected" tools depend on previous turn outcomes
- Alternative valid tool sequences exist
- What matters is: **Was the dispute resolved?**

---

## Setup Guide

### Prerequisites

- Python 3.10+ with `uv` package manager
- Azure CLI authenticated (`az login`)
- Existing `.env` file configured (see main repo [SETUP.md](../../SETUP.md))
- Azure subscription with:
  - Azure OpenAI resource (already configured in your `.env`)
  - Azure AI Project (for remote evaluation)

### Step 1: Environment Setup

If you haven't already set up the repository:

```bash
# Clone repository
git clone https://github.com/microsoft/OpenAIWorkshop.git
cd OpenAIWorkshop

# Install dependencies
uv sync
```

### Step 2: Configure Evaluation Variables

Add these variables to your existing `.env` file in `agentic_ai/applications/`:

```bash
# ============================================================
# EVALUATION-SPECIFIC CONFIGURATION (add to existing .env)
# ============================================================

# Azure AI Foundry Project Endpoint (Required for --remote evaluation)
# Get this from: https://ai.azure.com → Your Project → Settings → Project details
# Look for "Project endpoint" in the format:
#   https://<region>.api.azureml.ms/...  (older projects)
#   https://<account>.services.ai.azure.com/api/projects/<project>  (newer projects)
AZURE_AI_PROJECT_ENDPOINT=https://your-account.services.ai.azure.com/api/projects/your-project

# Evaluation Model (Optional - defaults to AZURE_OPENAI_CHAT_DEPLOYMENT)
# Use a separate deployment for evaluation to avoid rate limiting
# Supports GPT-4o, GPT-4o-mini, GPT-5, GPT-5.2, and o-series models
AZURE_OPENAI_EVAL_DEPLOYMENT=gpt-5.2
```

**Where to find the Project Endpoint:**
1. Go to [Azure AI Foundry](https://ai.azure.com)
2. Select your project
3. Click **Settings** → **Project details**
4. Copy the **Project endpoint** URL

> **Note**: The evaluation uses your existing `AZURE_OPENAI_CHAT_DEPLOYMENT` if `AZURE_OPENAI_EVAL_DEPLOYMENT` is not set. Consider using a separate deployment for evaluation to avoid rate limiting during heavy testing.

> **Reasoning Models (GPT-5+, o-series):** The framework automatically detects reasoning models
> and passes `is_reasoning_model=True` to all Azure AI Evaluation SDK evaluators. This ensures
> the SDK uses `max_completion_tokens` instead of `max_tokens`, which reasoning models require.
> No manual configuration is needed — just set your deployment name and the framework handles the rest.

**Assign required Azure roles:**
```bash
# Azure AI Developer role (required for remote evaluation)
az role assignment create \
  --assignee $(az ad signed-in-user show --query id -o tsv) \
  --role "Azure AI Developer" \
  --scope /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts/{ai-project}
```

### Step 3: Start Services

Start services in this order:

```bash
# Terminal 1: MCP Server (provides customer data APIs)
cd mcp
uv run python mcp_service.py
# Wait for: "MCP server running on http://localhost:8000"

# Terminal 2: Agent Backend
cd agentic_ai/applications
uv run python -m uvicorn backend:app --port 7000 --reload
# Wait for: "Application startup complete"
```

Verify services:
```bash
curl http://localhost:8000/health  # MCP server
curl http://localhost:7000/health  # Backend
```

---

## Running Evaluations

### Command-Line Options

```bash
cd agentic_ai/applications

uv run python ../evaluations/run_agent_eval.py [OPTIONS]
```

| Flag | Description |
|------|-------------|
| `--agent NAME` | Agent name for tracking (default: from AGENT_MODULE) |
| `--backend-url URL` | Backend URL (default: http://localhost:7000) |
| `--local` | Run local evaluation only (default if neither specified) |
| `--remote` | Push results to Azure AI Foundry |
| `--single-turn-only` | Run only single-turn test cases |
| `--multi-turn-only` | Run only multi-turn test cases |
| `--limit N` | Limit to N test cases (useful for testing) |
| `--ci` | CI mode: skip interactive prompts, auto-continue on MCP unavailability |

### Local Evaluation

Local evaluation runs custom metrics without Azure AI Foundry:

```bash
# Basic local evaluation (all test cases)
uv run python ../evaluations/run_agent_eval.py --agent my_agent

# Single-turn only
uv run python ../evaluations/run_agent_eval.py --agent my_agent --single-turn-only

# Multi-turn only  
uv run python ../evaluations/run_agent_eval.py --agent my_agent --multi-turn-only

# Quick test with 2 cases
uv run python ../evaluations/run_agent_eval.py --agent my_agent --limit 2
```

**Output:**
```
================================================================================
EVALUATION SUMMARY - http://localhost:7000
================================================================================
Agent: my_agent
Total Tests:    30
Passed:         26 ✓
Failed:         4 ✗
Pass Rate:      86.7%
Average Score:  4.12

Metric Breakdown (1-5 scale, threshold: 3):
  tool_behavior                   : 4.2/5 ████████████████     ✓
  completeness                    : 4.5/5 ██████████████████   ✓
  solution_accuracy               : 3.8/5 ███████████████      ✓
  coherence                       : 4.6/5 ██████████████████   ✓
  ...
```

### Remote Evaluation (Azure AI Foundry)

Remote evaluation pushes results to Azure AI Foundry portal:

```bash
# Remote only (skip local evaluation)
uv run python ../evaluations/run_agent_eval.py --agent my_agent --remote

# Both local and remote
uv run python ../evaluations/run_agent_eval.py --agent my_agent --local --remote
```

**What happens:**
1. Runs test cases against agent backend
2. Generates `evaluation_input_data.jsonl` in Foundry format
3. Creates evaluation in Azure AI Foundry with built-in evaluators:
   - `builtin.coherence`
   - `builtin.fluency`  
   - `builtin.relevance`
   - `builtin.groundedness`
   - `builtin.task_adherence`
   - `builtin.intent_resolution`
   - Custom `label_model` for solution_accuracy

**Portal naming convention:**
- Evaluation: `my_agent - Single Turn | 2026-02-03 14:30`
- Run: `my_agent | Single Turn | 2026-02-03 14:30`

### Comparing Agents

Compare different agent implementations:

```bash
# Compare single vs reflection agents
uv run python ../evaluations/run_agent_eval.py --agent agent_single --remote
# Restart backend with reflection agent
uv run python ../evaluations/run_agent_eval.py --agent agent_reflection --remote
```

View comparison in Azure AI Foundry portal → Evaluations → Compare runs.

---

## CI/CD Integration

Agent evaluation runs automatically in the CI/CD pipeline after integration tests pass. This provides continuous quality monitoring for every deployment.

### Architecture Decision

The evaluation infrastructure uses an **independent Azure AI Foundry project** that is **not** managed by the pipeline's Terraform. This is intentional:

| Concern | Pipeline-managed Foundry | Independent Foundry ✅ |
|---------|--------------------------|------------------------|
| `destroy-infrastructure` on dev | **Wipes all eval history** | Eval history preserved |
| Cross-branch comparison | Results lost per branch | All branches share one project |
| Setup complexity | Terraform modules needed | One-time manual setup |
| Lifecycle | Tied to deploy/destroy cycle | Persistent, always available |

The Foundry project (`evaluate`) lives in resource group `ml` and persists regardless of pipeline deploy/destroy cycles. This lets you compare agent quality trends across branches, deployments, and time.

### What Runs in CI

The `agent-evaluation` job runs as part of the **full deploy** pipeline (pushes and manual triggers, not PRs):

```
pipeline-config → preflight → deploy → build → update → integration-tests → agent-evaluation → destroy
```

The CI evaluation uses a focused subset for speed:

```bash
python agentic_ai/evaluations/run_agent_eval.py \
  --backend-url $BACKEND_ENDPOINT \
  --agent contoso-agent \
  --local --remote \
  --single-turn-only \
  --limit 5 \
  --ci
```

| Flag | Purpose |
|------|---------|
| `--single-turn-only` | Skip multi-turn tests (faster, deterministic) |
| `--limit 5` | Run 5 test cases (configurable via workflow input) |
| `--ci` | Non-interactive mode: skip `input()` prompts, auto-continue on MCP unavailability |
| `--local --remote` | Run local metrics AND push results to AI Foundry |

The job uses `continue-on-error: true` so evaluation failures **do not** block the pipeline. This is a quality gate for visibility, not a hard gate.

### Where Results Appear

**GitHub Actions:**
- **Step Summary** — Scores table rendered directly in the workflow run summary
- **Artifacts** — Full `eval_results/` directory downloadable from the run

**Azure AI Foundry Portal:**
- Navigate to [ai.azure.com](https://ai.azure.com) → Project `evaluate` → **Evaluations**
- Each CI run creates an evaluation named: `contoso-agent - Single Turn | YYYY-MM-DD HH:MM`
- Use the **Compare** feature to track quality across deployments

### Prerequisites

CI/CD evaluation requires one-time setup:

1. **RBAC roles** on the independent Foundry resources — see [GITHUB_ACTIONS_SETUP.md](../../infra/GITHUB_ACTIONS_SETUP.md#step-3b-assign-ai-foundry-evaluation-roles)
2. **GitHub Actions variables:**
   - `AZURE_AI_PROJECT_ENDPOINT` — AI Foundry project endpoint
   - `AZURE_OPENAI_EVAL_ENDPOINT` — AI Services endpoint for judge models
   - `AZURE_OPENAI_EVAL_DEPLOYMENT` — Model deployment name (e.g., `gpt-5.2`)
3. **No API keys needed** — authentication uses OIDC → `DefaultAzureCredential`
4. **SDK version** — CI uses `azure-ai-projects>=2.0.0b2` (pre-release) for `azure_ai_evaluator` support.
   The `--pre` flag is required for pip to resolve pre-release versions.

---

## Interpreting Results

### Score Thresholds

| Score Range | Meaning | Action |
|-------------|---------|--------|
| 4.5 - 5.0 | Excellent | Agent performing optimally |
| 3.5 - 4.4 | Good | Minor improvements possible |
| 3.0 - 3.4 | Acceptable | Investigate low-scoring metrics |
| 2.0 - 2.9 | Below expectations | Requires attention |
| 1.0 - 1.9 | Poor | Significant issues to fix |

### Common Issues

**Low Tool Behavior Score:**
- Agent using unnecessary tools (low efficiency)
- Missing required tools (low recall)
- Fix: Review agent's tool selection logic

**Low Solution Accuracy:**
- Agent response doesn't match expected outcome
- Fix: Check ground truth in dataset, verify agent logic

**Low Coherence/Fluency:**
- Response structure or language issues
- Fix: Adjust system prompts for clearer formatting

### Output Files

| File | Description |
|------|-------------|
| `eval_results/evaluation_summary.json` | Aggregate scores and pass rates |
| `eval_results/test_case_results.json` | Per-test-case detailed results |
| `evaluation_input_data.jsonl` | Foundry-format data for remote evaluation |

---

## Extending the Framework

### Adding Custom Metrics

1. Create evaluator class in `metrics.py`:

```python
class MyCustomEvaluator:
    def evaluate(self, response: str, expected: str) -> EvaluationResult:
        # Your evaluation logic
        score = ...  # 1-5 scale
        return EvaluationResult(
            metric_name="my_metric",
            metric_type=MetricType.ACCURACY,
            score=score,
            passed=score >= 3.0,
            details={...},
            explanation="..."
        )
```

2. Add to `evaluator.py` weights:
```python
SINGLE_TURN_WEIGHTS = {
    ...
    "my_metric": 0.05,  # 5% weight
}
```

### Adding Test Cases

Add to `eval_dataset.json`:

```json
{
  "id": "billing_new_scenario",
  "customer_query": "Your test query here",
  "customer_id": 101,
  "category": "billing",
  "expected_tools": ["get_billing_summary"],
  "required_tools": ["get_billing_summary"],
  "success_criteria": {"must_access_billing": true},
  "ground_truth_solution": "Expected agent response...",
  "scoring_rubric": "5: Complete and accurate...",
  "multi_turn": false
}
```

---

## Troubleshooting

### "Missing AZURE_AI_PROJECT_ENDPOINT"
```bash
# Add the project endpoint to your .env file
# Get it from: https://ai.azure.com → Your Project → Settings → Project details
echo 'AZURE_AI_PROJECT_ENDPOINT=https://your-account.services.ai.azure.com/api/projects/your-project' >> agentic_ai/applications/.env
```

### "Failed to resolve hostname" / DNS Error
```bash
# Placeholder values in .env file - must use real URLs
grep "AZURE_AI_PROJECT" agentic_ai/applications/.env
# Should show your actual Azure endpoint, not placeholders like "your-account"
```

### "Authentication failed"
```bash
az login
az account show
# Verify Azure AI Developer role is assigned to your account
```

### "Cannot connect to backend"
```bash
# Check services are running
curl http://localhost:8000/health  # MCP
curl http://localhost:7000/health  # Backend
```

### "No evaluation results in Foundry"
- Verify `--remote` flag was used
- Check `AZURE_AI_PROJECT_ENDPOINT` is set correctly
- Wait 1-2 minutes for portal to update

### "Rate limiting" during evaluation
```bash
# Use a separate deployment for evaluation
# Add to your .env:
AZURE_OPENAI_EVAL_DEPLOYMENT=gpt-4o-mini-eval
# This avoids sharing quota with your agent's chat deployment
```

### Low Scores on All Tests
- Verify MCP server has test data loaded
- Check agent can access tools (`DISABLE_AUTH=true` in dev)
- Review agent logs for errors

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_AI_PROJECT_ENDPOINT` | For `--remote` | Azure AI Foundry project endpoint URL |
| `AZURE_OPENAI_EVAL_DEPLOYMENT` | No | Model deployment for LLM-as-judge (defaults to `AZURE_OPENAI_CHAT_DEPLOYMENT`). Supports GPT-5+/o-series with auto reasoning model detection. |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Yes | Default model deployment (used if eval deployment not set) |
| `AZURE_OPENAI_ENDPOINT` | Yes | Azure OpenAI resource endpoint |
| `AZURE_OPENAI_API_KEY` | No* | Azure OpenAI API key (*not needed when using OIDC/managed identity in CI) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Evaluation Framework                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  run_agent_eval.py                                                      │
│  ├── Load eval_dataset.json (30 test cases)                            │
│  ├── Send queries to Agent Backend (HTTP)                              │
│  ├── Capture tool calls via WebSocket                                  │
│  └── Run evaluators                                                     │
│      │                                                                  │
│      ├── LOCAL EVALUATION (evaluator.py + metrics.py)                  │
│      │   ├── ToolBehaviorEvaluator (recall, precision, efficiency)     │
│      │   ├── CompletenessEvaluator (success criteria)                  │
│      │   ├── ResponseQualityEvaluator (LLM + basic)                    │
│      │   ├── GroundedAccuracyEvaluator                                 │
│      │   └── AzureAIEvaluatorSuite (if SDK available)                  │
│      │       ├── IntentResolutionEvaluator                             │
│      │       ├── TaskAdherenceEvaluator                                │
│      │       ├── ToolCallAccuracyEvaluator                             │
│      │       ├── CoherenceEvaluator                                    │
│      │       ├── FluencyEvaluator                                      │
│      │       └── RelevanceEvaluator                                    │
│      │                                                                  │
│      └── REMOTE EVALUATION (Azure AI Foundry)                          │
│          ├── Upload evaluation_input_data.jsonl                        │
│          ├── Run builtin.* evaluators                                  │
│          └── Run label_model for solution_accuracy                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## File Reference

| File | Purpose |
|------|---------|
| `run_agent_eval.py` | Main evaluation script - orchestrates tests, local eval, and remote push |
| `evaluator.py` | Evaluation runner, weight definitions, result aggregation |
| `metrics.py` | All metric implementations (custom + Azure AI wrappers) |
| `eval_dataset.json` | 30 test cases with ground truth and rubrics |
| `telemetry.py` | Azure Monitor tracing configuration |

**Generated files** (in `.gitignore`):
| File | Purpose |
|------|---------|
| `evaluation_input_data.jsonl` | Generated during `--remote` evaluation for Foundry upload |
| `eval_results/` | Local evaluation results and reports |

---

## License

This project is part of the Microsoft OpenAI Workshop. See [LICENSE](../../LICENSE) for details.
