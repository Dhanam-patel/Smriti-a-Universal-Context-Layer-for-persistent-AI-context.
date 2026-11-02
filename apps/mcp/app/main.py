import asyncio
from contextlib import asynccontextmanager

import mcp.types as types
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from mcp.server import Server, ServerRequestContext
from mcp.server.auth.middleware.bearer_auth import (
    AuthenticatedUser as MCPAuthenticatedUser,
)
from mcp.server.auth.provider import AccessToken
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from .auth import AuthenticatedUser, authenticate_mcp_client
from .config import settings, validate_settings
from .oauth import protected_resource_metadata
from .tools import TOOL_DEFINITIONS, TOOL_HANDLERS, ToolError


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_settings(settings)
    async with streamable_http.run():
        yield


app = FastAPI(title="UCL MCP Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id", "Last-Event-ID", "WWW-Authenticate"],
)


def _text_result(text: str, *, is_error: bool = False) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=text)],
        is_error=is_error,
    )


async def handle_list_tools(
    ctx: ServerRequestContext, req: types.PaginatedRequestParams | None
) -> types.ListToolsResult:
    return types.ListToolsResult(tools=TOOL_DEFINITIONS)


async def handle_call_tool(
    ctx: ServerRequestContext, req: types.CallToolRequestParams
) -> types.CallToolResult | types.InputRequiredResult:
    # Both MCP endpoints store the authenticated user on request.state (see authenticate_request).
    user: AuthenticatedUser | None = getattr(ctx.request.state, "user_info", None)
    if user is None:
        return _text_result(
            "Error: Could not retrieve authentication state", is_error=True
        )

    handler = TOOL_HANDLERS.get(req.name)
    if handler is None:
        return _text_result(f"Unknown tool: {req.name}", is_error=True)

    try:
        # Handlers use blocking Supabase/Pinecone clients, so keep them off the event loop.
        text = await asyncio.to_thread(handler, user, req.arguments or {})
    except ToolError as exc:
        return _text_result(str(exc), is_error=True)
    return _text_result(text)


server = Server(
    "UCL-MCP",
    on_list_tools=handle_list_tools,
    on_call_tool=handle_call_tool,
)

streamable_http = StreamableHTTPSessionManager(server, json_response=True)


async def authenticate_request(request: Request) -> AuthenticatedUser:
    """Authenticates the request, and records the user where tool handlers look for it.

    Raises HTTPException on failure.
    """
    # authenticate_mcp_client does blocking Supabase I/O.
    user = await asyncio.to_thread(authenticate_mcp_client, request)
    request.state.user_info = user
    request.scope["user"] = MCPAuthenticatedUser(
        AccessToken(
            token="validated",
            client_id=user.client_id or "mcp-client",
            scopes=[],
            subject=user.user_id,
            claims={"iss": settings.oauth_issuer_url},
        )
    )
    return user


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/.well-known/oauth-protected-resource")
@app.get("/.well-known/oauth-protected-resource/{resource_path:path}")
def oauth_protected_resource_metadata(resource_path: str = ""):
    """Publish RFC 9728 metadata so MCP clients can start OAuth discovery."""
    configured_path = settings.mcp_resource_url.split("://", 1)[-1].partition("/")[2].strip("/")
    if resource_path and resource_path.strip("/") != configured_path:
        raise HTTPException(status_code=404, detail="Protected resource metadata not found")
    return JSONResponse(protected_resource_metadata())


class MCPStreamableHTTPASGI:
    """Authenticate every Streamable HTTP request before MCP dispatch."""

    def __init__(self, transport: StreamableHTTPSessionManager | None = None):
        self._transport = transport

    @property
    def transport(self) -> StreamableHTTPSessionManager:
        return self._transport or streamable_http

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] == "OPTIONS":
            response = Response(status_code=204)
            await response(scope, receive, send)
            return

        request = Request(scope, receive, send)
        try:
            await authenticate_request(request)
        except HTTPException as exc:
            response = Response(
                content=exc.detail,
                status_code=exc.status_code,
                headers=exc.headers,
            )
            await response(scope, receive, send)
            return

        await self.transport.handle_request(scope, receive, send)


app.add_route("/mcp", MCPStreamableHTTPASGI(), methods=["GET", "POST", "DELETE", "OPTIONS"])
