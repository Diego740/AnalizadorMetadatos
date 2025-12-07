"""
Rutinas de extracción de metadatos.

Este módulo maneja la extracción de metadatos de varios formatos de archivo
incluyendo PDF, DOCX e Imágenes (JPEG/PNG/HEIC).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import json

import puremagic
from PIL import Image
from PIL.ExifTags import TAGS
from PyPDF2 import PdfReader
from docx import Document
import piexif
import piexif.helper
from pillow_heif import register_heif_opener

from utils.path_tools import ensure_readable_file

# Habilita el soporte HEIC para Pillow
register_heif_opener()




def sanitize_exif_value(value: Any) -> Any:
    """
    Ayuda a convertir datos EXIF en formatos compatibles con JSON.
    Maneja la decodificación de bytes y estructuras recursivas.
    """
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", "ignore")
        except Exception:
            # Si no podemos decodificarlo, devolvemos la representación en cadena
            return repr(value)
            
    if isinstance(value, tuple):
        return tuple(sanitize_exif_value(v) for v in value)
        
    if isinstance(value, list):
        return [sanitize_exif_value(v) for v in value]
        
    if isinstance(value, dict):
        return {k: sanitize_exif_value(v) for k, v in value.items()}
        
    return value


def extract_metadata_pdf(file_path: str | Path) -> Dict[str, Any]:
    """Lee los metadatos de un archivo PDF."""
    metadata: Dict[str, Any] = {}
    safe_path = ensure_readable_file(file_path)
    
    try:
        with safe_path.open("rb") as f:
            pdf = PdfReader(f)
            info = pdf.metadata or {}
            
            #Elimina / inicial
            for key, value in info.items():
                clean_key = key.strip("/")
                metadata[clean_key] = str(value)
                
    except Exception as e:
        metadata["error"] = f"Failed to read PDF metadata: {e}"
        
    return metadata


def extract_metadata_docx(file_path: str | Path) -> Dict[str, Any]:
    """Lee las propiedades principales de un archivo DOCX."""
    metadata: Dict[str, Any] = {}
    safe_path = ensure_readable_file(file_path)
    
    try:
        doc = Document(str(safe_path))
        props = doc.core_properties
        
        # Extrae propiedades estándar
        metadata = {
            "author": props.author,
            "title": props.title,
            "subject": props.subject,
            "created": str(props.created),
            "modified": str(props.modified),
            "last_printed": str(props.last_printed),
        }
        
    except Exception as e:
        metadata["error"] = f"Failed to read DOCX metadata: {e}"
        
    return metadata


def generate_maps_link(lat: float, lon: float) -> str:
    """Crea un enlace de Google Maps a partir de las coordenadas."""
    return f"https://www.google.com/maps?q={lat},{lon}"


def extract_metadata_image(file_path: str | Path) -> Dict[str, Any]:
    """
    Extrae EXIF y otros metadatos de imágenes.
    Soporta formatos estándar + HEIC.
    """
    safe_path = ensure_readable_file(file_path)
    metadata: Dict[str, Any] = {}
    
    try:
        img = Image.open(str(safe_path))
        metadata["Format"] = img.format
        
        # Intenta obtener datos EXIF sin procesar primero
        exif_bytes = img.info.get("exif")
        
        if exif_bytes:
            exif_data = piexif.load(exif_bytes)
            
            for ifd_name, content in exif_data.items():
                if isinstance(content, dict):
                    for tag_id, value in content.items():
                        # Resuelve los nombres de las etiquetas
                        tag_name = piexif.TAGS.get(ifd_name, {}).get(tag_id, {}).get("name", f"{ifd_name}-{tag_id}")
                        
                        if ifd_name == "GPS":
                            if "GPS" not in metadata:
                                metadata["GPS"] = {}
                            # Se asegura de que sea un diccionario antes de asignar
                            if not isinstance(metadata["GPS"], dict):
                                metadata["GPS"] = {}
                            metadata["GPS"][tag_name] = sanitize_exif_value(value)
                        elif tag_name == "UserComment":
                            # Intentar parsear UserComment como JSON para metadatos personalizados
                            try:
                                # UserComment suele venir como bytes con prefijo
                                comment = piexif.helper.UserComment.load(value)
                                if comment:
                                    custom_data = json.loads(comment)
                                    if isinstance(custom_data, dict):
                                        metadata.update(custom_data)
                                    else:
                                        metadata["UserComment"] = comment
                            except Exception:
                                # Si falla, guardar como string normal
                                metadata[tag_name] = sanitize_exif_value(value)
                        else:
                            # Evita colisión: El IFD 0 tiene una etiqueta llamada "GPS" (offset), que sobrescribiría nuestro diccionario GPS
                            if tag_name == "GPS":
                                tag_name = "GPSOffset"
                            metadata[tag_name] = sanitize_exif_value(value)
            
            # Procesa las coordenadas GPS si están disponibles
            coords = parse_gps_coordinates(exif_data.get("GPS", {}))
            if coords:
                metadata.update(coords)
                if "GPS_Latitude" in coords and "GPS_Longitude" in coords:
                    metadata["MapsLink"] = generate_maps_link(coords["GPS_Latitude"], coords["GPS_Longitude"])
            
            return metadata
            
        # Alternativa para EXIF básico
        exif = img.getexif()
        if exif:
            for tag_id, value in exif.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                metadata[tag_name] = sanitize_exif_value(value)
        
        # Leer metadatos adicionales de img.info (ej. PNG text chunks)
        # Filtramos claves binarias o internas grandes
        ignored_keys = {"exif", "icc_profile", "photoshop", "xml:com.adobe.xmp"}
        for key, value in img.info.items():
            if key.lower() not in ignored_keys and isinstance(value, (str, int, float)):
                metadata[key] = value

        if not exif and not metadata.get("info") and len(metadata) <= 1:
             # Si solo tenemos "Format" y nada más
            metadata["info"] = "No EXIF data found in image."
            
    except Exception as e:
        metadata["error"] = f"Error processing image: {e}"
        
    return metadata


def parse_gps_coordinates(gps_info: Dict[str, Any]) -> Dict[str, float]:
    """
    Decodifica metadatos GPS (tuplas racionales) a grados decimales.
    """
    if not gps_info:
        return {}

    def dms_to_decimal(dms_tuple):
        degrees = dms_tuple[0][0] / dms_tuple[0][1]
        minutes = dms_tuple[1][0] / dms_tuple[1][1]
        seconds = dms_tuple[2][0] / dms_tuple[2][1]
        return degrees + (minutes / 60) + (seconds / 3600)

    try:
        # Etiquetas GPS: 1=LatRef, 2=Lat, 3=LonRef, 4=Lon
        lat = dms_to_decimal(gps_info[2])
        lon = dms_to_decimal(gps_info[4])
        
        # Ajuste por hemisferio
        lat_ref = gps_info.get(1)
        if lat_ref in {b"S", "S"}:
            lat = -lat
            
        lon_ref = gps_info.get(3)
        if lon_ref in {b"W", "W"}:
            lon = -lon
            
        return {"GPS_Latitude": lat, "GPS_Longitude": lon}
        
    except Exception:
        # Si falla el análisis, devuelve vacío (no romper la ejecución)
        return {}


def extract_metadata_auto(file_path: str | Path) -> Dict[str, Any]:
    """
    Punto de entrada principal: detecta el tipo de archivo y llama al extractor apropiado.
    """
    safe_path = ensure_readable_file(file_path)

    # Comprobación rápida de archivos vacíos
    if safe_path.stat().st_size == 0:
        return {
            "file": safe_path.name,
            "path": str(safe_path),
            "mime_type": "application/x-empty",
            "extension": safe_path.suffix.lower(),
            "metadata": {"info": "File is empty (0 bytes)."},
        }

    # Detectar tipo
    from .detect_extension import get_mime_type
    mime_type = get_mime_type(safe_path)
    if mime_type is None:
        mime_type = "application/octet-stream"
    extension = safe_path.suffix.lower()

    result = {
        "file": safe_path.name,
        "path": str(safe_path),
        "mime_type": mime_type,
        "extension": extension,
        "metadata": {},
    }

    try:
        if mime_type.startswith("image/"):
            result["metadata"] = extract_metadata_image(safe_path)
            
        elif mime_type == "application/pdf":
            result["metadata"] = extract_metadata_pdf(safe_path)
            
        elif mime_type in (
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ):
            result["metadata"] = extract_metadata_docx(safe_path)
            
        else:
            result["metadata"] = {"info": "Format not currently supported for deep analysis."}
            
        # --- Integración de Análisis de Seguridad ---
        try:
            from security import analyze_risk
        except ImportError:
            # Respaldo para cuando se ejecuta desde la raíz del proyecto
            from src.security import analyze_risk
            
        security_report = analyze_risk(safe_path, result["metadata"], mime_type)
        if security_report["is_suspicious"]:
            result["security_analysis"] = security_report
            
    except Exception as e:
        print(f"Error analyzing {safe_path}: {e}")
        result["metadata"] = {"error": str(e)}
        
    return result


def format_metadata(metadata: Dict[str, Any]) -> str:
    """Imprime los metadatos como JSON formateado."""
    return json.dumps(metadata, indent=4, ensure_ascii=False)
