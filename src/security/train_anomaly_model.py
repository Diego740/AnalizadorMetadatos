"""
Entrenamiento del modelo de detección de anomalías.

Recorre la carpeta archivosTest/ (y subcarpetas), extrae las features
de cada archivo real, genera datos sintéticos alrededor de esas muestras
para ampliar el dataset, y entrena un IsolationForest que se guarda
como modelo_riesgo.joblib.

Uso desde la raíz del proyecto:
    python -m src.security.train_anomaly_model
"""
from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib


# --- Configuración ---

_SEMILLA: int = 42
_RUTA_MODELO: Path = Path(__file__).resolve().parent / "modelo_riesgo.joblib"

# Extensiones que sabemos analizar
_EXTENSIONES_SOPORTADAS = {
    ".pdf", ".docx", ".doc",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic",
}

# Las 13 features (deben coincidir con feature_engineering.NOMBRES_FEATURES)
_NOMBRES_FEATURES = [
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


# --- Paso 1: Extracción de features de archivos reales ---

def _buscar_archivos(directorio: Path) -> List[Path]:
    """Busca recursivamente todos los archivos con extensión soportada."""
    archivos: List[Path] = []
    for ruta in directorio.rglob("*"):
        if ruta.is_file() and ruta.suffix.lower() in _EXTENSIONES_SOPORTADAS:
            if ruta.stat().st_size > 0:  # Saltamos archivos vacíos
                archivos.append(ruta)
    return archivos


def _extraer_resultado_sin_ml(file_path: Path) -> Dict[str, Any]:
    """
    Extrae metadatos y ejecuta el análisis heurístico, pero SIN invocar
    el módulo ML (para evitar dependencia circular al entrenar).
    """
    try:
        from core.analyze_metadata import (
            extract_metadata_pdf, extract_metadata_docx,
            extract_metadata_image,
        )
        from core.detect_extension import get_mime_type
        from security.heuristics import analyze_risk
        from utils.path_tools import ensure_readable_file
    except ImportError:
        from src.core.analyze_metadata import (
            extract_metadata_pdf, extract_metadata_docx,
            extract_metadata_image,
        )
        from src.core.detect_extension import get_mime_type
        from src.security.heuristics import analyze_risk
        from src.utils.path_tools import ensure_readable_file

    safe_path = ensure_readable_file(file_path)
    mime_type = get_mime_type(safe_path) or "application/octet-stream"
    extension = safe_path.suffix.lower()

    result: Dict[str, Any] = {
        "file": safe_path.name,
        "path": str(safe_path),
        "mime_type": mime_type,
        "extension": extension,
        "metadata": {},
    }

    try:
        if mime_type.startswith("image/"):
            result["metadata"] = extract_metadata_image(safe_path)
        elif mime_type == "application/pdf":
            result["metadata"] = extract_metadata_pdf(safe_path)
        elif "wordprocessingml" in mime_type or mime_type == "application/msword":
            result["metadata"] = extract_metadata_docx(safe_path)
        else:
            result["metadata"] = {"info": "Formato no soportado."}

        # Solo heurística, nada de ML aquí
        security_report = analyze_risk(safe_path, result["metadata"], mime_type)
        if security_report["is_suspicious"]:
            result["security_analysis"] = security_report

    except Exception as e:
        result["metadata"] = {"error": str(e)}

    return result


def _extraer_features_reales(directorio: Path) -> Tuple[np.ndarray, List[str]]:
    """
    Recorre el directorio, analiza cada archivo y devuelve la matriz de
    features junto con los nombres de archivo procesados.
    """
    try:
        from security.feature_engineering import extraer_caracteristicas
    except ImportError:
        from src.security.feature_engineering import extraer_caracteristicas

    archivos = _buscar_archivos(directorio)
    vectores: List[np.ndarray] = []
    nombres: List[str] = []

    for archivo in archivos:
        try:
            resultado = _extraer_resultado_sin_ml(archivo)
            vector = extraer_caracteristicas(resultado)
            vectores.append(vector)
            nombres.append(archivo.name)
        except Exception as e:
            print(f"    ⚠ Error procesando {archivo.name}: {e}")

    if vectores:
        X = np.vstack(vectores)
    else:
        X = np.empty((0, len(_NOMBRES_FEATURES)))

    return X, nombres


# --- Paso 2: Generación de datos sintéticos ---

def _generar_sinteticos_desde_reales(
    X_real: np.ndarray,
    factor: int = 10,
    semilla: int = _SEMILLA,
) -> np.ndarray:
    """
    Crea copias de las muestras reales con ruido gaussiano ligero (15% de
    la desviación típica). Así ampliamos el dataset sin inventarnos
    distribuciones artificiales.
    """
    if X_real.shape[0] == 0:
        return np.empty((0, len(_NOMBRES_FEATURES)))

    rng = np.random.default_rng(semilla)

    # Desviación por feature (mínimo 0.1 para que siempre haya algo de ruido)
    std = np.maximum(np.std(X_real, axis=0), 0.1)

    sinteticos: List[np.ndarray] = []
    for _ in range(factor):
        ruido = rng.normal(0, std * 0.15, size=X_real.shape)
        copia = X_real + ruido

        # Las features binarias tienen que seguir siendo 0 o 1
        indices_binarios = [1, 2, 3, 4, 7, 8, 9, 11, 12]
        for idx in indices_binarios:
            copia[:, idx] = np.round(np.clip(copia[:, idx], 0, 1))

        # Acotamos valores que no pueden ser negativos
        copia[:, 0] = np.clip(copia[:, 0], 1, None)    # metadata_count ≥ 1
        copia[:, 5] = np.clip(copia[:, 5], 0, None)    # avg_value_length ≥ 0
        copia[:, 6] = np.clip(copia[:, 6], 0, 1)       # long_value_ratio ∈ [0,1]
        copia[:, 10] = np.clip(copia[:, 10], 0, 8)     # entropía ∈ [0,8]

        sinteticos.append(copia)

    return np.vstack(sinteticos)


def _generar_dataset_sintetico_base(semilla: int = _SEMILLA) -> np.ndarray:
    """
    Dataset sintético de respaldo con perfiles realistas por tipo de archivo.
    Se usa como complemento a los datos reales para asegurar que el modelo
    conoce la variabilidad típica de cada formato.
    """
    rng = np.random.default_rng(semilla)

    def _perfil(n, mc_loc, mc_sc, gps_p, avg_loc, avg_sc, ent_loc, ent_sc,
                is_img, is_p, is_d):
        """Genera n muestras con las distribuciones indicadas."""
        return np.column_stack([
            np.clip(rng.normal(mc_loc, mc_sc, n), 1, None),      # metadata_count
            rng.binomial(1, gps_p, n).astype(float),             # has_gps
            rng.binomial(1, 0.02, n).astype(float),              # has_macros
            rng.binomial(1, 0.01, n).astype(float),              # is_extension_spoofed
            rng.binomial(1, 0.02, n).astype(float),              # has_suspicious_patterns
            np.clip(rng.normal(avg_loc, avg_sc, n), 0, None),    # avg_value_length
            rng.beta(1, 30, n),                                   # long_value_ratio
            np.full(n, is_img),                                   # is_image
            np.full(n, is_p),                                     # is_pdf
            np.full(n, is_d),                                     # is_docx
            np.clip(rng.normal(ent_loc, ent_sc, n), 0, 8),       # entropy_score
            np.zeros(n),                                          # has_embedded_objects
            np.zeros(n),                                          # unusual_creator
        ])

    # Cada tipo tiene su perfil: las imágenes tienen muchos campos y GPS,
    # los PDFs pocos campos, y los DOCX aún menos.
    imgs = _perfil(80,  40, 15, 0.50, 50, 25, 3.8, 0.5, 1, 0, 0)
    pdfs = _perfil(80,   8,  3, 0.00, 20, 10, 3.5, 0.4, 0, 1, 0)
    docx = _perfil(80,   6,  2, 0.00, 15,  5, 3.2, 0.4, 0, 0, 1)

    base = np.vstack([imgs, pdfs, docx])
    rng.shuffle(base)
    return base


# --- Paso 3: Pipeline de entrenamiento ---

def entrenar_y_guardar(
    directorio_archivos: Path | None = None,
    ruta_salida: Path = _RUTA_MODELO,
) -> Path:
    """
    Pipeline completo: escanea archivos reales → genera sintéticos →
    escala → entrena IsolationForest → guarda modelo.
    """
    # Si no se indica directorio, buscamos archivosTest/ en la raíz
    if directorio_archivos is None:
        raiz_proyecto = Path(__file__).resolve().parent.parent.parent
        directorio_archivos = raiz_proyecto / "archivosTest"

    if not directorio_archivos.exists():
        print(f"[!] Directorio '{directorio_archivos}' no encontrado.")
        print("[*] Entrenando solo con datos sintéticos de respaldo…")
        X_real = np.empty((0, len(_NOMBRES_FEATURES)))
        nombres_reales: List[str] = []
    else:
        # Extraemos features de archivos reales
        print(f"[*] Escaneando archivos en: {directorio_archivos}")
        X_real, nombres_reales = _extraer_features_reales(directorio_archivos)
        print(f"    → {X_real.shape[0]} archivos procesados correctamente")

        for nombre in nombres_reales:
            print(f"      • {nombre}")

    # Generamos versiones "ruidosas" de los datos reales (×10)
    if X_real.shape[0] > 0:
        print(f"\n[*] Generando datos sintéticos (×10) a partir de {X_real.shape[0]} muestras reales…")
        X_sinteticos_reales = _generar_sinteticos_desde_reales(X_real, factor=10)
        print(f"    → {X_sinteticos_reales.shape[0]} muestras sintéticas generadas")
    else:
        X_sinteticos_reales = np.empty((0, len(_NOMBRES_FEATURES)))

    # Dataset base por tipo (cobertura extra)
    print("[*] Generando dataset sintético base (cobertura de tipos)…")
    X_sinteticos_base = _generar_dataset_sintetico_base()
    print(f"    → {X_sinteticos_base.shape[0]} muestras base generadas")

    # Juntamos todo
    bloques = [b for b in [X_real, X_sinteticos_reales, X_sinteticos_base]
               if b.shape[0] > 0]
    X_total = np.vstack(bloques)
    print(f"\n[*] Dataset final: {X_total.shape[0]} muestras, {X_total.shape[1]} features")
    print(f"    → Reales: {X_real.shape[0]}")
    print(f"    → Sintéticas (de reales): {X_sinteticos_reales.shape[0]}")
    print(f"    → Sintéticas (base): {X_sinteticos_base.shape[0]}")

    # Estandarizamos y entrenamos
    scaler = StandardScaler()
    X_escalado = scaler.fit_transform(X_total)
    print("[*] StandardScaler ajustado.")

    modelo = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=_SEMILLA,
        max_samples="auto",
    )
    modelo.fit(X_escalado)
    print("[*] IsolationForest entrenado (200 estimadores).")

    # Guardamos modelo + scaler como un solo paquete
    artefacto = {
        "modelo": modelo,
        "scaler": scaler,
        "features": _NOMBRES_FEATURES,
        "version": "3.0.0",
        "n_muestras_reales": X_real.shape[0],
        "n_muestras_total": X_total.shape[0],
        "archivos_entrenamiento": nombres_reales,
    }
    joblib.dump(artefacto, str(ruta_salida))
    print(f"\n[✓] Modelo v3.0 guardado en: {ruta_salida}")

    return ruta_salida


# --- Punto de entrada ---

if __name__ == "__main__":
    # Nos aseguramos de que src/ esté en el path
    raiz = Path(__file__).resolve().parent.parent.parent
    src_dir = str(raiz / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    entrenar_y_guardar()
