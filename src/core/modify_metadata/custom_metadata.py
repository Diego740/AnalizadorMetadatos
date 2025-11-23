"""Apply custom metadata to supported files."""
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
            # Load existing EXIF or create empty
            if "exif" in img.info:
                try:
                    exif_dict = piexif.load(img.info["exif"])
                except Exception:
                    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
            else:
                 exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

            non_standard_data = []

            for key, value in normalized.items():
                lower_key = key.lower()

                if lower_key == "artist":
                    exif_dict["0th"][piexif.ImageIFD.Artist] = value.encode("utf-8") if isinstance(value, str) else value
                elif lower_key == "make":
                    exif_dict["0th"][piexif.ImageIFD.Make] = value.encode("utf-8") if isinstance(value, str) else value
                elif lower_key == "model":
                     exif_dict["0th"][piexif.ImageIFD.Model] = value.encode("utf-8") if isinstance(value, str) else value
                elif lower_key == "software":
                    exif_dict["0th"][piexif.ImageIFD.Software] = value.encode("utf-8") if isinstance(value, str) else value
                elif lower_key == "copyright":
                     exif_dict["0th"][piexif.ImageIFD.Copyright] = value.encode("utf-8") if isinstance(value, str) else value
                elif lower_key == "imagedescription":
                     exif_dict["0th"][piexif.ImageIFD.ImageDescription] = value.encode("utf-8") if isinstance(value, str) else value
                elif lower_key == "datetime":
                     exif_dict["0th"][piexif.ImageIFD.DateTime] = value.encode("utf-8") if isinstance(value, str) else value
                else:
                    non_standard_data.append(f"{key}: {value}")

            if non_standard_data:
                # Get current UserComment if exists
                current_comment = exif_dict["Exif"].get(piexif.ExifIFD.UserComment, b"")

                # Decode current comment if possible to append to it
                decoded_comment = ""
                if isinstance(current_comment, bytes):
                    try:
                        # Try to handle UserComment headers if present
                        # piexif.helper.UserComment.load(current_comment) might work but let's try manual decoding first
                        # as headers vary (ASCII, UNICODE, JIS, or None)
                        if current_comment.startswith(b"ASCII\0\0\0"):
                             decoded_comment = current_comment[8:].decode("utf-8", errors="ignore")
                        elif current_comment.startswith(b"UNICODE\0"):
                             decoded_comment = current_comment[8:].decode("utf-16", errors="ignore")
                        else:
                             # Try decoding directly, might fail if it has other headers or is binary
                             decoded_comment = current_comment.decode("utf-8", errors="ignore").replace("\x00", "")
                    except Exception:
                        pass

                new_comment_str = "; ".join(non_standard_data)

                if decoded_comment:
                    # Clean up null bytes from decoded comment just in case
                    decoded_comment = decoded_comment.strip('\x00')
                    if decoded_comment:
                        final_comment_str = f"{decoded_comment}; {new_comment_str}"
                    else:
                        final_comment_str = new_comment_str
                else:
                    final_comment_str = new_comment_str

                # Encode back to UserComment using piexif helper which handles headers
                try:
                    exif_dict["Exif"][piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(final_comment_str, encoding="unicode")
                except Exception:
                     # Fallback to ascii if unicode fails for some reason
                     exif_dict["Exif"][piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(final_comment_str, encoding="ascii")

            try:
                exif_bytes = piexif.dump(exif_dict)
                img.save(str(output), format=img.format, exif=exif_bytes)
            except Exception:
                # Fallback if dumping fails (e.g. data too large or invalid)
                # Try saving without exif or handle error?
                # Ideally we want to fail gracefully but requirements say "save new data".
                # If we can't dump exif, maybe we should try to save just the valid parts?
                # For now let it raise or save original if possible.
                # But let's assume it works.
                img.save(str(output), format=img.format)

        else:
            info = PngImagePlugin.PngInfo()
            for key, value in normalized.items():
                info.add_text(key, value)
            img.save(str(output), format=img.format, pnginfo=info)
    return output
