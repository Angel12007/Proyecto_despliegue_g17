FROM python:3.12-slim

# Usuario sin privilegios que ejecuta la API
RUN adduser --disabled-password --gecos '' api-user

WORKDIR /opt/uci-api

# Dependencias (incluye el paquete del modelo modelo_uci .whl)
COPY ./requirements.txt /opt/uci-api/requirements.txt
COPY ./model-pkg /opt/uci-api/model-pkg
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Código de la API
COPY ./app /opt/uci-api/app
COPY ./run.sh /opt/uci-api/run.sh
RUN chmod +x run.sh && chown -R api-user:api-user ./

USER api-user
ENV PORT=8001
EXPOSE 8001

CMD ["bash", "./run.sh"]
