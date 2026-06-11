"""Recommendation orchestration service."""

from __future__ import annotations

from typing import Any

from api.schemas import ColdStartProductRequest
from services.embedding import ProductEmbeddingService
from services.redis_db import InteractionType, RedisSessionStore
from services.weaviate_db import WeaviateProductIndex


class RecommenderService:
    """Connect FastAPI routes to Redis state, embeddings, and Weaviate search."""

    def __init__(
        self,
        session_store: RedisSessionStore,
        product_index: WeaviateProductIndex,
        embedding_service: ProductEmbeddingService,
        catalog_mean_vector: list[float],
    ) -> None:
        self.session_store = session_store
        self.product_index = product_index
        self.embedding_service = embedding_service
        self.catalog_mean_vector = [float(value) for value in catalog_mean_vector]

    def get_home_feed(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return a uniform initial feed from the catalog mean vector."""
        return self.product_index.knn_search(
            vector=self.catalog_mean_vector,
            target_vector="rec_vector",
            limit=limit,
        )

    def record_interaction(
        self,
        session_id: str,
        article_id: str,
        action_type: InteractionType,
    ) -> list[float]:
        """Fetch item rec_vector, update Redis EMA, and return the new vector."""
        item_vector = self.product_index.get_rec_vector_by_article_id(article_id)
        return self.session_store.update_ema_vector(
            session_id=session_id,
            item_vector=item_vector,
            action_type=action_type,
        )

    def get_recommendations(self, session_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Return personalized K-NN recommendations using the session EMA vector."""
        ema_vector = self.session_store.get_or_init_ema_vector(session_id)
        return self.product_index.knn_search(
            vector=ema_vector,
            target_vector="rec_vector",
            limit=limit,
        )

    def hybrid_search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Encode a text query and run Weaviate hybrid search over rec_vector."""
        query_vector = self.embedding_service.encode_text_query(query)
        return self.product_index.hybrid_search(
            query=query,
            vector=query_vector,
            target_vector="rec_vector",
            limit=limit,
        )

    def insert_cold_start_product(self, payload: ColdStartProductRequest) -> str:
        """Create named vectors for a new product and insert it into Weaviate."""
        text = " ".join(
            [
                payload.prod_name,
                payload.detail_desc,
                payload.product_type_name,
                payload.colour_group_name,
                payload.graphical_appearance_name,
                payload.index_name,
            ]
        )
        rec_vector, visual_vector = self.embedding_service.encode_product(
            text=text,
            image_url=str(payload.image_url),
        )
        return self.product_index.insert_product(
            properties=payload.model_dump(mode="json"),
            vectors={
                "rec_vector": rec_vector,
                "visual_vector": visual_vector,
            },
        )
