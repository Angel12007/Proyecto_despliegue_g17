# API UCI Analytics

API en FastAPI que sirve los modelos del paquete `modelo_uci` (archivo `.whl` en `model-pkg/`).

| Ruta | Método | Para qué |
|---|---|---|
| `/` | GET | Página de inicio |
| `/docs` | GET | Documentación interactiva (Swagger) |
| `/api/v1/health` | GET | Estado y versiones de la API y del modelo |
| `/api/v1/model-info` | GET | Algoritmo, hiperparámetros, métricas y umbrales de riesgo |
| `/api/v1/predict` | POST | Probabilidad y categoría de riesgo de estancia ≥ 7 días y de muerte en UCI |

Ejemplo de solicitud a `/api/v1/predict`:

```json
{"inputs": [{"age": 65, "origin_of_tumor": 1, "type_of_admission": 1, "ecog": 2,
             "apacheii": 18, "sapsiii": 47, "sofa": 6, "lactate": 2.1, "pafi": 220,
             "platelet": 180000, "ventilatory_support": 1, "vasopressors_use": 0,
             "shock": 1, "sepsis": 1}]}
```

Respuesta:

```json
{"errors": null, "version": "0.1.0",
 "predictions": [{"p_estancia": 0.17, "riesgo_estancia": "Intermedio",
                  "p_muerte": 0.16, "riesgo_muerte": "Intermedio"}]}
```

Todos los campos son opcionales (los faltantes se imputan). Un valor fuera de rango responde 422.

## Correr localmente

```bash
cd api
pip install -r test_requirements.txt
python -m pytest app/tests
uvicorn app.main:app --port 8001
```

## Docker

```bash
docker build -t uci-api:1.0.0 ./api
docker run -d -p 8001:8001 --name uci-api uci-api:1.0.0
```
