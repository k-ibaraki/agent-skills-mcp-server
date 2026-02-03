"""OAuth access token verifiers for opaque (non-JWT) tokens."""

import time

import httpx
from fastmcp.server.auth import AccessToken, TokenVerifier

# Well-known tokeninfo endpoints for major providers
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


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
        """
        self._tokeninfo_url = tokeninfo_url
        self._client_id = client_id
        self._required_scopes = required_scopes or []
        self._timeout = timeout_seconds
        self._client_id_claim = client_id_claim
        self._scope_claim = scope_claim
        self._expiry_claim = expiry_claim
        self._user_id_claims = user_id_claims or ["email", "sub"]

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
                    return None

                data = response.json()

                # Verify the token was issued for our client
                token_client_id = self._extract_client_id(data)
                if token_client_id != self._client_id:
                    return None

                # Check token expiration
                expires_at = self._extract_expiry(data)
                if expires_at == 0:  # Expired
                    return None

                # Extract scopes
                scopes = self._extract_scopes(data)

                # Check required scopes
                if self._required_scopes:
                    token_scopes = set(scopes)
                    required = set(self._required_scopes)
                    if not required.issubset(token_scopes):
                        return None

                # Extract user ID
                user_id = self._extract_user_id(data)

                return AccessToken(
                    token=token,
                    client_id=user_id,
                    scopes=scopes,
                    expires_at=expires_at,
                )

        except Exception:
            return None


class GoogleTokenVerifier(OpaqueTokenVerifier):
    """TokenVerifier specifically for Google OAuth access tokens.

    This is a convenience subclass that pre-configures OpaqueTokenVerifier
    with Google's tokeninfo endpoint and claim mappings.

    Google OAuth access tokens are opaque tokens (not JWTs), so they cannot be
    verified using standard JWT verification. Instead, we use Google's tokeninfo
    endpoint to validate the token and extract claims.
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
            required_scopes: Optional list of required scopes
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
        )
