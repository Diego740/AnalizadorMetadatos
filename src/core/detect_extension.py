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
    Si hay múltiples coincidencias, prioriza la que coincida con la extensión del archivo.
    """
    try:
        safe_path = ensure_readable_file(file_path)
        # Usamos magic_file para obtener todas las posibles coincidencias con confianza
        matches = puremagic.magic_file(str(safe_path))
        
        if not matches:
            return None
            
        # Si solo hay una coincidencia, la devolvemos
        if len(matches) == 1:
            return matches[0].mime_type
            
        # Si hay múltiples, buscamos si alguna coincide con la extensión actual
        current_ext = safe_path.suffix.lower()
        expected_mime = EXTENSIONES_MIME.get(current_ext)
        
        if expected_mime:
            for match in matches:
                if match.mime_type == expected_mime:
                    return match.mime_type
                    
        # Si no hay coincidencia con la extensión, devolvemos la de mayor confianza (la primera)
        return matches[0].mime_type
        
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
