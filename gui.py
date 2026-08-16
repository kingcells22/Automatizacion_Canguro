import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image
import pandas as pd
import sqlite3
import os
import main
import requests
import threading

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('canguro.motor.cierre.1.0')
except:
    pass

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

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
        self.geometry("1280x750")
        self.configure(fg_color=CANGURO_BLACK)
        
        try:
            ruta_ico = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets", "icono.ico")
            if os.path.exists(ruta_ico): self.iconbitmap(ruta_ico)
        except: pass
        
        self.protocol("WM_DELETE_WINDOW", self.cerrar_app)
        
        self.db_path = "db/cierre_canguro.db"
        self.tasa_bcv = 0.0
        self.df_actual = None 
        self.porcentajes_manuales = {}
        self.limpiar_rutas()

        self._crear_ventana_terminal()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._configurar_estilos_treeview()
        self._crear_sidebar()
        self._crear_area_principal()
        
        threading.Thread(target=self.obtener_tasa_api, daemon=True).start()

    def limpiar_rutas(self):
        self.ruta_bifrost = None
        self.ruta_ingresos = None
        self.ruta_edr = None
        self.ruta_promedios = None
        self.ruta_maestro = None

    def _configurar_estilos_treeview(self):
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview", background=CANGURO_DARK_GREY, foreground=CANGURO_TEXT_LIGHT, rowheight=30, fieldbackground=CANGURO_DARK_GREY, borderwidth=0, font=("Roboto", 10))
        style.map('Treeview', background=[('selected', CANGURO_YELLOW)], foreground=[('selected', CANGURO_TEXT_DARK)])
        style.configure("Treeview.Heading", background="#111111", foreground=CANGURO_YELLOW, font=("Roboto", 11, "bold"), borderwidth=0, relief="flat", padding=(5, 5))
        style.map("Treeview.Heading", background=[('active', "#333333")])

    def _crear_ventana_terminal(self):
        self.vent_term = ctk.CTkToplevel(self)
        self.vent_term.title("Terminal del Sistema / Logs")
        self.vent_term.geometry("700x350")
        
        # --- FORZAR ICONO EN LA TERMINAL ---
        try:
            ruta_ico = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets", "icono.ico")
            if os.path.exists(ruta_ico):
                self.vent_term.after(200, lambda: self.vent_term.iconbitmap(ruta_ico))
        except: pass

        self.vent_term.withdraw()
        self.vent_term.protocol("WM_DELETE_WINDOW", self.vent_term.withdraw)
        
        self.consola = ctk.CTkTextbox(self.vent_term, fg_color=CANGURO_DARK_GREY, text_color=CANGURO_YELLOW, font=("Consolas", 12))
        self.consola.pack(fill="both", expand=True, padx=10, pady=10)
        self.consola.insert("0.0", "[SISTEMA INICIADO] Terminal operando en segundo plano...\n")
        self.consola.configure(state="disabled")

    def mostrar_terminal(self):
        self.vent_term.deiconify()
        self.vent_term.lift()

    def log(self, mensaje):
        self.consola.configure(state="normal")
        self.consola.insert("end", f"> {mensaje}\n")
        self.consola.see("end")
        self.consola.configure(state="disabled")

    def _crear_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=CANGURO_SIDEBAR)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")

        ruta_logo = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets", "logo.png")
        if os.path.exists(ruta_logo):
            logo_img = ctk.CTkImage(Image.open(ruta_logo), size=(100, 100))
            self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="", image=logo_img)
            self.logo_label.grid(row=0, column=0, padx=20, pady=(5, 0))
        
        self.titulo_label = ctk.CTkLabel(self.sidebar_frame, text="MOTOR DE CIERRE", font=("Roboto", 16, "bold"), text_color=CANGURO_YELLOW)
        self.titulo_label.grid(row=1, column=0, padx=20, pady=(0, 5))

        self.lbl_paso1 = ctk.CTkLabel(self.sidebar_frame, text="1. Archivos Locales", font=("Roboto", 13, "bold"))
        self.lbl_paso1.grid(row=2, column=0, padx=20, pady=(5, 0), sticky="w")
        
        self.btn_csv = ctk.CTkButton(self.sidebar_frame, text="📄 CSV Bifrost", fg_color="#333333", hover_color="#555555", command=lambda: self.cargar_archivo("bifrost"))
        self.btn_csv.grid(row=3, column=0, padx=20, pady=2, sticky="ew")
        
        self.btn_excel = ctk.CTkButton(self.sidebar_frame, text="📄 CSV Ingresos", fg_color="#333333", hover_color="#555555", command=lambda: self.cargar_archivo("ingresos"))
        self.btn_excel.grid(row=4, column=0, padx=20, pady=2, sticky="ew")

        self.btn_edr = ctk.CTkButton(self.sidebar_frame, text="📄 Excel EDR", fg_color="#333333", hover_color="#555555", command=lambda: self.cargar_archivo("edr"))
        self.btn_edr.grid(row=5, column=0, padx=20, pady=2, sticky="ew")

        self.btn_promedio = ctk.CTkButton(self.sidebar_frame, text="📄 Excel Promedios", fg_color="#333333", hover_color="#555555", command=lambda: self.cargar_archivo("promedios"))
        self.btn_promedio.grid(row=6, column=0, padx=20, pady=2, sticky="ew")

        self.btn_maestro = ctk.CTkButton(self.sidebar_frame, text="📄 Plan/Maestro Cuentas", fg_color="#1F4E79", hover_color="#296296", command=lambda: self.cargar_archivo("maestro"))
        self.btn_maestro.grid(row=7, column=0, padx=20, pady=(2, 0), sticky="ew")

        self.btn_add_codigo = ctk.CTkButton(self.sidebar_frame, text="➕ Añadir Código Manual", fg_color="transparent", border_width=1, border_color="#555555", text_color="#AAAAAA", hover_color="#333333", command=self.agregar_codigo_manual)
        self.btn_add_codigo.grid(row=8, column=0, padx=20, pady=(2, 5), sticky="ew")

        self.btn_limpiar = ctk.CTkButton(self.sidebar_frame, text="🧹 Limpiar Archivos", fg_color="transparent", border_width=1, border_color="#888888", text_color="#888888", hover_color="#333333", command=self.limpiar_ui)
        self.btn_limpiar.grid(row=9, column=0, padx=20, pady=(2, 10), sticky="ew")

        self.lbl_paso2 = ctk.CTkLabel(self.sidebar_frame, text="2. Tasa de Cambio", font=("Roboto", 13, "bold"))
        self.lbl_paso2.grid(row=10, column=0, padx=20, pady=(5, 0), sticky="w")

        self.tasa_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.tasa_frame.grid(row=11, column=0, padx=20, pady=2, sticky="ew")
        self.tasa_frame.grid_columnconfigure(0, weight=1)

        self.lbl_tasa = ctk.CTkLabel(self.tasa_frame, text="⏳ Conectando...", font=("Roboto", 13, "bold"), text_color=CANGURO_YELLOW)
        self.lbl_tasa.grid(row=0, column=0, sticky="w")

        self.btn_editar_tasa = ctk.CTkButton(self.tasa_frame, text="✏️", width=30, fg_color="#333333", hover_color="#555555", command=self.editar_tasa_manual)
        self.btn_editar_tasa.grid(row=0, column=1, padx=(5, 0), sticky="e")

        self.lbl_paso3 = ctk.CTkLabel(self.sidebar_frame, text="3. Período", font=("Roboto", 13, "bold"))
        self.lbl_paso3.grid(row=12, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.periodo_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Ej: 2026-07")
        self.periodo_entry.grid(row=13, column=0, padx=20, pady=2, sticky="ew")

        self.btn_procesar = ctk.CTkButton(self.sidebar_frame, text="⚡ Procesar y Consolidar", fg_color=CANGURO_YELLOW, text_color=CANGURO_TEXT_DARK, hover_color=CANGURO_YELLOW_HOVER, font=("Roboto", 14, "bold"), command=self.procesar_mes)
        self.btn_procesar.grid(row=14, column=0, padx=20, pady=(15, 10), sticky="ew")

        self.sidebar_frame.grid_rowconfigure(15, weight=1) 

        self.btn_export_excel = ctk.CTkButton(self.sidebar_frame, text="📊 Exportar Excel Final", fg_color="transparent", border_color=CANGURO_YELLOW, border_width=1, text_color=CANGURO_YELLOW, hover_color="#333333", command=self.exportar_excel)
        self.btn_export_excel.grid(row=16, column=0, padx=20, pady=2, sticky="ew")

        self.btn_export_bi = ctk.CTkButton(self.sidebar_frame, text="📈 Exportar CSV (PowerBI)", fg_color="transparent", border_color=CANGURO_YELLOW, border_width=1, text_color=CANGURO_YELLOW, hover_color="#333333", command=self.exportar_csv_bi)
        self.btn_export_bi.grid(row=17, column=0, padx=20, pady=(2, 10), sticky="ew")

        self.btn_terminal = ctk.CTkButton(self.sidebar_frame, text="💻 TERMINAL / LOGS", fg_color="#333333", hover_color="#555555", command=self.mostrar_terminal)
        self.btn_terminal.grid(row=18, column=0, padx=20, pady=(2, 5), sticky="ew")

        self.btn_salir = ctk.CTkButton(self.sidebar_frame, text="✖ CERRAR", fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER, font=("Roboto", 12, "bold"), command=self.cerrar_app)
        self.btn_salir.grid(row=19, column=0, padx=20, pady=(2, 15), sticky="ew")

    def _crear_area_principal(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        self.tab_view = ctk.CTkTabview(self.main_frame, fg_color=CANGURO_DARK_GREY, segmented_button_selected_color=CANGURO_YELLOW, segmented_button_selected_hover_color=CANGURO_YELLOW_HOVER, text_color=CANGURO_TEXT_DARK)
        self.tab_view.grid(row=0, column=0, sticky="nsew")
        
        self.tab_ingresos = self.tab_view.add("Auditoría Ingresos")
        self.tab_edr = self.tab_view.add("Auditoría EDR")
        self.tab_cierre = self.tab_view.add("Estado Resultados y Rentabilidad")
        self.tab_dashboards = self.tab_view.add("Dashboards Visuales")

        self.frame_t1, self.tree_ingresos = self._crear_arbol(self.tab_ingresos)
        self.frame_t1.pack(fill="both", expand=True)

        self.frame_t2, self.tree_edr = self._crear_arbol(self.tab_edr)
        self.frame_t2.pack(fill="both", expand=True)

        self.btn_ajuste_pct = ctk.CTkButton(self.tab_cierre, text="✏️ Ajustar % Impacto Manual", command=self.abrir_ventana_ajuste, fg_color="#1F4E79", hover_color="#296296")
        self.btn_ajuste_pct.pack(anchor="w", pady=(0, 5))
        self.frame_t3, self.tree_cierre = self._crear_arbol(self.tab_cierre)
        self.frame_t3.pack(fill="both", expand=True)

    def _crear_arbol(self, parent_frame):
        frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        tree = ttk.Treeview(frame, selectmode="extended")
        scroll_y = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scroll_x = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        return frame, tree

    # ==========================================
    # CÓDIGOS, % MANUALES Y VALIDACIÓN INTELIGENTE
    # ==========================================
    def abrir_ventana_ajuste(self):
        if self.df_actual is None or self.df_actual.empty:
            messagebox.showwarning("Aviso", "Procesa un mes primero para poder ajustar sus porcentajes.")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Ajuste Manual de Porcentaje")
        dialog.geometry("350x250")
        dialog.attributes("-topmost", True)
        
        # --- FORZAR ICONO EN EL POPUP DE AJUSTE ---
        try:
            ruta_ico = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets", "icono.ico")
            if os.path.exists(ruta_ico):
                dialog.after(200, lambda: dialog.iconbitmap(ruta_ico))
        except: pass

        dialog.transient(self)
        
        lbl_tienda = ctk.CTkLabel(dialog, text="1. Escribe la tienda (Ej: SAMBIL):", font=("Roboto", 12, "bold"))
        lbl_tienda.pack(pady=(15, 5))
        entry_tienda = ctk.CTkEntry(dialog, width=220)
        entry_tienda.pack(pady=5)
        
        lbl_pct = ctk.CTkLabel(dialog, text="2. Nuevo % de Impacto (Ej: 15.5):", font=("Roboto", 12, "bold"))
        lbl_pct.pack(pady=(10, 5))
        entry_pct = ctk.CTkEntry(dialog, width=220)
        entry_pct.pack(pady=5)
        
        def aplicar():
            tienda = entry_tienda.get().strip().upper()
            pct = entry_pct.get().strip()
            if not tienda or not pct:
                messagebox.showerror("Error", "Debes llenar ambos campos.")
                return
            try:
                pct_float = float(pct.replace(',', '.'))
                self.porcentajes_manuales[tienda] = pct_float
                self.log(f"[AJUSTE] % de '{tienda}' sobreescrito a {pct_float}%")
                self.procesar_mes(recalcular=True)
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "El porcentaje debe ser un número válido.")
                
        btn = ctk.CTkButton(dialog, text="Guardar y Recalcular", command=aplicar, fg_color=CANGURO_YELLOW, text_color=CANGURO_TEXT_DARK)
        btn.pack(pady=20)

    def agregar_codigo_manual(self):
        dialog = ctk.CTkInputDialog(text="Ingrese el Código Numérico (Ej: 5101060100):", title="Nuevo Código")
        cod = dialog.get_input()
        if cod:
            dialog2 = ctk.CTkInputDialog(text="Ingrese el Grupo de Cuenta (Ej: Gastos de personal):", title="Nuevo Código")
            nom = dialog2.get_input()
            if nom:
                try:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("CREATE TABLE IF NOT EXISTS maestro_cuentas (codigo TEXT, grupo_cuenta TEXT)")
                    cursor.execute("INSERT INTO maestro_cuentas VALUES (?, ?)", (cod, nom))
                    conn.commit()
                    conn.close()
                    self.log(f"[MAESTRO] Código '{cod}' -> '{nom}' agregado a la BD.")
                    messagebox.showinfo("Éxito", f"Código {cod} guardado correctamente.")
                except Exception as e:
                    self.log(f"[ERROR] Al guardar código: {e}")

    # ==========================================
    # API BCV
    # ==========================================
    def obtener_tasa_api(self):
        try:
            url_1 = "https://ve.dolarapi.com/v1/dolares/oficial"
            response = requests.get(url_1, timeout=10)
            if response.status_code == 200:
                self.tasa_bcv = float(response.json()['promedio'])
                self.after(0, lambda: self.lbl_tasa.configure(text=f"🟢 BCV: {self.tasa_bcv:,.2f} Bs/$", text_color="#2E8B57"))
                self.after(0, lambda: self.log(f"[API] Tasa BCV: {self.tasa_bcv} Bs/$"))
                return

            url_2 = "https://pydolarvenezuela-api.vercel.app/api/v1/dollar?page=bcv"
            response = requests.get(url_2, timeout=10)
            if response.status_code == 200:
                self.tasa_bcv = float(response.json()['monitors']['bcv']['price'])
                self.after(0, lambda: self.lbl_tasa.configure(text=f"🟢 BCV: {self.tasa_bcv:,.2f} Bs/$", text_color="#2E8B57"))
                self.after(0, lambda: self.log(f"[API] Tasa BCV: {self.tasa_bcv} Bs/$"))
                return
            raise Exception("Servidores caídos.")
        except Exception:
            self.after(0, lambda: self.lbl_tasa.configure(text="🔴 BCV: Fallo de red", text_color=BTN_DANGER))

    def editar_tasa_manual(self):
        dialog = ctk.CTkInputDialog(text="Ingrese la tasa BCV manual (Ej: 41.50):", title="Tasa BCV Manual")
        valor = dialog.get_input()
        if valor:
            try:
                self.tasa_bcv = float(valor.replace(',', '.'))
                self.lbl_tasa.configure(text=f"🟡 BCV (Manual): {self.tasa_bcv:,.2f} Bs/$", text_color=CANGURO_YELLOW)
                self.log(f"[SISTEMA] Tasa BCV fijada a: {self.tasa_bcv} Bs/$")
            except ValueError:
                messagebox.showerror("Error", "Número inválido.")

    # ==========================================
    # CARGA INTELIGENTE DE ARCHIVOS
    # ==========================================
    def cargar_archivo(self, tipo):
        archivo = filedialog.askopenfilename(title=f"Seleccionar Archivo {tipo.upper()}", filetypes=[("Archivos", "*.csv *.xlsx *.xls")])
        if not archivo: return
        
        # 1. EVITAR DUPLICADOS ABSOLUTOS
        rutas_activas = {
            "bifrost": self.ruta_bifrost,
            "ingresos": self.ruta_ingresos,
            "edr": self.ruta_edr,
            "promedios": self.ruta_promedios,
            "maestro": self.ruta_maestro
        }
        for key, path in rutas_activas.items():
            if path == archivo:
                messagebox.showerror("Archivo Duplicado", f"Ya subiste este archivo en el botón de '{key.upper()}'.\nNo puedes usar el mismo archivo para dos cosas distintas.")
                return

        # 2. INTELIGENCIA DE VALIDACIÓN (Previene Falsos Positivos)
        try:
            if archivo.endswith('.csv'):
                df_test = pd.read_csv(archivo, sep=';', nrows=1)
                if len(df_test.columns) == 1: df_test = pd.read_csv(archivo, sep=',', nrows=1)
            else:
                df_test = pd.read_excel(archivo, nrows=1)
                
            cols = [str(c).upper() for c in df_test.columns]
            
            if tipo == "maestro" and len(cols) > 4:
                messagebox.showerror("Error Semántico", "El Maestro de Cuentas debe tener solo 2 columnas (Código y Nombre).\nEstás intentando subir un archivo gigante (probablemente Bifrost).")
                return
            elif tipo == "bifrost" and len(cols) <= 2:
                messagebox.showerror("Error Semántico", "Este archivo solo tiene 2 columnas. Parece ser el Maestro de Cuentas, NO el reporte crudo de Bifrost.")
                return
            elif tipo == "ingresos" and not any(x in c for c in cols for x in ["MONTO", "USD", "MONEDA", "TRANSACCION"]):
                messagebox.showwarning("Advertencia", "Este archivo no parece contener las columnas de ingresos de Wilker. Verifica si es el correcto.")
        except Exception:
            pass # Si el test falla, igual lo deja pasar y que el motor central decida

        # 3. ASIGNACIÓN
        if tipo == "bifrost":
            self.ruta_bifrost = archivo
            self.btn_csv.configure(text="✅ Bifrost", fg_color="#2E8B57")
        elif tipo == "ingresos":
            self.ruta_ingresos = archivo
            self.btn_excel.configure(text="✅ Ingresos", fg_color="#2E8B57")
        elif tipo == "edr":
            self.ruta_edr = archivo
            self.btn_edr.configure(text="✅ EDR", fg_color="#2E8B57")
        elif tipo == "promedios":
            self.ruta_promedios = archivo
            self.btn_promedio.configure(text="✅ Promedios", fg_color="#2E8B57")
        elif tipo == "maestro":
            self.ruta_maestro = archivo
            self.btn_maestro.configure(text="✅ Maestro", fg_color="#2E8B57")
            
        self.log(f"[ARCHIVO] {tipo.upper()} enrutado con éxito.")

    def limpiar_ui(self):
        self.limpiar_rutas()
        self.btn_csv.configure(text="📄 CSV Bifrost", fg_color="#333333")
        self.btn_excel.configure(text="📄 CSV Ingresos", fg_color="#333333")
        self.btn_edr.configure(text="📄 Excel EDR", fg_color="#333333")
        self.btn_promedio.configure(text="📄 Excel Promedios", fg_color="#333333")
        self.btn_maestro.configure(text="📄 Plan/Maestro Cuentas", fg_color="#1F4E79")
        self.porcentajes_manuales.clear()
        
        self.tree_ingresos.delete(*self.tree_ingresos.get_children())
        self.tree_edr.delete(*self.tree_edr.get_children())
        self.tree_cierre.delete(*self.tree_cierre.get_children())
        self.df_actual = None
        for widget in self.tab_dashboards.winfo_children(): widget.destroy()
        self.log("[INFO] Interfaz limpiada.")

    def _llenar_tabla(self, treeview, df):
        treeview.delete(*treeview.get_children())
        if df.empty: return
        treeview["column"] = list(df.columns)
        treeview["show"] = "headings"
        for column in treeview["column"]:
            treeview.heading(column, text=str(column).upper(), anchor="w")
            max_data = df[column].astype(str).map(len).max() if not df[column].empty else 0
            treeview.column(column, width=max(min(max(max_data, len(str(column))) * 10, 350), 100), anchor="w", stretch=False)
        treeview.tag_configure("oddrow", background="#222222")
        treeview.tag_configure("evenrow", background="#161616")
        for i, row in enumerate(df.itertuples(index=False)):
            treeview.insert("", "end", values=[str(item) if pd.notnull(item) else "" for item in row], tags=("evenrow" if i % 2 == 0 else "oddrow",))

    def procesar_mes(self, recalcular=False):
        periodo = self.periodo_entry.get().strip()
        if not periodo:
            if not recalcular: messagebox.showwarning("Advertencia", "Ingrese un período válido.")
            return

        if not recalcular:
            for tree in [self.tree_ingresos, self.tree_edr, self.tree_cierre]: tree.delete(*tree.get_children())

            if not self.ruta_maestro and any([self.ruta_bifrost, self.ruta_ingresos, self.ruta_edr, self.ruta_promedios]):
                try:
                    conn = sqlite3.connect(self.db_path)
                    if conn.cursor().execute("SELECT name FROM sqlite_master WHERE type='table' AND name='maestro_cuentas'").fetchone():
                        if messagebox.askyesno("Maestro", "No subiste un Plan de Cuentas nuevo.\n\n¿Usar el de la memoria del sistema?"):
                            self.log("[SISTEMA] Utilizando Maestro Histórico.")
                    conn.close()
                except: pass

            if any([self.ruta_bifrost, self.ruta_ingresos, self.ruta_edr, self.ruta_promedios, self.ruta_maestro]):
                if not main.ingestar_datos(periodo, self.ruta_ingresos, self.ruta_bifrost, self.ruta_edr, self.ruta_promedios, self.ruta_maestro, log_callback=self.log):
                    messagebox.showerror("Error", "Falló la ingesta. Revise la terminal.")
                    return
            else:
                if not messagebox.askyesno("Atención", "No hay archivos nuevos.\n\n¿Consultar la BD?"): return

        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            if not recalcular:
                try: self._llenar_tabla(self.tree_ingresos, pd.read_sql_query("SELECT * FROM historico_ingresos WHERE periodo_carga = ? LIMIT 100", conn, params=(periodo,)))
                except: pass
                try: self._llenar_tabla(self.tree_edr, pd.read_sql_query("SELECT * FROM historico_bifrost WHERE periodo_carga = ? LIMIT 100", conn, params=(periodo,)))
                except: pass

            df_resultado = main.calcular_rentabilidad(periodo, self.db_path, self.porcentajes_manuales, log_callback=self.log)
            if not df_resultado.empty:
                self.df_actual = df_resultado 
                self._llenar_tabla(self.tree_cierre, df_resultado)
                self._dibujar_dashboards(df_resultado, periodo)
            else:
                self.log("[INFO] Sin rentabilidad generada.")
        except Exception as e: self.log(f"[ERROR CRÍTICO] {e}")
        finally:
            if conn: conn.close()

    def _dibujar_dashboards(self, df, periodo):
        for widget in self.tab_dashboards.winfo_children(): widget.destroy()
        if df.empty: return
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
        if self.df_actual is None or self.df_actual.empty: return
        ruta = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile=f"Reporte_Rentabilidad_{self.periodo_entry.get().strip()}.xlsx", filetypes=[("Archivos de Excel", "*.xlsx")])
        if ruta: self.df_actual.to_excel(ruta, index=False)

    def exportar_csv_bi(self):
        if self.df_actual is None or self.df_actual.empty: return
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=f"Dataset_PowerBI_{self.periodo_entry.get().strip()}.csv", filetypes=[("Archivo CSV", "*.csv")])
        if ruta: self.df_actual.to_csv(ruta, index=False, sep=';', decimal=',', encoding='utf-8-sig')

    def cerrar_app(self):
        try: plt.close('all')
        except: pass
        self.quit()
        self.destroy()

if __name__ == "__main__":
    app = CierreContableApp()
    app.mainloop()