"""
Structured logging for Jarvis.

Provides a single `get_logger(name)` factory used throughout the codebase
so every module logs with consistent formatting, including request IDs
where available. In production this can be swapped for JSON-formatted
output (e.g. for ingestion into ELK/Datadog) by changing `_FORMATTER` only.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import settings

_LOG_DIR = Path("logs")
_LOG_DIR.mkdir(exist_ok=True)

_FORMATTER = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _build_root_logger() -> None:
    root = logging.getLogger("jarvis")
    root.setLevel(settings.log_level.upper())

    if root.handlers:
        # Avoid duplicate handlers on reload
        return

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(_FORMATTER)
    root.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        _LOG_DIR / "jarvis.log", maxBytes=5_000_000, backupCount=5
    )
    file_handler.setFormatter(_FORMATTER)
    root.addHandler(file_handler)


_build_root_logger()


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger, e.g. get_logger(__name__)."""
    return logging.getLogger(f"jarvis.{name}")
