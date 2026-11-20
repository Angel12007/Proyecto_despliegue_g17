from pathlib import Path
import itertools
import joblib
import numpy as np
import pandas as pd
import pydantic
import sklearn
import xgboost
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

SEMILLA = 42
RAIZ = Path(__file__).resolve().parents[1]
RUTA_DATOS = RAIZ / "data" / "processed" / "dataset_modelado.csv"
DIR_MODELOS = Path(__file__).resolve().parent / "modelo_uci" / "modelos"

VARIABLES = [
    "age", "origin_of_tumor", "type_of_admission", "ecog",
    "apacheii", "sapsiii", "sofa", "lactate", "pafi", "platelet",
    "ventilatory_support", "vasopressors_use", "shock", "sepsis",
]

CATEGORICAS = [
    "origin_of_tumor", "type_of_admission", "ecog",
    "ventilatory_support", "vasopressors_use", "shock", "sepsis",
]

REJILLAS = {
    "xgboost": {
        "n_estimators": [200, 500],
        "max_depth": [3, 5],
        "learning_rate": [0.03, 0.1],
    },
    "random_forest": {
        "n_estimators": [300, 600],
        "max_depth": [4, 8, None],
        "min_samples_leaf": [1, 5],
    },
}


def crear_pipeline(algoritmo: str, **hiper) -> Pipeline:
    categ = [v for v in VARIABLES if v in CATEGORICAS]
    contin = [v for v in VARIABLES if v not in CATEGORICAS]
    prepro = ColumnTransformer([
        ("continuas", Pipeline([
            ("escalar", StandardScaler()),
            ("imputar", KNNImputer(n_neighbors=5)),
        ]), contin),
        ("categoricas", SimpleImputer(strategy="most_frequent"), categ),
    ])
    if algoritmo == "xgboost":
        est = XGBClassifier(random_state=SEMILLA, eval_metric="logloss", n_jobs=-1, **hiper)
    else:
        est = RandomForestClassifier(random_state=SEMILLA, n_jobs=-1, **hiper)
    return Pipeline([("prepro", prepro), ("modelo", est)])


def entrenar_y_guardar(df: pd.DataFrame, desenlace: str, algoritmo: str, archivo_salida: str) -> None:
    datos = df.dropna(subset=[desenlace])
    ent = datos[datos["particion_temporal"] == "entrenamiento"]
    pru = datos[datos["particion_temporal"] == "prueba"]

    X_ent, y_ent = ent[VARIABLES].astype(float), ent[desenlace].astype(int)
    X_pru, y_pru = pru[VARIABLES].astype(float), pru[desenlace].astype(int)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEMILLA)
    claves = list(REJILLAS[algoritmo])
    combos = [dict(zip(claves, vals)) for vals in itertools.product(*REJILLAS[algoritmo].values())]

    mejor_auc, mejor_hiper = -1.0, {}
    for hiper in combos:
        auc = cross_val_score(crear_pipeline(algoritmo, **hiper), X_ent, y_ent, cv=cv, scoring="roc_auc", n_jobs=1).mean()
        if auc > mejor_auc:
            mejor_auc, mejor_hiper = float(auc), hiper

    pipe_final = crear_pipeline(algoritmo, **mejor_hiper).fit(X_ent, y_ent)
    p_ent = pipe_final.predict_proba(X_ent)[:, 1]
    p_pru = pipe_final.predict_proba(X_pru)[:, 1]

    artefacto = {
        "pipeline": pipe_final,
        "variables": VARIABLES,
        "desenlace": desenlace,
        "algoritmo": algoritmo,
        "hiperparametros": mejor_hiper,
        "umbrales": {
            "intermedio": float(np.quantile(p_ent, 0.50)),
            "alto": float(np.quantile(p_ent, 0.80)),
        },
        "metricas": {
            "auroc_cv": mejor_auc,
            "auroc_prueba": float(roc_auc_score(y_pru, p_pru)),
            "brier_prueba": float(brier_score_loss(y_pru, p_pru)),
        },
    }

    DIR_MODELOS.mkdir(parents=True, exist_ok=True)
    joblib.dump(artefacto, DIR_MODELOS / archivo_salida)
    print(f"[OK] {desenlace} ({algoritmo}) -> AUROC prueba: {artefacto['metricas']['auroc_prueba']:.3f} | Hiper: {mejor_hiper}")


def escribir_pyproject() -> None:
    contenido = f"""[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "modelo_uci"
version = "0.1.0"
description = "Paquete de modelos predictivos UCI Analytics - Grupo 17"
requires-python = ">=3.10"
dependencies = [
    "numpy=={np.__version__}",
    "pandas=={pd.__version__}",
    "scikit-learn=={sklearn.__version__}",
    "xgboost=={xgboost.__version__}",
    "joblib=={joblib.__version__}",
    "pydantic=={pydantic.__version__}",
]

[tool.setuptools.packages.find]
include = ["modelo_uci*"]

[tool.setuptools.package-data]
modelo_uci = ["modelos/*.joblib"]
"""
    (Path(__file__).resolve().parent / "pyproject.toml").write_text(contenido, encoding="utf-8")
    print("[OK] pyproject.toml generado.")


if __name__ == "__main__":
    df = pd.read_csv(RUTA_DATOS)
    entrenar_y_guardar(df, "estancia_prolongada", "xgboost", "modelo_estancia.joblib")
    entrenar_y_guardar(df, "mortality", "random_forest", "modelo_mortalidad.joblib")
    escribir_pyproject()
