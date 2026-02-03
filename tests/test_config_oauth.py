"""Unit tests for OAuth configuration in Config class."""

import pytest

from agent_skills_mcp.config import Config


class TestOAuthConfig:
    """Test OAuth configuration validation and helper methods."""

    def test_oauth_disabled_by_default(self):
        """OAuth should be disabled by default."""
        config = Config()
        assert config.oauth_enabled is False

    def test_get_oauth_scopes_empty_when_none(self):
        """get_oauth_scopes should return empty list when oauth_required_scopes is None."""
        config = Config(oauth_required_scopes=None)
        assert config.get_oauth_scopes() == []

    def test_get_oauth_scopes_empty_when_empty_string(self):
        """get_oauth_scopes should return empty list when oauth_required_scopes is empty."""
        config = Config(oauth_required_scopes="")
        assert config.get_oauth_scopes() == []

    def test_get_oauth_scopes_single_scope(self):
        """get_oauth_scopes should parse single scope correctly."""
        config = Config(oauth_required_scopes="openid")
        assert config.get_oauth_scopes() == ["openid"]

    def test_get_oauth_scopes_multiple_scopes(self):
        """get_oauth_scopes should parse comma-separated scopes correctly."""
        config = Config(oauth_required_scopes="openid, email, profile")
        assert config.get_oauth_scopes() == ["openid", "email", "profile"]

    def test_get_oauth_scopes_with_extra_whitespace(self):
        """get_oauth_scopes should handle extra whitespace."""
        config = Config(oauth_required_scopes="  openid  ,  email  ,  profile  ")
        assert config.get_oauth_scopes() == ["openid", "email", "profile"]

    def test_get_oauth_allowed_redirect_uris_none_allows_all(self):
        """None oauth_allowed_redirect_uris should return None (allow all)."""
        config = Config(oauth_allowed_redirect_uris=None)
        assert config.get_oauth_allowed_redirect_uris() is None

    def test_get_oauth_allowed_redirect_uris_empty_denies_all(self):
        """Empty oauth_allowed_redirect_uris should return empty list (deny all)."""
        config = Config(oauth_allowed_redirect_uris="")
        assert config.get_oauth_allowed_redirect_uris() == []

    def test_get_oauth_allowed_redirect_uris_single_uri(self):
        """get_oauth_allowed_redirect_uris should parse single URI correctly."""
        config = Config(oauth_allowed_redirect_uris="http://localhost:*")
        assert config.get_oauth_allowed_redirect_uris() == ["http://localhost:*"]

    def test_get_oauth_allowed_redirect_uris_multiple_uris(self):
        """get_oauth_allowed_redirect_uris should parse comma-separated URIs correctly."""
        config = Config(
            oauth_allowed_redirect_uris="https://claude.ai/*,https://*.anthropic.com/*"
        )
        assert config.get_oauth_allowed_redirect_uris() == [
            "https://claude.ai/*",
            "https://*.anthropic.com/*",
        ]

    def test_get_google_extra_params_empty_when_not_set(self):
        """get_google_extra_params should return empty dict when not set."""
        config = Config()
        assert config.get_google_extra_params() == {}

    def test_get_google_extra_params_access_type_only(self):
        """get_google_extra_params should return access_type when set."""
        config = Config(google_oauth_access_type="offline")
        assert config.get_google_extra_params() == {"access_type": "offline"}

    def test_get_google_extra_params_prompt_only(self):
        """get_google_extra_params should return prompt when set."""
        config = Config(google_oauth_prompt="consent")
        assert config.get_google_extra_params() == {"prompt": "consent"}

    def test_get_google_extra_params_both_set(self):
        """get_google_extra_params should return both access_type and prompt when set."""
        config = Config(
            google_oauth_access_type="offline",
            google_oauth_prompt="consent",
        )
        assert config.get_google_extra_params() == {
            "access_type": "offline",
            "prompt": "consent",
        }

    def test_validate_oauth_config_passes_when_disabled(self):
        """validate_oauth_config should pass when OAuth is disabled."""
        config = Config(oauth_enabled=False)
        config.validate_oauth_config()  # Should not raise

    def test_validate_oauth_config_passes_when_all_required_fields_set(self):
        """validate_oauth_config should pass when all required fields are set."""
        config = Config(
            oauth_enabled=True,
            oauth_config_url="https://accounts.google.com/.well-known/openid-configuration",
            oauth_client_id="client-id",
            oauth_client_secret="client-secret",
        )
        config.validate_oauth_config()  # Should not raise

    def test_validate_oauth_config_fails_when_config_url_missing(self):
        """validate_oauth_config should raise ValueError when oauth_config_url is missing."""
        config = Config(
            oauth_enabled=True,
            oauth_client_id="client-id",
            oauth_client_secret="client-secret",
        )
        with pytest.raises(ValueError, match="OAUTH_CONFIG_URL"):
            config.validate_oauth_config()

    def test_validate_oauth_config_fails_when_client_id_missing(self):
        """validate_oauth_config should raise ValueError when oauth_client_id is missing."""
        config = Config(
            oauth_enabled=True,
            oauth_config_url="https://accounts.google.com/.well-known/openid-configuration",
            oauth_client_secret="client-secret",
        )
        with pytest.raises(ValueError, match="OAUTH_CLIENT_ID"):
            config.validate_oauth_config()

    def test_validate_oauth_config_fails_when_client_secret_missing(self):
        """validate_oauth_config should raise ValueError when oauth_client_secret is missing."""
        config = Config(
            oauth_enabled=True,
            oauth_config_url="https://accounts.google.com/.well-known/openid-configuration",
            oauth_client_id="client-id",
        )
        with pytest.raises(ValueError, match="OAUTH_CLIENT_SECRET"):
            config.validate_oauth_config()

    def test_validate_oauth_config_fails_when_all_fields_missing(self):
        """validate_oauth_config should raise ValueError when all required fields are missing."""
        config = Config(oauth_enabled=True)
        with pytest.raises(ValueError) as exc_info:
            config.validate_oauth_config()

        error_message = str(exc_info.value)
        assert "OAUTH_CONFIG_URL" in error_message
        assert "OAUTH_CLIENT_ID" in error_message
        assert "OAUTH_CLIENT_SECRET" in error_message


class TestOAuthTokeninfoUrl:
    """Test get_oauth_tokeninfo_url method for opaque token verification."""

    def test_explicit_tokeninfo_url(self):
        """Explicit oauth_tokeninfo_url should be returned."""
        config = Config(
            oauth_tokeninfo_url="https://custom.provider/tokeninfo",
            oauth_config_url="https://accounts.google.com/.well-known/openid-configuration",
        )
        assert config.get_oauth_tokeninfo_url() == "https://custom.provider/tokeninfo"

    def test_google_autodetect(self):
        """Google tokeninfo URL should be auto-detected from config_url."""
        config = Config(
            oauth_config_url="https://accounts.google.com/.well-known/openid-configuration",
            oauth_tokeninfo_url=None,  # Explicitly unset to avoid .env override
        )
        assert (
            config.get_oauth_tokeninfo_url()
            == "https://oauth2.googleapis.com/tokeninfo"
        )

    def test_unknown_provider_returns_none(self):
        """Unknown providers should return None (use default JWT verification)."""
        config = Config(
            oauth_config_url="https://login.microsoftonline.com/tenant/v2.0/.well-known/openid-configuration",
            oauth_tokeninfo_url=None,  # Explicitly unset to avoid .env override
        )
        assert config.get_oauth_tokeninfo_url() is None

    def test_no_config_url_returns_none(self):
        """No config_url should return None."""
        config = Config(
            oauth_config_url=None,  # Explicitly unset to avoid .env override
            oauth_tokeninfo_url=None,  # Explicitly unset to avoid .env override
        )
        assert config.get_oauth_tokeninfo_url() is None
