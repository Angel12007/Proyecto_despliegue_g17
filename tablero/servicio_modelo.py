"""Predicciones, explicación por paciente, días esperados y tarifas.

Las predicciones vienen de la API (FastAPI, contenedor `api`) cuando está definida
la variable de entorno API_URL. Sin ella, el tablero usa directamente el paquete
`modelo_uci` instalado (útil para desarrollo). Las pantallas no cambian en ningún caso.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd
import requests

import config

LOTE = 300  # pacientes por solicitud a la API


RANGOS = {c[0]: c[3] for c in config.CAMPOS if c[2] == "num"}


def _limpiar(X: pd.DataFrame) -> list[dict]:
    """Convierte la tabla a registros JSON: NaN -> None y categorías a enteros.

    Los valores fuera de los rangos que acepta la API (por ejemplo, un lactato de 230
    en la base histórica) se tratan como faltantes y el modelo los imputa.
    """
    X = X[config.VARIABLES].astype(float).copy()
    for v, (minimo, maximo) in RANGOS.items():
        X.loc[(X[v] < minimo) | (X[v] > maximo), v] = np.nan
    registros = []
    for fila in X.to_dict("records"):
        registros.append({k: (None if pd.isna(v) else (int(v) if float(v).is_integer() else float(v)))
                          for k, v in fila.items()})
    return registros


def _predecir_api(registros: list[dict]) -> list[dict]:
    salida = []
    for i in range(0, len(registros), LOTE):
        r = requests.post(config.API_PREDICT, json={"inputs": registros[i:i + LOTE]}, timeout=60)
        r.raise_for_status()
        salida.extend(r.json()["predictions"])
    return salida


def _predecir_local(registros: list[dict]) -> list[dict]:
    from modelo_uci.predict import make_prediction
    res = make_prediction(input_data=pd.DataFrame(registros, columns=config.VARIABLES))
    if res["errors"]:
        raise ValueError(res["errors"])
    return res["predictions"]


def predecir_tabla(X: pd.DataFrame) -> pd.DataFrame:
    """Probabilidades y categorías de riesgo para varios pacientes."""
    registros = _limpiar(X)
    preds = _predecir_api(registros) if config.API_URL else _predecir_local(registros)
    return pd.DataFrame(preds, index=X.index)


@lru_cache(maxsize=1)
def info_modelo() -> dict:
    """Algoritmo y métricas de los modelos en uso (desde la API o el paquete)."""
    if config.API_URL:
        r = requests.get(config.API_INFO, timeout=30)
        r.raise_for_status()
        return r.json()
    from modelo_uci.predict import info_modelos
    return info_modelos()


@lru_cache(maxsize=1)
def medianas() -> dict:
    """Medianas de la cohorte de entrenamiento, para la explicación por paciente."""
    df = pd.read_csv(config.RUTA_DATOS)
    ent = df[df["particion_temporal"] == "entrenamiento"]
    return ent[config.VARIABLES].median().to_dict()


def contribuciones(paciente: dict, n: int = 5) -> dict[str, pd.DataFrame]:
    """Cuánto cambia la probabilidad si cada dato se reemplaza por la mediana de la cohorte.

    Válido para cualquier modelo: valores positivos indican que ese dato del paciente
    sube su riesgo frente a un paciente típico. Se resuelve en una sola solicitud a la API.
    """
    base = pd.DataFrame([paciente])[config.VARIABLES].astype(float)
    filas, nombres = [base], []
    for v in config.VARIABLES:
        if pd.isna(base.at[0, v]):
            continue
        alt = base.copy()
        alt.at[0, v] = medianas()[v]
        filas.append(alt)
        nombres.append(v)
    pred = predecir_tabla(pd.concat(filas, ignore_index=True))
    salida = {}
    for desenlace in ["estancia", "muerte"]:
        p = pred[f"p_{desenlace}"].to_numpy()
        tabla = pd.DataFrame({"variable": [config.ETIQUETAS[v] for v in nombres], "efecto": p[0] - p[1:]})
        salida[desenlace] = tabla.reindex(tabla["efecto"].abs().sort_values(ascending=False).index).head(n)
    return salida


# ----------------------------------------------------------------------------
# Días esperados
# ----------------------------------------------------------------------------
class EstimadorDias:
    """Días de estancia esperados a partir de la probabilidad de estancia >= 7 días.

        días esperados = p · media(>= 7 días) + (1 - p) · media(< 7 días)

    con la distribución de estancias de la partición de entrenamiento. Para un paciente
    que ya lleva d días en la UCI, se actualiza p con la información de que sigue
    hospitalizado y se usa la estancia residual media de cada grupo.
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
