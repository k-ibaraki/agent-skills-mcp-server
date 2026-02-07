"""FastMCP server providing Agent Skills management and execution tools."""

import logging
import sys

import typer
from fastmcp import FastMCP
from fastmcp.server.auth.oidc_proxy import OIDCProxy

from agent_skills_mcp.auth import (
    BearerTokenAuthProvider,
    GoogleTokenVerifier,
    OpaqueTokenVerifier,
)
from agent_skills_mcp.config import get_config
from agent_skills_mcp.llm_client import LLMClient
from agent_skills_mcp.skills_manager import SkillsManager
from agent_skills_mcp.vector_store import VectorStore

# Logging
logger = logging.getLogger(__name__)

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
    """Create authentication provider with Bearer token and OAuth support.

    Supports two authentication methods:
    1. Bearer token in Authorization header (checked first)
    2. OAuth flow via OIDCProxy (fallback)

    Returns:
        BearerTokenAuthProvider | OIDCProxy | None: Auth provider instance if OAuth is enabled, None otherwise.

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
        # Use GoogleTokenVerifier for Google OAuth (includes scope aliases)
        if "oauth2.googleapis.com" in tokeninfo_url:
            logging.info(
                "Using GoogleTokenVerifier with built-in scope aliases "
                f"for tokeninfo endpoint: {tokeninfo_url}"
            )
            token_verifier = GoogleTokenVerifier(
                client_id=config.oauth_client_id,
                required_scopes=required_scopes,
            )
        else:
            # Generic OpaqueTokenVerifier for other providers
            logging.info(
                f"Using OpaqueTokenVerifier with tokeninfo endpoint: {tokeninfo_url}"
            )
            token_verifier = OpaqueTokenVerifier(
                tokeninfo_url=tokeninfo_url,
                client_id=config.oauth_client_id,
                required_scopes=required_scopes,
            )

    # Create OIDCProxy for OAuth flow
    # Note: When using a custom token_verifier, required_scopes must NOT be provided
    # to OIDCProxy at all - it must be configured on the verifier itself.
    oidc_kwargs = {
        "config_url": config.oauth_config_url,
        "client_id": config.oauth_client_id,
        "client_secret": config.oauth_client_secret,
        "base_url": config.oauth_server_base_url,
        "redirect_path": config.oauth_redirect_path,
        "allowed_client_redirect_uris": allowed_uris,
    }

    # Only add required_scopes if NOT using custom token_verifier
    if not token_verifier:
        oidc_kwargs["required_scopes"] = required_scopes
    else:
        oidc_kwargs["token_verifier"] = token_verifier

    if extra_params:
        oidc_kwargs["extra_authorize_params"] = extra_params

    oidc_proxy = OIDCProxy(**oidc_kwargs)

    # Wrap with BearerTokenAuthProvider if token verifier is available
    if token_verifier:
        logging.info("Enabling Bearer token authentication with OAuth flow fallback")
        return BearerTokenAuthProvider(
            token_verifier=token_verifier,
            oidc_proxy=oidc_proxy,
        )

    # Return OIDCProxy directly if no token verifier
    return oidc_proxy


# Initialize FastMCP server
mcp = FastMCP(
    "agent-skills-mcp-server",
    auth=_create_auth_provider(),
    instructions="""Agent Skills - Proactive Skill Creation

Workflow:
1. Search: skills_search for relevant skills
2. Evaluate search results:
   - Score < 0.5 → CREATE new skill immediately
   - Score ≥ 0.5 → TRY executing with skills_execute
3. Evaluate execution results:
   - Result is insufficient/wrong/incomplete → CREATE new skill
   - Result is good → Done
4. Create WITHOUT asking: skills_manage(create) immediately when needed

Examples:
A) Low score: "花粉情報" → weather-forecast (0.3) → CREATE pollen-forecast → execute
B) Try first: "天気" → weather-forecast (0.8) → execute → insufficient detail → CREATE detailed-weather → execute

Be proactive - create new skills when search OR execution results are insufficient.""",
)

# Initialize managers
skills_manager = SkillsManager()
llm_client = LLMClient()


@mcp.tool()
async def skills_search(
    query: str | None = None,
    name_filter: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Search for Agent Skills by semantic matching. Returns skills with relevance scores (0-1).

    Score Guide:
    - ≥0.5: Use existing skill
    - <0.5 or 0 results: Create new skill with skills_manage

    Create new when: Low score, missing features, or doesn't match requirements.

    Args:
        query: Search query for descriptions (semantic).
        name_filter: Filter by name prefix.
        limit: Max results (default: 10).

    Returns:
        List with metadata and score. Low score → create new skill.
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

    After execution, evaluate if the result meets user requirements.
    If insufficient, create a new skill with skills_manage.

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


@mcp.tool()
async def skills_manage(
    operation: str,
    skill_name: str,
    purpose: str | None = None,
    detailed_requirements: str | None = None,
    allowed_tools: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """Manage Agent Skills (create, update, delete).

    Use this tool when skills_search returns no results and you need to create
    a custom skill for the user's specific requirements.

    This tool provides unified skill management using the skill-builder.
    Skills are stored in the managed-skills/ directory, separate from
    official and community skills.

    Args:
        operation: Operation to perform ("create", "update", or "delete").
        skill_name: Name of the skill in kebab-case (e.g., "my-new-skill").
        purpose: Brief description of the skill's purpose (required for create/update).
        detailed_requirements: Detailed requirements (required for create/update):
            - What the skill should do
            - Expected inputs and outputs
            - Specific workflows or patterns
            - Tools needed (web_fetch, file_read, shell, etc.)
        allowed_tools: Optional comma-separated list of tools (e.g., "web_fetch,file_read").
        metadata: Optional metadata dict (e.g., {"author": "...", "version": "1.0"}).

    Returns:
        Dict with operation result:
        - operation: Operation performed
        - skill_name: Name of the skill
        - response: Result message or error
        - model: Model used (for create/update)
        - input_tokens, output_tokens: Token usage (for create/update)
        - execution_time: Time taken
        - skill_path: Path to the skill directory

    Raises:
        ValueError: If operation is invalid or skill-builder is not available.
    """
    import re
    import shutil
    from pathlib import Path

    config = get_config()

    # Check if skill creation is enabled
    if not config.skills_creation_enabled:
        return {
            "operation": operation,
            "skill_name": skill_name,
            "response": "Error: Skill management is disabled. Set SKILLS_CREATION_ENABLED=true to enable.",
            "model": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "execution_time": 0.0,
            "skill_path": None,
        }

    # Validate operation
    valid_operations = ["create", "update", "delete"]
    if operation not in valid_operations:
        return {
            "operation": operation,
            "skill_name": skill_name,
            "response": f"Error: Invalid operation '{operation}'. Must be one of: {', '.join(valid_operations)}.",
            "model": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "execution_time": 0.0,
            "skill_path": None,
        }

    # Validate skill_name format (kebab-case)
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", skill_name):
        return {
            "operation": operation,
            "skill_name": skill_name,
            "response": f"Error: Invalid skill name '{skill_name}'. Must be kebab-case (e.g., 'my-skill').",
            "model": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "execution_time": 0.0,
            "skill_path": None,
        }

    skill_path = Path("managed-skills") / config.managed_skills_user / skill_name

    # Operation: delete
    if operation == "delete":
        if not skill_path.exists():
            return {
                "operation": operation,
                "skill_name": skill_name,
                "response": f"Error: Skill '{skill_name}' not found in managed-skills/{config.managed_skills_user}/.",
                "model": "",
                "input_tokens": 0,
                "output_tokens": 0,
                "execution_time": 0.0,
                "skill_path": str(skill_path),
            }

        try:
            import time

            start_time = time.time()
            shutil.rmtree(skill_path)
            execution_time = time.time() - start_time

            # Refresh skills index
            if skills_manager.refresh_index():
                logger.info(f"Skills index refreshed after deleting '{skill_name}'")

            return {
                "operation": operation,
                "skill_name": skill_name,
                "response": f"Successfully deleted skill '{skill_name}' from managed-skills/{config.managed_skills_user}/.",
                "model": "",
                "input_tokens": 0,
                "output_tokens": 0,
                "execution_time": execution_time,
                "skill_path": str(skill_path),
            }
        except Exception as e:
            logger.error(f"Failed to delete skill '{skill_name}': {e}")
            return {
                "operation": operation,
                "skill_name": skill_name,
                "response": f"Error: Failed to delete skill: {e}",
                "model": "",
                "input_tokens": 0,
                "output_tokens": 0,
                "execution_time": 0.0,
                "skill_path": str(skill_path),
            }

    # Operation: create or update
    # Validate required parameters
    if not purpose:
        return {
            "operation": operation,
            "skill_name": skill_name,
            "response": f"Error: 'purpose' is required for {operation} operation.",
            "model": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "execution_time": 0.0,
            "skill_path": str(skill_path),
        }

    if not detailed_requirements:
        return {
            "operation": operation,
            "skill_name": skill_name,
            "response": f"Error: 'detailed_requirements' is required for {operation} operation.",
            "model": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "execution_time": 0.0,
            "skill_path": str(skill_path),
        }

    # Check if skill-builder is available
    try:
        skill_creator = skills_manager.load_skill("skill-builder")
    except ValueError as e:
        return {
            "operation": operation,
            "skill_name": skill_name,
            "response": f"Error: skill-builder not found. Please ensure it's available in the skills directory. {e}",
            "model": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "execution_time": 0.0,
            "skill_path": str(skill_path),
        }

    # Check for existing skill (for create operation)
    if operation == "create" and skill_path.exists():
        return {
            "operation": operation,
            "skill_name": skill_name,
            "response": f"Error: Skill '{skill_name}' already exists in managed-skills/{config.managed_skills_user}/. Use operation='update' to modify it.",
            "model": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "execution_time": 0.0,
            "skill_path": str(skill_path),
        }

    # Check for non-existing skill (for update operation)
    if operation == "update" and not skill_path.exists():
        return {
            "operation": operation,
            "skill_name": skill_name,
            "response": f"Error: Skill '{skill_name}' not found in managed-skills/{config.managed_skills_user}/. Use operation='create' to create it.",
            "model": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "execution_time": 0.0,
            "skill_path": str(skill_path),
        }

    # Construct user prompt for skill-builder
    target_path = f"managed-skills/{config.managed_skills_user}/{skill_name}/SKILL.md"

    action_verb = "Create" if operation == "create" else "Update"
    user_prompt = f"""{action_verb} a skill: {skill_name}

Purpose: {purpose}

Requirements:
{detailed_requirements}
"""

    if allowed_tools:
        user_prompt += f"\nAllowed tools: {allowed_tools}\n"

    if metadata:
        import json

        user_prompt += f"\nMetadata: {json.dumps(metadata)}\n"

    user_prompt += f"\nWrite SKILL.md to: {target_path}\n"

    # Execute skill-builder with high-performance model
    try:
        result = await llm_client.execute_with_skill(
            skill_name="skill-builder",
            skill_content=skill_creator.full_content,
            user_prompt=user_prompt,
            model=config.skill_builder_model,
        )

        # Refresh skills index to include the new/updated skill
        if skills_manager.refresh_index():
            logger.info(f"Skills index refreshed after {operation} '{skill_name}'")
        else:
            logger.warning(
                f"Failed to refresh skills index after {operation} '{skill_name}'"
            )

        return {
            "operation": operation,
            "skill_name": skill_name,
            "response": result.response,
            "model": result.model,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "execution_time": result.execution_time,
            "skill_path": str(skill_path),
        }

    except Exception as e:
        logger.error(f"Failed to {operation} skill '{skill_name}': {e}")
        return {
            "operation": operation,
            "skill_name": skill_name,
            "response": f"Error: Skill {operation} failed: {e}",
            "model": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "execution_time": 0.0,
            "skill_path": str(skill_path),
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
