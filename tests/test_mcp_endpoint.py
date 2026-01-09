import json
import os
import asyncio

import pytest
import pytest_asyncio

from mcp import ClientSession
# streamable-http transport :contentReference[oaicite:2]{index=2}
from mcp.client.streamable_http import streamable_http_client

pytestmark = pytest.mark.integration

# Retry settings for cold-start scenarios
MAX_RETRIES = 3
RETRY_DELAY = 15


@pytest.fixture(scope="session")
def mcp_url() -> str:
    url = os.getenv("MCP_ENDPOINT")
    if not url:
        pytest.skip("MCP_ENDPOINT not set")
    
    # Skip if MCP is internal-only (not reachable from GitHub Actions)
    if os.getenv("MCP_INTERNAL_ONLY", "false").lower() == "true":
        pytest.skip("MCP is internal-only, skipping external connectivity test")

    url = f'{url.rstrip("/")}/mcp'
    return url  # normalize


@pytest.fixture
def anyio_backend():
    return "asyncio"   # ensures AnyIO uses asyncio backend


@pytest.mark.anyio
async def test_remote_list_tools(mcp_url):
    """Test MCP endpoint with retry logic for cold-start scenarios."""
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            async with streamable_http_client(mcp_url) as transport:
                read, write, *_ = transport
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    res = await session.list_tools()
                    tools = getattr(res, "tools", res)
                    assert tools, "Expected at least one tool"
                    return  # Success!
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {RETRY_DELAY}s...")
                await asyncio.sleep(RETRY_DELAY)
    
    # All retries failed
    raise last_error
