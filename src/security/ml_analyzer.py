"""
Módulo de inferencia ML — Semáforo de Riesgo Inteligente.

Carga el modelo entrenado (IsolationForest + StandardScaler), extrae las
features estructurales de un archivo ya analizado y devuelve un veredicto
con tres niveles: Bajo (Verde), Medio (Amarillo) o Alto (Rojo).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import joblib

try:
    from security.feature_engineering import extraer_caracteristicas, NOMBRES_FEATURES
except ImportError:
    from src.security.feature_engineering import extraer_caracteristicas, NOMBRES_FEATURES


# --- Constantes ---

_RUTA_MODELO: Path = Path(__file__).resolve().parent / "modelo_riesgo.joblib"

# Caché en memoria para no recargar el modelo en cada análisis
_modelo_cache: Optional[Dict[str, Any]] = None


# --- Carga del modelo ---

def _cargar_modelo() -> Dict[str, Any]:
    """
    Carga el modelo desde disco la primera vez y lo guarda en caché.
    Si el archivo no existe, lanza FileNotFoundError (hay que entrenar primero).
    """
    global _modelo_cache

    if _modelo_cache is not None:
        return _modelo_cache

    if not _RUTA_MODELO.exists():
        raise FileNotFoundError(
            f"No se encontró el modelo en '{_RUTA_MODELO}'. "
            "Ejecuta primero: python -m src.security.train_anomaly_model"
        )

    _modelo_cache = joblib.load(str(_RUTA_MODELO))
    return _modelo_cache


# --- Inferencia ---

def analizar_riesgo_ml(resultado: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recibe el dict de extract_metadata_auto() y devuelve el veredicto ML.

    El resultado incluye:
      - prediccion:  1 (normal), 0 (medio) o -1 (anómalo)
      - nivel_riesgo: "Bajo", "Medio" o "Alto"
      - color:        "Verde", "Amarillo" o "Rojo" (para la GUI)
      - score:        valor de la decision function (más negativo = más raro)
      - features_extraidas: dict con cada feature calculada (transparencia)
    """
    # Cargamos modelo y scaler
    artefacto = _cargar_modelo()
    modelo = artefacto["modelo"]
    scaler = artefacto["scaler"]

    # Extraemos y escalamos las features
    vector = extraer_caracteristicas(resultado)
    vector_2d = vector.reshape(1, -1)
    vector_escalado = scaler.transform(vector_2d)

    # Predicción del Isolation Forest
    prediccion_raw: int = int(modelo.predict(vector_escalado)[0])
    score: float = float(modelo.decision_function(vector_escalado)[0])

    # Dict de features para depuración/transparencia
    features_dict: Dict[str, float] = {
        nombre: float(valor)
        for nombre, valor in zip(NOMBRES_FEATURES, vector)
    }

    # --- Post-procesamiento: semáforo de 3 niveles ---
    # Contamos cuántos indicadores de riesgo están activos
    indicadores_riesgo = sum([
        features_dict.get("has_macros", 0) > 0,
        features_dict.get("has_suspicious_patterns", 0) > 0,
        features_dict.get("has_embedded_objects", 0) > 0,
        features_dict.get("unusual_creator", 0) > 0,
    ])
    extension_suplantada = features_dict.get("is_extension_spoofed", 0) > 0

    # Lógica del semáforo:
    #   ROJO:     El modelo lo marca anómalo, o extensión suplantada + indicadores, o ≥2 indicadores
    #   AMARILLO: Solo extensión suplantada, o un solo indicador aislado
    #   VERDE:    Todo limpio
    if prediccion_raw == -1:
        nivel_riesgo = "Alto"
        color = "Rojo"
        prediccion_final = -1
    elif extension_suplantada and indicadores_riesgo >= 1:
        nivel_riesgo = "Alto"
        color = "Rojo"
        prediccion_final = -1
    elif extension_suplantada:
        nivel_riesgo = "Medio"
        color = "Amarillo"
        prediccion_final = 0
    elif indicadores_riesgo >= 2:
        nivel_riesgo = "Alto"
        color = "Rojo"
        prediccion_final = -1
    elif indicadores_riesgo == 1:
        nivel_riesgo = "Medio"
        color = "Amarillo"
        prediccion_final = 0
    else:
        nivel_riesgo = "Bajo"
        color = "Verde"
        prediccion_final = 1

    return {
        "prediccion": prediccion_final,
        "nivel_riesgo": nivel_riesgo,
        "color": color,
        "score": round(score, 4),
        "features_extraidas": features_dict,
    }
