"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from services.embedding import ProductEmbeddingService
from services.recommender import RecommenderService
from services.redis_db import RedisSessionStore
from services.weaviate_db import WeaviateProductIndex
from utils.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create shared backend clients once per FastAPI process."""
    settings = get_settings()
    product_index = WeaviateProductIndex(
        url=settings.weaviate_url,
        api_key=settings.weaviate_api_key,
        collection_name=settings.weaviate_collection,
    )
    session_store = RedisSessionStore(
        redis_url=settings.redis_url,
        catalog_mean_vector=settings.catalog_mean_vector,
        ttl_seconds=settings.redis_session_ttl_seconds,
    )
    embedding_service = ProductEmbeddingService(settings.student_mlp_path)
    app.state.recommender_service = RecommenderService(
        session_store=session_store,
        product_index=product_index,
        embedding_service=embedding_service,
        catalog_mean_vector=settings.catalog_mean_vector,
    )

    try:
        yield
    finally:
        product_index.close()


settings = get_settings()

app = FastAPI(title="FREEDOM-RT", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
