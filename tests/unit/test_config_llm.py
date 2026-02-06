"""Unit tests for LLM configuration validation in config module.

This module tests the validate_llm_config method and related configuration
for different LLM providers (Anthropic, AWS Bedrock, Google Vertex AI).
"""

import pytest

from agent_skills_mcp.config import Config


@pytest.mark.unit
class TestValidateLLMConfig:
    """Test validate_llm_config method for different providers."""

    # Anthropic tests
    def test_anthropic_model_with_api_key(self, monkeypatch):
        """Test that Anthropic model validates successfully with API key."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test123")
        config = Config()
        # Should not raise
        config.validate_llm_config("anthropic/claude-3-5-sonnet-20241022")

    def test_anthropic_model_without_api_key(self):
        """Test that Anthropic model fails without API key."""
        config = Config()
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
            config.validate_llm_config("anthropic/claude-3-5-sonnet-20241022")

    def test_anthropic_latest_model(self, monkeypatch):
        """Test validation for latest Anthropic model."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test123")
        config = Config()
        config.validate_llm_config("anthropic/claude-sonnet-4-5-20250929")

    # AWS Bedrock tests
    def test_bedrock_model_with_credentials(self, monkeypatch):
        """Test that Bedrock model validates successfully with credentials."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIATEST123")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret123")
        config = Config()
        config.validate_llm_config("bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0")

    def test_bedrock_model_without_access_key(self, monkeypatch):
        """Test that Bedrock model fails without access key."""
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret123")
        config = Config()
        with pytest.raises(
            ValueError, match="AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required"
        ):
            config.validate_llm_config(
                "bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0"
            )

    def test_bedrock_model_without_secret_key(self, monkeypatch):
        """Test that Bedrock model fails without secret key."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIATEST123")
        config = Config()
        with pytest.raises(
            ValueError, match="AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required"
        ):
            config.validate_llm_config(
                "bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0"
            )

    def test_bedrock_latest_model(self, monkeypatch):
        """Test validation for latest Bedrock model."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIATEST123")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret123")
        config = Config()
        config.validate_llm_config("bedrock/us.anthropic.claude-sonnet-4-5-v1:0")

    # Google Vertex AI tests
    def test_vertex_ai_model_with_credentials(self, monkeypatch):
        """Test that Vertex AI model validates successfully with credentials."""
        monkeypatch.setenv("VERTEXAI_PROJECT", "my-project")
        monkeypatch.setenv("VERTEXAI_LOCATION", "us-central1")
        config = Config()
        config.validate_llm_config("vertex_ai/claude-3-5-sonnet-v2@20241022")

    def test_vertex_ai_model_without_project(self, monkeypatch):
        """Test that Vertex AI model fails without project."""
        monkeypatch.setenv("VERTEXAI_LOCATION", "us-central1")
        config = Config()
        with pytest.raises(
            ValueError, match="VERTEXAI_PROJECT and VERTEXAI_LOCATION are required"
        ):
            config.validate_llm_config("vertex_ai/claude-3-5-sonnet-v2@20241022")

    def test_vertex_ai_model_without_location(self, monkeypatch):
        """Test that Vertex AI model fails without location."""
        monkeypatch.setenv("VERTEXAI_PROJECT", "my-project")
        config = Config()
        with pytest.raises(
            ValueError, match="VERTEXAI_PROJECT and VERTEXAI_LOCATION are required"
        ):
            config.validate_llm_config("vertex_ai/claude-3-5-sonnet-v2@20241022")

    def test_vertex_ai_claude_latest_model(self, monkeypatch):
        """Test validation for latest Vertex AI Claude model."""
        monkeypatch.setenv("VERTEXAI_PROJECT", "my-project")
        monkeypatch.setenv("VERTEXAI_LOCATION", "us-central1")
        config = Config()
        config.validate_llm_config("vertex_ai/claude-sonnet-4-5@20250929")

    def test_vertex_ai_gemini_models(self, monkeypatch):
        """Test validation for Vertex AI Gemini models."""
        monkeypatch.setenv("VERTEXAI_PROJECT", "my-project")
        monkeypatch.setenv("VERTEXAI_LOCATION", "us-central1")
        config = Config()

        # Test various Gemini models
        config.validate_llm_config("vertex_ai/gemini-2.5-pro")
        config.validate_llm_config("vertex_ai/gemini-2.0-flash-exp")
        config.validate_llm_config("vertex_ai/gemini-1.5-pro")
        config.validate_llm_config("vertex_ai/gemini-1.5-flash")
        config.validate_llm_config("vertex_ai/gemini-3-flash-preview")

    # Edge cases
    def test_unknown_provider_no_error(self):
        """Test that unknown provider prefix doesn't raise error."""
        config = Config()
        # Unknown provider should not raise (no validation implemented)
        config.validate_llm_config("unknown_provider/model-name")

    def test_empty_model_string(self):
        """Test validation with empty model string."""
        config = Config()
        # Empty string should not match any provider (no validation)
        config.validate_llm_config("")

    def test_model_without_prefix(self):
        """Test validation with model name without prefix."""
        config = Config()
        # Model without prefix should not match any provider (no validation)
        config.validate_llm_config("claude-3-5-sonnet-20241022")

    def test_case_sensitive_prefix(self, monkeypatch):
        """Test that provider prefix matching is case-sensitive."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test123")
        config = Config()

        # Lowercase should work
        config.validate_llm_config("anthropic/claude-3-5-sonnet-20241022")

        # Uppercase should not match (no validation)
        config.validate_llm_config("ANTHROPIC/claude-3-5-sonnet-20241022")

    def test_special_characters_in_model_name(self, monkeypatch):
        """Test model names with special characters."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test123")
        config = Config()

        # Model names with dots, hyphens, colons
        config.validate_llm_config("anthropic/claude-3.5-sonnet:2024-10-22")

    def test_multiple_slashes_in_model_name(self, monkeypatch):
        """Test model names with multiple slashes."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIATEST123")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret123")
        config = Config()

        # Bedrock models can have multiple slashes in ARN format
        # Should match "bedrock/" prefix
        config.validate_llm_config(
            "bedrock/arn:aws:bedrock:us-east-1::model/anthropic.claude-3-5-sonnet"
        )


@pytest.mark.unit
class TestConfigDefaults:
    """Test default configuration values."""

    def test_default_model(self):
        """Test that default model is set correctly."""
        config = Config()
        assert config.default_model == "anthropic/claude-3-5-sonnet-20241022"

    def test_default_aws_region(self):
        """Test that default AWS region is set."""
        config = Config()
        assert config.aws_region_name == "us-east-1"

    def test_optional_credentials_none_by_default(self):
        """Test that optional credentials are None by default."""
        config = Config()
        assert config.anthropic_api_key is None
        assert config.aws_access_key_id is None
        assert config.aws_secret_access_key is None
        assert config.vertexai_project is None
        assert config.vertexai_location is None


@pytest.mark.unit
class TestConfigFromEnvironment:
    """Test configuration loading from environment variables."""

    def test_load_anthropic_config(self, monkeypatch):
        """Test loading Anthropic configuration from environment."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test123")
        monkeypatch.setenv("DEFAULT_MODEL", "anthropic/claude-sonnet-4-5-20250929")

        config = Config()
        assert config.anthropic_api_key == "sk-ant-test123"
        assert config.default_model == "anthropic/claude-sonnet-4-5-20250929"

    def test_load_bedrock_config(self, monkeypatch):
        """Test loading Bedrock configuration from environment."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIATEST123")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret123")
        monkeypatch.setenv("AWS_REGION_NAME", "us-west-2")

        config = Config()
        assert config.aws_access_key_id == "AKIATEST123"
        assert config.aws_secret_access_key == "secret123"
        assert config.aws_region_name == "us-west-2"

    def test_load_vertex_ai_config(self, monkeypatch):
        """Test loading Vertex AI configuration from environment."""
        monkeypatch.setenv("VERTEXAI_PROJECT", "my-project-123")
        monkeypatch.setenv("VERTEXAI_LOCATION", "europe-west1")

        config = Config()
        assert config.vertexai_project == "my-project-123"
        assert config.vertexai_location == "europe-west1"

    def test_case_insensitive_env_vars(self, monkeypatch):
        """Test that environment variables are case-insensitive."""
        # Config uses case_sensitive=False in model_config
        monkeypatch.setenv("anthropic_api_key", "sk-ant-lowercase")

        config = Config()
        assert config.anthropic_api_key == "sk-ant-lowercase"

    def test_extra_env_vars_ignored(self, monkeypatch):
        """Test that extra environment variables are ignored."""
        monkeypatch.setenv("UNKNOWN_SETTING", "value")
        monkeypatch.setenv("RANDOM_KEY", "random_value")

        # Should not raise (extra="ignore" in model_config)
        config = Config()
        assert not hasattr(config, "unknown_setting")
        assert not hasattr(config, "random_key")
