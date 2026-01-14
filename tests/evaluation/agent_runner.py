"""
Generic Agent Evaluation Runner

This module provides a consistent interface for evaluating ANY agent implementation.
It works with any agent that follows the standard BaseAgent pattern:
1. Inherits from BaseAgent
2. Implements set_websocket_manager(manager)
3. Implements chat_async(prompt) -> str
4. Broadcasts events via _ws_manager.broadcast()

Usage:
    from agent_runner import AgentTestRunner, ToolCallTracker
    
    # Load any agent by module path
    runner = AgentTestRunner("agents.agent_framework.single_agent")
    
    # Run with tool tracking
    result = await runner.run_query("What is customer 251's balance?")
    print(result.response)
    print(result.tool_calls)
"""

import asyncio
import importlib
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# ═══════════════════════════════════════════════════════════════════════════════
# PATH SETUP
# ═══════════════════════════════════════════════════════════════════════════════

_eval_dir = Path(__file__).parent.resolve()
_tests_dir = _eval_dir.parent
_workspace_root = _tests_dir.parent
_agentic_ai_dir = _workspace_root / "agentic_ai"

sys.path.insert(0, str(_agentic_ai_dir))
sys.path.insert(0, str(_tests_dir))

load_dotenv(_eval_dir / ".env")


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL CALL TRACKER
# ═══════════════════════════════════════════════════════════════════════════════


class ToolCallTracker:
    """
    Captures agent events by implementing the WebSocket manager interface.
    
    All agents in this codebase follow a consistent pattern:
    1. Inherit from BaseAgent
    2. Override set_websocket_manager(manager) to store the manager
    3. Call self._ws_manager.broadcast(session_id, message) for events
    
    This tracker captures those events, providing a consistent testing interface
    for ANY agent implementation (current and future).
    
    Standard Event Types:
        - tool_called: {type: "tool_called", tool_name: str, agent_id: str}
        - agent_start: {type: "agent_start", agent_id: str, agent_name: str}
        - agent_token: {type: "agent_token", agent_id: str, content: str}
        - final_result: {type: "final_result", content: str}
    """
    
    def __init__(self):
        self.events: list[dict] = []
        self.tool_calls: list[str] = []
        self.agent_transitions: list[str] = []  # For multi-agent tracking
    
    async def broadcast(self, session_id: str, message: dict) -> None:
        """Capture broadcast messages (implements WebSocket manager interface)."""
        self.events.append({"session_id": session_id, "timestamp": time.time(), **message})
        
        msg_type = message.get("type", "")
        
        if msg_type == "tool_called":
            tool_name = message.get("tool_name", "")
            if tool_name:
                self.tool_calls.append(tool_name)
        
        if msg_type == "agent_start":
            agent_id = message.get("agent_id", "unknown")
            self.agent_transitions.append(agent_id)
    
    def get_tool_calls(self) -> list[str]:
        """Get list of tools called in order."""
        return self.tool_calls.copy()
    
    def get_unique_tools(self) -> set[str]:
        """Get unique set of tools called."""
        return set(self.tool_calls)
    
    def get_agent_transitions(self) -> list[str]:
        """Get agent transitions (for multi-agent evaluation)."""
        return self.agent_transitions.copy()
    
    def get_events_by_type(self, event_type: str) -> list[dict]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.get("type") == event_type]
    
    def reset(self):
        """Reset tracker for new conversation turn."""
        self.events.clear()
        self.tool_calls.clear()
        self.agent_transitions.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# QUERY RESULT
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class QueryResult:
    """Result from running a query against an agent."""
    
    query: str
    response: str
    tool_calls: list[str] = field(default_factory=list)
    agent_transitions: list[str] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    execution_time: float = 0.0
    error: str | None = None
    
    @property
    def success(self) -> bool:
        return self.error is None and bool(self.response)
    
    @property
    def unique_tools(self) -> set[str]:
        return set(self.tool_calls)


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT TEST RUNNER
# ═══════════════════════════════════════════════════════════════════════════════


class AgentTestRunner:
    """
    Generic test runner for any agent implementation.
    
    Works with any agent that:
    1. Has an Agent class in the module
    2. Agent.__init__(state_store, session_id, ...) 
    3. Agent.set_websocket_manager(manager)
    4. Agent.chat_async(prompt) -> str
    
    Example:
        runner = AgentTestRunner("agents.agent_framework.single_agent")
        result = await runner.run_query("Hello")
        print(result.tool_calls)
    """
    
    # Known agent modules for convenience
    KNOWN_AGENTS = {
        "single": "agents.agent_framework.single_agent",
        "reflection": "agents.agent_framework.multi_agent.reflection_agent",
        "handoff": "agents.agent_framework.multi_agent.handoff_multi_domain_agent",
        "magentic": "agents.agent_framework.multi_agent.magentic_group",
    }
    
    def __init__(self, agent_module: str):
        """
        Initialize runner with an agent module path.
        
        Args:
            agent_module: Full module path (e.g., "agents.agent_framework.single_agent")
                         or shorthand ("single", "reflection", "handoff", "magentic")
        """
        # Resolve shorthand names
        self.agent_module = self.KNOWN_AGENTS.get(agent_module, agent_module)
        self._agent_class = None
        self._tracker = ToolCallTracker()
        self._session_counter = 0
    
    def _load_agent_class(self):
        """Dynamically load the Agent class from the module."""
        if self._agent_class is None:
            module = importlib.import_module(self.agent_module)
            self._agent_class = getattr(module, "Agent")
        return self._agent_class
    
    def _create_agent(self, session_id: str | None = None) -> Any:
        """Create a new agent instance with fresh state."""
        AgentClass = self._load_agent_class()
        
        if session_id is None:
            self._session_counter += 1
            session_id = f"eval_{self._session_counter}_{int(time.time() * 1000)}"
        
        state_store: dict[str, Any] = {}
        agent = AgentClass(state_store=state_store, session_id=session_id)
        agent.set_websocket_manager(self._tracker)
        
        return agent
    
    async def run_query(
        self,
        query: str,
        session_id: str | None = None,
        reset_tracker: bool = True,
    ) -> QueryResult:
        """
        Run a single query against the agent.
        
        Args:
            query: User query to send
            session_id: Optional session ID (auto-generated if not provided)
            reset_tracker: Whether to reset the tracker before running
            
        Returns:
            QueryResult with response, tool calls, and events
        """
        if reset_tracker:
            self._tracker.reset()
        
        agent = self._create_agent(session_id)
        start_time = time.time()
        
        try:
            response = await agent.chat_async(query)
            
            return QueryResult(
                query=query,
                response=response,
                tool_calls=self._tracker.get_tool_calls(),
                agent_transitions=self._tracker.get_agent_transitions(),
                events=self._tracker.events.copy(),
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            return QueryResult(
                query=query,
                response="",
                tool_calls=self._tracker.get_tool_calls(),
                agent_transitions=self._tracker.get_agent_transitions(),
                events=self._tracker.events.copy(),
                execution_time=time.time() - start_time,
                error=str(e),
            )
    
    async def run_conversation(
        self,
        queries: list[str],
        session_id: str | None = None,
    ) -> list[QueryResult]:
        """
        Run a multi-turn conversation with the same agent instance.
        
        Args:
            queries: List of user queries in order
            session_id: Session ID for conversation continuity
            
        Returns:
            List of QueryResult, one per turn
        """
        if session_id is None:
            self._session_counter += 1
            session_id = f"conv_{self._session_counter}_{int(time.time() * 1000)}"
        
        agent = self._create_agent(session_id)
        results = []
        
        for query in queries:
            self._tracker.reset()  # Reset per turn
            start_time = time.time()
            
            try:
                response = await agent.chat_async(query)
                
                results.append(QueryResult(
                    query=query,
                    response=response,
                    tool_calls=self._tracker.get_tool_calls(),
                    agent_transitions=self._tracker.get_agent_transitions(),
                    events=self._tracker.events.copy(),
                    execution_time=time.time() - start_time,
                ))
            except Exception as e:
                results.append(QueryResult(
                    query=query,
                    response="",
                    tool_calls=self._tracker.get_tool_calls(),
                    agent_transitions=self._tracker.get_agent_transitions(),
                    events=self._tracker.events.copy(),
                    execution_time=time.time() - start_time,
                    error=str(e),
                ))
        
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def list_available_agents() -> dict[str, str]:
    """List known agent shorthand names and their module paths."""
    return AgentTestRunner.KNOWN_AGENTS.copy()


async def compare_agents(
    query: str,
    agent_modules: list[str] | None = None,
) -> dict[str, QueryResult]:
    """
    Run the same query against multiple agents and compare results.
    
    Args:
        query: Query to run
        agent_modules: List of agent modules (defaults to all known agents)
        
    Returns:
        Dict mapping agent name to QueryResult
    """
    if agent_modules is None:
        agent_modules = ["single", "reflection"]
    
    results = {}
    for agent_name in agent_modules:
        runner = AgentTestRunner(agent_name)
        result = await runner.run_query(query)
        results[agent_name] = result
        
        status = "✅" if result.success else "❌"
        print(f"{status} {agent_name}: {result.execution_time:.1f}s, "
              f"tools={len(result.tool_calls)}")
    
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE DEMO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import logging
    import warnings
    
    # Suppress MCP client cleanup warnings (they don't affect results)
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    async def demo():
        print("Agent Test Runner Demo")
        print("=" * 50)
        
        # Show available agents
        print("\nAvailable agents:")
        for name, module in list_available_agents().items():
            print(f"  {name}: {module}")
        
        # Run a simple comparison
        print("\nComparing agents on a simple query...")
        query = "Hi, I'm customer 251. Can you tell me about my account?"
        
        results = await compare_agents(query, ["single", "reflection"])
        
        print("\n" + "-" * 50)
        for name, result in results.items():
            print(f"\n{name}:")
            print(f"  Response: {result.response[:150]}...")
            print(f"  Tools: {result.tool_calls}")
            print(f"  Time: {result.execution_time:.1f}s")
    
    asyncio.run(demo())
