import datetime
import uuid
from collections.abc import Callable, Mapping
from typing import Any

import mcp.types as types
from pinecone import Pinecone

from .auth import AuthenticatedUser
from .db import supabase

DEFAULT_EMBEDDING_MODEL = "multilingual-e5-large"
SEARCH_TOP_K = 5

ToolArguments = Mapping[str, Any]


class ToolError(Exception):
    """A failure that should be reported to the MCP client as the tool's text result."""


TOOL_DEFINITIONS: list[types.Tool] = [
    types.Tool(
        name="read_context",
        description="Reads the user's UCL context from a specific chat",
        inputSchema={
            "type": "object",
            "properties": {
                "chat": {"type": "string", "description": "The UCL chat name/slug"},
                "query": {"type": "string", "description": "The search query"},
            },
            "required": ["chat", "query"],
        },
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
            "required": ["chat", "content"],
        },
    ),
]


def _require(args: ToolArguments, key: str) -> str:
    value = args.get(key)
    if not value:
        raise ToolError(f"Error: {key} is required")
    return value


def _resolve_namespace(user: AuthenticatedUser, chat_slug: str) -> str:
    """Verifies the chat belongs to the user and returns its Pinecone namespace."""
    resp = (
        supabase.table("chats")
        .select("pinecone_namespace")
        .eq("slug", chat_slug)
        .eq("user_id", user.user_id)
        .execute()
    )
    if not resp.data:
        raise ToolError(
            f"Error: Chat '{chat_slug}' not found or you don't have access."
        )
    return resp.data[0]["pinecone_namespace"]


def _embed(
    pc: Pinecone, user: AuthenticatedUser, text: str, input_type: str
) -> list[float]:
    try:
        response = pc.inference.embed(
            model=user.pinecone.embedding_model or DEFAULT_EMBEDDING_MODEL,
            inputs=[text],
            parameters={"input_type": input_type, "truncate": "END"},
        )
        return response[0].values
    except Exception as exc:
        raise ToolError(f"Pinecone inference error: {exc}") from exc


def read_context(user: AuthenticatedUser, args: ToolArguments) -> str:
    chat_slug = _require(args, "chat")
    query = _require(args, "query")
    namespace = _resolve_namespace(user, chat_slug)

    pc = Pinecone(api_key=user.pinecone.api_key)
    embedding = _embed(pc, user, query, "query")

    try:
        index = pc.index(user.pinecone.index_name)
        response = index.query(
            namespace=namespace,
            vector=embedding,
            top_k=SEARCH_TOP_K,
            include_metadata=True,
        )
    except Exception as exc:
        raise ToolError(f"Pinecone search error: {exc}") from exc

    lines = [
        f"- {m.metadata.get('content', '')} (Score: {m.score})"
        for m in response.matches
    ]
    return "Context Search Results:\n\n" + "".join(f"{line}\n" for line in lines)


def write_context(user: AuthenticatedUser, args: ToolArguments) -> str:
    chat_slug = _require(args, "chat")
    content = _require(args, "content")
    namespace = _resolve_namespace(user, chat_slug)

    pc = Pinecone(api_key=user.pinecone.api_key)
    embedding = _embed(pc, user, content, "passage")

    try:
        index = pc.index(user.pinecone.index_name)
        now = datetime.datetime.utcnow().isoformat()
        index.upsert(
            namespace=namespace,
            vectors=[
                {
                    "id": f"ctx_{uuid.uuid4()}",
                    "values": embedding,
                    "metadata": {
                        "content": content,
                        "source": "mcp",
                        "created_at": now,
                        "updated_at": now,
                    },
                }
            ],
        )
    except Exception as exc:
        raise ToolError(f"Pinecone upsert error: {exc}") from exc

    return f"Successfully wrote context to chat {chat_slug}."


ToolHandler = Callable[[AuthenticatedUser, ToolArguments], str]

TOOL_HANDLERS: dict[str, ToolHandler] = {
    "read_context": read_context,
    "write_context": write_context,
}
