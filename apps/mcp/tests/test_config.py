from app.config import Settings


def test_unrelated_env_file_keys_are_ignored(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SUPABASE_URL=https://example.supabase.co\n"
        "SUPABASE_SERVICE_ROLE_KEY=service-key\n"
        "MCP_API_KEY=used-by-test_mcp-only\n"
    )

    settings = Settings(_env_file=env_file)

    assert settings.supabase_url == "https://example.supabase.co"
    assert settings.supabase_service_role_key == "service-key"
    assert not hasattr(settings, "mcp_api_key")


def test_cors_defaults_to_any_origin():
    assert Settings(_env_file=None).cors_allowed_origins == ["*"]
