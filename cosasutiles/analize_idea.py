import os
import sys
import json
from pathlib import Path
from utils import archivo_existe
import magic

# Librerías externas específicas para metadatos
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from PyPDF2 import PdfReader
from docx import Document
import zipfile

# ============================================================
# FUNCIONES PRINCIPALES
# ============================================================

def extraer_metadatos(ruta_archivo):
    """
    Extrae los metadatos del archivo en función de su tipo MIME.

    Args:
        ruta_archivo (str): Ruta completa al archivo.

    Returns:
        dict: Diccionario con los metadatos extraídos.
    """
    if not archivo_existe(ruta_archivo):
        raise FileNotFoundError(f"El archivo '{ruta_archivo}' no existe.")

    mime = magic.from_file(ruta_archivo, mime=True)
    extension = Path(ruta_archivo).suffix.lower()

    metadatos = {
        "archivo": os.path.basename(ruta_archivo),
        "ruta": str(Path(ruta_archivo).resolve()),
        "tipo_mime": mime,
        "extension": extension,
        "metadatos_extraidos": {}
    }

    try:
        # Archivos de imagen
        if mime.startswith("image/"):
            metadatos["metadatos_extraidos"] = extraer_metadatos_imagen(ruta_archivo)

        # Archivos PDF
        elif mime == "application/pdf":
            metadatos["metadatos_extraidos"] = extraer_metadatos_pdf(ruta_archivo)

        # Documentos Word
        elif mime in [
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]:
            metadatos["metadatos_extraidos"] = extraer_metadatos_docx(ruta_archivo)

        # Archivos ZIP o RAR
        elif mime in ["application/zip", "application/x-rar-compressed"]:
            metadatos["metadatos_extraidos"] = extraer_metadatos_zip(ruta_archivo)

        # Archivos de texto plano
        elif mime.startswith("text/"):
            metadatos["metadatos_extraidos"] = {
                "tamaño_bytes": os.path.getsize(ruta_archivo)
            }

        else:
            metadatos["metadatos_extraidos"] = {
                "info": "Formato no soportado o sin metadatos legibles"
            }

    except Exception as e:
        metadatos["error"] = str(e)

    return metadatos


# ============================================================
# EXTRACCIÓN SEGÚN FORMATO
# ============================================================

def extraer_metadatos_imagen(ruta_archivo):
    """Extrae metadatos EXIF y convierte coordenadas GPS si están disponibles."""
    datos = {}
    try:
        with Image.open(ruta_archivo) as img:
            exif_data = img.getexif()

            if not exif_data:
                return {"info": "No se encontraron metadatos EXIF"}

            for tag_id, valor in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)

                # Si es información GPS, comprobamos su tipo
                if tag == "GPSInfo":
                    if isinstance(valor, dict):  # ✅ solo si es un diccionario real
                        gps_info = {}
                        for t in valor:
                            sub_tag = GPSTAGS.get(t, t)
                            gps_info[sub_tag] = valor[t]
                        datos["GPSInfo"] = gps_info

                        # Intentamos convertir coordenadas
                        coords = convertir_gps_a_decimales(gps_info)
                        if coords:
                            datos["GPS_Latitud"] = coords["latitud"]
                            datos["GPS_Longitud"] = coords["longitud"]
                    else:
                        # Si solo hay un número (puntero), lo guardamos tal cual
                        datos["GPSInfo"] = valor
                else:
                    datos[tag] = str(valor)

    except Exception as e:
        datos["error"] = f"No se pudieron leer metadatos EXIF: {e}"
    return datos


def convertir_gps_a_decimales(gps_info):
    """
    Convierte datos EXIF GPSInfo a coordenadas decimales.
    """
    try:
        def convertir_coordenada(valor):
            grados = valor[0][0] / valor[0][1]
            minutos = valor[1][0] / valor[1][1]
            segundos = valor[2][0] / valor[2][1]
            return grados + (minutos / 60.0) + (segundos / 3600.0)

        lat = convertir_coordenada(gps_info[2])
        lon = convertir_coordenada(gps_info[4])

        if gps_info[1] == 'S':
            lat = -lat
        if gps_info[3] == 'W':
            lon = -lon

        return {"latitud": lat, "longitud": lon}

    except Exception:
        return None


def extraer_metadatos_pdf(ruta_archivo):
    """Extrae metadatos de archivos PDF."""
    datos = {}
    try:
        with open(ruta_archivo, "rb") as f:
            reader = PdfReader(f)
            info = reader.metadata
            if info:
                for clave, valor in info.items():
                    datos[clave.strip("/")] = str(valor)
            else:
                datos["info"] = "El PDF no contiene metadatos."
    except Exception as e:
        datos["error"] = f"No se pudieron leer metadatos PDF: {e}"
    return datos


def extraer_metadatos_docx(ruta_archivo):
    """Extrae metadatos de archivos DOCX (Microsoft Word)."""
    datos = {}
    try:
        doc = Document(ruta_archivo)
        prop = doc.core_properties
        datos = {
            "autor": prop.author,
            "titulo": prop.title,
            "asunto": prop.subject,
            "creado": str(prop.created),
            "modificado": str(prop.modified),
            "ultima_impresion": str(prop.last_printed),
        }
    except Exception as e:
        datos["error"] = f"No se pudieron leer metadatos DOCX: {e}"
    return datos


def extraer_metadatos_zip(ruta_archivo):
    """Extrae información básica de archivos ZIP (contenido y tamaño)."""
    datos = {}
    try:
        with zipfile.ZipFile(ruta_archivo, "r") as zipf:
            datos["num_archivos"] = len(zipf.namelist())
            datos["nombres"] = zipf.namelist()[:10]  # mostramos los primeros 10
    except Exception as e:
        datos["error"] = f"No se pudieron leer metadatos ZIP: {e}"
    return datos


# ============================================================
# VISUALIZACIÓN
# ============================================================

def mostrar_metadatos(metadatos):
    """Muestra los metadatos en formato legible por consola."""
    print(json.dumps(metadatos, indent=4, ensure_ascii=False))


# ============================================================
# MAIN PARA PRUEBAS MANUALES
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python analyze_metadata.py <ruta_del_archivo>")
    else:
        ruta = sys.argv[1]
        try:
            resultado = extraer_metadatos(ruta)
            mostrar_metadatos(resultado)
        except Exception as e:
            print(f"Error: {e}")
