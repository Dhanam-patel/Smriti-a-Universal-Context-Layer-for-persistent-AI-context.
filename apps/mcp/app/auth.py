from fastapi import Request, HTTPException
import hashlib

from supabase import create_client, Client
from .config import settings

# Initialize Supabase client
supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_role_key
)

def authenticate_mcp_client(request: Request):
    """
    Authenticates the MCP client.
    Extracts the Bearer token (secret credential) from header or query param.
    """
    token = None
    
    # 1. Try Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        
    # 2. Try query parameter (needed for browser EventSource and Claude.ai web)
    if not token:
        token = request.query_params.get("api_key")
        
    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    
    # Validate token_hash against Supabase DB
    mcp_resp = supabase.table("mcp_connections").select("user_id, status").eq("credential_hash", token_hash).execute()
    
    if not mcp_resp.data or len(mcp_resp.data) == 0:
        raise HTTPException(status_code=401, detail="Invalid MCP credential")
        
    mcp_conn = mcp_resp.data[0]
    if mcp_conn.get("status") != "active":
        raise HTTPException(status_code=403, detail="MCP connection is not active")
        
    user_id = mcp_conn["user_id"]
    
    # Get Pinecone configuration for this user
    pc_resp = supabase.table("pinecone_connections").select("index_name, encrypted_api_key, embedding_model, namespace_prefix").eq("user_id", user_id).execute()
    
    if not pc_resp.data or len(pc_resp.data) == 0:
        raise HTTPException(status_code=400, detail="Pinecone connection not configured for this user")
        
    pinecone_conn = pc_resp.data[0]
    
    user_info = {
        "user_id": user_id,
        "pinecone_connection": pinecone_conn
    }
    
    return user_info
