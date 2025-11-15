"""Centralized logging configuration."""
from __future__ import annotations

import logging
from logging import Logger


def get_logger(name: str = "analizador") -> Logger:
    """Return a module level logger with a basic configuration."""

    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
