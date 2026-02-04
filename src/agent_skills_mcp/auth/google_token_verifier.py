"""OAuth access token verifiers for opaque (non-JWT) tokens."""

import logging
import time

import httpx
from fastmcp.server.auth import AccessToken, TokenVerifier

logger = logging.getLogger(__name__)

# Well-known tokeninfo endpoints for major providers
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"

# Well-known scope aliases (short name -> full scope URIs)
# Used to map user-friendly scope names to provider-specific full URIs
GOOGLE_SCOPE_ALIASES: dict[str, list[str]] = {
    "email": ["https://www.googleapis.com/auth/userinfo.email"],
    "profile": ["https://www.googleapis.com/auth/userinfo.profile"],
}


class OpaqueTokenVerifier(TokenVerifier):
    """TokenVerifier for opaque (non-JWT) OAuth access tokens.

    Many OAuth providers (including Google) issue access tokens that are opaque
    tokens rather than JWTs. These cannot be verified using standard JWT verification.
    Instead, they must be validated using the provider's tokeninfo/introspection endpoint.

    This verifier is generic and can be used with any OAuth provider that supports
    a tokeninfo endpoint returning JSON with standard claims.
    """

    def __init__(
        self,
        *,
        tokeninfo_url: str,
        client_id: str,
        required_scopes: list[str] | None = None,
        timeout_seconds: int = 30,
        client_id_claim: str | None = None,
        scope_claim: str = "scope",
        expiry_claim: str = "expires_in",
        user_id_claims: list[str] | None = None,
        scope_aliases: dict[str, list[str]] | None = None,
    ):
        """Initialize the opaque token verifier.

        Args:
            tokeninfo_url: URL of the tokeninfo/introspection endpoint
            client_id: The OAuth client ID (used to verify the token was issued for this app)
            required_scopes: Optional list of required scopes
            timeout_seconds: HTTP request timeout
            client_id_claim: Claim name for client ID validation (default: tries "aud" then "azp")
            scope_claim: Claim name for scopes (default: "scope")
            expiry_claim: Claim name for token expiration in seconds (default: "expires_in")
            user_id_claims: Claim names to try for user ID extraction (default: ["email", "sub"])
            scope_aliases: Mapping of short scope names to full scope URIs.
                          Used to match required scopes like "email" to full URIs like
                          "https://www.googleapis.com/auth/userinfo.email".
        """
        self._tokeninfo_url = tokeninfo_url
        self._client_id = client_id
        self._required_scopes = required_scopes or []
        self._timeout = timeout_seconds
        self._client_id_claim = client_id_claim
        self._scope_claim = scope_claim
        self._expiry_claim = expiry_claim
        self._user_id_claims = user_id_claims or ["email", "sub"]
        self._scope_aliases = scope_aliases or {}

    @property
    def required_scopes(self) -> list[str]:
        """Return the required scopes for this verifier."""
        return self._required_scopes

    def _extract_client_id(self, data: dict) -> str | None:
        """Extract client ID from tokeninfo response."""
        if self._client_id_claim:
            return data.get(self._client_id_claim)
        # Default: try "aud" then "azp" (Google's convention)
        return data.get("aud") or data.get("azp")

    def _extract_user_id(self, data: dict) -> str:
        """Extract user ID from tokeninfo response."""
        for claim in self._user_id_claims:
            if value := data.get(claim):
                return str(value)
        return "unknown"

    def _extract_scopes(self, data: dict) -> list[str]:
        """Extract scopes from tokeninfo response."""
        scope_str = data.get(self._scope_claim, "")
        return scope_str.split() if scope_str else []

    def _extract_expiry(self, data: dict) -> int | None:
        """Extract expiration time from tokeninfo response."""
        expires_in = data.get(self._expiry_claim)
        if expires_in is not None:
            expires_in = int(expires_in)
            if expires_in <= 0:
                return 0  # Indicates expired
            return int(time.time()) + expires_in
        return None

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify an OAuth access token using the tokeninfo endpoint.

        Args:
            token: The access token to verify

        Returns:
            AccessToken if valid, None otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    self._tokeninfo_url,
                    params={"access_token": token},
                )

                if response.status_code != 200:
                    logger.debug(
                        "Tokeninfo request failed with status %d", response.status_code
                    )
                    return None

                data = response.json()
                logger.debug("Tokeninfo response: %s", data)

                # Verify the token was issued for our client
                token_client_id = self._extract_client_id(data)
                if token_client_id != self._client_id:
                    logger.debug(
                        "Client ID mismatch: expected '%s', got '%s'",
                        self._client_id,
                        token_client_id,
                    )
                    return None

                # Check token expiration
                expires_at = self._extract_expiry(data)
                if expires_at == 0:  # Expired
                    logger.debug("Token has expired")
                    return None

                # Extract scopes
                scopes = self._extract_scopes(data)

                # Check required scopes (with alias support)
                if self._required_scopes:
                    token_scopes = set(scopes)
                    for required_scope in self._required_scopes:
                        # Check if the required scope is directly present
                        if required_scope in token_scopes:
                            continue
                        # Check if any alias for this scope is present
                        aliases = self._scope_aliases.get(required_scope, [])
                        if not any(alias in token_scopes for alias in aliases):
                            logger.debug(
                                "Required scope '%s' not found in token scopes: %s "
                                "(aliases checked: %s)",
                                required_scope,
                                token_scopes,
                                aliases,
                            )
                            return None

                # Extract user ID
                user_id = self._extract_user_id(data)

                # IMPORTANT: Enrich scopes with short names for FastMCP compatibility
                #
                # Problem: Some OAuth providers (like Google) return scopes as full URIs
                # (e.g., "https://www.googleapis.com/auth/userinfo.email"), but FastMCP
                # may compare these against the short names in required_scopes (e.g., "email").
                #
                # Solution: Add short names to AccessToken.scopes so that FastMCP's scope
                # validation can match both formats. This ensures compatibility without
                # requiring users to specify full URIs in their configuration.
                #
                # This is a workaround for FastMCP's internal scope validation behavior.
                # If FastMCP changes its validation logic, this may need to be revisited.
                enriched_scopes = list(scopes)  # Start with original scopes
                for short_name, aliases in self._scope_aliases.items():
                    # If any alias is present in the token scopes, add the short name too
                    if any(alias in scopes for alias in aliases):
                        if short_name not in enriched_scopes:
                            enriched_scopes.append(short_name)

                return AccessToken(
                    token=token,
                    client_id=user_id,
                    scopes=enriched_scopes,
                    expires_at=expires_at,
                )

        except Exception as e:
            logger.debug("Token verification failed with exception: %s", e)
            return None


class GoogleTokenVerifier(OpaqueTokenVerifier):
    """TokenVerifier specifically for Google OAuth access tokens.

    This is a convenience subclass that pre-configures OpaqueTokenVerifier
    with Google's tokeninfo endpoint and claim mappings.

    Google OAuth access tokens are opaque tokens (not JWTs), so they cannot be
    verified using standard JWT verification. Instead, we use Google's tokeninfo
    endpoint to validate the token and extract claims.

    This verifier includes built-in support for Google's scope aliases:
    - "email" matches "https://www.googleapis.com/auth/userinfo.email"
    - "profile" matches "https://www.googleapis.com/auth/userinfo.profile"
    """

    def __init__(
        self,
        *,
        client_id: str,
        required_scopes: list[str] | None = None,
        timeout_seconds: int = 30,
    ):
        """Initialize the Google token verifier.

        Args:
            client_id: The OAuth client ID (used to verify the token was issued for this app)
            required_scopes: Optional list of required scopes (supports both short names
                           like "email" and full URIs)
            timeout_seconds: HTTP request timeout
        """
        super().__init__(
            tokeninfo_url=GOOGLE_TOKENINFO_URL,
            client_id=client_id,
            required_scopes=required_scopes,
            timeout_seconds=timeout_seconds,
            # Google uses "aud" or "azp" for client ID (handled by default)
            # Google uses "scope" for scopes (default)
            # Google uses "expires_in" for expiration (default)
            # Google uses "email" or "sub" for user ID (default)
            # Google scope aliases for mapping short names to full URIs
            scope_aliases=GOOGLE_SCOPE_ALIASES,
        )
