# Tablero UCI Analytics

Aplicación en Dash con tres pantallas:

| Pantalla | Para qué sirve |
|---|---|
| **Predicción individual** | Con los datos de las primeras 24 h, estima la probabilidad de estancia ≥ 7 días y de muerte en UCI, la categoría de riesgo, los días y el costo de referencia esperados, y qué datos del paciente mueven más el riesgo. Permite agregar el paciente a "Mi lista". |
| **Planificación de camas** | Lista de pacientes ordenada por riesgo, con días-cama, estancias prolongadas y costo esperados. Tres fuentes: censo histórico de un día, ingresos de un periodo (comparando lo esperado con lo real) y "Mi lista" (CSV con la plantilla o pacientes agregados desde la predicción). |
| **Capacidad y costos** | Indicadores con filtros (origen del tumor, tipo de ingreso, fechas), costo de referencia total, de las estancias prolongadas y del 20 % de mayor riesgo, concentración de días-cama del modelo frente a SAPS III, días-cama por grupo de riesgo y tendencia por semestre. Las tarifas se pueden editar. |

## Cómo correrlo

Desde la carpeta principal del repositorio, con el entorno activado:

```cmd
pip install -r requirements-tablero.txt
dvc repro modelo_tablero
python tablero/app.py
```

Abrir http://127.0.0.1:8050 en el navegador.

`dvc repro modelo_tablero` crea el modelo provisional en `models/` si no existe. Sin DVC también funciona: `python tablero/preparar_modelo_provisional.py`.

## Archivos

| Archivo | Contenido |
|---|---|
| `app.py` | Pantallas y callbacks |
| `servicio_modelo.py` | Predicciones, categorías de riesgo, explicación por paciente, días esperados y tarifas. En la entrega 3 se cambia para llamar a la API. |
| `datos.py` | Censo por fecha, ingresos por periodo, indicadores y curvas |
| `config.py` | Variables del formulario, tarifas y rutas |
| `preparar_modelo_provisional.py` | Regresión logística provisional mientras el equipo elige el modelo final |
| `assets/estilos.css` | Estilos según la maqueta |

## Supuestos

- **Modelo:** regresión logística provisional, entrenada con los ingresos anteriores al 1-jul-2024. Se reemplaza por el modelo elegido en MLflow, guardado con el mismo formato en `models/`.
- **Riesgo alto:** probabilidad en el 20 % superior de la cohorte de entrenamiento. Intermedio: entre la mediana y ese corte.
- **Días esperados:** p × estancia media de quienes se quedan ≥ 7 días + (1 − p) × estancia media de los demás (cohorte de entrenamiento). En el censo se ajustan por los días que el paciente ya lleva.
- **Costos de referencia:** Resolución 1068 de 2020: $2.458.848 por día de UCI adulto (pacientes con soporte ventilatorio en 24 h) y $1.921.669 por día de cuidado intermedio adulto (los demás), pesos de 2020. No son costos reales del hospital.
- **Explicación por paciente:** cambio en la probabilidad al reemplazar cada dato por la mediana de la cohorte.
- **Censo:** la cohorte es una parte de los ingresos de la UCI, por eso el censo reconstruido es menor que las 28 camas.
