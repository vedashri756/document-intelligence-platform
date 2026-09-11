"""
Logging setup. Logs go to both console and a rotating file so processing
stages, validation failures, OCR/model calls and exceptions can be traced
during evaluation without exposing anything sensitive to the API caller.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

from app.config import settings


def configure_logging() -> None:
    os.makedirs(os.path.dirname(settings.LOG_FILE) or ".", exist_ok=True)

    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    file_handler = RotatingFileHandler(
        settings.LOG_FILE, maxBytes=2_000_000, backupCount=3
    )
    file_handler.setFormatter(fmt)

    # Avoid duplicate handlers on reload
    root.handlers.clear()
    root.addHandler(console_handler)
    root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
