"""Student MLP model definition."""

import torch
from torch import nn


class StudentMLP(nn.Module):
    """Funnel MLP mapping 1024-dim multimodal features to 128-dim graph targets."""

    def __init__(
        self,
        input_dim: int = 1024,
        hidden_dim_1: int = 512,
        hidden_dim_2: int = 256,
        output_dim: int = 128,
        dropout: float = 0.1,
    ) -> None:
        """
        Initialize the student network layers with a gradual funnel architecture
        """
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim_1),
            nn.LayerNorm(hidden_dim_1),
            nn.GELU(),
            nn.Dropout(dropout),
            
            nn.Linear(hidden_dim_1, hidden_dim_2),
            nn.LayerNorm(hidden_dim_2),
            nn.GELU(),
            nn.Dropout(dropout),
            
            nn.Linear(hidden_dim_2, output_dim),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        """Run a forward pass for product features."""
        return self.network(features)