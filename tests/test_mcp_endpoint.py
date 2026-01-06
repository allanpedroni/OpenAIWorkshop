import json
import os

import pytest
import pytest_asyncio

from mcp import ClientSession
# streamable-http transport :contentReference[oaicite:2]{index=2}
from mcp.client.streamable_http import streamable_http_client

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def mcp_url() -> str:
    url = os.getenv("MCP_ENDPOINT")
    if not url:
        pytest.skip("MCP_ENDPOINT not set")

    url = f'{url.rstrip("/")}/mcp'
    return url  # normalize


@pytest.fixture
def anyio_backend():
    return "asyncio"   # ensures AnyIO uses asyncio backend


@pytest.mark.anyio
async def test_remote_list_tools(mcp_url):
    async with streamable_http_client(mcp_url) as transport:
        read, write, *_ = transport
        async with ClientSession(read, write) as session:
            await session.initialize()
            res = await session.list_tools()
            tools = getattr(res, "tools", res)
            assert tools, "Expected at least one tool"
