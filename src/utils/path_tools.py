"""Utilities to work with filesystem paths."""
from __future__ import annotations

from pathlib import Path


def resolve_path(path: str | Path) -> Path:
    """Return an absolute :class:`Path` instance for *path*.

    The function does not require that the file exists. It simply
    resolves the user provided path so that higher level helpers can
    work with a canonical location.
    """

    return Path(path).expanduser().resolve()


def file_exists(path: str | Path) -> bool:
    """Return ``True`` if *path* is an existing regular file."""

    return resolve_path(path).is_file()


def ensure_readable_file(path: str | Path) -> Path:
    """Validate that *path* is a readable file and return it.

    Raises:
        FileNotFoundError: If the path does not exist or is not a file.
    """

    resolved = resolve_path(path)
    if not resolved.is_file():
        raise FileNotFoundError(f"El archivo '{resolved}' no existe o no es válido")
    return resolved
