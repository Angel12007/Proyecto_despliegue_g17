# Guía paso a paso: entrenar los modelos en Databricks

## Qué le toca

| Integrante | Modelos |
|---|---|
| Angel | `logistica` y `random_forest` |
| Alejandro | `xgboost` y `catboost` |

Usted **no programa nada**: el código ya está hecho. Solo sube unos archivos a Databricks, elige opciones en un menú y le da "correr".

## Archivos del zip

Descomprima `modelos_para_companeros.zip`. Va a ver:

- `dataset_modelado.csv` → la base de datos
- `src/modelado.py` → el código que entrena
- `notebooks/entrenar_modelos_databricks.py` → el notebook que se corre
- `docs/guia_modelos.md` → esta guía
- `requirements-modelos.txt` → librerías (solo para GitHub)

---

## PARTE 1. Preparar Databricks (una sola vez)

**Paso 1.** Entre a Databricks con su cuenta, la misma del taller 4.

**Paso 2. Crear el lugar donde van la base y el código**

1. En el menú de la izquierda haga clic en **Catalog**.
2. Haga clic en **workspace** y luego en **default**.
3. Arriba a la derecha: **Create** → **Volume**.
4. En el nombre escriba: `g17` → **Create**.

**Paso 3. Subir dos archivos a ese volume**

1. Dentro del volume `g17`, haga clic en **Upload to this volume**.
2. Suba `dataset_modelado.csv`.
3. Repita y suba `modelado.py` (está dentro de la carpeta `src` del zip).

Deben quedar los dos archivos juntos en `g17`.

**Paso 4. Subir el notebook**

1. En el menú de la izquierda: **Workspace**.
2. Entre a su carpeta (la que tiene su correo).
3. Clic derecho, o los tres puntos **⋮** → **Import**.
4. Elija **File** y suba `entrenar_modelos_databricks.py` (está en la carpeta `notebooks` del zip) → **Import**.

---

## PARTE 2. Correr los modelos

**Paso 5.** Abra el notebook `entrenar_modelos_databricks`.

**Paso 6.** Arriba a la derecha, donde dice **Connect**, elija **Serverless**.

**Paso 7.** Haga clic en **Run all** (arriba). La primera vez tarda unos minutos porque instala librerías. Termina con el mensaje *"Elija su modelo en el menú 'modelo'..."*: es normal. Ahora aparecen arriba unos menús desplegables (*widgets*).

**Paso 8.** En esos menús elija la primera combinación de la tabla de abajo y vuelva a darle **Run all**.

Al final del notebook sale un mensaje como este:

```
AUROC CV 0.872 | AUROC prueba 0.907 (0.859-0.948) | Brier 0.086 | E/O 1.16
```

Eso significa que terminó bien.

**Paso 9.** Cambie los menús a la siguiente combinación y **Run all** otra vez. Repita hasta completar las 8.

| # | modelo | desenlace | variables |
|---|---|---|---|
| 1 | su modelo 1 | estancia_prolongada | tablero |
| 2 | su modelo 1 | estancia_prolongada | completo |
| 3 | su modelo 1 | mortality | tablero |
| 4 | su modelo 1 | mortality | completo |
| 5 | su modelo 2 | estancia_prolongada | tablero |
| 6 | su modelo 2 | estancia_prolongada | completo |
| 7 | su modelo 2 | mortality | tablero |
| 8 | su modelo 2 | mortality | completo |

No toque los otros dos menús (`ruta_datos` y `registrar_como`). Cada corrida tarda entre 1 y 3 minutos.

---

## PARTE 3. Capturas para el reporte 📸

En **todas** las capturas debe verse **su correo de Databricks** (arriba a la derecha).

1. 📸 Menú izquierdo → **Experiments** → abra `G17_UCI_triage`. Captura de la lista de corridas.
2. 📸 Haga clic en la flechita **▸** de una corrida para ver las corridas "hijas" (las pruebas de hiperparámetros). Captura.
3. 📸 Marque las casillas de sus 8 corridas principales → botón **Compare** → captura de la gráfica.
4. 📸 Abra su mejor corrida → pestaña **Artifacts** → carpeta `evaluacion` → abra `roc_prueba.png`. Captura. Repita con `calibracion_prueba.png`.
5. 📸 Vuelva al notebook, baje hasta la tabla final y tome la captura.

---

## PARTE 4. Subir su trabajo a GitHub

**Paso 10. Descargar sus resultados**

**Catalog** → **workspace** → **default** → **g17** → busque `resultados_<su-usuario>.csv` → tres puntos **⋮** → **Download**.

**Paso 11. Tener el repositorio en su computador**

El repositorio del grupo es:

**https://github.com/Angel12007/Proyecto_despliegue_g17**

Antes de empezar:

- Necesita tener **Git** instalado. Abra la ventana negra (tecla Windows → escriba `cmd` → Enter) y escriba `git --version`. Si sale un número, ya lo tiene. Si dice "no se reconoce", instálelo desde https://git-scm.com/download/win dejando todas las opciones por defecto, y vuelva a abrir la ventana negra.
- Debe ser **colaborador** del repositorio. Angel es el dueño y ya lo es. **Alejandro:** pídale a Angel que lo invite (*Settings → Collaborators → Add people*, con su usuario de GitHub) y acepte la invitación que le llega al correo.

**Elija su caso:**

**A. Si NO tiene el repositorio en su computador** (nunca lo ha clonado), lo descarga con estos comandos. Copie y pegue uno por uno:

```cmd
cd %USERPROFILE%\Downloads
git clone https://github.com/Angel12007/Proyecto_despliegue_g17.git
cd Proyecto_despliegue_g17
git config user.name "Su Nombre"
git config user.email "el-correo-de-su-cuenta-de-github"
git checkout -b feature/modelos-SUNOMBRE
```

Queda una carpeta nueva en **Descargas** llamada `Proyecto_despliegue_g17`.

**B. Si YA lo tiene** (por ejemplo, Angel desde la exploración), entre a esa carpeta y actualícela:

```cmd
cd ruta\de\su\carpeta\Proyecto_despliegue_g17
git checkout main
git pull
git checkout -b feature/modelos-SUNOMBRE
```

En los dos casos, cambie `SUNOMBRE` por su nombre, sin tildes ni espacios. Ejemplo: `feature/modelos-alejandro`.

> Para esta parte **no** necesita DVC ni la base de datos dentro de la carpeta. Solo se suben a GitHub los archivos de código y su archivo de resultados.

**Paso 12. Copiar los archivos a la carpeta del proyecto**

Con el Explorador de archivos:

- **Angel** copia:
  - `modelado.py` → dentro de la carpeta `src`
  - la carpeta `notebooks` completa → en la carpeta principal
  - `guia_modelos.md` → dentro de la carpeta `docs`
  - `requirements-modelos.txt` → en la carpeta principal
  - su `resultados_....csv` → en una carpeta nueva `reports\modelos`
- **Alejandro** solo copia su `resultados_....csv` → en `reports\modelos`

**Paso 13. Subir (copiar y pegar en la ventana negra)**

**Angel:**

```cmd
git add src/modelado.py notebooks docs/guia_modelos.md requirements-modelos.txt reports/modelos
git commit -m "Codigo de modelado y experimentos de logistica y random forest"
git push -u origin feature/modelos-angel
```

**Alejandro** (cuando lo de Angel ya esté en GitHub):

```cmd
git add reports/modelos
git commit -m "Experimentos de XGBoost y CatBoost"
git push -u origin feature/modelos-alejandro
```

📸 Captura del mensaje del push.

**Paso 14. Pull request**

1. Abra https://github.com/Angel12007/Proyecto_despliegue_g17
2. Clic en el botón amarillo **Compare & pull request**.
3. A la derecha, en **Reviewers**, elija a **adraya01** (Adriana).
4. **Create pull request**.
5. Cuando Adriana lo apruebe: **Merge pull request** → **Confirm merge**.

📸 Captura del pull request en estado **Merged** (morado).

---

## PARTE 5. Qué escribir para el reporte

Un párrafo por cada uno de sus modelos. Todo está en MLflow, en su corrida principal:

- Los mejores hiperparámetros (aparecen como `mejor_...`).
- `cv_auroc_mejor` (validación cruzada) y `test_auroc` con su intervalo (`test_auroc_ic_inf` a `test_auroc_ic_sup`).
- `test_brier` y `test_razon_esperado_observado` (calibración: lo ideal es cercano a 1).
- `test_pct_dias_cama_en_top20` y `test_pct_eventos_en_top20`. Las metas son ≥ 45 % y ≥ 65 %.
- `test_auroc_saps3_mismos_pacientes`, para comparar el modelo contra SAPS III.
- Si las 14 variables (`tablero`) dan un resultado parecido a las 43 (`completo`).

---

## Si algo sale mal

| Mensaje | Qué hacer |
|---|---|
| `No module named 'modelado'` | `modelado.py` no está en el volume `g17`. Revise el Paso 3. |
| `FileNotFoundError` | `dataset_modelado.csv` no está en el volume `g17`, o le cambió el nombre. |
| `No module named 'catboost'` | Vuelva a darle **Run all**. |
| `403` o `Permission denied` en `git push` | Pídale a Angel que lo agregue como colaborador y acepte la invitación del correo. |
| Al hacer `git push` se abre una ventana de GitHub | Es normal: elija **Sign in with your browser** e inicie sesión. |
| `fatal: not a git repository` | No está dentro de la carpeta `Proyecto_despliegue_g17`. Repita el `cd`. |

Si se queda trabado, mande una foto del error al grupo.

---

## Anexo para el reporte: qué hace el código

- Usa la base final del pipeline DVC (997 pacientes).
- **Validación temporal:** entrena con los 816 ingresos anteriores al 1 de julio de 2024 y evalúa una sola vez con los 181 posteriores.
- La imputación de faltantes (KNN para continuas, moda para categóricas) y la estandarización se ajustan solo con los datos de entrenamiento.
- Prueba varias combinaciones de hiperparámetros con validación cruzada de 5 pliegues y se queda con la de mejor AUROC. Cada combinación queda registrada en MLflow como corrida hija.
- **Variables:** `tablero` usa las 14 que pide el tablero (edad, APACHE II, SAPS III, SOFA, lactato, PaO2/FiO2, plaquetas, soporte ventilatorio, vasopresores, choque, sepsis, ECOG, origen del tumor y tipo de ingreso). `completo` usa las 43 disponibles.
- **El modelo final se elige** por el AUROC de validación cruzada y la calibración, no por el AUROC de prueba.
