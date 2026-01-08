"""
Reflection Agent - Primary Agent + Reviewer pattern with optional streaming.

This agent implements a quality assurance workflow:
1. Primary Agent generates a response using MCP tools
2. Reviewer evaluates the response for accuracy and completeness
3. If not approved, Primary Agent refines based on feedback (up to max_refinements)
"""

import logging
from typing import Any, Dict, List

from agent_framework import AgentThread, ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Agent instructions
PRIMARY_AGENT_INSTRUCTIONS = """You are a helpful customer support assistant for Contoso company. 
You can help with billing, promotions, security, account information, and other customer inquiries.
Use the available MCP tools to look up customer information, billing details, promotions, and security settings.
When a customer provides an ID or asks about their account, use the tools to retrieve accurate, up-to-date information.
If the user input is just an ID or feels incomplete, infer intent from the conversation context.
Always be helpful, professional, and provide detailed information when available."""

REVIEWER_INSTRUCTIONS = """You are a quality assurance reviewer for customer support responses.
Review responses for: 1) Accuracy, 2) Completeness, 3) Professional tone, 4) Proper tool usage.
If the response meets quality standards, respond with exactly 'APPROVE'.
If improvements are needed, provide specific, constructive feedback."""

# Agent display names for UI
AGENT_NAMES = {
    "primary_agent": "Primary Agent",
    "reviewer_agent": "Quality Reviewer",
}


class Agent(BaseAgent):
    """Reflection Agent with Primary Agent + Reviewer workflow."""

    def __init__(
        self, 
        state_store: Dict[str, Any], 
        session_id: str, 
        access_token: str | None = None,
        max_refinements: int = 2,
    ) -> None:
        super().__init__(state_store, session_id)
        self._primary_agent: ChatAgent | None = None
        self._reviewer: ChatAgent | None = None
        self._thread: AgentThread | None = None
        self._initialized = False
        self._access_token = access_token
        self._ws_manager = None
        self._max_refinements = max_refinements
        logger.info(f"[Reflection] Initialized session: {session_id}")

    def set_websocket_manager(self, manager: Any) -> None:
        """Allow backend to inject WebSocket manager for streaming events."""
        self._ws_manager = manager

    async def _broadcast(self, kind: str, content: str, **extra: Any) -> None:
        """Send a message to the WebSocket if available."""
        if self._ws_manager:
            message = {"type": "orchestrator", "kind": kind, "content": content, **extra}
            await self._ws_manager.broadcast(self.session_id, message)

    async def _broadcast_raw(self, message: Dict[str, Any]) -> None:
        """Send a raw message to the WebSocket if available."""
        if self._ws_manager:
            await self._ws_manager.broadcast(self.session_id, message)

    async def _setup_agents(self) -> None:
        """Initialize Primary Agent and Reviewer with MCP tools."""
        if self._initialized:
            return

        # Validate configuration
        if not all([self.azure_deployment, self.azure_openai_endpoint, self.api_version]):
            raise RuntimeError("Azure OpenAI configuration incomplete.")
        
        if not self.azure_openai_key and not self.azure_credential:
            raise RuntimeError("Azure OpenAI authentication not configured.")

        # Create chat client
        client_kwargs = {
            "deployment_name": self.azure_deployment,
            "endpoint": self.azure_openai_endpoint,
            "api_version": self.api_version,
        }
        if self.azure_openai_key:
            client_kwargs["api_key"] = self.azure_openai_key
        else:
            client_kwargs["credential"] = self.azure_credential
        
        chat_client = AzureOpenAIChatClient(**client_kwargs)

        # Create MCP tools
        tools = await self._create_mcp_tools()

        # Create agents
        self._primary_agent = ChatAgent(
            name="PrimaryAgent",
            chat_client=chat_client,
            instructions=PRIMARY_AGENT_INSTRUCTIONS,
            tools=tools,
            model=self.openai_model_name,
        )

        self._reviewer = ChatAgent(
            name="Reviewer",
            chat_client=chat_client,
            instructions=REVIEWER_INSTRUCTIONS,
            tools=tools,
            model=self.openai_model_name,
        )

        # Initialize agents
        await self._primary_agent.__aenter__()
        await self._reviewer.__aenter__()

        # Load or create thread
        if self.state:
            self._thread = await self._primary_agent.deserialize_thread(self.state)
        else:
            self._thread = self._primary_agent.get_new_thread()

        self._initialized = True
        logger.info("[Reflection] Agents initialized")

    async def _create_mcp_tools(self) -> MCPStreamableHTTPTool | None:
        """Create MCP tools if configured."""
        if not self.mcp_server_uri:
            logger.warning("MCP_SERVER_URI not configured")
            return None
        
        headers = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        
        return MCPStreamableHTTPTool(
            name="mcp-streamable",
            url=self.mcp_server_uri,
            headers=headers,
            timeout=30,
            request_timeout=30,
        )

    async def _run_agent(
        self, 
        agent: ChatAgent, 
        prompt: str, 
        agent_id: str,
    ) -> str:
        """Run an agent with optional streaming."""
        if self._ws_manager:
            return await self._run_agent_streaming(agent, prompt, agent_id)
        else:
            result = await agent.run(prompt, thread=self._thread)
            return result.text

    async def _run_agent_streaming(
        self, 
        agent: ChatAgent, 
        prompt: str, 
        agent_id: str,
    ) -> str:
        """Run an agent with streaming to WebSocket."""
        # Notify UI that agent started with label
        await self._broadcast_raw({
            "type": "agent_start",
            "agent_id": agent_id,
            "agent_name": AGENT_NAMES.get(agent_id, agent_id),
            "show_message_in_internal_process": True,
        })
        
        chunks: List[str] = []
        
        async for chunk in agent.run_stream(prompt, thread=self._thread):
            # Handle tool calls
            if hasattr(chunk, 'contents') and chunk.contents:
                for content in chunk.contents:
                    if content.type == "function_call":
                        await self._broadcast_raw({
                            "type": "tool_called",
                            "agent_id": agent_id,
                            "tool_name": content.name,
                        })
            
            # Stream text
            if hasattr(chunk, 'text') and chunk.text:
                chunks.append(chunk.text)
                await self._broadcast_raw({
                    "type": "agent_token",
                    "agent_id": agent_id,
                    "content": chunk.text,
                })
        
        response = ''.join(chunks)
        
        # Send complete message
        await self._broadcast_raw({
            "type": "agent_message",
            "agent_id": agent_id,
            "role": "assistant",
            "content": response,
        })
        
        return response

    def _is_approved(self, review: str) -> bool:
        """Check if the reviewer approved the response."""
        return "APPROVE" in review.upper()

    async def chat_async(self, prompt: str) -> str:
        """Run the reflection workflow: Primary → Reviewer → Refine (if needed)."""
        logger.info(f"[Reflection] Processing: {prompt[:50]}...")
        
        await self._setup_agents()
        if not self._primary_agent or not self._reviewer or not self._thread:
            raise RuntimeError("Agents not initialized")

        # Notify start
        await self._broadcast("plan", "🔄 Reflection Workflow\n\nStarting Primary Agent → Reviewer pipeline...")

        # Step 1: Primary Agent generates response
        await self._broadcast("step", "🤖 **Primary Agent** analyzing request...")
        response = await self._run_agent(self._primary_agent, prompt, "primary_agent")
        logger.info(f"[Reflection] Primary response: {len(response)} chars")

        # Step 2: Reviewer evaluates
        await self._broadcast("step", "🔍 **Reviewer** evaluating response...")
        review_prompt = (
            f"Review this customer support response:\n\n"
            f"**Question:** {prompt}\n\n"
            f"**Response:** {response}"
        )
        review = await self._run_agent(self._reviewer, review_prompt, "reviewer_agent")
        logger.info(f"[Reflection] Review: approved={self._is_approved(review)}")

        # Step 3: Refine if needed (up to max_refinements)
        for attempt in range(self._max_refinements):
            if self._is_approved(review):
                await self._broadcast("step", "✅ **Reviewer** approved the response!")
                break
            
            await self._broadcast(
                "step", 
                f"🔄 **Primary Agent** refining response (attempt {attempt + 1}/{self._max_refinements})..."
            )
            
            refine_prompt = (
                f"Improve your response based on this feedback:\n\n"
                f"**Original Question:** {prompt}\n\n"
                f"**Your Response:** {response}\n\n"
                f"**Reviewer Feedback:** {review}\n\n"
                f"Provide only the improved response, no meta-commentary."
            )
            response = await self._run_agent(self._primary_agent, refine_prompt, "primary_agent")
            
            # Re-review if not last attempt
            if attempt < self._max_refinements - 1:
                review_prompt = (
                    f"Review this refined response:\n\n"
                    f"**Question:** {prompt}\n\n"
                    f"**Response:** {response}"
                )
                review = await self._run_agent(self._reviewer, review_prompt, "reviewer_agent")
                logger.info(f"[Reflection] Re-review: approved={self._is_approved(review)}")

        # Complete
        await self._broadcast("result", "✅ Reflection Complete\n\nFinal response delivered with quality assurance!")
        await self._broadcast_raw({"type": "final_result", "content": response})

        # Save state
        self.append_to_chat_history([
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response},
        ])
        self._setstate(await self._thread.serialize())

        return response
