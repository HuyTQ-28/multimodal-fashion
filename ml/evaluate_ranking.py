"""Evaluate StudentMLP item embeddings for top-k recommendation ranking."""

from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import DefaultDict

import numpy as np
import pandas as pd
import torch

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from ml.model import StudentMLP


FEATURE_DIM = 512
STUDENT_INPUT_DIM = 1024
REC_VECTOR_DIM = 128
EVAL_KS = (5, 10, 20)
MAX_K = max(EVAL_KS)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class InteractionSplits:
    """User-level train/validation history and test ground truth."""

    train_val_items: dict[int, np.ndarray]
    test_items: dict[int, np.ndarray]
    valid_users: np.ndarray
    interaction_count: int


@dataclass(frozen=True)
class RankingMetrics:
    """Aggregated ranking metrics for one cutoff."""

    recall: float
    ndcg: float


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Evaluate StudentMLP recommendation ranking on held-out test week."
    )
    parser.add_argument("--data-dir", type=Path, default=Path("dataset"))
    parser.add_argument("--interactions", type=Path, default=None)
    parser.add_argument("--image-feat", type=Path, default=None)
    parser.add_argument("--text-feat", type=Path, default=None)
    parser.add_argument("--teacher-user", type=Path, default=None)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--user-batch-size", type=int, default=512)
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=("auto", "cpu", "cuda"),
        help="Device for StudentMLP inference and ranking.",
    )
    return parser.parse_args()


def configure_logging() -> None:
    """Configure compact console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def resolve_device(device_arg: str) -> torch.device:
    """Resolve the requested torch device."""
    if device_arg == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device_arg == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested, but torch.cuda.is_available() is false.")
    return torch.device(device_arg)


def require_file(path: Path, description: str) -> None:
    """Raise a clear error when a required input file is missing."""
    if not path.exists():
        raise FileNotFoundError(f"{description} not found: {path}")


def validate_matrix_shape(
    array: np.ndarray,
    expected_dim: int,
    name: str,
    expected_rows: int | None = None,
) -> None:
    """Validate a two-dimensional embedding/feature matrix."""
    if array.ndim != 2 or array.shape[1] != expected_dim:
        raise ValueError(f"Expected {name} shape [N, {expected_dim}], got {array.shape}.")
    if expected_rows is not None and array.shape[0] != expected_rows:
        raise ValueError(
            f"Expected {name} to have {expected_rows} rows, got {array.shape[0]}."
        )


def load_student_model(checkpoint_path: Path, device: torch.device) -> StudentMLP:
    """Load StudentMLP from either a raw state dict or a training checkpoint dict."""
    require_file(checkpoint_path, "StudentMLP checkpoint")
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    state_dict = checkpoint.get("model_state_dict", checkpoint)
    hidden_dim_1 = int(checkpoint.get("hidden_dim_1", state_dict["network.0.weight"].shape[0]))
    hidden_dim_2 = int(checkpoint.get("hidden_dim_2", state_dict["network.4.weight"].shape[0]))
    dropout = float(checkpoint.get("dropout", 0.0))

    model = StudentMLP(hidden_dim_1=hidden_dim_1, hidden_dim_2=hidden_dim_2, dropout=dropout)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model


@torch.no_grad()
def infer_item_vectors(
    model: StudentMLP,
    image_feat_path: Path,
    text_feat_path: Path,
    batch_size: int,
    device: torch.device,
) -> torch.Tensor:
    """Infer 128-dim StudentMLP vectors for all catalog items."""
    require_file(image_feat_path, "Image feature file")
    require_file(text_feat_path, "Text feature file")
    if batch_size <= 0:
        raise ValueError(f"batch_size must be positive, got {batch_size}.")

    image_features = np.load(image_feat_path)
    text_features = np.load(text_feat_path)
    validate_matrix_shape(image_features, FEATURE_DIM, "image features")
    validate_matrix_shape(text_features, FEATURE_DIM, "text features", image_features.shape[0])

    input_features = np.concatenate([image_features, text_features], axis=1)
    validate_matrix_shape(input_features, STUDENT_INPUT_DIM, "student input features")

    vectors: list[torch.Tensor] = []
    for start in range(0, input_features.shape[0], batch_size):
        batch = np.ascontiguousarray(input_features[start : start + batch_size], dtype=np.float32)
        batch_tensor = torch.from_numpy(batch).to(device, non_blocking=True)
        vectors.append(model(batch_tensor).detach().cpu())

    item_vectors = torch.cat(vectors, dim=0).contiguous()
    if item_vectors.shape != (input_features.shape[0], REC_VECTOR_DIM):
        raise ValueError(
            "Expected inferred item vectors shape "
            f"[{input_features.shape[0]}, {REC_VECTOR_DIM}], got {tuple(item_vectors.shape)}."
        )
    return item_vectors


def _resolve_interaction_columns(columns: list[str]) -> tuple[str, str, str]:
    """Find user, item, and week/split columns in RecBole-style interaction files."""
    aliases = {
        "user": ("user_id", "userID:token", "user_id:token"),
        "item": ("item_id", "itemID:token", "item_id:token"),
        "week": ("week", "week:float", "x_label:float"),
    }
    resolved: list[str] = []
    for field, candidates in aliases.items():
        for candidate in candidates:
            if candidate in columns:
                resolved.append(candidate)
                break
        else:
            raise ValueError(
                f"Could not find {field} column. Expected one of {candidates}, got {columns}."
            )
    return resolved[0], resolved[1], resolved[2]


def load_interaction_splits(path: Path) -> InteractionSplits:
    """Load train/validation masks and test ground truth from hm.inter."""
    require_file(path, "Interaction file")
    frame = pd.read_csv(path, sep="\t")
    user_col, item_col, week_col = _resolve_interaction_columns(frame.columns.tolist())

    users = frame[user_col].astype(np.int64).to_numpy()
    items = frame[item_col].astype(np.int64).to_numpy()
    weeks = frame[week_col].astype(np.int64).to_numpy()

    train_val: DefaultDict[int, set[int]] = defaultdict(set)
    test: DefaultDict[int, set[int]] = defaultdict(set)

    train_val_mask = np.isin(weeks, (0, 1))
    test_mask = weeks == 2

    for user_id, item_id in zip(users[train_val_mask], items[train_val_mask]):
        train_val[int(user_id)].add(int(item_id))
    for user_id, item_id in zip(users[test_mask], items[test_mask]):
        test[int(user_id)].add(int(item_id))

    test_items = {
        user_id: np.fromiter(sorted(item_ids), dtype=np.int64)
        for user_id, item_ids in test.items()
        if item_ids
    }
    train_val_items = {
        user_id: np.fromiter(sorted(item_ids), dtype=np.int64)
        for user_id, item_ids in train_val.items()
        if item_ids
    }
    valid_users = np.fromiter(sorted(test_items), dtype=np.int64)
    if valid_users.size == 0:
        raise ValueError("No valid test users found for week == 2.")

    return InteractionSplits(
        train_val_items=train_val_items,
        test_items=test_items,
        valid_users=valid_users,
        interaction_count=len(frame),
    )


def validate_id_ranges(
    splits: InteractionSplits,
    user_count: int,
    item_count: int,
) -> None:
    """Validate user and item IDs fit available embedding rows."""
    max_user_id = int(splits.valid_users.max())
    if max_user_id >= user_count:
        raise ValueError(
            f"Interaction user id {max_user_id} exceeds teacher_user rows {user_count}."
        )

    all_items: list[np.ndarray] = []
    all_items.extend(splits.test_items.values())
    all_items.extend(splits.train_val_items.values())
    if all_items:
        max_item_id = int(max(int(items.max()) for items in all_items if items.size))
        if max_item_id >= item_count:
            raise ValueError(f"Interaction item id {max_item_id} exceeds item rows {item_count}.")


def load_teacher_user_vectors(path: Path) -> np.ndarray:
    """Load teacher user vectors required for ranking."""
    require_file(path, "Teacher user embedding file")
    user_vectors = np.load(path)
    validate_matrix_shape(user_vectors, REC_VECTOR_DIM, "teacher user vectors")
    return np.ascontiguousarray(user_vectors, dtype=np.float32)


def _dcg(hit_positions: np.ndarray) -> float:
    """Compute DCG from zero-based hit positions."""
    if hit_positions.size == 0:
        return 0.0
    return float(np.sum(1.0 / np.log2(hit_positions.astype(np.float64) + 2.0)))


def evaluate_ranking(
    user_vectors: np.ndarray,
    item_vectors: torch.Tensor,
    splits: InteractionSplits,
    user_batch_size: int,
    device: torch.device,
) -> dict[int, RankingMetrics]:
    """Evaluate Recall@K and NDCG@K over valid test users."""
    if user_batch_size <= 0:
        raise ValueError(f"user_batch_size must be positive, got {user_batch_size}.")

    item_vectors = item_vectors.to(device)
    metric_totals = {k: {"recall": 0.0, "ndcg": 0.0} for k in EVAL_KS}
    discounts = {k: 1.0 / np.log2(np.arange(2, k + 2, dtype=np.float64)) for k in EVAL_KS}

    valid_users = splits.valid_users
    for start in range(0, valid_users.size, user_batch_size):
        batch_users = valid_users[start : start + user_batch_size]
        batch_vectors = torch.from_numpy(user_vectors[batch_users]).to(device, non_blocking=True)
        scores = batch_vectors @ item_vectors.T

        for row_index, user_id in enumerate(batch_users):
            seen_items = splits.train_val_items.get(int(user_id))
            if seen_items is not None and seen_items.size > 0:
                scores[row_index, torch.from_numpy(seen_items).to(device)] = -torch.inf

        top_items = torch.topk(scores, k=MAX_K, dim=1).indices.cpu().numpy()

        for row_index, user_id in enumerate(batch_users):
            ground_truth = splits.test_items[int(user_id)]
            gt_count = ground_truth.size
            recommendations = top_items[row_index]
            relevant = np.isin(recommendations, ground_truth, assume_unique=False)

            for k in EVAL_KS:
                hits = relevant[:k]
                hit_count = int(hits.sum())
                metric_totals[k]["recall"] += hit_count / gt_count

                hit_positions = np.flatnonzero(hits)
                ideal_count = min(gt_count, k)
                ideal_dcg = float(np.sum(discounts[k][:ideal_count]))
                metric_totals[k]["ndcg"] += _dcg(hit_positions) / ideal_dcg

    user_count = float(valid_users.size)
    return {
        k: RankingMetrics(
            recall=metric_totals[k]["recall"] / user_count,
            ndcg=metric_totals[k]["ndcg"] / user_count,
        )
        for k in EVAL_KS
    }


def log_metrics(metrics: dict[int, RankingMetrics]) -> None:
    """Log the final metric table and headline K=20 values."""
    LOGGER.info("Final ranking metrics")
    LOGGER.info("%-4s %-12s %-12s", "K", "Recall@K", "NDCG@K")
    for k in EVAL_KS:
        LOGGER.info("%-4d %-12.6f %-12.6f", k, metrics[k].recall, metrics[k].ndcg)

    LOGGER.info(
        "Headline: Recall@20=%.6f NDCG@20=%.6f",
        metrics[20].recall,
        metrics[20].ndcg,
    )


def main() -> None:
    """Run StudentMLP ranking evaluation."""
    configure_logging()
    args = parse_args()

    data_dir = args.data_dir
    interactions_path = args.interactions or data_dir / "hm.inter"
    image_feat_path = args.image_feat or data_dir / "image_feat.npy"
    text_feat_path = args.text_feat or data_dir / "text_feat.npy"
    teacher_user_path = args.teacher_user or data_dir / "saved" / "teacher_user_128.npy"
    checkpoint_path = args.checkpoint or data_dir / "saved" / "student_mlp.pth"

    device = resolve_device(args.device)
    LOGGER.info("Using device: %s", device)

    require_file(teacher_user_path, "Teacher user embedding file")
    require_file(interactions_path, "Interaction file")
    require_file(checkpoint_path, "StudentMLP checkpoint")
    require_file(image_feat_path, "Image feature file")
    require_file(text_feat_path, "Text feature file")

    splits = load_interaction_splits(interactions_path)
    LOGGER.info("Loaded %d interactions", splits.interaction_count)
    LOGGER.info("Valid test users: %d", splits.valid_users.size)

    user_vectors = load_teacher_user_vectors(teacher_user_path)
    model = load_student_model(checkpoint_path, device)
    item_vectors = infer_item_vectors(
        model=model,
        image_feat_path=image_feat_path,
        text_feat_path=text_feat_path,
        batch_size=args.batch_size,
        device=device,
    )
    LOGGER.info("Items: %d", item_vectors.shape[0])

    validate_id_ranges(
        splits=splits,
        user_count=user_vectors.shape[0],
        item_count=item_vectors.shape[0],
    )

    metrics = evaluate_ranking(
        user_vectors=user_vectors,
        item_vectors=item_vectors,
        splits=splits,
        user_batch_size=args.user_batch_size,
        device=device,
    )
    log_metrics(metrics)


if __name__ == "__main__":
    main()
