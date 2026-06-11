"""Application configuration loading."""

from functools import lru_cache
from pathlib import Path

import numpy as np
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    app_name: str = "FREEDOM-RT"
    app_env: str = "development"
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"
    redis_session_ttl_seconds: int = 604800
    weaviate_url: str = ""
    weaviate_api_key: str = ""
    weaviate_collection: str = "FashionItem"
    catalog_mean_vector: list[float] = Field(default_factory=list)
    catalog_vectors_path: Path = Path("dataset/saved/teacher_item_128.npy")
    student_mlp_path: Path = Path("dataset/saved/student_mlp.pth")
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Load and cache application settings from the environment."""
    settings = Settings()
    if not settings.catalog_mean_vector:
        settings.catalog_mean_vector = _load_catalog_mean(settings.catalog_vectors_path)
    if len(settings.catalog_mean_vector) != 128:
        raise ValueError("catalog_mean_vector must contain exactly 128 floats.")
    return settings


def _load_catalog_mean(vectors_path: Path) -> list[float]:
    """Compute the catalog mean from the 128-dim teacher item embeddings."""
    if not vectors_path.exists():
        raise FileNotFoundError(f"Catalog vector file not found: {vectors_path}")

    vectors = np.load(vectors_path)
    if vectors.ndim != 2 or vectors.shape[1] != 128:
        raise ValueError(f"Expected catalog vectors with shape [N, 128], got {vectors.shape}.")

    return vectors.astype(np.float32).mean(axis=0).astype(float).tolist()
