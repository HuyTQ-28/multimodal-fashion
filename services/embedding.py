"""Local feature extraction and StudentMLP inference for runtime embeddings."""

from __future__ import annotations

import hashlib
from pathlib import Path

import torch

from ml.model import StudentMLP


FEATURE_DIM = 512
STUDENT_INPUT_DIM = 1024
REC_VECTOR_DIM = 128


class ProductEmbeddingService:
    """Create 128-dim recommendation vectors and 512-dim visual vectors."""

    def __init__(self, student_mlp_path: str | Path, device: str | None = None) -> None:
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model = self._load_student_model(Path(student_mlp_path)).to(self.device)
        self.model.eval()

    def encode_text_query(self, query: str) -> list[float]:
        """Encode a text-only query into the StudentMLP 128-dim recommendation space."""
        text_feature = self._hash_feature(query, namespace="text")
        image_feature = [0.0] * FEATURE_DIM
        return self._run_student(text_feature + image_feature)

    def encode_product(self, text: str, image_url: str) -> tuple[list[float], list[float]]:
        """Encode product text/image URL into rec_vector and visual_vector."""
        text_feature = self._hash_feature(text, namespace="text")
        visual_vector = self._hash_feature(image_url, namespace="image")
        rec_vector = self._run_student(text_feature + visual_vector)
        return rec_vector, visual_vector

    def _run_student(self, features: list[float]) -> list[float]:
        if len(features) != STUDENT_INPUT_DIM:
            raise ValueError(f"Expected {STUDENT_INPUT_DIM}-dim StudentMLP input.")
        tensor = torch.tensor(features, dtype=torch.float32, device=self.device).unsqueeze(0)
        with torch.no_grad():
            output = self.model(tensor).squeeze(0).detach().cpu().tolist()
        if len(output) != REC_VECTOR_DIM:
            raise ValueError(f"Expected {REC_VECTOR_DIM}-dim StudentMLP output.")
        return [float(value) for value in output]

    @staticmethod
    def _hash_feature(value: str, namespace: str) -> list[float]:
        """Deterministic 512-dim local feature fallback for runtime inputs."""
        feature = [0.0] * FEATURE_DIM
        tokens = value.lower().split() or [value.lower()]
        for token in tokens:
            digest = hashlib.blake2b(f"{namespace}:{token}".encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:4], "little") % FEATURE_DIM
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            feature[index] += sign

        norm = sum(value * value for value in feature) ** 0.5
        if norm == 0.0:
            return feature
        return [value / norm for value in feature]

    @staticmethod
    def _load_student_model(checkpoint_path: Path) -> StudentMLP:
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"StudentMLP checkpoint not found: {checkpoint_path}")

        checkpoint = torch.load(checkpoint_path, map_location="cpu")
        state_dict = checkpoint.get("model_state_dict", checkpoint)
        hidden_dim_1 = int(checkpoint.get("hidden_dim_1", state_dict["network.0.weight"].shape[0]))
        hidden_dim_2 = int(checkpoint.get("hidden_dim_2", state_dict["network.4.weight"].shape[0]))
        dropout = float(checkpoint.get("dropout", 0.0))

        model = StudentMLP(hidden_dim_1=hidden_dim_1, hidden_dim_2=hidden_dim_2, dropout=dropout)
        model.load_state_dict(state_dict)
        return model
