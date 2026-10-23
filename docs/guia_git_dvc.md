# Guía de ejecución – Repositorio Git y DVC (Entrega 1, G17)

Los comandos se corren en la máquina virtual EC2 de AWS Academy, igual que en los talleres de las semanas 1 y 2. Cada 📸 marca una captura que va al reporte (sección "Repositorios").

Antes de empezar:

- **Angel** (dueño del repositorio) agrega a Adriana, Alejandro y Jeison como colaboradores: GitHub → `Proyecto_despliegue_g17` → *Settings* → *Collaborators* → *Add people*. Sin esto, el `git push` de los demás falla con error 403.
- Para hacer push desde la VM se necesita un *Personal Access Token* (GitHub → *Settings* → *Developer settings* → *Tokens (classic)*, permiso `repo`). Se pega como contraseña cuando git la pida.
- Las credenciales de AWS Academy cambian en cada sesión del laboratorio. Se copian de *AWS Details* → *AWS CLI* al archivo `~/.aws/credentials` de la VM. **No se guardan en el repositorio ni en archivos de texto dentro de la carpeta del proyecto.**

---

## Paso 0. Subir la carpeta del proyecto a la VM

Desde PowerShell en Windows (ajustar la ruta de la llave `.pem` y la IP pública de la instancia):

```powershell
scp -i "C:\ruta\labsuser.pem" -r "C:\Users\adria\Downloads\Uniandes\Despliegue\Proyecto\Proyecto_despliegue_g17" ubuntu@<IP_PUBLICA>:~/
```

Luego conectarse por SSH:

```powershell
ssh -i "C:\ruta\labsuser.pem" ubuntu@<IP_PUBLICA>
```

## Paso 1. Entorno de Python

```bash
cd ~/Proyecto_despliegue_g17
sudo apt update && sudo apt install -y python3-venv git
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
dvc --version
```

## Paso 2. Repositorio Git conectado a GitHub

El repositorio de GitHub está vacío, así que se inicia localmente y se conecta:

```bash
git init -b main
git config user.name "Adriana Aya"
git config user.email "<correo usado en GitHub>"
git remote add origin https://github.com/Angel12007/Proyecto_despliegue_g17.git
git status                       # 📸 archivos sin seguimiento
```

Primer commit, solo código (la base de datos todavía no se agrega):

```bash
git add README.md .gitignore requirements.txt params.yaml src docs LICENSE_codigo_articulo.txt
git commit -m "Estructura inicial: código de cargue y procesamiento de la base"
git push -u origin main          # 📸 push exitoso
```

> Si `git add` incluyera `data/raw/df_merged_final.xlsx`, deténgase: la base la versiona DVC, no Git.

## Paso 3. Inicializar DVC y versionar la base

```bash
dvc init
git commit -m "Inicializar DVC"

dvc add data/raw/df_merged_final.xlsx
cat data/raw/df_merged_final.xlsx.dvc   # 📸 identificador md5 de la base
git add data/raw/df_merged_final.xlsx.dvc data/raw/.gitignore
git commit -m "Versionar base cruda con DVC"
```

## Paso 4. Remoto en S3

Crear el bucket (el nombre debe ser único en todo AWS; solo minúsculas, números y guiones):

```bash
aws s3 mb s3://proyecto-g17-dvc-<iniciales-o-numero>
```

Si `aws` no está instalado: `sudo apt install -y awscli`, o crear el bucket desde la consola de S3.

```bash
dvc remote add -d s3remote s3://proyecto-g17-dvc-<iniciales-o-numero>/datos
cat .dvc/config                  # 📸 remoto configurado
git add .dvc/config
git commit -m "Configurar remoto S3 para DVC"
dvc push                         # 📸 archivos enviados a S3
```

En la consola de S3 se verá la carpeta `datos/files/md5/...` 📸.

## Paso 5. Pipeline reproducible: cargar → procesar

```bash
dvc repro                        # 📸 las dos etapas corriendo
dvc dag                          # 📸 grafo del pipeline
git add dvc.yaml dvc.lock data/interim/.gitignore data/processed/.gitignore
git commit -m "Pipeline DVC: cargue y procesamiento; versión final para modelado"
dvc push
git push                         # 📸 repositorio en GitHub con archivos .dvc, dvc.yaml y dvc.lock
```

La versión final para modelado queda en `data/processed/dataset_modelado.csv`, versionada con DVC. La exploración la agrega otro integrante como una etapa nueva que depende de ese archivo.

## Paso 6. Prueba de que otro integrante puede reproducirlo

En otra carpeta (o en la VM de otro integrante):

```bash
cd ~
git clone https://github.com/Angel12007/Proyecto_despliegue_g17.git prueba_clon
cd prueba_clon
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
dvc pull                         # 📸 descarga la base desde S3
dvc status                       # "Data and pipelines are up to date"
```

## Paso 7. Trabajo en equipo con ramas (soporte para el reporte de equipo)

Cada integrante trabaja en su rama y abre un *pull request* hacia `main`:

```bash
git checkout -b feature/<nombre-tarea>
# ... cambios ...
git add <archivos> && git commit -m "<qué cambió>"
git push -u origin feature/<nombre-tarea>
```

En GitHub: *Compare & pull request* → revisión de otro integrante → *Merge* 📸.

`git log --oneline --graph --all` 📸 muestra el historial con aportes de todos.

---

## Errores frecuentes

| Mensaje | Causa | Qué hacer |
|---|---|---|
| `remote: Permission denied ... 403` | No es colaborador o el token no tiene permiso `repo` | Pedir a Angel que lo agregue; generar token nuevo |
| `ExpiredToken` / `InvalidAccessKeyId` en `dvc push` | Expiró la sesión de AWS Academy | Copiar de nuevo las credenciales a `~/.aws/credentials` |
| `NoSuchBucket` | Nombre de bucket mal escrito o en otra región | `aws s3 ls` para verificar |
| `failed to push - output 'data/raw/...' already tracked by SCM` | La base se agregó con `git add` | `git rm --cached data/raw/df_merged_final.xlsx` y repetir el paso 3 |
