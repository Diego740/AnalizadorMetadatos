"""File loader abstraction that centralizes type detection."""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from core.detect_extension import get_mime_type
from utils.path_tools import ensure_readable_file

FileType = Literal["image", "pdf", "docx", "unknown"]


def _infer_type(extension: str, mime: Optional[str]) -> FileType:
    if mime and mime.startswith("image/"):
        return "image"
    if mime == "application/pdf" or extension == ".pdf":
        return "pdf"
    if mime in (
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ) or extension in {".doc", ".docx"}:
        return "docx"
    return "unknown"


def load_file(path: str | Path) -> dict[str, str]:
    """Return a dictionary describing the file."""

    archivo = ensure_readable_file(path)
    mime = get_mime_type(archivo) or "desconocido"
    extension = archivo.suffix.lower()
    return {
        "path": str(archivo),
        "extension": extension,
        "mime": mime,
        "type": _infer_type(extension, mime),
    }
