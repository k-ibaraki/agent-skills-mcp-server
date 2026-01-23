"""Data models for Agent Skills."""

from pydantic import BaseModel, Field


class SkillMetadata(BaseModel):
    """Basic skill metadata."""

    name: str = Field(
        ...,
        max_length=64,
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
        description="Skill name in kebab-case format",
    )
    description: str = Field(
        ..., max_length=1024, min_length=1, description="Skill description"
    )


class SkillFrontmatter(SkillMetadata):
    """Complete YAML frontmatter structure for a skill."""

    license: str | None = Field(
        None, description="License identifier (e.g., Apache-2.0)"
    )
    compatibility: str | None = Field(
        None, max_length=500, description="Compatibility information"
    )
    metadata: dict[str, str] | None = Field(
        None, description="Additional metadata (author, version, etc.)"
    )
    allowed_tools: str | None = Field(
        None, description="Comma-separated list of allowed tools"
    )


class Skill(BaseModel):
    """Complete skill representation including frontmatter and markdown body."""

    frontmatter: SkillFrontmatter = Field(..., description="Parsed YAML frontmatter")
    markdown_body: str = Field(..., description="Markdown content after frontmatter")
    directory_path: str = Field(..., description="Absolute path to skill directory")

    @property
    def name(self) -> str:
        """Get skill name from frontmatter."""
        return self.frontmatter.name

    @property
    def description(self) -> str:
        """Get skill description from frontmatter."""
        return self.frontmatter.description

    @property
    def full_content(self) -> str:
        """Get complete skill content (frontmatter + markdown)."""
        # Reconstruct original SKILL.md format for LLM consumption
        import yaml

        frontmatter_yaml = yaml.dump(
            self.frontmatter.model_dump(exclude_none=True),
            allow_unicode=True,
            sort_keys=False,
        )
        return f"---\n{frontmatter_yaml}---\n\n{self.markdown_body}"


class SkillSearchResult(BaseModel):
    """Search result for a skill."""

    name: str = Field(..., description="Skill name")
    description: str = Field(..., description="Skill description")
    directory_path: str = Field(..., description="Path to skill directory")


class SkillExecutionResult(BaseModel):
    """Result of skill execution via LLM."""

    skill_name: str = Field(..., description="Name of executed skill")
    response: str = Field(..., description="LLM response content")
    model: str = Field(..., description="Model used for execution")
    input_tokens: int | None = Field(None, description="Number of input tokens")
    output_tokens: int | None = Field(None, description="Number of output tokens")
    execution_time: float | None = Field(None, description="Execution time in seconds")
