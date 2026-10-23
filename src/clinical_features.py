import pandas as pd
import numpy as np

def procesar_variables_clinicas(df, verbose=True):
    """
    Procesa variables clínicas:
    - Clasifica origen tumoral.
    - Crea estadio global.
    - Define soporte ventilatorio.
    - Define administración de tratamiento oncológico en UCI.
    
    También imprime un resumen de las nuevas columnas creadas.
    
    Parámetros:
        df (pd.DataFrame): DataFrame de entrada.
        verbose (bool): Si True, imprime resumen de columnas creadas.
        
    Retorna:
        df (pd.DataFrame): DataFrame con columnas procesadas.
    """
    
    nuevas_columnas = []

    # -------------------- 1. Clasificar origen tumoral --------------------
    if 'ufc' in df.columns:
        grupo_hematologico = {6}
        grupo_otros = {1, 2, 3, 4, 5, 7, 8, 9, 10, 11}
        def asignar_grupo(valor):
            if valor in grupo_hematologico:
                return 0
            elif valor in grupo_otros:
                return 1
            else:
                return np.nan
        df['origen_tumor_cat'] = df['ufc'].apply(asignar_grupo)
        nuevas_columnas.append('origen_tumor_cat')

    # -------------------- 2. Crear estadio global --------------------
    estadio_cols = ['PRONOSTICO leucemias', 'estadio_ general L/MM', 'estadio_cat_final']
    estadio_validas = [col for col in estadio_cols if col in df.columns]
    if estadio_validas:
        df['estadio_global'] = df[estadio_validas].bfill(axis=1).iloc[:, 0]
        nuevas_columnas.append('estadio_global')

    # -------------------- 3. Soporte ventilatorio --------------------
    if all(col in df.columns for col in ['vmni', 'cafo', 'vmi']):
        def definir_soporte_ventilatorio(row):
            return 1 if (row.get('vmni') == 2 or row.get('cafo') == 2 or row.get('vmi') == 2) else 0
        df['soporte_ventilatorio'] = df.apply(definir_soporte_ventilatorio, axis=1)
        nuevas_columnas.append('soporte_ventilatorio')

    # -------------------- 4. Tratamiento oncológico --------------------
    tto_cols = ['quimio', 'inmuno', 'terapia_dirigida', 'hormonal']
    tto_validas = [col for col in tto_cols if col in df.columns]
    if tto_validas and 'medicamento_uci___11' in df.columns:
        df['tto_oncologico'] = (
            df[tto_validas].notna().any(axis=1) |
            (df['medicamento_uci___11'] == 1)
        ).astype(int)
        nuevas_columnas.append('tto_oncologico')

    # -------------------- 5. Mostrar resumen --------------------
    if verbose and nuevas_columnas:
        print("\n📊 Resumen de columnas creadas/modificadas:")
        resumen = []
        for col in nuevas_columnas:
            valores_unicos = df[col].unique()
            resumen.append({
                "Columna": col,
                "Nulos": df[col].isnull().sum(),
                "Valores Únicos": len(valores_unicos),
                "Ejemplos": valores_unicos[:5]
            })
        resumen_df = pd.DataFrame(resumen)
        print(resumen_df.to_string(index=False))
    elif verbose:
        print("⚠️ No se creó ninguna columna nueva. Verifica que las columnas requeridas estén en el DataFrame.")

    return df

