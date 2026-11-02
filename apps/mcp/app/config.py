from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_KEY_LENGTH = 20


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    # JSON list in the environment, e.g. CORS_ALLOWED_ORIGINS='["https://app.example.com"]'.
    # Authentication is a Bearer header (no cookies), so credentialed CORS is not needed.
    cors_allowed_origins: list[str] = ["*"]

    # .env is shared with other tools (e.g. MCP_API_KEY for test_mcp.py), so ignore unknown keys.
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
    if problems:
        raise ConfigError("; ".join(problems) + ". Set them in apps/mcp/.env.")


settings = Settings()
