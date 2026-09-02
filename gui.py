import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image
import pandas as pd
import sqlite3
import os
import main
import geodata
import requests
import threading
import numpy as np
from ctk_scrollable_dropdown import CTkScrollableDropdown

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.gridspec as gridspec

# Intentar aplicar el icono en la barra de tareas de Windows nativamente
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('canguro.motor.cierre.1.0')
except Exception:
    pass

# Configuración del Tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Paleta de Colores Corporativos
CANGURO_YELLOW = "#FFD700"
CANGURO_YELLOW_HOVER = "#E6C200"
CANGURO_BLACK = "#101010"
CANGURO_SIDEBAR = "#1A1A1A"
CANGURO_DARK_GREY = "#242424"
CANGURO_TEXT_LIGHT = "#FFFFFF"
CANGURO_TEXT_DARK = "#000000"
BTN_DANGER = "#D9534F"
BTN_DANGER_HOVER = "#C9302C"

# Paleta Neón para Dashboards
CHART_BG = "#1A1A1A"
C_CYAN = "#00E5FF"
C_MAGENTA = "#FF0055"
C_LIME = "#00E676"
C_YELLOW = "#FFD700"

class CierreContableApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Motor de Cierre Contable - Canguro")
        self.geometry("1350x800")
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
        self.periodo_actual = ""
        self.offsets = {'ingresos': 0, 'edr': 0, 'empleados': 0}
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
        self.ruta_empleados = None

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
        try:
            ruta_ico = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets", "icono.ico")
            if os.path.exists(ruta_ico): self.vent_term.after(200, lambda: self.vent_term.iconbitmap(ruta_ico))
        except: pass
        self.vent_term.withdraw()
        self.vent_term.protocol("WM_DELETE_WINDOW", self.vent_term.withdraw)
        
        self.consola = ctk.CTkTextbox(self.vent_term, fg_color=CANGURO_DARK_GREY, text_color=CANGURO_YELLOW, font=("Consolas", 12))
        self.consola.pack(fill="both", expand=True, padx=10, pady=10)
        self.consola.insert("0.0", "[SISTEMA INICIADO] Terminal operando...\n")
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
        self.header_sidebar = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.header_sidebar.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        self.logo_label = ctk.CTkLabel(self.header_sidebar, text="", image=logo_img if os.path.exists(ruta_logo) else None)
        self.logo_label.pack(side="left", expand=True)
        
        self.btn_toggle_in_sidebar = ctk.CTkButton(self.header_sidebar, text="☰", width=30, fg_color="transparent", hover_color="#333333", font=("Roboto", 18), command=self.toggle_sidebar)
        self.btn_toggle_in_sidebar.pack(side="right")
        
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
        # self.btn_promedio.grid(row=6, column=0, padx=20, pady=2, sticky="ew")  # Oculto por requerimiento

        self.btn_empleados = ctk.CTkButton(self.sidebar_frame, text="👥 Excel Empleados", fg_color="#1F4E79", hover_color="#296296", command=lambda: self.cargar_archivo("empleados"))
        self.btn_empleados.grid(row=7, column=0, padx=20, pady=(2, 0), sticky="ew")

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

        self.lbl_paso3 = ctk.CTkLabel(self.sidebar_frame, text="3. Filtro de Períodos", font=("Roboto", 13, "bold"))
        self.lbl_paso3.grid(row=12, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.frame_periodos = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.frame_periodos.grid(row=13, column=0, padx=20, pady=2, sticky="ew")
        self.frame_periodos.grid_columnconfigure((0, 1), weight=1)

        from tkcalendar import DateEntry

        self.periodo_desde = DateEntry(self.frame_periodos, width=12, background='#1F4E79', foreground='white', borderwidth=0, date_pattern='y-mm-dd')
        self.periodo_desde.grid(row=0, column=0, padx=(0, 2), sticky="ew")
        self.periodo_hasta = DateEntry(self.frame_periodos, width=12, background='#1F4E79', foreground='white', borderwidth=0, date_pattern='y-mm-dd')
        self.periodo_hasta.grid(row=0, column=1, padx=(2, 0), sticky="ew")

        self.btn_procesar = ctk.CTkButton(self.sidebar_frame, text="⚡ Consultar Histórico", fg_color=CANGURO_YELLOW, text_color=CANGURO_TEXT_DARK, hover_color=CANGURO_YELLOW_HOVER, font=("Roboto", 14, "bold"), command=self.procesar_mes)
        self.btn_procesar.grid(row=14, column=0, padx=20, pady=(15, 10), sticky="ew")

        self.btn_limpiar_bd = ctk.CTkButton(self.sidebar_frame, text="⚠️ LIMPIAR BASE DE DATOS", fg_color="#8B0000", hover_color="#A52A2A", font=("Roboto", 12, "bold"), command=self.limpiar_base_datos)
        self.btn_limpiar_bd.grid(row=15, column=0, padx=20, pady=(2, 10), sticky="ew")

        self.sidebar_frame.grid_rowconfigure(16, weight=1) 

        self.btn_export_excel = ctk.CTkButton(self.sidebar_frame, text="📊 Exportar Excel Final", fg_color="transparent", border_color=CANGURO_YELLOW, border_width=1, text_color=CANGURO_YELLOW, hover_color="#333333", command=self.exportar_excel)
        self.btn_export_excel.grid(row=17, column=0, padx=20, pady=2, sticky="ew")

        self.btn_export_bi = ctk.CTkButton(self.sidebar_frame, text="📈 Exportar CSV (PowerBI)", fg_color="transparent", border_color=CANGURO_YELLOW, border_width=1, text_color=CANGURO_YELLOW, hover_color="#333333", command=self.exportar_csv_bi)
        self.btn_export_bi.grid(row=18, column=0, padx=20, pady=(2, 10), sticky="ew")

        self.btn_terminal = ctk.CTkButton(self.sidebar_frame, text="💻 TERMINAL / LOGS", fg_color="#333333", hover_color="#555555", command=self.mostrar_terminal)
        self.btn_terminal.grid(row=19, column=0, padx=20, pady=(2, 5), sticky="ew")

        self.btn_salir = ctk.CTkButton(self.sidebar_frame, text="✖ CERRAR", fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER, font=("Roboto", 12, "bold"), command=self.cerrar_app)
        self.btn_salir.grid(row=20, column=0, padx=20, pady=(2, 15), sticky="ew")

    def _actualizar_reloj(self):
        from datetime import datetime
        # Formato de 12 horas DD/MM/AAAA sin formato militar
        ahora = datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")
        try:
            self.lbl_reloj.configure(text=ahora)
            self.after(1000, self._actualizar_reloj)
        except Exception:
            pass

    def _actualizar_labels_tasa(self, text, color):
        self.lbl_tasa.configure(text=text, text_color=color)
        if hasattr(self, 'lbl_tasa_top'):
            self.lbl_tasa_top.configure(text=text, text_color=color)

    def toggle_sidebar(self):
        if getattr(self, 'sidebar_expanded', True):
            # Ocultar panel (mostrar iconos)
            self.titulo_label.grid_remove()
            self.lbl_paso1.grid_remove()
            self.lbl_paso2.grid_remove()
            self.lbl_paso3.grid_remove()
            self.tasa_frame.grid_remove()
            self.frame_periodos.grid_remove()
            self.logo_label.pack_forget()
            
            # Ajustar header
            self.header_sidebar.grid(padx=5)
            self.btn_toggle_in_sidebar.pack(anchor="center", expand=True)

            botones = [
                (self.btn_csv, "📄"), (self.btn_excel, "📄"), (self.btn_edr, "📄"), 
                (self.btn_empleados, "👥"), (self.btn_limpiar, "🧹"),
                (self.btn_procesar, "⚡"), (self.btn_limpiar_bd, "⚠️"),
                (self.btn_export_excel, "📊"), (self.btn_export_bi, "📈"),
                (self.btn_terminal, "💻"), (self.btn_salir, "✖")
            ]
            for btn, icon in botones:
                btn.configure(text=icon, width=40)
                btn.grid(padx=10)
                
            self.sidebar_frame.configure(width=60)
            
            # Mostrar tasa debajo del reloj
            self.lbl_tasa_top.configure(text=self.lbl_tasa.cget("text"), text_color=self.lbl_tasa.cget("text_color"))
            self.lbl_tasa_top.pack(anchor="e")
            
            self.sidebar_expanded = False
        else:
            # Mostrar panel completo
            self.logo_label.pack(side="left", expand=True)
            self.btn_toggle_in_sidebar.pack_forget()
            self.btn_toggle_in_sidebar.pack(side="right")
            
            self.header_sidebar.grid(padx=20)
            self.titulo_label.grid()
            self.lbl_paso1.grid()
            self.lbl_paso2.grid()
            self.lbl_paso3.grid()
            self.tasa_frame.grid()
            self.frame_periodos.grid()
            
            botones = [
                (self.btn_csv, "📄 CSV Bifrost"), (self.btn_excel, "📄 CSV Ingresos"), 
                (self.btn_edr, "📄 Excel EDR"), (self.btn_empleados, "👥 Excel Empleados"), 
                (self.btn_limpiar, "🧹 Limpiar Archivos"),
                (self.btn_procesar, "⚡ Consultar Histórico"), (self.btn_limpiar_bd, "⚠️ LIMPIAR BASE DE DATOS"),
                (self.btn_export_excel, "📊 Exportar Excel Final"), (self.btn_export_bi, "📈 Exportar CSV (PowerBI)"),
                (self.btn_terminal, "💻 TERMINAL / LOGS"), (self.btn_salir, "✖ CERRAR")
            ]
            for btn, texto in botones:
                btn.configure(text=texto, width=240)
                btn.grid(padx=20)
                
            self.sidebar_frame.configure(width=280)
            
            # Ocultar tasa del header
            self.lbl_tasa_top.pack_forget()
            
            self.sidebar_expanded = True

    def _crear_area_principal(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=0)
        self.main_frame.grid_rowconfigure(1, weight=1)

        self.top_bar = ctk.CTkFrame(self.main_frame, height=30, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        self.reloj_tasa_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.reloj_tasa_frame.pack(side="right", padx=10)

        # Reloj principal en la barra superior (esquina derecha)
        self.lbl_reloj = ctk.CTkLabel(self.reloj_tasa_frame, text="", font=("Roboto", 14, "bold"), text_color="white")
        self.lbl_reloj.pack(anchor="e")
        
        self.lbl_tasa_top = ctk.CTkLabel(self.reloj_tasa_frame, text="", font=("Roboto", 12, "bold"), text_color=CANGURO_YELLOW)
        self.lbl_tasa_top.pack_forget()
        
        self._actualizar_reloj()

        self.tab_view = ctk.CTkTabview(self.main_frame, fg_color=CANGURO_DARK_GREY, segmented_button_selected_color=CANGURO_YELLOW, segmented_button_selected_hover_color=CANGURO_YELLOW_HOVER, text_color=CANGURO_TEXT_DARK)
        self.tab_view.grid(row=1, column=0, sticky="nsew")
        
        self.tab_ingresos = self.tab_view.add("Auditoría Ingresos")
        self.tab_edr = self.tab_view.add("Auditoría EDR")
        self.tab_cierre = self.tab_view.add("Estado Resultados y Rentabilidad")
        self.tab_empleados = self.tab_view.add("RRHH / Empleados")
        self.tab_dashboards = self.tab_view.add("Dashboards Visuales (BI)")

        self.frame_t1, self.tree_ingresos = self._crear_arbol(self.tab_ingresos)
        self.frame_t1.pack(fill="both", expand=True)
        self._crear_paginacion(self.tab_ingresos, 'ingresos')

        self.frame_t2, self.tree_edr = self._crear_arbol(self.tab_edr)
        self.frame_t2.pack(fill="both", expand=True)
        self._crear_paginacion(self.tab_edr, 'edr')

        self.btn_ajuste_pct = ctk.CTkButton(self.tab_cierre, text="✏️ Ajustar % Impacto Manual", command=self.abrir_ventana_ajuste, fg_color="#1F4E79", hover_color="#296296")
        self.btn_ajuste_pct.pack(anchor="w", pady=(0, 5))
        self.frame_t3, self.tree_cierre = self._crear_arbol(self.tab_cierre)
        self.frame_t3.pack(fill="both", expand=True)

        self.frame_t4, self.tree_empleados = self._crear_arbol(self.tab_empleados)
        self.frame_t4.pack(fill="both", expand=True)
        self._crear_paginacion(self.tab_empleados, 'empleados')
        
        # --- ZONA DASHBOARDS (BI) ---
        self.tab_dashboards.grid_columnconfigure(0, weight=1)
        self.tab_dashboards.grid_rowconfigure(2, weight=1)

        # 1. Filtros del Dashboard (CON EL BOTON DE APLICAR)
        self.dash_filter_frame = ctk.CTkFrame(self.tab_dashboards, fg_color="#1A1A1A", corner_radius=8)
        self.dash_filter_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5), ipadx=5, ipady=5)
        
        lbl_panel = ctk.CTkLabel(self.dash_filter_frame, text="📊 Panel Gerencial", font=("Roboto", 14, "bold"), text_color=CANGURO_YELLOW)
        lbl_panel.pack(side="left", padx=10)
        
        self.combo_ciudad = ctk.CTkComboBox(self.dash_filter_frame, values=["Todas las Ciudades"], width=220, command=self._on_ciudad_selected)
        self.combo_ciudad.pack(side="left", padx=5)
        
        self.combo_region = ctk.CTkComboBox(self.dash_filter_frame, values=["Todas las Regiones"], width=180, command=self._on_region_selected)
        self.combo_region.pack(side="left", padx=5)
        
        self.btn_filtrar = ctk.CTkButton(self.dash_filter_frame, text="🔍 Aplicar Filtro", fg_color="#1F4E79", width=100, command=self.aplicar_filtro_dash)
        self.btn_filtrar.pack(side="left", padx=5)
        
        self.btn_fullscreen = ctk.CTkButton(self.dash_filter_frame, text="🗖 Pantalla Completa", width=120, command=self.abrir_dashboard_ampliado, fg_color=CANGURO_YELLOW, text_color="#000000")
        self.btn_fullscreen.pack(side="right", padx=10)

        # 2. Marco para KPIs numéricos (Arriba)
        self.kpi_container = ctk.CTkFrame(self.tab_dashboards, fg_color="transparent", height=60)
        self.kpi_container.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        
        # 3. Marco para los Gráficos de Matplotlib (Abajo)
        self.dash_chart_frame = ctk.CTkFrame(self.tab_dashboards, fg_color="transparent")
        self.dash_chart_frame.grid(row=2, column=0, sticky="nsew")
        self.canvas_dash = None 

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

    def _crear_paginacion(self, parent, tabla):
        frame_pag = ctk.CTkFrame(parent, fg_color="transparent", height=40)
        frame_pag.pack(fill="x", pady=5)
        
        btn_prev = ctk.CTkButton(frame_pag, text="⬅ Anterior", width=100, command=lambda: self.cambiar_pagina(tabla, -100))
        btn_prev.pack(side="left", padx=10)
        
        lbl_pag = ctk.CTkLabel(frame_pag, text="Registros 1 - 100", font=("Roboto", 12))
        lbl_pag.pack(side="left", expand=True)
        setattr(self, f"lbl_pag_{tabla}", lbl_pag)
        
        btn_next = ctk.CTkButton(frame_pag, text="Siguiente ➡", width=100, command=lambda: self.cambiar_pagina(tabla, 100))
        btn_next.pack(side="right", padx=10)

    def cambiar_pagina(self, tabla, delta):
        if not hasattr(self, 'offsets'): self.offsets = {'ingresos': 0, 'edr': 0, 'empleados': 0}
        nuevo_offset = self.offsets[tabla] + delta
        if nuevo_offset < 0: nuevo_offset = 0
        self.offsets[tabla] = nuevo_offset
        
        lbl = getattr(self, f"lbl_pag_{tabla}")
        lbl.configure(text=f"Registros {nuevo_offset + 1} - {nuevo_offset + 100}")
        
        desde_raw = self.periodo_desde.get().strip()
        hasta_raw = self.periodo_hasta.get().strip()
        desde = desde_raw[:7] if len(desde_raw) >= 7 else desde_raw
        hasta = hasta_raw[:7] if len(hasta_raw) >= 7 else hasta_raw
        
        threading.Thread(target=self._cargar_pagina, args=(tabla, desde, hasta, nuevo_offset), daemon=True).start()

    def _cargar_pagina(self, tabla, desde, hasta, offset):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            if tabla == 'ingresos':
                df = pd.read_sql_query(f"SELECT * FROM historico_ingresos WHERE periodo_carga BETWEEN ? AND ? LIMIT 100 OFFSET {offset}", conn, params=(desde, hasta))
                if 'periodo_carga' in df.columns: df.drop(columns=['periodo_carga'], inplace=True)
                self.after(0, self._llenar_tabla, self.tree_ingresos, df)
            elif tabla == 'edr':
                df = pd.read_sql_query(f"SELECT * FROM historico_bifrost WHERE periodo_carga BETWEEN ? AND ? LIMIT 100 OFFSET {offset}", conn, params=(desde, hasta))
                if 'periodo_carga' in df.columns: df.drop(columns=['periodo_carga'], inplace=True)
                self.after(0, self._llenar_tabla, self.tree_edr, df)
            elif tabla == 'empleados':
                df = pd.read_sql_query(f"SELECT * FROM historico_empleados WHERE periodo_carga BETWEEN ? AND ? LIMIT 100 OFFSET {offset}", conn, params=(desde, hasta))
                if 'periodo_carga' in df.columns: df.drop(columns=['periodo_carga'], inplace=True)
                self.after(0, self._llenar_tabla, self.tree_empleados, df)
        except Exception as e:
            self.log(f"[ERROR PAGINACIÓN] {e}")
        finally:
            if conn: conn.close()

    def abrir_ventana_ajuste(self):
        if self.df_actual is None or self.df_actual.empty:
            messagebox.showwarning("Aviso", "Procesa un mes primero para poder ajustar sus porcentajes.")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Ajuste Manual de Porcentaje")
        dialog.geometry("350x250")
        dialog.attributes("-topmost", True)
        try:
            ruta_ico = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets", "icono.ico")
            if os.path.exists(ruta_ico): dialog.after(200, lambda: dialog.iconbitmap(ruta_ico))
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

    def obtener_tasa_api(self):
        try:
            url_1 = "https://ve.dolarapi.com/v1/dolares/oficial"
            response = requests.get(url_1, timeout=10)
            if response.status_code == 200:
                self.tasa_bcv = float(response.json()['promedio'])
                try:
                    self.after(0, lambda: self._actualizar_labels_tasa(f"🟢 BCV: {self.tasa_bcv:,.2f} Bs/$", "#2E8B57"))
                    self.after(0, lambda: self.log(f"[API] Tasa BCV: {self.tasa_bcv} Bs/$"))
                except Exception: pass
                return

            url_2 = "https://pydolarvenezuela-api.vercel.app/api/v1/dollar?page=bcv"
            response = requests.get(url_2, timeout=10)
            if response.status_code == 200:
                self.tasa_bcv = float(response.json()['monitors']['bcv']['price'])
                try:
                    self.after(0, lambda: self._actualizar_labels_tasa(f"🟢 BCV: {self.tasa_bcv:,.2f} Bs/$", "#2E8B57"))
                    self.after(0, lambda: self.log(f"[API] Tasa BCV: {self.tasa_bcv} Bs/$"))
                except Exception: pass
                return
            raise Exception("Servidores caídos.")
        except Exception:
            try:
                self.after(0, lambda: self._actualizar_labels_tasa("🔴 BCV: Fallo de red", BTN_DANGER))
            except Exception: pass

    def editar_tasa_manual(self):
        dialog = ctk.CTkInputDialog(text="Ingrese la tasa BCV manual (Ej: 41.50):", title="Tasa BCV Manual")
        valor = dialog.get_input()
        if valor:
            try:
                self.tasa_bcv = float(valor.replace(',', '.'))
                self._actualizar_labels_tasa(f"🟡 BCV (Manual): {self.tasa_bcv:,.2f} Bs/$", CANGURO_YELLOW)
                self.log(f"[SISTEMA] Tasa BCV fijada a: {self.tasa_bcv} Bs/$")
            except ValueError:
                messagebox.showerror("Error", "Número inválido.")

    def cargar_archivo(self, tipo):
        archivo = filedialog.askopenfilename(title=f"Seleccionar Archivo {tipo.upper()}", filetypes=[("Archivos", "*.csv *.xlsx *.xls")])
        if not archivo: return
        
        rutas_activas = {"bifrost": self.ruta_bifrost, "ingresos": self.ruta_ingresos, "edr": self.ruta_edr, "promedios": self.ruta_promedios, "empleados": self.ruta_empleados}
        for key, path in rutas_activas.items():
            if path == archivo:
                messagebox.showerror("Archivo Duplicado", f"Ya subiste este archivo en el botón de '{key.upper()}'.\nNo puedes usar el mismo archivo para dos cosas distintas.")
                return

        try:
            if archivo.endswith('.csv'):
                df_test = pd.read_csv(archivo, sep=';', nrows=1)
                if len(df_test.columns) == 1: df_test = pd.read_csv(archivo, sep=',', nrows=1)
            else:
                df_test = pd.read_excel(archivo, nrows=1)
                
            cols = [str(c).upper() for c in df_test.columns]
            
            if tipo == "bifrost" and len(cols) <= 2:
                messagebox.showerror("Error Semántico", "Este archivo solo tiene 2 columnas. Parece ser un Maestro de Cuentas, NO el reporte crudo.")
                return
            elif tipo == "ingresos" and not any(x in c for c in cols for x in ["MONTO", "USD", "MONEDA", "TRANSACCION"]):
                messagebox.showwarning("Advertencia", "Este archivo no parece contener las columnas de ingresos.")
        except Exception:
            pass 

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
        elif tipo == "empleados":
            self.ruta_empleados = archivo
            self.btn_empleados.configure(text="✅ Empleados", fg_color="#2E8B57")
            
        self.log(f"[ARCHIVO] {tipo.upper()} enrutado con éxito.")
        
        # Bloquear filtros de consulta durante modo ingesta
        self.periodo_desde.configure(state="disabled")
        self.periodo_hasta.configure(state="disabled")
        self.btn_procesar.configure(text="⚡ INGESTAR AL HISTÓRICO", state="normal")

    def limpiar_base_datos(self):
        respuesta = messagebox.askyesno("Limpiar Base de Datos", "⚠️ ADVERTENCIA CRÍTICA: Esto eliminará de forma irreversible todo el histórico de la base de datos (Ingresos, Empleados, Bifrost).\n¿Estás completamente seguro de que deseas continuar?")
        if respuesta:
            import main
            if main.limpiar_bd():
                self.log("[SISTEMA] Base de datos histórica ELIMINADA.")
                messagebox.showinfo("Éxito", "Base de datos borrada. Debe cargar los archivos necesarios para procesar el histórico nuevamente.")
                self.limpiar_ui()
            else:
                self.log("[ERROR] No se pudo limpiar la base de datos.")

    def limpiar_ui(self):
        self.limpiar_rutas()
        self.btn_csv.configure(text="📄 CSV Bifrost", fg_color="#333333")
        self.btn_excel.configure(text="📄 CSV Ingresos", fg_color="#333333")
        self.btn_edr.configure(text="📄 Excel EDR", fg_color="#333333")
        self.btn_promedio.configure(text="📄 Excel Promedios", fg_color="#333333")
        self.btn_empleados.configure(text="👥 Excel Empleados", fg_color="#1F4E79")
        self.porcentajes_manuales.clear()
        
        self.periodo_desde.configure(state="normal")
        self.periodo_hasta.configure(state="normal")
        self.btn_procesar.configure(text="⚡ Consultar Histórico", state="normal")
        
        self.tree_ingresos.delete(*self.tree_ingresos.get_children())
        self.tree_edr.delete(*self.tree_edr.get_children())
        self.tree_cierre.delete(*self.tree_cierre.get_children())
        self.tree_empleados.delete(*self.tree_empleados.get_children())
        self.df_actual = None
        if self.canvas_dash: 
            self.canvas_dash.get_tk_widget().destroy()
            self.canvas_dash = None
        for widget in self.kpi_container.winfo_children(): widget.destroy()
        self.log("[INFO] Interfaz limpiada.")

    def _llenar_tabla(self, treeview, df):
        treeview.delete(*treeview.get_children())
        if df.empty: return
        
        col_ids = [f"col_{i}" for i in range(len(df.columns))]
        treeview["column"] = col_ids
        treeview["show"] = "headings"
        for i, column in enumerate(df.columns):
            cid = col_ids[i]
            treeview.heading(cid, text=str(column).upper(), anchor="w")
            max_data = df[column].fillna("").astype(str).map(len).max() if not df[column].empty else 0
            treeview.column(cid, width=max(min(max(max_data, len(str(column))) * 10, 350), 100), anchor="w", stretch=False)
        treeview.tag_configure("oddrow", background="#222222")
        treeview.tag_configure("evenrow", background="#161616")
        for i, row in enumerate(df.itertuples(index=False)):
            treeview.insert("", "end", values=[str(item) if pd.notnull(item) else "" for item in row], tags=("evenrow" if i % 2 == 0 else "oddrow",))

    def procesar_mes(self, recalcular=False):
        desde_raw = self.periodo_desde.get().strip()
        hasta_raw = self.periodo_hasta.get().strip()
        
        # Como la BD guarda YYYY-MM, cortamos hasta el mes si nos dan un día
        desde = desde_raw[:7] if len(desde_raw) >= 7 else desde_raw
        hasta = hasta_raw[:7] if len(hasta_raw) >= 7 else hasta_raw
        
        # Modo Consulta requiere fechas si no estamos ingiriendo
        hay_archivos = any([self.ruta_bifrost, self.ruta_ingresos, self.ruta_edr, self.ruta_promedios, self.ruta_empleados])
        if not hay_archivos and not (desde and hasta):
            if not recalcular: messagebox.showwarning("Advertencia", "Por favor ingrese el rango (Desde y Hasta) para consultar.")
            return
            
        self.periodo_actual = f"{desde} al {hasta}"

        if not recalcular:
            self.offsets = {'ingresos': 0, 'edr': 0, 'empleados': 0}
            try:
                self.lbl_pag_ingresos.configure(text="Registros 1 - 100")
                self.lbl_pag_edr.configure(text="Registros 1 - 100")
                self.lbl_pag_empleados.configure(text="Registros 1 - 100")
            except: pass

            for tree in [self.tree_ingresos, self.tree_edr, self.tree_cierre, self.tree_empleados]: tree.delete(*tree.get_children())

            if hay_archivos:
                self.btn_procesar.configure(state="disabled", text="PROCESANDO...")
                threading.Thread(target=self._hilo_ingesta_y_consulta, args=(desde, hasta), daemon=True).start()
                return
            else:
                threading.Thread(target=self._hilo_ingesta_y_consulta, args=(desde, hasta, False), daemon=True).start()
                return

    def _hilo_ingesta_y_consulta(self, desde, hasta, ingestar=True):
        import main
        if ingestar:
            if not main.ingestar_datos(self.ruta_ingresos, self.ruta_bifrost, self.ruta_edr, self.ruta_promedios, self.ruta_empleados, log_callback=self.log):
                self.after(0, lambda: messagebox.showerror("Error", "Falló la ingesta. Revise la terminal."))
                self.after(0, lambda: self.btn_procesar.configure(state="normal", text="⚡ INGESTAR AL HISTÓRICO"))
                return
            self.after(0, lambda: messagebox.showinfo("Éxito", "Archivos procesados y añadidos al histórico. La UI se limpiará ahora."))
            self.after(0, self.limpiar_ui)
            return
            
        # MODO CONSULTA PURA
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            try: 
                df_ingresos = pd.read_sql_query("SELECT * FROM historico_ingresos WHERE periodo_carga BETWEEN ? AND ? LIMIT 100", conn, params=(desde, hasta))
                if 'periodo_carga' in df_ingresos.columns: df_ingresos.drop(columns=['periodo_carga'], inplace=True)
                self.after(0, self._llenar_tabla, self.tree_ingresos, df_ingresos)
            except: pass
            try: 
                df_bifrost = pd.read_sql_query("SELECT * FROM historico_bifrost WHERE periodo_carga BETWEEN ? AND ? LIMIT 100", conn, params=(desde, hasta))
                if 'periodo_carga' in df_bifrost.columns: df_bifrost.drop(columns=['periodo_carga'], inplace=True)
                self.after(0, self._llenar_tabla, self.tree_edr, df_bifrost)
            except: pass
            
            try: 
                df_empleados = pd.read_sql_query("SELECT * FROM historico_empleados WHERE periodo_carga BETWEEN ? AND ? LIMIT 100", conn, params=(desde, hasta))
                if 'periodo_carga' in df_empleados.columns: df_empleados.drop(columns=['periodo_carga'], inplace=True)
                self.after(0, self._llenar_tabla, self.tree_empleados, df_empleados)
            except: pass

            df_resultado = main.calcular_rentabilidad(desde, hasta, self.db_path, self.porcentajes_manuales, log_callback=self.log)
            if not df_resultado.empty:
                self.df_actual = df_resultado 
                self.after(0, self._llenar_tabla, self.tree_cierre, df_resultado)
                # Como self._actualizar_filtros_combobox hace queries, lo ejecuto aquí mismo en el hilo secundario
                self._actualizar_filtros_combobox(conn, df_resultado)
                
                # Y el dibujado en el hilo principal
                ciudad = None if self.combo_ciudad.get() == "Todas las Ciudades" else self.combo_ciudad.get()
                self.after(0, self._dibujar_dashboards, df_resultado, self.periodo_actual, ciudad)
            else:
                self.log("[INFO] Sin rentabilidad generada.")
                
        except Exception as e: self.log(f"[ERROR CRÍTICO] {e}")
        finally:
            if conn: conn.close()

    def _actualizar_filtros_combobox(self, conn, df):
        """Llena la barra superior con las ciudades y meses históricos"""
        
        # 1. CIUDADES
        todas_las_tiendas = df['CENTRO DE COSTO / TIENDA'].tolist()
        tiendas_acronimo = [t for t in todas_las_tiendas if str(t).strip().startswith('[')]
        tiendas = ["Todas las Ciudades"] + sorted(list(set(tiendas_acronimo)))
        self.combo_ciudad.configure(values=tiendas)
        
        if hasattr(self, 'scroll_ciudad'):
            self.scroll_ciudad.destroy()
        self.scroll_ciudad = CTkScrollableDropdown(self.combo_ciudad, values=tiendas, command=self._on_ciudad_selected, justify="left", button_color="transparent")
        
        self.combo_ciudad.set("Todas las Ciudades")

        # 3. REGIONES
        import regiones
        regs = ["Todas las Regiones"] + sorted(list(set(regiones.REGIONES.values())))
        self.combo_region.configure(values=regs)
        
        # --- INYECCIÓN DEL SCROLL PARA REGIÓN ---
        if hasattr(self, 'scroll_region'):
            self.scroll_region.destroy()
        self.scroll_region = CTkScrollableDropdown(self.combo_region, values=regs, command=self._on_region_selected, justify="left", button_color="transparent")
        # ----------------------------------------
        
        self.combo_region.set("Todas las Regiones")

    def _on_ciudad_selected(self, val):
        if val != "Todas las Ciudades":
            self.combo_region.set("Todas las Regiones")
        self.aplicar_filtro_dash()

    def _on_region_selected(self, val):
        if val != "Todas las Regiones":
            self.combo_ciudad.set("Todas las Ciudades")
        self.aplicar_filtro_dash()

    def aplicar_filtro_dash(self):
        """Recalcula el dashboard si escogen una sola ciudad o un mes viejo"""
        if self.df_actual is None or self.df_actual.empty:
            return
        
        ciu_sel = self.combo_ciudad.get()
        reg_sel = self.combo_region.get()

        df_filtro = self.df_actual.copy()
        
        import regiones
        df_filtro['REGION'] = df_filtro['CENTRO DE COSTO / TIENDA'].map(regiones.REGIONES).fillna("OTRO")
        
        tienda_sel = None
        if ciu_sel != "Todas las Ciudades":
            tienda_sel = ciu_sel
            df_filtro = df_filtro[df_filtro['CENTRO DE COSTO / TIENDA'] == ciu_sel]
        elif reg_sel != "Todas las Regiones":
            df_filtro = df_filtro[df_filtro['REGION'] == reg_sel]
            
        self._dibujar_dashboards(df_filtro, self.periodo_actual, tienda_seleccionada=tienda_sel)


    # ==========================================
    # MODULO BI: DASHBOARDS (CON MAPA DE VENEZUELA Y DONAS OPTIMIZADAS)
    # ==========================================
    def _crear_kpi_card(self, parent, titulo, valor, color_valor):
        """Dibuja un rectángulo moderno para indicadores clave"""
        card = ctk.CTkFrame(parent, fg_color="#222222", corner_radius=5)
        card.pack(side="left", fill="both", expand=True, padx=5)
        
        lbl_tit = ctk.CTkLabel(card, text=titulo.upper(), font=("Roboto", 11, "bold"), text_color="#AAAAAA")
        lbl_tit.pack(anchor="w", padx=15, pady=(10, 0))
        
        lbl_val = ctk.CTkLabel(card, text=valor, font=("Roboto", 22, "bold"), text_color=color_valor)
        lbl_val.pack(anchor="w", padx=15, pady=(0, 10))

    def _crear_figura_dashboard(self, df, periodo, tienda_seleccionada=None):
        """Genera el Grid de Matplotlib. Mapa de Venezuela maximizado y 4 Donas informativas con montos y porcentajes."""
        plt.style.use("dark_background")
        fig = Figure(figsize=(14, 8), dpi=100)
        fig.patch.set_facecolor(CHART_BG)
        
        if df.empty: return fig

        # Formateador de divisas compacto y legible
        def fmt_monto(val):
            if abs(val) >= 1_000_000:
                return f"${val/1_000_000:.2f}M"
            elif abs(val) >= 1_000:
                return f"${val/1_000:.1f}K"
            else:
                return f"${val:,.0f}"

        # --- MARCA DE AGUA (LOGO DE FONDO) ---
        try:
            ruta_logo = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets", "logo.png")
            if os.path.exists(ruta_logo):
                img = plt.imread(ruta_logo)
                ax_bg = fig.add_axes([0, 0, 1, 1], zorder=-1)
                ax_bg.axis('off')
                ax_bg.imshow(img, alpha=0.03, aspect='auto') 
        except Exception:
            pass

        # Configurar la Cuadrícula: Margen superior optimizado para que los títulos nunca se corten
        gs = gridspec.GridSpec(2, 4, figure=fig, height_ratios=[1.60, 1.0], left=0.015, right=0.985, top=0.92, bottom=0.07, wspace=0.18, hspace=0.25)

        cols_base = ['CENTRO DE COSTO / TIENDA', 'INGRESOS TOTALES (USD)', '% IMPACTO', 'GASTO APLICADO (PRORRATEO)', 'REGION', 'ingresos', 'otros_ingresos', 'costo_directo']
        gastos_cols = [c for c in df.columns if c not in cols_base and c != '% IMPACTO NUM']

        df_plot = df.copy()
        df_plot['CORTA'] = df_plot['CENTRO DE COSTO / TIENDA'].apply(lambda x: str(x).split('-')[-1].strip() if '-' in str(x) else str(x))

        # ---------------------------------------------------------
        # AX1: MAPA VECTORIAL DE VENEZUELA CON TIENDAS Y ESTADOS
        # ---------------------------------------------------------
        ax_map = fig.add_subplot(gs[0, 0:2])
        df_origen_mapa = self.df_actual if (self.df_actual is not None and not self.df_actual.empty) else df_plot
        geodata.dibujar_mapa_venezuela(ax_map, df_origen_mapa, tienda_seleccionada=tienda_seleccionada)

        # ---------------------------------------------------------
        # AX2: CURVA DE INGRESOS (TENDENCIA GENERAL O COMPARATIVA)
        # ---------------------------------------------------------
        ax_area = fig.add_subplot(gs[0, 2:4])
        ax_area.set_facecolor(CHART_BG)
        
        if tienda_seleccionada and self.df_actual is not None and len(self.df_actual) > 1:
            df_trend = self.df_actual.head(15).copy().reset_index(drop=True)
            def _corta_nombre(x):
                s = str(x).split('-')[-1].strip() if '-' in str(x) else str(x)
                return s[:12] + '..' if len(s) > 12 else s
            df_trend['CORTA'] = df_trend['CENTRO DE COSTO / TIENDA'].apply(_corta_nombre)
            x = np.arange(len(df_trend))
            y = df_trend['INGRESOS TOTALES (USD)']
            
            ax_area.plot(x, y, color=C_CYAN, lw=2, alpha=0.85)
            ax_area.fill_between(x, y, 0, color=C_CYAN, alpha=0.15)
            
            # Resaltar la sede si está en el top visible
            idx_t = df_trend.index[df_trend['CENTRO DE COSTO / TIENDA'] == tienda_seleccionada].tolist()
            if idx_t:
                pos = idx_t[0]
                val_y = float(y.iloc[pos])
                ax_area.scatter([pos], [val_y], color=C_YELLOW, s=120, zorder=5, edgecolors='#FFFFFF', linewidth=1.5)
                max_val = float(y.max()) if len(y) > 0 else 1.0
                ax_area.annotate(f"Sede Actual\n${val_y:,.0f}", (pos, val_y),
                                 xytext=(pos, val_y + (max_val*0.12 if val_y < max_val*0.75 else -max_val*0.18)),
                                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#111111", edgecolor=C_YELLOW, alpha=0.9),
                                 fontsize=7.5, color=C_YELLOW, fontweight='bold', ha='center',
                                 arrowprops=dict(arrowstyle="->", color=C_YELLOW))
                                 
            ax_area.set_xticks(x)
            ax_area.set_xticklabels(df_trend['CORTA'], rotation=40, ha='right', fontsize=6.5, color='#CCCCCC')
            ax_area.set_title("Comparativa de Tendencia (Top Tiendas)", color='white', pad=10, fontweight='bold', loc='left')
        else:
            df_trend = df_plot.head(15).copy().reset_index(drop=True)
            def _corta_nombre2(x):
                s = str(x).split('-')[-1].strip() if '-' in str(x) else str(x)
                return s[:12] + '..' if len(s) > 12 else s
            df_trend['CORTA'] = df_trend['CENTRO DE COSTO / TIENDA'].apply(_corta_nombre2)
            x = np.arange(len(df_trend))
            y = df_trend['INGRESOS TOTALES (USD)']
            
            ax_area.plot(x, y, color=C_CYAN, lw=2)
            ax_area.fill_between(x, y, 0, color=C_CYAN, alpha=0.2)
            ax_area.set_xticks(x)
            ax_area.set_xticklabels(df_trend['CORTA'], rotation=40, ha='right', fontsize=6.5, color='#CCCCCC')
            ax_area.set_title("Curva de Tendencia de Ingresos", color='white', pad=10, fontweight='bold', loc='left')

        ax_area.tick_params(axis='y', labelsize=8, colors='#CCCCCC')
        ax_area.tick_params(axis='x', labelsize=6.5, colors='#CCCCCC', pad=1)
        ax_area.spines['top'].set_visible(False)
        ax_area.spines['right'].set_visible(False)
        ax_area.grid(axis='y', linestyle='--', alpha=0.1)

        # Guardar datos para interactividad hover
        fig._hover_data = {
            'ax_area': ax_area,
            'df_trend': df_trend,
            'x': x,
            'y': y
        }

        # ---------------------------------------------------------
        # AX4: GRAFICOS DE DONA INFORMATIVOS Y CON MONTOS CLAROS
        # ---------------------------------------------------------
        def draw_donut(ax, sizes, labels, colors, title, center_top=None, center_sub=None):
            ax.clear()
            ax.set_facecolor(CHART_BG)
            sizes_clean = [max(0, float(s)) for s in sizes] if sizes else []
            total_s = sum(sizes_clean)
            
            if not sizes_clean or total_s <= 0:
                ax.pie([1], colors=['#262626'], radius=0.82, wedgeprops=dict(width=0.30, edgecolor=CHART_BG))
                if center_top:
                    ax.text(0, 0.08, str(center_top), ha='center', va='center', color='#999999', fontsize=8.0, fontweight='bold')
                if center_sub:
                    ax.text(0, -0.15, str(center_sub), ha='center', va='center', color='#666666', fontsize=7.2)
                ax.set_title(title, color='#AAAAAA', pad=6, fontweight='bold', fontsize=9.0)
                if labels:
                    h_prox = [plt.Rectangle((0,0),1,1, color='#262626') for _ in labels]
                    ax.legend(h_prox, labels, loc="lower center", bbox_to_anchor=(0.5, -0.18), fontsize=7.0, frameon=False, ncol=1)
                return

            ax.pie(
                sizes_clean,
                colors=colors,
                radius=0.82,
                wedgeprops=dict(width=0.30, edgecolor=CHART_BG)
            )
            
            if center_top:
                ax.text(0, 0.08, str(center_top), ha='center', va='center', color='white', fontsize=8.0, fontweight='bold')
            if center_sub:
                ax.text(0, -0.15, str(center_sub), ha='center', va='center', color=C_YELLOW, fontsize=7.5, fontweight='bold')

            ax.set_title(title, color='white', pad=6, fontweight='bold', fontsize=9.0)
            if labels:
                h_colors = colors if colors else ['#262626']
                handles = [plt.Rectangle((0,0),1,1, color=h_colors[i % len(h_colors)]) for i in range(len(labels))]
                ax.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, -0.18), fontsize=7.0, frameon=False, ncol=1)

        # Dona 1: Concentración Ingresos / Cuota de la Tienda
        ax_d1 = fig.add_subplot(gs[1, 0])
        if tienda_seleccionada and self.df_actual is not None and not self.df_actual.empty:
            ing_t = df_plot['INGRESOS TOTALES (USD)'].sum()
            ing_total_emp = self.df_actual['INGRESOS TOTALES (USD)'].sum()
            resto_rev = max(ing_total_emp - ing_t, 0)
            pct_cuota = (ing_t / ing_total_emp * 100) if ing_total_emp > 0 else 0
            pct_resto = 100.0 - pct_cuota
            labs_d1 = [f"Sede: {fmt_monto(ing_t)} ({pct_cuota:.1f}%)", f"Resto: {fmt_monto(resto_rev)} ({pct_resto:.1f}%)"]
            draw_donut(ax_d1, [ing_t, resto_rev], labs_d1, [C_YELLOW, '#383838'], "Cuota en Ventas", center_top="Cuota", center_sub=f"{pct_cuota:.1f}%")
        else:
            top3_rev = df_plot.head(3)['INGRESOS TOTALES (USD)'].sum()
            resto_rev = df_plot.iloc[3:]['INGRESOS TOTALES (USD)'].sum() if len(df_plot) > 3 else 0
            total_rev = top3_rev + resto_rev
            p_top3 = (top3_rev / total_rev * 100) if total_rev > 0 else 0
            p_resto = (resto_rev / total_rev * 100) if total_rev > 0 else 0
            labs_d1 = [f"Top 3: {fmt_monto(top3_rev)} ({p_top3:.1f}%)", f"Resto: {fmt_monto(resto_rev)} ({p_resto:.1f}%)"]
            draw_donut(ax_d1, [top3_rev, resto_rev], labs_d1, [C_YELLOW, '#383838'], "Concentración Ingresos", center_top="Top 3", center_sub=f"{p_top3:.1f}%")

        # Grafico 2: RRHH - Top Tiendas por Empleados (Ocupa el lugar de Dona 2)
        ax_d2 = fig.add_subplot(gs[1, 1])
        ax_d2.set_facecolor(CHART_BG)
        # Grafico 3: RRHH - Empleados por Región (Ocupa el lugar de Dona 3)
        ax_d3 = fig.add_subplot(gs[1, 2])
        ax_d3.set_facecolor(CHART_BG)

        try:
            import main
            import regiones
            if " al " in periodo:
                d, h = periodo.split(" al ")
            else:
                d, h = periodo, periodo
            df_tiendas, _ = main.obtener_datos_dashboard(d.strip(), h.strip(), self.db_path)
            
            has_data = False
            if df_tiendas is not None and not df_tiendas.empty:
                tiendas_activas = df['CENTRO DE COSTO / TIENDA'].unique()
                df_t_filt = df_tiendas[df_tiendas['Tienda'].isin(tiendas_activas)].copy()
                
                if not df_t_filt.empty:
                    has_data = True
                    # Preparar data ax_d2
                    df_top = df_t_filt.sort_values('Cantidad', ascending=False).head(15)
                    x_pos = np.arange(len(df_top))
                    ax_d2.bar(x_pos, df_top['Cantidad'], color=C_CYAN, width=0.6)
                    short_names = df_top['Tienda'].apply(lambda x: str(x).split('-')[-1].strip() if '-' in str(x) else str(x))
                    ax_d2.set_xticks(x_pos)
                    ax_d2.set_xticklabels(short_names, rotation=35, ha='right', fontsize=6.5, color='#CCCCCC')
                    ax_d2.set_title("Top 15 Tiendas - Empleados", color='white', pad=6, fontweight='bold', fontsize=9.0)
                    ax_d2.tick_params(axis='y', colors='#CCCCCC', labelsize=6.5)
                    ax_d2.spines['top'].set_visible(False)
                    ax_d2.spines['right'].set_visible(False)
                    for i, v in enumerate(df_top['Cantidad']):
                        ax_d2.text(i, v + (df_top['Cantidad'].max() * 0.02), str(v), color='white', ha='center', fontsize=6.5)
                    
                    # Preparar data ax_d3
                    df_t_filt['Region'] = df_t_filt['Tienda'].map(regiones.REGIONES).fillna('OTRO')
                    df_r_filt = df_t_filt.groupby('Region')['Cantidad'].sum().reset_index().rename(columns={'Cantidad':'Empleados'}).sort_values('Empleados', ascending=False)
                    
                    x_pos2 = np.arange(len(df_r_filt))
                    ax_d3.bar(x_pos2, df_r_filt['Empleados'], color=C_MAGENTA, width=0.5)
                    ax_d3.set_xticks(x_pos2)
                    ax_d3.set_xticklabels(df_r_filt['Region'], rotation=25, ha='right', fontsize=6.5, color='#CCCCCC')
                    ax_d3.set_title("Empleados por Región", color='white', pad=6, fontweight='bold', fontsize=9.0)
                    ax_d3.tick_params(axis='y', colors='#CCCCCC', labelsize=6.5)
                    ax_d3.spines['top'].set_visible(False)
                    ax_d3.spines['right'].set_visible(False)
                    for i, v in enumerate(df_r_filt['Empleados']):
                        ax_d3.text(i, v + (df_r_filt['Empleados'].max() * 0.02), str(v), color='white', ha='center', fontsize=6.5)

            if not has_data:
                for ax in [ax_d2, ax_d3]:
                    ax.axis('off')
                    ax.text(0.5, 0.5, "Sin Datos de Empleados", color='#555555', ha='center', va='center', fontsize=12, fontweight='bold')
                    
        except Exception as e:
            self.log(f"[WARN] No se pudo cargar gráficos RRHH: {e}")

        # Dona 4: Margen General
        ax_d4 = fig.add_subplot(gs[1, 3])
        ing_total_m = df_plot['INGRESOS TOTALES (USD)'].sum()
        # Para el costo total m necesitamos recalcular sin la columna region si está
        tot_prorr = df_plot['GASTO APLICADO (PRORRATEO)'].sum()
        tot_dir = df_plot[gastos_cols].sum().sum() if gastos_cols else 0
        costo_total_m = tot_prorr + tot_dir
        rent_total = max(ing_total_m - costo_total_m, 0)
        margen_pct = (rent_total / ing_total_m * 100) if ing_total_m > 0 else 0
        
        if costo_total_m <= 0:
            labs_d4 = [f"Rentabilidad: {fmt_monto(rent_total)} (100.0%)", f"Costo Total: {fmt_monto(0)} (0.0%)"]
            draw_donut(ax_d4, [ing_total_m], labs_d4, [C_CYAN], "Margen General", center_top="Margen", center_sub=f"{margen_pct:.1f}%")
        else:
            p_rent = (rent_total / ing_total_m * 100) if ing_total_m > 0 else 0
            p_cost = (costo_total_m / ing_total_m * 100) if ing_total_m > 0 else 0
            labs_d4 = [f"Rentabilidad: {fmt_monto(rent_total)} ({p_rent:.1f}%)", f"Costo Total: {fmt_monto(costo_total_m)} ({p_cost:.1f}%)"]
            draw_donut(ax_d4, [rent_total, costo_total_m], labs_d4, [C_CYAN, '#383838'], "Margen General", center_top="Margen", center_sub=f"{margen_pct:.1f}%")
            
        return fig

    def _conectar_hover_curva(self, canvas, fig):
        """Conecta interactividad de paso del mouse (hover tooltip) sobre la curva de tendencia de ingresos"""
        if not hasattr(fig, '_hover_data'): return
        data = fig._hover_data
        ax = data['ax_area']
        df_t = data['df_trend']
        x_vals = data['x']
        y_vals = data['y']
        
        # Crear marcador y badge flotante ocultos inicialmente
        hover_dot = ax.scatter([], [], color=C_YELLOW, s=110, edgecolors='#FFFFFF', linewidth=1.5, zorder=8)
        hover_dot.set_visible(False)
        
        hover_annot = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(0, 18),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.45", facecolor="#10131A", edgecolor=C_CYAN, linewidth=1.4, alpha=0.96),
            color="#FFFFFF",
            fontsize=8,
            fontweight="bold",
            ha="center",
            va="bottom",
            arrowprops=dict(arrowstyle="->", color=C_CYAN, lw=1.2),
            zorder=9
        )
        hover_annot.set_visible(False)
        
        def on_motion(event):
            if event.inaxes == ax:
                if event.xdata is not None and event.ydata is not None:
                    idx = int(round(event.xdata))
                    if 0 <= idx < len(df_t):
                        row = df_t.iloc[idx]
                        nom_tienda = row['CENTRO DE COSTO / TIENDA']
                        rev = float(row['INGRESOS TOTALES (USD)'])
                        px = x_vals[idx]
                        py = float(y_vals.iloc[idx])
                        
                        hover_dot.set_offsets([[px, py]])
                        hover_dot.set_visible(True)
                        
                        hover_annot.xy = (px, py)
                        hover_annot.set_text(f"#{idx+1}: {nom_tienda}\nIngresos: ${rev:,.2f}")
                        hover_annot.set_visible(True)
                        canvas.draw_idle()
                        return
            if hover_annot.get_visible():
                hover_annot.set_visible(False)
                hover_dot.set_visible(False)
                canvas.draw_idle()

        canvas.mpl_connect("motion_notify_event", on_motion)

    def _dibujar_dashboards(self, df, periodo, tienda_seleccionada=None):
        for w in self.kpi_container.winfo_children(): w.destroy()
        if self.canvas_dash: self.canvas_dash.get_tk_widget().destroy()

        if df.empty: return

        # 2. Calcular Variables para Tarjetas KPI (Totalmente Dinámicas)
        # Sumar usando 'ingresos' y 'otros_ingresos' desde la matriz
        if 'ingresos' in df.columns and 'otros_ingresos' in df.columns:
            ingresos_totales = df['ingresos'].sum() + df['otros_ingresos'].sum()
        else:
            ingresos_totales = df['INGRESOS TOTALES (USD)'].sum()
            
        # Calcular costo directo y gastos
        costo_directo = df['costo_directo'].sum() if 'costo_directo' in df.columns else 0
        gastos_prorrateo = df['GASTO APLICADO (PRORRATEO)'].sum() if 'GASTO APLICADO (PRORRATEO)' in df.columns else 0
        gastos_directos = df['gastos'].sum() if 'gastos' in df.columns else 0
        
        if tienda_seleccionada and tienda_seleccionada != "Todas las Ciudades":
            gasto_total_real = gastos_directos + gastos_prorrateo
        else:
            gasto_total_real = gastos_directos
        margen = ((ingresos_totales - costo_directo) / ingresos_totales * 100) if ingresos_totales > 0 else 0

        # Dibujar Tarjetas (Sin Decimales)
        self._crear_kpi_card(self.kpi_container, "Ingresos Totales", f"${ingresos_totales:,.0f}", C_CYAN)
        self._crear_kpi_card(self.kpi_container, "COSTO DIRECTO", f"${costo_directo:,.0f}", C_LIME if costo_directo >= 0 else BTN_DANGER)
        self._crear_kpi_card(self.kpi_container, "Gastos Directos", f"${gasto_total_real:,.0f}", C_MAGENTA)
        self._crear_kpi_card(self.kpi_container, "MARGEN BRUTO", f"{margen:.0f}%", C_YELLOW)

        # 3. Dibujar Matplotlib
        fig = self._crear_figura_dashboard(df, periodo, tienda_seleccionada=tienda_seleccionada)
        self.canvas_dash = FigureCanvasTkAgg(fig, master=self.dash_chart_frame)
        self.canvas_dash.draw()
        self.canvas_dash.get_tk_widget().pack(fill="both", expand=True)
        self._conectar_hover_curva(self.canvas_dash, fig)

    def abrir_dashboard_ampliado(self):
        if self.df_actual is None or self.df_actual.empty:
            messagebox.showwarning("Aviso", "No hay datos para mostrar en el Dashboard.")
            return
            
        vent_dash = ctk.CTkToplevel(self)
        vent_dash.title(f"Dashboard BI Corporativo - {self.periodo_actual}")
        vent_dash.geometry("1400x800")
        vent_dash.configure(fg_color=CANGURO_BLACK)
        
        try:
            ruta_ico = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets", "icono.ico")
            if os.path.exists(ruta_ico): vent_dash.after(200, lambda: vent_dash.iconbitmap(ruta_ico))
        except: pass

        # --- AQUI ESTA LA VARIABLE QUE FALTABA (EL CONTENEDOR PRINCIPAL) ---
        dash_filter_frame_amp = ctk.CTkFrame(vent_dash, fg_color="#1A1A1A", corner_radius=8)
        dash_filter_frame_amp.pack(fill="x", padx=10, pady=(10, 5), ipadx=5, ipady=5)
        
        lbl_panel_amp = ctk.CTkLabel(dash_filter_frame_amp, text="📊 Panel Gerencial", font=("Roboto", 14, "bold"), text_color=CANGURO_YELLOW)
        lbl_panel_amp.pack(side="left", padx=10)

        # Reloj ampliado en la barra superior (esquina derecha)
        lbl_reloj_amp = ctk.CTkLabel(dash_filter_frame_amp, text="", font=("Roboto", 14, "bold"), text_color="white")
        lbl_reloj_amp.pack(side="right", padx=10)

        def _actualizar_reloj_amp():
            from datetime import datetime
            try:
                lbl_reloj_amp.configure(text=datetime.now().strftime("%d/%m/%Y %I:%M:%S %p"))
                vent_dash.after(1000, _actualizar_reloj_amp)
            except Exception:
                pass
        _actualizar_reloj_amp()
        
        # --- FUNCIONES DE AUTO-ACTUALIZADO ---
        def _on_periodo_amp_sel(val=None):
            aplicar_filtro_ampliado()

        def _on_ciudad_amp_sel(val=None):
            if val != "Todas las Ciudades":
                combo_region_amp.set("Todas las Regiones")
            aplicar_filtro_ampliado()
            
        def _on_region_amp_sel(val=None):
            if val != "Todas las Regiones":
                combo_ciudad_amp.set("Todas las Ciudades")
            aplicar_filtro_ampliado()

        # --- 1. COMBO PERÍODO CON SCROLL ---
        combo_periodo_amp = ctk.CTkComboBox(dash_filter_frame_amp, values=self.combo_periodo.cget("values"), width=120)
        CTkScrollableDropdown(combo_periodo_amp, values=self.combo_periodo.cget("values"), command=_on_periodo_amp_sel, justify="left", button_color="transparent")
        combo_periodo_amp.set(self.combo_periodo.get())
        combo_periodo_amp.pack(side="left", padx=5)

        # --- 2. COMBO CIUDAD CON SCROLL ---
        combo_ciudad_amp = ctk.CTkComboBox(dash_filter_frame_amp, values=self.combo_ciudad.cget("values"), width=220)
        CTkScrollableDropdown(combo_ciudad_amp, values=self.combo_ciudad.cget("values"), command=_on_ciudad_amp_sel, justify="left", button_color="transparent")
        combo_ciudad_amp.set(self.combo_ciudad.get())
        combo_ciudad_amp.pack(side="left", padx=5)
        
        # --- 3. COMBO REGIÓN CON SCROLL ---
        combo_region_amp = ctk.CTkComboBox(dash_filter_frame_amp, values=self.combo_region.cget("values"), width=180)
        CTkScrollableDropdown(combo_region_amp, values=self.combo_region.cget("values"), command=_on_region_amp_sel, justify="left", button_color="transparent")
        combo_region_amp.set(self.combo_region.get())
        combo_region_amp.pack(side="left", padx=5)

        kpi_container_amp = ctk.CTkFrame(vent_dash, fg_color="transparent", height=60)
        kpi_container_amp.pack(fill="x", padx=10, pady=(0, 5))
        
        chart_frame_amp = ctk.CTkFrame(vent_dash, fg_color="transparent")
        chart_frame_amp.pack(fill="both", expand=True, padx=10, pady=5)

        # Función para aplicar filtros DENTRO de la pantalla completa
        def aplicar_filtro_ampliado():
            per_sel = combo_periodo_amp.get()
            ciu_sel = combo_ciudad_amp.get()
            reg_sel = combo_region_amp.get()

            if per_sel != self.periodo_actual:
                self.combo_periodo.set(per_sel)
                import datetime
                try:
                    if " al " in per_sel:
                        d, h = per_sel.split(" al ")
                    else:
                        d, h = per_sel, per_sel
                    y1, m1 = map(int, d.split('-')[:2])
                    y2, m2 = map(int, h.split('-')[:2])
                    self.periodo_desde.set_date(datetime.date(y1, m1, 1))
                    self.periodo_hasta.set_date(datetime.date(y2, m2, 28))
                except: pass
                self.procesar_mes(recalcular=True)
                vent_dash.destroy()
                self.abrir_dashboard_ampliado() 
                return

            df_filtro = self.df_actual.copy()
            import regiones
            df_filtro['REGION'] = df_filtro['CENTRO DE COSTO / TIENDA'].map(regiones.REGIONES).fillna("OTRO")
            
            tienda_sel = None
            if ciu_sel != "Todas las Ciudades":
                tienda_sel = ciu_sel
                df_filtro = df_filtro[df_filtro['CENTRO DE COSTO / TIENDA'] == ciu_sel]
            elif reg_sel != "Todas las Regiones":
                df_filtro = df_filtro[df_filtro['REGION'] == reg_sel]
                
            for w in kpi_container_amp.winfo_children(): w.destroy()
            for w in chart_frame_amp.winfo_children(): w.destroy()
            
            if 'ingreso' in df_filtro.columns and 'otros_ingresos' in df_filtro.columns:
                ingresos_totales = df_filtro['ingreso'].sum() + df_filtro['otros_ingresos'].sum()
            else:
                ingresos_totales = df_filtro['INGRESOS TOTALES (USD)'].sum()
                
            costo_directo = df_filtro['costo_directo'].sum() if 'costo_directo' in df_filtro.columns else 0
            gastos_prorrateo = df_filtro['GASTO APLICADO (PRORRATEO)'].sum() if 'GASTO APLICADO (PRORRATEO)' in df_filtro.columns else 0
            gastos_directos = df_filtro['gasto'].sum() if 'gasto' in df_filtro.columns else 0
            
            if ciu_sel and ciu_sel != "Todas las Ciudades":
                gasto_total_real = gastos_directos + gastos_prorrateo
            else:
                gasto_total_real = gastos_directos
                
            margen = ((ingresos_totales - costo_directo) / ingresos_totales * 100) if ingresos_totales > 0 else 0

            # Redibujar Tarjetas Ampliadas (Sin Decimales)
            self._crear_kpi_card(kpi_container_amp, "Ingresos Totales", f"${ingresos_totales:,.0f}", C_CYAN)
            self._crear_kpi_card(kpi_container_amp, "COSTO DIRECTO", f"${costo_directo:,.0f}", C_LIME if costo_directo >= 0 else BTN_DANGER)
            self._crear_kpi_card(kpi_container_amp, "Gastos Directos", f"${gasto_total_real:,.0f}", C_MAGENTA)
            self._crear_kpi_card(kpi_container_amp, "MARGEN BRUTO", f"{margen:.0f}%", C_YELLOW)

            fig_nueva = self._crear_figura_dashboard(df_filtro, per_sel, tienda_seleccionada=tienda_sel)
            canvas_nuevo = FigureCanvasTkAgg(fig_nueva, master=chart_frame_amp)
            canvas_nuevo.draw()
            canvas_nuevo.get_tk_widget().pack(fill="both", expand=True)
            self._conectar_hover_curva(canvas_nuevo, fig_nueva)

        # Ejecutar la primera vez para llenar la pantalla
        aplicar_filtro_ampliado()

    # ==========================================
    # EXPORTACIÓN
    # ==========================================
    def exportar_excel(self):
        if self.df_actual is None or self.df_actual.empty: return
        ruta = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile=f"Reporte_Rentabilidad_{self.periodo_actual}.xlsx", filetypes=[("Archivos de Excel", "*.xlsx")])
        if ruta: 
            self.df_actual.to_excel(ruta, index=False)
            messagebox.showinfo("Éxito", "Reporte Excel exportado correctamente.")

    def exportar_csv_bi(self):
        if self.df_actual is None or self.df_actual.empty: return
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=f"Dataset_PowerBI_{self.periodo_actual}.csv", filetypes=[("Archivo CSV", "*.csv")])
        if ruta: 
            self.df_actual.to_csv(ruta, index=False, sep=';', decimal=',', encoding='utf-8-sig')
            messagebox.showinfo("Éxito", "CSV exportado correctamente.")

    def cerrar_app(self):
        try: plt.close('all')
        except: pass
        self.quit()
        self.destroy()

if __name__ == "__main__":
    app = CierreContableApp()
    app.mainloop()