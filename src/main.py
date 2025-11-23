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

MENU = """\nSelect an option:\n1. Analyze metadata\n2. Verify extension/MIME\n3. Wipe metadata\n4. Apply default metadata\n5. Modify custom metadata\n6. Exit\n> """


def _prompt_path() -> str:
    return input("File path: ").strip()


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
        print(f"Detected MIME type: {mime}")
        print(f"Extension matches?: {'Yes' if matches else 'No'}")
        if not matches and suggestion:
            print(f"Suggested extension: {suggestion}")
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
            print("Unsupported format.")
            return
        print(f"Metadata wiped. Generated file: {new_path}")
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
            print("Unsupported format.")
            return
        print(f"Default metadata applied. Generated file: {new_path}")
    except FileNotFoundError as exc:
        print(exc)


def _prompt_metadata_dict() -> Dict[str, str]:
    print("Enter key=value pairs separated by comma. Example: author=John, title=Report")
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
        print("No valid metadata entered.")
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
            print("Unsupported format.")
            return
        print(f"Custom metadata applied. Generated file: {new_path}")
    except FileNotFoundError as exc:
        print(exc)


def main() -> None:
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
            print("Exiting...")
            break
        action = actions.get(choice)
        if action:
            action()
        else:
            print("Invalid option.")


if __name__ == "__main__":
    main()
