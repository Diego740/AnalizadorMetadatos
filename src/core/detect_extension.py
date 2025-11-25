"""
Ayudantes para detectar y validar extensiones de archivo usando libmagic.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import puremagic

from utils.mime_tools import EXTENSIONES_MIME, guess_extension_from_mime
from utils.path_tools import ensure_readable_file


def get_mime_type(file_path: str | Path) -> Optional[str]:
    """
    Devuelve el tipo MIME reportado por libmagic.
    """
    try:
        safe_path = ensure_readable_file(file_path)
        return puremagic.from_file(str(safe_path), mime=True)
    except FileNotFoundError:
        raise
    except Exception:
        return None


def extension_matches_mime(file_path: str | Path) -> bool:
    """
    Comprueba si la extensión del archivo coincide con su tipo MIME detectado.
    """
    safe_path = ensure_readable_file(file_path)
    current_extension = safe_path.suffix.lower()
    mime_type = get_mime_type(safe_path)
    
    if mime_type is None:
        return False
        
    return EXTENSIONES_MIME.get(current_extension) == mime_type


def suggest_correct_extension(file_path: str | Path) -> Optional[str]:
    """
    Sugiere la extensión correcta basada en el tipo MIME del archivo.
    Devuelve None si la extensión actual ya es correcta o si es desconocida.
    """
    safe_path = ensure_readable_file(file_path)
    mime_type = get_mime_type(safe_path)
    
    if mime_type is None:
        return None

    suggested = guess_extension_from_mime(mime_type)
    if suggested:
        return suggested
        
    return safe_path.suffix.lower() or None
