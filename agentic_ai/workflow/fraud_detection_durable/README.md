# Durable Fraud Detection Workflow

A hybrid architecture combining **Workflow** (complex topology) and **Durable Task** (durability, HITL) for enterprise-grade fraud detection.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DURABLE TASK ORCHESTRATION (Outer Layer)              │
│                    Handles: Durability, Long Waits, Crash Recovery       │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  1. Receive Alert                                                │   │
│  │  2. Call "run_fraud_analysis" Activity ──────────────────────┐  │   │
│  │                                                               │  │   │
│  │     ┌─────────────────────────────────────────────────────┐  │  │   │
│  │     │        WORKFLOW (Inner Layer - Activity)             │  │  │   │
│  │     │        Handles: Complex Topology, Fast Execution     │  │  │   │
│  │     │                                                      │  │  │   │
│  │     │   AlertRouter                                        │  │  │   │
│  │     │       ↓                                              │  │  │   │
│  │     │   ┌───┴───┬───────┐   (fan-out)                     │  │  │   │
│  │     │   ↓       ↓       ↓                                  │  │  │   │
│  │     │ Usage  Location Billing                              │  │  │   │
│  │     │   └───────┼───────┘   (fan-in)                      │  │  │   │
│  │     │           ↓                                          │  │  │   │
│  │     │     Aggregator (LLM)                                 │  │  │   │
│  │     │           ↓                                          │  │  │   │
│  │     │   Returns: FraudRiskAssessment                       │  │  │   │
│  │     └─────────────────────────────────────────────────────┘  │  │   │
│  │                                                        ◄─────┘  │   │
│  │  3. Check Risk Score (simple if/else)                           │   │
│  │                                                                  │   │
│  │     IF risk >= 0.6:                                             │   │
│  │       → notify_analyst Activity                                 │   │
│  │       → wait_for_external_event("AnalystDecision") ⏸️           │   │
│  │       → execute_fraud_action Activity                           │   │
│  │                                                                  │   │
│  │     ELSE:                                                        │   │
│  │       → auto_clear Activity                                     │   │
│  │                                                                  │   │
│  │  4. send_notification Activity                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## 🎯 Why Hybrid Architecture?

| Feature | Workflow Only | Durable Task Only | **Hybrid (This)** |
|---------|--------------|-------------------|-------------------|
| Complex topology (fan-out/fan-in) | ✅ Easy | ❌ Manual | ✅ Easy |
| Crash recovery | ❌ Lost state | ✅ Automatic | ✅ Automatic |
| Human-in-the-loop | ⚠️ Manual checkpoints | ✅ Built-in events | ✅ Built-in events |
| Timeout handling | ❌ Not built-in | ✅ Native timers | ✅ Native timers |
| Long waits (hours/days) | ❌ Memory-bound | ✅ Persistent | ✅ Persistent |
| Visibility/Dashboard | ❌ Custom logging | ✅ DTS Dashboard | ✅ DTS Dashboard |

## 📁 Project Structure

```
fraud_detection_durable/
├── pyproject.toml                  # Dependencies
├── .env.sample                     # Environment template
├── fraud_analysis_workflow.py      # Inner workflow (fan-out → aggregate)
├── worker.py                       # DTS Worker with orchestration
├── client.py                       # CLI client for testing
├── backend.py                      # FastAPI backend for UI
├── README.md                       # This file
└── ui/                             # React UI
    ├── src/
    │   ├── App.jsx                 # Main app with WebSocket connection
    │   └── components/
    │       └── WorkflowVisualizer.jsx  # Interactive workflow diagram
    └── package.json
```

## 🚀 Quick Start

### Prerequisites

1. **Docker** - For DTS emulator
2. **Python 3.12+**
3. **Azure OpenAI** - With a deployed model
4. **MCP Server** - Running on port 8000

### Step 1: Start Durable Task Scheduler

```bash
docker run -d --name dts-emulator \
  -p 8080:8080 -p 8082:8082 \
  mcr.microsoft.com/dts/dts-emulator:latest
```

Dashboard: http://localhost:8082

### Step 2: Start MCP Server

```bash
cd mcp
uv run mcp_service.py
```

### Step 3: Configure Environment

```bash
cd agentic_ai/workflow/fraud_detection_durable
cp .env.sample .env
# Edit .env with your Azure OpenAI credentials
```

### Step 4: Install Dependencies

```bash
uv sync
```

### Step 5: Start Worker

```bash
uv run worker.py
```

### Step 6: Run Tests

**Option A: CLI Client**
```bash
uv run client.py
```

**Option B: FastAPI Backend + React UI**
```bash
# Terminal 1: Backend
uv run backend.py

# Terminal 2: React UI
cd ui
npm install
npm run dev
```

Open http://localhost:5173 to view the interactive workflow UI.

## 🧪 Test Scenarios

### 1. High-Risk Alert with Analyst Approval

```
Alert: ALERT-001 (multi_country_login, high severity)
    ↓
Workflow: Fan-out to 3 specialists
    ↓
Risk Score: 0.75 (HIGH RISK)
    ↓
⏸️ Waiting for analyst decision...
    ↓
Analyst: "lock_account"
    ↓
✅ Account locked, notification sent
```

### 2. Low-Risk Alert with Auto-Clear

```
Alert: ALERT-002 (data_spike, low severity)
    ↓
Workflow: Fan-out to 3 specialists
    ↓
Risk Score: 0.35 (LOW RISK)
    ↓
✅ Auto-cleared, notification sent
```

### 3. Timeout Escalation

```
Alert: ALERT-003 (unusual_charges, high severity)
    ↓
Workflow: Fan-out to 3 specialists
    ↓
Risk Score: 0.80 (CRITICAL)
    ↓
⏸️ Waiting for analyst decision...
    ↓
⏰ Timeout (72 hours)
    ↓
⚠️ Escalated to manager
```

## �️ React UI Features

The interactive React UI provides real-time visualization of the fraud detection workflow:

### Interactive Workflow Diagram

- **Real-time Status Updates**: Nodes change color based on execution state
  - Gray: Pending
  - Blue: Running (with pulse animation)
  - Green: Completed
  - Red: Failed

- **Clickable Nodes**: Click any workflow step to see detailed execution info:
  - **Tool Calls**: Actual MCP tool calls made (e.g., `get_billing_summary`, `get_data_usage`)
  - **Arguments**: Parameters passed to each tool
  - **Results**: Output returned from each tool call
  - **Step Output**: Final output from the agent step

### Human-in-the-Loop Panel

When the workflow reaches the Review Gateway (risk ≥ 0.6):
- Shows analyst decision options: `lock_account`, `flag_review`, `dismiss`
- Displays risk assessment details
- Allows analyst to submit decision via UI

### Example: Viewing Step Details

```
1. Click on "Usage Analyst" node
2. Popover shows:
   - Tool Calls (Real):
     • get_data_usage(subscription_id=5, start_date="2025-12-01", ...)
       → Result: {"total_gb": 45.2, "daily_avg": 1.5, ...}
     • get_billing_summary(customer_id=3)
       → Result: {"current_balance": 150.00, ...}
   - Output: "Usage analysis indicates 300% spike in data..."
```

## �📊 DTS Dashboard

Open http://localhost:8082 to see:

- All orchestration instances
- Pending external events (analyst decisions)
- Activity execution logs
- Orchestration timeline and status

![DTS Dashboard](../docs/media/dts-dashboard.png)

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | Required |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Deployment name | `gpt-4o` |
| `MCP_SERVER_URI` | MCP server URL | `http://localhost:8000/mcp` |
| `DTS_ENDPOINT` | DTS scheduler URL | `http://localhost:8080` |
| `DTS_TASKHUB` | DTS task hub name | `fraud-detection` |
| `ANALYST_APPROVAL_TIMEOUT_HOURS` | Timeout for analyst review | `72` |

### Risk Threshold

Edit `worker.py` to change the risk threshold:

```python
# Current: 0.6 (60%)
if risk_score >= 0.6:
    # High risk path
else:
    # Low risk path
```

## 🏛️ Key Components

### 1. Inner Workflow (`fraud_analysis_workflow.py`)

The workflow handles complex multi-agent topology:

```python
# Fan-out: Alert → 3 Specialists
builder.add_edge(alert_router, usage_executor)
builder.add_edge(alert_router, location_executor)
builder.add_edge(alert_router, billing_executor)

# Fan-in: 3 Specialists → Aggregator
builder.add_fan_in_edge(
    [usage_executor, location_executor, billing_executor],
    aggregator
)
```

### 2. DTS Orchestration (`worker.py`)

The orchestration handles durability and HITL:

```python
def fraud_detection_orchestration(context, payload):
    # Run inner workflow as activity
    assessment = yield context.call_activity("run_fraud_analysis", alert)
    
    if assessment["risk_score"] >= 0.6:
        # Wait for analyst with timeout
        approval_task = context.wait_for_external_event("AnalystDecision")
        timeout_task = context.create_timer(timedelta(hours=72))
        
        winner = yield when_any([approval_task, timeout_task])
        
        if winner == approval_task:
            yield context.call_activity("execute_fraud_action", decision)
        else:
            yield context.call_activity("escalate_timeout", assessment)
    else:
        yield context.call_activity("auto_clear_alert", assessment)
```

### 3. Activities

| Activity | Purpose |
|----------|---------|
| `run_fraud_analysis` | Runs inner workflow, returns assessment |
| `notify_analyst` | Sends notification for review |
| `execute_fraud_action` | Executes approved action |
| `auto_clear_alert` | Auto-clears low-risk alerts |
| `escalate_timeout` | Escalates on timeout |
| `send_notification` | Sends final notification |

## 🔄 Comparison with Original Implementation

| Aspect | Original (`fraud_detection/`) | Durable (`fraud_detection_durable/`) |
|--------|-------------------------------|-------------------------------------|
| HITL Pattern | `ctx.request_info()` + `@response_handler` | `wait_for_external_event()` |
| Checkpointing | `FileCheckpointStorage` (manual) | DTS (automatic) |
| Timeout | Not built-in | Native `create_timer()` |
| Recovery | Load checkpoint manually | Automatic replay |
| Dashboard | Custom logging | DTS Dashboard |
| Topology | Full workflow | Workflow as activity |

## 🐛 Troubleshooting

### "Cannot connect to DTS"

```bash
# Check if DTS is running
docker ps | grep dts

# Restart if needed
docker restart dts-emulator
```

### "Worker not processing"

1. Check worker is running: `uv run worker.py`
2. Check logs for errors
3. Verify DTS endpoint in `.env`

### "Analyst decision not received"

1. Check instance ID matches
2. Verify event name is `AnalystDecision`
3. Check DTS dashboard for pending events

## 📚 Related Documentation

- [Agent Framework Workflow](../human-in-the-loop.md)
- [Durable Task Samples](https://github.com/microsoft/agent-framework/tree/main/python/samples/getting_started/durabletask)
- [Original Fraud Detection](../fraud_detection/README.md)

## 📜 License

Copyright (c) Microsoft. All rights reserved.
