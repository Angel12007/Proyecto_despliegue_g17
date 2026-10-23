import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.impute import KNNImputer

""" Analizar faltantes
"""
def analizar_faltantes(df, umbral=20):
    """
    Analiza y muestra el porcentaje de datos faltantes por columna en un DataFrame.

    Parámetros:
        df (pd.DataFrame): El DataFrame a analizar.
        umbral (float): Porcentaje mínimo para considerar un faltante como significativo (default = 20%).

    Retorna:
        pd.Series con el porcentaje de faltantes por columna.
    """
    print("="*60)
    print("✅ Porcentaje de valores faltantes por columna:")
    porcentaje_faltantes = df.isnull().sum() * 100 / len(df)
    print(porcentaje_faltantes)
    
    print("\n✅ Porcentaje de faltantes (ordenado de menor a mayor):")
    porcentaje_faltantes_ord = porcentaje_faltantes.sort_values()
    print(porcentaje_faltantes_ord)
    
    print(f"\n🚨 Columnas con más del {umbral}% de datos faltantes:")
    faltantes_mayor_umbral = porcentaje_faltantes_ord[porcentaje_faltantes_ord > umbral]
    print(faltantes_mayor_umbral)

    return porcentaje_faltantes_ord

def imputar_variables_continuas(df, variables, n_vecinos=5):
    """
    Imputa variables continuas en un DataFrame utilizando:
    - Reemplazo de 'Sin dato' por NaN
    - Conversión a numérico
    - Escalado MinMax
    - Imputación con KNN
    - Desescalado inverso
    - Relleno con la media para valores faltantes restantes
    
    Parámetros:
        df (pd.DataFrame): El DataFrame original.
        variables (list): Lista de nombres de columnas a imputar.
        n_vecinos (int): Número de vecinos para KNN (default=5).
    
    Retorna:
        df (pd.DataFrame): DataFrame con las variables imputadas.
    """
    df = df.copy()
    
    # Paso 1: Reemplazar "Sin dato" por NaN
    df.replace("Sin dato", np.nan, inplace=True)

    # Paso 2: Asegurar que las columnas sean numéricas
    df[variables] = df[variables].apply(pd.to_numeric, errors='coerce')

    # Paso 3: Escalado MinMax
    scaler = MinMaxScaler()
    df_scaled = pd.DataFrame(scaler.fit_transform(df[variables]), columns=variables)

    # Paso 4: Imputación con KNN
    imputer = KNNImputer(n_neighbors=n_vecinos)
    df_imputed = pd.DataFrame(imputer.fit_transform(df_scaled), columns=variables)

    # Paso 5: Inversión del escalado
    df_inverse_scaled = pd.DataFrame(scaler.inverse_transform(df_imputed), columns=variables)

    # Paso 6: Reemplazar columnas originales con valores imputados
    df[variables] = df_inverse_scaled

    # Paso 7: Imputar cualquier NaN restante con la media
    df[variables] = df[variables].fillna(df[variables].mean())

    # Paso 8: Verificación final
    print("✅ Valores faltantes por variable tras imputación:")
    print(df[variables].isnull().sum())

    return df


def limpiar_y_preparar_dataset(df):
    """
    Limpia el dataset:
    - Elimina columnas no necesarias
    - Convierte columnas categóricas
    - Elimina duplicados
    - Renombra variables al formato estándar
    """

    # Eliminar columnas innecesarias
    columnas_a_eliminar = [
        'fecha_ing', 'fecha_egre1', 'fecha_egre2','otro_sitiocancer','otro_focosepsis','peso', 'talla',
        'fech_muerte_uci', 'mortesper_saps3','labs_ing','nro_ingreso_crudo','result_procal_ing','focosepsis',
        'logit', 'mortaespe', 'escalas_in_uci', 'ufc', 'result_troping', 'result_ldhing_2','karnofsky',
        'labs_tomados_ing___1', 'labs_tomados_ing___2', 'labs_tomados_ing___3','pco2ing', 'po2ing','gav',
        'labs_tomados_ing___4', 'labs_tomados_ing___5', 'labs_tomados_ing___6','quimio', 'inmuno', 'terapia_dirigida', 'hormonal',
        'labs_tomados_ing___7', 'labs_tomados_ing___8', 'sitiocancer', 'PRONOSTICO leucemias', 
        'estadio_ general L/MM', 'estadio_cat_final',
        'tip_escalas_in_uci___1' ,'tip_escalas_in_uci___2','tip_escalas_in_uci___3','medicamento_uci___9',
        'medicamento_uci___10','medicamento_uci___11','medicamento_uci___14', 'medicamento_uci___16','tipchoque',
        'tip_gav___1', 'tip_gav___2', 'vmni', 'cafo', 'vmi',
        'medicamento_uci___2','medicamento_uci___5','medicamento_uci___6','medicamento_uci___7',
        'medicamento_uci___12','medicamento_uci___13','medicamento_uci___15',
        'objetivoterapeutico', 'diastot'
        
    ]
    df = df.drop(columns=[c for c in columnas_a_eliminar if c in df.columns], errors='ignore')

    # Columnas categóricas
    columnas_categoricas = [
        'soportere', 'delirium', 'choque','sepsis', 'origen_tumor_cat', 'ecog',
        'result_secuenc_final', 'tto_oncologico', 'nro_ingresos_cat', 'estadio_global', 'sexo',
        'categoria', 'medicamento_uci___1','medicamento_uci___3','medicamento_uci___4',
        'medicamento_uci___8', 'soporte_ventilatorio'
    ]
    for col in columnas_categoricas:
        if col in df.columns:
            df[col] = df[col].astype('category')

    # Duplicados
    cantidad_repetidos = df['record_id'].duplicated().sum()
    print(f"🔁 Número de record_id repetidos: {cantidad_repetidos}")
    if cantidad_repetidos > 0:
        ids_duplicados = df['record_id'][df['record_id'].duplicated()].unique()
        print(f"IDs duplicados: {ids_duplicados}")
    df = df.drop_duplicates(subset='record_id', keep='first')
    print(f"✅ Sin duplicados. Nueva forma del dataset: {df.shape}")

    # Renombrar columnas
    column_renames = {
        'sexo': 'sex', 'edad': 'age', 'imc': 'bmi', 'categoria': 'type_of_admission',
         'ecog': 'ecog', 'choque': 'shock',
        'sepsis': 'sepsis',  'lactatoing': 'lactate', 'being': 'excess base',
        'hco3ing': 'bicarbonate', 'pafiing': 'pafi', 'hbing': 'hemoglobin', 'leucosingr': 'leukocytes',
        'neutingr': 'neuthrophils', 'linfingre': 'lymphocytes', 'plaqingr': 'platelet', 'pting': 'pt',
        'pttingr': 'aptt', 'tgoing': 'alt', 'tgping': 'ast', 'bilitorring': 'total_bilirubin',
        'bding': 'direct_bilirubin', 'biing': 'indirect_bilirubin', 'creing': 'creatinine', 
        'buning': 'bun', 'potasioing': 'potassium', 'sodioing': 'sodium', 'calciing': 'calcium',
        'apacheii': 'apacheii', 'saps_3': 'sapsiii', 'sofa_24h': 'sofa', 'soportere': 'support renal',
        'medicamento_uci___1': 'vasopressors_use', 'medicamento_uci___3': 'sedatives_use',
        'medicamento_uci___4': 'painkillers_use', 'medicamento_uci___8': 'methylene_blue_use',
        'delirium': 'delirium', 'mortalidad': 'mortality', 'sobrevida30': '30survival',
        'result_secuenc_final': 'Sequ_mol_fish_study', 'nro_ingresos_cat': 'icu_readmission',
        'origen_tumor_cat': 'origin_of_tumor', 'estadio_global': 'staging_risk',
        'soporte_ventilatorio': 'ventilatory_support', 'tto_oncologico': 'oncological_treatment'
    }
    df = df.rename(columns=column_renames)

    return df

