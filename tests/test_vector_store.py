"""Unit tests for VectorStore."""

import pytest

from agent_skills_mcp.models import Skill, SkillFrontmatter
from agent_skills_mcp.vector_store import SemanticSearchResult, VectorStore


def create_test_skill(name: str, description: str) -> Skill:
    """Create a test skill with given name and description."""
    return Skill(
        frontmatter=SkillFrontmatter(name=name, description=description),
        markdown_body=f"# {name}\n\nTest skill for {description}",
        directory_path=f"/test/skills/{name}",
    )


@pytest.fixture
def sample_skills() -> list[Skill]:
    """Create sample skills for testing."""
    return [
        create_test_skill(
            "weather-forecast",
            "Get weather forecast for a specific location",
        ),
        create_test_skill(
            "notepm-search",
            "Search and retrieve documents from NotePM",
        ),
        create_test_skill(
            "code-review",
            "Review code and provide suggestions for improvement",
        ),
        create_test_skill(
            "translate-text",
            "Translate text between multiple languages",
        ),
        create_test_skill(
            "summarize-article",
            "Summarize long articles into concise summaries",
        ),
    ]


@pytest.fixture
def vector_store() -> VectorStore:
    """Create a fresh VectorStore instance."""
    return VectorStore()


class TestVectorStoreInitialization:
    """Tests for VectorStore initialization."""

    @pytest.mark.unit
    def test_vector_store_lazy_initialization(self, vector_store: VectorStore):
        """VectorStore should not be initialized until initialize() is called."""
        assert not vector_store.is_initialized
        assert vector_store.skill_count == 0

    @pytest.mark.unit
    def test_vector_store_initialize_with_skills(
        self, vector_store: VectorStore, sample_skills: list[Skill]
    ):
        """VectorStore should successfully initialize with skills."""
        result = vector_store.initialize(sample_skills)
        assert result is True
        assert vector_store.is_initialized
        assert vector_store.skill_count == len(sample_skills)

    @pytest.mark.unit
    def test_vector_store_initialize_with_empty_list(self, vector_store: VectorStore):
        """VectorStore should handle empty skill list."""
        result = vector_store.initialize([])
        assert result is True
        assert vector_store.is_initialized
        assert vector_store.skill_count == 0


class TestVectorStoreSearch:
    """Tests for VectorStore search functionality."""

    @pytest.mark.unit
    def test_search_without_initialization_raises_error(
        self, vector_store: VectorStore
    ):
        """Search should raise error if not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            vector_store.search("weather")

    @pytest.mark.unit
    def test_search_returns_semantic_results(
        self, vector_store: VectorStore, sample_skills: list[Skill]
    ):
        """Search should return semantically relevant results."""
        vector_store.initialize(sample_skills)
        results = vector_store.search("weather")

        assert len(results) > 0
        assert all(isinstance(r, SemanticSearchResult) for r in results)
        assert results[0].skill_name == "weather-forecast"
        assert results[0].score > 0

    @pytest.mark.unit
    def test_search_respects_limit(
        self, vector_store: VectorStore, sample_skills: list[Skill]
    ):
        """Search should respect the limit parameter."""
        vector_store.initialize(sample_skills)
        results = vector_store.search("document", limit=2)

        assert len(results) <= 2

    @pytest.mark.unit
    def test_search_japanese_query(
        self, vector_store: VectorStore, sample_skills: list[Skill]
    ):
        """Search should work with Japanese queries."""
        vector_store.initialize(sample_skills)
        results = vector_store.search("天気予報")

        assert len(results) > 0
        assert results[0].skill_name == "weather-forecast"

    @pytest.mark.unit
    def test_search_document_query(
        self, vector_store: VectorStore, sample_skills: list[Skill]
    ):
        """Search for document-related skills."""
        vector_store.initialize(sample_skills)
        results = vector_store.search("ドキュメント検索")

        assert len(results) > 0
        assert results[0].skill_name == "notepm-search"

    @pytest.mark.unit
    def test_search_results_sorted_by_relevance(
        self, vector_store: VectorStore, sample_skills: list[Skill]
    ):
        """Results should be sorted by relevance score descending."""
        vector_store.initialize(sample_skills)
        results = vector_store.search("code review suggestions")

        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


class TestVectorStoreRebuild:
    """Tests for VectorStore rebuild functionality."""

    @pytest.mark.unit
    def test_rebuild_replaces_existing_index(
        self, vector_store: VectorStore, sample_skills: list[Skill]
    ):
        """Rebuild should replace the existing index."""
        vector_store.initialize(sample_skills)
        assert vector_store.skill_count == 5

        new_skills = [
            create_test_skill("new-skill", "A brand new skill"),
        ]
        result = vector_store.rebuild(new_skills)

        assert result is True
        assert vector_store.skill_count == 1

        results = vector_store.search("brand new")
        assert len(results) == 1
        assert results[0].skill_name == "new-skill"

    @pytest.mark.unit
    def test_rebuild_with_empty_list(
        self, vector_store: VectorStore, sample_skills: list[Skill]
    ):
        """Rebuild with empty list should clear the index."""
        vector_store.initialize(sample_skills)
        assert vector_store.skill_count == 5

        result = vector_store.rebuild([])
        assert result is True
        assert vector_store.skill_count == 0


class TestSemanticSearchResult:
    """Tests for SemanticSearchResult dataclass."""

    @pytest.mark.unit
    def test_semantic_search_result_creation(self, sample_skills: list[Skill]):
        """SemanticSearchResult should be created correctly."""
        skill = sample_skills[0]
        result = SemanticSearchResult(
            skill_name=skill.name,
            score=0.85,
            skill=skill,
        )

        assert result.skill_name == "weather-forecast"
        assert result.score == 0.85
        assert result.skill == skill
