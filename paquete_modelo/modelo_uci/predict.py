from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from modelo_uci import __version__

DIR_MODELOS = Path(__file__).resolve().parent / "modelos"

VARIABLES = [
    "age", "origin_of_tumor", "type_of_admission", "ecog",
    "apacheii", "sapsiii", "sofa", "lactate", "pafi", "platelet",
    "ventilatory_support", "vasopressors_use", "shock", "sepsis",
]


@lru_cache(maxsize=None)
def _cargar_artefacto(nombre_archivo: str) -> dict[str, Any]:
    return joblib.load(DIR_MODELOS / nombre_archivo)


def _categoria_riesgo(prob: float, umbrales: dict[str, float]) -> str:
    if prob >= umbrales["alto"]:
        return "Alto"
    if prob >= umbrales["intermedio"]:
        return "Intermedio"
    return "Bajo"


def info_modelos() -> dict[str, Any]:
    m_est = _cargar_artefacto("modelo_estancia.joblib")
    m_mue = _cargar_artefacto("modelo_mortalidad.joblib")
    return {
        "estancia": {
            "algoritmo": m_est["algoritmo"],
            "version": __version__,
            "hiperparametros": m_est["hiperparametros"],
            "metricas": m_est["metricas"],
            "umbrales": m_est["umbrales"],
        },
        "muerte": {
            "algoritmo": m_mue["algoritmo"],
            "version": __version__,
            "hiperparametros": m_mue["hiperparametros"],
            "metricas": m_mue["metricas"],
            "umbrales": m_mue["umbrales"],
        },
    }


def make_prediction(input_data: pd.DataFrame) -> dict[str, Any]:
    try:
        m_est = _cargar_artefacto("modelo_estancia.joblib")
        m_mue = _cargar_artefacto("modelo_mortalidad.joblib")

        df = input_data.copy()
        for col in VARIABLES:
            if col not in df.columns:
                df[col] = np.nan
        X = df[VARIABLES].astype(float)

        probs_est = m_est["pipeline"].predict_proba(X)[:, 1]
        probs_mue = m_mue["pipeline"].predict_proba(X)[:, 1]

        predicciones = []
        for pe, pm in zip(probs_est, probs_mue):
            pe_val = float(pe)
            pm_val = float(pm)
            predicciones.append({
                "p_estancia": pe_val,
                "riesgo_estancia": _categoria_riesgo(pe_val, m_est["umbrales"]),
                "p_muerte": pm_val,
                "riesgo_muerte": _categoria_riesgo(pm_val, m_mue["umbrales"]),
            })

        return {
            "errors": None,
            "version": __version__,
            "predictions": predicciones,
        }
    except Exception as exc:
        return {
            "errors": json.dumps(str(exc)),
            "version": __version__,
            "predictions": None,
        }
