"""Integration tests for SkillsManager with semantic search."""

import tempfile
from pathlib import Path

import pytest

from agent_skills_mcp.skills_manager import SkillSearchResult, SkillsManager
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
        assert all(isinstance(r, SkillSearchResult) for r in results)
        assert results[0].skill.name == "weather-forecast"
        assert results[0].score is not None
        assert results[0].score > 0

    @pytest.mark.integration
    def test_semantic_search_weather_japanese(
        self, skills_manager_with_vector_store: SkillsManager
    ):
        """Semantic search should find weather skill with Japanese query."""
        results = skills_manager_with_vector_store.search_skills(query="天気予報")
        assert len(results) > 0
        assert results[0].skill.name == "weather-forecast"
        assert results[0].score is not None

    @pytest.mark.integration
    def test_semantic_search_document_japanese(
        self, skills_manager_with_vector_store: SkillsManager
    ):
        """Semantic search should find document skill with Japanese query."""
        results = skills_manager_with_vector_store.search_skills(
            query="ドキュメント検索"
        )
        assert len(results) > 0
        assert results[0].skill.name == "notepm-search"
        assert results[0].score is not None

    @pytest.mark.integration
    def test_semantic_search_code_related(
        self, skills_manager_with_vector_store: SkillsManager
    ):
        """Semantic search should find code-related skills."""
        results = skills_manager_with_vector_store.search_skills(query="review my code")
        assert len(results) > 0
        assert results[0].skill.name == "code-review"

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
        assert all(r.skill.name.startswith("translate") for r in results)

    @pytest.mark.integration
    def test_search_without_query_returns_all(
        self, skills_manager_with_vector_store: SkillsManager
    ):
        """Search without query should return all skills (keyword search)."""
        results = skills_manager_with_vector_store.search_skills()
        assert len(results) == 5
        # Keyword search returns None for score
        assert all(r.score is None for r in results)

    @pytest.mark.integration
    def test_semantic_search_results_have_scores(
        self, skills_manager_with_vector_store: SkillsManager
    ):
        """Semantic search results should have relevance scores."""
        results = skills_manager_with_vector_store.search_skills(query="weather")
        assert len(results) > 0
        for result in results:
            assert result.score is not None
            assert 0.0 <= result.score <= 1.0

    @pytest.mark.integration
    def test_semantic_search_scores_are_sorted(
        self, skills_manager_with_vector_store: SkillsManager
    ):
        """Semantic search results should be sorted by score descending."""
        results = skills_manager_with_vector_store.search_skills(query="text")
        if len(results) > 1:
            scores = [r.score for r in results]
            assert scores == sorted(scores, reverse=True)


class TestKeywordSearchFallback:
    """Tests for keyword search fallback."""

    @pytest.mark.unit
    def test_keyword_search_without_vector_store(
        self, skills_manager_without_vector_store: SkillsManager
    ):
        """Search should work without vector store (keyword search)."""
        results = skills_manager_without_vector_store.search_skills(query="weather")
        assert len(results) >= 1
        assert any(r.skill.name == "weather-forecast" for r in results)
        # Keyword search returns None for score
        assert all(r.score is None for r in results)

    @pytest.mark.unit
    def test_keyword_search_with_name_filter(
        self, skills_manager_without_vector_store: SkillsManager
    ):
        """Keyword search should work with name filter."""
        results = skills_manager_without_vector_store.search_skills(name_filter="code")
        assert len(results) == 1
        assert results[0].skill.name == "code-review"


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
        skill_names = [r.skill.name for r in results]
        assert "new-weather-app" in skill_names


class TestThresholdFiltering:
    """Tests for similarity threshold filtering."""

    @pytest.mark.integration
    def test_threshold_filters_low_relevance(
        self, skills_manager_with_vector_store: SkillsManager
    ):
        """Results below threshold should be filtered out."""
        # Search for something very specific - low relevance results should be excluded
        results = skills_manager_with_vector_store.search_skills(
            query="weather forecast location"
        )
        # All results should have score above threshold (default 0.3)
        for result in results:
            if result.score is not None:
                assert result.score >= 0.3
