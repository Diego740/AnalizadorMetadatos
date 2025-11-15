"""Helpers to detect and validate file extensions using libmagic."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import magic

from utils.mime_tools import EXTENSIONES_MIME, guess_extension_from_mime
from utils.path_tools import ensure_readable_file


def get_mime_type(path: str | Path) -> Optional[str]:
    """Return the MIME type reported by libmagic for *path*.

    Args:
        path: Local path to the file.

    Returns:
        The MIME type string or ``None`` if it cannot be determined.
    """

    try:
        archivo = ensure_readable_file(path)
        ms_mime = magic.Magic(mime=True)
        return ms_mime.from_file(str(archivo))
    except FileNotFoundError:
        raise
    except Exception:
        return None


def extension_matches_mime(path: str | Path) -> bool:
    """Return ``True`` if the extension matches the detected MIME."""

    archivo = ensure_readable_file(path)
    extension = archivo.suffix.lower()
    mime = get_mime_type(archivo)
    if mime is None:
        return False
    return EXTENSIONES_MIME.get(extension) == mime


def suggest_correct_extension(path: str | Path) -> Optional[str]:
    """Return the best extension suggestion for *path*.

    If the current extension already matches the MIME type the same
    extension is returned. Otherwise, the function tries to guess the
    correct one using the MIME table.
    """

    archivo = ensure_readable_file(path)
    mime = get_mime_type(archivo)
    if mime is None:
        return None

    detected = guess_extension_from_mime(mime)
    if detected:
        return detected
    return archivo.suffix.lower() or None


# Example usage:
# >>> suggest_correct_extension("foto.jpeg")
