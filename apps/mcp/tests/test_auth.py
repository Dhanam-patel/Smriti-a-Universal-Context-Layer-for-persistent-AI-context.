from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from app import auth
from app.auth import AuthenticatedUser, PineconeConnection
from app.oauth import OAuthAccessToken
from fastapi import HTTPException


def _request(authorization=None):
    headers = {} if authorization is None else {"Authorization": authorization}
    return SimpleNamespace(headers=headers)


def _fake_supabase(pinecone_rows=()):
    sb = MagicMock()
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.execute.return_value = SimpleNamespace(data=list(pinecone_rows))
    sb.table.return_value = query
    return sb, query


def test_oauth_subject_resolves_to_the_matching_smriti_user():
    sb, query = _fake_supabase(
        [{"index_name": "idx", "encrypted_api_key": "pc-key", "embedding_model": None}]
    )
    token = OAuthAccessToken(subject="u1", client_id="oauth-client")

    with (
        patch.object(auth, "authenticate_oauth_request", return_value=token),
        patch.object(auth, "get_supabase", return_value=sb),
    ):
        user = auth.authenticate_mcp_client(_request("Bearer access-token"))

    assert user == AuthenticatedUser("u1", PineconeConnection("idx", "pc-key", None))
    query.eq.assert_called_once_with("user_id", "u1")


def test_missing_pinecone_configuration_is_400():
    sb, _ = _fake_supabase()
    token = OAuthAccessToken(subject="u1", client_id="oauth-client")
    with (
        patch.object(auth, "authenticate_oauth_request", return_value=token),
        patch.object(auth, "get_supabase", return_value=sb),
        pytest.raises(HTTPException) as exc,
    ):
        auth.authenticate_mcp_client(_request("Bearer access-token"))
    assert exc.value.status_code == 400
