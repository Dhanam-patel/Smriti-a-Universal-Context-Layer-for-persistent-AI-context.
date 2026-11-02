import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from app import main, tools
from app.auth import AuthenticatedUser, PineconeConnection

USER = AuthenticatedUser("u1", PineconeConnection("idx", "key", None))


def _chat_lookup(sb, data):
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = SimpleNamespace(
        data=data
    )


@pytest.fixture
def supabase():
    with patch.object(tools, "supabase") as sb:
        _chat_lookup(sb, [{"pinecone_namespace": "ns"}])
        yield sb


@pytest.fixture
def pinecone():
    with patch.object(tools, "Pinecone") as pinecone_cls:
        pc = pinecone_cls.return_value
        pc.inference.embed.return_value = [SimpleNamespace(values=[0.1, 0.2])]
        pc.index.return_value.query.return_value = SimpleNamespace(
            matches=[SimpleNamespace(metadata={"content": "hello"}, score=0.9)]
        )
        yield pc


@pytest.mark.parametrize(
    "handler, args, missing",
    [
        (tools.read_context, {}, "chat"),
        (tools.read_context, {"chat": "c"}, "query"),
        (tools.write_context, {"chat": "c"}, "content"),
    ],
)
def test_missing_arguments_raise_tool_error(handler, args, missing):
    with pytest.raises(tools.ToolError, match=f"{missing} is required"):
        handler(USER, args)


def test_unknown_or_foreign_chat_is_rejected(supabase, pinecone):
    _chat_lookup(supabase, [])
    with pytest.raises(tools.ToolError, match="not found or you don't have access"):
        tools.read_context(USER, {"chat": "c", "query": "q"})
    pinecone.inference.embed.assert_not_called()


def test_read_context_formats_matches(supabase, pinecone):
    result = tools.read_context(USER, {"chat": "c", "query": "q"})

    assert result == "Context Search Results:\n\n- hello (Score: 0.9)\n"
    embed_kwargs = pinecone.inference.embed.call_args.kwargs
    assert embed_kwargs["model"] == tools.DEFAULT_EMBEDDING_MODEL
    assert embed_kwargs["parameters"]["input_type"] == "query"


def test_write_context_upserts_into_chat_namespace(supabase, pinecone):
    result = tools.write_context(USER, {"chat": "c", "content": "text"})

    assert result == "Successfully wrote context to chat c."
    upsert_kwargs = pinecone.index.return_value.upsert.call_args.kwargs
    assert upsert_kwargs["namespace"] == "ns"
    assert upsert_kwargs["vectors"][0]["metadata"]["content"] == "text"


def test_embedding_failure_is_reported_as_tool_error(supabase, pinecone):
    pinecone.inference.embed.side_effect = RuntimeError("boom")
    with pytest.raises(tools.ToolError, match="Pinecone inference error: boom"):
        tools.write_context(USER, {"chat": "c", "content": "text"})


def _call(name, user=None, arguments=None):
    state = SimpleNamespace() if user is None else SimpleNamespace(user_info=user)
    ctx = SimpleNamespace(request=SimpleNamespace(state=state))
    req = SimpleNamespace(name=name, arguments=arguments)
    return asyncio.run(main.handle_call_tool(ctx, req)).content[0].text


def test_call_tool_requires_authenticated_user():
    assert _call("read_context") == "Error: Could not retrieve authentication state"


def test_call_tool_rejects_unknown_tool():
    assert _call("nope", user=USER) == "Unknown tool: nope"


def test_call_tool_tolerates_missing_arguments():
    assert _call("read_context", user=USER, arguments=None) == "Error: chat is required"


def test_call_tool_returns_handler_output(supabase, pinecone):
    text = _call("read_context", user=USER, arguments={"chat": "c", "query": "q"})
    assert text.startswith("Context Search Results:")
