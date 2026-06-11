"""API route declarations for FREEDOM-RT."""

from fastapi import APIRouter

from api.schemas import (
    ColdStartProductRequest,
    HybridSearchRequest,
    InteractionRequest,
    ProductResponse,
    RecommendationRequest,
)

router = APIRouter(prefix="/api/v1", tags=["freedom-rt"])


@router.post("/interactions", response_model=dict[str, str])
async def update_interaction(payload: InteractionRequest) -> dict[str, str]:
    """Update a user's intent-aware EMA vector from an interaction."""
    raise NotImplementedError


@router.post("/recommendations", response_model=list[ProductResponse])
async def get_recommendations(payload: RecommendationRequest) -> list[ProductResponse]:
    """Return K-NN recommendations for a user session."""
    raise NotImplementedError


@router.post("/search/hybrid", response_model=list[ProductResponse])
async def hybrid_search(payload: HybridSearchRequest) -> list[ProductResponse]:
    """Return hybrid BM25 and vector search results."""
    raise NotImplementedError


@router.post("/products/cold-start", response_model=dict[str, str])
async def add_cold_start_product(payload: ColdStartProductRequest) -> dict[str, str]:
    """Add a new cold-start product to the vector index."""
    raise NotImplementedError

