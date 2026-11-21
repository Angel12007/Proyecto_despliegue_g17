# UCI Analytics – Triage de riesgo al ingreso en UCI oncológica (Grupo 17)

Herramienta que estima, con la información de las primeras 24 horas, el riesgo de **estancia en UCI ≥ 7 días** (desenlace principal) y de **muerte en UCI** (secundario) en pacientes oncológicos de un hospital de cuarto nivel, y traduce esas probabilidades en días-cama y costos de referencia para planificar camas.

Curso: Despliegue de Soluciones Analíticas – MIAD, Universidad de los Andes.

## Enlaces

| Componente | Dirección |
|---|---|
| API (documentación interactiva) | https://proyectodespliegueg17-production.up.railway.app/docs |
| Tablero | [pendiente: URL del tablero en Railway] |
| Datos (remoto DVC) | `s3://proyecto-g17-dvc-2026/datos` |

## Arquitectura

```
dataset (DVC) ──► experimentos MLflow (Databricks) ──► paquete modelo_uci (.whl)
                                                            │
Navegador ──► Tablero Dash (Docker) ──HTTP──► API FastAPI (Docker) ──┘
```

## Estructura

```
├── data/                 # base inicial, cargada y final (versionadas con DVC en S3)
├── src/                  # cargue, procesamiento y exploración (etapas DVC)
├── reports/eda/          # resultados de la exploración
├── experimentos/         # entrenamiento y resultados en MLflow (Databricks)
│   ├── logistica_random_forest/
│   ├── xgboost_catboost/
│   └── resultados/       # tablas de las 16 corridas
├── paquete_modelo/       # paquete modelo_uci: XGBoost (estancia) y Random Forest (mortalidad), 14 variables
├── api/                  # API FastAPI que sirve el paquete (Dockerfile)
├── tablero/              # tablero Dash que consume la API (Dockerfile)
├── docs/                 # guías y manuales
├── dvc.yaml · dvc.lock · params.yaml
└── docker-compose.yml    # API + tablero en una máquina con Docker
```

## Modelos desplegados

| Desenlace | Modelo | Variables | AUROC (prueba temporal) |
|---|---|---|---|
| Estancia ≥ 7 días | XGBoost | 14 | 0,898 |
| Muerte en UCI | Random Forest | 14 | 0,937 |

Validación temporal: entrenamiento con ingresos hasta junio de 2024 (816 pacientes) y prueba con los posteriores (181). Las 14 variables son las del formulario del tablero: edad, APACHE II, SAPS III, SOFA, lactato, PaO2/FiO2, plaquetas, soporte ventilatorio, vasopresores, choque, sepsis, ECOG, origen del tumor y tipo de ingreso.

## Reproducir

```bash
pip install -r requirements.txt
dvc pull            # base desde S3 (requiere credenciales de AWS Academy)
dvc repro           # cargar → procesar → explorar
```

`data/processed/dataset_modelado.csv` también está en Git (con `cache: false` en DVC) porque el tablero desplegado en Railway lo necesita y Railway no puede hacer `dvc pull`.

## Documentación

| Documento | Contenido |
|---|---|
| [docs/manual_instalacion.md](docs/manual_instalacion.md) | Despliegue de la API y el tablero |
| [docs/manual_usuario.md](docs/manual_usuario.md) | Uso del tablero |

## Origen de los datos

La base anonimizada y las funciones de `src/clinical_features.py` y `src/preprocessing.py` provienen de un repositorio previo del equipo investigador, publicado bajo licencia CC BY 4.0 (ver `LICENSE_codigo_articulo.txt`).
