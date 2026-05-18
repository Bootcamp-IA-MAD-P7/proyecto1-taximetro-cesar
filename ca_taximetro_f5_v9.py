# Documentación Completa — Sistema Taxímetro F5 V.P9

```python
"""
═══════════════════════════════════════════════════════════════
 TAXÍMETRO F5 V.P9
═══════════════════════════════════════════════════════════════

Autor: Cesar Sandoval
Versión: F5 V.P9
Lenguaje: Python 3
Framework GUI: Tkinter
Base de datos: TinyDB

DESCRIPCIÓN GENERAL
───────────────────────────────────────────────────────────────
Proyecto educativo para  codificar un taxímetro digital con control de turnos, carreras, 
tiempos de movimiento/detenido, estadísticas,gráficos y exportación de reportes.

FUNCIONALIDADES PRINCIPALES
───────────────────────────────────────────────────────────────
✓ Inicio y cierre de turnos
✓ Registro de carreras
✓ Control de estados:
    - Movimiento
    - Detenido
✓ Cálculo automático de tarifas
✓ Historial visual de viajes
✓ Estadísticas por conductor y fecha
✓ Ranking de conductores
✓ Gráficos estadísticos
✓ Exportación:
    - CSV
    - JSON
    - Markdown
✓ Persistencia local usando TinyDB

OBJETIVO DEL PROYECTO
───────────────────────────────────────────────────────────────
Permitir el control operativo y financiero de un servicio de taxi mediante 
el registro automático del tiempo en movimiento y detenido, calculando costos y 
almacenando el historial de turnos y carreras.

ESTRUCTURA GENERAL
───────────────────────────────────────────────────────────────
1. Configuración global
2. Clase principal Taximetro
3. Construcción de interfaz gráfica
4. Lógica del taxímetro
5. Estadísticas y visualización
6. Persistencia de datos
7. Exportación de reportes

═══════════════════════════════════════════════════════════════
"""

# ═════════════════════════════════════════════════════════════
# IMPORTACIÓN DE LIBRERÍAS
# ═════════════════════════════════════════════════════════════

# Tkinter: Framework estándar de Python para GUI
import tkinter as tk

# ttk: Widgets avanzados
from tkinter import ttk, simpledialog, messagebox

# Librerías estándar del sistema para conversión de formatos
import datetime, csv, json, os

# TinyDB: Base de datos documental ligera basada en JSON
from tinydb import TinyDB, Query

# defaultdict: Diccionario con valores automáticos
from collections import defaultdict


# ═════════════════════════════════════════════════════════════
# CONFIGURACIÓN GLOBAL DEL SISTEMA
# ═════════════════════════════════════════════════════════════

# Tarifa aplicada por segundo en movimiento
TARIFA_MOVIMIENTO = 0.05

# Tarifa aplicada por segundo detenido
TARIFA_DETENIDO   = 0.02

# Ruta local donde se almacenará la base de datos JSON
DB_PATH = os.path.join(os.path.expanduser("~"), "taximetro_db.json")


# ═════════════════════════════════════════════════════════════
# FUNCIONES UTILITARIAS
# ═════════════════════════════════════════════════════════════


def ahora_str():
    """
    Retorna la hora actual del sistema en formato HH:MM:SS.

    Utilizada para:
    ─────────────────────────────
    - Registrar inicio de tramos
    - Registrar fin de tramos
    - Registrar inicio de turnos
    - Registrar cierre de turnos
    """
    return datetime.datetime.now().strftime("%H:%M:%S")



def fecha_str():
    """
    Retorna la fecha actual en formato DD/MM/YYYY.

    Utilizada para:
    ─────────────────────────────
    - Registrar turnos
    - Estadísticas
    - Reportes exportados
    """
    return datetime.datetime.now().strftime("%d/%m/%Y")


# ═════════════════════════════════════════════════════════════
# CLASE PRINCIPAL DEL SISTEMA
# ═════════════════════════════════════════════════════════════

class Taximetro:
    """
    Clase principal del sistema Taxímetro.

    Gestiona:
    ─────────────────────────────
    - Interfaz gráfica
    - Control de turnos
    - Carreras
    - Tramos
    - Estadísticas
    - Persistencia de datos
    - Exportación de reportes
    - Visualización gráfica
    """

    def __init__(self, root):
        """
        Inicializa la aplicación.

        Parámetros:
        ─────────────────────────────
        root : tkinter.Tk
            Ventana principal de la aplicación.

        Funciones:
        ─────────────────────────────
        - Configura la ventana principal
        - Inicializa variables de estado
        - Conecta la base de datos
        - Solicita conductor
        - Construye interfaz gráfica
        """

        # Referencia principal a la ventana Tkinter
        self.root = root

        # Configuración visual principal
        self.root.title("Taximetro F5 V.P9")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(True, True)
        self.root.geometry("1280x768")

        # Inicialización de base de datos TinyDB
        self.db = TinyDB(DB_PATH)

        # Solicita nombre del conductor
        self.conductor = self._pedir_conductor()

        # Fecha actual del sistema
        self.fecha = fecha_str()

        # ═════════════════════════════════════════════════════
        # VARIABLES DE ESTADO DE LA CARRERA
        # ═════════════════════════════════════════════════════

        # Tiempo total acumulado
        self.tiempo_total = 0

        # Tiempo acumulado en movimiento
        self.tiempo_movimiento = 0

        # Tiempo acumulado detenido
        self.tiempo_detenido = 0

        # Estado actual del vehículo
        # Valores posibles:
        # - movimiento
        # - detenido
        self.estado = "detenido"

        # Indica si la carrera está activa
        self.iniciado = False

        # Referencia al temporizador after() de Tkinter
        self.intervalo = None

        # Número de tramo actual
        self.tramo_actual = 0

        # Contadores internos por tramo
        self.tramo_inicio_mov = 0
        self.tramo_inicio_det = 0

        # Hora de inicio del tramo actual
        self.hora_inicio_tramo = ""

        # Número de carrera actual
        self.carrera_actual = 0

        # Estado del turno
        self.turno_iniciado = False
        self.turno_cerrado = False

        # Horas de control del turno
        self.hora_inicio_turno = ""
        self.hora_cierre_turno = ""

        # ═════════════════════════════════════════════════════
        # ACUMULADOS DEL DÍA
        # ═════════════════════════════════════════════════════

        # Tiempo total en movimiento del día
        self.dia_movimiento = 0

        # Tiempo total detenido del día
        self.dia_detenido = 0

        # Cantidad total de carreras
        self.dia_carreras = 0

        # Monto total recaudado
        self.dia_total_costo = 0.0

        # Historial utilizado para exportación
        self.historial_export = []

        # Construcción completa de la interfaz gráfica
        self._build_ui()


    # ═════════════════════════════════════════════════════════════
    # GESTIÓN DE CONDUCTOR
    # ═════════════════════════════════════════════════════════════

    def _pedir_conductor(self):
        """
        Solicita el nombre del conductor mediante diálogo.

        Funciones:
        ─────────────────────────────
        - Obtiene conductores registrados previamente
        - Muestra sugerencias
        - Retorna nombre validado

        Retorno:
        ─────────────────────────────
        str : Nombre del conductor
        """

        conductores = list({t["conductor"] for t in self.db.table("turnos").all()})

        hint = "  (conocidos: " + ", ".join(conductores[:4]) + ")" if conductores else ""

        n = simpledialog.askstring(
            "Bienvenido",
            f"Ingresa el nombre del conductor:{hint}",
            parent=self.root
        )

        return n.strip() if n and n.strip() else "Sin nombre"


    # ═════════════════════════════════════════════════════════════
    # CONSTRUCCIÓN DE INTERFAZ GRÁFICA
    # ═════════════════════════════════════════════════════════════

    def _build_ui(self):
        """
        Construye toda la interfaz gráfica principal.

        Secciones:
        ─────────────────────────────
        - Panel izquierdo:
            * Contador
            * Botones de control
            * Resúmenes
            * Exportaciones

        - Panel derecho:
            * Historial de viajes
            * Estadísticas
            * Ranking
            * Gráficos
        """

        # Contenedor principal de toda la aplicación
        main = tk.Frame(self.root, bg="#1a1a2e")

        # fill="both": ocupa ancho y alto
        # expand=True: se adapta al tamaño de ventana
        main.pack(fill="both", expand=True, padx=14, pady=14)

        # ═════════════════════════════════════════════════════
        # PANEL IZQUIERDO
        # ═════════════════════════════════════════════════════

        # Panel lateral con controles y resúmenes
        left = tk.Frame(main, bg="#1a1a2e", width=290)

        left.pack(side="left", fill="y", padx=(0, 10))

        # Evita que el frame cambie automáticamente de tamaño
        left.pack_propagate(False)

        # Título principal de la aplicación
        tk.Label(
            left,
            text="  TAXIMETRO F5 V.P9",
            bg="#1a1a2e",
            fg="#f5c518",
            font=("Arial", 16, "bold")
        ).pack(pady=(0, 6))

        # ═════════════════════════════════════════════════════
        # CONTADOR PRINCIPAL
        # ═════════════════════════════════════════════════════

        # Card visual del contador
        card = tk.Frame(left, bg="#16213e")
        card.pack(fill="x")

        # Etiqueta descriptiva
        tk.Label(
            card,
            text="Tiempo transcurrido",
            bg="#16213e",
            fg="#8892b0",
            font=("Arial", 10)
        ).pack(pady=(5, 0))

        # Contador principal del taxímetro
        self.lbl_contador = tk.Label(
            card,
            text="0 s",
            bg="#16213e",
            fg="#ffffff",
            font=("Arial", 28, "bold")
        )

        self.lbl_contador.pack()

        # Estado actual del sistema
        self.lbl_estado = tk.Label(
            card,
            text="⏸  Turno no iniciado",
            bg="#16213e",
            fg="#8892b0",
            font=("Arial", 10)
        )

        self.lbl_estado.pack(pady=(2, 8))

        # ═════════════════════════════════════════════════════
        # BOTONES DE CONTROL
        # ═════════════════════════════════════════════════════

        # Contenedor de botones operativos
        bf = tk.Frame(left, bg="#1a1a2e")
        bf.pack(fill="x", pady=(6, 0))

        # Botón para iniciar turno completo
        self.btn_iniciar_turno = self._btn(
            bf,
            "  Iniciar turno",
            "#f5c518",
            self.iniciar_turno,
            fg_color="#1a1a2e"
        )

        self.btn_iniciar_turno.pack(fill="x", pady=(0, 4))

        # Línea separadora visual
        tk.Frame(bf, bg="#2a2a4a", height=1).pack(fill="x", pady=(0, 4))

        # ═════════════════════════════════════════════════════
        # CONTROLES DE CARRERA
        # ═════════════════════════════════════════════════════

        # Frame horizontal para botones de estado
        row_pp = tk.Frame(bf, bg="#1a1a2e")
        row_pp.pack(fill="x")

        # Botón para detener movimiento
        self.btn_parar = self._btn(
            row_pp,
            "⏸ Parar",
            "#e67e22",
            self.parar,
            "disabled"
        )

        # Botón para continuar movimiento
        self.btn_continuar = self._btn(
            row_pp,
            "▶ Continuar",
            "#2980b9",
            self.continuar,
            "disabled"
        )

        # Botón para finalizar carrera
        self.btn_terminar = self._btn(
            row_pp,
            "■ Fin viaje",
            "#c0392b",
            self.terminar,
            "disabled"
        )

        # Empaquetado horizontal de botones
        self.btn_parar.pack(side="left", expand=True, fill="x", padx=(0, 2), pady=2)
        self.btn_continuar.pack(side="left", expand=True, fill="x", padx=2, pady=2)
        self.btn_terminar.pack(side="left", expand=True, fill="x", padx=(2, 0), pady=2)

        # ═════════════════════════════════════════════════════
        # BOTONES DE GESTIÓN DE CARRERAS
        # ═════════════════════════════════════════════════════

        row_nc = tk.Frame(bf, bg="#1a1a2e")
        row_nc.pack(fill="x", pady=2)

        # Inicia nueva carrera dentro del mismo turno
        self.btn_nueva = self._btn(
            row_nc,
            " Nueva carrera",
            "#6c3483",
            self.nueva_carrera,
            "disabled"
        )

        # Cierra definitivamente el turno
        self.btn_cerrar_turno = self._btn(
            row_nc,
            " Cerrar turno",
            "#7f3f00",
            self.cerrar_turno,
            "disabled"
        )

        # ═════════════════════════════════════════════════════
        # SUGERENCIAS DE DOCUMENTACIÓN
        # ═════════════════════════════════════════════════════

        # RECOMENDACIÓN:
        # Separar la construcción de UI en múltiples funciones:
        #
        # - _build_panel_izquierdo()
        # - _build_panel_derecho()
        # - _build_botones()
        # - _build_resumenes()
        #
        # Esto mejora:
        # - Mantenibilidad
        # - Lectura
        # - Escalabilidad
        # - Testing


    # ═════════════════════════════════════════════════════════════
    # CONTROL DE TURNOS
    # ═════════════════════════════════════════════════════════════

    def iniciar_turno(self):
        """
        Inicia un nuevo turno operativo.

        Funciones:
        ─────────────────────────────
        - Registra hora de inicio
        - Activa controles
        - Inserta encabezado en historial
        - Inicia automáticamente la primera carrera
        """

        # Evita múltiples inicios de turno
        if self.turno_iniciado or self.turno_cerrado:
            return

        # Marca turno como activo
        self.turno_iniciado = True

        # Registra hora inicial
        self.hora_inicio_turno = ahora_str()

        # Inserta encabezado visual en tabla
        self.tabla.insert(
            "",
            "end",
            values=(f" TURNO INICIADO — {self.hora_inicio_turno}", "", "", "", "", "", ""),
            tags=("header_turno",)
        )

        # Auto-scroll al final de la tabla
        self._scroll_tabla()

        # Desactiva botón de inicio
        self.btn_iniciar_turno.config(state="disabled")

        # Actualiza estado visual
        self.lbl_estado.config(text="⏸  Turno activo", fg="#7fff00")

        # Inicia automáticamente primera carrera
        self._arrancar_carrera()


    def _arrancar_carrera(self):
        """
        Inicializa una nueva carrera.

        Procesos:
        ─────────────────────────────
        - Incrementa contador de carreras
        - Reinicia variables de tramo
        - Configura estado inicial
        - Inicia temporizador principal
        """

        # Incremento de carrera actual
        self.carrera_actual += 1

        # Acumulador diario
        self.dia_carreras += 1

        # Marca carrera como activa
        self.iniciado = True

        # Estado inicial siempre es movimiento
        self.estado = "movimiento"

        # Primer tramo de la carrera
        self.tramo_actual = 1

        # Reinicio de contadores internos
        self.tramo_inicio_mov = 0
        self.tramo_inicio_det = 0

        # Hora de inicio del tramo
        self.hora_inicio_tramo = ahora_str()

        # Inserción visual en historial
        self.tabla.insert(
            "",
            "end",
            values=(f" CARRERA {self.carrera_actual}", "", "", "", "", "", ""),
            tags=("header_carrera",)
        )

        self._scroll_tabla()

        # Actualiza indicadores visuales
        self._actualizar_estado_label()

        # Habilitación/deshabilitación de controles
        self.btn_parar.config(state="normal")
        self.btn_continuar.config(state="disabled")
        self.btn_terminar.config(state="normal")

        # Inicia temporizador principal
        self._tick()


    # ═════════════════════════════════════════════════════════════
    # CONTROL DE ESTADOS DEL VEHÍCULO
    # ═════════════════════════════════════════════════════════════

    def parar(self):
        """
        Cambia el estado del vehículo a detenido.

        Acciones:
        ─────────────────────────────
        - Finaliza tramo anterior
        - Genera nuevo tramo detenido
        - Actualiza interfaz gráfica
        """

        # Validación de estado actual
        if not self.iniciado or self.estado == "detenido":
            return

        # Cierra tramo anterior
        self._cerrar_tramo()

        # Cambio de estado
        self.estado = "detenido"

        # Nuevo tramo
        self.tramo_actual += 1

        # Reinicio de contadores de tramo
        self.tramo_inicio_mov = 0
        self.tramo_inicio_det = 0

        # Nueva hora de inicio
        self.hora_inicio_tramo = ahora_str()

        # Refresca interfaz
        self._actualizar_estado_label()


    def continuar(self):
        """
        Reanuda el movimiento del vehículo.

        Acciones:
        ─────────────────────────────
        - Finaliza tramo detenido
        - Inicia nuevo tramo en movimiento
        - Actualiza controles visuales
        """

        if not self.iniciado or self.estado == "movimiento":
            return

        self._cerrar_tramo()

        self.estado = "movimiento"

        self.tramo_actual += 1

        self.tramo_inicio_mov = 0
        self.tramo_inicio_det = 0

        self.hora_inicio_tramo = ahora_str()

        self._actualizar_estado_label()


    # ═════════════════════════════════════════════════════════════
    # FINALIZACIÓN DE CARRERA
    # ═════════════════════════════════════════════════════════════

    def terminar(self):
        """
        Finaliza la carrera actual.

        Procesos:
        ─────────────────────────────
        - Detiene temporizador
        - Calcula costos
        - Genera subtotal
        - Actualiza acumulados diarios
        - Habilita nueva carrera
        """

        # Cancela temporizador Tkinter
        if self.intervalo:
            self.root.after_cancel(self.intervalo)
            self.intervalo = None

        # Finaliza último tramo
        self._cerrar_tramo()

        # Cálculo de costos
        cm = self.tiempo_movimiento * TARIFA_MOVIMIENTO
        cd = self.tiempo_detenido * TARIFA_DETENIDO

        # Total general de carrera
        total = cm + cd

        # Inserta subtotal en historial
        self.tabla.insert(
            "",
            "end",
            values=(
                " SUBTOTAL",
                "",
                "",
                f"{self.tiempo_detenido} s",
                f"{self.tiempo_movimiento} s",
                f"{self.tiempo_total} s",
                f"S/ {total:.2f}"
            ),
            tags=("subtotal",)
        )

        self._scroll_tabla()

        # Actualización de acumulados diarios
        self.dia_movimiento += self.tiempo_movimiento
        self.dia_detenido += self.tiempo_detenido
        self.dia_total_costo += total

        # Refresca paneles resumen
        self._actualizar_resumen_carrera()
        self._actualizar_resumen_dia()


    # ═════════════════════════════════════════════════════════════
    # TEMPORIZADOR PRINCIPAL
    # ═════════════════════════════════════════════════════════════

    def _tick(self):
        """
        Temporizador principal del taxímetro.

        Se ejecuta cada segundo para:
        ─────────────────────────────
        - Incrementar tiempos
        - Actualizar movimiento/detenido
        - Refrescar contador visual
        - Mantener sincronización del sistema
        """

        # Incrementa tiempo total
        self.tiempo_total += 1

        # Incrementa contadores según estado actual
        if self.estado == "movimiento":
            self.tiempo_movimiento += 1
            self.tramo_inicio_mov += 1
        else:
            self.tiempo_detenido += 1
            self.tramo_inicio_det += 1

        # Actualiza contador visual
        self.lbl_contador.config(text=f"{self.tiempo_total} s")

        # Actualiza resumen de carrera
        self._actualizar_resumen_carrera()

        # Programa siguiente ejecución en 1 segundo
        self.intervalo = self.root.after(1000, self._tick)


    # ═════════════════════════════════════════════════════════════
    # GESTIÓN DE TRAMOS
    # ═════════════════════════════════════════════════════════════

    def _cerrar_tramo(self):
        """
        Finaliza el tramo actual y lo registra.

        Información almacenada:
        ─────────────────────────────
        - Tipo de tramo
        - Hora inicio/fin
        - Tiempo detenido
        - Tiempo movimiento
        - Tiempo total
        - Costo
        """

        # Tiempos internos del tramo
        det = self.tramo_inicio_det
        mov = self.tramo_inicio_mov

        # Tiempo total del tramo
        tot = det + mov

        # Evita registrar tramos vacíos
        if tot == 0:
            return

        # Hora final del tramo
        hora_fin = ahora_str()

        # Cálculo de costo
        costo = mov * TARIFA_MOVIMIENTO + det * TARIFA_DETENIDO

        # Tipo descriptivo
        tipo = "Movimiento" if self.estado == "movimiento" else "Detenido"

        # Icono visual
        icono = "" if self.estado == "movimiento" else ""

        # Inserción visual en tabla
        self.tabla.insert(
            "",
            "end",
            values=(
                f"{icono} Tramo {self.tramo_actual}",
                self.hora_inicio_tramo,
                hora_fin,
                f"{det} s",
                f"{mov} s",
                f"{tot} s",
                f"S/ {costo:.2f}"
            )
        )

        self._scroll_tabla()

        # Registro interno para exportación y BD
        self.historial_export.append({
            "carrera": self.carrera_actual,
            "tramo": self.tramo_actual,
            "tipo": tipo,
            "inicio": self.hora_inicio_tramo,
            "fin": hora_fin,
            "detenido": det,
            "movimiento": mov,
            "total": tot,
            "costo": costo
        })


    # ═════════════════════════════════════════════════════════════
    # CIERRE DE TURNO
    # ═════════════════════════════════════════════════════════════

    def cerrar_turno(self):
        """
        Finaliza definitivamente el turno operativo.

        Procesos:
        ─────────────────────────────
        - Solicita confirmación
        - Genera resumen total
        - Guarda información en BD
        - Bloquea controles
        - Notifica al usuario
        """

        if self.turno_cerrado:
            return

        # Confirmación de seguridad
        if not messagebox.askyesno(
            "Cerrar turno",
            f"¿Confirmas el cierre del turno de {self.conductor}?\n\nNo se podrán iniciar más carreras."
        ):
            return

        # Marca cierre definitivo
        self.turno_cerrado = True

        # Registra hora de cierre
        self.hora_cierre_turno = ahora_str()

        # Guarda toda la información en BD
        self._guardar_en_bd()

        # Notificación final
        messagebox.showinfo(
            "Turno cerrado",
            f"Turno cerrado a las {self.hora_cierre_turno}."
        )


    # ═════════════════════════════════════════════════════════════
    # PERSISTENCIA EN BASE DE DATOS
    # ═════════════════════════════════════════════════════════════

    def _guardar_en_bd(self):
        """
        Guarda información del turno y carreras en TinyDB.

        Tablas utilizadas:
        ─────────────────────────────
        - turnos
        - carreras

        Datos almacenados:
        ─────────────────────────────
        - conductor
        - fecha
        - tiempos
        - costos
        - carreras realizadas
        """

        # Inserción principal de turno
        self.db.table("turnos").insert({
            "conductor": self.conductor,
            "fecha": self.fecha,
            "inicio_turno": self.hora_inicio_turno,
            "cierre_turno": self.hora_cierre_turno,
            "total_carreras": self.dia_carreras,
            "tiempo_movimiento_s": self.dia_movimiento,
            "tiempo_detenido_s": self.dia_detenido,
            "costo_movimiento": round(self.dia_movimiento * TARIFA_MOVIMIENTO, 2),
            "costo_detenido": round(self.dia_detenido * TARIFA_DETENIDO, 2),
            "total_s": round(self.dia_total_costo, 2)
        })

        # Inserción individual de carreras
        for r in self.historial_export:
            self.db.table("carreras").insert({
                "conductor": self.conductor,
                "fecha": self.fecha,
                **r
            })


    # ═════════════════════════════════════════════════════════════
    # EXPORTACIÓN DE REPORTES
    # ═════════════════════════════════════════════════════════════

    def descargar_csv(self):
        """
        Exporta el resumen del día en formato CSV.

        Incluye:
        ─────────────────────────────
        - Datos del conductor
        - Historial de carreras
        - Resumen financiero
        """

        # Validación de existencia de datos
        if not self._check_datos():
            return

        # Ruta final del archivo
        ruta = self._ruta("csv")

        # Escritura del archivo CSV
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)

            # Cabecera principal
            w.writerow(["TAXÍMETRO — RESUMEN DEL DÍA"])

            # Información general
            w.writerow(["Conductor:", self.conductor])
            w.writerow(["Fecha:", self.fecha])

        # Mensaje final
        messagebox.showinfo("✅ CSV guardado", f"Archivo:\n{ruta}")


    def descargar_json(self):
        """
        Exporta información completa en formato JSON.

        Ideal para:
        ─────────────────────────────
        - APIs
        - Integraciones
        - Backups
        - Procesamiento externo
        """

        if not self._check_datos():
            return


    def descargar_md(self):
        """
        Genera reporte Markdown del turno.

        Incluye:
        ─────────────────────────────
        - Resumen del día
        - Detalle de carreras
        - Costos
        - Totales
        """

        if not self._check_datos():
            return


    # ═════════════════════════════════════════════════════════════
    # ESTADÍSTICAS Y ANALÍTICA
    # ═════════════════════════════════════════════════════════════

    def _cargar_stats(self):
        """
        Carga estadísticas desde TinyDB.

        Genera:
        ─────────────────────────────
        - KPIs
        - Ranking de conductores
        - Historial de turnos
        - Historial de carreras
        """

        # Obtención de datos desde BD
        turnos_raw = self.db.table("turnos").all()
        carreras_raw = self.db.table("carreras").all()

        # Filtros activos
        fc = self.filtro_conductor.get().strip().lower()
        ff = self.filtro_fecha.get().strip()

        # Filtrado por conductor
        if fc:
            turnos_raw = [
                t for t in turnos_raw
                if fc in t.get("conductor", "").lower()
            ]

        # Filtrado por fecha
        if ff:
            turnos_raw = [
                t for t in turnos_raw
                if t.get("fecha", "") == ff
            ]


    # ═════════════════════════════════════════════════════════════
    # GRÁFICOS ESTADÍSTICOS
    # ═════════════════════════════════════════════════════════════

    def _dibujar_graficos(self):
        """
        Dibuja gráficos estadísticos usando Canvas.

        Visualizaciones:
        ─────────────────────────────
        - Recaudación por fecha
        - Movimiento vs detenido
        - Comparativa por conductor
        """

        # Referencia al canvas principal
        c = self.canvas_graficos

        # Limpia gráficos anteriores
        c.delete("all")

        # Actualiza geometría interna
        c.update_idletasks()

        # Dimensiones dinámicas
        W = c.winfo_width()
        H = c.winfo_height()

        # Validación mínima de tamaño
        if W < 50 or H < 50:
            return


    # ═════════════════════════════════════════════════════════════
    # HELPERS GRÁFICOS
    # ═════════════════════════════════════════════════════════════

    def _barras(self, c, labels, valores, color, x1, y1, x2, y2, prefijo=""):
        """
        Dibuja gráfico de barras simple.

        Parámetros:
        ─────────────────────────────
        c : Canvas
            Superficie de dibujo

        labels : list
            Etiquetas del eje X

        valores : list
            Valores numéricos

        color : str
            Color hexadecimal de barras
        """

        # Evita división entre cero
        if not valores or max(valores) == 0:
            return


    def _barras_apiladas(self, c, labels, vals_mov, vals_det, x1, y1, x2, y2):
        """
        Dibuja gráfico de barras apiladas.

        Representa:
        ─────────────────────────────
        - Tiempo en movimiento
        - Tiempo detenido

        por conductor.
        """

        if not labels:
            return


    # ═════════════════════════════════════════════════════════════
    # HELPERS DE INTERFAZ
    # ═════════════════════════════════════════════════════════════

    def _scroll_tabla(self):
        """
        Desplaza automáticamente la tabla al último registro.

        Mejora:
        ─────────────────────────────
        - Experiencia visual
        - Seguimiento en tiempo real
        """

        ch = self.tabla.get_children()

        if ch:
            self.tabla.see(ch[-1])


    def _actualizar_estado_label(self):
        """
        Actualiza el indicador visual de estado.

        Estados posibles:
        ─────────────────────────────
        - Movimiento
        - Detenido
        """

        if self.estado == "movimiento":
            self.lbl_estado.config(
                text="  En movimiento",
                fg="#0f9b58"
            )
        else:
            self.lbl_estado.config(
                text="  Detenido",
                fg="#e74c3c"
            )


# ═════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA DEL SISTEMA
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Punto de inicio principal de la aplicación.

    Procesos:
    ─────────────────────────────
    - Crea ventana Tkinter
    - Inicializa Taximetro
    - Ejecuta loop principal
    """

    # Creación de ventana principal
    root = tk.Tk()

    # Inicialización de aplicación
    Taximetro(root)

    # Loop principal de eventos GUI
    root.mainloop()
```


