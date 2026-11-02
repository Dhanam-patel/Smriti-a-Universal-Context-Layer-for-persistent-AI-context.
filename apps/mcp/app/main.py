import asyncio

import mcp.types as types
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from mcp.server import Server, ServerRequestContext
from mcp.server.sse import SseServerTransport

from .auth import AuthenticatedUser, authenticate_mcp_client
from .tools import TOOL_DEFINITIONS, TOOL_HANDLERS, ToolError

app = FastAPI(title="UCL MCP Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _text_result(text: str) -> types.CallToolResult:
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)])


async def handle_list_tools(
    ctx: ServerRequestContext, req: types.PaginatedRequestParams | None
) -> types.ListToolsResult:
    return types.ListToolsResult(tools=TOOL_DEFINITIONS)


async def handle_call_tool(
    ctx: ServerRequestContext, req: types.CallToolRequestParams
) -> types.CallToolResult | types.InputRequiredResult:
    # The POST /mcp/messages handler stores the authenticated user on request.state.
    user: AuthenticatedUser | None = getattr(ctx.request.state, "user_info", None)
    if user is None:
        return _text_result("Error: Could not retrieve authentication state")

    handler = TOOL_HANDLERS.get(req.name)
    if handler is None:
        return _text_result(f"Unknown tool: {req.name}")

    try:
        # Handlers use blocking Supabase/Pinecone clients, so keep them off the event loop.
        text = await asyncio.to_thread(handler, user, req.arguments or {})
    except ToolError as exc:
        return _text_result(str(exc))
    return _text_result(text)


server = Server(
    "UCL-MCP",
    on_list_tools=handle_list_tools,
    on_call_tool=handle_call_tool,
)

sse = SseServerTransport("/mcp/messages")


class _TransportUser:
    """Placeholder that SseServerTransport expects to find at scope["user"].

    Real authentication is done by authenticate_mcp_client; this only marks the
    scope as authenticated for the transport.
    """


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/mcp/sse", dependencies=[Depends(authenticate_mcp_client)])
async def mcp_sse(request: Request):
    request.scope["user"] = _TransportUser()

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
            user = await asyncio.to_thread(authenticate_mcp_client, request)
        except HTTPException as exc:
            response = Response(content=exc.detail, status_code=exc.status_code)
            await response(scope, receive, send)
            return

        request.state.user_info = user
        scope["user"] = _TransportUser()

        await self.sse.handle_post_message(scope, receive, send)


app.add_route("/mcp/messages", MCPMessagesASGI(sse), methods=["POST", "OPTIONS"])
