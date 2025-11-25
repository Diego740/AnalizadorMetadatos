"""
Ayudantes compartidos para módulos de modificación de metadatos.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from utils.path_tools import ensure_readable_file, resolve_path


def ensure_editable_file(file_path: str | Path) -> Path:
    """
    Valida que el archivo existe y es legible.
    Devuelve un objeto Path.
    """
    return ensure_readable_file(file_path)


def ensure_output_path(source_path: Path, destination: str | Path | None = None, suffix: str = "") -> Path:
    """
    Determina la ruta de salida.
    Si no se proporciona destino, añade el sufijo al nombre del archivo fuente.
    Asegura que los directorios padres existan.
    """
    if destination:
        target = resolve_path(destination)
    else:
        # Crea un nuevo nombre de archivo como "documento_clean.pdf"
        target = source_path.with_name(f"{source_path.stem}{suffix or ''}{source_path.suffix}")
        
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def normalize_metadata_dict(metadata: Dict[str, Any]) -> Dict[str, str]:
    """
    Limpia el diccionario de metadatos:
    - Convierte valores a cadenas
    - Elimina espacios en blanco
    - Elimina valores None
    """
    normalized: Dict[str, str] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        normalized[str(key).strip()] = str(value).strip()
        
    return normalized
