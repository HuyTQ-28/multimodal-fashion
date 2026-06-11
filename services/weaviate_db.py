"""Weaviate vector search stubs."""

from typing import Any


class WeaviateProductIndex:
    """Weaviate index wrapper for fashion products."""

    def __init__(self, url: str, api_key: str, collection_name: str) -> None:
        """Initialize the Weaviate product index client."""
        raise NotImplementedError

    def knn_search(self, vector: list[float], limit: int = 20) -> list[dict[str, Any]]:
        """Run K-NN vector search over product embeddings."""
        raise NotImplementedError

    def hybrid_search(
        self,
        query: str,
        vector: list[float] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Run hybrid BM25 plus vector search."""
        raise NotImplementedError

    def insert_product(
        self,
        product_id: str,
        vector: list[float],
        properties: dict[str, Any],
    ) -> None:
        """Insert one product into Weaviate."""
        raise NotImplementedError

    def batch_insert_products(self, products: list[dict[str, Any]]) -> None:
        """Insert many products into Weaviate."""
        raise NotImplementedError

