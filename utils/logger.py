"""Simple application logger factory."""

import logging


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Create or fetch a configured logger."""
    raise NotImplementedError

