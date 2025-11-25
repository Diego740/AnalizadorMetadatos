"""
Aplica metadatos personalizados a archivos soportados.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import piexif
from PIL import Image, PngImagePlugin
from PyPDF2 import PdfReader, PdfWriter
from docx import Document

from .utils_modifier import ensure_editable_file, ensure_output_path, normalize_metadata_dict


def apply_custom_pdf_metadata(
    file_path: str | Path,
    metadata: Dict[str, str],
    destination: Optional[str | Path] = None,
) -> Path:
    """
    Escribe entradas de metadatos arbitrarias en un archivo PDF.
    Crea un nuevo archivo con el sufijo '_custom' por defecto.
    """
    normalized_data = normalize_metadata_dict(metadata)
    source_file = ensure_editable_file(file_path)
    output_file = ensure_output_path(source_file, destination, suffix="_custom")
    
    reader = PdfReader(str(source_file))
    writer = PdfWriter()
    
    # Copia todas las páginas
    for page in reader.pages:
        writer.add_page(page)
        
    # Añade nuevos metadatos (las claves PDF suelen empezar con /)
    writer.add_metadata({f"/{k}": v for k, v in normalized_data.items()})
    
    with output_file.open("wb") as f:
        writer.write(f)
        
    return output_file


def apply_custom_docx_metadata(
    file_path: str | Path,
    metadata: Dict[str, str],
    destination: Optional[str | Path] = None,
) -> Path:
    """
    Actualiza las propiedades principales de DOCX usando los metadatos proporcionados.
    Solo mapea propiedades conocidas como autor, título, etc.
    """
    normalized_data = normalize_metadata_dict(metadata)
    source_file = ensure_editable_file(file_path)
    output_file = ensure_output_path(source_file, destination, suffix="_custom")
    
    doc = Document(str(source_file))
    props = doc.core_properties
    
    # Mapea claves de usuario a atributos de propiedad DOCX reales
    property_map = {
        "author": "author",
        "title": "title",
        "subject": "subject",
        "comments": "comments",
        "category": "category",
        "keywords": "keywords",
    }
    
    for key, attr_name in property_map.items():
        if key in normalized_data:
            setattr(props, attr_name, normalized_data[key])
            
    doc.save(str(output_file))
    return output_file


def apply_custom_image_metadata(
    file_path: str | Path,
    metadata: Dict[str, str],
    destination: Optional[str | Path] = None,
) -> Path:
    """
    Persiste metadatos arbitrarios para formatos JPEG/PNG.
    Para JPEGs, actualiza etiquetas EXIF específicas.
    Para PNGs, añade fragmentos de texto.
    """
    normalized_data = normalize_metadata_dict(metadata)
    source_file = ensure_editable_file(file_path)
    output_file = ensure_output_path(source_file, destination, suffix="_custom")
    
    with Image.open(str(source_file)) as img:
        format_name = (img.format or "").upper()
        
        if format_name in {"JPEG", "JPG", "TIFF"}:
            # Maneja EXIF para JPEGs
            zeroth_ifd = {}
            for key, value in normalized_data.items():
                key_lower = key.lower()
                if key_lower == "artist":
                    zeroth_ifd[piexif.ImageIFD.Artist] = value
                elif key_lower == "make":
                    zeroth_ifd[piexif.ImageIFD.Make] = value
                elif key_lower == "software":
                    zeroth_ifd[piexif.ImageIFD.Software] = value
                    
            exif_dict = {"0th": zeroth_ifd, "Exif": {}}
            exif_bytes = piexif.dump(exif_dict)
            img.save(str(output_file), format=img.format, exif=exif_bytes)
            
        else:
            # Maneja fragmentos de texto PNG
            png_info = PngImagePlugin.PngInfo()
            for key, value in normalized_data.items():
                png_info.add_text(key, value)
            img.save(str(output_file), format=img.format, pnginfo=png_info)
            
    return output_file
