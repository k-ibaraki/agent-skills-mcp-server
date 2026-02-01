"""Vector store for semantic search using ChromaDB and sentence-transformers."""

import logging
from dataclasses import dataclass

from agent_skills_mcp.config import get_config
from agent_skills_mcp.models import Skill

logger = logging.getLogger(__name__)


@dataclass
class SemanticSearchResult:
    """Result of a semantic search query."""

    skill_name: str
    score: float
    skill: Skill


class VectorStore:
    """Vector store for semantic skill search using ChromaDB."""

    def __init__(self):
        """Initialize the vector store with lazy loading."""
        self._initialized = False
        self._client = None
        self._collection = None
        self._embedding_function = None
        self._skills_map: dict[str, Skill] = {}
        self._config = get_config()

    def _ensure_initialized(self) -> bool:
        """Ensure embedding model and ChromaDB are initialized.

        Returns:
            True if initialization was successful, False otherwise.
        """
        if self._initialized:
            return True

        try:
            self._initialize_components()
            self._initialized = True
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize vector store: {e}")
            return False

    def _initialize_components(self) -> None:
        """Initialize embedding model and ChromaDB client."""
        import chromadb
        from chromadb.utils import embedding_functions

        logger.info(
            f"Initializing vector store with model: {self._config.embedding_model}"
        )

        self._embedding_function = (
            embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self._config.embedding_model
            )
        )

        self._client = chromadb.Client()

        self._collection = self._client.get_or_create_collection(
            name="skills",
            embedding_function=self._embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info("Vector store initialized successfully")

    def initialize(self, skills: list[Skill]) -> bool:
        """Build vector index from skill list.

        Args:
            skills: List of skills to index.

        Returns:
            True if initialization was successful, False otherwise.
        """
        if not self._ensure_initialized():
            return False

        try:
            self._skills_map = {skill.name: skill for skill in skills}
            self._collection.delete(where={"indexed": True})

            if not skills:
                logger.info("No skills to index")
                return True

            documents = []
            ids = []
            metadatas = []

            for skill in skills:
                search_text = f"{skill.name} {skill.description}"
                documents.append(search_text)
                ids.append(skill.name)
                metadatas.append(
                    {
                        "name": skill.name,
                        "description": skill.description,
                        "indexed": True,
                    }
                )

            self._collection.add(
                documents=documents,
                ids=ids,
                metadatas=metadatas,
            )

            logger.info(f"Indexed {len(skills)} skills")
            return True

        except Exception as e:
            logger.warning(f"Failed to initialize vector index: {e}")
            return False

    def search(
        self, query: str, limit: int | None = None
    ) -> list[SemanticSearchResult]:
        """Perform semantic search for skills.

        Args:
            query: Search query string.
            limit: Maximum number of results to return.

        Returns:
            List of SemanticSearchResult sorted by relevance.

        Raises:
            RuntimeError: If vector store is not initialized.
        """
        if not self._initialized:
            raise RuntimeError("Vector store not initialized. Call initialize() first.")

        if limit is None:
            limit = self._config.semantic_search_limit

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(limit, len(self._skills_map)),
                include=["distances", "metadatas"],
            )

            search_results = []

            if results["ids"] and results["ids"][0]:
                ids = results["ids"][0]
                distances = results["distances"][0] if results["distances"] else []

                for i, skill_name in enumerate(ids):
                    if skill_name not in self._skills_map:
                        continue

                    distance = distances[i] if i < len(distances) else 1.0
                    score = 1.0 - distance

                    search_results.append(
                        SemanticSearchResult(
                            skill_name=skill_name,
                            score=score,
                            skill=self._skills_map[skill_name],
                        )
                    )

            search_results.sort(key=lambda r: r.score, reverse=True)
            return search_results

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            raise

    def rebuild(self, skills: list[Skill]) -> bool:
        """Rebuild the vector index with new skills.

        Args:
            skills: List of skills to index.

        Returns:
            True if rebuild was successful, False otherwise.
        """
        return self.initialize(skills)

    @property
    def is_initialized(self) -> bool:
        """Check if the vector store is initialized."""
        return self._initialized

    @property
    def skill_count(self) -> int:
        """Get the number of indexed skills."""
        return len(self._skills_map)
