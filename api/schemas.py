"""Pydantic schemas for API requests and responses."""

from typing import Literal

from pydantic import BaseModel, Field


InteractionType = Literal["click", "like", "cart"]


class InteractionRequest(BaseModel):
    """Payload for a user-product interaction."""

    session_id: str
    product_id: str
    interaction_type: InteractionType
    product_vector: list[float] = Field(..., min_length=128, max_length=128)


class RecommendationRequest(BaseModel):
    """Payload for personalized K-NN recommendations."""

    session_id: str
    limit: int = Field(default=20, ge=1, le=100)


class HybridSearchRequest(BaseModel):
    """Payload for hybrid text and vector search."""

    query: str
    session_id: str | None = None
    query_vector: list[float] | None = Field(default=None, min_length=128, max_length=128)
    limit: int = Field(default=20, ge=1, le=100)


class ColdStartProductRequest(BaseModel):
    """Payload for inserting a cold-start fashion product."""

    product_id: str
    title: str
    description: str | None = None
    image_url: str | None = None
    feature_vector: list[float] = Field(..., min_length=128, max_length=128)


class ProductResponse(BaseModel):
    """Product recommendation response."""

    product_id: str
    title: str | None = None
    image_url: str | None = None
    score: float | None = None
    metadata: dict[str, str | int | float | bool | None] | None = None

