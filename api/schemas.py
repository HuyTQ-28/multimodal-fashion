"""Pydantic schemas for FREEDOM-RT API requests and responses."""

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl


InteractionType = Literal["click", "like", "add_to_cart"]


class InteractionRequest(BaseModel):
    """Payload for intent-aware preference updates."""

    session_id: str = Field(..., min_length=1)
    article_id: str = Field(..., min_length=1)
    action_type: InteractionType


class InteractionResponse(BaseModel):
    """Response after persisting a session EMA update."""

    status: str
    session_id: str
    article_id: str
    action_type: InteractionType
    vector_dim: int


class ColdStartProductRequest(BaseModel):
    """Payload for inserting a new product with runtime embeddings."""

    article_id: str = Field(default_factory=lambda: f"frt_{uuid4().hex}", min_length=1)
    image_url: HttpUrl
    prod_name: str = ""
    detail_desc: str = ""
    product_type_name: str = ""
    colour_group_name: str = ""
    graphical_appearance_name: str = ""
    index_name: str = ""


class ProductResponse(BaseModel):
    """Standard product response returned by recommendation/search endpoints."""

    article_id: str
    image_url: str = ""
    prod_name: str = ""
    detail_desc: str = ""
    product_type_name: str = ""
    colour_group_name: str = ""
    graphical_appearance_name: str = ""
    index_name: str = ""
    score: float | None = None
