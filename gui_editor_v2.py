#!/usr/bin/env python3
"""
MURATURA GUI Editor v2.0 - Interfaccia Professionale Step-by-Step

Nuova architettura con:
- Ribbon toolbar con tabs (Home, Geometria, Carichi, Analisi, Risultati)
- Project Browser laterale (albero elementi)
- Quick Actions per azioni immediate
- Workflow guidato step-by-step
- Pannello proprietà contestuale
- Status bar con indicatore progresso

Ispirato a: CQ-editor, FreeCAD, SkyCiv
"""

import sys
import math
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum, Flag, auto

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QTableWidget, QTableWidgetItem,
    QToolBar, QAction, QActionGroup, QStatusBar, QMenuBar,
    QFileDialog, QMessageBox, QInputDialog, QDialog,
    QFormLayout, QLineEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QDialogButtonBox, QLabel, QGroupBox,
    QHeaderView, QPushButton, QFrame, QStackedWidget,
    QWizard, QWizardPage, QCompleter, QListWidget, QTextEdit,
    QGridLayout, QRadioButton, QButtonGroup, QScrollArea,
    QTreeWidget, QTreeWidgetItem, QDockWidget, QToolButton,
    QSizePolicy, QProgressBar, QCheckBox
)
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QWheelEvent,
    QMouseEvent, QPainterPath, QKeyEvent, QIcon, QPixmap
)

# Import moduli Muratura
try:
    from Material.seismic import (
        SeismicAnalysis, SoilCategory, TopographicCategory,
        UseClass, LimitState, COMUNI_DATABASE, search_comuni
    )
    SEISMIC_AVAILABLE = True
except ImportError:
    SEISMIC_AVAILABLE = False

try:
    from Material.floors import Floor, FloorType, FloorStiffness, FLOOR_DATABASE
    FLOORS_AVAILABLE = True
except ImportError:
    FLOORS_AVAILABLE = False

try:
    from Material.loads import SnowLoad, WindLoad, calcola_carichi_climatici
    LOADS_AVAILABLE = True
except ImportError:
    LOADS_AVAILABLE = False

try:
    from Material.analyses.por import analyze_por, MaterialProperties, AnalysisOptions
    POR_AVAILABLE = True
except ImportError:
    POR_AVAILABLE = False

try:
    from Material.analyses.sam import analyze_sam
    SAM_AVAILABLE = True
except ImportError:
    SAM_AVAILABLE = False

try:
    from Material.analyses.porflex import analyze_porflex
    PORFLEX_AVAILABLE = True
except ImportError:
    PORFLEX_AVAILABLE = False

try:
    from Material.analyses.limit import LimitAnalysis
    LIMIT_AVAILABLE = True
except ImportError:
    LIMIT_AVAILABLE = False

try:
    from Material.analyses.micro import analyze_micro
    MICRO_AVAILABLE = True
except ImportError:
    MICRO_AVAILABLE = False

try:
    from Material.analyses.fem import _analyze_fem as analyze_fem
    FEM_AVAILABLE = True
except ImportError:
    FEM_AVAILABLE = False

try:
    from Material.analyses.fiber import FiberModel
    FIBER_AVAILABLE = True
except ImportError:
    FIBER_AVAILABLE = False


# ============================================================================
# ANALYSIS METHODS INFO
# ============================================================================

ANALYSIS_METHODS = {
    'POR': {
        'name': 'POR - Pier Only Resistance',
        'description': 'Metodo semplificato per maschi murari isolati. Calcola resistenza a taglio e pressoflessione.',
        'ntc_ref': 'NTC 2018 §7.8.2.2',
        'available': POR_AVAILABLE,
        'complexity': 'Base',
        'time': '< 1 sec'
    },
    'SAM': {
        'name': 'SAM - Simple Analysis Method',
        'description': 'Analisi semplificata a telaio equivalente. Considera redistribuzione delle forze.',
        'ntc_ref': 'NTC 2018 §7.8.1.5',
        'available': SAM_AVAILABLE,
        'complexity': 'Media',
        'time': '1-5 sec'
    },
    'PORFLEX': {
        'name': 'PORFlex - POR con Flessibilità',
        'description': 'Estensione del POR con considerazione della flessibilità dei solai.',
        'ntc_ref': 'Circolare §C8.7.1',
        'available': PORFLEX_AVAILABLE,
        'complexity': 'Media',
        'time': '1-5 sec'
    },
    'LIMIT': {
        'name': 'Analisi Limite Cinematica',
        'description': 'Analisi dei meccanismi di collasso locali (ribaltamento, flessione).',
        'ntc_ref': 'NTC 2018 §8.7.1',
        'available': LIMIT_AVAILABLE,
        'complexity': 'Media',
        'time': '2-10 sec'
    },
    'FEM': {
        'name': 'FEM - Elementi Finiti',
        'description': 'Modellazione agli elementi finiti per analisi dettagliata.',
        'ntc_ref': 'NTC 2018 §7.8.1.4',
        'available': FEM_AVAILABLE,
        'complexity': 'Alta',
        'time': '10-60 sec'
    },
    'FIBER': {
        'name': 'Analisi a Fibre',
        'description': 'Modellazione delle sezioni con discretizzazione a fibre.',
        'ntc_ref': 'Avanzato',
        'available': FIBER_AVAILABLE,
        'complexity': 'Alta',
        'time': '10-60 sec'
    },
    'MICRO': {
        'name': 'Micro-Modellazione',
        'description': 'Modellazione dettagliata dei singoli blocchi e giunti di malta.',
        'ntc_ref': 'Ricerca',
        'available': MICRO_AVAILABLE,
        'complexity': 'Molto Alta',
        'time': '> 60 sec'
    }
}


# ============================================================================
# WORKFLOW STEPS
# ============================================================================

class WorkflowStep(Enum):
    """Steps del workflow guidato"""
    PROGETTO = 0      # Dati progetto + localizzazione
    PIANI = 1         # Definizione piani
    GEOMETRIA = 2     # Disegno muri
    APERTURE = 3      # Inserimento aperture
    FONDAZIONI = 4    # Fondazioni
    CORDOLI = 5       # Cordoli e tiranti
    SOLAI = 6         # Definizione solai
    CARICHI = 7       # Carichi
    MATERIALI = 8     # Materiali
    ANALISI = 9       # Esecuzione analisi
    RISULTATI = 10    # Visualizzazione risultati


STEP_NAMES = {
    WorkflowStep.PROGETTO: "1. Dati Progetto",
    WorkflowStep.PIANI: "2. Piani",
    WorkflowStep.GEOMETRIA: "3. Geometria",
    WorkflowStep.APERTURE: "4. Aperture",
    WorkflowStep.FONDAZIONI: "5. Fondazioni",
    WorkflowStep.CORDOLI: "6. Cordoli/Tiranti",
    WorkflowStep.SOLAI: "7. Solai",
    WorkflowStep.CARICHI: "8. Carichi",
    WorkflowStep.MATERIALI: "9. Materiali",
    WorkflowStep.ANALISI: "10. Analisi",
    WorkflowStep.RISULTATI: "11. Risultati",
}


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Muro:
    nome: str
    x1: float
    y1: float
    x2: float
    y2: float
    spessore: float = 0.30
    altezza: float = 3.0
    materiale: str = "mattoni"
    z: float = 0.0
    selected: bool = False
    dcr: float = 0.0
    verificato: bool = True

    @property
    def lunghezza(self) -> float:
        return math.sqrt((self.x2-self.x1)**2 + (self.y2-self.y1)**2)


@dataclass
class Apertura:
    nome: str
    muro: str
    tipo: str  # "finestra" o "porta"
    larghezza: float
    altezza: float
    posizione: float  # distanza dall'inizio del muro
    altezza_davanzale: float = 0.9
    selected: bool = False


@dataclass
class Piano:
    numero: int
    quota: float
    altezza: float = 3.0
    nome: str = ""

    def __post_init__(self):
        if not self.nome:
            self.nome = f"Piano {self.numero}"


@dataclass
class Solaio:
    nome: str
    piano: int
    tipo: str = "laterocemento"
    luce: float = 5.0
    larghezza: float = 5.0
    peso_proprio: float = 3.2
    carico_variabile: float = 2.0
    categoria_uso: str = "A"

    @property
    def area(self) -> float:
        return self.luce * self.larghezza

    @property
    def carico_totale(self) -> float:
        return self.peso_proprio + 1.5 + self.carico_variabile


@dataclass
class ParametriSismici:
    comune: str = ""
    provincia: str = ""
    sottosuolo: str = "B"
    topografia: str = "T1"
    vita_nominale: float = 50
    classe_uso: int = 2
    fattore_struttura: float = 2.0
    ag_slv: float = 0.0


# ============================================================================
# NUOVE CLASSI STRUTTURALI
# ============================================================================

@dataclass
class Fondazione:
    """Elemento fondazione - plinto, trave rovescia, platea"""
    nome: str
    tipo: str = "trave_rovescia"  # plinto, trave_rovescia, platea, continua
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    larghezza: float = 0.60  # larghezza fondazione
    altezza: float = 0.50   # altezza fondazione
    profondita: float = 1.0  # profondità dal piano campagna
    muro_collegato: str = ""  # nome muro soprastante
    armatura: str = "standard"  # standard, rinforzata
    cls: str = "C25/30"
    acciaio: str = "B450C"
    sigma_amm_terreno: float = 150.0  # kPa
    selected: bool = False

    @property
    def lunghezza(self) -> float:
        return math.sqrt((self.x2-self.x1)**2 + (self.y2-self.y1)**2)

    @property
    def area_base(self) -> float:
        return self.lunghezza * self.larghezza


@dataclass
class Cordolo:
    """Cordolo in c.a. - ring beam"""
    nome: str
    piano: int
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    base: float = 0.30  # larghezza (come muro)
    altezza: float = 0.25
    cls: str = "C25/30"
    acciaio: str = "B450C"
    armatura_longitudinale: str = "4Ø16"
    staffe: str = "Ø8/20"
    muro_collegato: str = ""
    selected: bool = False

    @property
    def lunghezza(self) -> float:
        return math.sqrt((self.x2-self.x1)**2 + (self.y2-self.y1)**2)


@dataclass
class Tirante:
    """Tirante/catena metallica"""
    nome: str
    piano: int
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    diametro: float = 24.0  # mm
    materiale: str = "S275"  # S235, S275, S355
    tipo: str = "barra"  # barra, cavo, piatto
    pretensione: float = 0.0  # kN
    capochiave_tipo: str = "piastra"  # piastra, paletto, incassato
    quota_z: float = 2.8  # quota rispetto al piano
    selected: bool = False

    @property
    def lunghezza(self) -> float:
        return math.sqrt((self.x2-self.x1)**2 + (self.y2-self.y1)**2)

    @property
    def area_sezione(self) -> float:
        """Area sezione in mm²"""
        return math.pi * (self.diametro/2)**2

    @property
    def resistenza_trazione(self) -> float:
        """Resistenza a trazione in kN"""
        fy = {'S235': 235, 'S275': 275, 'S355': 355}.get(self.materiale, 275)
        return self.area_sezione * fy / 1000 / 1.05  # gamma_M0


@dataclass
class Scala:
    """Elemento scala"""
    nome: str
    piano_partenza: int
    piano_arrivo: int
    tipo: str = "a_rampa"  # a_rampa, a_chiocciola, a_gradini_isolati
    larghezza: float = 1.20
    pedata: float = 0.30
    alzata: float = 0.17
    x_partenza: float = 0.0
    y_partenza: float = 0.0
    x_arrivo: float = 0.0
    y_arrivo: float = 0.0
    materiale: str = "muratura"  # muratura, ca, acciaio, legno
    selected: bool = False

    @property
    def n_gradini(self) -> int:
        """Numero gradini approssimato"""
        dislivello = 3.0  # assumiamo 3m per piano
        return int(dislivello / self.alzata) + 1

    @property
    def sviluppo(self) -> float:
        """Sviluppo orizzontale"""
        return self.n_gradini * self.pedata


@dataclass
class Balcone:
    """Balcone o sbalzo"""
    nome: str
    piano: int
    muro_collegato: str
    posizione_su_muro: float  # distanza dall'inizio muro
    larghezza: float = 3.0  # lungo il muro
    profondita: float = 1.20  # sbalzo
    spessore: float = 0.20
    tipo: str = "sbalzo"  # sbalzo, mensola, appoggiato
    materiale: str = "laterocemento"
    parapetto: bool = True
    altezza_parapetto: float = 1.0
    selected: bool = False

    @property
    def area(self) -> float:
        return self.larghezza * self.profondita

    @property
    def peso_proprio(self) -> float:
        """Peso proprio in kN/m²"""
        return self.spessore * 25  # 25 kN/m³ per cls


@dataclass
class Copertura:
    """Definizione copertura"""
    nome: str = "Copertura"
    tipo: str = "a_falde"  # piana, a_falde, a_padiglione, volta
    n_falde: int = 2
    pendenza: float = 30.0  # gradi
    altezza_colmo: float = 1.5  # rispetto all'imposta
    materiale_struttura: str = "legno"  # legno, acciaio, ca, muratura
    materiale_manto: str = "coppi"  # coppi, tegole, lamiera, guaina
    peso_proprio: float = 1.5  # kN/m²
    isolamento: bool = False
    spessore_isolamento: float = 0.10
    gronda: float = 0.50  # sbalzo gronda
    cordolo_sommitale: bool = True
    vertici: List[Tuple[float, float]] = field(default_factory=list)  # poligono base
    selected: bool = False


@dataclass
class Progetto:
    nome: str = "Nuovo Progetto"
    autore: str = ""
    muri: List[Muro] = field(default_factory=list)
    aperture: List[Apertura] = field(default_factory=list)
    piani: List[Piano] = field(default_factory=list)
    solai: List[Solaio] = field(default_factory=list)
    sismici: ParametriSismici = field(default_factory=ParametriSismici)
    # Nuovi elementi strutturali
    fondazioni: List[Fondazione] = field(default_factory=list)
    cordoli: List[Cordolo] = field(default_factory=list)
    tiranti: List[Tirante] = field(default_factory=list)
    scale: List[Scala] = field(default_factory=list)
    balconi: List[Balcone] = field(default_factory=list)
    copertura: Optional[Copertura] = None
    # Parametri progetto
    n_piani: int = 2
    altezza_piano: float = 3.0
    indice_rischio: float = 0.0
    current_step: WorkflowStep = WorkflowStep.PROGETTO
    filepath: str = ""


# ============================================================================
# RIBBON TOOLBAR
# ============================================================================

class RibbonButton(QToolButton):
    """Pulsante grande per Ribbon con icona e testo"""

    def __init__(self, text: str, icon_char: str = "", parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setMinimumSize(70, 60)
        self.setMaximumSize(90, 70)

        # Stile
        self.setStyleSheet("""
            QToolButton {
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 5px;
                font-size: 10px;
            }
            QToolButton:hover {
                background-color: #e0e0e0;
                border: 1px solid #c0c0c0;
            }
            QToolButton:pressed {
                background-color: #d0d0d0;
            }
            QToolButton:checked {
                background-color: #cce0ff;
                border: 1px solid #99c0ff;
            }
        """)


class RibbonPanel(QFrame):
    """Pannello del Ribbon con titolo e pulsanti"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(2)

        # Area pulsanti
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(2)
        layout.addLayout(self.button_layout)

        # Titolo pannello
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 9px; color: #666;")
        layout.addWidget(title_label)

        # Separatore verticale
        self.setStyleSheet("""
            RibbonPanel {
                border-right: 1px solid #d0d0d0;
            }
        """)

    def addButton(self, button: RibbonButton):
        self.button_layout.addWidget(button)


class RibbonTab(QWidget):
    """Tab del Ribbon con più pannelli"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 0)
        self.layout.setSpacing(10)
        self.layout.addStretch()

        self.setStyleSheet("background-color: #f5f5f5;")

    def addPanel(self, panel: RibbonPanel):
        # Inserisce prima dello stretch
        self.layout.insertWidget(self.layout.count() - 1, panel)


class RibbonToolbar(QTabWidget):
    """Toolbar stile Ribbon con tabs"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(95)
        self.setMaximumHeight(95)

        self.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #f5f5f5;
            }
            QTabBar::tab {
                padding: 8px 20px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #f5f5f5;
                border-bottom: 2px solid #0066cc;
            }
            QTabBar::tab:!selected {
                background-color: #e8e8e8;
            }
        """)


# ============================================================================
# PROJECT BROWSER
# ============================================================================

class ProjectBrowser(QDockWidget):
    """Browser ad albero del progetto"""

    itemSelected = pyqtSignal(str, str)  # tipo, nome

    def __init__(self, parent=None):
        super().__init__("Progetto", parent)
        self.setMinimumWidth(200)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(15)
        self.tree.itemClicked.connect(self.onItemClicked)

        self.tree.setStyleSheet("""
            QTreeWidget {
                border: none;
                font-size: 11px;
            }
            QTreeWidget::item {
                padding: 3px;
            }
            QTreeWidget::item:selected {
                background-color: #cce0ff;
            }
        """)

        self.setWidget(self.tree)

        # Nodi principali
        self.root_progetto = QTreeWidgetItem(self.tree, ["📁 Progetto"])
        self.root_piani = QTreeWidgetItem(self.tree, ["📐 Piani"])
        self.root_muri = QTreeWidgetItem(self.tree, ["🧱 Muri"])
        self.root_aperture = QTreeWidgetItem(self.tree, ["🚪 Aperture"])
        self.root_fondazioni = QTreeWidgetItem(self.tree, ["🏗️ Fondazioni"])
        self.root_cordoli = QTreeWidgetItem(self.tree, ["🔗 Cordoli"])
        self.root_tiranti = QTreeWidgetItem(self.tree, ["⛓️ Tiranti"])
        self.root_solai = QTreeWidgetItem(self.tree, ["▭ Solai"])
        self.root_scale = QTreeWidgetItem(self.tree, ["🪜 Scale"])
        self.root_balconi = QTreeWidgetItem(self.tree, ["🏠 Balconi"])
        self.root_copertura = QTreeWidgetItem(self.tree, ["🏠 Copertura"])
        self.root_carichi = QTreeWidgetItem(self.tree, ["⬇ Carichi"])
        self.root_analisi = QTreeWidgetItem(self.tree, ["📊 Analisi"])

        self.tree.expandAll()

    def updateFromProject(self, progetto: Progetto):
        """Aggiorna albero dal progetto"""
        # Pulisci figli
        for root in [self.root_piani, self.root_muri, self.root_aperture,
                     self.root_fondazioni, self.root_cordoli, self.root_tiranti,
                     self.root_solai, self.root_scale, self.root_balconi]:
            root.takeChildren()

        # Progetto
        self.root_progetto.setText(0, f"📁 {progetto.nome}")

        # Piani
        for piano in progetto.piani:
            QTreeWidgetItem(self.root_piani, [f"  {piano.nome} (h={piano.altezza}m)"])

        # Muri
        for muro in progetto.muri:
            dcr_str = f" DCR={muro.dcr:.2f}" if muro.dcr > 0 else ""
            QTreeWidgetItem(self.root_muri, [f"  {muro.nome} ({muro.lunghezza:.1f}m){dcr_str}"])

        # Aperture
        for ap in progetto.aperture:
            QTreeWidgetItem(self.root_aperture, [f"  {ap.nome} ({ap.tipo})"])

        # Solai
        for solaio in progetto.solai:
            QTreeWidgetItem(self.root_solai, [f"  {solaio.nome} ({solaio.tipo})"])

        # Fondazioni
        for fond in progetto.fondazioni:
            QTreeWidgetItem(self.root_fondazioni, [f"  {fond.nome} ({fond.tipo})"])

        # Cordoli
        for cord in progetto.cordoli:
            QTreeWidgetItem(self.root_cordoli, [f"  {cord.nome} P{cord.piano}"])

        # Tiranti
        for tir in progetto.tiranti:
            QTreeWidgetItem(self.root_tiranti, [f"  {tir.nome} Ø{tir.diametro}"])

        # Scale
        for scala in progetto.scale:
            QTreeWidgetItem(self.root_scale, [f"  {scala.nome} ({scala.tipo})"])

        # Balconi
        for balc in progetto.balconi:
            QTreeWidgetItem(self.root_balconi, [f"  {balc.nome} ({balc.profondita}m)"])

        # Copertura
        self.root_copertura.takeChildren()
        if progetto.copertura:
            QTreeWidgetItem(self.root_copertura, [f"  {progetto.copertura.tipo}"])

        # Conta elementi
        self.root_muri.setText(0, f"🧱 Muri ({len(progetto.muri)})")
        self.root_aperture.setText(0, f"🚪 Aperture ({len(progetto.aperture)})")
        self.root_fondazioni.setText(0, f"🏗️ Fondazioni ({len(progetto.fondazioni)})")
        self.root_cordoli.setText(0, f"🔗 Cordoli ({len(progetto.cordoli)})")
        self.root_tiranti.setText(0, f"⛓️ Tiranti ({len(progetto.tiranti)})")
        self.root_solai.setText(0, f"▭ Solai ({len(progetto.solai)})")
        self.root_scale.setText(0, f"🪜 Scale ({len(progetto.scale)})")
        self.root_balconi.setText(0, f"🏠 Balconi ({len(progetto.balconi)})")

        self.tree.expandAll()

    def onItemClicked(self, item, column):
        parent = item.parent()
        if parent:
            tipo = parent.text(0).split()[0]  # Emoji
            nome = item.text(0).strip().split()[0]
            self.itemSelected.emit(tipo, nome)


# ============================================================================
# WORKFLOW PANEL (GUIDA STEP-BY-STEP)
# ============================================================================

class WorkflowPanel(QWidget):
    """Pannello che guida l'utente attraverso gli step"""

    stepClicked = pyqtSignal(WorkflowStep)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_step = WorkflowStep.PROGETTO
        self.completed_steps = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Titolo
        title = QLabel("📋 WORKFLOW")
        title.setStyleSheet("font-weight: bold; font-size: 12px; color: #0066cc;")
        layout.addWidget(title)

        # Step buttons
        self.step_buttons = {}
        for step in WorkflowStep:
            btn = QPushButton(STEP_NAMES[step])
            btn.setCheckable(True)
            btn.setMinimumHeight(35)
            btn.clicked.connect(lambda checked, s=step: self.onStepClicked(s))
            self.step_buttons[step] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Progress
        self.progress = QProgressBar()
        self.progress.setMaximum(len(WorkflowStep))
        self.progress.setTextVisible(True)
        self.progress.setFormat("Completamento: %p%")
        layout.addWidget(self.progress)

        self.updateStyle()

    def setCurrentStep(self, step: WorkflowStep):
        self.current_step = step
        self.updateStyle()

    def markCompleted(self, step: WorkflowStep):
        self.completed_steps.add(step)
        self.progress.setValue(len(self.completed_steps))
        self.updateStyle()

    def updateStyle(self):
        for step, btn in self.step_buttons.items():
            if step in self.completed_steps:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #d4edda;
                        border: 1px solid #28a745;
                        border-radius: 4px;
                        text-align: left;
                        padding-left: 10px;
                    }
                """)
                btn.setText("✓ " + STEP_NAMES[step])
            elif step == self.current_step:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #cce0ff;
                        border: 2px solid #0066cc;
                        border-radius: 4px;
                        font-weight: bold;
                        text-align: left;
                        padding-left: 10px;
                    }
                """)
                btn.setText("▶ " + STEP_NAMES[step])
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f8f9fa;
                        border: 1px solid #dee2e6;
                        border-radius: 4px;
                        text-align: left;
                        padding-left: 10px;
                    }
                """)
                btn.setText("   " + STEP_NAMES[step])

    def onStepClicked(self, step: WorkflowStep):
        self.stepClicked.emit(step)


# ============================================================================
# QUICK ACTIONS PANEL
# ============================================================================

class QuickActionsPanel(QWidget):
    """Pannello azioni rapide per nuovi utenti"""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Titolo
        title = QLabel("🚀 AZIONI RAPIDE")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Seleziona un'azione per iniziare")
        subtitle.setStyleSheet("color: #666; margin-bottom: 20px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        # Grid di pulsanti grandi
        grid = QGridLayout()
        grid.setSpacing(15)

        self.btn_nuovo = self.createBigButton("📄", "Nuovo Progetto",
            "Crea un nuovo progetto con wizard guidato")
        self.btn_apri = self.createBigButton("📂", "Apri Progetto",
            "Apri un progetto esistente (.mur)")
        self.btn_esempio = self.createBigButton("🏠", "Carica Esempio",
            "Carica un edificio di esempio")
        self.btn_guida = self.createBigButton("❓", "Guida Rapida",
            "Visualizza la guida rapida")

        grid.addWidget(self.btn_nuovo, 0, 0)
        grid.addWidget(self.btn_apri, 0, 1)
        grid.addWidget(self.btn_esempio, 1, 0)
        grid.addWidget(self.btn_guida, 1, 1)

        layout.addLayout(grid)
        layout.addStretch()

        # Info
        info = QLabel("Muratura v2.0 - Software per analisi sismica edifici in muratura\nConforme NTC 2018")
        info.setStyleSheet("color: #999; font-size: 10px; margin-top: 20px;")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)

    def createBigButton(self, icon: str, title: str, desc: str) -> QPushButton:
        btn = QPushButton()
        btn.setMinimumSize(180, 120)
        btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #0066cc;
            }
            QPushButton:pressed {
                background-color: #e9ecef;
            }
        """)

        layout = QVBoxLayout(btn)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 32px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        desc_label = QLabel(desc)
        desc_label.setStyleSheet("color: #666; font-size: 9px;")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        return btn


# ============================================================================
# STEP PANELS (pannelli per ogni step del workflow)
# ============================================================================

class StepProgettoPanel(QWidget):
    """Step 1: Dati progetto e localizzazione"""

    dataChanged = pyqtSignal()

    def __init__(self, progetto: Progetto, parent=None):
        super().__init__(parent)
        self.progetto = progetto

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("📋 STEP 1: DATI PROGETTO E LOCALIZZAZIONE SISMICA")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #0066cc; padding: 10px;")
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Dati generali
        gen_group = QGroupBox("Dati Generali")
        gen_layout = QFormLayout()

        self.nome_edit = QLineEdit(progetto.nome)
        self.nome_edit.textChanged.connect(self.onDataChanged)
        gen_layout.addRow("Nome Progetto:", self.nome_edit)

        self.autore_edit = QLineEdit(progetto.autore)
        gen_layout.addRow("Autore:", self.autore_edit)

        self.n_piani_spin = QSpinBox()
        self.n_piani_spin.setRange(1, 10)
        self.n_piani_spin.setValue(progetto.n_piani)
        gen_layout.addRow("Numero Piani:", self.n_piani_spin)

        self.h_piano_spin = QDoubleSpinBox()
        self.h_piano_spin.setRange(2.0, 6.0)
        self.h_piano_spin.setValue(progetto.altezza_piano)
        self.h_piano_spin.setSuffix(" m")
        gen_layout.addRow("Altezza Interpiano:", self.h_piano_spin)

        gen_group.setLayout(gen_layout)
        scroll_layout.addWidget(gen_group)

        # Localizzazione sismica
        sismica_group = QGroupBox("🌍 Localizzazione Sismica")
        sismica_layout = QFormLayout()

        self.comune_edit = QLineEdit(progetto.sismici.comune)
        self.comune_edit.setPlaceholderText("Digita il nome del comune...")
        self.comune_edit.textChanged.connect(self.onComuneChanged)
        sismica_layout.addRow("Comune:", self.comune_edit)

        # Completer per comuni
        if SEISMIC_AVAILABLE:
            comuni_list = list(COMUNI_DATABASE.keys())
            completer = QCompleter(comuni_list)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            self.comune_edit.setCompleter(completer)

        self.provincia_label = QLabel(progetto.sismici.provincia or "-")
        sismica_layout.addRow("Provincia:", self.provincia_label)

        self.ag_label = QLabel(f"{progetto.sismici.ag_slv:.3f} g" if progetto.sismici.ag_slv else "-")
        self.ag_label.setStyleSheet("font-weight: bold; color: #cc0000;")
        sismica_layout.addRow("ag (SLV):", self.ag_label)

        self.sottosuolo_combo = QComboBox()
        self.sottosuolo_combo.addItems(["A", "B", "C", "D", "E"])
        self.sottosuolo_combo.setCurrentText(progetto.sismici.sottosuolo)
        sismica_layout.addRow("Categoria Sottosuolo:", self.sottosuolo_combo)

        self.topografia_combo = QComboBox()
        self.topografia_combo.addItems(["T1", "T2", "T3", "T4"])
        self.topografia_combo.setCurrentText(progetto.sismici.topografia)
        sismica_layout.addRow("Categoria Topografica:", self.topografia_combo)

        self.vn_spin = QSpinBox()
        self.vn_spin.setRange(10, 100)
        self.vn_spin.setValue(int(progetto.sismici.vita_nominale))
        self.vn_spin.setSuffix(" anni")
        sismica_layout.addRow("Vita Nominale:", self.vn_spin)

        self.classe_combo = QComboBox()
        self.classe_combo.addItems(["I", "II", "III", "IV"])
        self.classe_combo.setCurrentIndex(progetto.sismici.classe_uso - 1)
        sismica_layout.addRow("Classe d'Uso:", self.classe_combo)

        sismica_group.setLayout(sismica_layout)
        scroll_layout.addWidget(sismica_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Pulsante avanti
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_avanti = QPushButton("Avanti → Definizione Piani")
        self.btn_avanti.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                font-weight: bold;
                padding: 10px 30px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0052a3;
            }
        """)
        btn_layout.addWidget(self.btn_avanti)
        layout.addLayout(btn_layout)

    def onComuneChanged(self, text):
        if SEISMIC_AVAILABLE and text.upper() in COMUNI_DATABASE:
            try:
                analisi = SeismicAnalysis(
                    comune=text.upper(),
                    VN=self.vn_spin.value(),
                    use_class=UseClass(self.classe_combo.currentIndex() + 1)
                )
                self.provincia_label.setText(COMUNI_DATABASE[text.upper()].get('provincia', '-'))
                self.ag_label.setText(f"{analisi.ag_SLV:.3f} g")
                self.progetto.sismici.ag_slv = analisi.ag_SLV
            except:
                pass

    def onDataChanged(self):
        self.progetto.nome = self.nome_edit.text()
        self.dataChanged.emit()

    def saveData(self):
        self.progetto.nome = self.nome_edit.text()
        self.progetto.autore = self.autore_edit.text()
        self.progetto.n_piani = self.n_piani_spin.value()
        self.progetto.altezza_piano = self.h_piano_spin.value()
        self.progetto.sismici.comune = self.comune_edit.text().upper()
        self.progetto.sismici.sottosuolo = self.sottosuolo_combo.currentText()
        self.progetto.sismici.topografia = self.topografia_combo.currentText()
        self.progetto.sismici.vita_nominale = self.vn_spin.value()
        self.progetto.sismici.classe_uso = self.classe_combo.currentIndex() + 1

        # Crea piani
        self.progetto.piani = []
        for i in range(self.progetto.n_piani):
            self.progetto.piani.append(Piano(
                numero=i,
                quota=i * self.progetto.altezza_piano,
                altezza=self.progetto.altezza_piano
            ))


class StepPianiPanel(QWidget):
    """Step 2: Definizione dettagliata piani"""

    def __init__(self, progetto: Progetto, parent=None):
        super().__init__(parent)
        self.progetto = progetto

        layout = QVBoxLayout(self)

        header = QLabel("📐 STEP 2: DEFINIZIONE PIANI")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #0066cc; padding: 10px;")
        layout.addWidget(header)

        info = QLabel("Configura l'altezza di ogni piano. Puoi modificare i valori nella tabella.")
        info.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info)

        # Tabella piani
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Piano", "Nome", "Quota [m]", "Altezza [m]"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # Pulsanti
        btn_layout = QHBoxLayout()

        btn_indietro = QPushButton("← Indietro")
        btn_indietro.clicked.connect(lambda: self.parent().goToStep(WorkflowStep.PROGETTO))
        btn_layout.addWidget(btn_indietro)

        btn_layout.addStretch()

        self.btn_avanti = QPushButton("Avanti → Disegno Muri")
        self.btn_avanti.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                font-weight: bold;
                padding: 10px 30px;
                border-radius: 5px;
            }
        """)
        btn_layout.addWidget(self.btn_avanti)
        layout.addLayout(btn_layout)

    def refresh(self):
        self.table.setRowCount(len(self.progetto.piani))
        for i, piano in enumerate(self.progetto.piani):
            self.table.setItem(i, 0, QTableWidgetItem(str(piano.numero)))
            self.table.setItem(i, 1, QTableWidgetItem(piano.nome))
            self.table.setItem(i, 2, QTableWidgetItem(f"{piano.quota:.2f}"))

            h_spin = QDoubleSpinBox()
            h_spin.setRange(2.0, 6.0)
            h_spin.setValue(piano.altezza)
            h_spin.setSuffix(" m")
            self.table.setCellWidget(i, 3, h_spin)

    def saveData(self):
        for i, piano in enumerate(self.progetto.piani):
            h_spin = self.table.cellWidget(i, 3)
            if h_spin:
                piano.altezza = h_spin.value()
            # Ricalcola quote
            if i > 0:
                piano.quota = self.progetto.piani[i-1].quota + self.progetto.piani[i-1].altezza


# ============================================================================
# DIALOGO APERTURA (porte e finestre)
# ============================================================================

class DialogoApertura(QDialog):
    """Dialogo per inserire porte e finestre"""

    def __init__(self, progetto: Progetto, muro_selezionato: str = "", parent=None):
        super().__init__(parent)
        self.progetto = progetto
        self.apertura_creata = None

        self.setWindowTitle("🚪 Inserisci Apertura")
        self.setMinimumSize(450, 500)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("Inserisci Porta o Finestra")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #0066cc;")
        layout.addWidget(header)

        # Tipo apertura
        tipo_group = QGroupBox("Tipo Apertura")
        tipo_layout = QHBoxLayout()
        self.tipo_group = QButtonGroup()

        self.rb_finestra = QRadioButton("🪟 Finestra")
        self.rb_finestra.setChecked(True)
        self.tipo_group.addButton(self.rb_finestra)
        tipo_layout.addWidget(self.rb_finestra)

        self.rb_porta = QRadioButton("🚪 Porta")
        self.tipo_group.addButton(self.rb_porta)
        tipo_layout.addWidget(self.rb_porta)

        self.rb_portafinestra = QRadioButton("🚪🪟 Porta-Finestra")
        self.tipo_group.addButton(self.rb_portafinestra)
        tipo_layout.addWidget(self.rb_portafinestra)

        tipo_group.setLayout(tipo_layout)
        layout.addWidget(tipo_group)

        # Selezione muro
        muro_group = QGroupBox("Muro")
        muro_layout = QFormLayout()

        self.muro_combo = QComboBox()
        for muro in progetto.muri:
            self.muro_combo.addItem(f"{muro.nome} ({muro.lunghezza:.2f}m)", muro.nome)
        if muro_selezionato:
            idx = self.muro_combo.findData(muro_selezionato)
            if idx >= 0:
                self.muro_combo.setCurrentIndex(idx)
        self.muro_combo.currentIndexChanged.connect(self.onMuroChanged)
        muro_layout.addRow("Muro:", self.muro_combo)

        self.muro_info = QLabel("-")
        self.muro_info.setStyleSheet("color: #666;")
        muro_layout.addRow("Info:", self.muro_info)

        muro_group.setLayout(muro_layout)
        layout.addWidget(muro_group)

        # Dimensioni
        dim_group = QGroupBox("Dimensioni")
        dim_layout = QFormLayout()

        self.larghezza_spin = QDoubleSpinBox()
        self.larghezza_spin.setRange(0.40, 4.0)
        self.larghezza_spin.setValue(1.20)
        self.larghezza_spin.setSuffix(" m")
        self.larghezza_spin.setDecimals(2)
        dim_layout.addRow("Larghezza:", self.larghezza_spin)

        self.altezza_spin = QDoubleSpinBox()
        self.altezza_spin.setRange(0.40, 3.0)
        self.altezza_spin.setValue(1.40)
        self.altezza_spin.setSuffix(" m")
        dim_layout.addRow("Altezza:", self.altezza_spin)

        self.davanzale_spin = QDoubleSpinBox()
        self.davanzale_spin.setRange(0.0, 2.0)
        self.davanzale_spin.setValue(0.90)
        self.davanzale_spin.setSuffix(" m")
        dim_layout.addRow("Altezza Davanzale:", self.davanzale_spin)

        dim_group.setLayout(dim_layout)
        layout.addWidget(dim_group)

        # Posizione
        pos_group = QGroupBox("Posizione sul Muro")
        pos_layout = QFormLayout()

        self.posizione_spin = QDoubleSpinBox()
        self.posizione_spin.setRange(0.0, 20.0)
        self.posizione_spin.setValue(1.0)
        self.posizione_spin.setSuffix(" m")
        self.posizione_spin.setDecimals(2)
        pos_layout.addRow("Distanza da Inizio:", self.posizione_spin)

        self.centra_btn = QPushButton("📍 Centra sul Muro")
        self.centra_btn.clicked.connect(self.centraSuMuro)
        pos_layout.addRow("", self.centra_btn)

        pos_group.setLayout(pos_layout)
        layout.addWidget(pos_group)

        # Presets veloci
        preset_group = QGroupBox("⚡ Preset Veloci")
        preset_layout = QGridLayout()

        btn_f1 = QPushButton("Finestra\n120x140")
        btn_f1.clicked.connect(lambda: self.applicaPreset("finestra", 1.20, 1.40, 0.90))
        preset_layout.addWidget(btn_f1, 0, 0)

        btn_f2 = QPushButton("Finestra\n80x120")
        btn_f2.clicked.connect(lambda: self.applicaPreset("finestra", 0.80, 1.20, 1.00))
        preset_layout.addWidget(btn_f2, 0, 1)

        btn_p1 = QPushButton("Porta\n90x210")
        btn_p1.clicked.connect(lambda: self.applicaPreset("porta", 0.90, 2.10, 0.0))
        preset_layout.addWidget(btn_p1, 1, 0)

        btn_p2 = QPushButton("Porta\n80x210")
        btn_p2.clicked.connect(lambda: self.applicaPreset("porta", 0.80, 2.10, 0.0))
        preset_layout.addWidget(btn_p2, 1, 1)

        btn_pf = QPushButton("Portafinestra\n120x220")
        btn_pf.clicked.connect(lambda: self.applicaPreset("portafinestra", 1.20, 2.20, 0.0))
        preset_layout.addWidget(btn_pf, 2, 0)

        btn_pf2 = QPushButton("Portafinestra\n180x220")
        btn_pf2.clicked.connect(lambda: self.applicaPreset("portafinestra", 1.80, 2.20, 0.0))
        preset_layout.addWidget(btn_pf2, 2, 1)

        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)

        # Connessione tipo -> davanzale
        self.rb_porta.toggled.connect(lambda c: self.davanzale_spin.setValue(0.0) if c else None)
        self.rb_portafinestra.toggled.connect(lambda c: self.davanzale_spin.setValue(0.0) if c else None)

        # Pulsanti
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Annulla")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_layout.addStretch()

        btn_ok = QPushButton("✓ Inserisci Apertura")
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #218838; }
        """)
        btn_ok.clicked.connect(self.creaApertura)
        btn_layout.addWidget(btn_ok)

        layout.addLayout(btn_layout)

        # Aggiorna info muro
        self.onMuroChanged()

    def onMuroChanged(self):
        muro_nome = self.muro_combo.currentData()
        muro = next((m for m in self.progetto.muri if m.nome == muro_nome), None)
        if muro:
            self.muro_info.setText(f"L={muro.lunghezza:.2f}m, s={muro.spessore}m, h={muro.altezza}m")
            self.posizione_spin.setMaximum(muro.lunghezza - self.larghezza_spin.value())

    def centraSuMuro(self):
        muro_nome = self.muro_combo.currentData()
        muro = next((m for m in self.progetto.muri if m.nome == muro_nome), None)
        if muro:
            pos = (muro.lunghezza - self.larghezza_spin.value()) / 2
            self.posizione_spin.setValue(max(0, pos))

    def applicaPreset(self, tipo: str, larghezza: float, altezza: float, davanzale: float):
        if tipo == "finestra":
            self.rb_finestra.setChecked(True)
        elif tipo == "porta":
            self.rb_porta.setChecked(True)
        else:
            self.rb_portafinestra.setChecked(True)

        self.larghezza_spin.setValue(larghezza)
        self.altezza_spin.setValue(altezza)
        self.davanzale_spin.setValue(davanzale)

    def creaApertura(self):
        muro_nome = self.muro_combo.currentData()
        if not muro_nome:
            QMessageBox.warning(self, "Errore", "Seleziona un muro")
            return

        # Determina tipo
        if self.rb_porta.isChecked():
            tipo = "porta"
        elif self.rb_portafinestra.isChecked():
            tipo = "portafinestra"
        else:
            tipo = "finestra"

        # Crea nome unico
        prefisso = "P" if tipo == "porta" else "PF" if tipo == "portafinestra" else "F"
        n = len([a for a in self.progetto.aperture if a.tipo == tipo]) + 1
        nome = f"{prefisso}{n}"

        # Crea apertura
        self.apertura_creata = Apertura(
            nome=nome,
            muro=muro_nome,
            tipo=tipo,
            larghezza=self.larghezza_spin.value(),
            altezza=self.altezza_spin.value(),
            posizione=self.posizione_spin.value(),
            altezza_davanzale=self.davanzale_spin.value()
        )

        self.accept()


# ============================================================================
# DIALOGO FONDAZIONE
# ============================================================================

class DialogoFondazione(QDialog):
    """Dialogo per inserire fondazioni"""

    def __init__(self, progetto: Progetto, muro_selezionato: str = "", parent=None):
        super().__init__(parent)
        self.progetto = progetto
        self.fondazione_creata = None

        self.setWindowTitle("🏗️ Inserisci Fondazione")
        self.setMinimumSize(500, 550)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("Definizione Fondazione")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #0066cc;")
        layout.addWidget(header)

        # Tipo fondazione
        tipo_group = QGroupBox("Tipo Fondazione")
        tipo_layout = QVBoxLayout()

        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems([
            "Trave Rovescia (continua)",
            "Plinto Isolato",
            "Platea di Fondazione",
            "Fondazione a Nastro"
        ])
        self.tipo_combo.currentIndexChanged.connect(self.onTipoChanged)
        tipo_layout.addWidget(self.tipo_combo)

        self.tipo_desc = QLabel("Fondazione continua sotto il muro")
        self.tipo_desc.setStyleSheet("color: #666; font-style: italic;")
        tipo_layout.addWidget(self.tipo_desc)

        tipo_group.setLayout(tipo_layout)
        layout.addWidget(tipo_group)

        # Collegamento muro
        muro_group = QGroupBox("Muro Soprastante")
        muro_layout = QFormLayout()

        self.muro_combo = QComboBox()
        self.muro_combo.addItem("(Nessuno - posizionamento libero)", "")
        for muro in progetto.muri:
            self.muro_combo.addItem(f"{muro.nome} ({muro.lunghezza:.2f}m)", muro.nome)
        if muro_selezionato:
            idx = self.muro_combo.findData(muro_selezionato)
            if idx >= 0:
                self.muro_combo.setCurrentIndex(idx)
        self.muro_combo.currentIndexChanged.connect(self.onMuroChanged)
        muro_layout.addRow("Muro:", self.muro_combo)

        self.auto_pos = QCheckBox("Posiziona automaticamente sotto il muro")
        self.auto_pos.setChecked(True)
        muro_layout.addRow("", self.auto_pos)

        muro_group.setLayout(muro_layout)
        layout.addWidget(muro_group)

        # Dimensioni
        dim_group = QGroupBox("Dimensioni Geometriche")
        dim_layout = QFormLayout()

        self.larghezza_spin = QDoubleSpinBox()
        self.larghezza_spin.setRange(0.30, 2.0)
        self.larghezza_spin.setValue(0.60)
        self.larghezza_spin.setSuffix(" m")
        dim_layout.addRow("Larghezza (B):", self.larghezza_spin)

        self.altezza_spin = QDoubleSpinBox()
        self.altezza_spin.setRange(0.30, 1.5)
        self.altezza_spin.setValue(0.50)
        self.altezza_spin.setSuffix(" m")
        dim_layout.addRow("Altezza (H):", self.altezza_spin)

        self.profondita_spin = QDoubleSpinBox()
        self.profondita_spin.setRange(0.50, 3.0)
        self.profondita_spin.setValue(1.0)
        self.profondita_spin.setSuffix(" m")
        dim_layout.addRow("Profondità (D):", self.profondita_spin)

        dim_group.setLayout(dim_layout)
        layout.addWidget(dim_group)

        # Materiali
        mat_group = QGroupBox("Materiali")
        mat_layout = QFormLayout()

        self.cls_combo = QComboBox()
        self.cls_combo.addItems(["C20/25", "C25/30", "C28/35", "C30/37"])
        self.cls_combo.setCurrentText("C25/30")
        mat_layout.addRow("Classe Cls:", self.cls_combo)

        self.acciaio_combo = QComboBox()
        self.acciaio_combo.addItems(["B450C", "B450A", "B500B"])
        mat_layout.addRow("Acciaio:", self.acciaio_combo)

        self.armatura_combo = QComboBox()
        self.armatura_combo.addItems(["Standard", "Rinforzata", "Leggera"])
        mat_layout.addRow("Armatura:", self.armatura_combo)

        mat_group.setLayout(mat_layout)
        layout.addWidget(mat_group)

        # Terreno
        terr_group = QGroupBox("Terreno")
        terr_layout = QFormLayout()

        self.sigma_spin = QDoubleSpinBox()
        self.sigma_spin.setRange(50, 500)
        self.sigma_spin.setValue(150)
        self.sigma_spin.setSuffix(" kPa")
        terr_layout.addRow("σ ammissibile:", self.sigma_spin)

        terr_group.setLayout(terr_layout)
        layout.addWidget(terr_group)

        # Pulsanti
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Annulla")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_layout.addStretch()

        btn_ok = QPushButton("✓ Crea Fondazione")
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
        """)
        btn_ok.clicked.connect(self.creaFondazione)
        btn_layout.addWidget(btn_ok)

        layout.addLayout(btn_layout)

    def onTipoChanged(self, idx):
        descs = [
            "Fondazione continua sotto il muro - la più comune per muratura",
            "Fondazione isolata per pilastri o carichi concentrati",
            "Fondazione unica per tutto l'edificio - terreni scarsi",
            "Fondazione continua a sezione rettangolare"
        ]
        self.tipo_desc.setText(descs[idx] if idx < len(descs) else "")

    def onMuroChanged(self):
        muro_nome = self.muro_combo.currentData()
        self.auto_pos.setEnabled(bool(muro_nome))

    def creaFondazione(self):
        # Determina tipo
        tipo_map = {0: "trave_rovescia", 1: "plinto", 2: "platea", 3: "continua"}
        tipo = tipo_map.get(self.tipo_combo.currentIndex(), "trave_rovescia")

        # Crea nome
        n = len(self.progetto.fondazioni) + 1
        nome = f"F{n}"

        # Coordinate (da muro se selezionato)
        x1, y1, x2, y2 = 0, 0, 0, 0
        muro_nome = self.muro_combo.currentData()
        if muro_nome and self.auto_pos.isChecked():
            muro = next((m for m in self.progetto.muri if m.nome == muro_nome), None)
            if muro:
                x1, y1, x2, y2 = muro.x1, muro.y1, muro.x2, muro.y2

        self.fondazione_creata = Fondazione(
            nome=nome,
            tipo=tipo,
            x1=x1, y1=y1, x2=x2, y2=y2,
            larghezza=self.larghezza_spin.value(),
            altezza=self.altezza_spin.value(),
            profondita=self.profondita_spin.value(),
            muro_collegato=muro_nome or "",
            cls=self.cls_combo.currentText(),
            acciaio=self.acciaio_combo.currentText(),
            armatura=self.armatura_combo.currentText().lower(),
            sigma_amm_terreno=self.sigma_spin.value()
        )

        self.accept()


# ============================================================================
# STEP FONDAZIONI PANEL
# ============================================================================

class StepFondazioniPanel(QWidget):
    """Step per definizione fondazioni"""

    def __init__(self, progetto: Progetto, parent=None):
        super().__init__(parent)
        self.progetto = progetto

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("🏗️ STEP 5: FONDAZIONI")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #0066cc; padding: 10px;")
        layout.addWidget(header)

        info = QLabel("Definisci le fondazioni sotto ogni muro portante. Per edifici nuovi si consiglia trave rovescia continua.")
        info.setStyleSheet("color: #666; padding: 5px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Toolbar
        toolbar = QHBoxLayout()

        self.btn_aggiungi = QPushButton("➕ Aggiungi Fondazione")
        self.btn_aggiungi.clicked.connect(self.aggiungiFondazione)
        toolbar.addWidget(self.btn_aggiungi)

        self.btn_auto = QPushButton("⚡ Genera Automaticamente")
        self.btn_auto.setToolTip("Crea fondazioni automatiche sotto tutti i muri")
        self.btn_auto.clicked.connect(self.generaAutomatiche)
        toolbar.addWidget(self.btn_auto)

        toolbar.addStretch()

        self.btn_elimina = QPushButton("🗑️ Elimina")
        self.btn_elimina.clicked.connect(self.eliminaFondazione)
        toolbar.addWidget(self.btn_elimina)

        layout.addLayout(toolbar)

        # Tabella fondazioni
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Nome", "Tipo", "Muro", "L [m]", "B [m]", "H [m]", "σ [kPa]"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # Riepilogo
        self.summary = QLabel("")
        self.summary.setStyleSheet("padding: 10px; background: #f8f9fa; border-radius: 5px;")
        layout.addWidget(self.summary)

        # Pulsanti navigazione
        btn_layout = QHBoxLayout()

        btn_indietro = QPushButton("← Indietro")
        btn_layout.addWidget(btn_indietro)

        btn_layout.addStretch()

        self.btn_avanti = QPushButton("Avanti → Cordoli/Tiranti")
        self.btn_avanti.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                font-weight: bold;
                padding: 10px 30px;
                border-radius: 5px;
            }
        """)
        btn_layout.addWidget(self.btn_avanti)

        layout.addLayout(btn_layout)

    def refresh(self):
        self.table.setRowCount(len(self.progetto.fondazioni))
        for i, fond in enumerate(self.progetto.fondazioni):
            self.table.setItem(i, 0, QTableWidgetItem(fond.nome))
            self.table.setItem(i, 1, QTableWidgetItem(fond.tipo))
            self.table.setItem(i, 2, QTableWidgetItem(fond.muro_collegato or "-"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{fond.lunghezza:.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{fond.larghezza:.2f}"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{fond.altezza:.2f}"))
            self.table.setItem(i, 6, QTableWidgetItem(f"{fond.sigma_amm_terreno:.0f}"))

        # Riepilogo
        n_fond = len(self.progetto.fondazioni)
        n_muri = len(self.progetto.muri)
        copertura = n_fond / n_muri * 100 if n_muri > 0 else 0

        self.summary.setText(f"""
📊 Riepilogo: {n_fond} fondazioni definite per {n_muri} muri ({copertura:.0f}% copertura)
{'⚠️ Alcuni muri non hanno fondazione!' if copertura < 100 else '✓ Tutti i muri hanno fondazione'}
        """.strip())

    def aggiungiFondazione(self):
        dlg = DialogoFondazione(self.progetto, parent=self)
        if dlg.exec_() == QDialog.Accepted and dlg.fondazione_creata:
            self.progetto.fondazioni.append(dlg.fondazione_creata)
            self.refresh()

    def generaAutomatiche(self):
        """Genera fondazioni automatiche per tutti i muri senza fondazione"""
        muri_con_fond = {f.muro_collegato for f in self.progetto.fondazioni}
        nuove = 0

        for muro in self.progetto.muri:
            if muro.nome not in muri_con_fond:
                n = len(self.progetto.fondazioni) + 1
                fond = Fondazione(
                    nome=f"F{n}",
                    tipo="trave_rovescia",
                    x1=muro.x1, y1=muro.y1,
                    x2=muro.x2, y2=muro.y2,
                    larghezza=max(0.60, muro.spessore * 2),
                    altezza=0.50,
                    profondita=1.0,
                    muro_collegato=muro.nome
                )
                self.progetto.fondazioni.append(fond)
                nuove += 1

        self.refresh()
        QMessageBox.information(self, "Fondazioni Generate",
            f"Create {nuove} fondazioni automatiche")

    def eliminaFondazione(self):
        row = self.table.currentRow()
        if row >= 0 and row < len(self.progetto.fondazioni):
            del self.progetto.fondazioni[row]
            self.refresh()


# ============================================================================
# STEP CORDOLI/TIRANTI PANEL
# ============================================================================

class StepCordoliPanel(QWidget):
    """Step per cordoli e tiranti"""

    def __init__(self, progetto: Progetto, parent=None):
        super().__init__(parent)
        self.progetto = progetto

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("🔗 STEP 6: CORDOLI E TIRANTI")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #0066cc; padding: 10px;")
        layout.addWidget(header)

        info = QLabel("I cordoli in c.a. e i tiranti metallici migliorano il comportamento scatolare dell'edificio.")
        info.setStyleSheet("color: #666; padding: 5px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Tab per cordoli e tiranti
        tabs = QTabWidget()

        # Tab Cordoli
        cordoli_tab = QWidget()
        cordoli_layout = QVBoxLayout(cordoli_tab)

        cordoli_toolbar = QHBoxLayout()
        btn_add_cordolo = QPushButton("➕ Aggiungi Cordolo")
        btn_add_cordolo.clicked.connect(self.aggiungiCordolo)
        cordoli_toolbar.addWidget(btn_add_cordolo)
        btn_auto_cordoli = QPushButton("⚡ Genera su Tutti i Muri")
        btn_auto_cordoli.clicked.connect(self.generaCordoliAutomatici)
        cordoli_toolbar.addWidget(btn_auto_cordoli)
        cordoli_toolbar.addStretch()
        cordoli_layout.addLayout(cordoli_toolbar)

        self.cordoli_table = QTableWidget()
        self.cordoli_table.setColumnCount(6)
        self.cordoli_table.setHorizontalHeaderLabels([
            "Nome", "Piano", "Muro", "L [m]", "b×h [cm]", "Armatura"
        ])
        cordoli_layout.addWidget(self.cordoli_table)

        tabs.addTab(cordoli_tab, "🧱 Cordoli")

        # Tab Tiranti
        tiranti_tab = QWidget()
        tiranti_layout = QVBoxLayout(tiranti_tab)

        tiranti_toolbar = QHBoxLayout()
        btn_add_tirante = QPushButton("➕ Aggiungi Tirante")
        btn_add_tirante.clicked.connect(self.aggiungiTirante)
        tiranti_toolbar.addWidget(btn_add_tirante)
        tiranti_toolbar.addStretch()
        tiranti_layout.addLayout(tiranti_toolbar)

        self.tiranti_table = QTableWidget()
        self.tiranti_table.setColumnCount(6)
        self.tiranti_table.setHorizontalHeaderLabels([
            "Nome", "Piano", "Ø [mm]", "L [m]", "Materiale", "Resistenza [kN]"
        ])
        tiranti_layout.addWidget(self.tiranti_table)

        tabs.addTab(tiranti_tab, "⛓️ Tiranti")

        layout.addWidget(tabs)

        # Pulsanti navigazione
        btn_layout = QHBoxLayout()
        btn_indietro = QPushButton("← Indietro")
        btn_layout.addWidget(btn_indietro)
        btn_layout.addStretch()
        self.btn_avanti = QPushButton("Avanti → Solai")
        self.btn_avanti.setStyleSheet("""
            QPushButton {
                background-color: #0066cc; color: white;
                font-weight: bold; padding: 10px 30px; border-radius: 5px;
            }
        """)
        btn_layout.addWidget(self.btn_avanti)
        layout.addLayout(btn_layout)

    def refresh(self):
        # Cordoli
        self.cordoli_table.setRowCount(len(self.progetto.cordoli))
        for i, c in enumerate(self.progetto.cordoli):
            self.cordoli_table.setItem(i, 0, QTableWidgetItem(c.nome))
            self.cordoli_table.setItem(i, 1, QTableWidgetItem(str(c.piano)))
            self.cordoli_table.setItem(i, 2, QTableWidgetItem(c.muro_collegato or "-"))
            self.cordoli_table.setItem(i, 3, QTableWidgetItem(f"{c.lunghezza:.2f}"))
            self.cordoli_table.setItem(i, 4, QTableWidgetItem(f"{c.base*100:.0f}×{c.altezza*100:.0f}"))
            self.cordoli_table.setItem(i, 5, QTableWidgetItem(c.armatura_longitudinale))

        # Tiranti
        self.tiranti_table.setRowCount(len(self.progetto.tiranti))
        for i, t in enumerate(self.progetto.tiranti):
            self.tiranti_table.setItem(i, 0, QTableWidgetItem(t.nome))
            self.tiranti_table.setItem(i, 1, QTableWidgetItem(str(t.piano)))
            self.tiranti_table.setItem(i, 2, QTableWidgetItem(f"{t.diametro:.0f}"))
            self.tiranti_table.setItem(i, 3, QTableWidgetItem(f"{t.lunghezza:.2f}"))
            self.tiranti_table.setItem(i, 4, QTableWidgetItem(t.materiale))
            self.tiranti_table.setItem(i, 5, QTableWidgetItem(f"{t.resistenza_trazione:.1f}"))

    def aggiungiCordolo(self):
        # TODO: Dialogo cordolo
        QMessageBox.information(self, "Info", "Seleziona un muro e aggiungi il cordolo")

    def aggiungiTirante(self):
        # TODO: Dialogo tirante
        QMessageBox.information(self, "Info", "Definisci posizione e diametro tirante")

    def generaCordoliAutomatici(self):
        """Genera cordoli su tutti i muri dell'ultimo piano"""
        if not self.progetto.piani:
            return

        ultimo_piano = max(p.numero for p in self.progetto.piani)
        nuovi = 0

        for muro in self.progetto.muri:
            # Verifica se già esiste cordolo
            exists = any(c.muro_collegato == muro.nome and c.piano == ultimo_piano
                        for c in self.progetto.cordoli)
            if not exists:
                n = len(self.progetto.cordoli) + 1
                cordolo = Cordolo(
                    nome=f"C{n}",
                    piano=ultimo_piano,
                    x1=muro.x1, y1=muro.y1,
                    x2=muro.x2, y2=muro.y2,
                    base=muro.spessore,
                    altezza=0.25,
                    muro_collegato=muro.nome
                )
                self.progetto.cordoli.append(cordolo)
                nuovi += 1

        self.refresh()
        QMessageBox.information(self, "Cordoli Generati",
            f"Creati {nuovi} cordoli sommitali")


# ============================================================================
# STEP SOLAI PANEL
# ============================================================================

class StepSolaiPanel(QWidget):
    """Step per definizione solai"""

    def __init__(self, progetto: Progetto, parent=None):
        super().__init__(parent)
        self.progetto = progetto

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("▭ STEP 7: DEFINIZIONE SOLAI")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #0066cc; padding: 10px;")
        layout.addWidget(header)

        info = QLabel("Definisci i solai per ogni piano. I solai determinano i carichi verticali e la distribuzione delle masse.")
        info.setStyleSheet("color: #666; padding: 5px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Toolbar
        toolbar = QHBoxLayout()

        self.btn_aggiungi = QPushButton("➕ Aggiungi Solaio")
        self.btn_aggiungi.clicked.connect(self.aggiungiSolaio)
        toolbar.addWidget(self.btn_aggiungi)

        toolbar.addStretch()

        self.btn_elimina = QPushButton("🗑️ Elimina")
        self.btn_elimina.clicked.connect(self.eliminaSolaio)
        toolbar.addWidget(self.btn_elimina)

        layout.addLayout(toolbar)

        # Tabella solai
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Nome", "Piano", "Tipo", "Luce [m]", "Larg [m]", "G [kN/m²]", "Q [kN/m²]", "Categoria"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # Database tipi solaio
        tipo_group = QGroupBox("📚 Tipi Solaio Standard")
        tipo_layout = QGridLayout()

        tipi = [
            ("Laterocemento 20+5", 3.2, "A"),
            ("Laterocemento 25+5", 3.8, "A"),
            ("Soletta piena 20cm", 5.0, "A"),
            ("Legno tradizionale", 1.2, "A"),
            ("Acciaio e lamiera", 2.0, "B"),
            ("Predalles", 2.8, "A"),
        ]

        for i, (nome, peso, cat) in enumerate(tipi):
            btn = QPushButton(f"{nome}\n{peso} kN/m²")
            btn.setMinimumHeight(50)
            btn.clicked.connect(lambda c, n=nome, p=peso: self.applicaTipo(n, p))
            tipo_layout.addWidget(btn, i // 3, i % 3)

        tipo_group.setLayout(tipo_layout)
        layout.addWidget(tipo_group)

        # Riepilogo
        self.summary = QLabel("")
        self.summary.setStyleSheet("padding: 10px; background: #f8f9fa; border-radius: 5px;")
        layout.addWidget(self.summary)

        # Pulsanti navigazione
        btn_layout = QHBoxLayout()
        btn_indietro = QPushButton("← Indietro")
        btn_layout.addWidget(btn_indietro)
        btn_layout.addStretch()
        self.btn_avanti = QPushButton("Avanti → Carichi")
        self.btn_avanti.setStyleSheet("""
            QPushButton { background-color: #0066cc; color: white;
                         font-weight: bold; padding: 10px 30px; border-radius: 5px; }
        """)
        btn_layout.addWidget(self.btn_avanti)
        layout.addLayout(btn_layout)

    def refresh(self):
        self.table.setRowCount(len(self.progetto.solai))
        for i, s in enumerate(self.progetto.solai):
            self.table.setItem(i, 0, QTableWidgetItem(s.nome))
            self.table.setItem(i, 1, QTableWidgetItem(str(s.piano)))
            self.table.setItem(i, 2, QTableWidgetItem(s.tipo))
            self.table.setItem(i, 3, QTableWidgetItem(f"{s.luce:.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{s.larghezza:.2f}"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{s.peso_proprio:.1f}"))
            self.table.setItem(i, 6, QTableWidgetItem(f"{s.carico_variabile:.1f}"))
            self.table.setItem(i, 7, QTableWidgetItem(s.categoria_uso))

        # Riepilogo
        n = len(self.progetto.solai)
        area_tot = sum(s.area for s in self.progetto.solai)
        carico_tot = sum(s.carico_totale * s.area for s in self.progetto.solai)
        self.summary.setText(f"📊 Totale: {n} solai | Area: {area_tot:.1f} m² | Carico: {carico_tot:.0f} kN")

    def aggiungiSolaio(self):
        n = len(self.progetto.solai) + 1
        piano = 0 if not self.progetto.piani else self.progetto.piani[0].numero
        solaio = Solaio(f"S{n}", piano)
        self.progetto.solai.append(solaio)
        self.refresh()

    def eliminaSolaio(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.progetto.solai):
            del self.progetto.solai[row]
            self.refresh()

    def applicaTipo(self, nome: str, peso: float):
        row = self.table.currentRow()
        if 0 <= row < len(self.progetto.solai):
            self.progetto.solai[row].tipo = nome
            self.progetto.solai[row].peso_proprio = peso
            self.refresh()


# ============================================================================
# STEP CARICHI PANEL
# ============================================================================

class StepCarichiPanel(QWidget):
    """Step per definizione carichi"""

    def __init__(self, progetto: Progetto, parent=None):
        super().__init__(parent)
        self.progetto = progetto

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("⬇ STEP 8: CARICHI")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #0066cc; padding: 10px;")
        layout.addWidget(header)

        # Tabs
        tabs = QTabWidget()

        # Tab Permanenti
        perm_tab = QWidget()
        perm_layout = QVBoxLayout(perm_tab)

        perm_info = QLabel("Carichi permanenti strutturali (G1) e non strutturali (G2)")
        perm_info.setStyleSheet("color: #666;")
        perm_layout.addWidget(perm_info)

        perm_form = QFormLayout()

        self.g1_solaio = QDoubleSpinBox()
        self.g1_solaio.setRange(0, 10)
        self.g1_solaio.setValue(3.2)
        self.g1_solaio.setSuffix(" kN/m²")
        perm_form.addRow("G1 - Solaio:", self.g1_solaio)

        self.g2_pavimento = QDoubleSpinBox()
        self.g2_pavimento.setRange(0, 5)
        self.g2_pavimento.setValue(1.5)
        self.g2_pavimento.setSuffix(" kN/m²")
        perm_form.addRow("G2 - Pavimento:", self.g2_pavimento)

        self.g2_divisori = QDoubleSpinBox()
        self.g2_divisori.setRange(0, 3)
        self.g2_divisori.setValue(0.8)
        self.g2_divisori.setSuffix(" kN/m²")
        perm_form.addRow("G2 - Divisori:", self.g2_divisori)

        perm_layout.addLayout(perm_form)
        perm_layout.addStretch()

        tabs.addTab(perm_tab, "📦 Permanenti")

        # Tab Variabili
        var_tab = QWidget()
        var_layout = QVBoxLayout(var_tab)

        var_info = QLabel("Carichi variabili (Q) secondo categoria d'uso NTC 2018")
        var_info.setStyleSheet("color: #666;")
        var_layout.addWidget(var_info)

        # Categorie
        cat_group = QGroupBox("Categoria d'Uso")
        cat_layout = QVBoxLayout()

        self.cat_buttons = QButtonGroup()
        categorie = [
            ("A - Residenziale", 2.0),
            ("B - Uffici", 3.0),
            ("C1 - Aree soggette ad affollamento", 3.0),
            ("C2 - Balconi, ballatoi", 4.0),
            ("D1 - Negozi", 4.0),
            ("E1 - Archivi/Magazzini", 6.0),
        ]

        for i, (nome, valore) in enumerate(categorie):
            rb = QRadioButton(f"{nome} - {valore} kN/m²")
            rb.setProperty("qk", valore)
            if i == 0:
                rb.setChecked(True)
            self.cat_buttons.addButton(rb, i)
            cat_layout.addWidget(rb)

        cat_group.setLayout(cat_layout)
        var_layout.addWidget(cat_group)

        tabs.addTab(var_tab, "📋 Variabili")

        # Tab Climatici
        clim_tab = QWidget()
        clim_layout = QVBoxLayout(clim_tab)

        clim_info = QLabel("Carichi neve e vento secondo NTC 2018")
        clim_info.setStyleSheet("color: #666;")
        clim_layout.addWidget(clim_info)

        clim_form = QFormLayout()

        self.zona_neve = QComboBox()
        self.zona_neve.addItems(["I-Alpina", "I-Mediterranea", "II", "III"])
        clim_form.addRow("Zona neve:", self.zona_neve)

        self.altitudine = QSpinBox()
        self.altitudine.setRange(0, 3000)
        self.altitudine.setValue(100)
        self.altitudine.setSuffix(" m s.l.m.")
        clim_form.addRow("Altitudine:", self.altitudine)

        self.qs_calc = QLabel("-")
        self.qs_calc.setStyleSheet("font-weight: bold; color: #0066cc;")
        clim_form.addRow("Carico neve qs:", self.qs_calc)

        self.zona_vento = QComboBox()
        self.zona_vento.addItems(["1", "2", "3", "4", "5", "6", "7", "8", "9"])
        clim_form.addRow("Zona vento:", self.zona_vento)

        self.qw_calc = QLabel("-")
        self.qw_calc.setStyleSheet("font-weight: bold; color: #0066cc;")
        clim_form.addRow("Pressione vento qw:", self.qw_calc)

        clim_layout.addLayout(clim_form)

        btn_calc = QPushButton("🔄 Calcola Carichi Climatici")
        btn_calc.clicked.connect(self.calcolaCarichiClimatici)
        clim_layout.addWidget(btn_calc)

        clim_layout.addStretch()

        tabs.addTab(clim_tab, "❄ Climatici")

        layout.addWidget(tabs)

        # Pulsanti navigazione
        btn_layout = QHBoxLayout()
        btn_indietro = QPushButton("← Indietro")
        btn_layout.addWidget(btn_indietro)
        btn_layout.addStretch()
        self.btn_avanti = QPushButton("Avanti → Materiali")
        self.btn_avanti.setStyleSheet("""
            QPushButton { background-color: #0066cc; color: white;
                         font-weight: bold; padding: 10px 30px; border-radius: 5px; }
        """)
        btn_layout.addWidget(self.btn_avanti)
        layout.addLayout(btn_layout)

    def calcolaCarichiClimatici(self):
        """Calcola carichi neve e vento semplificati"""
        # Neve - formula semplificata
        zona = self.zona_neve.currentText()
        as_val = self.altitudine.value()

        # qsk base per zona
        qsk_base = {"I-Alpina": 1.5, "I-Mediterranea": 1.5, "II": 1.0, "III": 0.6}
        qsk = qsk_base.get(zona.split()[0], 1.0)

        # Correzione altitudine
        if as_val > 200:
            qsk *= 1 + (as_val - 200) / 1000

        self.qs_calc.setText(f"{qsk:.2f} kN/m²")

        # Vento - formula semplificata
        zona_v = int(self.zona_vento.currentText())
        vb = [25, 25, 27, 28, 28, 28, 28, 30, 31][zona_v - 1]  # Velocità base
        qw = 0.5 * 1.25 * (vb ** 2) / 1000  # Pressione cinetica
        self.qw_calc.setText(f"{qw:.2f} kN/m²")


# ============================================================================
# VISTA 3D WIDGET (semplificata isometrica)
# ============================================================================

class Vista3DWidget(QWidget):
    """Widget per vista 3D isometrica dell'edificio"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.progetto: Optional[Progetto] = None
        self.setMinimumSize(400, 400)

        # Parametri vista
        self.scala = 25  # pixel per metro
        self.rotazione = 30  # gradi
        self.offset_x = 200
        self.offset_y = 350
        self.mostra_dcr = True
        self.mostra_aperture = True

    def setProgetto(self, progetto: Progetto):
        self.progetto = progetto
        self.update()

    def project3D(self, x: float, y: float, z: float) -> Tuple[int, int]:
        """Proiezione isometrica 3D -> 2D"""
        angle = math.radians(self.rotazione)

        # Isometrica semplificata
        px = (x - y) * math.cos(angle) * self.scala + self.offset_x
        py = -(x + y) * math.sin(angle) * self.scala * 0.5 - z * self.scala + self.offset_y

        return int(px), int(py)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Sfondo
        painter.fillRect(self.rect(), QColor(240, 245, 250))

        if not self.progetto:
            painter.drawText(self.rect(), Qt.AlignCenter, "Nessun progetto")
            return

        # Disegna piani (basi)
        for piano in self.progetto.piani:
            self.drawPianoBase(painter, piano)

        # Disegna muri
        for muro in self.progetto.muri:
            self.drawMuro3D(painter, muro)

        # Disegna fondazioni
        for fond in self.progetto.fondazioni:
            self.drawFondazione3D(painter, fond)

        # Info
        painter.setPen(QPen(QColor(100, 100, 100)))
        painter.setFont(QFont("Arial", 9))
        painter.drawText(10, 20, f"Vista Isometrica - {self.progetto.nome}")
        painter.drawText(10, 35, f"Muri: {len(self.progetto.muri)} | Piani: {len(self.progetto.piani)}")

    def drawPianoBase(self, painter, piano: Piano):
        """Disegna base piano come griglia"""
        z = piano.quota
        size = 15  # dimensione griglia

        painter.setPen(QPen(QColor(200, 200, 200), 1))

        # Griglia
        for i in range(-2, 15):
            # Linee X
            p1 = self.project3D(i, -2, z)
            p2 = self.project3D(i, 15, z)
            painter.drawLine(p1[0], p1[1], p2[0], p2[1])

            # Linee Y
            p1 = self.project3D(-2, i, z)
            p2 = self.project3D(15, i, z)
            painter.drawLine(p1[0], p1[1], p2[0], p2[1])

    def drawMuro3D(self, painter, muro: Muro):
        """Disegna muro in 3D"""
        # Colore base DCR
        if self.mostra_dcr and muro.dcr > 0:
            if muro.dcr > 1.0:
                color = QColor(255, 80, 80)
            elif muro.dcr > 0.8:
                color = QColor(255, 180, 80)
            else:
                color = QColor(80, 200, 80)
        else:
            color = QColor(180, 140, 100)

        # 4 vertici base
        b1 = self.project3D(muro.x1, muro.y1, muro.z)
        b2 = self.project3D(muro.x2, muro.y2, muro.z)

        # 4 vertici top
        z_top = muro.z + muro.altezza
        t1 = self.project3D(muro.x1, muro.y1, z_top)
        t2 = self.project3D(muro.x2, muro.y2, z_top)

        # Disegna faccia frontale
        painter.setPen(QPen(QColor(60, 40, 30), 1))
        painter.setBrush(QBrush(color))

        path = QPainterPath()
        path.moveTo(b1[0], b1[1])
        path.lineTo(b2[0], b2[1])
        path.lineTo(t2[0], t2[1])
        path.lineTo(t1[0], t1[1])
        path.closeSubpath()
        painter.drawPath(path)

        # Label
        mx = (b1[0] + b2[0]) / 2
        my = (b1[1] + t1[1]) / 2
        painter.setFont(QFont("Arial", 8))
        painter.drawText(int(mx) - 10, int(my), muro.nome)

    def drawFondazione3D(self, painter, fond: Fondazione):
        """Disegna fondazione in 3D"""
        z = -fond.profondita  # Sotto quota zero

        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.setBrush(QBrush(QColor(150, 150, 150)))

        # Punti base e top
        b1 = self.project3D(fond.x1, fond.y1, z)
        b2 = self.project3D(fond.x2, fond.y2, z)
        t1 = self.project3D(fond.x1, fond.y1, 0)
        t2 = self.project3D(fond.x2, fond.y2, 0)

        path = QPainterPath()
        path.moveTo(b1[0], b1[1])
        path.lineTo(b2[0], b2[1])
        path.lineTo(t2[0], t2[1])
        path.lineTo(t1[0], t1[1])
        path.closeSubpath()
        painter.drawPath(path)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.scala = min(60, self.scala * 1.1)
        else:
            self.scala = max(10, self.scala / 1.1)
        self.update()

    def mousePressEvent(self, event):
        # Ruota vista con click
        if event.button() == Qt.LeftButton:
            self.rotazione = (self.rotazione + 15) % 360
            self.update()


# ============================================================================
# SPETTRO WIDGET - Visualizzazione spettro sismico NTC 2018
# ============================================================================

class SpettroWidget(QWidget):
    """Widget per visualizzare spettro di risposta elastico NTC 2018"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)

        # Parametri spettro
        self.ag = 0.15  # accelerazione di picco
        self.F0 = 2.5   # fattore amplificazione
        self.Tc_star = 0.5  # periodo inizio tratto velocità costante
        self.S = 1.2    # coefficiente stratigrafico
        self.eta = 1.0  # fattore smorzamento
        self.q = 2.0    # fattore struttura

        # Punti spettro
        self.punti_elastico = []
        self.punti_progetto = []
        self.calcolaSpettro()

        # Vista
        self.margin = 60
        self.show_progetto = True

    def setParametri(self, ag: float, F0: float, Tc_star: float, S: float, q: float):
        """Imposta parametri spettro"""
        self.ag = ag
        self.F0 = F0
        self.Tc_star = Tc_star
        self.S = S
        self.q = q
        self.calcolaSpettro()
        self.update()

    def calcolaSpettro(self):
        """Calcola punti dello spettro NTC 2018"""
        self.punti_elastico = []
        self.punti_progetto = []

        ag = self.ag
        S = self.S
        F0 = self.F0
        eta = self.eta
        Tc = self.Tc_star * 1.0  # Assumiamo CC=1
        Tb = Tc / 3
        Td = 4 * ag + 1.6

        # Genera punti per T da 0 a 4 secondi
        for i in range(401):
            T = i * 0.01

            # Spettro elastico
            if T < Tb:
                Se = ag * S * eta * F0 * (T/Tb + (1/(eta*F0)) * (1 - T/Tb))
            elif T < Tc:
                Se = ag * S * eta * F0
            elif T < Td:
                Se = ag * S * eta * F0 * (Tc / T)
            else:
                Se = ag * S * eta * F0 * (Tc * Td / (T * T))

            self.punti_elastico.append((T, Se))

            # Spettro di progetto (con q)
            Sd = Se / self.q
            if Sd < 0.2 * ag:
                Sd = 0.2 * ag
            self.punti_progetto.append((T, Sd))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Sfondo
        painter.fillRect(self.rect(), QColor(255, 255, 255))

        w = self.width() - 2 * self.margin
        h = self.height() - 2 * self.margin

        # Trova massimo
        max_Se = max(p[1] for p in self.punti_elastico) if self.punti_elastico else 1.0
        max_T = 4.0

        def toScreen(T, Se):
            x = self.margin + (T / max_T) * w
            y = self.height() - self.margin - (Se / (max_Se * 1.1)) * h
            return int(x), int(y)

        # Griglia
        painter.setPen(QPen(QColor(220, 220, 220), 1))
        for i in range(5):
            y = self.margin + i * h / 4
            painter.drawLine(self.margin, int(y), self.width() - self.margin, int(y))
        for i in range(5):
            x = self.margin + i * w / 4
            painter.drawLine(int(x), self.margin, int(x), self.height() - self.margin)

        # Assi
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawLine(self.margin, self.height() - self.margin,
                        self.width() - self.margin, self.height() - self.margin)
        painter.drawLine(self.margin, self.margin, self.margin, self.height() - self.margin)

        # Label assi
        painter.setFont(QFont("Arial", 10))
        painter.drawText(self.width() // 2 - 30, self.height() - 10, "Periodo T [s]")
        painter.save()
        painter.translate(15, self.height() // 2)
        painter.rotate(-90)
        painter.drawText(0, 0, "Se [g]")
        painter.restore()

        # Valori assi
        painter.setFont(QFont("Arial", 8))
        for i in range(5):
            T = i
            x, _ = toScreen(T, 0)
            painter.drawText(x - 5, self.height() - self.margin + 15, str(T))

            Se = max_Se * (4 - i) / 4
            _, y = toScreen(0, Se)
            painter.drawText(self.margin - 35, y + 5, f"{Se:.2f}")

        # Spettro elastico
        painter.setPen(QPen(QColor(0, 100, 200), 2))
        path = QPainterPath()
        first = True
        for T, Se in self.punti_elastico:
            x, y = toScreen(T, Se)
            if first:
                path.moveTo(x, y)
                first = False
            else:
                path.lineTo(x, y)
        painter.drawPath(path)

        # Spettro di progetto
        if self.show_progetto:
            painter.setPen(QPen(QColor(200, 50, 50), 2, Qt.DashLine))
            path = QPainterPath()
            first = True
            for T, Sd in self.punti_progetto:
                x, y = toScreen(T, Sd)
                if first:
                    path.moveTo(x, y)
                    first = False
                else:
                    path.lineTo(x, y)
            painter.drawPath(path)

        # Legenda
        painter.setPen(QPen(QColor(0, 0, 0)))
        painter.setFont(QFont("Arial", 10))
        painter.fillRect(self.width() - 180, 10, 170, 70, QColor(255, 255, 255, 200))
        painter.drawRect(self.width() - 180, 10, 170, 70)

        painter.setPen(QPen(QColor(0, 100, 200), 2))
        painter.drawLine(self.width() - 170, 30, self.width() - 130, 30)
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(self.width() - 120, 35, "Elastico")

        if self.show_progetto:
            painter.setPen(QPen(QColor(200, 50, 50), 2, Qt.DashLine))
            painter.drawLine(self.width() - 170, 50, self.width() - 130, 50)
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(self.width() - 120, 55, f"Progetto (q={self.q})")

        # Parametri
        painter.drawText(self.width() - 170, 75, f"ag={self.ag}g S={self.S}")

        # Titolo
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.drawText(self.margin, 25, "SPETTRO DI RISPOSTA NTC 2018")


# ============================================================================
# DIALOGO MATERIALE
# ============================================================================

class DialogoMateriale(QDialog):
    """Dialogo per definire proprietà materiali muratura"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🧱 Proprietà Materiale Muratura")
        self.setMinimumSize(500, 600)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("Definizione Materiale Muratura NTC 2018")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #0066cc;")
        layout.addWidget(header)

        # Tipo muratura
        tipo_group = QGroupBox("Tipo Muratura")
        tipo_layout = QVBoxLayout()

        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems([
            "Muratura in mattoni pieni e malta di calce",
            "Muratura in mattoni pieni e malta cementizia",
            "Muratura in mattoni semipieni",
            "Muratura in blocchi di laterizio",
            "Muratura in pietra squadrata",
            "Muratura in pietra listata",
            "Muratura in pietra non squadrata",
            "Muratura in blocchi di calcestruzzo",
            "Personalizzato"
        ])
        self.tipo_combo.currentIndexChanged.connect(self.onTipoChanged)
        tipo_layout.addWidget(self.tipo_combo)

        tipo_group.setLayout(tipo_layout)
        layout.addWidget(tipo_group)

        # Proprietà meccaniche
        mech_group = QGroupBox("Proprietà Meccaniche (valori medi)")
        mech_layout = QFormLayout()

        self.fm_spin = QDoubleSpinBox()
        self.fm_spin.setRange(0.5, 15.0)
        self.fm_spin.setValue(2.4)
        self.fm_spin.setSuffix(" MPa")
        self.fm_spin.setDecimals(2)
        mech_layout.addRow("fm (resistenza compressione):", self.fm_spin)

        self.tau0_spin = QDoubleSpinBox()
        self.tau0_spin.setRange(0.01, 0.50)
        self.tau0_spin.setValue(0.060)
        self.tau0_spin.setSuffix(" MPa")
        self.tau0_spin.setDecimals(3)
        mech_layout.addRow("τ0 (resistenza taglio):", self.tau0_spin)

        self.E_spin = QSpinBox()
        self.E_spin.setRange(500, 10000)
        self.E_spin.setValue(1500)
        self.E_spin.setSuffix(" MPa")
        mech_layout.addRow("E (modulo elastico):", self.E_spin)

        self.G_spin = QSpinBox()
        self.G_spin.setRange(100, 5000)
        self.G_spin.setValue(500)
        self.G_spin.setSuffix(" MPa")
        mech_layout.addRow("G (modulo taglio):", self.G_spin)

        self.w_spin = QDoubleSpinBox()
        self.w_spin.setRange(10, 25)
        self.w_spin.setValue(18.0)
        self.w_spin.setSuffix(" kN/m³")
        mech_layout.addRow("γ (peso specifico):", self.w_spin)

        mech_group.setLayout(mech_layout)
        layout.addWidget(mech_group)

        # Coefficienti sicurezza
        coef_group = QGroupBox("Coefficienti di Sicurezza")
        coef_layout = QFormLayout()

        self.gamma_m = QDoubleSpinBox()
        self.gamma_m.setRange(1.5, 3.5)
        self.gamma_m.setValue(2.0)
        coef_layout.addRow("γM (materiale):", self.gamma_m)

        self.fc_combo = QComboBox()
        self.fc_combo.addItems(["1.35 - LC1", "1.20 - LC2", "1.00 - LC3"])
        coef_layout.addRow("FC (conoscenza):", self.fc_combo)

        coef_group.setLayout(coef_layout)
        layout.addWidget(coef_group)

        # Tabella NTC 2018
        ntc_label = QLabel("📖 Valori di riferimento NTC 2018 Tab. C8.5.I")
        ntc_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(ntc_label)

        # Pulsanti
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Annulla")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        btn_ok = QPushButton("✓ Applica")
        btn_ok.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 8px 20px;")
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    def onTipoChanged(self, idx):
        """Imposta valori default per tipo muratura"""
        # Valori tipici da NTC 2018 Tab C8.5.I
        valori = [
            (2.4, 0.060, 1500, 500, 18),  # Mattoni pieni calce
            (3.2, 0.076, 1800, 600, 18),  # Mattoni pieni cemento
            (5.0, 0.090, 3500, 875, 15),  # Mattoni semipieni
            (4.0, 0.080, 2800, 700, 12),  # Blocchi laterizio
            (6.0, 0.090, 2400, 800, 22),  # Pietra squadrata
            (2.6, 0.056, 1500, 500, 21),  # Pietra listata
            (1.0, 0.020, 690, 230, 19),   # Pietra non squadrata
            (3.0, 0.090, 2400, 800, 14),  # Blocchi cls
            (2.4, 0.060, 1500, 500, 18),  # Personalizzato
        ]
        if idx < len(valori):
            fm, tau0, E, G, w = valori[idx]
            self.fm_spin.setValue(fm)
            self.tau0_spin.setValue(tau0)
            self.E_spin.setValue(E)
            self.G_spin.setValue(G)
            self.w_spin.setValue(w)


# ============================================================================
# COMBINAZIONI CARICHI NTC 2018
# ============================================================================

class CombinazioniCarichi:
    """Calcolo combinazioni di carico NTC 2018"""

    # Coefficienti parziali
    GAMMA_G1 = 1.3   # Carichi permanenti strutturali
    GAMMA_G2 = 1.5   # Carichi permanenti non strutturali
    GAMMA_Q = 1.5    # Carichi variabili

    # Coefficienti psi per categoria d'uso
    PSI = {
        'A': (0.7, 0.5, 0.3),  # Residenziale
        'B': (0.7, 0.5, 0.3),  # Uffici
        'C': (0.7, 0.7, 0.6),  # Affollamento
        'D': (0.7, 0.7, 0.6),  # Commerciale
        'E': (1.0, 0.9, 0.8),  # Magazzini
        'F': (0.7, 0.7, 0.6),  # Rimesse
        'G': (0.7, 0.5, 0.3),  # Coperture
        'H': (0.0, 0.0, 0.0),  # Neve
    }

    @staticmethod
    def SLU_STR(G1: float, G2: float, Q: float, cat: str = 'A') -> float:
        """Combinazione SLU fondamentale STR"""
        psi = CombinazioniCarichi.PSI.get(cat, (0.7, 0.5, 0.3))
        return (CombinazioniCarichi.GAMMA_G1 * G1 +
                CombinazioniCarichi.GAMMA_G2 * G2 +
                CombinazioniCarichi.GAMMA_Q * Q)

    @staticmethod
    def SLE_RARA(G1: float, G2: float, Q: float, cat: str = 'A') -> float:
        """Combinazione SLE rara"""
        return G1 + G2 + Q

    @staticmethod
    def SLE_FREQUENTE(G1: float, G2: float, Q: float, cat: str = 'A') -> float:
        """Combinazione SLE frequente"""
        psi = CombinazioniCarichi.PSI.get(cat, (0.7, 0.5, 0.3))
        return G1 + G2 + psi[0] * Q

    @staticmethod
    def SLE_QUASI_PERM(G1: float, G2: float, Q: float, cat: str = 'A') -> float:
        """Combinazione SLE quasi permanente"""
        psi = CombinazioniCarichi.PSI.get(cat, (0.7, 0.5, 0.3))
        return G1 + G2 + psi[2] * Q

    @staticmethod
    def SISMICA(G1: float, G2: float, Q: float, E: float, cat: str = 'A') -> float:
        """Combinazione sismica E"""
        psi = CombinazioniCarichi.PSI.get(cat, (0.7, 0.5, 0.3))
        return G1 + G2 + psi[1] * Q + E

    @staticmethod
    def tutte_combinazioni(G1: float, G2: float, Q: float, cat: str = 'A') -> dict:
        """Calcola tutte le combinazioni"""
        return {
            'SLU_STR': CombinazioniCarichi.SLU_STR(G1, G2, Q, cat),
            'SLE_RARA': CombinazioniCarichi.SLE_RARA(G1, G2, Q, cat),
            'SLE_FREQ': CombinazioniCarichi.SLE_FREQUENTE(G1, G2, Q, cat),
            'SLE_QP': CombinazioniCarichi.SLE_QUASI_PERM(G1, G2, Q, cat),
        }


# ============================================================================
# PUSHOVER CURVE WIDGET
# ============================================================================

class PushoverWidget(QWidget):
    """Widget per visualizzare curva pushover capacitiva"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 400)

        # Dati curva
        self.V_base = []  # Taglio alla base [kN]
        self.delta_top = []  # Spostamento sommità [mm]

        # Parametri bilineare
        self.Vy = None
        self.Vu = None
        self.delta_y = None
        self.delta_u = None
        self.mu = None

        self.bilinear_V = []
        self.bilinear_delta = []
        self.margin = 60

    def setCurva(self, V_base: List[float], delta_top: List[float]):
        """Imposta dati curva pushover"""
        self.V_base = V_base
        self.delta_top = [d * 1000 for d in delta_top]  # m -> mm
        self.calcola_bilineare()
        self.update()

    def calcola_bilineare(self):
        """Calcola bilinearizzazione e parametri prestazionali"""
        if len(self.V_base) < 10:
            return
        self.Vu = max(self.V_base)
        idx_u = self.V_base.index(self.Vu)
        self.delta_u = self.delta_top[idx_u]
        target_Vy = 0.7 * self.Vu
        for i, V in enumerate(self.V_base):
            if V >= target_Vy:
                self.Vy = V
                self.delta_y = self.delta_top[i]
                break
        if self.Vy and self.delta_y and self.delta_y > 0:
            self.mu = self.delta_u / self.delta_y
            self.bilinear_delta = [0, self.delta_y, self.delta_u]
            self.bilinear_V = [0, self.Vy, self.Vu]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(255, 255, 255))

        w = self.width() - 2 * self.margin
        h = self.height() - 2 * self.margin

        if not self.V_base or not self.delta_top:
            painter.drawText(self.rect(), Qt.AlignCenter, "Esegui analisi pushover")
            return

        max_V = max(self.V_base) * 1.1
        max_delta = max(self.delta_top) * 1.1

        def toScreen(delta, V):
            x = self.margin + (delta / max_delta) * w
            y = self.height() - self.margin - (V / max_V) * h
            return int(x), int(y)

        # Griglia
        painter.setPen(QPen(QColor(220, 220, 220), 1))
        for i in range(5):
            y = self.margin + i * h / 4
            painter.drawLine(self.margin, int(y), self.width() - self.margin, int(y))

        # Assi
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawLine(self.margin, self.height() - self.margin,
                        self.width() - self.margin, self.height() - self.margin)
        painter.drawLine(self.margin, self.margin, self.margin, self.height() - self.margin)

        # Curva pushover
        painter.setPen(QPen(QColor(0, 100, 200), 2))
        path = QPainterPath()
        for i, (delta, V) in enumerate(zip(self.delta_top, self.V_base)):
            x, y = toScreen(delta, V)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        painter.drawPath(path)

        # Bilineare
        if self.bilinear_V:
            painter.setPen(QPen(QColor(200, 50, 50), 2, Qt.DashLine))
            path = QPainterPath()
            for i, (delta, V) in enumerate(zip(self.bilinear_delta, self.bilinear_V)):
                x, y = toScreen(delta, V)
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            painter.drawPath(path)

        # Titolo e legenda
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(self.margin, 25, "CURVA PUSHOVER")

        if self.mu:
            painter.setFont(QFont("Arial", 10))
            painter.drawText(self.width() - 150, 30, f"μ = {self.mu:.2f}")
            painter.drawText(self.width() - 150, 50, f"Vu = {self.Vu:.0f} kN")


# ============================================================================
# VALIDAZIONE GEOMETRIA
# ============================================================================

class GeometryValidator:
    """Classe per validare la geometria dell'edificio"""

    @staticmethod
    def validaAperture(progetto: Progetto) -> List[str]:
        """Verifica che le aperture siano dentro i muri"""
        errori = []
        for ap in progetto.aperture:
            muro = next((m for m in progetto.muri if m.nome == ap.muro), None)
            if not muro:
                errori.append(f"Apertura {ap.nome}: muro {ap.muro} non trovato")
            elif ap.posizione + ap.larghezza > muro.lunghezza:
                errori.append(f"Apertura {ap.nome}: esce dal muro {ap.muro} (pos={ap.posizione}, L_ap={ap.larghezza}, L_muro={muro.lunghezza:.2f})")
            elif ap.altezza + ap.altezza_davanzale > muro.altezza:
                errori.append(f"Apertura {ap.nome}: altezza eccessiva (h={ap.altezza}+{ap.altezza_davanzale} > {muro.altezza})")
        return errori

    @staticmethod
    def validaMuriChiusi(progetto: Progetto, tolleranza: float = 0.1) -> List[str]:
        """Verifica che i muri formino contorni chiusi"""
        warnings = []
        # Trova estremi muri
        estremi = []
        for m in progetto.muri:
            estremi.append((m.x1, m.y1, m.nome, "inizio"))
            estremi.append((m.x2, m.y2, m.nome, "fine"))

        # Conta connessioni per ogni estremo
        for i, (x1, y1, nome1, tipo1) in enumerate(estremi):
            connesso = False
            for j, (x2, y2, nome2, tipo2) in enumerate(estremi):
                if i != j and nome1 != nome2:
                    dist = math.sqrt((x1-x2)**2 + (y1-y2)**2)
                    if dist < tolleranza:
                        connesso = True
                        break
            if not connesso:
                warnings.append(f"Muro {nome1} ({tipo1}) non connesso a ({x1:.2f}, {y1:.2f})")

        return warnings

    @staticmethod
    def validaSovrapposizioni(progetto: Progetto) -> List[str]:
        """Verifica sovrapposizioni tra muri"""
        warnings = []
        muri = progetto.muri
        for i, m1 in enumerate(muri):
            for m2 in muri[i+1:]:
                # Sovrapposizione semplificata: stesso segmento
                if abs(m1.x1 - m2.x1) < 0.1 and abs(m1.y1 - m2.y1) < 0.1:
                    if abs(m1.x2 - m2.x2) < 0.1 and abs(m1.y2 - m2.y2) < 0.1:
                        warnings.append(f"Muri {m1.nome} e {m2.nome} sovrapposti")
        return warnings

    @staticmethod
    def validaTutto(progetto: Progetto) -> Dict[str, List[str]]:
        """Esegue tutte le validazioni"""
        return {
            'aperture': GeometryValidator.validaAperture(progetto),
            'chiusura': GeometryValidator.validaMuriChiusi(progetto),
            'sovrapposizioni': GeometryValidator.validaSovrapposizioni(progetto)
        }


# ============================================================================
# CANVAS DISEGNO (migliorato)
# ============================================================================

class DrawingCanvas(QWidget):
    """Canvas per disegno muri con tools migliorati"""

    muroAggiunto = pyqtSignal(Muro)
    selectionChanged = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.progetto: Optional[Progetto] = None
        self.setMinimumSize(600, 400)
        self.setMouseTracking(True)

        # Vista
        self.scala = 40  # pixel per metro
        self.offset_x = 300
        self.offset_y = 300
        self.griglia = True
        self.passo_griglia = 0.5

        # Strumento corrente
        # Strumenti: select, muro, apertura, pan, rettangolo, misura, copia
        self.strumento = 'select'

        # Disegno muro/rettangolo
        self.punto_inizio = None
        self.punto_corrente = None

        # Strumento rettangolo
        self.rettangolo_punti = []  # [p1, p2] per disegnare 4 muri

        # Strumento misura
        self.misura_attiva = False
        self.misura_start = None
        self.misura_end = None
        self.misura_risultato = None

        # Clipboard per copia
        self.clipboard_muri = []
        self.clipboard_offset = (0.5, 0.5)

        # Piano corrente
        self.piano_corrente = 0

        # Stile
        self.setStyleSheet("background-color: white;")

    def setProgetto(self, progetto: Progetto):
        self.progetto = progetto
        self.update()

    def setStrumento(self, strumento: str):
        self.strumento = strumento
        self.punto_inizio = None
        self.update()

    def worldToScreen(self, x: float, y: float) -> Tuple[int, int]:
        sx = int(x * self.scala + self.offset_x)
        sy = int(-y * self.scala + self.offset_y)
        return sx, sy

    def screenToWorld(self, sx: int, sy: int) -> Tuple[float, float]:
        x = (sx - self.offset_x) / self.scala
        y = -(sy - self.offset_y) / self.scala
        return x, y

    def snapToGrid(self, x: float, y: float) -> Tuple[float, float]:
        if self.griglia:
            x = round(x / self.passo_griglia) * self.passo_griglia
            y = round(y / self.passo_griglia) * self.passo_griglia
        return x, y

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Sfondo
        painter.fillRect(self.rect(), QColor(255, 255, 255))

        # Griglia
        if self.griglia:
            self.drawGrid(painter)

        # Assi
        self.drawAxes(painter)

        # Muri
        if self.progetto:
            for muro in self.progetto.muri:
                if muro.z == self.piano_corrente * (self.progetto.altezza_piano if self.progetto else 3.0):
                    self.drawMuro(painter, muro)

            # Aperture
            for ap in self.progetto.aperture:
                muro = next((m for m in self.progetto.muri if m.nome == ap.muro), None)
                if muro:
                    self.drawApertura(painter, ap, muro)

        # Muro in corso di disegno
        if self.strumento == 'muro' and self.punto_inizio and self.punto_corrente:
            self.drawTempMuro(painter)

        # Rettangolo in corso di disegno
        if self.strumento == 'rettangolo' and self.punto_inizio and self.punto_corrente:
            self.drawTempRettangolo(painter)

        # Linea di misura
        if self.strumento == 'misura' and (self.misura_start or self.misura_attiva):
            self.drawMisura(painter)

        # Info strumento
        self.drawToolInfo(painter)

    def drawGrid(self, painter):
        painter.setPen(QPen(QColor(230, 230, 230), 1))

        # Calcola range visibile
        w, h = self.width(), self.height()
        x1, y1 = self.screenToWorld(0, h)
        x2, y2 = self.screenToWorld(w, 0)

        # Linee verticali
        x = math.floor(x1 / self.passo_griglia) * self.passo_griglia
        while x <= x2:
            sx, _ = self.worldToScreen(x, 0)
            painter.drawLine(sx, 0, sx, h)
            x += self.passo_griglia

        # Linee orizzontali
        y = math.floor(y1 / self.passo_griglia) * self.passo_griglia
        while y <= y2:
            _, sy = self.worldToScreen(0, y)
            painter.drawLine(0, sy, w, sy)
            y += self.passo_griglia

    def drawAxes(self, painter):
        # Asse X (rosso)
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        sx0, sy0 = self.worldToScreen(0, 0)
        sx1, _ = self.worldToScreen(2, 0)
        painter.drawLine(sx0, sy0, sx1, sy0)
        painter.drawText(sx1 + 5, sy0 + 5, "X")

        # Asse Y (verde)
        painter.setPen(QPen(QColor(0, 200, 0), 2))
        _, sy1 = self.worldToScreen(0, 2)
        painter.drawLine(sx0, sy0, sx0, sy1)
        painter.drawText(sx0 + 5, sy1 - 5, "Y")

    def drawMuro(self, painter, muro: Muro):
        x1, y1 = self.worldToScreen(muro.x1, muro.y1)
        x2, y2 = self.worldToScreen(muro.x2, muro.y2)

        # Colore in base a DCR
        if muro.dcr > 1.0:
            color = QColor(255, 100, 100)
        elif muro.dcr > 0.8:
            color = QColor(255, 200, 100)
        elif muro.dcr > 0:
            color = QColor(100, 200, 100)
        else:
            color = QColor(180, 140, 100)

        if muro.selected:
            color = QColor(100, 150, 255)

        # Calcola spessore in pixel
        spessore_px = max(muro.spessore * self.scala, 4)

        # Disegna muro
        painter.setPen(QPen(QColor(80, 60, 40), 1))
        painter.setBrush(QBrush(color))

        # Calcola rettangolo del muro
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length > 0:
            nx, ny = -dy/length * spessore_px/2, dx/length * spessore_px/2
            points = [
                QPointF(x1 - nx, y1 - ny),
                QPointF(x1 + nx, y1 + ny),
                QPointF(x2 + nx, y2 + ny),
                QPointF(x2 - nx, y2 - ny),
            ]
            painter.drawPolygon(*points)

        # Etichetta
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        painter.setPen(QPen(QColor(0, 0, 0)))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(int(mx) - 20, int(my) - 5, f"{muro.nome}")
        painter.drawText(int(mx) - 20, int(my) + 10, f"{muro.lunghezza:.2f}m")

    def drawApertura(self, painter, ap: Apertura, muro: Muro):
        # Calcola posizione apertura sul muro
        dx = muro.x2 - muro.x1
        dy = muro.y2 - muro.y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0:
            return

        # Punto medio apertura
        t = (ap.posizione + ap.larghezza/2) / length
        ax = muro.x1 + dx * t
        ay = muro.y1 + dy * t

        sx, sy = self.worldToScreen(ax, ay)

        # Disegna simbolo
        size = int(ap.larghezza * self.scala / 2)
        if ap.tipo == "finestra":
            painter.setPen(QPen(QColor(0, 100, 200), 2))
            painter.setBrush(QBrush(QColor(150, 200, 255, 150)))
        else:
            painter.setPen(QPen(QColor(100, 60, 20), 2))
            painter.setBrush(QBrush(QColor(180, 140, 100, 150)))

        painter.drawRect(sx - size, sy - size//2, size*2, size)

    def drawTempMuro(self, painter):
        x1, y1 = self.worldToScreen(self.punto_inizio[0], self.punto_inizio[1])
        x2, y2 = self.worldToScreen(self.punto_corrente[0], self.punto_corrente[1])

        painter.setPen(QPen(QColor(0, 100, 200), 2, Qt.DashLine))
        painter.drawLine(x1, y1, x2, y2)

        # Lunghezza
        dx = self.punto_corrente[0] - self.punto_inizio[0]
        dy = self.punto_corrente[1] - self.punto_inizio[1]
        length = math.sqrt(dx*dx + dy*dy)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        painter.drawText(int(mx), int(my) - 10, f"{length:.2f} m")

    def drawTempRettangolo(self, painter):
        """Disegna preview rettangolo in costruzione"""
        x1, y1 = self.worldToScreen(self.punto_inizio[0], self.punto_inizio[1])
        x2, y2 = self.worldToScreen(self.punto_corrente[0], self.punto_corrente[1])

        painter.setPen(QPen(QColor(0, 150, 100), 2, Qt.DashLine))
        painter.setBrush(QBrush(QColor(0, 200, 100, 30)))

        # Disegna rettangolo
        rect = QRectF(min(x1, x2), min(y1, y2), abs(x2-x1), abs(y2-y1))
        painter.drawRect(rect)

        # Dimensioni
        width = abs(self.punto_corrente[0] - self.punto_inizio[0])
        height = abs(self.punto_corrente[1] - self.punto_inizio[1])
        painter.setPen(QPen(QColor(0, 100, 50)))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(int(min(x1, x2)), int(min(y1, y2)) - 5,
                        f"{width:.2f} x {height:.2f} m")

    def drawToolInfo(self, painter):
        painter.setPen(QPen(QColor(100, 100, 100)))
        painter.setFont(QFont("Arial", 9))

        tool_names = {
            'select': '🔍 Seleziona',
            'muro': '🧱 Disegna Muro',
            'rettangolo': '⬜ Disegna Rettangolo',
            'apertura': '🚪 Aggiungi Apertura',
            'misura': '📏 Misura Distanza',
            'pan': '✋ Sposta Vista'
        }

        painter.drawText(10, 20, f"Strumento: {tool_names.get(self.strumento, self.strumento)}")
        painter.drawText(10, 35, f"Piano: {self.piano_corrente}")

        if self.progetto:
            painter.drawText(10, 50, f"Muri: {len(self.progetto.muri)}")
            painter.drawText(10, 65, f"Aperture: {len(self.progetto.aperture)}")

        # Istruzioni
        istruzioni = {
            'muro': "Click: inizio | Click: fine | ESC/RClick: annulla",
            'rettangolo': "Click: primo angolo | Click: angolo opposto",
            'misura': "Click: inizio | Click: fine",
            'select': "Click: seleziona | Ctrl+C: copia | Ctrl+V: incolla"
        }
        if self.strumento in istruzioni:
            painter.drawText(10, self.height() - 10, istruzioni[self.strumento])

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            wx, wy = self.screenToWorld(event.x(), event.y())
            wx, wy = self.snapToGrid(wx, wy)

            if self.strumento == 'muro':
                if not self.punto_inizio:
                    self.punto_inizio = (wx, wy)
                else:
                    # Crea muro
                    self.createMuro(wx, wy)
                    self.punto_inizio = None
                    self.punto_corrente = None

            elif self.strumento == 'rettangolo':
                if not self.punto_inizio:
                    self.punto_inizio = (wx, wy)
                else:
                    # Crea rettangolo (4 muri)
                    self.drawRettangolo(
                        self.punto_inizio[0], self.punto_inizio[1],
                        wx, wy
                    )
                    self.punto_inizio = None
                    self.punto_corrente = None

            elif self.strumento == 'misura':
                if not self.misura_attiva:
                    self.startMisura(wx, wy)
                else:
                    self.endMisura()

            elif self.strumento == 'select':
                self.selectAt(wx, wy)

        elif event.button() == Qt.RightButton:
            # Annulla operazione corrente
            self.punto_inizio = None
            self.punto_corrente = None
            if self.misura_attiva:
                self.endMisura()
                self.misura_start = None
                self.misura_end = None

        self.update()

    def mouseMoveEvent(self, event):
        wx, wy = self.screenToWorld(event.x(), event.y())
        wx, wy = self.snapToGrid(wx, wy)

        if self.strumento in ['muro', 'rettangolo'] and self.punto_inizio:
            self.punto_corrente = (wx, wy)

        if self.strumento == 'misura' and self.misura_attiva:
            self.updateMisura(wx, wy)

        self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.scala = min(200, self.scala * 1.1)
        else:
            self.scala = max(10, self.scala / 1.1)
        self.update()

    def createMuro(self, x2: float, y2: float):
        if not self.progetto:
            return

        n = len(self.progetto.muri) + 1
        z = self.piano_corrente * self.progetto.altezza_piano

        muro = Muro(
            nome=f"M{n}",
            x1=self.punto_inizio[0],
            y1=self.punto_inizio[1],
            x2=x2,
            y2=y2,
            z=z,
            altezza=self.progetto.altezza_piano
        )

        self.progetto.muri.append(muro)
        self.muroAggiunto.emit(muro)

    def selectAt(self, wx: float, wy: float):
        if not self.progetto:
            return

        # Deseleziona tutti
        for m in self.progetto.muri:
            m.selected = False

        # Cerca muro vicino
        for muro in self.progetto.muri:
            # Distanza punto-segmento
            dist = self.pointToSegmentDist(wx, wy, muro.x1, muro.y1, muro.x2, muro.y2)
            if dist < 0.5:  # 50cm di tolleranza
                muro.selected = True
                self.selectionChanged.emit(muro)
                break

    def pointToSegmentDist(self, px, py, x1, y1, x2, y2) -> float:
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.sqrt((px-x1)**2 + (py-y1)**2)

        t = max(0, min(1, ((px-x1)*dx + (py-y1)*dy) / (dx*dx + dy*dy)))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.sqrt((px-proj_x)**2 + (py-proj_y)**2)

    # ========== STRUMENTO RETTANGOLO ==========

    def drawRettangolo(self, x1: float, y1: float, x2: float, y2: float):
        """Disegna 4 muri che formano un rettangolo"""
        if not self.progetto:
            return

        n = len(self.progetto.muri)
        z = self.piano_corrente * self.progetto.altezza_piano
        h = self.progetto.altezza_piano

        # 4 muri del rettangolo
        muri_nuovi = [
            Muro(f"M{n+1}", x1, y1, x2, y1, 0.30, h, z=z),  # basso
            Muro(f"M{n+2}", x2, y1, x2, y2, 0.30, h, z=z),  # destra
            Muro(f"M{n+3}", x2, y2, x1, y2, 0.30, h, z=z),  # alto
            Muro(f"M{n+4}", x1, y2, x1, y1, 0.30, h, z=z),  # sinistra
        ]

        for m in muri_nuovi:
            self.progetto.muri.append(m)
            self.muroAggiunto.emit(m)

    # ========== STRUMENTO MISURA ==========

    def startMisura(self, x: float, y: float):
        """Inizia misurazione"""
        self.misura_attiva = True
        self.misura_start = (x, y)
        self.misura_end = (x, y)
        self.misura_risultato = None

    def updateMisura(self, x: float, y: float):
        """Aggiorna punto finale misura"""
        if self.misura_attiva:
            self.misura_end = (x, y)
            dx = self.misura_end[0] - self.misura_start[0]
            dy = self.misura_end[1] - self.misura_start[1]
            self.misura_risultato = math.sqrt(dx*dx + dy*dy)

    def endMisura(self):
        """Termina misurazione"""
        self.misura_attiva = False

    def drawMisura(self, painter):
        """Disegna linea di misura"""
        if not self.misura_start or not self.misura_end:
            return

        x1, y1 = self.worldToScreen(self.misura_start[0], self.misura_start[1])
        x2, y2 = self.worldToScreen(self.misura_end[0], self.misura_end[1])

        # Linea tratteggiata
        pen = QPen(QColor(255, 100, 0), 2, Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(x1, y1, x2, y2)

        # Cerchi agli estremi
        painter.setBrush(QBrush(QColor(255, 100, 0)))
        painter.drawEllipse(QPointF(x1, y1), 5, 5)
        painter.drawEllipse(QPointF(x2, y2), 5, 5)

        # Testo distanza
        if self.misura_risultato is not None:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            painter.setPen(QPen(QColor(200, 50, 0)))
            painter.setFont(QFont("Arial", 12, QFont.Bold))
            painter.drawText(int(mx) + 10, int(my) - 10, f"{self.misura_risultato:.2f} m")

    # ========== STRUMENTO COPIA ==========

    def copiaSelezionati(self):
        """Copia muri selezionati nella clipboard"""
        if not self.progetto:
            return 0

        self.clipboard_muri = [m for m in self.progetto.muri if m.selected]
        return len(self.clipboard_muri)

    def incollaCliboard(self, offset_x: float = 0.5, offset_y: float = 0.5):
        """Incolla muri dalla clipboard con offset"""
        if not self.progetto or not self.clipboard_muri:
            return 0

        nuovi = 0
        n = len(self.progetto.muri)

        for muro in self.clipboard_muri:
            n += 1
            nuovo = Muro(
                nome=f"M{n}",
                x1=muro.x1 + offset_x,
                y1=muro.y1 + offset_y,
                x2=muro.x2 + offset_x,
                y2=muro.y2 + offset_y,
                spessore=muro.spessore,
                altezza=muro.altezza,
                materiale=muro.materiale,
                z=muro.z
            )
            self.progetto.muri.append(nuovo)
            self.muroAggiunto.emit(nuovo)
            nuovi += 1

        return nuovi

    # ========== STRUMENTO SPECCHIA ==========

    def specchiaMuri(self, asse: str = 'y', centro: float = 0.0):
        """Specchia muri selezionati rispetto a un asse"""
        if not self.progetto:
            return 0

        selezionati = [m for m in self.progetto.muri if m.selected]
        n = len(self.progetto.muri)
        nuovi = 0

        for muro in selezionati:
            n += 1
            if asse == 'y':
                # Specchia rispetto a asse Y (verticale)
                nuovo = Muro(
                    nome=f"M{n}",
                    x1=2*centro - muro.x1,
                    y1=muro.y1,
                    x2=2*centro - muro.x2,
                    y2=muro.y2,
                    spessore=muro.spessore,
                    altezza=muro.altezza,
                    materiale=muro.materiale,
                    z=muro.z
                )
            else:
                # Specchia rispetto a asse X (orizzontale)
                nuovo = Muro(
                    nome=f"M{n}",
                    x1=muro.x1,
                    y1=2*centro - muro.y1,
                    x2=muro.x2,
                    y2=2*centro - muro.y2,
                    spessore=muro.spessore,
                    altezza=muro.altezza,
                    materiale=muro.materiale,
                    z=muro.z
                )
            self.progetto.muri.append(nuovo)
            nuovi += 1

        return nuovi

    # ========== STRUMENTO OFFSET ==========

    def offsetMuro(self, distanza: float = 0.5):
        """Crea muro parallelo al selezionato"""
        if not self.progetto:
            return None

        selezionato = next((m for m in self.progetto.muri if m.selected), None)
        if not selezionato:
            return None

        dx = selezionato.x2 - selezionato.x1
        dy = selezionato.y2 - selezionato.y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0:
            return None

        # Normale al muro
        nx, ny = -dy/length, dx/length

        n = len(self.progetto.muri) + 1
        nuovo = Muro(
            nome=f"M{n}",
            x1=selezionato.x1 + nx * distanza,
            y1=selezionato.y1 + ny * distanza,
            x2=selezionato.x2 + nx * distanza,
            y2=selezionato.y2 + ny * distanza,
            spessore=selezionato.spessore,
            altezza=selezionato.altezza,
            materiale=selezionato.materiale,
            z=selezionato.z
        )
        self.progetto.muri.append(nuovo)
        self.muroAggiunto.emit(nuovo)
        return nuovo


# ============================================================================
# ANALYSIS DIALOG - SELEZIONE METODO DI CALCOLO
# ============================================================================

class AnalysisMethodDialog(QDialog):
    """Dialogo per selezionare e configurare il metodo di analisi"""

    def __init__(self, progetto: Progetto, parent=None):
        super().__init__(parent)
        self.progetto = progetto
        self.selected_method = None
        self.results = None

        self.setWindowTitle("🔬 SELEZIONE METODO DI ANALISI")
        self.setMinimumSize(900, 600)

        layout = QHBoxLayout(self)

        # SINISTRA: Lista metodi
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        title = QLabel("Metodi di Calcolo Disponibili")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #0066cc;")
        left_layout.addWidget(title)

        info = QLabel("Seleziona un metodo per vedere i dettagli")
        info.setStyleSheet("color: #666; margin-bottom: 10px;")
        left_layout.addWidget(info)

        # Lista metodi
        self.method_list = QListWidget()
        self.method_list.setMinimumWidth(300)
        self.method_list.setStyleSheet("""
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #cce0ff;
            }
            QListWidget::item:hover {
                background-color: #f0f0f0;
            }
        """)

        for key, info in ANALYSIS_METHODS.items():
            status = "✓" if info['available'] else "✗"
            item_text = f"{status} {info['name']}\n   Complessità: {info['complexity']} | Tempo: {info['time']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, key)
            if not info['available']:
                item.setForeground(QColor(150, 150, 150))
            self.method_list.addItem(item)

        self.method_list.currentItemChanged.connect(self.onMethodSelected)
        left_layout.addWidget(self.method_list)

        layout.addWidget(left_panel)

        # DESTRA: Dettagli e configurazione
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Dettagli metodo
        self.details_group = QGroupBox("Dettagli Metodo")
        details_layout = QVBoxLayout()

        self.method_title = QLabel("-")
        self.method_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        details_layout.addWidget(self.method_title)

        self.method_desc = QLabel("-")
        self.method_desc.setWordWrap(True)
        self.method_desc.setStyleSheet("color: #333; margin: 10px 0;")
        details_layout.addWidget(self.method_desc)

        self.method_ntc = QLabel("-")
        self.method_ntc.setStyleSheet("color: #0066cc; font-style: italic;")
        details_layout.addWidget(self.method_ntc)

        self.details_group.setLayout(details_layout)
        right_layout.addWidget(self.details_group)

        # Parametri materiale
        mat_group = QGroupBox("🧱 Parametri Materiale")
        mat_layout = QFormLayout()

        self.fm_spin = QDoubleSpinBox()
        self.fm_spin.setRange(0.5, 10.0)
        self.fm_spin.setValue(2.4)
        self.fm_spin.setSuffix(" MPa")
        mat_layout.addRow("fm (compressione):", self.fm_spin)

        self.tau0_spin = QDoubleSpinBox()
        self.tau0_spin.setRange(0.01, 0.5)
        self.tau0_spin.setValue(0.06)
        self.tau0_spin.setSuffix(" MPa")
        self.tau0_spin.setDecimals(3)
        mat_layout.addRow("τ0 (taglio):", self.tau0_spin)

        self.E_spin = QDoubleSpinBox()
        self.E_spin.setRange(500, 10000)
        self.E_spin.setValue(1500)
        self.E_spin.setSuffix(" MPa")
        mat_layout.addRow("E (modulo):", self.E_spin)

        self.gamma_m = QDoubleSpinBox()
        self.gamma_m.setRange(1.5, 3.5)
        self.gamma_m.setValue(2.0)
        mat_layout.addRow("γM:", self.gamma_m)

        self.fc_spin = QDoubleSpinBox()
        self.fc_spin.setRange(1.0, 1.35)
        self.fc_spin.setValue(1.35)
        mat_layout.addRow("FC:", self.fc_spin)

        mat_group.setLayout(mat_layout)
        right_layout.addWidget(mat_group)

        # Opzioni analisi
        opt_group = QGroupBox("⚙️ Opzioni Analisi")
        opt_layout = QVBoxLayout()

        self.include_weight = QCheckBox("Includi peso proprio")
        self.include_weight.setChecked(True)
        opt_layout.addWidget(self.include_weight)

        self.second_order = QCheckBox("Effetti del secondo ordine")
        opt_layout.addWidget(self.second_order)

        self.detailed_output = QCheckBox("Output dettagliato")
        self.detailed_output.setChecked(True)
        opt_layout.addWidget(self.detailed_output)

        opt_group.setLayout(opt_layout)
        right_layout.addWidget(opt_group)

        right_layout.addStretch()

        # Pulsanti
        btn_layout = QHBoxLayout()

        self.btn_run = QPushButton("▶ ESEGUI ANALISI")
        self.btn_run.setEnabled(False)
        self.btn_run.setMinimumHeight(50)
        self.btn_run.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.btn_run.clicked.connect(self.runAnalysis)
        btn_layout.addWidget(self.btn_run)

        btn_cancel = QPushButton("Annulla")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        right_layout.addLayout(btn_layout)

        layout.addWidget(right_panel)

        # Seleziona primo metodo disponibile
        self.method_list.setCurrentRow(0)

    def onMethodSelected(self, current, previous):
        if not current:
            return

        key = current.data(Qt.UserRole)
        info = ANALYSIS_METHODS.get(key, {})

        self.selected_method = key
        self.method_title.setText(info.get('name', '-'))
        self.method_desc.setText(info.get('description', '-'))
        self.method_ntc.setText(f"Riferimento: {info.get('ntc_ref', '-')}")

        self.btn_run.setEnabled(info.get('available', False))

        if not info.get('available', False):
            self.btn_run.setText("⚠ Modulo non disponibile")
        else:
            self.btn_run.setText(f"▶ ESEGUI {key}")

    def runAnalysis(self):
        """Esegue l'analisi selezionata"""
        if not self.selected_method:
            return

        if not self.progetto.muri:
            QMessageBox.warning(self, "Avviso", "Nessun muro nel progetto!")
            return

        # Progress dialog
        self.btn_run.setText("⏳ Analisi in corso...")
        self.btn_run.setEnabled(False)
        QApplication.processEvents()

        try:
            # Crea materiale
            material = None
            if POR_AVAILABLE:
                material = MaterialProperties(
                    fm=self.fm_spin.value(),
                    tau0=self.tau0_spin.value(),
                    E=self.E_spin.value(),
                    G=self.E_spin.value() / 2.5,
                    w=18.0
                )

            # Parametri sismici
            ag = self.progetto.sismici.ag_slv if self.progetto.sismici.ag_slv > 0 else 0.15

            # Stima massa
            massa_solai = sum(s.carico_totale * s.area for s in self.progetto.solai) / 10 if self.progetto.solai else 100
            massa_muri = sum(m.lunghezza * m.altezza * m.spessore * 18 for m in self.progetto.muri)
            massa_totale = massa_solai + massa_muri / 10
            V_totale = massa_totale * ag * 10

            # Esegui analisi in base al metodo
            results = {'method': self.selected_method, 'walls': []}
            max_dcr = 0
            n_ok = 0

            for muro in self.progetto.muri:
                wall_data = {
                    'length': muro.lunghezza,
                    'height': muro.altezza,
                    'thickness': muro.spessore
                }

                tot_len = sum(m.lunghezza for m in self.progetto.muri)
                N_muro = (muro.lunghezza / tot_len) * massa_totale * 10 if tot_len > 0 else 100
                V_muro = (muro.lunghezza / tot_len) * V_totale if tot_len > 0 else V_totale / len(self.progetto.muri)

                loads = {'vertical': N_muro, 'horizontal': V_muro}

                try:
                    if self.selected_method == 'POR' and POR_AVAILABLE:
                        options = AnalysisOptions(
                            gamma_m=self.gamma_m.value(),
                            FC=self.fc_spin.value(),
                            include_self_weight=self.include_weight.isChecked()
                        )
                        result = analyze_por(wall_data, material, loads, options)
                        Vu = result.get('global_capacity', {}).get('total_Vu', 1)
                        dcr = V_muro / max(Vu, 1)
                        failure = result.get('governing_failure', 'N/A')

                    elif self.selected_method == 'SAM' and SAM_AVAILABLE:
                        result = analyze_sam(wall_data, material, loads)
                        Vu = result.get('capacity', {}).get('Vu', 1)
                        dcr = V_muro / max(Vu, 1)
                        failure = result.get('failure_mode', 'N/A')

                    elif self.selected_method == 'PORFLEX' and PORFLEX_AVAILABLE:
                        result = analyze_porflex(wall_data, material, loads)
                        Vu = result.get('global_capacity', {}).get('total_Vu', 1)
                        dcr = V_muro / max(Vu, 1)
                        failure = result.get('governing_failure', 'N/A')

                    else:
                        # Metodo generico semplificato
                        fvd = self.tau0_spin.value() / self.gamma_m.value() / self.fc_spin.value()
                        Vu = fvd * 1000 * muro.lunghezza * muro.spessore
                        dcr = V_muro / max(Vu, 1)
                        failure = 'simplified'

                    muro.dcr = dcr
                    muro.verificato = dcr <= 1.0
                    max_dcr = max(max_dcr, dcr)
                    if dcr <= 1.0:
                        n_ok += 1

                    results['walls'].append({
                        'nome': muro.nome,
                        'dcr': dcr,
                        'Vu': Vu,
                        'failure': failure
                    })

                except Exception as e:
                    results['walls'].append({
                        'nome': muro.nome,
                        'dcr': 999,
                        'Vu': 0,
                        'failure': f'Error: {str(e)}'
                    })

            # Calcola indice rischio
            ir = 1.0 / max_dcr if max_dcr > 0 else 1.0
            self.progetto.indice_rischio = ir

            results['max_dcr'] = max_dcr
            results['ir'] = ir
            results['n_ok'] = n_ok
            results['n_total'] = len(self.progetto.muri)

            self.results = results
            self.showResults(results)

        except Exception as e:
            QMessageBox.critical(self, "Errore Analisi", f"Errore durante l'analisi:\n{str(e)}")

        finally:
            self.btn_run.setText(f"▶ ESEGUI {self.selected_method}")
            self.btn_run.setEnabled(True)

    def showResults(self, results):
        """Mostra i risultati dell'analisi"""
        ir = results.get('ir', 0)
        max_dcr = results.get('max_dcr', 0)
        n_ok = results.get('n_ok', 0)
        n_total = results.get('n_total', 0)

        if ir >= 1.0:
            status = "✓ STRUTTURA VERIFICATA"
            color = "green"
        elif ir >= 0.8:
            status = "⚠ CARENZE MODERATE"
            color = "orange"
        else:
            status = "✗ STRUTTURA NON VERIFICATA"
            color = "red"

        msg = f"""
<h2 style="color:{color}">{status}</h2>

<h3>RISULTATI ANALISI {results.get('method', '-')}</h3>

<table border="1" cellpadding="5" style="border-collapse: collapse;">
<tr><td><b>Indice di Rischio (IR)</b></td><td style="font-size:18px; color:{color}"><b>{ir:.3f}</b></td></tr>
<tr><td>DCR Massimo</td><td>{max_dcr:.3f}</td></tr>
<tr><td>Muri Verificati</td><td>{n_ok} / {n_total}</td></tr>
</table>

<h3>DETTAGLIO MURI</h3>
<table border="1" cellpadding="5" style="border-collapse: collapse;">
<tr><th>Muro</th><th>DCR</th><th>Vu [kN]</th><th>Stato</th></tr>
"""
        for w in results.get('walls', []):
            stato = "✓ OK" if w['dcr'] <= 1.0 else "✗ CRITICO"
            c = "green" if w['dcr'] <= 1.0 else "red"
            msg += f"<tr><td>{w['nome']}</td><td>{w['dcr']:.3f}</td><td>{w['Vu']:.1f}</td><td style='color:{c}'>{stato}</td></tr>\n"

        msg += "</table>"

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Risultati {results.get('method', 'Analisi')}")
        dlg.setMinimumSize(500, 400)

        layout = QVBoxLayout(dlg)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml(msg)
        layout.addWidget(text)

        btn = QPushButton("Chiudi")
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)

        dlg.exec_()


# ============================================================================
# PROPERTIES PANEL
# ============================================================================

class PropertiesPanel(QDockWidget):
    """Pannello proprietà contestuale"""

    def __init__(self, parent=None):
        super().__init__("Proprietà", parent)
        self.setMinimumWidth(250)

        self.stack = QStackedWidget()
        self.setWidget(self.stack)

        # Pagina vuota
        empty = QLabel("Seleziona un elemento\nper vederne le proprietà")
        empty.setAlignment(Qt.AlignCenter)
        empty.setStyleSheet("color: #888;")
        self.stack.addWidget(empty)

        # Pagina muro
        self.muro_widget = QWidget()
        muro_layout = QFormLayout(self.muro_widget)
        self.muro_nome = QLineEdit()
        self.muro_lunghezza = QLabel()
        self.muro_spessore = QDoubleSpinBox()
        self.muro_spessore.setRange(0.1, 1.0)
        self.muro_spessore.setSuffix(" m")
        self.muro_altezza = QDoubleSpinBox()
        self.muro_altezza.setRange(2.0, 6.0)
        self.muro_altezza.setSuffix(" m")
        self.muro_dcr = QLabel()

        muro_layout.addRow("Nome:", self.muro_nome)
        muro_layout.addRow("Lunghezza:", self.muro_lunghezza)
        muro_layout.addRow("Spessore:", self.muro_spessore)
        muro_layout.addRow("Altezza:", self.muro_altezza)
        muro_layout.addRow("DCR:", self.muro_dcr)

        self.stack.addWidget(self.muro_widget)

    def showMuroProperties(self, muro: Muro):
        self.muro_nome.setText(muro.nome)
        self.muro_lunghezza.setText(f"{muro.lunghezza:.2f} m")
        self.muro_spessore.setValue(muro.spessore)
        self.muro_altezza.setValue(muro.altezza)

        if muro.dcr > 0:
            color = "green" if muro.dcr <= 1.0 else "red"
            self.muro_dcr.setText(f"<span style='color:{color}'>{muro.dcr:.3f}</span>")
        else:
            self.muro_dcr.setText("-")

        self.stack.setCurrentIndex(1)

    def clearSelection(self):
        self.stack.setCurrentIndex(0)


# ============================================================================
# MAIN WINDOW
# ============================================================================

class MuraturaEditorV2(QMainWindow):
    """Finestra principale v2.0 con interfaccia step-by-step"""

    def __init__(self):
        super().__init__()
        self.progetto = Progetto()
        self.show_quick_actions = True

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Muratura v2.0 - Editor Strutturale")
        self.setGeometry(50, 50, 1400, 900)

        # Central widget con stack
        self.central_stack = QStackedWidget()
        self.setCentralWidget(self.central_stack)

        # Quick Actions (schermata iniziale)
        self.quick_actions = QuickActionsPanel()
        self.quick_actions.btn_nuovo.clicked.connect(self.nuovoProgetto)
        self.quick_actions.btn_apri.clicked.connect(self.apriProgetto)
        self.quick_actions.btn_esempio.clicked.connect(self.caricaEsempio)
        self.quick_actions.btn_guida.clicked.connect(self.mostraGuida)
        self.central_stack.addWidget(self.quick_actions)

        # Main workspace
        self.workspace = QWidget()
        workspace_layout = QHBoxLayout(self.workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)

        # Workflow panel (sinistra)
        self.workflow_panel = WorkflowPanel()
        self.workflow_panel.setFixedWidth(180)
        self.workflow_panel.stepClicked.connect(self.goToStep)
        workspace_layout.addWidget(self.workflow_panel)

        # Content stack (centro)
        self.content_stack = QStackedWidget()
        workspace_layout.addWidget(self.content_stack)

        # Step panels
        self.step_progetto = StepProgettoPanel(self.progetto)
        self.step_progetto.btn_avanti.clicked.connect(lambda: self.goToStep(WorkflowStep.PIANI))
        self.content_stack.addWidget(self.step_progetto)

        self.step_piani = StepPianiPanel(self.progetto)
        self.step_piani.btn_avanti.clicked.connect(lambda: self.goToStep(WorkflowStep.GEOMETRIA))
        self.content_stack.addWidget(self.step_piani)

        # Canvas (per step geometria e aperture)
        self.canvas = DrawingCanvas()
        self.canvas.setProgetto(self.progetto)
        self.canvas.muroAggiunto.connect(self.onMuroAggiunto)
        self.canvas.selectionChanged.connect(self.onSelectionChanged)
        self.content_stack.addWidget(self.canvas)

        # Step Fondazioni
        self.step_fondazioni = StepFondazioniPanel(self.progetto)
        self.step_fondazioni.btn_avanti.clicked.connect(lambda: self.goToStep(WorkflowStep.CORDOLI))
        self.content_stack.addWidget(self.step_fondazioni)

        # Step Cordoli/Tiranti
        self.step_cordoli = StepCordoliPanel(self.progetto)
        self.step_cordoli.btn_avanti.clicked.connect(lambda: self.goToStep(WorkflowStep.SOLAI))
        self.content_stack.addWidget(self.step_cordoli)

        # Step Solai
        self.step_solai = StepSolaiPanel(self.progetto)
        self.step_solai.btn_avanti.clicked.connect(lambda: self.goToStep(WorkflowStep.CARICHI))
        self.content_stack.addWidget(self.step_solai)

        # Step Carichi
        self.step_carichi = StepCarichiPanel(self.progetto)
        self.step_carichi.btn_avanti.clicked.connect(lambda: self.goToStep(WorkflowStep.MATERIALI))
        self.content_stack.addWidget(self.step_carichi)

        # Vista 3D
        self.vista_3d = Vista3DWidget()
        self.content_stack.addWidget(self.vista_3d)

        self.central_stack.addWidget(self.workspace)

        # Ribbon toolbar
        self.createRibbon()

        # Project Browser (dock sinistra)
        self.browser = ProjectBrowser(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.browser)
        self.browser.hide()  # Nascosto finché non c'è un progetto

        # Properties panel (dock destra)
        self.properties = PropertiesPanel(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties)
        self.properties.hide()

        # Status bar
        self.status_label = QLabel("Pronto")
        self.statusBar().addWidget(self.status_label)

        self.step_progress = QLabel("Step: -")
        self.statusBar().addPermanentWidget(self.step_progress)

    def createRibbon(self):
        self.ribbon = RibbonToolbar()

        # Tab HOME
        home_tab = RibbonTab()

        file_panel = RibbonPanel("File")
        btn_nuovo = RibbonButton("Nuovo")
        btn_nuovo.clicked.connect(self.nuovoProgetto)
        file_panel.addButton(btn_nuovo)
        btn_apri = RibbonButton("Apri")
        btn_apri.clicked.connect(self.apriProgetto)
        file_panel.addButton(btn_apri)
        btn_salva = RibbonButton("Salva")
        btn_salva.clicked.connect(self.salvaProgetto)
        file_panel.addButton(btn_salva)
        home_tab.addPanel(file_panel)

        tools_panel = RibbonPanel("Strumenti")
        self.btn_select = RibbonButton("Seleziona")
        self.btn_select.setCheckable(True)
        self.btn_select.setChecked(True)
        self.btn_select.clicked.connect(lambda: self.canvas.setStrumento('select'))
        tools_panel.addButton(self.btn_select)
        self.btn_muro = RibbonButton("Muro")
        self.btn_muro.setCheckable(True)
        self.btn_muro.clicked.connect(lambda: self.canvas.setStrumento('muro'))
        tools_panel.addButton(self.btn_muro)
        self.btn_rettangolo = RibbonButton("Rettangolo")
        self.btn_rettangolo.setCheckable(True)
        self.btn_rettangolo.setToolTip("Disegna 4 muri che formano un rettangolo")
        self.btn_rettangolo.clicked.connect(lambda: self.canvas.setStrumento('rettangolo'))
        tools_panel.addButton(self.btn_rettangolo)
        self.btn_apertura = RibbonButton("Apertura")
        self.btn_apertura.clicked.connect(self.aggiungiApertura)
        tools_panel.addButton(self.btn_apertura)
        home_tab.addPanel(tools_panel)

        # Pannello strumenti avanzati
        adv_panel = RibbonPanel("Avanzati")
        btn_misura = RibbonButton("Misura")
        btn_misura.setCheckable(True)
        btn_misura.setToolTip("Misura distanze nel disegno")
        btn_misura.clicked.connect(lambda: self.canvas.setStrumento('misura'))
        adv_panel.addButton(btn_misura)
        btn_copia = RibbonButton("Copia")
        btn_copia.setToolTip("Copia muri selezionati (Ctrl+C)")
        btn_copia.clicked.connect(self.copiaMuri)
        adv_panel.addButton(btn_copia)
        btn_incolla = RibbonButton("Incolla")
        btn_incolla.setToolTip("Incolla muri (Ctrl+V)")
        btn_incolla.clicked.connect(self.incollaMuri)
        adv_panel.addButton(btn_incolla)
        btn_specchia = RibbonButton("Specchia")
        btn_specchia.setToolTip("Specchia elementi selezionati")
        btn_specchia.clicked.connect(self.specchiaMuri)
        adv_panel.addButton(btn_specchia)
        btn_offset = RibbonButton("Offset")
        btn_offset.setToolTip("Crea muro parallelo")
        btn_offset.clicked.connect(self.offsetMuro)
        adv_panel.addButton(btn_offset)
        home_tab.addPanel(adv_panel)

        self.ribbon.addTab(home_tab, "Home")

        # Tab ANALISI
        analisi_tab = RibbonTab()

        verifica_panel = RibbonPanel("Verifica")
        btn_verifica = RibbonButton("Verifica\nRapida")
        btn_verifica.clicked.connect(self.verificaRapida)
        verifica_panel.addButton(btn_verifica)
        btn_analisi = RibbonButton("Analisi\nAvanzata")
        btn_analisi.setToolTip("Apre il pannello con tutti i 7 metodi di calcolo")
        btn_analisi.clicked.connect(self.analisiPOR)
        verifica_panel.addButton(btn_analisi)
        analisi_tab.addPanel(verifica_panel)

        risultati_panel = RibbonPanel("Risultati")
        btn_dcr = RibbonButton("Mostra\nDCR")
        btn_dcr.setCheckable(True)
        risultati_panel.addButton(btn_dcr)
        btn_3d = RibbonButton("Vista 3D")
        btn_3d.setToolTip("Mostra vista isometrica 3D dell'edificio")
        btn_3d.clicked.connect(self.mostraVista3D)
        risultati_panel.addButton(btn_3d)
        btn_report = RibbonButton("Report")
        btn_report.clicked.connect(self.esportaReport)
        risultati_panel.addButton(btn_report)
        analisi_tab.addPanel(risultati_panel)

        # Spettro
        spettro_panel = RibbonPanel("NTC 2018")
        btn_spettro = RibbonButton("Spettro\nSismico")
        btn_spettro.setToolTip("Visualizza spettro di risposta")
        btn_spettro.clicked.connect(self.mostraSpettro)
        spettro_panel.addButton(btn_spettro)
        btn_valida = RibbonButton("Valida\nGeometria")
        btn_valida.setToolTip("Verifica geometria edificio")
        btn_valida.clicked.connect(self.validaGeometria)
        spettro_panel.addButton(btn_valida)
        analisi_tab.addPanel(spettro_panel)

        self.ribbon.addTab(analisi_tab, "Analisi")

        # Aggiungi ribbon al layout
        # Il ribbon è separato dalla barra menu
        ribbon_dock = QDockWidget()
        ribbon_dock.setTitleBarWidget(QWidget())  # Nascondi title bar
        ribbon_dock.setWidget(self.ribbon)
        ribbon_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.addDockWidget(Qt.TopDockWidgetArea, ribbon_dock)

    def nuovoProgetto(self):
        self.progetto = Progetto()
        self.step_progetto.progetto = self.progetto
        self.canvas.setProgetto(self.progetto)

        # Mostra workspace
        self.central_stack.setCurrentWidget(self.workspace)
        self.browser.show()
        self.properties.show()

        # Vai al primo step
        self.goToStep(WorkflowStep.PROGETTO)

        self.status_label.setText("Nuovo progetto creato")

    def apriProgetto(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Apri Progetto", "", "File Muratura (*.mur)"
        )
        if filepath:
            # TODO: implementare caricamento
            self.status_label.setText(f"Aperto: {filepath}")

    def salvaProgetto(self):
        if not self.progetto.filepath:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Salva Progetto", "", "File Muratura (*.mur)"
            )
            if filepath:
                self.progetto.filepath = filepath

        if self.progetto.filepath:
            # TODO: implementare salvataggio
            self.status_label.setText(f"Salvato: {self.progetto.filepath}")

    def caricaEsempio(self):
        """Carica un progetto di esempio"""
        self.progetto = Progetto(nome="Edificio Esempio")
        self.progetto.n_piani = 2
        self.progetto.altezza_piano = 3.0
        self.progetto.sismici.comune = "ROMA"
        self.progetto.sismici.sottosuolo = "B"

        # Piani
        self.progetto.piani = [
            Piano(0, 0.0, 3.0, "Piano Terra"),
            Piano(1, 3.0, 3.0, "Piano Primo"),
        ]

        # Muri esempio (rettangolo 10x8m)
        self.progetto.muri = [
            Muro("M1", 0, 0, 10, 0, 0.30, 3.0),
            Muro("M2", 10, 0, 10, 8, 0.30, 3.0),
            Muro("M3", 10, 8, 0, 8, 0.30, 3.0),
            Muro("M4", 0, 8, 0, 0, 0.30, 3.0),
            Muro("M5", 5, 0, 5, 8, 0.25, 3.0),  # Muro interno
        ]

        # Aperture
        self.progetto.aperture = [
            Apertura("F1", "M1", "finestra", 1.2, 1.4, 2.0, 0.9),
            Apertura("F2", "M1", "finestra", 1.2, 1.4, 6.0, 0.9),
            Apertura("P1", "M3", "porta", 0.9, 2.1, 4.5, 0.0),
        ]

        # Solaio
        self.progetto.solai = [
            Solaio("S1", 0, "laterocemento", 10.0, 8.0, 3.2, 2.0, "A"),
        ]

        self.canvas.setProgetto(self.progetto)
        self.browser.updateFromProject(self.progetto)

        # Mostra workspace
        self.central_stack.setCurrentWidget(self.workspace)
        self.browser.show()
        self.properties.show()

        # Vai alla geometria
        self.goToStep(WorkflowStep.GEOMETRIA)

        self.status_label.setText("Caricato edificio di esempio")

    def mostraGuida(self):
        QMessageBox.information(self, "Guida Rapida", """
GUIDA RAPIDA - MURATURA v2.0

1. NUOVO PROGETTO
   Clicca "Nuovo Progetto" e segui il workflow guidato

2. WORKFLOW STEP-BY-STEP
   - Step 1: Inserisci dati progetto e localizzazione
   - Step 2: Definisci altezze piani
   - Step 3: Disegna i muri sulla pianta
   - Step 4: Aggiungi finestre e porte
   - Step 5: Definisci i solai
   - Step 6: Configura carichi
   - Step 7: Esegui analisi
   - Step 8: Visualizza risultati

3. STRUMENTI DISEGNO
   - Seleziona: clicca su un elemento
   - Muro: clicca inizio e fine
   - Rotella mouse: zoom

4. ANALISI
   - Verifica Rapida: calcolo DCR semplificato
   - Analisi POR: verifica NTC 2018 completa

5. EXPORT
   - Report HTML con tutti i risultati
        """)

    def goToStep(self, step: WorkflowStep):
        """Naviga a uno step del workflow"""
        # Salva dati step corrente
        if self.progetto.current_step == WorkflowStep.PROGETTO:
            self.step_progetto.saveData()
        elif self.progetto.current_step == WorkflowStep.PIANI:
            self.step_piani.saveData()

        # Marca completato se si va avanti
        if step.value > self.progetto.current_step.value:
            self.workflow_panel.markCompleted(self.progetto.current_step)

        self.progetto.current_step = step
        self.workflow_panel.setCurrentStep(step)

        # Mostra pannello appropriato
        if step == WorkflowStep.PROGETTO:
            self.content_stack.setCurrentWidget(self.step_progetto)
        elif step == WorkflowStep.PIANI:
            self.step_piani.refresh()
            self.content_stack.setCurrentWidget(self.step_piani)
        elif step in [WorkflowStep.GEOMETRIA, WorkflowStep.APERTURE]:
            self.content_stack.setCurrentWidget(self.canvas)
            if step == WorkflowStep.APERTURE:
                self.canvas.setStrumento('select')  # Per selezionare muri
        elif step == WorkflowStep.FONDAZIONI:
            self.step_fondazioni.refresh()
            self.content_stack.setCurrentWidget(self.step_fondazioni)
        elif step == WorkflowStep.CORDOLI:
            self.step_cordoli.refresh()
            self.content_stack.setCurrentWidget(self.step_cordoli)
        elif step == WorkflowStep.SOLAI:
            self.step_solai.refresh()
            self.content_stack.setCurrentWidget(self.step_solai)
        elif step == WorkflowStep.CARICHI:
            self.content_stack.setCurrentWidget(self.step_carichi)
        elif step == WorkflowStep.MATERIALI:
            self.content_stack.setCurrentWidget(self.canvas)  # Per ora usa canvas
        elif step == WorkflowStep.ANALISI:
            self.analisiPOR()  # Apri dialogo analisi
        elif step == WorkflowStep.RISULTATI:
            # Mostra vista 3D con risultati
            self.vista_3d.setProgetto(self.progetto)
            self.content_stack.setCurrentWidget(self.vista_3d)

        # Aggiorna browser
        self.browser.updateFromProject(self.progetto)

        self.step_progress.setText(f"Step: {STEP_NAMES[step]}")

    def aggiungiApertura(self):
        """Apre il dialogo per aggiungere un'apertura"""
        if not self.progetto.muri:
            QMessageBox.warning(self, "Avviso", "Disegna prima almeno un muro")
            return

        # Trova muro selezionato
        muro_sel = next((m.nome for m in self.progetto.muri if m.selected), "")

        dlg = DialogoApertura(self.progetto, muro_sel, self)
        if dlg.exec_() == QDialog.Accepted and dlg.apertura_creata:
            self.progetto.aperture.append(dlg.apertura_creata)
            self.browser.updateFromProject(self.progetto)
            self.canvas.update()
            self.status_label.setText(f"Aggiunta apertura: {dlg.apertura_creata.nome}")

    def verificaRapida(self):
        if not self.progetto.muri:
            QMessageBox.warning(self, "Avviso", "Nessun muro nel progetto")
            return

        # Calcolo DCR semplificato
        ag = self.progetto.sismici.ag_slv if self.progetto.sismici.ag_slv > 0 else 0.15
        massa = sum(s.carico_totale * s.area for s in self.progetto.solai) / 10 if self.progetto.solai else 100
        V_tot = massa * ag * 10

        n_muri = len(self.progetto.muri)
        V_muro = V_tot / n_muri

        max_dcr = 0
        for muro in self.progetto.muri:
            Vt = 0.1 * 1000 * muro.lunghezza * muro.spessore / 2  # Resistenza semplificata
            muro.dcr = V_muro / max(Vt, 1)
            muro.verificato = muro.dcr <= 1.0
            max_dcr = max(max_dcr, muro.dcr)

        self.progetto.indice_rischio = 1.0 / max_dcr if max_dcr > 0 else 1.0

        self.canvas.update()
        self.browser.updateFromProject(self.progetto)

        QMessageBox.information(self, "Verifica Completata", f"""
RISULTATI VERIFICA RAPIDA

Muri analizzati: {n_muri}
DCR massimo: {max_dcr:.3f}
Indice di Rischio: {self.progetto.indice_rischio:.3f}

{'✓ STRUTTURA VERIFICATA' if self.progetto.indice_rischio >= 1.0 else '✗ STRUTTURA NON VERIFICATA'}
        """)

    def analisiPOR(self):
        """Apre il dialogo per selezionare e lanciare qualsiasi metodo di analisi"""
        if not self.progetto.muri:
            QMessageBox.warning(self, "Avviso", "Nessun muro nel progetto.\nDisegna prima la struttura.")
            return

        dialogo = AnalysisMethodDialog(self.progetto, self)
        if dialogo.exec_() == QDialog.Accepted:
            # Aggiorna visualizzazione
            self.canvas.update()
            self.browser.updateFromProject(self.progetto)

    def esportaReport(self):
        if not self.progetto.muri:
            QMessageBox.warning(self, "Avviso", "Nessun dato da esportare")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Esporta Report", f"{self.progetto.nome}_report.html",
            "HTML (*.html);;PDF (*.pdf)"
        )

        if filepath:
            if filepath.endswith('.pdf'):
                self.esportaPDF(filepath)
            else:
                self.esportaHTML(filepath)

    def esportaHTML(self, filepath: str):
        """Esporta report in formato HTML"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Report Strutturale - {self.progetto.nome}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #0066cc; border-bottom: 2px solid #0066cc; }}
        h2 {{ color: #333; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #0066cc; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .ok {{ color: green; font-weight: bold; }}
        .ko {{ color: red; font-weight: bold; }}
        .warning {{ color: orange; }}
        .header-info {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>RELAZIONE DI CALCOLO STRUTTURALE</h1>
    <h2>{self.progetto.nome}</h2>

    <div class="header-info">
        <p><strong>Autore:</strong> {self.progetto.autore or '-'}</p>
        <p><strong>Data:</strong> {__import__('datetime').datetime.now().strftime('%d/%m/%Y')}</p>
        <p><strong>Software:</strong> Muratura v2.0 - Analisi Edifici in Muratura</p>
    </div>

    <h2>1. DATI GENERALI</h2>
    <table>
        <tr><th>Parametro</th><th>Valore</th></tr>
        <tr><td>Numero piani</td><td>{self.progetto.n_piani}</td></tr>
        <tr><td>Altezza interpiano</td><td>{self.progetto.altezza_piano} m</td></tr>
        <tr><td>Numero muri</td><td>{len(self.progetto.muri)}</td></tr>
        <tr><td>Numero aperture</td><td>{len(self.progetto.aperture)}</td></tr>
        <tr><td>Numero fondazioni</td><td>{len(self.progetto.fondazioni)}</td></tr>
    </table>

    <h2>2. PARAMETRI SISMICI</h2>
    <table>
        <tr><th>Parametro</th><th>Valore</th></tr>
        <tr><td>Comune</td><td>{self.progetto.sismici.comune}</td></tr>
        <tr><td>Categoria sottosuolo</td><td>{self.progetto.sismici.sottosuolo}</td></tr>
        <tr><td>Categoria topografica</td><td>{self.progetto.sismici.topografia}</td></tr>
        <tr><td>Vita nominale</td><td>{self.progetto.sismici.vita_nominale} anni</td></tr>
        <tr><td>Classe d'uso</td><td>{self.progetto.sismici.classe_uso}</td></tr>
        <tr><td>ag (SLV)</td><td>{self.progetto.sismici.ag_slv:.3f} g</td></tr>
        <tr><td>Fattore struttura q</td><td>{self.progetto.sismici.fattore_struttura}</td></tr>
    </table>

    <h2>3. GEOMETRIA MURI</h2>
    <table>
        <tr><th>Nome</th><th>L [m]</th><th>s [m]</th><th>h [m]</th><th>DCR</th><th>Stato</th></tr>
"""
        for m in self.progetto.muri:
            stato = "OK" if m.dcr <= 1.0 else "CRITICO"
            cls = "ok" if m.dcr <= 1.0 else "ko"
            html += f"<tr><td>{m.nome}</td><td>{m.lunghezza:.2f}</td><td>{m.spessore}</td><td>{m.altezza}</td><td>{m.dcr:.3f}</td><td class='{cls}'>{stato}</td></tr>\n"

        html += """    </table>

    <h2>4. APERTURE</h2>
    <table>
        <tr><th>Nome</th><th>Tipo</th><th>Muro</th><th>L [m]</th><th>H [m]</th></tr>
"""
        for ap in self.progetto.aperture:
            html += f"<tr><td>{ap.nome}</td><td>{ap.tipo}</td><td>{ap.muro}</td><td>{ap.larghezza}</td><td>{ap.altezza}</td></tr>\n"

        html += """    </table>

    <h2>5. FONDAZIONI</h2>
    <table>
        <tr><th>Nome</th><th>Tipo</th><th>Muro</th><th>B [m]</th><th>H [m]</th></tr>
"""
        for f in self.progetto.fondazioni:
            html += f"<tr><td>{f.nome}</td><td>{f.tipo}</td><td>{f.muro_collegato}</td><td>{f.larghezza}</td><td>{f.altezza}</td></tr>\n"

        # Risultati
        ir = self.progetto.indice_rischio
        ir_cls = "ok" if ir >= 1.0 else "ko" if ir < 0.8 else "warning"
        ir_stato = "VERIFICATA" if ir >= 1.0 else "NON VERIFICATA"

        html += f"""    </table>

    <h2>6. RISULTATI ANALISI</h2>
    <div class="header-info">
        <p><strong>Indice di Rischio (IR):</strong> <span class="{ir_cls}" style="font-size: 24px">{ir:.3f}</span></p>
        <p><strong>Esito:</strong> <span class="{ir_cls}">STRUTTURA {ir_stato}</span></p>
    </div>

    <hr>
    <p style="color: #999; font-size: 10px;">
        Generato con Muratura v2.0 - Software per analisi sismica edifici in muratura<br>
        Conforme NTC 2018 e Circolare n. 7/2019
    </p>
</body>
</html>
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        self.status_label.setText(f"Report HTML esportato: {filepath}")
        QMessageBox.information(self, "Export Completato",
            f"Report esportato in:\n{filepath}")

    def esportaPDF(self, filepath: str):
        """Esporta report in formato PDF (via HTML)"""
        # Prima esporta HTML temporaneo
        html_temp = filepath.replace('.pdf', '_temp.html')
        self.esportaHTML(html_temp)

        try:
            # Prova a usare weasyprint se disponibile
            from weasyprint import HTML
            HTML(html_temp).write_pdf(filepath)
            import os
            os.remove(html_temp)
            self.status_label.setText(f"Report PDF esportato: {filepath}")
            QMessageBox.information(self, "Export Completato",
                f"Report PDF esportato in:\n{filepath}")
        except ImportError:
            # Fallback: apri HTML nel browser per stampa PDF manuale
            import webbrowser
            webbrowser.open(html_temp)
            QMessageBox.information(self, "Export PDF",
                "WeasyPrint non installato.\n"
                "Il report HTML è stato aperto nel browser.\n"
                "Usa Stampa → Salva come PDF dal browser.")

    def onMuroAggiunto(self, muro: Muro):
        self.browser.updateFromProject(self.progetto)
        self.status_label.setText(f"Aggiunto: {muro.nome} ({muro.lunghezza:.2f}m)")

    def onSelectionChanged(self, obj):
        if isinstance(obj, Muro):
            self.properties.showMuroProperties(obj)
        else:
            self.properties.clearSelection()

    def copiaMuri(self):
        """Copia muri selezionati"""
        n = self.canvas.copiaSelezionati()
        if n > 0:
            self.status_label.setText(f"Copiati {n} muri")
        else:
            self.status_label.setText("Nessun muro selezionato")

    def incollaMuri(self):
        """Incolla muri dalla clipboard"""
        n = self.canvas.incollaCliboard()
        if n > 0:
            self.browser.updateFromProject(self.progetto)
            self.canvas.update()
            self.status_label.setText(f"Incollati {n} muri")
        else:
            self.status_label.setText("Niente da incollare")

    def specchiaMuri(self):
        """Specchia muri selezionati"""
        # Chiedi asse
        asse, ok = QInputDialog.getItem(self, "Specchia", "Specchia rispetto a:",
                                        ["Asse Y (verticale)", "Asse X (orizzontale)"], 0, False)
        if ok:
            asse_char = 'y' if 'Y' in asse else 'x'
            centro, ok2 = QInputDialog.getDouble(self, "Centro", f"Coordinata {asse_char.upper()} del centro:", 0.0)
            if ok2:
                n = self.canvas.specchiaMuri(asse_char, centro)
                if n > 0:
                    self.browser.updateFromProject(self.progetto)
                    self.canvas.update()
                    self.status_label.setText(f"Specchiati {n} muri")

    def offsetMuro(self):
        """Crea muro parallelo"""
        dist, ok = QInputDialog.getDouble(self, "Offset", "Distanza offset (m):", 0.5, 0.1, 5.0, 2)
        if ok:
            nuovo = self.canvas.offsetMuro(dist)
            if nuovo:
                self.browser.updateFromProject(self.progetto)
                self.canvas.update()
                self.status_label.setText(f"Creato muro offset: {nuovo.nome}")
            else:
                self.status_label.setText("Seleziona prima un muro")

    def mostraVista3D(self):
        """Mostra vista 3D dell'edificio"""
        self.vista_3d.setProgetto(self.progetto)
        self.content_stack.setCurrentWidget(self.vista_3d)
        self.status_label.setText("Vista 3D - Click per ruotare, rotella per zoom")

    def mostraSpettro(self):
        """Mostra spettro sismico"""
        dlg = QDialog(self)
        dlg.setWindowTitle("📊 Spettro di Risposta NTC 2018")
        dlg.setMinimumSize(700, 500)

        layout = QVBoxLayout(dlg)

        # Widget spettro
        spettro = SpettroWidget()

        # Imposta parametri dal progetto
        ag = self.progetto.sismici.ag_slv if self.progetto.sismici.ag_slv > 0 else 0.15
        q = self.progetto.sismici.fattore_struttura if hasattr(self.progetto.sismici, 'fattore_struttura') else 2.0
        spettro.setParametri(ag, 2.5, 0.5, 1.2, q)

        layout.addWidget(spettro)

        # Controlli
        ctrl_layout = QHBoxLayout()

        lbl_q = QLabel("Fattore q:")
        ctrl_layout.addWidget(lbl_q)

        spin_q = QDoubleSpinBox()
        spin_q.setRange(1.0, 5.0)
        spin_q.setValue(q)
        spin_q.valueChanged.connect(lambda v: spettro.setParametri(ag, 2.5, 0.5, 1.2, v))
        ctrl_layout.addWidget(spin_q)

        ctrl_layout.addStretch()

        cb_progetto = QCheckBox("Mostra spettro di progetto")
        cb_progetto.setChecked(True)
        cb_progetto.toggled.connect(lambda c: setattr(spettro, 'show_progetto', c) or spettro.update())
        ctrl_layout.addWidget(cb_progetto)

        layout.addLayout(ctrl_layout)

        btn_close = QPushButton("Chiudi")
        btn_close.clicked.connect(dlg.accept)
        layout.addWidget(btn_close)

        dlg.exec_()

    def validaGeometria(self):
        """Valida geometria edificio"""
        risultati = GeometryValidator.validaTutto(self.progetto)

        msg = "<h2>🔍 VALIDAZIONE GEOMETRIA</h2>"

        tot_errori = 0
        tot_warnings = 0

        # Aperture
        msg += "<h3>Aperture</h3>"
        if risultati['aperture']:
            for err in risultati['aperture']:
                msg += f"<p style='color:red'>❌ {err}</p>"
                tot_errori += 1
        else:
            msg += "<p style='color:green'>✓ Tutte le aperture sono corrette</p>"

        # Chiusura
        msg += "<h3>Connessione Muri</h3>"
        if risultati['chiusura']:
            for warn in risultati['chiusura']:
                msg += f"<p style='color:orange'>⚠️ {warn}</p>"
                tot_warnings += 1
        else:
            msg += "<p style='color:green'>✓ Tutti i muri sono connessi</p>"

        # Sovrapposizioni
        msg += "<h3>Sovrapposizioni</h3>"
        if risultati['sovrapposizioni']:
            for warn in risultati['sovrapposizioni']:
                msg += f"<p style='color:orange'>⚠️ {warn}</p>"
                tot_warnings += 1
        else:
            msg += "<p style='color:green'>✓ Nessuna sovrapposizione</p>"

        # Riepilogo
        msg += "<hr><h3>Riepilogo</h3>"
        if tot_errori == 0 and tot_warnings == 0:
            msg += "<p style='color:green; font-size:14px; font-weight:bold'>✓ GEOMETRIA VALIDA</p>"
        elif tot_errori == 0:
            msg += f"<p style='color:orange; font-weight:bold'>⚠️ {tot_warnings} avvisi da verificare</p>"
        else:
            msg += f"<p style='color:red; font-weight:bold'>❌ {tot_errori} errori da correggere</p>"

        dlg = QDialog(self)
        dlg.setWindowTitle("Validazione Geometria")
        dlg.setMinimumSize(500, 400)

        layout = QVBoxLayout(dlg)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml(msg)
        layout.addWidget(text)

        btn = QPushButton("Chiudi")
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)

        dlg.exec_()


# ============================================================================
# MAIN
# ============================================================================

def main():
    app = QApplication(sys.argv)

    # Stile globale
    app.setStyle('Fusion')

    editor = MuraturaEditorV2()
    editor.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
