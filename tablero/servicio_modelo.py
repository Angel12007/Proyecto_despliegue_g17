"""Predicciones, días esperados y costos.

Toda la lógica del modelo está aquí, separada de las pantallas. En la entrega 3
`predecir_tabla` se cambiará para llamar a la API (FastAPI) en lugar de cargar
los archivos .joblib; el resto del tablero no cambia.
"""
from __future__ import annotations

from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

import config


@lru_cache(maxsize=None)
def cargar_modelo(desenlace: str) -> dict:
    ruta = config.MODELOS[desenlace]
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta}. Corra primero: python tablero/preparar_modelo_provisional.py "
            "(o dvc repro).")
    return joblib.load(ruta)


def categoria(p: float, umbrales: dict) -> str:
    if p >= umbrales["alto"]:
        return "Alto"
    if p >= umbrales["intermedio"]:
        return "Intermedio"
    return "Bajo"


def predecir_tabla(X: pd.DataFrame) -> pd.DataFrame:
    """Probabilidades y categorías de riesgo para varios pacientes."""
    salida = pd.DataFrame(index=X.index)
    for desenlace, sufijo in [("estancia_prolongada", "estancia"), ("mortality", "muerte")]:
        m = cargar_modelo(desenlace)
        p = m["pipeline"].predict_proba(X[m["variables"]].astype(float))[:, 1]
        salida[f"p_{sufijo}"] = p
        salida[f"riesgo_{sufijo}"] = [categoria(v, m["umbrales"]) for v in p]
    return salida


def contribuciones(paciente: dict, desenlace: str, n: int = 5) -> pd.DataFrame:
    """Cuánto cambia la probabilidad si cada variable se reemplaza por la mediana de la cohorte.

    Es una explicación sencilla y válida para cualquier modelo: valores positivos
    indican que ese dato del paciente sube su riesgo frente a un paciente típico.
    """
    m = cargar_modelo(desenlace)
    base = pd.DataFrame([paciente])[m["variables"]].astype(float)
    p0 = m["pipeline"].predict_proba(base)[0, 1]
    filas = []
    for v in m["variables"]:
        if pd.isna(base.at[0, v]):
            continue
        alterno = base.copy()
        alterno.at[0, v] = m["medianas"][v]
        delta = p0 - m["pipeline"].predict_proba(alterno)[0, 1]
        filas.append({"variable": config.ETIQUETAS[v], "efecto": delta})
    tabla = pd.DataFrame(filas)
    if tabla.empty:
        return tabla
    return tabla.reindex(tabla["efecto"].abs().sort_values(ascending=False).index).head(n)


# ----------------------------------------------------------------------------
# Días esperados
# ----------------------------------------------------------------------------
class EstimadorDias:
    """Días de estancia esperados a partir de la probabilidad de estancia >= 7 días.

    Usa la distribución de estancias observada en la partición de entrenamiento,
    separada en dos grupos (< 7 días y >= 7 días):

        días esperados = p · media(>= 7) + (1 - p) · media(< 7)

    Para un paciente que ya lleva d días en la UCI, se actualiza p con la
    información de que sigue hospitalizado (si d >= 7, ya es estancia prolongada)
    y se usa la estancia residual media de cada grupo.
    """

    def __init__(self, dias_entrenamiento: pd.Series):
        dias = dias_entrenamiento.dropna().to_numpy()
        self.largos = dias[dias >= config.UMBRAL_ESTANCIA]
        self.cortos = dias[dias < config.UMBRAL_ESTANCIA]

    @staticmethod
    def _residual(grupo: np.ndarray, d: int) -> tuple[float, float]:
        sigue = grupo[grupo > d]
        if len(grupo) == 0 or len(sigue) == 0:
            return 0.0, 1.0
        return len(sigue) / len(grupo), float((sigue - d).mean())

    def totales(self, p) -> np.ndarray:
        p = np.asarray(p, dtype=float)
        return p * self.largos.mean() + (1 - p) * self.cortos.mean()

    def restantes(self, p: float, d: int) -> float:
        s1, r1 = self._residual(self.largos, d)
        s0, r0 = self._residual(self.cortos, d)
        denom = p * s1 + (1 - p) * s0
        p_act = 1.0 if denom == 0 else p * s1 / denom
        return p_act * r1 + (1 - p_act) * r0


def tarifa_paciente(ventilacion, tarifa_uci: float, tarifa_intermedio: float) -> np.ndarray:
    v = np.asarray(ventilacion, dtype=float)
    return np.where(v == 1, tarifa_uci, tarifa_intermedio)
