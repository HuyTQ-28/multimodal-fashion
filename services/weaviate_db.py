"""Weaviate Cloud wrapper for FashionItem named-vector search."""

from __future__ import annotations

import re
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

HYBRID_QUERY_PROPERTIES: tuple[str, ...] = (
    "prod_name^5",
    "product_type_name^4",
    "detail_desc^2",
    "index_name",
    "colour_group_name",
    "graphical_appearance_name",
)

TEXT_RANK_FIELDS: tuple[str, ...] = (
    "prod_name",
    "product_type_name",
    "detail_desc",
    "index_name",
    "colour_group_name",
    "graphical_appearance_name",
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
        """Run text-first BM25 plus vector hybrid search against rec_vector."""
        candidate_limit = min(max(limit * 4, 20), 100)
        response = self.collection.query.hybrid(
            query=query,
            vector=vector,
            target_vector=target_vector,
            alpha=0.15,
            query_properties=list(HYBRID_QUERY_PROPERTIES),
            limit=candidate_limit,
            return_properties=list(PRODUCT_PROPERTIES),
            return_metadata=MetadataQuery(score=True),
        )
        candidates = [self._format_object(obj) for obj in response.objects]
        return self._rerank_text_matches(query=query, items=candidates)[:limit]

    def get_rec_vector_by_article_id(self, article_id: str) -> list[float]:
        """Fetch the stored 128-dim rec_vector for one article."""
        response = self.collection.query.fetch_objects(
            filters=Filter.by_property("article_id").equal(article_id),
            limit=1,
            include_vector=True,
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

    @classmethod
    def _rerank_text_matches(
        cls,
        query: str,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Keep hybrid recall while making exact text intent dominate ranking."""
        query_text = query.strip().lower()
        tokens = cls._tokens(query_text)
        if not query_text or not tokens:
            return items

        ranked_items = [
            (cls._lexical_score(query_text=query_text, tokens=tokens, item=item), index, item)
            for index, item in enumerate(items)
        ]
        has_text_match = any(score > 0 for score, _, _ in ranked_items)
        if not has_text_match:
            return items

        ranked_items.sort(
            key=lambda row: (
                row[0] == 0,
                -row[0],
                -(float(row[2].get("score") or 0.0)),
                row[1],
            )
        )
        return [item for _, _, item in ranked_items]

    @classmethod
    def _lexical_score(
        cls,
        query_text: str,
        tokens: set[str],
        item: dict[str, Any],
    ) -> float:
        score = 0.0
        for field in TEXT_RANK_FIELDS:
            value = str(item.get(field, "") or "").lower()
            if not value:
                continue

            field_weight = {
                "prod_name": 6.0,
                "product_type_name": 5.0,
                "detail_desc": 2.0,
            }.get(field, 1.0)

            if value == query_text:
                score += field_weight * 3.0
            elif query_text in value:
                score += field_weight * 2.0

            value_tokens = cls._tokens(value)
            score += field_weight * len(tokens.intersection(value_tokens))

        return score

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 1}
