"""Entrenamiento y evaluación de modelos con registro en MLflow.

Un solo módulo para que todo el equipo entrene igual y los resultados sean
comparables entre modelos:

  - Datos: data/processed/dataset_modelado.csv (salida de la etapa `procesar`).
  - Validación temporal: se ajusta con `particion_temporal == "entrenamiento"`
    (ingresos antes del 1-jul-2024) y se evalúa una sola vez en "prueba".
  - Preprocesamiento dentro del pipeline: estandarización + imputación KNN
    para continuas y moda para categóricas, ajustadas solo con entrenamiento.
  - Búsqueda de hiperparámetros con validación cruzada estratificada de 5
    pliegues dentro de entrenamiento (métrica: AUROC). Cada combinación queda
    como una corrida hija en MLflow; la corrida madre guarda el mejor modelo
    evaluado en prueba.

Uso local (registra en ./mlruns o en el servidor que indique
MLFLOW_TRACKING_URI):

    python src/modelado.py --modelo catboost --desenlace estancia_prolongada --variables tablero

En Databricks se usa desde notebooks/entrenar_modelos_databricks.py.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from sklearn.base import clone
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             roc_auc_score, roc_curve)
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SEMILLA = 42
RAIZ = Path(__file__).resolve().parents[1]
RUTA_DATOS = RAIZ / "data" / "processed" / "dataset_modelado.csv"

DESENLACES = {
    "estancia_prolongada": "Estancia en UCI >= 7 días",
    "mortality": "Muerte en UCI",
}

# Columnas que no son predictores: identificadores, fechas, desenlaces y
# escalas de mortalidad esperada (se usan solo para comparar).
NO_PREDICTORES = [
    "record_id", "fecha_ingreso", "dias_estancia", "particion_temporal",
    "mort_esperada_saps3", "mort_esperada_apache",
    "mortality", "death_30d", "estancia_prolongada", "muerte_o_estancia_prolongada",
]

# Variables que el tablero pide al usuario (disponibles en las primeras 24 h).
VARIABLES_TABLERO = [
    "age", "apacheii", "sapsiii", "sofa", "lactate", "pafi", "platelet",
    "ventilatory_support", "vasopressors_use", "shock", "sepsis", "ecog",
    "origin_of_tumor", "type_of_admission",
]

# Variables con pocos valores posibles: se imputan con la moda, no con KNN.
CATEGORICAS = [
    "sex", "type_of_admission", "ecog", "shock", "sepsis", "support renal",
    "vasopressors_use", "sedatives_use", "painkillers_use", "methylene_blue_use",
    "delirium", "Sequ_mol_fish_study", "icu_readmission", "origin_of_tumor",
    "staging_risk", "ventilatory_support", "oncological_treatment",
]

# Rejillas de hiperparámetros. Cada combinación es una corrida hija en MLflow.
REJILLAS = {
    "logistica": {"C": [0.01, 0.1, 1.0], "class_weight": [None, "balanced"]},
    "random_forest": {"n_estimators": [300, 600], "max_depth": [4, 8, None],
                      "min_samples_leaf": [1, 5]},
    "xgboost": {"n_estimators": [200, 500], "max_depth": [3, 5],
                "learning_rate": [0.03, 0.1]},
    "catboost": {"iterations": [500, 1000], "depth": [4, 6],
                 "learning_rate": [0.03, 0.1]},
}


# ----------------------------------------------------------------------------
# Datos
# ----------------------------------------------------------------------------
def cargar_datos(ruta: str | Path = RUTA_DATOS) -> pd.DataFrame:
    return pd.read_csv(ruta)


def seleccionar_variables(df: pd.DataFrame, conjunto: str) -> list[str]:
    if conjunto == "tablero":
        return list(VARIABLES_TABLERO)
    if conjunto == "completo":
        return [c for c in df.columns if c not in NO_PREDICTORES]
    raise ValueError("conjunto debe ser 'tablero' o 'completo'")


def particionar(df: pd.DataFrame, desenlace: str, variables: list[str]):
    datos = df.dropna(subset=[desenlace])
    ent = datos[datos["particion_temporal"] == "entrenamiento"]
    pru = datos[datos["particion_temporal"] == "prueba"]
    return (ent[variables].astype(float), ent[desenlace].astype(int),
            pru[variables].astype(float), pru[desenlace].astype(int), pru)


# ----------------------------------------------------------------------------
# Modelos
# ----------------------------------------------------------------------------
def crear_estimador(modelo: str, **hiper):
    if modelo == "logistica":
        return LogisticRegression(max_iter=5000, random_state=SEMILLA, **hiper)
    if modelo == "random_forest":
        return RandomForestClassifier(random_state=SEMILLA, n_jobs=-1, **hiper)
    if modelo == "xgboost":
        from xgboost import XGBClassifier
        return XGBClassifier(random_state=SEMILLA, eval_metric="logloss", n_jobs=-1, **hiper)
    if modelo == "catboost":
        from catboost import CatBoostClassifier
        return CatBoostClassifier(random_seed=SEMILLA, verbose=0, allow_writing_files=False, **hiper)
    raise ValueError(f"Modelo no reconocido: {modelo}")


def crear_pipeline(modelo: str, variables: list[str], **hiper) -> Pipeline:
    categ = [v for v in variables if v in CATEGORICAS]
    contin = [v for v in variables if v not in CATEGORICAS]
    prepro = ColumnTransformer([
        ("continuas", Pipeline([("escalar", StandardScaler()),
                                ("imputar", KNNImputer(n_neighbors=5))]), contin),
        ("categoricas", SimpleImputer(strategy="most_frequent"), categ),
    ])
    return Pipeline([("prepro", prepro), ("modelo", crear_estimador(modelo, **hiper))])


def combinaciones(rejilla: dict) -> list[dict]:
    claves = list(rejilla)
    return [dict(zip(claves, valores)) for valores in itertools.product(*rejilla.values())]


# ----------------------------------------------------------------------------
# Métricas
# ----------------------------------------------------------------------------
def auroc_ic(y, p, n=1000, semilla=SEMILLA):
    rng = np.random.default_rng(semilla)
    y, p = np.asarray(y), np.asarray(p)
    valores = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        if y[i].min() != y[i].max():
            valores.append(roc_auc_score(y[i], p[i]))
    return roc_auc_score(y, p), np.percentile(valores, 2.5), np.percentile(valores, 97.5)


def calibracion(y, p):
    """Intercepto y pendiente de calibración (regresión logística sobre el logit)."""
    p = np.clip(p, 1e-6, 1 - 1e-6)
    logit = np.log(p / (1 - p)).reshape(-1, 1)
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(logit, y)
    return float(lr.intercept_[0]), float(lr.coef_[0, 0])


def metricas_negocio(prueba: pd.DataFrame, p, desenlace: str, fraccion=0.20) -> dict:
    """Qué parte de los eventos y de los días-cama cae en el 20 % de mayor riesgo."""
    df = prueba.assign(riesgo=p).sort_values("riesgo", ascending=False)
    top = df.head(int(np.ceil(len(df) * fraccion)))
    res = {"pct_eventos_en_top20": 100 * top[desenlace].sum() / df[desenlace].sum()}
    if "dias_estancia" in df:
        res["pct_dias_cama_en_top20"] = 100 * top["dias_estancia"].sum() / df["dias_estancia"].sum()
    return res


def evaluar(y, p, prueba: pd.DataFrame, desenlace: str) -> dict:
    auc, li, ls = auroc_ic(y, p)
    inter, pend = calibracion(y, p)
    m = {
        "test_auroc": auc, "test_auroc_ic_inf": li, "test_auroc_ic_sup": ls,
        "test_auprc": average_precision_score(y, p),
        "test_brier": brier_score_loss(y, p),
        "test_calib_intercepto": inter, "test_calib_pendiente": pend,
        "test_prob_media": float(np.mean(p)), "test_tasa_observada": float(np.mean(y)),
        "test_razon_esperado_observado": float(np.mean(p) / np.mean(y)),
    }
    m.update({f"test_{k}": v for k, v in metricas_negocio(prueba, p, desenlace).items()})
    # Comparación con SAPS III en los mismos pacientes de prueba
    saps = prueba["sapsiii"]
    ok = saps.notna().to_numpy()
    if ok.sum() > 20:
        m["test_auroc_saps3_mismos_pacientes"] = roc_auc_score(np.asarray(y)[ok], saps[ok])
        m["test_auroc_modelo_mismos_pacientes"] = roc_auc_score(np.asarray(y)[ok], np.asarray(p)[ok])
    return {k: float(v) for k, v in m.items()}


# ----------------------------------------------------------------------------
# Gráficas
# ----------------------------------------------------------------------------
def graficar(y, p, titulo: str, carpeta: Path) -> list[Path]:
    rutas = []
    fpr, tpr, _ = roc_curve(y, p)
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    ax.plot(fpr, tpr, lw=2, label=f"AUROC {roc_auc_score(y, p):.3f}")
    ax.plot([0, 1], [0, 1], "--", color="grey")
    ax.set(xlabel="1 - especificidad", ylabel="Sensibilidad", title=f"ROC – {titulo}")
    ax.legend(loc="lower right")
    fig.tight_layout(); rutas.append(carpeta / "roc_prueba.png"); fig.savefig(rutas[-1], dpi=130); plt.close(fig)

    obs, pred = calibration_curve(y, p, n_bins=8, strategy="quantile")
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    ax.plot(pred, obs, "o-", lw=2)
    ax.plot([0, 1], [0, 1], "--", color="grey")
    lim = max(pred.max(), obs.max()) * 1.1
    ax.set(xlim=(0, lim), ylim=(0, lim), xlabel="Probabilidad predicha",
           ylabel="Frecuencia observada", title=f"Calibración – {titulo}")
    fig.tight_layout(); rutas.append(carpeta / "calibracion_prueba.png"); fig.savefig(rutas[-1], dpi=130); plt.close(fig)
    return rutas


def importancia(pipe, X, y, carpeta: Path) -> Path:
    r = permutation_importance(pipe, X, y, scoring="roc_auc", n_repeats=5, random_state=SEMILLA, n_jobs=-1)
    imp = (pd.DataFrame({"variable": X.columns, "importancia": r.importances_mean, "de": r.importances_std})
           .sort_values("importancia", ascending=False))
    imp.to_csv(carpeta / "importancia_permutacion.csv", index=False)
    top = imp.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(5, 4.5))
    ax.barh(top["variable"], top["importancia"], xerr=top["de"], color="#2c7fb8")
    ax.set(xlabel="Caída de AUROC al permutar (prueba)", title="Importancia por permutación")
    fig.tight_layout(); fig.savefig(carpeta / "importancia_permutacion.png", dpi=130); plt.close(fig)
    return carpeta


# ----------------------------------------------------------------------------
# Entrenamiento con MLflow
# ----------------------------------------------------------------------------
def entrenar(modelo: str, desenlace: str, variables: str = "tablero",
             datos: str | Path | pd.DataFrame = RUTA_DATOS,
             experimento: str = "G17_UCI_triage", autor: str | None = None,
             registrar_como: str | None = None, guardar_en: str | Path | None = None) -> dict:
    """Busca hiperparámetros con CV en entrenamiento, evalúa en prueba y registra todo en MLflow."""
    df = datos if isinstance(datos, pd.DataFrame) else cargar_datos(datos)
    cols = seleccionar_variables(df, variables)
    X_ent, y_ent, X_pru, y_pru, prueba = particionar(df, desenlace, cols)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEMILLA)

    mlflow.set_experiment(experimento)
    nombre = f"{modelo} | {desenlace} | {variables}"
    etiquetas = {"modelo": modelo, "desenlace": desenlace, "variables": variables,
                 "autor": autor or os.environ.get("USER") or os.environ.get("USERNAME", "sin_dato")}

    with mlflow.start_run(run_name=nombre, tags=etiquetas) as madre:
        mlflow.log_params({"modelo": modelo, "desenlace": desenlace, "conjunto_variables": variables,
                           "n_variables": len(cols), "n_entrenamiento": len(y_ent), "n_prueba": len(y_pru),
                           "eventos_entrenamiento": int(y_ent.sum()), "eventos_prueba": int(y_pru.sum()),
                           "validacion": "temporal (corte 2024-07-01) + CV 5 pliegues en entrenamiento"})

        resultados = []
        for hiper in combinaciones(REJILLAS[modelo]):
            with mlflow.start_run(run_name=f"{modelo} {hiper}", nested=True, tags=etiquetas):
                pipe = crear_pipeline(modelo, cols, **hiper)
                aucs = cross_val_score(pipe, X_ent, y_ent, cv=cv, scoring="roc_auc", n_jobs=1)
                mlflow.log_params(hiper)
                mlflow.log_metrics({"cv_auroc_media": aucs.mean(), "cv_auroc_de": aucs.std()})
                resultados.append({**hiper, "cv_auroc_media": aucs.mean(), "cv_auroc_de": aucs.std()})
                print(f"  {hiper} -> AUROC CV {aucs.mean():.3f} ± {aucs.std():.3f}")

        tabla = pd.DataFrame(resultados).sort_values("cv_auroc_media", ascending=False)
        mejor = {}
        for k in REJILLAS[modelo]:
            v = tabla.iloc[0][k]
            v = v.item() if hasattr(v, "item") else v
            if isinstance(v, float) and np.isnan(v):
                v = None
            elif isinstance(v, float) and v.is_integer() and k != "C":
                v = int(v)
            mejor[k] = v

        final = crear_pipeline(modelo, cols, **mejor).fit(X_ent, y_ent)
        p = final.predict_proba(X_pru)[:, 1]
        met = evaluar(y_pru, p, prueba, desenlace)
        met["cv_auroc_mejor"] = float(tabla.iloc[0]["cv_auroc_media"])

        mlflow.log_params({f"mejor_{k}": v for k, v in mejor.items()})
        mlflow.log_metrics(met)

        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            tabla.to_csv(carpeta / "busqueda_hiperparametros.csv", index=False)
            pd.DataFrame({"record_id": prueba["record_id"], "y": y_pru.values, "prob": p}).to_csv(
                carpeta / "predicciones_prueba.csv", index=False)
            graficar(y_pru, p, f"{DESENLACES[desenlace]} ({modelo})", carpeta)
            importancia(final, X_pru, y_pru, carpeta)
            (carpeta / "variables.json").write_text(json.dumps(cols, ensure_ascii=False, indent=1))
            mlflow.log_artifacts(str(carpeta), artifact_path="evaluacion")

        args_modelo = dict(
            serialization_format="cloudpickle",
            signature=infer_signature(X_ent.head(20), final.predict_proba(X_ent.head(20))[:, 1]),
            input_example=X_ent.head(3), registered_model_name=registrar_como)
        if int(mlflow.__version__.split(".")[0]) >= 3:
            mlflow.sklearn.log_model(final, name="modelo", **args_modelo)
        else:  # MLflow 2.x (algunos entornos de Databricks)
            mlflow.sklearn.log_model(final, artifact_path="modelo", **args_modelo)

        if guardar_en:
            import joblib
            Path(guardar_en).parent.mkdir(parents=True, exist_ok=True)
            joblib.dump({"pipeline": final, "variables": cols, "desenlace": desenlace,
                         "modelo": modelo, "hiperparametros": mejor, "metricas_prueba": met}, guardar_en)

        print(f"\n{nombre}: mejor {mejor}")
        print(f"  AUROC CV {met['cv_auroc_mejor']:.3f} | AUROC prueba {met['test_auroc']:.3f} "
              f"({met['test_auroc_ic_inf']:.3f}-{met['test_auroc_ic_sup']:.3f}) | Brier {met['test_brier']:.3f} "
              f"| E/O {met['test_razon_esperado_observado']:.2f}")
        return {"run_id": madre.info.run_id, "mejores_hiperparametros": mejor, **met}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modelo", required=True, choices=list(REJILLAS))
    ap.add_argument("--desenlace", required=True, choices=list(DESENLACES))
    ap.add_argument("--variables", default="tablero", choices=["tablero", "completo"])
    ap.add_argument("--experimento", default="G17_UCI_triage")
    ap.add_argument("--autor", default=None)
    ap.add_argument("--guardar-en", default=None, help="ruta .joblib para usar el modelo en el tablero")
    a = ap.parse_args()
    entrenar(a.modelo, a.desenlace, a.variables, experimento=a.experimento,
             autor=a.autor, guardar_en=a.guardar_en)


if __name__ == "__main__":
    main()
