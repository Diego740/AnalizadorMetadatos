from __future__ import annotations

from typing import Dict

from core.analyze_metadata import extract_metadata_auto, format_metadata
from core.detect_extension import (
    extension_matches_mime,
    get_mime_type,
    suggest_correct_extension,
)
from core.file_loader import load_file_info
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

# Menú principal de la aplicación
MAIN_MENU = """
=== Metadata Analyzer Tool ===

1. Analyze file metadata
2. Verify file extension consistency
3. Wipe all metadata
4. Apply default metadata templates
5. Set custom metadata fields
6. Exit

Select an option > """


def get_file_path() -> str:
    """Pide al usuario la ruta del archivo y limpia la entrada."""
    return input("Please enter the file path: ").strip()


def analyze_metadata_flow() -> None:
    """Maneja el flujo de análisis de metadatos."""
    path = get_file_path()
    try:
        # Extrae los metadatos y los muestra con formato
        results = extract_metadata_auto(path)
        print("\n--- Analysis Results ---")
        print(format_metadata(results))
        print("------------------------\n")
    except FileNotFoundError as e:
        print(f"Oops, couldn't find that file: {e}")


def verify_extension_flow() -> None:
    """Comprueba si la extensión del archivo coincide con su contenido real."""
    path = get_file_path()
    try:
        mime_type = get_mime_type(path)
        is_match = extension_matches_mime(path)
        suggestion = suggest_correct_extension(path)

        print(f"\nDetected MIME type: {mime_type}")
        print(f"Extension matches content? {'Yes' if is_match else 'No'}")
        
        if not is_match and suggestion:
            print(f"Tip: It looks like this file should be a {suggestion}")
        print()
            
    except FileNotFoundError as e:
        print(f"Error: {e}")


def wipe_metadata_flow() -> None:
    """Elimina los metadatos de los tipos de archivo soportados."""
    path = get_file_path()
    try:
        file_info = load_file_info(path)
        file_type = file_info["type"]
        
        new_path = None
        if file_type == "pdf":
            new_path = wipe_metadata_pdf(path)
        elif file_type == "docx":
            new_path = wipe_metadata_docx(path)
        elif file_type == "image":
            new_path = wipe_metadata_image(path)
        else:
            print("Sorry, we don't support wiping metadata for this file type yet.")
            return

        print(f"Success! Clean file saved to: {new_path}")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")


def apply_default_metadata_flow() -> None:
    """Aplica un conjunto estándar de metadatos al archivo."""
    path = get_file_path()
    try:
        file_info = load_file_info(path)
        file_type = file_info["type"]
        
        new_path = None
        if file_type == "pdf":
            new_path = apply_default_pdf_metadata(path)
        elif file_type == "docx":
            new_path = apply_default_docx_metadata(path)
        elif file_type == "image":
            new_path = apply_default_image_metadata(path)
        else:
            print("Unsupported file format for default metadata.")
            return

        print(f"Done. File with default metadata created at: {new_path}")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")


def get_custom_metadata_input() -> Dict[str, str]:
    """Procesa la entrada del usuario para campos de metadatos personalizados."""
    print("\nEnter metadata as key=value pairs (separated by commas).")
    print("Example: author=Jane Doe, title=Final Report")
    raw_input = input("> ").strip()
    
    parsed_data: Dict[str, str] = {}
    if not raw_input:
        return parsed_data

    # Divide por comas y luego por el signo igual
    for item in raw_input.split(','):
        if '=' in item:
            key, value = item.split('=', 1)
            parsed_data[key.strip()] = value.strip()
            
    return parsed_data


def apply_custom_metadata_flow() -> None:
    """Permite al usuario establecer campos de metadatos específicos."""
    path = get_file_path()
    metadata = get_custom_metadata_input()
    
    if not metadata:
        print("No metadata provided. Aborting.")
        return

    try:
        file_info = load_file_info(path)
        file_type = file_info["type"]
        
        new_path = None
        if file_type == "pdf":
            new_path = apply_custom_pdf_metadata(path, metadata)
        elif file_type == "docx":
            new_path = apply_custom_docx_metadata(path, metadata)
        elif file_type == "image":
            new_path = apply_custom_image_metadata(path, metadata)
        else:
            print("Unsupported file format.")
            return

        print(f"Custom metadata applied! Saved to: {new_path}")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")


def run_cli() -> None:
    """Bucle principal de la aplicación en modo consola."""
    menu_options = {
        "1": analyze_metadata_flow,
        "2": verify_extension_flow,
        "3": wipe_metadata_flow,
        "4": apply_default_metadata_flow,
        "5": apply_custom_metadata_flow,
    }
    
    while True:
        user_choice = input(MAIN_MENU).strip()
        
        if user_choice == "6":
            print("See you later!")
            break
            
        action = menu_options.get(user_choice)
        if action:
            action()
        else:
            print("Invalid selection, please try again.")


def run_gui() -> None:
    """Inicia la aplicación en modo gráfico (GUI)."""
    try:
        # Importación local para evitar dependencias circulares o errores si no hay GUI
        from gui.main_window import MetadataAnalyzerApp
        app = MetadataAnalyzerApp()
        app.mainloop()
    except ImportError as e:
        print(f"Error launching GUI: {e}")
        print("Make sure you have all dependencies installed.")


def main() -> None:
    """Punto de entrada principal que procesa argumentos."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Metadata Analyzer Tool")
    parser.add_argument("-g", "--gui", action="store_true", help="Launch the Graphical User Interface")
    
    args = parser.parse_args()
    
    if args.gui:
        run_gui()
    else:
        run_cli()


if __name__ == "__main__":
    main()

