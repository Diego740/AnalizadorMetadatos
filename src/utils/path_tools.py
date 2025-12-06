"""Utilidades para trabajar con rutas del sistema de archivos."""
from __future__ import annotations

from pathlib import Path


def resolve_path(path: str | Path) -> Path:
    """Devuelve una instancia absoluta de :class:`Path` para *path*.

    La función no requiere que el archivo exista. Simplemente
    resuelve la ruta proporcionada por el usuario para que los ayudantes de nivel superior
    puedan trabajar con una ubicación canónica.
    """

    return Path(path).expanduser().resolve()


def file_exists(path: str | Path) -> bool:
    """Devuelve ``True`` si *path* es un archivo regular existente."""

    return resolve_path(path).is_file()


def ensure_readable_file(path: str | Path) -> Path:
    """Valida que *path* es un archivo legible y lo devuelve.

    Raises:
        FileNotFoundError: Si la ruta no existe o no es un archivo.
    """

    resolved = resolve_path(path)
    if not resolved.is_file():
        raise FileNotFoundError(f"El archivo '{resolved}' no existe o no es válido")
    return resolved
