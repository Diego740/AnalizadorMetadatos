"""MIME helpers shared across the application."""
from __future__ import annotations

from typing import Optional

EXTENSIONES_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".txt": "text/plain",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".zip": "application/zip",
    ".rar": "application/x-rar-compressed",
    ".mp3": "audio/mpeg",
    ".mp4": "video/mp4",
    ".avi": "video/x-msvideo",
    ".rtf": "text/rtf",
}


def guess_extension_from_mime(mime: str) -> Optional[str]:
    """Return the first extension that matches *mime* or ``None``."""

    mime = (mime or "").lower()
    for ext, expected in EXTENSIONES_MIME.items():
        if expected == mime:
            return ext
    return None
