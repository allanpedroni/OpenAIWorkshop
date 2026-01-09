# Integration Guide: Workflow Reflection Agent

This guide shows how to integrate the workflow-based reflection agent into your existing application.

## Quick Start

### 1. Import the Agent

```python
from agentic_ai.agents.agent_framework.multi_agent.reflection_workflow_agent import Agent
```

### 2. Basic Integration

Replace your existing reflection agent import:

```python
# OLD: Traditional reflection agent
# from agentic_ai.agents.agent_framework.multi_agent.reflection_agent import Agent

# NEW: Workflow-based reflection agent
from agentic_ai.agents.agent_framework.multi_agent.reflection_workflow_agent import Agent
```

### 3. Use Same Interface

The workflow agent implements the same `BaseAgent` interface:

```python
# Create agent instance
state_store = {}
session_id = "user_123"
agent = Agent(state_store=state_store, session_id=session_id)

# Optional: Set WebSocket manager for streaming
agent.set_websocket_manager(ws_manager)

# Chat with user
response = await agent.chat_async("Help me with billing for customer 1")
```

## Backend Integration (FastAPI/Flask)

### Example: FastAPI Backend

```python
from fastapi import FastAPI, WebSocket
from typing import Dict, Any
from agentic_ai.agents.agent_framework.multi_agent.reflection_workflow_agent import Agent

app = FastAPI()

# Global state store (in production, use Redis or database)
state_store: Dict[str, Any] = {}

@app.post("/chat")
async def chat_endpoint(
    session_id: str,
    message: str,
    use_workflow: bool = True  # Toggle between traditional and workflow
):
    """
    Chat endpoint with workflow reflection agent.
    """
    
    if use_workflow:
        from agentic_ai.agents.agent_framework.multi_agent.reflection_workflow_agent import Agent
    else:
        from agentic_ai.agents.agent_framework.multi_agent.reflection_agent import Agent
    
    # Create agent
    agent = Agent(state_store=state_store, session_id=session_id)
    
    # Process message
    response = await agent.chat_async(message)
    
    return {
        "session_id": session_id,
        "response": response,
        "agent_type": "workflow" if use_workflow else "traditional"
    }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for streaming support.
    """
    await websocket.accept()
    
    # Create WebSocket manager (simplified)
    class WSManager:
        async def broadcast(self, sid: str, message: dict):
            if sid == session_id:
                await websocket.send_json(message)
    
    ws_manager = WSManager()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get("message", "")
            
            # Create agent with streaming support
            agent = Agent(state_store=state_store, session_id=session_id)
            agent.set_websocket_manager(ws_manager)
            
            # Process message (will stream updates via WebSocket)
            response = await agent.chat_async(message)
            
            # Send final confirmation
            await websocket.send_json({
                "type": "complete",
                "response": response
            })
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()
```

## Frontend Integration

### JavaScript/TypeScript Client

```typescript
interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface StreamEvent {
  type: 'orchestrator' | 'agent_start' | 'agent_token' | 'agent_message' | 'final_result';
  agent_id?: string;
  content?: string;
  kind?: 'plan' | 'progress' | 'result';
}

class WorkflowReflectionClient {
  private ws: WebSocket;
  private sessionId: string;
  
  constructor(sessionId: string) {
    this.sessionId = sessionId;
    this.ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);
    this.setupEventHandlers();
  }
  
  private setupEventHandlers() {
    this.ws.onmessage = (event) => {
      const data: StreamEvent = JSON.parse(event.data);
      this.handleStreamEvent(data);
    };
  }
  
  private handleStreamEvent(event: StreamEvent) {
    switch (event.type) {
      case 'orchestrator':
        this.updateOrchestrator(event.kind!, event.content!);
        break;
        
      case 'agent_start':
        this.showAgentBadge(event.agent_id!);
        break;
        
      case 'agent_token':
        this.appendToken(event.agent_id!, event.content!);
        break;
        
      case 'agent_message':
        this.finalizeAgentMessage(event.agent_id!, event.content!);
        break;
        
      case 'final_result':
        this.displayFinalResponse(event.content!);
        break;
    }
  }
  
  private updateOrchestrator(kind: string, content: string) {
    const container = document.getElementById('orchestrator-status');
    if (container) {
      container.innerHTML = `
        <div class="orchestrator-${kind}">
          <strong>${kind.toUpperCase()}</strong>
          <p>${content}</p>
        </div>
      `;
    }
  }
  
  private showAgentBadge(agentId: string) {
    const badge = document.createElement('div');
    badge.className = `agent-badge ${agentId}`;
    badge.textContent = agentId.replace('_', ' ').toUpperCase();
    document.getElementById('agent-container')?.appendChild(badge);
  }
  
  private appendToken(agentId: string, token: string) {
    const messageDiv = document.getElementById(`message-${agentId}`) 
      || this.createMessageDiv(agentId);
    messageDiv.textContent += token;
  }
  
  private createMessageDiv(agentId: string): HTMLDivElement {
    const div = document.createElement('div');
    div.id = `message-${agentId}`;
    div.className = 'agent-message streaming';
    document.getElementById('messages-container')?.appendChild(div);
    return div;
  }
  
  private finalizeAgentMessage(agentId: string, content: string) {
    const messageDiv = document.getElementById(`message-${agentId}`);
    if (messageDiv) {
      messageDiv.classList.remove('streaming');
      messageDiv.classList.add('complete');
    }
  }
  
  private displayFinalResponse(content: string) {
    const responseDiv = document.createElement('div');
    responseDiv.className = 'final-response';
    responseDiv.innerHTML = `
      <div class="message assistant">
        <strong>Assistant:</strong>
        <p>${content}</p>
      </div>
    `;
    document.getElementById('chat-container')?.appendChild(responseDiv);
  }
  
  public sendMessage(message: string) {
    this.ws.send(JSON.stringify({ message }));
  }
}

// Usage
const client = new WorkflowReflectionClient('user_session_123');
client.sendMessage('What is the billing status for customer 1?');
```

### React Component

```tsx
import React, { useState, useEffect, useCallback } from 'react';

interface StreamEvent {
  type: string;
  agent_id?: string;
  content?: string;
  kind?: string;
}

const WorkflowReflectionChat: React.FC<{ sessionId: string }> = ({ sessionId }) => {
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [orchestratorStatus, setOrchestratorStatus] = useState<string>('');
  const [activeAgents, setActiveAgents] = useState<Set<string>>(new Set());
  const [ws, setWs] = useState<WebSocket | null>(null);
  
  useEffect(() => {
    const websocket = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);
    
    websocket.onmessage = (event) => {
      const data: StreamEvent = JSON.parse(event.data);
      handleStreamEvent(data);
    };
    
    setWs(websocket);
    
    return () => {
      websocket.close();
    };
  }, [sessionId]);
  
  const handleStreamEvent = (event: StreamEvent) => {
    switch (event.type) {
      case 'orchestrator':
        setOrchestratorStatus(event.content || '');
        break;
        
      case 'agent_start':
        setActiveAgents(prev => new Set(prev).add(event.agent_id!));
        break;
        
      case 'final_result':
        setMessages(prev => [...prev, { role: 'assistant', content: event.content! }]);
        setActiveAgents(new Set());
        break;
    }
  };
  
  const sendMessage = useCallback((message: string) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ message }));
      setMessages(prev => [...prev, { role: 'user', content: message }]);
    }
  }, [ws]);
  
  return (
    <div className="workflow-reflection-chat">
      <div className="orchestrator-status">
        {orchestratorStatus && (
          <div className="status-banner">
            {orchestratorStatus}
          </div>
        )}
      </div>
      
      <div className="active-agents">
        {Array.from(activeAgents).map(agentId => (
          <span key={agentId} className="agent-badge">
            {agentId.replace('_', ' ')}
          </span>
        ))}
      </div>
      
      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <strong>{msg.role}:</strong>
            <p>{msg.content}</p>
          </div>
        ))}
      </div>
      
      <ChatInput onSend={sendMessage} />
    </div>
  );
};
```

## Streamlit Integration

```python
import streamlit as st
import asyncio
from agentic_ai.agents.agent_framework.multi_agent.reflection_workflow_agent import Agent

# Initialize session state
if 'state_store' not in st.session_state:
    st.session_state.state_store = {}
if 'session_id' not in st.session_state:
    st.session_state.session_id = "streamlit_session"

# Create agent
@st.cache_resource
def get_agent():
    return Agent(
        state_store=st.session_state.state_store,
        session_id=st.session_state.session_id
    )

# UI
st.title("Workflow Reflection Agent Chat")

# Display chat history
chat_history = st.session_state.state_store.get(
    f"{st.session_state.session_id}_chat_history", []
)

for msg in chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input
if prompt := st.chat_input("Ask me anything..."):
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)
    
    # Get agent response
    agent = get_agent()
    
    # Show processing indicator
    with st.spinner("Processing with workflow reflection..."):
        response = asyncio.run(agent.chat_async(prompt))
    
    # Display assistant response
    with st.chat_message("assistant"):
        st.write(response)
    
    # Rerun to update chat history
    st.rerun()
```

## Configuration Management

### Environment Configuration

Create a `.env` file:

```bash
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
OPENAI_MODEL_NAME=gpt-4

# Optional: MCP Server
MCP_SERVER_URI=http://localhost:5000/mcp
```

### Dynamic Agent Selection

```python
from typing import Literal
from agentic_ai.agents.base_agent import BaseAgent

AgentType = Literal["workflow", "traditional"]

def create_agent(
    agent_type: AgentType,
    state_store: dict,
    session_id: str,
    **kwargs
) -> BaseAgent:
    """
    Factory function to create the appropriate agent type.
    """
    if agent_type == "workflow":
        from agentic_ai.agents.agent_framework.multi_agent.reflection_workflow_agent import Agent
    elif agent_type == "traditional":
        from agentic_ai.agents.agent_framework.multi_agent.reflection_agent import Agent
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    return Agent(state_store=state_store, session_id=session_id, **kwargs)

# Usage
agent = create_agent(
    agent_type="workflow",  # or "traditional"
    state_store=state_store,
    session_id=session_id,
    access_token=access_token
)
```

## Monitoring and Logging

### Enhanced Logging

```python
import logging
from agentic_ai.agents.agent_framework.multi_agent.reflection_workflow_agent import Agent

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('workflow_agent.log'),
        logging.StreamHandler()
    ]
)

# Create agent
agent = Agent(state_store=state_store, session_id=session_id)

# Use agent (logs will capture all workflow steps)
response = await agent.chat_async("Help me")
```

### Metrics Collection

```python
import time
from dataclasses import dataclass
from typing import List

@dataclass
class WorkflowMetrics:
    session_id: str
    request_id: str
    start_time: float
    end_time: float
    refinement_count: int
    approved: bool
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

class MetricsCollector:
    def __init__(self):
        self.metrics: List[WorkflowMetrics] = []
    
    def track_request(self, session_id: str, request_id: str):
        # Implementation for tracking metrics
        pass
    
    def report(self):
        total_requests = len(self.metrics)
        avg_duration = sum(m.duration for m in self.metrics) / total_requests
        avg_refinements = sum(m.refinement_count for m in self.metrics) / total_requests
        
        print(f"Total Requests: {total_requests}")
        print(f"Average Duration: {avg_duration:.2f}s")
        print(f"Average Refinements: {avg_refinements:.2f}")

# Usage with agent
metrics = MetricsCollector()
# Integrate with agent workflow
```

## Testing

### Unit Tests

```python
import pytest
from agentic_ai.agents.agent_framework.multi_agent.reflection_workflow_agent import Agent

@pytest.fixture
def agent():
    state_store = {}
    return Agent(state_store=state_store, session_id="test_session")

@pytest.mark.asyncio
async def test_basic_chat(agent):
    response = await agent.chat_async("What is 2+2?")
    assert response is not None
    assert len(response) > 0

@pytest.mark.asyncio
async def test_conversation_history(agent):
    # First message
    await agent.chat_async("My name is John")
    
    # Second message should have context
    response = await agent.chat_async("What is my name?")
    assert "john" in response.lower()

@pytest.mark.asyncio
async def test_mcp_tool_usage(agent):
    # Assuming MCP is configured
    response = await agent.chat_async("Get customer details for ID 1")
    # Verify tool was used and response contains customer data
    assert "customer" in response.lower()
```

### Integration Tests

```python
import pytest
from fastapi.testclient import TestClient
from your_backend import app

@pytest.fixture
def client():
    return TestClient(app)

def test_chat_endpoint(client):
    response = client.post(
        "/chat",
        json={
            "session_id": "test_123",
            "message": "Hello",
            "use_workflow": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["agent_type"] == "workflow"
    assert "response" in data
```

## Best Practices

1. **Session Management**: Use unique session IDs per user
2. **State Persistence**: Store state in Redis/database for production
3. **Error Handling**: Implement proper error boundaries
4. **Rate Limiting**: Protect endpoints from abuse
5. **Authentication**: Secure MCP endpoints with proper tokens
6. **Monitoring**: Log all workflow events for debugging
7. **Testing**: Write comprehensive tests for edge cases

## Troubleshooting

### Issue: Workflow hangs

**Cause**: Missing message handlers or unconnected edges

**Solution**: Verify WorkflowBuilder has all necessary edges:
```python
.add_edge(primary_agent, reviewer_agent)
.add_edge(reviewer_agent, primary_agent)
```

### Issue: MCP tools not working

**Cause**: MCP_SERVER_URI not set or server not running

**Solution**: 
```bash
# Start MCP server
python mcp/mcp_service.py

# Set environment variable
export MCP_SERVER_URI=http://localhost:5000/mcp
```

### Issue: Streaming not working

**Cause**: WebSocket manager not set

**Solution**:
```python
agent.set_websocket_manager(ws_manager)
```

## Migration Checklist

- [ ] Update agent imports
- [ ] Test basic chat functionality
- [ ] Verify conversation history persistence
- [ ] Test streaming with WebSocket
- [ ] Validate MCP tool integration
- [ ] Update frontend to handle new event types
- [ ] Configure monitoring and logging
- [ ] Run integration tests
- [ ] Deploy to staging environment
- [ ] Monitor performance metrics

## Support

For issues or questions:
1. Check the [README](WORKFLOW_REFLECTION_README.md)
2. Review [Architecture Diagrams](WORKFLOW_DIAGRAMS.md)
3. Run tests: `python test_reflection_workflow_agent.py`
4. Enable debug logging for detailed traces
