"""Integration tests for SkillsManager with semantic search."""

import tempfile
from pathlib import Path

import pytest

from agent_skills_mcp.skills_manager import SkillsManager
from agent_skills_mcp.vector_store import VectorStore


def create_skill_file(skill_dir: Path, name: str, description: str) -> None:
    """Create a SKILL.md file in the given directory."""
    skill_subdir = skill_dir / name
    skill_subdir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_subdir / "SKILL.md"
    skill_file.write_text(
        f"""---
name: {name}
description: {description}
---

# {name}

This is a test skill for {description}.
""",
        encoding="utf-8",
    )


@pytest.fixture
def skills_directory():
    """Create a temporary directory with test skills."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)

        # Create test skills
        create_skill_file(
            skills_dir,
            "weather-forecast",
            "Get weather forecast for a specific location",
        )
        create_skill_file(
            skills_dir,
            "notepm-search",
            "Search and retrieve documents from NotePM knowledge base",
        )
        create_skill_file(
            skills_dir,
            "code-review",
            "Review code and provide suggestions for improvement",
        )
        create_skill_file(
            skills_dir,
            "translate-text",
            "Translate text between multiple languages including Japanese and English",
        )
        create_skill_file(
            skills_dir,
            "summarize-article",
            "Summarize long articles into concise summaries",
        )

        yield skills_dir


@pytest.fixture
def skills_manager_with_vector_store(skills_directory: Path) -> SkillsManager:
    """Create a SkillsManager with VectorStore."""
    vector_store = VectorStore()
    manager = SkillsManager(
        skills_directory=skills_directory,
        vector_store=vector_store,
    )
    return manager


@pytest.fixture
def skills_manager_without_vector_store(skills_directory: Path) -> SkillsManager:
    """Create a SkillsManager without VectorStore."""
    return SkillsManager(skills_directory=skills_directory)


class TestSemanticSearchIntegration:
    """Integration tests for semantic search via SkillsManager."""

    @pytest.mark.integration
    def test_semantic_search_weather_english(
        self, skills_manager_with_vector_store: SkillsManager
    ):
        """Semantic search should find weather skill with English query."""
        results = skills_manager_with_vector_store.search_skills(query="weather")
        assert len(results) > 0
        assert results[0].name == "weather-forecast"

    @pytest.mark.integration
    def test_semantic_search_weather_japanese(
        self, skills_manager_with_vector_store: SkillsManager
    ):
        """Semantic search should find weather skill with Japanese query."""
        results = skills_manager_with_vector_store.search_skills(query="天気予報")
        assert len(results) > 0
        assert results[0].name == "weather-forecast"

    @pytest.mark.integration
    def test_semantic_search_document_japanese(
        self, skills_manager_with_vector_store: SkillsManager
    ):
        """Semantic search should find document skill with Japanese query."""
        results = skills_manager_with_vector_store.search_skills(
            query="ドキュメント検索"
        )
        assert len(results) > 0
        assert results[0].name == "notepm-search"

    @pytest.mark.integration
    def test_semantic_search_code_related(
        self, skills_manager_with_vector_store: SkillsManager
    ):
        """Semantic search should find code-related skills."""
        results = skills_manager_with_vector_store.search_skills(query="review my code")
        assert len(results) > 0
        assert results[0].name == "code-review"

    @pytest.mark.integration
    def test_semantic_search_respects_limit(
        self, skills_manager_with_vector_store: SkillsManager
    ):
        """Semantic search should respect the limit parameter."""
        results = skills_manager_with_vector_store.search_skills(query="text", limit=2)
        assert len(results) <= 2

    @pytest.mark.integration
    def test_semantic_search_with_name_filter(
        self, skills_manager_with_vector_store: SkillsManager
    ):
        """Semantic search should work with name filter."""
        results = skills_manager_with_vector_store.search_skills(
            query="text processing", name_filter="translate"
        )
        assert len(results) > 0
        assert all(r.name.startswith("translate") for r in results)

    @pytest.mark.integration
    def test_search_without_query_returns_all(
        self, skills_manager_with_vector_store: SkillsManager
    ):
        """Search without query should return all skills (keyword search)."""
        results = skills_manager_with_vector_store.search_skills()
        assert len(results) == 5


class TestKeywordSearchFallback:
    """Tests for keyword search fallback."""

    @pytest.mark.unit
    def test_keyword_search_without_vector_store(
        self, skills_manager_without_vector_store: SkillsManager
    ):
        """Search should work without vector store (keyword search)."""
        results = skills_manager_without_vector_store.search_skills(query="weather")
        assert len(results) >= 1
        assert any(r.name == "weather-forecast" for r in results)

    @pytest.mark.unit
    def test_keyword_search_with_name_filter(
        self, skills_manager_without_vector_store: SkillsManager
    ):
        """Keyword search should work with name filter."""
        results = skills_manager_without_vector_store.search_skills(name_filter="code")
        assert len(results) == 1
        assert results[0].name == "code-review"


class TestRefreshIndex:
    """Tests for index refresh functionality."""

    @pytest.mark.integration
    def test_refresh_index(
        self, skills_manager_with_vector_store: SkillsManager, skills_directory: Path
    ):
        """Refresh index should update the vector store."""
        # Initial search
        results = skills_manager_with_vector_store.search_skills(query="weather")
        assert len(results) > 0

        # Add a new skill
        create_skill_file(
            skills_directory,
            "new-weather-app",
            "Advanced weather application with hourly forecasts",
        )

        # Refresh index
        success = skills_manager_with_vector_store.refresh_index()
        assert success is True

        # Search should find the new skill
        results = skills_manager_with_vector_store.search_skills(query="weather")
        skill_names = [r.name for r in results]
        assert "new-weather-app" in skill_names
