"""Simple CLI entry-point for the metadata toolkit."""
from __future__ import annotations

from typing import Dict

from core.analyze_metadata import extract_metadata_auto, format_metadata
from core.detect_extension import (
    extension_matches_mime,
    get_mime_type,
    suggest_correct_extension,
)
from core.file_loader import load_file
from core.modify_metadata.custom_metadata import (
    apply_custom_docx_metadata,
    apply_custom_image_metadata,
    apply_custom_pdf_metadata,
)
from core.modify_metadata.default_metadata import (
    apply_default_docx_metadata,
    apply_default_image_metadata,
    apply_default_pdf_metadata,
)
from core.modify_metadata.wipe_metadata import (
    wipe_metadata_docx,
    wipe_metadata_image,
    wipe_metadata_pdf,
)
from utils.path_autocomplete import enable_autocomplete

MENU = """\nSeleccione una opción:\n1. Analizar metadatos\n2. Verificar extensión/MIME\n3. Borrar metadatos\n4. Asignar metadatos por defecto\n5. Modificar metadatos personalizados\n6. Salir\n> """


def _prompt_path() -> str:
    return input("Ruta del archivo: ").strip()


def _handle_analyze() -> None:
    path = _prompt_path()
    try:
        data = extract_metadata_auto(path)
        print(format_metadata(data))
    except FileNotFoundError as exc:
        print(exc)


def _handle_verify_extension() -> None:
    path = _prompt_path()
    try:
        mime = get_mime_type(path)
        matches = extension_matches_mime(path)
        suggestion = suggest_correct_extension(path)
        print(f"Tipo MIME detectado: {mime}")
        print(f"¿Coincide la extensión?: {'Sí' if matches else 'No'}")
        if not matches and suggestion:
            print(f"Extensión sugerida: {suggestion}")
    except FileNotFoundError as exc:
        print(exc)


def _handle_wipe_metadata() -> None:
    path = _prompt_path()
    try:
        info = load_file(path)
        if info["type"] == "pdf":
            new_path = wipe_metadata_pdf(path)
        elif info["type"] == "docx":
            new_path = wipe_metadata_docx(path)
        elif info["type"] == "image":
            new_path = wipe_metadata_image(path)
        else:
            print("Formato no soportado.")
            return
        print(f"Metadatos eliminados. Archivo generado: {new_path}")
    except FileNotFoundError as exc:
        print(exc)


def _handle_default_metadata() -> None:
    path = _prompt_path()
    try:
        info = load_file(path)
        if info["type"] == "pdf":
            new_path = apply_default_pdf_metadata(path)
        elif info["type"] == "docx":
            new_path = apply_default_docx_metadata(path)
        elif info["type"] == "image":
            new_path = apply_default_image_metadata(path)
        else:
            print("Formato no soportado.")
            return
        print(f"Metadatos por defecto aplicados. Archivo generado: {new_path}")
    except FileNotFoundError as exc:
        print(exc)


def _prompt_metadata_dict() -> Dict[str, str]:
    print("Ingrese pares clave=valor separados por coma. Ejemplo: autor=Juan, titulo=Reporte")
    raw = input("> ").strip()
    result: Dict[str, str] = {}
    for pair in raw.split(','):
        if '=' in pair:
            key, value = pair.split('=', 1)
            result[key.strip()] = value.strip()
    return result


def _handle_custom_metadata() -> None:
    path = _prompt_path()
    metadata = _prompt_metadata_dict()
    if not metadata:
        print("No se ingresaron metadatos válidos.")
        return
    try:
        info = load_file(path)
        if info["type"] == "pdf":
            new_path = apply_custom_pdf_metadata(path, metadata)
        elif info["type"] == "docx":
            new_path = apply_custom_docx_metadata(path, metadata)
        elif info["type"] == "image":
            new_path = apply_custom_image_metadata(path, metadata)
        else:
            print("Formato no soportado.")
            return
        print(f"Metadatos personalizados aplicados. Archivo generado: {new_path}")
    except FileNotFoundError as exc:
        print(exc)


def main() -> None:
    enable_autocomplete()
    actions = {
        "1": _handle_analyze,
        "2": _handle_verify_extension,
        "3": _handle_wipe_metadata,
        "4": _handle_default_metadata,
        "5": _handle_custom_metadata,
    }
    while True:
        choice = input(MENU).strip()
        if choice == "6":
            print("Saliendo...")
            break
        action = actions.get(choice)
        if action:
            action()
        else:
            print("Opción no válida.")


if __name__ == "__main__":
    main()
