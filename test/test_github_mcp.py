import json
import os

import pytest
from fastmcp import Client
from fastmcp.client import StreamableHttpTransport, ClientTransport
from mcp import McpError
from mcp.types import Tool

GITHUB_REMOTE_MCP_URL = "https://api.githubcopilot.com/mcp/"

HEADER_AUTHORIZATION = "Authorization"
MCP_GITHUB_PAT = os.getenv("MCP_GITHUB_PAT")


# https://docs.github.com/en/copilot/customizing-copilot/using-model-context-protocol/using-the-github-mcp-server

@pytest.fixture(name="streamable_http_client", autouse=True)
def fixture_streamable_http_client() -> Client[ClientTransport]:
    return Client(
        StreamableHttpTransport(url=GITHUB_REMOTE_MCP_URL,
                                headers={HEADER_AUTHORIZATION: f"Bearer {MCP_GITHUB_PAT}"}
                                )
    )

    # https://docs.github.com/en/copilot/customizing-copilot/using-model-context-protocol/using-the-github-mcp-server


@pytest.mark.asyncio
async def test_connect_disconnect(streamable_http_client: Client[StreamableHttpTransport]):
    async with streamable_http_client:
        assert streamable_http_client.is_connected() is True
        await streamable_http_client._disconnect()  # pylint: disable=W0212 (protected-access)
        assert streamable_http_client.is_connected() is False


@pytest.mark.asyncio
async def test_ping(streamable_http_client: Client[StreamableHttpTransport]):
    """Test pinging the server."""
    async with streamable_http_client:
        assert streamable_http_client.is_connected() is True
        result = await streamable_http_client.ping()
        assert result is True


@pytest.mark.asyncio
async def test_list_tools(streamable_http_client: Client[StreamableHttpTransport]):
    """Test listing the MCP tools"""
    async with streamable_http_client:
        assert streamable_http_client.is_connected()
        tools = await streamable_http_client.list_tools()
        assert isinstance(tools, list)
        assert len(tools) >= 40
        for tool in tools:
            assert isinstance(tool, Tool)
            assert len(tool.name) > 0
            assert len(tool.description) > 0
            assert isinstance(tool.inputSchema, dict)
            assert len(tool.inputSchema) > 0


@pytest.mark.asyncio
async def test_list_resources(streamable_http_client: Client[StreamableHttpTransport]):
    """Test listing the MCP resources """
    async with streamable_http_client:
        assert streamable_http_client.is_connected()
        resources = await streamable_http_client.list_resources()
        assert isinstance(resources, list)
        assert len(resources) == 0


@pytest.mark.asyncio
async def test_list_prompts(streamable_http_client: Client[StreamableHttpTransport]):
    """Test listing the MCP prompts """
    async with streamable_http_client:
        assert streamable_http_client.is_connected()
        try:
            await streamable_http_client.list_prompts()
        except McpError as e:
            assert e.args[0] == "prompts not supported"


@pytest.mark.asyncio
async def test_call_tool_ko(streamable_http_client: Client[StreamableHttpTransport]):
    """Test calling a non-existing tool"""
    async with streamable_http_client:
        assert streamable_http_client.is_connected()
        try:
            await streamable_http_client.call_tool("foo")
        except McpError as e:
            assert "tool not found" in e.args[0]


@pytest.mark.asyncio
async def test_call_tool_list_commits(streamable_http_client: Client[StreamableHttpTransport]):
    """Test calling a list_commit tool"""
    async with streamable_http_client:
        assert streamable_http_client.is_connected()
        result = await streamable_http_client.call_tool("list_commits",
                                                        {"owner": "didier-durand", "repo": "strands-serverless"})
        assert isinstance(result, list)
        assert len(result) == 1
        commits = json.loads(result[0].text)
        for commit in commits:
            assert isinstance(commit, dict)
            assert "sha" in commit
            assert "author" in commit
            assert "commit" in commit
            assert "author" in commit["commit"]
            assert len(commit["commit"]["author"]["date"]) > 0
            assert len(commit["commit"]["author"]["name"]) > 0
            assert len(commit["commit"]["author"]["email"]) > 0
