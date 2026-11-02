import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from app import main, tools
from app.auth import AuthenticatedUser, PineconeConnection
from fastapi import HTTPException
from fastapi.testclient import TestClient

USER = AuthenticatedUser("u1", PineconeConnection("idx", "key", None))


def _call(name, user=None, arguments=None):
    state = SimpleNamespace() if user is None else SimpleNamespace(user_info=user)
    ctx = SimpleNamespace(request=SimpleNamespace(state=state))
    req = SimpleNamespace(name=name, arguments=arguments)
    return asyncio.run(main.handle_call_tool(ctx, req))


@pytest.fixture
def backends():
    """Fake Supabase and Pinecone so a read_context call can run end to end."""
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = SimpleNamespace(
        data=[{"pinecone_namespace": "ns"}]
    )
    with (
        patch.object(tools, "get_supabase", return_value=sb),
        patch.object(tools, "Pinecone") as pinecone_cls,
    ):
        pc = pinecone_cls.return_value
        pc.inference.embed.return_value = [SimpleNamespace(values=[0.1])]
        pc.index.return_value.query.return_value = SimpleNamespace(
            matches=[SimpleNamespace(metadata={"content": "hello"}, score=0.9)]
        )
        yield


def test_list_tools_exposes_both_tools():
    result = asyncio.run(main.handle_list_tools(None, None))
    assert [tool.name for tool in result.tools] == ["read_context", "write_context"]


def test_call_tool_requires_authenticated_user():
    result = _call("read_context")
    assert result.is_error
    assert result.content[0].text == "Error: Could not retrieve authentication state"


def test_call_tool_rejects_unknown_tool():
    result = _call("nope", user=USER)
    assert result.is_error
    assert result.content[0].text == "Unknown tool: nope"


def test_call_tool_tolerates_missing_arguments():
    result = _call("read_context", user=USER, arguments=None)
    assert result.is_error
    assert result.content[0].text == "Error: chat is required"


def test_call_tool_returns_handler_output(backends):
    result = _call("read_context", user=USER, arguments={"chat": "c", "query": "q"})
    assert not result.is_error
    assert result.content[0].text.startswith("Context Search Results:")


def test_messages_endpoint_returns_real_auth_status():
    failure = HTTPException(status_code=403, detail="MCP connection is not active")
    with patch.object(main, "authenticate_mcp_client", side_effect=failure):
        response = TestClient(main.app).post("/mcp/messages", json={})

    assert response.status_code == 403
    assert response.text == "MCP connection is not active"


def test_sse_endpoint_rejects_unauthenticated_requests():
    failure = HTTPException(
        status_code=401, detail="Missing or invalid authentication token"
    )
    with patch.object(main, "authenticate_mcp_client", side_effect=failure):
        response = TestClient(main.app).get("/mcp/sse")

    assert response.status_code == 401


def test_health_does_not_require_auth():
    assert TestClient(main.app).get("/health").json() == {"status": "ok"}
