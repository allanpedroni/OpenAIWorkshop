"""
Agent Framework Workflow-based Reflection Agent

This implementation uses the WorkflowBuilder pattern with a 3-party communication flow:
User -> PrimaryAgent -> ReviewerAgent -> User (if approved) OR back to PrimaryAgent (if rejected)

Key Design:
- PrimaryAgent receives user messages but cannot send directly to user
- All PrimaryAgent outputs go to ReviewerAgent for evaluation
- ReviewerAgent acts as a conditional gate: approve or request_for_edit
- Conversation history is maintained between user and PrimaryAgent only
- History is passed to both agents for context
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List
from uuid import uuid4

from agent_framework import (
    AgentRunResponseUpdate,
    AgentRunUpdateEvent,
    ChatMessage,
    Contents,
    Executor,
    MCPStreamableHTTPTool,
    Role,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)
from agent_framework.azure import AzureOpenAIChatClient
from pydantic import BaseModel

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ReviewDecision(BaseModel):
    """Structured output from ReviewerAgent for reliable routing."""
    approved: bool
    feedback: str


@dataclass
class PrimaryAgentRequest:
    """Request sent to PrimaryAgent with conversation history."""
    request_id: str
    user_prompt: str
    conversation_history: list[ChatMessage]


@dataclass
class ReviewRequest:
    """Request sent from PrimaryAgent to ReviewerAgent."""
    request_id: str
    user_prompt: str
    conversation_history: list[ChatMessage]
    primary_agent_response: list[ChatMessage]


@dataclass
class ReviewResponse:
    """Response from ReviewerAgent back to PrimaryAgent."""
    request_id: str
    approved: bool
    feedback: str


class PrimaryAgentExecutor(Executor):
    """
    Primary Agent - Customer Support Agent with MCP tools.
    Receives user messages and generates responses sent to ReviewerAgent for approval.
    """

    def __init__(
        self,
        id: str,
        chat_client: AzureOpenAIChatClient,
        tools: MCPStreamableHTTPTool | None = None,
        model: str | None = None,
        max_refinements: int = 3,
    ) -> None:
        super().__init__(id=id)
        self._chat_client = chat_client
        self._tools = tools
        self._model = model
        self._max_refinements = max_refinements
        # Track pending requests for retry with feedback
        self._pending_requests: dict[str, tuple[PrimaryAgentRequest, list[ChatMessage]]] = {}
        # Track refinement counts to prevent infinite loops
        self._refinement_counts: dict[str, int] = {}

    @handler
    async def handle_user_request(
        self, request: PrimaryAgentRequest, ctx: WorkflowContext[ReviewRequest]
    ) -> None:
        """Handle initial user request with conversation history."""
        print(f"[PrimaryAgent] Processing user request (ID: {request.request_id[:8]})")
        logger.info(f"[PrimaryAgent] Processing user request (ID: {request.request_id[:8]})")

        # Build message list with system prompt, history, and new user message
        messages = [
            ChatMessage(
                role=Role.SYSTEM,
                text=(
                    "You are a helpful customer support assistant for Contoso company. "
                    "You can help with billing, promotions, security, account information, and other customer inquiries. "
                    "Use the available MCP tools to look up customer information, billing details, promotions, and security settings. "
                    "When a customer provides an ID or asks about their account, use the tools to retrieve accurate, up-to-date information. "
                    "Always be helpful, professional, and provide detailed information when available."
                ),
            )
        ]
        
        # Add conversation history for context
        messages.extend(request.conversation_history)
        
        # Add current user prompt
        messages.append(ChatMessage(role=Role.USER, text=request.user_prompt))

        print(f"[PrimaryAgent] Generating response with {len(messages)} messages in context")
        logger.info(f"[PrimaryAgent] Generating response with {len(messages)} messages in context")

        # Generate response
        response = await self._chat_client.get_response(
            messages=messages,
            tools=self._tools,
            model=self._model,
        )

        print(f"[PrimaryAgent] Response generated: {response.messages[-1].text[:100]}...")
        logger.info(f"[PrimaryAgent] Response generated")

        # Store full message context for potential retry
        all_messages = messages + response.messages
        self._pending_requests[request.request_id] = (request, all_messages)
        
        # Initialize refinement counter
        if request.request_id not in self._refinement_counts:
            self._refinement_counts[request.request_id] = 0

        # Send to ReviewerAgent for evaluation
        review_request = ReviewRequest(
            request_id=request.request_id,
            user_prompt=request.user_prompt,
            conversation_history=request.conversation_history,
            primary_agent_response=response.messages,
        )
        
        print(f"[PrimaryAgent] Sending response to ReviewerAgent for evaluation")
        logger.info(f"[PrimaryAgent] Sending response to ReviewerAgent for evaluation")
        await ctx.send_message(review_request)

    @handler
    async def handle_review_feedback(
        self, review: ReviewResponse, ctx: WorkflowContext[ReviewRequest]
    ) -> None:
        """Handle feedback from ReviewerAgent and regenerate if needed."""
        print(f"[PrimaryAgent] Received review (ID: {review.request_id[:8]}) - Approved: {review.approved}")
        logger.info(f"[PrimaryAgent] Received review (ID: {review.request_id[:8]}) - Approved: {review.approved}")

        if review.request_id not in self._pending_requests:
            logger.error(f"[PrimaryAgent] Unknown request ID: {review.request_id}")
            raise ValueError(f"Unknown request ID in review: {review.request_id}")

        original_request, messages = self._pending_requests.pop(review.request_id)

        if review.approved:
            print(f"[PrimaryAgent] Response approved! Sending to user via WorkflowAgent")
            logger.info(f"[PrimaryAgent] Response approved")
            
            # Clean up refinement counter
            self._refinement_counts.pop(review.request_id, None)
            
            # Extract contents from response to emit to user
            # The WorkflowAgent will handle emitting this to the external consumer
            # We don't send directly - ReviewerAgent will handle final emission
            return

        # Check if we've exceeded max refinements
        current_count = self._refinement_counts.get(review.request_id, 0)
        if current_count >= self._max_refinements:
            print(f"[PrimaryAgent] Max refinements ({self._max_refinements}) reached. Force approving response.")
            logger.warning(f"[PrimaryAgent] Max refinements reached for request {review.request_id[:8]}")
            
            # Clean up
            self._refinement_counts.pop(review.request_id, None)
            
            # Force emit the last response even though not approved
            # The ReviewerAgent already sent the ReviewResponse, so we're done
            return

        # Increment refinement counter
        self._refinement_counts[review.request_id] = current_count + 1
        
        # Not approved - incorporate feedback and regenerate
        print(f"[PrimaryAgent] Response not approved (attempt {current_count + 1}/{self._max_refinements}). Feedback: {review.feedback[:100]}...")
        logger.info(f"[PrimaryAgent] Regenerating with feedback (attempt {current_count + 1}/{self._max_refinements})")

        # Add feedback to message context
        messages.append(
            ChatMessage(
                role=Role.SYSTEM,
                text=f"REVIEWER FEEDBACK: {review.feedback}\n\nPlease improve your response based on this feedback.",
            )
        )
        
        # Add the original user prompt again for clarity
        messages.append(ChatMessage(role=Role.USER, text=original_request.user_prompt))

        # Regenerate response
        response = await self._chat_client.get_response(
            messages=messages,
            tools=self._tools,
            model=self._model,
        )

        print(f"[PrimaryAgent] New response generated: {response.messages[-1].text[:100]}...")
        logger.info(f"[PrimaryAgent] New response generated")

        # Update stored messages
        messages.extend(response.messages)
        self._pending_requests[review.request_id] = (original_request, messages)

        # Send updated response for re-review
        review_request = ReviewRequest(
            request_id=review.request_id,
            user_prompt=original_request.user_prompt,
            conversation_history=original_request.conversation_history,
            primary_agent_response=response.messages,
        )
        
        print(f"[PrimaryAgent] Sending refined response to ReviewerAgent")
        logger.info(f"[PrimaryAgent] Sending refined response to ReviewerAgent")
        await ctx.send_message(review_request)


class ReviewerAgentExecutor(Executor):
    """
    Reviewer Agent - Quality assurance gate.
    Evaluates PrimaryAgent responses for accuracy, completeness, and professionalism.
    Acts as conditional gate: approved responses go to user, rejected go back to PrimaryAgent.
    """

    def __init__(
        self,
        id: str,
        chat_client: AzureOpenAIChatClient,
        tools: MCPStreamableHTTPTool | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._chat_client = chat_client
        self._tools = tools
        self._model = model

    @handler
    async def review_response(
        self, request: ReviewRequest, ctx: WorkflowContext[ReviewResponse]
    ) -> None:
        """
        Review the PrimaryAgent's response and decide: approve or request edit.
        Approved responses are emitted to user via AgentRunUpdateEvent.
        Rejected responses are sent back to PrimaryAgent with feedback.
        """
        print(f"[ReviewerAgent] Evaluating response (ID: {request.request_id[:8]})")
        logger.info(f"[ReviewerAgent] Evaluating response (ID: {request.request_id[:8]})")

        # Build review context with conversation history
        messages = [
            ChatMessage(
                role=Role.SYSTEM,
                text=(
                    "You are a quality assurance reviewer for customer support responses. "
                    "Review the customer support agent's response for:\n"
                    "1. Accuracy of information\n"
                    "2. Completeness of answer\n"
                    "3. Professional tone\n"
                    "4. Proper use of available tools\n"
                    "5. Clarity and helpfulness\n\n"
                    "Be reasonable in your evaluation. If the response is professional, addresses the customer's question, "
                    "and provides useful information, APPROVE it. Only reject if there are significant issues.\n\n"
                    "Respond with a structured JSON containing:\n"
                    "- approved: true if response meets quality standards (be reasonable), false only for major issues\n"
                    "- feedback: constructive feedback (if not approved) or brief approval note"
                ),
            )
        ]

        # Add conversation history for context
        messages.extend(request.conversation_history)

        # Add the user's question
        messages.append(ChatMessage(role=Role.USER, text=request.user_prompt))

        # Add the agent's response
        messages.extend(request.primary_agent_response)

        # Add explicit review instruction
        messages.append(
            ChatMessage(
                role=Role.USER,
                text="Please review the agent's response above and provide your assessment.",
            )
        )

        print(f"[ReviewerAgent] Sending review request to LLM")
        logger.info(f"[ReviewerAgent] Sending review request to LLM")

        # Get structured review decision
        response = await self._chat_client.get_response(
            messages=messages,
            response_format=ReviewDecision,
            tools=self._tools,
            model=self._model,
        )

        # Parse decision
        decision = ReviewDecision.model_validate_json(response.messages[-1].text)

        print(f"[ReviewerAgent] Review decision - Approved: {decision.approved}")
        if not decision.approved:
            print(f"[ReviewerAgent] Feedback: {decision.feedback[:100]}...")
        logger.info(f"[ReviewerAgent] Review decision - Approved: {decision.approved}")

        if decision.approved:
            # Emit approved response to external consumer (user)
            print(f"[ReviewerAgent] Emitting approved response to user")
            logger.info(f"[ReviewerAgent] Emitting approved response to user")
            
            contents: list[Contents] = []
            for message in request.primary_agent_response:
                contents.extend(message.contents)

            await ctx.add_event(
                AgentRunUpdateEvent(self.id, data=AgentRunResponseUpdate(contents=contents, role=Role.ASSISTANT))
            )
        else:
            # Send feedback back to PrimaryAgent for refinement
            print(f"[ReviewerAgent] Sending feedback to PrimaryAgent for refinement")
            logger.info(f"[ReviewerAgent] Sending feedback to PrimaryAgent for refinement")

        # Always send review response back to enable loop continuation
        await ctx.send_message(
            ReviewResponse(
                request_id=request.request_id,
                approved=decision.approved,
                feedback=decision.feedback,
            )
        )


class Agent(BaseAgent):
    """
    Workflow-based Reflection Agent implementation.
    
    Implements a 3-party communication pattern:
    User -> PrimaryAgent -> ReviewerAgent -> User (if approved) OR back to PrimaryAgent (if not)
    
    Conversation history is maintained between user and PrimaryAgent only.
    Both agents receive history for context.
    """

    def __init__(self, state_store: Dict[str, Any], session_id: str, access_token: str | None = None) -> None:
        super().__init__(state_store, session_id)
        self._workflow = None
        self._initialized = False
        self._access_token = access_token
        self._ws_manager = None
        self._mcp_tool = None  # Store connected MCP tool
        
        # Track conversation history as ChatMessage objects
        self._conversation_history: list[ChatMessage] = []
        self._load_conversation_history()
        
        print(f"WORKFLOW REFLECTION AGENT INITIALIZED - Session: {session_id}")
        logger.info(f"WORKFLOW REFLECTION AGENT INITIALIZED - Session: {session_id}")

    def _load_conversation_history(self) -> None:
        """Load conversation history from state store and convert to ChatMessage format."""
        chat_history = self.chat_history  # From BaseAgent
        for msg in chat_history:
            role = Role.USER if msg.get("role") == "user" else Role.ASSISTANT
            text = msg.get("content", "")
            self._conversation_history.append(ChatMessage(role=role, text=text))
        
        logger.info(f"Loaded {len(self._conversation_history)} messages from history")

    def set_websocket_manager(self, manager: Any) -> None:
        """Allow backend to inject WebSocket manager for streaming events."""
        self._ws_manager = manager
        logger.info(f"[STREAMING] WebSocket manager set for workflow reflection agent, session_id={self.session_id}")

    async def _setup_workflow(self) -> None:
        """Initialize the workflow with PrimaryAgent and ReviewerAgent executors."""
        if self._initialized:
            return

        if not all([self.azure_openai_key, self.azure_deployment, self.azure_openai_endpoint, self.api_version]):
            raise RuntimeError(
                "Azure OpenAI configuration is incomplete. Ensure AZURE_OPENAI_API_KEY, "
                "AZURE_OPENAI_CHAT_DEPLOYMENT, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_API_VERSION are set."
            )

        print(f"[WORKFLOW] Setting up workflow agents...")
        logger.info(f"[WORKFLOW] Setting up workflow agents")

        # Setup MCP tools if configured (create only once)
        if not self._mcp_tool:
            headers = self._build_headers()
            mcp_tools = await self._maybe_create_tools(headers)
            self._mcp_tool = mcp_tools[0] if mcp_tools else None
            
            if self._mcp_tool:
                print(f"[WORKFLOW] MCP tool created (will connect on first use)")
                logger.info(f"[WORKFLOW] MCP tool created")

        # Create Azure OpenAI chat client
        chat_client = AzureOpenAIChatClient(
            api_key=self.azure_openai_key,
            deployment_name=self.azure_deployment,
            endpoint=self.azure_openai_endpoint,
            api_version=self.api_version,
        )

        # Create executors
        primary_agent = PrimaryAgentExecutor(
            id="primary_agent",
            chat_client=chat_client,
            tools=self._mcp_tool,
            model=self.openai_model_name,
        )

        reviewer_agent = ReviewerAgentExecutor(
            id="reviewer_agent",
            chat_client=chat_client,
            tools=self._mcp_tool,
            model=self.openai_model_name,
        )

        print(f"[WORKFLOW] Building workflow graph: PrimaryAgent <-> ReviewerAgent")
        logger.info(f"[WORKFLOW] Building workflow graph")

        # Build workflow with bidirectional edges
        self._workflow = (
            WorkflowBuilder()
            .add_edge(primary_agent, reviewer_agent)  # Primary -> Reviewer
            .add_edge(reviewer_agent, primary_agent)  # Reviewer -> Primary (for feedback)
            .set_start_executor(primary_agent)
            .build()
        )

        self._initialized = True
        print(f"[WORKFLOW] Workflow initialization complete")
        logger.info(f"[WORKFLOW] Workflow initialization complete")

    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers for MCP tool requests."""
        headers = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    async def _maybe_create_tools(self, headers: Dict[str, str]) -> List[MCPStreamableHTTPTool] | None:
        """Create MCP tools if server URI is configured."""
        if not self.mcp_server_uri:
            logger.warning("MCP_SERVER_URI not configured; agents run without MCP tools.")
            return None
        
        print(f"[WORKFLOW] Creating MCP tools with server: {self.mcp_server_uri}")
        return [
            MCPStreamableHTTPTool(
                name="mcp-streamable",
                url=self.mcp_server_uri,
                headers=headers,
                timeout=30,
                request_timeout=30,
            )
        ]

    async def chat_async(self, prompt: str) -> str:
        """
        Process user prompt through the reflection workflow.
        
        Flow:
        1. Create PrimaryAgentRequest with conversation history
        2. PrimaryAgent generates response
        3. ReviewerAgent evaluates response
        4. If approved -> return to user
        5. If not approved -> PrimaryAgent refines with feedback (loop continues)
        """
        print(f"WORKFLOW REFLECTION AGENT chat_async called with prompt: {prompt[:50]}...")
        logger.info(f"WORKFLOW REFLECTION AGENT chat_async called with prompt: {prompt[:50]}...")

        await self._setup_workflow()
        if not self._workflow:
            raise RuntimeError("Workflow not initialized correctly.")

        # Create request with conversation history
        request_id = str(uuid4())
        request = PrimaryAgentRequest(
            request_id=request_id,
            user_prompt=prompt,
            conversation_history=self._conversation_history.copy(),
        )

        print(f"[WORKFLOW] Starting workflow execution (Request ID: {request_id[:8]})")
        logger.info(f"[WORKFLOW] Starting workflow execution")

        # Run workflow (streaming or non-streaming based on ws_manager)
        if self._ws_manager:
            print(f"[WORKFLOW] Using STREAMING mode")
            logger.info(f"[WORKFLOW] Using STREAMING mode")
            response_text = await self._run_workflow_streaming(request)
        else:
            print(f"[WORKFLOW] Using NON-STREAMING mode")
            logger.info(f"[WORKFLOW] Using NON-STREAMING mode")
            response_text = await self._run_workflow(request)

        # Update conversation history
        self._conversation_history.append(ChatMessage(role=Role.USER, text=prompt))
        self._conversation_history.append(ChatMessage(role=Role.ASSISTANT, text=response_text))

        # Update chat history in base class format
        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response_text},
        ]
        self.append_to_chat_history(messages)

        print(f"[WORKFLOW] Workflow execution complete")
        logger.info(f"[WORKFLOW] Workflow execution complete")

        return response_text

    async def _run_workflow(self, request: PrimaryAgentRequest) -> str:
        """Run workflow in non-streaming mode."""
        # Run the workflow directly with the custom request
        response = await self._workflow.run(request)
        
        # Extract text from the workflow result
        response_text = response.output if hasattr(response, 'output') else str(response)
        
        print(f"[WORKFLOW] Response received: {response_text[:100]}...")
        logger.info(f"[WORKFLOW] Response received")
        
        return response_text

    async def _run_workflow_streaming(self, request: PrimaryAgentRequest) -> str:
        """Run workflow in streaming mode with WebSocket updates."""
        
        # Notify UI that workflow is starting
        if self._ws_manager:
            await self._ws_manager.broadcast(
                self.session_id,
                {
                    "type": "orchestrator",
                    "kind": "plan",
                    "content": "Workflow Reflection Pattern Starting\n\nInitiating PrimaryAgent → ReviewerAgent workflow for quality-assured responses...",
                },
            )

        response_text = ""
        
        try:
            async for event in self._workflow.run_stream(request):
                # Handle different event types
                event_str = str(event)
                print(f"[WORKFLOW STREAM] Event: {event_str[:100]}...")
                
                # Check if this is an AgentRunUpdateEvent with approved response
                if isinstance(event, AgentRunUpdateEvent):
                    print(f"[WORKFLOW STREAM] AgentRunUpdateEvent detected from {event.executor_id}")
                    
                    # Extract response from the event data
                    if hasattr(event, 'data') and isinstance(event.data, AgentRunResponseUpdate):
                        # Extract text from contents
                        for content in event.data.contents:
                            if hasattr(content, 'text') and content.text:
                                response_text += content.text
                                
                                # Stream to WebSocket
                                if self._ws_manager:
                                    await self._ws_manager.broadcast(
                                        self.session_id,
                                        {
                                            "type": "agent_token",
                                            "agent_id": "workflow_reflection",
                                            "content": content.text,
                                        },
                                    )
                                    
                        print(f"[WORKFLOW STREAM] Extracted response text: {response_text[:100]}...")
                
                # Also check for text attribute directly on event
                elif hasattr(event, 'text') and event.text:
                    response_text += event.text
                    
                    # Stream to WebSocket
                    if self._ws_manager:
                        await self._ws_manager.broadcast(
                            self.session_id,
                            {
                                "type": "agent_token",
                                "agent_id": "workflow_reflection",
                                "content": event.text,
                            },
                        )
                
                # Check for messages attribute
                elif hasattr(event, 'messages'):
                    for msg in event.messages:
                        if hasattr(msg, 'text') and msg.text:
                            response_text = msg.text

            # Send final result
            if self._ws_manager and response_text:
                await self._ws_manager.broadcast(
                    self.session_id,
                    {
                        "type": "final_result",
                        "content": response_text,
                    },
                )
                
                await self._ws_manager.broadcast(
                    self.session_id,
                    {
                        "type": "orchestrator",
                        "kind": "result",
                        "content": "Workflow Complete\n\nQuality-assured response delivered through PrimaryAgent → ReviewerAgent workflow!",
                    },
                )

        except Exception as exc:
            logger.error(f"[WORKFLOW] Error during streaming: {exc}", exc_info=True)
            raise

        print(f"[WORKFLOW STREAM] Complete. Response length: {len(response_text)}")
        logger.info(f"[WORKFLOW STREAM] Complete")
        
        return response_text
