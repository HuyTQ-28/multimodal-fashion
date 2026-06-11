"""Sync FashionItem metadata and named vectors into Weaviate Cloud."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable
import uuid

import numpy as np
import pandas as pd
import weaviate
from dotenv import load_dotenv
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.init import Auth
from weaviate.client import WeaviateClient


COLLECTION_NAME = "FashionItem"
TEXT_FIELDS: tuple[str, ...] = (
    "prod_name",
    "detail_desc",
    "product_type_name",
    "colour_group_name",
    "graphical_appearance_name",
    "index_name",
)
PROPERTY_FIELDS: tuple[str, ...] = ("article_id", "image_url", *TEXT_FIELDS)


def normalize_article_id(value: Any) -> str:
    """Normalize H&M article IDs to zero-padded 10-digit strings."""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if not text.isdigit():
        raise ValueError(f"Invalid article_id value: {value!r}")
    return text.zfill(10)


def load_metadata(path: Path) -> dict[str, dict[str, str]]:
    """Load clean metadata and index it by article_id."""
    with path.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError(f"Expected list records in {path}.")

    metadata: dict[str, dict[str, str]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        article_id = normalize_article_id(record.get("article_id", ""))
        metadata[article_id] = {
            field: str(record.get(field, "") or "")
            for field in PROPERTY_FIELDS
        }
        metadata[article_id]["article_id"] = article_id

    if not metadata:
        raise ValueError(f"No valid metadata records found in {path}.")
    return metadata


def load_item_index_map(path: Path) -> pd.DataFrame:
    """Load item index mapping used to align metadata with .npy vector rows."""
    item_map = pd.read_csv(path, dtype={"article_id": str})
    required_columns = {"article_id", "item_idx"}
    missing_columns = required_columns.difference(item_map.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns in {path}: {sorted(missing_columns)}")

    item_map["article_id"] = item_map["article_id"].map(normalize_article_id)
    item_map["item_idx"] = item_map["item_idx"].astype(int)
    return item_map.sort_values("item_idx")


def validate_vectors(
    rec_vectors: np.ndarray,
    visual_vectors: np.ndarray,
    expected_rows: int,
) -> None:
    """Validate vector matrix shape before inserting into Weaviate."""
    if rec_vectors.shape != (expected_rows, 128):
        raise ValueError(
            f"Expected rec vectors shape {(expected_rows, 128)}, got {rec_vectors.shape}."
        )
    if visual_vectors.shape != (expected_rows, 512):
        raise ValueError(
            f"Expected visual vectors shape {(expected_rows, 512)}, got {visual_vectors.shape}."
        )


def connect_client() -> WeaviateClient:
    """Connect to Weaviate Cloud using WEAVIATE_URL and WEAVIATE_API_KEY."""
    load_dotenv()

    import os

    weaviate_url = os.getenv("WEAVIATE_URL")
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
    if not weaviate_url:
        raise RuntimeError("Missing WEAVIATE_URL in environment.")
    if not weaviate_api_key:
        raise RuntimeError("Missing WEAVIATE_API_KEY in environment.")

    return weaviate.connect_to_weaviate_cloud(
        cluster_url=weaviate_url,
        auth_credentials=Auth.api_key(weaviate_api_key),
    )


def ensure_collection(client: WeaviateClient, recreate: bool = False) -> None:
    """Create FashionItem with two self-provided named vectors."""
    if client.collections.exists(COLLECTION_NAME):
        if not recreate:
            return
        client.collections.delete(COLLECTION_NAME)

    client.collections.create(
        name=COLLECTION_NAME,
        properties=[
            Property(name="article_id", data_type=DataType.TEXT),
            Property(name="image_url", data_type=DataType.TEXT),
            *(Property(name=field, data_type=DataType.TEXT) for field in TEXT_FIELDS),
        ],
        vector_config=[
            Configure.Vectors.self_provided(name="rec_vector"),
            Configure.Vectors.self_provided(name="visual_vector"),
        ],
    )


def stable_uuid(article_id: str) -> str:
    """Generate deterministic UUIDs for idempotent FashionItem inserts."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"freedom-rt/fashion-item/{article_id}"))


def iter_objects(
    metadata: dict[str, dict[str, str]],
    item_map: pd.DataFrame,
    rec_vectors: np.ndarray,
    visual_vectors: np.ndarray,
) -> Iterable[tuple[str, dict[str, str], dict[str, list[float]]]]:
    """Yield Weaviate properties and named vectors in .npy row order."""
    for row in item_map.itertuples(index=False):
        article_id = normalize_article_id(row.article_id)
        item_idx = int(row.item_idx)
        properties = metadata.get(article_id)
        if properties is None:
            raise KeyError(f"Missing metadata for article_id={article_id}.")

        yield (
            article_id,
            properties,
            {
                "rec_vector": rec_vectors[item_idx].astype(np.float32).tolist(),
                "visual_vector": visual_vectors[item_idx].astype(np.float32).tolist(),
            },
        )


def sync_fashion_items(
    client: WeaviateClient,
    metadata_path: Path,
    item_map_path: Path,
    rec_vectors_path: Path,
    visual_vectors_path: Path,
    recreate: bool = False,
) -> int:
    """Batch insert FashionItem objects with rec_vector and visual_vector named vectors."""
    metadata = load_metadata(metadata_path)
    item_map = load_item_index_map(item_map_path)
    rec_vectors = np.load(rec_vectors_path)
    visual_vectors = np.load(visual_vectors_path)
    validate_vectors(
        rec_vectors=rec_vectors,
        visual_vectors=visual_vectors,
        expected_rows=len(item_map),
    )
    ensure_collection(client, recreate=recreate)

    inserted = 0
    with client.batch.dynamic() as batch:
        for article_id, properties, vectors in iter_objects(
            metadata=metadata,
            item_map=item_map,
            rec_vectors=rec_vectors,
            visual_vectors=visual_vectors,
        ):
            batch.add_object(
                collection=COLLECTION_NAME,
                properties=properties,
                uuid=stable_uuid(article_id),
                vector=vectors,
            )
            inserted += 1

    failed_objects = client.batch.failed_objects
    if failed_objects:
        first_error = failed_objects[0]
        raise RuntimeError(
            f"Weaviate batch import failed for {len(failed_objects)} objects. "
            f"First failure: {first_error}"
        )

    return inserted


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for Weaviate sync."""
    parser = argparse.ArgumentParser(description="Sync FashionItem data to Weaviate Cloud.")
    parser.add_argument("--metadata", type=Path, default=Path("dataset/clean_metadata.json"))
    parser.add_argument("--item-map", type=Path, default=Path("dataset/id_map_item.csv"))
    parser.add_argument("--rec-vectors", type=Path, default=Path("dataset/saved/teacher_item_128.npy"))
    parser.add_argument("--visual-vectors", type=Path, default=Path("dataset/image_feat.npy"))
    parser.add_argument("--recreate", action="store_true")
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint for Weaviate Cloud synchronization."""
    args = parse_args()
    client = connect_client()
    try:
        inserted = sync_fashion_items(
            client=client,
            metadata_path=args.metadata,
            item_map_path=args.item_map,
            rec_vectors_path=args.rec_vectors,
            visual_vectors_path=args.visual_vectors,
            recreate=args.recreate,
        )
        print(f"synced {inserted} FashionItem objects to Weaviate", flush=True)
    finally:
        client.close()


if __name__ == "__main__":
    main()
