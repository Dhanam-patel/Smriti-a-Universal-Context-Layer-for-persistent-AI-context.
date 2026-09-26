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

@app.get("/health")
def health_check():
    return {"status": "ok"}

# ==============================================================================
# PART 1: PROCESS LOGIC (VALIDATION, CREATION, UPDATION)
# ==============================================================================
# This core logic is used by both the Antigravity and Claude integrations.

def get_tool_list():
    return [
        {
            "name": "read_context",
            "description": "Reads the user's UCL context from a specific chat",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "chat": {"type": "string", "description": "The UCL chat name/slug"},
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["chat", "query"]
            }
        },
        {
            "name": "write_context",
            "description": "Writes new information to the user's UCL context",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "chat": {"type": "string", "description": "The UCL chat name/slug"},
                    "content": {"type": "string", "description": "The content to save"}
                },
                "required": ["chat", "content"]
            }
        }
    ]

def execute_read_context(user_info: dict, chat_slug: str, query: str):
    if not query:
        raise ValueError("Missing query argument")
        
    user_id = user_info["user_id"]
    pc_conn = user_info["pinecone_connection"]
    
    chat_resp = supabase.table("chats").select("pinecone_namespace").eq("slug", chat_slug).eq("user_id", user_id).execute()
    if not chat_resp.data or len(chat_resp.data) == 0:
        raise ValueError(f"Chat '{chat_slug}' not found or access denied.")
        
    namespace = chat_resp.data[0]["pinecone_namespace"]
    pc = Pinecone(api_key=pc_conn["encrypted_api_key"])
    model = pc_conn.get("embedding_model") or "multilingual-e5-large"
    index = pc.index(pc_conn["index_name"])
    
    embedding_response = pc.inference.embed(
        model=model, inputs=[query], parameters={"input_type": "query", "truncate": "END"}
    )
    query_response = index.query(namespace=namespace, vector=embedding_response[0].values, top_k=5, include_metadata=True)
    
    results_text = "Context Search Results:\n\n"
    for match in query_response.matches:
        results_text += f"- {match.metadata.get('content', '')} (Score: {match.score})\n"
        
    return results_text

def execute_write_context(user_info: dict, chat_slug: str, content: str):
    if not content:
        raise ValueError("Missing content argument")
        
    user_id = user_info["user_id"]
    pc_conn = user_info["pinecone_connection"]
    
    chat_resp = supabase.table("chats").select("pinecone_namespace").eq("slug", chat_slug).eq("user_id", user_id).execute()
    if not chat_resp.data or len(chat_resp.data) == 0:
        raise ValueError(f"Chat '{chat_slug}' not found or access denied.")
        
    namespace = chat_resp.data[0]["pinecone_namespace"]
    pc = Pinecone(api_key=pc_conn["encrypted_api_key"])
    model = pc_conn.get("embedding_model") or "multilingual-e5-large"
    index = pc.index(pc_conn["index_name"])
    
    embedding_response = pc.inference.embed(
        model=model, inputs=[content], parameters={"input_type": "passage", "truncate": "END"}
    )
    
    record_id = f"ctx_{uuid.uuid4()}"
    now = datetime.datetime.utcnow().isoformat()
    index.upsert(
        namespace=namespace,
        vectors=[{
            "id": record_id,
            "values": embedding_response[0].values,
            "metadata": {"content": content, "source": "mcp", "created_at": now, "updated_at": now}
        }]
    )
    return f"Successfully wrote context to chat {chat_slug}."


# ==============================================================================
# PART 2: ANTIGRAVITY MCP INTEGRATION (STANDARD SSE)
# ==============================================================================
# Antigravity (and standard MCP clients) use the official GET /mcp/sse 
# and POST /mcp/messages endpoints based on the official Python SDK.

async def handle_list_tools(ctx: ServerRequestContext, req: types.PaginatedRequestParams | None) -> types.ListToolsResult:
    tools_def = get_tool_list()
    return types.ListToolsResult(
        tools=[types.Tool(**t) for t in tools_def]
    )

async def handle_call_tool(ctx: ServerRequestContext, req: types.CallToolRequestParams) -> types.CallToolResult | types.InputRequiredResult:
    try:
        user_info = ctx.request.state.user_info
    except Exception:
        user_info = ctx.request.scope.get("state", {}).get("user_info")
        if not user_info:
            return types.CallToolResult(content=[types.TextContent(type="text", text="Error: Could not retrieve authentication state")])
            
    chat_slug = req.arguments.get("chat")
    if not chat_slug:
        return types.CallToolResult(content=[types.TextContent(type="text", text="Error: Missing chat argument")])
        
    try:
        if req.name == "read_context":
            result = execute_read_context(user_info, chat_slug, req.arguments.get("query"))
            return types.CallToolResult(content=[types.TextContent(type="text", text=result)])
        elif req.name == "write_context":
            result = execute_write_context(user_info, chat_slug, req.arguments.get("content"))
            return types.CallToolResult(content=[types.TextContent(type="text", text=result)])
        else:
            return types.CallToolResult(content=[types.TextContent(type="text", text=f"Unknown tool: {req.name}")])
    except Exception as e:
        return types.CallToolResult(content=[types.TextContent(type="text", text=f"Error: {str(e)}")])

server = Server("UCL-MCP", on_list_tools=handle_list_tools, on_call_tool=handle_call_tool)
sse = SseServerTransport("/mcp/messages")
active_sessions = {}

@app.get("/mcp/sse")
async def mcp_sse(request: Request, user_info: dict = Depends(authenticate_mcp_client)):
    class DummyAuthUser: pass
    request.scope["user"] = DummyAuthUser()
    sse._session_owners = getattr(sse, "_session_owners", {})
    
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        if hasattr(sse, "sessions") and sse.sessions:
            session_id = list(sse.sessions.keys())[-1]
            active_sessions[session_id] = user_info
            
        await server.run(streams[0], streams[1], server.create_initialization_options())
        
        if 'session_id' in locals() and session_id in active_sessions:
            del active_sessions[session_id]

class MCPMessagesASGI:
    def __init__(self, sse_transport):
        self.sse = sse_transport

    async def __call__(self, scope, receive, send):
        request = Request(scope, receive, send)
        session_id = request.query_params.get("sessionId")
        if session_id and session_id in active_sessions:
            request.state.user_info = active_sessions[session_id]
        else:
            try:
                request.state.user_info = authenticate_mcp_client(request)
            except Exception:
                response = Response(content="Unauthorized", status_code=401)
                await response(scope, receive, send)
                return
                
        class DummyAuthUser: pass
        scope["user"] = DummyAuthUser()
        await self.sse.handle_post_message(scope, receive, send)

app.add_route("/mcp/messages", MCPMessagesASGI(sse), methods=["POST", "OPTIONS"])


# ==============================================================================
# PART 3: CLAUDE.AI INTEGRATION (STATELESS HTTP)
# ==============================================================================
# Claude's custom connectors use aggressive validation and streamable HTTP which
# can fail on Vercel Serverless. This POST endpoint acts as a stateless MCP server.

@app.post("/mcp/sse")
async def mcp_sse_post(request: Request):
    try:
        body = await request.json()
    except:
        body = {}
        
    req_id = body.get("id", 1)
    method = body.get("method")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "UCL-MCP-Stateless", "version": "1.0.0"}
            }
        }
    if method == "notifications/initialized":
        return {"jsonrpc": "2.0"}
        
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": get_tool_list()}}
        
    try:
        user_info = authenticate_mcp_client(request)
    except Exception:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": "Unauthorized"}}
        
    if method == "tools/call":
        params = body.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})
        chat_slug = args.get("chat")
        
        if not chat_slug:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": "Missing chat argument"}}
            
        try:
            if tool_name == "read_context":
                result = execute_read_context(user_info, chat_slug, args.get("query"))
            elif tool_name == "write_context":
                result = execute_write_context(user_info, chat_slug, args.get("content"))
            else:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}
                
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": result}]}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e)}}
            
    return {"jsonrpc": "2.0", "id": req_id, "result": {}}

