"""Default metadata assignment for supported files."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import piexif
from PIL import Image, PngImagePlugin
from PyPDF2 import PdfReader, PdfWriter
from docx import Document

from .utils_modifier import ensure_editable_file, ensure_output_path

DEFAULT_AUTHOR = "AnalizadorMetadatos"
DEFAULT_TITLE = "Documento procesado"


def _now_string() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def apply_default_pdf_metadata(path: str | Path, destination: Optional[str | Path] = None) -> Path:
    """Add default metadata to a PDF file."""

    source = ensure_editable_file(path)
    output = ensure_output_path(source, destination, suffix="_default")
    reader = PdfReader(str(source))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({
        "/Author": DEFAULT_AUTHOR,
        "/Title": DEFAULT_TITLE,
        "/Producer": "AnalizadorMetadatos",
        "/Creator": "Analizador CLI",
        "/CreationDate": _now_string(),
    })
    with output.open("wb") as handler:
        writer.write(handler)
    return output


def apply_default_docx_metadata(path: str | Path, destination: Optional[str | Path] = None) -> Path:
    """Assign default properties to a DOCX file."""

    source = ensure_editable_file(path)
    output = ensure_output_path(source, destination, suffix="_default")
    document = Document(str(source))
    props = document.core_properties
    props.author = DEFAULT_AUTHOR
    props.title = DEFAULT_TITLE
    props.subject = "Documento generado"
    props.comments = "Metadatos asignados automáticamente"
    props.last_modified_by = DEFAULT_AUTHOR
    props.category = "Analizador"
    document.save(str(output))
    return output


def apply_default_image_metadata(path: str | Path, destination: Optional[str | Path] = None) -> Path:
    """Insert a very small EXIF header on supported formats."""

    source = ensure_editable_file(path)
    output = ensure_output_path(source, destination, suffix="_default")
    with Image.open(str(source)) as img:
        format_name = (img.format or "").upper()
        if format_name in {"JPEG", "JPG", "TIFF"}:
            exif_dict = {
                "0th": {
                    piexif.ImageIFD.Make: DEFAULT_AUTHOR,
                    piexif.ImageIFD.Software: "Analizador CLI",
                    piexif.ImageIFD.Artist: DEFAULT_AUTHOR,
                },
                "Exif": {
                    piexif.ExifIFD.DateTimeOriginal: _now_string(),
                },
            }
            exif_bytes = piexif.dump(exif_dict)
            img.save(str(output), format=img.format, exif=exif_bytes)
        else:
            info = PngImagePlugin.PngInfo()
            info.add_text("Author", DEFAULT_AUTHOR)
            info.add_text("Software", "Analizador CLI")
            info.add_text("Description", DEFAULT_TITLE)
            img.save(str(output), format=img.format, pnginfo=info)
    return output
