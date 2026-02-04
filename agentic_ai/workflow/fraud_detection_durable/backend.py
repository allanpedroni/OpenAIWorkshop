"""
FastAPI Backend for Durable Fraud Detection.

This backend provides:
1. REST API to start orchestrations and submit decisions
2. WebSocket for real-time status updates
3. Integration with DTS client

The UI connects here instead of managing workflow directly.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from durabletask.azuremanaged.client import DurableTaskSchedulerClient
from durabletask.client import OrchestrationState
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Durable Fraud Detection API",
    description="Hybrid Workflow + Durable Task architecture for fraud detection",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
ANALYST_APPROVAL_EVENT = "AnalystDecision"
ORCHESTRATION_NAME = "fraud_detection_orchestration"


# ============================================================================
# Request/Response Models
# ============================================================================


class StartWorkflowRequest(BaseModel):
    """Request to start a fraud detection workflow."""
    alert_id: str
    customer_id: int
    alert_type: str
    description: str = ""
    severity: str = "medium"
    approval_timeout_hours: float = 72.0


class StartWorkflowResponse(BaseModel):
    """Response after starting a workflow."""
    instance_id: str
    alert_id: str
    status: str


class AnalystDecisionRequest(BaseModel):
    """Analyst decision submitted from UI."""
    instance_id: str
    alert_id: str
    approved_action: str
    analyst_notes: str = ""
    analyst_id: str = "analyst_ui"


class WorkflowStatusResponse(BaseModel):
    """Workflow status response."""
    instance_id: str
    status: str
    custom_status: str | None
    result: dict | None


class AlertInfo(BaseModel):
    """Sample alert info."""
    alert_id: str
    customer_id: int
    alert_type: str
    description: str
    severity: str


# ============================================================================
# Sample Alerts
# ============================================================================

SAMPLE_ALERTS = [
    AlertInfo(
        alert_id="ALERT-001",
        customer_id=1,
        alert_type="multi_country_login",
        description="Login attempts from USA and Russia within 2 hours",
        severity="high",
    ),
    AlertInfo(
        alert_id="ALERT-002",
        customer_id=2,
        alert_type="data_spike",
        description="Data usage increased by 500% in last 24 hours",
        severity="medium",
    ),
    AlertInfo(
        alert_id="ALERT-003",
        customer_id=3,
        alert_type="unusual_charges",
        description="Three large purchases totaling $5,000 in 10 minutes",
        severity="high",
    ),
]


# ============================================================================
# DTS Client
# ============================================================================

_dts_client: DurableTaskSchedulerClient | None = None


def get_dts_client() -> DurableTaskSchedulerClient:
    """Get or create DTS client."""
    global _dts_client
    
    if _dts_client is None:
        taskhub = os.getenv("DTS_TASKHUB", "default")
        endpoint = os.getenv("DTS_ENDPOINT", "http://localhost:8080")
        
        credential = None if endpoint.startswith("http://localhost") else DefaultAzureCredential()
        
        _dts_client = DurableTaskSchedulerClient(
            host_address=endpoint,
            secure_channel=not endpoint.startswith("http://localhost"),
            taskhub=taskhub,
            token_credential=credential,
        )
        logger.info(f"DTS client initialized: {endpoint}/{taskhub}")
    
    return _dts_client


# ============================================================================
# WebSocket Manager
# ============================================================================


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}  # instance_id -> connections

    async def connect(self, websocket: WebSocket, instance_id: str):
        await websocket.accept()
        if instance_id not in self.active_connections:
            self.active_connections[instance_id] = []
        self.active_connections[instance_id].append(websocket)
        logger.info(f"WebSocket connected for instance {instance_id}")

    def disconnect(self, websocket: WebSocket, instance_id: str):
        if instance_id in self.active_connections:
            self.active_connections[instance_id].remove(websocket)
            if not self.active_connections[instance_id]:
                del self.active_connections[instance_id]
        logger.info(f"WebSocket disconnected for instance {instance_id}")

    async def broadcast(self, instance_id: str, message: dict):
        """Broadcast message to all connections watching this instance."""
        if instance_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[instance_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            
            for conn in disconnected:
                self.disconnect(conn, instance_id)


manager = ConnectionManager()


# ============================================================================
# Background Task: Poll DTS for Status Updates
# ============================================================================

_polling_tasks: dict[str, asyncio.Task] = {}


async def poll_orchestration_status(instance_id: str):
    """Background task to poll DTS and broadcast status updates."""
    client = get_dts_client()
    last_status = None
    last_custom_status = None
    
    while instance_id in manager.active_connections:
        try:
            state = client.get_orchestration_state(instance_id)
            
            if state:
                status = state.runtime_status.name
                custom_status_raw = state.serialized_custom_status
                
                # Debug: log raw custom_status
                # logger.info(f"[Backend] Raw custom_status: {custom_status_raw[:200] if custom_status_raw else 'None'}")
                
                # Parse custom_status JSON if present
                custom_status = custom_status_raw
                step_details = None
                status_message = custom_status_raw
                
                if custom_status_raw:
                    try:
                        parsed = json.loads(custom_status_raw)
                        # Handle double-encoding: if parsed is still a string, parse again
                        if isinstance(parsed, str):
                            try:
                                parsed = json.loads(parsed)
                            except json.JSONDecodeError:
                                pass  # Keep as string
                        
                        if isinstance(parsed, dict):
                            status_message = parsed.get("message", custom_status_raw)
                            step_details = parsed.get("step_details")
                            custom_status = status_message
                    except json.JSONDecodeError:
                        pass  # Keep original string
                
                # Only broadcast if status changed
                if status != last_status or custom_status_raw != last_custom_status:
                    message = {
                        "type": "status_update",
                        "instance_id": instance_id,
                        "status": status,
                        "custom_status": custom_status,
                        "step_details": step_details,
                        "timestamp": datetime.now().isoformat(),
                    }
                    
                    # Check if waiting for analyst
                    if custom_status and "Awaiting analyst" in custom_status:
                        message["decision_required"] = True
                    
                    # Check if completed
                    if status in ("COMPLETED", "FAILED", "TERMINATED"):
                        if state.serialized_output:
                            try:
                                message["result"] = json.loads(state.serialized_output)
                            except json.JSONDecodeError:
                                message["result"] = {"raw": state.serialized_output}
                    
                    await manager.broadcast(instance_id, message)
                    
                    last_status = status
                    last_custom_status = custom_status_raw
                
                # Stop polling if completed
                if status in ("COMPLETED", "FAILED", "TERMINATED"):
                    logger.info(f"Orchestration {instance_id} completed, stopping poll")
                    break
        
        except Exception as e:
            logger.error(f"Error polling status for {instance_id}: {e}")
        
        await asyncio.sleep(0.1)  # Poll every 100ms for responsive UI
    
    # Cleanup
    if instance_id in _polling_tasks:
        del _polling_tasks[instance_id]


def start_status_polling(instance_id: str):
    """Start background polling for an instance."""
    if instance_id not in _polling_tasks:
        task = asyncio.create_task(poll_orchestration_status(instance_id))
        _polling_tasks[instance_id] = task


# ============================================================================
# REST API Endpoints
# ============================================================================


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/alerts", response_model=list[AlertInfo])
async def get_alerts():
    """Get sample alerts."""
    return SAMPLE_ALERTS


@app.post("/api/workflow/start", response_model=StartWorkflowResponse)
async def start_workflow(request: StartWorkflowRequest):
    """Start a new fraud detection orchestration."""
    client = get_dts_client()
    
    alert = {
        "alert_id": request.alert_id,
        "customer_id": request.customer_id,
        "alert_type": request.alert_type,
        "description": request.description,
        "timestamp": datetime.now().isoformat(),
        "severity": request.severity,
        "approval_timeout_hours": request.approval_timeout_hours,
    }
    
    instance_id = client.schedule_new_orchestration(
        ORCHESTRATION_NAME,
        input=alert,
        instance_id=f"fraud-{request.alert_id}-{int(time.time())}",
    )
    
    logger.info(f"Started orchestration {instance_id} for alert {request.alert_id}")
    
    return StartWorkflowResponse(
        instance_id=instance_id,
        alert_id=request.alert_id,
        status="started",
    )


@app.get("/api/workflow/status/{instance_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(instance_id: str):
    """Get current status of an orchestration."""
    client = get_dts_client()
    
    state = client.get_orchestration_state(instance_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Orchestration not found")
    
    result = None
    if state.serialized_output:
        try:
            result = json.loads(state.serialized_output)
        except json.JSONDecodeError:
            result = {"raw": state.serialized_output}
    
    return WorkflowStatusResponse(
        instance_id=instance_id,
        status=state.runtime_status.name,
        custom_status=state.serialized_custom_status,
        result=result,
    )


@app.post("/api/workflow/decision")
async def submit_decision(request: AnalystDecisionRequest):
    """Submit analyst decision for a pending orchestration."""
    client = get_dts_client()
    
    decision = {
        "alert_id": request.alert_id,
        "approved_action": request.approved_action,
        "analyst_notes": request.analyst_notes,
        "analyst_id": request.analyst_id,
    }
    
    client.raise_orchestration_event(
        instance_id=request.instance_id,
        event_name=ANALYST_APPROVAL_EVENT,
        data=decision,
    )
    
    logger.info(f"Submitted decision for {request.instance_id}: {request.approved_action}")
    
    # Broadcast decision event
    await manager.broadcast(request.instance_id, {
        "type": "decision_submitted",
        "instance_id": request.instance_id,
        "action": request.approved_action,
        "timestamp": datetime.now().isoformat(),
    })
    
    return {"status": "submitted", "instance_id": request.instance_id}


# ============================================================================
# WebSocket Endpoint
# ============================================================================


@app.websocket("/ws/{instance_id}")
async def websocket_endpoint(websocket: WebSocket, instance_id: str):
    """
    WebSocket endpoint for real-time status updates.
    
    Connect to /ws/{instance_id} to receive updates for a specific orchestration.
    """
    await manager.connect(websocket, instance_id)
    
    # Start polling for this instance
    start_status_polling(instance_id)
    
    try:
        # Send initial status
        client = get_dts_client()
        state = client.get_orchestration_state(instance_id)
        
        if state:
            await websocket.send_json({
                "type": "initial_status",
                "instance_id": instance_id,
                "status": state.runtime_status.name,
                "custom_status": state.serialized_custom_status,
            })
        
        # Keep connection alive
        while True:
            try:
                # Wait for client messages (ping/pong, commands, etc.)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                
                # Handle client commands
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    pass
                    
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {instance_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {instance_id}: {e}")
    finally:
        manager.disconnect(websocket, instance_id)


# ============================================================================
# Startup/Shutdown
# ============================================================================


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    logger.info("="*60)
    logger.info("Starting Durable Fraud Detection Backend")
    logger.info("="*60)
    
    # Pre-initialize DTS client
    try:
        get_dts_client()
        logger.info("✓ DTS client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize DTS client: {e}")
        logger.error("Make sure DTS emulator is running")
    
    logger.info("Backend ready! 🚀")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    logger.info("Shutting down backend...")
    
    # Cancel polling tasks
    for task in _polling_tasks.values():
        task.cancel()


# ============================================================================
# Main
# ============================================================================


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info",
    )
