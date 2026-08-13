import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image
import pandas as pd
import sqlite3
import os
import main  # Conexión al motor lógico

# --- IMPORTACIONES PARA GRÁFICOS ---
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Truco para forzar el icono en la barra de tareas de Windows
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('canguro.motor.cierre.1.0')
except:
    pass

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Colores de la marca Canguro y UI
CANGURO_YELLOW = "#FFD700"
CANGURO_YELLOW_HOVER = "#E6C200"
CANGURO_BLACK = "#101010"
CANGURO_SIDEBAR = "#1A1A1A"
CANGURO_DARK_GREY = "#242424"
CANGURO_TEXT_LIGHT = "#FFFFFF"
CANGURO_TEXT_DARK = "#000000"
BTN_DANGER = "#D9534F"
BTN_DANGER_HOVER = "#C9302C"

class CierreContableApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Motor de Cierre Contable - Canguro")
        self.geometry("1250x750")
        self.configure(fg_color=CANGURO_BLACK)
        
        # --- MÉTODO INFALIBLE PARA ICONO EN WINDOWS ---
        try:
            ruta_ico = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets", "icono.ico")
            if os.path.exists(ruta_ico):
                self.iconbitmap(ruta_ico)
        except Exception as e:
            print(f"Aviso de icono: {e}")
        
        # Regla de cerrado limpio
        self.protocol("WM_DELETE_WINDOW", self.cerrar_app)

        self.db_path = "db/cierre_canguro.db"
        self.limpiar_rutas()
        self.df_actual = None 

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._configurar_estilos_treeview()
        self._crear_sidebar()
        self._crear_area_principal()

    def limpiar_rutas(self):
        self.ruta_bifrost = None
        self.ruta_ingresos = None
        self.ruta_edr = None
        self.ruta_promedios = None

    def _configurar_estilos_treeview(self):
        style = ttk.Style(self)
        style.theme_use("default")
        
        style.configure("Treeview", background=CANGURO_DARK_GREY, foreground=CANGURO_TEXT_LIGHT, rowheight=30, fieldbackground=CANGURO_DARK_GREY, borderwidth=0, font=("Roboto", 10))
        style.map('Treeview', background=[('selected', CANGURO_YELLOW)], foreground=[('selected', CANGURO_TEXT_DARK)])
        
        style.configure("Treeview.Heading", background="#111111", foreground=CANGURO_YELLOW, font=("Roboto", 11, "bold"), borderwidth=0, relief="flat", padding=(5, 5))
        style.map("Treeview.Heading", background=[('active', "#333333")])
        style.configure("Vertical.TScrollbar", background=CANGURO_DARK_GREY, bordercolor=CANGURO_BLACK)
        style.configure("Horizontal.TScrollbar", background=CANGURO_DARK_GREY, bordercolor=CANGURO_BLACK)

    def _crear_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=CANGURO_SIDEBAR)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")

        ruta_logo = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets", "logo.png")
        if os.path.exists(ruta_logo):
            logo_img = ctk.CTkImage(Image.open(ruta_logo), size=(130, 130))
            self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="", image=logo_img)
            self.logo_label.grid(row=0, column=0, padx=20, pady=(15, 0))
        
        self.titulo_label = ctk.CTkLabel(self.sidebar_frame, text="MOTOR DE CIERRE", font=("Roboto", 18, "bold"), text_color=CANGURO_YELLOW)
        self.titulo_label.grid(row=1, column=0, padx=20, pady=(5, 10))

        self.lbl_paso1 = ctk.CTkLabel(self.sidebar_frame, text="1. Archivos Locales", font=("Roboto", 14, "bold"))
        self.lbl_paso1.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.btn_csv = ctk.CTkButton(self.sidebar_frame, text="📄 CSV Bifrost", fg_color="#333333", hover_color="#555555", command=lambda: self.cargar_archivo("bifrost"))
        self.btn_csv.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        
        self.btn_excel = ctk.CTkButton(self.sidebar_frame, text="📄 CSV Ingresos", fg_color="#333333", hover_color="#555555", command=lambda: self.cargar_archivo("ingresos"))
        self.btn_excel.grid(row=4, column=0, padx=20, pady=5, sticky="ew")

        self.btn_edr = ctk.CTkButton(self.sidebar_frame, text="📄 Excel EDR", fg_color="#333333", hover_color="#555555", command=lambda: self.cargar_archivo("edr"))
        self.btn_edr.grid(row=5, column=0, padx=20, pady=5, sticky="ew")

        self.btn_promedio = ctk.CTkButton(self.sidebar_frame, text="📄 Excel Promedios", fg_color="#333333", hover_color="#555555", command=lambda: self.cargar_archivo("promedios"))
        self.btn_promedio.grid(row=6, column=0, padx=20, pady=5, sticky="ew")

        self.btn_limpiar = ctk.CTkButton(self.sidebar_frame, text="🧹 Limpiar Archivos", fg_color="transparent", border_width=1, border_color="#888888", text_color="#888888", hover_color="#333333", command=self.limpiar_ui)
        self.btn_limpiar.grid(row=7, column=0, padx=20, pady=5, sticky="ew")

        self.lbl_paso2 = ctk.CTkLabel(self.sidebar_frame, text="2. Conexión en la Nube", font=("Roboto", 14, "bold"))
        self.lbl_paso2.grid(row=8, column=0, padx=20, pady=(15, 5), sticky="w")

        self.btn_api = ctk.CTkButton(self.sidebar_frame, text="☁️ Conectar a Odoo (API)", fg_color="#1F4E79", hover_color="#296296", command=self.dummy_api)
        self.btn_api.grid(row=9, column=0, padx=20, pady=5, sticky="ew")

        self.lbl_paso3 = ctk.CTkLabel(self.sidebar_frame, text="3. Período", font=("Roboto", 14, "bold"))
        self.lbl_paso3.grid(row=10, column=0, padx=20, pady=(15, 5), sticky="w")
        
        self.periodo_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Ej: 2026-07")
        self.periodo_entry.grid(row=11, column=0, padx=20, pady=5, sticky="ew")

        self.btn_procesar = ctk.CTkButton(self.sidebar_frame, text="⚡ Procesar y Consolidar", fg_color=CANGURO_YELLOW, text_color=CANGURO_TEXT_DARK, hover_color=CANGURO_YELLOW_HOVER, font=("Roboto", 14, "bold"), command=self.procesar_mes)
        self.btn_procesar.grid(row=12, column=0, padx=20, pady=(20, 20), sticky="ew")

        self.sidebar_frame.grid_rowconfigure(13, weight=1) 

        # Salidas / Exportación
        self.btn_export_excel = ctk.CTkButton(self.sidebar_frame, text="📊 Exportar Excel Final", fg_color="transparent", border_color=CANGURO_YELLOW, border_width=1, text_color=CANGURO_YELLOW, hover_color="#333333", command=self.exportar_excel)
        self.btn_export_excel.grid(row=14, column=0, padx=20, pady=5, sticky="ew")

        self.btn_export_bi = ctk.CTkButton(self.sidebar_frame, text="📈 Exportar CSV (PowerBI)", fg_color="transparent", border_color=CANGURO_YELLOW, border_width=1, text_color=CANGURO_YELLOW, hover_color="#333333", command=self.exportar_csv_bi)
        self.btn_export_bi.grid(row=15, column=0, padx=20, pady=(5, 20), sticky="ew")

        # Cerrar App
        self.btn_salir = ctk.CTkButton(self.sidebar_frame, text="✖ CERRAR", fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER, font=("Roboto", 12, "bold"), command=self.cerrar_app)
        self.btn_salir.grid(row=16, column=0, padx=20, pady=(5, 20), sticky="ew")

    def _crear_area_principal(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # ------------------ SISTEMA DE PESTAÑAS ------------------
        self.tab_view = ctk.CTkTabview(self.main_frame, fg_color=CANGURO_DARK_GREY, segmented_button_selected_color=CANGURO_YELLOW, segmented_button_selected_hover_color=CANGURO_YELLOW_HOVER, text_color=CANGURO_TEXT_DARK)
        self.tab_view.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        
        self.tab_ingresos = self.tab_view.add("Auditoría Ingresos")
        self.tab_edr = self.tab_view.add("Auditoría EDR")
        self.tab_cierre = self.tab_view.add("Estado de Resultados y Rentabilidad")
        self.tab_dashboards = self.tab_view.add("Dashboards Visuales")

        for tab in [self.tab_ingresos, self.tab_edr, self.tab_cierre, self.tab_dashboards]:
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

        # --- TABLAS ---
        self.tree_ingresos = self._crear_arbol(self.tab_ingresos)
        self.tree_edr = self._crear_arbol(self.tab_edr)
        self.tree_cierre = self._crear_arbol(self.tab_cierre)

        # Consola de Estatus
        self.consola = ctk.CTkTextbox(self.main_frame, height=120, fg_color=CANGURO_DARK_GREY, text_color=CANGURO_YELLOW, font=("Consolas", 12))
        self.consola.grid(row=1, column=0, sticky="ew")
        self.consola.insert("0.0", "[SISTEMA INICIADO] Interfaz cargada. Esperando instrucciones...\n")
        self.consola.configure(state="disabled")

    def _crear_arbol(self, parent_frame):
        tree = ttk.Treeview(parent_frame, selectmode="extended")
        scroll_y = ttk.Scrollbar(parent_frame, orient="vertical", command=tree.yview)
        scroll_x = ttk.Scrollbar(parent_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        
        tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        return tree

    def log(self, mensaje):
        self.consola.configure(state="normal")
        self.consola.insert("end", f"> {mensaje}\n")
        self.consola.see("end")
        self.consola.configure(state="disabled")

    def dummy_api(self):
        self.log("[API ODOO] Funcionalidad de conexión directa a nube en desarrollo (Próximamente)...")

    def limpiar_ui(self):
        self.limpiar_rutas()
        self.btn_csv.configure(text="📄 CSV Bifrost", fg_color="#333333", hover_color="#555555")
        self.btn_excel.configure(text="📄 CSV Ingresos", fg_color="#333333", hover_color="#555555")
        self.btn_edr.configure(text="📄 Excel EDR", fg_color="#333333", hover_color="#555555")
        self.btn_promedio.configure(text="📄 Excel Promedios", fg_color="#333333", hover_color="#555555")
        self.tree_ingresos.delete(*self.tree_ingresos.get_children())
        self.tree_edr.delete(*self.tree_edr.get_children())
        self.tree_cierre.delete(*self.tree_cierre.get_children())
        self.df_actual = None
        for widget in self.tab_dashboards.winfo_children():
            widget.destroy()
        self.log("[INFO] Interfaz limpiada por completo.")

    def cargar_archivo(self, tipo):
        archivo = filedialog.askopenfilename(
            title=f"Seleccionar Archivo {tipo.upper()}",
            filetypes=[("Archivos", "*.csv *.xlsx *.xls"), ("Todos los archivos", "*.*")]
        )
        if archivo:
            if tipo == "bifrost":
                self.ruta_bifrost = archivo
                self.btn_csv.configure(text="✅ Bifrost", fg_color="#2E8B57", hover_color="#3CB371")
            elif tipo == "ingresos":
                self.ruta_ingresos = archivo
                self.btn_excel.configure(text="✅ Ingresos", fg_color="#2E8B57", hover_color="#3CB371")
            elif tipo == "edr":
                self.ruta_edr = archivo
                self.btn_edr.configure(text="✅ EDR", fg_color="#2E8B57", hover_color="#3CB371")
            elif tipo == "promedios":
                self.ruta_promedios = archivo
                self.btn_promedio.configure(text="✅ Promedios", fg_color="#2E8B57", hover_color="#3CB371")
            self.log(f"[ARCHIVO] {tipo.upper()} enrutado: {os.path.basename(archivo)}")

    def _llenar_tabla(self, treeview, df):
        treeview.delete(*treeview.get_children())
        if df.empty: return

        treeview["column"] = list(df.columns)
        treeview["show"] = "headings"
        
        for column in treeview["column"]:
            treeview.heading(column, text=str(column).upper(), anchor="w")
            max_data_len = df[column].astype(str).map(len).max() if not df[column].empty else 0
            max_len = max(max_data_len, len(str(column)))
            ancho_ideal = max(min(max_len * 10, 350), 100)
            treeview.column(column, width=ancho_ideal, anchor="w", stretch=False)

        treeview.tag_configure("oddrow", background="#222222")
        treeview.tag_configure("evenrow", background="#161616")

        for i, row in enumerate(df.itertuples(index=False)):
            row_str = [str(item) if pd.notnull(item) else "" for item in row]
            tag = "evenrow" if i % 2 == 0 else "oddrow"
            treeview.insert("", "end", values=row_str, tags=(tag,))

    def procesar_mes(self):
        periodo = self.periodo_entry.get().strip()
        
        if not periodo:
            self.log("[ERROR] Debes ingresar un período válido.")
            messagebox.showwarning("Advertencia", "Por favor, ingrese un período válido (ej. 2026-07).")
            return

        for tree in [self.tree_ingresos, self.tree_edr, self.tree_cierre]:
            tree.delete(*tree.get_children())

        if any([self.ruta_bifrost, self.ruta_ingresos, self.ruta_edr, self.ruta_promedios]):
            self.log("Iniciando ingesta de archivos en SQLite...")
            exito = main.ingestar_datos(periodo, self.ruta_ingresos, self.ruta_bifrost, self.ruta_edr, self.ruta_promedios, log_callback=self.log)
            if not exito:
                messagebox.showerror("Error", "Falló la ingesta de datos. Revisa la consola.")
                return
        else:
            respuesta = messagebox.askyesno("Atención", "No has cargado archivos nuevos.\n\n¿Quieres consultar el consolidado desde la BD?")
            if not respuesta:
                return

        self.log(f"Consultando BD para el período: {periodo}...")

        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            
            try:
                df_ingresos = pd.read_sql_query("SELECT * FROM historico_ingresos WHERE periodo_carga = ? LIMIT 100", conn, params=(periodo,))
                self._llenar_tabla(self.tree_ingresos, df_ingresos)
            except Exception:
                self.log("[ADVERTENCIA] No hay datos de Ingresos para mostrar.")

            try:
                df_bifrost = pd.read_sql_query("SELECT * FROM historico_bifrost WHERE periodo_carga = ? LIMIT 100", conn, params=(periodo,))
                self._llenar_tabla(self.tree_edr, df_bifrost)
            except Exception:
                self.log("[ADVERTENCIA] No hay datos de Bifrost para mostrar.")

            df_resultado_final = main.calcular_rentabilidad(periodo, self.db_path, log_callback=self.log)
            if not df_resultado_final.empty:
                self.df_actual = df_resultado_final 
                self._llenar_tabla(self.tree_cierre, df_resultado_final)
                self._dibujar_dashboards(df_resultado_final, periodo)
            else:
                self.log("[INFO] No se pudo generar la rentabilidad.")

            self.log("[OK] Previsualización y Dashboards completados.")

        except Exception as e:
            self.log(f"[ERROR CRÍTICO] {e}")
        finally:
            if conn:
                conn.close()

    def _dibujar_dashboards(self, df, periodo):
        for widget in self.tab_dashboards.winfo_children():
            widget.destroy()

        if df.empty:
            return

        df_top = df.head(10).copy()
        df_top['TIENDA_CORTA'] = df_top['CENTRO DE COSTO / TIENDA'].apply(lambda x: str(x).split('-')[-1].strip() if '-' in str(x) else str(x))

        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(9, 4), dpi=100)
        fig.patch.set_facecolor('#242424')
        ax.set_facecolor('#242424')
        
        ax.bar(df_top['TIENDA_CORTA'], df_top['INGRESOS TOTALES (USD)'], color=CANGURO_YELLOW)
        ax.set_title(f"Top 10 Tiendas por Ingresos - Período: {periodo}", color='white', pad=15, fontweight='bold')
        
        plt.xticks(rotation=45, ha='right', color='white', fontsize=9)
        plt.yticks(color='white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#555555')
        ax.spines['left'].set_color('#555555')
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.tab_dashboards)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def exportar_excel(self):
        if self.df_actual is None or self.df_actual.empty:
            messagebox.showwarning("Sin datos", "No hay datos procesados para exportar.")
            return

        ruta = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            title="Guardar Reporte Excel",
            initialfile=f"Reporte_Rentabilidad_{self.periodo_entry.get().strip()}.xlsx",
            filetypes=[("Archivos de Excel", "*.xlsx")]
        )
        if ruta:
            try:
                self.df_actual.to_excel(ruta, index=False)
                self.log(f"[EXPORTACIÓN] Archivo Excel guardado en: {ruta}")
                messagebox.showinfo("Éxito", "Reporte Excel exportado correctamente.")
            except Exception as e:
                self.log(f"[ERROR EXPORTACIÓN] {e}")
                messagebox.showerror("Error", f"No se pudo guardar el archivo:\n{e}")

    def exportar_csv_bi(self):
        if self.df_actual is None or self.df_actual.empty:
            messagebox.showwarning("Sin datos", "No hay datos procesados para exportar.")
            return

        ruta = filedialog.asksaveasfilename(
            defaultextension=".csv",
            title="Guardar Dataset para PowerBI",
            initialfile=f"Dataset_PowerBI_{self.periodo_entry.get().strip()}.csv",
            filetypes=[("Archivo CSV", "*.csv")]
        )
        if ruta:
            try:
                self.df_actual.to_csv(ruta, index=False, sep=';', decimal=',', encoding='utf-8-sig')
                self.log(f"[EXPORTACIÓN BI] Dataset para PowerBI guardado en: {ruta}")
                messagebox.showinfo("Éxito", "Data para Business Intelligence exportada correctamente.")
            except Exception as e:
                self.log(f"[ERROR EXPORTACIÓN] {e}")
                messagebox.showerror("Error", f"No se pudo guardar el archivo:\n{e}")

    def cerrar_app(self):
        try:
            plt.close('all')
        except:
            pass
        self.quit()
        self.destroy()

if __name__ == "__main__":
    app = CierreContableApp()
    app.mainloop()