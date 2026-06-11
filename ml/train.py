"""K-Fold distillation training for the FREEDOM-RT Student MLP."""

import argparse
from dataclasses import dataclass
from itertools import product
from pathlib import Path
import sys
from typing import Iterable

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.model_selection import KFold
from torch import nn
from torch.optim import Optimizer
from torch.utils.data import DataLoader, Subset

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from ml.dataset import FashionDistillationDataset, create_dataloader
from ml.model import StudentMLP


@dataclass(frozen=True)
class TrainConfig:
    """Hyperparameters evaluated during K-Fold search."""

    learning_rate: float
    weight_decay: float
    hidden_dim_1: int
    hidden_dim_2: int
    dropout: float


@dataclass
class EpochMetrics:
    """Loss and cosine similarity metrics for one epoch."""

    loss: float
    cosine_similarity: float


@dataclass
class CrossValidationResult:
    """Averaged K-Fold curves and selected training configuration."""

    config: TrainConfig
    best_epoch: int
    best_val_loss: float
    train_loss: list[float]
    val_loss: list[float]
    train_cosine: list[float]
    val_cosine: list[float]


class EmbeddingDistillationLoss(nn.Module):
    """Hybrid loss for continuous embedding distillation."""

    def __init__(self, mse_weight: float = 1.0, cosine_weight: float = 0.25) -> None:
        super().__init__()
        self.mse_weight = mse_weight
        self.cosine_weight = cosine_weight
        self.mse = nn.MSELoss()

    def forward(self, predictions: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        mse_loss = self.mse(predictions, targets)
        cosine_loss = 1.0 - F.cosine_similarity(predictions, targets, dim=1).mean()
        return (self.mse_weight * mse_loss) + (self.cosine_weight * cosine_loss)


def create_loss() -> nn.Module:
    """MSE preserves teacher coordinates; cosine preserves retrieval direction."""
    return EmbeddingDistillationLoss()


def create_model(config: TrainConfig) -> StudentMLP:
    """Build a fresh StudentMLP for one fold or final training run."""
    return StudentMLP(
        hidden_dim_1=config.hidden_dim_1,
        hidden_dim_2=config.hidden_dim_2,
        dropout=config.dropout,
    )


def create_optimizer(
    model: StudentMLP,
    learning_rate: float,
    weight_decay: float,
) -> Optimizer:
    """Create the AdamW optimizer used for all distillation runs."""
    return torch.optim.AdamW(
        model.parameters(),
        lr=learning_rate,
        weight_decay=weight_decay,
    )


def _to_float_list(value: str) -> list[float]:
    """Parse comma-separated float hyperparameter values."""
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def _to_int_list(value: str) -> list[int]:
    """Parse comma-separated integer hyperparameter values."""
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def build_config_grid(args: argparse.Namespace) -> list[TrainConfig]:
    """Create the hyperparameter grid evaluated by K-Fold CV."""
    configs = [
        TrainConfig(
            learning_rate=learning_rate,
            weight_decay=weight_decay,
            hidden_dim_1=hidden_dim_1,
            hidden_dim_2=hidden_dim_2,
            dropout=dropout,
        )
        for learning_rate, weight_decay, hidden_dim_1, hidden_dim_2, dropout in product(
            _to_float_list(args.learning_rates),
            _to_float_list(args.weight_decays),
            _to_int_list(args.hidden_dim_1_values),
            _to_int_list(args.hidden_dim_2_values),
            _to_float_list(args.dropouts),
        )
    ]
    if not configs:
        raise ValueError("Hyperparameter grid is empty.")
    return configs


def train_one_epoch(
    model: StudentMLP,
    dataloader: DataLoader[tuple[torch.Tensor, torch.Tensor]],
    loss_fn: nn.Module,
    optimizer: Optimizer,
    device: torch.device,
) -> EpochMetrics:
    """Train for one epoch and return average loss and cosine similarity."""
    model.train()
    total_loss = 0.0
    total_cosine = 0.0
    total_samples = 0

    for features, targets in dataloader:
        features = features.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)
        predictions = model(features)
        loss = loss_fn(predictions, targets)
        loss.backward()
        optimizer.step()

        batch_size = features.size(0)
        batch_cosine = F.cosine_similarity(predictions.detach(), targets, dim=1).mean()
        total_loss += loss.item() * batch_size
        total_cosine += batch_cosine.item() * batch_size
        total_samples += batch_size

    if total_samples == 0:
        raise RuntimeError("Cannot train on an empty dataloader.")

    return EpochMetrics(
        loss=total_loss / total_samples,
        cosine_similarity=total_cosine / total_samples,
    )


@torch.no_grad()
def evaluate(
    model: StudentMLP,
    dataloader: DataLoader[tuple[torch.Tensor, torch.Tensor]],
    loss_fn: nn.Module,
    device: torch.device,
) -> EpochMetrics:
    """Evaluate loss and cosine similarity without gradient updates."""
    model.eval()
    total_loss = 0.0
    total_cosine = 0.0
    total_samples = 0

    for features, targets in dataloader:
        features = features.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)
        predictions = model(features)
        loss = loss_fn(predictions, targets)

        batch_size = features.size(0)
        batch_cosine = F.cosine_similarity(predictions, targets, dim=1).mean()
        total_loss += loss.item() * batch_size
        total_cosine += batch_cosine.item() * batch_size
        total_samples += batch_size

    if total_samples == 0:
        raise RuntimeError("Cannot evaluate on an empty dataloader.")

    return EpochMetrics(
        loss=total_loss / total_samples,
        cosine_similarity=total_cosine / total_samples,
    )


def make_subset_loader(
    dataset: FashionDistillationDataset,
    indices: Iterable[int],
    batch_size: int,
    shuffle: bool,
    num_workers: int,
    pin_memory: bool,
) -> DataLoader[tuple[torch.Tensor, torch.Tensor]]:
    """Create a DataLoader over a K-Fold subset."""
    return create_dataloader(
        dataset=Subset(dataset, list(indices)),
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )


def run_cross_validation(
    dataset: FashionDistillationDataset,
    configs: list[TrainConfig],
    args: argparse.Namespace,
    device: torch.device,
) -> CrossValidationResult:
    """Run K-Fold CV for every config and return the best averaged result."""
    kfold = KFold(n_splits=args.folds, shuffle=True, random_state=args.seed)
    loss_fn = create_loss()
    best_result: CrossValidationResult | None = None

    for config_id, config in enumerate(configs, start=1):
        fold_train_loss: list[list[float]] = []
        fold_val_loss: list[list[float]] = []
        fold_train_cosine: list[list[float]] = []
        fold_val_cosine: list[list[float]] = []

        for fold_id, (train_indices, val_indices) in enumerate(kfold.split(dataset), start=1):
            torch.manual_seed(args.seed + fold_id)
            model = create_model(config).to(device)
            optimizer = create_optimizer(model, config.learning_rate, config.weight_decay)
            train_loader = make_subset_loader(
                dataset=dataset,
                indices=train_indices,
                batch_size=args.batch_size,
                shuffle=True,
                num_workers=args.num_workers,
                pin_memory=device.type == "cuda",
            )
            val_loader = make_subset_loader(
                dataset=dataset,
                indices=val_indices,
                batch_size=args.batch_size,
                shuffle=False,
                num_workers=args.num_workers,
                pin_memory=device.type == "cuda",
            )

            train_losses: list[float] = []
            val_losses: list[float] = []
            train_cosines: list[float] = []
            val_cosines: list[float] = []

            for epoch in range(1, args.epochs + 1):
                train_metrics = train_one_epoch(
                    model=model,
                    dataloader=train_loader,
                    loss_fn=loss_fn,
                    optimizer=optimizer,
                    device=device,
                )
                val_metrics = evaluate(
                    model=model,
                    dataloader=val_loader,
                    loss_fn=loss_fn,
                    device=device,
                )

                train_losses.append(train_metrics.loss)
                val_losses.append(val_metrics.loss)
                train_cosines.append(train_metrics.cosine_similarity)
                val_cosines.append(val_metrics.cosine_similarity)

                print(
                    "cv "
                    f"config={config_id}/{len(configs)} "
                    f"fold={fold_id}/{args.folds} "
                    f"epoch={epoch:03d} "
                    f"train_loss={train_metrics.loss:.6f} "
                    f"val_loss={val_metrics.loss:.6f} "
                    f"train_cos={train_metrics.cosine_similarity:.6f} "
                    f"val_cos={val_metrics.cosine_similarity:.6f}",
                    flush=True,
                )

            fold_train_loss.append(train_losses)
            fold_val_loss.append(val_losses)
            fold_train_cosine.append(train_cosines)
            fold_val_cosine.append(val_cosines)

        avg_train_loss = np.mean(np.asarray(fold_train_loss), axis=0).tolist()
        avg_val_loss = np.mean(np.asarray(fold_val_loss), axis=0).tolist()
        avg_train_cosine = np.mean(np.asarray(fold_train_cosine), axis=0).tolist()
        avg_val_cosine = np.mean(np.asarray(fold_val_cosine), axis=0).tolist()

        best_epoch_index = int(np.argmin(avg_val_loss))
        result = CrossValidationResult(
            config=config,
            best_epoch=best_epoch_index + 1,
            best_val_loss=float(avg_val_loss[best_epoch_index]),
            train_loss=[float(value) for value in avg_train_loss],
            val_loss=[float(value) for value in avg_val_loss],
            train_cosine=[float(value) for value in avg_train_cosine],
            val_cosine=[float(value) for value in avg_val_cosine],
        )

        if best_result is None or result.best_val_loss < best_result.best_val_loss:
            best_result = result

    if best_result is None:
        raise RuntimeError("K-Fold cross-validation did not produce a result.")
    return best_result


def plot_training_curves(result: CrossValidationResult, output_path: Path) -> None:
    """Export averaged K-Fold train/val loss and cosine similarity curves."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epochs = range(1, len(result.train_loss) + 1)

    figure, axes = plt.subplots(1, 2, figsize=(12, 4), dpi=160)
    axes[0].plot(epochs, result.train_loss, label="Train Loss", linewidth=2)
    axes[0].plot(epochs, result.val_loss, label="Val Loss", linewidth=2)
    axes[0].axvline(result.best_epoch, color="tab:gray", linestyle="--", linewidth=1)
    axes[0].set_title("Hybrid Distillation Loss")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].grid(alpha=0.25)
    axes[0].legend()

    axes[1].plot(epochs, result.train_cosine, label="Train Cosine", linewidth=2)
    axes[1].plot(epochs, result.val_cosine, label="Val Cosine", linewidth=2)
    axes[1].axvline(result.best_epoch, color="tab:gray", linestyle="--", linewidth=1)
    axes[1].set_title("Cosine Similarity")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Similarity")
    axes[1].grid(alpha=0.25)
    axes[1].legend()

    figure.tight_layout()
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)


def train_final_model(
    dataset: FashionDistillationDataset,
    result: CrossValidationResult,
    args: argparse.Namespace,
    device: torch.device,
) -> None:
    """Train a fresh model on 100% of the dataset using the best CV setup."""
    torch.manual_seed(args.seed)
    model = create_model(result.config).to(device)
    loss_fn = create_loss()
    optimizer = create_optimizer(
        model=model,
        learning_rate=result.config.learning_rate,
        weight_decay=result.config.weight_decay,
    )
    train_loader = create_dataloader(
        dataset=dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=device.type == "cuda",
    )

    for epoch in range(1, result.best_epoch + 1):
        metrics = train_one_epoch(
            model=model,
            dataloader=train_loader,
            loss_fn=loss_fn,
            optimizer=optimizer,
            device=device,
        )
        print(
            f"final epoch={epoch:03d}/{result.best_epoch:03d} "
            f"loss={metrics.loss:.6f} cosine={metrics.cosine_similarity:.6f}",
            flush=True,
        )

    args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "input_dim": 1024,
            "hidden_dim_1": result.config.hidden_dim_1,
            "hidden_dim_2": result.config.hidden_dim_2,
            "output_dim": 128,
            "dropout": result.config.dropout,
            "best_epoch": result.best_epoch,
            "learning_rate": result.config.learning_rate,
            "weight_decay": result.config.weight_decay,
            "cv_best_val_loss": result.best_val_loss,
        },
        args.checkpoint,
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for K-Fold tuning and final training."""
    parser = argparse.ArgumentParser(description="Train FREEDOM-RT Student MLP with K-Fold CV.")
    parser.add_argument("--data-dir", type=Path, default=Path("dataset"))
    parser.add_argument("--image-feat", type=Path, default=None)
    parser.add_argument("--text-feat", type=Path, default=None)
    parser.add_argument("--teacher-target", type=Path, default=None)
    parser.add_argument("--checkpoint", type=Path, default=Path("dataset/saved/student_mlp.pth"))
    parser.add_argument("--plot-path", type=Path, default=Path("dataset/saved/training_curves.png"))
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=1024)
    parser.add_argument("--learning-rates", type=str, default="0.001")
    parser.add_argument("--weight-decays", type=str, default="0.0001")
    parser.add_argument("--hidden-dim-1-values", type=str, default="512")
    parser.add_argument("--hidden-dim-2-values", type=str, default="256")
    parser.add_argument("--dropouts", type=str, default="0.1")
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--weight-decay", type=float, default=None)
    parser.add_argument("--hidden-dim-1", type=int, default=None)
    parser.add_argument("--hidden-dim-2", type=int, default=None)
    parser.add_argument("--dropout", type=float, default=None)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # Backward-compatible single-value aliases for existing local/Modal commands.
    if args.learning_rate is not None:
        args.learning_rates = str(args.learning_rate)
    if args.weight_decay is not None:
        args.weight_decays = str(args.weight_decay)
    if args.hidden_dim_1 is not None:
        args.hidden_dim_1_values = str(args.hidden_dim_1)
    if args.hidden_dim_2 is not None:
        args.hidden_dim_2_values = str(args.hidden_dim_2)
    if args.dropout is not None:
        args.dropouts = str(args.dropout)
    return args


def main() -> None:
    """Run K-Fold hyperparameter tuning, plot curves, then train the final model."""
    args = parse_args()
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    image_feat_path = args.image_feat or args.data_dir / "image_feat.npy"
    text_feat_path = args.text_feat or args.data_dir / "text_feat.npy"
    teacher_target_path = args.teacher_target or args.data_dir / "saved" / "teacher_item_128.npy"

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dataset = FashionDistillationDataset.from_npy(
        image_feat_path=image_feat_path,
        text_feat_path=text_feat_path,
        teacher_target_path=teacher_target_path,
    )
    if len(dataset) != 17_647:
        print(f"warning expected 17647 samples, found {len(dataset)}", flush=True)

    best_result = run_cross_validation(
        dataset=dataset,
        configs=build_config_grid(args),
        args=args,
        device=device,
    )
    plot_training_curves(best_result, args.plot_path)
    train_final_model(dataset=dataset, result=best_result, args=args, device=device)

    print(
        "best "
        f"epoch={best_result.best_epoch} "
        f"val_loss={best_result.best_val_loss:.6f} "
        f"lr={best_result.config.learning_rate} "
        f"weight_decay={best_result.config.weight_decay} "
        f"hidden_dim_1={best_result.config.hidden_dim_1} "
        f"hidden_dim_2={best_result.config.hidden_dim_2} "
        f"dropout={best_result.config.dropout}",
        flush=True,
    )


if __name__ == "__main__":
    main()

# modal run modal_train.py \
#   --epochs 30 \
#   --batch-size 1024 \
#   --learning-rate 0.001 \
#   --local-data-dir dataset