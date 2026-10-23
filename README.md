# Proyecto Despliegue G17 – Triage de riesgo al ingreso en UCI oncológica

Herramienta para estimar, en las primeras 24 horas de ingreso a una UCI de un hospital de cuarto nivel de atención oncológica, el riesgo de **muerte en UCI** y de **estancia prolongada (≥ 7 días)**. La herramienta se despliega como API con un tablero de capacidad.

Curso: Despliegue de Soluciones Analíticas – MIAD, Universidad de los Andes. Grupo 17.

## Qué contiene este repositorio

El cargue de la base y su procesamiento hasta dejar la **versión final para modelado**. Los datos no se guardan en Git: los versiona DVC con un remoto en S3.

```
├── data/
│   ├── raw/df_merged_final.xlsx.dvc   # base inicial (DVC)
│   ├── interim/                       # base cargada, tipos corregidos (DVC)
│   └── processed/                     # base final para modelado: dataset_modelado.csv (DVC)
├── src/
│   ├── cargar_datos.py        # etapa 1: lee el Excel, "Sin dato" → faltante, tipos numéricos
│   ├── procesar_datos.py      # etapa 2: variables clínicas, desenlaces y partición temporal
│   ├── clinical_features.py   # construcción de variables clínicas
│   └── preprocessing.py       # limpieza, duplicados y renombrado de variables
├── docs/                      # guía de Git y DVC
├── params.yaml                # umbral de estancia y fecha de corte temporal
├── dvc.yaml / dvc.lock        # pipeline reproducible
└── requirements.txt
```

## Cómo reproducirlo

```bash
git clone https://github.com/Angel12007/Proyecto_despliegue_g17.git
cd Proyecto_despliegue_g17
python -m venv .venv
.venv\Scripts\activate            # Windows (cmd)
# source .venv/bin/activate       # Linux / máquina virtual
pip install -r requirements.txt

# con credenciales vigentes de AWS Academy en ~/.aws/credentials
dvc pull      # descarga la base inicial y la final desde S3
dvc repro     # vuelve a correr cargar → procesar si algo cambió
```

## Decisiones de procesamiento

- **No se imputa sobre la base completa.** Los faltantes se dejan como están; la imputación (KNN para laboratorios y media para lo restante) se ajustará dentro del pipeline del modelo usando solo la partición de entrenamiento, para no pasar información de la prueba al entrenamiento.
- Se eliminan reingresos duplicados: queda el primer ingreso de cada paciente.
- Desenlaces codificados 0/1, con 1 = evento: `mortality` (muerte en UCI), `death_30d` (muerte a 30 días), `estancia_prolongada` (≥ 7 días) y `muerte_o_estancia_prolongada`.
- `particion_temporal`: ingresos antes del 1 de julio de 2024 = entrenamiento (n = 816); desde esa fecha = prueba (n = 181). La fecha y el umbral de estancia se cambian en `params.yaml`.

## Datos

997 pacientes con cáncer ingresados a la UCI entre julio de 2022 y agosto de 2025. La base está anonimizada.

## Licencia y origen

La base y las funciones de `clinical_features.py` y `preprocessing.py` provienen de un repositorio previo del equipo investigador, publicado bajo licencia CC BY 4.0 (ver `LICENSE_codigo_articulo.txt`).
