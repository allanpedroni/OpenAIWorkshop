# Workflow Reflection Agent - Quick Reference

## One-Minute Overview

**What**: Workflow-based reflection agent with 3-party quality assurance pattern  
**When**: Use for high-quality responses with built-in review process  
**Why**: Better control flow, scalability, and maintainability vs traditional approach

## Quick Start (30 seconds)

```python
from agentic_ai.agents.agent_framework.multi_agent.reflection_workflow_agent import Agent

state_store = {}
agent = Agent(state_store=state_store, session_id="user_123")
response = await agent.chat_async("Your question here")
```

## Architecture at a Glance

```
User ─┬──> PrimaryAgent ─┬──> ReviewerAgent ─┬──> User (if approved)
      │                   │                    │
      └─ History ─────────┘                    └──> PrimaryAgent (if rejected)
                                                           │
                                                           └──> (loop)
```

## Key Files

| File | Purpose | Size |
|------|---------|------|
| `reflection_workflow_agent.py` | Main implementation | ~600 lines |
| `test_reflection_workflow_agent.py` | Test suite | ~200 lines |
| `WORKFLOW_REFLECTION_README.md` | Full documentation | ~400 lines |
| `WORKFLOW_DIAGRAMS.md` | Visual diagrams | ~500 lines |
| `INTEGRATION_GUIDE.md` | Integration examples | ~800 lines |

## Message Flow Cheat Sheet

### 1️⃣ User → PrimaryAgent
```python
PrimaryAgentRequest(
    request_id=uuid4(),
    user_prompt="Help me",
    conversation_history=[...]
)
```

### 2️⃣ PrimaryAgent → ReviewerAgent
```python
ReviewRequest(
    request_id=request_id,
    user_prompt="Help me",
    conversation_history=[...],
    primary_agent_response=[ChatMessage(...)]
)
```

### 3️⃣ ReviewerAgent Decision
```python
ReviewDecision(
    approved=True/False,
    feedback="..."
)
```

### 4️⃣ Output
- **If approved**: `AgentRunUpdateEvent` → User
- **If rejected**: `ReviewResponse` → PrimaryAgent (loop to step 2)

## Common Tasks

### Enable Streaming
```python
agent.set_websocket_manager(ws_manager)
```

### Enable MCP Tools
```bash
export MCP_SERVER_URI=http://localhost:5000/mcp
```

### Access History
```python
history = agent.chat_history  # List of dicts
# or
history = agent._conversation_history  # List of ChatMessage
```

### Run Tests
```bash
python agentic_ai/agents/agent_framework/multi_agent/test_reflection_workflow_agent.py
```

## Environment Variables

```bash
# Required
AZURE_OPENAI_API_KEY=sk-...
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4
AZURE_OPENAI_ENDPOINT=https://....openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
OPENAI_MODEL_NAME=gpt-4

# Optional
MCP_SERVER_URI=http://localhost:5000/mcp
```

## Streaming Events

| Event Type | When | Purpose |
|------------|------|---------|
| `orchestrator` | Start/Progress/End | Workflow status |
| `agent_start` | Agent begins | Show agent badge |
| `agent_token` | Token generated | Stream text |
| `agent_message` | Agent completes | Full message |
| `tool_called` | Tool invoked | Show tool usage |
| `final_result` | Workflow done | Final response |

## Debug Checklist

❓ **Not working?**
1. Check environment variables are set
2. Verify MCP server is running (if using tools)
3. Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`
4. Check WebSocket manager is set (for streaming)
5. Review logs for error messages

❓ **Infinite loop?**
1. Check reviewer criteria are achievable
2. Add max refinement counter
3. Review feedback content for clarity

❓ **No MCP tools?**
1. Verify `MCP_SERVER_URI` is set
2. Test MCP server: `curl $MCP_SERVER_URI/health`
3. Check access token is valid

## Comparison Matrix

| Feature | Traditional | Workflow | Winner |
|---------|------------|----------|--------|
| Control Flow | Implicit | Explicit | 🏆 Workflow |
| Testability | Medium | High | 🏆 Workflow |
| Scalability | Limited | High | 🏆 Workflow |
| Learning Curve | Low | Medium | 🥈 Traditional |
| State Management | Manual | Auto | 🏆 Workflow |
| Debugging | Hard | Easy | 🏆 Workflow |

## Code Snippets

### Backend Integration (FastAPI)
```python
@app.post("/chat")
async def chat(session_id: str, message: str):
    agent = Agent(state_store, session_id)
    response = await agent.chat_async(message)
    return {"response": response}
```

### Frontend Integration (React)
```tsx
const [response, setResponse] = useState('');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'final_result') {
    setResponse(data.content);
  }
};
```

### Streamlit Integration
```python
agent = Agent(st.session_state.state_store, session_id)
if prompt := st.chat_input("Ask..."):
    response = asyncio.run(agent.chat_async(prompt))
    st.chat_message("assistant").write(response)
```

## Performance Tips

✅ **DO:**
- Use streaming for better UX
- Enable debug logging during development
- Implement retry logic for MCP tools
- Cache frequent queries
- Monitor refinement counts

❌ **DON'T:**
- Allow unlimited refinement loops
- Log sensitive customer data
- Skip error handling
- Forget to persist state
- Ignore WebSocket errors

## Workflow Builder Pattern

```python
workflow = (
    WorkflowBuilder()
    .add_edge(executor_a, executor_b)  # A → B
    .add_edge(executor_b, executor_a)  # B → A (feedback)
    .set_start_executor(executor_a)     # Start with A
    .build()                            # Build workflow
    .as_agent()                         # Expose as agent
)
```

## Executor Handlers

```python
class MyExecutor(Executor):
    @handler
    async def handle_message(
        self, 
        request: RequestType,
        ctx: WorkflowContext[ResponseType]
    ) -> None:
        # Process request
        result = await self.process(request)
        
        # Send to next executor
        await ctx.send_message(result)
        
        # Or emit to user
        await ctx.add_event(
            AgentRunUpdateEvent(
                self.id, 
                data=AgentRunResponseUpdate(...)
            )
        )
```

## Structured Output

```python
from pydantic import BaseModel

class MyResponse(BaseModel):
    field1: str
    field2: bool

# Use in chat client
response = await chat_client.get_response(
    messages=[...],
    response_format=MyResponse
)

# Parse
parsed = MyResponse.model_validate_json(response.text)
```

## Logging Best Practices

```python
import logging

logger = logging.getLogger(__name__)

# In executor
logger.info(f"[{self.id}] Processing request {request_id[:8]}")
logger.debug(f"[{self.id}] Full request: {request}")
logger.error(f"[{self.id}] Error: {e}", exc_info=True)
```

## Testing Patterns

```python
@pytest.fixture
def agent():
    return Agent(state_store={}, session_id="test")

@pytest.mark.asyncio
async def test_chat(agent):
    response = await agent.chat_async("Hello")
    assert response is not None
    assert len(response) > 0

@pytest.mark.asyncio
async def test_history(agent):
    await agent.chat_async("My name is John")
    response = await agent.chat_async("What is my name?")
    assert "john" in response.lower()
```

## Common Pitfalls

🔴 **Pitfall 1**: Not setting start executor
```python
# Wrong
WorkflowBuilder().add_edge(a, b).build()

# Right
WorkflowBuilder().add_edge(a, b).set_start_executor(a).build()
```

🔴 **Pitfall 2**: Missing return edges
```python
# Wrong (one-way only)
.add_edge(primary, reviewer)

# Right (bidirectional for loops)
.add_edge(primary, reviewer)
.add_edge(reviewer, primary)
```

🔴 **Pitfall 3**: Not handling async properly
```python
# Wrong
response = agent.chat_async(prompt)

# Right
response = await agent.chat_async(prompt)
# or
response = asyncio.run(agent.chat_async(prompt))
```

## Links

📚 **Documentation**
- [Full README](WORKFLOW_REFLECTION_README.md)
- [Diagrams](WORKFLOW_DIAGRAMS.md)
- [Integration Guide](INTEGRATION_GUIDE.md)
- [Project Summary](PROJECT_SUMMARY.md)

🔧 **Code**
- [Implementation](reflection_workflow_agent.py)
- [Tests](test_reflection_workflow_agent.py)

📖 **Examples**
- Agent Framework Samples in `reference/agent-framework/`

## Support

1. Check docs ↑
2. Run tests
3. Enable debug logging
4. Review error messages
5. Check environment vars

## Version Info

- **Version**: 1.0.0
- **Status**: ✅ Production Ready
- **Python**: 3.10+
- **Dependencies**: agent-framework, pydantic, azure-identity

---

**TIP**: Bookmark this page for quick reference! 📌
