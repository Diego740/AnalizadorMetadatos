"""
Configuración centralizada de registros (logging).
"""
from __future__ import annotations

import logging
from logging import Logger


def get_logger(name: str = "metadata_analyzer") -> Logger:
    """
    Configura un logger simple con un formato estándar.
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
    return logger
