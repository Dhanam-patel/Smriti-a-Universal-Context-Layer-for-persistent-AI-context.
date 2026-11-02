import datetime
import uuid
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import mcp.types as types
from pinecone import Pinecone

from .auth import AuthenticatedUser
from .db import get_supabase

DEFAULT_EMBEDDING_MODEL = "multilingual-e5-large"
SEARCH_TOP_K = 5

ToolArguments = Mapping[str, Any]


class ToolError(Exception):
    """A failure that should be reported to the MCP client as an error result."""


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


@contextmanager
def _pinecone_errors(operation: str) -> Iterator[None]:
    """Reports any failure inside the block as a ToolError for the given operation."""
    try:
        yield
    except Exception as exc:
        raise ToolError(f"Pinecone {operation} error: {exc}") from exc


def _require_str(args: ToolArguments, key: str) -> str:
    value = args.get(key)
    if not value:
        raise ToolError(f"Error: {key} is required")
    if not isinstance(value, str):
        raise ToolError(f"Error: {key} must be a string")
    return value


def _resolve_namespace(user: AuthenticatedUser, chat_slug: str) -> str:
    """Verifies the chat belongs to the user and returns its Pinecone namespace."""
    resp = (
        get_supabase()
        .table("chats")
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


@dataclass(frozen=True)
class _PreparedCall:
    """Validated arguments plus everything both tools need before touching the index."""

    chat_slug: str
    text: str
    namespace: str
    index: Any
    embedding: list[float]


def _prepare(
    user: AuthenticatedUser, args: ToolArguments, text_field: str, input_type: str
) -> _PreparedCall:
    if user.pinecone is None:
        raise ToolError(
            "PINECONE_NOT_CONNECTED: Pinecone connection is not configured for this user. Please connect Pinecone in the Smriti dashboard."
        )
    chat_slug = _require_str(args, "chat")
    text = _require_str(args, text_field)
    namespace = _resolve_namespace(user, chat_slug)

    pc = Pinecone(api_key=user.pinecone.api_key)
    with _pinecone_errors("inference"):
        response = pc.inference.embed(
            model=user.pinecone.embedding_model or DEFAULT_EMBEDDING_MODEL,
            inputs=[text],
            parameters={"input_type": input_type, "truncate": "END"},
        )
        embedding = response[0].values

    return _PreparedCall(
        chat_slug=chat_slug,
        text=text,
        namespace=namespace,
        index=pc.index(user.pinecone.index_name),
        embedding=embedding,
    )


def read_context(user: AuthenticatedUser, args: ToolArguments) -> str:
    call = _prepare(user, args, text_field="query", input_type="query")

    with _pinecone_errors("search"):
        response = call.index.query(
            namespace=call.namespace,
            vector=call.embedding,
            top_k=SEARCH_TOP_K,
            include_metadata=True,
        )
        lines = [
            f"- {m.metadata.get('content', '')} (Score: {m.score})\n"
            for m in response.matches
        ]

    return "Context Search Results:\n\n" + "".join(lines)


def write_context(user: AuthenticatedUser, args: ToolArguments) -> str:
    call = _prepare(user, args, text_field="content", input_type="passage")

    with _pinecone_errors("upsert"):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        call.index.upsert(
            namespace=call.namespace,
            vectors=[
                {
                    "id": f"ctx_{uuid.uuid4()}",
                    "values": call.embedding,
                    "metadata": {
                        "content": call.text,
                        "source": "mcp",
                        "created_at": now,
                        "updated_at": now,
                    },
                }
            ],
        )

    return f"Successfully wrote context to chat {call.chat_slug}."


ToolHandler = Callable[[AuthenticatedUser, ToolArguments], str]

TOOL_HANDLERS: dict[str, ToolHandler] = {
    "read_context": read_context,
    "write_context": write_context,
}
