"""
Módulo de heurística de seguridad.
Contiene la lógica para detectar patrones sospechosos en metadatos y estructuras de archivos.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# --- Constantes y Patrones ---

# Patrones de cadenas sospechosas en metadatos (texto)
SUSPICIOUS_METADATA_PATTERNS = [
    (r"<script.*?>", "Posible inyección de script HTML"),
    (r"javascript:", "Posible esquema URI de JavaScript"),
    (r"eval\(", "Uso de eval() (ejecución de código dinámico)"),
    (r"base64_decode", "Decodificación Base64 (común en obfuscación)"),
    (r"cmd\.exe", "Referencia a línea de comandos de Windows"),
    (r"powershell", "Referencia a PowerShell"),
    (r"/bin/sh", "Referencia a shell de Unix"),
    (r"auto_open", "Macro de auto-ejecución (Office)"),
    (r"Document_Open", "Macro de auto-ejecución (Office)"),
]

# Palabras clave sospechosas en estructura PDF (bytes)
PDF_THREAT_KEYWORDS = {
    b"/JavaScript": "Contiene código JavaScript",
    b"/JS": "Contiene código JavaScript",
    b"/OpenAction": "Ejecuta una acción al abrir el documento",
    #b"/AA": "Contiene acciones automáticas (AutoAction)", # Revisar porque da muchos falsos positivos
    b"/Launch": "Intenta lanzar un programa externo",
    b"/RichMedia": "Contenido multimedia enriquecido (posible vector de ataque)",
}


# --- Funciones de Análisis ---

def check_metadata_risk(metadata: Dict[str, Any]) -> List[str]:
    """
    Escanea recursivamente los valores de los metadatos en busca de patrones sospechosos.
    """
    indicators = []

    def recursive_scan(value: Any, path: str = ""):
        if isinstance(value, dict):
            for k, v in value.items():
                recursive_scan(v, f"{path}.{k}" if path else k)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                recursive_scan(v, f"{path}[{i}]")
        elif isinstance(value, str):
            # Comprobación de longitud excesiva (posible buffer overflow o payload oculto)
            # 5000 es un límite arbitrario pero razonable para metadatos normales
            if len(value) > 5000:
                indicators.append(f"Valor inusualmente largo en '{path}' ({len(value)} caracteres)")

            # Comprobación de patrones regex
            for pattern, desc in SUSPICIOUS_METADATA_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    indicators.append(f"Detectado '{desc}' en '{path}'")

    recursive_scan(metadata)
    return indicators


def check_file_risk(file_path: Path, mime_type: str) -> List[str]:
    """
    Analiza la estructura del archivo en busca de amenazas específicas del formato.
    """
    indicators = []
    
    try:
        if mime_type == "application/pdf":
            indicators.extend(scan_pdf_structure(file_path))
            
        elif mime_type in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # docx
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",      # xlsx
            "application/vnd.openxmlformats-officedocument.presentationml.presentation" # pptx
        ):
            indicators.extend(scan_office_structure(file_path))
            
    except Exception as e:
        indicators.append(f"Error al analizar estructura del archivo: {e}")
        
    return indicators


def scan_pdf_structure(file_path: Path) -> List[str]:
    """Escaneo básico de estructura PDF."""
    indicators = []
    try:
        with open(file_path, "rb") as f:
            content = f.read()
            
        # Comprobación de falsos positivos comunes (ej. jsPDF)
        # jsPDF a menudo incluye referencias a /OpenAction o /JavaScript por defecto
        if b"jsPDF" in content:
             # Si es jsPDF, somos más permisivos, solo alertamos si hay código JS explícito
             # que parezca malicioso, no solo la presencia de la etiqueta.
             pass

        for keyword, desc in PDF_THREAT_KEYWORDS.items():
            if keyword in content:
                # Refinamiento: /OpenAction es muy común en PDFs legítimos para ajustar el zoom inicial.
                # Solo lo marcamos si NO parece ser una configuración de vista estándar.
                if keyword == b"/OpenAction":
                    # Buscamos si es una acción de JavaScript o Launch
                    # Si solo es un diccionario de vista (ej. /Fit), lo ignoramos (simplificado)
                    # Como es un escaneo de bytes crudos, es difícil saber el contexto exacto sin parsear.
                    # Estrategia: Si encontramos /OpenAction Y (/JavaScript o /Launch), entonces es sospechoso.
                    # Si está solo, podría ser benigno.
                    
                    # Para reducir ruido, solo reportamos OpenAction si también detectamos JS o Launch
                    if b"/JavaScript" in content or b"/JS" in content or b"/Launch" in content:
                         indicators.append(f"Estructura PDF sospechosa: {desc} combinada con scripts/lanzadores")
                else:
                    indicators.append(f"Estructura PDF sospechosa: {desc} ({keyword.decode()})")
                    
    except Exception:
        pass # Errores de lectura se manejan arriba
    return list(set(indicators)) # Eliminar duplicados


def scan_office_structure(file_path: Path) -> List[str]:
    """Escaneo de estructura Office (ZIP)."""
    indicators = []
    try:
        if not zipfile.is_zipfile(file_path):
            return []

        with zipfile.ZipFile(file_path, 'r') as zf:
            file_names = zf.namelist()
            
            # Detección de Macros VBA
            if any(name.endswith("vbaProject.bin") for name in file_names):
                indicators.append("Contiene Macros VBA (vbaProject.bin)")
            
            # Detección de objetos OLE
            ole_files = [f for f in file_names if "embeddings/oleObject" in f]
            if ole_files:
                indicators.append(f"Contiene {len(ole_files)} objeto(s) OLE incrustado(s)")
    except Exception:
        pass
    return indicators


# --- Punto de Entrada Principal ---

def analyze_risk(file_path: Path, metadata: Dict[str, Any], mime_type: str) -> Dict[str, Any]:
    """
    Realiza un análisis de seguridad completo (metadatos + estructura).
    Devuelve un diccionario con los hallazgos.
    """
    findings = []
    
    # 1. Analizar metadatos extraídos
    findings.extend(check_metadata_risk(metadata))
    
    # 2. Analizar estructura del archivo
    findings.extend(check_file_risk(file_path, mime_type))
    
    return {
        "is_suspicious": len(findings) > 0,
        "indicators": findings
    }
