"""Skills management - discovery, loading, parsing, and validation."""

import logging
import re
from pathlib import Path

import yaml
from pydantic import ValidationError

from agent_skills_mcp.config import get_config
from agent_skills_mcp.models import Skill, SkillFrontmatter

logger = logging.getLogger(__name__)


class SkillsManager:
    """Manager for Agent Skills operations."""

    def __init__(
        self,
        skills_directory: Path | None = None,
        vector_store: "VectorStore | None" = None,
    ):
        """Initialize the skills manager.

        Args:
            skills_directory: Path to skills directory. If None, uses config default.
            vector_store: Optional VectorStore for semantic search.
        """
        self.config = get_config()
        self.skills_directory = skills_directory or self.config.skills_directory
        self.skills_directory = Path(self.skills_directory).resolve()

        if not self.skills_directory.exists():
            raise ValueError(f"Skills directory not found: {self.skills_directory}")

        self._vector_store = vector_store
        self._vector_store_initialized = False

    def set_vector_store(self, vector_store: "VectorStore") -> None:
        """Set the vector store for semantic search.

        Args:
            vector_store: VectorStore instance to use.
        """
        self._vector_store = vector_store
        self._vector_store_initialized = False

    def _ensure_vector_store_initialized(self) -> bool:
        """Ensure vector store is initialized with current skills.

        Returns:
            True if vector store is ready, False otherwise.
        """
        if not self._vector_store:
            return False

        if self._vector_store_initialized:
            return True

        try:
            all_skills = self._load_all_skills()
            if self._vector_store.initialize(all_skills):
                self._vector_store_initialized = True
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to initialize vector store: {e}")
            return False

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
        limit: int | None = None,
    ) -> list[Skill]:
        """Search for skills by query and/or name filter.

        Uses semantic search when available, falls back to keyword search.

        Args:
            query: Search query (semantic search or partial match).
            name_filter: Name prefix filter (case-insensitive).
            limit: Maximum number of results (default from config).

        Returns:
            List of matching Skill objects.
        """
        if limit is None:
            limit = self.config.semantic_search_limit

        # Try semantic search if enabled and query provided
        if (
            query
            and self.config.semantic_search_enabled
            and self._vector_store
            and self._ensure_vector_store_initialized()
        ):
            try:
                return self._semantic_search(query, name_filter, limit)
            except Exception as e:
                logger.warning(f"Semantic search failed, falling back to keyword: {e}")

        # Fallback to keyword search
        return self._keyword_search(query, name_filter, limit)

    def _semantic_search(
        self,
        query: str,
        name_filter: str | None,
        limit: int,
    ) -> list[Skill]:
        """Perform semantic search using vector store.

        Args:
            query: Search query string.
            name_filter: Optional name prefix filter.
            limit: Maximum number of results.

        Returns:
            List of matching Skill objects.
        """
        # Get more results than needed if we need to filter by name
        search_limit = limit * 3 if name_filter else limit

        results = self._vector_store.search(query, limit=search_limit)

        # Apply name filter if specified
        if name_filter:
            name_filter_lower = name_filter.lower()
            results = [
                r for r in results if r.skill_name.lower().startswith(name_filter_lower)
            ]

        # Return skills, respecting limit
        return [r.skill for r in results[:limit]]

    def _keyword_search(
        self,
        query: str | None,
        name_filter: str | None,
        limit: int,
    ) -> list[Skill]:
        """Perform keyword-based search (fallback).

        Args:
            query: Search query for description matching.
            name_filter: Name prefix filter.
            limit: Maximum number of results.

        Returns:
            List of matching Skill objects.
        """
        all_skills = self._load_all_skills()
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
                or query_lower in skill.name.lower()
            ]

        return filtered_skills[:limit]

    def _load_all_skills(self) -> list[Skill]:
        """Load all valid skills from the skills directory.

        Returns:
            List of Skill objects.
        """
        results = []

        for skill_dir in self.skills_directory.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                skill = self._parse_skill_md(skill_file)
                results.append(skill)
            except (ValidationError, ValueError, yaml.YAMLError):
                continue

        return results

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

    def refresh_index(self) -> bool:
        """Refresh the vector store index with current skills.

        Returns:
            True if refresh was successful, False otherwise.
        """
        if not self._vector_store:
            return False

        try:
            all_skills = self._load_all_skills()
            if self._vector_store.rebuild(all_skills):
                self._vector_store_initialized = True
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to refresh vector store index: {e}")
            return False


# Import at end to avoid circular import
from agent_skills_mcp.vector_store import VectorStore  # noqa: E402, F401
