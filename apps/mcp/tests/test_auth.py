import hashlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from app import auth
from app.auth import AuthenticatedUser, PineconeConnection
from fastapi import HTTPException

TOKEN = "smr_secret"


def _request(authorization=None):
    headers = {} if authorization is None else {"Authorization": authorization}
    return SimpleNamespace(headers=headers)


def _fake_supabase(mcp_rows, pinecone_rows=()):
    """Builds a client whose table() returns rows keyed by table name."""
    rows = {
        "mcp_connections": list(mcp_rows),
        "pinecone_connections": list(pinecone_rows),
    }
    sb = MagicMock()
    sb.queries = {}

    def table(name):
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.execute.return_value = SimpleNamespace(data=rows[name])
        sb.queries[name] = query
        return query

    sb.table.side_effect = table
    return sb


def _authenticate(sb, authorization=f"Bearer {TOKEN}"):
    with patch.object(auth, "get_supabase", return_value=sb):
        return auth.authenticate_mcp_client(_request(authorization))


@pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer"])
def test_missing_or_malformed_header_is_401(header):
    with pytest.raises(HTTPException) as exc:
        _authenticate(_fake_supabase([]), authorization=header)
    assert exc.value.status_code == 401


def test_unknown_credential_is_401():
    with pytest.raises(HTTPException) as exc:
        _authenticate(_fake_supabase([]))
    assert exc.value.status_code == 401


def test_inactive_connection_is_403():
    sb = _fake_supabase([{"user_id": "u1", "status": "revoked"}])
    with pytest.raises(HTTPException) as exc:
        _authenticate(sb)
    assert exc.value.status_code == 403


def test_missing_pinecone_configuration_is_400():
    sb = _fake_supabase([{"user_id": "u1", "status": auth.STATUS_ACTIVE}])
    with pytest.raises(HTTPException) as exc:
        _authenticate(sb)
    assert exc.value.status_code == 400


def test_valid_credential_returns_typed_user_and_looks_up_hash():
    sb = _fake_supabase(
        [{"user_id": "u1", "status": auth.STATUS_ACTIVE}],
        [{"index_name": "idx", "encrypted_api_key": "pc-key", "embedding_model": None}],
    )

    user = _authenticate(sb)

    assert user == AuthenticatedUser("u1", PineconeConnection("idx", "pc-key", None))
    expected_hash = hashlib.sha256(TOKEN.encode()).hexdigest()
    sb.queries["mcp_connections"].eq.assert_called_once_with(
        "credential_hash", expected_hash
    )
    sb.queries["pinecone_connections"].eq.assert_called_once_with("user_id", "u1")
    sb.queries["pinecone_connections"].eq.assert_called_once_with("user_id", "u1")
