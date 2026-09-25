from fastapi import FastAPI, Depends, HTTPException, Request
from .config import settings
from .auth import authenticate_mcp_client
# from mcp.server import ... # MCP SDK specific imports

app = FastAPI(title="UCL MCP Server")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/mcp/{connection_id}/sse")
async def mcp_sse(connection_id: str, request: Request, user_info: dict = Depends(authenticate_mcp_client)):
    """
    SSE transport endpoint for MCP clients.
    """
    # This is where the MCP SDK SSE transport will be attached
    return {"message": f"SSE Transport placeholder for connection {connection_id}"}

@app.post("/mcp/{connection_id}/messages")
async def mcp_messages(connection_id: str, request: Request, user_info: dict = Depends(authenticate_mcp_client)):
    """
    Message receiving endpoint for the SSE transport.
    """
    # This is where the MCP SDK processes incoming messages
    return {"message": "Message transport placeholder"}
