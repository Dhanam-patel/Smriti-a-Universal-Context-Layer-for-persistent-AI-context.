import hashlib
from dataclasses import dataclass

from fastapi import HTTPException, Request

from .db import supabase

BEARER_PREFIX = "Bearer "


@dataclass(frozen=True)
class PineconeConnection:
    index_name: str
    api_key: str
    embedding_model: str | None


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    pinecone: PineconeConnection


def _extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith(BEARER_PREFIX):
        raise HTTPException(
            status_code=401, detail="Missing or invalid authentication token"
        )
    return auth_header[len(BEARER_PREFIX) :]


def authenticate_mcp_client(request: Request) -> AuthenticatedUser:
    """
    Authenticates the MCP client.

    Hashes the Bearer token (secret credential) and looks it up in the Supabase
    `mcp_connections` table. Returns the owning user and their Pinecone
    configuration. Raises HTTPException (401/403/400) on failure.

    This performs blocking network I/O; call it via a worker thread from async code.
    """
    token = _extract_bearer_token(request)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    mcp_resp = (
        supabase.table("mcp_connections")
        .select("user_id, status")
        .eq("credential_hash", token_hash)
        .execute()
    )
    if not mcp_resp.data:
        raise HTTPException(status_code=401, detail="Invalid MCP credential")

    mcp_conn = mcp_resp.data[0]
    if mcp_conn.get("status") != "active":
        raise HTTPException(status_code=403, detail="MCP connection is not active")

    user_id = mcp_conn["user_id"]

    pc_resp = (
        supabase.table("pinecone_connections")
        .select("index_name, encrypted_api_key, embedding_model")
        .eq("user_id", user_id)
        .execute()
    )
    if not pc_resp.data:
        raise HTTPException(
            status_code=400, detail="Pinecone connection not configured for this user"
        )

    pc_row = pc_resp.data[0]
    return AuthenticatedUser(
        user_id=user_id,
        pinecone=PineconeConnection(
            index_name=pc_row["index_name"],
            api_key=pc_row["encrypted_api_key"],
            embedding_model=pc_row.get("embedding_model"),
        ),
    )
