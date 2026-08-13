import pandas as pd
import sqlite3
import os
import sys

# Forzar utf-8 en la salida estándar
sys.stdout.reconfigure(encoding='utf-8')

db_path = 'db/cierre_canguro.db'
os.makedirs('db', exist_ok=True)

def ingestar_datos(periodo, ruta_ingresos, ruta_bifrost, ruta_edr, ruta_promedios, log_callback=print):
    """
    Motor de ingesta dinámico.
    """
    log_callback(f"--- Iniciando procesamiento para el período: {periodo} ---")
    conn = None
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. PROCESAR INGRESOS (CSV)
        if ruta_ingresos:
            log_callback("Procesando archivo de Ingresos...")
            try:
                df_ingresos = pd.read_csv(ruta_ingresos, sep=';', encoding='utf-8', low_memory=False)
            except UnicodeDecodeError:
                df_ingresos = pd.read_csv(ruta_ingresos, sep=';', encoding='latin-1', low_memory=False)
            
            if len(df_ingresos.columns) == 1:
                try:
                    df_ingresos = pd.read_csv(ruta_ingresos, sep=',', encoding='utf-8', low_memory=False)
                except:
                    df_ingresos = pd.read_csv(ruta_ingresos, sep=',', encoding='latin-1', low_memory=False)
                    
            df_ingresos.to_sql('raw_ingresos', conn, if_exists='replace', index=False)
            df_ingresos['periodo_carga'] = periodo
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='historico_ingresos'")
            if cursor.fetchone():
                cursor.execute("DELETE FROM historico_ingresos WHERE periodo_carga = ?", (periodo,))
            df_ingresos.to_sql('historico_ingresos', conn, if_exists='append', index=False)
            log_callback(f"[OK] Ingresos guardados. ({len(df_ingresos)} filas)")

        # 2. PROCESAR BIFROST (CSV)
        if ruta_bifrost:
            log_callback("Procesando archivo de Bifrost...")
            try:
                df_bifrost = pd.read_csv(ruta_bifrost, sep=';', encoding='utf-8-sig', on_bad_lines='skip', low_memory=False)
            except UnicodeDecodeError:
                df_bifrost = pd.read_csv(ruta_bifrost, sep=';', encoding='latin-1', on_bad_lines='skip', low_memory=False)
            
            if len(df_bifrost.columns) == 1:
                try:
                    df_bifrost = pd.read_csv(ruta_bifrost, sep=',', encoding='utf-8-sig', on_bad_lines='skip', low_memory=False)
                except:
                    df_bifrost = pd.read_csv(ruta_bifrost, sep=',', encoding='latin-1', on_bad_lines='skip', low_memory=False)
            
            if len(df_bifrost.columns) == 2:
                df_bifrost.columns = ['cuenta_codigo', 'cuenta_nombre']

            df_bifrost.to_sql('raw_bifrost', conn, if_exists='replace', index=False)
            df_bifrost['periodo_carga'] = periodo
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='historico_bifrost'")
            if cursor.fetchone():
                cursor.execute("DELETE FROM historico_bifrost WHERE periodo_carga = ?", (periodo,))
            df_bifrost.to_sql('historico_bifrost', conn, if_exists='append', index=False)
            log_callback(f"[OK] Bifrost guardado. ({len(df_bifrost)} filas)")

        # 3. PROCESAR EDR (EXCEL)
        if ruta_edr:
            log_callback("Procesando Excel EDR (Múltiples Pestañas)...")
            xls = pd.ExcelFile(ruta_edr)
            for sheet in xls.sheet_names:
                df_sheet = pd.read_excel(xls, sheet_name=sheet)
                clean_name = f"raw_edr_{sheet.replace(' ', '_').lower()}"
                df_sheet.to_sql(clean_name, conn, if_exists='replace', index=False)
                log_callback(f"  -> Pestaña '{sheet}' guardada.")

        # 4. PROCESAR PROMEDIOS (EXCEL)
        if ruta_promedios:
            log_callback("Procesando Excel Promedios (Múltiples Pestañas)...")
            xls = pd.ExcelFile(ruta_promedios)
            for sheet in xls.sheet_names:
                df_sheet = pd.read_excel(xls, sheet_name=sheet)
                clean_name = f"raw_promedio_{sheet.replace(' ', '_').lower()}"
                df_sheet.to_sql(clean_name, conn, if_exists='replace', index=False)
                log_callback(f"  -> Pestaña '{sheet}' guardada.")

        conn.commit()
        log_callback("[ÉXITO] Todos los datos fueron integrados en la Base de Datos.")
        return True
        
    except ImportError as ie:
        log_callback(f"[ERROR] Librería faltante. Instala openpyxl (pip install openpyxl)")
        return False
    except Exception as e:
        log_callback(f"[ERROR CRÍTICO DURANTE INGESTA] {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def calcular_rentabilidad(periodo, ruta_bd, log_callback=print):
    """
    Motor matemático de Pandas: Realiza la consolidación, agrupación 
    y prorrateo de gastos contables.
    """
    log_callback(f"--- Iniciando cruce contable y prorrateo para {periodo} ---")
    conn = None
    try:
        conn = sqlite3.connect(ruta_bd)
        
        # Extraer datos de la BD
        query_ingresos = "SELECT nombre_tienda, [MONTO AUDITADO USD] FROM historico_ingresos WHERE periodo_carga = ?"
        df_ingresos = pd.read_sql_query(query_ingresos, conn, params=(periodo,))
        
        if df_ingresos.empty:
            log_callback("[ADVERTENCIA] No hay datos de ingresos para generar la rentabilidad.")
            return pd.DataFrame()

        log_callback("Agrupando ingresos por Centro de Costo (Paso 3)...")
        
        # Limpieza de números (convertir comas a puntos si vienen como texto)
        if df_ingresos['MONTO AUDITADO USD'].dtype == object:
            df_ingresos['MONTO AUDITADO USD'] = df_ingresos['MONTO AUDITADO USD'].str.replace(',', '.')
            
        df_ingresos['MONTO AUDITADO USD'] = pd.to_numeric(df_ingresos['MONTO AUDITADO USD'], errors='coerce').fillna(0)

        # Agrupación (Suma todo lo de una tienda en una sola fila)
        df_resumen = df_ingresos.groupby('nombre_tienda', as_index=False)['MONTO AUDITADO USD'].sum()
        df_resumen.rename(columns={'nombre_tienda': 'CENTRO DE COSTO / TIENDA', 'MONTO AUDITADO USD': 'INGRESOS TOTALES (USD)'}, inplace=True)
        
        # Cálculos de Prorrateo (Paso 5 y 6 del Informe)
        log_callback("Calculando porcentaje de impacto sobre ingresos generales...")
        total_ingresos_empresa = df_resumen['INGRESOS TOTALES (USD)'].sum()
        
        if total_ingresos_empresa > 0:
            df_resumen['% IMPACTO (PRORRATEO)'] = (df_resumen['INGRESOS TOTALES (USD)'] / total_ingresos_empresa) * 100
        else:
            df_resumen['% IMPACTO (PRORRATEO)'] = 0
            
        # Formatear estética
        df_resumen['INGRESOS TOTALES (USD)'] = df_resumen['INGRESOS TOTALES (USD)'].round(2)
        df_resumen['% IMPACTO (PRORRATEO)'] = df_resumen['% IMPACTO (PRORRATEO)'].round(2).astype(str) + " %"

        # Ordenar de la que más vende a la que menos vende
        df_resumen = df_resumen.sort_values(by='INGRESOS TOTALES (USD)', ascending=False)
        
        log_callback("[ÉXITO] Tabla de Rentabilidad Base procesada con Pandas.")
        return df_resumen

    except Exception as e:
        log_callback(f"[ERROR MÓDULO PANDAS] Fallo al calcular rentabilidad: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Módulo main.py importado correctamente.")