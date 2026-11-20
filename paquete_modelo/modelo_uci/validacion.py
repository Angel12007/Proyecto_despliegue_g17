from typing import Optional
from pydantic import BaseModel, Field


class EntradaPaciente(BaseModel):
    age: Optional[float] = Field(default=None, ge=18, le=110)
    origin_of_tumor: Optional[int] = Field(default=None, ge=0, le=1)
    type_of_admission: Optional[int] = Field(default=None, ge=1, le=2)
    ecog: Optional[int] = Field(default=None, ge=1, le=5)
    apacheii: Optional[float] = Field(default=None, ge=0, le=71)
    sapsiii: Optional[float] = Field(default=None, ge=0, le=217)
    sofa: Optional[float] = Field(default=None, ge=0, le=24)
    lactate: Optional[float] = Field(default=None, ge=0, le=30)
    pafi: Optional[float] = Field(default=None, ge=20, le=700)
    platelet: Optional[float] = Field(default=None, ge=0, le=2_000_000)
    ventilatory_support: Optional[int] = Field(default=None, ge=0, le=1)
    vasopressors_use: Optional[int] = Field(default=None, ge=0, le=1)
    shock: Optional[int] = Field(default=None, ge=1, le=2)
    sepsis: Optional[int] = Field(default=None, ge=1, le=2)
