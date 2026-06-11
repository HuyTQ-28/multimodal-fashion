"""Dataset utilities for student distillation training."""

from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset


class FashionDistillationDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    """Dataset backed by concatenated image/text features and teacher targets."""

    def __init__(
        self,
        input_features: np.ndarray,
        target_vectors: np.ndarray,
    ) -> None:
        if input_features.ndim != 2 or input_features.shape[1] != 1024:
            raise ValueError(
                f"Expected input features with shape [N, 1024], got {input_features.shape}."
            )
        if target_vectors.ndim != 2 or target_vectors.shape[1] != 128:
            raise ValueError(
                f"Expected teacher targets with shape [N, 128], got {target_vectors.shape}."
            )
        if input_features.shape[0] != target_vectors.shape[0]:
            raise ValueError(
                "Input features and teacher targets must have the same number of rows: "
                f"{input_features.shape[0]} != {target_vectors.shape[0]}."
            )

        self.input_features = torch.from_numpy(
            np.ascontiguousarray(input_features, dtype=np.float32)
        )
        self.target_vectors = torch.from_numpy(
            np.ascontiguousarray(target_vectors, dtype=np.float32)
        )

    @classmethod
    def from_npy(
        cls,
        image_feat_path: str | Path,
        text_feat_path: str | Path,
        teacher_target_path: str | Path,
    ) -> "FashionDistillationDataset":
        """Load raw vectors from .npy files and concatenate image/text inputs."""
        image_features = np.load(Path(image_feat_path))
        text_features = np.load(Path(text_feat_path))
        teacher_targets = np.load(Path(teacher_target_path))

        if image_features.ndim != 2 or image_features.shape[1] != 512:
            raise ValueError(
                f"Expected image features with shape [N, 512], got {image_features.shape}."
            )
        if text_features.ndim != 2 or text_features.shape[1] != 512:
            raise ValueError(
                f"Expected text features with shape [N, 512], got {text_features.shape}."
            )
        if image_features.shape[0] != text_features.shape[0]:
            raise ValueError(
                "Image and text feature files must have the same number of rows: "
                f"{image_features.shape[0]} != {text_features.shape[0]}."
            )

        input_features = np.concatenate([image_features, text_features], axis=1)
        return cls(input_features=input_features, target_vectors=teacher_targets)

    def __len__(self) -> int:
        return self.input_features.shape[0]

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.input_features[index], self.target_vectors[index]


def create_dataloader(
    dataset: FashionDistillationDataset,
    batch_size: int,
    shuffle: bool = True,
    num_workers: int = 0,
    pin_memory: bool = False,
) -> DataLoader[tuple[torch.Tensor, torch.Tensor]]:
    """Create a PyTorch DataLoader for distillation data."""
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=False,
    )
