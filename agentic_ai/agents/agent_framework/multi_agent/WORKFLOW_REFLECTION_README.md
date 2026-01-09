# Workflow-Based Reflection Agent

A workflow implementation of the reflection pattern using Agent Framework's `WorkflowBuilder`, featuring a 3-party communication design with quality assurance gates.

## Overview

This agent implements a sophisticated reflection pattern where responses are iteratively refined until they meet quality standards. Unlike the traditional two-agent reflection pattern, this uses a workflow-based approach with explicit conditional routing.

## Architecture

### 3-Party Communication Pattern

```
User → PrimaryAgent → ReviewerAgent → {approve: User, reject: PrimaryAgent}
         ↑                                          |
         |__________________________________________|
                    (feedback loop)
```

**Key Design Principles:**

1. **PrimaryAgent**: Customer support agent that:
   - Receives user messages with conversation history
   - Cannot send messages directly to user
   - All outputs go to ReviewerAgent for evaluation
   - Uses MCP tools for data retrieval

2. **ReviewerAgent**: Quality assurance gate that:
   - Evaluates PrimaryAgent responses
   - Acts as conditional router:
     - `approve=true` → Emit to user
     - `approve=false` → Send feedback to PrimaryAgent
   - Has access to full conversation context

3. **Conversation History**:
   - Maintained between User and PrimaryAgent only
   - Both agents receive history for context
   - Updated only when approved responses are delivered

## Features

✅ **Workflow-Based Architecture**
- Built using `WorkflowBuilder` for explicit control flow
- Bidirectional edges between PrimaryAgent and ReviewerAgent
- Conditional routing based on structured review decisions

✅ **Quality Assurance**
- Every response is reviewed before reaching the user
- Structured evaluation criteria:
  - Accuracy of information
  - Completeness of answer
  - Professional tone
  - Proper tool usage
  - Clarity and helpfulness

✅ **Iterative Refinement**
- Failed reviews trigger regeneration with feedback
- Conversation context preserved across iterations
- Unlimited refinement cycles until approval

✅ **MCP Tool Integration**
- Supports MCP tools for external data access
- Tools available to both agents
- Proper authentication via bearer tokens

✅ **Streaming Support**
- WebSocket-based streaming for real-time updates
- Progress indicators for each workflow stage
- Token-level streaming for agent responses

## Implementation Details

### Executor Classes

#### `PrimaryAgentExecutor`
```python
class PrimaryAgentExecutor(Executor):
    """
    Generates customer support responses.
    Sends all outputs to ReviewerAgent.
    """
    
    @handler
    async def handle_user_request(
        self, request: PrimaryAgentRequest, ctx: WorkflowContext[ReviewRequest]
    ) -> None:
        # Generate response with conversation history
        # Send to ReviewerAgent for evaluation
    
    @handler
    async def handle_review_feedback(
        self, review: ReviewResponse, ctx: WorkflowContext[ReviewRequest]
    ) -> None:
        # If not approved: incorporate feedback and regenerate
        # Send refined response back to ReviewerAgent
```

#### `ReviewerAgentExecutor`
```python
class ReviewerAgentExecutor(Executor):
    """
    Evaluates responses and acts as conditional gate.
    """
    
    @handler
    async def review_response(
        self, request: ReviewRequest, ctx: WorkflowContext[ReviewResponse]
    ) -> None:
        # Evaluate response quality
        # If approved: emit to user via AgentRunUpdateEvent
        # If not: send feedback to PrimaryAgent
```

### Message Flow

1. **User Input**
   ```python
   PrimaryAgentRequest(
       request_id=uuid4(),
       user_prompt="What is customer 1's billing status?",
       conversation_history=[...previous messages...]
   )
   ```

2. **Primary Agent → Reviewer**
   ```python
   ReviewRequest(
       request_id=request_id,
       user_prompt="What is customer 1's billing status?",
       conversation_history=[...],
       primary_agent_response=[...ChatMessage...]
   )
   ```

3. **Reviewer Decision**
   ```python
   ReviewDecision(
       approved=True/False,
       feedback="Constructive feedback or approval note"
   )
   ```

4. **Conditional Routing**
   - **Approved**: `AgentRunUpdateEvent` → User
   - **Rejected**: `ReviewResponse` → PrimaryAgent → Loop back to step 2

### Workflow Graph

```python
workflow = (
    WorkflowBuilder()
    .add_edge(primary_agent, reviewer_agent)  # Forward path
    .add_edge(reviewer_agent, primary_agent)  # Feedback path
    .set_start_executor(primary_agent)
    .build()
    .as_agent()  # Expose as standard agent interface
)
```

## Usage

### Basic Usage

```python
from agentic_ai.agents.agent_framework.multi_agent.reflection_workflow_agent import Agent

# Create agent instance
state_store = {}
session_id = "user_session_123"
agent = Agent(state_store=state_store, session_id=session_id)

# Process user query
response = await agent.chat_async("Can you help me with customer ID 1?")
print(response)
```

### With Streaming

```python
# Set WebSocket manager for streaming updates
agent.set_websocket_manager(ws_manager)

# Chat will now stream progress updates
response = await agent.chat_async("What promotions are available?")
```

### With MCP Tools

```python
# Set MCP_SERVER_URI environment variable
os.environ["MCP_SERVER_URI"] = "http://localhost:5000/mcp"

# Agent will automatically use MCP tools
agent = Agent(state_store=state_store, session_id=session_id, access_token=token)
response = await agent.chat_async("Get billing summary for customer 1")
```

## Environment Variables

Required:
- `AZURE_OPENAI_API_KEY`: Azure OpenAI API key
- `AZURE_OPENAI_CHAT_DEPLOYMENT`: Deployment name
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint URL
- `AZURE_OPENAI_API_VERSION`: API version (e.g., "2024-02-15-preview")
- `OPENAI_MODEL_NAME`: Model name (e.g., "gpt-4")

Optional:
- `MCP_SERVER_URI`: URI for MCP server (enables tool usage)

## Testing

Run the test script:

```bash
# From project root
python agentic_ai/agents/agent_framework/multi_agent/test_reflection_workflow_agent.py
```

The test script will:
1. Verify environment configuration
2. Run basic queries
3. Test MCP tool integration (if configured)
4. Display conversation history

## Comparison: Workflow vs Traditional

### Traditional Reflection Agent (`reflection_agent.py`)
- Direct agent-to-agent communication via `run()` calls
- Sequential execution (Step 1 → Step 2 → Step 3)
- Implicit control flow
- Manual state management

### Workflow Reflection Agent (`reflection_workflow_agent.py`)
- Message-based communication via `WorkflowContext`
- Graph-based execution (workflow edges)
- Explicit conditional routing
- Framework-managed state
- Better scalability for complex workflows

## Advanced Features

### Custom Review Criteria

Modify the ReviewerAgent's system prompt to enforce custom quality standards:

```python
# In ReviewerAgentExecutor.__init__
custom_criteria = """
Review for:
1. Response time < 2 seconds
2. Includes specific customer name
3. References at least 2 data points
4. Professional greeting and closing
"""
```

### Multiple Refinement Rounds Limit

Add a counter to prevent infinite loops:

```python
class PrimaryAgentExecutor(Executor):
    def __init__(self, max_refinements: int = 3):
        self._max_refinements = max_refinements
        self._refinement_counts = {}
    
    async def handle_review_feedback(self, review, ctx):
        count = self._refinement_counts.get(review.request_id, 0)
        if count >= self._max_refinements:
            # Force approval or escalate
            return
```

### Logging and Monitoring

All workflow events are logged with structured information:

```python
logger.info(f"[PrimaryAgent] Processing request {request_id[:8]}")
logger.info(f"[ReviewerAgent] Review decision - Approved: {approved}")
```

Enable debug logging for detailed traces:

```python
logging.basicConfig(level=logging.DEBUG)
```

## Best Practices

1. **Conversation History Management**
   - Keep history concise (last N messages)
   - Summarize old conversations for long sessions

2. **Error Handling**
   - Handle MCP tool failures gracefully
   - Implement retry logic with exponential backoff

3. **Performance**
   - Use streaming for better user experience
   - Consider caching for frequent queries

4. **Security**
   - Always validate MCP tool responses
   - Sanitize user inputs
   - Use bearer tokens for authentication

## Troubleshooting

### Common Issues

**Issue**: Agent not using MCP tools
- **Solution**: Verify `MCP_SERVER_URI` is set and server is running

**Issue**: Infinite refinement loop
- **Solution**: Check ReviewerAgent criteria are achievable, add max refinement limit

**Issue**: Missing conversation context
- **Solution**: Ensure history is properly loaded from state_store

**Issue**: Workflow hangs
- **Solution**: Check for unhandled message types, verify all edges are configured

## Future Enhancements

- [ ] Support for multi-modal inputs (images, files)
- [ ] Parallel reviewer agents (consensus-based approval)
- [ ] A/B testing of different review criteria
- [ ] Metrics and analytics dashboard
- [ ] Human-in-the-loop escalation for uncertain cases
- [ ] Fine-tuned reviewer models

## Related Examples

- `reference/agent-framework/python/samples/getting_started/workflows/agents/workflow_as_agent_reflection_pattern_azure.py` - Two-agent reflection
- `reference/agent-framework/python/samples/getting_started/workflows/agents/workflow_as_agent_human_in_the_loop_azure.py` - Human escalation
- `reference/agent-framework/python/samples/getting_started/workflows/control-flow/edge_condition.py` - Conditional routing

## License

This code is part of the OpenAI Workshop project. See LICENSE file for details.

## Contributing

Contributions are welcome! Please follow the project's contribution guidelines.
