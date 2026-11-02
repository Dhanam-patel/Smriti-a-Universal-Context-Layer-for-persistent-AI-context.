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
    pc: Pinecone


_index_schema_cache: dict[str, Any] = {}


def _get_index_schema(pc: Any, index_name: str) -> Any | None:
    if index_name in _index_schema_cache:
        return _index_schema_cache[index_name]
    try:
        desc_fn = getattr(pc, "describe_index", None)
        if callable(desc_fn):
            desc = desc_fn(index_name)
        elif hasattr(pc, "indexes") and hasattr(pc.indexes, "describe"):
            desc = pc.indexes.describe(index_name)
        else:
            desc = None
        schema = getattr(desc, "schema", None) if not isinstance(desc, dict) else desc.get("schema")
        if schema is not None and not str(type(schema)).endswith("MagicMock'>"):
            _index_schema_cache[index_name] = schema
            return schema
    except Exception:
        pass
    return None


def _get_schema_fields(schema: Any | None) -> dict[str, Any]:
    if not schema:
        return {}
    if isinstance(schema, dict):
        fields = schema.get("fields")
        return fields if isinstance(fields, dict) else {}
    fields = getattr(schema, "fields", None)
    return fields if isinstance(fields, dict) else {}


def _extract_document_content(doc: Any) -> str:
    if hasattr(doc, "get"):
        val = doc.get("content") or doc.get("text") or doc.get("body")
        if val:
            return str(val)
    if hasattr(doc, "metadata") and isinstance(doc.metadata, dict):
        val = doc.metadata.get("content") or doc.metadata.get("text")
        if val:
            return str(val)
    fields = getattr(doc, "fields", None)
    if isinstance(fields, dict):
        val = fields.get("content") or fields.get("text") or fields.get("body")
        if val:
            return str(val)
    for attr in ("content", "text", "body"):
        val = getattr(doc, attr, None)
        if val and not callable(val):
            return str(val)
    if hasattr(doc, "id"):
        return str(doc.id)
    return str(doc)


def _build_document(
    record_id: str,
    text: str,
    embedding: list[float],
    now: str,
    schema: Any | None = None,
) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "_id": record_id,
        "source": "mcp",
        "created_at": now,
        "updated_at": now,
    }
    fields = _get_schema_fields(schema)
    dense_vector_field: str | None = None
    text_fields: list[str] = []

    if fields:
        for field_name, field_def in fields.items():
            type_name = type(field_def).__name__
            f_type = getattr(field_def, "type", None) if not isinstance(field_def, dict) else field_def.get("type")
            if f_type == "dense_vector" or "DenseVector" in type_name:
                if dense_vector_field is None:
                    dense_vector_field = field_name
            elif (
                f_type in ("string", "semantic_text")
                or "String" in type_name
                or "SemanticText" in type_name
            ):
                text_fields.append(field_name)

    # Only assign the embedding to the schema's declared dense vector field.
    # Never attach float arrays to metadata, because Pinecone metadata only allows
    # booleans, numbers, strings, or arrays of strings.
    if dense_vector_field:
        doc[dense_vector_field] = embedding

    # Store text in any declared text fields
    if text_fields:
        for f in text_fields:
            doc[f] = text
    else:
        doc["content"] = text
        doc["text"] = text

    # Ensure content is always available for search/read formatting if not conflicting
    if "content" not in doc:
        doc["content"] = text

    return doc


def _build_score_by(
    text: str, embedding: list[float], schema: Any | None = None
) -> list[dict[str, Any]]:
    fields = _get_schema_fields(schema)
    if fields:
        # 1. Prefer dense vector query if index has a dense vector field
        for field_name, field_def in fields.items():
            type_name = type(field_def).__name__
            f_type = getattr(field_def, "type", None) if not isinstance(field_def, dict) else field_def.get("type")
            if f_type == "dense_vector" or "DenseVector" in type_name:
                return [{"type": "dense_vector", "field": field_name, "values": embedding}]

        # 2. Prefer embed query if index has an embedded text field (integrated embedding)
        for field_name, field_def in fields.items():
            type_name = type(field_def).__name__
            f_type = getattr(field_def, "type", None) if not isinstance(field_def, dict) else field_def.get("type")
            embed = getattr(field_def, "embed", None) if not isinstance(field_def, dict) else field_def.get("embed")
            if embed or f_type == "semantic_text" or "SemanticText" in type_name:
                return [{"type": "embed", "field": field_name, "query": text}]

        # 3. Text query for searchable text fields
        for field_name, field_def in fields.items():
            type_name = type(field_def).__name__
            f_type = getattr(field_def, "type", None) if not isinstance(field_def, dict) else field_def.get("type")
            if f_type == "string" or "String" in type_name:
                return [{"type": "text", "fields": [field_name], "query": text}]

    return [{"type": "text", "fields": ["text"], "query": text}]


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

    if user.pinecone.host:
        index = pc.index(host=user.pinecone.host)
    else:
        index = pc.index(user.pinecone.index_name)

    return _PreparedCall(
        chat_slug=chat_slug,
        text=text,
        namespace=namespace,
        index=index,
        embedding=embedding,
        pc=pc,
    )


def read_context(user: AuthenticatedUser, args: ToolArguments) -> str:
    call = _prepare(user, args, text_field="query", input_type="query")

    with _pinecone_errors("search"):
        schema = _get_index_schema(call.pc, user.pinecone.index_name)
        if schema and _get_schema_fields(schema) and hasattr(call.index, "documents"):
            score_by = _build_score_by(call.text, call.embedding, schema)
            response = call.index.documents.search(
                namespace=call.namespace,
                top_k=SEARCH_TOP_K,
                score_by=score_by,
                include_fields=["*"],
            )
            lines = [
                f"- {_extract_document_content(m)} (Score: {getattr(m, 'score', None)})\n"
                for m in response.matches
            ]
        else:
            try:
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
            except Exception as exc:
                err_msg = str(exc).lower()
                if (
                    "document schema" in err_msg
                    or "documents/search" in err_msg
                    or "documents/upsert" in err_msg
                    or "documents api" in err_msg
                ) and hasattr(call.index, "documents"):
                    if schema is None:
                        schema = _get_index_schema(call.pc, user.pinecone.index_name)
                    score_by = _build_score_by(call.text, call.embedding, schema)
                    response = call.index.documents.search(
                        namespace=call.namespace,
                        top_k=SEARCH_TOP_K,
                        score_by=score_by,
                        include_fields=["*"],
                    )
                    lines = [
                        f"- {_extract_document_content(m)} (Score: {getattr(m, 'score', None)})\n"
                        for m in response.matches
                    ]
                else:
                    raise

    return "Context Search Results:\n\n" + "".join(lines)


def write_context(user: AuthenticatedUser, args: ToolArguments) -> str:
    call = _prepare(user, args, text_field="content", input_type="passage")

    with _pinecone_errors("upsert"):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        record_id = f"ctx_{uuid.uuid4()}"

        schema = _get_index_schema(call.pc, user.pinecone.index_name)
        if schema and _get_schema_fields(schema) and hasattr(call.index, "documents"):
            doc = _build_document(record_id, call.text, call.embedding, now, schema)
            call.index.documents.upsert(
                namespace=call.namespace,
                documents=[doc],
            )
        else:
            try:
                call.index.upsert(
                    namespace=call.namespace,
                    vectors=[
                        {
                            "id": record_id,
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
            except Exception as exc:
                err_msg = str(exc).lower()
                if (
                    "document schema" in err_msg
                    or "documents/upsert" in err_msg
                    or "documents api" in err_msg
                ) and hasattr(call.index, "documents"):
                    if schema is None:
                        schema = _get_index_schema(call.pc, user.pinecone.index_name)
                    doc = _build_document(
                        record_id, call.text, call.embedding, now, schema
                    )
                    call.index.documents.upsert(
                        namespace=call.namespace,
                        documents=[doc],
                    )
                else:
                    raise

    return f"Successfully wrote context to chat {call.chat_slug}."


ToolHandler = Callable[[AuthenticatedUser, ToolArguments], str]

TOOL_HANDLERS: dict[str, ToolHandler] = {
    "read_context": read_context,
    "write_context": write_context,
}
