"""Unit tests for Bearer Token Authentication Provider."""

from unittest.mock import AsyncMock, Mock

import pytest

from agent_skills_mcp.auth.bearer_token_auth import BearerTokenAuthProvider


def _make_access_token(**kwargs):
    """Create a mock AccessToken."""
    token = Mock()
    token.token = kwargs.get("token", "test-token")
    token.client_id = kwargs.get("client_id", "test-client")
    token.scopes = kwargs.get("scopes", ["openid", "email"])
    token.expires_at = kwargs.get("expires_at", None)
    return token


@pytest.mark.unit
class TestBearerTokenAuthProvider:
    """Test BearerTokenAuthProvider."""

    def test_init_from_oidc_proxy(self):
        """Test initialization delegates base_url and scopes from oidc_proxy."""
        mock_verifier = Mock()
        mock_oidc_proxy = Mock()
        mock_oidc_proxy.base_url = "http://localhost:8080"
        mock_oidc_proxy.required_scopes = ["openid", "email"]

        provider = BearerTokenAuthProvider(
            token_verifier=mock_verifier,
            oidc_proxy=mock_oidc_proxy,
        )

        assert provider.required_scopes == ["openid", "email"]

    @pytest.mark.asyncio
    async def test_external_token_success(self):
        """Test successful external Bearer token verification."""
        access_token = _make_access_token()

        mock_verifier = AsyncMock()
        mock_verifier.verify_token = AsyncMock(return_value=access_token)

        mock_oidc_proxy = Mock()
        mock_oidc_proxy.base_url = None
        mock_oidc_proxy.required_scopes = []

        provider = BearerTokenAuthProvider(
            token_verifier=mock_verifier,
            oidc_proxy=mock_oidc_proxy,
        )

        result = await provider.verify_token("external-google-token")

        assert result is access_token
        mock_verifier.verify_token.assert_called_once_with("external-google-token")

    @pytest.mark.asyncio
    async def test_external_fails_oidc_succeeds(self):
        """Test fallback to OIDCProxy when external verification fails."""
        access_token = _make_access_token()

        mock_verifier = AsyncMock()
        mock_verifier.verify_token = AsyncMock(return_value=None)

        mock_oidc_proxy = AsyncMock()
        mock_oidc_proxy.base_url = None
        mock_oidc_proxy.required_scopes = []
        mock_oidc_proxy.verify_token = AsyncMock(return_value=access_token)

        provider = BearerTokenAuthProvider(
            token_verifier=mock_verifier,
            oidc_proxy=mock_oidc_proxy,
        )

        result = await provider.verify_token("fastmcp-jwt-token")

        assert result is access_token
        mock_verifier.verify_token.assert_called_once_with("fastmcp-jwt-token")
        mock_oidc_proxy.verify_token.assert_called_once_with("fastmcp-jwt-token")

    @pytest.mark.asyncio
    async def test_external_exception_falls_back_to_oidc(self):
        """Test fallback when external verifier raises exception."""
        access_token = _make_access_token()

        mock_verifier = AsyncMock()
        mock_verifier.verify_token = AsyncMock(side_effect=Exception("Token invalid"))

        mock_oidc_proxy = AsyncMock()
        mock_oidc_proxy.base_url = None
        mock_oidc_proxy.required_scopes = []
        mock_oidc_proxy.verify_token = AsyncMock(return_value=access_token)

        provider = BearerTokenAuthProvider(
            token_verifier=mock_verifier,
            oidc_proxy=mock_oidc_proxy,
        )

        result = await provider.verify_token("fastmcp-jwt-token")

        assert result is access_token

    @pytest.mark.asyncio
    async def test_both_verification_fail(self):
        """Test that None is returned when both verifications fail."""
        mock_verifier = AsyncMock()
        mock_verifier.verify_token = AsyncMock(return_value=None)

        mock_oidc_proxy = AsyncMock()
        mock_oidc_proxy.base_url = None
        mock_oidc_proxy.required_scopes = []
        mock_oidc_proxy.verify_token = AsyncMock(side_effect=Exception("JWT invalid"))

        provider = BearerTokenAuthProvider(
            token_verifier=mock_verifier,
            oidc_proxy=mock_oidc_proxy,
        )

        result = await provider.verify_token("invalid-token")

        assert result is None

    def test_get_routes_delegates_to_oidc_proxy(self):
        """Test that get_routes delegates to oidc_proxy."""
        mock_verifier = Mock()
        mock_oidc_proxy = Mock()
        mock_oidc_proxy.base_url = None
        mock_oidc_proxy.required_scopes = []
        mock_oidc_proxy.get_routes.return_value = ["route1", "route2"]

        provider = BearerTokenAuthProvider(
            token_verifier=mock_verifier,
            oidc_proxy=mock_oidc_proxy,
        )

        routes = provider.get_routes("/mcp")

        assert routes == ["route1", "route2"]
        mock_oidc_proxy.get_routes.assert_called_once_with("/mcp")

    def test_get_middleware_returns_auth_middleware(self):
        """Test that get_middleware returns proper auth middleware."""
        mock_verifier = Mock()
        mock_oidc_proxy = Mock()
        mock_oidc_proxy.base_url = None
        mock_oidc_proxy.required_scopes = []

        provider = BearerTokenAuthProvider(
            token_verifier=mock_verifier,
            oidc_proxy=mock_oidc_proxy,
        )

        middleware = provider.get_middleware()

        # Should return 2 middleware: AuthenticationMiddleware + AuthContextMiddleware
        assert len(middleware) == 2

    def test_set_mcp_path_delegates_to_both(self):
        """Test that set_mcp_path is called on both self and oidc_proxy."""
        mock_verifier = Mock()
        mock_oidc_proxy = Mock()
        mock_oidc_proxy.base_url = None
        mock_oidc_proxy.required_scopes = []

        provider = BearerTokenAuthProvider(
            token_verifier=mock_verifier,
            oidc_proxy=mock_oidc_proxy,
        )

        provider.set_mcp_path("/mcp")

        mock_oidc_proxy.set_mcp_path.assert_called_once_with("/mcp")
