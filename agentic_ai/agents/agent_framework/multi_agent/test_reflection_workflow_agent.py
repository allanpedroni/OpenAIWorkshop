"""
Test script for the Workflow-based Reflection Agent

This script demonstrates the 3-party communication pattern:
User -> PrimaryAgent -> ReviewerAgent -> User (if approved) OR back to PrimaryAgent (if not)

Usage:
    python test_reflection_workflow_agent.py
"""

import asyncio
import logging
import os
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_workflow_reflection_agent():
    """Test the workflow-based reflection agent."""
    
    print("=" * 70)
    print("WORKFLOW REFLECTION AGENT TEST")
    print("=" * 70)
    print()
    
    # Check environment variables
    required_env_vars = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_CHAT_DEPLOYMENT",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION",
        "OPENAI_MODEL_NAME",
    ]
    
    print("Checking environment variables...")
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("\nPlease set the following environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        return
    
    print("✓ All required environment variables are set")
    print()
    
    # Optional MCP server
    mcp_uri = os.getenv("MCP_SERVER_URI")
    if mcp_uri:
        print(f"✓ MCP Server configured: {mcp_uri}")
    else:
        print("ℹ MCP Server not configured (agents will work without MCP tools)")
    print()
    
    # Import the agent (after env check to avoid import errors)
    try:
        from agentic_ai.agents.agent_framework.multi_agent.reflection_workflow_agent import Agent
    except ImportError as e:
        print(f"❌ Failed to import Agent: {e}")
        print("\nMake sure you're running from the project root directory:")
        print("  python agentic_ai/agents/agent_framework/multi_agent/test_reflection_workflow_agent.py")
        return
    
    # Create state store and agent
    state_store: Dict[str, Any] = {}
    session_id = "test_session_001"
    
    print(f"Creating Workflow Reflection Agent (Session: {session_id})...")
    agent = Agent(state_store=state_store, session_id=session_id)
    print("✓ Agent created successfully")
    print()
    
    # Test queries
    test_queries = [
        "What is the capital of France?",
        "Can you help me with customer ID 1?",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print("=" * 70)
        print(f"TEST QUERY {i}: {query}")
        print("=" * 70)
        print()
        
        try:
            print(f"Sending query to agent...")
            print(f"Expected flow: User -> PrimaryAgent -> ReviewerAgent -> (approve/reject)")
            print()
            
            response = await agent.chat_async(query)
            
            print()
            print("-" * 70)
            print("FINAL RESPONSE:")
            print("-" * 70)
            print(response)
            print()
            
            print("✓ Query completed successfully")
            print()
            
        except Exception as e:
            print(f"❌ Error during query: {e}")
            logger.error(f"Error during query: {e}", exc_info=True)
            print()
    
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"- Total queries tested: {len(test_queries)}")
    print(f"- Session ID: {session_id}")
    print(f"- Conversation history entries: {len(state_store.get(f'{session_id}_chat_history', []))}")
    print()
    print("Key features demonstrated:")
    print("  ✓ 3-party communication pattern (User -> PrimaryAgent -> ReviewerAgent)")
    print("  ✓ Conditional gate (approve/reject)")
    print("  ✓ Conversation history maintenance")
    print("  ✓ Iterative refinement loop")
    print()


async def test_with_mcp_tools():
    """Test with actual MCP tools if configured."""
    
    print("=" * 70)
    print("WORKFLOW REFLECTION AGENT TEST WITH MCP TOOLS")
    print("=" * 70)
    print()
    
    if not os.getenv("MCP_SERVER_URI"):
        print("⚠ MCP_SERVER_URI not configured. Skipping MCP test.")
        print("To test with MCP tools, set the MCP_SERVER_URI environment variable.")
        return
    
    # Import the agent
    try:
        from agentic_ai.agents.agent_framework.multi_agent.reflection_workflow_agent import Agent
    except ImportError as e:
        print(f"❌ Failed to import Agent: {e}")
        return
    
    # Create state store and agent
    state_store: Dict[str, Any] = {}
    session_id = "test_session_mcp_001"
    
    print(f"Creating Workflow Reflection Agent with MCP tools (Session: {session_id})...")
    agent = Agent(state_store=state_store, session_id=session_id)
    print("✓ Agent created successfully")
    print()
    
    # Test MCP-specific queries
    mcp_queries = [
        "Can you list all customers?",
        "What are the billing details for customer ID 1?",
        "What promotions are available for customer 1?",
    ]
    
    for i, query in enumerate(mcp_queries, 1):
        print("=" * 70)
        print(f"MCP TEST QUERY {i}: {query}")
        print("=" * 70)
        print()
        
        try:
            print(f"Sending query to agent (expects MCP tool usage)...")
            print(f"Expected: PrimaryAgent will use MCP tools, ReviewerAgent will verify accuracy")
            print()
            
            response = await agent.chat_async(query)
            
            print()
            print("-" * 70)
            print("FINAL RESPONSE:")
            print("-" * 70)
            print(response)
            print()
            
            print("✓ MCP query completed successfully")
            print()
            
        except Exception as e:
            print(f"❌ Error during MCP query: {e}")
            logger.error(f"Error during MCP query: {e}", exc_info=True)
            print()
    
    print("=" * 70)
    print("MCP TEST COMPLETE")
    print("=" * 70)


def main():
    """Main entry point."""
    print()
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║     WORKFLOW-BASED REFLECTION AGENT TEST SUITE                   ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print()
    
    # Run basic test
    asyncio.run(test_workflow_reflection_agent())
    
    print()
    print("-" * 70)
    print()
    
    # Run MCP test if configured
    asyncio.run(test_with_mcp_tools())
    
    print()
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║     ALL TESTS COMPLETE                                            ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print()


if __name__ == "__main__":
    main()
