"""Apply custom metadata to supported files."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import piexif
from PIL import Image, PngImagePlugin
from PyPDF2 import PdfReader, PdfWriter
from docx import Document

from .utils_modifier import ensure_editable_file, ensure_output_path, normalize_metadata_dict


def apply_custom_pdf_metadata(
    path: str | Path,
    metadata: Dict[str, str],
    destination: Optional[str | Path] = None,
) -> Path:
    """Write arbitrary metadata entries to a PDF file."""

    normalized = normalize_metadata_dict(metadata)
    source = ensure_editable_file(path)
    output = ensure_output_path(source, destination, suffix="_custom")
    reader = PdfReader(str(source))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({f"/{k}": v for k, v in normalized.items()})
    with output.open("wb") as handler:
        writer.write(handler)
    return output


def apply_custom_docx_metadata(
    path: str | Path,
    metadata: Dict[str, str],
    destination: Optional[str | Path] = None,
) -> Path:
    """Update DOCX core properties using *metadata*."""

    normalized = normalize_metadata_dict(metadata)
    source = ensure_editable_file(path)
    output = ensure_output_path(source, destination, suffix="_custom")
    document = Document(str(source))
    props = document.core_properties
    mapping = {
        "author": "author",
        "title": "title",
        "subject": "subject",
        "comments": "comments",
        "category": "category",
        "keywords": "keywords",
    }
    for key, attr in mapping.items():
        if key in normalized:
            setattr(props, attr, normalized[key])
    document.save(str(output))
    return output


def apply_custom_image_metadata(
    path: str | Path,
    metadata: Dict[str, str],
    destination: Optional[str | Path] = None,
) -> Path:
    """Persist arbitrary metadata for JPEG/PNG formats."""

    normalized = normalize_metadata_dict(metadata)
    source = ensure_editable_file(path)
    output = ensure_output_path(source, destination, suffix="_custom")
    with Image.open(str(source)) as img:
        format_name = (img.format or "").upper()
        if format_name in {"JPEG", "JPG", "TIFF"}:
            zeroth = {}
            for key, value in normalized.items():
                if key.lower() == "artist":
                    zeroth[piexif.ImageIFD.Artist] = value
                elif key.lower() == "make":
                    zeroth[piexif.ImageIFD.Make] = value
                elif key.lower() == "software":
                    zeroth[piexif.ImageIFD.Software] = value
            exif_dict = {"0th": zeroth, "Exif": {}}
            exif_bytes = piexif.dump(exif_dict)
            img.save(str(output), format=img.format, exif=exif_bytes)
        else:
            info = PngImagePlugin.PngInfo()
            for key, value in normalized.items():
                info.add_text(key, value)
            img.save(str(output), format=img.format, pnginfo=info)
    return output
