"""FastMCP server providing Agent Skills management and execution tools."""

import logging
import sys

import typer
from fastmcp import FastMCP
from fastmcp.server.auth.oidc_proxy import OIDCProxy

from agent_skills_mcp.auth import OpaqueTokenVerifier
from agent_skills_mcp.config import get_config
from agent_skills_mcp.llm_client import LLMClient
from agent_skills_mcp.skills_manager import SkillsManager
from agent_skills_mcp.vector_store import VectorStore

# Typer app
app = typer.Typer()


def setup_logging():
    """
    Configure logging to output to stderr.
    This prevents stdout pollution for stdio transport.
    Log level can be controlled via LOG_LEVEL environment variable.
    """
    config = get_config()
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)

    log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] - %(message)s")
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    root_logger.handlers.clear()

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(log_formatter)
    root_logger.addHandler(stream_handler)


def initialize_semantic_search():
    """Initialize vector store and build index at startup."""
    config = get_config()

    if not config.semantic_search_enabled:
        logging.info("Semantic search is disabled")
        return

    logging.info("Initializing semantic search...")
    vector_store = VectorStore()
    skills_manager.set_vector_store(vector_store)

    # Initialize immediately to avoid delay on first search
    if skills_manager.initialize_vector_store():
        logging.info("Semantic search initialized successfully")
    else:
        logging.warning("Failed to initialize semantic search, will use keyword search")


def _create_auth_provider():
    """Create OAuth authentication provider based on configuration.

    Returns:
        OIDCProxy | None: OIDCProxy instance if OAuth is enabled, None otherwise.

    Raises:
        ValueError: If OAuth configuration is invalid.
    """
    config = get_config()

    if not config.oauth_enabled:
        return None

    # Validate configuration
    config.validate_oauth_config()

    # Get redirect URIs, scopes, and extra parameters
    allowed_uris = config.get_oauth_allowed_redirect_uris()
    required_scopes = config.get_oauth_scopes() or ["openid"]
    extra_params = config.get_google_extra_params()

    # Log configuration
    logging.info(f"OAuth allowed redirect URIs: {allowed_uris}")
    if extra_params:
        logging.info(f"OAuth extra authorize params: {extra_params}")

    # Create custom token verifier for providers with opaque (non-JWT) access tokens
    token_verifier = None
    tokeninfo_url = config.get_oauth_tokeninfo_url()
    if tokeninfo_url:
        logging.info(
            f"Using OpaqueTokenVerifier with tokeninfo endpoint: {tokeninfo_url}"
        )
        token_verifier = OpaqueTokenVerifier(
            tokeninfo_url=tokeninfo_url,
            client_id=config.oauth_client_id,
            required_scopes=required_scopes,
        )

    # Create OIDCProxy
    # Note: When using a custom token_verifier, required_scopes must be configured
    # on the verifier itself, not on OIDCProxy
    return OIDCProxy(
        config_url=config.oauth_config_url,
        client_id=config.oauth_client_id,
        client_secret=config.oauth_client_secret,
        base_url=config.oauth_server_base_url,
        redirect_path=config.oauth_redirect_path,
        required_scopes=required_scopes if not token_verifier else None,
        allowed_client_redirect_uris=allowed_uris,
        extra_authorize_params=extra_params if extra_params else None,
        token_verifier=token_verifier,
    )


# Initialize FastMCP server
mcp = FastMCP("agent-skills-mcp-server", auth=_create_auth_provider())

# Initialize managers
skills_manager = SkillsManager()
llm_client = LLMClient()


@mcp.tool()
async def skills_search(
    query: str | None = None,
    name_filter: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Search for Agent Skills by description or name.

    Uses semantic search for better relevance matching.
    Results are filtered by similarity threshold and include relevance scores.

    Args:
        query: Search query for skill descriptions (semantic search).
        name_filter: Filter by skill name prefix.
        limit: Maximum number of results to return (default: 10).

    Returns:
        List of matching skills with metadata and relevance score.
    """
    results = skills_manager.search_skills(
        query=query, name_filter=name_filter, limit=limit
    )

    return [
        {
            **result.skill.frontmatter.model_dump(exclude_none=True),
            "score": round(result.score, 3) if result.score is not None else None,
        }
        for result in results
    ]


@mcp.tool()
async def skills_execute(
    skill_name: str,
    user_prompt: str,
) -> dict:
    """Execute an Agent Skill with the LLM.

    Args:
        skill_name: Name of the skill to execute.
        user_prompt: User's request to process with the skill.
    """
    # Load skill
    skill = skills_manager.load_skill(skill_name)

    # Execute with LLM
    result = await llm_client.execute_with_skill(
        skill_name=skill_name,
        skill_content=skill.full_content,
        user_prompt=user_prompt,
    )

    return {
        "skill_name": result.skill_name,
        "response": result.response,
        "model": result.model,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "execution_time": result.execution_time,
    }


@app.command()
def main(
    transport: str = typer.Option(
        default="stdio",
        help="Transport protocol to use ('stdio' or 'http')",
    ),
    host: str = typer.Option(
        default="127.0.0.1",
        help="Host for HTTP server (http mode only)",
    ),
    port: int = typer.Option(
        default=8080,
        help="Port for HTTP server (http mode only)",
    ),
):
    """
    Start the MCP server with stdio or http transport.
    """
    setup_logging()

    config = get_config()

    # OAuth authentication is only available with HTTP transport
    if config.oauth_enabled and transport != "http":
        logging.error(
            "OAuth authentication is only available with HTTP transport. "
            "Please use '--transport http' or disable OAuth by setting OAUTH_ENABLED=false."
        )
        raise typer.Exit(code=1)

    # Initialize semantic search at startup (before starting MCP server)
    initialize_semantic_search()

    if transport == "stdio":
        logging.info("Starting MCP server with stdio transport...")
        mcp.run()
    elif transport == "http":
        if config.oauth_enabled:
            logging.info(
                f"Starting MCP server with http transport and OAuth authentication on {host}:{port}..."
            )
            logging.info(
                f"OAuth callback URL: {config.oauth_server_base_url}{config.oauth_redirect_path}"
            )
        else:
            logging.info(
                f"Starting MCP server with http transport (no auth) on {host}:{port}..."
            )
        mcp.run(transport="http", host=host, port=port)
    else:
        logging.error(f"Invalid transport: {transport}. Use 'stdio' or 'http'.")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
