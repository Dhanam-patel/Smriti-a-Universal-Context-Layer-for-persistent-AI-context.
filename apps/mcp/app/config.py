from pydantic_settings import BaseSettings, SettingsConfigDict


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


settings = Settings()
