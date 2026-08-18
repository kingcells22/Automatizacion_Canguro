import pandas as pd
import sqlite3
import os
import sys

# Forzar utf-8 en la salida estándar
sys.stdout.reconfigure(encoding='utf-8')

db_path = 'db/cierre_canguro.db'
os.makedirs('db', exist_ok=True)

def clean_currency(x):
    """
    Inteligencia de parsing numérico: Detecta automáticamente si el separador
    decimal es coma o punto sin importar el formato regional.
    """
    if pd.isna(x): return 0.0
    if isinstance(x, (int, float)): return float(x)
    x = str(x).strip()
    if x == '': return 0.0
    
    if '.' in x and ',' in x:
        if x.rfind(',') > x.rfind('.'):
            # Formato VE/EU: 1.234,56 -> 1234.56
            x = x.replace('.', '').replace(',', '.')
        else:
            # Formato US: 1,234.56 -> 1234.56
            x = x.replace(',', '')
    elif ',' in x:
        # Si solo hay coma, en el contexto VE suele ser el decimal
        x = x.replace(',', '.')
        
    try:
        return float(x)
    except:
        return 0.0

def ingestar_datos(periodo, ruta_ingresos, ruta_bifrost, ruta_edr, ruta_promedios, ruta_maestro=None, log_callback=print):
    log_callback(f"--- Iniciando procesamiento para el período: {periodo} ---")
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. INGRESOS
        if ruta_ingresos:
            log_callback("Procesando archivo de Ingresos...")
            try: df_ingresos = pd.read_csv(ruta_ingresos, sep=';', encoding='utf-8', low_memory=False)
            except: df_ingresos = pd.read_csv(ruta_ingresos, sep=';', encoding='latin-1', low_memory=False)
            if len(df_ingresos.columns) == 1:
                try: df_ingresos = pd.read_csv(ruta_ingresos, sep=',', encoding='utf-8', low_memory=False)
                except: df_ingresos = pd.read_csv(ruta_ingresos, sep=',', encoding='latin-1', low_memory=False)
            df_ingresos.to_sql('raw_ingresos', conn, if_exists='replace', index=False)
            df_ingresos['periodo_carga'] = periodo
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='historico_ingresos'")
            if cursor.fetchone(): cursor.execute("DELETE FROM historico_ingresos WHERE periodo_carga = ?", (periodo,))
            df_ingresos.to_sql('historico_ingresos', conn, if_exists='append', index=False)
            log_callback(f"[OK] Ingresos guardados. ({len(df_ingresos)} filas)")

        # 2. BIFROST
        if ruta_bifrost:
            log_callback("Procesando archivo de Bifrost...")
            try: df_bifrost = pd.read_csv(ruta_bifrost, sep=';', encoding='utf-8-sig', on_bad_lines='skip', low_memory=False)
            except: df_bifrost = pd.read_csv(ruta_bifrost, sep=';', encoding='latin-1', on_bad_lines='skip', low_memory=False)
            if len(df_bifrost.columns) == 1:
                try: df_bifrost = pd.read_csv(ruta_bifrost, sep=',', encoding='utf-8-sig', on_bad_lines='skip', low_memory=False)
                except: df_bifrost = pd.read_csv(ruta_bifrost, sep=',', encoding='latin-1', on_bad_lines='skip', low_memory=False)
            
            if len(df_bifrost.columns) <= 2:
                log_callback("[ERROR] Archivo Bifrost muy pequeño. Parece ser el Maestro. Ignorando.")
            else:
                df_bifrost.to_sql('raw_bifrost', conn, if_exists='replace', index=False)
                df_bifrost['periodo_carga'] = periodo
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='historico_bifrost'")
                if cursor.fetchone(): cursor.execute("DELETE FROM historico_bifrost WHERE periodo_carga = ?", (periodo,))
                df_bifrost.to_sql('historico_bifrost', conn, if_exists='append', index=False)
                log_callback(f"[OK] Bifrost guardado. ({len(df_bifrost)} filas)")

        # 3. EDR EXCEL
        if ruta_edr:
            log_callback("Procesando Excel EDR...")
            xls = pd.ExcelFile(ruta_edr)
            for sheet in xls.sheet_names:
                df_sheet = pd.read_excel(xls, sheet_name=sheet)
                df_sheet.to_sql(f"raw_edr_{sheet.replace(' ', '_').lower()}", conn, if_exists='replace', index=False)

        # 4. PROMEDIOS
        if ruta_promedios:
            log_callback("Procesando Excel Promedios...")
            xls = pd.ExcelFile(ruta_promedios)
            for sheet in xls.sheet_names:
                df_sheet = pd.read_excel(xls, sheet_name=sheet)
                df_sheet.to_sql(f"raw_promedio_{sheet.replace(' ', '_').lower()}", conn, if_exists='replace', index=False)

        # 5. MAESTRO DE CUENTAS
        if ruta_maestro:
            log_callback("Procesando Plan/Maestro de Cuentas...")
            try:
                if ruta_maestro.endswith('.csv'):
                    df_maestro = pd.read_csv(ruta_maestro, sep=';', encoding='utf-8', on_bad_lines='skip', header=None, names=['codigo', 'grupo_cuenta'])
                    if len(df_maestro.columns) == 1:
                        df_maestro = pd.read_csv(ruta_maestro, sep=',', encoding='utf-8', header=None, names=['codigo', 'grupo_cuenta'])
                else:
                    df_maestro = pd.read_excel(ruta_maestro, header=None, names=['codigo', 'grupo_cuenta'])
                df_maestro.to_sql('maestro_cuentas', conn, if_exists='replace', index=False)
                log_callback(f"[OK] Maestro de Cuentas actualizado en memoria. ({len(df_maestro)} códigos)")
            except Exception as e:
                log_callback(f"[ERROR] No se pudo leer el Maestro de Cuentas: {e}")

        conn.commit()
        log_callback("[ÉXITO] Ingesta completada.")
        return True
    except Exception as e:
        log_callback(f"[ERROR CRÍTICO] {e}")
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()

def calcular_rentabilidad(periodo, ruta_bd, porcentajes_manuales=None, log_callback=print):
    if porcentajes_manuales is None:
        porcentajes_manuales = {}

    log_callback(f"--- Iniciando cálculos y Tablas Dinámicas para {periodo} ---")
    conn = None
    try:
        conn = sqlite3.connect(ruta_bd)
        
        # 1. INGRESOS
        query_ingresos = "SELECT nombre_tienda, [MONTO AUDITADO USD] FROM historico_ingresos WHERE periodo_carga = ?"
        df_ingresos = pd.read_sql_query(query_ingresos, conn, params=(periodo,))
        if df_ingresos.empty:
            log_callback("[ADVERTENCIA] No hay datos de ingresos.")
            return pd.DataFrame()

        # Parseo inteligente
        df_ingresos['MONTO AUDITADO USD'] = df_ingresos['MONTO AUDITADO USD'].apply(clean_currency)
        df_resumen = df_ingresos.groupby('nombre_tienda', as_index=False)['MONTO AUDITADO USD'].sum()
        df_resumen.rename(columns={'nombre_tienda': 'CENTRO DE COSTO / TIENDA', 'MONTO AUDITADO USD': 'INGRESOS TOTALES (USD)'}, inplace=True)
        
        # 2. CALCULAR % DE IMPACTO
        total_ingresos_empresa = df_resumen['INGRESOS TOTALES (USD)'].sum()
        df_resumen['% IMPACTO NUM'] = (df_resumen['INGRESOS TOTALES (USD)'] / total_ingresos_empresa * 100) if total_ingresos_empresa > 0 else 0

        # 3. APLICAR AJUSTES MANUALES
        for tienda_manual, pct_manual in porcentajes_manuales.items():
            idx = df_resumen['CENTRO DE COSTO / TIENDA'].str.upper().str.contains(tienda_manual, regex=False)
            if idx.any():
                df_resumen.loc[idx, '% IMPACTO NUM'] = pct_manual
                log_callback(f"[AJUSTE] Aplicado {pct_manual}% a la tienda {tienda_manual}")

        # 4. TABLA DINÁMICA DE GASTOS Y PRORRATEO (El "Jaque Mate")
        gasto_corporativo = 0
        df_pivot_gastos = pd.DataFrame()
        
        try:
            df_bifrost = pd.read_sql_query("SELECT * FROM historico_bifrost WHERE periodo_carga = ?", conn, params=(periodo,))
            if not df_bifrost.empty:
                df_bifrost.columns = [c.upper().strip() for c in df_bifrost.columns]
                
                if 'TIENDA' in df_bifrost.columns and 'BALANCE' in df_bifrost.columns:
                    df_bifrost['TIENDA'] = df_bifrost['TIENDA'].astype(str).str.upper()
                    df_bifrost['BALANCE'] = df_bifrost['BALANCE'].apply(clean_currency)
                    
                    # Extraer Gasto Corporativo para prorratear
                    corp_mask = df_bifrost['TIENDA'].str.contains('CORPORATIVO|FINANZAS|IT VEN|DIRECCION|LEGAL|LOGISTICA', na=False)
                    gasto_corporativo = df_bifrost.loc[corp_mask, 'BALANCE'].sum()
                    log_callback(f"[PRORRATEO] Total Gastos Corporativos: {gasto_corporativo:,.2f} USD")
                    
                    # Intentar Cruce con Maestro de Cuentas
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='maestro_cuentas'")
                    if cursor.fetchone():
                        df_maestro = pd.read_sql_query("SELECT codigo, grupo_cuenta FROM maestro_cuentas", conn)
                        df_maestro['codigo'] = df_maestro['codigo'].astype(str).str.strip()
                        
                        # Buscar dinámicamente la columna de Códigos en Bifrost
                        col_cod = next((c for c in df_bifrost.columns if 'CODIGO' in c or 'CUENTA' in c), None)
                        if col_cod:
                            df_bifrost[col_cod] = df_bifrost[col_cod].astype(str).str.strip()
                            df_bifrost = pd.merge(df_bifrost, df_maestro, left_on=col_cod, right_on='codigo', how='left')
                            df_bifrost['grupo_cuenta'] = df_bifrost['grupo_cuenta'].fillna('Sin Clasificar')
                            log_callback("[CRUCE] Cuentas mapeadas exitosamente mediante BUSCARV dinámico.")
                        else:
                            df_bifrost['grupo_cuenta'] = 'Gastos Generales'
                    else:
                        df_bifrost['grupo_cuenta'] = 'Gastos Generales'

                    # Generar la Pivot Table Dinámica en Memoria (Filas: Tienda, Columnas: Grupo Cuenta)
                    df_pivot_gastos = pd.pivot_table(df_bifrost, values='BALANCE', index='TIENDA', columns='grupo_cuenta', aggfunc='sum', fill_value=0).reset_index()
                    df_pivot_gastos.rename(columns={'TIENDA': 'CENTRO DE COSTO / TIENDA'}, inplace=True)
                    log_callback("[TABLA DINÁMICA] Matriz de gastos generada correctamente.")

        except Exception as e:
            log_callback(f"[INFO] No se procesaron los gastos de Bifrost: {e}")

        # 5. CONSOLIDACIÓN FINAL (Merge)
        # Unimos Ingresos con la Pivot de Gastos
        if not df_pivot_gastos.empty:
            df_resumen = pd.merge(df_resumen, df_pivot_gastos, on='CENTRO DE COSTO / TIENDA', how='left').fillna(0)

        df_resumen['GASTO APLICADO (PRORRATEO)'] = (df_resumen['% IMPACTO NUM'] / 100) * gasto_corporativo
        
        # 6. ESTÉTICA
        # Redondear todas las columnas numéricas dinámicamente
        for col in df_resumen.columns:
            if col not in ['CENTRO DE COSTO / TIENDA', '% IMPACTO NUM'] and pd.api.types.is_numeric_dtype(df_resumen[col]):
                df_resumen[col] = df_resumen[col].round(2)
                
        df_resumen['% IMPACTO'] = df_resumen['% IMPACTO NUM'].round(2).astype(str) + " %"
        
        # Organizar columnas: Tienda, Ingresos, %, Gasto Aplicado, y luego el resto de gastos dinámicos
        cols_base = ['CENTRO DE COSTO / TIENDA', 'INGRESOS TOTALES (USD)', '% IMPACTO', 'GASTO APLICADO (PRORRATEO)']
        cols_extras = [c for c in df_resumen.columns if c not in cols_base and c != '% IMPACTO NUM']
        df_resumen = df_resumen[cols_base + cols_extras]
        
        df_resumen = df_resumen.sort_values(by='INGRESOS TOTALES (USD)', ascending=False)
        
        return df_resumen
    except Exception as e:
        log_callback(f"[ERROR PANDAS] {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    print("Módulo main.py importado.")