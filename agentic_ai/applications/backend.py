"""  
FastAPI entry-point.  
  
Only two lines changed compared with your original file:  
    from utils.state_store import get_state_store  
    STATE_STORE = get_state_store()  
Everything else is untouched.  
"""  
  
import os  
import sys  
from pathlib import Path  
from typing import Dict, List, Any, Optional, Set, DefaultDict
from collections import defaultdict
  
import uvicorn  
from fastapi import FastAPI  
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel  
from dotenv import load_dotenv  
from fastapi import FastAPI, Depends, Header, WebSocket, WebSocketDisconnect

# ------------------------------------------------------------------  
# Environment  
# ------------------------------------------------------------------  
load_dotenv()  # read .env if present  

# Feature flag: disable auth for local dev / demos
DISABLE_AUTH = os.getenv("DISABLE_AUTH", "false").lower() in ("1", "true", "yes")

if DISABLE_AUTH:
    AAD_TENANT_ID = None
    EXPECTED_AUDIENCE = None
else:
    # Azure AD / Entra tenant and expected audience for tokens hitting this backend
    AAD_TENANT_ID = os.getenv("AAD_TENANT_ID") or os.getenv("TENANT_ID")
    if not AAD_TENANT_ID:
        raise RuntimeError("AAD_TENANT_ID (or TENANT_ID) must be set unless DISABLE_AUTH is true.")
    # Audience should be the App ID URI of the MCP API you're protecting via APIM, e.g., "api://<mcp-api-app-id>"
    EXPECTED_AUDIENCE = (
        os.getenv("MCP_API_AUDIENCE")
        or os.getenv("API_AUDIENCE")
        or (f"api://{os.getenv('MCP_API_CLIENT_ID')}" if os.getenv("MCP_API_CLIENT_ID") else None)
    )
    if not EXPECTED_AUDIENCE:
        raise RuntimeError("Set MCP_API_AUDIENCE (e.g., api://<mcp-api-app-id>) for JWT validation or set DISABLE_AUTH=true.")


def verify_token(authorization: str | None = Header(None, alias="Authorization")):
    """Return bearer token or placeholder when auth disabled.

    In production (DISABLE_AUTH=false) you should validate signature, issuer,
    audience, expiry, scopes, etc. Here we keep it minimal.
    """
    if DISABLE_AUTH:
        return "dev-anon-token"
    # Minimal check (can be expanded):
    if not authorization or not authorization.startswith("Bearer "):
        # For stricter behavior we could raise HTTPException(401,...)
        return None
    return authorization.split(" ", 1)[1]

# ------------------------------------------------------------------  
# Bring project root onto the path & load your agent dynamically  
# ------------------------------------------------------------------  
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  

# Available agent modules that can be selected
AVAILABLE_AGENTS = [
    "agents.agent_framework.single_agent",
    "agents.agent_framework.multi_agent.handoff_multi_domain_agent",
    "agents.agent_framework.multi_agent.magentic_group",
    "agents.agent_framework.multi_agent.reflection_agent",
    "agents.agent_framework.multi_agent.reflection_workflow_agent",
]

# Current active agent module (can be changed at runtime)
CURRENT_AGENT_MODULE = os.getenv("AGENT_MODULE", AVAILABLE_AGENTS[0])

def load_agent_class(module_path: str):
    """Dynamically load and return the Agent class from the given module path."""
    try:
        agent_module = __import__(module_path, fromlist=["Agent"])  # type: ignore[arg-type]
        return getattr(agent_module, "Agent")
    except Exception as e:
        print(f"Error loading agent module {module_path}: {e}")
        raise

# Load initial agent
Agent = load_agent_class(CURRENT_AGENT_MODULE)  
  
# ------------------------------------------------------------------  
# Get the correct state-store implementation  
# ------------------------------------------------------------------  
from utils import get_state_store  
  
STATE_STORE = get_state_store()  # either dict or CosmosDBStateStore  
  
# ------------------------------------------------------------------  
# FastAPI app  
# ------------------------------------------------------------------  
app = FastAPI()

# Add CORS middleware to handle preflight OPTIONS requests from React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Serve static files from React build (production mode only)
STATIC_DIR = Path(__file__).parent / "static"
STATIC_ASSET_DIR = STATIC_DIR / "static"

if STATIC_ASSET_DIR.exists():  # CRA build places assets in nested /static directory
    app.mount("/static", StaticFiles(directory=str(STATIC_ASSET_DIR)), name="static")
elif STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ---------------------------------------------------------------
# WebSocket connection manager (per session broadcast)
# ---------------------------------------------------------------
class ConnectionManager:
    def __init__(self) -> None:
        self.sessions: DefaultDict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, session_id: str, ws: WebSocket) -> None:
        self.sessions[session_id].add(ws)

    def disconnect(self, session_id: str, ws: WebSocket) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].discard(ws)
            if not self.sessions[session_id]:
                self.sessions.pop(session_id, None)

    async def broadcast(self, session_id: str, message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self.sessions.get(session_id, [])):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(session_id, ws)

MANAGER = ConnectionManager()

# Make MANAGER globally accessible for background tasks
import builtins
builtins.GLOBAL_WS_MANAGER = MANAGER
  
  
class ChatRequest(BaseModel):  
    session_id: str  
    prompt: str  
  
  
class ChatResponse(BaseModel):  
    response: str  
  
  
class ConversationHistoryResponse(BaseModel):  
    session_id: str  
    history: List[Dict[str, str]]  
  
  
class SessionResetRequest(BaseModel):  
    session_id: str  
  
@app.post("/chat", response_model=ChatResponse)  
async def chat(req: ChatRequest, token: str = Depends(verify_token)):  
    # Propagate the bearer token down to the agent so it can call the MCP (via APIM)
    try:
        agent = Agent(STATE_STORE, req.session_id, access_token=token)
    except TypeError:
        agent = Agent(STATE_STORE, req.session_id)
    answer = await agent.chat_async(req.prompt)  
    return ChatResponse(response=answer)  
  
@app.post("/reset_session")  
async def reset_session(req: SessionResetRequest, token: str = Depends(verify_token)):  
    if req.session_id in STATE_STORE:  
        del STATE_STORE[req.session_id]  
    hist_key = f"{req.session_id}_chat_history"  
    if hist_key in STATE_STORE:  
        del STATE_STORE[hist_key]
    return {"status": "success", "message": "Session reset successfully"}

@app.get("/history/{session_id}", response_model=ConversationHistoryResponse)  
async def get_conversation_history(session_id: str, token: str = Depends(verify_token)):  
    history = STATE_STORE.get(f"{session_id}_chat_history", [])  
    return ConversationHistoryResponse(session_id=session_id, history=history)

# ──────────────────────────────────────────────────────────────
# Agent Management Endpoints
# ──────────────────────────────────────────────────────────────
class AgentInfo(BaseModel):
    module_path: str
    display_name: str
    description: str

class AgentListResponse(BaseModel):
    agents: List[AgentInfo]
    current_agent: str

class SetAgentRequest(BaseModel):
    module_path: str

@app.get("/agents", response_model=AgentListResponse)
async def list_agents(token: str = Depends(verify_token)):
    """List all available agent modules and the currently active one."""
    agents = []
    for module_path in AVAILABLE_AGENTS:
        # Parse display name and description from module path
        parts = module_path.split('.')[-1]
        display_name = parts.replace('_', ' ').title()
        
        # Add descriptions for known agents
        descriptions = {
            "single_agent": "Simple single-agent chat without orchestration",
            "handoff_multi_domain_agent": "Multi-agent system with domain-specific specialists and handoffs",
            "magentic_group": "MagenticOne-style orchestrator with specialist agents",
            "reflection_agent": "Agent with built-in reflection and self-critique",
            "reflection_workflow_agent": "Workflow-based reflection with quality assurance gates",
        }
        description = descriptions.get(parts, "Agent module")
        
        agents.append(AgentInfo(
            module_path=module_path,
            display_name=display_name,
            description=description
        ))
    
    return AgentListResponse(
        agents=agents,
        current_agent=CURRENT_AGENT_MODULE
    )

@app.post("/agents/set")
async def set_active_agent(req: SetAgentRequest, token: str = Depends(verify_token)):
    """Change the active agent module."""
    global CURRENT_AGENT_MODULE, Agent
    
    if req.module_path not in AVAILABLE_AGENTS:
        return {
            "status": "error",
            "message": f"Invalid agent module. Available: {AVAILABLE_AGENTS}"
        }
    
    try:
        # Load new agent class
        NewAgent = load_agent_class(req.module_path)
        
        # Update globals
        CURRENT_AGENT_MODULE = req.module_path
        Agent = NewAgent
        
        return {
            "status": "success",
            "message": f"Active agent changed to {req.module_path}",
            "current_agent": CURRENT_AGENT_MODULE
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to load agent: {str(e)}"
        }

# ──────────────────────────────────────────────────────────────
# Root route to serve React app
# ──────────────────────────────────────────────────────────────
@app.get("/")
async def read_root():
    """Serve the React frontend index.html"""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "OpenAI Workshop Backend API", "version": "1.0.0"}

# ──────────────────────────────────────────────────────────────
# NEW: WebSocket streaming endpoint
#   - Wraps agent.run_stream
#   - Streams tokens, messages, tool calls, and side-channel progress
# ──────────────────────────────────────────────────────────────
@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    await ws.accept()
    connected_session: Optional[str] = None
    try:
        while True:
            data = await ws.receive_json()
            session_id = data.get("session_id")
            prompt = data.get("prompt")
            token = data.get("access_token")  # optional

            if not session_id:
                await ws.send_json({"type": "error", "message": "Missing session_id"})
                continue
            if connected_session is None:
                await MANAGER.connect(session_id, ws)
                connected_session = session_id
                await ws.send_json({"type": "info", "message": f"Registered session {session_id}"})

            # If only registering (no prompt) continue
            if not prompt:
                continue

            # Create agent for this session
            try:
                agent = Agent(STATE_STORE, session_id, access_token=token)
            except TypeError:
                agent = Agent(STATE_STORE, session_id)

            # Inject WebSocket manager for Magentic streaming
            if hasattr(agent, "set_websocket_manager"):
                agent.set_websocket_manager(MANAGER)

            # Set progress sink if supported (for some agent types)
            if hasattr(agent, "set_progress_sink"):
                async def progress_sink(ev: dict):
                    # Broadcast progress events
                    await MANAGER.broadcast(session_id, ev)
                agent.set_progress_sink(progress_sink)

            # Stream events from agent
            try:
                # Check if agent supports streaming (Autogen or Agent Framework)
                if hasattr(agent, "chat_stream"):
                    # Autogen streaming
                    async for event in agent.chat_stream(prompt):
                        evt = await serialize_autogen_event(event)
                        if evt and evt.get("type") in ("token", "message", "final"):
                            await MANAGER.broadcast(session_id, evt)
                elif hasattr(agent, "chat_async"):
                    # Agent Framework - may or may not use streaming callback
                    result = await agent.chat_async(prompt)
                    # If agent has _ws_manager attribute, it supports streaming and events sent via callback
                    # Otherwise, broadcast final result here
                    if not hasattr(agent, "_ws_manager"):
                        await MANAGER.broadcast(session_id, {"type": "final_result", "content": result})
                    # Else: events including final result are sent via streaming callback
                else:
                    await MANAGER.broadcast(session_id, {"type": "error", "message": "Agent does not support streaming"})

                await MANAGER.broadcast(session_id, {"type": "done"})
            except Exception as e:
                await MANAGER.broadcast(session_id, {"type": "error", "message": str(e)})
    except WebSocketDisconnect:
        pass
    finally:
        if connected_session:
            MANAGER.disconnect(connected_session, ws)


# Helper: serialize Autogen streaming events to JSON
async def serialize_autogen_event(event: Any) -> Optional[dict]:
    """
    Convert Autogen streaming event (BaseChatMessage | BaseAgentEvent | Response) to a JSON-friendly dict.
    """
    try:
        # Lazy imports to avoid hard dep here
        from autogen_agentchat.messages import TextMessage, ToolCallSummaryMessage, HandoffMessage, StructuredMessage
        from autogen_agentchat.messages import ModelClientStreamingChunkEvent, ThoughtEvent, ToolCallRequestEvent, ToolCallExecutionEvent
        from autogen_agentchat.base import Response

        if isinstance(event, ModelClientStreamingChunkEvent):
            return {"type": "token", "content": event.content}
        if isinstance(event, TextMessage):
            if event.source != "user":
                return {"type": "message", "role": "assistant", "content": event.content}
        if isinstance(event, ThoughtEvent):
            return {"type": "thought", "content": event.content}
        if isinstance(event, ToolCallRequestEvent):
            # includes FunctionCall list
            calls = []

            for c in event.content:
                try:
                    calls.append({"name": c.name, "arguments": c.arguments})
                except Exception:
                    pass
            return {"type": "tool_call", "calls": calls}
        if isinstance(event, ToolCallExecutionEvent):
            # results list
            results = []
            for r in event.content:
                try:
                    results.append({"is_error": r.is_error, "content": r.content, "name": r.name})
                except Exception:
                    pass
            return {"type": "tool_result", "results": results}
        if isinstance(event, ToolCallSummaryMessage):
            return {"type": "tool_summary", "content": event.content}
        if isinstance(event, HandoffMessage):
            return {"type": "handoff", "target": event.target, "content": getattr(event, "content", "")}
        if isinstance(event, StructuredMessage):
            return {"type": "structured", "content": getattr(event, "content", {})}
        if isinstance(event, Response):

            # Final assistant message in Response.chat_message
            msg = event.chat_message
            if hasattr(msg, "content"):
                return {"type": "final", "content": getattr(msg, "content")}
            return {"type": "final"}
        # Fallthrough: ignore unknown types
        return None
    except Exception:
        return None

  
  
if __name__ == "__main__":  
    uvicorn.run(app, host="0.0.0.0", port=7000)