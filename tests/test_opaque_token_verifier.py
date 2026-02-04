"""Unit tests for OpaqueTokenVerifier and GoogleTokenVerifier."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_skills_mcp.auth import GoogleTokenVerifier, OpaqueTokenVerifier


@pytest.mark.unit
class TestOpaqueTokenVerifier:
    """Test OpaqueTokenVerifier for generic opaque token verification."""

    @pytest.fixture
    def verifier(self):
        """Create a verifier instance for testing."""
        return OpaqueTokenVerifier(
            tokeninfo_url="https://example.com/tokeninfo",
            client_id="test-client-id",
            required_scopes=["openid", "email"],
        )

    @pytest.fixture
    def verifier_no_scopes(self):
        """Create a verifier instance without required scopes."""
        return OpaqueTokenVerifier(
            tokeninfo_url="https://example.com/tokeninfo",
            client_id="test-client-id",
        )

    def test_required_scopes_property(self, verifier):
        """Test required_scopes property returns configured scopes."""
        assert verifier.required_scopes == ["openid", "email"]

    def test_required_scopes_empty_by_default(self, verifier_no_scopes):
        """Test required_scopes returns empty list when not configured."""
        assert verifier_no_scopes.required_scopes == []

    @pytest.mark.asyncio
    async def test_verify_valid_token(self, verifier):
        """Test verification of a valid token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "test-client-id",
            "expires_in": "3600",
            "scope": "openid email profile",
            "email": "test@example.com",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier.verify_token("valid-token")

            assert result is not None
            assert result.client_id == "test@example.com"
            assert "openid" in result.scopes
            assert "email" in result.scopes
            assert "profile" in result.scopes
            assert result.token == "valid-token"
            assert result.expires_at is not None

    @pytest.mark.asyncio
    async def test_verify_token_with_azp_claim(self, verifier):
        """Test verification when client ID is in 'azp' claim instead of 'aud'."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "azp": "test-client-id",  # Using azp instead of aud
            "expires_in": "3600",
            "scope": "openid email",
            "sub": "user-123",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier.verify_token("valid-token")

            assert result is not None
            assert result.client_id == "user-123"

    @pytest.mark.asyncio
    async def test_verify_expired_token(self, verifier):
        """Test verification of an expired token returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "test-client-id",
            "expires_in": "0",  # Expired
            "scope": "openid email",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier.verify_token("expired-token")

            assert result is None

    @pytest.mark.asyncio
    async def test_verify_negative_expiry_token(self, verifier):
        """Test verification of a token with negative expiry returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "test-client-id",
            "expires_in": "-100",  # Negative
            "scope": "openid email",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier.verify_token("expired-token")

            assert result is None

    @pytest.mark.asyncio
    async def test_verify_invalid_client_id(self, verifier):
        """Test verification fails for wrong client ID."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "different-client-id",  # Wrong client
            "expires_in": "3600",
            "scope": "openid email",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier.verify_token("token")

            assert result is None

    @pytest.mark.asyncio
    async def test_verify_missing_required_scopes(self, verifier):
        """Test verification fails when required scopes are missing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "test-client-id",
            "expires_in": "3600",
            "scope": "openid",  # Missing 'email' scope
            "email": "test@example.com",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier.verify_token("token")

            assert result is None

    @pytest.mark.asyncio
    async def test_verify_token_without_required_scopes(self, verifier_no_scopes):
        """Test verification succeeds when no scopes are required."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "test-client-id",
            "expires_in": "3600",
            "scope": "",
            "sub": "user-123",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier_no_scopes.verify_token("token")

            assert result is not None
            assert result.scopes == []

    @pytest.mark.asyncio
    async def test_verify_token_http_error(self, verifier):
        """Test verification returns None on HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 400

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier.verify_token("invalid-token")

            assert result is None

    @pytest.mark.asyncio
    async def test_verify_token_network_error(self, verifier):
        """Test verification returns None on network error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Network error")

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier.verify_token("token")

            assert result is None

    @pytest.mark.asyncio
    async def test_verify_token_no_expiry(self, verifier_no_scopes):
        """Test verification succeeds when expiry is not provided."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "test-client-id",
            # No expires_in
            "scope": "openid",
            "email": "test@example.com",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier_no_scopes.verify_token("token")

            assert result is not None
            assert result.expires_at is None

    @pytest.mark.asyncio
    async def test_verify_token_unknown_user(self, verifier_no_scopes):
        """Test verification uses 'unknown' when no user ID claims present."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "test-client-id",
            "expires_in": "3600",
            "scope": "openid",
            # No email or sub
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier_no_scopes.verify_token("token")

            assert result is not None
            assert result.client_id == "unknown"


@pytest.mark.unit
class TestOpaqueTokenVerifierScopeAliases:
    """Test OpaqueTokenVerifier scope alias functionality."""

    @pytest.fixture
    def verifier_with_aliases(self):
        """Create a verifier with scope aliases for testing."""
        return OpaqueTokenVerifier(
            tokeninfo_url="https://example.com/tokeninfo",
            client_id="test-client-id",
            required_scopes=["openid", "email", "profile"],
            scope_aliases={
                "email": ["https://www.googleapis.com/auth/userinfo.email"],
                "profile": ["https://www.googleapis.com/auth/userinfo.profile"],
            },
        )

    @pytest.mark.asyncio
    async def test_scope_alias_matching(self, verifier_with_aliases):
        """Test that scope aliases are correctly matched."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "test-client-id",
            "expires_in": "3600",
            # Google returns full URIs for email and profile scopes
            "scope": "openid https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile",
            "email": "test@example.com",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier_with_aliases.verify_token("valid-token")

            # Should succeed because aliases map "email" -> full URI
            assert result is not None
            assert result.client_id == "test@example.com"

    @pytest.mark.asyncio
    async def test_scope_direct_match_takes_precedence(self, verifier_with_aliases):
        """Test that direct scope match works even with aliases configured."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "test-client-id",
            "expires_in": "3600",
            # Direct scope names (not URIs)
            "scope": "openid email profile",
            "email": "test@example.com",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier_with_aliases.verify_token("valid-token")

            assert result is not None

    @pytest.mark.asyncio
    async def test_scope_alias_partial_match(self, verifier_with_aliases):
        """Test that partial alias match fails correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "test-client-id",
            "expires_in": "3600",
            # Missing profile scope (neither direct nor alias)
            "scope": "openid https://www.googleapis.com/auth/userinfo.email",
            "email": "test@example.com",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier_with_aliases.verify_token("valid-token")

            # Should fail because "profile" scope is missing
            assert result is None

    @pytest.mark.asyncio
    async def test_no_aliases_configured(self):
        """Test that verification works without aliases when scopes match directly."""
        verifier = OpaqueTokenVerifier(
            tokeninfo_url="https://example.com/tokeninfo",
            client_id="test-client-id",
            required_scopes=["openid", "email"],
            # No scope_aliases
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "test-client-id",
            "expires_in": "3600",
            "scope": "openid email",
            "email": "test@example.com",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier.verify_token("valid-token")

            assert result is not None

    @pytest.mark.asyncio
    async def test_multiple_aliases_for_scope(self):
        """Test that multiple aliases for a single scope work."""
        verifier = OpaqueTokenVerifier(
            tokeninfo_url="https://example.com/tokeninfo",
            client_id="test-client-id",
            required_scopes=["read"],
            scope_aliases={
                "read": [
                    "https://api.example.com/read",
                    "https://api.example.com/readonly",
                ],
            },
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "test-client-id",
            "expires_in": "3600",
            # Second alias matches
            "scope": "https://api.example.com/readonly",
            "sub": "user-123",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier.verify_token("valid-token")

            assert result is not None


@pytest.mark.unit
class TestOpaqueTokenVerifierCustomClaims:
    """Test OpaqueTokenVerifier with custom claim configurations."""

    @pytest.mark.asyncio
    async def test_custom_client_id_claim(self):
        """Test verification with custom client ID claim name."""
        verifier = OpaqueTokenVerifier(
            tokeninfo_url="https://example.com/tokeninfo",
            client_id="test-client-id",
            client_id_claim="client_id",  # Custom claim name
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "client_id": "test-client-id",  # Using custom claim
            "expires_in": "3600",
            "scope": "openid",
            "email": "test@example.com",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier.verify_token("token")

            assert result is not None

    @pytest.mark.asyncio
    async def test_custom_scope_claim(self):
        """Test verification with custom scope claim name."""
        verifier = OpaqueTokenVerifier(
            tokeninfo_url="https://example.com/tokeninfo",
            client_id="test-client-id",
            scope_claim="scp",  # Custom claim name
            required_scopes=["read"],
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "test-client-id",
            "expires_in": "3600",
            "scp": "read write",  # Using custom claim
            "sub": "user-123",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier.verify_token("token")

            assert result is not None
            assert "read" in result.scopes
            assert "write" in result.scopes

    @pytest.mark.asyncio
    async def test_custom_user_id_claims(self):
        """Test verification with custom user ID claim order."""
        verifier = OpaqueTokenVerifier(
            tokeninfo_url="https://example.com/tokeninfo",
            client_id="test-client-id",
            user_id_claims=["username", "id"],  # Custom claim order
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "test-client-id",
            "expires_in": "3600",
            "scope": "openid",
            "username": "testuser",
            "id": "12345",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier.verify_token("token")

            assert result is not None
            assert result.client_id == "testuser"  # First matching claim


@pytest.mark.unit
class TestGoogleTokenVerifier:
    """Test GoogleTokenVerifier convenience class."""

    def test_uses_google_tokeninfo_url(self):
        """Test that GoogleTokenVerifier uses Google's tokeninfo endpoint."""
        verifier = GoogleTokenVerifier(client_id="test-client-id")
        assert verifier._tokeninfo_url == "https://oauth2.googleapis.com/tokeninfo"

    def test_required_scopes_passed_through(self):
        """Test that required_scopes are properly configured."""
        verifier = GoogleTokenVerifier(
            client_id="test-client-id",
            required_scopes=["openid", "email"],
        )
        assert verifier.required_scopes == ["openid", "email"]

    def test_has_google_scope_aliases(self):
        """Test that GoogleTokenVerifier has Google scope aliases configured."""
        verifier = GoogleTokenVerifier(client_id="test-client-id")
        assert "email" in verifier._scope_aliases
        assert "profile" in verifier._scope_aliases
        assert (
            "https://www.googleapis.com/auth/userinfo.email"
            in verifier._scope_aliases["email"]
        )
        assert (
            "https://www.googleapis.com/auth/userinfo.profile"
            in verifier._scope_aliases["profile"]
        )

    @pytest.mark.asyncio
    async def test_verify_google_token(self):
        """Test verification of a Google token."""
        verifier = GoogleTokenVerifier(
            client_id="test-client-id.apps.googleusercontent.com",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aud": "test-client-id.apps.googleusercontent.com",
            "expires_in": "3600",
            "scope": "openid email profile",
            "email": "user@gmail.com",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier.verify_token("google-access-token")

            assert result is not None
            assert result.client_id == "user@gmail.com"
            mock_client.get.assert_called_once_with(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"access_token": "google-access-token"},
            )

    @pytest.mark.asyncio
    async def test_verify_google_token_with_full_scope_uris(self):
        """Test verification with Google's full scope URIs (real tokeninfo response).

        This test simulates the actual Google tokeninfo response format,
        where scopes are returned as full URIs instead of short names.
        """
        verifier = GoogleTokenVerifier(
            client_id="test-client-id.apps.googleusercontent.com",
            required_scopes=["openid", "email", "profile"],
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        # This is what Google's tokeninfo actually returns
        mock_response.json.return_value = {
            "aud": "test-client-id.apps.googleusercontent.com",
            "expires_in": "3600",
            "scope": "openid https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile",
            "email": "user@gmail.com",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await verifier.verify_token("google-access-token")

            # Should succeed because GoogleTokenVerifier has scope aliases
            assert result is not None
            assert result.client_id == "user@gmail.com"
