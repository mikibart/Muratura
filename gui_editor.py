#!/usr/bin/env python3
"""
GUI Editor per Muratura - Interfaccia grafica per definire edifici

Funzionalita':
- Canvas interattivo per disegnare muri
- Tabelle per editare dati numerici
- Import/Export file .mur
- Visualizzazione 2D pianta

Uso:
    python gui_editor.py
    oppure
    from gui_editor import MuraturaEditor
    app = MuraturaEditor()
    app.run()
"""

import sys
import math
from enum import Flag, auto
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


# ============================================================================
# OSNAP TYPES
# ============================================================================

class OsnapMode(Flag):
    """Tipi di Object Snap disponibili"""
    NONE = 0
    ENDPOINT = auto()    # Estremi dei muri
    MIDPOINT = auto()    # Punto medio dei muri
    INTERSECTION = auto()  # Intersezioni tra muri
    PERPENDICULAR = auto()  # Perpendicolare al muro
    GRID = auto()        # Griglia


@dataclass
class OsnapPoint:
    """Punto di snap trovato"""
    x: float
    y: float
    tipo: OsnapMode
    distanza: float  # distanza dal cursore

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QTableWidget, QTableWidgetItem,
    QToolBar, QAction, QActionGroup, QStatusBar, QMenuBar,
    QFileDialog, QMessageBox, QInputDialog, QDialog,
    QFormLayout, QLineEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QDialogButtonBox, QLabel, QGroupBox,
    QHeaderView, QPushButton, QFrame, QStackedWidget,
    QWizard, QWizardPage, QCompleter, QListWidget, QTextEdit,
    QGridLayout, QRadioButton, QButtonGroup, QScrollArea
)
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal, QSize
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QWheelEvent,
    QMouseEvent, QPainterPath, QKeyEvent, QIcon, QPixmap, QImage
)

# Import modulo sismico
try:
    from Material.seismic import (
        SeismicAnalysis, SoilCategory, TopographicCategory,
        UseClass, LimitState, COMUNI_DATABASE, search_comuni,
        get_all_regions, get_comuni_by_region
    )
    SEISMIC_AVAILABLE = True
except ImportError:
    SEISMIC_AVAILABLE = False
    print("Avviso: modulo seismic.py non disponibile")

# Import modulo solai
try:
    from Material.floors import (
        Floor, Roof, FloorType, FloorStiffness, RoofType,
        FloorStratigraphy, FLOOR_DATABASE, TYPICAL_STRATIFICATIONS,
        get_floor_presets, calculate_seismic_mass
    )
    FLOORS_AVAILABLE = True
except ImportError:
    FLOORS_AVAILABLE = False
    print("Avviso: modulo floors.py non disponibile")

# Import modulo carichi climatici
try:
    from Material.loads import (
        SnowLoad, WindLoad, SnowZone, WindZone,
        SnowExposure, SnowThermal, ExposureCategory, TopographicClass,
        calcola_carichi_climatici, get_zones_by_province, PROVINCE_ZONES
    )
    LOADS_AVAILABLE = True
except ImportError:
    LOADS_AVAILABLE = False
    print("Avviso: modulo loads.py non disponibile")


# ============================================================================
# STRUTTURE DATI
# ============================================================================

@dataclass
class ParametriSismici:
    """Parametri sismici del progetto"""
    comune: str = ""
    provincia: str = ""
    regione: str = ""
    sottosuolo: str = "B"  # A, B, C, D, E
    topografia: str = "T1"  # T1, T2, T3, T4
    vita_nominale: float = 50.0  # anni
    classe_uso: int = 2  # I, II, III, IV
    fattore_struttura: float = 1.5  # q per muratura


@dataclass
class CarichiClimatici:
    """Carichi neve e vento calcolati secondo NTC 2018"""
    # Neve
    zona_neve: str = "II"               # I-Alpina, I-Med, II, III
    qsk: float = 1.0                    # Carico neve al suolo [kN/m2]
    qs: float = 0.8                     # Carico neve su copertura [kN/m2]
    esposizione_neve: str = "normale"   # battuta_venti, normale, riparata

    # Vento
    zona_vento: int = 3                 # 1-9
    vb: float = 27.0                    # Velocita' riferimento [m/s]
    qb: float = 0.45                    # Pressione cinetica [kN/m2]
    p_vento: float = 1.0                # Pressione vento [kN/m2]
    categoria_esposizione: int = 3      # I-V


@dataclass
class Muro:
    """Rappresenta un muro con coordinate"""
    nome: str
    x1: float
    y1: float
    x2: float
    y2: float
    z: float
    altezza: float
    spessore: float
    materiale: str
    selected: bool = False
    # Risultati verifica (popolati dopo analisi)
    dcr: float = 0.0          # Demand/Capacity Ratio (0=non calcolato)
    dcr_tipo: str = ""        # Tipo verifica critica (taglio/flessione)
    verificato: bool = True   # True se DCR <= 1.0

    @property
    def lunghezza(self) -> float:
        return math.sqrt((self.x2 - self.x1)**2 + (self.y2 - self.y1)**2)

    @property
    def centro(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def angolo(self) -> float:
        return math.degrees(math.atan2(self.y2 - self.y1, self.x2 - self.x1))


@dataclass
class Apertura:
    """Rappresenta un'apertura (finestra/porta)"""
    muro: str
    tipo: str  # finestra, porta
    larghezza: float
    altezza: float
    distanza: float  # da inizio muro
    quota: float  # da base muro
    selected: bool = False


@dataclass
class Materiale:
    """Rappresenta un materiale"""
    nome: str
    tipo: str
    malta: str
    conservazione: str


@dataclass
class Piano:
    """Rappresenta un piano/solaio"""
    indice: int
    quota: float  # quota Z del piano
    altezza: float  # altezza interpiano
    massa: float = 0.0  # massa in kg
    # Planimetria di sfondo
    planimetria: str = ""  # percorso immagine
    plan_scala: float = 1.0  # scala immagine (pixel per metro)
    plan_x: float = 0.0  # offset X in metri
    plan_y: float = 0.0  # offset Y in metri
    plan_opacita: float = 0.5  # opacità (0-1)


@dataclass
class Carico:
    """Rappresenta i carichi su un piano"""
    piano: int
    permanente: float  # kN/m²
    variabile: float  # kN/m²
    copertura: bool = False


@dataclass
class Cordolo:
    """Rappresenta un cordolo (ring beam)"""
    nome: str
    piano: int
    base: float  # larghezza sezione [m]
    altezza: float  # altezza sezione [m]
    materiale: str = "calcestruzzo"
    # Coordinate opzionali (se None, cordolo perimetrale)
    x1: Optional[float] = None
    y1: Optional[float] = None
    x2: Optional[float] = None
    y2: Optional[float] = None
    selected: bool = False

    @property
    def is_perimetrale(self) -> bool:
        return self.x1 is None

    @property
    def area(self) -> float:
        return self.base * self.altezza

    @property
    def lunghezza(self) -> float:
        if self.x1 is not None:
            return math.sqrt((self.x2 - self.x1)**2 + (self.y2 - self.y1)**2)
        return 0.0


@dataclass
class Solaio:
    """Rappresenta un solaio del progetto"""
    nome: str
    piano: int                      # Piano (0 = terra)
    tipo: str = "laterocemento"     # laterocemento, legno, acciaio, ca_pieno, volta
    preset: str = "LAT_20+4"        # Preset dal database

    # Geometria
    luce: float = 5.0               # Luce [m]
    larghezza: float = 5.0          # Larghezza [m]
    orditura: float = 0.0           # Angolo orditura [gradi, 0=X]

    # Carichi automatici da preset
    peso_proprio: float = 3.2       # G1 [kN/m2]
    peso_finiture: float = 1.5      # G2 [kN/m2]
    carico_variabile: float = 2.0   # Qk [kN/m2]
    categoria_uso: str = "A"        # Categoria NTC

    # Rigidezza
    rigidezza: str = "rigido"       # rigido, semi_rigido, flessibile

    # Contorno (opzionale, per disegno)
    vertici: List[Tuple[float, float]] = field(default_factory=list)
    selected: bool = False

    @property
    def area(self) -> float:
        """Area approssimata"""
        if self.vertici and len(self.vertici) >= 3:
            # Calcolo area poligono (formula del laccio)
            n = len(self.vertici)
            a = 0.0
            for i in range(n):
                j = (i + 1) % n
                a += self.vertici[i][0] * self.vertici[j][1]
                a -= self.vertici[j][0] * self.vertici[i][1]
            return abs(a) / 2.0
        return self.luce * self.larghezza

    @property
    def G1(self) -> float:
        return self.peso_proprio

    @property
    def G2(self) -> float:
        return self.peso_finiture

    @property
    def Gk(self) -> float:
        return self.G1 + self.G2

    @property
    def Qk(self) -> float:
        return self.carico_variabile

    @property
    def carico_totale(self) -> float:
        return self.Gk + self.Qk

    def carico_progetto(self, combinazione: str = 'SLU') -> float:
        """Carico di progetto per combinazione"""
        if combinazione == 'SLU':
            return 1.3 * self.G1 + 1.5 * self.G2 + 1.5 * self.Qk
        elif combinazione == 'SLE':
            return self.Gk + self.Qk
        elif combinazione == 'SISMA':
            return self.G1 + self.G2 + 0.3 * self.Qk
        return self.carico_totale


@dataclass
class Progetto:
    """Contiene tutti i dati del progetto"""
    nome: str = "Nuovo Progetto"
    autore: str = ""
    data: str = ""
    muri: List[Muro] = field(default_factory=list)
    aperture: List[Apertura] = field(default_factory=list)
    materiali: List[Materiale] = field(default_factory=list)
    piani: List[Piano] = field(default_factory=list)
    carichi: List[Carico] = field(default_factory=list)
    cordoli: List[Cordolo] = field(default_factory=list)
    solai: List[Solaio] = field(default_factory=list)
    filepath: str = ""
    # Parametri sismici
    sismici: ParametriSismici = field(default_factory=ParametriSismici)
    # Carichi climatici (neve/vento)
    climatici: CarichiClimatici = field(default_factory=CarichiClimatici)
    # Parametri edificio
    n_piani: int = 1
    altezza_piano: float = 3.0
    altitudine: float = 100.0  # Altitudine sito [m s.l.m.]
    # Risultati analisi
    indice_rischio: float = 0.0  # IR = PGA_capacity / PGA_demand
    pga_domanda: float = 0.0  # PGA di domanda (ag)
    pga_capacita: float = 0.0  # PGA di capacita'


# ============================================================================
# CANVAS DI DISEGNO
# ============================================================================

class PiantaCanvas(QWidget):
    """Canvas per disegnare la pianta dell'edificio"""

    muroAggiunto = pyqtSignal(Muro)
    selezioneChanged = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(600, 400)
        self.setMouseTracking(True)

        # Stato
        self.progetto: Optional[Progetto] = None
        self.scala = 30.0  # pixel per metro
        self.offset_x = 50
        self.offset_y = 350
        self.griglia = True

        # Strumenti
        self.strumento = 'select'  # select, muro, finestra, porta, pan
        self.disegno_attivo = False
        self.punto_inizio: Optional[QPointF] = None
        self.punto_corrente: Optional[QPointF] = None

        # Materiale e quota correnti
        self.materiale_corrente = "mattoni"
        self.z_corrente = 0.0
        self.altezza_corrente = 3.0
        self.spessore_corrente = 0.45

        # Pan
        self.panning = False
        self.pan_start = None

        # OSNAP
        self.osnap_mode = OsnapMode.ENDPOINT | OsnapMode.GRID
        self.osnap_raggio = 0.5  # raggio di ricerca in metri
        self.osnap_attivo: Optional[OsnapPoint] = None

        # Griglia configurabile
        self.passo_griglia = 0.5  # metri (default 50cm)
        self.mostra_quote = True  # mostra lunghezze sui muri

        # Planimetria di sfondo
        self.planimetria_img: Optional[QPixmap] = None
        self.planimetria_piano: Optional[Piano] = None
        self.mostra_planimetria = True

        # Filtro piano
        self.solo_piano_corrente = False

        # Visualizzazione DCR
        self.mostra_dcr = False  # Colorazione muri per DCR

    def setProgetto(self, progetto: Progetto):
        self.progetto = progetto
        self.aggiornaPlanimetria()
        self.update()

    def aggiornaPlanimetria(self):
        """Aggiorna la planimetria per il piano corrente"""
        if not self.progetto:
            self.planimetria_img = None
            self.planimetria_piano = None
            return

        # Trova il piano corrispondente alla quota Z corrente
        piano = None
        for p in self.progetto.piani:
            if abs(p.quota - self.z_corrente) < 0.1:
                piano = p
                break

        if piano and piano.planimetria:
            if self.planimetria_piano != piano or self.planimetria_img is None:
                # Carica nuova immagine
                img = QPixmap(piano.planimetria)
                if not img.isNull():
                    self.planimetria_img = img
                    self.planimetria_piano = piano
                else:
                    self.planimetria_img = None
                    self.planimetria_piano = None
        else:
            self.planimetria_img = None
            self.planimetria_piano = None

    def caricaPlanimetria(self, filepath: str, piano: Piano):
        """Carica un'immagine planimetria per un piano"""
        piano.planimetria = filepath
        self.aggiornaPlanimetria()
        self.update()

    def setStrumento(self, strumento: str):
        self.strumento = strumento
        self.disegno_attivo = False
        self.punto_inizio = None
        self.update()

    def worldToScreen(self, x: float, y: float) -> QPointF:
        """Converte coordinate mondo in coordinate schermo"""
        sx = self.offset_x + x * self.scala
        sy = self.offset_y - y * self.scala  # Y invertito
        return QPointF(sx, sy)

    def screenToWorld(self, sx: float, sy: float) -> QPointF:
        """Converte coordinate schermo in coordinate mondo"""
        x = (sx - self.offset_x) / self.scala
        y = (self.offset_y - sy) / self.scala
        return QPointF(x, y)

    def snapToGrid(self, p: QPointF, grid_size: float = None) -> QPointF:
        """Snap al punto griglia piu' vicino"""
        if grid_size is None:
            grid_size = self.passo_griglia
        x = round(p.x() / grid_size) * grid_size
        y = round(p.y() / grid_size) * grid_size
        return QPointF(x, y)

    def setPassoGriglia(self, passo: float):
        """Imposta il passo della griglia in metri"""
        self.passo_griglia = max(0.05, min(2.0, passo))  # Limita tra 5cm e 2m
        self.update()

    def findOsnap(self, pos: QPointF) -> Optional[OsnapPoint]:
        """Trova il punto di snap piu' vicino"""
        if self.osnap_mode == OsnapMode.NONE or not self.progetto:
            return None

        candidati: List[OsnapPoint] = []
        px, py = pos.x(), pos.y()

        # ENDPOINT - estremi dei muri
        if OsnapMode.ENDPOINT in self.osnap_mode:
            for muro in self.progetto.muri:
                # Punto iniziale
                d1 = math.sqrt((px - muro.x1)**2 + (py - muro.y1)**2)
                if d1 < self.osnap_raggio:
                    candidati.append(OsnapPoint(muro.x1, muro.y1, OsnapMode.ENDPOINT, d1))
                # Punto finale
                d2 = math.sqrt((px - muro.x2)**2 + (py - muro.y2)**2)
                if d2 < self.osnap_raggio:
                    candidati.append(OsnapPoint(muro.x2, muro.y2, OsnapMode.ENDPOINT, d2))

        # MIDPOINT - punto medio dei muri
        if OsnapMode.MIDPOINT in self.osnap_mode:
            for muro in self.progetto.muri:
                mx, my = muro.centro
                d = math.sqrt((px - mx)**2 + (py - my)**2)
                if d < self.osnap_raggio:
                    candidati.append(OsnapPoint(mx, my, OsnapMode.MIDPOINT, d))

        # INTERSECTION - intersezioni tra muri
        if OsnapMode.INTERSECTION in self.osnap_mode:
            muri = self.progetto.muri
            for i, m1 in enumerate(muri):
                for m2 in muri[i+1:]:
                    inter = self.calcolaIntersezione(
                        m1.x1, m1.y1, m1.x2, m1.y2,
                        m2.x1, m2.y1, m2.x2, m2.y2
                    )
                    if inter:
                        ix, iy = inter
                        d = math.sqrt((px - ix)**2 + (py - iy)**2)
                        if d < self.osnap_raggio:
                            candidati.append(OsnapPoint(ix, iy, OsnapMode.INTERSECTION, d))

        # PERPENDICULAR - proiezione perpendicolare sul muro
        if OsnapMode.PERPENDICULAR in self.osnap_mode and self.punto_inizio:
            for muro in self.progetto.muri:
                perp = self.calcolaPerpendicolare(
                    self.punto_inizio.x(), self.punto_inizio.y(),
                    muro.x1, muro.y1, muro.x2, muro.y2
                )
                if perp:
                    perpx, perpy = perp
                    d = math.sqrt((px - perpx)**2 + (py - perpy)**2)
                    if d < self.osnap_raggio:
                        candidati.append(OsnapPoint(perpx, perpy, OsnapMode.PERPENDICULAR, d))

        # GRID - snap alla griglia (priorita' piu' bassa)
        if OsnapMode.GRID in self.osnap_mode:
            gx = round(px / 0.5) * 0.5
            gy = round(py / 0.5) * 0.5
            d = math.sqrt((px - gx)**2 + (py - gy)**2)
            if d < self.osnap_raggio:
                candidati.append(OsnapPoint(gx, gy, OsnapMode.GRID, d + 0.1))  # +0.1 per priorita' bassa

        # Restituisci il punto piu' vicino
        if candidati:
            return min(candidati, key=lambda p: p.distanza)
        return None

    def calcolaIntersezione(self, x1, y1, x2, y2, x3, y3, x4, y4) -> Optional[Tuple[float, float]]:
        """Calcola intersezione tra due segmenti"""
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-10:
            return None

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

        if 0 <= t <= 1 and 0 <= u <= 1:
            ix = x1 + t * (x2 - x1)
            iy = y1 + t * (y2 - y1)
            return (ix, iy)
        return None

    def calcolaPerpendicolare(self, px, py, x1, y1, x2, y2) -> Optional[Tuple[float, float]]:
        """Calcola il punto perpendicolare sul segmento"""
        dx, dy = x2 - x1, y2 - y1
        lunghezza_sq = dx*dx + dy*dy
        if lunghezza_sq == 0:
            return None

        t = ((px - x1) * dx + (py - y1) * dy) / lunghezza_sq
        if 0 <= t <= 1:
            return (x1 + t * dx, y1 + t * dy)
        return None

    def applicaOsnap(self, pos: QPointF) -> QPointF:
        """Applica OSNAP e restituisce la posizione snappata"""
        snap = self.findOsnap(pos)
        if snap:
            self.osnap_attivo = snap
            return QPointF(snap.x, snap.y)
        else:
            self.osnap_attivo = None
            return self.snapToGrid(pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Sfondo
        painter.fillRect(self.rect(), QColor(245, 245, 245))

        # Planimetria di sfondo
        if self.mostra_planimetria and self.planimetria_img and self.planimetria_piano:
            self.disegnaPlanimetria(painter)

        # Griglia
        if self.griglia:
            self.disegnaGriglia(painter)

        # Assi
        self.disegnaAssi(painter)

        # Muri
        if self.progetto:
            for muro in self.progetto.muri:
                # Filtra per piano se richiesto
                if self.solo_piano_corrente:
                    if abs(muro.z - self.z_corrente) > 0.1:
                        continue
                self.disegnaMuro(painter, muro)

            # Aperture
            for apertura in self.progetto.aperture:
                # Filtra aperture in base ai muri visibili
                if self.solo_piano_corrente:
                    muro = next((m for m in self.progetto.muri if m.nome == apertura.muro), None)
                    if muro and abs(muro.z - self.z_corrente) > 0.1:
                        continue
                self.disegnaApertura(painter, apertura)

        # Muro in corso di disegno
        if self.disegno_attivo and self.punto_inizio and self.punto_corrente:
            self.disegnaMuroTemporaneo(painter)

        # Marker OSNAP
        if self.osnap_attivo:
            self.disegnaOsnapMarker(painter)

    def disegnaPlanimetria(self, painter: QPainter):
        """Disegna la planimetria di sfondo"""
        piano = self.planimetria_piano
        img = self.planimetria_img

        # Calcola posizione e dimensioni
        # L'immagine viene posizionata secondo plan_x, plan_y (in metri)
        # e scalata secondo plan_scala (pixel immagine per metro)
        pos_screen = self.worldToScreen(piano.plan_x, piano.plan_y)

        # Dimensioni in pixel schermo
        # plan_scala = pixel immagine per metro reale
        # self.scala = pixel schermo per metro reale
        scala_totale = self.scala / piano.plan_scala
        width = int(img.width() * scala_totale)
        height = int(img.height() * scala_totale)

        # Applica opacità
        painter.setOpacity(piano.plan_opacita)

        # Disegna l'immagine (Y invertito perché coordinate schermo)
        painter.drawPixmap(
            int(pos_screen.x()),
            int(pos_screen.y()) - height,  # Y invertito
            width, height,
            img
        )

        # Ripristina opacità
        painter.setOpacity(1.0)

    def disegnaGriglia(self, painter: QPainter):
        """Disegna la griglia di sfondo con passo configurabile"""
        # Griglia secondaria (passo configurabile)
        pen_sec = QPen(QColor(235, 235, 235), 1)
        painter.setPen(pen_sec)

        passo = self.passo_griglia
        x_min, x_max = -10, 30
        y_min, y_max = -10, 30

        x = x_min
        while x <= x_max:
            p1 = self.worldToScreen(x, y_min)
            p2 = self.worldToScreen(x, y_max)
            painter.drawLine(p1, p2)
            x += passo

        y = y_min
        while y <= y_max:
            p1 = self.worldToScreen(x_min, y)
            p2 = self.worldToScreen(x_max, y)
            painter.drawLine(p1, p2)
            y += passo

        # Griglia principale (ogni metro)
        pen_main = QPen(QColor(200, 200, 200), 1)
        painter.setPen(pen_main)

        for x in range(x_min, x_max + 1):
            p1 = self.worldToScreen(x, y_min)
            p2 = self.worldToScreen(x, y_max)
            painter.drawLine(p1, p2)

        for y in range(y_min, y_max + 1):
            p1 = self.worldToScreen(x_min, y)
            p2 = self.worldToScreen(x_max, y)
            painter.drawLine(p1, p2)

        # Quote sulla griglia principale (ogni 5 metri)
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        for x in range(0, x_max + 1, 5):
            p = self.worldToScreen(x, -0.3)
            painter.drawText(int(p.x() - 10), int(p.y()), f"{x}m")

        for y in range(0, y_max + 1, 5):
            p = self.worldToScreen(-0.5, y)
            painter.drawText(int(p.x() - 20), int(p.y() + 5), f"{y}m")

    def disegnaAssi(self, painter: QPainter):
        """Disegna gli assi X e Y"""
        # Asse X
        pen = QPen(QColor(200, 0, 0), 2)
        painter.setPen(pen)
        p1 = self.worldToScreen(0, 0)
        p2 = self.worldToScreen(15, 0)
        painter.drawLine(p1, p2)
        painter.drawText(int(p2.x() + 5), int(p2.y() + 5), "X")

        # Asse Y
        pen = QPen(QColor(0, 150, 0), 2)
        painter.setPen(pen)
        p1 = self.worldToScreen(0, 0)
        p2 = self.worldToScreen(0, 12)
        painter.drawLine(p1, p2)
        painter.drawText(int(p2.x() - 15), int(p2.y() - 5), "Y")

        # Origine
        painter.setPen(QPen(Qt.black, 1))
        orig = self.worldToScreen(0, 0)
        painter.drawText(int(orig.x() - 15), int(orig.y() + 15), "0")

    def disegnaMuro(self, painter: QPainter, muro: Muro):
        """Disegna un singolo muro"""
        p1 = self.worldToScreen(muro.x1, muro.y1)
        p2 = self.worldToScreen(muro.x2, muro.y2)

        # Colore in base allo stato
        if muro.selected:
            colore = QColor(0, 120, 215)
            width = 4
        elif self.mostra_dcr and muro.dcr > 0:
            # Colorazione in base al DCR
            if muro.dcr <= 0.5:
                colore = QColor(0, 180, 0)       # Verde - sicuro
            elif muro.dcr <= 0.8:
                colore = QColor(100, 200, 0)    # Verde chiaro
            elif muro.dcr <= 1.0:
                colore = QColor(255, 200, 0)    # Giallo - attenzione
            elif muro.dcr <= 1.2:
                colore = QColor(255, 140, 0)    # Arancione
            else:
                colore = QColor(255, 0, 0)      # Rosso - critico
            width = max(3, int(muro.spessore * self.scala / 4))
        else:
            # Colore in base alla quota z
            if muro.z == 0:
                colore = QColor(139, 90, 43)  # Marrone - piano terra
            elif muro.z < 4:
                colore = QColor(180, 120, 60)  # Marrone chiaro - piano 1
            else:
                colore = QColor(210, 160, 100)  # Beige - piani superiori
            width = max(2, int(muro.spessore * self.scala / 5))

        pen = QPen(colore, width)
        painter.setPen(pen)
        painter.drawLine(p1, p2)

        # Nome muro e DCR al centro
        centro = self.worldToScreen(*muro.centro)
        painter.setPen(QPen(Qt.black, 1))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        if self.mostra_dcr and muro.dcr > 0:
            # Mostra DCR invece della lunghezza
            dcr_text = f"DCR={muro.dcr:.2f}"
            if muro.dcr > 1.0:
                dcr_text += " !"
            painter.drawText(int(centro.x()) - 20, int(centro.y()) - 5,
                            f"{muro.nome}\n{dcr_text}")
        else:
            painter.drawText(int(centro.x()) - 10, int(centro.y()) - 5,
                            f"{muro.nome}\n{muro.lunghezza:.1f}m")

    def disegnaApertura(self, painter: QPainter, apertura: Apertura):
        """Disegna un'apertura su un muro"""
        # Trova il muro di riferimento
        muro = next((m for m in self.progetto.muri if m.nome == apertura.muro), None)
        if not muro:
            return

        # Calcola posizione apertura sul muro
        dx = muro.x2 - muro.x1
        dy = muro.y2 - muro.y1
        lunghezza = muro.lunghezza
        if lunghezza == 0:
            return

        # Posizione lungo il muro (normalizzata)
        t = apertura.distanza / lunghezza
        x = muro.x1 + t * dx
        y = muro.y1 + t * dy

        pos = self.worldToScreen(x, y)
        size = apertura.larghezza * self.scala / 2

        # Colore in base al tipo
        if apertura.tipo == 'finestra':
            colore = QColor(135, 206, 250)  # Azzurro
        else:
            colore = QColor(160, 82, 45)  # Marrone porta

        if apertura.selected:
            colore = QColor(0, 120, 215)

        painter.setPen(QPen(colore, 2))
        painter.setBrush(QBrush(colore.lighter(150)))
        painter.drawRect(int(pos.x() - size), int(pos.y() - size/2),
                        int(size * 2), int(size))

    def disegnaMuroTemporaneo(self, painter: QPainter):
        """Disegna il muro in corso di creazione"""
        p1 = self.worldToScreen(self.punto_inizio.x(), self.punto_inizio.y())
        p2 = self.worldToScreen(self.punto_corrente.x(), self.punto_corrente.y())

        pen = QPen(QColor(0, 120, 215), 3, Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(p1, p2)

        # Mostra lunghezza
        lunghezza = math.sqrt(
            (self.punto_corrente.x() - self.punto_inizio.x())**2 +
            (self.punto_corrente.y() - self.punto_inizio.y())**2
        )
        centro = QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)
        painter.setPen(QPen(Qt.black, 1))
        painter.drawText(int(centro.x()), int(centro.y()) - 10, f"{lunghezza:.2f}m")

    def disegnaOsnapMarker(self, painter: QPainter):
        """Disegna il marker per l'OSNAP attivo"""
        snap = self.osnap_attivo
        pos = self.worldToScreen(snap.x, snap.y)
        size = 8

        # Colore e forma in base al tipo di snap
        if snap.tipo == OsnapMode.ENDPOINT:
            # Quadrato verde
            painter.setPen(QPen(QColor(0, 200, 0), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(int(pos.x() - size), int(pos.y() - size), size * 2, size * 2)
        elif snap.tipo == OsnapMode.MIDPOINT:
            # Triangolo arancione
            painter.setPen(QPen(QColor(255, 165, 0), 2))
            painter.setBrush(Qt.NoBrush)
            path = QPainterPath()
            path.moveTo(pos.x(), pos.y() - size)
            path.lineTo(pos.x() - size, pos.y() + size)
            path.lineTo(pos.x() + size, pos.y() + size)
            path.closeSubpath()
            painter.drawPath(path)
        elif snap.tipo == OsnapMode.INTERSECTION:
            # X rossa
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.drawLine(int(pos.x() - size), int(pos.y() - size),
                           int(pos.x() + size), int(pos.y() + size))
            painter.drawLine(int(pos.x() - size), int(pos.y() + size),
                           int(pos.x() + size), int(pos.y() - size))
        elif snap.tipo == OsnapMode.PERPENDICULAR:
            # Simbolo perpendicolare blu
            painter.setPen(QPen(QColor(0, 100, 255), 2))
            painter.drawLine(int(pos.x() - size), int(pos.y()),
                           int(pos.x() + size), int(pos.y()))
            painter.drawLine(int(pos.x()), int(pos.y() - size),
                           int(pos.x()), int(pos.y() + size))
        elif snap.tipo == OsnapMode.GRID:
            # Punto grigio
            painter.setPen(QPen(QColor(128, 128, 128), 1))
            painter.setBrush(QBrush(QColor(128, 128, 128)))
            painter.drawEllipse(int(pos.x() - 3), int(pos.y() - 3), 6, 6)

        # Mostra nome dello snap
        painter.setPen(QPen(Qt.black, 1))
        nome_snap = snap.tipo.name if snap.tipo != OsnapMode.NONE else ""
        painter.drawText(int(pos.x() + size + 3), int(pos.y() - 3), nome_snap)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            pos_mondo = self.screenToWorld(event.x(), event.y())
            pos_snap = self.applicaOsnap(pos_mondo)

            if self.strumento == 'muro':
                if not self.disegno_attivo:
                    self.disegno_attivo = True
                    self.punto_inizio = pos_snap
                    self.punto_corrente = pos_snap
                else:
                    # Completa il muro
                    self.creaMuro()
                    self.disegno_attivo = False

            elif self.strumento == 'select':
                self.selezionaElemento(pos_mondo)

            elif self.strumento == 'pan':
                self.panning = True
                self.pan_start = event.pos()

        elif event.button() == Qt.MiddleButton:
            self.panning = True
            self.pan_start = event.pos()

        elif event.button() == Qt.RightButton:
            # Annulla operazione corrente
            self.disegno_attivo = False
            self.punto_inizio = None
            self.osnap_attivo = None
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos_mondo = self.screenToWorld(event.x(), event.y())

        if self.disegno_attivo:
            self.punto_corrente = self.applicaOsnap(pos_mondo)
        else:
            # Mostra anteprima OSNAP anche senza disegnare
            self.osnap_attivo = self.findOsnap(pos_mondo)
        self.update()

        if self.panning and self.pan_start:
            delta = event.pos() - self.pan_start
            self.offset_x += delta.x()
            self.offset_y += delta.y()
            self.pan_start = event.pos()
            self.update()

        # Aggiorna status bar con coordinate
        self.parent().parent().statusBar().showMessage(
            f"X: {pos_mondo.x():.2f}m  Y: {pos_mondo.y():.2f}m  Scala: {self.scala:.0f}px/m"
        )

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() in (Qt.LeftButton, Qt.MiddleButton):
            self.panning = False
            self.pan_start = None

    def wheelEvent(self, event: QWheelEvent):
        # Zoom
        delta = event.angleDelta().y()
        fattore = 1.15 if delta > 0 else 0.85

        # Zoom centrato sulla posizione del mouse
        pos_prima = self.screenToWorld(event.x(), event.y())
        self.scala *= fattore
        self.scala = max(5, min(200, self.scala))
        pos_dopo = self.screenToWorld(event.x(), event.y())

        # Aggiusta offset per mantenere la posizione
        self.offset_x += (pos_dopo.x() - pos_prima.x()) * self.scala
        self.offset_y -= (pos_dopo.y() - pos_prima.y()) * self.scala

        self.update()

    def creaMuro(self):
        """Crea un nuovo muro dalle coordinate correnti"""
        if not self.progetto or not self.punto_inizio or not self.punto_corrente:
            return

        # Genera nome automatico
        n = len([m for m in self.progetto.muri if m.z == self.z_corrente]) + 1
        nome = f"M{n}"

        muro = Muro(
            nome=nome,
            x1=self.punto_inizio.x(),
            y1=self.punto_inizio.y(),
            x2=self.punto_corrente.x(),
            y2=self.punto_corrente.y(),
            z=self.z_corrente,
            altezza=self.altezza_corrente,
            spessore=self.spessore_corrente,
            materiale=self.materiale_corrente
        )

        self.progetto.muri.append(muro)
        self.muroAggiunto.emit(muro)
        self.punto_inizio = None
        self.punto_corrente = None
        self.update()

    def selezionaElemento(self, pos: QPointF):
        """Seleziona muro o apertura vicino al punto"""
        if not self.progetto:
            return

        # Deseleziona tutto
        for m in self.progetto.muri:
            m.selected = False
        for a in self.progetto.aperture:
            a.selected = False

        # Cerca muro vicino
        min_dist = float('inf')
        elemento_vicino = None

        for muro in self.progetto.muri:
            dist = self.distanzaPuntoSegmento(
                pos.x(), pos.y(),
                muro.x1, muro.y1, muro.x2, muro.y2
            )
            if dist < min_dist and dist < 0.5:  # soglia 0.5m
                min_dist = dist
                elemento_vicino = muro

        if elemento_vicino:
            elemento_vicino.selected = True
            self.selezioneChanged.emit(elemento_vicino)

        self.update()

    def distanzaPuntoSegmento(self, px, py, x1, y1, x2, y2) -> float:
        """Calcola distanza punto-segmento"""
        dx = x2 - x1
        dy = y2 - y1
        lunghezza_sq = dx*dx + dy*dy

        if lunghezza_sq == 0:
            return math.sqrt((px-x1)**2 + (py-y1)**2)

        t = max(0, min(1, ((px-x1)*dx + (py-y1)*dy) / lunghezza_sq))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy

        return math.sqrt((px-proj_x)**2 + (py-proj_y)**2)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Delete:
            self.eliminaSelezionato()
        elif event.key() == Qt.Key_Escape:
            self.disegno_attivo = False
            self.punto_inizio = None
            self.update()

    def eliminaSelezionato(self):
        """Elimina l'elemento selezionato"""
        if not self.progetto:
            return

        self.progetto.muri = [m for m in self.progetto.muri if not m.selected]
        self.progetto.aperture = [a for a in self.progetto.aperture if not a.selected]
        self.update()


# ============================================================================
# DIALOGS
# ============================================================================

class WizardNuovoProgetto(QWizard):
    """Wizard per creare un nuovo progetto con tutti i parametri"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuovo Progetto - Wizard")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setMinimumSize(700, 500)

        # Aggiungi pagine
        self.addPage(self.creaPaginaDatiGenerali())
        self.addPage(self.creaPaginaLocalizzazione())
        self.addPage(self.creaPaginaParametriEdificio())
        self.addPage(self.creaPaginaRiepilogo())

    def creaPaginaDatiGenerali(self) -> QWizardPage:
        """Pagina 1: Dati generali del progetto"""
        page = QWizardPage()
        page.setTitle("Dati Generali")
        page.setSubTitle("Inserisci le informazioni base del progetto")

        layout = QFormLayout(page)

        self.nome_edit = QLineEdit("Nuovo Edificio")
        self.nome_edit.setPlaceholderText("Nome del progetto")
        layout.addRow("Nome progetto:", self.nome_edit)

        self.autore_edit = QLineEdit()
        self.autore_edit.setPlaceholderText("Ing. Mario Rossi")
        layout.addRow("Progettista:", self.autore_edit)

        from datetime import datetime
        self.data_edit = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        layout.addRow("Data:", self.data_edit)

        # Tipo di intervento
        self.tipo_intervento = QComboBox()
        self.tipo_intervento.addItems([
            "Verifica edificio esistente",
            "Nuovo edificio",
            "Miglioramento sismico",
            "Adeguamento sismico"
        ])
        layout.addRow("Tipo intervento:", self.tipo_intervento)

        # Registra campi obbligatori
        page.registerField("nome*", self.nome_edit)

        return page

    def creaPaginaLocalizzazione(self) -> QWizardPage:
        """Pagina 2: Localizzazione sismica"""
        page = QWizardPage()
        page.setTitle("Localizzazione Sismica")
        page.setSubTitle("Definisci la posizione geografica e i parametri del sito")

        layout = QVBoxLayout(page)

        # Gruppo localita'
        grp_loc = QGroupBox("Localita'")
        loc_layout = QFormLayout(grp_loc)

        # Comune con autocompletamento
        self.comune_edit = QLineEdit()
        self.comune_edit.setPlaceholderText("Inizia a digitare il nome del comune...")
        if SEISMIC_AVAILABLE:
            completer = QCompleter(list(COMUNI_DATABASE.keys()))
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            self.comune_edit.setCompleter(completer)
            self.comune_edit.textChanged.connect(self.onComuneChanged)
        loc_layout.addRow("Comune:", self.comune_edit)

        self.provincia_label = QLabel("-")
        loc_layout.addRow("Provincia:", self.provincia_label)

        self.regione_label = QLabel("-")
        loc_layout.addRow("Regione:", self.regione_label)

        # Info sismiche (mostrate dopo selezione comune)
        self.ag_label = QLabel("-")
        loc_layout.addRow("ag (SLV):", self.ag_label)

        self.zona_label = QLabel("-")
        loc_layout.addRow("Zona sismica:", self.zona_label)

        layout.addWidget(grp_loc)

        # Gruppo parametri sito
        grp_sito = QGroupBox("Parametri del Sito")
        sito_layout = QFormLayout(grp_sito)

        self.sottosuolo_combo = QComboBox()
        self.sottosuolo_combo.addItems(["A", "B", "C", "D", "E"])
        self.sottosuolo_combo.setCurrentText("B")
        sottosuolo_desc = QLabel("B = Depositi di sabbie/ghiaie molto addensate (360 < Vs30 <= 800 m/s)")
        sottosuolo_desc.setStyleSheet("color: gray; font-size: 10px;")
        sito_layout.addRow("Categoria sottosuolo:", self.sottosuolo_combo)
        sito_layout.addRow("", sottosuolo_desc)

        self.topografia_combo = QComboBox()
        self.topografia_combo.addItems(["T1", "T2", "T3", "T4"])
        self.topografia_combo.setCurrentText("T1")
        topo_desc = QLabel("T1 = Superficie pianeggiante, pendii < 15 gradi")
        topo_desc.setStyleSheet("color: gray; font-size: 10px;")
        sito_layout.addRow("Categoria topografica:", self.topografia_combo)
        sito_layout.addRow("", topo_desc)

        layout.addWidget(grp_sito)

        # Registra campo comune come obbligatorio
        page.registerField("comune*", self.comune_edit)

        return page

    def onComuneChanged(self, text):
        """Aggiorna info quando si seleziona un comune"""
        if not SEISMIC_AVAILABLE:
            return

        comune_upper = text.upper().strip()
        if comune_upper in COMUNI_DATABASE:
            data = COMUNI_DATABASE[comune_upper]
            self.provincia_label.setText(data.get('provincia', '-'))
            self.regione_label.setText(data.get('regione', '-'))

            # Calcola ag
            try:
                analysis = SeismicAnalysis(comune=comune_upper)
                self.ag_label.setText(f"{analysis.ag_SLV:.3f} g")
                self.zona_label.setText(str(analysis.seismic_zone))
            except:
                self.ag_label.setText("-")
                self.zona_label.setText("-")
        else:
            self.provincia_label.setText("-")
            self.regione_label.setText("-")
            self.ag_label.setText("-")
            self.zona_label.setText("-")

    def creaPaginaParametriEdificio(self) -> QWizardPage:
        """Pagina 3: Parametri dell'edificio"""
        page = QWizardPage()
        page.setTitle("Parametri Edificio")
        page.setSubTitle("Definisci le caratteristiche strutturali dell'edificio")

        layout = QVBoxLayout(page)

        # Gruppo vita nominale e classe uso
        grp_vn = QGroupBox("Vita Nominale e Classe d'Uso (NTC 2018 Tab. 2.4.I/II)")
        vn_layout = QFormLayout(grp_vn)

        self.vn_spin = QDoubleSpinBox()
        self.vn_spin.setRange(10, 100)
        self.vn_spin.setValue(50)
        self.vn_spin.setSuffix(" anni")
        self.vn_spin.valueChanged.connect(self.aggiornaVR)
        vn_layout.addRow("Vita nominale VN:", self.vn_spin)

        self.classe_uso_combo = QComboBox()
        self.classe_uso_combo.addItems([
            "I - Presenza occasionale (Cu=0.7)",
            "II - Affollamento normale (Cu=1.0)",
            "III - Affollamento significativo (Cu=1.5)",
            "IV - Funzioni strategiche (Cu=2.0)"
        ])
        self.classe_uso_combo.setCurrentIndex(1)
        self.classe_uso_combo.currentIndexChanged.connect(self.aggiornaVR)
        vn_layout.addRow("Classe d'uso:", self.classe_uso_combo)

        self.vr_label = QLabel("VR = 50 anni")
        self.vr_label.setStyleSheet("font-weight: bold;")
        vn_layout.addRow("Periodo di riferimento:", self.vr_label)

        layout.addWidget(grp_vn)

        # Gruppo geometria edificio
        grp_geom = QGroupBox("Geometria Edificio")
        geom_layout = QFormLayout(grp_geom)

        self.n_piani_spin = QSpinBox()
        self.n_piani_spin.setRange(1, 10)
        self.n_piani_spin.setValue(2)
        geom_layout.addRow("Numero piani:", self.n_piani_spin)

        self.h_piano_spin = QDoubleSpinBox()
        self.h_piano_spin.setRange(2.0, 6.0)
        self.h_piano_spin.setValue(3.0)
        self.h_piano_spin.setSuffix(" m")
        self.h_piano_spin.setSingleStep(0.1)
        geom_layout.addRow("Altezza interpiano:", self.h_piano_spin)

        layout.addWidget(grp_geom)

        # Gruppo fattore di struttura
        grp_q = QGroupBox("Fattore di Struttura (NTC 2018 Tab. 7.8.I)")
        q_layout = QFormLayout(grp_q)

        self.q_spin = QDoubleSpinBox()
        self.q_spin.setRange(1.0, 3.0)
        self.q_spin.setValue(1.5)
        self.q_spin.setSingleStep(0.1)
        q_desc = QLabel("1.5 = Muratura ordinaria non armata\n2.0 = Muratura armata")
        q_desc.setStyleSheet("color: gray; font-size: 10px;")
        q_layout.addRow("Fattore q:", self.q_spin)
        q_layout.addRow("", q_desc)

        layout.addWidget(grp_q)

        return page

    def aggiornaVR(self):
        """Aggiorna il periodo di riferimento VR"""
        VN = self.vn_spin.value()
        Cu_map = {0: 0.7, 1: 1.0, 2: 1.5, 3: 2.0}
        Cu = Cu_map.get(self.classe_uso_combo.currentIndex(), 1.0)
        VR = VN * Cu
        self.vr_label.setText(f"VR = {VR:.0f} anni")

    def creaPaginaRiepilogo(self) -> QWizardPage:
        """Pagina 4: Riepilogo"""
        page = QWizardPage()
        page.setTitle("Riepilogo")
        page.setSubTitle("Verifica i dati inseriti prima di creare il progetto")

        layout = QVBoxLayout(page)

        self.riepilogo_text = QTextEdit()
        self.riepilogo_text.setReadOnly(True)
        layout.addWidget(self.riepilogo_text)

        # Aggiorna riepilogo quando si entra nella pagina
        page.initializePage = self.aggiornaRiepilogo

        return page

    def aggiornaRiepilogo(self):
        """Genera il testo del riepilogo"""
        lines = [
            "=" * 50,
            "RIEPILOGO PROGETTO",
            "=" * 50,
            "",
            f"Nome: {self.nome_edit.text()}",
            f"Progettista: {self.autore_edit.text()}",
            f"Data: {self.data_edit.text()}",
            f"Tipo intervento: {self.tipo_intervento.currentText()}",
            "",
            "LOCALIZZAZIONE:",
            f"  Comune: {self.comune_edit.text().upper()}",
            f"  Provincia: {self.provincia_label.text()}",
            f"  Regione: {self.regione_label.text()}",
            f"  ag (SLV): {self.ag_label.text()}",
            f"  Zona sismica: {self.zona_label.text()}",
            "",
            "PARAMETRI SITO:",
            f"  Categoria sottosuolo: {self.sottosuolo_combo.currentText()}",
            f"  Categoria topografica: {self.topografia_combo.currentText()}",
            "",
            "PARAMETRI EDIFICIO:",
            f"  Vita nominale: {self.vn_spin.value():.0f} anni",
            f"  Classe d'uso: {self.classe_uso_combo.currentText().split(' - ')[0]}",
            f"  {self.vr_label.text()}",
            f"  Numero piani: {self.n_piani_spin.value()}",
            f"  Altezza interpiano: {self.h_piano_spin.value():.2f} m",
            f"  Fattore di struttura q: {self.q_spin.value():.2f}",
            "",
            "=" * 50,
        ]
        self.riepilogo_text.setText("\n".join(lines))

    def getProgetto(self) -> Progetto:
        """Restituisce il progetto configurato"""
        p = Progetto()
        p.nome = self.nome_edit.text()
        p.autore = self.autore_edit.text()
        p.data = self.data_edit.text()
        p.n_piani = self.n_piani_spin.value()
        p.altezza_piano = self.h_piano_spin.value()

        # Parametri sismici
        p.sismici.comune = self.comune_edit.text().upper()
        p.sismici.provincia = self.provincia_label.text()
        p.sismici.regione = self.regione_label.text()
        p.sismici.sottosuolo = self.sottosuolo_combo.currentText()
        p.sismici.topografia = self.topografia_combo.currentText()
        p.sismici.vita_nominale = self.vn_spin.value()
        p.sismici.classe_uso = self.classe_uso_combo.currentIndex() + 1
        p.sismici.fattore_struttura = self.q_spin.value()

        # Crea piani di default
        for i in range(p.n_piani):
            p.piani.append(Piano(
                numero=i,
                quota=i * p.altezza_piano,
                altezza=p.altezza_piano
            ))

        return p


class DialogoNuovoProgetto(QDialog):
    """Dialogo semplice per creare un nuovo progetto (legacy)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuovo Progetto")
        self.setModal(True)

        layout = QFormLayout(self)

        self.nome_edit = QLineEdit("Nuovo Edificio")
        self.autore_edit = QLineEdit()

        layout.addRow("Nome progetto:", self.nome_edit)
        layout.addRow("Autore:", self.autore_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def getValues(self) -> Tuple[str, str]:
        return self.nome_edit.text(), self.autore_edit.text()


class DialogoMateriale(QDialog):
    """Dialogo per aggiungere un materiale"""

    TIPI_MURATURA = [
        "MATTONI_PIENI", "MATTONI_SEMIPIENI", "PIETRA_SQUADRATA",
        "PIETRA_IRREGOLARE", "BLOCCHI_LATERIZIO", "BLOCCHI_CLS"
    ]
    QUALITA_MALTA = ["SCADENTE", "BUONA", "OTTIME"]
    CONSERVAZIONE = ["CATTIVO", "MEDIOCRE", "BUONO", "OTTIMO"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuovo Materiale")
        self.setModal(True)

        layout = QFormLayout(self)

        self.nome_edit = QLineEdit("mattoni")
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(self.TIPI_MURATURA)
        self.malta_combo = QComboBox()
        self.malta_combo.addItems(self.QUALITA_MALTA)
        self.malta_combo.setCurrentText("BUONA")
        self.cons_combo = QComboBox()
        self.cons_combo.addItems(self.CONSERVAZIONE)
        self.cons_combo.setCurrentText("BUONO")

        layout.addRow("Nome:", self.nome_edit)
        layout.addRow("Tipo muratura:", self.tipo_combo)
        layout.addRow("Qualita' malta:", self.malta_combo)
        layout.addRow("Conservazione:", self.cons_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def getMateriale(self) -> Materiale:
        return Materiale(
            nome=self.nome_edit.text(),
            tipo=self.tipo_combo.currentText(),
            malta=self.malta_combo.currentText(),
            conservazione=self.cons_combo.currentText()
        )


class DialogoProprietaMuro(QDialog):
    """Dialogo per le proprieta' del muro corrente"""

    def __init__(self, materiali: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Proprieta' Muro")
        self.setModal(True)

        layout = QFormLayout(self)

        self.z_spin = QDoubleSpinBox()
        self.z_spin.setRange(0, 100)
        self.z_spin.setValue(0)
        self.z_spin.setSuffix(" m")

        self.altezza_spin = QDoubleSpinBox()
        self.altezza_spin.setRange(0.5, 20)
        self.altezza_spin.setValue(3.0)
        self.altezza_spin.setSuffix(" m")

        self.spessore_spin = QDoubleSpinBox()
        self.spessore_spin.setRange(0.1, 2)
        self.spessore_spin.setValue(0.45)
        self.spessore_spin.setDecimals(2)
        self.spessore_spin.setSuffix(" m")

        self.materiale_combo = QComboBox()
        self.materiale_combo.addItems(materiali if materiali else ["mattoni"])

        layout.addRow("Quota Z (base):", self.z_spin)
        layout.addRow("Altezza:", self.altezza_spin)
        layout.addRow("Spessore:", self.spessore_spin)
        layout.addRow("Materiale:", self.materiale_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def getValues(self) -> Tuple[float, float, float, str]:
        return (
            self.z_spin.value(),
            self.altezza_spin.value(),
            self.spessore_spin.value(),
            self.materiale_combo.currentText()
        )


class DialogoPlanimetria(QDialog):
    """Dialogo per impostare scala e posizione planimetria"""

    def __init__(self, piano: Piano, parent=None):
        super().__init__(parent)
        self.piano = piano
        self.setWindowTitle(f"Planimetria Piano {piano.indice}")
        self.setModal(True)
        self.filepath = piano.planimetria

        layout = QVBoxLayout(self)

        # File immagine
        file_group = QGroupBox("File Immagine")
        file_layout = QHBoxLayout(file_group)
        self.file_label = QLabel(piano.planimetria if piano.planimetria else "Nessun file")
        self.file_label.setMinimumWidth(200)
        btn_sfoglia = QPushButton("Sfoglia...")
        btn_sfoglia.clicked.connect(self.sfogliaFile)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(btn_sfoglia)
        layout.addWidget(file_group)

        # Scala e posizione
        form = QFormLayout()

        self.scala_spin = QDoubleSpinBox()
        self.scala_spin.setRange(1, 1000)
        self.scala_spin.setValue(piano.plan_scala if piano.plan_scala > 0 else 100)
        self.scala_spin.setSuffix(" px/m")
        self.scala_spin.setToolTip("Pixel dell'immagine per metro reale")
        form.addRow("Scala immagine:", self.scala_spin)

        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-1000, 1000)
        self.x_spin.setValue(piano.plan_x)
        self.x_spin.setSuffix(" m")
        form.addRow("Offset X:", self.x_spin)

        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-1000, 1000)
        self.y_spin.setValue(piano.plan_y)
        self.y_spin.setSuffix(" m")
        form.addRow("Offset Y:", self.y_spin)

        self.opacita_spin = QDoubleSpinBox()
        self.opacita_spin.setRange(0.1, 1.0)
        self.opacita_spin.setValue(piano.plan_opacita)
        self.opacita_spin.setSingleStep(0.1)
        form.addRow("Opacita':", self.opacita_spin)

        layout.addLayout(form)

        # Suggerimento scala
        hint = QLabel("Suggerimento: misura una lunghezza nota nell'immagine\n"
                     "in pixel e dividi per i metri reali")
        hint.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(hint)

        # Pulsanti
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def sfogliaFile(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Seleziona Planimetria", "",
            "Immagini (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;Tutti i file (*)"
        )
        if filepath:
            self.filepath = filepath
            self.file_label.setText(filepath.split('/')[-1].split('\\')[-1])

    def getValues(self) -> Tuple[str, float, float, float, float]:
        return (
            self.filepath,
            self.scala_spin.value(),
            self.x_spin.value(),
            self.y_spin.value(),
            self.opacita_spin.value()
        )


class DialogoSolaio(QDialog):
    """Dialogo per inserimento/modifica solaio"""

    # Database preset solai (copiato da floors.py per evitare dipendenza)
    PRESET_SOLAI = {
        'LAT_16+4': {'tipo': 'laterocemento', 'desc': 'Laterocemento 16+4', 'peso': 2.80, 'rigidezza': 'rigido'},
        'LAT_20+4': {'tipo': 'laterocemento', 'desc': 'Laterocemento 20+4', 'peso': 3.20, 'rigidezza': 'rigido'},
        'LAT_24+4': {'tipo': 'laterocemento', 'desc': 'Laterocemento 24+4', 'peso': 3.50, 'rigidezza': 'rigido'},
        'LEGNO_14x20': {'tipo': 'legno', 'desc': 'Travi legno 14x20', 'peso': 0.70, 'rigidezza': 'flessibile'},
        'LEGNO_16x24': {'tipo': 'legno', 'desc': 'Travi legno 16x24', 'peso': 0.80, 'rigidezza': 'flessibile'},
        'LEGNO_CONN': {'tipo': 'legno_connesso', 'desc': 'Legno con soletta', 'peso': 2.00, 'rigidezza': 'semi_rigido'},
        'ACCIAIO_IPE200': {'tipo': 'acciaio', 'desc': 'IPE 200 + tavelloni', 'peso': 1.80, 'rigidezza': 'flessibile'},
        'ACCIAIO_IPE240': {'tipo': 'acciaio', 'desc': 'IPE 240 + tavelloni', 'peso': 2.00, 'rigidezza': 'flessibile'},
        'CA_15': {'tipo': 'ca_pieno', 'desc': 'Soletta c.a. 15cm', 'peso': 3.75, 'rigidezza': 'rigido'},
        'CA_20': {'tipo': 'ca_pieno', 'desc': 'Soletta c.a. 20cm', 'peso': 5.00, 'rigidezza': 'rigido'},
        'VOLTA_BOTTE': {'tipo': 'volta', 'desc': 'Volta a botte', 'peso': 4.00, 'rigidezza': 'semi_rigido'},
        'VOLTA_CROCIERA': {'tipo': 'volta', 'desc': 'Volta a crociera', 'peso': 3.50, 'rigidezza': 'semi_rigido'},
    }

    # Stratigrafie tipiche
    STRATIGRAFIE = {
        'civile_standard': 1.50,      # kN/m2
        'civile_riscaldamento': 2.00,
        'terrazzo': 2.50,
        'sottotetto': 0.30,
        'nessuna': 0.0,
    }

    # Categorie uso NTC
    CATEGORIE_USO = {
        'A': ('Abitazione', 2.0),
        'B': ('Uffici', 3.0),
        'C1': ('Sale riunioni', 3.0),
        'C2': ('Cinema, teatri', 4.0),
        'C3': ('Musei, biblioteche', 5.0),
        'D1': ('Negozi', 4.0),
        'D2': ('Centri commerciali', 5.0),
        'E': ('Archivi, magazzini', 6.0),
        'H': ('Coperture non praticabili', 0.5),
    }

    def __init__(self, piani_disponibili: List[int], solaio: Optional[Solaio] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Solaio" if solaio is None else f"Modifica Solaio {solaio.nome}")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.solaio_esistente = solaio

        layout = QVBoxLayout(self)

        # ---- Gruppo Identificazione ----
        grp_id = QGroupBox("Identificazione")
        form_id = QFormLayout(grp_id)

        self.nome_edit = QLineEdit()
        self.nome_edit.setText(solaio.nome if solaio else "S1")
        form_id.addRow("Nome:", self.nome_edit)

        self.piano_combo = QComboBox()
        for p in piani_disponibili:
            self.piano_combo.addItem(f"Piano {p}", p)
        if solaio:
            idx = self.piano_combo.findData(solaio.piano)
            if idx >= 0:
                self.piano_combo.setCurrentIndex(idx)
        form_id.addRow("Piano:", self.piano_combo)

        layout.addWidget(grp_id)

        # ---- Gruppo Tipologia ----
        grp_tipo = QGroupBox("Tipologia strutturale")
        form_tipo = QFormLayout(grp_tipo)

        self.preset_combo = QComboBox()
        for key, data in self.PRESET_SOLAI.items():
            self.preset_combo.addItem(f"{key} - {data['desc']}", key)
        if solaio and solaio.preset:
            idx = self.preset_combo.findData(solaio.preset)
            if idx >= 0:
                self.preset_combo.setCurrentIndex(idx)
        self.preset_combo.currentIndexChanged.connect(self.onPresetChanged)
        form_tipo.addRow("Preset:", self.preset_combo)

        self.peso_proprio_spin = QDoubleSpinBox()
        self.peso_proprio_spin.setRange(0.1, 20.0)
        self.peso_proprio_spin.setValue(solaio.peso_proprio if solaio else 3.2)
        self.peso_proprio_spin.setSuffix(" kN/m²")
        self.peso_proprio_spin.setDecimals(2)
        form_tipo.addRow("Peso proprio G1:", self.peso_proprio_spin)

        self.rigidezza_combo = QComboBox()
        self.rigidezza_combo.addItems(["rigido", "semi_rigido", "flessibile"])
        if solaio:
            idx = self.rigidezza_combo.findText(solaio.rigidezza)
            if idx >= 0:
                self.rigidezza_combo.setCurrentIndex(idx)
        form_tipo.addRow("Rigidezza:", self.rigidezza_combo)

        layout.addWidget(grp_tipo)

        # ---- Gruppo Geometria ----
        grp_geom = QGroupBox("Geometria")
        form_geom = QFormLayout(grp_geom)

        self.luce_spin = QDoubleSpinBox()
        self.luce_spin.setRange(1.0, 20.0)
        self.luce_spin.setValue(solaio.luce if solaio else 5.0)
        self.luce_spin.setSuffix(" m")
        form_geom.addRow("Luce:", self.luce_spin)

        self.larghezza_spin = QDoubleSpinBox()
        self.larghezza_spin.setRange(1.0, 50.0)
        self.larghezza_spin.setValue(solaio.larghezza if solaio else 5.0)
        self.larghezza_spin.setSuffix(" m")
        form_geom.addRow("Larghezza:", self.larghezza_spin)

        self.orditura_spin = QDoubleSpinBox()
        self.orditura_spin.setRange(0, 180)
        self.orditura_spin.setValue(solaio.orditura if solaio else 0.0)
        self.orditura_spin.setSuffix(" °")
        self.orditura_spin.setToolTip("0° = orditura parallela a X, 90° = parallela a Y")
        form_geom.addRow("Orditura:", self.orditura_spin)

        layout.addWidget(grp_geom)

        # ---- Gruppo Carichi ----
        grp_carichi = QGroupBox("Carichi")
        form_carichi = QFormLayout(grp_carichi)

        self.stratigrafia_combo = QComboBox()
        for key, peso in self.STRATIGRAFIE.items():
            desc = key.replace('_', ' ').title()
            self.stratigrafia_combo.addItem(f"{desc} ({peso:.2f} kN/m²)", key)
        self.stratigrafia_combo.currentIndexChanged.connect(self.onStratigrafiaChanged)
        form_carichi.addRow("Stratigrafia:", self.stratigrafia_combo)

        self.peso_finiture_spin = QDoubleSpinBox()
        self.peso_finiture_spin.setRange(0.0, 10.0)
        self.peso_finiture_spin.setValue(solaio.peso_finiture if solaio else 1.5)
        self.peso_finiture_spin.setSuffix(" kN/m²")
        self.peso_finiture_spin.setDecimals(2)
        form_carichi.addRow("Peso finiture G2:", self.peso_finiture_spin)

        self.categoria_combo = QComboBox()
        for cat, (desc, qk) in self.CATEGORIE_USO.items():
            self.categoria_combo.addItem(f"{cat} - {desc} ({qk:.1f} kN/m²)", cat)
        if solaio:
            idx = self.categoria_combo.findData(solaio.categoria_uso)
            if idx >= 0:
                self.categoria_combo.setCurrentIndex(idx)
        self.categoria_combo.currentIndexChanged.connect(self.onCategoriaChanged)
        form_carichi.addRow("Categoria uso:", self.categoria_combo)

        self.qk_spin = QDoubleSpinBox()
        self.qk_spin.setRange(0.0, 20.0)
        self.qk_spin.setValue(solaio.carico_variabile if solaio else 2.0)
        self.qk_spin.setSuffix(" kN/m²")
        self.qk_spin.setDecimals(2)
        form_carichi.addRow("Carico variabile Qk:", self.qk_spin)

        layout.addWidget(grp_carichi)

        # ---- Riepilogo carichi ----
        self.lbl_riepilogo = QLabel()
        self.lbl_riepilogo.setStyleSheet("background: #f0f0f0; padding: 8px; border-radius: 4px;")
        layout.addWidget(self.lbl_riepilogo)

        # Aggiorna riepilogo
        self.aggiornaRiepilogo()

        # Connetti signals per aggiornare riepilogo
        self.peso_proprio_spin.valueChanged.connect(self.aggiornaRiepilogo)
        self.peso_finiture_spin.valueChanged.connect(self.aggiornaRiepilogo)
        self.qk_spin.valueChanged.connect(self.aggiornaRiepilogo)
        self.luce_spin.valueChanged.connect(self.aggiornaRiepilogo)
        self.larghezza_spin.valueChanged.connect(self.aggiornaRiepilogo)

        # ---- Pulsanti ----
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def onPresetChanged(self, index):
        """Aggiorna valori quando cambia il preset"""
        preset_key = self.preset_combo.currentData()
        if preset_key in self.PRESET_SOLAI:
            data = self.PRESET_SOLAI[preset_key]
            self.peso_proprio_spin.setValue(data['peso'])
            idx = self.rigidezza_combo.findText(data['rigidezza'])
            if idx >= 0:
                self.rigidezza_combo.setCurrentIndex(idx)

    def onStratigrafiaChanged(self, index):
        """Aggiorna peso finiture quando cambia stratigrafia"""
        key = self.stratigrafia_combo.currentData()
        if key in self.STRATIGRAFIE:
            self.peso_finiture_spin.setValue(self.STRATIGRAFIE[key])

    def onCategoriaChanged(self, index):
        """Aggiorna Qk quando cambia categoria"""
        cat = self.categoria_combo.currentData()
        if cat in self.CATEGORIE_USO:
            _, qk = self.CATEGORIE_USO[cat]
            self.qk_spin.setValue(qk)

    def aggiornaRiepilogo(self):
        """Aggiorna il riepilogo carichi"""
        G1 = self.peso_proprio_spin.value()
        G2 = self.peso_finiture_spin.value()
        Qk = self.qk_spin.value()
        Gk = G1 + G2
        totale = Gk + Qk

        # Calcoli combinazioni
        SLU = 1.3 * G1 + 1.5 * G2 + 1.5 * Qk
        area = self.luce_spin.value() * self.larghezza_spin.value()

        self.lbl_riepilogo.setText(
            f"<b>Riepilogo Carichi:</b><br>"
            f"G1 = {G1:.2f} kN/m² | G2 = {G2:.2f} kN/m² | Qk = {Qk:.2f} kN/m²<br>"
            f"Totale caratteristico: <b>{totale:.2f} kN/m²</b><br>"
            f"Combinazione SLU: <b>{SLU:.2f} kN/m²</b><br>"
            f"Area: {area:.1f} m² | Carico totale: {totale * area:.1f} kN"
        )

    def getSolaio(self) -> Solaio:
        """Restituisce l'oggetto Solaio con i dati inseriti"""
        preset_key = self.preset_combo.currentData()
        tipo = self.PRESET_SOLAI[preset_key]['tipo'] if preset_key in self.PRESET_SOLAI else 'laterocemento'

        return Solaio(
            nome=self.nome_edit.text() or "S1",
            piano=self.piano_combo.currentData() or 0,
            tipo=tipo,
            preset=preset_key or "LAT_20+4",
            luce=self.luce_spin.value(),
            larghezza=self.larghezza_spin.value(),
            orditura=self.orditura_spin.value(),
            peso_proprio=self.peso_proprio_spin.value(),
            peso_finiture=self.peso_finiture_spin.value(),
            carico_variabile=self.qk_spin.value(),
            categoria_uso=self.categoria_combo.currentData() or "A",
            rigidezza=self.rigidezza_combo.currentText(),
        )


class DialogoCarichiClimatici(QDialog):
    """Dialogo per configurare i carichi neve e vento"""

    ZONE_NEVE = {
        'I-Alpina': 'Zona I Alpina (Nord montano)',
        'I-Med': 'Zona I Mediterranea (Pianura Padana)',
        'II': 'Zona II (Centro Italia)',
        'III': 'Zona III (Sud e isole)',
    }

    ESPOSIZIONI_NEVE = {
        'battuta_venti': 'Battuta dai venti (CE=0.9)',
        'normale': 'Normale (CE=1.0)',
        'riparata': 'Riparata (CE=1.1)',
    }

    CATEGORIE_VENTO = {
        1: 'I - Mare aperto, costa piatta',
        2: 'II - Area agricola',
        3: 'III - Area suburbana/industriale',
        4: 'IV - Area urbana (edifici >15m)',
        5: 'V - Centro citta (>15%)',
    }

    def __init__(self, provincia: str = "", altitudine: float = 100.0,
                 altezza_edificio: float = 9.0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Carichi Climatici (NTC 2018)")
        self.setModal(True)
        self.setMinimumWidth(550)

        self.provincia = provincia
        self.altitudine = altitudine
        self.altezza_edificio = altezza_edificio

        layout = QVBoxLayout(self)

        # ---- Dati localita' ----
        grp_loc = QGroupBox("Localizzazione")
        form_loc = QFormLayout(grp_loc)

        self.provincia_edit = QLineEdit(provincia)
        self.provincia_edit.textChanged.connect(self.onProvinciaChanged)
        form_loc.addRow("Provincia:", self.provincia_edit)

        self.altitudine_spin = QDoubleSpinBox()
        self.altitudine_spin.setRange(0, 3000)
        self.altitudine_spin.setValue(altitudine)
        self.altitudine_spin.setSuffix(" m s.l.m.")
        self.altitudine_spin.valueChanged.connect(self.ricalcola)
        form_loc.addRow("Altitudine:", self.altitudine_spin)

        self.altezza_spin = QDoubleSpinBox()
        self.altezza_spin.setRange(3, 100)
        self.altezza_spin.setValue(altezza_edificio)
        self.altezza_spin.setSuffix(" m")
        self.altezza_spin.valueChanged.connect(self.ricalcola)
        form_loc.addRow("Altezza edificio:", self.altezza_spin)

        layout.addWidget(grp_loc)

        # ---- Carico Neve ----
        grp_neve = QGroupBox("Carico Neve")
        form_neve = QFormLayout(grp_neve)

        self.zona_neve_combo = QComboBox()
        for key, desc in self.ZONE_NEVE.items():
            self.zona_neve_combo.addItem(desc, key)
        self.zona_neve_combo.currentIndexChanged.connect(self.ricalcola)
        form_neve.addRow("Zona neve:", self.zona_neve_combo)

        self.esp_neve_combo = QComboBox()
        for key, desc in self.ESPOSIZIONI_NEVE.items():
            self.esp_neve_combo.addItem(desc, key)
        self.esp_neve_combo.setCurrentIndex(1)  # normale
        self.esp_neve_combo.currentIndexChanged.connect(self.ricalcola)
        form_neve.addRow("Esposizione:", self.esp_neve_combo)

        self.pendenza_spin = QDoubleSpinBox()
        self.pendenza_spin.setRange(0, 60)
        self.pendenza_spin.setValue(0)
        self.pendenza_spin.setSuffix(" °")
        self.pendenza_spin.valueChanged.connect(self.ricalcola)
        form_neve.addRow("Pendenza copertura:", self.pendenza_spin)

        self.lbl_neve = QLabel()
        self.lbl_neve.setStyleSheet("font-weight: bold; color: #0066cc;")
        form_neve.addRow("Carico neve qs:", self.lbl_neve)

        layout.addWidget(grp_neve)

        # ---- Carico Vento ----
        grp_vento = QGroupBox("Carico Vento")
        form_vento = QFormLayout(grp_vento)

        self.zona_vento_spin = QSpinBox()
        self.zona_vento_spin.setRange(1, 9)
        self.zona_vento_spin.setValue(3)
        self.zona_vento_spin.valueChanged.connect(self.ricalcola)
        form_vento.addRow("Zona vento:", self.zona_vento_spin)

        self.cat_esp_combo = QComboBox()
        for key, desc in self.CATEGORIE_VENTO.items():
            self.cat_esp_combo.addItem(desc, key)
        self.cat_esp_combo.setCurrentIndex(2)  # cat III
        self.cat_esp_combo.currentIndexChanged.connect(self.ricalcola)
        form_vento.addRow("Categoria esposizione:", self.cat_esp_combo)

        self.lbl_vento = QLabel()
        self.lbl_vento.setStyleSheet("font-weight: bold; color: #cc6600;")
        form_vento.addRow("Pressione vento p:", self.lbl_vento)

        layout.addWidget(grp_vento)

        # ---- Riepilogo ----
        self.lbl_riepilogo = QLabel()
        self.lbl_riepilogo.setStyleSheet(
            "background: #f5f5f5; padding: 10px; border-radius: 4px; font-family: monospace;"
        )
        self.lbl_riepilogo.setWordWrap(True)
        layout.addWidget(self.lbl_riepilogo)

        # ---- Pulsanti ----
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Auto-detect zone da provincia
        self.onProvinciaChanged(provincia)
        self.ricalcola()

    def onProvinciaChanged(self, provincia: str):
        """Auto-detect zone da provincia"""
        if not LOADS_AVAILABLE:
            return

        zones = get_zones_by_province(provincia)
        if zones:
            snow_zone, wind_zone = zones
            # Imposta zona neve
            zona_neve_str = snow_zone.value
            idx = self.zona_neve_combo.findData(zona_neve_str)
            if idx >= 0:
                self.zona_neve_combo.setCurrentIndex(idx)
            # Imposta zona vento
            self.zona_vento_spin.setValue(wind_zone.zone_num)

    def ricalcola(self):
        """Ricalcola i carichi"""
        if not LOADS_AVAILABLE:
            self.lbl_neve.setText("Modulo loads non disponibile")
            self.lbl_vento.setText("Modulo loads non disponibile")
            return

        try:
            # Parametri neve
            zona_neve_str = self.zona_neve_combo.currentData()
            zona_neve_map = {
                'I-Alpina': SnowZone.I_ALPINA,
                'I-Med': SnowZone.I_MEDITERRANEA,
                'II': SnowZone.II,
                'III': SnowZone.III,
            }
            zona_neve = zona_neve_map.get(zona_neve_str, SnowZone.II)

            esp_neve_str = self.esp_neve_combo.currentData()
            esp_neve_map = {
                'battuta_venti': SnowExposure.BATTUTA_VENTI,
                'normale': SnowExposure.NORMALE,
                'riparata': SnowExposure.RIPARATA,
            }
            esp_neve = esp_neve_map.get(esp_neve_str, SnowExposure.NORMALE)

            snow = SnowLoad(
                zone=zona_neve,
                altitude=self.altitudine_spin.value(),
                exposure=esp_neve,
                roof_slope=self.pendenza_spin.value()
            )

            self.lbl_neve.setText(f"{snow.qs:.2f} kN/m² (qsk={snow.qsk:.2f})")
            self.snow_result = snow

            # Parametri vento
            zona_vento_num = self.zona_vento_spin.value()
            zona_vento_map = {
                1: WindZone.ZONE_1, 2: WindZone.ZONE_2, 3: WindZone.ZONE_3,
                4: WindZone.ZONE_4, 5: WindZone.ZONE_5, 6: WindZone.ZONE_6,
                7: WindZone.ZONE_7, 8: WindZone.ZONE_8, 9: WindZone.ZONE_9,
            }
            zona_vento = zona_vento_map.get(zona_vento_num, WindZone.ZONE_3)

            cat_esp_num = self.cat_esp_combo.currentData()
            cat_esp_map = {
                1: ExposureCategory.I, 2: ExposureCategory.II,
                3: ExposureCategory.III, 4: ExposureCategory.IV,
                5: ExposureCategory.V,
            }
            cat_esp = cat_esp_map.get(cat_esp_num, ExposureCategory.III)

            wind = WindLoad(
                zone=zona_vento,
                altitude=self.altitudine_spin.value(),
                building_height=self.altezza_spin.value(),
                exposure=cat_esp
            )

            self.lbl_vento.setText(f"{wind.p:.3f} kN/m² (vb={wind.vb:.1f} m/s)")
            self.wind_result = wind

            # Riepilogo
            self.lbl_riepilogo.setText(
                f"Altitudine: {self.altitudine_spin.value():.0f} m s.l.m.\n"
                f"Altezza edificio: {self.altezza_spin.value():.1f} m\n\n"
                f"NEVE:\n"
                f"  Zona: {zona_neve_str} | qsk = {snow.qsk:.2f} kN/m²\n"
                f"  CE = {snow.CE:.1f} | mu = {snow.mu:.2f}\n"
                f"  qs = {snow.qs:.2f} kN/m²\n\n"
                f"VENTO:\n"
                f"  Zona: {zona_vento_num} | vb = {wind.vb:.1f} m/s\n"
                f"  qb = {wind.qb:.3f} kN/m² | ce = {wind.ce:.2f}\n"
                f"  p = {wind.p:.3f} kN/m²"
            )

        except Exception as e:
            self.lbl_riepilogo.setText(f"Errore: {e}")

    def getCarichiClimatici(self) -> CarichiClimatici:
        """Restituisce l'oggetto CarichiClimatici"""
        return CarichiClimatici(
            zona_neve=self.zona_neve_combo.currentData() or "II",
            qsk=self.snow_result.qsk if hasattr(self, 'snow_result') else 1.0,
            qs=self.snow_result.qs if hasattr(self, 'snow_result') else 0.8,
            esposizione_neve=self.esp_neve_combo.currentData() or "normale",
            zona_vento=self.zona_vento_spin.value(),
            vb=self.wind_result.vb if hasattr(self, 'wind_result') else 27.0,
            qb=self.wind_result.qb if hasattr(self, 'wind_result') else 0.45,
            p_vento=self.wind_result.p if hasattr(self, 'wind_result') else 1.0,
            categoria_esposizione=self.cat_esp_combo.currentData() or 3,
        )


# ============================================================================
# PANNELLO LATERALE
# ============================================================================

class PannelloProprietà(QWidget):
    """Pannello laterale con tabelle e proprieta'"""

    def __init__(self):
        super().__init__()
        self.progetto: Optional[Progetto] = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Tabs
        self.tabs = QTabWidget()

        # Tab Muri
        self.tab_muri = QWidget()
        layout_muri = QVBoxLayout(self.tab_muri)
        self.tabella_muri = QTableWidget()
        self.tabella_muri.setColumnCount(8)
        self.tabella_muri.setHorizontalHeaderLabels([
            "Nome", "X1", "Y1", "X2", "Y2", "Z", "Alt", "Spess"
        ])
        self.tabella_muri.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout_muri.addWidget(self.tabella_muri)
        self.tabs.addTab(self.tab_muri, "Muri")

        # Tab Aperture
        self.tab_aperture = QWidget()
        layout_aperture = QVBoxLayout(self.tab_aperture)
        self.tabella_aperture = QTableWidget()
        self.tabella_aperture.setColumnCount(6)
        self.tabella_aperture.setHorizontalHeaderLabels([
            "Muro", "Tipo", "Larg", "Alt", "Dist", "Quota"
        ])
        self.tabella_aperture.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout_aperture.addWidget(self.tabella_aperture)

        btn_add_apertura = QPushButton("+ Aggiungi Apertura")
        btn_add_apertura.clicked.connect(self.aggiungiApertura)
        layout_aperture.addWidget(btn_add_apertura)

        self.tabs.addTab(self.tab_aperture, "Aperture")

        # Tab Materiali
        self.tab_materiali = QWidget()
        layout_materiali = QVBoxLayout(self.tab_materiali)
        self.tabella_materiali = QTableWidget()
        self.tabella_materiali.setColumnCount(4)
        self.tabella_materiali.setHorizontalHeaderLabels([
            "Nome", "Tipo", "Malta", "Conserv"
        ])
        self.tabella_materiali.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout_materiali.addWidget(self.tabella_materiali)

        btn_add_mat = QPushButton("+ Aggiungi Materiale")
        btn_add_mat.clicked.connect(self.aggiungiMateriale)
        layout_materiali.addWidget(btn_add_mat)

        self.tabs.addTab(self.tab_materiali, "Materiali")

        # Tab Piani
        self.tab_piani = QWidget()
        layout_piani = QVBoxLayout(self.tab_piani)
        self.tabella_piani = QTableWidget()
        self.tabella_piani.setColumnCount(4)
        self.tabella_piani.setHorizontalHeaderLabels([
            "Piano", "Quota Z", "Altezza", "Massa (kg)"
        ])
        self.tabella_piani.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout_piani.addWidget(self.tabella_piani)

        btn_add_piano = QPushButton("+ Aggiungi Piano")
        btn_add_piano.clicked.connect(self.aggiungiPiano)
        layout_piani.addWidget(btn_add_piano)

        self.tabs.addTab(self.tab_piani, "Piani")

        # Tab Carichi
        self.tab_carichi = QWidget()
        layout_carichi = QVBoxLayout(self.tab_carichi)
        self.tabella_carichi = QTableWidget()
        self.tabella_carichi.setColumnCount(4)
        self.tabella_carichi.setHorizontalHeaderLabels([
            "Piano", "Perm (kN/m²)", "Var (kN/m²)", "Copertura"
        ])
        self.tabella_carichi.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout_carichi.addWidget(self.tabella_carichi)

        btn_add_carico = QPushButton("+ Aggiungi Carico")
        btn_add_carico.clicked.connect(self.aggiungiCarico)
        layout_carichi.addWidget(btn_add_carico)

        self.tabs.addTab(self.tab_carichi, "Carichi")

        # Tab Cordoli
        self.tab_cordoli = QWidget()
        layout_cordoli = QVBoxLayout(self.tab_cordoli)
        self.tabella_cordoli = QTableWidget()
        self.tabella_cordoli.setColumnCount(7)
        self.tabella_cordoli.setHorizontalHeaderLabels([
            "Nome", "Piano", "Base (m)", "Altezza (m)", "Materiale", "Tipo", "L (m)"
        ])
        self.tabella_cordoli.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout_cordoli.addWidget(self.tabella_cordoli)

        btn_layout_cordoli = QHBoxLayout()
        btn_add_cordolo = QPushButton("+ Cordolo Perimetrale")
        btn_add_cordolo.clicked.connect(self.aggiungiCordolo)
        btn_layout_cordoli.addWidget(btn_add_cordolo)

        btn_add_cordolo_linea = QPushButton("+ Cordolo Lineare")
        btn_add_cordolo_linea.clicked.connect(self.aggiungiCordoloLinea)
        btn_layout_cordoli.addWidget(btn_add_cordolo_linea)

        btn_del_cordolo = QPushButton("- Rimuovi")
        btn_del_cordolo.clicked.connect(self.rimuoviCordolo)
        btn_layout_cordoli.addWidget(btn_del_cordolo)

        layout_cordoli.addLayout(btn_layout_cordoli)

        self.tabs.addTab(self.tab_cordoli, "Cordoli")

        # Tab Solai
        self.tab_solai = QWidget()
        layout_solai = QVBoxLayout(self.tab_solai)
        self.tabella_solai = QTableWidget()
        self.tabella_solai.setColumnCount(8)
        self.tabella_solai.setHorizontalHeaderLabels([
            "Nome", "Piano", "Tipo", "Luce", "Larg", "G1+G2", "Qk", "Rigidezza"
        ])
        self.tabella_solai.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabella_solai.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabella_solai.doubleClicked.connect(self.modificaSolaio)
        layout_solai.addWidget(self.tabella_solai)

        btn_layout_solai = QHBoxLayout()
        btn_add_solaio = QPushButton("+ Aggiungi Solaio")
        btn_add_solaio.clicked.connect(self.aggiungiSolaio)
        btn_layout_solai.addWidget(btn_add_solaio)

        btn_mod_solaio = QPushButton("Modifica")
        btn_mod_solaio.clicked.connect(self.modificaSolaio)
        btn_layout_solai.addWidget(btn_mod_solaio)

        btn_del_solaio = QPushButton("- Rimuovi")
        btn_del_solaio.clicked.connect(self.rimuoviSolaio)
        btn_layout_solai.addWidget(btn_del_solaio)

        layout_solai.addLayout(btn_layout_solai)

        self.tabs.addTab(self.tab_solai, "Solai")

        layout.addWidget(self.tabs)

    def setProgetto(self, progetto: Progetto):
        self.progetto = progetto
        self.aggiornaTutto()

    def aggiornaTutto(self):
        self.aggiornaTabelllaMuri()
        self.aggiornaTabelllaAperture()
        self.aggiornaTabellaMateriali()
        self.aggiornaTabelllaPiani()
        self.aggiornaTabelllaCarichi()
        self.aggiornaTabelllaCordoli()
        self.aggiornaTabellaSolai()

    def aggiornaTabelllaMuri(self):
        if not self.progetto:
            return

        self.tabella_muri.setRowCount(len(self.progetto.muri))
        for i, muro in enumerate(self.progetto.muri):
            self.tabella_muri.setItem(i, 0, QTableWidgetItem(muro.nome))
            self.tabella_muri.setItem(i, 1, QTableWidgetItem(f"{muro.x1:.2f}"))
            self.tabella_muri.setItem(i, 2, QTableWidgetItem(f"{muro.y1:.2f}"))
            self.tabella_muri.setItem(i, 3, QTableWidgetItem(f"{muro.x2:.2f}"))
            self.tabella_muri.setItem(i, 4, QTableWidgetItem(f"{muro.y2:.2f}"))
            self.tabella_muri.setItem(i, 5, QTableWidgetItem(f"{muro.z:.1f}"))
            self.tabella_muri.setItem(i, 6, QTableWidgetItem(f"{muro.altezza:.1f}"))
            self.tabella_muri.setItem(i, 7, QTableWidgetItem(f"{muro.spessore:.2f}"))

    def aggiornaTabelllaAperture(self):
        if not self.progetto:
            return

        self.tabella_aperture.setRowCount(len(self.progetto.aperture))
        for i, ap in enumerate(self.progetto.aperture):
            self.tabella_aperture.setItem(i, 0, QTableWidgetItem(ap.muro))
            self.tabella_aperture.setItem(i, 1, QTableWidgetItem(ap.tipo))
            self.tabella_aperture.setItem(i, 2, QTableWidgetItem(f"{ap.larghezza:.2f}"))
            self.tabella_aperture.setItem(i, 3, QTableWidgetItem(f"{ap.altezza:.2f}"))
            self.tabella_aperture.setItem(i, 4, QTableWidgetItem(f"{ap.distanza:.2f}"))
            self.tabella_aperture.setItem(i, 5, QTableWidgetItem(f"{ap.quota:.2f}"))

    def aggiornaTabellaMateriali(self):
        if not self.progetto:
            return

        self.tabella_materiali.setRowCount(len(self.progetto.materiali))
        for i, mat in enumerate(self.progetto.materiali):
            self.tabella_materiali.setItem(i, 0, QTableWidgetItem(mat.nome))
            self.tabella_materiali.setItem(i, 1, QTableWidgetItem(mat.tipo))
            self.tabella_materiali.setItem(i, 2, QTableWidgetItem(mat.malta))
            self.tabella_materiali.setItem(i, 3, QTableWidgetItem(mat.conservazione))

    def aggiungiMateriale(self):
        dialogo = DialogoMateriale(self)
        if dialogo.exec_() == QDialog.Accepted:
            mat = dialogo.getMateriale()
            self.progetto.materiali.append(mat)
            self.aggiornaTabellaMateriali()

    def aggiungiApertura(self):
        if not self.progetto or not self.progetto.muri:
            QMessageBox.warning(self, "Errore", "Devi prima creare almeno un muro")
            return

        # Dialogo semplificato per apertura
        muro_nome, ok = QInputDialog.getItem(
            self, "Seleziona Muro", "Muro:",
            [m.nome for m in self.progetto.muri], 0, False
        )
        if not ok:
            return

        tipo, ok = QInputDialog.getItem(
            self, "Tipo Apertura", "Tipo:",
            ["finestra", "porta"], 0, False
        )
        if not ok:
            return

        larghezza, ok = QInputDialog.getDouble(
            self, "Larghezza", "Larghezza (m):", 1.2, 0.3, 5.0, 2
        )
        if not ok:
            return

        altezza, ok = QInputDialog.getDouble(
            self, "Altezza", "Altezza (m):", 1.4, 0.3, 3.0, 2
        )
        if not ok:
            return

        distanza, ok = QInputDialog.getDouble(
            self, "Distanza", "Distanza da inizio muro (m):", 2.0, 0, 20, 2
        )
        if not ok:
            return

        quota = 0.9 if tipo == "finestra" else 0.0

        apertura = Apertura(
            muro=muro_nome,
            tipo=tipo,
            larghezza=larghezza,
            altezza=altezza,
            distanza=distanza,
            quota=quota
        )
        self.progetto.aperture.append(apertura)
        self.aggiornaTabelllaAperture()

    def aggiornaTabelllaPiani(self):
        if not self.progetto:
            return

        self.tabella_piani.setRowCount(len(self.progetto.piani))
        for i, piano in enumerate(self.progetto.piani):
            self.tabella_piani.setItem(i, 0, QTableWidgetItem(str(piano.indice)))
            self.tabella_piani.setItem(i, 1, QTableWidgetItem(f"{piano.quota:.2f}"))
            self.tabella_piani.setItem(i, 2, QTableWidgetItem(f"{piano.altezza:.2f}"))
            self.tabella_piani.setItem(i, 3, QTableWidgetItem(f"{piano.massa:.0f}"))

    def aggiornaTabelllaCarichi(self):
        if not self.progetto:
            return

        self.tabella_carichi.setRowCount(len(self.progetto.carichi))
        for i, carico in enumerate(self.progetto.carichi):
            self.tabella_carichi.setItem(i, 0, QTableWidgetItem(str(carico.piano)))
            self.tabella_carichi.setItem(i, 1, QTableWidgetItem(f"{carico.permanente:.1f}"))
            self.tabella_carichi.setItem(i, 2, QTableWidgetItem(f"{carico.variabile:.1f}"))
            self.tabella_carichi.setItem(i, 3, QTableWidgetItem("Si" if carico.copertura else "No"))

    def aggiornaTabelllaCordoli(self):
        if not self.progetto:
            return

        self.tabella_cordoli.setRowCount(len(self.progetto.cordoli))
        for i, cordolo in enumerate(self.progetto.cordoli):
            self.tabella_cordoli.setItem(i, 0, QTableWidgetItem(cordolo.nome))
            self.tabella_cordoli.setItem(i, 1, QTableWidgetItem(str(cordolo.piano)))
            self.tabella_cordoli.setItem(i, 2, QTableWidgetItem(f"{cordolo.base:.2f}"))
            self.tabella_cordoli.setItem(i, 3, QTableWidgetItem(f"{cordolo.altezza:.2f}"))
            self.tabella_cordoli.setItem(i, 4, QTableWidgetItem(cordolo.materiale))
            tipo = "Perimetrale" if cordolo.is_perimetrale else "Lineare"
            self.tabella_cordoli.setItem(i, 5, QTableWidgetItem(tipo))
            lunghezza = cordolo.lunghezza if not cordolo.is_perimetrale else 0.0
            self.tabella_cordoli.setItem(i, 6, QTableWidgetItem(f"{lunghezza:.2f}"))

    def aggiungiCordolo(self):
        """Aggiunge un cordolo perimetrale"""
        if not self.progetto:
            return

        # Seleziona piano
        piani_disponibili = [str(p.indice) for p in self.progetto.piani]
        if not piani_disponibili:
            piani_disponibili = ["0", "1", "2"]

        piano_str, ok = QInputDialog.getItem(
            self, "Piano", "Seleziona piano:",
            piani_disponibili, 0, False
        )
        if not ok:
            return

        nome, ok = QInputDialog.getText(
            self, "Nome Cordolo", "Nome:",
            text=f"C{piano_str}"
        )
        if not ok or not nome:
            return

        base, ok = QInputDialog.getDouble(
            self, "Base", "Base sezione (m):",
            0.30, 0.10, 1.0, 2
        )
        if not ok:
            return

        altezza, ok = QInputDialog.getDouble(
            self, "Altezza", "Altezza sezione (m):",
            0.25, 0.10, 1.0, 2
        )
        if not ok:
            return

        materiali = ["calcestruzzo", "acciaio", "legno"]
        materiale, ok = QInputDialog.getItem(
            self, "Materiale", "Materiale cordolo:",
            materiali, 0, False
        )
        if not ok:
            return

        cordolo = Cordolo(
            nome=nome,
            piano=int(piano_str),
            base=base,
            altezza=altezza,
            materiale=materiale
        )
        self.progetto.cordoli.append(cordolo)
        self.aggiornaTabelllaCordoli()

    def aggiungiCordoloLinea(self):
        """Aggiunge un cordolo con coordinate specifiche"""
        if not self.progetto:
            return

        # Seleziona piano
        piani_disponibili = [str(p.indice) for p in self.progetto.piani]
        if not piani_disponibili:
            piani_disponibili = ["0", "1", "2"]

        piano_str, ok = QInputDialog.getItem(
            self, "Piano", "Seleziona piano:",
            piani_disponibili, 0, False
        )
        if not ok:
            return

        nome, ok = QInputDialog.getText(
            self, "Nome Cordolo", "Nome:",
            text=f"CL{piano_str}"
        )
        if not ok or not nome:
            return

        # Coordinate
        x1, ok = QInputDialog.getDouble(self, "X1", "X1 (m):", 0.0, -100, 100, 2)
        if not ok:
            return
        y1, ok = QInputDialog.getDouble(self, "Y1", "Y1 (m):", 0.0, -100, 100, 2)
        if not ok:
            return
        x2, ok = QInputDialog.getDouble(self, "X2", "X2 (m):", 5.0, -100, 100, 2)
        if not ok:
            return
        y2, ok = QInputDialog.getDouble(self, "Y2", "Y2 (m):", 0.0, -100, 100, 2)
        if not ok:
            return

        base, ok = QInputDialog.getDouble(
            self, "Base", "Base sezione (m):",
            0.30, 0.10, 1.0, 2
        )
        if not ok:
            return

        altezza, ok = QInputDialog.getDouble(
            self, "Altezza", "Altezza sezione (m):",
            0.25, 0.10, 1.0, 2
        )
        if not ok:
            return

        materiali = ["calcestruzzo", "acciaio", "legno"]
        materiale, ok = QInputDialog.getItem(
            self, "Materiale", "Materiale cordolo:",
            materiali, 0, False
        )
        if not ok:
            return

        cordolo = Cordolo(
            nome=nome,
            piano=int(piano_str),
            base=base,
            altezza=altezza,
            materiale=materiale,
            x1=x1, y1=y1, x2=x2, y2=y2
        )
        self.progetto.cordoli.append(cordolo)
        self.aggiornaTabelllaCordoli()

    def rimuoviCordolo(self):
        """Rimuove il cordolo selezionato"""
        if not self.progetto:
            return

        row = self.tabella_cordoli.currentRow()
        if row >= 0 and row < len(self.progetto.cordoli):
            del self.progetto.cordoli[row]
            self.aggiornaTabelllaCordoli()

    def aggiungiPiano(self):
        if not self.progetto:
            return

        # Calcola prossimo indice e quota
        if self.progetto.piani:
            ultimo = max(self.progetto.piani, key=lambda p: p.indice)
            nuovo_indice = ultimo.indice + 1
            nuova_quota = ultimo.quota + ultimo.altezza
        else:
            nuovo_indice = 0
            nuova_quota = 0.0

        # Dialogo per piano
        indice, ok = QInputDialog.getInt(
            self, "Indice Piano", "Numero piano:",
            nuovo_indice, 0, 20
        )
        if not ok:
            return

        quota, ok = QInputDialog.getDouble(
            self, "Quota", "Quota Z (m):",
            nuova_quota, 0, 100, 2
        )
        if not ok:
            return

        altezza, ok = QInputDialog.getDouble(
            self, "Altezza", "Altezza interpiano (m):",
            3.0, 1.0, 10.0, 2
        )
        if not ok:
            return

        massa, ok = QInputDialog.getDouble(
            self, "Massa", "Massa piano (kg):",
            10000, 0, 1000000, 0
        )
        if not ok:
            return

        piano = Piano(
            indice=indice,
            quota=quota,
            altezza=altezza,
            massa=massa
        )
        self.progetto.piani.append(piano)
        self.progetto.piani.sort(key=lambda p: p.indice)
        self.aggiornaTabelllaPiani()

    def aggiungiCarico(self):
        if not self.progetto:
            return

        # Seleziona piano
        piani_disponibili = [str(p.indice) for p in self.progetto.piani]
        if not piani_disponibili:
            # Se non ci sono piani, usa indici generici
            piani_disponibili = ["0", "1", "2"]

        piano_str, ok = QInputDialog.getItem(
            self, "Piano", "Seleziona piano:",
            piani_disponibili, 0, False
        )
        if not ok:
            return

        permanente, ok = QInputDialog.getDouble(
            self, "Carico Permanente", "G (kN/m²):",
            5.0, 0, 50, 1
        )
        if not ok:
            return

        variabile, ok = QInputDialog.getDouble(
            self, "Carico Variabile", "Q (kN/m²):",
            2.0, 0, 20, 1
        )
        if not ok:
            return

        copertura, ok = QInputDialog.getItem(
            self, "Tipo", "E' copertura?",
            ["No", "Si"], 0, False
        )
        if not ok:
            return

        carico = Carico(
            piano=int(piano_str),
            permanente=permanente,
            variabile=variabile,
            copertura=(copertura == "Si")
        )
        self.progetto.carichi.append(carico)
        self.aggiornaTabelllaCarichi()

    # ---------- SOLAI ----------

    def aggiornaTabellaSolai(self):
        """Aggiorna la tabella dei solai"""
        if not self.progetto:
            return

        self.tabella_solai.setRowCount(len(self.progetto.solai))
        for i, solaio in enumerate(self.progetto.solai):
            self.tabella_solai.setItem(i, 0, QTableWidgetItem(solaio.nome))
            self.tabella_solai.setItem(i, 1, QTableWidgetItem(str(solaio.piano)))
            self.tabella_solai.setItem(i, 2, QTableWidgetItem(solaio.tipo))
            self.tabella_solai.setItem(i, 3, QTableWidgetItem(f"{solaio.luce:.1f}"))
            self.tabella_solai.setItem(i, 4, QTableWidgetItem(f"{solaio.larghezza:.1f}"))
            Gk = solaio.Gk
            self.tabella_solai.setItem(i, 5, QTableWidgetItem(f"{Gk:.2f}"))
            self.tabella_solai.setItem(i, 6, QTableWidgetItem(f"{solaio.Qk:.2f}"))
            self.tabella_solai.setItem(i, 7, QTableWidgetItem(solaio.rigidezza))

    def aggiungiSolaio(self):
        """Apre il dialogo per aggiungere un nuovo solaio"""
        if not self.progetto:
            return

        # Determina piani disponibili
        if self.progetto.piani:
            piani = [p.indice for p in self.progetto.piani]
        else:
            piani = list(range(self.progetto.n_piani + 1))

        # Genera nome automatico
        n_solai = len(self.progetto.solai)
        nome_default = f"S{n_solai + 1}"

        dialogo = DialogoSolaio(piani, parent=self)

        if dialogo.exec_() == QDialog.Accepted:
            solaio = dialogo.getSolaio()
            # Verifica nome univoco
            nomi_esistenti = [s.nome for s in self.progetto.solai]
            if solaio.nome in nomi_esistenti:
                # Aggiungi suffisso
                base = solaio.nome
                i = 2
                while f"{base}_{i}" in nomi_esistenti:
                    i += 1
                solaio.nome = f"{base}_{i}"

            self.progetto.solai.append(solaio)
            self.aggiornaTabellaSolai()

    def modificaSolaio(self):
        """Apre il dialogo per modificare il solaio selezionato"""
        if not self.progetto:
            return

        row = self.tabella_solai.currentRow()
        if row < 0 or row >= len(self.progetto.solai):
            QMessageBox.information(self, "Info", "Seleziona un solaio dalla tabella")
            return

        solaio = self.progetto.solai[row]

        # Determina piani disponibili
        if self.progetto.piani:
            piani = [p.indice for p in self.progetto.piani]
        else:
            piani = list(range(self.progetto.n_piani + 1))

        dialogo = DialogoSolaio(piani, solaio=solaio, parent=self)

        if dialogo.exec_() == QDialog.Accepted:
            nuovo_solaio = dialogo.getSolaio()
            self.progetto.solai[row] = nuovo_solaio
            self.aggiornaTabellaSolai()

    def rimuoviSolaio(self):
        """Rimuove il solaio selezionato"""
        if not self.progetto:
            return

        row = self.tabella_solai.currentRow()
        if row < 0 or row >= len(self.progetto.solai):
            QMessageBox.information(self, "Info", "Seleziona un solaio dalla tabella")
            return

        solaio = self.progetto.solai[row]
        reply = QMessageBox.question(
            self, "Conferma",
            f"Rimuovere il solaio '{solaio.nome}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            del self.progetto.solai[row]
            self.aggiornaTabellaSolai()


# ============================================================================
# VISTA 3D
# ============================================================================

class Vista3DWidget(QWidget):
    """Widget per visualizzazione 3D isometrica dell'edificio"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.progetto: Optional[Progetto] = None
        self.setMinimumSize(400, 400)
        self.setStyleSheet("background-color: white;")

        # Parametri vista
        self.angolo = 30  # Angolo rotazione orizzontale (gradi)
        self.inclinazione = 30  # Angolo inclinazione verticale
        self.scala = 30  # Pixel per metro
        self.offset_x = 0
        self.offset_y = 0

        # Interazione mouse
        self.dragging = False
        self.last_pos = None

        # Colori
        self.colore_muro = QColor(200, 150, 100)  # Mattoni
        self.colore_muro_ombra = QColor(160, 120, 80)
        self.colore_apertura = QColor(100, 150, 200, 150)  # Vetro
        self.colore_solaio = QColor(180, 180, 180, 200)

    def setProgetto(self, progetto: Progetto):
        self.progetto = progetto
        self.update()

    def proietta(self, x: float, y: float, z: float) -> Tuple[float, float]:
        """Proietta coordinate 3D in 2D isometrico"""
        # Rotazione attorno all'asse Z
        rad = math.radians(self.angolo)
        x_rot = x * math.cos(rad) - y * math.sin(rad)
        y_rot = x * math.sin(rad) + y * math.cos(rad)

        # Proiezione isometrica
        rad_inc = math.radians(self.inclinazione)
        px = x_rot * self.scala
        py = (-y_rot * math.cos(rad_inc) - z) * self.scala

        # Centro del widget + offset
        cx = self.width() / 2 + self.offset_x
        cy = self.height() / 2 + self.offset_y

        return (cx + px, cy + py)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Sfondo
        painter.fillRect(self.rect(), QColor(245, 248, 250))

        if not self.progetto:
            painter.drawText(self.rect(), Qt.AlignCenter, "Nessun progetto caricato")
            return

        # Disegna griglia a terra
        self.disegnaGriglia(painter)

        # Disegna solai (prima, come base)
        for solaio in self.progetto.solai:
            self.disegnaSolaio(painter, solaio)

        # Disegna muri (ordinati per distanza dalla camera)
        muri_ordinati = self.ordinaMuriPerProfondita()
        for muro in muri_ordinati:
            self.disegnaMuro3D(painter, muro)

        # Info
        painter.setPen(QPen(QColor(100, 100, 100)))
        font = QFont("Arial", 9)
        painter.setFont(font)
        painter.drawText(10, 20, f"Rotazione: {self.angolo}° | Scala: {self.scala} px/m")
        painter.drawText(10, 35, "Trascinare per ruotare, rotella per zoom")

    def disegnaGriglia(self, painter):
        """Disegna griglia di riferimento sul piano XY"""
        painter.setPen(QPen(QColor(200, 200, 200), 0.5))

        # Griglia 20x20 m
        for i in range(-10, 11, 2):
            # Linee X
            p1 = self.proietta(i, -10, 0)
            p2 = self.proietta(i, 10, 0)
            painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))

            # Linee Y
            p1 = self.proietta(-10, i, 0)
            p2 = self.proietta(10, i, 0)
            painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))

        # Assi
        painter.setPen(QPen(QColor(255, 0, 0), 2))  # X rosso
        p0 = self.proietta(0, 0, 0)
        px = self.proietta(3, 0, 0)
        painter.drawLine(int(p0[0]), int(p0[1]), int(px[0]), int(px[1]))
        painter.drawText(int(px[0]) + 5, int(px[1]), "X")

        painter.setPen(QPen(QColor(0, 200, 0), 2))  # Y verde
        py = self.proietta(0, 3, 0)
        painter.drawLine(int(p0[0]), int(p0[1]), int(py[0]), int(py[1]))
        painter.drawText(int(py[0]) + 5, int(py[1]), "Y")

        painter.setPen(QPen(QColor(0, 0, 255), 2))  # Z blu
        pz = self.proietta(0, 0, 3)
        painter.drawLine(int(p0[0]), int(p0[1]), int(pz[0]), int(pz[1]))
        painter.drawText(int(pz[0]) + 5, int(pz[1]), "Z")

    def ordinaMuriPerProfondita(self) -> List[Muro]:
        """Ordina i muri dal piu' lontano al piu' vicino"""
        if not self.progetto:
            return []

        rad = math.radians(self.angolo)

        def distanza_camera(muro):
            cx = (muro.x1 + muro.x2) / 2
            cy = (muro.y1 + muro.y2) / 2
            # Distanza lungo la direzione di vista
            return -(cx * math.sin(rad) + cy * math.cos(rad))

        return sorted(self.progetto.muri, key=distanza_camera)

    def disegnaMuro3D(self, painter, muro: Muro):
        """Disegna un muro come parallelepipedo 3D"""
        # Calcola i vertici del muro
        dx = muro.x2 - muro.x1
        dy = muro.y2 - muro.y1
        lunghezza = math.sqrt(dx*dx + dy*dy)
        if lunghezza < 0.01:
            return

        # Direzione normale (perpendicolare al muro)
        nx = -dy / lunghezza * muro.spessore / 2
        ny = dx / lunghezza * muro.spessore / 2

        # 8 vertici del parallelepipedo
        z_base = muro.z
        z_top = muro.z + muro.altezza

        # Base (4 vertici)
        v = [
            (muro.x1 - nx, muro.y1 - ny, z_base),
            (muro.x1 + nx, muro.y1 + ny, z_base),
            (muro.x2 + nx, muro.y2 + ny, z_base),
            (muro.x2 - nx, muro.y2 - ny, z_base),
            # Top (4 vertici)
            (muro.x1 - nx, muro.y1 - ny, z_top),
            (muro.x1 + nx, muro.y1 + ny, z_top),
            (muro.x2 + nx, muro.y2 + ny, z_top),
            (muro.x2 - nx, muro.y2 - ny, z_top),
        ]

        # Proietta tutti i vertici
        pv = [self.proietta(*vert) for vert in v]

        # Colore in base a DCR se attivo
        if muro.dcr > 0:
            if muro.dcr <= 0.5:
                colore = QColor(0, 180, 0)
            elif muro.dcr <= 0.8:
                colore = QColor(100, 200, 0)
            elif muro.dcr <= 1.0:
                colore = QColor(255, 200, 0)
            elif muro.dcr <= 1.2:
                colore = QColor(255, 140, 0)
            else:
                colore = QColor(255, 0, 0)
            colore_ombra = colore.darker(120)
        else:
            colore = self.colore_muro
            colore_ombra = self.colore_muro_ombra

        # Disegna le facce visibili
        # Faccia superiore (top)
        path_top = QPainterPath()
        path_top.moveTo(pv[4][0], pv[4][1])
        path_top.lineTo(pv[5][0], pv[5][1])
        path_top.lineTo(pv[6][0], pv[6][1])
        path_top.lineTo(pv[7][0], pv[7][1])
        path_top.closeSubpath()
        painter.setBrush(QBrush(colore.lighter(110)))
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawPath(path_top)

        # Facce laterali (semplificato - disegna solo 2 facce visibili)
        # Faccia frontale 1 (0-3-7-4)
        path_f1 = QPainterPath()
        path_f1.moveTo(pv[0][0], pv[0][1])
        path_f1.lineTo(pv[3][0], pv[3][1])
        path_f1.lineTo(pv[7][0], pv[7][1])
        path_f1.lineTo(pv[4][0], pv[4][1])
        path_f1.closeSubpath()
        painter.setBrush(QBrush(colore))
        painter.drawPath(path_f1)

        # Faccia frontale 2 (1-2-6-5)
        path_f2 = QPainterPath()
        path_f2.moveTo(pv[1][0], pv[1][1])
        path_f2.lineTo(pv[2][0], pv[2][1])
        path_f2.lineTo(pv[6][0], pv[6][1])
        path_f2.lineTo(pv[5][0], pv[5][1])
        path_f2.closeSubpath()
        painter.setBrush(QBrush(colore_ombra))
        painter.drawPath(path_f2)

        # Facce di estremita'
        # Estremo 1 (0-1-5-4)
        path_e1 = QPainterPath()
        path_e1.moveTo(pv[0][0], pv[0][1])
        path_e1.lineTo(pv[1][0], pv[1][1])
        path_e1.lineTo(pv[5][0], pv[5][1])
        path_e1.lineTo(pv[4][0], pv[4][1])
        path_e1.closeSubpath()
        painter.setBrush(QBrush(colore.darker(105)))
        painter.drawPath(path_e1)

        # Estremo 2 (2-3-7-6)
        path_e2 = QPainterPath()
        path_e2.moveTo(pv[2][0], pv[2][1])
        path_e2.lineTo(pv[3][0], pv[3][1])
        path_e2.lineTo(pv[7][0], pv[7][1])
        path_e2.lineTo(pv[6][0], pv[6][1])
        path_e2.closeSubpath()
        painter.drawPath(path_e2)

        # Disegna aperture (finestre/porte)
        self.disegnaAperture3D(painter, muro, v)

    def disegnaAperture3D(self, painter, muro: Muro, v):
        """Disegna le aperture sul muro in 3D"""
        if not self.progetto:
            return

        # Trova aperture su questo muro
        aperture = [a for a in self.progetto.aperture if a.muro == muro.nome]

        for ap in aperture:
            # Calcola posizione apertura lungo il muro
            dx = muro.x2 - muro.x1
            dy = muro.y2 - muro.y1
            lunghezza = math.sqrt(dx*dx + dy*dy)
            if lunghezza < 0.01:
                continue

            # Posizione relativa (0-1) lungo il muro
            t_start = ap.posizione / lunghezza
            t_end = (ap.posizione + ap.larghezza) / lunghezza

            # Vertici apertura
            z_bot = muro.z + ap.altezza_davanzale
            z_top = z_bot + ap.altezza

            # Calcola punti sulla faccia del muro
            nx = -dy / lunghezza * muro.spessore / 2
            ny = dx / lunghezza * muro.spessore / 2

            # Punti sulla faccia frontale
            ax1 = muro.x1 + dx * t_start - nx
            ay1 = muro.y1 + dy * t_start - ny
            ax2 = muro.x1 + dx * t_end - nx
            ay2 = muro.y1 + dy * t_end - ny

            # Proietta
            p1 = self.proietta(ax1, ay1, z_bot)
            p2 = self.proietta(ax2, ay2, z_bot)
            p3 = self.proietta(ax2, ay2, z_top)
            p4 = self.proietta(ax1, ay1, z_top)

            # Disegna apertura (colore diverso per finestre/porte)
            if ap.tipo == "finestra":
                painter.setBrush(QBrush(QColor(150, 200, 255, 180)))  # Vetro
            else:
                painter.setBrush(QBrush(QColor(100, 70, 50, 200)))  # Porta legno

            painter.setPen(QPen(QColor(60, 60, 60), 1))
            path = QPainterPath()
            path.moveTo(p1[0], p1[1])
            path.lineTo(p2[0], p2[1])
            path.lineTo(p3[0], p3[1])
            path.lineTo(p4[0], p4[1])
            path.closeSubpath()
            painter.drawPath(path)

    def disegnaSolaio(self, painter, solaio: Solaio):
        """Disegna un solaio come piano orizzontale"""
        # Posiziona il solaio alla quota del piano
        z = solaio.piano * self.progetto.altezza_piano

        # Usa le dimensioni del solaio come area
        x1, y1 = 0, 0
        x2 = solaio.larghezza
        y2 = solaio.luce

        # Vertici del solaio
        p1 = self.proietta(x1, y1, z)
        p2 = self.proietta(x2, y1, z)
        p3 = self.proietta(x2, y2, z)
        p4 = self.proietta(x1, y2, z)

        # Disegna
        painter.setBrush(QBrush(self.colore_solaio))
        painter.setPen(QPen(QColor(100, 100, 100), 1))

        path = QPainterPath()
        path.moveTo(p1[0], p1[1])
        path.lineTo(p2[0], p2[1])
        path.lineTo(p3[0], p3[1])
        path.lineTo(p4[0], p4[1])
        path.closeSubpath()
        painter.drawPath(path)

        # Etichetta
        cx = (p1[0] + p3[0]) / 2
        cy = (p1[1] + p3[1]) / 2
        painter.setPen(QPen(QColor(50, 50, 50)))
        font = QFont("Arial", 8)
        painter.setFont(font)
        painter.drawText(int(cx) - 20, int(cy), solaio.nome)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.last_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragging and self.last_pos:
            dx = event.x() - self.last_pos.x()
            dy = event.y() - self.last_pos.y()

            # Rotazione con movimento orizzontale
            self.angolo = (self.angolo + dx * 0.5) % 360

            # Pan con movimento verticale (shift) o inclinazione
            if event.modifiers() & Qt.ShiftModifier:
                self.offset_x += dx
                self.offset_y += dy
            else:
                self.inclinazione = max(10, min(60, self.inclinazione + dy * 0.2))

            self.last_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.last_pos = None

    def wheelEvent(self, event):
        # Zoom con rotella
        delta = event.angleDelta().y()
        if delta > 0:
            self.scala = min(100, self.scala * 1.1)
        else:
            self.scala = max(5, self.scala / 1.1)
        self.update()


class Dialogo3D(QDialog):
    """Finestra per vista 3D dell'edificio"""

    def __init__(self, progetto: Progetto, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vista 3D - " + progetto.nome)
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()

        reset_btn = QPushButton("Reset Vista")
        reset_btn.clicked.connect(self.resetVista)
        toolbar.addWidget(reset_btn)

        toolbar.addWidget(QLabel("Rotazione:"))
        self.angolo_spin = QSpinBox()
        self.angolo_spin.setRange(0, 359)
        self.angolo_spin.setValue(30)
        self.angolo_spin.valueChanged.connect(self.onAngoloChanged)
        toolbar.addWidget(self.angolo_spin)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Vista 3D
        self.vista3d = Vista3DWidget()
        self.vista3d.setProgetto(progetto)
        layout.addWidget(self.vista3d)

        # Info
        info_label = QLabel("Mouse: Trascina per ruotare | Shift+Trascina per pan | Rotella per zoom")
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info_label)

    def resetVista(self):
        self.vista3d.angolo = 30
        self.vista3d.inclinazione = 30
        self.vista3d.scala = 30
        self.vista3d.offset_x = 0
        self.vista3d.offset_y = 0
        self.angolo_spin.setValue(30)
        self.vista3d.update()

    def onAngoloChanged(self, value):
        self.vista3d.angolo = value
        self.vista3d.update()


# ============================================================================
# FINESTRA PRINCIPALE
# ============================================================================

class MuraturaEditor(QMainWindow):
    """Finestra principale dell'editor"""

    def __init__(self):
        super().__init__()
        self.progetto = Progetto()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Muratura Editor - Nuovo Progetto")
        self.setGeometry(100, 100, 1200, 800)

        # Menu
        self.creaMenu()

        # Toolbar
        self.creaToolbar()

        # Widget centrale con splitter
        splitter = QSplitter(Qt.Horizontal)

        # Canvas
        self.canvas = PiantaCanvas()
        self.canvas.setProgetto(self.progetto)
        self.canvas.muroAggiunto.connect(self.onMuroAggiunto)

        # Pannello laterale
        self.pannello = PannelloProprietà()
        self.pannello.setProgetto(self.progetto)
        self.pannello.setMinimumWidth(300)

        splitter.addWidget(self.canvas)
        splitter.addWidget(self.pannello)
        splitter.setSizes([800, 400])

        self.setCentralWidget(splitter)

        # Status bar
        self.statusBar().showMessage("Pronto - Usa gli strumenti per disegnare")

        # Aggiungi materiale di default
        self.progetto.materiali.append(Materiale(
            nome="mattoni",
            tipo="MATTONI_PIENI",
            malta="BUONA",
            conservazione="BUONO"
        ))
        self.pannello.aggiornaTabellaMateriali()

    def creaMenu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        nuovo_action = QAction("Nuovo", self)
        nuovo_action.setShortcut("Ctrl+N")
        nuovo_action.triggered.connect(self.nuovoProgetto)
        file_menu.addAction(nuovo_action)

        apri_action = QAction("Apri...", self)
        apri_action.setShortcut("Ctrl+O")
        apri_action.triggered.connect(self.apriProgetto)
        file_menu.addAction(apri_action)

        file_menu.addSeparator()

        salva_action = QAction("Salva", self)
        salva_action.setShortcut("Ctrl+S")
        salva_action.triggered.connect(self.salvaProgetto)
        file_menu.addAction(salva_action)

        salva_come_action = QAction("Salva come...", self)
        salva_come_action.setShortcut("Ctrl+Shift+S")
        salva_come_action.triggered.connect(self.salvaProgettoCome)
        file_menu.addAction(salva_come_action)

        file_menu.addSeparator()

        report_action = QAction("Esporta Report HTML...", self)
        report_action.setShortcut("Ctrl+R")
        report_action.triggered.connect(self.esportaReportHTML)
        file_menu.addAction(report_action)

        file_menu.addSeparator()

        esci_action = QAction("Esci", self)
        esci_action.setShortcut("Ctrl+Q")
        esci_action.triggered.connect(self.close)
        file_menu.addAction(esci_action)

        # Modifica menu
        modifica_menu = menubar.addMenu("Modifica")

        elimina_action = QAction("Elimina", self)
        elimina_action.setShortcut("Delete")
        elimina_action.triggered.connect(self.eliminaSelezionato)
        modifica_menu.addAction(elimina_action)

        modifica_menu.addSeparator()

        prop_muro_action = QAction("Proprieta' muro...", self)
        prop_muro_action.triggered.connect(self.editProprietaMuro)
        modifica_menu.addAction(prop_muro_action)

        # Vista menu
        vista_menu = menubar.addMenu("Vista")

        griglia_action = QAction("Mostra griglia", self)
        griglia_action.setCheckable(True)
        griglia_action.setChecked(True)
        griglia_action.triggered.connect(self.toggleGriglia)
        vista_menu.addAction(griglia_action)

        # Submenu passo griglia
        griglia_menu = vista_menu.addMenu("Passo griglia")
        self.griglia_actions = QActionGroup(self)
        for passo, label in [(0.10, "10 cm"), (0.25, "25 cm"), (0.50, "50 cm (default)"),
                             (1.0, "1 m"), (2.0, "2 m")]:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(passo == 0.5)
            action.triggered.connect(lambda checked, p=passo: self.setPassoGriglia(p))
            self.griglia_actions.addAction(action)
            griglia_menu.addAction(action)

        # Mostra quote
        quote_action = QAction("Mostra quote sui muri", self)
        quote_action.setCheckable(True)
        quote_action.setChecked(True)
        quote_action.triggered.connect(self.toggleQuote)
        vista_menu.addAction(quote_action)

        zoom_fit_action = QAction("Adatta alla vista", self)
        zoom_fit_action.setShortcut("Ctrl+0")
        zoom_fit_action.triggered.connect(self.zoomFit)
        vista_menu.addAction(zoom_fit_action)

        # OSNAP submenu
        vista_menu.addSeparator()
        osnap_menu = vista_menu.addMenu("OSNAP")

        self.osnap_endpoint = QAction("Endpoint (estremi)", self)
        self.osnap_endpoint.setCheckable(True)
        self.osnap_endpoint.setChecked(True)
        self.osnap_endpoint.triggered.connect(lambda c: self.toggleOsnap(OsnapMode.ENDPOINT, c))
        osnap_menu.addAction(self.osnap_endpoint)

        self.osnap_midpoint = QAction("Midpoint (punto medio)", self)
        self.osnap_midpoint.setCheckable(True)
        self.osnap_midpoint.setChecked(False)
        self.osnap_midpoint.triggered.connect(lambda c: self.toggleOsnap(OsnapMode.MIDPOINT, c))
        osnap_menu.addAction(self.osnap_midpoint)

        self.osnap_intersection = QAction("Intersection (intersezione)", self)
        self.osnap_intersection.setCheckable(True)
        self.osnap_intersection.setChecked(False)
        self.osnap_intersection.triggered.connect(lambda c: self.toggleOsnap(OsnapMode.INTERSECTION, c))
        osnap_menu.addAction(self.osnap_intersection)

        self.osnap_perpendicular = QAction("Perpendicular (perpendicolare)", self)
        self.osnap_perpendicular.setCheckable(True)
        self.osnap_perpendicular.setChecked(False)
        self.osnap_perpendicular.triggered.connect(lambda c: self.toggleOsnap(OsnapMode.PERPENDICULAR, c))
        osnap_menu.addAction(self.osnap_perpendicular)

        self.osnap_grid = QAction("Grid (griglia)", self)
        self.osnap_grid.setCheckable(True)
        self.osnap_grid.setChecked(True)
        self.osnap_grid.triggered.connect(lambda c: self.toggleOsnap(OsnapMode.GRID, c))
        osnap_menu.addAction(self.osnap_grid)

        # Planimetria
        vista_menu.addSeparator()

        planimetria_action = QAction("Carica Planimetria...", self)
        planimetria_action.triggered.connect(self.caricaPlanimetria)
        vista_menu.addAction(planimetria_action)

        self.mostra_plan_action = QAction("Mostra Planimetria", self)
        self.mostra_plan_action.setCheckable(True)
        self.mostra_plan_action.setChecked(True)
        self.mostra_plan_action.triggered.connect(self.togglePlanimetria)
        vista_menu.addAction(self.mostra_plan_action)

        # Vista 3D
        vista_menu.addSeparator()

        vista3d_action = QAction("Vista 3D...", self)
        vista3d_action.setShortcut("F3")
        vista3d_action.triggered.connect(self.mostraVista3D)
        vista_menu.addAction(vista3d_action)

        # Progetto menu
        progetto_menu = menubar.addMenu("Progetto")

        carichi_action = QAction("Carichi Climatici...", self)
        carichi_action.setToolTip("Configura carichi neve e vento (NTC 2018)")
        carichi_action.triggered.connect(self.editCarichiClimatici)
        progetto_menu.addAction(carichi_action)

        progetto_menu.addSeparator()

        riepilogo_action = QAction("Riepilogo Progetto", self)
        riepilogo_action.triggered.connect(self.mostraRiepilogoProgetto)
        progetto_menu.addAction(riepilogo_action)

        # Analisi menu
        analisi_menu = menubar.addMenu("Analisi")

        verifica_action = QAction("Verifica Semplificata...", self)
        verifica_action.setToolTip("Calcola DCR semplificato per tutti i muri")
        verifica_action.triggered.connect(self.eseguiVerificaSemplificata)
        analisi_menu.addAction(verifica_action)

        analisi_menu.addSeparator()

        self.dcr_action = QAction("Mostra Colorazione DCR", self)
        self.dcr_action.setCheckable(True)
        self.dcr_action.setChecked(False)
        self.dcr_action.triggered.connect(self.toggleDCR)
        analisi_menu.addAction(self.dcr_action)

        legenda_action = QAction("Legenda DCR", self)
        legenda_action.triggered.connect(self.mostraLegendaDCR)
        analisi_menu.addAction(legenda_action)

    def creaToolbar(self):
        toolbar = QToolBar("Strumenti")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # Gruppo strumenti
        gruppo = QActionGroup(self)

        select_action = QAction("Seleziona", self)
        select_action.setCheckable(True)
        select_action.setChecked(True)
        select_action.triggered.connect(lambda: self.canvas.setStrumento('select'))
        gruppo.addAction(select_action)
        toolbar.addAction(select_action)

        muro_action = QAction("Muro", self)
        muro_action.setCheckable(True)
        muro_action.triggered.connect(lambda: self.canvas.setStrumento('muro'))
        gruppo.addAction(muro_action)
        toolbar.addAction(muro_action)

        pan_action = QAction("Pan", self)
        pan_action.setCheckable(True)
        pan_action.triggered.connect(lambda: self.canvas.setStrumento('pan'))
        gruppo.addAction(pan_action)
        toolbar.addAction(pan_action)

        toolbar.addSeparator()

        # Elimina
        elimina_btn = QAction("Elimina", self)
        elimina_btn.setShortcut("Delete")
        elimina_btn.triggered.connect(self.eliminaSelezionato)
        toolbar.addAction(elimina_btn)

        toolbar.addSeparator()

        # Quota Z
        toolbar.addWidget(QLabel(" Z: "))
        self.z_spin = QDoubleSpinBox()
        self.z_spin.setRange(0, 100)
        self.z_spin.setValue(0)
        self.z_spin.setSuffix(" m")
        self.z_spin.valueChanged.connect(self.onZChanged)
        toolbar.addWidget(self.z_spin)

        # Altezza
        toolbar.addWidget(QLabel(" H: "))
        self.h_spin = QDoubleSpinBox()
        self.h_spin.setRange(0.5, 20)
        self.h_spin.setValue(3.0)
        self.h_spin.setSuffix(" m")
        self.h_spin.valueChanged.connect(self.onAltezzaChanged)
        toolbar.addWidget(self.h_spin)

        # Spessore
        toolbar.addWidget(QLabel(" s: "))
        self.s_spin = QDoubleSpinBox()
        self.s_spin.setRange(0.1, 2)
        self.s_spin.setValue(0.45)
        self.s_spin.setDecimals(2)
        self.s_spin.setSuffix(" m")
        self.s_spin.valueChanged.connect(self.onSpessoreChanged)
        toolbar.addWidget(self.s_spin)

        toolbar.addSeparator()

        # Selettore piano
        toolbar.addWidget(QLabel(" Piano: "))
        self.piano_combo = QComboBox()
        self.piano_combo.setMinimumWidth(80)
        self.piano_combo.addItem("Piano 0", 0)
        self.piano_combo.currentIndexChanged.connect(self.onPianoChanged)
        toolbar.addWidget(self.piano_combo)

        # Aggiungi piano
        btn_add_piano = QPushButton("+")
        btn_add_piano.setFixedWidth(30)
        btn_add_piano.setToolTip("Aggiungi nuovo piano")
        btn_add_piano.clicked.connect(self.aggiungiPianoRapido)
        toolbar.addWidget(btn_add_piano)

        # Solo piano corrente
        from PyQt5.QtWidgets import QCheckBox
        self.solo_piano_check = QCheckBox("Solo questo piano")
        self.solo_piano_check.setChecked(False)
        self.solo_piano_check.stateChanged.connect(self.onSoloPianoChanged)
        toolbar.addWidget(self.solo_piano_check)

        toolbar.addSeparator()

        # Copia piano
        btn_copia = QPushButton("Copia Piano")
        btn_copia.setToolTip("Copia tutti i muri del piano corrente su un altro piano")
        btn_copia.clicked.connect(self.copiaPiano)
        toolbar.addWidget(btn_copia)

    def onZChanged(self, value):
        self.canvas.z_corrente = value
        self.canvas.aggiornaPlanimetria()
        self.canvas.update()
        # Aggiorna selezione nel combo se corrisponde a un piano
        self.sincronizzaPianoCombo()

    def onAltezzaChanged(self, value):
        self.canvas.altezza_corrente = value

    def onSpessoreChanged(self, value):
        self.canvas.spessore_corrente = value

    def onPianoChanged(self, index):
        """Cambia piano selezionato"""
        if index >= 0:
            piano_idx = self.piano_combo.currentData()
            if piano_idx is not None:
                # Trova il piano e imposta Z
                for p in self.progetto.piani:
                    if p.indice == piano_idx:
                        self.z_spin.setValue(p.quota)
                        self.h_spin.setValue(p.altezza)
                        break
                else:
                    # Piano non trovato, usa quota = indice * 3
                    self.z_spin.setValue(piano_idx * 3.0)

    def onSoloPianoChanged(self, state):
        """Attiva/disattiva visualizzazione solo piano corrente"""
        self.canvas.solo_piano_corrente = (state == Qt.Checked)
        self.canvas.update()

    def sincronizzaPianoCombo(self):
        """Sincronizza il combo con la quota Z corrente"""
        z = self.canvas.z_corrente
        for i in range(self.piano_combo.count()):
            piano_idx = self.piano_combo.itemData(i)
            for p in self.progetto.piani:
                if p.indice == piano_idx and abs(p.quota - z) < 0.1:
                    self.piano_combo.blockSignals(True)
                    self.piano_combo.setCurrentIndex(i)
                    self.piano_combo.blockSignals(False)
                    return

    def aggiornaPianoCombo(self):
        """Aggiorna il combo dei piani"""
        self.piano_combo.blockSignals(True)
        self.piano_combo.clear()

        if self.progetto.piani:
            for p in sorted(self.progetto.piani, key=lambda x: x.indice):
                self.piano_combo.addItem(f"Piano {p.indice}", p.indice)
        else:
            # Nessun piano definito, mostra piano 0
            self.piano_combo.addItem("Piano 0", 0)

        self.piano_combo.blockSignals(False)
        self.sincronizzaPianoCombo()

    def aggiungiPianoRapido(self):
        """Aggiunge un nuovo piano velocemente"""
        # Calcola prossimo indice
        if self.progetto.piani:
            ultimo = max(self.progetto.piani, key=lambda p: p.indice)
            nuovo_indice = ultimo.indice + 1
            nuova_quota = ultimo.quota + ultimo.altezza
        else:
            nuovo_indice = 0
            nuova_quota = 0.0

        piano = Piano(
            indice=nuovo_indice,
            quota=nuova_quota,
            altezza=self.canvas.altezza_corrente,
            massa=10000
        )
        self.progetto.piani.append(piano)
        self.aggiornaPianoCombo()
        self.pannello.aggiornaTabelllaPiani()

        # Seleziona il nuovo piano
        self.piano_combo.setCurrentIndex(self.piano_combo.count() - 1)
        self.statusBar().showMessage(f"Aggiunto Piano {nuovo_indice} a quota {nuova_quota:.1f}m")

    def copiaPiano(self):
        """Copia tutti i muri del piano corrente su un altro piano"""
        z_corrente = self.canvas.z_corrente

        # Trova muri del piano corrente
        muri_piano = [m for m in self.progetto.muri if abs(m.z - z_corrente) < 0.1]

        if not muri_piano:
            QMessageBox.warning(self, "Nessun muro",
                              f"Non ci sono muri alla quota Z={z_corrente:.1f}m")
            return

        # Chiedi piano destinazione
        piani_dest = []
        for p in self.progetto.piani:
            if abs(p.quota - z_corrente) > 0.1:  # Escludi piano corrente
                piani_dest.append(f"Piano {p.indice} (Z={p.quota:.1f}m)")

        if not piani_dest:
            # Proponi di creare un nuovo piano
            risposta = QMessageBox.question(
                self, "Crea nuovo piano",
                "Non ci sono altri piani. Vuoi creare un nuovo piano?",
                QMessageBox.Yes | QMessageBox.No
            )
            if risposta == QMessageBox.Yes:
                self.aggiungiPianoRapido()
                # Riprova
                piani_dest = []
                for p in self.progetto.piani:
                    if abs(p.quota - z_corrente) > 0.1:
                        piani_dest.append(f"Piano {p.indice} (Z={p.quota:.1f}m)")

        if not piani_dest:
            return

        piano_str, ok = QInputDialog.getItem(
            self, "Piano Destinazione",
            f"Copia {len(muri_piano)} muri su:",
            piani_dest, 0, False
        )
        if not ok:
            return

        # Estrai indice piano
        piano_idx = int(piano_str.split()[1])
        piano_dest = next((p for p in self.progetto.piani if p.indice == piano_idx), None)

        if not piano_dest:
            return

        # Copia muri
        nuovi_muri = []
        for muro in muri_piano:
            # Crea nuovo nome
            n = len([m for m in self.progetto.muri if m.z == piano_dest.quota]) + len(nuovi_muri) + 1
            nuovo_nome = f"M{n}_{piano_idx}"

            nuovo_muro = Muro(
                nome=nuovo_nome,
                x1=muro.x1, y1=muro.y1,
                x2=muro.x2, y2=muro.y2,
                z=piano_dest.quota,
                altezza=piano_dest.altezza,
                spessore=muro.spessore,
                materiale=muro.materiale
            )
            nuovi_muri.append(nuovo_muro)

        self.progetto.muri.extend(nuovi_muri)
        self.pannello.aggiornaTabelllaMuri()
        self.canvas.update()

        self.statusBar().showMessage(
            f"Copiati {len(nuovi_muri)} muri su Piano {piano_idx} (Z={piano_dest.quota:.1f}m)"
        )

    def onMuroAggiunto(self, muro: Muro):
        self.pannello.aggiornaTabelllaMuri()
        self.statusBar().showMessage(f"Muro '{muro.nome}' aggiunto - L={muro.lunghezza:.2f}m")

    def nuovoProgetto(self):
        """Crea un nuovo progetto usando il wizard"""
        wizard = WizardNuovoProgetto(self)
        if wizard.exec_() == QWizard.Accepted:
            # Ottieni progetto configurato dal wizard
            self.progetto = wizard.getProgetto()

            # Aggiungi materiale di default
            self.progetto.materiali.append(Materiale(
                nome="mattoni", tipo="MATTONI_PIENI",
                malta="BUONA", conservazione="BUONO"
            ))

            # Aggiorna GUI
            self.canvas.setProgetto(self.progetto)
            self.pannello.setProgetto(self.progetto)
            self.aggiornaPianoCombo()
            self.setWindowTitle(f"Muratura Editor - {self.progetto.nome}")

            # Mostra info sismiche nella status bar
            if self.progetto.sismici.comune:
                self.statusBar().showMessage(
                    f"Progetto creato: {self.progetto.nome} - "
                    f"Comune: {self.progetto.sismici.comune} - "
                    f"Zona sismica: {self.zona_sismica()}"
                )

    def zona_sismica(self) -> str:
        """Calcola la zona sismica del progetto"""
        if not SEISMIC_AVAILABLE or not self.progetto.sismici.comune:
            return "-"
        try:
            analysis = SeismicAnalysis(comune=self.progetto.sismici.comune)
            return str(analysis.seismic_zone)
        except:
            return "-"

    def apriProgetto(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Apri Progetto", "",
            "File Muratura (*.mur);;Tutti i file (*)"
        )
        if filepath:
            self.caricaFile(filepath)

    def caricaFile(self, filepath: str):
        """Carica un file .mur"""
        try:
            from Material.dsl_parser import load_dsl

            dsl_project = load_dsl(filepath)

            # Converti in formato GUI
            self.progetto = Progetto(
                nome=dsl_project.nome,
                autore=dsl_project.autore,
                filepath=filepath
            )

            # Materiali
            for nome, mat_def in dsl_project.materiali.items():
                self.progetto.materiali.append(Materiale(
                    nome=nome,
                    tipo=mat_def.tipo,
                    malta=mat_def.malta,
                    conservazione=mat_def.conservazione
                ))

            # Muri
            for muro_def in dsl_project.muri:
                self.progetto.muri.append(Muro(
                    nome=muro_def.nome,
                    x1=muro_def.x1, y1=muro_def.y1,
                    x2=muro_def.x2, y2=muro_def.y2,
                    z=muro_def.z,
                    altezza=muro_def.altezza,
                    spessore=muro_def.spessore,
                    materiale=muro_def.materiale
                ))

            # Aperture
            for ap_def in dsl_project.aperture:
                self.progetto.aperture.append(Apertura(
                    muro=ap_def.parete,
                    tipo=ap_def.tipo,
                    larghezza=ap_def.larghezza,
                    altezza=ap_def.altezza,
                    distanza=ap_def.x + 4,  # Approssimazione
                    quota=ap_def.y
                ))

            # Piani
            for idx, piano_def in dsl_project.piani.items():
                self.progetto.piani.append(Piano(
                    indice=idx,
                    quota=piano_def.quota if hasattr(piano_def, 'quota') else idx * piano_def.altezza,
                    altezza=piano_def.altezza,
                    massa=piano_def.massa
                ))

            # Carichi
            for idx, carico_def in dsl_project.carichi.items():
                self.progetto.carichi.append(Carico(
                    piano=idx,
                    permanente=carico_def.permanente,
                    variabile=carico_def.variabile,
                    copertura=carico_def.copertura
                ))

            # Cordoli
            for cordolo_def in dsl_project.cordoli:
                self.progetto.cordoli.append(Cordolo(
                    nome=cordolo_def.nome,
                    piano=cordolo_def.piano,
                    base=cordolo_def.base,
                    altezza=cordolo_def.altezza,
                    materiale=cordolo_def.materiale,
                    x1=cordolo_def.x1,
                    y1=cordolo_def.y1,
                    x2=cordolo_def.x2,
                    y2=cordolo_def.y2
                ))

            # Solai
            for solaio_def in dsl_project.solai:
                self.progetto.solai.append(Solaio(
                    nome=solaio_def.nome,
                    piano=solaio_def.piano,
                    tipo=solaio_def.tipo,
                    preset=solaio_def.preset,
                    luce=solaio_def.luce,
                    larghezza=solaio_def.larghezza,
                    orditura=solaio_def.orditura,
                    peso_proprio=solaio_def.peso_proprio,
                    peso_finiture=solaio_def.peso_finiture,
                    carico_variabile=solaio_def.carico_variabile,
                    categoria_uso=solaio_def.categoria_uso,
                    rigidezza=solaio_def.rigidezza
                ))

            self.canvas.setProgetto(self.progetto)
            self.pannello.setProgetto(self.progetto)
            self.aggiornaPianoCombo()
            self.setWindowTitle(f"Muratura Editor - {self.progetto.nome}")
            self.statusBar().showMessage(f"Progetto caricato: {filepath}")

        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore caricamento:\n{e}")

    def salvaProgetto(self):
        if self.progetto.filepath:
            self.salvaFile(self.progetto.filepath)
        else:
            self.salvaProgettoCome()

    def salvaProgettoCome(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Salva Progetto", f"{self.progetto.nome}.mur",
            "File Muratura (*.mur);;Tutti i file (*)"
        )
        if filepath:
            self.salvaFile(filepath)

    def salvaFile(self, filepath: str):
        """Salva in formato .mur"""
        try:
            lines = []

            # Header
            lines.append(f'PROGETTO "{self.progetto.nome}" AUTORE "{self.progetto.autore}"')
            lines.append("")

            # Materiali
            lines.append("# MATERIALI")
            for mat in self.progetto.materiali:
                lines.append(f"MATERIALE {mat.nome} {mat.tipo} {mat.malta} {mat.conservazione}")
            lines.append("")

            # Muri
            lines.append("# MURI")
            for muro in self.progetto.muri:
                lines.append(
                    f"MURO {muro.nome} {muro.x1:.2f} {muro.y1:.2f} "
                    f"{muro.x2:.2f} {muro.y2:.2f} {muro.z:.1f} "
                    f"{muro.altezza:.1f} {muro.spessore:.2f} {muro.materiale}"
                )
            lines.append("")

            # Aperture
            if self.progetto.aperture:
                lines.append("# APERTURE")
                for ap in self.progetto.aperture:
                    if ap.tipo == 'finestra':
                        lines.append(
                            f"FINESTRA {ap.muro} {ap.larghezza:.2f} "
                            f"{ap.altezza:.2f} {ap.distanza:.2f} {ap.quota:.2f}"
                        )
                    else:
                        lines.append(
                            f"PORTA {ap.muro} {ap.larghezza:.2f} "
                            f"{ap.altezza:.2f} {ap.distanza:.2f}"
                        )
                lines.append("")

            # Piani
            if self.progetto.piani:
                lines.append("# PIANI")
                for piano in self.progetto.piani:
                    lines.append(
                        f"PIANO {piano.indice} {piano.altezza:.2f} {piano.massa:.0f}"
                    )
                lines.append("")

            # Carichi
            if self.progetto.carichi:
                lines.append("# CARICHI")
                for carico in self.progetto.carichi:
                    copertura_str = " copertura" if carico.copertura else ""
                    lines.append(
                        f"CARICO {carico.piano} {carico.permanente:.1f} {carico.variabile:.1f}{copertura_str}"
                    )
                lines.append("")

            # Cordoli
            if self.progetto.cordoli:
                lines.append("# CORDOLI")
                for cordolo in self.progetto.cordoli:
                    if cordolo.is_perimetrale:
                        lines.append(
                            f"CORDOLO {cordolo.nome} {cordolo.piano} "
                            f"{cordolo.base:.2f} {cordolo.altezza:.2f} {cordolo.materiale}"
                        )
                    else:
                        lines.append(
                            f"CORDOLO_LINEA {cordolo.nome} {cordolo.piano} "
                            f"{cordolo.base:.2f} {cordolo.altezza:.2f} {cordolo.materiale} "
                            f"{cordolo.x1:.2f} {cordolo.y1:.2f} {cordolo.x2:.2f} {cordolo.y2:.2f}"
                        )
                lines.append("")

            # Solai
            if self.progetto.solai:
                lines.append("# SOLAI")
                for solaio in self.progetto.solai:
                    # SOLAIO nome piano tipo preset luce larghezza orditura G1 G2 Qk categoria rigidezza
                    lines.append(
                        f"SOLAIO {solaio.nome} {solaio.piano} {solaio.tipo} {solaio.preset} "
                        f"{solaio.luce:.2f} {solaio.larghezza:.2f} {solaio.orditura:.1f} "
                        f"{solaio.peso_proprio:.2f} {solaio.peso_finiture:.2f} {solaio.carico_variabile:.2f} "
                        f"{solaio.categoria_uso} {solaio.rigidezza}"
                    )
                lines.append("")

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            self.progetto.filepath = filepath
            self.statusBar().showMessage(f"Salvato: {filepath}")

        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore salvataggio:\n{e}")

    def editProprietaMuro(self):
        materiali = [m.nome for m in self.progetto.materiali]
        dialogo = DialogoProprietaMuro(materiali, self)

        if dialogo.exec_() == QDialog.Accepted:
            z, alt, spess, mat = dialogo.getValues()
            self.canvas.z_corrente = z
            self.canvas.altezza_corrente = alt
            self.canvas.spessore_corrente = spess
            self.canvas.materiale_corrente = mat

            self.z_spin.setValue(z)
            self.h_spin.setValue(alt)
            self.s_spin.setValue(spess)

    def editCarichiClimatici(self):
        """Apre il dialogo per configurare i carichi climatici"""
        # Calcola altezza edificio
        if self.progetto.piani:
            altezza = sum(p.altezza for p in self.progetto.piani)
        else:
            altezza = self.progetto.n_piani * self.progetto.altezza_piano

        dialogo = DialogoCarichiClimatici(
            provincia=self.progetto.sismici.provincia,
            altitudine=self.progetto.altitudine,
            altezza_edificio=altezza,
            parent=self
        )

        if dialogo.exec_() == QDialog.Accepted:
            self.progetto.climatici = dialogo.getCarichiClimatici()
            self.progetto.altitudine = dialogo.altitudine_spin.value()
            self.statusBar().showMessage(
                f"Carichi climatici aggiornati - "
                f"Neve: {self.progetto.climatici.qs:.2f} kN/m2, "
                f"Vento: {self.progetto.climatici.p_vento:.3f} kN/m2"
            )

    def mostraRiepilogoProgetto(self):
        """Mostra un riepilogo del progetto"""
        p = self.progetto

        # Calcola statistiche
        area_muri = sum(m.lunghezza * m.altezza for m in p.muri)
        vol_muri = sum(m.lunghezza * m.altezza * m.spessore for m in p.muri)
        n_finestre = len([a for a in p.aperture if a.tipo == 'finestra'])
        n_porte = len([a for a in p.aperture if a.tipo == 'porta'])

        # Carichi totali dai solai
        carico_tot = sum(s.carico_totale * s.area for s in p.solai)

        msg = f"""
RIEPILOGO PROGETTO: {p.nome}

GEOMETRIA:
  Muri: {len(p.muri)} (area {area_muri:.1f} m2, volume {vol_muri:.1f} m3)
  Aperture: {n_finestre} finestre, {n_porte} porte
  Piani: {len(p.piani) or p.n_piani}
  Solai: {len(p.solai)}
  Cordoli: {len(p.cordoli)}

LOCALIZZAZIONE:
  Comune: {p.sismici.comune or 'Non specificato'}
  Provincia: {p.sismici.provincia or 'Non specificata'}
  Altitudine: {p.altitudine:.0f} m s.l.m.

CARICHI CLIMATICI (NTC 2018):
  Neve (qs): {p.climatici.qs:.2f} kN/m2
  Vento (p): {p.climatici.p_vento:.3f} kN/m2

PARAMETRI SISMICI:
  Sottosuolo: {p.sismici.sottosuolo}
  Topografia: {p.sismici.topografia}
  Classe d'uso: {p.sismici.classe_uso}
  Fattore q: {p.sismici.fattore_struttura}

CARICHI TOTALI:
  Da solai: {carico_tot:.1f} kN
"""

        QMessageBox.information(self, "Riepilogo Progetto", msg.strip())

    def esportaReportHTML(self):
        """Esporta un report HTML completo del progetto"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Esporta Report HTML",
            f"{self.progetto.nome}_report.html",
            "File HTML (*.html);;Tutti i file (*)"
        )

        if not filepath:
            return

        try:
            p = self.progetto
            from datetime import datetime

            # Calcola statistiche
            area_muri = sum(m.lunghezza * m.altezza for m in p.muri)
            vol_muri = sum(m.lunghezza * m.altezza * m.spessore for m in p.muri)
            n_finestre = len([a for a in p.aperture if a.tipo == 'finestra'])
            n_porte = len([a for a in p.aperture if a.tipo == 'porta'])
            carico_tot = sum(s.carico_totale * s.area for s in p.solai)

            # DCR statistics
            if p.muri and any(m.dcr > 0 for m in p.muri):
                max_dcr = max(m.dcr for m in p.muri)
                muri_ok = sum(1 for m in p.muri if m.dcr <= 1.0 and m.dcr > 0)
                muri_ko = sum(1 for m in p.muri if m.dcr > 1.0)

                # Indice di rischio sismico
                ir = p.indice_rischio if p.indice_rischio > 0 else (1.0 / max_dcr if max_dcr > 0 else 0)
                if ir >= 1.0:
                    ir_esito = "VERIFICATO"
                    ir_class = "ok"
                elif ir >= 0.8:
                    ir_esito = "CARENTE"
                    ir_class = "warn"
                elif ir >= 0.6:
                    ir_esito = "INSUFFICIENTE"
                    ir_class = "ko"
                else:
                    ir_esito = "CRITICO"
                    ir_class = "ko"

                dcr_section = f"""
        <h2>Indice di Rischio Sismico</h2>
        <div style="background: #f0f0f0; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
            <span style="font-size: 48px; font-weight: bold; color: {'#28a745' if ir >= 1.0 else '#ffc107' if ir >= 0.8 else '#dc3545'};">{ir:.3f}</span>
            <p style="font-size: 18px; margin: 10px 0;"><strong>{ir_esito}</strong></p>
            <p>IR = PGA<sub>capacita'</sub> / PGA<sub>domanda</sub></p>
            <p>PGA domanda: {p.pga_domanda:.3f} g | PGA capacita': {p.pga_capacita:.3f} g</p>
        </div>

        <h2>Risultati Verifica</h2>
        <table>
            <tr><th>Parametro</th><th>Valore</th></tr>
            <tr><td>Indice Rischio IR</td><td class="{ir_class}">{ir:.3f} ({ir_esito})</td></tr>
            <tr><td>DCR Massimo</td><td class="{'ok' if max_dcr <= 1.0 else 'ko'}">{max_dcr:.3f}</td></tr>
            <tr><td>Muri Verificati</td><td class="ok">{muri_ok}</td></tr>
            <tr><td>Muri Non Verificati</td><td class="{'ok' if muri_ko == 0 else 'ko'}">{muri_ko}</td></tr>
        </table>

        <h3>Dettaglio Muri</h3>
        <table>
            <tr><th>Nome</th><th>L [m]</th><th>H [m]</th><th>s [m]</th><th>DCR</th><th>Stato</th></tr>
"""
                for m in p.muri:
                    stato = "OK" if m.dcr <= 1.0 else "CRITICO"
                    stato_class = "ok" if m.dcr <= 1.0 else "ko"
                    dcr_section += f'            <tr><td>{m.nome}</td><td>{m.lunghezza:.2f}</td><td>{m.altezza:.2f}</td><td>{m.spessore:.2f}</td><td>{m.dcr:.3f}</td><td class="{stato_class}">{stato}</td></tr>\n'
                dcr_section += "        </table>"
            else:
                dcr_section = "<p><em>Nessuna verifica eseguita. Usare Analisi > Verifica Semplificata.</em></p>"

            # Genera HTML
            html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Report {p.nome}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #333; border-bottom: 2px solid #0066cc; padding-bottom: 10px; }}
        h2 {{ color: #0066cc; margin-top: 30px; }}
        h3 {{ color: #666; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #0066cc; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .ok {{ color: green; font-weight: bold; }}
        .warn {{ color: #e67e00; font-weight: bold; }}
        .ko {{ color: red; font-weight: bold; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
        .footer {{ margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>RELAZIONE DI CALCOLO</h1>
        <p><strong>Progetto:</strong> {p.nome}</p>
        <p><strong>Autore:</strong> {p.autore or 'Non specificato'}</p>
        <p><strong>Data:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    </div>

    <h2>1. Dati Generali</h2>
    <table>
        <tr><th>Parametro</th><th>Valore</th></tr>
        <tr><td>Nome progetto</td><td>{p.nome}</td></tr>
        <tr><td>Comune</td><td>{p.sismici.comune or 'Non specificato'}</td></tr>
        <tr><td>Provincia</td><td>{p.sismici.provincia or 'Non specificata'}</td></tr>
        <tr><td>Altitudine</td><td>{p.altitudine:.0f} m s.l.m.</td></tr>
        <tr><td>Numero piani</td><td>{len(p.piani) or p.n_piani}</td></tr>
        <tr><td>Altezza interpiano</td><td>{p.altezza_piano:.2f} m</td></tr>
    </table>

    <h2>2. Parametri Sismici (NTC 2018)</h2>
    <table>
        <tr><th>Parametro</th><th>Valore</th></tr>
        <tr><td>Categoria sottosuolo</td><td>{p.sismici.sottosuolo}</td></tr>
        <tr><td>Categoria topografica</td><td>{p.sismici.topografia}</td></tr>
        <tr><td>Vita nominale VN</td><td>{p.sismici.vita_nominale:.0f} anni</td></tr>
        <tr><td>Classe d'uso</td><td>{p.sismici.classe_uso}</td></tr>
        <tr><td>Fattore di struttura q</td><td>{p.sismici.fattore_struttura:.2f}</td></tr>
    </table>

    <h2>3. Carichi Climatici (NTC 2018)</h2>
    <table>
        <tr><th>Tipo carico</th><th>Valore</th><th>Unita'</th></tr>
        <tr><td>Carico neve qs</td><td>{p.climatici.qs:.2f}</td><td>kN/m2</td></tr>
        <tr><td>Pressione vento p</td><td>{p.climatici.p_vento:.3f}</td><td>kN/m2</td></tr>
    </table>

    <h2>4. Geometria Strutturale</h2>
    <table>
        <tr><th>Elemento</th><th>Quantita'</th><th>Note</th></tr>
        <tr><td>Muri</td><td>{len(p.muri)}</td><td>Area: {area_muri:.1f} m2, Volume: {vol_muri:.1f} m3</td></tr>
        <tr><td>Finestre</td><td>{n_finestre}</td><td></td></tr>
        <tr><td>Porte</td><td>{n_porte}</td><td></td></tr>
        <tr><td>Solai</td><td>{len(p.solai)}</td><td>Carico totale: {carico_tot:.1f} kN</td></tr>
        <tr><td>Cordoli</td><td>{len(p.cordoli)}</td><td></td></tr>
    </table>

    <h2>5. Solai</h2>
    <table>
        <tr><th>Nome</th><th>Piano</th><th>Tipo</th><th>G1 [kN/m2]</th><th>G2 [kN/m2]</th><th>Qk [kN/m2]</th><th>Rigidezza</th></tr>
"""
            for s in p.solai:
                html += f'        <tr><td>{s.nome}</td><td>{s.piano}</td><td>{s.tipo}</td><td>{s.G1:.2f}</td><td>{s.G2:.2f}</td><td>{s.Qk:.2f}</td><td>{s.rigidezza}</td></tr>\n'

            html += f"""    </table>

    {dcr_section}

    <h2>6. Normativa di Riferimento</h2>
    <ul>
        <li>NTC 2018 - Norme Tecniche per le Costruzioni (D.M. 17/01/2018)</li>
        <li>Circolare n. 7/2019 - Istruzioni per l'applicazione delle NTC 2018</li>
    </ul>

    <div class="footer">
        <p>Report generato da <strong>Muratura</strong> - Software per analisi strutturale di edifici in muratura</p>
        <p>GitHub: <a href="https://github.com/mikibart/Muratura">https://github.com/mikibart/Muratura</a></p>
    </div>
</body>
</html>
"""
            # Salva file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)

            self.statusBar().showMessage(f"Report esportato: {filepath}")

            # Chiedi se aprire
            reply = QMessageBox.question(
                self, "Report Esportato",
                f"Report salvato in:\n{filepath}\n\nAprire nel browser?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                import webbrowser
                webbrowser.open(filepath)

        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore esportazione:\n{e}")

    def eliminaSelezionato(self):
        """Elimina l'elemento selezionato"""
        # Conta elementi selezionati
        muri_sel = [m for m in self.progetto.muri if m.selected]
        ap_sel = [a for a in self.progetto.aperture if a.selected]

        if not muri_sel and not ap_sel:
            self.statusBar().showMessage("Nessun elemento selezionato")
            return

        # Rimuovi elementi
        for muro in muri_sel:
            self.progetto.muri.remove(muro)
            # Rimuovi anche aperture associate
            self.progetto.aperture = [a for a in self.progetto.aperture if a.muro != muro.nome]

        for ap in ap_sel:
            self.progetto.aperture.remove(ap)

        # Aggiorna viste
        self.canvas.update()
        self.pannello.aggiornaTabelllaMuri()
        self.pannello.aggiornaTabelllaAperture()
        self.statusBar().showMessage(f"Eliminati: {len(muri_sel)} muri, {len(ap_sel)} aperture")

    def toggleOsnap(self, mode: OsnapMode, checked: bool):
        """Attiva/disattiva un tipo di OSNAP"""
        if checked:
            self.canvas.osnap_mode |= mode
        else:
            self.canvas.osnap_mode &= ~mode

        # Mostra stato nella status bar
        attivi = []
        if OsnapMode.ENDPOINT in self.canvas.osnap_mode:
            attivi.append("END")
        if OsnapMode.MIDPOINT in self.canvas.osnap_mode:
            attivi.append("MID")
        if OsnapMode.INTERSECTION in self.canvas.osnap_mode:
            attivi.append("INT")
        if OsnapMode.PERPENDICULAR in self.canvas.osnap_mode:
            attivi.append("PERP")
        if OsnapMode.GRID in self.canvas.osnap_mode:
            attivi.append("GRID")

        self.statusBar().showMessage(f"OSNAP: {', '.join(attivi) if attivi else 'OFF'}")

    def toggleGriglia(self, checked):
        self.canvas.griglia = checked
        self.canvas.update()

    def setPassoGriglia(self, passo: float):
        """Imposta il passo della griglia"""
        self.canvas.setPassoGriglia(passo)
        self.statusBar().showMessage(f"Passo griglia: {passo*100:.0f} cm")

    def toggleDCR(self, checked):
        """Attiva/disattiva visualizzazione DCR"""
        self.canvas.mostra_dcr = checked
        self.canvas.update()
        if checked:
            self.statusBar().showMessage("Visualizzazione DCR attiva")
        else:
            self.statusBar().showMessage("Visualizzazione DCR disattivata")

    def mostraLegendaDCR(self):
        """Mostra la legenda colori DCR"""
        legenda = """
LEGENDA COLORI DCR (Demand/Capacity Ratio)

Verde scuro:   DCR <= 0.5  - Molto sicuro
Verde chiaro:  DCR <= 0.8  - Sicuro
Giallo:        DCR <= 1.0  - Limite verifica
Arancione:     DCR <= 1.2  - Superamento lieve
Rosso:         DCR > 1.2   - Critico

La verifica e' soddisfatta quando DCR <= 1.0
"""
        QMessageBox.information(self, "Legenda DCR", legenda.strip())

    def eseguiVerificaSemplificata(self):
        """Esegue una verifica semplificata dei muri"""
        if not self.progetto.muri:
            QMessageBox.warning(self, "Avviso", "Nessun muro presente nel progetto")
            return

        # Parametri sismici semplificati
        ag = 0.15  # PGA di default (g)
        if SEISMIC_AVAILABLE and self.progetto.sismici.comune:
            # Cerca nel database sismico
            try:
                analisi = SeismicAnalysis(
                    comune=self.progetto.sismici.comune,
                    VN=self.progetto.sismici.vita_nominale,
                    use_class=UseClass(self.progetto.sismici.classe_uso)
                )
                ag = analisi.ag_SLV
            except:
                pass

        # Calcolo DCR semplificato per ogni muro
        # Formula semplificata: DCR = Taglio_sismico / Resistenza_taglio
        # Taglio_sismico approssimato da massa sismica * ag
        # Resistenza_taglio da fvk * l * t

        # Stima massa per piano
        if self.progetto.solai:
            massa_solaio = sum(s.carico_totale * s.area for s in self.progetto.solai) / 10  # kN -> ton approx
        else:
            massa_solaio = 100  # ton default

        n_muri = len(self.progetto.muri)
        taglio_per_muro = massa_solaio * ag * 10 / max(n_muri, 1)  # kN

        # Resistenza taglio muratura (semplificata)
        fvk0 = 0.2  # MPa (valore minimo NTC)
        gamma_M = 2.0  # Coefficiente sicurezza

        risultati = []
        muri_critici = 0

        for muro in self.progetto.muri:
            # Resistenza taglio (semplificata)
            # Vt = fvd * l * t
            fvd = fvk0 / gamma_M  # MPa = N/mm2 = MN/m2
            l = muro.lunghezza  # m
            t = muro.spessore  # m

            # Taglio resistente
            Vt = fvd * 1000 * l * t  # kN

            # DCR
            dcr = taglio_per_muro / max(Vt, 0.01)

            # Aggiorna muro
            muro.dcr = dcr
            muro.dcr_tipo = "taglio"
            muro.verificato = (dcr <= 1.0)

            if dcr > 1.0:
                muri_critici += 1

            risultati.append((muro.nome, dcr, muro.verificato))

        # Attiva visualizzazione DCR
        self.canvas.mostra_dcr = True
        self.dcr_action.setChecked(True)
        self.canvas.update()

        # Calcolo indice di rischio sismico (IR)
        # IR = PGA_capacita / PGA_domanda
        # PGA_capacita = ag / max(DCR) (semplificato)
        max_dcr = max(m.dcr for m in self.progetto.muri) if self.progetto.muri else 0

        if max_dcr > 0:
            # Indice di rischio: capacita / domanda
            # Se DCR_max = 1 => IR = 1 (struttura al limite)
            # Se DCR_max > 1 => IR < 1 (struttura insufficiente)
            # Se DCR_max < 1 => IR > 1 (struttura sicura)
            indice_rischio = 1.0 / max_dcr
            pga_capacita = ag * indice_rischio  # PGA a cui la struttura raggiunge il limite
        else:
            indice_rischio = 0.0
            pga_capacita = 0.0

        # Salva nel progetto
        self.progetto.indice_rischio = indice_rischio
        self.progetto.pga_domanda = ag
        self.progetto.pga_capacita = pga_capacita

        # Valutazione esito
        if indice_rischio >= 1.0:
            esito = "VERIFICATO"
            esito_dettaglio = "La struttura soddisfa i requisiti sismici NTC 2018"
        elif indice_rischio >= 0.8:
            esito = "CARENTE"
            esito_dettaglio = "Struttura con carenze moderate - interventi consigliati"
        elif indice_rischio >= 0.6:
            esito = "INSUFFICIENTE"
            esito_dettaglio = "Struttura insufficiente - interventi necessari"
        else:
            esito = "CRITICO"
            esito_dettaglio = "Struttura fortemente carente - interventi urgenti"

        # Mostra risultati
        msg = f"""
VERIFICA SEMPLIFICATA COMPLETATA

INDICE DI RISCHIO SISMICO
═══════════════════════════════════════
IR = {indice_rischio:.3f}   ({esito})
═══════════════════════════════════════
PGA domanda:  {ag:.3f} g
PGA capacita': {pga_capacita:.3f} g
{esito_dettaglio}

RISULTATI VERIFICHE
───────────────────────────────────────
Muri analizzati: {n_muri}
Muri verificati: {n_muri - muri_critici}
Muri critici (DCR > 1): {muri_critici}
DCR massimo: {max_dcr:.3f}

PARAMETRI UTILIZZATI
───────────────────────────────────────
ag = {ag:.3f} g
fvk0 = {fvk0:.2f} MPa
gamma_M = {gamma_M:.1f}

NOTA: Verifica semplificata a scopo indicativo.
Per verifiche accurate usare SAM, POR o PUSHOVER.
"""
        QMessageBox.information(self, "Risultati Verifica", msg.strip())

    def toggleQuote(self, checked):
        """Mostra/nascondi quote sui muri"""
        self.canvas.mostra_quote = checked
        self.canvas.update()

    def caricaPlanimetria(self):
        """Apre dialogo per caricare planimetria per il piano corrente"""
        # Trova o crea il piano per la quota Z corrente
        z_corrente = self.canvas.z_corrente
        piano = None
        for p in self.progetto.piani:
            if abs(p.quota - z_corrente) < 0.1:
                piano = p
                break

        if not piano:
            # Crea piano automaticamente
            piano = Piano(
                indice=len(self.progetto.piani),
                quota=z_corrente,
                altezza=3.0,
                massa=10000
            )
            self.progetto.piani.append(piano)
            self.pannello.aggiornaTabelllaPiani()

        # Apri dialogo
        dialogo = DialogoPlanimetria(piano, self)
        if dialogo.exec_() == QDialog.Accepted:
            filepath, scala, x, y, opacita = dialogo.getValues()
            piano.planimetria = filepath
            piano.plan_scala = scala
            piano.plan_x = x
            piano.plan_y = y
            piano.plan_opacita = opacita

            # Aggiorna canvas
            self.canvas.aggiornaPlanimetria()
            self.canvas.update()
            self.statusBar().showMessage(f"Planimetria caricata per piano {piano.indice}")

    def togglePlanimetria(self, checked):
        """Mostra/nasconde la planimetria di sfondo"""
        self.canvas.mostra_planimetria = checked
        self.canvas.update()

    def mostraVista3D(self):
        """Apre la finestra con la vista 3D dell'edificio"""
        if not self.progetto.muri:
            QMessageBox.information(self, "Vista 3D",
                "Nessun muro presente. Disegna prima la struttura.")
            return

        dialogo = Dialogo3D(self.progetto, self)
        dialogo.exec_()

    def zoomFit(self):
        if not self.progetto.muri:
            return

        # Calcola bounding box
        min_x = min(min(m.x1, m.x2) for m in self.progetto.muri)
        max_x = max(max(m.x1, m.x2) for m in self.progetto.muri)
        min_y = min(min(m.y1, m.y2) for m in self.progetto.muri)
        max_y = max(max(m.y1, m.y2) for m in self.progetto.muri)

        # Calcola scala
        width = max_x - min_x + 2
        height = max_y - min_y + 2
        scala_x = self.canvas.width() / width
        scala_y = self.canvas.height() / height
        self.canvas.scala = min(scala_x, scala_y) * 0.8

        # Centra
        centro_x = (min_x + max_x) / 2
        centro_y = (min_y + max_y) / 2
        self.canvas.offset_x = self.canvas.width() / 2 - centro_x * self.canvas.scala
        self.canvas.offset_y = self.canvas.height() / 2 + centro_y * self.canvas.scala

        self.canvas.update()


# ============================================================================
# MAIN
# ============================================================================

def run():
    """Avvia l'applicazione"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    editor = MuraturaEditor()
    editor.show()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(run())
