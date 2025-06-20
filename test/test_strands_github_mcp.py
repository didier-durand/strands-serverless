import os
from typing import Any

import httpx
import pytest
from httpx import AsyncClient, Request, Response
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.tools.mcp import MCPClient

from httpx_helpers import TracingTransport
from utils import on_github

REPO_OWNER = "strands-agents"
REPO_NAME = "python-sdk"

HTTPX_HOOKS: bool = True
GITHUB_REMOTE_MCP_URL = "https://api.githubcopilot.com/mcp/"

HEADER_AUTHORIZATION = "Authorization"
MCP_GITHUB_PAT = os.getenv("MCP_GITHUB_PAT")

TIMEOUT = 300

SYSTEM_PROMPT = "you are a helpful assistant"


# extension of mcp.shared._httpx_utils.create_mcp_http_client with Transport
def create_mcp_http_client_with_transport(
        headers: dict[str, str] | None = None,
        timeout: httpx.Timeout | None = None,
        auth: httpx.Auth | None = None,
        transport: httpx.AsyncBaseTransport | None = None
) -> httpx.AsyncClient:
    kwargs: dict[str, Any] = {
        "follow_redirects": True,
    }

    if timeout is None:
        kwargs["timeout"] = httpx.Timeout(30.0)
    else:
        kwargs["timeout"] = timeout

    if headers is not None:
        kwargs["headers"] = headers

    if auth is not None:
        kwargs["auth"] = auth

    if transport is not None:
        kwargs["transport"] = transport

    return httpx.AsyncClient(**kwargs)


@pytest.fixture(name="github_mcp_client", autouse=True)
def fixture_streamable_http_client() -> MCPClient:
    # for content: https://github.com/encode/httpx/discussions/3073
    kwargs = {
        "url": GITHUB_REMOTE_MCP_URL,
        "headers": {HEADER_AUTHORIZATION: f"Bearer {MCP_GITHUB_PAT}"},
        "timeout": TIMEOUT
    }
    if HTTPX_HOOKS:
        def create_mcp_http_client_with_hooks(**http_args) -> AsyncClient:
            async def log_request(request: Request):
                print(f"Request event hook: {request.method} - url: {request.url} - "
                      f"content: {request.content} - headers: {request.headers} - Waiting for response")

            async def log_response(response: Response):
                request = response.request
                print(f"Response event hook: {request.method} {request.url} - Status: {response.status_code}")

            http_args["transport"] = TracingTransport(httpx.AsyncHTTPTransport())
            client = create_mcp_http_client_with_transport(**http_args)
            client.event_hooks['request'] = [log_request]
            client.event_hooks['response'] = [log_response]
            return client

        kwargs["httpx_client_factory"] = create_mcp_http_client_with_hooks  # noqa

    def streamable_http_client():
        return streamablehttp_client(**kwargs)

    return MCPClient(streamable_http_client)


def test_github_list_tools(github_mcp_client):
    print()
    with github_mcp_client:
        tools = github_mcp_client.list_tools_sync()
    agent = Agent(system_prompt=SYSTEM_PROMPT, tools=tools)
    print(f"tool names: {agent.tool_names}")
    assert isinstance(agent.tool_names, list)
    assert len(agent.tool_names) > 40
    assert "create_issue" in agent.tool_names
    assert "delete_file" in agent.tool_names
    assert "list_commits" in agent.tool_names
    assert "get_commit" in agent.tool_names
    assert isinstance(agent.tool_config["tools"], list)
    print(f"tool names: {len(agent.tool_names)} - tool configs: {len(agent.tool_config['tools'])}")
    assert len(agent.tool_config["tools"]) == len(agent.tool_names)
    for tool in agent.tool_config["tools"]:
        assert tool["toolSpec"]["name"] in agent.tool_names


# https://modelcontextprotocol.io/specification/2025-06-18/changelog
# https://modelcontextprotocol.io/specification/2025-06-18/basic#meta

@pytest.mark.skipif(on_github(), reason="not working yet")
def test_github_list_commits(github_mcp_client):
    with github_mcp_client:
        tools = github_mcp_client.list_tools_sync()
        agent = Agent(system_prompt=SYSTEM_PROMPT, tools=tools)
        result = agent.tool.list_commits(owner=REPO_OWNER, repo=REPO_NAME)
    print(result)
    assert result['status'] != 'error'
