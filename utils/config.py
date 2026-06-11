"""Application configuration loading."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    app_name: str = "FREEDOM-RT"
    app_env: str = "development"
    log_level: str = "INFO"
    redis_url: str
    weaviate_url: str
    weaviate_api_key: str
    weaviate_collection: str = "FashionProduct"
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


def get_settings() -> Settings:
    """Load application settings from the environment."""
    raise NotImplementedError

