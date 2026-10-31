"""Carga de la base y cálculos agregados para las pantallas de censo y capacidad."""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

import config
import servicio_modelo as sm


@lru_cache(maxsize=1)
def base() -> pd.DataFrame:
    """Base final con las predicciones del modelo para cada paciente."""
    df = pd.read_csv(config.RUTA_DATOS, parse_dates=["fecha_ingreso"])
    df = df.dropna(subset=["fecha_ingreso"]).copy()
    df["fecha_egreso"] = df["fecha_ingreso"] + pd.to_timedelta(df["dias_estancia"].fillna(0), unit="D")
    df = df.join(sm.predecir_tabla(df[config.VARIABLES]))
    df["origen"] = df["origin_of_tumor"].map({1: "Sólido", 0: "Hematológico"})
    df["ingreso"] = df["type_of_admission"].map({1: "Médico", 2: "Quirúrgico"})
    df["ventilacion"] = df["ventilatory_support"].map({1: "Sí", 0: "No"})
    return df


@lru_cache(maxsize=1)
def estimador() -> sm.EstimadorDias:
    df = base()
    return sm.EstimadorDias(df.loc[df["particion_temporal"] == "entrenamiento", "dias_estancia"])


def rango_prueba() -> tuple[pd.Timestamp, pd.Timestamp]:
    """Fechas del periodo de prueba: el modelo no vio a estos pacientes."""
    pru = base()[base()["particion_temporal"] == "prueba"]
    return pru["fecha_ingreso"].min(), pru["fecha_egreso"].max()


def costear(df: pd.DataFrame, dias_col: str, tarifas: dict) -> pd.Series:
    t = sm.tarifa_paciente(df["ventilatory_support"], tarifas["uci"], tarifas["intermedio"])
    return df[dias_col] * t


# ----------------------------------------------------------------------------
# Pantalla 2: censo y planificación
# ----------------------------------------------------------------------------
def censo(fecha, tarifas: dict) -> pd.DataFrame:
    """Pacientes de la cohorte que estaban en la UCI en la fecha, con días restantes esperados."""
    f = pd.Timestamp(fecha)
    df = base()
    en_uci = df[(df["fecha_ingreso"] <= f) & (df["fecha_egreso"] > f)].copy()
    est = estimador()
    en_uci["dias_transcurridos"] = (f - en_uci["fecha_ingreso"]).dt.days
    en_uci["dias_restantes_esperados"] = [est.restantes(p, d) for p, d in
                                          zip(en_uci["p_estancia"], en_uci["dias_transcurridos"])]
    en_uci["dias_restantes_reales"] = (en_uci["fecha_egreso"] - f).dt.days
    en_uci["costo_esperado"] = costear(en_uci, "dias_restantes_esperados", tarifas)
    en_uci["costo_real"] = costear(en_uci, "dias_restantes_reales", tarifas)
    return en_uci.sort_values("p_estancia", ascending=False)


def ingresos_periodo(inicio, fin, tarifas: dict) -> pd.DataFrame:
    """Pacientes que ingresaron en el periodo, con días y costos esperados desde el ingreso."""
    df = base()
    sel = df[(df["fecha_ingreso"] >= pd.Timestamp(inicio)) & (df["fecha_ingreso"] <= pd.Timestamp(fin))].copy()
    sel["dias_esperados"] = estimador().totales(sel["p_estancia"])
    sel["costo_esperado"] = costear(sel, "dias_esperados", tarifas)
    sel["costo_real"] = costear(sel.assign(d=sel["dias_estancia"].fillna(0)), "d", tarifas)
    return sel.sort_values("p_estancia", ascending=False)


def lista_propia(pacientes: list[dict], tarifas: dict) -> pd.DataFrame:
    """Pacientes cargados desde un archivo o agregados desde la pantalla de predicción."""
    if not pacientes:
        return pd.DataFrame()
    df = pd.DataFrame(pacientes)
    for v in config.VARIABLES:
        if v not in df:
            df[v] = np.nan
    df = df.join(sm.predecir_tabla(df[config.VARIABLES]))
    df["dias_esperados"] = estimador().totales(df["p_estancia"])
    df["costo_esperado"] = costear(df, "dias_esperados", tarifas)
    return df.sort_values("p_estancia", ascending=False)


# ----------------------------------------------------------------------------
# Pantalla 3: capacidad y costos
# ----------------------------------------------------------------------------
def filtrar(origen: list, ingreso: list, inicio, fin) -> pd.DataFrame:
    df = base()
    # Un paciente sin tipo de ingreso registrado se incluye cuando se eligen ambos tipos
    m = df["origen"].isin(origen) & (df["ingreso"].isin(ingreso) | (df["ingreso"].isna() & (len(ingreso) == 2)))
    m &= (df["fecha_ingreso"] >= pd.Timestamp(inicio)) & (df["fecha_ingreso"] <= pd.Timestamp(fin))
    return df[m]


def kpis(df: pd.DataFrame, tarifas: dict) -> dict:
    dias = df["dias_estancia"].fillna(0)
    costo = costear(df.assign(d=dias), "d", tarifas)
    top = df["p_estancia"] >= df["p_estancia"].quantile(1 - config.FRACCION_ALTO_RIESGO) if len(df) else []
    return {
        "pacientes": len(df),
        "dias_cama": float(dias.sum()),
        "pct_prolongada": 100 * df["estancia_prolongada"].mean() if len(df) else np.nan,
        "mortalidad": 100 * df["mortality"].mean() if len(df) else np.nan,
        "costo_total": float(costo.sum()),
        "costo_prolongadas": float(costo[df["estancia_prolongada"] == 1].sum()),
        "costo_top20": float(costo[top].sum()) if len(df) else 0.0,
        "dias_vent_pct": 100 * dias[df["ventilatory_support"] == 1].sum() / dias.sum() if dias.sum() else np.nan,
        "pac_vent_pct": 100 * (df["ventilatory_support"] == 1).mean() if len(df) else np.nan,
    }


def curva_concentracion(df: pd.DataFrame, puntaje: str) -> pd.DataFrame:
    """% acumulado de días-cama al ordenar a los pacientes de mayor a menor riesgo."""
    d = df.dropna(subset=[puntaje, "dias_estancia"]).sort_values(puntaje, ascending=False)
    if d.empty:
        return pd.DataFrame({"pct_pacientes": [], "pct_dias": []})
    return pd.DataFrame({
        "pct_pacientes": 100 * np.arange(1, len(d) + 1) / len(d),
        "pct_dias": 100 * d["dias_estancia"].cumsum() / d["dias_estancia"].sum(),
    })


def tendencia(df: pd.DataFrame) -> pd.DataFrame:
    f = df["fecha_ingreso"]
    sem = f.dt.year.astype(str) + "-S" + np.where(f.dt.month <= 6, "1", "2")
    t = df.assign(semestre=sem).groupby("semestre").agg(
        ingresos=("record_id", "count"), dias_cama=("dias_estancia", "sum"),
        prolongada=("estancia_prolongada", "mean"), mortalidad=("mortality", "mean")).reset_index()
    return t[t["ingresos"] >= 10]
