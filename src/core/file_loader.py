"""
Abstracción del cargador de archivos que centraliza la detección de tipos.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from core.detect_extension import get_mime_type
from utils.path_tools import ensure_readable_file

FileType = Literal["image", "pdf", "docx", "unknown"]


def _infer_file_type(extension: str, mime_type: Optional[str]) -> FileType:
    """
    Determina el tipo de archivo basándose en el tipo MIME y la extensión.
    Prioriza el tipo MIME pero recurre a la extensión si es necesario.
    """
    if mime_type and mime_type.startswith("image/"):
        return "image"
        
    if mime_type == "application/pdf" or extension == ".pdf":
        return "pdf"
        
    if mime_type in (
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ) or extension in {".doc", ".docx"}:
        return "docx"
        
    return "unknown"


def load_file_info(file_path: str | Path) -> dict[str, str]:
    """
    Devuelve un diccionario describiendo las propiedades del archivo.
    """
    safe_path = ensure_readable_file(file_path)
    mime_type = get_mime_type(safe_path) or "unknown"
    extension = safe_path.suffix.lower()
    
    return {
        "path": str(safe_path),
        "extension": extension,
        "mime": mime_type,
        "type": _infer_file_type(extension, mime_type),
    }
