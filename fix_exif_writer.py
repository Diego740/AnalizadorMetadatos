"""Herramientas robustas para leer, regenerar y escribir metadatos EXIF en JPEG."""
from __future__ import annotations

import sys
from io import BytesIO
from typing import Dict, Optional

from PIL import Image
import piexif
from piexif import helper
from piexif._exceptions import InvalidImageDataError


def load_exif(path: str) -> Optional[dict]:
    """Carga EXIF de forma segura.

    Devuelve ``None`` si el archivo no contiene EXIF válido o si está corrupto.
    """
    try:
        exif_dict = piexif.load(path)
    except InvalidImageDataError as exc:
        print(f"[load_exif] EXIF corrupto en '{path}': {exc}")
        return None
    except Exception as exc:  # pragma: no cover - diagnóstico general
        print(f"[load_exif] Error inesperado al leer '{path}': {exc}")
        return None

    if not exif_dict or not any(exif_dict.get(ifd) for ifd in ("0th", "Exif", "GPS", "1st")):
        print(f"[load_exif] No se encontró EXIF válido en '{path}'.")
        return None

    print(f"[load_exif] EXIF cargado correctamente desde '{path}'.")
    return exif_dict


def _clean_maker_note(exif_dict: dict) -> dict:
    """Elimina MakerNote dañados que impiden reescribir EXIF."""
    cleaned = {**exif_dict}
    exif_ifd = dict(cleaned.get("Exif", {}))
    if piexif.ExifIFD.MakerNote in exif_ifd:
        exif_ifd.pop(piexif.ExifIFD.MakerNote, None)
        print("[write_exif] MakerNote eliminado para evitar corrupción de EXIF.")
    cleaned["Exif"] = exif_ifd
    return cleaned


def write_exif(path_in: str, path_out: str, exif_dict: dict) -> None:
    """Escribe el diccionario EXIF en un JPEG usando piexif.insert.

    Maneja estructuras inconsistentes y asegura que el archivo de salida conserve
    los metadatos.
    """
    try:
        with open(path_in, "rb") as fh:
            original_bytes = fh.read()
    except OSError as exc:  # pragma: no cover - I/O
        print(f"[write_exif] No se pudo leer '{path_in}': {exc}")
        return

    # Verificar que sea JPEG válido.
    try:
        with Image.open(BytesIO(original_bytes)) as img:
            if img.format != "JPEG":
                raise ValueError("Solo se admiten imágenes JPEG")
    except Exception as exc:  # pragma: no cover - diagnóstico
        print(f"[write_exif] '{path_in}' no es un JPEG válido: {exc}")
        return

    exif_ready = _clean_maker_note(exif_dict)
    try:
        exif_bytes = piexif.dump(exif_ready)
    except Exception as exc:  # pragma: no cover - diagnóstico
        print(f"[write_exif] No se pudo convertir EXIF a bytes: {exc}")
        return

    try:
        new_bytes = piexif.insert(exif_bytes, original_bytes)
    except Exception as exc:
        print(f"[write_exif] piexif.insert falló, intentando reescribir: {exc}")
        try:
            with Image.open(BytesIO(original_bytes)) as img:
                buffer = BytesIO()
                img.save(buffer, format="JPEG")
                new_bytes = piexif.insert(exif_bytes, buffer.getvalue())
        except Exception as retry_exc:  # pragma: no cover - diagnóstico
            print(f"[write_exif] Falló reescritura con piexif.insert: {retry_exc}")
            return

    try:
        with open(path_out, "wb") as fh:
            fh.write(new_bytes)
        print(f"[write_exif] EXIF escrito correctamente en '{path_out}'.")
    except OSError as exc:  # pragma: no cover - I/O
        print(f"[write_exif] No se pudo escribir '{path_out}': {exc}")


def _map_metadata_to_ifds(metadata: Dict[str, object]) -> Dict[str, Dict[int, object]]:
    """Convierte claves de metadatos (por nombre) a IFDs válidos."""
    mapped = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}}
    for key, value in metadata.items():
        for ifd_name, tags in piexif.TAGS.items():
            for tag_id, tag_info in tags.items():
                if tag_info["name"] == key:
                    mapped.setdefault(ifd_name, {})[tag_id] = value
                    break
    return mapped


def rebuild_exif(minimal_info: Dict[str, object]) -> dict:
    """Crea un EXIF mínimo válido a partir de datos simples."""
    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
    mapped = _map_metadata_to_ifds(minimal_info)

    for tag_id, value in mapped.get("0th", {}).items():
        exif_dict["0th"][tag_id] = _ensure_bytes(value)
    for tag_id, value in mapped.get("Exif", {}).items():
        if tag_id == piexif.ExifIFD.UserComment:
            exif_dict["Exif"][tag_id] = _build_user_comment(value)
        else:
            exif_dict["Exif"][tag_id] = _ensure_bytes(value)
    for tag_id, value in mapped.get("Interop", {}).items():
        exif_dict["Interop"][tag_id] = _ensure_bytes(value)

    # Añadir fechas mínimas si no están presentes.
    if piexif.ImageIFD.DateTime not in exif_dict["0th"]:
        exif_dict["0th"][piexif.ImageIFD.DateTime] = _ensure_bytes(minimal_info.get("DateTimeOriginal", ""))
    if piexif.ExifIFD.DateTimeOriginal not in exif_dict["Exif"]:
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = _ensure_bytes(minimal_info.get("DateTimeOriginal", ""))

    print("[rebuild_exif] EXIF mínimo reconstruido.")
    return exif_dict


def _ensure_bytes(value: object) -> bytes:
    if isinstance(value, bytes):
        return value
    return str(value).encode("utf-8")


def _build_user_comment(value: object) -> bytes:
    try:
        return helper.UserComment.dump(str(value), encoding="unicode")
    except Exception:
        return helper.UserComment.dump(str(value))


def apply_custom_metadata(path_in: str, path_out: str, metadata: Dict[str, object]) -> None:
    """Aplica metadatos personalizados de forma segura.

    Si el EXIF original está ausente o corrupto, se reconstruye desde cero.
    Solo se modifican campos válidos. Tras escribir, se verifica la presencia
    de EXIF en el archivo resultante.
    """
    exif_dict = load_exif(path_in)
    mapped = _map_metadata_to_ifds(metadata)

    if exif_dict is None:
        exif_dict = rebuild_exif(metadata)
    else:
        for ifd_name in ("0th", "Exif", "GPS", "Interop", "1st"):
            target_ifd = dict(exif_dict.get(ifd_name, {}))
            for tag_id, value in mapped.get(ifd_name, {}).items():
                if ifd_name == "Exif" and tag_id == piexif.ExifIFD.UserComment:
                    target_ifd[tag_id] = _build_user_comment(value)
                else:
                    target_ifd[tag_id] = _ensure_bytes(value)
            exif_dict[ifd_name] = target_ifd

    write_exif(path_in, path_out, exif_dict)

    final_exif = load_exif(path_out)
    if final_exif is None:
        print("[apply_custom_metadata] Advertencia: no se encontró EXIF tras guardar.")
    else:
        print("[apply_custom_metadata] Metadatos aplicados correctamente.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python fix_exif_writer.py <input.jpg> <output.jpg> [clave=valor ...]")
        sys.exit(1)

    input_path, output_path, *pairs = sys.argv[1:]
    metadata: Dict[str, str] = {}
    for pair in pairs:
        if "=" in pair:
            key, value = pair.split("=", 1)
            metadata[key] = value

    print(f"[main] Leyendo EXIF de '{input_path}'.")
    original_exif = load_exif(input_path)
    if original_exif:
        print(f"[main] EXIF inicial contiene {len(original_exif.get('0th', {}))} entradas en 0th y {len(original_exif.get('Exif', {}))} en Exif.")

    print("[main] Aplicando metadatos personalizados...")
    apply_custom_metadata(input_path, output_path, metadata)

    print(f"[main] Releyendo EXIF desde '{output_path}'.")
    final_exif = load_exif(output_path)
    if final_exif:
        print(f"[main] EXIF final contiene {len(final_exif.get('0th', {}))} entradas en 0th y {len(final_exif.get('Exif', {}))} en Exif.")
        print("[main] Guardado completado con EXIF.")
    else:
        print("[main] No se pudo guardar EXIF en la imagen resultante.")
