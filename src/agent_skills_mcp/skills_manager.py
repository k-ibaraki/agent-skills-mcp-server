"""Skills management - discovery, loading, parsing, and validation."""

import re
from pathlib import Path

import yaml
from pydantic import ValidationError

from agent_skills_mcp.config import get_config
from agent_skills_mcp.models import Skill, SkillFrontmatter, SkillSearchResult


class SkillsManager:
    """Manager for Agent Skills operations."""

    def __init__(self, skills_directory: Path | None = None):
        """Initialize the skills manager.

        Args:
            skills_directory: Path to skills directory. If None, uses config default.
        """
        self.config = get_config()
        self.skills_directory = skills_directory or self.config.skills_directory
        self.skills_directory = Path(self.skills_directory).resolve()

        if not self.skills_directory.exists():
            raise ValueError(f"Skills directory not found: {self.skills_directory}")

    def discover_skills(self) -> list[SkillSearchResult]:
        """Discover all valid skills in the skills directory.

        Returns:
            List of skill search results with name, description, and path.

        Raises:
            ValueError: If skills directory doesn't exist.
        """
        results = []

        # Scan for skill directories (containing SKILL.md)
        for skill_dir in self.skills_directory.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                # Parse and validate skill
                skill = self._parse_skill_md(skill_file)

                results.append(
                    SkillSearchResult(
                        name=skill.name,
                        description=skill.description,
                        directory_path=str(skill_dir),
                    )
                )
            except (ValidationError, ValueError, yaml.YAMLError):
                # Skip invalid skills silently during discovery
                continue

        return results

    def load_skill(self, skill_name: str) -> Skill:
        """Load complete skill content by name.

        Args:
            skill_name: Name of the skill to load.

        Returns:
            Complete Skill object with frontmatter and markdown body.

        Raises:
            ValueError: If skill not found or invalid.
        """
        # Find skill directory
        skill_dir = self.skills_directory / skill_name
        if not skill_dir.exists() or not skill_dir.is_dir():
            raise ValueError(f"Skill not found: {skill_name}")

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            raise ValueError(f"SKILL.md not found in: {skill_dir}")

        return self._parse_skill_md(skill_file)

    def search_skills(
        self,
        query: str | None = None,
        name_filter: str | None = None,
    ) -> list[SkillSearchResult]:
        """Search for skills by query and/or name filter.

        Args:
            query: Search query to match against description (partial match, case-insensitive).
            name_filter: Name prefix filter (case-insensitive).

        Returns:
            List of matching skill search results.
        """
        all_skills = self.discover_skills()

        # Apply filters
        filtered_skills = all_skills

        if name_filter:
            name_filter_lower = name_filter.lower()
            filtered_skills = [
                skill
                for skill in filtered_skills
                if skill.name.lower().startswith(name_filter_lower)
            ]

        if query:
            query_lower = query.lower()
            filtered_skills = [
                skill
                for skill in filtered_skills
                if query_lower in skill.description.lower()
            ]

        return filtered_skills

    def validate_skill(self, skill_path: Path) -> tuple[bool, str | None]:
        """Validate a skill file.

        Args:
            skill_path: Path to SKILL.md file.

        Returns:
            Tuple of (is_valid, error_message). error_message is None if valid.
        """
        try:
            self._parse_skill_md(skill_path)
            return (True, None)
        except ValidationError as e:
            return (False, f"Validation error: {e}")
        except yaml.YAMLError as e:
            return (False, f"YAML parsing error: {e}")
        except ValueError as e:
            return (False, str(e))
        except Exception as e:
            return (False, f"Unexpected error: {e}")

    def _parse_skill_md(self, skill_path: Path) -> Skill:
        """Parse SKILL.md file into a Skill object.

        Args:
            skill_path: Path to SKILL.md file.

        Returns:
            Parsed Skill object.

        Raises:
            ValueError: If file format is invalid.
            ValidationError: If frontmatter doesn't match schema.
            yaml.YAMLError: If YAML parsing fails.
        """
        content = skill_path.read_text(encoding="utf-8")

        # Parse YAML frontmatter using regex
        # Format: ---\nYAML content\n---\n\nMarkdown body
        frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if not match:
            raise ValueError(
                "Invalid SKILL.md format. Expected YAML frontmatter between '---' markers."
            )

        yaml_content = match.group(1)
        markdown_body = match.group(2).strip()

        # Parse and validate YAML frontmatter
        try:
            frontmatter_dict = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Failed to parse YAML frontmatter: {e}") from e

        if not isinstance(frontmatter_dict, dict):
            raise ValueError("Frontmatter must be a YAML dictionary")

        # Validate with Pydantic
        frontmatter = SkillFrontmatter(**frontmatter_dict)

        # Get skill directory path
        directory_path = str(skill_path.parent.resolve())

        return Skill(
            frontmatter=frontmatter,
            markdown_body=markdown_body,
            directory_path=directory_path,
        )
