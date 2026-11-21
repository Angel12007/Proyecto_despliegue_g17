
# Modelos XGBoost y CatBoost - Alejandro Ardila

Esta carpeta contiene los archivos asociados al entrenamiento
y evaluación de XGBoost y CatBoost para el proyecto G17.

## Archivos
- entrenar_modelos_databricks.ipynb: notebook de ejecución en Databricks.
- modelado.py: módulo de modelado utilizado por el notebook.
- resultados_alejandro.csv: resultados de los experimentos.

## Experimentos
Se evaluaron ocho configuraciones combinando:
- XGBoost y CatBoost.
- Estancia prolongada y mortalidad en UCI.
- Variables del tablero y conjunto completo.

Las métricas y ejecuciones se registraron en MLflow
dentro del experimento G17_UCI_triage.
