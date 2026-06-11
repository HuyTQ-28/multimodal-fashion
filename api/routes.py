"""API route declarations for FREEDOM-RT."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.schemas import (
    ColdStartProductRequest,
    InteractionRequest,
    InteractionResponse,
    ProductResponse,
)
from services.recommender import RecommenderService


router = APIRouter(prefix="/api/v1", tags=["freedom-rt"])


def get_recommender_service(request: Request) -> RecommenderService:
    """Resolve the app-level singleton RecommenderService."""
    service = getattr(request.app.state, "recommender_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation service is not initialized.",
        )
    return service


@router.get("/home", response_model=list[ProductResponse])
async def get_home_feed(
    service: Annotated[RecommenderService, Depends(get_recommender_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ProductResponse]:
    """Return the initial landing feed using the catalog mean vector."""
    return _to_products(service.get_home_feed(limit=limit))


@router.post("/interactions", response_model=InteractionResponse)
async def update_interaction(
    payload: InteractionRequest,
    service: Annotated[RecommenderService, Depends(get_recommender_service)],
) -> InteractionResponse:
    """Update a user's intent-aware EMA vector from an interaction."""
    try:
        updated_vector = service.record_interaction(
            session_id=payload.session_id,
            article_id=payload.article_id,
            action_type=payload.action_type,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return InteractionResponse(
        status="updated",
        session_id=payload.session_id,
        article_id=payload.article_id,
        action_type=payload.action_type,
        vector_dim=len(updated_vector),
    )


@router.get("/recommendations", response_model=list[ProductResponse])
async def get_recommendations(
    service: Annotated[RecommenderService, Depends(get_recommender_service)],
    session_id: Annotated[str, Query(min_length=1)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ProductResponse]:
    """Return personalized K-NN recommendations for a session."""
    return _to_products(service.get_recommendations(session_id=session_id, limit=limit))


@router.get("/search", response_model=list[ProductResponse])
async def hybrid_search(
    service: Annotated[RecommenderService, Depends(get_recommender_service)],
    q: Annotated[str, Query(min_length=1)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ProductResponse]:
    """Return hybrid BM25 and vector search results."""
    return _to_products(service.hybrid_search(query=q, limit=limit))


@router.post("/products", response_model=dict[str, str])
async def add_cold_start_product(
    payload: ColdStartProductRequest,
    service: Annotated[RecommenderService, Depends(get_recommender_service)],
) -> dict[str, str]:
    """Add a cold-start product with both Weaviate named vectors."""
    try:
        object_uuid = service.insert_cold_start_product(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "status": "inserted",
        "article_id": payload.article_id,
        "uuid": object_uuid,
    }


def _to_products(items: list[dict[str, object]]) -> list[ProductResponse]:
    """Normalize Weaviate dictionaries into API response models."""
    return [ProductResponse.model_validate(item) for item in items]
