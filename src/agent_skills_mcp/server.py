"""FastMCP server providing Agent Skills management and execution tools."""

import logging
import sys

import typer
from fastmcp import FastMCP

from agent_skills_mcp.config import get_config
from agent_skills_mcp.llm_client import LLMClient
from agent_skills_mcp.skills_manager import SkillsManager

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


# Initialize FastMCP server
mcp = FastMCP("agent-skills-mcp-server")

# Initialize managers
skills_manager = SkillsManager()
llm_client = LLMClient()


@mcp.tool()
async def skills_search(
    query: str | None = None,
    name_filter: str | None = None,
) -> list[dict]:
    """Search for Agent Skills by description or name.

    Args:
        query: Search query for skill descriptions (partial match).
        name_filter: Filter by skill name prefix.
    """
    results = skills_manager.search_skills(query=query, name_filter=name_filter)

    return [skill.frontmatter.model_dump(exclude_none=True) for skill in results]


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

    if transport == "stdio":
        logging.info("Starting MCP server with stdio transport...")
        mcp.run()
    elif transport == "http":
        logging.info(f"Starting MCP server with http transport on {host}:{port}...")
        mcp.run(transport="http", host=host, port=port)
    else:
        logging.error(f"Invalid transport: {transport}. Use 'stdio' or 'http'.")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
