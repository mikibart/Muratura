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
    QHeaderView, QPushButton, QFrame
)
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal, QSize
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QWheelEvent,
    QMouseEvent, QPainterPath, QKeyEvent, QIcon, QPixmap, QImage
)


# ============================================================================
# STRUTTURE DATI
# ============================================================================

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
class Progetto:
    """Contiene tutti i dati del progetto"""
    nome: str = "Nuovo Progetto"
    autore: str = ""
    muri: List[Muro] = field(default_factory=list)
    aperture: List[Apertura] = field(default_factory=list)
    materiali: List[Materiale] = field(default_factory=list)
    piani: List[Piano] = field(default_factory=list)
    carichi: List[Carico] = field(default_factory=list)
    cordoli: List[Cordolo] = field(default_factory=list)
    filepath: str = ""


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

        # Planimetria di sfondo
        self.planimetria_img: Optional[QPixmap] = None
        self.planimetria_piano: Optional[Piano] = None
        self.mostra_planimetria = True

        # Filtro piano
        self.solo_piano_corrente = False

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

    def snapToGrid(self, p: QPointF, grid_size: float = 0.5) -> QPointF:
        """Snap al punto griglia piu' vicino"""
        x = round(p.x() / grid_size) * grid_size
        y = round(p.y() / grid_size) * grid_size
        return QPointF(x, y)

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
        """Disegna la griglia di sfondo"""
        pen = QPen(QColor(220, 220, 220), 1)
        painter.setPen(pen)

        # Griglia ogni metro
        for x in range(-10, 30):
            p1 = self.worldToScreen(x, -10)
            p2 = self.worldToScreen(x, 30)
            painter.drawLine(p1, p2)

        for y in range(-10, 30):
            p1 = self.worldToScreen(-10, y)
            p2 = self.worldToScreen(30, y)
            painter.drawLine(p1, p2)

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

        # Nome muro al centro
        centro = self.worldToScreen(*muro.centro)
        painter.setPen(QPen(Qt.black, 1))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
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

class DialogoNuovoProgetto(QDialog):
    """Dialogo per creare un nuovo progetto"""

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
        dialogo = DialogoNuovoProgetto(self)
        if dialogo.exec_() == QDialog.Accepted:
            nome, autore = dialogo.getValues()
            self.progetto = Progetto(nome=nome, autore=autore)
            self.progetto.materiali.append(Materiale(
                nome="mattoni", tipo="MATTONI_PIENI",
                malta="BUONA", conservazione="BUONO"
            ))
            self.canvas.setProgetto(self.progetto)
            self.pannello.setProgetto(self.progetto)
            self.aggiornaPianoCombo()
            self.setWindowTitle(f"Muratura Editor - {nome}")

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
