"""Pytest configuration and fixtures for tests."""

import os

import pytest


@pytest.fixture(autouse=True)
def clean_env():
    """Clean environment variables before each test.

    This fixture ensures tests are not affected by environment variables
    set in the shell or by .env file. Sets TESTING=true to prevent
    load_dotenv() from running in config.py.
    Tests can set their own environment variables as needed.
    """
    # Set TESTING flag to prevent .env file loading
    os.environ["TESTING"] = "true"

    # Environment variables to clean for isolated testing
    env_vars_to_clean = [
        # OAuth configuration
        "OAUTH_ENABLED",
        "OAUTH_CONFIG_URL",
        "OAUTH_CLIENT_ID",
        "OAUTH_CLIENT_SECRET",
        "OAUTH_SERVER_BASE_URL",
        "OAUTH_REQUIRED_SCOPES",
        "OAUTH_ALLOWED_REDIRECT_URIS",
        "OAUTH_REDIRECT_PATH",
        "OAUTH_TOKENINFO_URL",
        "GOOGLE_OAUTH_ACCESS_TYPE",
        "GOOGLE_OAUTH_PROMPT",
        # LLM configuration
        "DEFAULT_MODEL",
        "ANTHROPIC_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION_NAME",
        "VERTEXAI_PROJECT",
        "VERTEXAI_LOCATION",
    ]

    # Store original values
    original_env = {}
    for var in env_vars_to_clean:
        if var in os.environ:
            original_env[var] = os.environ.pop(var)

    yield

    # Restore original values
    for var, value in original_env.items():
        os.environ[var] = value

    # Clean up TESTING flag
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
