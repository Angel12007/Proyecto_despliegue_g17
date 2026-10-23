"""Etapa 2 del pipeline: procesamiento de variables clínicas.

Usa dos funciones del repositorio de origen de la base:
  - procesar_variables_clinicas: origen tumoral, estadio global,
    soporte ventilatorio y tratamiento oncológico en UCI.
  - limpiar_y_preparar_dataset: elimina columnas no usadas, define
    categóricas, quita reingresos duplicados y renombra al inglés.

Sobre esa base:
  - No se imputa sobre la base completa. La imputación KNN + media se hará
    dentro de cada partición de entrenamiento en la etapa de modelado.
  - Desenlaces recodificados a 0/1 con 1 = evento (muerte).
  - Se añaden los desenlaces del proyecto: estancia prolongada (>= 7 días)
    y el compuesto muerte en UCI o estancia prolongada.
  - Se marca la partición temporal (entrenamiento / prueba) según la fecha
    de ingreso.

Salida: data/processed/dataset_modelado.csv, versión final para modelado.

Uso:  python src/procesar_datos.py
"""
import contextlib
import io
from pathlib import Path

import pandas as pd
import yaml

from clinical_features import procesar_variables_clinicas
from preprocessing import limpiar_y_preparar_dataset

RAIZ = Path(__file__).resolve().parents[1]

# Columnas que limpiar_y_preparar_dataset elimina pero que el proyecto necesita
# para definir desenlaces, la partición temporal y la comparación con escalas.
COLUMNAS_AUXILIARES = {
    "fecha_ing": "fecha_ingreso",
    "diastot": "dias_estancia",
    "mortesper_saps3": "mort_esperada_saps3",
    "mortaespe": "mort_esperada_apache",
}


def procesar(df_cargado: pd.DataFrame, umbral_estancia: int, fecha_corte: str) -> pd.DataFrame:
    auxiliares = (
        df_cargado.drop_duplicates("record_id", keep="first")[["record_id", *COLUMNAS_AUXILIARES]]
        .rename(columns=COLUMNAS_AUXILIARES)
    )

    # Estas funciones imprimen mucho detalle; se silencia aquí.
    with contextlib.redirect_stdout(io.StringIO()):
        df = procesar_variables_clinicas(df_cargado.copy(), verbose=False)
        df = limpiar_y_preparar_dataset(df)

    # Desenlaces: en el EDC 1 = vivo y 2 = muerto (UCI); 1 = muerto y 2 = vivo (30 días).
    df["mortality"] = df["mortality"].map({1: 0, 2: 1})
    df["death_30d"] = df["30survival"].map({1: 1, 2: 0})
    df = df.drop(columns=["30survival"])

    df = df.merge(auxiliares, on="record_id", how="left")
    df["fecha_ingreso"] = pd.to_datetime(df["fecha_ingreso"], errors="coerce")
    df["estancia_prolongada"] = (df["dias_estancia"] >= umbral_estancia).astype("Int64")
    df.loc[df["dias_estancia"].isna(), "estancia_prolongada"] = pd.NA
    df["muerte_o_estancia_prolongada"] = (
        (df["mortality"] == 1) | (df["estancia_prolongada"] == 1)
    ).astype(int)
    df["particion_temporal"] = (df["fecha_ingreso"] < pd.Timestamp(fecha_corte)).map(
        {True: "entrenamiento", False: "prueba"}
    )
    return df


def main() -> None:
    params = yaml.safe_load(open(RAIZ / "params.yaml", encoding="utf-8"))
    rutas, proc = params["datos"], params["procesamiento"]

    df_cargado = pd.read_csv(RAIZ / rutas["archivo_cargado"])
    df = procesar(df_cargado, proc["umbral_estancia_prolongada_dias"], proc["fecha_corte_temporal"])

    salida = RAIZ / rutas["archivo_procesado"]
    salida.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(salida, index=False)

    print(f"Pacientes: {len(df)} | variables: {df.shape[1]}")
    for d in ["mortality", "death_30d", "estancia_prolongada", "muerte_o_estancia_prolongada"]:
        print(f"  {d}: {int(df[d].sum())} eventos ({df[d].mean():.1%}) | faltantes {df[d].isna().sum()}")
    print(df["particion_temporal"].value_counts().to_string())
    print(f"Guardado en {salida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
