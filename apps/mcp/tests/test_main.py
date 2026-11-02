import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from app import main, tools
from app.auth import AuthenticatedUser, PineconeConnection
from fastapi import HTTPException
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager


@pytest.fixture(autouse=True)
def fresh_streamable_http():
    main.streamable_http = StreamableHTTPSessionManager(main.server, json_response=True)
    yield main.streamable_http


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


def test_streamable_endpoint_returns_real_auth_status():
    failure = HTTPException(status_code=403, detail="MCP connection is not active")
    with patch.object(main, "authenticate_mcp_client", side_effect=failure):
        response = TestClient(main.app).post("/mcp", json={})

    assert response.status_code == 403
    assert response.text == "MCP connection is not active"


def test_streamable_endpoint_rejects_unauthenticated_requests():
    failure = HTTPException(
        status_code=401, detail="Missing or invalid authentication token"
    )
    with patch.object(main, "authenticate_mcp_client", side_effect=failure):
        response = TestClient(main.app).get("/mcp")

    assert response.status_code == 401


def test_health_does_not_require_auth():
    assert TestClient(main.app).get("/health").json() == {"status": "ok"}


def test_options_mcp_endpoint_does_not_require_auth():
    response = TestClient(main.app).options("/mcp")
    assert response.status_code == 204


def test_oauth_protected_resource_metadata_endpoints():
    test_settings = SimpleNamespace(
        mcp_resource_url="https://mcp.example.com/mcp",
        oauth_issuer_url="https://project.supabase.co/auth/v1",
    )
    with (
        patch.object(main, "settings", test_settings),
        patch("app.oauth.settings", test_settings),
    ):
        client = TestClient(main.app)
        # Both default well-known path and resource-specific path should succeed
        res1 = client.get("/.well-known/oauth-protected-resource")
        assert res1.status_code == 200
        assert "authorization_servers" in res1.json()

        res2 = client.get("/.well-known/oauth-protected-resource/mcp")
        assert res2.status_code == 200
        assert res2.json() == res1.json()

        # Unknown resource path returns 404
        res3 = client.get("/.well-known/oauth-protected-resource/unknown")
        assert res3.status_code == 404


@pytest.mark.anyio
async def test_streamable_http_lifecycle(backends):
    user = AuthenticatedUser(
        "u1", PineconeConnection("idx", "pc-key", None), client_id="client-1"
    )

    with (
        patch.object(main, "validate_settings"),
        patch.object(main, "authenticate_mcp_client", return_value=user),
    ):
        async with main.lifespan(main.app):
            transport = ASGITransport(app=main.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # 1. Initialize
                init_res = await client.post(
                    "/mcp",
                    headers={
                        "Authorization": "Bearer test-token",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "test-client", "version": "1.0"},
                        },
                    },
                )
                assert init_res.status_code == 200
                session_id = init_res.headers.get("mcp-session-id")
                assert session_id is not None
                init_data = init_res.json()
                assert init_data["result"]["protocolVersion"] == "2024-11-05"

                headers = {
                    "Authorization": "Bearer test-token",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "mcp-session-id": session_id,
                }

                # 2. Notification: initialized
                notif_res = await client.post(
                    "/mcp",
                    headers=headers,
                    json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                )
                assert notif_res.status_code == 202

                # 3. Call tool
                call_res = await client.post(
                    "/mcp",
                    headers=headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "read_context",
                            "arguments": {"chat": "test-chat", "query": "test-query"},
                        },
                    },
                )
                assert call_res.status_code == 200
                call_data = call_res.json()
                assert not call_data["result"]["isError"]
                assert call_data["result"]["content"][0]["text"].startswith("Context Search Results:")

                # 4. Cleanly delete session
                del_res = await client.delete(
                    "/mcp",
                    headers={
                        "Authorization": "Bearer test-token",
                        "mcp-session-id": session_id,
                    },
                )
                assert del_res.status_code == 200

                # 5. Subsequent request with deleted session ID returns 404
                after_res = await client.post(
                    "/mcp",
                    headers=headers,
                    json={"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
                )
                assert after_res.status_code == 404


@pytest.mark.anyio
async def test_streamable_http_session_isolation():
    user_a = AuthenticatedUser(
        "user-a", PineconeConnection("idx", "pc-key", None), client_id="client-a"
    )
    user_b = AuthenticatedUser(
        "user-b", PineconeConnection("idx", "pc-key", None), client_id="client-b"
    )

    current_user = user_a

    def auth_mock(req):
        return current_user

    with (
        patch.object(main, "validate_settings"),
        patch.object(main, "authenticate_mcp_client", side_effect=auth_mock),
    ):
        async with main.lifespan(main.app):
            transport = ASGITransport(app=main.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # User A creates session
                current_user = user_a
                init_res = await client.post(
                    "/mcp",
                    headers={
                        "Authorization": "Bearer token-a",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "test-client", "version": "1.0"},
                        },
                    },
                )
                assert init_res.status_code == 200
                session_id = init_res.headers.get("mcp-session-id")

                # User B attempts to access User A's session -> must be rejected with 404
                current_user = user_b
                b_res = await client.post(
                    "/mcp",
                    headers={
                        "Authorization": "Bearer token-b",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "mcp-session-id": session_id,
                    },
                    json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                )
                assert b_res.status_code == 404

