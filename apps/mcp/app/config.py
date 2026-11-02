from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_KEY_LENGTH = 20


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    # Public, canonical URL of this resource server. This must match the OAuth
    # access token's `aud` claim (apart from a trailing slash).
    mcp_resource_url: str = ""
    # Supabase Auth acts as the OAuth 2.1 authorization server. The MCP server
    # validates its asymmetric JWTs against the project's public JWKS endpoint.
    oauth_issuer_url: str = ""
    oauth_jwks_url: str = ""
    # JSON list in the environment, e.g. CORS_ALLOWED_ORIGINS='["https://app.example.com"]'.
    # Authentication is a Bearer header (no cookies), so credentialed CORS is not needed.
    cors_allowed_origins: list[str] = ["*"]

    # .env is shared with other tools, so ignore unknown keys.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class ConfigError(RuntimeError):
    """Raised at startup when required configuration is missing or still a placeholder."""


def validate_settings(current: Settings) -> None:
    """Fails fast with an actionable message instead of a 500 on the first request."""
    problems = []
    if not current.supabase_url.startswith(("http://", "https://")):
        problems.append(
            f"SUPABASE_URL must be an http(s) URL (got {current.supabase_url!r})"
        )
    if len(current.supabase_service_role_key) < MIN_KEY_LENGTH:
        problems.append(
            "SUPABASE_SERVICE_ROLE_KEY is missing or looks like a placeholder"
        )
    if not current.mcp_resource_url.startswith(("http://", "https://")):
        problems.append("MCP_RESOURCE_URL must be an http(s) URL")
    if not current.oauth_issuer_url.startswith(("http://", "https://")):
        problems.append("OAUTH_ISSUER_URL must be an http(s) URL")
    if not current.oauth_jwks_url.startswith(("http://", "https://")):
        problems.append("OAUTH_JWKS_URL must be an http(s) URL")
    if problems:
        raise ConfigError("; ".join(problems) + ". Set them in apps/mcp/.env.")


settings = Settings()
