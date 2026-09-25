from fastapi import FastAPI, Depends, Request
from fastapi.responses import Response
from .config import settings
from .auth import authenticate_mcp_client
from mcp.server import Server, ServerRequestContext
from mcp.server.sse import SseServerTransport
import mcp.types as types
from pinecone import Pinecone
import uuid
import datetime
import json
from supabase import create_client

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="UCL MCP Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase = create_client(
    settings.supabase_url,
    settings.supabase_service_role_key
)

async def handle_list_tools(ctx: ServerRequestContext, req: types.PaginatedRequestParams | None) -> types.ListToolsResult:
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name="read_context",
                description="Reads the user's UCL context from a specific chat",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chat": {"type": "string", "description": "The UCL chat name/slug"},
                        "query": {"type": "string", "description": "The search query"},
                    },
                    "required": ["chat", "query"]
                }
            ),
            types.Tool(
                name="write_context",
                description="Writes new information to the user's UCL context",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chat": {"type": "string", "description": "The UCL chat name/slug"},
                        "content": {"type": "string", "description": "The content to save"},
                    },
                    "required": ["chat", "content"]
                }
            )
        ]
    )

async def handle_call_tool(ctx: ServerRequestContext, req: types.CallToolRequestParams) -> types.CallToolResult | types.InputRequiredResult:
    # Authenticated user info is attached to the starlette scope by SseServerTransport if we pass it, but wait!
    # In SseServerTransport, user is `scope.get("user")`.
    # Let's extract the user_info from ctx.meta or ctx.request if possible, but actually we can just pass the Starlette request via ctx.request
    try:
        user_info = ctx.request.state.user_info
    except Exception as e:
        # Fallback to scope if available
        user_info = ctx.request.scope.get("state", {}).get("user_info")
        if not user_info:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text="Error: Could not retrieve authentication state")]
            )
            
    user_id = user_info["user_id"]
    pc_conn = user_info["pinecone_connection"]
    
    chat_slug = req.arguments.get("chat")
    
    # 1. Fetch chat to verify ownership and get namespace
    chat_resp = supabase.table("chats").select("pinecone_namespace").eq("slug", chat_slug).eq("user_id", user_id).execute()
    if not chat_resp.data or len(chat_resp.data) == 0:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Error: Chat '{chat_slug}' not found or you don't have access.")]
        )
    
    namespace = chat_resp.data[0]["pinecone_namespace"]
    
    pc = Pinecone(api_key=pc_conn["encrypted_api_key"])
    model = pc_conn.get("embedding_model") or "multilingual-e5-large"
    index_name = pc_conn["index_name"]
    index = pc.index(index_name)
    
    if req.name == "read_context":
        query = req.arguments.get("query")
        if not query:
            return types.CallToolResult(content=[types.TextContent(type="text", text="Error: query is required")])
            
        try:
            embedding_response = pc.inference.embed(
                model=model,
                inputs=[query],
                parameters={"input_type": "query", "truncate": "END"}
            )
            embedding = embedding_response[0].values
        except Exception as e:
            return types.CallToolResult(content=[types.TextContent(type="text", text=f"Pinecone inference error: {str(e)}")])
            
        try:
            query_response = index.query(
                namespace=namespace,
                vector=embedding,
                top_k=5,
                include_metadata=True
            )
            
            results_text = "Context Search Results:\n\n"
            for match in query_response.matches:
                results_text += f"- {match.metadata.get('content', '')} (Score: {match.score})\n"
                
            return types.CallToolResult(content=[types.TextContent(type="text", text=results_text)])
        except Exception as e:
            return types.CallToolResult(content=[types.TextContent(type="text", text=f"Pinecone search error: {str(e)}")])
            
    elif req.name == "write_context":
        content = req.arguments.get("content")
        if not content:
            return types.CallToolResult(content=[types.TextContent(type="text", text="Error: content is required")])
            
        try:
            embedding_response = pc.inference.embed(
                model=model,
                inputs=[content],
                parameters={"input_type": "passage", "truncate": "END"}
            )
            embedding = embedding_response[0].values
        except Exception as e:
            return types.CallToolResult(content=[types.TextContent(type="text", text=f"Pinecone inference error: {str(e)}")])
            
        try:
            record_id = f"ctx_{uuid.uuid4()}"
            now = datetime.datetime.utcnow().isoformat()
            index.upsert(
                namespace=namespace,
                vectors=[{
                    "id": record_id,
                    "values": embedding,
                    "metadata": {
                        "content": content,
                        "source": "mcp",
                        "created_at": now,
                        "updated_at": now
                    }
                }]
            )
            return types.CallToolResult(content=[types.TextContent(type="text", text=f"Successfully wrote context to chat {chat_slug}.")])
        except Exception as e:
            return types.CallToolResult(content=[types.TextContent(type="text", text=f"Pinecone upsert error: {str(e)}")])
            
    return types.CallToolResult(content=[types.TextContent(type="text", text=f"Unknown tool: {req.name}")])


server = Server(
    "UCL-MCP",
    on_list_tools=handle_list_tools,
    on_call_tool=handle_call_tool
)

sse = SseServerTransport("/mcp/messages")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/mcp/sse")
async def mcp_sse(request: Request, user_info: dict = Depends(authenticate_mcp_client)):
    # Authenticate via Depend sets request.state.user_info, but wait, this is a GET.
    # The MCP client reconnects. But since Starlette might pass the Request context differently,
    # let's inject user_info into the user object of the scope so SseServerTransport can use it for auth verification.
    class DummyAuthUser:
        pass
    dummy = DummyAuthUser()
    request.scope["user"] = dummy
    sse._session_owners = getattr(sse, "_session_owners", {})
    
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())

@app.post("/mcp/sse")
async def mcp_sse_post(request: Request, user_info: dict = Depends(authenticate_mcp_client)):
    # Claude.ai probes the URL with a POST request. If the user provided the api_key
    # query parameter, authenticate_mcp_client will succeed and we return 200 OK
    # to let Claude know the endpoint is valid and authenticated.
    return {"status": "ok", "message": "Probe successful"}

class MCPMessagesASGI:
    def __init__(self, sse_transport):
        self.sse = sse_transport

    async def __call__(self, scope, receive, send):
        request = Request(scope, receive, send)
        try:
            user_info = authenticate_mcp_client(request)
        except Exception as e:
            response = Response(content="Unauthorized", status_code=401)
            await response(scope, receive, send)
            return

        request.state.user_info = user_info
        class DummyAuthUser:
            pass
        scope["user"] = DummyAuthUser()
        
        await self.sse.handle_post_message(scope, receive, send)

app.add_route("/mcp/messages", MCPMessagesASGI(sse), methods=["POST", "OPTIONS"])

