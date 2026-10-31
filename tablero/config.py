"""Parámetros del tablero UCI Analytics."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RUTA_DATOS = RAIZ / "data" / "processed" / "dataset_modelado.csv"
CARPETA_MODELOS = RAIZ / "models"
MODELOS = {
    "estancia_prolongada": CARPETA_MODELOS / "modelo_estancia.joblib",
    "mortality": CARPETA_MODELOS / "modelo_mortalidad.joblib",
}

UMBRAL_ESTANCIA = 7  # días
FRACCION_ALTO_RIESGO = 0.20  # meta de negocio: 20 % de mayor riesgo

# Tarifas de referencia: Resolución 1068 de 2020, Ministerio de Salud, art. 3 (pesos de 2020).
# Supuesto del equipo: tarifa UCI adulto para pacientes con soporte ventilatorio en las
# primeras 24 h; tarifa de cuidado intermedio adulto para los demás.
TARIFA_UCI = 2_458_848
TARIFA_INTERMEDIO = 1_921_669
FUENTE_TARIFAS = ("Resolución 1068 de 2020 (MinSalud), art. 3: UCI adulto $2.458.848 y cuidado "
                  "intermedio adulto $1.921.669 por día, pesos de 2020. Tarifa definida para COVID-19 "
                  "bajo control del CRUE; no incluye comorbilidades. Se usa solo como referencia.")

# Variables que pide el formulario: (columna, etiqueta, tipo, opciones o rango)
CAMPOS = [
    ("age", "Edad (años)", "num", (18, 100)),
    ("origin_of_tumor", "Origen del tumor", "cat", {"Sólido": 1, "Hematológico": 0}),
    ("type_of_admission", "Tipo de ingreso", "cat", {"Médico": 1, "Quirúrgico": 2}),
    ("ecog", "ECOG (codificación de la base, 1–5)", "cat", {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5}),
    ("apacheii", "APACHE II", "num", (0, 71)),
    ("sapsiii", "SAPS III", "num", (0, 217)),
    ("sofa", "SOFA", "num", (0, 24)),
    ("lactate", "Lactato (mmol/L)", "num", (0, 30)),
    ("pafi", "PaO2/FiO2", "num", (20, 700)),
    ("platelet", "Plaquetas (/µL)", "num", (0, 2_000_000)),
    ("ventilatory_support", "Soporte ventilatorio en 24 h", "cat", {"No": 0, "Sí": 1}),
    ("vasopressors_use", "Vasopresores", "cat", {"No": 0, "Sí": 1}),
    ("shock", "Choque", "cat", {"No": 1, "Sí": 2}),
    ("sepsis", "Sepsis", "cat", {"No": 1, "Sí": 2}),
]
VARIABLES = [c[0] for c in CAMPOS]
ETIQUETAS = {c[0]: c[1] for c in CAMPOS}

GRUPOS_FORMULARIO = [
    ("Paciente", ["age", "origin_of_tumor", "type_of_admission", "ecog"]),
    ("Escalas de gravedad", ["apacheii", "sapsiii", "sofa"]),
    ("Laboratorio", ["lactate", "pafi", "platelet"]),
    ("Soportes y condiciones en 24 h", ["ventilatory_support", "vasopressors_use", "shock", "sepsis"]),
]

# Paciente de ejemplo (el de la maqueta, completado)
EJEMPLO = {"age": 65, "origin_of_tumor": 1, "type_of_admission": 1, "ecog": 2, "apacheii": 18,
           "sapsiii": 47, "sofa": 6, "lactate": 2.1, "pafi": 220, "platelet": 180000,
           "ventilatory_support": 1, "vasopressors_use": 0, "shock": 1, "sepsis": 1}
