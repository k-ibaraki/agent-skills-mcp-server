"""Configuration management for Agent Skills MCP Server."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file if exists and not in test mode
# This ensures environment variables are available before Config is instantiated
if not os.getenv("TESTING") and Path(".env").exists():
    load_dotenv(".env")


class Config(BaseSettings):
    """Application configuration loaded from environment variables.

    Note: This class reads from environment variables only.
    For development, use load_dotenv() before creating Config instances
    (already handled in server.py startup).
    """

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )

    # Skills configuration
    skills_directory: Path = Field(
        default=Path("./skills"),
        description="Directory containing Agent Skills",
    )

    # LLM configuration
    default_model: str = Field(
        default="anthropic/claude-3-5-sonnet-20241022",
        description="Default LLM model to use for skill execution",
    )

    # Anthropic API
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key",
    )

    # AWS Bedrock
    aws_access_key_id: str | None = Field(
        default=None,
        description="AWS access key ID for Bedrock",
    )
    aws_secret_access_key: str | None = Field(
        default=None,
        description="AWS secret access key for Bedrock",
    )
    aws_region_name: str = Field(
        default="us-east-1",
        description="AWS region for Bedrock",
    )

    # Google Vertex AI
    vertexai_project: str | None = Field(
        default=None,
        description="Google Cloud project ID for Vertex AI",
    )
    vertexai_location: str | None = Field(
        default=None,
        description="Google Cloud location for Vertex AI",
    )

    # Logging configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    # RAG / Semantic Search configuration
    embedding_model: str = Field(
        default="paraphrase-multilingual-MiniLM-L12-v2",
        description="Sentence-transformers model for embeddings (supports 50+ languages)",
    )
    semantic_search_limit: int = Field(
        default=10,
        description="Default number of results for semantic search",
        ge=1,
        le=100,
    )
    semantic_search_enabled: bool = Field(
        default=True,
        description="Enable semantic search (falls back to keyword search if disabled or on error)",
    )
    semantic_search_threshold: float = Field(
        default=0.3,
        description="Minimum similarity score (0-1) for semantic search results",
        ge=0.0,
        le=1.0,
    )

    # OIDC/OAuth authentication configuration (HTTP transport only)
    oauth_enabled: bool = Field(
        default=False,
        description="Enable OIDC/OAuth authentication (HTTP transport only)",
    )
    oauth_config_url: str | None = Field(
        default=None,
        description="OIDC configuration endpoint URL (e.g., https://accounts.google.com/.well-known/openid-configuration)",
    )
    oauth_client_id: str | None = Field(
        default=None,
        description="OAuth client ID",
    )
    oauth_client_secret: str | None = Field(
        default=None,
        description="OAuth client secret",
    )
    oauth_server_base_url: str = Field(
        default="http://localhost:8080",
        description="FastMCP server public base URL",
    )
    oauth_required_scopes: str | None = Field(
        default=None,
        description="Required OAuth scopes (comma-separated)",
    )
    oauth_allowed_redirect_uris: str | None = Field(
        default=None,
        description="Allowed MCP client redirect URIs (comma-separated, wildcard support). None=allow all, ''=deny all",
    )
    oauth_redirect_path: str = Field(
        default="/auth/callback",
        description="OAuth callback redirect path",
    )

    # Opaque token verification (for providers using non-JWT access tokens)
    oauth_tokeninfo_url: str | None = Field(
        default=None,
        description="Token introspection endpoint URL for opaque token verification. "
        "If not set, auto-detected for known providers (e.g., Google).",
    )

    # Google OAuth specific configuration
    google_oauth_access_type: str | None = Field(
        default=None,
        description="Google OAuth access_type parameter (e.g., 'offline' for refresh token support)",
    )
    google_oauth_prompt: str | None = Field(
        default=None,
        description="Google OAuth prompt parameter (e.g., 'consent' to force consent screen)",
    )

    def get_oauth_scopes(self) -> list[str]:
        """Parse comma-separated OAuth scopes into a list.

        Returns:
            List of scope strings. Returns empty list if oauth_required_scopes is None or empty.
        """
        if not self.oauth_required_scopes:
            return []
        return [
            scope.strip()
            for scope in self.oauth_required_scopes.split(",")
            if scope.strip()
        ]

    def get_oauth_allowed_redirect_uris(self) -> list[str] | None:
        """Parse comma-separated redirect URIs into a list.

        Returns:
            None: Allow all redirect URIs (development mode)
            []: Deny all redirect URIs
            list[str]: Explicit list of allowed redirect URIs (production mode)
        """
        if self.oauth_allowed_redirect_uris is None:
            return None  # Allow all
        if not self.oauth_allowed_redirect_uris.strip():
            return []  # Deny all
        return [
            uri.strip()
            for uri in self.oauth_allowed_redirect_uris.split(",")
            if uri.strip()
        ]

    def get_google_extra_params(self) -> dict[str, str]:
        """Get Google-specific extra authorization parameters.

        Returns:
            Dictionary of extra parameters for Google OAuth.
        """
        extra_params = {}
        if self.google_oauth_access_type:
            extra_params["access_type"] = self.google_oauth_access_type
        if self.google_oauth_prompt:
            extra_params["prompt"] = self.google_oauth_prompt
        return extra_params

    def get_oauth_tokeninfo_url(self) -> str | None:
        """Get the tokeninfo URL for opaque token verification.

        If oauth_tokeninfo_url is explicitly set, use it.
        Otherwise, auto-detect based on known providers.

        Returns:
            Tokeninfo URL if available, None if not needed (JWT tokens).
        """
        if self.oauth_tokeninfo_url:
            return self.oauth_tokeninfo_url

        # Auto-detect for known providers with opaque access tokens
        if self.oauth_config_url:
            if "accounts.google.com" in self.oauth_config_url:
                return "https://oauth2.googleapis.com/tokeninfo"

        return None

    def validate_oauth_config(self) -> None:
        """Validate OAuth configuration when OAuth is enabled.

        Raises:
            ValueError: If required OAuth settings are missing.
        """
        if not self.oauth_enabled:
            return

        missing_fields = []
        if not self.oauth_config_url:
            missing_fields.append("OAUTH_CONFIG_URL")
        if not self.oauth_client_id:
            missing_fields.append("OAUTH_CLIENT_ID")
        if not self.oauth_client_secret:
            missing_fields.append("OAUTH_CLIENT_SECRET")

        if missing_fields:
            raise ValueError(
                f"OAuth is enabled but required settings are missing: {', '.join(missing_fields)}. "
                "Please set them in your .env file or disable OAuth by setting OAUTH_ENABLED=false."
            )

    def validate_llm_config(self, model: str) -> None:
        """Validate that required credentials are available for the specified model.

        Args:
            model: Model identifier (e.g., "anthropic/...", "bedrock/...", "vertex_ai/...")

        Raises:
            ValueError: If required credentials are missing for the model provider.
        """
        if model.startswith("anthropic/"):
            if not self.anthropic_api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY is required for Anthropic models. "
                    "Please set it in your .env file."
                )
        elif model.startswith("bedrock/"):
            if not self.aws_access_key_id or not self.aws_secret_access_key:
                raise ValueError(
                    "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required for Bedrock models. "
                    "Please set them in your .env file."
                )
        elif model.startswith("vertex_ai/"):
            if not self.vertexai_project or not self.vertexai_location:
                raise ValueError(
                    "VERTEXAI_PROJECT and VERTEXAI_LOCATION are required for Vertex AI models. "
                    "Please set them in your .env file."
                )


# Global configuration instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance (singleton pattern)."""
    global _config
    if _config is None:
        _config = Config()
    return _config
