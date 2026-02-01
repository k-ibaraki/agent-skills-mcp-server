"""Configuration management for Agent Skills MCP Server."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
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
