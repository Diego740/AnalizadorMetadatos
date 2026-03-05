"""
Ingeniería de características para la detección de anomalías.

Transforma el diccionario de metadatos que devuelve extract_metadata_auto()
en un vector numérico que pueda consumir el modelo de Isolation Forest.
Cada feature captura un aspecto estructural del archivo que podría delatar
ofuscación, esteganografía o inyección.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List

import numpy as np

# Reutilizamos el mapa extensión→MIME de utils
try:
    from utils.mime_tools import EXTENSIONES_MIME
except ImportError:
    from src.utils.mime_tools import EXTENSIONES_MIME


# --- Creadores/herramientas sospechosas ---

# Si alguno de estos aparece (como subcadena, sin importar mayúsculas)
# en los campos de autoría del archivo, levantamos la flag.
_CREADORES_SOSPECHOSOS: List[str] = [
    "metasploit",
    "cobalt strike",
    "empire",
    "msfvenom",
    "burp",
    "set toolkit",
    "beef",
    "mimikatz",
    "nmap",
    "hydra",
]


# --- Utilidades internas ---

def _contar_campos(diccionario: Any, profundidad_max: int = 5) -> int:
    """Cuenta recursivamente todas las claves de un dict anidado."""
    if not isinstance(diccionario, dict) or profundidad_max <= 0:
        return 0

    total = len(diccionario)
    for valor in diccionario.values():
        if isinstance(valor, dict):
            total += _contar_campos(valor, profundidad_max - 1)
    return total


def _obtener_valores_string(diccionario: Any, profundidad_max: int = 5) -> List[str]:
    """Recopila todos los valores de tipo str de un dict anidado."""
    valores: List[str] = []
    if not isinstance(diccionario, dict) or profundidad_max <= 0:
        return valores

    for valor in diccionario.values():
        if isinstance(valor, str):
            valores.append(valor)
        elif isinstance(valor, dict):
            valores.extend(_obtener_valores_string(valor, profundidad_max - 1))
    return valores


def _calcular_entropia_shannon(texto: str) -> float:
    """
    Calcula la entropía de Shannon (en bits) de una cadena.
    Texto normal suele dar ~3.5-4.0; Base64/cifrado sube a ~4.5-6.0.
    Un valor alto en campos de metadatos sugiere payloads ocultos.
    """
    if not texto:
        return 0.0

    conteo = Counter(texto)
    longitud = len(texto)
    entropia = 0.0
    for frecuencia in conteo.values():
        probabilidad = frecuencia / longitud
        if probabilidad > 0:
            entropia -= probabilidad * math.log2(probabilidad)
    return entropia


def _detectar_tipo_archivo(mime_type: str) -> tuple[float, float, float]:
    """Devuelve tres flags (is_image, is_pdf, is_docx) según el MIME."""
    mime_lower = mime_type.lower()
    is_image = 1.0 if mime_lower.startswith("image/") else 0.0
    is_pdf = 1.0 if mime_lower == "application/pdf" else 0.0
    is_docx = 1.0 if "wordprocessingml" in mime_lower or mime_lower == "application/msword" else 0.0
    return is_image, is_pdf, is_docx


def _tiene_creador_sospechoso(metadata: Dict[str, Any]) -> float:
    """Comprueba si los campos de autoría mencionan herramientas de pentesting."""
    campos_autor = ["Creator", "Producer", "author", "creator", "producer"]
    for campo in campos_autor:
        valor = metadata.get(campo, "")
        if isinstance(valor, str) and valor:
            valor_lower = valor.lower()
            for sospechoso in _CREADORES_SOSPECHOSOS:
                if sospechoso in valor_lower:
                    return 1.0
    return 0.0


# --- Extracción principal ---

def extraer_caracteristicas(resultado: Dict[str, Any]) -> np.ndarray:
    """
    Recibe el dict completo de extract_metadata_auto() y devuelve un array
    de 13 features numéricas/binarias listas para el modelo.

    Features:
      0. metadata_count           - Nº total de campos en los metadatos
      1. has_gps                  - ¿Tiene datos de geolocalización?
      2. has_macros               - ¿Contiene macros VBA?
      3. is_extension_spoofed     - ¿La extensión no coincide con el MIME real?
      4. has_suspicious_patterns  - ¿El análisis heurístico encontró algo?
      5. avg_value_length         - Longitud media de los valores string
      6. long_value_ratio         - Proporción de strings excesivamente largos
      7. is_image                 - ¿Es una imagen?
      8. is_pdf                   - ¿Es un PDF?
      9. is_docx                  - ¿Es un DOCX?
     10. entropy_score            - Entropía de Shannon de los valores string
     11. has_embedded_objects      - ¿Tiene objetos OLE incrustados?
     12. unusual_creator          - ¿El creador es una herramienta sospechosa?
    """
    metadata: Dict[str, Any] = resultado.get("metadata", {})
    security: Dict[str, Any] = resultado.get("security_analysis", {})
    extension: str = resultado.get("extension", "")
    mime_type: str = resultado.get("mime_type", "")

    # Número total de campos
    metadata_count: int = _contar_campos(metadata)

    # ¿Tiene GPS?
    claves_gps = {"GPS", "GPS_Latitude", "GPS_Longitude"}
    has_gps: float = 1.0 if claves_gps.intersection(metadata.keys()) else 0.0

    # ¿Tiene macros VBA? (lo sacamos de los indicadores de seguridad)
    indicadores: List[str] = security.get("indicators", [])
    has_macros: float = 1.0 if any(
        "macros vba" in ind.lower() for ind in indicadores
    ) else 0.0

    # ¿La extensión está suplantada?
    #   - Sin extensión pero con MIME detectado → sospechoso
    #   - Extensión conocida pero no coincide con MIME → suplantado
    #   - Extensión desconocida → no podemos validar, asumimos OK
    if not extension or extension == ".":
        is_extension_spoofed: float = 1.0 if mime_type and mime_type != "application/octet-stream" else 0.0
    else:
        mime_esperado = EXTENSIONES_MIME.get(extension.lower())
        if mime_esperado is not None:
            is_extension_spoofed = 0.0 if mime_esperado == mime_type else 1.0
        else:
            is_extension_spoofed = 0.0

    # ¿La heurística encontró patrones sospechosos?
    has_suspicious_patterns: float = 1.0 if security.get("is_suspicious", False) else 0.0

    # Estadísticas de longitud de los valores string
    valores_str = _obtener_valores_string(metadata)
    if valores_str:
        longitudes = [len(v) for v in valores_str]
        avg_value_length: float = float(np.mean(longitudes))
        long_value_ratio: float = sum(1 for l in longitudes if l > 500) / len(longitudes)
    else:
        avg_value_length = 0.0
        long_value_ratio = 0.0

    # Tipo de archivo (para que el modelo entienda que una imagen con
    # muchos campos EXIF es normal, pero un PDF con 70 campos no lo es)
    is_image, is_pdf, is_docx = _detectar_tipo_archivo(mime_type)

    # Entropía de Shannon sobre todos los valores string concatenados
    texto_concatenado = " ".join(valores_str)
    entropy_score: float = _calcular_entropia_shannon(texto_concatenado)

    # ¿Tiene objetos OLE incrustados?
    has_embedded_objects: float = 1.0 if any(
        "ole" in ind.lower() or "incrustado" in ind.lower()
        for ind in indicadores
    ) else 0.0

    # ¿El creador es sospechoso?
    unusual_creator: float = _tiene_creador_sospechoso(metadata)

    # Montamos el vector final
    vector = np.array([
        float(metadata_count),
        has_gps,
        has_macros,
        is_extension_spoofed,
        has_suspicious_patterns,
        avg_value_length,
        long_value_ratio,
        is_image,
        is_pdf,
        is_docx,
        entropy_score,
        has_embedded_objects,
        unusual_creator,
    ], dtype=np.float64)

    return vector


# Nombres de las features en orden (útil para depuración y para la GUI)
NOMBRES_FEATURES: List[str] = [
    "metadata_count",
    "has_gps",
    "has_macros",
    "is_extension_spoofed",
    "has_suspicious_patterns",
    "avg_value_length",
    "long_value_ratio",
    "is_image",
    "is_pdf",
    "is_docx",
    "entropy_score",
    "has_embedded_objects",
    "unusual_creator",
]
