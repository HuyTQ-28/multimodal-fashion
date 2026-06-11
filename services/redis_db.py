"""Redis-backed storage for active session preference vectors."""

from __future__ import annotations

import json
from typing import Literal

import redis


InteractionType = Literal["click", "like", "add_to_cart"]

INTERACTION_WEIGHTS: dict[InteractionType, float] = {
    "click": 0.1,
    "like": 0.3,
    "add_to_cart": 0.5,
}

VECTOR_DIM = 128


class RedisSessionStore:
    """Store one active 128-dim EMA vector per anonymous session."""

    def __init__(
        self,
        redis_url: str,
        catalog_mean_vector: list[float],
        ttl_seconds: int = 604800,
    ) -> None:
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)
        self.catalog_mean_vector = self._validate_vector(catalog_mean_vector)
        self.ttl_seconds = ttl_seconds

    def get_ema_vector(self, session_id: str) -> list[float] | None:
        """Fetch the current EMA vector and refresh its TTL."""
        key = self._key(session_id)
        raw_vector = self.client.get(key)
        if raw_vector is None:
            return None
        self.client.expire(key, self.ttl_seconds)
        return self._validate_vector(json.loads(raw_vector))

    def get_or_init_ema_vector(self, session_id: str) -> list[float]:
        """Return an existing vector or initialize from the catalog mean vector."""
        vector = self.get_ema_vector(session_id)
        if vector is not None:
            return vector
        self.set_ema_vector(session_id, self.catalog_mean_vector)
        return list(self.catalog_mean_vector)

    def set_ema_vector(self, session_id: str, vector: list[float]) -> None:
        """Persist a validated vector as JSON with session TTL."""
        clean_vector = self._validate_vector(vector)
        self.client.setex(
            self._key(session_id),
            self.ttl_seconds,
            json.dumps(clean_vector, separators=(",", ":")),
        )

    def update_ema_vector(
        self,
        session_id: str,
        item_vector: list[float],
        action_type: InteractionType,
    ) -> list[float]:
        """Apply intent-aware EMA and store the updated session vector."""
        if action_type not in INTERACTION_WEIGHTS:
            raise ValueError(f"Unsupported action_type: {action_type}")

        old_vector = self.get_or_init_ema_vector(session_id)
        clean_item_vector = self._validate_vector(item_vector)
        alpha = INTERACTION_WEIGHTS[action_type]
        new_vector = [
            (alpha * item_value) + ((1.0 - alpha) * old_value)
            for old_value, item_value in zip(old_vector, clean_item_vector, strict=True)
        ]
        self.set_ema_vector(session_id, new_vector)
        return new_vector

    def clear_session(self, session_id: str) -> None:
        """Remove a session preference vector."""
        self.client.delete(self._key(session_id))

    @staticmethod
    def _key(session_id: str) -> str:
        if not session_id:
            raise ValueError("session_id cannot be empty.")
        return f"session:{session_id}:ema"

    @staticmethod
    def _validate_vector(vector: list[float]) -> list[float]:
        if len(vector) != VECTOR_DIM:
            raise ValueError(f"Expected {VECTOR_DIM}-dim vector, got {len(vector)}.")
        return [float(value) for value in vector]
