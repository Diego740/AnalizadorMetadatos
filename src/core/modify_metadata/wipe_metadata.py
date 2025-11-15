"""Routines to remove metadata from supported files."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
from docx import Document

from .utils_modifier import ensure_editable_file, ensure_output_path


def wipe_metadata_pdf(path: str | Path, destination: Optional[str | Path] = None) -> Path:
    """Remove PDF metadata by rewriting the document."""

    source = ensure_editable_file(path)
    output = ensure_output_path(source, destination, suffix="_clean")
    reader = PdfReader(str(source))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({})
    with output.open("wb") as handler:
        writer.write(handler)
    return output


def wipe_metadata_docx(path: str | Path, destination: Optional[str | Path] = None) -> Path:
    """Remove DOCX core properties."""

    source = ensure_editable_file(path)
    output = ensure_output_path(source, destination, suffix="_clean")
    document = Document(str(source))
    props = document.core_properties
    props.author = ""
    props.title = ""
    props.subject = ""
    props.comments = ""
    props.category = ""
    props.keywords = ""
    props.last_modified_by = ""
    document.save(str(output))
    return output


def wipe_metadata_image(path: str | Path, destination: Optional[str | Path] = None) -> Path:
    """Create a copy of the image without EXIF data."""

    source = ensure_editable_file(path)
    output = ensure_output_path(source, destination, suffix="_clean")
    with Image.open(str(source)) as img:
        data = list(img.getdata())
        clean = Image.new(img.mode, img.size)
        clean.putdata(data)
        clean.save(str(output), format=img.format)
    return output
