"""Bearer Token Authentication Provider.

Supports both external Bearer token authentication and OAuth flow:
- If Authorization header has a Bearer token, try external verification first
- If external verification fails, fall back to OIDCProxy's verification (FastMCP JWT)
- OAuth flow routes (/authorize, /token, /auth/callback) are delegated to OIDCProxy
"""

import logging

from fastmcp.server.auth.auth import AccessToken, AuthProvider
from starlette.routing import Route

logger = logging.getLogger(__name__)


class BearerTokenAuthProvider(AuthProvider):
    """Authentication provider that supports external Bearer tokens with OAuth fallback.

    This provider wraps an OIDCProxy and a TokenVerifier to support two auth flows:

    1. External Bearer token: Token obtained externally (e.g., via Google OAuth)
       is passed in Authorization header and verified directly by TokenVerifier.
    2. OAuth flow: Standard OAuth flow via OIDCProxy, which issues FastMCP JWTs.

    The verify_token() method tries external verification first, then falls back
    to OIDCProxy's JWT-based verification.

    Args:
        token_verifier: Token verifier for external tokens (GoogleTokenVerifier etc.).
        oidc_proxy: OIDCProxy instance for OAuth flow and FastMCP JWT verification.
    """

    def __init__(
        self,
        token_verifier: AuthProvider,
        oidc_proxy: AuthProvider,
    ):
        super().__init__(
            base_url=oidc_proxy.base_url,
            required_scopes=oidc_proxy.required_scopes,
        )
        self._token_verifier = token_verifier
        self._oidc_proxy = oidc_proxy

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify a Bearer token.

        Tries external token verification first (e.g., Google tokeninfo API),
        then falls back to OIDCProxy's FastMCP JWT verification.

        Args:
            token: The Bearer token to verify.

        Returns:
            AccessToken if valid, None if invalid.
        """
        # Try external token verification first
        try:
            result = await self._token_verifier.verify_token(token)
            if result is not None:
                logger.debug("External Bearer token verification succeeded")
                return result
        except Exception as e:
            logger.debug(f"External token verification failed, trying OAuth flow: {e}")

        # Fall back to OIDCProxy verification (FastMCP JWT from OAuth flow)
        try:
            return await self._oidc_proxy.verify_token(token)
        except Exception as e:
            logger.debug(f"OIDCProxy token verification also failed: {e}")
            return None

    def get_routes(self, mcp_path: str | None = None) -> list[Route]:
        """Delegate route creation to OIDCProxy.

        This provides OAuth flow endpoints (/authorize, /token, /auth/callback, etc.).
        """
        return self._oidc_proxy.get_routes(mcp_path)

    def get_middleware(self) -> list:
        """Return auth middleware using this provider's verify_token.

        Uses the default AuthProvider middleware which creates BearerAuthBackend(self),
        ensuring our custom verify_token() is called for all requests.
        """
        return super().get_middleware()

    def set_mcp_path(self, mcp_path: str | None = None) -> None:
        """Set MCP path on both this provider and the wrapped OIDCProxy."""
        super().set_mcp_path(mcp_path)
        self._oidc_proxy.set_mcp_path(mcp_path)
