from dataclasses import dataclass

from fastapi import HTTPException, Request

from .db import get_supabase
from .oauth import OAuthAccessToken, authenticate_oauth_request


@dataclass(frozen=True)
class PineconeConnection:
    index_name: str
    # The `encrypted_api_key` column currently stores the key as plaintext (the web app
    # writes it that way), so no decryption happens here.
    api_key: str
    embedding_model: str | None
    host: str | None = None


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    pinecone: PineconeConnection | None = None
    client_id: str | None = None


def authenticate_mcp_client(request: Request) -> AuthenticatedUser:
    """
    Authenticates the MCP client.

    Verifies an OAuth 2.1 access token, then resolves its subject to the
    corresponding Smriti user and Pinecone configuration. The authorization
    server must issue the Smriti user id as the token's ``sub`` claim.

    This performs blocking network I/O; call it via a worker thread from async code.
    """
    access_token: OAuthAccessToken = authenticate_oauth_request(request)
    supabase = get_supabase()
    user_id = access_token.subject

    pc_resp = (
        supabase.table("pinecone_connections")
        .select("index_name, host, encrypted_api_key, embedding_model")
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
            host=pc_row.get("host"),
        ),
        client_id=access_token.client_id,
    )
