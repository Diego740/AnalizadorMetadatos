import os
import sys
import json
from pathlib import Path
from utils import archivo_existe
import magic

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from PyPDF2 import PdfReader
from docx import Document
import zipfile

from pillow_heif import register_heif_opener
import piexif

# Habilita lectura HEIC/HEIF en Pillow
register_heif_opener()


# ===============================================================
# CONVERSIÓN JSON SAFE
# ===============================================================

def to_json_safe(value):
    """Convierte cualquier valor EXIF a algo JSON-serializable."""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", "ignore")
        except:
            return str(value)

    if isinstance(value, tuple):
        return tuple(to_json_safe(v) for v in value)

    if isinstance(value, list):
        return [to_json_safe(v) for v in value]

    if isinstance(value, dict):
        return {to_json_safe(k): to_json_safe(v) for k, v in value.items()}

    return value


# ===============================================================
# EXTRACCIÓN GENERAL
# ===============================================================

def extraer_metadatos(ruta_archivo):
    """Detecta tipo MIME y delega al extractor adecuado."""
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
        match mime:

            case m if m.startswith("image/"):
                metadatos["metadatos_extraidos"] = extraer_metadatos_imagen(ruta_archivo)

            case "application/pdf":
                metadatos["metadatos_extraidos"] = extraer_metadatos_pdf(ruta_archivo)

            case "application/msword" | "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                metadatos["metadatos_extraidos"] = extraer_metadatos_docx(ruta_archivo)

            case "application/zip" | "application/x-rar-compressed":
                metadatos["metadatos_extraidos"] = extraer_metadatos_zip(ruta_archivo)

            case m if m.startswith("text/"):
                metadatos["metadatos_extraidos"] = {
                    "tamaño_bytes": os.path.getsize(ruta_archivo)
                }

            case _:
                metadatos["metadatos_extraidos"] = {
                    "info": "Formato no soportado o sin metadatos legibles"
                }

    except Exception as e:
        metadatos["error"] = str(e)

    return metadatos


# ===============================================================
# EXTRACCIÓN EXIF DE IMÁGENES
# ===============================================================

def extraer_metadatos_imagen(ruta_archivo):
    """Extrae EXIF real compatible con JPEG, HEIC, MPO y Apple."""
    datos = {}

    try:
        img = Image.open(ruta_archivo)
        datos["Formato"] = img.format

        # EXIF RAW (más fiable en Apple/HEIC/JPEG)
        exif_bytes = img.info.get("exif")

        if exif_bytes:
            exif_dict = piexif.load(exif_bytes)

            for ifd_name in exif_dict:
                if isinstance(exif_dict[ifd_name], dict):
                    for tag_id, value in exif_dict[ifd_name].items():

                        try:
                            tag_name = piexif.TAGS[ifd_name][tag_id]["name"]
                        except:
                            tag_name = f"{ifd_name}-{tag_id}"

                        # GPS
                        if ifd_name == "GPS":
                            gps_raw = {
                                piexif.TAGS["GPS"][t]["name"]: exif_dict["GPS"][t]
                                for t in exif_dict["GPS"]
                            }
                            datos["GPSInfo"] = to_json_safe(gps_raw)

                            coords = convertir_gps_a_decimales(exif_dict["GPS"])
                            if coords:
                                datos["GPS_Latitud"] = coords["latitud"]
                                datos["GPS_Longitud"] = coords["longitud"]

                        else:
                            datos[tag_name] = to_json_safe(value)

            return datos

        # Fallback → PIL
        exif = img.getexif()
        if exif:
            for tag_id, value in exif.items():
                datos[TAGS.get(tag_id, tag_id)] = to_json_safe(value)
            return datos

        datos["info"] = "No se encontraron metadatos EXIF."

    except Exception as e:
        datos["error"] = f"Error al leer metadatos: {e}"

    return datos


def convertir_gps_a_decimales(gps_info):
    """Convierte datos EXIF GPS a coordenadas decimales."""
    try:
        def convertir(valor):
            grados = valor[0][0] / valor[0][1]
            minutos = valor[1][0] / valor[1][1]
            segundos = valor[2][0] / valor[2][1]
            return grados + minutos/60 + segundos/3600

        lat = convertir(gps_info[2])
        lon = convertir(gps_info[4])

        if gps_info[1] == b'S' or gps_info[1] == 'S':
            lat = -lat
        if gps_info[3] == b'W' or gps_info[3] == 'W':
            lon = -lon

        return {"latitud": lat, "longitud": lon}

    except:
        return None


# ===============================================================
# EXTRACCIÓN PDF
# ===============================================================

def extraer_metadatos_pdf(ruta_archivo):
    datos = {}
    try:
        with open(ruta_archivo, "rb") as f:
            info = PdfReader(f).metadata
            if info:
                for k, v in info.items():
                    datos[k.strip("/")] = str(v)
            else:
                datos["info"] = "El PDF no contiene metadatos."
    except Exception as e:
        datos["error"] = f"No se pudieron leer metadatos PDF: {e}"
    return datos


# ===============================================================
# EXTRACCIÓN DOCX
# ===============================================================

def extraer_metadatos_docx(ruta_archivo):
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


# ===============================================================
# EXTRACCIÓN ZIP
# ===============================================================

def extraer_metadatos_zip(ruta_archivo):
    datos = {}
    try:
        with zipfile.ZipFile(ruta_archivo, "r") as zipf:
            datos["num_archivos"] = len(zipf.namelist())
            datos["nombres"] = zipf.namelist()[:10]
    except Exception as e:
        datos["error"] = f"No se pudieron leer metadatos ZIP: {e}"
    return datos


# ===============================================================
# AGRUPACIÓN PARA SALIDA JSON LEGIBLE
# ===============================================================

def organizar_metadatos(metadatos):
    """Reestructura los metadatos en un JSON mucho más legible."""

    datos = metadatos.get("metadatos_extraidos", {})
    salida = {
        "general": {
            "archivo": metadatos.get("archivo"),
            "ruta": metadatos.get("ruta"),
            "tipo_mime": metadatos.get("tipo_mime"),
            "extension": metadatos.get("extension"),
            "formato_imagen": datos.get("Formato"),
            "fabricante": datos.get("Make"),
            "modelo": datos.get("Model"),
            "software": datos.get("Software"),
            "fecha": datos.get("DateTime")
        },
        "gps": {},
        "camara": {},
        "exif": {}
    }

    # GPS
    lat = datos.get("GPS_Latitud")
    lon = datos.get("GPS_Longitud")

    if lat and lon:
        salida["gps"] = {
            "latitud": lat,
            "longitud": lon,
            "maps_url": f"https://maps.google.com/?q={lat},{lon}",
            "gps_raw": datos.get("GPSInfo", {})
        }
    elif datos.get("GPSInfo"):
        salida["gps"] = {"gps_raw": datos["GPSInfo"]}

    # Cámara
    claves_camara = [
        "ExposureTime", "FNumber", "ExposureProgram",
        "ISOSpeedRatings", "ShutterSpeedValue",
        "ApertureValue", "FocalLength",
        "FocalLengthIn35mmFilm", "LensModel"
    ]

    for clave in claves_camara:
        if clave in datos:
            salida["camara"][clave] = datos[clave]

    # EXIF resto (sin MakerNote)
    for k, v in datos.items():
        if k != "MakerNote" and \
           k not in salida["general"].values() and \
           k not in salida["gps"] and \
           not k in salida["camara"]:

            if k not in ("GPSInfo", "GPS_Latitud", "GPS_Longitud"):
                salida["exif"][k] = v

    return salida


# ===============================================================
# MOSTRAR RESULTADO
# ===============================================================

def mostrar_metadatos(metadatos):
    """Muestra los metadatos en formato JSON agrupado y legible."""
    datos_limpios = organizar_metadatos(metadatos)
    print(json.dumps(datos_limpios, indent=4, ensure_ascii=False))


# ===============================================================
# MAIN
# ===============================================================

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