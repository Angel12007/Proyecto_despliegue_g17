# Se construye desde la raíz del repositorio:
#   docker build -f tablero/Dockerfile -t uci-tablero .
FROM python:3.12-slim

RUN adduser --disabled-password --gecos '' dash-user

WORKDIR /opt/tablero

COPY tablero/requirements.txt /opt/tablero/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Código del tablero y base final (traída con `dvc pull` antes de construir)
COPY tablero/ /opt/tablero/
COPY data/processed/dataset_modelado.csv /opt/tablero/data/dataset_modelado.csv
RUN chmod +x run.sh && chown -R dash-user:dash-user ./

USER dash-user
ENV PORT=8050 \
    RUTA_DATOS=/opt/tablero/data/dataset_modelado.csv \
    API_URL=http://api:8001
EXPOSE 8050

CMD ["bash", "./run.sh"]
