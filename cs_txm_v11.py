"""
Sistema de Control de Tarifas para Transporte (Taxímetro F5 V.11)
Aplicación desarrollada en Python para la gestión de turnos, carreras,
tiempos y recaudación en tiempo real. Construida con Tkinter y TinyDB.
Cesar Sandoval
"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import datetime, csv, json, os
from tinydb import TinyDB, Query
from collections import defaultdict

# --- CONSTANTES DE CONFIGURACIÓN ---
# Tarifas por segundo en soles (S/)
TARIFA_MOVIMIENTO = 0.25
TARIFA_DETENIDO   = 0.15
# Ruta de la base de datos local (TinyDB)
DB_PATH = os.path.join(os.path.expanduser("~"), "taximetro_db.json")

# --- FUNCIONES AUXILIARES ---
# Retorna la hora actual en formato HH:MM:SS
def ahora_str(): return datetime.datetime.now().strftime("%H:%M:%S")
# Retorna la fecha actual en formato DD/MM/YYYY
def fecha_str(): return datetime.datetime.now().strftime("%d/%m/%Y")


# --- CLASE PRINCIPAL ---
# Gestiona la interfaz gráfica, la lógica del taxímetro y la persistencia de datos
class Taximetro:
    # Inicializa la aplicación, configura la ventana principal y las variables de estado
    def __init__(self, root):
        self.root = root
        self.root.title("Taximetro F5 V.11")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(True, True)
        self.root.geometry("1280x768")

        self.db = TinyDB(DB_PATH)

        self.conductor = self._pedir_conductor()
        self.fecha     = fecha_str()

        # Estado carrera
        self.tiempo_total      = 0
        self.tiempo_movimiento = 0
        self.tiempo_detenido   = 0
        self.estado            = "detenido"
        self.iniciado          = False
        self.intervalo         = None
        self.tramo_actual      = 0
        self.tramo_inicio_mov  = 0
        self.tramo_inicio_det  = 0
        self.hora_inicio_tramo = ""
        self.carrera_actual    = 0
        self.turno_iniciado    = False
        self.turno_cerrado     = False
        self.hora_inicio_turno = ""
        self.hora_cierre_turno = ""

        # Acumulados día
        self.dia_movimiento  = 0
        self.dia_detenido    = 0
        self.dia_carreras    = 0
        self.dia_total_costo = 0.0
        self.historial_export = []

        self._build_ui()

    # Muestra un cuadro de diálogo para ingresar el nombre del conductor al iniciar
    def _pedir_conductor(self):
        conductores = list({t["conductor"] for t in self.db.table("turnos").all()})
        hint = "  (conocidos: " + ", ".join(conductores[:4]) + ")" if conductores else ""
        n = simpledialog.askstring("Bienvenido",
            f"Ingresa el nombre del conductor:{hint}", parent=self.root)
        return n.strip() if n and n.strip() else "Sin nombre"

    # ══════════════════════════════════════════════════════════════════
    # BUILD UI
    # ══════════════════════════════════════════════════════════════════
    # Construye la interfaz gráfica principal (paneles izquierdo y derecho)
    def _build_ui(self):
        main = tk.Frame(self.root, bg="#1a1a2e")
        main.pack(fill="both", expand=True, padx=14, pady=14)

        # ── COLUMNA IZQUIERDA ─────────────────────────────────────────
        left = tk.Frame(main, bg="#1a1a2e", width=290)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        tk.Label(left, text="🚕  TAXIMETRO F5 V.11",
                 bg="#1a1a2e", fg="#f5c518",
                 font=("Arial", 16, "bold")).pack(pady=(0, 6))

        # Contador
        card = tk.Frame(left, bg="#16213e")
        card.pack(fill="x")
        tk.Label(card, text="Tiempo transcurrido",
                 bg="#16213e", fg="#8892b0", font=("Arial", 10)).pack(pady=(5, 0))
        self.lbl_contador = tk.Label(card, text="0 s",
                                     bg="#16213e", fg="#ffffff",
                                     font=("Arial", 28, "bold"))
        self.lbl_contador.pack()
        self.lbl_estado = tk.Label(card, text="⏸  Turno no iniciado",
                                   bg="#16213e", fg="#8892b0", font=("Arial", 10))
        self.lbl_estado.pack(pady=(2, 8))

        # Botones de control
        bf = tk.Frame(left, bg="#1a1a2e")
        bf.pack(fill="x", pady=(6, 0))

        self.btn_iniciar_turno = self._btn(
            bf, "🚦  Iniciar turno", "#f5c518", self.iniciar_turno, fg_color="#1a1a2e")
        self.btn_iniciar_turno.pack(fill="x", pady=(0, 4))

        tk.Frame(bf, bg="#2a2a4a", height=1).pack(fill="x", pady=(0, 4))

        row_pp = tk.Frame(bf, bg="#1a1a2e")
        row_pp.pack(fill="x")
        self.btn_parar     = self._btn(row_pp, "⏸ Parar",     "#e67e22", self.parar,    "disabled")
        self.btn_continuar = self._btn(row_pp, "▶ Continuar", "#2980b9", self.continuar,"disabled")
        self.btn_terminar  = self._btn(row_pp, "■ Fin viaje", "#c0392b", self.terminar, "disabled")
        self.btn_parar.pack(side="left", expand=True, fill="x", padx=(0, 2), pady=2)
        self.btn_continuar.pack(side="left", expand=True, fill="x", padx=2, pady=2)
        self.btn_terminar.pack(side="left", expand=True, fill="x", padx=(2, 0), pady=2)

        row_nc = tk.Frame(bf, bg="#1a1a2e")
        row_nc.pack(fill="x", pady=2)
        self.btn_nueva        = self._btn(row_nc, "🔄 Nueva carrera", "#6c3483", self.nueva_carrera,  "disabled")
        self.btn_cerrar_turno = self._btn(row_nc, "🔒 Cerrar turno",  "#7f3f00", self.cerrar_turno,   "disabled")
        self.btn_nueva.pack(side="left", expand=True, fill="x", padx=(0, 2))
        self.btn_cerrar_turno.pack(side="left", expand=True, fill="x", padx=(2, 0))

        tk.Frame(left, bg="#2a2a4a", height=1).pack(fill="x", pady=(8, 4))

        # Resúmenes
        self._build_resumen_panel(left, "Carrera actual", "#8892b0",
            ("lbl_r_carr","lbl_r_mov","lbl_r_det","lbl_r_total"), "#ffffff")
        tk.Frame(left, bg="#2a2a4a", height=1).pack(fill="x", pady=(4, 4))
        self._build_resumen_panel(left, "Total del día", "#f5c518",
            ("lbl_d_carr","lbl_d_mov","lbl_d_det","lbl_d_total"), "#f5c518")

        tk.Frame(left, bg="#2a2a4a", height=1).pack(fill="x", pady=(6, 4))

        # Descargar
        tk.Label(left, text="💾  Descargar resúmenes",
                 bg="#1a1a2e", fg="#cdd6f4",
                 font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 4))
        row_dl = tk.Frame(left, bg="#1a1a2e")
        row_dl.pack(fill="x")
        for label, color, cmd in [
            ("CSV",  "#1a6b5a", self.descargar_csv),
            ("JSON", "#1a4a6b", self.descargar_json),
            ("MD",   "#3b1a6b", self.descargar_md),
        ]:
            tk.Button(row_dl, text=label, bg=color, fg="white",
                      font=("Arial", 10, "bold"), relief="flat", cursor="hand2",
                      activebackground=color, activeforeground="white",
                      padx=4, pady=6, command=cmd
                      ).pack(side="left", expand=True, fill="x", padx=2)

        # ── COLUMNA DERECHA: contenedor de vistas ─────────────────────
        self.right = tk.Frame(main, bg="#1a1a2e")
        self.right.pack(side="left", fill="both", expand=True)

        # Barra de navegación de vistas
        nav = tk.Frame(self.right, bg="#0f3460")
        nav.pack(fill="x", pady=(0, 0))

        tk.Label(nav, text=f"👤 {self.conductor}",
                 bg="#0f3460", fg="#cdd6f4",
                 font=("Arial", 11, "bold")).pack(side="left", padx=14, pady=8)
        tk.Label(nav, text=f"📅 {self.fecha}",
                 bg="#0f3460", fg="#cdd6f4",
                 font=("Arial", 11)).pack(side="left", pady=8)

        # Botones de vista (derecha del nav)
        self.btn_vista_viajes = tk.Button(nav, text="📋 Historial de viajes",
            bg="#1a5276", fg="#f5c518",
            font=("Arial", 10, "bold"), relief="flat", cursor="hand2",
            activebackground="#1a5276", activeforeground="#f5c518",
            padx=12, pady=8, command=self.mostrar_vista_viajes)
        self.btn_vista_viajes.pack(side="right", padx=(4, 14))

        self.btn_vista_stats = tk.Button(nav, text="📊 Estadísticas",
            bg="#0f3460", fg="#8892b0",
            font=("Arial", 10, "bold"), relief="flat", cursor="hand2",
            activebackground="#1a3a5a", activeforeground="#cdd6f4",
            padx=12, pady=8, command=self.mostrar_vista_stats)
        self.btn_vista_stats.pack(side="right", padx=2)

        # Contenedor que cambia de vista
        self.view_container = tk.Frame(self.right, bg="#1a1a2e")
        self.view_container.pack(fill="both", expand=True)

        self._build_vista_viajes()
        self._build_vista_stats()

        # Mostrar vista de viajes por defecto
        self.mostrar_vista_viajes()

    # ══════════════════════════════════════════════════════════════════
    # VISTA 1: HISTORIAL DE VIAJES (sesión actual)
    # ══════════════════════════════════════════════════════════════════
    # Construye la vista de historial de viajes (tabla principal de la sesión actual)
    def _build_vista_viajes(self):
        self.frame_viajes = tk.Frame(self.view_container, bg="#1a1a2e")

        self._apply_treeview_style()
        cols = ("tramo","inicio","fin","detenido","movimiento","total","costo")
        self.tabla = ttk.Treeview(self.frame_viajes, columns=cols,
                                  show="headings", style="Dark.Treeview", height=22)
        for col, text, w in [
            ("tramo","TRAMO",110), ("inicio","INICIO",75), ("fin","FIN",75),
            ("detenido","DETENIDO",80), ("movimiento","MOVIMIENTO",95),
            ("total","TOTAL",70), ("costo","COSTO",80),
        ]:
            self.tabla.heading(col, text=text)
            self.tabla.column(col, width=w, anchor="center", minwidth=w)

        self.tabla.tag_configure("header_turno",   background="#1a4000", foreground="#7fff00", font=("Arial",10,"bold"))
        self.tabla.tag_configure("header_carrera",  background="#0f3460", foreground="#f5c518", font=("Arial",10,"bold"))
        self.tabla.tag_configure("subtotal",        background="#1a1a40", foreground="#a0c4ff", font=("Arial",9,"italic"))
        self.tabla.tag_configure("resumen_header",  background="#2d2000", foreground="#f5c518", font=("Arial",10,"bold"))
        self.tabla.tag_configure("resumen_total",   background="#1a2e00", foreground="#7fff00", font=("Arial",10,"bold"))
        self.tabla.tag_configure("turno_cerrado",   background="#3d0000", foreground="#ff6b6b", font=("Arial",10,"bold"))

        sb = ttk.Scrollbar(self.frame_viajes, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=sb.set)
        self.tabla.pack(side="left", fill="both", expand=True, pady=(8,0))
        sb.pack(side="left", fill="y", pady=(8,0))

    # ══════════════════════════════════════════════════════════════════
    # VISTA 2: ESTADÍSTICAS (desde BD)
    # ══════════════════════════════════════════════════════════════════
    # Construye la vista de estadísticas (filtros, KPIs, tablas de BD y gráficos)
    def _build_vista_stats(self):
        self.frame_stats = tk.Frame(self.view_container, bg="#1a1a2e")

        # Filtros
        filtros = tk.Frame(self.frame_stats, bg="#16213e")
        filtros.pack(fill="x", pady=(8, 6), padx=4)

        tk.Label(filtros, text="Conductor:", bg="#16213e", fg="#cdd6f4",
                 font=("Arial", 10)).pack(side="left", padx=(12, 4), pady=8)
        self.filtro_conductor = tk.Entry(filtros, width=16, font=("Arial", 10),
                                          bg="#1a1a2e", fg="white",
                                          insertbackground="white", relief="flat")
        self.filtro_conductor.pack(side="left", pady=8)

        tk.Label(filtros, text="Fecha (dd/mm/aaaa):", bg="#16213e", fg="#cdd6f4",
                 font=("Arial", 10)).pack(side="left", padx=(14, 4))
        self.filtro_fecha = tk.Entry(filtros, width=12, font=("Arial", 10),
                                      bg="#1a1a2e", fg="white",
                                      insertbackground="white", relief="flat")
        self.filtro_fecha.pack(side="left", pady=8)

        tk.Button(filtros, text="🔍 Filtrar", bg="#2980b9", fg="white",
                  font=("Arial", 10, "bold"), relief="flat", cursor="hand2",
                  padx=10, pady=4,
                  command=self._cargar_stats).pack(side="left", padx=10)
        tk.Button(filtros, text="✖ Limpiar", bg="#555", fg="white",
                  font=("Arial", 10, "bold"), relief="flat", cursor="hand2",
                  padx=10, pady=4,
                  command=self._limpiar_filtros).pack(side="left")

        # Body: KPIs izq + tabs der
        body = tk.Frame(self.frame_stats, bg="#1a1a2e")
        body.pack(fill="both", expand=True, padx=4, pady=0)

        # KPI cards — más angosto
        kpi_col = tk.Frame(body, bg="#1a1a2e", width=155)
        kpi_col.pack(side="left", fill="y", padx=(0, 8))
        kpi_col.pack_propagate(False)

        tk.Label(kpi_col, text="Resumen",
                 bg="#1a1a2e", fg="#8892b0",
                 font=("Arial", 8, "bold")).pack(anchor="w", pady=(4, 4))

        self.kpis = {}
        for key, label, fg in [
            ("turnos",    "🗂 Turnos",        "#cdd6f4"),
            ("carreras",  "🚖 Carreras",       "#cdd6f4"),
            ("mov_s",     "🟢 Movimiento",     "#0f9b58"),
            ("det_s",     "🔴 Detenido",       "#e74c3c"),
            ("total_s",   "💰 Recaudado",      "#f5c518"),
            ("prom_carr", "📈 Prom/carrera",   "#a0c4ff"),
            ("prom_turno","📅 Prom/turno",     "#a0c4ff"),
            ("top_cond",  "🏆 Top conductor",  "#f5c518"),
        ]:
            card = tk.Frame(kpi_col, bg="#16213e")
            card.pack(fill="x", pady=1)
            tk.Label(card, text=label, bg="#16213e", fg="#8892b0",
                     font=("Arial", 7)).pack(anchor="w", padx=6, pady=(3, 0))
            lbl = tk.Label(card, text="—", bg="#16213e", fg=fg,
                           font=("Arial", 11, "bold"))
            lbl.pack(anchor="w", padx=6, pady=(0, 3))
            self.kpis[key] = lbl

        # Notebook de tablas
        nb_frame = tk.Frame(body, bg="#1a1a2e")
        nb_frame.pack(side="left", fill="both", expand=True)

        nb_style = ttk.Style()
        nb_style.configure("Dark.TNotebook",        background="#1a1a2e", borderwidth=0)
        nb_style.configure("Dark.TNotebook.Tab",    background="#16213e", foreground="#8892b0",
                           font=("Arial", 10, "bold"), padding=[12, 6])
        nb_style.map("Dark.TNotebook.Tab",
            background=[("selected", "#0f3460")],
            foreground=[("selected", "#f5c518")])

        self.nb = ttk.Notebook(nb_frame, style="Dark.TNotebook")
        self.nb.pack(fill="both", expand=True)

        tab_turnos        = tk.Frame(self.nb, bg="#1a1a2e")
        tab_carreras      = tk.Frame(self.nb, bg="#1a1a2e")
        tab_ranking       = tk.Frame(self.nb, bg="#1a1a2e")
        self.tab_graficos = tk.Frame(self.nb, bg="#1a1a2e")
        self.nb.add(tab_turnos,        text="  Turnos  ")
        self.nb.add(tab_carreras,      text="  Carreras  ")
        self.nb.add(tab_ranking,       text="  Ranking  ")
        self.nb.add(self.tab_graficos, text="  Gráficos 📊  ")
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

        self.tree_turnos   = self._make_tree(tab_turnos, [
            ("fecha","FECHA",90), ("conductor","CONDUCTOR",120),
            ("inicio","INICIO",70), ("cierre","CIERRE",70),
            ("carreras","CARRERAS",70), ("mov_s","MOV(s)",70),
            ("det_s","DET(s)",70), ("total","TOTAL S/",85),
        ])
        self.tree_carreras = self._make_tree(tab_carreras, [
            ("fecha","FECHA",85), ("conductor","CONDUCTOR",100),
            ("carrera","CAR.",55), ("tramo","TRAMO",55),
            ("tipo","TIPO",90), ("inicio","INICIO",68), ("fin","FIN",68),
            ("mov_s","MOV(s)",60), ("det_s","DET(s)",60),
            ("total_s","TOT(s)",60), ("costo","COSTO S/",80),
        ])
        self.tree_ranking  = self._make_tree(tab_ranking, [
            ("pos","#",35), ("conductor","CONDUCTOR",130),
            ("turnos","TURNOS",65), ("carreras","CARRERAS",75),
            ("total_s","TOTAL S/",95), ("prom","PROM/CARR S/",110),
            ("mov_s","MOV(s)",75), ("det_s","DET(s)",75),
        ])

        # Canvas para gráficos
        self.canvas_graficos = tk.Canvas(
            self.tab_graficos, bg="#16213e", highlightthickness=0)
        self.canvas_graficos.pack(fill="both", expand=True, padx=8, pady=8)

    # Función auxiliar para crear tablas (Treeview) con columnas específicas
    def _make_tree(self, parent, cols):
        frame = tk.Frame(parent, bg="#1a1a2e")
        frame.pack(fill="both", expand=True, padx=2, pady=4)
        col_ids = [c[0] for c in cols]
        tree = ttk.Treeview(frame, columns=col_ids, show="headings",
                            style="Dark.Treeview")
        for cid, text, w in cols:
            tree.heading(cid, text=text,
                         command=lambda c=cid, t=tree: self._sort(t, c, False))
            tree.column(cid, width=w, anchor="center", minwidth=w)
        tree.tag_configure("alt", background="#1c2a3a")
        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        return tree

    # Aplica el estilo visual oscuro a las tablas (Treeview)
    def _apply_treeview_style(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.Treeview",
            background="#16213e", foreground="#cdd6f4",
            fieldbackground="#16213e", rowheight=25, font=("Arial", 9))
        style.configure("Dark.Treeview.Heading",
            background="#0f3460", foreground="#f5c518",
            font=("Arial", 9, "bold"), relief="flat")
        style.map("Dark.Treeview",
            background=[("selected", "#0f3460")],
            foreground=[("selected", "#f5c518")])

    # Ordena los datos de una tabla al hacer clic en el encabezado de una columna
    def _sort(self, tree, col, reverse):
        data = [(tree.set(k, col), k) for k in tree.get_children("")]
        try:    data.sort(key=lambda x: float(x[0].replace("S/","").strip()), reverse=reverse)
        except: data.sort(reverse=reverse)
        for i, (_, k) in enumerate(data):
            tree.move(k, "", i)
        tree.heading(col, command=lambda: self._sort(tree, col, not reverse))

    # ── Alternar vistas ───────────────────────────────────────────────
    # Cambia la vista activa al historial de viajes de la sesión actual
    def mostrar_vista_viajes(self):
        self.frame_stats.pack_forget()
        self.frame_viajes.pack(fill="both", expand=True)
        self.btn_vista_viajes.config(bg="#1a5276", fg="#f5c518")
        self.btn_vista_stats.config(bg="#0f3460", fg="#8892b0")

    # Cambia la vista activa a las estadísticas y carga los datos desde la BD
    def mostrar_vista_stats(self):
        self.frame_viajes.pack_forget()
        self.frame_stats.pack(fill="both", expand=True)
        self.btn_vista_stats.config(bg="#1a5276", fg="#f5c518")
        self.btn_vista_viajes.config(bg="#0f3460", fg="#8892b0")
        self._cargar_stats()

    # ── Cargar estadísticas desde BD ─────────────────────────────────
    # Carga y filtra los datos de turnos y carreras desde la BD para mostrar en estadísticas
    def _cargar_stats(self):
        turnos_raw   = self.db.table("turnos").all()
        carreras_raw = self.db.table("carreras").all()

        fc = self.filtro_conductor.get().strip().lower()
        ff = self.filtro_fecha.get().strip()
        if fc:
            turnos_raw   = [t for t in turnos_raw   if fc in t.get("conductor","").lower()]
            carreras_raw = [c for c in carreras_raw if fc in c.get("conductor","").lower()]
        if ff:
            turnos_raw   = [t for t in turnos_raw   if t.get("fecha","") == ff]
            carreras_raw = [c for c in carreras_raw if c.get("fecha","") == ff]

        # Tabla turnos
        for r in self.tree_turnos.get_children(): self.tree_turnos.delete(r)
        for i, t in enumerate(sorted(turnos_raw,
                key=lambda x: (x["fecha"], x["inicio_turno"]), reverse=True)):
            tag = "alt" if i % 2 else ""
            self.tree_turnos.insert("", "end", tags=(tag,), values=(
                t["fecha"], t["conductor"], t["inicio_turno"],
                t.get("cierre_turno","—"), t["total_carreras"],
                t["tiempo_movimiento_s"], t["tiempo_detenido_s"],
                f"{t['total_s']:.2f}",
            ))

        # Tabla carreras
        for r in self.tree_carreras.get_children(): self.tree_carreras.delete(r)
        for i, c in enumerate(carreras_raw):
            tag = "alt" if i % 2 else ""
            self.tree_carreras.insert("", "end", tags=(tag,), values=(
                c["fecha"], c["conductor"], c["carrera"], c["tramo"],
                c["tipo"], c["inicio"], c["fin"],
                c["movimiento"], c["detenido"], c["total"],
                f"{c['costo']:.2f}",
            ))

        # Ranking
        agg = defaultdict(lambda: {"turnos":0,"carreras":0,"total_s":0.0,"mov_s":0,"det_s":0})
        for t in turnos_raw:
            a = agg[t["conductor"]]
            a["turnos"]   += 1
            a["carreras"] += t["total_carreras"]
            a["total_s"]  += t["total_s"]
            a["mov_s"]    += t["tiempo_movimiento_s"]
            a["det_s"]    += t["tiempo_detenido_s"]

        for r in self.tree_ranking.get_children(): self.tree_ranking.delete(r)
        ranking = sorted(agg.items(), key=lambda x: x[1]["total_s"], reverse=True)
        for pos, (cond, v) in enumerate(ranking, 1):
            prom = v["total_s"] / v["carreras"] if v["carreras"] else 0
            tag = "alt" if pos % 2 else ""
            self.tree_ranking.insert("", "end", tags=(tag,), values=(
                pos, cond, v["turnos"], v["carreras"],
                f"{v['total_s']:.2f}", f"{prom:.2f}",
                v["mov_s"], v["det_s"],
            ))

        # KPIs
        tot_t   = len(turnos_raw)
        tot_c   = sum(t["total_carreras"] for t in turnos_raw)
        tot_mov = sum(t["tiempo_movimiento_s"] for t in turnos_raw)
        tot_det = sum(t["tiempo_detenido_s"]   for t in turnos_raw)
        tot_s   = sum(t["total_s"] for t in turnos_raw)
        def fmt(s):
            h, r = divmod(s, 3600); m, s2 = divmod(r, 60)
            return f"{h}h {m}m {s2}s" if h else f"{m}m {s2}s"
        self.kpis["turnos"].config(text=str(tot_t))
        self.kpis["carreras"].config(text=str(tot_c))
        self.kpis["mov_s"].config(text=fmt(tot_mov))
        self.kpis["det_s"].config(text=fmt(tot_det))
        self.kpis["total_s"].config(text=f"S/ {tot_s:.2f}")
        self.kpis["prom_carr"].config(text=f"S/ {tot_s/tot_c:.2f}" if tot_c else "—")
        self.kpis["prom_turno"].config(text=f"S/ {tot_s/tot_t:.2f}" if tot_t else "—")
        self.kpis["top_cond"].config(text=ranking[0][0] if ranking else "—")

    # Limpia los campos de filtro en la vista de estadísticas y recarga los datos
    def _limpiar_filtros(self):
        self.filtro_conductor.delete(0, tk.END)
        self.filtro_fecha.delete(0, tk.END)
        self._cargar_stats()

    # Evento que se dispara al cambiar de pestaña en estadísticas (dibuja gráficos si es necesario)
    def _on_tab_change(self, event):
        idx = self.nb.index(self.nb.select())
        if idx == 3:
            self.root.after(50, self._dibujar_graficos)

    # Dibuja los gráficos de barras (recaudación y tiempos) en el canvas de estadísticas
    def _dibujar_graficos(self):
        c = self.canvas_graficos
        c.delete("all")
        c.update_idletasks()
        W = c.winfo_width()
        H = c.winfo_height()
        if W < 50 or H < 50:
            return

        # Datos desde BD con filtros activos
        turnos_raw = self.db.table("turnos").all()
        fc = self.filtro_conductor.get().strip().lower()
        ff = self.filtro_fecha.get().strip()
        if fc: turnos_raw = [t for t in turnos_raw if fc in t.get("conductor","").lower()]
        if ff: turnos_raw = [t for t in turnos_raw if t.get("fecha","") == ff]

        if not turnos_raw:
            c.create_text(W//2, H//2, text="Sin datos para graficar\nCierra un turno primero",
                          fill="#8892b0", font=("Arial",14), justify="center")
            return

        PAD_L, PAD_R, PAD_T, PAD_B = 60, 20, 40, 60
        MID_X = W // 2

        # ── GRÁFICO 1: Barras recaudado por fecha (mitad izquierda) ──
        self._titulo(c, "Recaudado por fecha (S/)", PAD_L, PAD_T - 24, MID_X - PAD_R)

        por_fecha = defaultdict(float)
        for t in turnos_raw:
            por_fecha[t["fecha"]] += t["total_s"]
        fechas  = sorted(por_fecha.keys())
        valores = [por_fecha[f] for f in fechas]
        self._barras(c, fechas, valores, "#f5c518",
                     PAD_L, PAD_T, MID_X - PAD_R, H - PAD_B, "S/")

        # ── GRÁFICO 2: Barras apiladas mov vs det por conductor (mitad derecha) ──
        self._titulo(c, "Tiempo por conductor (s)", MID_X + PAD_L, PAD_T - 24, W - PAD_R)

        agg = defaultdict(lambda: {"mov":0,"det":0})
        for t in turnos_raw:
            agg[t["conductor"]]["mov"] += t["tiempo_movimiento_s"]
            agg[t["conductor"]]["det"] += t["tiempo_detenido_s"]
        conductores = list(agg.keys())
        vals_mov = [agg[k]["mov"] for k in conductores]
        vals_det = [agg[k]["det"] for k in conductores]
        self._barras_apiladas(c, conductores, vals_mov, vals_det,
                              MID_X + PAD_L, PAD_T, W - PAD_R, H - PAD_B)

        # ── Separador central ──
        c.create_line(MID_X, PAD_T - 30, MID_X, H - PAD_B + 10,
                      fill="#2a2a4a", width=1, dash=(4,4))

    # ── helpers de dibujo ──────────────────────────────────────────────

    # Dibuja un título centrado en el canvas
    def _titulo(self, c, texto, x1, y, x2):
        c.create_text((x1+x2)//2, y, text=texto,
                      fill="#f5c518", font=("Arial", 9, "bold"), anchor="s")

    # Dibuja un gráfico de barras simples en el canvas
    def _barras(self, c, labels, valores, color, x1, y1, x2, y2, prefijo=""):
        if not valores or max(valores) == 0: return
        n      = len(labels)
        ancho  = (x2 - x1)
        gap    = max(4, ancho // (n * 6))
        bw     = (ancho - gap * (n + 1)) // n
        maxv   = max(valores)
        altura = y2 - y1

        # Eje Y
        for i in range(5):
            yy  = y1 + int(altura * i / 4)
            val = maxv * (1 - i/4)
            c.create_line(x1, yy, x2, yy, fill="#2a2a4a", width=1)
            c.create_text(x1 - 4, yy, text=f"{val:.0f}",
                          fill="#8892b0", font=("Arial", 7), anchor="e")

        for i, (lbl, val) in enumerate(zip(labels, valores)):
            bx1 = x1 + gap + i * (bw + gap)
            bx2 = bx1 + bw
            bh  = int(altura * val / maxv)
            by1 = y2 - bh
            # Sombra
            c.create_rectangle(bx1+2, by1+2, bx2+2, y2+2,
                                fill="#0a0a1a", outline="")
            # Barra
            c.create_rectangle(bx1, by1, bx2, y2,
                                fill=color, outline="#1a1a2e", width=1)
            # Valor encima
            c.create_text((bx1+bx2)//2, by1 - 4,
                          text=f"{prefijo}{val:.1f}",
                          fill="#ffffff", font=("Arial", 7), anchor="s")
            # Label abajo (rotado simulado con recorte)
            texto = lbl if len(lbl) <= 8 else lbl[:7] + "…"
            c.create_text((bx1+bx2)//2, y2 + 10,
                          text=texto, fill="#cdd6f4",
                          font=("Arial", 7), anchor="n")

    # Dibuja un gráfico de barras apiladas (movimiento vs detenido) en el canvas
    def _barras_apiladas(self, c, labels, vals_mov, vals_det, x1, y1, x2, y2):
        if not labels: return
        n      = len(labels)
        ancho  = x2 - x1
        gap    = max(4, ancho // (n * 6))
        bw     = (ancho - gap * (n + 1)) // n
        maxv   = max(m + d for m, d in zip(vals_mov, vals_det)) or 1
        altura = y2 - y1

        for i in range(5):
            yy  = y1 + int(altura * i / 4)
            val = maxv * (1 - i/4)
            c.create_line(x1, yy, x2, yy, fill="#2a2a4a", width=1)
            c.create_text(x1 - 4, yy, text=f"{val:.0f}",
                          fill="#8892b0", font=("Arial", 7), anchor="e")

        for i, (lbl, mov, det) in enumerate(zip(labels, vals_mov, vals_det)):
            bx1  = x1 + gap + i * (bw + gap)
            bx2  = bx1 + bw
            total = mov + det
            h_mov = int(altura * mov / maxv)
            h_det = int(altura * det / maxv)
            # Segmento detenido (rojo, abajo)
            c.create_rectangle(bx1, y2 - h_det, bx2, y2,
                                fill="#c0392b", outline="#1a1a2e", width=1)
            # Segmento movimiento (verde, arriba)
            c.create_rectangle(bx1, y2 - h_mov - h_det, bx2, y2 - h_det,
                                fill="#0f9b58", outline="#1a1a2e", width=1)
            # Total encima
            c.create_text((bx1+bx2)//2, y2 - h_mov - h_det - 4,
                          text=str(total),
                          fill="#ffffff", font=("Arial", 7), anchor="s")
            texto = lbl if len(lbl) <= 8 else lbl[:7] + "…"
            c.create_text((bx1+bx2)//2, y2 + 10,
                          text=texto, fill="#cdd6f4",
                          font=("Arial", 7), anchor="n")

        # Leyenda
        lx = x1 + 4
        ly = y1 + 2
        c.create_rectangle(lx, ly, lx+10, ly+8,    fill="#0f9b58", outline="")
        c.create_text(lx+13, ly+4, text="Movimiento", fill="#cdd6f4",
                      font=("Arial", 7), anchor="w")
        c.create_rectangle(lx+80, ly, lx+90, ly+8,  fill="#c0392b", outline="")
        c.create_text(lx+93, ly+4, text="Detenido",   fill="#cdd6f4",
                      font=("Arial", 7), anchor="w")

    # ══════════════════════════════════════════════════════════════════
    # LÓGICA TAXÍMETRO
    # ══════════════════════════════════════════════════════════════════
    # Registra la hora de inicio del turno y activa la primera carrera
    def iniciar_turno(self):
        if self.turno_iniciado or self.turno_cerrado: return
        self.turno_iniciado    = True
        self.hora_inicio_turno = ahora_str()
        self.tabla.insert("", "end",
            values=(f"🚦 TURNO INICIADO — {self.hora_inicio_turno}", "", "", "", "", "", ""),
            tags=("header_turno",))
        self._scroll_tabla()
        self.btn_iniciar_turno.config(state="disabled")
        self.lbl_estado.config(text="⏸  Turno activo", fg="#7fff00")
        self._arrancar_carrera()

    # Configura el estado inicial de una carrera y arranca el contador
    def _arrancar_carrera(self):
        self.carrera_actual   += 1
        self.dia_carreras     += 1
        self.iniciado          = True
        self.estado            = "movimiento"
        self.tramo_actual      = 1
        self.tramo_inicio_mov  = 0
        self.tramo_inicio_det  = 0
        self.hora_inicio_tramo = ahora_str()
        self.tabla.insert("", "end",
            values=(f"🚖 CARRERA {self.carrera_actual}", "", "", "", "", "", ""),
            tags=("header_carrera",))
        self._scroll_tabla()
        self._actualizar_estado_label()
        self.btn_parar.config(state="normal")
        self.btn_continuar.config(state="disabled")
        self.btn_terminar.config(state="normal")
        self.btn_nueva.config(state="disabled")
        self.btn_cerrar_turno.config(state="disabled")
        self._tick()

    # Cambia el estado del taxímetro a "detenido" (aplica tarifa de detenido)
    def parar(self):
        if not self.iniciado or self.estado == "detenido": return
        self._cerrar_tramo()
        self.estado = "detenido"
        self.tramo_actual += 1
        self.tramo_inicio_mov = 0; self.tramo_inicio_det = 0
        self.hora_inicio_tramo = ahora_str()
        self._actualizar_estado_label()
        self.btn_parar.config(state="disabled")
        self.btn_continuar.config(state="normal")

    # Cambia el estado del taxímetro a "movimiento" (aplica tarifa de movimiento)
    def continuar(self):
        if not self.iniciado or self.estado == "movimiento": return
        self._cerrar_tramo()
        self.estado = "movimiento"
        self.tramo_actual += 1
        self.tramo_inicio_mov = 0; self.tramo_inicio_det = 0
        self.hora_inicio_tramo = ahora_str()
        self._actualizar_estado_label()
        self.btn_continuar.config(state="disabled")
        self.btn_parar.config(state="normal")

    # Finaliza la carrera actual, calcula los costos totales y habilita el cierre o nueva carrera
    def terminar(self):
        if self.intervalo:
            self.root.after_cancel(self.intervalo)
            self.intervalo = None
        self._cerrar_tramo()
        cm = self.tiempo_movimiento * TARIFA_MOVIMIENTO
        cd = self.tiempo_detenido   * TARIFA_DETENIDO
        total = cm + cd
        self.tabla.insert("", "end",
            values=("💰 SUBTOTAL", "", "",
                    f"{self.tiempo_detenido} s", f"{self.tiempo_movimiento} s",
                    f"{self.tiempo_total} s",    f"S/ {total:.2f}"),
            tags=("subtotal",))
        self._scroll_tabla()
        self.dia_movimiento  += self.tiempo_movimiento
        self.dia_detenido    += self.tiempo_detenido
        self.dia_total_costo += total
        self._actualizar_resumen_carrera()
        self._actualizar_resumen_dia()
        for b in (self.btn_parar, self.btn_continuar, self.btn_terminar):
            b.config(state="disabled")
        self.btn_nueva.config(state="normal")
        self.btn_cerrar_turno.config(state="normal")
        self.lbl_estado.config(text="🏁  Viaje terminado", fg="#f5c518")

    # Resetea los contadores y prepara el sistema para iniciar una carrera adicional
    def nueva_carrera(self):
        if self.turno_cerrado: return
        self.tiempo_total = 0; self.tiempo_movimiento = 0; self.tiempo_detenido = 0
        self.estado = "detenido"; self.iniciado = False; self.intervalo = None
        self.tramo_actual = 0; self.tramo_inicio_mov = 0; self.tramo_inicio_det = 0
        self.hora_inicio_tramo = ""
        self.lbl_contador.config(text="0 s")
        self._actualizar_resumen_carrera()
        self._arrancar_carrera()

    # Finaliza el turno de trabajo, genera el resumen diario y persiste los datos en la BD
    def cerrar_turno(self):
        if self.turno_cerrado: return
        if not messagebox.askyesno("Cerrar turno",
            f"¿Confirmas el cierre del turno de {self.conductor}?\n\nNo se podrán iniciar más carreras."):
            return
        self.turno_cerrado     = True
        self.hora_cierre_turno = ahora_str()

        # ── Resumen total del día antes del cierre ──
        cm  = self.dia_movimiento * TARIFA_MOVIMIENTO
        cd  = self.dia_detenido   * TARIFA_DETENIDO
        tot = self.dia_total_costo
        self.tabla.insert("", "end",
            values=("── RESUMEN DEL DÍA ──", "", "", "", "", "", ""),
            tags=("resumen_header",))
        self.tabla.insert("", "end",
            values=(f"🚖 {self.dia_carreras} carreras",
                    self.hora_inicio_turno,
                    self.hora_cierre_turno,
                    f"{self.dia_detenido} s",
                    f"{self.dia_movimiento} s",
                    f"{self.dia_movimiento + self.dia_detenido} s",
                    f"S/ {tot:.2f}"),
            tags=("resumen_total",))
        self._scroll_tabla()

        self.tabla.insert("", "end",
            values=(f"🔒 TURNO CERRADO — {self.hora_cierre_turno}", "", "", "", "", "", ""),
            tags=("turno_cerrado",))
        self._scroll_tabla()
        for b in (self.btn_iniciar_turno, self.btn_parar, self.btn_continuar,
                  self.btn_terminar, self.btn_nueva, self.btn_cerrar_turno):
            b.config(state="disabled")
        self.lbl_estado.config(text=f"🔒  Turno cerrado {self.hora_cierre_turno}", fg="#ff6b6b")
        self._guardar_en_bd()
        messagebox.showinfo("Turno cerrado",
            f"Turno cerrado a las {self.hora_cierre_turno}.\n"
            f"Total carreras: {self.dia_carreras}\n"
            f"Total recaudado: S/ {self.dia_total_costo:.2f}\n\n"
            "Datos guardados. Puedes ver las estadísticas o descargar el resumen.")

    # Guarda los datos del turno y todas sus carreras en la base de datos TinyDB
    def _guardar_en_bd(self):
        self.db.table("turnos").insert({
            "conductor":           self.conductor,
            "fecha":               self.fecha,
            "inicio_turno":        self.hora_inicio_turno,
            "cierre_turno":        self.hora_cierre_turno,
            "total_carreras":      self.dia_carreras,
            "tiempo_movimiento_s": self.dia_movimiento,
            "tiempo_detenido_s":   self.dia_detenido,
            "costo_movimiento":    round(self.dia_movimiento * TARIFA_MOVIMIENTO, 2),
            "costo_detenido":      round(self.dia_detenido   * TARIFA_DETENIDO,   2),
            "total_s":             round(self.dia_total_costo, 2),
        })
        for r in self.historial_export:
            self.db.table("carreras").insert({"conductor": self.conductor,
                                              "fecha": self.fecha, **r})

    # ── EXPORTAR ──────────────────────────────────────────────────────
    # Verifica si hay datos en el historial antes de intentar exportar
    def _check_datos(self):
        if not self.historial_export:
            messagebox.showinfo("Sin datos", "Aún no hay carreras registradas.")
            return False
        return True

    # Genera la ruta de archivo para exportar (CSV, JSON, MD) basada en conductor y fecha
    def _ruta(self, ext):
        nombre = f"resumen_{self.conductor.replace(' ','_')}_{self.fecha.replace('/','_')}.{ext}"
        return os.path.join(os.path.expanduser("~"), nombre)

    # Exporta el resumen del día y el historial de carreras a un archivo CSV
    def descargar_csv(self):
        if not self._check_datos(): return
        ruta = self._ruta("csv")
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["TAXÍMETRO — RESUMEN DEL DÍA"])
            w.writerow(["Conductor:", self.conductor]); w.writerow(["Fecha:", self.fecha])
            w.writerow(["Inicio de turno:", self.hora_inicio_turno]); w.writerow([])
            w.writerow(["CARRERA","TRAMO","TIPO","INICIO","FIN","DET(s)","MOV(s)","TOTAL(s)","COSTO(S/)"])
            for r in self.historial_export:
                w.writerow([r["carrera"],r["tramo"],r["tipo"],r["inicio"],r["fin"],
                            r["detenido"],r["movimiento"],r["total"],f"{r['costo']:.2f}"])
            w.writerow([]); w.writerow(["RESUMEN TOTAL"])
            w.writerow(["Carreras:", self.dia_carreras])
            w.writerow(["Movimiento(s):", self.dia_movimiento])
            w.writerow(["Detenido(s):", self.dia_detenido])
            w.writerow(["TOTAL(S/):", f"{self.dia_total_costo:.2f}"])
        messagebox.showinfo("✅ CSV guardado", f"Archivo:\n{ruta}")

    # Exporta los datos del turno y carreras a un archivo JSON estructurado
    def descargar_json(self):
        if not self._check_datos(): return
        ruta = self._ruta("json")
        data = {"conductor":self.conductor,"fecha":self.fecha,
                "inicio_turno":self.hora_inicio_turno,"turno_cerrado":self.turno_cerrado,
                "carreras":self.historial_export,
                "resumen_dia":{"total_carreras":self.dia_carreras,
                               "tiempo_movimiento_s":self.dia_movimiento,
                               "tiempo_detenido_s":self.dia_detenido,
                               "total_s":round(self.dia_total_costo,2)}}
        with open(ruta,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)
        messagebox.showinfo("✅ JSON guardado", f"Archivo:\n{ruta}")

    # Exporta un reporte legible del turno y carreras en formato Markdown
    def descargar_md(self):
        if not self._check_datos(): return
        ruta = self._ruta("md")
        cm = self.dia_movimiento * TARIFA_MOVIMIENTO
        cd = self.dia_detenido   * TARIFA_DETENIDO
        lines = ["# 🚕 Taxímetro — Resumen del día","",
                 "| Campo | Valor |","|-------|-------|",
                 f"| **Conductor** | {self.conductor} |",
                 f"| **Fecha** | {self.fecha} |",
                 f"| **Inicio de turno** | {self.hora_inicio_turno} |",
                 f"| **Estado** | {'Cerrado 🔒' if self.turno_cerrado else 'Abierto 🟢'} |",""]
        carr_actual = None
        for r in self.historial_export:
            if r["carrera"] != carr_actual:
                carr_actual = r["carrera"]
                lines += [f"## 🚖 Carrera {carr_actual}","",
                          "| Tramo | Tipo | Inicio | Fin | Det | Mov | Total | Costo |",
                          "|-------|------|--------|-----|-----|-----|-------|-------|"]
            ico = "🟢" if r["tipo"]=="Movimiento" else "🔴"
            lines.append(f"| {r['tramo']} | {ico} {r['tipo']} | {r['inicio']} | {r['fin']} "
                         f"| {r['detenido']}s | {r['movimiento']}s | {r['total']}s | S/ {r['costo']:.2f} |")
        lines += ["","---","","## 📊 Resumen total del día","",
                  "| Concepto | Valor |","|----------|-------|",
                  f"| Total carreras | {self.dia_carreras} |",
                  f"| Tiempo en movimiento | {self.dia_movimiento} s |",
                  f"| Tiempo detenido | {self.dia_detenido} s |",
                  f"| Costo movimiento | S/ {cm:.2f} |",
                  f"| Costo detenido | S/ {cd:.2f} |",
                  f"| **TOTAL** | **S/ {self.dia_total_costo:.2f}** |"]
        with open(ruta,"w",encoding="utf-8") as f: f.write("\n".join(lines))
        messagebox.showinfo("✅ MD guardado", f"Archivo:\n{ruta}")

    # ── HELPERS ───────────────────────────────────────────────────────
    # Bucle principal del taxímetro: incrementa los contadores de tiempo cada segundo
    def _tick(self):
        self.tiempo_total += 1
        if self.estado == "movimiento":
            self.tiempo_movimiento += 1; self.tramo_inicio_mov += 1
        else:
            self.tiempo_detenido   += 1; self.tramo_inicio_det += 1
        self.lbl_contador.config(text=f"{self.tiempo_total} s")
        self._actualizar_resumen_carrera()
        self.intervalo = self.root.after(1000, self._tick)

    # Registra un tramo (período continuo en un mismo estado) en la tabla y el historial
    def _cerrar_tramo(self):
        det = self.tramo_inicio_det; mov = self.tramo_inicio_mov; tot = det + mov
        if tot == 0: return
        hora_fin = ahora_str()
        costo = mov * TARIFA_MOVIMIENTO + det * TARIFA_DETENIDO
        tipo  = "Movimiento" if self.estado == "movimiento" else "Detenido"
        icono = "🟢" if self.estado == "movimiento" else "🔴"
        self.tabla.insert("", "end", values=(
            f"{icono} Tramo {self.tramo_actual}",
            self.hora_inicio_tramo, hora_fin,
            f"{det} s", f"{mov} s", f"{tot} s", f"S/ {costo:.2f}"))
        self._scroll_tabla()
        self.historial_export.append({
            "carrera":self.carrera_actual,"tramo":self.tramo_actual,"tipo":tipo,
            "inicio":self.hora_inicio_tramo,"fin":hora_fin,
            "detenido":det,"movimiento":mov,"total":tot,"costo":costo})

    # Hace scroll automático hacia abajo en la tabla de historial de viajes
    def _scroll_tabla(self):
        ch = self.tabla.get_children()
        if ch: self.tabla.see(ch[-1])

    # Construye un panel de resumen (carrera actual o total del día) en la interfaz
    def _build_resumen_panel(self, parent, titulo, color_titulo, attrs, color_total):
        frame = tk.Frame(parent, bg="#16213e")
        frame.pack(fill="x")
        tk.Label(frame, text=f"── {titulo} ──",
                 bg="#16213e", fg=color_titulo,
                 font=("Arial", 8, "bold")
                 ).grid(row=0, column=0, columnspan=2, pady=(6, 2), padx=4)
        lkw = dict(bg="#16213e", fg="#cdd6f4", font=("Arial", 9), anchor="w")
        lvw = dict(bg="#16213e", fg="#ffffff",  font=("Arial", 9, "bold"), anchor="e")
        tk.Label(frame, text="🚖 Carreras:",   **lkw).grid(row=1, column=0, padx=(8,2), sticky="w")
        lc = tk.Label(frame, text="0", **lvw); lc.grid(row=1, column=1, padx=(2,8), sticky="e")
        tk.Label(frame, text="🟢 Movimiento:", **lkw).grid(row=2, column=0, padx=(8,2), sticky="w")
        lm = tk.Label(frame, text="0s  S/0.00", **lvw); lm.grid(row=2, column=1, padx=(2,8), sticky="e")
        tk.Label(frame, text="🔴 Detenido:",   **lkw).grid(row=3, column=0, padx=(8,2), sticky="w")
        ld = tk.Label(frame, text="0s  S/0.00", **lvw); ld.grid(row=3, column=1, padx=(2,8), sticky="e")
        tk.Label(frame, text="TOTAL:", bg="#16213e", fg=color_total,
                 font=("Arial", 11, "bold"), anchor="w"
                 ).grid(row=4, column=0, padx=(8,2), pady=(3,6), sticky="w")
        lt = tk.Label(frame, text="S/ 0.00", bg="#16213e", fg=color_total,
                      font=("Arial", 11, "bold"), anchor="e")
        lt.grid(row=4, column=1, padx=(2,8), pady=(3,6), sticky="e")
        frame.columnconfigure(1, weight=1)
        a_carr, a_mov, a_det, a_tot = attrs
        setattr(self, a_carr, lc); setattr(self, a_mov, lm)
        setattr(self, a_det,  ld); setattr(self, a_tot, lt)

    # Función auxiliar para crear botones estilizados de manera uniforme
    def _btn(self, parent, texto, color, cmd, state="normal", fg_color="white"):
        return tk.Button(parent, text=texto, bg=color, fg=fg_color,
                         font=("Arial", 10, "bold"), relief="flat", cursor="hand2",
                         activebackground=color, activeforeground=fg_color,
                         padx=6, pady=7, state=state, command=cmd)

    # Actualiza los valores mostrados en el panel de resumen de la carrera actual
    def _actualizar_resumen_carrera(self):
        cm = self.tiempo_movimiento * TARIFA_MOVIMIENTO
        cd = self.tiempo_detenido   * TARIFA_DETENIDO
        self.lbl_r_carr.config(text=str(self.carrera_actual) if self.carrera_actual else "0")
        self.lbl_r_mov.config(text=f"{self.tiempo_movimiento}s  S/{cm:.2f}")
        self.lbl_r_det.config(text=f"{self.tiempo_detenido}s  S/{cd:.2f}")
        self.lbl_r_total.config(text=f"S/ {cm+cd:.2f}")

    # Actualiza los valores mostrados en el panel de resumen total del día
    def _actualizar_resumen_dia(self):
        cm = self.dia_movimiento * TARIFA_MOVIMIENTO
        cd = self.dia_detenido   * TARIFA_DETENIDO
        self.lbl_d_carr.config(text=str(self.dia_carreras))
        self.lbl_d_mov.config(text=f"{self.dia_movimiento}s  S/{cm:.2f}")
        self.lbl_d_det.config(text=f"{self.dia_detenido}s  S/{cd:.2f}")
        self.lbl_d_total.config(text=f"S/ {self.dia_total_costo:.2f}")

    # Actualiza la etiqueta visual que indica si el taxi está en movimiento o detenido
    def _actualizar_estado_label(self):
        if self.estado == "movimiento":
            self.lbl_estado.config(text="🟢  En movimiento", fg="#0f9b58")
        else:
            self.lbl_estado.config(text="🔴  Detenido", fg="#e74c3c")


# --- PUNTO DE ENTRADA ---
# Inicia la aplicación de Tkinter
if __name__ == "__main__":
    root = tk.Tk()
    Taximetro(root)
    root.mainloop()