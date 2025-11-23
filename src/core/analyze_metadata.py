"""Metadata extraction routines."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import json

import puremagic
from PIL import Image
from PIL.ExifTags import TAGS
from PyPDF2 import PdfReader
from docx import Document
import piexif
from pillow_heif import register_heif_opener

from utils.logger import get_logger
from utils.path_tools import ensure_readable_file

register_heif_opener()
LOGGER = get_logger(__name__)


def _to_json_safe(value: Any) -> Any:
    """Convert EXIF values into JSON serializable objects."""

    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", "ignore")
        except Exception:
            return repr(value)
    if isinstance(value, tuple):
        return tuple(_to_json_safe(v) for v in value)
    if isinstance(value, list):
        return [_to_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_json_safe(v) for k, v in value.items()}
    return value


def extract_metadata_pdf(path: str | Path) -> Dict[str, Any]:
    """Extract metadata from a PDF file."""

    data: Dict[str, Any] = {}
    archivo = ensure_readable_file(path)
    try:
        with archivo.open("rb") as handler:
            info = PdfReader(handler).metadata or {}
            for key, value in info.items():
                data[key.strip("/")] = str(value)
    except Exception as exc:
        data["error"] = f"Could not read PDF metadata: {exc}"
    return data


def extract_metadata_docx(path: str | Path) -> Dict[str, Any]:
    """Extract metadata from a DOCX document."""

    data: Dict[str, Any] = {}
    archivo = ensure_readable_file(path)
    try:
        doc = Document(str(archivo))
        props = doc.core_properties
        data = {
            "author": props.author,
            "title": props.title,
            "subject": props.subject,
            "created": str(props.created),
            "modified": str(props.modified),
            "last_printed": str(props.last_printed),
        }
    except Exception as exc:
        data["error"] = f"Could not read DOCX metadata: {exc}"
    return data


def get_google_maps_link(lat: float, lon: float) -> str:
    """Generate a Google Maps link for the given coordinates."""
    return f"https://www.google.com/maps?q={lat},{lon}"


def extract_metadata_image(path: str | Path) -> Dict[str, Any]:
    """Extract EXIF metadata for JPEG/PNG/HEIC images."""

    archivo = ensure_readable_file(path)
    data: Dict[str, Any] = {}
    try:
        img = Image.open(str(archivo))
        data["Format"] = img.format
        exif_bytes = img.info.get("exif")
        if exif_bytes:
            exif_dict = piexif.load(exif_bytes)
            for ifd_name, content in exif_dict.items():
                if isinstance(content, dict):
                    for tag_id, value in content.items():
                        tag_name = piexif.TAGS.get(ifd_name, {}).get(tag_id, {}).get("name", f"{ifd_name}-{tag_id}")
                        if ifd_name == "GPS":
                            if "GPS" not in data:
                                data["GPS"] = {}
                            data["GPS"][tag_name] = _to_json_safe(value)
                        else:
                            data[tag_name] = _to_json_safe(value)
            coords = convert_gps_to_decimal(exif_dict.get("GPS", {}))
            if coords:
                data.update(coords)
                if "GPS_Latitude" in coords and "GPS_Longitude" in coords:
                    data["MapsLink"] = get_google_maps_link(coords["GPS_Latitude"], coords["GPS_Longitude"])
            return data
        exif = img.getexif()
        if exif:
            for tag_id, value in exif.items():
                data[TAGS.get(tag_id, str(tag_id))] = _to_json_safe(value)
        else:
            data["info"] = "No EXIF metadata found."
    except Exception as exc:
        data["error"] = f"Error reading metadata: {exc}"
    return data


def convert_gps_to_decimal(gps_info: Dict[str, Any]) -> Dict[str, float]:
    """Convert GPS rational tuples into decimal coordinates."""

    if not gps_info:
        return {}

    def _convert(value):
        grados = value[0][0] / value[0][1]
        minutos = value[1][0] / value[1][1]
        segundos = value[2][0] / value[2][1]
        return grados + minutos / 60 + segundos / 3600

    try:
        lat = _convert(gps_info[2])
        lon = _convert(gps_info[4])
        if gps_info.get(1) in {b"S", "S"}:
            lat = -lat
        if gps_info.get(3) in {b"W", "W"}:
            lon = -lon
        return {"GPS_Latitude": lat, "GPS_Longitude": lon}
    except Exception:
        return {}


def extract_metadata_auto(path: str | Path) -> Dict[str, Any]:
    """Detect file type and dispatch to the proper extractor."""

    archivo = ensure_readable_file(path)

    # Check for empty file
    if archivo.stat().st_size == 0:
        return {
            "file": archivo.name,
            "path": str(archivo),
            "mime_type": "application/x-empty",
            "extension": archivo.suffix.lower(),
            "metadata": {"info": "The file is empty (0 bytes)."},
        }

    mime = puremagic.from_file(str(archivo), mime=True)
    extension = archivo.suffix.lower()

    resultado = {
        "file": archivo.name,
        "path": str(archivo),
        "mime_type": mime,
        "extension": extension,
        "metadata": {},
    }

    try:
        if mime.startswith("image/"):
            resultado["metadata"] = extract_metadata_image(archivo)
        elif mime == "application/pdf":
            resultado["metadata"] = extract_metadata_pdf(archivo)
        elif mime in (
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ):
            resultado["metadata"] = extract_metadata_docx(archivo)
        else:
            resultado["metadata"] = {"info": "Unsupported format"}
    except Exception as exc:
        LOGGER.error("Error analyzing %s: %s", archivo, exc)
        resultado["metadata"] = {"error": str(exc)}
    return resultado


def format_metadata(metadata: Dict[str, Any]) -> str:
    """Return metadata as a formatted JSON string."""

    return json.dumps(metadata, indent=4, ensure_ascii=False)


# Example:
# >>> print(format_metadata(extract_metadata_auto("/tmp/foto.jpg")))
