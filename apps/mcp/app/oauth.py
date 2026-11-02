"""Supabase OAuth 2.1 resource-server support for MCP HTTP endpoints."""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
import jwt
from fastapi import HTTPException, Request

from .config import Settings, settings

_ALLOWED_SIGNING_ALGORITHMS = ("RS256", "ES256")
_JWKS_CACHE_SECONDS = 300
_jwks_cache: dict[str, tuple[float, dict[str, Any]]] = {}


@dataclass(frozen=True)
class OAuthAccessToken:
    """Verified claims used to authorize a request to the MCP resource server."""

    subject: str
    client_id: str


def _normalise_url(value: str) -> str:
    parts = urlsplit(value)
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", "")
    )


def _metadata_url(resource_url: str) -> str:
    resource = urlsplit(_normalise_url(resource_url))
    origin = urlunsplit((resource.scheme, resource.netloc, "", "", ""))
    metadata_path = "/.well-known/oauth-protected-resource"
    if resource.path:
        metadata_path = f"{metadata_path}/{resource.path.lstrip('/')}"
    return f"{origin}{metadata_path}"


def protected_resource_metadata(current: Settings = settings) -> dict[str, object]:
    """Return RFC 9728 metadata that directs MCP clients to Supabase Auth."""
    return {
        "resource": _normalise_url(current.mcp_resource_url),
        "authorization_servers": [_normalise_url(current.oauth_issuer_url)],
        "bearer_methods_supported": ["header"],
    }


def bearer_challenge(current: Settings = settings, *, error: str | None = None) -> str:
    values = [
        'Bearer realm="mcp"',
        f'resource_metadata="{_metadata_url(current.mcp_resource_url)}"',
    ]
    if error:
        values.append(f'error="{error}"')
    return ", ".join(values)


def _unauthorized(current: Settings, *, error: str = "invalid_token") -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="OAuth access token is missing, invalid, expired, or not valid for this MCP server",
        headers={"WWW-Authenticate": bearer_challenge(current, error=error)},
    )


def _load_jwks(current: Settings) -> dict[str, Any]:
    """Fetch public signing keys and cache briefly to avoid a network call per tool call."""
    cached = _jwks_cache.get(current.oauth_jwks_url)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    try:
        response = httpx.get(
            current.oauth_jwks_url,
            timeout=httpx.Timeout(10.0, connect=5.0),
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        raise _unauthorized(current) from None
    if not isinstance(payload, dict) or not isinstance(payload.get("keys"), list):
        raise _unauthorized(current)
    _jwks_cache[current.oauth_jwks_url] = (
        time.monotonic() + _JWKS_CACHE_SECONDS,
        payload,
    )
    return payload


def _signing_key(token: str, current: Settings) -> Any:
    try:
        header = jwt.get_unverified_header(token)
        kid = header["kid"]
        algorithm = header["alg"]
    except (jwt.DecodeError, KeyError, TypeError):
        raise _unauthorized(current) from None
    if not isinstance(kid, str) or algorithm not in _ALLOWED_SIGNING_ALGORITHMS:
        raise _unauthorized(current)

    keys = _load_jwks(current)["keys"]
    matching_key = next(
        (key for key in keys if isinstance(key, dict) and key.get("kid") == kid), None
    )
    # Key rotation can leave a valid token's key absent from the short-lived
    # cache. Refresh once before rejecting it.
    if matching_key is None:
        _jwks_cache.pop(current.oauth_jwks_url, None)
        keys = _load_jwks(current)["keys"]
        matching_key = next(
            (key for key in keys if isinstance(key, dict) and key.get("kid") == kid),
            None,
        )
    if matching_key is None:
        raise _unauthorized(current)
    try:
        key = jwt.PyJWK.from_dict(matching_key)
    except (jwt.PyJWKError, jwt.InvalidKeyError, ValueError):
        raise _unauthorized(current) from None
    if key.algorithm_name != algorithm:
        raise _unauthorized(current)
    return key.key


def verify_access_token(token: str, current: Settings = settings) -> OAuthAccessToken:
    """Verify a Supabase OAuth JWT's signature, issuer, audience, and identity."""
    try:
        claims = jwt.decode(
            token,
            _signing_key(token, current),
            algorithms=list(_ALLOWED_SIGNING_ALGORITHMS),
            audience=[
                _normalise_url(current.mcp_resource_url),
                f"{_normalise_url(current.mcp_resource_url)}/",
            ],
            issuer=_normalise_url(current.oauth_issuer_url),
            options={"require": ["exp", "iat", "iss", "aud", "sub", "client_id"]},
        )
    except jwt.PyJWTError:
        raise _unauthorized(current) from None
    if not isinstance(claims, Mapping):
        raise _unauthorized(current)
    subject = claims.get("sub")
    client_id = claims.get("client_id")
    if not isinstance(subject, str) or not subject or not isinstance(client_id, str) or not client_id:
        raise _unauthorized(current)
    return OAuthAccessToken(subject=subject, client_id=client_id)


def authenticate_oauth_request(
    request: Request, current: Settings = settings
) -> OAuthAccessToken:
    """Extract and verify a bearer access token; called off the event loop."""
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized(current, error="invalid_request")
    return verify_access_token(token, current)
