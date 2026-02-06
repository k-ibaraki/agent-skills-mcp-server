"""Google OAuth access token verifier."""

from agent_skills_mcp.auth.opaque_token_verifier import OpaqueTokenVerifier

# Well-known tokeninfo endpoints for major providers
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"

# Well-known scope aliases (short name -> full scope URIs)
# Used to map user-friendly scope names to provider-specific full URIs
GOOGLE_SCOPE_ALIASES: dict[str, list[str]] = {
    "email": ["https://www.googleapis.com/auth/userinfo.email"],
    "profile": ["https://www.googleapis.com/auth/userinfo.profile"],
}


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
