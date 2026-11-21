# Experimentos (MLflow en Databricks)

Entrenamiento y comparación de modelos para los dos desenlaces, registrados en MLflow en el experimento `G17_UCI_triage`.

| Carpeta | Modelos | Responsable |
|---|---|---|
| `logistica_random_forest/` | Regresión logística y Random Forest | Ángel Hernández |
| `xgboost_catboost/` | XGBoost y CatBoost | Alejandro Ardila |
| `resultados/` | Métricas de las 16 corridas (4 modelos × 2 desenlaces × 2 conjuntos de variables) | — |

`modelado.py` es el módulo común: validación temporal, preprocesamiento dentro del pipeline (estandarización + KNN para continuas, moda para categóricas), búsqueda de hiperparámetros con validación cruzada de 5 pliegues y métricas en prueba (AUROC con IC 95 %, Brier, calibración, razón esperado/observado y concentración de días-cama en el 20 % de mayor riesgo).

Modelos elegidos para el despliegue (con las 14 variables del tablero): XGBoost para estancia ≥ 7 días y Random Forest para muerte en UCI. Ver `paquete_modelo/`.
