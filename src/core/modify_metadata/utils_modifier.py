"""Shared helpers for metadata modification modules."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from utils.path_tools import ensure_readable_file, resolve_path


def ensure_editable_file(path: str | Path) -> Path:
    """Return the validated file path that will be modified."""

    return ensure_readable_file(path)


def ensure_output_path(source: Path, destination: str | Path | None = None, suffix: str = "") -> Path:
    """Return the output path, creating parent folders when required."""

    if destination:
        target = resolve_path(destination)
    else:
        target = source.with_name(f"{source.stem}{suffix or ''}{source.suffix}")
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def normalize_metadata_dict(metadata: Dict[str, Any]) -> Dict[str, str]:
    """Normalize metadata keys and values for writing operations."""

    normalized: Dict[str, str] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        normalized[str(key).strip()] = str(value).strip()
    return normalized
