"""Entrena el modelo PROVISIONAL que usa el tablero mientras el equipo elige el final.

Regresión logística con el mismo preprocesamiento del resto del proyecto
(estandarización + imputación KNN para continuas, moda para categóricas),
ajustada solo con la partición temporal de entrenamiento y con las 14
variables del formulario. Guarda un archivo por desenlace en models/.

Cuando el equipo elija el modelo final en MLflow, se reemplazan estos
archivos con el mismo formato (diccionario con "pipeline", "variables",
"umbrales", "medianas", "nombre", "metricas").

Uso:  python tablero/preparar_modelo_provisional.py
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import config

CATEGORICAS = ["origin_of_tumor", "type_of_admission", "ecog", "ventilatory_support",
               "vasopressors_use", "shock", "sepsis"]


def crear_pipeline(C: float) -> Pipeline:
    contin = [v for v in config.VARIABLES if v not in CATEGORICAS]
    categ = [v for v in config.VARIABLES if v in CATEGORICAS]
    prepro = ColumnTransformer([
        ("continuas", Pipeline([("escalar", StandardScaler()), ("imputar", KNNImputer(n_neighbors=5))]), contin),
        ("categoricas", SimpleImputer(strategy="most_frequent"), categ),
    ])
    return Pipeline([("prepro", prepro), ("modelo", LogisticRegression(C=C, max_iter=5000))])


def entrenar(df: pd.DataFrame, desenlace: str) -> dict:
    datos = df.dropna(subset=[desenlace])
    ent = datos[datos["particion_temporal"] == "entrenamiento"]
    pru = datos[datos["particion_temporal"] == "prueba"]
    X, y = ent[config.VARIABLES].astype(float), ent[desenlace].astype(int)
    cv = StratifiedKFold(5, shuffle=True, random_state=42)
    mejor_C = max([0.01, 0.1, 1.0], key=lambda C: cross_val_score(crear_pipeline(C), X, y, cv=cv,
                                                                  scoring="roc_auc").mean())
    pipe = crear_pipeline(mejor_C).fit(X, y)
    p_ent = pipe.predict_proba(X)[:, 1]
    p_pru = pipe.predict_proba(pru[config.VARIABLES].astype(float))[:, 1]
    return {
        "pipeline": pipe,
        "variables": list(config.VARIABLES),
        "desenlace": desenlace,
        "nombre": f"Regresión logística provisional (C={mejor_C})",
        # Cortes de riesgo según la distribución en entrenamiento: alto = 20 % superior
        "umbrales": {"intermedio": float(np.quantile(p_ent, 0.50)),
                     "alto": float(np.quantile(p_ent, 1 - config.FRACCION_ALTO_RIESGO))},
        "medianas": X.median().to_dict(),
        "metricas": {"auroc_prueba": float(roc_auc_score(pru[desenlace], p_pru)),
                     "brier_prueba": float(brier_score_loss(pru[desenlace], p_pru))},
    }


def main() -> None:
    df = pd.read_csv(config.RUTA_DATOS)
    config.CARPETA_MODELOS.mkdir(exist_ok=True)
    for desenlace, ruta in config.MODELOS.items():
        art = entrenar(df, desenlace)
        joblib.dump(art, ruta)
        print(f"{desenlace}: {art['nombre']} | AUROC prueba {art['metricas']['auroc_prueba']:.3f} "
              f"| Brier {art['metricas']['brier_prueba']:.3f} -> {Path(ruta).relative_to(config.RAIZ)}")


if __name__ == "__main__":
    main()
