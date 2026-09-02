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

def inferir_periodos(df, ruta_archivo):
    import re
    # 1. Si existe columna MES (como en Bifrost)
    cols = [c.upper().strip() for c in df.columns]
    for col_real in df.columns:
        if col_real.upper().strip() in ['MES', 'PERIODO', 'PERÍODO']:
            return df[col_real].astype(str)
            
    # 2. Si existe columna de Fecha (ej. Ingresos/EDR)
    for col_real in df.columns:
        if 'FECHA' in col_real.upper().strip() or 'DATE' in col_real.upper().strip():
            try:
                fechas = pd.to_datetime(df[col_real], errors='coerce', dayfirst=True)
                return fechas.dt.strftime('%Y-%m').fillna('0000-00')
            except: pass
            
    # 3. Intentar sacar la fecha del nombre del archivo (YYYY-MM o YYYY_MM)
    nombre = str(ruta_archivo)
    match = re.search(r'(20\d{2})[-_](0[1-9]|1[0-2])', nombre)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
        
    return '0000-00'

def procesar_y_guardar_historico(df, tabla, conn, cursor, log_callback, ruta):
    # Inferir periodos y asignar
    periodos = inferir_periodos(df, ruta)
    df['periodo_carga'] = periodos
    
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabla}'")
    if cursor.fetchone():
        # Borrar solo los periodos que vamos a inyectar para evitar duplicados
        periodos_unicos = df['periodo_carga'].unique()
        for p in periodos_unicos:
            cursor.execute(f"DELETE FROM {tabla} WHERE periodo_carga = ?", (str(p),))
            
    df.to_sql(tabla, conn, if_exists='append', index=False)
    log_callback(f"[OK] {tabla} guardados. ({len(df)} filas, periodos: {', '.join([str(x) for x in df['periodo_carga'].unique()][:3])}...)")

def limpiar_bd():
    import os
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
        return True
    except Exception as e:
        print(f"Error limpiando BD: {e}")
        return False

def ingestar_datos(ruta_ingresos, ruta_bifrost, ruta_edr, ruta_promedios, ruta_empleados=None, log_callback=print):
    log_callback(f"--- Iniciando procesamiento de Ingesta Inteligente ---")
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
            procesar_y_guardar_historico(df_ingresos, 'historico_ingresos', conn, cursor, log_callback, ruta_ingresos)

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
                # Estandarizar y traducir los tipos y grupos de cuenta
                traducciones = {
                    'expense': 'gastos', 'expense_direct_cost': 'costo_directo',
                    'costo': 'costo_directo', 'costos': 'costo_directo',
                    'income': 'ingresos', 'income_other': 'otros_ingresos', 'otros ingresos': 'otros_ingresos',
                    'asset': 'activo', 'liability': 'pasivo', 'equity': 'patrimonio',
                    'gasto': 'gastos', 'gastos': 'gastos', 'ingreso': 'ingresos', 'ingresos': 'ingresos'
                }
                for col in df_bifrost.columns:
                    if col.lower().strip() in ['tipo de cuenta', 'grupo de cuenta']:
                        df_bifrost[col] = df_bifrost[col].astype(str).str.lower().str.strip().map(lambda x: traducciones.get(x, x))
                        
                df_bifrost.to_sql('raw_bifrost', conn, if_exists='replace', index=False)
                procesar_y_guardar_historico(df_bifrost, 'historico_bifrost', conn, cursor, log_callback, ruta_bifrost)

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

        # 5. EMPLEADOS (RRHH)
        if ruta_empleados:
            log_callback("Procesando Excel Empleados (RRHH)...")
            try:
                if ruta_empleados.endswith('.csv'):
                    df_empleados = pd.read_csv(ruta_empleados, sep=';', encoding='utf-8', on_bad_lines='skip')
                    if len(df_empleados.columns) == 1:
                        df_empleados = pd.read_csv(ruta_empleados, sep=',', encoding='utf-8')
                else:
                    df_empleados = pd.read_excel(ruta_empleados)
                
                df_empleados.to_sql('raw_empleados', conn, if_exists='replace', index=False)
                procesar_y_guardar_historico(df_empleados, 'historico_empleados', conn, cursor, log_callback, ruta_empleados)
            except Exception as e:
                log_callback(f"[ERROR] No se pudo leer el archivo de Empleados: {e}")

        conn.commit()
        log_callback("[ÉXITO] Ingesta completada.")
        return True
    except Exception as e:
        import traceback
        log_callback(f"[ERROR CRÍTICO] {e}\n{traceback.format_exc()}")
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()

def calcular_rentabilidad(desde, hasta, ruta_bd, porcentajes_manuales=None, log_callback=print):
    if porcentajes_manuales is None:
        porcentajes_manuales = {}

    log_callback(f"--- Iniciando cálculos y Tablas Dinámicas para el rango: {desde} al {hasta} ---")
    conn = None
    try:
        conn = sqlite3.connect(ruta_bd)
        
        # 1. LEER DATOS DE BIFROST (Única fuente de verdad ahora)
        df_bifrost = pd.read_sql_query("SELECT * FROM historico_bifrost WHERE periodo_carga BETWEEN ? AND ?", conn, params=(desde, hasta))
        if df_bifrost.empty:
            log_callback("[ADVERTENCIA] No hay datos de Bifrost.")
            return pd.DataFrame()
            
        df_bifrost.columns = [c.upper().strip() for c in df_bifrost.columns]
        if 'TIENDA' in df_bifrost.columns and 'BALANCE' in df_bifrost.columns:
            df_bifrost['TIENDA'] = df_bifrost['TIENDA'].astype(str).str.upper()
            df_bifrost['BALANCE'] = df_bifrost['BALANCE'].apply(clean_currency)
            
            # Identificar la columna Tipo de Cuenta
            col_tipo = next((c for c in df_bifrost.columns if 'TIPO DE CUENTA' in c or 'GRUPO DE CUENTA' in c), None)
            if col_tipo:
                traducciones = {
                    'expense': 'gastos', 'expense_direct_cost': 'costo_directo',
                    'costo': 'costo_directo', 'costos': 'costo_directo',
                    'income': 'ingresos', 'income_other': 'otros_ingresos', 'otros ingresos': 'otros_ingresos',
                    'asset': 'activo', 'liability': 'pasivo', 'equity': 'patrimonio',
                    'gasto': 'gastos', 'gastos': 'gastos', 'ingreso': 'ingresos', 'ingresos': 'ingresos'
                }
                df_bifrost['tipo_cuenta'] = df_bifrost[col_tipo].astype(str).str.lower().str.strip().map(lambda x: traducciones.get(x, x))
            else:
                df_bifrost['tipo_cuenta'] = 'gastos'
                
            # Extraer Gasto Corporativo para prorratear
            corp_mask = df_bifrost['TIENDA'].str.contains('CORPORATIVO|FINANZAS|IT VEN|DIRECCION|LEGAL|LOGISTICA', na=False)
            gasto_corporativo = df_bifrost.loc[corp_mask & (df_bifrost['tipo_cuenta'] == 'gastos'), 'BALANCE'].sum()
            log_callback(f"[PRORRATEO] Total Gastos Corporativos: {gasto_corporativo:,.2f} USD")
            
            # Crear Pivot por TIPO DE CUENTA
            df_pivot = pd.pivot_table(df_bifrost, values='BALANCE', index='TIENDA', columns='tipo_cuenta', aggfunc='sum', fill_value=0).reset_index()
            df_pivot.rename(columns={'TIENDA': 'CENTRO DE COSTO / TIENDA'}, inplace=True)
            
            # Garantizar columnas minimas y convertirlas a positivo (ingresos contables son creditos negativos)
            for col in ['ingresos', 'otros_ingresos', 'costo_directo', 'gastos']:
                if col not in df_pivot.columns:
                    df_pivot[col] = 0
                else:
                    if col in ['ingresos', 'otros_ingresos']:
                        df_pivot[col] = df_pivot[col] * -1
                    else:
                        pass # Dejar los gastos y costos con su signo real para respetar reembolsos
                    
            df_resumen = df_pivot.copy()
            df_resumen['INGRESOS TOTALES (USD)'] = df_resumen['ingresos'] + df_resumen['otros_ingresos']
            
            # CALCULAR % DE IMPACTO
            total_ingresos_empresa = df_resumen['INGRESOS TOTALES (USD)'].sum()
            df_resumen['% IMPACTO NUM'] = (df_resumen['INGRESOS TOTALES (USD)'] / total_ingresos_empresa * 100) if total_ingresos_empresa > 0 else 0
            
            # APLICAR AJUSTES MANUALES
            for tienda_manual, pct_manual in porcentajes_manuales.items():
                idx = df_resumen['CENTRO DE COSTO / TIENDA'].str.upper().str.contains(tienda_manual, regex=False)
                if idx.any():
                    df_resumen.loc[idx, '% IMPACTO NUM'] = pct_manual
                    log_callback(f"[AJUSTE] Aplicado {pct_manual}% a la tienda {tienda_manual}")
                    
            # GASTO APLICADO
            df_resumen['GASTO APLICADO (PRORRATEO)'] = (df_resumen['% IMPACTO NUM'] / 100) * gasto_corporativo
            
            # ESTÉTICA Y ORDEN
            for col in df_resumen.columns:
                if col not in ['CENTRO DE COSTO / TIENDA', '% IMPACTO NUM'] and pd.api.types.is_numeric_dtype(df_resumen[col]):
                    df_resumen[col] = df_resumen[col].round(2)
            df_resumen['% IMPACTO'] = df_resumen['% IMPACTO NUM'].round(2).astype(str) + " %"
            
            cols_base = ['CENTRO DE COSTO / TIENDA', 'INGRESOS TOTALES (USD)', '% IMPACTO', 'GASTO APLICADO (PRORRATEO)', 'ingresos', 'otros_ingresos', 'costo_directo']
            cols_extras = [c for c in df_resumen.columns if c not in cols_base and c != '% IMPACTO NUM']
            df_resumen = df_resumen[cols_base + cols_extras]
        else:
            return pd.DataFrame()
        
        df_resumen = df_resumen.sort_values(by='INGRESOS TOTALES (USD)', ascending=False)
        
        return df_resumen
    except Exception as e:
        log_callback(f"[ERROR PANDAS] {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()

def obtener_datos_dashboard(desde, hasta, db_path):
    import sqlite3
    import pandas as pd
    try:
        from regiones import REGIONES
    except ImportError:
        REGIONES = {}
        
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        df_emp = pd.read_sql_query("SELECT Departamento FROM historico_empleados WHERE periodo_carga BETWEEN ? AND ?", conn, params=(desde, hasta))
        
        if df_emp.empty: return None, None
        
        # Empleados por Tienda
        df_tiendas = df_emp['Departamento'].value_counts().reset_index()
        df_tiendas.columns = ['Tienda', 'Cantidad']
        
        # Tiendas por Región
        # We need to map the 'Tienda' to 'Region'
        df_tiendas['Region'] = df_tiendas['Tienda'].map(lambda x: REGIONES.get(str(x).strip(), 'OTRO'))
        df_regiones = df_tiendas.groupby('Region')['Cantidad'].sum().reset_index()
        df_regiones.columns = ['Region', 'Empleados']
        
        return df_tiendas, df_regiones
    except Exception as e:
        print(f"Error obteniendo datos dashboard: {e}")
        return None, None
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    print("Módulo main.py importado.")