import json
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from loguru import logger
from modelo_uci import __version__ as model_version
from modelo_uci.predict import info_modelos, make_prediction

from app import __version__, schemas
from app.config import settings

api_router = APIRouter()


@api_router.get("/health", response_model=schemas.Health, status_code=200)
def health() -> dict:
    """Verifica que la API esté en ejecución y muestra las versiones."""
    return schemas.Health(name=settings.PROJECT_NAME, api_version=__version__,
                          model_version=model_version).model_dump()


@api_router.get("/model-info", status_code=200)
def model_info() -> dict:
    """Algoritmo, hiperparámetros, métricas en prueba y umbrales de riesgo de cada modelo."""
    return info_modelos()


@api_router.post("/predict", response_model=schemas.PredictionResults, status_code=200)
async def predict(input_data: schemas.MultipleDataInputs) -> Any:
    """Probabilidad y categoría de riesgo de estancia >= 7 días y de muerte en UCI."""
    input_df = pd.DataFrame(jsonable_encoder(input_data.inputs))
    logger.info(f"Predicción para {len(input_df)} paciente(s)")
    results = make_prediction(input_data=input_df)
    if results["errors"] is not None:
        logger.warning(f"Error de validación: {results['errors']}")
        raise HTTPException(status_code=400, detail=json.loads(results["errors"]))
    return results
