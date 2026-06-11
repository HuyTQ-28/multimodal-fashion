"""Redis session and intent-vector storage stubs."""

from typing import Literal


InteractionType = Literal["click", "like", "cart"]

INTERACTION_WEIGHTS: dict[InteractionType, float] = {
    "click": 0.1,
    "like": 0.3,
    "cart": 0.5,
}


class RedisSessionStore:
    """Redis-backed store for session EMA vectors."""

    def __init__(self, redis_url: str) -> None:
        """Initialize Redis session storage."""
        raise NotImplementedError

    def init_session(self, session_id: str) -> None:
        """Initialize a session vector if it does not exist."""
        raise NotImplementedError

    def get_ema_vector(self, session_id: str) -> list[float] | None:
        """Fetch the current EMA vector for a session."""
        raise NotImplementedError

    def update_ema_vector(
        self,
        session_id: str,
        product_vector: list[float],
        interaction_type: InteractionType,
    ) -> list[float]:
        """Update an intent-aware EMA vector for click, like, or cart."""
        raise NotImplementedError

    def clear_session(self, session_id: str) -> None:
        """Remove a session and its stored vector."""
        raise NotImplementedError

