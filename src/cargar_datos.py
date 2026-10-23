"""Etapa 1 del pipeline: cargue de la base cruda.

Lee el Excel exportado del EDC (df_merged_final.xlsx), convierte el texto
"Sin dato" en valores faltantes, fuerza a numérico las variables continuas
y guarda una copia tabular en data/interim/.

No imputa ni elimina pacientes: eso ocurre después, y la imputación va
dentro del pipeline del modelo para no filtrar información entre
entrenamiento y validación.

Uso:  python src/cargar_datos.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]

# Variables continuas que en el Excel llegan como texto por el "Sin dato".
VARIABLES_NUMERICAS = [
    "potasioing", "mortesper_saps3", "creing", "sodioing", "buning", "sofa_24h",
    "ecog", "calciing", "pco2ing", "po2ing", "hco3ing", "being", "lactatoing",
    "pafiing", "karnofsky", "pting", "pttingr", "bilitorring", "bding", "biing",
    "tgoing", "tgping", "mortaespe", "apacheii", "saps_3", "diastot",
]


def cargar_base(ruta_excel: Path) -> pd.DataFrame:
    df = pd.read_excel(ruta_excel)
    df = df.replace("Sin dato", np.nan)
    for col in VARIABLES_NUMERICAS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["fecha_ing"] = pd.to_datetime(df["fecha_ing"], errors="coerce")
    return df


def validar_base(df: pd.DataFrame) -> None:
    """Chequeos mínimos para detectar una base corrupta o un cambio de formato."""
    requeridas = {"record_id", "fecha_ing", "mortalidad", "sobrevida30", "diastot"}
    faltan = requeridas - set(df.columns)
    if faltan:
        raise ValueError(f"Faltan columnas obligatorias: {sorted(faltan)}")
    if not set(df["mortalidad"].dropna().unique()) <= {1, 2}:
        raise ValueError("'mortalidad' debe estar codificada 1 = vivo, 2 = muerto")


def main() -> None:
    params = yaml.safe_load(open(RAIZ / "params.yaml", encoding="utf-8"))["datos"]
    df = cargar_base(RAIZ / params["archivo_crudo"])
    validar_base(df)

    salida = RAIZ / params["archivo_cargado"]
    salida.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(salida, index=False)

    print(f"Filas: {len(df)} | pacientes únicos: {df['record_id'].nunique()} | columnas: {df.shape[1]}")
    print(f"Ingresos entre {df['fecha_ing'].min():%Y-%m-%d} y {df['fecha_ing'].max():%Y-%m-%d}")
    print(f"Guardado en {salida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
