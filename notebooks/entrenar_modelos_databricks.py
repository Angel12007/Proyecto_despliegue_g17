# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # G17 – Entrenamiento de modelos con MLflow en Databricks
# MAGIC
# MAGIC Este notebook usa `src/modelado.py` del repositorio, de modo que todos los integrantes entrenan con el mismo
# MAGIC preprocesamiento, la misma validación temporal y las mismas métricas.
# MAGIC
# MAGIC **Antes de correrlo**
# MAGIC 1. `modelado.py` debe estar en el mismo Volume que la base (o en `../src` si se usa el repositorio como Git folder).
# MAGIC 2. `dataset_modelado.csv` debe estar cargado en un Volume (por defecto `/Volumes/workspace/default/g17/`).
# MAGIC 3. Arriba, en los widgets, elija su modelo y el desenlace.

# COMMAND ----------

# MAGIC %pip install -q catboost xgboost

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.dropdown("modelo", "elegir", ["elegir", "logistica", "random_forest", "xgboost", "catboost"])
dbutils.widgets.dropdown("desenlace", "estancia_prolongada", ["estancia_prolongada", "mortality"])
dbutils.widgets.dropdown("variables", "tablero", ["tablero", "completo"])
dbutils.widgets.text("ruta_datos", "/Volumes/workspace/default/g17/dataset_modelado.csv")
dbutils.widgets.text("registrar_como", "")  # p. ej. workspace.default.g17_estancia (solo el modelo elegido)

# COMMAND ----------

import os
import sys

import mlflow

# Busca modelado.py en ../src (repositorio como Git folder) o en el Volume donde está la base
carpeta_nb = os.getcwd()
raiz_repo = os.path.abspath(os.path.join(carpeta_nb, ".."))
carpeta_volume = os.path.dirname(dbutils.widgets.get("ruta_datos"))
en_repo = os.path.exists(os.path.join(raiz_repo, "src", "modelado.py"))
sys.path.insert(0, os.path.join(raiz_repo, "src") if en_repo else carpeta_volume)
import modelado  # noqa: E402
print("modelado.py cargado desde:", modelado.__file__)

usuario = spark.sql("SELECT current_user()").first()[0]
experimento = f"/Users/{usuario}/G17_UCI_triage"
mlflow.set_registry_uri("databricks-uc")
print("Usuario:", usuario)
print("Experimento:", experimento)

# COMMAND ----------

if dbutils.widgets.get("modelo") == "elegir":
    dbutils.notebook.exit("Elija su modelo en el menú 'modelo' de arriba y vuelva a darle Run all.")

resultado = modelado.entrenar(
    modelo=dbutils.widgets.get("modelo"),
    desenlace=dbutils.widgets.get("desenlace"),
    variables=dbutils.widgets.get("variables"),
    datos=dbutils.widgets.get("ruta_datos"),
    experimento=experimento,
    autor=usuario,
    registrar_como=dbutils.widgets.get("registrar_como") or None,
)
resultado

# COMMAND ----------

# MAGIC %md
# MAGIC ## Comparar las corridas
# MAGIC Tabla de las corridas principales del experimento (una por modelo × desenlace × conjunto de variables).

# COMMAND ----------

corridas = mlflow.search_runs(experiment_names=[experimento])
if "tags.mlflow.parentRunId" in corridas.columns:
    corridas = corridas[corridas["tags.mlflow.parentRunId"].isna()]
    
columnas = ["tags.modelo", "tags.desenlace", "tags.variables", "metrics.cv_auroc_mejor",
            "metrics.test_auroc", "metrics.test_auroc_ic_inf", "metrics.test_auroc_ic_sup",
            "metrics.test_brier", "metrics.test_razon_esperado_observado",
            "metrics.test_pct_eventos_en_top20", "metrics.test_pct_dias_cama_en_top20",
            "metrics.test_auroc_saps3_mismos_pacientes"]
tabla = corridas[[c for c in columnas if c in corridas.columns]].sort_values("metrics.test_auroc", ascending=False)
display(tabla)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Guardar el resumen en el repositorio
# MAGIC Escribe `resultados_<usuario>.csv` en el Volume (o en `reports/modelos/` si se usa el Git folder).
# MAGIC Descárguelo y súbalo al repositorio en `reports/modelos/` (ver la guía).

# COMMAND ----------

carpeta = os.path.join(raiz_repo, "reports", "modelos") if en_repo else carpeta_volume
os.makedirs(carpeta, exist_ok=True)
nombre = usuario.split("@")[0].replace(".", "_")
salida = os.path.join(carpeta, f"resultados_{nombre}.csv")
tabla.rename(columns=lambda c: c.split(".", 1)[-1]).to_csv(salida, index=False)
print("Guardado:", salida)