from unittest.mock import MagicMock, patch

import jwt
import pytest
from app.config import Settings
from app.oauth import (
    _jwks_cache,
    _load_jwks,
    authenticate_oauth_request,
    protected_resource_metadata,
    verify_access_token,
)
from fastapi import HTTPException
from starlette.requests import Request


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        supabase_url="https://project.supabase.co",
        supabase_service_role_key="x" * 40,
        mcp_resource_url="https://mcp.example.com/mcp",
        oauth_issuer_url="https://project.supabase.co/auth/v1",
        oauth_jwks_url="https://project.supabase.co/auth/v1/.well-known/jwks.json",
    )


def _request(header: str | None = None) -> Request:
    headers = [] if header is None else [(b"authorization", header.encode())]
    return Request(
        {"type": "http", "method": "GET", "path": "/mcp", "headers": headers}
    )


def _claims(**overrides):
    return {
        "iss": "https://project.supabase.co/auth/v1",
        "aud": "https://mcp.example.com/mcp",
        "sub": "supabase-user-id",
        "client_id": "mcp-client-id",
        "iat": 1,
        "exp": 9999999999,
        **overrides,
    }


def test_protected_resource_metadata_advertises_supabase_auth_server():
    assert protected_resource_metadata(_settings()) == {
        "resource": "https://mcp.example.com/mcp",
        "authorization_servers": ["https://project.supabase.co/auth/v1"],
        "bearer_methods_supported": ["header"],
    }


def test_missing_bearer_token_returns_discovery_challenge():
    with pytest.raises(HTTPException) as exc:
        authenticate_oauth_request(_request(), _settings())

    assert exc.value.status_code == 401
    assert 'realm="mcp"' in exc.value.headers["WWW-Authenticate"]
    assert "resource_metadata=\"https://mcp.example.com/.well-known/oauth-protected-resource/mcp\"" in exc.value.headers["WWW-Authenticate"]


def test_valid_jwt_claims_are_accepted_with_expected_issuer_and_audience():
    current = _settings()
    with (
        patch("app.oauth._signing_key", return_value="public-key"),
        patch("app.oauth.jwt.decode", return_value=_claims()) as decode,
    ):
        access_token = verify_access_token("access-token", current)

    assert access_token.subject == "supabase-user-id"
    assert access_token.client_id == "mcp-client-id"
    assert decode.call_args.kwargs["audience"] == [
        "https://mcp.example.com/mcp",
        "https://mcp.example.com/mcp/",
    ]
    assert decode.call_args.kwargs["issuer"] == "https://project.supabase.co/auth/v1"


@pytest.mark.parametrize(
    "claims",
    [
        _claims(sub=""),
        _claims(client_id=""),
    ],
)
def test_rejects_missing_client_identity(claims):
    with (
        patch("app.oauth._signing_key", return_value="public-key"),
        patch("app.oauth.jwt.decode", return_value=claims),
        pytest.raises(HTTPException) as exc,
    ):
        verify_access_token("access-token", _settings())
    assert exc.value.status_code == 401


@pytest.mark.parametrize("jwt_error", [jwt.ExpiredSignatureError, jwt.InvalidAudienceError])
def test_rejects_invalid_jwt_signature_expiry_or_audience(jwt_error):
    with (
        patch("app.oauth._signing_key", return_value="public-key"),
        patch("app.oauth.jwt.decode", side_effect=jwt_error),
        pytest.raises(HTTPException) as exc,
    ):
        verify_access_token("access-token", _settings())
    assert exc.value.status_code == 401


def test_jwks_response_is_cached():
    current = _settings()
    _jwks_cache.clear()
    response = MagicMock()
    response.json.return_value = {"keys": [{"kid": "key-1"}]}
    with patch("app.oauth.httpx.get", return_value=response) as get:
        assert _load_jwks(current) == {"keys": [{"kid": "key-1"}]}
        assert _load_jwks(current) == {"keys": [{"kid": "key-1"}]}
    get.assert_called_once()
