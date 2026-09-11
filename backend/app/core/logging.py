"""
Centralized logging configuration.

Code-quality rule (mandatory):
'Implement meaningful logging for request processing, validation failures,
OCR/model calls, exceptions and major processing stages. Logs should be
sufficient to diagnose failures during evaluation.'
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from app.core.config import get_settings

_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)


def configure_logging() -> None:
    """Call once at startup (see main.py)."""
    settings = get_settings()

    root = logging.getLogger()
    root.setLevel(settings.log_level)

    # Avoid duplicate handlers on reload
    if root.handlers:
        return

    formatter = logging.Formatter(_LOG_FORMAT)

    # Console handler — always on, useful for platform log viewers (Render/Railway)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # Rotating file handler — local diagnosis without unbounded growth
    try:
        os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)
        file_handler = RotatingFileHandler(
            settings.log_file, maxBytes=2_000_000, backupCount=3
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        # Read-only filesystem on some deploy platforms — console logging still works
        root.warning("Could not attach file log handler; continuing with console only.")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
