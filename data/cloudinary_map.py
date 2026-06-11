"""Cloudinary URL mapping utilities for H&M articles."""

from pathlib import Path


class CloudinaryArticleMapper:
    """Map H&M article IDs to Cloudinary image URLs."""

    def __init__(self, cloud_name: str, api_key: str, api_secret: str) -> None:
        """Initialize Cloudinary credentials."""
        raise NotImplementedError

    def map_article_url(self, article_id: str) -> str | None:
        """Return the Cloudinary URL for one article ID."""
        raise NotImplementedError

    def build_mapping(self, articles_path: Path, output_path: Path) -> None:
        """Build and persist article-to-image URL mappings."""
        raise NotImplementedError


def main() -> None:
    """CLI entrypoint for Cloudinary mapping."""
    raise NotImplementedError


if __name__ == "__main__":
    main()

