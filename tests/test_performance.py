"""Performance tests for semantic search."""

import tempfile
import time
from pathlib import Path

import pytest

from agent_skills_mcp.models import Skill, SkillFrontmatter
from agent_skills_mcp.skills_manager import SkillsManager
from agent_skills_mcp.vector_store import VectorStore


def create_test_skill(name: str, description: str) -> Skill:
    """Create a test skill with given name and description."""
    return Skill(
        frontmatter=SkillFrontmatter(name=name, description=description),
        markdown_body=f"# {name}\n\nTest skill for {description}",
        directory_path=f"/test/skills/{name}",
    )


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
def many_skills() -> list[Skill]:
    """Create a large set of skills for performance testing."""
    skills = []
    descriptions = [
        "Process and analyze data from various sources",
        "Generate reports and visualizations",
        "Search and retrieve documents from knowledge bases",
        "Translate text between multiple languages",
        "Summarize long articles and documents",
        "Review and improve code quality",
        "Manage project tasks and workflows",
        "Send notifications and alerts",
        "Integrate with external APIs and services",
        "Monitor and log system activities",
    ]

    for i in range(50):
        desc_idx = i % len(descriptions)
        skills.append(
            create_test_skill(
                f"skill-{i:03d}",
                f"{descriptions[desc_idx]} - variant {i}",
            )
        )
    return skills


@pytest.fixture
def skills_directory_large():
    """Create a temporary directory with many test skills."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)

        descriptions = [
            "Process and analyze data from various sources",
            "Generate reports and visualizations",
            "Search and retrieve documents from knowledge bases",
            "Translate text between multiple languages",
            "Summarize long articles and documents",
            "Review and improve code quality",
            "Manage project tasks and workflows",
            "Send notifications and alerts",
            "Integrate with external APIs and services",
            "Monitor and log system activities",
        ]

        for i in range(50):
            desc_idx = i % len(descriptions)
            create_skill_file(
                skills_dir,
                f"skill-{i:03d}",
                f"{descriptions[desc_idx]} - variant {i}",
            )

        yield skills_dir


class TestVectorStorePerformance:
    """Performance tests for VectorStore."""

    @pytest.mark.slow
    def test_initialization_time(self, many_skills: list[Skill]):
        """Test that vector store initialization completes in reasonable time."""
        vector_store = VectorStore()

        start_time = time.perf_counter()
        result = vector_store.initialize(many_skills)
        elapsed_time = time.perf_counter() - start_time

        assert result is True
        # First initialization includes model loading, should be < 60 seconds
        assert elapsed_time < 60, (
            f"Initialization took {elapsed_time:.2f}s (expected < 60s)"
        )
        print(f"\nFirst initialization time: {elapsed_time:.2f}s")

    @pytest.mark.slow
    def test_search_latency(self, many_skills: list[Skill]):
        """Test that search operations are fast after initialization."""
        vector_store = VectorStore()
        vector_store.initialize(many_skills)

        queries = [
            "data analysis",
            "document search",
            "code review",
            "translate Japanese",
            "generate reports",
        ]

        latencies = []
        for query in queries:
            start_time = time.perf_counter()
            # Use threshold=0 to ensure results are returned
            results = vector_store.search(query, limit=10, threshold=0.0)
            elapsed_time = time.perf_counter() - start_time
            latencies.append(elapsed_time)
            assert len(results) > 0

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        # Search should be fast (< 100ms average)
        assert avg_latency < 0.1, (
            f"Average search latency {avg_latency:.3f}s (expected < 0.1s)"
        )
        assert max_latency < 0.5, (
            f"Max search latency {max_latency:.3f}s (expected < 0.5s)"
        )
        print(f"\nAverage search latency: {avg_latency * 1000:.1f}ms")
        print(f"Max search latency: {max_latency * 1000:.1f}ms")

    @pytest.mark.slow
    def test_rebuild_time(self, many_skills: list[Skill]):
        """Test that rebuild is faster than initial initialization."""
        vector_store = VectorStore()

        # First initialization
        vector_store.initialize(many_skills)

        # Rebuild (model already loaded)
        start_time = time.perf_counter()
        result = vector_store.rebuild(many_skills)
        elapsed_time = time.perf_counter() - start_time

        assert result is True
        # Rebuild should be faster since model is already loaded
        assert elapsed_time < 5, f"Rebuild took {elapsed_time:.2f}s (expected < 5s)"
        print(f"\nRebuild time: {elapsed_time:.2f}s")


class TestSkillsManagerPerformance:
    """Performance tests for SkillsManager with semantic search."""

    @pytest.mark.slow
    def test_first_search_latency(self, skills_directory_large: Path):
        """Test latency of first search (includes lazy initialization)."""
        vector_store = VectorStore()
        manager = SkillsManager(
            skills_directory=skills_directory_large,
            vector_store=vector_store,
        )

        start_time = time.perf_counter()
        results = manager.search_skills(query="data analysis")
        elapsed_time = time.perf_counter() - start_time

        assert len(results) > 0
        # First search includes model loading and indexing
        assert elapsed_time < 120, (
            f"First search took {elapsed_time:.2f}s (expected < 120s)"
        )
        print(f"\nFirst search time (with lazy init): {elapsed_time:.2f}s")

    @pytest.mark.slow
    def test_subsequent_search_latency(self, skills_directory_large: Path):
        """Test latency of subsequent searches (after initialization)."""
        vector_store = VectorStore()
        manager = SkillsManager(
            skills_directory=skills_directory_large,
            vector_store=vector_store,
        )

        # Warm up (trigger lazy initialization)
        manager.search_skills(query="warmup")

        queries = [
            "process data",
            "search documents",
            "review code",
            "generate reports",
            "translate text",
        ]

        latencies = []
        for query in queries:
            start_time = time.perf_counter()
            results = manager.search_skills(query=query)
            elapsed_time = time.perf_counter() - start_time
            latencies.append(elapsed_time)
            assert len(results) > 0

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        # Subsequent searches should be fast
        assert avg_latency < 0.1, (
            f"Average search latency {avg_latency:.3f}s (expected < 0.1s)"
        )
        print(f"\nSubsequent search average latency: {avg_latency * 1000:.1f}ms")
        print(f"Subsequent search max latency: {max_latency * 1000:.1f}ms")


class TestStartupPerformance:
    """Tests for server startup performance."""

    @pytest.mark.slow
    def test_vector_store_creation_is_fast(self):
        """VectorStore creation should be nearly instant (lazy loading)."""
        start_time = time.perf_counter()
        vector_store = VectorStore()
        elapsed_time = time.perf_counter() - start_time

        assert not vector_store.is_initialized
        # Creation should be instant (< 10ms)
        assert elapsed_time < 0.01, (
            f"VectorStore creation took {elapsed_time:.3f}s (expected < 0.01s)"
        )
        print(f"\nVectorStore creation time: {elapsed_time * 1000:.2f}ms")

    @pytest.mark.slow
    def test_skills_manager_creation_is_fast(self, skills_directory_large: Path):
        """SkillsManager creation should be fast (no eager loading)."""
        vector_store = VectorStore()

        start_time = time.perf_counter()
        manager = SkillsManager(
            skills_directory=skills_directory_large,
            vector_store=vector_store,
        )
        elapsed_time = time.perf_counter() - start_time

        assert manager is not None
        # Creation should be fast (< 100ms)
        assert elapsed_time < 0.1, (
            f"SkillsManager creation took {elapsed_time:.3f}s (expected < 0.1s)"
        )
        print(f"\nSkillsManager creation time: {elapsed_time * 1000:.2f}ms")
