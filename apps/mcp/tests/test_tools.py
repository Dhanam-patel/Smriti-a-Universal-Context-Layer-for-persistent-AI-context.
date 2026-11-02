import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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
    sb = MagicMock()
    _chat_lookup(sb, [{"pinecone_namespace": "ns"}])
    with patch.object(tools, "get_supabase", return_value=sb):
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
    "handler, args, message",
    [
        (tools.read_context, {}, "chat is required"),
        (tools.read_context, {"chat": "c"}, "query is required"),
        (tools.write_context, {"chat": "c"}, "content is required"),
        (tools.read_context, {"chat": 5, "query": "q"}, "chat must be a string"),
        (
            tools.write_context,
            {"chat": "c", "content": ["x"]},
            "content must be a string",
        ),
    ],
)
def test_invalid_arguments_raise_tool_error(handler, args, message):
    with pytest.raises(tools.ToolError, match=message):
        handler(USER, args)


def test_unknown_or_foreign_chat_is_rejected(supabase, pinecone):
    _chat_lookup(supabase, [])
    with pytest.raises(tools.ToolError, match="not found or you don't have access"):
        tools.read_context(USER, {"chat": "c", "query": "q"})
    pinecone.inference.embed.assert_not_called()


def test_chat_lookup_is_scoped_to_the_user(supabase, pinecone):
    tools.read_context(USER, {"chat": "c", "query": "q"})

    select = supabase.table.return_value.select.return_value
    select.eq.assert_called_once_with("slug", "c")
    select.eq.return_value.eq.assert_called_once_with("user_id", "u1")


def test_read_context_formats_matches(supabase, pinecone):
    result = tools.read_context(USER, {"chat": "c", "query": "q"})

    assert result == "Context Search Results:\n\n- hello (Score: 0.9)\n"
    embed_kwargs = pinecone.inference.embed.call_args.kwargs
    assert embed_kwargs["model"] == tools.DEFAULT_EMBEDDING_MODEL
    assert embed_kwargs["parameters"]["input_type"] == "query"


def test_configured_embedding_model_is_used(supabase, pinecone):
    user = AuthenticatedUser("u1", PineconeConnection("idx", "key", "custom-model"))
    tools.read_context(user, {"chat": "c", "query": "q"})
    assert pinecone.inference.embed.call_args.kwargs["model"] == "custom-model"


def test_write_context_upserts_into_chat_namespace(supabase, pinecone):
    result = tools.write_context(USER, {"chat": "c", "content": "text"})

    assert result == "Successfully wrote context to chat c."
    assert (
        pinecone.inference.embed.call_args.kwargs["parameters"]["input_type"]
        == "passage"
    )
    upsert_kwargs = pinecone.index.return_value.upsert.call_args.kwargs
    assert upsert_kwargs["namespace"] == "ns"
    assert upsert_kwargs["vectors"][0]["metadata"]["content"] == "text"


@pytest.mark.parametrize(
    "failing_call, handler, args, message",
    [
        (
            "inference.embed",
            tools.write_context,
            {"chat": "c", "content": "t"},
            "Pinecone inference error: boom",
        ),
        (
            "index.return_value.query",
            tools.read_context,
            {"chat": "c", "query": "q"},
            "Pinecone search error: boom",
        ),
        (
            "index.return_value.upsert",
            tools.write_context,
            {"chat": "c", "content": "t"},
            "Pinecone upsert error: boom",
        ),
    ],
)
def test_pinecone_failures_are_reported_as_tool_errors(
    supabase, pinecone, failing_call, handler, args, message
):
    target = pinecone
    for part in failing_call.split("."):
        target = getattr(target, part)
    target.side_effect = RuntimeError("boom")

    with pytest.raises(tools.ToolError, match=message):
        handler(USER, args)


def _call(name, user=None, arguments=None):
    state = SimpleNamespace() if user is None else SimpleNamespace(user_info=user)
    ctx = SimpleNamespace(request=SimpleNamespace(state=state))
    req = SimpleNamespace(name=name, arguments=arguments)
    return asyncio.run(main.handle_call_tool(ctx, req))


def test_call_tool_requires_authenticated_user():
    result = _call("read_context")
    assert result.is_error
    assert result.content[0].text == "Error: Could not retrieve authentication state"


def test_call_tool_rejects_unknown_tool():
    result = _call("nope", user=USER)
    assert result.is_error
    assert result.content[0].text == "Unknown tool: nope"


def test_call_tool_tolerates_missing_arguments():
    result = _call("read_context", user=USER, arguments=None)
    assert result.is_error
    assert result.content[0].text == "Error: chat is required"


def test_call_tool_returns_handler_output(supabase, pinecone):
    result = _call("read_context", user=USER, arguments={"chat": "c", "query": "q"})
    assert not result.is_error
    assert result.content[0].text.startswith("Context Search Results:")
