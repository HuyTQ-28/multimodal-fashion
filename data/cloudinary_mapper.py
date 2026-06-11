"""Build clean FashionItem metadata by joining article text fields with image URLs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import re
import pandas as pd


TEXT_FIELDS: tuple[str, ...] = (
    "prod_name",
    "detail_desc",
    "product_type_name",
    "colour_group_name",
    "graphical_appearance_name",
    "index_name",
)

def clean_text_field(text: any) -> str:
    if text is None or (isinstance(text, float) and text != text):
        return ""
    
    text_str = str(text).lower().strip()
    text_str = re.sub(re.compile(r'\s+'), ' ', text_str)
    
    return text_str


def normalize_article_id(value: Any) -> str:
    """Normalize H&M article IDs to zero-padded 10-digit strings."""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if not text.isdigit():
        raise ValueError(f"Invalid article_id value: {value!r}")
    return text.zfill(10)


def load_cloudinary_urls(path: Path) -> dict[str, str]:
    """Load article_id -> image_url mapping from Cloudinary JSON output."""
    with path.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    if isinstance(raw_data, dict):
        return {
            normalize_article_id(article_id): str(image_url)
            for article_id, image_url in raw_data.items()
            if image_url
        }

    if isinstance(raw_data, list):
        mapping: dict[str, str] = {}
        for record in raw_data:
            if not isinstance(record, dict):
                continue
            article_id = record.get("article_id")
            image_url = record.get("image_url") or record.get("url")
            if article_id is not None and image_url:
                mapping[normalize_article_id(article_id)] = str(image_url)
        return mapping

    raise ValueError(f"Unsupported Cloudinary JSON format in {path}.")


def build_clean_metadata(
    articles_path: Path,
    cloudinary_urls_path: Path,
) -> list[dict[str, str]]:
    """Merge article metadata with Cloudinary image URLs and keep only required fields."""
    required_columns = ("article_id", *TEXT_FIELDS)
    articles = pd.read_csv(
        articles_path,
        dtype={"article_id": str},
        usecols=list(required_columns),
    )
    missing_columns = set(required_columns).difference(articles.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns in {articles_path}: {sorted(missing_columns)}")

    cloudinary_urls = load_cloudinary_urls(cloudinary_urls_path)
    articles["article_id"] = articles["article_id"].map(normalize_article_id)
    articles = articles.fillna("")

    for field in TEXT_FIELDS:
        articles[field] = articles[field].astype(str).apply(clean_text_field)
    articles["image_url"] = articles["article_id"].map(cloudinary_urls).fillna("")

    output_columns = ("article_id", "image_url", *TEXT_FIELDS)
    records = articles.loc[:, output_columns].to_dict(orient="records")
    return [{key: str(value) for key, value in record.items()} for record in records]


def save_clean_metadata(records: list[dict[str, str]], output_path: Path) -> None:
    """Persist merged metadata as UTF-8 JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for metadata processing."""
    parser = argparse.ArgumentParser(description="Build clean FashionItem metadata JSON.")
    parser.add_argument("--articles", type=Path, default=Path("dataset/articles.csv"))
    parser.add_argument("--cloudinary-urls", type=Path, default=Path("dataset/cloudinary_urls.json"))
    parser.add_argument("--output", type=Path, default=Path("dataset/clean_metadata.json"))
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint for metadata cleaning."""
    args = parse_args()
    records = build_clean_metadata(
        articles_path=args.articles,
        cloudinary_urls_path=args.cloudinary_urls,
    )
    save_clean_metadata(records, args.output)
    print(f"saved {len(records)} records to {args.output}", flush=True)


if __name__ == "__main__":
    main()
