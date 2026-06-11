"""Recommendation orchestration service."""

from typing import Any

from services.redis_db import InteractionType, RedisSessionStore
from services.weaviate_db import WeaviateProductIndex


class RecommenderService:
    """Connect API requests to Redis session state and Weaviate search."""

    def __init__(
        self,
        session_store: RedisSessionStore,
        product_index: WeaviateProductIndex,
    ) -> None:
        """Initialize the recommender dependencies."""
        raise NotImplementedError

    def record_interaction(
        self,
        session_id: str,
        product_id: str,
        product_vector: list[float],
        interaction_type: InteractionType,
    ) -> list[float]:
        """Record an interaction and update the session EMA vector."""
        raise NotImplementedError

    def recommend_for_session(self, session_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Return personalized K-NN recommendations for a session."""
        raise NotImplementedError

    def search_hybrid(
        self,
        query: str,
        session_id: str | None = None,
        query_vector: list[float] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Return hybrid text and vector search results."""
        raise NotImplementedError

    def add_cold_start_product(
        self,
        product_id: str,
        title: str,
        feature_vector: list[float],
        image_url: str | None = None,
        description: str | None = None,
    ) -> None:
        """Add a cold-start product to the search index."""
        raise NotImplementedError

