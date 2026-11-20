from typing import Any, List, Optional

from modelo_uci.validacion import EntradaPaciente
from pydantic import BaseModel, ConfigDict


class Prediccion(BaseModel):
    p_estancia: float
    riesgo_estancia: str
    p_muerte: float
    riesgo_muerte: str


class PredictionResults(BaseModel):
    errors: Optional[Any] = None
    version: str
    predictions: Optional[List[Prediccion]] = None


class MultipleDataInputs(BaseModel):
    inputs: List[EntradaPaciente]

    model_config = ConfigDict(json_schema_extra={
        "example": {"inputs": [{
            "age": 65, "origin_of_tumor": 1, "type_of_admission": 1, "ecog": 2,
            "apacheii": 18, "sapsiii": 47, "sofa": 6, "lactate": 2.1, "pafi": 220,
            "platelet": 180000, "ventilatory_support": 1, "vasopressors_use": 0,
            "shock": 1, "sepsis": 1}]}
    })
