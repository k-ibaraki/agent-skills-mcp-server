"""FastMCP server providing Agent Skills management and execution tools."""

from fastmcp import FastMCP

from agent_skills_mcp.llm_client import LLMClient
from agent_skills_mcp.skills_manager import SkillsManager

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
        query: Search query to match against skill descriptions (partial match, case-insensitive).
        name_filter: Filter by skill name prefix (case-insensitive).

    Returns:
        List of matching skills with name, description, and directory path.

    Examples:
        - skills_search(query="pdf") - Find skills related to PDF processing
        - skills_search(name_filter="example") - Find skills starting with "example"
        - skills_search(query="data", name_filter="etl") - Combine both filters
    """
    results = skills_manager.search_skills(query=query, name_filter=name_filter)

    return [
        {
            "name": skill.name,
            "description": skill.description,
            "directory_path": skill.directory_path,
        }
        for skill in results
    ]


@mcp.tool()
async def skills_describe(skill_name: str) -> dict:
    """Get complete details of a specific Agent Skill.

    Args:
        skill_name: Name of the skill to describe.

    Returns:
        Complete skill information including frontmatter metadata and markdown content.

    Raises:
        ValueError: If skill not found or invalid.

    Examples:
        - skills_describe("example-skill") - Get full details of the example skill
    """
    skill = skills_manager.load_skill(skill_name)

    return {
        "name": skill.name,
        "description": skill.description,
        "directory_path": skill.directory_path,
        "frontmatter": skill.frontmatter.model_dump(exclude_none=True),
        "markdown_body": skill.markdown_body,
        "full_content": skill.full_content,
    }


@mcp.tool()
async def skills_execute(
    skill_name: str,
    user_prompt: str,
    model: str | None = None,
) -> dict:
    """Execute an Agent Skill by injecting it into an LLM as system prompt.

    Args:
        skill_name: Name of the skill to execute.
        user_prompt: User's prompt/request to send to the LLM.
        model: Optional model override (e.g., "anthropic/claude-3-5-sonnet-20241022").
               If not specified, uses default model from config.

    Returns:
        Execution result including LLM response, model used, token usage, and execution time.

    Raises:
        ValueError: If skill not found or model credentials not configured.
        Exception: If LLM API call fails.

    Examples:
        - skills_execute("example-skill", "Hello, test the skill")
        - skills_execute("example-skill", "Process this data", model="anthropic/claude-3-5-sonnet-20241022")
    """
    # Load skill
    skill = skills_manager.load_skill(skill_name)

    # Execute with LLM
    result = await llm_client.execute_with_skill(
        skill_name=skill_name,
        skill_content=skill.full_content,
        user_prompt=user_prompt,
        model=model,
    )

    return {
        "skill_name": result.skill_name,
        "response": result.response,
        "model": result.model,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "execution_time": result.execution_time,
    }


def main():
    """Main entry point for the MCP server."""
    import sys

    # Check for transport argument
    transport = "stdio"  # Default to stdio for Claude Desktop
    port = 8000

    if "--transport" in sys.argv:
        idx = sys.argv.index("--transport")
        if idx + 1 < len(sys.argv):
            transport = sys.argv[idx + 1]

    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])

    # Run server with specified transport
    if transport == "http":
        mcp.run(transport="streamable-http", port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
