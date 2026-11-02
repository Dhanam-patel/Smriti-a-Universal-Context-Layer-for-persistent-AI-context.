import asyncio
from contextlib import asynccontextmanager

import mcp.types as types
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from mcp.server import Server, ServerRequestContext
from mcp.server.sse import SseServerTransport

from .auth import AuthenticatedUser, authenticate_mcp_client
from .config import settings, validate_settings
from .tools import TOOL_DEFINITIONS, TOOL_HANDLERS, ToolError


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_settings(settings)
    yield


app = FastAPI(title="UCL MCP Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
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

sse = SseServerTransport("/mcp/messages")


class _TransportUser:
    """Placeholder that SseServerTransport expects to find at scope["user"].

    Real authentication is done by authenticate_request; this only marks the
    scope as authenticated for the transport.
    """


async def authenticate_request(request: Request) -> AuthenticatedUser:
    """Authenticates the request, and records the user where tool handlers look for it.

    Raises HTTPException on failure. Used by both MCP endpoints so they behave identically.
    """
    # authenticate_mcp_client does blocking Supabase I/O.
    user = await asyncio.to_thread(authenticate_mcp_client, request)
    request.state.user_info = user
    request.scope["user"] = _TransportUser()
    return user


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/mcp/sse", dependencies=[Depends(authenticate_request)])
async def mcp_sse(request: Request):
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


class MCPMessagesASGI:
    def __init__(self, sse_transport: SseServerTransport):
        self.sse = sse_transport

    async def __call__(self, scope, receive, send):
        request = Request(scope, receive, send)
        try:
            await authenticate_request(request)
        except HTTPException as exc:
            response = Response(content=exc.detail, status_code=exc.status_code)
            await response(scope, receive, send)
            return

        await self.sse.handle_post_message(scope, receive, send)


app.add_route("/mcp/messages", MCPMessagesASGI(sse), methods=["POST", "OPTIONS"])
