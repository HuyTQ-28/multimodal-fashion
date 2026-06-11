"""Weaviate Cloud wrapper for FashionItem named-vector search."""

from __future__ import annotations

from typing import Any
import uuid

import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import Filter, MetadataQuery
from weaviate.client import WeaviateClient


PRODUCT_PROPERTIES: tuple[str, ...] = (
    "article_id",
    "image_url",
    "prod_name",
    "detail_desc",
    "product_type_name",
    "colour_group_name",
    "graphical_appearance_name",
    "index_name",
)


class WeaviateProductIndex:
    """Search and mutate the single FashionItem collection."""

    def __init__(self, url: str, api_key: str, collection_name: str = "FashionItem") -> None:
        self.client: WeaviateClient = weaviate.connect_to_weaviate_cloud(
            cluster_url=url,
            auth_credentials=Auth.api_key(api_key),
        )
        self.collection_name = collection_name
        self.collection = self.client.collections.get(collection_name)

    def close(self) -> None:
        """Close the underlying Weaviate client connection."""
        self.client.close()

    def knn_search(
        self,
        vector: list[float],
        target_vector: str = "rec_vector",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Run K-NN search against a specific named vector space."""
        response = self.collection.query.near_vector(
            near_vector=vector,
            target_vector=target_vector,
            limit=limit,
            return_properties=list(PRODUCT_PROPERTIES),
            return_metadata=MetadataQuery(distance=True),
        )
        return [self._format_object(obj) for obj in response.objects]

    def hybrid_search(
        self,
        query: str,
        vector: list[float],
        target_vector: str = "rec_vector",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Run BM25 plus vector hybrid search against the rec_vector space."""
        response = self.collection.query.hybrid(
            query=query,
            vector=vector,
            target_vector=target_vector,
            alpha=0.5,
            limit=limit,
            return_properties=list(PRODUCT_PROPERTIES),
            return_metadata=MetadataQuery(score=True),
        )
        return [self._format_object(obj) for obj in response.objects]

    def get_rec_vector_by_article_id(self, article_id: str) -> list[float]:
        """Fetch the stored 128-dim rec_vector for one article."""
        response = self.collection.query.fetch_objects(
            filters=Filter.by_property("article_id").equal(article_id),
            limit=1,
            include_vector="rec_vector",
            return_properties=["article_id"],
        )
        if not response.objects:
            raise KeyError(f"Article not found in Weaviate: {article_id}")

        vector = response.objects[0].vector
        rec_vector = vector.get("rec_vector") if isinstance(vector, dict) else vector
        if rec_vector is None:
            raise KeyError(f"Missing rec_vector for article_id={article_id}")
        return [float(value) for value in rec_vector]

    def insert_product(self, properties: dict[str, Any], vectors: dict[str, list[float]]) -> str:
        """Insert one FashionItem with both named vectors."""
        article_id = str(properties["article_id"])
        object_uuid = self._stable_uuid(article_id)
        clean_properties = {
            field: str(properties.get(field, "") or "")
            for field in PRODUCT_PROPERTIES
        }
        self.collection.data.insert(
            properties=clean_properties,
            uuid=object_uuid,
            vector=vectors,
        )
        return object_uuid

    @staticmethod
    def _stable_uuid(article_id: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"freedom-rt/fashion-item/{article_id}"))

    @staticmethod
    def _format_object(obj: Any) -> dict[str, Any]:
        properties = dict(obj.properties or {})
        metadata = obj.metadata
        score = getattr(metadata, "score", None)
        distance = getattr(metadata, "distance", None)
        properties["score"] = score if score is not None else distance
        return properties
