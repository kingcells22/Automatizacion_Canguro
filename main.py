import pandas as pd
import sqlite3
import os
import sys

# Forzar utf-8 en la salida estándar
sys.stdout.reconfigure(encoding='utf-8')

db_path = 'db/cierre_canguro.db'
os.makedirs('db', exist_ok=True)

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
            
            # Defensa Anti-Confusión en Backend
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

    log_callback(f"--- Iniciando cálculos y prorrateo para {periodo} ---")
    conn = None
    try:
        conn = sqlite3.connect(ruta_bd)
        
        # 1. INGRESOS
        query_ingresos = "SELECT nombre_tienda, [MONTO AUDITADO USD] FROM historico_ingresos WHERE periodo_carga = ?"
        df_ingresos = pd.read_sql_query(query_ingresos, conn, params=(periodo,))
        if df_ingresos.empty:
            log_callback("[ADVERTENCIA] No hay datos de ingresos.")
            return pd.DataFrame()

        if df_ingresos['MONTO AUDITADO USD'].dtype == object:
            df_ingresos['MONTO AUDITADO USD'] = df_ingresos['MONTO AUDITADO USD'].str.replace(',', '.')
        df_ingresos['MONTO AUDITADO USD'] = pd.to_numeric(df_ingresos['MONTO AUDITADO USD'], errors='coerce').fillna(0)

        df_resumen = df_ingresos.groupby('nombre_tienda', as_index=False)['MONTO AUDITADO USD'].sum()
        df_resumen.rename(columns={'nombre_tienda': 'CENTRO DE COSTO / TIENDA', 'MONTO AUDITADO USD': 'INGRESOS TOTALES (USD)'}, inplace=True)
        
        # 2. CALCULAR % DE IMPACTO
        total_ingresos_empresa = df_resumen['INGRESOS TOTALES (USD)'].sum()
        if total_ingresos_empresa > 0:
            df_resumen['% IMPACTO NUM'] = (df_resumen['INGRESOS TOTALES (USD)'] / total_ingresos_empresa) * 100
        else:
            df_resumen['% IMPACTO NUM'] = 0

        # 3. APLICAR AJUSTES MANUALES DE PORCENTAJE
        for tienda_manual, pct_manual in porcentajes_manuales.items():
            idx = df_resumen['CENTRO DE COSTO / TIENDA'].str.upper().str.contains(tienda_manual, regex=False)
            if idx.any():
                df_resumen.loc[idx, '% IMPACTO NUM'] = pct_manual
                log_callback(f"[AJUSTE] Aplicado {pct_manual}% a la tienda {tienda_manual}")

        # 4. PRORRATEO
        gasto_corporativo = 0
        try:
            df_bifrost = pd.read_sql_query("SELECT * FROM historico_bifrost WHERE periodo_carga = ?", conn, params=(periodo,))
            if not df_bifrost.empty:
                df_bifrost.columns = [c.upper().strip() for c in df_bifrost.columns]
                if 'TIENDA' in df_bifrost.columns and 'BALANCE' in df_bifrost.columns:
                    df_bifrost['TIENDA'] = df_bifrost['TIENDA'].astype(str).str.upper()
                    if df_bifrost['BALANCE'].dtype == object:
                        df_bifrost['BALANCE'] = df_bifrost['BALANCE'].str.replace(',', '.')
                    df_bifrost['BALANCE'] = pd.to_numeric(df_bifrost['BALANCE'], errors='coerce').fillna(0)
                    
                    corp_mask = df_bifrost['TIENDA'].str.contains('CORPORATIVO|FINANZAS|IT VEN|DIRECCION|LEGAL|LOGISTICA', na=False)
                    gasto_corporativo = df_bifrost.loc[corp_mask, 'BALANCE'].sum()
                    log_callback(f"[PRORRATEO] Total Gastos Administrativos: {gasto_corporativo:,.2f} USD")
        except Exception as e:
            log_callback(f"[INFO] Bifrost no procesado para prorrateo: {e}")

        df_resumen['GASTO APLICADO (PRORRATEO)'] = (df_resumen['% IMPACTO NUM'] / 100) * gasto_corporativo
        
        # 5. ESTÉTICA FINAL
        df_resumen['INGRESOS TOTALES (USD)'] = df_resumen['INGRESOS TOTALES (USD)'].round(2)
        df_resumen['GASTO APLICADO (PRORRATEO)'] = df_resumen['GASTO APLICADO (PRORRATEO)'].round(2)
        df_resumen['% IMPACTO'] = df_resumen['% IMPACTO NUM'].round(2).astype(str) + " %"
        df_resumen.drop(columns=['% IMPACTO NUM'], inplace=True)
        
        df_resumen = df_resumen[['CENTRO DE COSTO / TIENDA', 'INGRESOS TOTALES (USD)', '% IMPACTO', 'GASTO APLICADO (PRORRATEO)']]
        df_resumen = df_resumen.sort_values(by='INGRESOS TOTALES (USD)', ascending=False)
        
        return df_resumen
    except Exception as e:
        log_callback(f"[ERROR PANDAS] {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    print("Módulo main.py importado.")