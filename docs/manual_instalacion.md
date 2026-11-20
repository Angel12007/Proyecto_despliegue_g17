# Manual de instalación – UCI Analytics (API + tablero)

La solución tiene dos contenedores Docker que corren en una máquina AWS EC2:

| Contenedor | Contenido | Puerto |
|---|---|---|
| `uci-api` | API FastAPI con el paquete `modelo_uci` (XGBoost para estancia, Random Forest para mortalidad) | 8001 |
| `uci-tablero` | Tablero Dash; consulta la API para todas las predicciones | 8050 |

```
Navegador ──► Tablero (8050) ──HTTP──► API (8001) ──► modelo_uci (.whl)
```

## 1. Requisitos

- Cuenta de AWS Academy (Learner Lab).
- Credenciales de lectura del bucket S3 del proyecto (para `dvc pull`).
- Una instancia EC2 Ubuntu 22.04 o 24.04, tipo **t2.medium** o superior, disco de 20 GB.

## 2. Crear la máquina EC2

1. Consola de AWS → **EC2** → **Launch instance**.
2. Nombre `uci-analytics-g17`, imagen **Ubuntu**, tipo **t2.medium**, par de llaves `vockey` (o el suyo), disco **20 GB**.
3. **Security group**: agregar reglas de entrada **TCP 22** (SSH), **TCP 8001** (API) y **TCP 8050** (tablero), origen `0.0.0.0/0`.
4. **Launch instance** y anotar la **IP pública**.

## 3. Instalar Docker y Git en la máquina

Conectarse por SSH (`ssh -i labsuser.pem ubuntu@<IP_PUBLICA>`) y correr:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git python3-venv
sudo usermod -aG docker ubuntu
exit
```

Volver a entrar por SSH para que el permiso de Docker tome efecto. Comprobar con `docker run hello-world`.

## 4. Traer el código y los datos

```bash
git clone https://github.com/Angel12007/Proyecto_despliegue_g17.git
cd Proyecto_despliegue_g17
python3 -m venv .venv && source .venv/bin/activate
pip install "dvc[s3]"
mkdir -p ~/.aws && nano ~/.aws/credentials     # pegar las credenciales de AWS Academy
dvc pull data/processed/dataset_modelado.csv
deactivate
```

El tablero necesita `data/processed/dataset_modelado.csv` (versionado con DVC) para los indicadores históricos.

## 5. Construir y levantar los contenedores

```bash
docker compose up -d --build
docker ps
```

`docker ps` debe mostrar `uci-api` y `uci-tablero` en estado `Up`.

## 6. Verificar

| Qué | Dirección |
|---|---|
| API | `http://<IP_PUBLICA>:8001/docs` |
| Salud de la API | `http://<IP_PUBLICA>:8001/api/v1/health` |
| Tablero | `http://<IP_PUBLICA>:8050` |

En el tablero, el panel lateral debe decir **"vía API"** bajo *Modelo en uso*.

## 7. Operación

| Acción | Comando |
|---|---|
| Ver registros | `docker logs -f uci-api` / `docker logs -f uci-tablero` |
| Detener | `docker compose down` |
| Actualizar a una nueva versión | `git pull && docker compose up -d --build` |

## Alternativa sin docker compose

```bash
docker network create uci-red
docker build -t uci-api:1.0.0 ./api
docker build -f tablero/Dockerfile -t uci-tablero:1.0.0 .
docker run -d --name api --network uci-red -p 8001:8001 uci-api:1.0.0
docker run -d --name uci-tablero --network uci-red -e API_URL=http://api:8001 -p 8050:8050 uci-tablero:1.0.0
```

## Instalación local (desarrollo, sin Docker)

```bash
pip install -r api/test_requirements.txt          # instala la API y el paquete del modelo
uvicorn app.main:app --port 8001 --app-dir api    # terminal 1
pip install -r tablero/requirements.txt
API_URL=http://127.0.0.1:8001 python tablero/app.py   # terminal 2 (en Windows: set API_URL=...)
```

Sin la variable `API_URL`, el tablero usa directamente el paquete `modelo_uci` instalado.

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| El navegador no abre la IP | Falta abrir el puerto 8001 u 8050 en el security group. |
| Panel lateral: "No hay conexión con el modelo" | El contenedor `uci-api` no está corriendo: `docker logs uci-api`. |
| `COPY failed: ... dataset_modelado.csv` al construir | Falta `dvc pull` (paso 4). |
| La IP cambió | En AWS Academy la IP pública cambia al reiniciar el laboratorio; usar la nueva. |
