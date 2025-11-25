"""
Rutinas para eliminar metadatos de archivos soportados.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
from docx import Document

from .utils_modifier import ensure_editable_file, ensure_output_path


def wipe_metadata_pdf(file_path: str | Path, destination: Optional[str | Path] = None) -> Path:
    """
    Elimina los metadatos del PDF reescribiendo el documento con un diccionario de metadatos vacío.
    """
    source_file = ensure_editable_file(file_path)
    output_file = ensure_output_path(source_file, destination, suffix="_clean")
    
    reader = PdfReader(str(source_file))
    writer = PdfWriter()
    
    for page in reader.pages:
        writer.add_page(page)
        
    # Sobrescribe los metadatos con un diccionario vacío
    writer.add_metadata({})
    
    with output_file.open("wb") as f:
        writer.write(f)
        
    return output_file


def wipe_metadata_docx(file_path: str | Path, destination: Optional[str | Path] = None) -> Path:
    """
    Borra todas las propiedades principales estándar de DOCX.
    """
    source_file = ensure_editable_file(file_path)
    output_file = ensure_output_path(source_file, destination, suffix="_clean")
    
    doc = Document(str(source_file))
    props = doc.core_properties
    
    # Deja en blanco los campos comunes
    props.author = ""
    props.title = ""
    props.subject = ""
    props.comments = ""
    props.category = ""
    props.keywords = ""
    props.last_modified_by = ""
    
    doc.save(str(output_file))
    return output_file


def wipe_metadata_image(file_path: str | Path, destination: Optional[str | Path] = None) -> Path:
    """
    Crea una copia de la imagen sin datos EXIF copiando los datos de píxeles a una nueva imagen.
    """
    source_file = ensure_editable_file(file_path)
    output_file = ensure_output_path(source_file, destination, suffix="_clean")
    
    with Image.open(str(source_file)) as img:
        # Copia los datos de píxeles a un nuevo objeto de imagen para eliminar los metadatos
        data = list(img.getdata())
        clean_img = Image.new(img.mode, img.size)
        clean_img.putdata(data)
        clean_img.save(str(output_file), format=img.format)
        
    return output_file
