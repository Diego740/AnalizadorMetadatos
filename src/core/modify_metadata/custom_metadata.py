"""
Aplica metadatos personalizados a archivos soportados.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import piexif
import piexif.helper
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
        
    # Obtiene metadatos existentes y los fusiona con los nuevos
    metadata_to_write = dict(reader.metadata) if reader.metadata else {}
    for k, v in normalized_data.items():
        metadata_to_write[f"/{k}"] = v
        
    writer.add_metadata(metadata_to_write)
    
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
        
        if format_name in {"JPEG", "JPG", "TIFF", "MPO", "HEIC", "HEIF"}:
            # Maneja EXIF para JPEGs
            try:
                exif_dict = piexif.load(img.info.get("exif", b""))
            except Exception as e:
                print(f"Warning: Failed to load EXIF data: {e}")
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

            zeroth_ifd = exif_dict.get("0th", {})
            exif_ifd = exif_dict.get("Exif", {})
            
            # Mapeo de claves conocidas a etiquetas EXIF
            known_tags = {
                "artist": piexif.ImageIFD.Artist,
                "make": piexif.ImageIFD.Make,
                "model": piexif.ImageIFD.Model,
                "software": piexif.ImageIFD.Software,
                "copyright": piexif.ImageIFD.Copyright,
                "datetime": piexif.ImageIFD.DateTime,
            }

            custom_data = {}
            
            for key, value in normalized_data.items():
                key_lower = key.lower()
                
                # Normalizar formato de fecha si es necesario (YYYY-MM-DD -> YYYY:MM:DD)
                if "date" in key_lower and "-" in value[:10]:
                    value = value[:10].replace("-", ":") + value[10:]

                if key_lower in known_tags:
                    zeroth_ifd[known_tags[key_lower]] = value
                else:
                    custom_data[key] = value
            
            # Si hay datos personalizados extra, guardarlos en UserComment
            if custom_data:
                import json
                user_comment = json.dumps(custom_data, ensure_ascii=False)
                exif_ifd[piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(user_comment, encoding="unicode")

            exif_dict["0th"] = zeroth_ifd
            exif_dict["Exif"] = exif_ifd
            
            try:
                exif_bytes = piexif.dump(exif_dict)
                img.save(str(output_file), format=img.format, exif=exif_bytes)
            except Exception as e:
                print(f"Error saving EXIF data: {e}")
                # Respaldo: guardar sin EXIF si falla el volcado
                img.save(str(output_file), format=img.format)
            
        else:
            # Maneja fragmentos de texto PNG
            png_info = PngImagePlugin.PngInfo()
            for key, value in normalized_data.items():
                png_info.add_text(key, value)
            img.save(str(output_file), format=img.format, pnginfo=png_info)
            
    return output_file
