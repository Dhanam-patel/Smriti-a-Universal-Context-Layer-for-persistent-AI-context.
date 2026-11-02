import pytest
from app.config import ConfigError, Settings, validate_settings

VALID_URL = "https://example.supabase.co"
VALID_KEY = "k" * 40
RESOURCE_URL = "https://mcp.example.com"
ISSUER_URL = "https://identity.example.com/realms/smriti"
JWKS_URL = "https://example.supabase.co/auth/v1/.well-known/jwks.json"


def _settings(**overrides) -> Settings:
    values = {
        "supabase_url": VALID_URL,
        "supabase_service_role_key": VALID_KEY,
        "mcp_resource_url": RESOURCE_URL,
        "oauth_issuer_url": ISSUER_URL,
        "oauth_jwks_url": JWKS_URL,
        **overrides,
    }
    return Settings(_env_file=None, **values)


def test_unrelated_env_file_keys_are_ignored(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"SUPABASE_URL={VALID_URL}\n"
        f"SUPABASE_SERVICE_ROLE_KEY={VALID_KEY}\n"
        f"MCP_RESOURCE_URL={RESOURCE_URL}\n"
        f"OAUTH_ISSUER_URL={ISSUER_URL}\n"
        f"OAUTH_JWKS_URL={JWKS_URL}\n"
        "UNRELATED_TOOL_SETTING=ignored-by-mcp\n"
    )

    settings = Settings(_env_file=env_file)

    assert settings.supabase_url == VALID_URL
    assert settings.supabase_service_role_key == VALID_KEY
    assert not hasattr(settings, "mcp_api_key")


def test_cors_defaults_to_any_origin():
    assert Settings(_env_file=None).cors_allowed_origins == ["*"]


def test_valid_settings_pass_validation():
    validate_settings(_settings())


@pytest.mark.parametrize("url", ["", "...", "example.supabase.co"])
def test_invalid_supabase_url_fails_fast(url):
    with pytest.raises(ConfigError, match="SUPABASE_URL"):
        validate_settings(_settings(supabase_url=url))


@pytest.mark.parametrize("key", ["", "..."])
def test_placeholder_service_key_fails_fast(key):
    with pytest.raises(ConfigError, match="SUPABASE_SERVICE_ROLE_KEY"):
        validate_settings(_settings(supabase_service_role_key=key))


def test_validation_error_never_includes_the_service_key():
    with pytest.raises(ConfigError) as exc:
        validate_settings(
            _settings(supabase_url="bad", supabase_service_role_key="s" * 5)
        )
    assert "sssss" not in str(exc.value)


@pytest.mark.parametrize("field", ["mcp_resource_url", "oauth_issuer_url", "oauth_jwks_url"])
def test_invalid_oauth_urls_fail_fast(field):
    with pytest.raises(ConfigError):
        validate_settings(_settings(**{field: "not-a-url"}))


def test_missing_jwks_url_fails_fast():
    with pytest.raises(ConfigError):
        validate_settings(_settings(oauth_jwks_url=""))
