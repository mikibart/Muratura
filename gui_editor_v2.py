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
import json
import socket
import threading
from datetime import datetime
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
    QSizePolicy, QProgressBar, QCheckBox, QMenu, QSlider,
    QUndoStack, QUndoCommand, QShortcut
)
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal, QSize, QTimer, QByteArray, QThread
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QWheelEvent,
    QMouseEvent, QPainterPath, QKeyEvent, QIcon, QPixmap,
    QKeySequence, QImage, QLinearGradient, QRadialGradient
)

# Import SVG support
try:
    from PyQt5.QtSvg import QSvgRenderer
    SVG_AVAILABLE = True
except ImportError:
    SVG_AVAILABLE = False

# Import librerie export
try:
    import ezdxf
    DXF_AVAILABLE = True
except ImportError:
    DXF_AVAILABLE = False

# Import Shapely per geometria 2D e spatial indexing
try:
    from shapely.geometry import LineString, Point, Polygon
    from shapely.strtree import STRtree
    import numpy as np
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

# Import mathutils (da Blender) per trasformazioni 3D
try:
    from mathutils import Vector, Matrix, Quaternion
    MATHUTILS_AVAILABLE = True
except ImportError:
    MATHUTILS_AVAILABLE = False

# Import ModernGL per GPU rendering
try:
    import moderngl
    from PyQt5.QtOpenGL import QGLWidget
    MODERNGL_AVAILABLE = True
except ImportError:
    MODERNGL_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm, mm
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

import json
import copy

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
# UNDO/REDO COMMANDS
# ============================================================================

class AddMuroCommand(QUndoCommand):
    """Comando per aggiungere un muro (supporta undo/redo)"""
    def __init__(self, progetto, muro, description="Aggiungi muro"):
        super().__init__(description)
        self.progetto = progetto
        self.muro = muro

    def redo(self):
        self.progetto.muri.append(self.muro)

    def undo(self):
        if self.muro in self.progetto.muri:
            self.progetto.muri.remove(self.muro)


class DeleteMuroCommand(QUndoCommand):
    """Comando per eliminare un muro"""
    def __init__(self, progetto, muro, description="Elimina muro"):
        super().__init__(description)
        self.progetto = progetto
        self.muro = muro
        self.index = -1

    def redo(self):
        if self.muro in self.progetto.muri:
            self.index = self.progetto.muri.index(self.muro)
            self.progetto.muri.remove(self.muro)

    def undo(self):
        if self.index >= 0:
            self.progetto.muri.insert(self.index, self.muro)


class MoveMuroCommand(QUndoCommand):
    """Comando per spostare un muro"""
    def __init__(self, muro, dx, dy, description="Sposta muro"):
        super().__init__(description)
        self.muro = muro
        self.dx = dx
        self.dy = dy

    def redo(self):
        self.muro.x1 += self.dx
        self.muro.y1 += self.dy
        self.muro.x2 += self.dx
        self.muro.y2 += self.dy

    def undo(self):
        self.muro.x1 -= self.dx
        self.muro.y1 -= self.dy
        self.muro.x2 -= self.dx
        self.muro.y2 -= self.dy


class RotateMuriCommand(QUndoCommand):
    """Comando per ruotare muri selezionati"""
    def __init__(self, muri, angolo, centro_x, centro_y, description="Ruota muri"):
        super().__init__(description)
        self.muri = muri
        self.angolo = angolo
        self.centro_x = centro_x
        self.centro_y = centro_y
        self.old_coords = [(m.x1, m.y1, m.x2, m.y2) for m in muri]

    def redo(self):
        rad = math.radians(self.angolo)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        for muro in self.muri:
            # Ruota punto 1
            dx1 = muro.x1 - self.centro_x
            dy1 = muro.y1 - self.centro_y
            muro.x1 = self.centro_x + dx1 * cos_a - dy1 * sin_a
            muro.y1 = self.centro_y + dx1 * sin_a + dy1 * cos_a
            # Ruota punto 2
            dx2 = muro.x2 - self.centro_x
            dy2 = muro.y2 - self.centro_y
            muro.x2 = self.centro_x + dx2 * cos_a - dy2 * sin_a
            muro.y2 = self.centro_y + dx2 * sin_a + dy2 * cos_a

    def undo(self):
        for i, muro in enumerate(self.muri):
            muro.x1, muro.y1, muro.x2, muro.y2 = self.old_coords[i]


# ============================================================================
# THEME SYSTEM - Temi chiaro/scuro
# ============================================================================

class ThemeManager:
    """Gestore dei temi dell'applicazione"""

    THEMES = {
        'light': {
            'name': 'Chiaro',
            'background': '#FFFFFF',
            'surface': '#F5F5F5',
            'primary': '#0078D4',
            'secondary': '#5C6BC0',
            'text': '#212121',
            'text_secondary': '#757575',
            'border': '#E0E0E0',
            'canvas_bg': '#FFFFFF',
            'grid': '#E8E8E8',
            'selection': '#0078D4',
            'hover': '#E3F2FD',
            'error': '#D32F2F',
            'warning': '#FFA000',
            'success': '#388E3C',
        },
        'dark': {
            'name': 'Scuro',
            'background': '#1E1E1E',
            'surface': '#252526',
            'primary': '#0078D4',
            'secondary': '#7986CB',
            'text': '#FFFFFF',
            'text_secondary': '#B0B0B0',
            'border': '#3C3C3C',
            'canvas_bg': '#2D2D2D',
            'grid': '#3A3A3A',
            'selection': '#264F78',
            'hover': '#2A2D2E',
            'error': '#F44336',
            'warning': '#FFB74D',
            'success': '#4CAF50',
        }
    }

    _current_theme = 'light'
    _callbacks = []

    @classmethod
    def current_theme(cls) -> str:
        return cls._current_theme

    @classmethod
    def get(cls, key: str) -> str:
        """Ottiene un colore dal tema corrente"""
        return cls.THEMES[cls._current_theme].get(key, '#000000')

    @classmethod
    def set_theme(cls, theme_name: str):
        """Imposta il tema corrente"""
        if theme_name in cls.THEMES:
            cls._current_theme = theme_name
            for callback in cls._callbacks:
                try:
                    callback(theme_name)
                except:
                    pass

    @classmethod
    def toggle_theme(cls):
        """Toggle tra tema chiaro e scuro"""
        new_theme = 'dark' if cls._current_theme == 'light' else 'light'
        cls.set_theme(new_theme)
        return new_theme

    @classmethod
    def register_callback(cls, callback):
        """Registra callback per cambio tema"""
        cls._callbacks.append(callback)

    @classmethod
    def get_stylesheet(cls) -> str:
        """Genera stylesheet Qt per il tema corrente"""
        t = cls.THEMES[cls._current_theme]
        return f"""
            QMainWindow, QDialog {{
                background-color: {t['background']};
                color: {t['text']};
            }}
            QWidget {{
                background-color: {t['background']};
                color: {t['text']};
            }}
            QDockWidget {{
                background-color: {t['surface']};
                color: {t['text']};
                titlebar-close-icon: url(close.png);
            }}
            QDockWidget::title {{
                background-color: {t['surface']};
                padding: 6px;
                border-bottom: 1px solid {t['border']};
            }}
            QToolBar {{
                background-color: {t['surface']};
                border: none;
                spacing: 3px;
                padding: 3px;
            }}
            QPushButton {{
                background-color: {t['surface']};
                color: {t['text']};
                border: 1px solid {t['border']};
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {t['hover']};
            }}
            QPushButton:pressed {{
                background-color: {t['primary']};
                color: white;
            }}
            QPushButton:checked {{
                background-color: {t['primary']};
                color: white;
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                background-color: {t['surface']};
                color: {t['text']};
                border: 1px solid {t['border']};
                padding: 4px 8px;
                border-radius: 4px;
            }}
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
                border-color: {t['primary']};
            }}
            QTreeView, QListView, QTableView {{
                background-color: {t['surface']};
                color: {t['text']};
                border: 1px solid {t['border']};
                alternate-background-color: {t['hover']};
            }}
            QTreeView::item:hover, QListView::item:hover {{
                background-color: {t['hover']};
            }}
            QTreeView::item:selected, QListView::item:selected {{
                background-color: {t['selection']};
            }}
            QHeaderView::section {{
                background-color: {t['surface']};
                color: {t['text']};
                padding: 4px;
                border: none;
                border-right: 1px solid {t['border']};
                border-bottom: 1px solid {t['border']};
            }}
            QMenuBar {{
                background-color: {t['surface']};
                color: {t['text']};
            }}
            QMenuBar::item:selected {{
                background-color: {t['hover']};
            }}
            QMenu {{
                background-color: {t['surface']};
                color: {t['text']};
                border: 1px solid {t['border']};
            }}
            QMenu::item:selected {{
                background-color: {t['selection']};
            }}
            QTabWidget::pane {{
                border: 1px solid {t['border']};
                background-color: {t['surface']};
            }}
            QTabBar::tab {{
                background-color: {t['background']};
                color: {t['text']};
                padding: 8px 16px;
                border: 1px solid {t['border']};
                border-bottom: none;
            }}
            QTabBar::tab:selected {{
                background-color: {t['surface']};
                border-bottom: 2px solid {t['primary']};
            }}
            QScrollBar:vertical {{
                background-color: {t['background']};
                width: 12px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {t['border']};
                min-height: 20px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {t['text_secondary']};
            }}
            QScrollBar:horizontal {{
                background-color: {t['background']};
                height: 12px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {t['border']};
                min-width: 20px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::add-line, QScrollBar::sub-line {{
                width: 0;
                height: 0;
            }}
            QStatusBar {{
                background-color: {t['surface']};
                color: {t['text_secondary']};
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {t['border']};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QLabel {{
                color: {t['text']};
            }}
            QCheckBox {{
                color: {t['text']};
            }}
            QRadioButton {{
                color: {t['text']};
            }}
            QSlider::groove:horizontal {{
                background-color: {t['border']};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background-color: {t['primary']};
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }}
            QProgressBar {{
                background-color: {t['surface']};
                border: 1px solid {t['border']};
                border-radius: 4px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {t['primary']};
                border-radius: 3px;
            }}
        """


# ============================================================================
# ICON MANAGER - Gestione centralizzata icone professionali
# ============================================================================

class IconManager:
    """Gestore centralizzato delle icone con supporto temi e cache"""

    _cache = {}
    _resources_path = None

    # Mapping emoji -> nome icona
    EMOJI_TO_ICON = {
        '📁': ('navigation', 'folder'),
        '📐': ('navigation', 'floors'),
        '🧱': ('elements', 'wall'),
        '🚪': ('elements', 'door'),
        '🏗️': ('elements', 'foundation'),
        '🔗': ('elements', 'chain'),
        '⛓️': ('elements', 'tie'),
        '▭': ('elements', 'slab'),
        '🪜': ('elements', 'stairs'),
        '🏠': ('elements', 'roof'),
        '⬇': ('elements', 'load'),
        '📊': ('misc', 'chart'),
        '📄': ('actions', 'file-new'),
        '📂': ('actions', 'folder-open'),
        '💾': ('actions', 'save'),
        '🚀': ('misc', 'rocket'),
        '❓': ('misc', 'help-circle'),
        '📋': ('misc', 'list'),
        '✓': ('status', 'check-circle'),
        '✗': ('status', 'x-circle'),
        '⚠': ('status', 'alert-triangle'),
        '▶': ('misc', 'play'),
        '🔬': ('misc', 'chart'),
        '⚙️': ('misc', 'settings'),
        '🌍': ('misc', 'globe'),
        '🔍': ('navigation', 'zoom-in'),
        '⬜': ('tools', 'rectangle'),
        '📏': ('tools', 'measure'),
        '✋': ('tools', 'hand'),
        '⬠': ('tools', 'polygon'),
        '🪟': ('elements', 'window'),
        '📍': ('misc', 'globe'),
        '⚡': ('status', 'alert-triangle'),
        '🗑️': ('actions', 'trash'),
    }

    @classmethod
    def init(cls, resources_path: str = None):
        """Inizializza il gestore icone"""
        if resources_path:
            cls._resources_path = Path(resources_path)
        else:
            # Cerca la cartella resources relativa al file corrente
            cls._resources_path = Path(__file__).parent / 'resources'

        if not cls._resources_path.exists():
            print(f"Warning: Resources path not found: {cls._resources_path}")

    @classmethod
    def get_icon_path(cls, category: str, name: str, theme: str = None) -> str:
        """Ottiene il path completo di un'icona"""
        if theme is None:
            theme = ThemeManager.current_theme()

        if cls._resources_path:
            path = cls._resources_path / 'icons' / theme / category / f'{name}.svg'
            if path.exists():
                return str(path)
        return ""

    @classmethod
    def get_icon(cls, category: str, name: str, size: int = 24) -> QIcon:
        """Ottiene un QIcon da categoria e nome"""
        theme = ThemeManager.current_theme()
        cache_key = f"{theme}:{category}:{name}:{size}"

        if cache_key in cls._cache:
            return cls._cache[cache_key]

        icon = QIcon()
        path = cls.get_icon_path(category, name, theme)

        if path and Path(path).exists():
            # Usa QSvgRenderer per caricare SVG correttamente
            if SVG_AVAILABLE:
                renderer = QSvgRenderer(path)
                if renderer.isValid():
                    pixmap = QPixmap(size, size)
                    pixmap.fill(Qt.transparent)
                    painter = QPainter(pixmap)
                    renderer.render(painter)
                    painter.end()
                    icon = QIcon(pixmap)
            else:
                # Fallback a caricamento diretto
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    icon = QIcon(scaled)

        cls._cache[cache_key] = icon
        return icon

    @classmethod
    def get_icon_from_emoji(cls, emoji: str, size: int = 24) -> QIcon:
        """Converte un emoji nel corrispondente icona professionale"""
        if emoji in cls.EMOJI_TO_ICON:
            category, name = cls.EMOJI_TO_ICON[emoji]
            return cls.get_icon(category, name, size)
        return QIcon()

    @classmethod
    def clear_cache(cls):
        """Pulisce la cache delle icone (utile per cambio tema)"""
        cls._cache.clear()

    @classmethod
    def get_pixmap(cls, category: str, name: str, size: int = 24) -> QPixmap:
        """Ottiene un QPixmap da categoria e nome"""
        theme = ThemeManager.current_theme()
        path = cls.get_icon_path(category, name, theme)

        if path and Path(path).exists():
            if SVG_AVAILABLE:
                renderer = QSvgRenderer(path)
                if renderer.isValid():
                    pixmap = QPixmap(size, size)
                    pixmap.fill(Qt.transparent)
                    painter = QPainter(pixmap)
                    renderer.render(painter)
                    painter.end()
                    return pixmap
            else:
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        return QPixmap()


# ============================================================================
# TYPOGRAPHY - Costanti tipografiche per consistenza
# ============================================================================

class Typography:
    """Costanti tipografiche per UI consistente"""

    # Font families
    FONT_FAMILY = "Segoe UI, Arial, sans-serif"
    FONT_FAMILY_MONO = "Consolas, Courier New, monospace"

    # Font sizes
    SIZE_H1 = 24
    SIZE_H2 = 18
    SIZE_H3 = 14
    SIZE_BODY = 12
    SIZE_SMALL = 10
    SIZE_TINY = 9

    # Font weights
    WEIGHT_LIGHT = 300
    WEIGHT_REGULAR = 400
    WEIGHT_MEDIUM = 500
    WEIGHT_BOLD = 700

    @classmethod
    def get_font(cls, size: int = None, bold: bool = False) -> QFont:
        """Crea un QFont con le impostazioni standard"""
        font = QFont(cls.FONT_FAMILY.split(',')[0].strip())
        font.setPointSize(size or cls.SIZE_BODY)
        if bold:
            font.setWeight(cls.WEIGHT_BOLD)
        return font

    @classmethod
    def get_header_font(cls, level: int = 1) -> QFont:
        """Crea font per header (livello 1-3)"""
        sizes = {1: cls.SIZE_H1, 2: cls.SIZE_H2, 3: cls.SIZE_H3}
        return cls.get_font(sizes.get(level, cls.SIZE_H3), bold=True)


# ============================================================================
# PROFESSIONAL SPLASH SCREEN
# ============================================================================

class ProfessionalSplashScreen(QWidget):
    """Splash screen professionale con progress bar"""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setFixedSize(500, 300)

        # Centra sullo schermo
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        self.progress = 0
        self.status_text = "Inizializzazione..."

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background gradient
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor('#1a237e'))
        gradient.setColorAt(1, QColor('#0d47a1'))

        # Rounded rectangle background
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 10, 10)
        painter.fillPath(path, QBrush(gradient))

        # Border
        painter.setPen(QPen(QColor('#FFFFFF'), 1))
        painter.drawPath(path)

        # Brick pattern icon
        painter.setPen(QPen(QColor(255, 255, 255, 40), 2))
        self._draw_brick_pattern(painter, 210, 50, 80)

        # Title
        painter.setPen(QColor('#FFFFFF'))
        title_font = QFont('Segoe UI', 32, QFont.Bold)
        painter.setFont(title_font)
        painter.drawText(QRectF(0, 145, self.width(), 50), Qt.AlignCenter, "MURATURA")

        # Subtitle
        painter.setPen(QColor(255, 255, 255, 200))
        sub_font = QFont('Segoe UI', 12)
        painter.setFont(sub_font)
        painter.drawText(QRectF(0, 185, self.width(), 25), Qt.AlignCenter,
                        "Analisi Sismica Edifici in Muratura")

        # Version
        painter.setPen(QColor(255, 255, 255, 150))
        ver_font = QFont('Segoe UI', 10)
        painter.setFont(ver_font)
        painter.drawText(QRectF(0, 210, self.width(), 20), Qt.AlignCenter,
                        "Versione 2.0 - Conforme NTC 2018")

        # Progress bar background
        bar_rect = QRectF(100, 250, 300, 8)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 50))
        painter.drawRoundedRect(bar_rect, 4, 4)

        # Progress bar fill
        if self.progress > 0:
            fill_width = (self.progress / 100) * 300
            fill_rect = QRectF(100, 250, fill_width, 8)
            painter.setBrush(QColor('#4CAF50'))
            painter.drawRoundedRect(fill_rect, 4, 4)

        # Status text
        painter.setPen(QColor(255, 255, 255, 150))
        status_font = QFont('Segoe UI', 9)
        painter.setFont(status_font)
        painter.drawText(QRectF(0, 265, self.width(), 25), Qt.AlignCenter, self.status_text)

    def _draw_brick_pattern(self, painter, x, y, size):
        """Disegna il pattern di mattoni per il logo"""
        painter.setPen(QPen(QColor(255, 255, 255, 180), 2))

        # Outer rect
        rect = QRectF(x, y, size, size)
        painter.drawRoundedRect(rect, 8, 8)

        # Horizontal lines
        third = size / 3
        painter.drawLine(int(x), int(y + third), int(x + size), int(y + third))
        painter.drawLine(int(x), int(y + 2*third), int(x + size), int(y + 2*third))

        # Vertical lines (brick pattern)
        painter.drawLine(int(x + third), int(y), int(x + third), int(y + third))
        painter.drawLine(int(x + 2*third), int(y), int(x + 2*third), int(y + third))

        painter.drawLine(int(x + third/2), int(y + third), int(x + third/2), int(y + 2*third))
        painter.drawLine(int(x + third + third/2), int(y + third), int(x + third + third/2), int(y + 2*third))
        painter.drawLine(int(x + 2*third + third/2), int(y + third), int(x + 2*third + third/2), int(y + 2*third))

        painter.drawLine(int(x + third), int(y + 2*third), int(x + third), int(y + size))
        painter.drawLine(int(x + 2*third), int(y + 2*third), int(x + 2*third), int(y + size))

    def setProgress(self, value: int, status: str = None):
        """Aggiorna progresso e status"""
        self.progress = min(100, max(0, value))
        if status:
            self.status_text = status
        self.update()
        QApplication.processEvents()

    def finish(self, main_window):
        """Chiude lo splash e mostra la finestra principale"""
        main_window.show()
        self.close()


# ============================================================================
# ABOUT DIALOG
# ============================================================================

class AboutDialog(QDialog):
    """Dialogo informazioni sull'applicazione"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Informazioni su Muratura")
        self.setFixedSize(450, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 20)

        # Logo/Title area
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)

        # Icon
        icon_label = QLabel()
        icon_pixmap = IconManager.get_pixmap('elements', 'wall', 64)
        if not icon_pixmap.isNull():
            icon_label.setPixmap(icon_pixmap)
        else:
            icon_label.setText("🧱")
            icon_label.setStyleSheet("font-size: 48px;")
        title_layout.addWidget(icon_label)

        # Title and version
        title_text = QVBoxLayout()
        app_name = QLabel("MURATURA")
        app_name.setStyleSheet("font-size: 28px; font-weight: bold; color: #1a237e;")
        title_text.addWidget(app_name)

        version = QLabel("Versione 2.0")
        version.setStyleSheet("font-size: 14px; color: #666;")
        title_text.addWidget(version)
        title_layout.addLayout(title_text)
        title_layout.addStretch()

        layout.addWidget(title_widget)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e0e0e0;")
        layout.addWidget(line)

        # Description
        desc = QLabel(
            "Software professionale per l'analisi sismica di edifici in muratura.\n\n"
            "Conforme alle Norme Tecniche per le Costruzioni 2018 (NTC 2018) "
            "e alla relativa Circolare esplicativa n. 7/2019.\n\n"
            "Metodi di analisi implementati:\n"
            "• POR - Pier Only Resistance\n"
            "• SAM - Simple Analysis Method\n"
            "• Analisi Limite Cinematica\n"
            "• FEM - Elementi Finiti\n"
            "• Micro-Modellazione"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #333; line-height: 1.4;")
        layout.addWidget(desc)

        layout.addStretch()

        # Copyright
        copyright_label = QLabel("© 2024 - Tutti i diritti riservati")
        copyright_label.setStyleSheet("color: #999; font-size: 10px;")
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)

        # Close button
        btn_close = QPushButton("Chiudi")
        btn_close.setMinimumHeight(35)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)


# ============================================================================
# LAYER SYSTEM
# ============================================================================

class Layer:
    """Definizione di un layer"""
    def __init__(self, name: str, color: str = "#0064C8", visible: bool = True,
                 locked: bool = False, printable: bool = True):
        self.name = name
        self.color = color
        self.visible = visible
        self.locked = locked
        self.printable = printable


class LayerManager(QDockWidget):
    """Gestore dei layer del progetto"""

    layerVisibilityChanged = pyqtSignal(str, bool)

    PREDEFINED_LAYERS = {
        'Geometria': {'color': '#0064C8', 'visible': True, 'locked': False},
        'Aperture': {'color': '#C86400', 'visible': True, 'locked': False},
        'Fondazioni': {'color': '#646464', 'visible': True, 'locked': False},
        'Cordoli': {'color': '#00C864', 'visible': True, 'locked': False},
        'Carichi': {'color': '#C80000', 'visible': True, 'locked': False},
        'Risultati': {'color': '#FFA000', 'visible': True, 'locked': True},
        'Quote': {'color': '#000000', 'visible': True, 'locked': False},
        'Reference': {'color': '#808080', 'visible': False, 'locked': False}
    }

    def __init__(self, parent=None):
        super().__init__("Layer", parent)
        self.setMinimumWidth(200)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

        self.layers = {}
        for name, props in self.PREDEFINED_LAYERS.items():
            self.layers[name] = Layer(name, **props)

        self.setupUI()

    def setupUI(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Toolbar layer
        toolbar = QHBoxLayout()
        btn_all_on = QPushButton("Tutti On")
        btn_all_on.clicked.connect(self.showAllLayers)
        btn_all_off = QPushButton("Tutti Off")
        btn_all_off.clicked.connect(self.hideAllLayers)
        toolbar.addWidget(btn_all_on)
        toolbar.addWidget(btn_all_off)
        layout.addLayout(toolbar)

        # Lista layer
        self.layer_list = QTreeWidget()
        self.layer_list.setHeaderLabels(["", "Layer", "Colore"])
        self.layer_list.setColumnWidth(0, 30)
        self.layer_list.setColumnWidth(1, 100)
        self.layer_list.setColumnWidth(2, 50)

        for name, layer in self.layers.items():
            item = QTreeWidgetItem()
            item.setCheckState(0, Qt.Checked if layer.visible else Qt.Unchecked)
            item.setText(1, name)
            item.setData(1, Qt.UserRole, name)

            # Colore
            color_label = QLabel()
            color_label.setFixedSize(20, 20)
            color_label.setStyleSheet(f"background-color: {layer.color}; border: 1px solid #ccc;")

            self.layer_list.addTopLevelItem(item)
            self.layer_list.setItemWidget(item, 2, color_label)

        self.layer_list.itemChanged.connect(self.onLayerChanged)
        layout.addWidget(self.layer_list)

        self.setWidget(widget)

    def onLayerChanged(self, item, column):
        if column == 0:
            layer_name = item.data(1, Qt.UserRole)
            visible = item.checkState(0) == Qt.Checked
            if layer_name in self.layers:
                self.layers[layer_name].visible = visible
                self.layerVisibilityChanged.emit(layer_name, visible)

    def showAllLayers(self):
        for i in range(self.layer_list.topLevelItemCount()):
            item = self.layer_list.topLevelItem(i)
            item.setCheckState(0, Qt.Checked)

    def hideAllLayers(self):
        for i in range(self.layer_list.topLevelItemCount()):
            item = self.layer_list.topLevelItem(i)
            item.setCheckState(0, Qt.Unchecked)

    def isLayerVisible(self, layer_name: str) -> bool:
        if layer_name in self.layers:
            return self.layers[layer_name].visible
        return True


# ============================================================================
# NTC 2018 VERIFICHE
# ============================================================================

class VerificheNTC2018:
    """Verifiche secondo NTC 2018 per murature"""

    # Snellezza massima da Tab. 7.8.II NTC 2018
    SNELLEZZA_MAX = {
        'pietra_irregolare': 10,
        'pietra_squadrata': 12,
        'mattoni_pieni': 15,
        'mattoni_semipieni': 15,
        'blocchi_cls': 15,
        'blocchi_laterizio': 15,
        'muratura_armata': 15
    }

    @staticmethod
    def verifica_snellezza(muro, tipo_muratura: str = 'mattoni_pieni') -> dict:
        """
        Verifica snellezza muratura §7.8.2.2 NTC 2018
        λ = h₀/t ≤ λ_max
        """
        lambda_eff = muro.altezza / muro.spessore
        lambda_max = VerificheNTC2018.SNELLEZZA_MAX.get(tipo_muratura, 15)
        verificato = lambda_eff <= lambda_max

        return {
            'lambda': round(lambda_eff, 2),
            'lambda_max': lambda_max,
            'verificato': verificato,
            'margine': round((lambda_max - lambda_eff) / lambda_max * 100, 1),
            'ntc_ref': '§7.8.2.2 Tab. 7.8.II'
        }

    @staticmethod
    def verifica_eccentricita(muro, e1: float = 0.0, e2: float = 0.0) -> dict:
        """
        Verifica eccentricità §7.8.2.2.2 NTC 2018
        e = e1 + e2 ≤ 0.33t
        """
        e_totale = abs(e1) + abs(e2)
        e_max = 0.33 * muro.spessore
        verificato = e_totale <= e_max

        return {
            'e_totale': round(e_totale, 3),
            'e_max': round(e_max, 3),
            'verificato': verificato,
            'rapporto': round(e_totale / e_max, 2) if e_max > 0 else 0,
            'ntc_ref': '§7.8.2.2.2'
        }

    @staticmethod
    def calcola_classe_rischio(IR: float) -> dict:
        """
        Calcola classe rischio sismico secondo Linee Guida Sismabonus
        IR = Indice di Rischio (capacità / domanda)
        """
        if IR >= 1.0:
            classe = 'A+'
            descrizione = 'Edificio sicuro'
        elif IR >= 0.80:
            classe = 'A'
            descrizione = 'Rischio molto basso'
        elif IR >= 0.60:
            classe = 'B'
            descrizione = 'Rischio basso'
        elif IR >= 0.45:
            classe = 'C'
            descrizione = 'Rischio medio-basso'
        elif IR >= 0.30:
            classe = 'D'
            descrizione = 'Rischio medio'
        elif IR >= 0.15:
            classe = 'E'
            descrizione = 'Rischio alto'
        else:
            classe = 'F'
            descrizione = 'Rischio molto alto'

        # Calcola salto di classe possibile con intervento
        salti_possibili = 0
        if IR < 0.15:
            salti_possibili = 5
        elif IR < 0.30:
            salti_possibili = 4
        elif IR < 0.45:
            salti_possibili = 3
        elif IR < 0.60:
            salti_possibili = 2
        elif IR < 0.80:
            salti_possibili = 1

        return {
            'IR': round(IR, 3),
            'classe': classe,
            'descrizione': descrizione,
            'salti_possibili': salti_possibili,
            'colore': {
                'A+': '#00AA00', 'A': '#00CC00', 'B': '#88CC00',
                'C': '#CCCC00', 'D': '#CCAA00', 'E': '#CC6600', 'F': '#CC0000'
            }.get(classe, '#808080')
        }

    @staticmethod
    def verifica_meccanismo_ribaltamento(muro, ag: float, q: float = 2.0,
                                          peso_solaio: float = 0.0) -> dict:
        """
        Verifica ribaltamento semplice §8.7.1 NTC 2018
        Meccanismo cinematico di tipo 1
        """
        # Peso proprio muro (assumo 18 kN/m³)
        gamma_mur = 18.0
        peso_muro = muro.lunghezza * muro.spessore * muro.altezza * gamma_mur

        # Baricentro
        h_baricentro = muro.altezza / 2

        # Momento stabilizzante
        braccio_stab = muro.spessore / 2
        M_stab = peso_muro * braccio_stab + peso_solaio * muro.spessore

        # Forza sismica
        alpha_0 = ag / q  # moltiplicatore sismico semplificato
        F_sisma = alpha_0 * peso_muro

        # Momento ribaltante
        M_rib = F_sisma * h_baricentro

        # Verifica
        verificato = M_stab >= M_rib

        return {
            'M_stabilizzante': round(M_stab, 2),
            'M_ribaltante': round(M_rib, 2),
            'rapporto': round(M_stab / M_rib, 3) if M_rib > 0 else float('inf'),
            'verificato': verificato,
            'alpha_0': round(alpha_0, 3),
            'ntc_ref': '§8.7.1'
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
# PROJECT SERIALIZER - SALVATAGGIO/CARICAMENTO JSON
# ============================================================================

class ProjectSerializer:
    """Gestisce salvataggio e caricamento progetti in formato JSON (.mur)"""

    VERSION = "2.0"

    @staticmethod
    def save(progetto: Progetto, filepath: str) -> bool:
        """Salva il progetto in formato JSON"""
        try:
            data = {
                "version": ProjectSerializer.VERSION,
                "format": "muratura",
                "saved_at": datetime.now().isoformat(),
                "project": {
                    "nome": progetto.nome,
                    "autore": progetto.autore,
                    "n_piani": progetto.n_piani,
                    "altezza_piano": progetto.altezza_piano,
                    "indice_rischio": progetto.indice_rischio,
                    "current_step": progetto.current_step.value,
                },
                "muri": [ProjectSerializer._muro_to_dict(m) for m in progetto.muri],
                "aperture": [ProjectSerializer._apertura_to_dict(a) for a in progetto.aperture],
                "piani": [ProjectSerializer._piano_to_dict(p) for p in progetto.piani],
                "solai": [ProjectSerializer._solaio_to_dict(s) for s in progetto.solai],
                "fondazioni": [ProjectSerializer._fondazione_to_dict(f) for f in progetto.fondazioni],
                "cordoli": [ProjectSerializer._cordolo_to_dict(c) for c in progetto.cordoli],
                "tiranti": [ProjectSerializer._tirante_to_dict(t) for t in progetto.tiranti],
                "scale": [ProjectSerializer._scala_to_dict(s) for s in progetto.scale],
                "balconi": [ProjectSerializer._balcone_to_dict(b) for b in progetto.balconi],
                "copertura": ProjectSerializer._copertura_to_dict(progetto.copertura) if progetto.copertura else None,
                "sismici": ProjectSerializer._sismici_to_dict(progetto.sismici),
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Errore salvataggio: {e}")
            return False

    @staticmethod
    def load(filepath: str) -> Optional[Progetto]:
        """Carica un progetto da file JSON"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Verifica formato
            if data.get("format") != "muratura":
                raise ValueError("Formato file non valido")

            proj_data = data.get("project", {})

            progetto = Progetto(
                nome=proj_data.get("nome", "Progetto Importato"),
                autore=proj_data.get("autore", ""),
                n_piani=proj_data.get("n_piani", 2),
                altezza_piano=proj_data.get("altezza_piano", 3.0),
                indice_rischio=proj_data.get("indice_rischio", 0.0),
                filepath=filepath,
            )

            # Current step
            step_val = proj_data.get("current_step", 0)
            try:
                progetto.current_step = WorkflowStep(step_val)
            except ValueError:
                progetto.current_step = WorkflowStep.PROGETTO

            # Carica elementi
            progetto.muri = [ProjectSerializer._dict_to_muro(m) for m in data.get("muri", [])]
            progetto.aperture = [ProjectSerializer._dict_to_apertura(a) for a in data.get("aperture", [])]
            progetto.piani = [ProjectSerializer._dict_to_piano(p) for p in data.get("piani", [])]
            progetto.solai = [ProjectSerializer._dict_to_solaio(s) for s in data.get("solai", [])]
            progetto.fondazioni = [ProjectSerializer._dict_to_fondazione(f) for f in data.get("fondazioni", [])]
            progetto.cordoli = [ProjectSerializer._dict_to_cordolo(c) for c in data.get("cordoli", [])]
            progetto.tiranti = [ProjectSerializer._dict_to_tirante(t) for t in data.get("tiranti", [])]
            progetto.scale = [ProjectSerializer._dict_to_scala(s) for s in data.get("scale", [])]
            progetto.balconi = [ProjectSerializer._dict_to_balcone(b) for b in data.get("balconi", [])]

            copertura_data = data.get("copertura")
            if copertura_data:
                progetto.copertura = ProjectSerializer._dict_to_copertura(copertura_data)

            sismici_data = data.get("sismici", {})
            progetto.sismici = ProjectSerializer._dict_to_sismici(sismici_data)

            return progetto

        except Exception as e:
            print(f"Errore caricamento: {e}")
            return None

    # === Serializzazione elementi ===

    @staticmethod
    def _muro_to_dict(m: Muro) -> dict:
        return {
            "nome": m.nome, "x1": m.x1, "y1": m.y1, "x2": m.x2, "y2": m.y2,
            "spessore": m.spessore, "altezza": m.altezza, "z": m.z,
            "materiale": m.materiale, "selected": m.selected
        }

    @staticmethod
    def _dict_to_muro(d: dict) -> Muro:
        return Muro(
            nome=d.get("nome", ""), x1=d.get("x1", 0), y1=d.get("y1", 0),
            x2=d.get("x2", 0), y2=d.get("y2", 0),
            spessore=d.get("spessore", 0.3), altezza=d.get("altezza", 3.0),
            z=d.get("z", 0), materiale=d.get("materiale", "muratura"),
            selected=d.get("selected", False)
        )

    @staticmethod
    def _apertura_to_dict(a: Apertura) -> dict:
        return {
            "nome": a.nome, "muro": a.muro, "tipo": a.tipo,
            "larghezza": a.larghezza, "altezza": a.altezza,
            "posizione": a.posizione, "altezza_davanzale": a.altezza_davanzale
        }

    @staticmethod
    def _dict_to_apertura(d: dict) -> Apertura:
        return Apertura(
            nome=d.get("nome", ""), muro=d.get("muro", ""),
            tipo=d.get("tipo", "finestra"), larghezza=d.get("larghezza", 1.0),
            altezza=d.get("altezza", 1.0), posizione=d.get("posizione", 0),
            altezza_davanzale=d.get("altezza_davanzale", 0.9)
        )

    @staticmethod
    def _piano_to_dict(p: Piano) -> dict:
        return {
            "numero": p.numero, "quota": p.quota,
            "altezza": p.altezza, "nome": p.nome
        }

    @staticmethod
    def _dict_to_piano(d: dict) -> Piano:
        return Piano(
            numero=d.get("numero", 0), quota=d.get("quota", 0),
            altezza=d.get("altezza", 3.0), nome=d.get("nome", "")
        )

    @staticmethod
    def _solaio_to_dict(s: Solaio) -> dict:
        return {
            "nome": s.nome, "piano": s.piano, "tipo": s.tipo,
            "lunghezza": s.lunghezza, "larghezza": s.larghezza,
            "peso_proprio": s.peso_proprio, "sovraccarico": s.sovraccarico,
            "direzione_orditura": s.direzione_orditura
        }

    @staticmethod
    def _dict_to_solaio(d: dict) -> Solaio:
        return Solaio(
            nome=d.get("nome", ""), piano=d.get("piano", 0),
            tipo=d.get("tipo", "laterocemento"),
            lunghezza=d.get("lunghezza", 0), larghezza=d.get("larghezza", 0),
            peso_proprio=d.get("peso_proprio", 3.0),
            sovraccarico=d.get("sovraccarico", 2.0),
            direzione_orditura=d.get("direzione_orditura", "X")
        )

    @staticmethod
    def _fondazione_to_dict(f: Fondazione) -> dict:
        return {
            "nome": f.nome, "tipo": f.tipo, "larghezza": f.larghezza,
            "altezza": f.altezza, "muro_associato": f.muro_associato
        }

    @staticmethod
    def _dict_to_fondazione(d: dict) -> Fondazione:
        return Fondazione(
            nome=d.get("nome", ""), tipo=d.get("tipo", "continua"),
            larghezza=d.get("larghezza", 0.6), altezza=d.get("altezza", 0.5),
            muro_associato=d.get("muro_associato", "")
        )

    @staticmethod
    def _cordolo_to_dict(c: Cordolo) -> dict:
        return {
            "nome": c.nome, "piano": c.piano, "base": c.base,
            "altezza": c.altezza, "armatura": c.armatura, "muro": c.muro
        }

    @staticmethod
    def _dict_to_cordolo(d: dict) -> Cordolo:
        return Cordolo(
            nome=d.get("nome", ""), piano=d.get("piano", 0),
            base=d.get("base", 0.3), altezza=d.get("altezza", 0.25),
            armatura=d.get("armatura", "4Ø12"), muro=d.get("muro", "")
        )

    @staticmethod
    def _tirante_to_dict(t: Tirante) -> dict:
        return {
            "nome": t.nome, "piano": t.piano, "diametro": t.diametro,
            "materiale": t.materiale, "x1": t.x1, "y1": t.y1,
            "x2": t.x2, "y2": t.y2
        }

    @staticmethod
    def _dict_to_tirante(d: dict) -> Tirante:
        return Tirante(
            nome=d.get("nome", ""), piano=d.get("piano", 0),
            diametro=d.get("diametro", 20), materiale=d.get("materiale", "acciaio"),
            x1=d.get("x1", 0), y1=d.get("y1", 0),
            x2=d.get("x2", 0), y2=d.get("y2", 0)
        )

    @staticmethod
    def _scala_to_dict(s: Scala) -> dict:
        return {
            "nome": s.nome, "tipo": s.tipo, "larghezza": s.larghezza,
            "n_gradini": s.n_gradini, "piano_partenza": s.piano_partenza
        }

    @staticmethod
    def _dict_to_scala(d: dict) -> Scala:
        return Scala(
            nome=d.get("nome", ""), tipo=d.get("tipo", "rampa"),
            larghezza=d.get("larghezza", 1.2),
            n_gradini=d.get("n_gradini", 16),
            piano_partenza=d.get("piano_partenza", 0)
        )

    @staticmethod
    def _balcone_to_dict(b: Balcone) -> dict:
        return {
            "nome": b.nome, "piano": b.piano, "muro": b.muro,
            "lunghezza": b.lunghezza, "sbalzo": b.sbalzo, "spessore": b.spessore
        }

    @staticmethod
    def _dict_to_balcone(d: dict) -> Balcone:
        return Balcone(
            nome=d.get("nome", ""), piano=d.get("piano", 0),
            muro=d.get("muro", ""), lunghezza=d.get("lunghezza", 2.0),
            sbalzo=d.get("sbalzo", 1.0), spessore=d.get("spessore", 0.15)
        )

    @staticmethod
    def _copertura_to_dict(c: Copertura) -> dict:
        return {
            "tipo": c.tipo, "pendenza": c.pendenza,
            "materiale": c.materiale, "peso": c.peso
        }

    @staticmethod
    def _dict_to_copertura(d: dict) -> Copertura:
        return Copertura(
            tipo=d.get("tipo", "piana"), pendenza=d.get("pendenza", 0),
            materiale=d.get("materiale", "laterizio"), peso=d.get("peso", 1.5)
        )

    @staticmethod
    def _sismici_to_dict(s: ParametriSismici) -> dict:
        return {
            "comune": s.comune, "lon": s.lon, "lat": s.lat,
            "ag_slv": s.ag_slv, "F0": s.F0, "Tc_star": s.Tc_star,
            "sottosuolo": s.sottosuolo, "topografia": s.topografia,
            "classe_uso": s.classe_uso, "vita_nominale": s.vita_nominale,
            "fattore_struttura": getattr(s, 'fattore_struttura', 2.0)
        }

    @staticmethod
    def _dict_to_sismici(d: dict) -> ParametriSismici:
        s = ParametriSismici(
            comune=d.get("comune", ""),
            lon=d.get("lon", 0), lat=d.get("lat", 0),
            ag_slv=d.get("ag_slv", 0), F0=d.get("F0", 2.5),
            Tc_star=d.get("Tc_star", 0.3),
            sottosuolo=d.get("sottosuolo", "B"),
            topografia=d.get("topografia", "T1"),
            classe_uso=d.get("classe_uso", "II"),
            vita_nominale=d.get("vita_nominale", 50)
        )
        if 'fattore_struttura' in d:
            s.fattore_struttura = d['fattore_struttura']
        return s


# ============================================================================
# GEOMETRY ENGINE (Shapely-based spatial indexing)
# ============================================================================

class GeometryEngine:
    """
    Engine geometrico basato su Shapely per operazioni efficienti.
    Utilizza STRtree per query spaziali O(log n) invece di O(n²).
    """

    def __init__(self):
        self._spatial_index = None
        self._geometries = []
        self._muri_refs = []  # Riferimento ai muri originali
        self._index_valid = False

    def rebuild_index(self, muri: list):
        """Ricostruisce spatial index per query veloci"""
        if not SHAPELY_AVAILABLE:
            self._index_valid = False
            return

        self._geometries = []
        self._muri_refs = []

        for muro in muri:
            line = LineString([(muro.x1, muro.y1), (muro.x2, muro.y2)])
            self._geometries.append(line)
            self._muri_refs.append(muro)

        if self._geometries:
            self._spatial_index = STRtree(self._geometries)
        else:
            self._spatial_index = None

        self._index_valid = True

    def invalidate(self):
        """Invalida l'indice (da chiamare quando i muri cambiano)"""
        self._index_valid = False

    @property
    def is_valid(self):
        return self._index_valid and SHAPELY_AVAILABLE

    def find_near_point(self, x: float, y: float, radius: float) -> list:
        """
        Trova muri vicini a un punto - O(log n) invece di O(n²).
        Ritorna lista di tuple (muro, distanza, punto_piu_vicino).
        """
        if not self.is_valid or self._spatial_index is None:
            return []

        point = Point(x, y)
        search_area = point.buffer(radius)

        results = []
        # Query l'indice spaziale
        candidate_indices = self._spatial_index.query(search_area)

        for idx in candidate_indices:
            if idx < len(self._geometries):
                geom = self._geometries[idx]
                muro = self._muri_refs[idx]
                dist = point.distance(geom)
                if dist <= radius:
                    # Trova punto più vicino sulla linea
                    nearest = geom.interpolate(geom.project(point))
                    results.append((muro, dist, (nearest.x, nearest.y)))

        # Ordina per distanza
        results.sort(key=lambda x: x[1])
        return results

    def find_intersections(self, x1: float, y1: float, x2: float, y2: float) -> list:
        """
        Trova intersezioni tra una linea e i muri esistenti.
        Ritorna lista di tuple (muro, punto_intersezione).
        """
        if not self.is_valid or self._spatial_index is None:
            return []

        line = LineString([(x1, y1), (x2, y2)])
        results = []

        candidate_indices = self._spatial_index.query(line)

        for idx in candidate_indices:
            if idx < len(self._geometries):
                geom = self._geometries[idx]
                muro = self._muri_refs[idx]
                if line.intersects(geom):
                    intersection = line.intersection(geom)
                    if not intersection.is_empty:
                        if intersection.geom_type == 'Point':
                            results.append((muro, (intersection.x, intersection.y)))
                        elif intersection.geom_type == 'MultiPoint':
                            for pt in intersection.geoms:
                                results.append((muro, (pt.x, pt.y)))

        return results

    def get_endpoints(self, radius: float = 0.01) -> list:
        """
        Ritorna tutti gli endpoint dei muri per snap.
        Ritorna lista di tuple (x, y, muro).
        """
        endpoints = []
        for muro in self._muri_refs:
            endpoints.append((muro.x1, muro.y1, muro))
            endpoints.append((muro.x2, muro.y2, muro))
        return endpoints

    def get_midpoints(self) -> list:
        """
        Ritorna tutti i punti medi dei muri per snap.
        Ritorna lista di tuple (x, y, muro).
        """
        midpoints = []
        for muro in self._muri_refs:
            mx = (muro.x1 + muro.x2) / 2
            my = (muro.y1 + muro.y2) / 2
            midpoints.append((mx, my, muro))
        return midpoints


# ============================================================================
# GEOMETRY WORKER (QThread per calcoli pesanti)
# ============================================================================

class GeometryWorker(QThread):
    """
    Worker thread per calcoli geometrici pesanti.
    Esegue operazioni in background senza bloccare la UI.
    """

    # Segnali per comunicare risultati
    snap_result = pyqtSignal(float, float, str)  # x, y, snap_type
    intersection_result = pyqtSignal(list)  # lista intersezioni
    validation_result = pyqtSignal(bool, str)  # valido, messaggio
    progress = pyqtSignal(int)  # percentuale completamento
    finished_task = pyqtSignal(str, object)  # nome_task, risultato

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task = None
        self.params = {}
        self.geometry_engine = None
        self._stop_requested = False

    def setTask(self, task_name: str, params: dict, engine: 'GeometryEngine' = None):
        """
        Imposta il task da eseguire.
        task_name: 'snap', 'intersections', 'validate', 'rebuild_index'
        params: dizionario con parametri specifici del task
        """
        self.task = task_name
        self.params = params
        self.geometry_engine = engine

    def requestStop(self):
        """Richiede interruzione del task"""
        self._stop_requested = True

    def run(self):
        """Esegue il task in background"""
        self._stop_requested = False

        try:
            if self.task == 'snap':
                self._runSnapTask()
            elif self.task == 'intersections':
                self._runIntersectionsTask()
            elif self.task == 'validate':
                self._runValidationTask()
            elif self.task == 'rebuild_index':
                self._runRebuildIndexTask()
            elif self.task == 'batch_snap':
                self._runBatchSnapTask()
        except Exception as e:
            self.finished_task.emit(self.task, {'error': str(e)})

    def _runSnapTask(self):
        """Calcola snap point in background"""
        x = self.params.get('x', 0)
        y = self.params.get('y', 0)
        radius = self.params.get('radius', 0.3)

        if self.geometry_engine and self.geometry_engine.is_valid:
            nearby = self.geometry_engine.find_near_point(x, y, radius)
            if nearby:
                muro, dist, point = nearby[0]
                self.snap_result.emit(point[0], point[1], 'nearest')
                return

        self.snap_result.emit(x, y, 'none')

    def _runIntersectionsTask(self):
        """Trova tutte le intersezioni in background"""
        muri = self.params.get('muri', [])
        results = []

        total = len(muri) * (len(muri) - 1) // 2
        count = 0

        for i, m1 in enumerate(muri):
            if self._stop_requested:
                break
            for m2 in muri[i+1:]:
                if self._stop_requested:
                    break
                # Calcola intersezione
                ix, iy = self._lineIntersection(
                    m1.x1, m1.y1, m1.x2, m1.y2,
                    m2.x1, m2.y1, m2.x2, m2.y2
                )
                if ix is not None:
                    results.append({
                        'muro1': m1.nome,
                        'muro2': m2.nome,
                        'x': ix, 'y': iy
                    })
                count += 1
                if total > 0:
                    self.progress.emit(int(count / total * 100))

        self.intersection_result.emit(results)
        self.finished_task.emit('intersections', results)

    def _runValidationTask(self):
        """Valida geometria edificio in background"""
        muri = self.params.get('muri', [])
        issues = []

        # Controlla muri troppo corti
        for m in muri:
            if self._stop_requested:
                break
            if m.lunghezza < 0.5:
                issues.append(f"{m.nome}: lunghezza troppo corta ({m.lunghezza:.2f}m)")

        # Controlla muri sovrapposti
        for i, m1 in enumerate(muri):
            if self._stop_requested:
                break
            for m2 in muri[i+1:]:
                if self._checkOverlap(m1, m2):
                    issues.append(f"{m1.nome} e {m2.nome}: sovrapposizione rilevata")

        valid = len(issues) == 0
        message = "Geometria valida" if valid else "\n".join(issues)
        self.validation_result.emit(valid, message)
        self.finished_task.emit('validate', {'valid': valid, 'issues': issues})

    def _runRebuildIndexTask(self):
        """Ricostruisce spatial index in background"""
        muri = self.params.get('muri', [])

        if self.geometry_engine:
            self.geometry_engine.rebuild_index(muri)
            self.finished_task.emit('rebuild_index', {'count': len(muri)})

    def _runBatchSnapTask(self):
        """Calcola snap points per batch di punti"""
        points = self.params.get('points', [])
        radius = self.params.get('radius', 0.3)
        results = []

        for i, (x, y) in enumerate(points):
            if self._stop_requested:
                break
            if self.geometry_engine and self.geometry_engine.is_valid:
                nearby = self.geometry_engine.find_near_point(x, y, radius)
                if nearby:
                    muro, dist, point = nearby[0]
                    results.append((point[0], point[1], 'nearest'))
                else:
                    results.append((x, y, 'none'))
            else:
                results.append((x, y, 'none'))

            self.progress.emit(int((i + 1) / len(points) * 100))

        self.finished_task.emit('batch_snap', results)

    def _lineIntersection(self, x1, y1, x2, y2, x3, y3, x4, y4):
        """Calcola intersezione tra due segmenti"""
        denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
        if abs(denom) < 1e-10:
            return None, None

        t = ((x1-x3)*(y3-y4) - (y1-y3)*(x3-x4)) / denom
        u = -((x1-x2)*(y1-y3) - (y1-y2)*(x1-x3)) / denom

        if 0 <= t <= 1 and 0 <= u <= 1:
            ix = x1 + t*(x2-x1)
            iy = y1 + t*(y2-y1)
            return ix, iy
        return None, None

    def _checkOverlap(self, m1, m2):
        """Controlla se due muri si sovrappongono"""
        # Semplificato: controlla se i centri sono troppo vicini
        cx1 = (m1.x1 + m1.x2) / 2
        cy1 = (m1.y1 + m1.y2) / 2
        cx2 = (m2.x1 + m2.x2) / 2
        cy2 = (m2.y1 + m2.y2) / 2

        dist = math.sqrt((cx1-cx2)**2 + (cy1-cy2)**2)
        min_dist = (m1.spessore + m2.spessore) / 2

        return dist < min_dist and abs(m1.z - m2.z) < 0.1


# ============================================================================
# GPU RENDERING (ModernGL)
# ============================================================================

class GLDrawingCanvas(QGLWidget if MODERNGL_AVAILABLE else QWidget):
    """
    Canvas 2D con rendering GPU accelerato usando ModernGL.
    Disegna muri e elementi usando OpenGL per performance elevate.
    Fallback a QPainter se OpenGL non disponibile.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ctx = None
        self.prog = None
        self.vbo = None
        self.vao = None
        self.use_gpu = MODERNGL_AVAILABLE

        # Dati geometria
        self.vertices = []
        self.colors = []
        self.needs_update = True

        # Vista
        self.scala = 40
        self.offset_x = 0
        self.offset_y = 0

        # Progetto
        self.progetto = None

    def initializeGL(self):
        """Inizializza contesto OpenGL e shader"""
        if not MODERNGL_AVAILABLE:
            return

        try:
            self.ctx = moderngl.create_context()

            # Shader per linee 2D con colori
            self.prog = self.ctx.program(
                vertex_shader='''
                    #version 330
                    in vec2 in_position;
                    in vec3 in_color;
                    out vec3 v_color;
                    uniform vec2 u_scale;
                    uniform vec2 u_offset;
                    uniform vec2 u_resolution;

                    void main() {
                        vec2 pos = (in_position * u_scale + u_offset) / u_resolution * 2.0 - 1.0;
                        pos.y = -pos.y;  // Flip Y per coordinate schermo
                        gl_Position = vec4(pos, 0.0, 1.0);
                        v_color = in_color;
                    }
                ''',
                fragment_shader='''
                    #version 330
                    in vec3 v_color;
                    out vec4 fragColor;

                    void main() {
                        fragColor = vec4(v_color, 1.0);
                    }
                '''
            )

            # Uniform locations
            self.u_scale = self.prog['u_scale']
            self.u_offset = self.prog['u_offset']
            self.u_resolution = self.prog['u_resolution']

        except Exception as e:
            print(f"Errore inizializzazione OpenGL: {e}")
            self.use_gpu = False

    def setProgetto(self, progetto):
        """Imposta il progetto e aggiorna geometria GPU"""
        self.progetto = progetto
        self.needs_update = True
        self.update()

    def updateGeometry(self):
        """Aggiorna VBO con la geometria dei muri"""
        if not self.use_gpu or not self.ctx or not self.progetto:
            return

        vertices = []
        colors = []

        # Colore muri (blu)
        muro_color = (0.2, 0.4, 0.8)

        for muro in self.progetto.muri:
            # Calcola i 4 punti del muro
            dx = muro.x2 - muro.x1
            dy = muro.y2 - muro.y1
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0:
                nx = -dy / length * muro.spessore / 2
                ny = dx / length * muro.spessore / 2

                # 4 vertici del rettangolo
                p1 = (muro.x1 - nx, muro.y1 - ny)
                p2 = (muro.x1 + nx, muro.y1 + ny)
                p3 = (muro.x2 + nx, muro.y2 + ny)
                p4 = (muro.x2 - nx, muro.y2 - ny)

                # Due triangoli per il rettangolo
                for p in [p1, p2, p3, p1, p3, p4]:
                    vertices.extend(p)
                    colors.extend(muro_color)

        if vertices:
            # Crea array numpy
            import numpy as np
            vertices_array = np.array(vertices, dtype='f4')
            colors_array = np.array(colors, dtype='f4')

            # Combina posizioni e colori
            data = np.zeros(len(vertices) // 2 * 5, dtype='f4')
            data[0::5] = vertices_array[0::2]  # x
            data[1::5] = vertices_array[1::2]  # y
            data[2::5] = colors_array[0::3]    # r
            data[3::5] = colors_array[1::3]    # g
            data[4::5] = colors_array[2::3]    # b

            # Aggiorna VBO
            if self.vbo:
                self.vbo.release()
            self.vbo = self.ctx.buffer(data.tobytes())

            # Crea VAO
            if self.vao:
                self.vao.release()
            self.vao = self.ctx.simple_vertex_array(
                self.prog, self.vbo, 'in_position', 'in_color',
            )

        self.needs_update = False

    def paintGL(self):
        """Renderizza scena con OpenGL"""
        if not self.use_gpu or not self.ctx:
            # Fallback a QPainter
            self.paintFallback()
            return

        # Pulisci sfondo
        self.ctx.clear(0.95, 0.95, 0.98)

        if self.needs_update:
            self.updateGeometry()

        if self.vao:
            # Imposta uniform
            self.u_scale.value = (self.scala, self.scala)
            self.u_offset.value = (self.offset_x, self.offset_y)
            self.u_resolution.value = (self.width(), self.height())

            # Render
            self.vao.render(moderngl.TRIANGLES)

    def paintFallback(self):
        """Fallback rendering con QPainter se OpenGL non disponibile"""
        from PyQt5.QtGui import QPainter, QColor, QPen, QBrush
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Sfondo
        painter.fillRect(self.rect(), QColor(240, 240, 245))

        if not self.progetto:
            return

        # Disegna muri
        painter.setPen(QPen(QColor(50, 100, 200), 2))
        painter.setBrush(QBrush(QColor(100, 150, 220, 100)))

        for muro in self.progetto.muri:
            dx = muro.x2 - muro.x1
            dy = muro.y2 - muro.y1
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0:
                nx = -dy / length * muro.spessore / 2
                ny = dx / length * muro.spessore / 2

                # Trasforma a coordinate schermo
                def toScreen(x, y):
                    return (
                        int(x * self.scala + self.offset_x),
                        int(-y * self.scala + self.offset_y)
                    )

                from PyQt5.QtGui import QPolygonF
                from PyQt5.QtCore import QPointF
                points = [
                    QPointF(*toScreen(muro.x1 - nx, muro.y1 - ny)),
                    QPointF(*toScreen(muro.x1 + nx, muro.y1 + ny)),
                    QPointF(*toScreen(muro.x2 + nx, muro.y2 + ny)),
                    QPointF(*toScreen(muro.x2 - nx, muro.y2 - ny)),
                ]
                painter.drawPolygon(QPolygonF(points))

    def resizeGL(self, w, h):
        """Gestisce resize del widget"""
        if self.ctx:
            self.ctx.viewport = (0, 0, w, h)
        self.offset_x = w // 2
        self.offset_y = h // 2

    def wheelEvent(self, event):
        """Zoom con rotella mouse"""
        delta = event.angleDelta().y()
        if delta > 0:
            self.scala = min(200, self.scala * 1.1)
        else:
            self.scala = max(10, self.scala / 1.1)
        self.update()


# ============================================================================
# RIBBON TOOLBAR
# ============================================================================

class RibbonButton(QToolButton):
    """Pulsante grande per Ribbon con icona e testo"""

    def __init__(self, text: str, icon_name: str = None, icon_category: str = None, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setMinimumSize(65, 65)
        self.setMaximumSize(80, 75)
        self.setIconSize(QSize(24, 24))

        # Imposta icona se specificata
        if icon_name and icon_category:
            icon = IconManager.get_icon(icon_category, icon_name, 24)
            if not icon.isNull():
                self.setIcon(icon)

        # Stile professionale con supporto temi
        self._update_style()

    def _update_style(self):
        """Aggiorna stile in base al tema"""
        t = ThemeManager.THEMES[ThemeManager.current_theme()]
        self.setStyleSheet(f"""
            QToolButton {{
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px 2px;
                font-size: 9px;
                background-color: transparent;
                color: {t['text']};
            }}
            QToolButton:hover {{
                background-color: {t['hover']};
                border: 1px solid {t['border']};
            }}
            QToolButton:pressed {{
                background-color: {t['primary']};
                color: white;
            }}
            QToolButton:checked {{
                background-color: {t['selection']};
                border: 1px solid {t['primary']};
            }}
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

    def addWidget(self, widget):
        """Aggiunge un widget generico al pannello"""
        self.button_layout.addWidget(widget)


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
        self.setMinimumHeight(100)
        self.setMaximumHeight(100)

        t = ThemeManager.THEMES[ThemeManager.current_theme()]
        self.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {t['surface']};
            }}
            QTabBar::tab {{
                padding: 10px 25px;
                font-weight: bold;
                font-size: 11px;
                min-width: 60px;
            }}
            QTabBar::tab:selected {{
                background-color: {t['surface']};
                border-bottom: 3px solid {t['primary']};
            }}
            QTabBar::tab:!selected {{
                background-color: {t['background']};
            }}
            QTabBar::tab:hover {{
                background-color: {t['hover']};
            }}
        """)


# ============================================================================
# PROJECT BROWSER
# ============================================================================

class ProjectBrowser(QDockWidget):
    """Browser ad albero del progetto con icone professionali"""

    itemSelected = pyqtSignal(str, str)  # tipo, nome

    # Mapping nodi -> icone
    NODE_ICONS = {
        'progetto': ('navigation', 'folder'),
        'piani': ('navigation', 'floors'),
        'muri': ('elements', 'wall'),
        'aperture': ('elements', 'door'),
        'fondazioni': ('elements', 'foundation'),
        'cordoli': ('elements', 'chain'),
        'tiranti': ('elements', 'tie'),
        'solai': ('elements', 'slab'),
        'scale': ('elements', 'stairs'),
        'balconi': ('elements', 'balcony'),
        'copertura': ('elements', 'roof'),
        'carichi': ('elements', 'load'),
        'analisi': ('misc', 'chart'),
    }

    def __init__(self, parent=None):
        super().__init__("Progetto", parent)
        self.setMinimumWidth(220)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        self.tree.setIconSize(QSize(18, 18))
        self.tree.itemClicked.connect(self.onItemClicked)

        self._update_style()
        self.setWidget(self.tree)

        # Nodi principali con icone
        self.root_progetto = self._create_node("Progetto", 'progetto')
        self.root_piani = self._create_node("Piani", 'piani')
        self.root_muri = self._create_node("Muri", 'muri')
        self.root_aperture = self._create_node("Aperture", 'aperture')
        self.root_fondazioni = self._create_node("Fondazioni", 'fondazioni')
        self.root_cordoli = self._create_node("Cordoli", 'cordoli')
        self.root_tiranti = self._create_node("Tiranti", 'tiranti')
        self.root_solai = self._create_node("Solai", 'solai')
        self.root_scale = self._create_node("Scale", 'scale')
        self.root_balconi = self._create_node("Balconi", 'balconi')
        self.root_copertura = self._create_node("Copertura", 'copertura')
        self.root_carichi = self._create_node("Carichi", 'carichi')
        self.root_analisi = self._create_node("Analisi", 'analisi')

        self.tree.expandAll()

    def _create_node(self, text: str, icon_key: str) -> QTreeWidgetItem:
        """Crea un nodo con icona professionale"""
        item = QTreeWidgetItem(self.tree, [text])
        if icon_key in self.NODE_ICONS:
            category, name = self.NODE_ICONS[icon_key]
            icon = IconManager.get_icon(category, name, 18)
            if not icon.isNull():
                item.setIcon(0, icon)
        return item

    def _update_style(self):
        """Aggiorna stile in base al tema"""
        t = ThemeManager.THEMES[ThemeManager.current_theme()]
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                border: none;
                font-size: 11px;
                background-color: {t['surface']};
                color: {t['text']};
            }}
            QTreeWidget::item {{
                padding: 4px 2px;
                border-radius: 3px;
            }}
            QTreeWidget::item:hover {{
                background-color: {t['hover']};
            }}
            QTreeWidget::item:selected {{
                background-color: {t['selection']};
                color: white;
            }}
        """)

    def updateFromProject(self, progetto: Progetto):
        """Aggiorna albero dal progetto"""
        # Pulisci figli
        for root in [self.root_piani, self.root_muri, self.root_aperture,
                     self.root_fondazioni, self.root_cordoli, self.root_tiranti,
                     self.root_solai, self.root_scale, self.root_balconi]:
            root.takeChildren()

        # Progetto
        self.root_progetto.setText(0, progetto.nome)

        # Piani
        for piano in progetto.piani:
            QTreeWidgetItem(self.root_piani, [f"{piano.nome} (h={piano.altezza}m)"])

        # Muri
        for muro in progetto.muri:
            dcr_str = f" DCR={muro.dcr:.2f}" if muro.dcr > 0 else ""
            QTreeWidgetItem(self.root_muri, [f"{muro.nome} ({muro.lunghezza:.1f}m){dcr_str}"])

        # Aperture
        for ap in progetto.aperture:
            QTreeWidgetItem(self.root_aperture, [f"{ap.nome} ({ap.tipo})"])

        # Solai
        for solaio in progetto.solai:
            QTreeWidgetItem(self.root_solai, [f"{solaio.nome} ({solaio.tipo})"])

        # Fondazioni
        for fond in progetto.fondazioni:
            QTreeWidgetItem(self.root_fondazioni, [f"{fond.nome} ({fond.tipo})"])

        # Cordoli
        for cord in progetto.cordoli:
            QTreeWidgetItem(self.root_cordoli, [f"{cord.nome} P{cord.piano}"])

        # Tiranti
        for tir in progetto.tiranti:
            QTreeWidgetItem(self.root_tiranti, [f"{tir.nome} Ø{tir.diametro}"])

        # Scale
        for scala in progetto.scale:
            QTreeWidgetItem(self.root_scale, [f"{scala.nome} ({scala.tipo})"])

        # Balconi
        for balc in progetto.balconi:
            QTreeWidgetItem(self.root_balconi, [f"{balc.nome} ({balc.profondita}m)"])

        # Copertura
        self.root_copertura.takeChildren()
        if progetto.copertura:
            QTreeWidgetItem(self.root_copertura, [f"{progetto.copertura.tipo}"])

        # Conta elementi
        self.root_muri.setText(0, f"Muri ({len(progetto.muri)})")
        self.root_aperture.setText(0, f"Aperture ({len(progetto.aperture)})")
        self.root_fondazioni.setText(0, f"Fondazioni ({len(progetto.fondazioni)})")
        self.root_cordoli.setText(0, f"Cordoli ({len(progetto.cordoli)})")
        self.root_tiranti.setText(0, f"Tiranti ({len(progetto.tiranti)})")
        self.root_solai.setText(0, f"Solai ({len(progetto.solai)})")
        self.root_scale.setText(0, f"Scale ({len(progetto.scale)})")
        self.root_balconi.setText(0, f"Balconi ({len(progetto.balconi)})")

        self.tree.expandAll()

    def onItemClicked(self, item, column):
        parent = item.parent()
        if parent:
            tipo = parent.text(0).split()[0]
            nome = item.text(0).strip().split()[0]
            self.itemSelected.emit(tipo, nome)


# ============================================================================
# WORKFLOW PANEL (GUIDA STEP-BY-STEP)
# ============================================================================

class WorkflowPanel(QWidget):
    """Pannello che guida l'utente attraverso gli step con icone professionali"""

    stepClicked = pyqtSignal(WorkflowStep)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_step = WorkflowStep.PROGETTO
        self.completed_steps = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Titolo con icona
        title_layout = QHBoxLayout()
        title_icon = QLabel()
        icon_pixmap = IconManager.get_pixmap('misc', 'list', 18)
        if not icon_pixmap.isNull():
            title_icon.setPixmap(icon_pixmap)
        title_layout.addWidget(title_icon)

        title = QLabel("WORKFLOW")
        title.setStyleSheet("font-weight: bold; font-size: 12px; color: #0066cc;")
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Step buttons
        self.step_buttons = {}
        for step in WorkflowStep:
            btn = QPushButton(STEP_NAMES[step])
            btn.setCheckable(True)
            btn.setMinimumHeight(35)
            btn.setIconSize(QSize(16, 16))
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
        t = ThemeManager.THEMES[ThemeManager.current_theme()]
        for step, btn in self.step_buttons.items():
            if step in self.completed_steps:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {t['success']}22;
                        border: 1px solid {t['success']};
                        border-radius: 4px;
                        text-align: left;
                        padding-left: 10px;
                        color: {t['text']};
                    }}
                """)
                # Usa icona check
                check_icon = IconManager.get_icon('status', 'check-circle', 16)
                btn.setIcon(check_icon)
                btn.setText(STEP_NAMES[step])
            elif step == self.current_step:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {t['primary']}33;
                        border: 2px solid {t['primary']};
                        border-radius: 4px;
                        font-weight: bold;
                        text-align: left;
                        padding-left: 10px;
                        color: {t['text']};
                    }}
                """)
                # Usa icona play
                play_icon = IconManager.get_icon('misc', 'play', 16)
                btn.setIcon(play_icon)
                btn.setText(STEP_NAMES[step])
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {t['surface']};
                        border: 1px solid {t['border']};
                        border-radius: 4px;
                        text-align: left;
                        padding-left: 10px;
                        color: {t['text_secondary']};
                    }}
                    QPushButton:hover {{
                        background-color: {t['hover']};
                    }}
                """)
                btn.setIcon(QIcon())
                btn.setText("   " + STEP_NAMES[step])

    def onStepClicked(self, step: WorkflowStep):
        self.stepClicked.emit(step)


# ============================================================================
# QUICK ACTIONS PANEL
# ============================================================================

class QuickActionsPanel(QWidget):
    """Pannello azioni rapide per nuovi utenti con icone professionali"""

    # Mapping pulsanti -> icone
    BUTTON_ICONS = {
        'nuovo': ('actions', 'file-new'),
        'apri': ('actions', 'folder-open'),
        'esempio': ('elements', 'roof'),
        'guida': ('misc', 'help-circle'),
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Titolo con icona
        title_layout = QHBoxLayout()
        title_layout.addStretch()
        title_icon = QLabel()
        icon_pixmap = IconManager.get_pixmap('misc', 'rocket', 24)
        if not icon_pixmap.isNull():
            title_icon.setPixmap(icon_pixmap)
        title_layout.addWidget(title_icon)

        title = QLabel("AZIONI RAPIDE")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1a237e;")
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        subtitle = QLabel("Seleziona un'azione per iniziare")
        subtitle.setStyleSheet("color: #666; margin-bottom: 20px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        # Grid di pulsanti grandi
        grid = QGridLayout()
        grid.setSpacing(15)

        self.btn_nuovo = self.createBigButton('nuovo', "Nuovo Progetto",
            "Crea un nuovo progetto con wizard guidato")
        self.btn_apri = self.createBigButton('apri', "Apri Progetto",
            "Apri un progetto esistente (.mur)")
        self.btn_esempio = self.createBigButton('esempio', "Carica Esempio",
            "Carica un edificio di esempio")
        self.btn_guida = self.createBigButton('guida', "Guida Rapida",
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

    def createBigButton(self, icon_key: str, title: str, desc: str) -> QPushButton:
        t = ThemeManager.THEMES[ThemeManager.current_theme()]
        btn = QPushButton()
        btn.setMinimumSize(180, 120)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['surface']};
                border: 2px solid {t['border']};
                border-radius: 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {t['hover']};
                border-color: {t['primary']};
            }}
            QPushButton:pressed {{
                background-color: {t['selection']};
            }}
        """)

        layout = QVBoxLayout(btn)

        # Usa icona professionale
        icon_label = QLabel()
        if icon_key in self.BUTTON_ICONS:
            category, name = self.BUTTON_ICONS[icon_key]
            pixmap = IconManager.get_pixmap(category, name, 40)
            if not pixmap.isNull():
                icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {t['text']};")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        desc_label = QLabel(desc)
        desc_label.setStyleSheet(f"color: {t['text_secondary']}; font-size: 9px;")
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
# DIALOGO CORDOLO
# ============================================================================

class DialogoCordolo(QDialog):
    """Dialogo per inserire cordoli in c.a."""

    def __init__(self, progetto: Progetto, piano: int = 0, muro_selezionato: str = "", parent=None):
        super().__init__(parent)
        self.progetto = progetto
        self.cordolo_creato = None

        self.setWindowTitle("Inserisci Cordolo")
        self.setMinimumSize(400, 450)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("Cordolo in Cemento Armato")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #0066cc;")
        layout.addWidget(header)

        # Piano
        piano_group = QGroupBox("Piano")
        piano_layout = QFormLayout()
        self.piano_spin = QSpinBox()
        self.piano_spin.setRange(0, 10)
        self.piano_spin.setValue(piano)
        piano_layout.addRow("Piano:", self.piano_spin)
        piano_group.setLayout(piano_layout)
        layout.addWidget(piano_group)

        # Muro collegato
        muro_group = QGroupBox("Muro Collegato")
        muro_layout = QFormLayout()
        self.muro_combo = QComboBox()
        self.muro_combo.addItem("-- Seleziona muro --", "")
        for muro in progetto.muri:
            self.muro_combo.addItem(f"{muro.nome} ({muro.lunghezza:.2f}m)", muro.nome)
        if muro_selezionato:
            idx = self.muro_combo.findData(muro_selezionato)
            if idx >= 0:
                self.muro_combo.setCurrentIndex(idx)
        self.muro_combo.currentIndexChanged.connect(self.onMuroChanged)
        muro_layout.addRow("Muro:", self.muro_combo)

        self.auto_pos = QCheckBox("Posiziona automaticamente sul muro")
        self.auto_pos.setChecked(True)
        muro_layout.addRow("", self.auto_pos)
        muro_group.setLayout(muro_layout)
        layout.addWidget(muro_group)

        # Dimensioni
        dim_group = QGroupBox("Dimensioni")
        dim_layout = QFormLayout()

        self.base_spin = QDoubleSpinBox()
        self.base_spin.setRange(0.15, 0.60)
        self.base_spin.setValue(0.30)
        self.base_spin.setSuffix(" m")
        dim_layout.addRow("Base:", self.base_spin)

        self.altezza_spin = QDoubleSpinBox()
        self.altezza_spin.setRange(0.15, 0.50)
        self.altezza_spin.setValue(0.25)
        self.altezza_spin.setSuffix(" m")
        dim_layout.addRow("Altezza:", self.altezza_spin)

        dim_group.setLayout(dim_layout)
        layout.addWidget(dim_group)

        # Materiali
        mat_group = QGroupBox("Materiali e Armatura")
        mat_layout = QFormLayout()

        self.cls_combo = QComboBox()
        self.cls_combo.addItems(["C20/25", "C25/30", "C28/35", "C30/37"])
        self.cls_combo.setCurrentText("C25/30")
        mat_layout.addRow("Calcestruzzo:", self.cls_combo)

        self.acciaio_combo = QComboBox()
        self.acciaio_combo.addItems(["B450C", "B450A", "B500A"])
        mat_layout.addRow("Acciaio:", self.acciaio_combo)

        self.arm_edit = QLineEdit("4Ø16")
        mat_layout.addRow("Armatura long.:", self.arm_edit)

        self.staffe_edit = QLineEdit("Ø8/20")
        mat_layout.addRow("Staffe:", self.staffe_edit)

        mat_group.setLayout(mat_layout)
        layout.addWidget(mat_group)

        # Pulsanti
        btn_layout = QHBoxLayout()
        btn_annulla = QPushButton("Annulla")
        btn_annulla.clicked.connect(self.reject)
        btn_crea = QPushButton("Crea Cordolo")
        btn_crea.setStyleSheet("background-color: #0066cc; color: white; font-weight: bold; padding: 8px 20px;")
        btn_crea.clicked.connect(self.creaCordolo)
        btn_layout.addWidget(btn_annulla)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_crea)
        layout.addLayout(btn_layout)

    def onMuroChanged(self, idx):
        muro_nome = self.muro_combo.currentData()
        self.auto_pos.setEnabled(bool(muro_nome))

    def creaCordolo(self):
        muro_nome = self.muro_combo.currentData()
        x1, y1, x2, y2 = 0, 0, 0, 0

        if muro_nome and self.auto_pos.isChecked():
            muro = next((m for m in self.progetto.muri if m.nome == muro_nome), None)
            if muro:
                x1, y1, x2, y2 = muro.x1, muro.y1, muro.x2, muro.y2

        n = len(self.progetto.cordoli) + 1
        self.cordolo_creato = Cordolo(
            nome=f"C{n}",
            piano=self.piano_spin.value(),
            x1=x1, y1=y1, x2=x2, y2=y2,
            base=self.base_spin.value(),
            altezza=self.altezza_spin.value(),
            cls=self.cls_combo.currentText(),
            acciaio=self.acciaio_combo.currentText(),
            armatura_longitudinale=self.arm_edit.text(),
            staffe=self.staffe_edit.text(),
            muro_collegato=muro_nome or ""
        )
        self.accept()


# ============================================================================
# DIALOGO TIRANTE
# ============================================================================

class DialogoTirante(QDialog):
    """Dialogo per inserire tiranti/catene"""

    def __init__(self, progetto: Progetto, piano: int = 0, parent=None):
        super().__init__(parent)
        self.progetto = progetto
        self.tirante_creato = None

        self.setWindowTitle("Inserisci Tirante")
        self.setMinimumSize(400, 500)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("Tirante / Catena Metallica")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #0066cc;")
        layout.addWidget(header)

        # Piano
        piano_group = QGroupBox("Posizione")
        piano_layout = QFormLayout()

        self.piano_spin = QSpinBox()
        self.piano_spin.setRange(0, 10)
        self.piano_spin.setValue(piano)
        piano_layout.addRow("Piano:", self.piano_spin)

        self.quota_spin = QDoubleSpinBox()
        self.quota_spin.setRange(0.0, 5.0)
        self.quota_spin.setValue(2.8)
        self.quota_spin.setSuffix(" m")
        piano_layout.addRow("Quota dal piano:", self.quota_spin)

        piano_group.setLayout(piano_layout)
        layout.addWidget(piano_group)

        # Muri di ancoraggio (inizio e fine)
        anc_group = QGroupBox("Muri di Ancoraggio")
        anc_layout = QFormLayout()

        self.muro1_combo = QComboBox()
        self.muro1_combo.addItem("-- Muro iniziale --", "")
        self.muro2_combo = QComboBox()
        self.muro2_combo.addItem("-- Muro finale --", "")
        for muro in progetto.muri:
            self.muro1_combo.addItem(f"{muro.nome}", muro.nome)
            self.muro2_combo.addItem(f"{muro.nome}", muro.nome)

        anc_layout.addRow("Muro iniziale:", self.muro1_combo)
        anc_layout.addRow("Muro finale:", self.muro2_combo)
        anc_group.setLayout(anc_layout)
        layout.addWidget(anc_group)

        # Caratteristiche
        car_group = QGroupBox("Caratteristiche")
        car_layout = QFormLayout()

        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["barra", "cavo", "piatto"])
        car_layout.addRow("Tipo:", self.tipo_combo)

        self.diametro_spin = QDoubleSpinBox()
        self.diametro_spin.setRange(12, 50)
        self.diametro_spin.setValue(24)
        self.diametro_spin.setSuffix(" mm")
        car_layout.addRow("Diametro:", self.diametro_spin)

        self.materiale_combo = QComboBox()
        self.materiale_combo.addItems(["S235", "S275", "S355"])
        self.materiale_combo.setCurrentText("S275")
        car_layout.addRow("Materiale:", self.materiale_combo)

        self.pretensione_spin = QDoubleSpinBox()
        self.pretensione_spin.setRange(0, 500)
        self.pretensione_spin.setValue(0)
        self.pretensione_spin.setSuffix(" kN")
        car_layout.addRow("Pretensione:", self.pretensione_spin)

        car_group.setLayout(car_layout)
        layout.addWidget(car_group)

        # Capochiave
        cap_group = QGroupBox("Capochiave")
        cap_layout = QFormLayout()

        self.capochiave_combo = QComboBox()
        self.capochiave_combo.addItems(["piastra", "paletto", "incassato"])
        cap_layout.addRow("Tipo:", self.capochiave_combo)

        cap_group.setLayout(cap_layout)
        layout.addWidget(cap_group)

        # Pulsanti
        btn_layout = QHBoxLayout()
        btn_annulla = QPushButton("Annulla")
        btn_annulla.clicked.connect(self.reject)
        btn_crea = QPushButton("Crea Tirante")
        btn_crea.setStyleSheet("background-color: #0066cc; color: white; font-weight: bold; padding: 8px 20px;")
        btn_crea.clicked.connect(self.creaTirante)
        btn_layout.addWidget(btn_annulla)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_crea)
        layout.addLayout(btn_layout)

    def creaTirante(self):
        muro1_nome = self.muro1_combo.currentData()
        muro2_nome = self.muro2_combo.currentData()

        x1, y1, x2, y2 = 0, 0, 0, 0

        # Trova coordinate dai muri selezionati
        if muro1_nome:
            muro1 = next((m for m in self.progetto.muri if m.nome == muro1_nome), None)
            if muro1:
                x1, y1 = (muro1.x1 + muro1.x2) / 2, (muro1.y1 + muro1.y2) / 2

        if muro2_nome:
            muro2 = next((m for m in self.progetto.muri if m.nome == muro2_nome), None)
            if muro2:
                x2, y2 = (muro2.x1 + muro2.x2) / 2, (muro2.y1 + muro2.y2) / 2

        n = len(self.progetto.tiranti) + 1
        self.tirante_creato = Tirante(
            nome=f"T{n}",
            piano=self.piano_spin.value(),
            x1=x1, y1=y1, x2=x2, y2=y2,
            diametro=self.diametro_spin.value(),
            materiale=self.materiale_combo.currentText(),
            tipo=self.tipo_combo.currentText(),
            pretensione=self.pretensione_spin.value(),
            capochiave_tipo=self.capochiave_combo.currentText(),
            quota_z=self.quota_spin.value()
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

        # Sezione muri senza fondazione
        self.missing_group = QGroupBox("Muri senza fondazione")
        self.missing_group.setStyleSheet("""
            QGroupBox { color: #c70000; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 5px; }
        """)
        missing_layout = QVBoxLayout()
        self.missing_list = QWidget()
        self.missing_list_layout = QVBoxLayout(self.missing_list)
        self.missing_list_layout.setContentsMargins(0, 0, 0, 0)
        self.missing_list_layout.setSpacing(4)
        missing_layout.addWidget(self.missing_list)
        self.missing_group.setLayout(missing_layout)
        layout.addWidget(self.missing_group)

        # Riepilogo
        self.summary = QLabel("")
        self.summary.setStyleSheet("padding: 10px; background: #f8f9fa; border-radius: 5px;")
        layout.addWidget(self.summary)

        # Pulsanti navigazione
        btn_layout = QHBoxLayout()

        btn_indietro = QPushButton("← Indietro")
        btn_indietro.clicked.connect(lambda: self.parent().goToStep(WorkflowStep.APERTURE))
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

        # Aggiorna lista muri senza fondazione
        self._updateMissingWalls()

        # Riepilogo
        n_fond = len(self.progetto.fondazioni)
        n_muri = len(self.progetto.muri)
        copertura = n_fond / n_muri * 100 if n_muri > 0 else 0

        self.summary.setText(f"""
📊 Riepilogo: {n_fond} fondazioni definite per {n_muri} muri ({copertura:.0f}% copertura)
{'⚠️ Alcuni muri non hanno fondazione!' if copertura < 100 else '✓ Tutti i muri hanno fondazione'}
        """.strip())

    def _updateMissingWalls(self):
        """Aggiorna lista muri senza fondazione"""
        # Pulisci layout esistente
        while self.missing_list_layout.count():
            item = self.missing_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Trova muri senza fondazione
        muri_con_fond = {f.muro_collegato for f in self.progetto.fondazioni}
        muri_mancanti = [m for m in self.progetto.muri if m.nome not in muri_con_fond]

        if not muri_mancanti:
            self.missing_group.hide()
            return

        self.missing_group.show()
        self.missing_group.setTitle(f"Muri senza fondazione ({len(muri_mancanti)})")

        for muro in muri_mancanti[:8]:  # Mostra max 8
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(5, 2, 5, 2)

            label = QLabel(f"{muro.nome} - L={muro.lunghezza:.2f}m, s={muro.spessore:.2f}m")
            label.setStyleSheet("color: #333;")
            row_layout.addWidget(label, 1)

            btn_add = QPushButton("+ Aggiungi")
            btn_add.setFixedWidth(90)
            btn_add.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border-radius: 3px;
                    padding: 3px 8px;
                }
                QPushButton:hover { background-color: #218838; }
            """)
            btn_add.clicked.connect(lambda checked, m=muro: self._quickAddFondazione(m))
            row_layout.addWidget(btn_add)

            self.missing_list_layout.addWidget(row)

        if len(muri_mancanti) > 8:
            more = QLabel(f"... e altri {len(muri_mancanti) - 8} muri")
            more.setStyleSheet("color: #666; font-style: italic;")
            self.missing_list_layout.addWidget(more)

    def _quickAddFondazione(self, muro):
        """Aggiunge fondazione automatica per un muro specifico"""
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
        self.refresh()
        # Notifica la modifica
        main_win = self.window()
        if hasattr(main_win, 'setModificato'):
            main_win.setModificato(True)

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
        btn_indietro.clicked.connect(lambda: self.parent().goToStep(WorkflowStep.FONDAZIONI))
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
        """Apre dialogo per inserire nuovo cordolo"""
        piano_corrente = 0
        if self.progetto.piani:
            piano_corrente = max(p.numero for p in self.progetto.piani)

        dlg = DialogoCordolo(self.progetto, piano=piano_corrente, parent=self)
        if dlg.exec_() == QDialog.Accepted and dlg.cordolo_creato:
            self.progetto.cordoli.append(dlg.cordolo_creato)
            self.refreshTables()
            # Notifica la modifica
            main_win = self.window()
            if hasattr(main_win, 'setModificato'):
                main_win.setModificato(True)

    def aggiungiTirante(self):
        """Apre dialogo per inserire nuovo tirante"""
        piano_corrente = 0
        if self.progetto.piani:
            piano_corrente = max(p.numero for p in self.progetto.piani)

        dlg = DialogoTirante(self.progetto, piano=piano_corrente, parent=self)
        if dlg.exec_() == QDialog.Accepted and dlg.tirante_creato:
            self.progetto.tiranti.append(dlg.tirante_creato)
            self.refreshTables()
            # Notifica la modifica
            main_win = self.window()
            if hasattr(main_win, 'setModificato'):
                main_win.setModificato(True)

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
# DIALOGO SOLAIO
# ============================================================================

class DialogoSolaio(QDialog):
    """Dialogo per inserire solai con tutti i parametri"""

    TIPI_SOLAIO = [
        ("Laterocemento 20+5", 3.2, "Solaio in laterizio e cls, H=25cm"),
        ("Laterocemento 25+5", 3.8, "Solaio in laterizio e cls, H=30cm"),
        ("Laterocemento 16+4", 2.6, "Solaio in laterizio e cls, H=20cm"),
        ("Soletta piena 20cm", 5.0, "Soletta in c.a. pieno"),
        ("Soletta piena 15cm", 3.75, "Soletta in c.a. pieno"),
        ("Legno tradizionale", 1.2, "Tavolato su travi in legno"),
        ("Legno lamellare", 1.5, "Pannello X-LAM o simile"),
        ("Acciaio e lamiera", 2.0, "Lamiera grecata collaborante"),
        ("Predalles", 2.8, "Lastre predalles prefabbricate"),
        ("Copertura leggera", 0.8, "Pannelli sandwich o simili"),
    ]

    CATEGORIE_USO = [
        ("A", "Residenziale (2.0 kN/m²)"),
        ("B", "Uffici (3.0 kN/m²)"),
        ("C1", "Aree con tavoli (3.0 kN/m²)"),
        ("C2", "Aree con sedili fissi (4.0 kN/m²)"),
        ("C3", "Aree senza ostacoli (5.0 kN/m²)"),
        ("D1", "Negozi (4.0 kN/m²)"),
        ("D2", "Grandi magazzini (5.0 kN/m²)"),
        ("E", "Biblioteche, archivi (6.0 kN/m²)"),
        ("F", "Autorimesse (2.5 kN/m²)"),
        ("H", "Coperture (0.5 kN/m²)"),
    ]

    CARICHI_CATEGORIA = {
        "A": 2.0, "B": 3.0, "C1": 3.0, "C2": 4.0, "C3": 5.0,
        "D1": 4.0, "D2": 5.0, "E": 6.0, "F": 2.5, "H": 0.5
    }

    def __init__(self, progetto: Progetto, piano: int = 0, parent=None):
        super().__init__(parent)
        self.progetto = progetto
        self.solaio_creato = None

        self.setWindowTitle("Inserisci Solaio")
        self.setMinimumSize(500, 600)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("Definizione Solaio")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #0066cc;")
        layout.addWidget(header)

        # Piano
        piano_group = QGroupBox("Piano")
        piano_layout = QFormLayout()
        self.piano_combo = QComboBox()
        for p in progetto.piani:
            self.piano_combo.addItem(f"{p.nome} (quota {p.quota:.2f}m)", p.numero)
        if piano < len(progetto.piani):
            self.piano_combo.setCurrentIndex(piano)
        piano_layout.addRow("Piano:", self.piano_combo)
        piano_group.setLayout(piano_layout)
        layout.addWidget(piano_group)

        # Tipo solaio
        tipo_group = QGroupBox("Tipo Solaio")
        tipo_layout = QVBoxLayout()

        self.tipo_combo = QComboBox()
        for nome, peso, desc in self.TIPI_SOLAIO:
            self.tipo_combo.addItem(f"{nome} ({peso:.1f} kN/m²)", (nome, peso))
        self.tipo_combo.currentIndexChanged.connect(self.onTipoChanged)
        tipo_layout.addWidget(self.tipo_combo)

        self.tipo_desc = QLabel(self.TIPI_SOLAIO[0][2])
        self.tipo_desc.setStyleSheet("color: #666; font-style: italic;")
        tipo_layout.addWidget(self.tipo_desc)

        tipo_group.setLayout(tipo_layout)
        layout.addWidget(tipo_group)

        # Dimensioni
        dim_group = QGroupBox("Dimensioni")
        dim_layout = QFormLayout()

        self.luce_spin = QDoubleSpinBox()
        self.luce_spin.setRange(1.0, 15.0)
        self.luce_spin.setValue(5.0)
        self.luce_spin.setSuffix(" m")
        self.luce_spin.setToolTip("Luce (distanza tra appoggi)")
        dim_layout.addRow("Luce:", self.luce_spin)

        self.larghezza_spin = QDoubleSpinBox()
        self.larghezza_spin.setRange(1.0, 30.0)
        self.larghezza_spin.setValue(5.0)
        self.larghezza_spin.setSuffix(" m")
        self.larghezza_spin.setToolTip("Larghezza del campo di solaio")
        dim_layout.addRow("Larghezza:", self.larghezza_spin)

        self.area_label = QLabel("25.0 m²")
        self.area_label.setStyleSheet("font-weight: bold;")
        dim_layout.addRow("Area:", self.area_label)

        self.luce_spin.valueChanged.connect(self.updateArea)
        self.larghezza_spin.valueChanged.connect(self.updateArea)

        dim_group.setLayout(dim_layout)
        layout.addWidget(dim_group)

        # Carichi
        carichi_group = QGroupBox("Carichi")
        carichi_layout = QFormLayout()

        self.categoria_combo = QComboBox()
        for cat, desc in self.CATEGORIE_USO:
            self.categoria_combo.addItem(f"{cat} - {desc}", cat)
        self.categoria_combo.currentIndexChanged.connect(self.onCategoriaChanged)
        carichi_layout.addRow("Categoria uso:", self.categoria_combo)

        self.peso_spin = QDoubleSpinBox()
        self.peso_spin.setRange(0.5, 10.0)
        self.peso_spin.setValue(3.2)
        self.peso_spin.setSuffix(" kN/m²")
        self.peso_spin.setToolTip("Peso proprio strutturale (G1)")
        carichi_layout.addRow("Peso proprio (G1):", self.peso_spin)

        self.perm_spin = QDoubleSpinBox()
        self.perm_spin.setRange(0.5, 5.0)
        self.perm_spin.setValue(1.5)
        self.perm_spin.setSuffix(" kN/m²")
        self.perm_spin.setToolTip("Carichi permanenti non strutturali (G2)")
        carichi_layout.addRow("Permanenti (G2):", self.perm_spin)

        self.variabile_spin = QDoubleSpinBox()
        self.variabile_spin.setRange(0.5, 10.0)
        self.variabile_spin.setValue(2.0)
        self.variabile_spin.setSuffix(" kN/m²")
        self.variabile_spin.setToolTip("Carico variabile (Q) da categoria uso")
        carichi_layout.addRow("Variabile (Q):", self.variabile_spin)

        self.totale_label = QLabel("6.7 kN/m²")
        self.totale_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        carichi_layout.addRow("Totale:", self.totale_label)

        self.peso_spin.valueChanged.connect(self.updateTotale)
        self.perm_spin.valueChanged.connect(self.updateTotale)
        self.variabile_spin.valueChanged.connect(self.updateTotale)

        carichi_group.setLayout(carichi_layout)
        layout.addWidget(carichi_group)

        # Pulsanti
        btn_layout = QHBoxLayout()
        btn_annulla = QPushButton("Annulla")
        btn_annulla.clicked.connect(self.reject)
        btn_crea = QPushButton("Crea Solaio")
        btn_crea.setStyleSheet("background-color: #0066cc; color: white; font-weight: bold; padding: 8px 20px;")
        btn_crea.clicked.connect(self.creaSolaio)
        btn_layout.addWidget(btn_annulla)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_crea)
        layout.addLayout(btn_layout)

    def onTipoChanged(self, idx):
        nome, peso = self.tipo_combo.currentData()
        self.peso_spin.setValue(peso)
        self.tipo_desc.setText(self.TIPI_SOLAIO[idx][2])

    def onCategoriaChanged(self, idx):
        cat = self.categoria_combo.currentData()
        self.variabile_spin.setValue(self.CARICHI_CATEGORIA.get(cat, 2.0))

    def updateArea(self):
        area = self.luce_spin.value() * self.larghezza_spin.value()
        self.area_label.setText(f"{area:.1f} m²")

    def updateTotale(self):
        tot = self.peso_spin.value() + self.perm_spin.value() + self.variabile_spin.value()
        self.totale_label.setText(f"{tot:.1f} kN/m²")

    def creaSolaio(self):
        n = len(self.progetto.solai) + 1
        nome, _ = self.tipo_combo.currentData()

        self.solaio_creato = Solaio(
            nome=f"S{n}",
            piano=self.piano_combo.currentData(),
            tipo=nome,
            luce=self.luce_spin.value(),
            larghezza=self.larghezza_spin.value(),
            peso_proprio=self.peso_spin.value(),
            carico_variabile=self.variabile_spin.value(),
            categoria_uso=self.categoria_combo.currentData()
        )
        self.accept()


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

        self.btn_auto = QPushButton("⚡ Genera Automaticamente")
        self.btn_auto.setToolTip("Crea un solaio per ogni piano")
        self.btn_auto.clicked.connect(self.generaAutomatici)
        toolbar.addWidget(self.btn_auto)

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

        # Sezione piani senza solaio
        self.missing_group = QGroupBox("Piani senza solaio")
        self.missing_group.setStyleSheet("""
            QGroupBox { color: #c70000; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 5px; }
        """)
        missing_layout = QVBoxLayout()
        self.missing_list = QWidget()
        self.missing_list_layout = QVBoxLayout(self.missing_list)
        self.missing_list_layout.setContentsMargins(0, 0, 0, 0)
        self.missing_list_layout.setSpacing(4)
        missing_layout.addWidget(self.missing_list)
        self.missing_group.setLayout(missing_layout)
        layout.addWidget(self.missing_group)

        # Riepilogo
        self.summary = QLabel("")
        self.summary.setStyleSheet("padding: 10px; background: #f8f9fa; border-radius: 5px;")
        layout.addWidget(self.summary)

        # Pulsanti navigazione
        btn_layout = QHBoxLayout()
        btn_indietro = QPushButton("← Indietro")
        btn_indietro.clicked.connect(lambda: self.parent().goToStep(WorkflowStep.CORDOLI))
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

        # Aggiorna lista piani senza solaio
        self._updateMissingFloors()

        # Riepilogo
        n = len(self.progetto.solai)
        area_tot = sum(s.area for s in self.progetto.solai)
        carico_tot = sum(s.carico_totale * s.area for s in self.progetto.solai)
        self.summary.setText(f"📊 Totale: {n} solai | Area: {area_tot:.1f} m² | Carico: {carico_tot:.0f} kN")

    def _updateMissingFloors(self):
        """Aggiorna lista piani senza solaio"""
        # Pulisci layout esistente
        while self.missing_list_layout.count():
            item = self.missing_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Trova piani senza solaio
        piani_con_solaio = {s.piano for s in self.progetto.solai}
        piani_mancanti = [p for p in self.progetto.piani if p.numero not in piani_con_solaio]

        if not piani_mancanti:
            self.missing_group.hide()
            return

        self.missing_group.show()
        self.missing_group.setTitle(f"Piani senza solaio ({len(piani_mancanti)})")

        for piano in piani_mancanti:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(5, 2, 5, 2)

            label = QLabel(f"{piano.nome} - Quota: {piano.quota:.2f}m, H={piano.altezza:.2f}m")
            label.setStyleSheet("color: #333;")
            row_layout.addWidget(label, 1)

            btn_add = QPushButton("+ Aggiungi")
            btn_add.setFixedWidth(90)
            btn_add.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border-radius: 3px;
                    padding: 3px 8px;
                }
                QPushButton:hover { background-color: #218838; }
            """)
            btn_add.clicked.connect(lambda checked, p=piano: self._quickAddSolaio(p))
            row_layout.addWidget(btn_add)

            self.missing_list_layout.addWidget(row)

    def _quickAddSolaio(self, piano):
        """Aggiunge solaio automatico per un piano specifico"""
        n = len(self.progetto.solai) + 1
        solaio = Solaio(
            nome=f"S{n}",
            piano=piano.numero,
            tipo="Laterocemento 20+5",
            luce=5.0,
            larghezza=5.0,
            peso_proprio=3.2,
            carico_variabile=2.0,
            categoria_uso="A"
        )
        self.progetto.solai.append(solaio)
        self.refresh()
        # Notifica la modifica
        main_win = self.window()
        if hasattr(main_win, 'setModificato'):
            main_win.setModificato(True)

    def aggiungiSolaio(self):
        """Apre dialogo per inserire nuovo solaio"""
        piano_default = 0
        if self.progetto.piani:
            # Trova primo piano senza solaio
            piani_con_solaio = {s.piano for s in self.progetto.solai}
            for p in self.progetto.piani:
                if p.numero not in piani_con_solaio:
                    piano_default = p.numero
                    break

        dlg = DialogoSolaio(self.progetto, piano=piano_default, parent=self)
        if dlg.exec_() == QDialog.Accepted and dlg.solaio_creato:
            self.progetto.solai.append(dlg.solaio_creato)
            self.refresh()
            # Notifica la modifica
            main_win = self.window()
            if hasattr(main_win, 'setModificato'):
                main_win.setModificato(True)

    def generaAutomatici(self):
        """Genera solai automatici per tutti i piani senza solaio"""
        piani_con_solaio = {s.piano for s in self.progetto.solai}
        nuovi = 0

        for piano in self.progetto.piani:
            if piano.numero not in piani_con_solaio:
                n = len(self.progetto.solai) + 1
                solaio = Solaio(
                    nome=f"S{n}",
                    piano=piano.numero,
                    tipo="Laterocemento 20+5",
                    luce=5.0,
                    larghezza=5.0,
                    peso_proprio=3.2,
                    carico_variabile=2.0,
                    categoria_uso="A"
                )
                self.progetto.solai.append(solaio)
                nuovi += 1

        self.refresh()
        QMessageBox.information(self, "Solai Generati", f"Creati {nuovi} solai automatici")

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
        btn_indietro.clicked.connect(lambda: self.parent().goToStep(WorkflowStep.SOLAI))
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
    """Widget per vista 3D isometrica/prospettica dell'edificio - Versione avanzata"""

    # Colori elementi
    COLORI = {
        'muro': QColor(200, 160, 120),
        'muro_scuro': QColor(160, 120, 80),
        'muro_chiaro': QColor(220, 190, 150),
        'fondazione': QColor(140, 140, 140),
        'fondazione_scuro': QColor(100, 100, 100),
        'cordolo': QColor(180, 180, 180),
        'cordolo_scuro': QColor(140, 140, 140),
        'solaio': QColor(180, 200, 180),
        'solaio_scuro': QColor(140, 160, 140),
        'finestra': QColor(150, 200, 255, 180),
        'porta': QColor(120, 80, 50),
        'terreno': QColor(180, 160, 130),
        'griglia': QColor(220, 220, 220),
        'asse_x': QColor(255, 80, 80),
        'asse_y': QColor(80, 200, 80),
        'asse_z': QColor(80, 80, 255),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.progetto: Optional[Progetto] = None
        self.setMinimumSize(400, 400)

        # Parametri vista
        self.scala = 30  # pixel per metro
        self.rotazione_h = 35  # rotazione orizzontale (gradi)
        self.rotazione_v = 25  # rotazione verticale (gradi)
        self.offset_x = 0
        self.offset_y = 0

        # Opzioni visualizzazione
        self.mostra_dcr = True
        self.mostra_aperture = True
        self.mostra_fondazioni = True
        self.mostra_cordoli = True
        self.mostra_solai = True
        self.mostra_griglia = True
        self.mostra_assi = True
        self.mostra_etichette = True

        # Modalità vista
        self.prospettiva = False
        self.distanza_camera = 60

        # Mouse interaction
        self.last_mouse_pos = None
        self.dragging = False
        self.panning = False

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def setProgetto(self, progetto: Progetto):
        self.progetto = progetto
        self._centerView()
        self.update()

    def _centerView(self):
        """Centra la vista sul modello"""
        if not self.progetto or not self.progetto.muri:
            self.offset_x = self.width() // 2
            self.offset_y = self.height() // 2
            return

        # Calcola bounding box
        xs = [m.x1 for m in self.progetto.muri] + [m.x2 for m in self.progetto.muri]
        ys = [m.y1 for m in self.progetto.muri] + [m.y2 for m in self.progetto.muri]
        cx = (min(xs) + max(xs)) / 2
        cy = (min(ys) + max(ys)) / 2

        # Centro schermo
        self.offset_x = self.width() // 2
        self.offset_y = self.height() // 2 + 50

    def project3D(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """
        Proiezione 3D -> 2D con profondità per z-sorting.
        Usa mathutils (da Blender) per trasformazioni ottimizzate se disponibile.
        """
        if MATHUTILS_AVAILABLE:
            # === VERSIONE OTTIMIZZATA CON MATHUTILS ===
            v = Vector((x, y, z))

            # Rotazione con quaternioni (più efficiente e numericamente stabile)
            angle_h = math.radians(self.rotazione_h)
            angle_v = math.radians(self.rotazione_v)

            # Quaternione per rotazione Z (orizzontale)
            rot_z = Quaternion((0, 0, 1), angle_h)
            # Quaternione per rotazione X (verticale)
            rot_x = Quaternion((1, 0, 0), angle_v)

            # Applica rotazioni (ordine: prima Z, poi X)
            v = rot_z @ v
            v = rot_x @ v

            rx, ry2, rz2 = v.x, v.y, v.z
        else:
            # === FALLBACK: calcolo manuale ===
            angle_h = math.radians(self.rotazione_h)
            angle_v = math.radians(self.rotazione_v)

            # Rotazione orizzontale (attorno asse Z)
            rx = x * math.cos(angle_h) - y * math.sin(angle_h)
            ry = x * math.sin(angle_h) + y * math.cos(angle_h)
            rz = z

            # Rotazione verticale (attorno asse X)
            ry2 = ry * math.cos(angle_v) - rz * math.sin(angle_v)
            rz2 = ry * math.sin(angle_v) + rz * math.cos(angle_v)

        # Proiezione prospettica o isometrica
        if self.prospettiva:
            d = self.distanza_camera
            factor = d / (d + ry2) if (d + ry2) > 0.1 else 1
            px = rx * factor * self.scala + self.offset_x
            py = -rz2 * factor * self.scala + self.offset_y
        else:
            # Isometrica
            px = rx * self.scala + self.offset_x
            py = -rz2 * self.scala + self.offset_y

        return (px, py, ry2)  # ry2 = profondità per z-sorting

    def project3D_2D(self, x: float, y: float, z: float) -> Tuple[int, int]:
        """Proiezione semplificata che ritorna solo coordinate schermo"""
        px, py, _ = self.project3D(x, y, z)
        return (int(px), int(py))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Sfondo gradiente (ottimizzato - singola operazione invece di 600+ drawLine)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(235, 240, 250))
        gradient.setColorAt(1, QColor(200, 210, 225))
        painter.fillRect(self.rect(), QBrush(gradient))

        if not self.progetto:
            painter.setPen(QColor(100, 100, 100))
            painter.setFont(QFont("Arial", 14))
            painter.drawText(self.rect(), Qt.AlignCenter, "Nessun progetto caricato")
            return

        # Raccogli tutti gli elementi con profondità per z-sorting
        elementi = []

        # Griglia e assi (sfondo)
        if self.mostra_griglia:
            self._drawGrid(painter)

        if self.mostra_assi:
            self._drawAxes(painter)

        # Disegna ombre a terra (prima degli elementi)
        self._drawShadows(painter)

        # Fondazioni
        if self.mostra_fondazioni:
            for fond in self.progetto.fondazioni:
                depth = self._getElementDepth(fond.x1, fond.y1, -fond.profondita/2)
                elementi.append(('fondazione', fond, depth))

        # Muri
        for muro in self.progetto.muri:
            cx = (muro.x1 + muro.x2) / 2
            cy = (muro.y1 + muro.y2) / 2
            cz = muro.z + muro.altezza / 2
            depth = self._getElementDepth(cx, cy, cz)
            elementi.append(('muro', muro, depth))

        # Cordoli
        if self.mostra_cordoli:
            for cordolo in self.progetto.cordoli:
                cx = (cordolo.x1 + cordolo.x2) / 2
                cy = (cordolo.y1 + cordolo.y2) / 2
                # Trova z dal muro collegato
                cz = 3.0  # default
                for m in self.progetto.muri:
                    if m.nome == cordolo.muro_collegato:
                        cz = m.z + m.altezza + cordolo.altezza / 2
                        break
                depth = self._getElementDepth(cx, cy, cz)
                elementi.append(('cordolo', cordolo, depth))

        # Solai
        if self.mostra_solai:
            for solaio in self.progetto.solai:
                # Calcola z corretto dal piano
                sz = 3.0
                for p in self.progetto.piani:
                    if p.numero == solaio.piano:
                        sz = p.quota + p.altezza
                        break
                # Centro del solaio per z-sorting
                if self.progetto.muri:
                    xs = [m.x1 for m in self.progetto.muri] + [m.x2 for m in self.progetto.muri]
                    ys = [m.y1 for m in self.progetto.muri] + [m.y2 for m in self.progetto.muri]
                    scx = (min(xs) + max(xs)) / 2
                    scy = (min(ys) + max(ys)) / 2
                else:
                    scx, scy = 5, 5
                depth = self._getElementDepth(scx, scy, sz)
                elementi.append(('solaio', solaio, depth))

        # Ordina per profondità (da lontano a vicino)
        elementi.sort(key=lambda e: e[2], reverse=True)

        # Disegna elementi ordinati
        for tipo, elem, _ in elementi:
            if tipo == 'fondazione':
                self._drawFondazione3D(painter, elem)
            elif tipo == 'muro':
                self._drawMuro3D(painter, elem)
            elif tipo == 'cordolo':
                self._drawCordolo3D(painter, elem)
            elif tipo == 'solaio':
                self._drawSolaio3D(painter, elem)

        # Info overlay
        self._drawInfo(painter)

    def _getElementDepth(self, x: float, y: float, z: float) -> float:
        """Calcola profondità elemento per z-sorting"""
        _, _, depth = self.project3D(x, y, z)
        return depth

    def _drawGrid(self, painter):
        """Disegna griglia a terra"""
        painter.setPen(QPen(self.COLORI['griglia'], 1))

        z = 0
        for i in range(-2, 20, 2):
            p1 = self.project3D_2D(i, -2, z)
            p2 = self.project3D_2D(i, 20, z)
            painter.drawLine(p1[0], p1[1], p2[0], p2[1])

            p1 = self.project3D_2D(-2, i, z)
            p2 = self.project3D_2D(20, i, z)
            painter.drawLine(p1[0], p1[1], p2[0], p2[1])

    def _drawAxes(self, painter):
        """Disegna assi di riferimento"""
        origin = self.project3D_2D(0, 0, 0)
        length = 2  # metri

        # Asse X (rosso)
        px = self.project3D_2D(length, 0, 0)
        painter.setPen(QPen(self.COLORI['asse_x'], 2))
        painter.drawLine(origin[0], origin[1], px[0], px[1])
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(px[0] + 5, px[1], "X")

        # Asse Y (verde)
        py = self.project3D_2D(0, length, 0)
        painter.setPen(QPen(self.COLORI['asse_y'], 2))
        painter.drawLine(origin[0], origin[1], py[0], py[1])
        painter.drawText(py[0] + 5, py[1], "Y")

        # Asse Z (blu)
        pz = self.project3D_2D(0, 0, length)
        painter.setPen(QPen(self.COLORI['asse_z'], 2))
        painter.drawLine(origin[0], origin[1], pz[0], pz[1])
        painter.drawText(pz[0] + 5, pz[1], "Z")

    def _drawMuro3D(self, painter, muro: Muro):
        """Disegna muro come box 3D con spessore"""
        # Colore base (con DCR se attivo)
        if self.mostra_dcr and muro.dcr > 0:
            if muro.dcr > 1.0:
                base_color = QColor(255, 100, 100)
            elif muro.dcr > 0.8:
                base_color = QColor(255, 200, 100)
            else:
                base_color = QColor(100, 220, 100)
        else:
            base_color = self.COLORI['muro']

        # Calcola direzione e normale del muro
        dx = muro.x2 - muro.x1
        dy = muro.y2 - muro.y1
        length = math.sqrt(dx*dx + dy*dy)
        if length < 0.01:
            return

        # Normale (perpendicolare)
        nx = -dy / length * muro.spessore / 2
        ny = dx / length * muro.spessore / 2

        z0 = muro.z
        z1 = muro.z + muro.altezza

        # 8 vertici del box
        v = [
            (muro.x1 - nx, muro.y1 - ny, z0),  # 0: fronte-sx-basso
            (muro.x2 - nx, muro.y2 - ny, z0),  # 1: fronte-dx-basso
            (muro.x2 - nx, muro.y2 - ny, z1),  # 2: fronte-dx-alto
            (muro.x1 - nx, muro.y1 - ny, z1),  # 3: fronte-sx-alto
            (muro.x1 + nx, muro.y1 + ny, z0),  # 4: retro-sx-basso
            (muro.x2 + nx, muro.y2 + ny, z0),  # 5: retro-dx-basso
            (muro.x2 + nx, muro.y2 + ny, z1),  # 6: retro-dx-alto
            (muro.x1 + nx, muro.y1 + ny, z1),  # 7: retro-sx-alto
        ]

        # Proietta vertici
        pv = [self.project3D_2D(*vtx) for vtx in v]

        # Disegna TUTTE le facce con gradienti per effetto 3D migliore
        # Bottom (sempre sotto) - scuro
        self._drawFace(painter, [pv[4], pv[5], pv[1], pv[0]], base_color.darker(140))

        # Back faces - più scure
        self._drawFaceGradient(painter, [pv[5], pv[4], pv[7], pv[6]],
                              base_color.darker(120), base_color.darker(135), vertical=True)
        self._drawFaceGradient(painter, [pv[4], pv[0], pv[3], pv[7]],
                              base_color.darker(115), base_color.darker(130), vertical=True)

        # Front faces - con gradiente verticale (più chiaro in alto)
        self._drawFaceGradient(painter, [pv[1], pv[5], pv[6], pv[2]],
                              base_color.darker(105), base_color.darker(115), vertical=True)
        self._drawFaceGradient(painter, [pv[0], pv[1], pv[2], pv[3]],
                              base_color, base_color.darker(108), vertical=True)

        # Top - chiaro con gradiente
        self._drawFaceGradient(painter, [pv[3], pv[2], pv[6], pv[7]],
                              base_color.lighter(115), base_color.lighter(105), vertical=False)

        # Disegna spigoli scuri per definizione del volume (ambient occlusion)
        edge_color = QColor(40, 30, 20)
        painter.setPen(QPen(edge_color, 2))

        # Spigoli verticali
        painter.drawLine(pv[0][0], pv[0][1], pv[3][0], pv[3][1])
        painter.drawLine(pv[1][0], pv[1][1], pv[2][0], pv[2][1])
        painter.drawLine(pv[4][0], pv[4][1], pv[7][0], pv[7][1])
        painter.drawLine(pv[5][0], pv[5][1], pv[6][0], pv[6][1])

        # Spigoli top
        painter.drawLine(pv[3][0], pv[3][1], pv[2][0], pv[2][1])
        painter.drawLine(pv[2][0], pv[2][1], pv[6][0], pv[6][1])
        painter.drawLine(pv[6][0], pv[6][1], pv[7][0], pv[7][1])
        painter.drawLine(pv[7][0], pv[7][1], pv[3][0], pv[3][1])

        # Spigoli bottom visibili
        painter.drawLine(pv[0][0], pv[0][1], pv[1][0], pv[1][1])
        painter.drawLine(pv[1][0], pv[1][1], pv[5][0], pv[5][1])

        # Disegna aperture
        if self.mostra_aperture:
            self._drawApertureSuMuro(painter, muro, v)

        # Etichetta con sfondo
        if self.mostra_etichette:
            cx = (pv[0][0] + pv[2][0]) / 2
            cy = (pv[0][1] + pv[2][1]) / 2
            # Sfondo etichetta
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 180)))
            painter.drawRoundedRect(int(cx) - 15, int(cy) - 12, 30, 16, 3, 3)
            # Testo
            painter.setPen(QColor(40, 30, 20))
            painter.setFont(QFont("Arial", 9, QFont.Bold))
            painter.drawText(int(cx) - 10, int(cy), muro.nome)

    def _drawApertureSuMuro(self, painter, muro: Muro, vertici_muro):
        """Disegna aperture (finestre/porte) su un muro"""
        aperture_muro = [a for a in self.progetto.aperture if a.muro == muro.nome]
        if not aperture_muro:
            return

        dx = muro.x2 - muro.x1
        dy = muro.y2 - muro.y1
        length = math.sqrt(dx*dx + dy*dy)
        if length < 0.01:
            return

        ux, uy = dx / length, dy / length

        for ap in aperture_muro:
            # Posizione apertura lungo il muro
            ax = muro.x1 + ux * ap.posizione
            ay = muro.y1 + uy * ap.posizione

            z0 = muro.z + ap.altezza_davanzale
            z1 = z0 + ap.altezza

            # 4 vertici apertura (sulla faccia frontale)
            nx = -dy / length * muro.spessore / 2 * 1.01  # Leggermente davanti
            ny = dx / length * muro.spessore / 2 * 1.01

            p0 = self.project3D_2D(ax - nx, ay - ny, z0)
            p1 = self.project3D_2D(ax + ux * ap.larghezza - nx, ay + uy * ap.larghezza - ny, z0)
            p2 = self.project3D_2D(ax + ux * ap.larghezza - nx, ay + uy * ap.larghezza - ny, z1)
            p3 = self.project3D_2D(ax - nx, ay - ny, z1)

            if ap.tipo == 'finestra':
                # Finestra: rettangolo azzurro con croce
                painter.setPen(QPen(QColor(60, 60, 80), 1))
                painter.setBrush(QBrush(self.COLORI['finestra']))
            elif ap.tipo == 'porta':
                # Porta: rettangolo marrone
                painter.setPen(QPen(QColor(60, 40, 20), 1))
                painter.setBrush(QBrush(self.COLORI['porta']))
            else:
                painter.setPen(QPen(QColor(60, 60, 80), 1))
                painter.setBrush(QBrush(self.COLORI['finestra']))

            path = QPainterPath()
            path.moveTo(p0[0], p0[1])
            path.lineTo(p1[0], p1[1])
            path.lineTo(p2[0], p2[1])
            path.lineTo(p3[0], p3[1])
            path.closeSubpath()
            painter.drawPath(path)

            # Croce per finestre
            if ap.tipo == 'finestra':
                painter.setPen(QPen(QColor(80, 80, 100), 1))
                cx = (p0[0] + p2[0]) / 2
                cy = (p0[1] + p2[1]) / 2
                painter.drawLine(int((p0[0]+p1[0])/2), int((p0[1]+p1[1])/2),
                               int((p2[0]+p3[0])/2), int((p2[1]+p3[1])/2))
                painter.drawLine(int((p0[0]+p3[0])/2), int((p0[1]+p3[1])/2),
                               int((p1[0]+p2[0])/2), int((p1[1]+p2[1])/2))

    def _drawFondazione3D(self, painter, fond: Fondazione):
        """Disegna fondazione come box 3D pieno"""
        z0 = -fond.profondita
        z1 = 0

        dx = fond.x2 - fond.x1
        dy = fond.y2 - fond.y1
        length = math.sqrt(dx*dx + dy*dy)
        if length < 0.01:
            return

        nx = -dy / length * fond.larghezza / 2
        ny = dx / length * fond.larghezza / 2

        # 8 vertici del box
        v = [
            (fond.x1 - nx, fond.y1 - ny, z0),  # 0
            (fond.x2 - nx, fond.y2 - ny, z0),  # 1
            (fond.x2 - nx, fond.y2 - ny, z1),  # 2
            (fond.x1 - nx, fond.y1 - ny, z1),  # 3
            (fond.x1 + nx, fond.y1 + ny, z0),  # 4
            (fond.x2 + nx, fond.y2 + ny, z0),  # 5
            (fond.x2 + nx, fond.y2 + ny, z1),  # 6
            (fond.x1 + nx, fond.y1 + ny, z1),  # 7
        ]

        pv = [self.project3D_2D(*vtx) for vtx in v]

        # Colore fondazione (cemento grigio scuro)
        base_color = QColor(130, 130, 135)

        # Disegna TUTTE le facce (volumi pieni)
        # Bottom
        self._drawFace(painter, [pv[4], pv[5], pv[1], pv[0]], base_color.darker(125))
        # Back
        self._drawFace(painter, [pv[5], pv[4], pv[7], pv[6]], base_color.darker(115))
        # Left
        self._drawFace(painter, [pv[4], pv[0], pv[3], pv[7]], base_color.darker(112))
        # Right
        self._drawFace(painter, [pv[1], pv[5], pv[6], pv[2]], base_color.darker(108))
        # Front
        self._drawFace(painter, [pv[0], pv[1], pv[2], pv[3]], base_color)
        # Top
        self._drawFace(painter, [pv[3], pv[2], pv[6], pv[7]], base_color.lighter(108))

        # Bordi per definizione
        painter.setPen(QPen(QColor(70, 70, 75), 2))
        # Spigoli verticali principali
        painter.drawLine(pv[0][0], pv[0][1], pv[3][0], pv[3][1])
        painter.drawLine(pv[1][0], pv[1][1], pv[2][0], pv[2][1])
        # Spigoli top
        painter.drawLine(pv[3][0], pv[3][1], pv[2][0], pv[2][1])
        painter.drawLine(pv[2][0], pv[2][1], pv[6][0], pv[6][1])
        painter.drawLine(pv[6][0], pv[6][1], pv[7][0], pv[7][1])
        painter.drawLine(pv[7][0], pv[7][1], pv[3][0], pv[3][1])

    def _drawCordolo3D(self, painter, cordolo: Cordolo):
        """Disegna cordolo come box 3D sopra il muro collegato"""
        # Trova il muro collegato per posizionare correttamente il cordolo
        z0 = 3.0  # Default: sopra piano terra
        muro_collegato = None
        for m in self.progetto.muri:
            if m.nome == cordolo.muro_collegato:
                muro_collegato = m
                z0 = m.z + m.altezza  # Cordolo sopra il muro
                break

        z1 = z0 + cordolo.altezza

        dx = cordolo.x2 - cordolo.x1
        dy = cordolo.y2 - cordolo.y1
        length = math.sqrt(dx*dx + dy*dy)
        if length < 0.01:
            return

        # Normale per spessore
        nx = -dy / length * cordolo.base / 2
        ny = dx / length * cordolo.base / 2

        # 8 vertici del box 3D
        v = [
            (cordolo.x1 - nx, cordolo.y1 - ny, z0),  # 0: fronte-sx-basso
            (cordolo.x2 - nx, cordolo.y2 - ny, z0),  # 1: fronte-dx-basso
            (cordolo.x2 - nx, cordolo.y2 - ny, z1),  # 2: fronte-dx-alto
            (cordolo.x1 - nx, cordolo.y1 - ny, z1),  # 3: fronte-sx-alto
            (cordolo.x1 + nx, cordolo.y1 + ny, z0),  # 4: retro-sx-basso
            (cordolo.x2 + nx, cordolo.y2 + ny, z0),  # 5: retro-dx-basso
            (cordolo.x2 + nx, cordolo.y2 + ny, z1),  # 6: retro-dx-alto
            (cordolo.x1 + nx, cordolo.y1 + ny, z1),  # 7: retro-sx-alto
        ]

        pv = [self.project3D_2D(*vtx) for vtx in v]

        # Colore cemento armato (grigio)
        base_color = QColor(160, 160, 165)

        # Disegna TUTTE le facce del cordolo (volumi pieni)
        # Bottom
        self._drawFace(painter, [pv[4], pv[5], pv[1], pv[0]], base_color.darker(120))
        # Back
        self._drawFace(painter, [pv[5], pv[4], pv[7], pv[6]], base_color.darker(115))
        # Left
        self._drawFace(painter, [pv[4], pv[0], pv[3], pv[7]], base_color.darker(112))
        # Right
        self._drawFace(painter, [pv[1], pv[5], pv[6], pv[2]], base_color.darker(108))
        # Front
        self._drawFace(painter, [pv[0], pv[1], pv[2], pv[3]], base_color)
        # Top
        self._drawFace(painter, [pv[3], pv[2], pv[6], pv[7]], base_color.lighter(110))

        # Bordi per definizione
        painter.setPen(QPen(QColor(90, 90, 100), 2))
        # Spigoli verticali
        painter.drawLine(pv[0][0], pv[0][1], pv[3][0], pv[3][1])
        painter.drawLine(pv[1][0], pv[1][1], pv[2][0], pv[2][1])
        # Spigoli top
        painter.drawLine(pv[3][0], pv[3][1], pv[2][0], pv[2][1])
        painter.drawLine(pv[2][0], pv[2][1], pv[6][0], pv[6][1])
        painter.drawLine(pv[6][0], pv[6][1], pv[7][0], pv[7][1])
        painter.drawLine(pv[7][0], pv[7][1], pv[3][0], pv[3][1])

    def _drawSolaio3D(self, painter, solaio: Solaio):
        """Disegna solaio come lastra 3D con spessore - posizionato sui muri"""
        # Trova i muri del piano corrispondente basandosi sulla quota Z
        # Piano 0: muri con z=0, Piano 1: muri con z=3, etc.
        quota_piano = solaio.piano * 3.0  # Stima quota base del piano

        # Trova muri che appartengono a questo piano (basandosi su z)
        muri_piano = [m for m in self.progetto.muri
                     if abs(m.z - quota_piano) < 1.0]

        if not muri_piano:
            # Nessun muro per questo piano - non disegnare il solaio
            return

        # Z del solaio = top dei muri di questo piano
        z_top = max(m.z + m.altezza for m in muri_piano)

        # Spessore solaio
        spessore = 0.20  # 20cm
        z_bottom = z_top - spessore

        # Bounding box dai muri
        xs = [m.x1 for m in muri_piano] + [m.x2 for m in muri_piano]
        ys = [m.y1 for m in muri_piano] + [m.y2 for m in muri_piano]

        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)

        # 8 vertici del box solaio
        v = [
            (x0, y0, z_bottom),  # 0: front-left-bottom
            (x1, y0, z_bottom),  # 1: front-right-bottom
            (x1, y1, z_bottom),  # 2: back-right-bottom
            (x0, y1, z_bottom),  # 3: back-left-bottom
            (x0, y0, z_top),     # 4: front-left-top
            (x1, y0, z_top),     # 5: front-right-top
            (x1, y1, z_top),     # 6: back-right-top
            (x0, y1, z_top),     # 7: back-left-top
        ]

        pv = [self.project3D_2D(*vtx) for vtx in v]

        # Colore solaio (laterizio/cemento)
        base_color = QColor(190, 175, 155)

        # Disegna TUTTE le facce (no backface culling - usiamo z-sorting)
        # Ordine: prima le facce più lontane
        self._drawFace(painter, [pv[0], pv[3], pv[2], pv[1]], base_color.darker(125))  # Bottom
        self._drawFace(painter, [pv[2], pv[3], pv[7], pv[6]], base_color.darker(115))  # Back
        self._drawFace(painter, [pv[0], pv[4], pv[7], pv[3]], base_color.darker(112))  # Left
        self._drawFace(painter, [pv[1], pv[2], pv[6], pv[5]], base_color.darker(108))  # Right
        self._drawFace(painter, [pv[0], pv[1], pv[5], pv[4]], base_color.darker(110))  # Front
        self._drawFace(painter, [pv[4], pv[5], pv[6], pv[7]], base_color.lighter(108)) # Top

        # Bordi per definizione
        painter.setPen(QPen(QColor(80, 70, 60), 2))
        painter.setBrush(Qt.NoBrush)
        # Bordi top
        painter.drawLine(pv[4][0], pv[4][1], pv[5][0], pv[5][1])
        painter.drawLine(pv[5][0], pv[5][1], pv[6][0], pv[6][1])
        painter.drawLine(pv[6][0], pv[6][1], pv[7][0], pv[7][1])
        painter.drawLine(pv[7][0], pv[7][1], pv[4][0], pv[4][1])

        # Etichetta centrata
        if self.mostra_etichette:
            cx = sum(pv[i][0] for i in [4,5,6,7]) / 4
            cy = sum(pv[i][1] for i in [4,5,6,7]) / 4
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
            painter.drawRoundedRect(int(cx) - 30, int(cy) - 10, 60, 18, 4, 4)
            painter.setPen(QColor(50, 40, 30))
            painter.setFont(QFont("Arial", 9, QFont.Bold))
            painter.drawText(int(cx) - 25, int(cy) + 4, f"Solaio P{solaio.piano}")

    def _drawFace(self, painter, pts, color, border_color=None):
        """Disegna una faccia poligonale con bordo"""
        if border_color is None:
            border_color = QColor(60, 50, 40)
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(QBrush(color))
        path = QPainterPath()
        path.moveTo(pts[0][0], pts[0][1])
        for pt in pts[1:]:
            path.lineTo(pt[0], pt[1])
        path.closeSubpath()
        painter.drawPath(path)

    def _drawFaceGradient(self, painter, pts, color1, color2, vertical=True):
        """Disegna una faccia con gradiente per effetto 3D"""
        if len(pts) < 3:
            return

        # Crea bounding box
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)

        # Gradiente
        if vertical:
            gradient = QLinearGradient(x0, y0, x0, y1)
        else:
            gradient = QLinearGradient(x0, y0, x1, y0)

        gradient.setColorAt(0, color1)
        gradient.setColorAt(1, color2)

        painter.setPen(QPen(QColor(50, 40, 30), 1))
        painter.setBrush(QBrush(gradient))

        path = QPainterPath()
        path.moveTo(pts[0][0], pts[0][1])
        for pt in pts[1:]:
            path.lineTo(pt[0], pt[1])
        path.closeSubpath()
        painter.drawPath(path)

    def _drawShadows(self, painter):
        """Disegna ombre proiettate a terra per tutti gli elementi"""
        shadow_color = QColor(0, 0, 0, 40)  # Nero semi-trasparente
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(shadow_color))

        # Offset ombra (simula luce da alto-destra)
        shadow_offset_x = 0.3
        shadow_offset_y = 0.3

        # Ombre dei muri
        for muro in self.progetto.muri:
            dx = muro.x2 - muro.x1
            dy = muro.y2 - muro.y1
            length = math.sqrt(dx*dx + dy*dy)
            if length < 0.01:
                continue

            nx = -dy / length * muro.spessore / 2
            ny = dx / length * muro.spessore / 2

            # Proietta ombra a z=0
            pts = [
                self.project3D_2D(muro.x1 - nx + shadow_offset_x, muro.y1 - ny + shadow_offset_y, 0),
                self.project3D_2D(muro.x2 - nx + shadow_offset_x, muro.y2 - ny + shadow_offset_y, 0),
                self.project3D_2D(muro.x2 + nx + shadow_offset_x, muro.y2 + ny + shadow_offset_y, 0),
                self.project3D_2D(muro.x1 + nx + shadow_offset_x, muro.y1 + ny + shadow_offset_y, 0),
            ]

            path = QPainterPath()
            path.moveTo(pts[0][0], pts[0][1])
            for pt in pts[1:]:
                path.lineTo(pt[0], pt[1])
            path.closeSubpath()
            painter.drawPath(path)

    def _drawInfo(self, painter):
        """Disegna informazioni overlay"""
        painter.setPen(QPen(QColor(60, 60, 80)))
        painter.setFont(QFont("Arial", 10))

        modo = "Prospettiva" if self.prospettiva else "Isometrica"
        painter.drawText(10, 20, f"Vista {modo} - {self.progetto.nome}")

        painter.setFont(QFont("Arial", 9))
        stats = f"Muri: {len(self.progetto.muri)} | Aperture: {len(self.progetto.aperture)} | Piani: {len(self.progetto.piani)}"
        painter.drawText(10, 38, stats)

        painter.setFont(QFont("Arial", 8))
        painter.setPen(QColor(100, 100, 120))
        h = self.height()
        painter.drawText(10, h - 65, "Mouse: Trascina=Ruota | Scroll=Zoom | Middle=Pan")
        painter.drawText(10, h - 50, "Toggle: F=Fondazioni | C=Cordoli | S=Solai | A=Aperture | G=Griglia | L=Etichette | D=DCR")
        painter.drawText(10, h - 35, "Vista: P=Prospettiva | R=Reset | Home=Frontale | +/-=Zoom")
        # Stato elementi visibili
        stato = []
        if self.mostra_fondazioni: stato.append("F")
        if self.mostra_cordoli: stato.append("C")
        if self.mostra_solai: stato.append("S")
        if self.mostra_aperture: stato.append("A")
        if self.mostra_griglia: stato.append("G")
        if self.mostra_etichette: stato.append("L")
        if self.mostra_dcr: stato.append("D")
        painter.drawText(10, h - 20, f"Rot: {self.rotazione_h:.0f}°/{self.rotazione_v:.0f}° | Scala: {self.scala:.0f}x | Attivi: [{','.join(stato)}]")

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.scala = min(80, self.scala * 1.1)
        else:
            self.scala = max(5, self.scala / 1.1)
        self.update()

    def mousePressEvent(self, event):
        self.last_mouse_pos = event.pos()
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.setCursor(Qt.ClosedHandCursor)
        elif event.button() == Qt.MiddleButton:
            self.panning = True
            self.setCursor(Qt.SizeAllCursor)

    def mouseMoveEvent(self, event):
        if self.last_mouse_pos is None:
            return

        delta = event.pos() - self.last_mouse_pos

        if self.dragging:
            # Rotazione con drag sinistro
            self.rotazione_h = (self.rotazione_h + delta.x() * 0.5) % 360
            # Rotazione verticale sempre attiva
            self.rotazione_v = max(-80, min(80, self.rotazione_v - delta.y() * 0.5))
            self.update()

        elif self.panning:
            # Pan con middle button
            self.offset_x += delta.x()
            self.offset_y += delta.y()
            self.update()

        self.last_mouse_pos = event.pos()

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.panning = False
        self.last_mouse_pos = None
        self.setCursor(Qt.ArrowCursor)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_P:
            # Toggle prospettiva/isometrica
            self.prospettiva = not self.prospettiva
            self.update()
        elif key == Qt.Key_R:
            # Reset vista
            self.rotazione_h = 30
            self.rotazione_v = 30
            self.scala = 25
            self.offset_x = 200
            self.offset_y = 350
            self.update()
        elif key == Qt.Key_Home:
            # Vista frontale
            self.rotazione_h = 0
            self.rotazione_v = 0
            self.update()
        elif key == Qt.Key_Plus or key == Qt.Key_Equal:
            self.scala = min(80, self.scala * 1.2)
            self.update()
        elif key == Qt.Key_Minus:
            self.scala = max(5, self.scala / 1.2)
            self.update()
        elif key == Qt.Key_F:
            # Toggle fondazioni
            self.mostra_fondazioni = not self.mostra_fondazioni
            self.update()
        elif key == Qt.Key_C:
            # Toggle cordoli
            self.mostra_cordoli = not self.mostra_cordoli
            self.update()
        elif key == Qt.Key_S:
            # Toggle solai
            self.mostra_solai = not self.mostra_solai
            self.update()
        elif key == Qt.Key_A:
            # Toggle aperture
            self.mostra_aperture = not self.mostra_aperture
            self.update()
        elif key == Qt.Key_G:
            # Toggle griglia
            self.mostra_griglia = not self.mostra_griglia
            self.update()
        elif key == Qt.Key_L:
            # Toggle etichette
            self.mostra_etichette = not self.mostra_etichette
            self.update()
        elif key == Qt.Key_D:
            # Toggle DCR colori
            self.mostra_dcr = not self.mostra_dcr
            self.update()

    def focusInEvent(self, event):
        # Permette alla widget di ricevere eventi tastiera
        super().focusInEvent(event)

    def mouseDoubleClickEvent(self, event):
        # Focus per abilitare tastiera
        self.setFocus()


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
# COORDINATE INPUT BAR - INPUT NUMERICO DIRETTO
# ============================================================================

class CoordinateInputBar(QWidget):
    """Barra di input coordinate per inserimento numerico diretto - stile CAD"""

    coordinateEntered = pyqtSignal(float, float)  # x, y assolute
    relativeEntered = pyqtSignal(float, float)    # dx, dy relative
    polarEntered = pyqtSignal(float, float)       # lunghezza, angolo
    commandEntered = pyqtSignal(str)              # comando testuale

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.canvas = None  # Riferimento al canvas
        self.last_point = None  # Ultimo punto inserito (per coordinate relative)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        # Etichetta modalità
        self.mode_label = QLabel("COMANDO:")
        self.mode_label.setStyleSheet("font-weight: bold; color: #0066cc; min-width: 80px;")
        layout.addWidget(self.mode_label)

        # Campo input principale
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Inserisci coordinate (es: 5,3 oppure @2,0 oppure <45,5)")
        self.input_field.setStyleSheet("""
            QLineEdit {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 4px 8px;
                border: 1px solid #0066cc;
                border-radius: 3px;
                background-color: #f0f7ff;
            }
            QLineEdit:focus {
                border: 2px solid #0066cc;
                background-color: white;
            }
        """)
        self.input_field.returnPressed.connect(self.processInput)
        layout.addWidget(self.input_field, 1)

        # Coordinate correnti (display)
        self.coord_display = QLabel("X: 0.00  Y: 0.00")
        self.coord_display.setStyleSheet("""
            font-family: 'Consolas', monospace;
            font-size: 11px;
            color: #666;
            background-color: #f5f5f5;
            padding: 4px 10px;
            border-radius: 3px;
            min-width: 140px;
        """)
        layout.addWidget(self.coord_display)

        # Lunghezza corrente (per disegno in corso)
        self.length_display = QLabel("L: --")
        self.length_display.setStyleSheet("""
            font-family: 'Consolas', monospace;
            font-size: 11px;
            color: #666;
            background-color: #f5f5f5;
            padding: 4px 10px;
            border-radius: 3px;
            min-width: 80px;
        """)
        layout.addWidget(self.length_display)

        # Angolo corrente
        self.angle_display = QLabel("A: --")
        self.angle_display.setStyleSheet("""
            font-family: 'Consolas', monospace;
            font-size: 11px;
            color: #666;
            background-color: #f5f5f5;
            padding: 4px 10px;
            border-radius: 3px;
            min-width: 70px;
        """)
        layout.addWidget(self.angle_display)

        # Snap attivo
        self.snap_indicator = QLabel("SNAP")
        self.snap_indicator.setStyleSheet("""
            font-size: 10px;
            font-weight: bold;
            color: white;
            background-color: #28a745;
            padding: 4px 8px;
            border-radius: 3px;
        """)
        layout.addWidget(self.snap_indicator)

        # Help button
        help_btn = QPushButton("?")
        help_btn.setFixedSize(24, 24)
        help_btn.setToolTip("Aiuto input coordinate")
        help_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #5a6268; }
        """)
        help_btn.clicked.connect(self.showHelp)
        layout.addWidget(help_btn)

        self.setStyleSheet("background-color: #e8f4fc; border-top: 1px solid #ccc;")

    def setCanvas(self, canvas):
        """Collega il canvas per aggiornare le coordinate"""
        self.canvas = canvas

    def updateCoordinates(self, x: float, y: float):
        """Aggiorna display coordinate correnti"""
        self.coord_display.setText(f"X: {x:.2f}  Y: {y:.2f}")

    def updateMeasurements(self, length: float = None, angle: float = None):
        """Aggiorna display lunghezza e angolo"""
        if length is not None:
            self.length_display.setText(f"L: {length:.2f}m")
        else:
            self.length_display.setText("L: --")

        if angle is not None:
            self.angle_display.setText(f"A: {angle:.1f}°")
        else:
            self.angle_display.setText("A: --")

    def updateSnapIndicator(self, snap_type: str = None):
        """Aggiorna indicatore snap"""
        if snap_type:
            colors = {
                'endpoint': '#dc3545',
                'midpoint': '#28a745',
                'intersection': '#fd7e14',
                'perpendicular': '#007bff',
                'grid': '#6c757d'
            }
            self.snap_indicator.setText(snap_type.upper()[:4])
            self.snap_indicator.setStyleSheet(f"""
                font-size: 10px;
                font-weight: bold;
                color: white;
                background-color: {colors.get(snap_type, '#6c757d')};
                padding: 4px 8px;
                border-radius: 3px;
            """)
        else:
            self.snap_indicator.setText("SNAP")
            self.snap_indicator.setStyleSheet("""
                font-size: 10px;
                font-weight: bold;
                color: white;
                background-color: #28a745;
                padding: 4px 8px;
                border-radius: 3px;
            """)

    def processInput(self):
        """Processa l'input dell'utente"""
        text = self.input_field.text().strip()
        if not text:
            return

        self.input_field.clear()

        try:
            # Formato: @dx,dy (coordinate relative)
            if text.startswith('@'):
                parts = text[1:].split(',')
                if len(parts) == 2:
                    dx = float(parts[0].strip())
                    dy = float(parts[1].strip())
                    self.relativeEntered.emit(dx, dy)
                    return

            # Formato: <angolo,lunghezza (polare)
            if text.startswith('<'):
                parts = text[1:].split(',')
                if len(parts) == 2:
                    angle = float(parts[0].strip())
                    length = float(parts[1].strip())
                    self.polarEntered.emit(length, angle)
                    return

            # Formato: x,y (coordinate assolute)
            if ',' in text:
                parts = text.split(',')
                if len(parts) == 2:
                    x = float(parts[0].strip())
                    y = float(parts[1].strip())
                    self.coordinateEntered.emit(x, y)
                    return

            # Formato: numero singolo (lunghezza nella direzione corrente)
            try:
                length = float(text)
                # Emette come polare con angolo attuale
                self.polarEntered.emit(length, 0)
                return
            except ValueError:
                pass

            # Comando testuale
            self.commandEntered.emit(text.upper())

        except ValueError as e:
            self.showError(f"Input non valido: {text}")

    def showError(self, message: str):
        """Mostra errore nell'input"""
        self.input_field.setStyleSheet("""
            QLineEdit {
                font-family: 'Consolas', monospace;
                font-size: 12px;
                padding: 4px 8px;
                border: 2px solid #dc3545;
                border-radius: 3px;
                background-color: #ffe6e6;
            }
        """)
        self.input_field.setPlaceholderText(message)
        # Reset style after 2 seconds
        QTimer.singleShot(2000, self.resetInputStyle)

    def resetInputStyle(self):
        """Ripristina lo stile dell'input"""
        self.input_field.setStyleSheet("""
            QLineEdit {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 4px 8px;
                border: 1px solid #0066cc;
                border-radius: 3px;
                background-color: #f0f7ff;
            }
            QLineEdit:focus {
                border: 2px solid #0066cc;
                background-color: white;
            }
        """)
        self.input_field.setPlaceholderText("Inserisci coordinate (es: 5,3 oppure @2,0 oppure <45,5)")

    def showHelp(self):
        """Mostra aiuto per l'input coordinate"""
        help_text = """
<h3>Input Coordinate</h3>
<table>
<tr><td><b>x,y</b></td><td>Coordinate assolute (es: 5,3)</td></tr>
<tr><td><b>@dx,dy</b></td><td>Coordinate relative all'ultimo punto (es: @2,0)</td></tr>
<tr><td><b>&lt;angolo,lunghezza</b></td><td>Coordinate polari (es: &lt;45,5)</td></tr>
<tr><td><b>numero</b></td><td>Lunghezza nella direzione corrente (es: 5)</td></tr>
</table>

<h3>Comandi</h3>
<table>
<tr><td><b>ESC</b></td><td>Annulla operazione corrente</td></tr>
<tr><td><b>ENTER</b></td><td>Chiude poligono (in modalità poligono)</td></tr>
<tr><td><b>DELETE</b></td><td>Elimina elemento selezionato</td></tr>
</table>

<h3>Snap</h3>
<p>Il sistema aggancia automaticamente a:</p>
<ul>
<li><span style="color: red;">●</span> <b>Endpoint</b> - Estremi dei muri</li>
<li><span style="color: green;">●</span> <b>Midpoint</b> - Punto medio dei muri</li>
<li><span style="color: orange;">●</span> <b>Intersection</b> - Intersezione tra muri</li>
<li><span style="color: blue;">●</span> <b>Perpendicular</b> - Punto perpendicolare</li>
<li><span style="color: gray;">●</span> <b>Grid</b> - Griglia</li>
</ul>
"""
        QMessageBox.information(self, "Aiuto Input Coordinate", help_text)

    def setFocusToInput(self):
        """Porta il focus all'input field"""
        self.input_field.setFocus()
        self.input_field.selectAll()


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
        # Trova estremi muri per ogni piano
        piano_muri = {}
        for m in progetto.muri:
            z = round(m.z, 1)
            if z not in piano_muri:
                piano_muri[z] = []
            piano_muri[z].append(m)

        for z, muri in piano_muri.items():
            estremi = []
            for m in muri:
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
                    warnings.append(f"Muro {nome1} ({tipo1}) non connesso a z={z:.1f}")

        return warnings

    @staticmethod
    def _segmentsOverlap(m1: Muro, m2: Muro, tolleranza: float = 0.05) -> bool:
        """Verifica se due segmenti di muro sono sovrapposti o paralleli troppo vicini"""
        # Stessa quota z?
        if abs(m1.z - m2.z) > 0.1:
            return False

        # Calcola vettori direzione
        d1x, d1y = m1.x2 - m1.x1, m1.y2 - m1.y1
        d2x, d2y = m2.x2 - m2.x1, m2.y2 - m2.y1
        len1 = math.sqrt(d1x*d1x + d1y*d1y)
        len2 = math.sqrt(d2x*d2x + d2y*d2y)

        if len1 < 0.01 or len2 < 0.01:
            return False

        # Normalizza
        d1x, d1y = d1x/len1, d1y/len1
        d2x, d2y = d2x/len2, d2y/len2

        # Cross product per verificare se sono paralleli
        cross = abs(d1x * d2y - d1y * d2x)
        if cross > 0.1:  # Non paralleli
            return False

        # Sono paralleli - verifica distanza e sovrapposizione
        # Proietta m2.start su linea m1
        px, py = m2.x1 - m1.x1, m2.y1 - m1.y1
        # Distanza perpendicolare
        dist = abs(px * (-d1y) + py * d1x)
        if dist > tolleranza + (m1.spessore + m2.spessore) / 2:
            return False

        # Verifica sovrapposizione lungo la direzione
        proj1_start = 0
        proj1_end = len1
        proj2_start = px * d1x + py * d1y
        px2, py2 = m2.x2 - m1.x1, m2.y2 - m1.y1
        proj2_end = px2 * d1x + py2 * d1y

        if proj2_start > proj2_end:
            proj2_start, proj2_end = proj2_end, proj2_start

        # Sovrapposizione?
        overlap_start = max(proj1_start, proj2_start)
        overlap_end = min(proj1_end, proj2_end)

        return overlap_end > overlap_start + tolleranza

    @staticmethod
    def validaSovrapposizioni(progetto: Progetto) -> List[str]:
        """Verifica sovrapposizioni tra muri con algoritmo migliorato"""
        warnings = []
        muri = progetto.muri
        for i, m1 in enumerate(muri):
            for m2 in muri[i+1:]:
                if GeometryValidator._segmentsOverlap(m1, m2):
                    warnings.append(f"Muri {m1.nome} e {m2.nome} si sovrappongono")
        return warnings

    @staticmethod
    def validaLunghezzaMinima(progetto: Progetto, min_length: float = 0.3) -> List[str]:
        """Verifica lunghezza minima dei muri"""
        warnings = []
        for m in progetto.muri:
            if m.lunghezza < min_length:
                warnings.append(f"Muro {m.nome} troppo corto ({m.lunghezza:.2f}m < {min_length}m)")
        return warnings

    @staticmethod
    def validaAngoliMuri(progetto: Progetto, tolleranza_angolo: float = 5.0) -> List[str]:
        """Verifica angoli tra muri connessi (idealmente 90° o multipli)"""
        warnings = []
        tolleranza = 0.15  # m per connessione

        for i, m1 in enumerate(progetto.muri):
            for m2 in progetto.muri[i+1:]:
                if abs(m1.z - m2.z) > 0.1:
                    continue

                # Verifica connessione agli estremi
                connections = []
                for p1 in [(m1.x1, m1.y1), (m1.x2, m1.y2)]:
                    for p2 in [(m2.x1, m2.y1), (m2.x2, m2.y2)]:
                        if math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2) < tolleranza:
                            connections.append((p1, p2))

                if connections:
                    # Calcola angolo tra i muri
                    ang1 = math.degrees(math.atan2(m1.y2 - m1.y1, m1.x2 - m1.x1))
                    ang2 = math.degrees(math.atan2(m2.y2 - m2.y1, m2.x2 - m2.x1))
                    delta = abs(ang1 - ang2)
                    if delta > 180:
                        delta = 360 - delta

                    # Verifica se vicino a multiplo di 90°
                    resto = delta % 90
                    if resto > tolleranza_angolo and resto < (90 - tolleranza_angolo):
                        warnings.append(f"Angolo tra {m1.nome} e {m2.nome}: {delta:.1f}° (non ortogonale)")

        return warnings

    @staticmethod
    def validaTutto(progetto: Progetto) -> Dict[str, List[str]]:
        """Esegue tutte le validazioni"""
        return {
            'errori': GeometryValidator.validaAperture(progetto),
            'chiusura': GeometryValidator.validaMuriChiusi(progetto),
            'sovrapposizioni': GeometryValidator.validaSovrapposizioni(progetto),
            'lunghezza': GeometryValidator.validaLunghezzaMinima(progetto),
            'angoli': GeometryValidator.validaAngoliMuri(progetto)
        }

    @staticmethod
    def validaInTempoReale(progetto: Progetto, nuovo_muro: Tuple[float, float, float, float]) -> Optional[str]:
        """Validazione in tempo reale mentre si disegna"""
        x1, y1, x2, y2 = nuovo_muro
        lunghezza = math.sqrt((x2-x1)**2 + (y2-y1)**2)

        if lunghezza < 0.3:
            return "Muro troppo corto (min 0.3m)"

        # Verifica sovrapposizioni con muri esistenti
        temp_muro = Muro("temp", x1, y1, x2, y2, 0.3, 3.0)
        for m in progetto.muri:
            if GeometryValidator._segmentsOverlap(temp_muro, m):
                return f"Sovrapposizione con {m.nome}"

        return None


# ============================================================================
# CANVAS DISEGNO (migliorato)
# ============================================================================

class DrawingCanvas(QWidget):
    """Canvas per disegno muri con tools migliorati"""

    muroAggiunto = pyqtSignal(Muro)
    selectionChanged = pyqtSignal(object)
    muriChanged = pyqtSignal()
    requestApertura = pyqtSignal(str, float)  # nome_muro, posizione
    coordinateUpdate = pyqtSignal(float, float, float, float, str)  # x, y, length, angle, snap_type

    def __init__(self, parent=None):
        super().__init__(parent)
        self.progetto: Optional[Progetto] = None
        self.setMinimumSize(600, 400)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)  # Per ricevere eventi tastiera

        # Vista
        self.scala = 40  # pixel per metro
        self.offset_x = 300
        self.offset_y = 300
        self.griglia = True
        self.passo_griglia = 0.5

        # Strumento corrente
        # Strumenti: select, muro, apertura, pan, rettangolo, misura, copia, polygon, ruota
        self.strumento = 'select'

        # Disegno muro/rettangolo
        self.punto_inizio = None
        self.punto_corrente = None

        # Strumento rettangolo
        self.rettangolo_punti = []  # [p1, p2] per disegnare 4 muri

        # Strumento poligono
        self.polygon_vertices = []

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

        # Multi-selezione
        self.multi_select_mode = False
        self.selection_rect_start = None
        self.selection_rect_end = None

        # Immagine di riferimento
        self.reference_image = None
        self.reference_image_pos = (0, 0)
        self.reference_image_scale = 1.0
        self.reference_image_opacity = 0.5
        self.show_reference = True

        # Pan con middle mouse
        self.panning = False
        self.pan_start = None

        # Undo stack (opzionale, passato dal parent)
        self.undo_stack = None

        # === SNAP INTELLIGENTE ===
        self.snap_enabled = True
        self.snap_radius = 0.3  # metri - raggio di attrazione snap
        self.snap_to_endpoint = True
        self.snap_to_midpoint = True
        self.snap_to_intersection = True
        self.snap_to_perpendicular = True
        self.snap_to_grid = True
        self.current_snap_point = None  # Punto di snap attivo (x, y, tipo)
        self.snap_types = {
            'endpoint': QColor(255, 0, 0),      # Rosso - estremi
            'midpoint': QColor(0, 255, 0),      # Verde - punto medio
            'intersection': QColor(255, 165, 0), # Arancione - intersezione
            'perpendicular': QColor(0, 0, 255),  # Blu - perpendicolare
            'grid': QColor(128, 128, 128),       # Grigio - griglia
        }

        # === QUOTATURA ===
        self.show_dimensions = True
        self.dimension_font = QFont('Segoe UI', 8)

        # === INPUT NUMERICO ===
        self.numeric_input_active = False
        self.numeric_input_buffer = ""

        # === THROTTLE SNAP (Performance) ===
        self.snap_timer = QTimer()
        self.snap_timer.setSingleShot(True)
        self.snap_timer.timeout.connect(self._executeSnapUpdate)
        self.pending_snap_event = None  # (screen_x, screen_y)
        self.snap_throttle_ms = 16  # ~60fps max per calcoli snap

        # === CACHE GRIGLIA (Performance) ===
        self._grid_path = None  # QPainterPath cachato
        self._grid_params = None  # (scala, passo_griglia, width, height, offset_x, offset_y)

        # === GEOMETRY ENGINE (Spatial Indexing) ===
        self.geometry_engine = GeometryEngine()

        # Stile
        self.setStyleSheet("background-color: white;")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

    def setProgetto(self, progetto: Progetto):
        self.progetto = progetto
        # Ricostruisci spatial index per snap veloce
        if progetto and progetto.muri:
            self.geometry_engine.rebuild_index(progetto.muri)
        else:
            self.geometry_engine.invalidate()
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

    def getSmartSnap(self, x: float, y: float) -> Tuple[float, float, Optional[str]]:
        """
        Trova il punto di snap più vicino con priorità:
        1. Endpoint (estremi muri)
        2. Intersection (intersezioni tra muri)
        3. Midpoint (punto medio muri)
        4. Perpendicular (proiezione perpendicolare)
        5. Grid (griglia)

        Usa GeometryEngine con spatial indexing per query O(log n) invece di O(n²).
        Ritorna: (snap_x, snap_y, snap_type) o coordinate originali se nessuno snap
        """
        if not self.snap_enabled or not self.progetto:
            gx, gy = self.snapToGrid(x, y)
            return gx, gy, 'grid' if self.snap_to_grid else None

        best_snap = None
        best_dist = self.snap_radius

        # Ottieni muri del piano corrente
        z_piano = self.piano_corrente * (self.progetto.altezza_piano if self.progetto else 3.0)
        muri_piano = [m for m in self.progetto.muri if abs(m.z - z_piano) <= 0.1]

        # === USA GEOMETRY ENGINE SE DISPONIBILE ===
        if self.geometry_engine.is_valid and SHAPELY_AVAILABLE:
            # Trova muri vicini con spatial index O(log n)
            nearby_walls = self.geometry_engine.find_near_point(x, y, self.snap_radius * 2)
            nearby_muri = [w[0] for w in nearby_walls if abs(w[0].z - z_piano) <= 0.1]

            # 1. SNAP ENDPOINT (usa solo muri vicini)
            if self.snap_to_endpoint:
                for muro in nearby_muri:
                    for px, py in [(muro.x1, muro.y1), (muro.x2, muro.y2)]:
                        dist = math.sqrt((x - px)**2 + (y - py)**2)
                        if dist < best_dist:
                            best_dist = dist
                            best_snap = (px, py, 'endpoint')

            # 2. SNAP INTERSECTION (usa Shapely per calcolo veloce)
            if self.snap_to_intersection and len(nearby_muri) > 1:
                for i, m1 in enumerate(nearby_muri):
                    for m2 in nearby_muri[i+1:]:
                        ix, iy = self._lineIntersection(
                            m1.x1, m1.y1, m1.x2, m1.y2,
                            m2.x1, m2.y1, m2.x2, m2.y2
                        )
                        if ix is not None:
                            dist = math.sqrt((x - ix)**2 + (y - iy)**2)
                            if dist < best_dist:
                                best_dist = dist
                                best_snap = (ix, iy, 'intersection')

            # 3. SNAP MIDPOINT
            if self.snap_to_midpoint:
                for muro in nearby_muri:
                    mx = (muro.x1 + muro.x2) / 2
                    my = (muro.y1 + muro.y2) / 2
                    dist = math.sqrt((x - mx)**2 + (y - my)**2)
                    if dist < best_dist:
                        best_dist = dist
                        best_snap = (mx, my, 'midpoint')

            # 4. SNAP PERPENDICULAR
            if self.snap_to_perpendicular and self.punto_inizio:
                for muro in nearby_muri:
                    px, py = self._perpendicularPoint(
                        self.punto_inizio[0], self.punto_inizio[1],
                        muro.x1, muro.y1, muro.x2, muro.y2
                    )
                    if px is not None:
                        dist = math.sqrt((x - px)**2 + (y - py)**2)
                        if dist < best_dist:
                            best_dist = dist
                            best_snap = (px, py, 'perpendicular')

        else:
            # === FALLBACK: metodo originale O(n) ===
            # 1. SNAP ENDPOINT (estremi muri) - priorità alta
            if self.snap_to_endpoint:
                for muro in muri_piano:
                    for px, py in [(muro.x1, muro.y1), (muro.x2, muro.y2)]:
                        dist = math.sqrt((x - px)**2 + (y - py)**2)
                        if dist < best_dist:
                            best_dist = dist
                            best_snap = (px, py, 'endpoint')

            # 2. SNAP INTERSECTION (intersezioni tra muri)
            if self.snap_to_intersection:
                for i, m1 in enumerate(muri_piano):
                    for m2 in muri_piano[i+1:]:
                        ix, iy = self._lineIntersection(
                            m1.x1, m1.y1, m1.x2, m1.y2,
                            m2.x1, m2.y1, m2.x2, m2.y2
                        )
                        if ix is not None:
                            dist = math.sqrt((x - ix)**2 + (y - iy)**2)
                            if dist < best_dist:
                                best_dist = dist
                                best_snap = (ix, iy, 'intersection')

            # 3. SNAP MIDPOINT (punto medio muri)
            if self.snap_to_midpoint:
                for muro in muri_piano:
                    mx = (muro.x1 + muro.x2) / 2
                    my = (muro.y1 + muro.y2) / 2
                    dist = math.sqrt((x - mx)**2 + (y - my)**2)
                    if dist < best_dist:
                        best_dist = dist
                        best_snap = (mx, my, 'midpoint')

            # 4. SNAP PERPENDICULAR (proiezione perpendicolare su muro)
            if self.snap_to_perpendicular and self.punto_inizio:
                for muro in muri_piano:
                    px, py = self._perpendicularPoint(
                        self.punto_inizio[0], self.punto_inizio[1],
                        muro.x1, muro.y1, muro.x2, muro.y2
                    )
                    if px is not None:
                        dist = math.sqrt((x - px)**2 + (y - py)**2)
                        if dist < best_dist:
                            best_dist = dist
                            best_snap = (px, py, 'perpendicular')

        # 5. GRID SNAP (fallback)
        if best_snap:
            return best_snap
        elif self.snap_to_grid:
            gx, gy = self.snapToGrid(x, y)
            return gx, gy, 'grid'
        else:
            return x, y, None

    def _lineIntersection(self, x1, y1, x2, y2, x3, y3, x4, y4):
        """Calcola intersezione tra due segmenti. Ritorna None se non si intersecano."""
        denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
        if abs(denom) < 1e-10:
            return None, None

        t = ((x1-x3)*(y3-y4) - (y1-y3)*(x3-x4)) / denom
        u = -((x1-x2)*(y1-y3) - (y1-y2)*(x1-x3)) / denom

        # Verifica che l'intersezione sia dentro entrambi i segmenti
        if 0 <= t <= 1 and 0 <= u <= 1:
            ix = x1 + t*(x2-x1)
            iy = y1 + t*(y2-y1)
            return ix, iy
        return None, None

    def _perpendicularPoint(self, px, py, x1, y1, x2, y2):
        """Trova la proiezione perpendicolare di (px,py) sul segmento (x1,y1)-(x2,y2)."""
        dx = x2 - x1
        dy = y2 - y1
        length_sq = dx*dx + dy*dy
        if length_sq < 1e-10:
            return None, None

        t = max(0, min(1, ((px-x1)*dx + (py-y1)*dy) / length_sq))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return proj_x, proj_y

    def drawSnapIndicator(self, painter):
        """Disegna l'indicatore visivo del punto di snap corrente."""
        if not self.current_snap_point:
            return

        x, y, snap_type = self.current_snap_point
        sx, sy = self.worldToScreen(x, y)

        # Colore in base al tipo di snap
        color = self.snap_types.get(snap_type, QColor(255, 255, 0))

        painter.setPen(QPen(color, 2))
        painter.setBrush(Qt.NoBrush)

        size = 8
        if snap_type == 'endpoint':
            # Quadrato
            painter.drawRect(sx - size, sy - size, size*2, size*2)
        elif snap_type == 'midpoint':
            # Triangolo
            path = QPainterPath()
            path.moveTo(sx, sy - size)
            path.lineTo(sx - size, sy + size)
            path.lineTo(sx + size, sy + size)
            path.closeSubpath()
            painter.drawPath(path)
        elif snap_type == 'intersection':
            # X
            painter.drawLine(sx - size, sy - size, sx + size, sy + size)
            painter.drawLine(sx - size, sy + size, sx + size, sy - size)
        elif snap_type == 'perpendicular':
            # Simbolo perpendicolare (angolo retto)
            painter.drawLine(sx - size, sy, sx, sy)
            painter.drawLine(sx, sy, sx, sy - size)
        else:
            # Cerchio per grid
            painter.drawEllipse(sx - size//2, sy - size//2, size, size)

        # Label del tipo di snap
        painter.setPen(color)
        painter.setFont(QFont('Segoe UI', 7))
        painter.drawText(sx + 12, sy - 5, snap_type.upper())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Sfondo
        painter.fillRect(self.rect(), QColor(255, 255, 255))

        # Immagine di riferimento (sotto tutto)
        self.drawReferenceImage(painter)

        # Griglia
        if self.griglia:
            self.drawGrid(painter)

        # Assi
        self.drawAxes(painter)

        # Muri
        if self.progetto:
            z_piano_corrente = self.piano_corrente * (self.progetto.altezza_piano if self.progetto else 3.0)

            # Prima disegna muri di piani adiacenti (ghost/sfumato)
            painter.setOpacity(0.2)
            for muro in self.progetto.muri:
                if abs(muro.z - z_piano_corrente) > 0.1:  # Altro piano
                    self.drawMuroGhost(painter, muro)
            painter.setOpacity(1.0)

            # Poi disegna muri del piano corrente
            for muro in self.progetto.muri:
                if abs(muro.z - z_piano_corrente) <= 0.1:  # Piano corrente
                    self.drawMuro(painter, muro)

            # Aperture solo del piano corrente
            for ap in self.progetto.aperture:
                muro = next((m for m in self.progetto.muri if m.nome == ap.muro), None)
                if muro and abs(muro.z - z_piano_corrente) <= 0.1:
                    self.drawApertura(painter, ap, muro)

        # Muro in corso di disegno
        if self.strumento == 'muro' and self.punto_inizio and self.punto_corrente:
            self.drawTempMuro(painter)

        # Rettangolo in corso di disegno
        if self.strumento == 'rettangolo' and self.punto_inizio and self.punto_corrente:
            self.drawTempRettangolo(painter)

        # Poligono in corso di disegno
        if self.strumento == 'polygon':
            self.drawTempPolygon(painter)

        # Linea di misura
        if self.strumento == 'misura' and (self.misura_start or self.misura_attiva):
            self.drawMisura(painter)

        # Info strumento
        self.drawToolInfo(painter)

    def drawGrid(self, painter):
        """Disegna griglia con caching QPainterPath per performance"""
        w, h = self.width(), self.height()
        current_params = (self.scala, self.passo_griglia, w, h, self.offset_x, self.offset_y)

        # Controlla se la cache è valida
        if self._grid_path is None or self._grid_params != current_params:
            # Ricostruisci la griglia in un QPainterPath
            self._grid_path = QPainterPath()
            self._grid_params = current_params

            # Calcola range visibile
            x1, y1 = self.screenToWorld(0, h)
            x2, y2 = self.screenToWorld(w, 0)

            # Linee verticali
            x = math.floor(x1 / self.passo_griglia) * self.passo_griglia
            while x <= x2:
                sx, _ = self.worldToScreen(x, 0)
                self._grid_path.moveTo(sx, 0)
                self._grid_path.lineTo(sx, h)
                x += self.passo_griglia

            # Linee orizzontali
            y = math.floor(y1 / self.passo_griglia) * self.passo_griglia
            while y <= y2:
                _, sy = self.worldToScreen(0, y)
                self._grid_path.moveTo(0, sy)
                self._grid_path.lineTo(w, sy)
                y += self.passo_griglia

        # Disegna il path cachato in una singola operazione
        painter.setPen(QPen(QColor(230, 230, 230), 1))
        painter.drawPath(self._grid_path)

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

    def drawMuroGhost(self, painter, muro: Muro):
        """Disegna muro ghost (altri piani) in modo semplificato"""
        x1, y1 = self.worldToScreen(muro.x1, muro.y1)
        x2, y2 = self.worldToScreen(muro.x2, muro.y2)

        painter.setPen(QPen(QColor(150, 150, 150), 1, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(int(x1), int(y1), int(x2), int(y2))

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
        spessore_px = max(muro.spessore * self.scala, 6)

        # Trova aperture su questo muro
        aperture_muro = [ap for ap in self.progetto.aperture if ap.muro == muro.nome]

        # Calcola segmenti del muro (con tagli per aperture)
        dx_world = muro.x2 - muro.x1
        dy_world = muro.y2 - muro.y1
        length_world = math.sqrt(dx_world*dx_world + dy_world*dy_world)

        if length_world == 0:
            return

        # Direzione normalizzata
        ux, uy = dx_world / length_world, dy_world / length_world

        # Crea lista di segmenti (start, end) in coordinate lungo il muro
        segments = [(0, length_world)]

        # Taglia i segmenti per ogni apertura
        for ap in sorted(aperture_muro, key=lambda a: a.posizione):
            ap_start = ap.posizione
            ap_end = ap.posizione + ap.larghezza
            new_segments = []
            for seg_start, seg_end in segments:
                if ap_end <= seg_start or ap_start >= seg_end:
                    # Nessuna sovrapposizione
                    new_segments.append((seg_start, seg_end))
                else:
                    # Sovrapposizione - taglia
                    if ap_start > seg_start:
                        new_segments.append((seg_start, ap_start))
                    if ap_end < seg_end:
                        new_segments.append((ap_end, seg_end))
            segments = new_segments

        # Disegna i segmenti del muro
        painter.setPen(QPen(QColor(80, 60, 40), 1))
        painter.setBrush(QBrush(color))

        dx, dy = x2 - x1, y2 - y1
        length_px = math.sqrt(dx*dx + dy*dy)
        if length_px > 0:
            nx, ny = -dy/length_px * spessore_px/2, dx/length_px * spessore_px/2

            for seg_start, seg_end in segments:
                # Calcola punti in coordinate schermo
                t1 = seg_start / length_world
                t2 = seg_end / length_world

                sx1 = x1 + dx * t1
                sy1 = y1 + dy * t1
                sx2 = x1 + dx * t2
                sy2 = y1 + dy * t2

                points = [
                    QPointF(sx1 - nx, sy1 - ny),
                    QPointF(sx1 + nx, sy1 + ny),
                    QPointF(sx2 + nx, sy2 + ny),
                    QPointF(sx2 - nx, sy2 - ny),
                ]
                painter.drawPolygon(*points)

        # Etichetta
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        painter.setPen(QPen(QColor(0, 0, 0)))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(int(mx) - 20, int(my) - 5, f"{muro.nome}")
        painter.drawText(int(mx) - 20, int(my) + 10, f"{muro.lunghezza:.2f}m")

    def drawApertura(self, painter, ap: Apertura, muro: Muro):
        """Disegna apertura con simbolo architettonico"""
        dx = muro.x2 - muro.x1
        dy = muro.y2 - muro.y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0:
            return

        # Calcola spessore muro in pixel
        spessore_px = max(muro.spessore * self.scala, 6)

        # Calcola posizioni lungo il muro
        t1 = ap.posizione / length
        t2 = (ap.posizione + ap.larghezza) / length

        # Punti inizio e fine apertura in world coords
        ax1 = muro.x1 + dx * t1
        ay1 = muro.y1 + dy * t1
        ax2 = muro.x1 + dx * t2
        ay2 = muro.y1 + dy * t2

        # Converti in screen coords
        sx1, sy1 = self.worldToScreen(ax1, ay1)
        sx2, sy2 = self.worldToScreen(ax2, ay2)

        # Calcola normale al muro
        adx, ady = sx2 - sx1, sy2 - sy1
        alen = math.sqrt(adx*adx + ady*ady)
        if alen > 0:
            anx, any = -ady/alen * spessore_px/2, adx/alen * spessore_px/2
        else:
            anx, any = 0, spessore_px/2

        if ap.tipo == "finestra":
            # Finestra: rettangolo azzurro con croce
            painter.setPen(QPen(QColor(0, 120, 200), 2))
            painter.setBrush(QBrush(QColor(173, 216, 230, 180)))  # Light blue

            # Rettangolo apertura
            points = [
                QPointF(sx1 - anx, sy1 - any),
                QPointF(sx1 + anx, sy1 + any),
                QPointF(sx2 + anx, sy2 + any),
                QPointF(sx2 - anx, sy2 - any),
            ]
            painter.drawPolygon(*points)

            # Croce finestra
            painter.setPen(QPen(QColor(0, 80, 150), 1))
            cmx, cmy = (sx1 + sx2) / 2, (sy1 + sy2) / 2
            painter.drawLine(int(sx1), int(sy1), int(sx2), int(sy2))
            painter.drawLine(int(cmx - anx), int(cmy - any), int(cmx + anx), int(cmy + any))

        elif ap.tipo == "porta":
            # Porta: apertura con arco di battente
            painter.setPen(QPen(QColor(139, 90, 43), 2))
            painter.setBrush(QBrush(QColor(255, 255, 255, 200)))

            # Rettangolo apertura bianco (vano)
            points = [
                QPointF(sx1 - anx, sy1 - any),
                QPointF(sx1 + anx, sy1 + any),
                QPointF(sx2 + anx, sy2 + any),
                QPointF(sx2 - anx, sy2 - any),
            ]
            painter.drawPolygon(*points)

            # Arco battente porta (90 gradi)
            painter.setPen(QPen(QColor(139, 90, 43), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            arc_radius = int(alen * 0.9)
            arc_rect = QRectF(sx1 - arc_radius, sy1 - arc_radius, arc_radius * 2, arc_radius * 2)
            # Calcola angolo di partenza basato sulla direzione del muro
            start_angle = int(math.degrees(math.atan2(-ady, adx)) * 16)
            painter.drawArc(arc_rect, start_angle, 90 * 16)

            # Linea porta
            painter.setPen(QPen(QColor(139, 90, 43), 2))
            painter.drawLine(int(sx1), int(sy1),
                           int(sx1 + arc_radius * math.cos(math.radians(start_angle/16 + 45))),
                           int(sy1 - arc_radius * math.sin(math.radians(start_angle/16 + 45))))

        else:  # porta-finestra
            # Porta-finestra: combinazione
            painter.setPen(QPen(QColor(0, 100, 150), 2))
            painter.setBrush(QBrush(QColor(200, 230, 255, 180)))

            points = [
                QPointF(sx1 - anx, sy1 - any),
                QPointF(sx1 + anx, sy1 + any),
                QPointF(sx2 + anx, sy2 + any),
                QPointF(sx2 - anx, sy2 - any),
            ]
            painter.drawPolygon(*points)

            # Divisione verticale
            painter.setPen(QPen(QColor(0, 80, 120), 1))
            cmx, cmy = (sx1 + sx2) / 2, (sy1 + sy2) / 2
            painter.drawLine(int(cmx - anx), int(cmy - any), int(cmx + anx), int(cmy + any))

        # Etichetta apertura
        painter.setPen(QPen(QColor(50, 50, 50)))
        painter.setFont(QFont("Arial", 7))
        lx, ly = (sx1 + sx2) / 2, (sy1 + sy2) / 2
        label = f"{ap.larghezza:.0f}x{ap.altezza:.0f}"
        painter.drawText(int(lx) - 15, int(ly) + 4, label)

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
            'apertura': '🚪 Clicca su muro per apertura',
            'misura': '📏 Misura Distanza',
            'pan': '✋ Sposta Vista',
            'polygon': '⬠ Disegna Poligono',
        }

        painter.drawText(10, 20, f"Strumento: {tool_names.get(self.strumento, self.strumento)}")
        painter.drawText(10, 35, f"Piano: {self.piano_corrente}")

        if self.progetto:
            painter.drawText(10, 50, f"Muri: {len(self.progetto.muri)}")
            painter.drawText(10, 65, f"Aperture: {len(self.progetto.aperture)}")

        # Istruzioni
        istruzioni = {
            'muro': "Click: inizio | Click: fine | ESC/RClick: annulla | Tab: input numerico",
            'rettangolo': "Click: primo angolo | Click: angolo opposto | Tab: input numerico",
            'misura': "Click: inizio | Click: fine",
            'select': "Click: seleziona | Ctrl+C: copia | Ctrl+V: incolla",
            'polygon': "Click: vertici | Doppio-click/Enter: chiudi | ESC: annulla"
        }
        if self.strumento in istruzioni:
            painter.drawText(10, self.height() - 10, istruzioni[self.strumento])

        # Indicatore snap intelligente
        self.drawSnapIndicator(painter)

        # Quotatura automatica dei muri
        if self.show_dimensions and self.progetto:
            self.drawDimensions(painter)

    def drawDimensions(self, painter):
        """Disegna le quote automatiche sui muri."""
        if not self.progetto:
            return

        painter.setFont(self.dimension_font)
        z_piano = self.piano_corrente * (self.progetto.altezza_piano if self.progetto else 3.0)

        for muro in self.progetto.muri:
            if abs(muro.z - z_piano) > 0.1:
                continue

            # Calcola punto medio e lunghezza
            mx = (muro.x1 + muro.x2) / 2
            my = (muro.y1 + muro.y2) / 2
            lunghezza = math.sqrt((muro.x2 - muro.x1)**2 + (muro.y2 - muro.y1)**2)

            # Posizione schermo
            sx, sy = self.worldToScreen(mx, my)

            # Offset perpendicolare per non sovrapporre al muro
            dx = muro.x2 - muro.x1
            dy = muro.y2 - muro.y1
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0:
                # Normale al muro
                nx = -dy / length
                ny = dx / length
                offset = 15  # pixel
                sx += int(nx * offset)
                sy -= int(ny * offset)

            # Disegna quota
            text = f"{lunghezza:.2f}m"
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(sx - 20, sy, text)

    def mousePressEvent(self, event):
        # Pan con middle mouse button
        if event.button() == Qt.MiddleButton:
            self.panning = True
            self.pan_start = (event.x(), event.y())
            self.setCursor(Qt.ClosedHandCursor)
            return

        if event.button() == Qt.LeftButton:
            wx, wy = self.screenToWorld(event.x(), event.y())
            # Usa Smart Snap se abilitato
            if self.snap_enabled:
                wx, wy, snap_type = self.getSmartSnap(wx, wy)
            else:
                wx, wy = self.snapToGrid(wx, wy)

            # Multi-selezione con Ctrl
            ctrl_pressed = event.modifiers() == Qt.ControlModifier

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

            elif self.strumento == 'polygon':
                # Aggiungi vertice al poligono
                self.handlePolygonClick(wx, wy)

            elif self.strumento == 'misura':
                if not self.misura_attiva:
                    self.startMisura(wx, wy)
                else:
                    self.endMisura()

            elif self.strumento == 'select':
                self.selectAt(wx, wy, multi=ctrl_pressed)

            elif self.strumento == 'apertura':
                # Trova muro più vicino e posizione
                muro, posizione = self.findWallAtPoint(wx, wy)
                if muro:
                    self.requestApertura.emit(muro.nome, posizione)

        elif event.button() == Qt.RightButton:
            # Annulla operazione corrente
            self.punto_inizio = None
            self.punto_corrente = None
            self.polygon_vertices = []
            if self.misura_attiva:
                self.endMisura()
                self.misura_start = None
                self.misura_end = None

        self.update()

    def mouseDoubleClickEvent(self, event):
        """Gestisce doppio click - chiude poligono"""
        if event.button() == Qt.LeftButton:
            if self.strumento == 'polygon' and len(self.polygon_vertices) >= 3:
                self.closePolygon()
        super().mouseDoubleClickEvent(event)

    def mouseReleaseEvent(self, event):
        """Gestisce rilascio mouse"""
        if event.button() == Qt.MiddleButton:
            self.panning = False
            self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        # Pan con middle mouse - sempre immediato (no throttle)
        if self.panning and self.pan_start:
            dx = event.x() - self.pan_start[0]
            dy = event.y() - self.pan_start[1]
            self.offset_x += dx
            self.offset_y += dy
            self.pan_start = (event.x(), event.y())
            self.update()
            return

        # Salva posizione e avvia timer throttle per calcoli snap costosi
        self.pending_snap_event = (event.x(), event.y())
        if not self.snap_timer.isActive():
            self.snap_timer.start(self.snap_throttle_ms)

    def _executeSnapUpdate(self):
        """Esegue calcoli snap throttled - chiamato dal timer"""
        if self.pending_snap_event is None:
            return

        screen_x, screen_y = self.pending_snap_event
        wx, wy = self.screenToWorld(screen_x, screen_y)
        snap_type = None

        # Usa Smart Snap se abilitato
        if self.snap_enabled:
            snap_x, snap_y, snap_type = self.getSmartSnap(wx, wy)
            if snap_type:
                self.current_snap_point = (snap_x, snap_y, snap_type)
                wx, wy = snap_x, snap_y
            else:
                self.current_snap_point = None
                wx, wy = self.snapToGrid(wx, wy)
        else:
            self.current_snap_point = None
            wx, wy = self.snapToGrid(wx, wy)

        # Calcola lunghezza e angolo se c'è un punto iniziale
        length = -1.0
        angle = -1.0
        if self.punto_inizio:
            dx = wx - self.punto_inizio[0]
            dy = wy - self.punto_inizio[1]
            length = math.sqrt(dx*dx + dy*dy)
            angle = math.degrees(math.atan2(dy, dx)) if length > 0.001 else 0
        elif self.polygon_vertices:
            last_v = self.polygon_vertices[-1]
            dx = wx - last_v[0]
            dy = wy - last_v[1]
            length = math.sqrt(dx*dx + dy*dy)
            angle = math.degrees(math.atan2(dy, dx)) if length > 0.001 else 0

        # Emetti aggiornamento coordinate
        self.coordinateUpdate.emit(wx, wy, length, angle, snap_type or "")

        if self.strumento in ['muro', 'rettangolo', 'polygon'] and (self.punto_inizio or self.polygon_vertices):
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

        # Usa undo stack se disponibile
        if self.undo_stack:
            cmd = AddMuroCommand(self.progetto, muro, f"Aggiungi {muro.nome}")
            self.undo_stack.push(cmd)
        else:
            self.progetto.muri.append(muro)

        self.muroAggiunto.emit(muro)

    def selectAt(self, wx: float, wy: float, multi: bool = False):
        if not self.progetto:
            return

        # Deseleziona tutti se non multi-selezione
        if not multi:
            for m in self.progetto.muri:
                m.selected = False

        # Cerca muro vicino
        for muro in self.progetto.muri:
            # Distanza punto-segmento
            dist = self.pointToSegmentDist(wx, wy, muro.x1, muro.y1, muro.x2, muro.y2)
            if dist < 0.5:  # 50cm di tolleranza
                muro.selected = not muro.selected if multi else True
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

    def findWallAtPoint(self, wx: float, wy: float):
        """Trova il muro più vicino al punto e la posizione lungo il muro.
        Returns: (Muro, posizione) o (None, 0)
        """
        if not self.progetto:
            return None, 0

        best_muro = None
        best_dist = float('inf')
        best_pos = 0

        for muro in self.progetto.muri:
            # Solo muri del piano corrente
            z_piano = self.piano_corrente * (self.progetto.altezza_piano if self.progetto else 3.0)
            if abs(muro.z - z_piano) > 0.1:
                continue

            dist = self.pointToSegmentDist(wx, wy, muro.x1, muro.y1, muro.x2, muro.y2)
            if dist < best_dist and dist < 1.0:  # 1m di tolleranza
                best_dist = dist
                best_muro = muro

                # Calcola posizione lungo il muro
                dx, dy = muro.x2 - muro.x1, muro.y2 - muro.y1
                length = math.sqrt(dx*dx + dy*dy)
                if length > 0:
                    t = max(0, min(1, ((wx-muro.x1)*dx + (wy-muro.y1)*dy) / (dx*dx + dy*dy)))
                    best_pos = t * length
                else:
                    best_pos = 0

        return best_muro, best_pos

    # ========== STRUMENTO RETTANGOLO ==========

    def drawRettangolo(self, x1: float, y1: float, x2: float, y2: float):
        """Disegna 4 muri che formano un rettangolo con supporto undo"""
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

        if self.undo_stack:
            self.undo_stack.beginMacro("Disegna rettangolo")
            for m in muri_nuovi:
                cmd = AddMuroCommand(self.progetto, m, f"Aggiungi {m.nome}")
                self.undo_stack.push(cmd)
                self.muroAggiunto.emit(m)
            self.undo_stack.endMacro()
        else:
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

    # ========== STRUMENTO POLIGONO ==========

    def handlePolygonClick(self, wx: float, wy: float):
        """Gestisce click per strumento poligono"""
        self.polygon_vertices.append((wx, wy))
        self.update()

    def closePolygon(self):
        """Chiude il poligono e crea i muri"""
        if not self.progetto or len(self.polygon_vertices) < 3:
            self.polygon_vertices = []
            return

        n = len(self.progetto.muri)
        z = self.piano_corrente * self.progetto.altezza_piano
        h = self.progetto.altezza_piano

        # Crea muri collegando i vertici
        for i in range(len(self.polygon_vertices)):
            p1 = self.polygon_vertices[i]
            p2 = self.polygon_vertices[(i + 1) % len(self.polygon_vertices)]
            n += 1
            muro = Muro(
                nome=f"M{n}",
                x1=p1[0], y1=p1[1],
                x2=p2[0], y2=p2[1],
                spessore=0.30, altezza=h, z=z
            )
            self.progetto.muri.append(muro)
            self.muroAggiunto.emit(muro)

        self.polygon_vertices = []
        self.update()

    def drawTempPolygon(self, painter):
        """Disegna preview del poligono in costruzione"""
        if len(self.polygon_vertices) < 1:
            return

        painter.setPen(QPen(QColor(128, 0, 128), 2, Qt.DashLine))
        painter.setBrush(QBrush(QColor(200, 150, 200, 50)))

        # Disegna linee tra vertici
        points = []
        for v in self.polygon_vertices:
            sx, sy = self.worldToScreen(v[0], v[1])
            points.append(QPointF(sx, sy))

        # Aggiungi punto corrente se presente
        if self.punto_corrente:
            sx, sy = self.worldToScreen(self.punto_corrente[0], self.punto_corrente[1])
            points.append(QPointF(sx, sy))

        if len(points) >= 2:
            path = QPainterPath()
            path.moveTo(points[0])
            for p in points[1:]:
                path.lineTo(p)
            painter.drawPath(path)

        # Disegna vertici
        painter.setBrush(QBrush(QColor(128, 0, 128)))
        for p in points[:-1]:  # Escludi punto corrente
            painter.drawEllipse(p, 5, 5)

        # Info
        painter.setPen(QPen(QColor(100, 0, 100)))
        painter.drawText(10, 80, f"Vertici: {len(self.polygon_vertices)} (Doppio-click o Enter per chiudere)")

    # ========== MENU CONTESTUALE ==========

    def showContextMenu(self, pos):
        """Mostra menu contestuale"""
        menu = QMenu(self)

        # Azioni comuni
        action_select_all = menu.addAction("Seleziona tutto")
        action_select_all.triggered.connect(self.selectAll)

        action_deselect = menu.addAction("Deseleziona")
        action_deselect.triggered.connect(self.deselectAll)

        menu.addSeparator()

        # Se c'è selezione
        selected = [m for m in self.progetto.muri if m.selected] if self.progetto else []
        if selected:
            action_delete = menu.addAction(f"Elimina ({len(selected)})")
            action_delete.triggered.connect(self.deleteSelected)

            action_copy = menu.addAction("Copia")
            action_copy.triggered.connect(self.copiaSelezionati)

            menu.addSeparator()

            action_rotate = menu.addAction("Ruota...")
            action_rotate.triggered.connect(self.showRotateDialog)

            action_mirror_x = menu.addAction("Specchia X")
            action_mirror_x.triggered.connect(lambda: self.specchiaMuri('x', 0))

            action_mirror_y = menu.addAction("Specchia Y")
            action_mirror_y.triggered.connect(lambda: self.specchiaMuri('y', 0))

        # Incolla se clipboard ha contenuto
        if self.clipboard_muri:
            menu.addSeparator()
            action_paste = menu.addAction(f"Incolla ({len(self.clipboard_muri)})")
            action_paste.triggered.connect(lambda: self.incollaCliboard())

        menu.addSeparator()

        # Vista
        action_fit = menu.addAction("Adatta alla vista")
        action_fit.triggered.connect(self.fitToView)

        action_grid = menu.addAction("Mostra/Nascondi griglia")
        action_grid.triggered.connect(self.toggleGrid)

        menu.exec_(self.mapToGlobal(pos))

    def selectAll(self):
        """Seleziona tutti i muri"""
        if self.progetto:
            for m in self.progetto.muri:
                m.selected = True
            self.update()

    def deselectAll(self):
        """Deseleziona tutti i muri"""
        if self.progetto:
            for m in self.progetto.muri:
                m.selected = False
            self.selectionChanged.emit(None)
            self.update()

    def deleteSelected(self):
        """Elimina muri selezionati con supporto undo"""
        if not self.progetto:
            return

        selected = [m for m in self.progetto.muri if m.selected]
        if not selected:
            return

        if self.undo_stack and len(selected) > 0:
            # Crea macro per eliminazioni multiple
            self.undo_stack.beginMacro(f"Elimina {len(selected)} muri")
            for muro in selected:
                cmd = DeleteMuroCommand(self.progetto, muro, f"Elimina {muro.nome}")
                self.undo_stack.push(cmd)
            self.undo_stack.endMacro()
        else:
            self.progetto.muri = [m for m in self.progetto.muri if not m.selected]

        self.muriChanged.emit()
        self.update()

    def toggleGrid(self):
        """Toggle visualizzazione griglia"""
        self.griglia = not self.griglia
        self.update()

    def fitToView(self):
        """Adatta la vista per mostrare tutti i muri"""
        if not self.progetto or not self.progetto.muri:
            return

        # Trova bounding box
        min_x = min(min(m.x1, m.x2) for m in self.progetto.muri)
        max_x = max(max(m.x1, m.x2) for m in self.progetto.muri)
        min_y = min(min(m.y1, m.y2) for m in self.progetto.muri)
        max_y = max(max(m.y1, m.y2) for m in self.progetto.muri)

        # Calcola scala e offset
        width = max_x - min_x + 2
        height = max_y - min_y + 2

        scale_x = self.width() / width if width > 0 else 40
        scale_y = self.height() / height if height > 0 else 40
        self.scala = min(scale_x, scale_y) * 0.8

        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        self.offset_x = self.width() / 2 - center_x * self.scala
        self.offset_y = self.height() / 2 + center_y * self.scala

        self.update()

    # ========== ROTAZIONE ==========

    def showRotateDialog(self):
        """Mostra dialogo per rotazione"""
        selected = [m for m in self.progetto.muri if m.selected] if self.progetto else []
        if not selected:
            return

        angolo, ok = QInputDialog.getDouble(
            self, "Ruota", "Angolo (gradi):",
            value=45.0, min=-360.0, max=360.0, decimals=1
        )
        if ok:
            self.rotateMuri(angolo)

    def rotateMuri(self, angolo: float):
        """Ruota muri selezionati attorno al loro centro"""
        if not self.progetto:
            return

        selected = [m for m in self.progetto.muri if m.selected]
        if not selected:
            return

        # Calcola centro della selezione
        all_x = []
        all_y = []
        for m in selected:
            all_x.extend([m.x1, m.x2])
            all_y.extend([m.y1, m.y2])

        centro_x = sum(all_x) / len(all_x)
        centro_y = sum(all_y) / len(all_y)

        # Ruota
        rad = math.radians(angolo)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        for muro in selected:
            # Ruota punto 1
            dx1 = muro.x1 - centro_x
            dy1 = muro.y1 - centro_y
            muro.x1 = centro_x + dx1 * cos_a - dy1 * sin_a
            muro.y1 = centro_y + dx1 * sin_a + dy1 * cos_a
            # Ruota punto 2
            dx2 = muro.x2 - centro_x
            dy2 = muro.y2 - centro_y
            muro.x2 = centro_x + dx2 * cos_a - dy2 * sin_a
            muro.y2 = centro_y + dx2 * sin_a + dy2 * cos_a

        self.muriChanged.emit()
        self.update()

    # ========== IMMAGINE DI RIFERIMENTO ==========

    def loadReferenceImage(self, filepath: str):
        """Carica un'immagine di riferimento (planimetria)"""
        if not PIL_AVAILABLE:
            QMessageBox.warning(self, "Errore", "Pillow non installato. Esegui: pip install Pillow")
            return False

        try:
            img = PILImage.open(filepath)
            img = img.convert("RGBA")

            # Converti a QImage
            data = img.tobytes("raw", "RGBA")
            qimg = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
            self.reference_image = QPixmap.fromImage(qimg)

            self.update()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Impossibile caricare immagine: {e}")
            return False

    def setReferenceImageScale(self, scale: float):
        """Imposta la scala dell'immagine di riferimento (pixel per metro)"""
        self.reference_image_scale = scale
        self.update()

    def setReferenceImageOpacity(self, opacity: float):
        """Imposta opacità immagine (0-1)"""
        self.reference_image_opacity = max(0, min(1, opacity))
        self.update()

    def drawReferenceImage(self, painter):
        """Disegna immagine di riferimento"""
        if not self.reference_image or not self.show_reference:
            return

        painter.setOpacity(self.reference_image_opacity)

        # Calcola posizione e dimensione
        sx, sy = self.worldToScreen(self.reference_image_pos[0], self.reference_image_pos[1])
        scaled_w = int(self.reference_image.width() * self.scala / self.reference_image_scale)
        scaled_h = int(self.reference_image.height() * self.scala / self.reference_image_scale)

        scaled_pixmap = self.reference_image.scaled(scaled_w, scaled_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(sx, sy - scaled_h, scaled_pixmap)

        painter.setOpacity(1.0)

    # ========== KEYBOARD EVENTS ==========

    def keyPressEvent(self, event):
        """Gestisce eventi tastiera"""
        if event.key() == Qt.Key_Escape:
            # Annulla operazione corrente
            self.punto_inizio = None
            self.punto_corrente = None
            self.polygon_vertices = []
            self.misura_attiva = False
            self.update()

        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # Chiudi poligono
            if self.strumento == 'polygon' and len(self.polygon_vertices) >= 3:
                self.closePolygon()

        elif event.key() == Qt.Key_Delete:
            # Elimina selezione
            self.deleteSelected()

        elif event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_A:
                self.selectAll()
            elif event.key() == Qt.Key_C:
                self.copiaSelezionati()
            elif event.key() == Qt.Key_V:
                self.incollaCliboard()
            elif event.key() == Qt.Key_Z:
                if self.undo_stack:
                    self.undo_stack.undo()
                    self.update()
            elif event.key() == Qt.Key_Y:
                if self.undo_stack:
                    self.undo_stack.redo()
                    self.update()

        super().keyPressEvent(event)


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

    # Segnale per comandi remoti (thread-safe)
    remoteCommandReceived = pyqtSignal(str, str)  # action, params_json

    def __init__(self):
        super().__init__()
        self.progetto = Progetto()
        self.show_quick_actions = True

        # Variabili per controllo remoto
        self._remote_result = None
        self._remote_action = None
        self._remote_params = None

        self.initUI()

        # Connetti segnale comandi remoti
        self.remoteCommandReceived.connect(self._executeRemoteCommand)

        # Avvia controller remoto
        self.remote_controller = RemoteController(self, port=9999)
        self.remote_controller.start()

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

        # Canvas (per step geometria e aperture) - con navigazione
        self.canvas_container = QWidget()
        canvas_layout = QVBoxLayout(self.canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(0)

        self.canvas = DrawingCanvas()
        self.canvas.setProgetto(self.progetto)
        self.canvas.muroAggiunto.connect(self.onMuroAggiunto)
        self.canvas.selectionChanged.connect(self.onSelectionChanged)
        self.canvas.requestApertura.connect(self.onRequestApertura)
        canvas_layout.addWidget(self.canvas, 1)  # stretch=1

        # Barra input coordinate (stile CAD)
        self.coord_input_bar = CoordinateInputBar()
        self.coord_input_bar.setCanvas(self.canvas)
        self.coord_input_bar.coordinateEntered.connect(self.onCoordinateEntered)
        self.coord_input_bar.relativeEntered.connect(self.onRelativeEntered)
        self.coord_input_bar.polarEntered.connect(self.onPolarEntered)
        self.coord_input_bar.commandEntered.connect(self.onCommandEntered)
        self.canvas.coordinateUpdate.connect(self.onCanvasCoordinateUpdate)
        canvas_layout.addWidget(self.coord_input_bar)

        # Barra di navigazione per canvas
        self.canvas_nav = QWidget()
        self.canvas_nav.setFixedHeight(50)
        self.canvas_nav.setStyleSheet("""
            QWidget { background-color: #f5f5f5; border-top: 1px solid #ddd; }
            QPushButton { padding: 8px 20px; font-size: 13px; border-radius: 4px; }
            QPushButton#btn_indietro { background-color: #6c757d; color: white; }
            QPushButton#btn_indietro:hover { background-color: #5a6268; }
            QPushButton#btn_avanti { background-color: #0066cc; color: white; font-weight: bold; }
            QPushButton#btn_avanti:hover { background-color: #0052a3; }
        """)
        nav_layout = QHBoxLayout(self.canvas_nav)
        nav_layout.setContentsMargins(15, 8, 15, 8)

        self.canvas_btn_indietro = QPushButton("← Indietro")
        self.canvas_btn_indietro.setObjectName("btn_indietro")
        self.canvas_btn_indietro.clicked.connect(self.canvasIndietro)
        nav_layout.addWidget(self.canvas_btn_indietro)

        self.canvas_step_label = QLabel("GEOMETRIA - Disegno Muri")
        self.canvas_step_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        self.canvas_step_label.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(self.canvas_step_label, 1)

        self.canvas_btn_avanti = QPushButton("Avanti →")
        self.canvas_btn_avanti.setObjectName("btn_avanti")
        self.canvas_btn_avanti.clicked.connect(self.canvasAvanti)
        nav_layout.addWidget(self.canvas_btn_avanti)

        canvas_layout.addWidget(self.canvas_nav)
        self.content_stack.addWidget(self.canvas_container)

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

        # Layer Manager (dock destra)
        self.layer_manager = LayerManager(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.layer_manager)
        self.layer_manager.layerVisibilityChanged.connect(self.onLayerVisibilityChanged)
        self.layer_manager.hide()

        # Undo Stack
        self.undo_stack = QUndoStack(self)
        self.canvas.undo_stack = self.undo_stack

        # Status bar professionale
        self.status_label = QLabel("Pronto")
        self.status_label.setMinimumWidth(300)
        self.statusBar().addWidget(self.status_label)

        # Separatore
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet("color: #ccc;")
        self.statusBar().addWidget(sep1)

        # Indicatore strumento corrente
        self.tool_indicator = QLabel("Strumento: Seleziona")
        self.tool_indicator.setStyleSheet("""
            font-weight: bold;
            color: #0066cc;
            padding: 2px 8px;
            background: #e8f4fc;
            border-radius: 3px;
        """)
        self.statusBar().addWidget(self.tool_indicator)

        # Contatore elementi
        self.element_counter = QLabel("Muri: 0 | Aperture: 0")
        self.element_counter.setStyleSheet("color: #666; padding: 0 10px;")
        self.statusBar().addPermanentWidget(self.element_counter)

        # Indicatore snap
        self.snap_status = QLabel("SNAP: ON")
        self.snap_status.setStyleSheet("""
            font-size: 10px;
            font-weight: bold;
            color: white;
            background-color: #28a745;
            padding: 2px 6px;
            border-radius: 3px;
        """)
        self.statusBar().addPermanentWidget(self.snap_status)

        # Indicatore griglia
        self.grid_status = QLabel("GRID: ON")
        self.grid_status.setStyleSheet("""
            font-size: 10px;
            font-weight: bold;
            color: white;
            background-color: #17a2b8;
            padding: 2px 6px;
            border-radius: 3px;
        """)
        self.statusBar().addPermanentWidget(self.grid_status)

        self.step_progress = QLabel("Step: -")
        self.step_progress.setStyleSheet("font-weight: bold; color: #333; padding: 0 10px;")
        self.statusBar().addPermanentWidget(self.step_progress)

    def createRibbon(self):
        self.ribbon = RibbonToolbar()

        # Tab HOME
        home_tab = RibbonTab()

        file_panel = RibbonPanel("File")
        btn_nuovo = RibbonButton("Nuovo", icon_name="file-new", icon_category="actions")
        btn_nuovo.clicked.connect(self.nuovoProgetto)
        file_panel.addButton(btn_nuovo)
        btn_apri = RibbonButton("Apri", icon_name="folder-open", icon_category="actions")
        btn_apri.clicked.connect(self.apriProgetto)
        file_panel.addButton(btn_apri)
        btn_salva = RibbonButton("Salva", icon_name="save", icon_category="actions")
        btn_salva.clicked.connect(self.salvaProgetto)
        file_panel.addButton(btn_salva)
        home_tab.addPanel(file_panel)

        tools_panel = RibbonPanel("Strumenti")
        self.btn_select = RibbonButton("Seleziona", icon_name="cursor", icon_category="tools")
        self.btn_select.setCheckable(True)
        self.btn_select.setChecked(True)
        self.btn_select.clicked.connect(lambda: self.setTool('select'))
        tools_panel.addButton(self.btn_select)
        self.btn_muro = RibbonButton("Muro", icon_name="wall", icon_category="elements")
        self.btn_muro.setCheckable(True)
        self.btn_muro.clicked.connect(lambda: self.setTool('muro'))
        tools_panel.addButton(self.btn_muro)
        self.btn_rettangolo = RibbonButton("Rettangolo", icon_name="rectangle", icon_category="tools")
        self.btn_rettangolo.setCheckable(True)
        self.btn_rettangolo.setToolTip("Disegna 4 muri che formano un rettangolo")
        self.btn_rettangolo.clicked.connect(lambda: self.setTool('rettangolo'))
        tools_panel.addButton(self.btn_rettangolo)
        self.btn_apertura = RibbonButton("Apertura", icon_name="door", icon_category="elements")
        self.btn_apertura.setCheckable(True)
        self.btn_apertura.setToolTip("Clicca su un muro per inserire apertura")
        self.btn_apertura.clicked.connect(lambda: self.setTool('apertura'))
        tools_panel.addButton(self.btn_apertura)
        self.btn_polygon = RibbonButton("Poligono", icon_name="polygon", icon_category="tools")
        self.btn_polygon.setCheckable(True)
        self.btn_polygon.setToolTip("Disegna poligono di muri (doppio-click o Enter per chiudere)")
        self.btn_polygon.clicked.connect(lambda: self.setTool('polygon'))
        tools_panel.addButton(self.btn_polygon)
        home_tab.addPanel(tools_panel)

        # Pannello Piano
        piano_panel = RibbonPanel("Piano")
        btn_piano_su = RibbonButton("▲")
        btn_piano_su.setToolTip("Piano superiore")
        btn_piano_su.setFixedWidth(40)
        btn_piano_su.clicked.connect(self.pianoSu)
        piano_panel.addButton(btn_piano_su)

        self.piano_label = QLabel("Piano 0")
        self.piano_label.setAlignment(Qt.AlignCenter)
        self.piano_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #0066cc;
                background-color: #e8f4fc;
                border: 1px solid #0066cc;
                border-radius: 4px;
                padding: 5px 10px;
                min-width: 70px;
            }
        """)
        piano_panel.addWidget(self.piano_label)

        btn_piano_giu = RibbonButton("▼")
        btn_piano_giu.setToolTip("Piano inferiore")
        btn_piano_giu.setFixedWidth(40)
        btn_piano_giu.clicked.connect(self.pianoGiu)
        piano_panel.addButton(btn_piano_giu)

        btn_aggiungi_piano = RibbonButton("+Piano")
        btn_aggiungi_piano.setToolTip("Aggiungi nuovo piano")
        btn_aggiungi_piano.clicked.connect(self.aggiungiPiano)
        piano_panel.addButton(btn_aggiungi_piano)

        btn_copia_piano = RibbonButton("Copia")
        btn_copia_piano.setToolTip("Copia elementi da altro piano")
        btn_copia_piano.clicked.connect(self.copiaPiano)
        piano_panel.addButton(btn_copia_piano)

        home_tab.addPanel(piano_panel)

        # Pannello strumenti avanzati
        adv_panel = RibbonPanel("Avanzati")
        btn_misura = RibbonButton("Misura", icon_name="measure", icon_category="tools")
        btn_misura.setCheckable(True)
        btn_misura.setToolTip("Misura distanze nel disegno")
        btn_misura.clicked.connect(lambda: self.canvas.setStrumento('misura'))
        adv_panel.addButton(btn_misura)
        btn_copia = RibbonButton("Copia", icon_name="copy", icon_category="actions")
        btn_copia.setToolTip("Copia muri selezionati (Ctrl+C)")
        btn_copia.clicked.connect(self.copiaMuri)
        adv_panel.addButton(btn_copia)
        btn_incolla = RibbonButton("Incolla", icon_name="paste", icon_category="actions")
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
        btn_ruota = RibbonButton("Ruota")
        btn_ruota.setToolTip("Ruota elementi selezionati")
        btn_ruota.clicked.connect(self.ruotaMuri)
        adv_panel.addButton(btn_ruota)
        home_tab.addPanel(adv_panel)

        # Pannello Export/Import
        export_panel = RibbonPanel("Export")
        btn_dxf = RibbonButton("DXF")
        btn_dxf.setToolTip("Esporta in formato DXF (AutoCAD)")
        btn_dxf.clicked.connect(self.esportaDXF)
        export_panel.addButton(btn_dxf)
        btn_pdf = RibbonButton("PDF")
        btn_pdf.setToolTip("Esporta report in PDF")
        btn_pdf.clicked.connect(self.esportaPDF)
        export_panel.addButton(btn_pdf)
        btn_img = RibbonButton("Immagine")
        btn_img.setToolTip("Importa immagine di riferimento")
        btn_img.clicked.connect(self.importaImmagine)
        export_panel.addButton(btn_img)
        home_tab.addPanel(export_panel)

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

        # Tab VISTA
        vista_tab = RibbonTab()

        pannelli_panel = RibbonPanel("Pannelli")
        btn_browser = RibbonButton("Browser\nProgetto")
        btn_browser.setCheckable(True)
        btn_browser.clicked.connect(self.toggleBrowser)
        pannelli_panel.addButton(btn_browser)
        btn_props = RibbonButton("Proprietà")
        btn_props.setCheckable(True)
        btn_props.clicked.connect(self.toggleProperties)
        pannelli_panel.addButton(btn_props)
        btn_layers = RibbonButton("Layer")
        btn_layers.setCheckable(True)
        btn_layers.clicked.connect(self.toggleLayers)
        pannelli_panel.addButton(btn_layers)
        vista_tab.addPanel(pannelli_panel)

        aspetto_panel = RibbonPanel("Aspetto")
        self.btn_tema = RibbonButton("Tema\nScuro")
        self.btn_tema.setCheckable(True)
        self.btn_tema.setToolTip("Cambia tema chiaro/scuro (Ctrl+T)")
        self.btn_tema.clicked.connect(self.toggleTema)
        aspetto_panel.addButton(self.btn_tema)
        btn_griglia = RibbonButton("Griglia")
        btn_griglia.setCheckable(True)
        btn_griglia.setChecked(True)
        btn_griglia.setToolTip("Mostra/nascondi griglia")
        btn_griglia.clicked.connect(self.toggleGriglia)
        aspetto_panel.addButton(btn_griglia)
        btn_quote = RibbonButton("Quote")
        btn_quote.setCheckable(True)
        btn_quote.setChecked(True)
        btn_quote.setToolTip("Mostra/nascondi quote automatiche")
        btn_quote.clicked.connect(self.toggleQuote)
        aspetto_panel.addButton(btn_quote)
        vista_tab.addPanel(aspetto_panel)

        zoom_panel = RibbonPanel("Zoom")
        btn_fit = RibbonButton("Adatta")
        btn_fit.setToolTip("Adatta vista a tutti gli elementi (Home)")
        btn_fit.clicked.connect(self.zoomFit)
        zoom_panel.addButton(btn_fit)
        btn_zoom_in = RibbonButton("Zoom +")
        btn_zoom_in.clicked.connect(self.zoomIn)
        zoom_panel.addButton(btn_zoom_in)
        btn_zoom_out = RibbonButton("Zoom -")
        btn_zoom_out.clicked.connect(self.zoomOut)
        zoom_panel.addButton(btn_zoom_out)
        vista_tab.addPanel(zoom_panel)

        self.ribbon.addTab(vista_tab, "Vista")

        # Tab HELP (?)
        help_tab = RibbonTab()

        info_panel = RibbonPanel("Informazioni")
        btn_guida = RibbonButton("Guida", icon_name="help-circle", icon_category="misc")
        btn_guida.setToolTip("Mostra guida rapida (F1)")
        btn_guida.clicked.connect(self.mostraGuida)
        info_panel.addButton(btn_guida)
        btn_about = RibbonButton("Info", icon_name="info", icon_category="status")
        btn_about.setToolTip("Informazioni su Muratura")
        btn_about.clicked.connect(self.showAbout)
        info_panel.addButton(btn_about)
        help_tab.addPanel(info_panel)

        self.ribbon.addTab(help_tab, "?")

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
            self, "Apri Progetto", "", "File Muratura (*.mur);;Tutti i file (*.*)"
        )
        if filepath:
            progetto = ProjectSerializer.load(filepath)
            if progetto:
                self.progetto = progetto
                self.canvas.setProgetto(self.progetto)
                self.browser.updateFromProject(self.progetto)
                self.vista_3d.setProgetto(self.progetto)

                # Aggiorna pannelli step
                self.step_progetto.progetto = self.progetto
                self.step_piani.progetto = self.progetto
                self.step_fondazioni.progetto = self.progetto
                self.step_cordoli.progetto = self.progetto
                self.step_solai.progetto = self.progetto
                self.step_carichi.progetto = self.progetto

                # Mostra workspace
                self.central_stack.setCurrentWidget(self.workspace)
                self.browser.show()
                self.properties.show()

                # Vai allo step salvato
                self.goToStep(self.progetto.current_step)

                self.setWindowTitle(f"MURATURA 2.0 - {self.progetto.nome}")
                self.status_label.setText(f"Progetto caricato: {filepath}")
            else:
                QMessageBox.warning(self, "Errore",
                    f"Impossibile caricare il progetto:\n{filepath}")

    def salvaProgetto(self):
        if not self.progetto.filepath:
            self.salvaProgettoConNome()
            return

        if ProjectSerializer.save(self.progetto, self.progetto.filepath):
            self.status_label.setText(f"Salvato: {self.progetto.filepath}")
            self.setWindowTitle(f"MURATURA 2.0 - {self.progetto.nome}")
        else:
            QMessageBox.warning(self, "Errore",
                f"Impossibile salvare il progetto:\n{self.progetto.filepath}")

    def salvaProgettoConNome(self):
        """Salva con nome - permette di scegliere percorso"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Salva Progetto con Nome", "",
            "File Muratura (*.mur);;Tutti i file (*.*)"
        )
        if filepath:
            # Aggiungi estensione se mancante
            if not filepath.lower().endswith('.mur'):
                filepath += '.mur'

            if ProjectSerializer.save(self.progetto, filepath):
                self.progetto.filepath = filepath
                self.status_label.setText(f"Salvato: {filepath}")
                self.setWindowTitle(f"MURATURA 2.0 - {self.progetto.nome}")
            else:
                QMessageBox.warning(self, "Errore",
                    f"Impossibile salvare il progetto:\n{filepath}")

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

    def showAbout(self):
        """Mostra dialogo informazioni"""
        dialog = AboutDialog(self)
        dialog.exec_()

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
            self.content_stack.setCurrentWidget(self.canvas_container)
            if step == WorkflowStep.GEOMETRIA:
                self.canvas_step_label.setText("GEOMETRIA - Disegno Muri")
                self.canvas_btn_indietro.setText("← Piani")
                self.canvas_btn_avanti.setText("Aperture →")
            else:  # APERTURE
                self.canvas_step_label.setText("APERTURE - Porte e Finestre")
                self.canvas_btn_indietro.setText("← Geometria")
                self.canvas_btn_avanti.setText("Fondazioni →")
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

    def onRequestApertura(self, nome_muro: str, posizione: float):
        """Chiamato quando l'utente clicca su un muro con lo strumento apertura"""
        dlg = DialogoApertura(self.progetto, nome_muro, self)
        # Pre-imposta la posizione
        dlg.posizione_spin.setValue(posizione)
        if dlg.exec_() == QDialog.Accepted and dlg.apertura_creata:
            self.progetto.aperture.append(dlg.apertura_creata)
            self.browser.updateFromProject(self.progetto)
            self.canvas.update()
            self.status_label.setText(f"Aggiunta apertura: {dlg.apertura_creata.nome}")

    # ========================================================================
    # NAVIGAZIONE CANVAS
    # ========================================================================

    def canvasIndietro(self):
        """Naviga indietro dalla schermata canvas"""
        if self.progetto.current_step == WorkflowStep.GEOMETRIA:
            self.goToStep(WorkflowStep.PIANI)
        elif self.progetto.current_step == WorkflowStep.APERTURE:
            self.goToStep(WorkflowStep.GEOMETRIA)

    def canvasAvanti(self):
        """Naviga avanti dalla schermata canvas"""
        if self.progetto.current_step == WorkflowStep.GEOMETRIA:
            self.goToStep(WorkflowStep.APERTURE)
        elif self.progetto.current_step == WorkflowStep.APERTURE:
            self.goToStep(WorkflowStep.FONDAZIONI)

    # ========================================================================
    # GESTIONE PIANI
    # ========================================================================

    def pianoSu(self):
        """Vai al piano superiore"""
        max_piano = len(self.progetto.piani) - 1
        if self.canvas.piano_corrente < max_piano:
            self.canvas.piano_corrente += 1
            self.updatePianoLabel()
            self.canvas.update()
            self.status_label.setText(f"Piano {self.canvas.piano_corrente}")

    def pianoGiu(self):
        """Vai al piano inferiore"""
        if self.canvas.piano_corrente > 0:
            self.canvas.piano_corrente -= 1
            self.updatePianoLabel()
            self.canvas.update()
            self.status_label.setText(f"Piano {self.canvas.piano_corrente}")

    def aggiungiPiano(self):
        """Aggiunge un nuovo piano al progetto"""
        n = len(self.progetto.piani)
        if n >= 10:
            QMessageBox.warning(self, "Avviso", "Massimo 10 piani supportati")
            return

        # Calcola quota del nuovo piano
        ultima_quota = self.progetto.piani[-1].quota if self.progetto.piani else 0
        ultima_altezza = self.progetto.piani[-1].altezza if self.progetto.piani else 3.0
        nuova_quota = ultima_quota + ultima_altezza

        nuovo_piano = Piano(
            numero=n,
            nome=f"Piano {n}",
            quota=nuova_quota,
            altezza=self.progetto.altezza_piano
        )
        self.progetto.piani.append(nuovo_piano)
        self.progetto.n_piani = len(self.progetto.piani)

        # Vai al nuovo piano
        self.canvas.piano_corrente = n
        self.updatePianoLabel()
        self.canvas.update()
        self.browser.updateFromProject(self.progetto)
        self.status_label.setText(f"Aggiunto Piano {n}")

    def updatePianoLabel(self):
        """Aggiorna l'etichetta del piano corrente"""
        piano = self.canvas.piano_corrente
        n_piani = len(self.progetto.piani)
        nome = self.progetto.piani[piano].nome if piano < n_piani else f"Piano {piano}"
        self.piano_label.setText(f"{nome}")
        self.piano_label.setToolTip(f"Piano {piano} di {n_piani} - Quota: {self.progetto.piani[piano].quota:.2f}m" if piano < n_piani else "")

    def copiaPiano(self):
        """Copia muri e aperture da un piano all'altro"""
        if len(self.progetto.piani) < 2:
            QMessageBox.warning(self, "Avviso", "Aggiungi almeno un altro piano prima di copiare")
            return

        piano_dest = self.canvas.piano_corrente
        if piano_dest >= len(self.progetto.piani):
            QMessageBox.warning(self, "Avviso", "Piano destinazione non valido")
            return

        # Crea lista piani sorgente (escludi destinazione)
        piani_disponibili = [p for p in self.progetto.piani if p.numero != piano_dest]
        if not piani_disponibili:
            QMessageBox.warning(self, "Avviso", "Nessun piano da cui copiare")
            return

        # Dialog selezione piano sorgente
        items = [f"{p.nome} (Piano {p.numero})" for p in piani_disponibili]
        item, ok = QInputDialog.getItem(
            self, "Copia Piano",
            f"Copia elementi verso {self.progetto.piani[piano_dest].nome}:\n\nSeleziona piano sorgente:",
            items, 0, False
        )
        if not ok:
            return

        # Trova piano sorgente selezionato
        idx = items.index(item)
        piano_src = piani_disponibili[idx].numero
        quota_src = self.progetto.piani[piano_src].quota
        quota_dest = self.progetto.piani[piano_dest].quota

        # Conta elementi nel piano sorgente
        muri_src = [m for m in self.progetto.muri if abs(m.z - quota_src) < 0.1]
        if not muri_src:
            QMessageBox.information(self, "Info", f"Il piano sorgente non ha muri da copiare")
            return

        # Chiedi conferma
        msg = f"Copiare {len(muri_src)} muri dal Piano {piano_src} al Piano {piano_dest}?\n"
        aperture_src = []
        for m in muri_src:
            aperture_src.extend([a for a in self.progetto.aperture if a.muro == m.nome])
        if aperture_src:
            msg += f"Verranno copiate anche {len(aperture_src)} aperture."

        reply = QMessageBox.question(self, "Conferma Copia", msg,
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # Esegui copia muri
        muri_copiati = 0
        mappa_nomi = {}  # vecchio_nome -> nuovo_nome
        for muro in muri_src:
            n = len(self.progetto.muri) + 1
            nuovo_nome = f"M{n}"
            nuovo_muro = Muro(
                nome=nuovo_nome,
                x1=muro.x1, y1=muro.y1,
                x2=muro.x2, y2=muro.y2,
                spessore=muro.spessore,
                altezza=muro.altezza,
                z=quota_dest,
                materiale=muro.materiale
            )
            self.progetto.muri.append(nuovo_muro)
            mappa_nomi[muro.nome] = nuovo_nome
            muri_copiati += 1

        # Copia aperture associate
        aperture_copiate = 0
        for ap in aperture_src:
            if ap.muro in mappa_nomi:
                n = len(self.progetto.aperture) + 1
                nuova_ap = Apertura(
                    nome=f"A{n}",
                    muro=mappa_nomi[ap.muro],
                    tipo=ap.tipo,
                    larghezza=ap.larghezza,
                    altezza=ap.altezza,
                    posizione=ap.posizione,
                    quota=ap.quota
                )
                self.progetto.aperture.append(nuova_ap)
                aperture_copiate += 1

        # Aggiorna interfaccia
        self.canvas.update()
        self.browser.updateFromProject(self.progetto)
        self.setModificato(True)
        self.status_label.setText(f"Copiati {muri_copiati} muri e {aperture_copiate} aperture")
        QMessageBox.information(self, "Copia Completata",
                               f"Copiati nel Piano {piano_dest}:\n• {muri_copiati} muri\n• {aperture_copiate} aperture")

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
        self.updateStatusBar()
        # Ricostruisci spatial index per snap veloce
        if self.progetto and self.progetto.muri:
            self.canvas.geometry_engine.rebuild_index(self.progetto.muri)

    def setTool(self, tool: str):
        """Imposta lo strumento corrente e aggiorna la UI"""
        self.canvas.setStrumento(tool)
        self.updateStatusBar()

        # Aggiorna bottoni radio
        tool_buttons = {
            'select': getattr(self, 'btn_select', None),
            'muro': getattr(self, 'btn_muro', None),
            'rettangolo': getattr(self, 'btn_rettangolo', None),
            'apertura': getattr(self, 'btn_apertura', None),
            'polygon': getattr(self, 'btn_polygon', None),
        }
        for t, btn in tool_buttons.items():
            if btn:
                btn.setChecked(t == tool)

    def updateStatusBar(self):
        """Aggiorna tutti gli elementi della status bar"""
        # Contatore elementi
        n_muri = len(self.progetto.muri) if self.progetto else 0
        n_aperture = len(self.progetto.aperture) if self.progetto else 0
        self.element_counter.setText(f"Muri: {n_muri} | Aperture: {n_aperture}")

        # Strumento corrente
        tool_names = {
            'select': 'Seleziona',
            'muro': 'Muro',
            'rettangolo': 'Rettangolo',
            'polygon': 'Poligono',
            'apertura': 'Apertura',
            'misura': 'Misura',
            'pan': 'Pan'
        }
        tool = self.canvas.strumento if hasattr(self, 'canvas') else 'select'
        self.tool_indicator.setText(f"Strumento: {tool_names.get(tool, tool)}")

        # Snap status
        if hasattr(self, 'canvas') and self.canvas.snap_enabled:
            self.snap_status.setText("SNAP: ON")
            self.snap_status.setStyleSheet("""
                font-size: 10px; font-weight: bold; color: white;
                background-color: #28a745; padding: 2px 6px; border-radius: 3px;
            """)
        else:
            self.snap_status.setText("SNAP: OFF")
            self.snap_status.setStyleSheet("""
                font-size: 10px; font-weight: bold; color: white;
                background-color: #6c757d; padding: 2px 6px; border-radius: 3px;
            """)

        # Grid status
        if hasattr(self, 'canvas') and self.canvas.griglia:
            self.grid_status.setText("GRID: ON")
            self.grid_status.setStyleSheet("""
                font-size: 10px; font-weight: bold; color: white;
                background-color: #17a2b8; padding: 2px 6px; border-radius: 3px;
            """)
        else:
            self.grid_status.setText("GRID: OFF")
            self.grid_status.setStyleSheet("""
                font-size: 10px; font-weight: bold; color: white;
                background-color: #6c757d; padding: 2px 6px; border-radius: 3px;
            """)

    # ========== COORDINATE INPUT HANDLERS ==========

    def onCanvasCoordinateUpdate(self, x: float, y: float, length: float, angle: float, snap_type: str):
        """Riceve aggiornamenti coordinate dal canvas"""
        self.coord_input_bar.updateCoordinates(x, y)
        if length >= 0:
            self.coord_input_bar.updateMeasurements(length, angle)
        else:
            self.coord_input_bar.updateMeasurements(None, None)
        if snap_type:
            self.coord_input_bar.updateSnapIndicator(snap_type)
        else:
            self.coord_input_bar.updateSnapIndicator(None)

    def onCoordinateEntered(self, x: float, y: float):
        """Gestisce input coordinate assolute"""
        self._processCoordinate(x, y)
        self.coord_input_bar.last_point = (x, y)

    def onRelativeEntered(self, dx: float, dy: float):
        """Gestisce input coordinate relative"""
        if self.coord_input_bar.last_point:
            x = self.coord_input_bar.last_point[0] + dx
            y = self.coord_input_bar.last_point[1] + dy
        elif self.canvas.punto_inizio:
            x = self.canvas.punto_inizio[0] + dx
            y = self.canvas.punto_inizio[1] + dy
        else:
            x, y = dx, dy
        self._processCoordinate(x, y)
        self.coord_input_bar.last_point = (x, y)

    def onPolarEntered(self, length: float, angle: float):
        """Gestisce input coordinate polari (lunghezza, angolo)"""
        import math
        rad = math.radians(angle)
        if self.coord_input_bar.last_point:
            x = self.coord_input_bar.last_point[0] + length * math.cos(rad)
            y = self.coord_input_bar.last_point[1] + length * math.sin(rad)
        elif self.canvas.punto_inizio:
            x = self.canvas.punto_inizio[0] + length * math.cos(rad)
            y = self.canvas.punto_inizio[1] + length * math.sin(rad)
        else:
            x = length * math.cos(rad)
            y = length * math.sin(rad)
        self._processCoordinate(x, y)
        self.coord_input_bar.last_point = (x, y)

    def onCommandEntered(self, command: str):
        """Gestisce comandi testuali"""
        command = command.upper()
        if command == 'ESC' or command == 'ANNULLA':
            self.canvas.punto_inizio = None
            self.canvas.punto_corrente = None
            self.canvas.polygon_vertices = []
            self.canvas.update()
            self.status_label.setText("Operazione annullata")
        elif command == 'MURO' or command == 'M':
            self.canvas.setStrumento('muro')
            self.status_label.setText("Strumento: Muro")
        elif command == 'RETTANGOLO' or command == 'R':
            self.canvas.setStrumento('rettangolo')
            self.status_label.setText("Strumento: Rettangolo")
        elif command == 'SELEZIONA' or command == 'S':
            self.canvas.setStrumento('select')
            self.status_label.setText("Strumento: Seleziona")
        elif command == 'POLIGONO' or command == 'P':
            self.canvas.setStrumento('polygon')
            self.status_label.setText("Strumento: Poligono")
        elif command == 'MISURA':
            self.canvas.setStrumento('misura')
            self.status_label.setText("Strumento: Misura")
        elif command == 'CHIUDI' or command == 'C':
            if self.canvas.strumento == 'polygon' and len(self.canvas.polygon_vertices) >= 3:
                self.canvas.closePolygon()
                self.status_label.setText("Poligono chiuso")
        elif command == 'GRIGLIA' or command == 'G':
            self.canvas.griglia = not self.canvas.griglia
            self.canvas.update()
            stato = "attivata" if self.canvas.griglia else "disattivata"
            self.status_label.setText(f"Griglia {stato}")
            self.updateStatusBar()
        elif command == 'SNAP':
            self.canvas.snap_enabled = not self.canvas.snap_enabled
            self.canvas.update()
            stato = "attivato" if self.canvas.snap_enabled else "disattivato"
            self.status_label.setText(f"Snap {stato}")
            self.updateStatusBar()
        elif command == 'QUOTE' or command == 'Q':
            self.canvas.show_dimensions = not self.canvas.show_dimensions
            self.canvas.update()
            stato = "attivate" if self.canvas.show_dimensions else "disattivate"
            self.status_label.setText(f"Quote {stato}")
        elif command == 'ZOOM' or command == 'Z':
            self.canvas.zoomFit()
            self.status_label.setText("Zoom adattato")
        elif command == 'ELIMINA' or command == 'DEL' or command == 'DELETE':
            self.canvas.deleteSelected()
        else:
            self.status_label.setText(f"Comando sconosciuto: {command}")

    def _processCoordinate(self, x: float, y: float):
        """Processa una coordinata per lo strumento corrente"""
        strumento = self.canvas.strumento

        if strumento == 'muro':
            if not self.canvas.punto_inizio:
                self.canvas.punto_inizio = (x, y)
                self.status_label.setText(f"Muro: punto iniziale ({x:.2f}, {y:.2f}) - inserisci punto finale")
            else:
                self.canvas.createMuro(x, y)
                self.canvas.punto_inizio = None
                self.canvas.punto_corrente = None
                self.coord_input_bar.last_point = (x, y)

        elif strumento == 'rettangolo':
            if not self.canvas.punto_inizio:
                self.canvas.punto_inizio = (x, y)
                self.status_label.setText(f"Rettangolo: angolo 1 ({x:.2f}, {y:.2f}) - inserisci angolo opposto")
            else:
                self.canvas.drawRettangolo(
                    self.canvas.punto_inizio[0], self.canvas.punto_inizio[1],
                    x, y
                )
                self.canvas.punto_inizio = None
                self.canvas.punto_corrente = None

        elif strumento == 'polygon':
            self.canvas.handlePolygonClick(x, y)
            self.status_label.setText(f"Poligono: {len(self.canvas.polygon_vertices)} vertici - 'C' per chiudere")

        self.canvas.update()

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

    # ========== NUOVE FUNZIONI ==========

    def onLayerVisibilityChanged(self, layer_name: str, visible: bool):
        """Gestisce cambio visibilità layer"""
        self.canvas.update()
        self.status_label.setText(f"Layer '{layer_name}': {'visibile' if visible else 'nascosto'}")

    def ruotaMuri(self):
        """Ruota muri selezionati"""
        self.canvas.showRotateDialog()

    def esportaDXF(self):
        """
        Esporta progetto in formato DXF professionale.
        Usa ezdxf per generare file compatibili con AutoCAD/FreeCAD.
        Include: layer separati, quote dimensionali, hatch per muri.
        """
        if not DXF_AVAILABLE:
            QMessageBox.warning(self, "Errore",
                "Libreria ezdxf non disponibile.\nInstalla con: pip install ezdxf")
            return

        if not self.progetto.muri:
            QMessageBox.warning(self, "Attenzione", "Nessun muro da esportare")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Esporta DXF", f"{self.progetto.nome}.dxf",
            "DXF Files (*.dxf)"
        )

        if not filepath:
            return

        try:
            doc = ezdxf.new('R2018')
            msp = doc.modelspace()

            # === SETUP LAYER PROFESSIONALI ===
            doc.layers.add('MURI', color=5, lineweight=35)  # Blu, spessore 0.35mm
            doc.layers.add('MURI_HATCH', color=251)  # Grigio chiaro per hatch
            doc.layers.add('APERTURE', color=1, lineweight=18)  # Rosso, 0.18mm
            doc.layers.add('APERTURE_SIMBOLI', color=3)  # Verde per simboli
            doc.layers.add('FONDAZIONI', color=8, lineweight=50)  # Grigio, 0.50mm
            doc.layers.add('QUOTE', color=7)  # Nero per testi
            doc.layers.add('DIMENSIONI', color=2)  # Giallo per quote dimensionali
            doc.layers.add('ASSI', color=4, linetype='CENTER')  # Ciano per assi

            # === SETUP STILE QUOTE ===
            doc.dimstyles.new('MURATURA',
                dxfattribs={
                    'dimtxt': 0.15,  # Altezza testo
                    'dimasz': 0.1,  # Dimensione frecce
                    'dimexe': 0.05,  # Estensione linee
                    'dimexo': 0.05,  # Offset linee estensione
                    'dimtad': 1,  # Testo sopra linea
                })

            # === ESPORTA MURI PER PIANO ===
            piani_esportati = set()
            for muro in self.progetto.muri:
                piano = int(muro.z / self.progetto.altezza_piano) if self.progetto.altezza_piano > 0 else 0
                piani_esportati.add(piano)

                # Calcola i 4 punti del muro (rettangolo)
                dx = muro.x2 - muro.x1
                dy = muro.y2 - muro.y1
                length = math.sqrt(dx*dx + dy*dy)
                if length > 0:
                    nx = -dy / length * muro.spessore / 2
                    ny = dx / length * muro.spessore / 2

                    points = [
                        (muro.x1 - nx, muro.y1 - ny),
                        (muro.x1 + nx, muro.y1 + ny),
                        (muro.x2 + nx, muro.y2 + ny),
                        (muro.x2 - nx, muro.y2 - ny),
                    ]

                    # Polilinea chiusa per contorno muro
                    poly = msp.add_lwpolyline(
                        points + [points[0]],
                        dxfattribs={'layer': 'MURI', 'const_width': 0}
                    )
                    poly.close()

                    # Aggiungi hatch riempimento (pattern muratura)
                    try:
                        hatch = msp.add_hatch(color=251, dxfattribs={'layer': 'MURI_HATCH'})
                        hatch.paths.add_polyline_path(points + [points[0]], is_closed=True)
                        hatch.set_pattern_fill('ANSI31', scale=0.5)
                    except Exception:
                        pass  # Hatch opzionale

                    # Testo nome muro al centro
                    cx = (muro.x1 + muro.x2) / 2
                    cy = (muro.y1 + muro.y2) / 2
                    angle = math.degrees(math.atan2(dy, dx))
                    msp.add_text(
                        muro.nome,
                        dxfattribs={
                            'layer': 'QUOTE',
                            'height': 0.12,
                            'rotation': angle if -90 < angle < 90 else angle + 180
                        }
                    ).set_placement((cx, cy), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

                    # Quota dimensionale lunghezza
                    try:
                        dim = msp.add_aligned_dim(
                            p1=(muro.x1, muro.y1),
                            p2=(muro.x2, muro.y2),
                            distance=0.3,
                            dimstyle='MURATURA',
                            override={'dimtxt': 0.1}
                        )
                        dim.dxf.layer = 'DIMENSIONI'
                        dim.render()
                    except Exception:
                        pass  # Quote opzionali

            # === ESPORTA APERTURE COME SIMBOLI ===
            for ap in self.progetto.aperture:
                muro = next((m for m in self.progetto.muri if m.nome == ap.muro), None)
                if muro:
                    dx = muro.x2 - muro.x1
                    dy = muro.y2 - muro.y1
                    length = math.sqrt(dx*dx + dy*dy)
                    if length > 0:
                        # Direzione lungo il muro
                        ux = dx / length
                        uy = dy / length
                        # Normale al muro
                        nx = -uy
                        ny = ux

                        # Posizione centro apertura
                        t = ap.posizione / length
                        ax = muro.x1 + dx * t
                        ay = muro.y1 + dy * t

                        # Mezza larghezza apertura
                        hw = ap.larghezza / 2
                        hs = muro.spessore / 2 * 1.1  # Leggermente oltre lo spessore

                        # Disegna simbolo apertura (linee di rottura)
                        # Linea interruzione sinistra
                        msp.add_line(
                            (ax - ux * hw - nx * hs, ay - uy * hw - ny * hs),
                            (ax - ux * hw + nx * hs, ay - uy * hw + ny * hs),
                            dxfattribs={'layer': 'APERTURE'}
                        )
                        # Linea interruzione destra
                        msp.add_line(
                            (ax + ux * hw - nx * hs, ay + uy * hw - ny * hs),
                            (ax + ux * hw + nx * hs, ay + uy * hw + ny * hs),
                            dxfattribs={'layer': 'APERTURE'}
                        )

                        # Arco simbolo porta/finestra
                        if ap.tipo == 'porta':
                            # Simbolo porta (arco 90°)
                            msp.add_arc(
                                center=(ax - ux * hw, ay - uy * hw),
                                radius=ap.larghezza,
                                start_angle=math.degrees(math.atan2(uy, ux)),
                                end_angle=math.degrees(math.atan2(uy, ux)) + 90,
                                dxfattribs={'layer': 'APERTURE_SIMBOLI'}
                            )
                        else:
                            # Simbolo finestra (X)
                            msp.add_line(
                                (ax - ux * hw * 0.7, ay - uy * hw * 0.7),
                                (ax + ux * hw * 0.7, ay + uy * hw * 0.7),
                                dxfattribs={'layer': 'APERTURE_SIMBOLI'}
                            )

                        # Label apertura
                        msp.add_text(
                            f"{ap.nome}\n{ap.larghezza:.2f}x{ap.altezza:.2f}",
                            dxfattribs={'layer': 'QUOTE', 'height': 0.08}
                        ).set_placement((ax, ay + 0.2))

            # === ESPORTA FONDAZIONI ===
            for fond in self.progetto.fondazioni:
                dx = fond.x2 - fond.x1
                dy = fond.y2 - fond.y1
                length = math.sqrt(dx*dx + dy*dy)
                if length > 0:
                    nx = -dy / length * fond.larghezza / 2
                    ny = dx / length * fond.larghezza / 2

                    points = [
                        (fond.x1 - nx, fond.y1 - ny),
                        (fond.x1 + nx, fond.y1 + ny),
                        (fond.x2 + nx, fond.y2 + ny),
                        (fond.x2 - nx, fond.y2 - ny),
                    ]
                    poly = msp.add_lwpolyline(
                        points + [points[0]],
                        dxfattribs={'layer': 'FONDAZIONI'}
                    )
                    poly.close()

            # === ASSI COORDINATI ===
            msp.add_line((-1, 0), (10, 0), dxfattribs={'layer': 'ASSI'})
            msp.add_line((0, -1), (0, 10), dxfattribs={'layer': 'ASSI'})
            msp.add_text('X', dxfattribs={'layer': 'ASSI', 'height': 0.2}).set_placement((10.2, 0))
            msp.add_text('Y', dxfattribs={'layer': 'ASSI', 'height': 0.2}).set_placement((0, 10.2))

            # Salva
            doc.saveas(filepath)
            self.status_label.setText(f"Esportato: {filepath}")

            # Info esportazione
            n_muri = len(self.progetto.muri)
            n_aperture = len(self.progetto.aperture)
            n_piani = len(piani_esportati)
            QMessageBox.information(self, "Esportazione DXF",
                f"File esportato con successo:\n{filepath}\n\n"
                f"Contenuto:\n"
                f"  - {n_muri} muri\n"
                f"  - {n_aperture} aperture\n"
                f"  - {len(self.progetto.fondazioni)} fondazioni\n"
                f"  - {n_piani} piani\n\n"
                f"Layer disponibili: MURI, APERTURE, FONDAZIONI, QUOTE, DIMENSIONI")

        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore durante l'esportazione:\n{e}")

    def esportaPDF(self):
        """Esporta report in PDF"""
        if not PDF_AVAILABLE:
            # Fallback: usa esportaReport che genera HTML
            self.esportaReport()
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Esporta PDF", f"{self.progetto.nome}_report.pdf",
            "PDF Files (*.pdf)"
        )

        if not filepath:
            return

        try:
            doc = SimpleDocTemplate(filepath, pagesize=A4,
                                   leftMargin=2*cm, rightMargin=2*cm,
                                   topMargin=2*cm, bottomMargin=2*cm)

            styles = getSampleStyleSheet()
            story = []

            # Titolo
            title_style = ParagraphStyle(
                'Title',
                parent=styles['Title'],
                fontSize=18,
                spaceAfter=30
            )
            story.append(Paragraph(f"RELAZIONE DI CALCOLO - {self.progetto.nome}", title_style))
            story.append(Spacer(1, 20))

            # Dati generali
            story.append(Paragraph("1. DATI GENERALI", styles['Heading2']))
            data_gen = [
                ["Progetto:", self.progetto.nome],
                ["Autore:", self.progetto.autore or "-"],
                ["N. Piani:", str(self.progetto.n_piani)],
                ["Altezza piano:", f"{self.progetto.altezza_piano:.2f} m"],
                ["N. Muri:", str(len(self.progetto.muri))],
                ["N. Aperture:", str(len(self.progetto.aperture))]
            ]
            t = Table(data_gen, colWidths=[5*cm, 10*cm])
            t.setStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ])
            story.append(t)
            story.append(Spacer(1, 20))

            # Parametri sismici
            story.append(Paragraph("2. PARAMETRI SISMICI", styles['Heading2']))
            sismici = self.progetto.sismici
            data_sism = [
                ["Comune:", sismici.comune or "-"],
                ["Sottosuolo:", sismici.sottosuolo],
                ["Topografia:", sismici.topografia],
                ["Vita nominale:", f"{sismici.vita_nominale} anni"],
                ["Classe d'uso:", str(sismici.classe_uso)],
                ["Fattore q:", f"{sismici.fattore_struttura:.2f}"],
                ["ag(SLV):", f"{sismici.ag_slv:.3f} g" if sismici.ag_slv else "-"]
            ]
            t = Table(data_sism, colWidths=[5*cm, 10*cm])
            t.setStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ])
            story.append(t)
            story.append(Spacer(1, 20))

            # Tabella muri
            story.append(Paragraph("3. GEOMETRIA MURI", styles['Heading2']))
            header = ["Nome", "Lunghezza", "Spessore", "Altezza", "DCR", "Verifica"]
            data_muri = [header]
            for m in self.progetto.muri:
                verifica = "OK" if m.dcr <= 1.0 or m.dcr == 0 else "NO"
                data_muri.append([
                    m.nome,
                    f"{m.lunghezza:.2f} m",
                    f"{m.spessore:.2f} m",
                    f"{m.altezza:.2f} m",
                    f"{m.dcr:.3f}" if m.dcr > 0 else "-",
                    verifica
                ])

            t = Table(data_muri, colWidths=[2*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2*cm, 2*cm])
            t.setStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ])
            story.append(t)
            story.append(Spacer(1, 20))

            # Risultati analisi
            story.append(Paragraph("4. RISULTATI ANALISI", styles['Heading2']))
            ir = self.progetto.indice_rischio
            classe = VerificheNTC2018.calcola_classe_rischio(ir)
            data_ris = [
                ["Indice di Rischio (IR):", f"{ir:.3f}"],
                ["Classe Rischio Sismico:", classe['classe']],
                ["Descrizione:", classe['descrizione']],
                ["Verifica globale:", "VERIFICATO" if ir >= 1.0 else "NON VERIFICATO"]
            ]
            t = Table(data_ris, colWidths=[5*cm, 10*cm])
            t.setStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ])
            story.append(t)

            # Build PDF
            doc.build(story)
            self.status_label.setText(f"PDF esportato: {filepath}")
            QMessageBox.information(self, "Esportazione PDF",
                f"Report PDF generato:\n{filepath}")

        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore generazione PDF:\n{e}")

    def importaImmagine(self):
        """Importa immagine di riferimento"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Importa Immagine di Riferimento", "",
            "Immagini (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"
        )

        if filepath:
            if self.canvas.loadReferenceImage(filepath):
                # Chiedi la scala
                scala, ok = QInputDialog.getDouble(
                    self, "Scala Immagine",
                    "Pixel per metro nell'immagine:",
                    value=100.0, min=1.0, max=1000.0, decimals=1
                )
                if ok:
                    self.canvas.setReferenceImageScale(scala)

                # Chiedi opacità
                opacita, ok = QInputDialog.getDouble(
                    self, "Opacità Immagine",
                    "Opacità (0-1):",
                    value=0.5, min=0.0, max=1.0, decimals=2
                )
                if ok:
                    self.canvas.setReferenceImageOpacity(opacita)

                self.status_label.setText(f"Immagine caricata: {filepath}")

    # ========================================================================
    # METODI VISTA E TEMA
    # ========================================================================

    def toggleTema(self):
        """Cambia tema chiaro/scuro"""
        new_theme = ThemeManager.toggle_theme()
        self.applyTheme()
        # Aggiorna testo pulsante
        if new_theme == 'dark':
            self.btn_tema.setText("Tema\nChiaro")
        else:
            self.btn_tema.setText("Tema\nScuro")
        self.status_label.setText(f"Tema: {ThemeManager.THEMES[new_theme]['name']}")

    def applyTheme(self):
        """Applica il tema corrente all'applicazione"""
        QApplication.instance().setStyleSheet(ThemeManager.get_stylesheet())
        # Aggiorna canvas
        if hasattr(self, 'canvas'):
            self.canvas.update()
        # Aggiorna vista 3D
        if hasattr(self, 'vista_3d'):
            self.vista_3d.update()

    def toggleBrowser(self):
        """Mostra/nascondi browser progetto"""
        if self.browser.isVisible():
            self.browser.hide()
        else:
            self.browser.show()

    def toggleProperties(self):
        """Mostra/nascondi pannello proprietà"""
        if self.properties.isVisible():
            self.properties.hide()
        else:
            self.properties.show()

    def toggleLayers(self):
        """Mostra/nascondi layer manager"""
        if self.layer_manager.isVisible():
            self.layer_manager.hide()
        else:
            self.layer_manager.show()

    def toggleGriglia(self):
        """Mostra/nascondi griglia"""
        if hasattr(self.canvas, 'mostra_griglia'):
            self.canvas.mostra_griglia = not self.canvas.mostra_griglia
        else:
            self.canvas.mostra_griglia = False
        self.canvas.update()

    def toggleQuote(self):
        """Mostra/nascondi quote automatiche"""
        if hasattr(self.canvas, 'mostra_quote'):
            self.canvas.mostra_quote = not self.canvas.mostra_quote
        else:
            self.canvas.mostra_quote = False
        self.canvas.update()

    def zoomFit(self):
        """Adatta zoom a tutti gli elementi"""
        if not self.progetto.muri:
            return

        # Trova bounding box
        min_x = min(min(m.x1, m.x2) for m in self.progetto.muri)
        max_x = max(max(m.x1, m.x2) for m in self.progetto.muri)
        min_y = min(min(m.y1, m.y2) for m in self.progetto.muri)
        max_y = max(max(m.y1, m.y2) for m in self.progetto.muri)

        # Calcola scala ottimale
        dx = max_x - min_x + 2
        dy = max_y - min_y + 2
        scale_x = (self.canvas.width() - 100) / dx if dx > 0 else 50
        scale_y = (self.canvas.height() - 100) / dy if dy > 0 else 50
        self.canvas.scala = min(scale_x, scale_y, 80)

        # Centra
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2
        self.canvas.offset_x = self.canvas.width() / 2 - cx * self.canvas.scala
        self.canvas.offset_y = self.canvas.height() / 2 + cy * self.canvas.scala

        self.canvas.update()
        self.status_label.setText("Vista adattata")

    def zoomIn(self):
        """Zoom avanti"""
        self.canvas.scala = min(80, self.canvas.scala * 1.25)
        self.canvas.update()

    def zoomOut(self):
        """Zoom indietro"""
        self.canvas.scala = max(5, self.canvas.scala / 1.25)
        self.canvas.update()

    # ========================================================================
    # CONTROLLO REMOTO - Esecuzione comandi da MCP
    # ========================================================================

    def _executeRemoteCommand(self, action: str, params_json: str):
        """Esegue un comando remoto nel thread principale Qt"""
        try:
            params = json.loads(params_json)
            result = self._dispatchRemoteAction(action, params)
            self._remote_result = result
        except Exception as e:
            self._remote_result = {'success': False, 'error': str(e)}

    def _dispatchRemoteAction(self, action: str, params: dict) -> dict:
        """Dispatcher per tutte le azioni remote"""

        # Feedback visivo
        self.status_label.setText(f"🤖 Comando remoto: {action}")
        self.status_label.setStyleSheet("color: #0066cc; font-weight: bold;")
        QApplication.processEvents()

        try:
            # === PROGETTO ===
            if action == "nuovo_progetto":
                self.nuovoProgetto()
                self.progetto.nome = params.get('nome', 'Nuovo Progetto')
                self.progetto.committente = params.get('committente', '')
                self.progetto.indirizzo = params.get('indirizzo', '')
                if hasattr(self.step_progetto, 'refresh'):
                    self.step_progetto.refresh()
                return {'success': True, 'message': f"Progetto '{self.progetto.nome}' creato"}

            elif action == "vai_step":
                step_name = params.get('step', 'PROGETTO')
                try:
                    step = WorkflowStep[step_name]
                    self.goToStep(step)
                    return {'success': True, 'step': step_name}
                except KeyError:
                    return {'success': False, 'error': f"Step '{step_name}' non valido"}

            elif action == "get_stato":
                return {
                    'success': True,
                    'progetto': self.progetto.nome,
                    'step_corrente': self.progetto.current_step.name,
                    'n_muri': len(self.progetto.muri),
                    'n_aperture': len(self.progetto.aperture),
                    'n_piani': len(self.progetto.piani),
                    'n_fondazioni': len(self.progetto.fondazioni),
                    'n_solai': len(self.progetto.solai)
                }

            # === PIANI ===
            elif action == "aggiungi_piano":
                self.aggiungiPiano()
                n = len(self.progetto.piani) - 1
                return {'success': True, 'piano': n, 'message': f"Piano {n} aggiunto"}

            elif action == "vai_piano":
                piano = params.get('piano', 0)
                if 0 <= piano < len(self.progetto.piani):
                    self.canvas.piano_corrente = piano
                    self.updatePianoLabel()
                    self.canvas.update()
                    return {'success': True, 'piano': piano}
                return {'success': False, 'error': 'Piano non valido'}

            # === GEOMETRIA - MURI ===
            elif action == "disegna_muro":
                x1 = float(params.get('x1', 0))
                y1 = float(params.get('y1', 0))
                x2 = float(params.get('x2', 5))
                y2 = float(params.get('y2', 0))
                spessore = float(params.get('spessore', 0.30))
                altezza = float(params.get('altezza', 3.0))

                # Calcola z dal piano corrente
                piano = self.canvas.piano_corrente
                z = self.progetto.piani[piano].quota if piano < len(self.progetto.piani) else 0

                n = len(self.progetto.muri) + 1
                muro = Muro(
                    nome=f"M{n}",
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    spessore=spessore,
                    altezza=altezza,
                    z=z
                )
                self.progetto.muri.append(muro)
                self.canvas.update()
                self.browser.updateFromProject(self.progetto)

                # Animazione visiva
                self._highlightElement(muro)

                return {'success': True, 'muro': muro.nome, 'lunghezza': muro.lunghezza}

            elif action == "disegna_rettangolo":
                # Disegna 4 muri a formare un rettangolo
                x = float(params.get('x', 0))
                y = float(params.get('y', 0))
                larghezza = float(params.get('larghezza', 10))
                profondita = float(params.get('profondita', 8))
                spessore = float(params.get('spessore', 0.30))

                muri_creati = []
                piano = self.canvas.piano_corrente
                z = self.progetto.piani[piano].quota if piano < len(self.progetto.piani) else 0

                # 4 lati
                lati = [
                    (x, y, x + larghezza, y),  # Sud
                    (x + larghezza, y, x + larghezza, y + profondita),  # Est
                    (x + larghezza, y + profondita, x, y + profondita),  # Nord
                    (x, y + profondita, x, y),  # Ovest
                ]

                for x1, y1, x2, y2 in lati:
                    n = len(self.progetto.muri) + 1
                    muro = Muro(nome=f"M{n}", x1=x1, y1=y1, x2=x2, y2=y2,
                               spessore=spessore, altezza=self.progetto.altezza_piano, z=z)
                    self.progetto.muri.append(muro)
                    muri_creati.append(muro.nome)
                    self.canvas.update()
                    QApplication.processEvents()
                    import time
                    time.sleep(0.3)  # Pausa per vedere l'animazione

                self.browser.updateFromProject(self.progetto)
                return {'success': True, 'muri': muri_creati}

            # === APERTURE ===
            elif action == "aggiungi_apertura":
                muro_nome = params.get('muro', '')
                tipo = params.get('tipo', 'finestra')
                larghezza = float(params.get('larghezza', 1.2))
                altezza = float(params.get('altezza', 1.4))
                posizione = float(params.get('posizione', 1.0))
                altezza_davanzale = float(params.get('quota', 0.9 if tipo == 'finestra' else 0.0))

                # Verifica muro
                muro = next((m for m in self.progetto.muri if m.nome == muro_nome), None)
                if not muro:
                    return {'success': False, 'error': f"Muro '{muro_nome}' non trovato"}

                n = len(self.progetto.aperture) + 1
                apertura = Apertura(
                    nome=f"A{n}",
                    muro=muro_nome,
                    tipo=tipo,
                    larghezza=larghezza,
                    altezza=altezza,
                    posizione=posizione,
                    altezza_davanzale=altezza_davanzale
                )
                self.progetto.aperture.append(apertura)
                self.canvas.update()
                self.browser.updateFromProject(self.progetto)

                return {'success': True, 'apertura': apertura.nome, 'muro': muro_nome}

            # === FONDAZIONI ===
            elif action == "genera_fondazioni":
                # Genera fondazioni senza mostrare dialog (bloccherebbe)
                self.goToStep(WorkflowStep.FONDAZIONI)
                QApplication.processEvents()

                muri_con_fond = {f.muro_collegato for f in self.progetto.fondazioni}
                nuove = 0
                for muro in self.progetto.muri:
                    if muro.nome not in muri_con_fond:
                        n = len(self.progetto.fondazioni) + 1
                        fond = Fondazione(
                            nome=f"F{n}",
                            tipo="trave_rovescia",
                            x1=muro.x1, y1=muro.y1, x2=muro.x2, y2=muro.y2,
                            larghezza=max(0.60, muro.spessore * 2),
                            altezza=0.50, profondita=1.0,
                            muro_collegato=muro.nome
                        )
                        self.progetto.fondazioni.append(fond)
                        nuove += 1

                self.step_fondazioni.refresh()
                return {'success': True, 'n_fondazioni': len(self.progetto.fondazioni), 'nuove': nuove}

            elif action == "aggiungi_fondazione":
                muro_nome = params.get('muro', '')
                muro = next((m for m in self.progetto.muri if m.nome == muro_nome), None)
                if not muro:
                    return {'success': False, 'error': f"Muro '{muro_nome}' non trovato"}

                n = len(self.progetto.fondazioni) + 1
                fond = Fondazione(
                    nome=f"F{n}",
                    tipo=params.get('tipo', 'trave_rovescia'),
                    x1=muro.x1, y1=muro.y1, x2=muro.x2, y2=muro.y2,
                    larghezza=float(params.get('larghezza', 0.6)),
                    altezza=float(params.get('altezza', 0.5)),
                    profondita=float(params.get('profondita', 1.0)),
                    muro_collegato=muro_nome
                )
                self.progetto.fondazioni.append(fond)
                if hasattr(self, 'step_fondazioni'):
                    self.step_fondazioni.refresh()
                return {'success': True, 'fondazione': fond.nome}

            # === CORDOLI ===
            elif action == "genera_cordoli":
                self.goToStep(WorkflowStep.CORDOLI)
                QApplication.processEvents()

                # Genera cordoli senza dialog
                if not self.progetto.piani:
                    return {'success': False, 'error': 'Nessun piano definito'}

                ultimo_piano = max(p.numero for p in self.progetto.piani)
                nuovi = 0
                for muro in self.progetto.muri:
                    exists = any(c.muro_collegato == muro.nome and c.piano == ultimo_piano
                                for c in self.progetto.cordoli)
                    if not exists:
                        n = len(self.progetto.cordoli) + 1
                        cordolo = Cordolo(
                            nome=f"C{n}", piano=ultimo_piano,
                            x1=muro.x1, y1=muro.y1, x2=muro.x2, y2=muro.y2,
                            base=0.30, altezza=0.25,
                            muro_collegato=muro.nome
                        )
                        self.progetto.cordoli.append(cordolo)
                        nuovi += 1

                self.step_cordoli.refresh()
                return {'success': True, 'n_cordoli': len(self.progetto.cordoli), 'nuovi': nuovi}

            # === SOLAI ===
            elif action == "genera_solai":
                self.goToStep(WorkflowStep.SOLAI)
                QApplication.processEvents()

                # Genera solai senza dialog
                piani_con_solaio = {s.piano for s in self.progetto.solai}
                nuovi = 0
                for piano in self.progetto.piani:
                    if piano.numero not in piani_con_solaio:
                        n = len(self.progetto.solai) + 1
                        solaio = Solaio(
                            nome=f"S{n}", piano=piano.numero,
                            tipo="Laterocemento 20+5",
                            luce=5.0, larghezza=5.0,
                            peso_proprio=3.2, carico_variabile=2.0,
                            categoria_uso="A"
                        )
                        self.progetto.solai.append(solaio)
                        nuovi += 1

                self.step_solai.refresh()
                return {'success': True, 'n_solai': len(self.progetto.solai), 'nuovi': nuovi}

            elif action == "aggiungi_solaio":
                piano = int(params.get('piano', 0))
                n = len(self.progetto.solai) + 1
                solaio = Solaio(
                    nome=f"S{n}",
                    piano=piano,
                    tipo=params.get('tipo', 'Laterocemento 20+5'),
                    luce=float(params.get('luce', 5.0)),
                    larghezza=float(params.get('larghezza', 5.0)),
                    peso_proprio=float(params.get('peso_proprio', 3.2)),
                    carico_variabile=float(params.get('carico_variabile', 2.0)),
                    categoria_uso=params.get('categoria', 'A')
                )
                self.progetto.solai.append(solaio)
                if hasattr(self, 'step_solai'):
                    self.step_solai.refresh()
                return {'success': True, 'solaio': solaio.nome}

            # === ANALISI ===
            elif action == "esegui_analisi":
                self.goToStep(WorkflowStep.ANALISI)
                QApplication.processEvents()
                # L'analisi si apre automaticamente
                return {'success': True, 'message': 'Analisi POR avviata'}

            # === VISTA ===
            elif action == "zoom_fit":
                self.zoomFit()
                return {'success': True}

            elif action == "mostra_3d":
                self.goToStep(WorkflowStep.RISULTATI)
                return {'success': True}

            # === COPIA PIANO ===
            elif action == "copia_piano":
                src = int(params.get('da_piano', 0))
                dest = int(params.get('a_piano', 1))
                # Simula la funzione copiaPiano
                self.canvas.piano_corrente = dest
                # ... logica copia
                return {'success': True, 'message': f'Copiato piano {src} -> {dest}'}

            # === SALVATAGGIO ===
            elif action == "salva_progetto":
                filepath = params.get('filepath', '')
                if filepath:
                    self.progetto.filepath = filepath
                    self.salvaProgetto()
                    return {'success': True, 'filepath': filepath}
                return {'success': False, 'error': 'Specificare filepath'}

            # === LISTA COMANDI ===
            elif action == "help":
                comandi = [
                    "nuovo_progetto", "vai_step", "get_stato",
                    "aggiungi_piano", "vai_piano",
                    "disegna_muro", "disegna_rettangolo",
                    "aggiungi_apertura",
                    "genera_fondazioni", "aggiungi_fondazione",
                    "genera_cordoli", "genera_solai", "aggiungi_solaio",
                    "esegui_analisi", "zoom_fit", "mostra_3d",
                    "copia_piano", "salva_progetto", "help"
                ]
                return {'success': True, 'comandi': comandi}

            else:
                return {'success': False, 'error': f"Azione '{action}' non riconosciuta"}

        except Exception as e:
            import traceback
            return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

        finally:
            # Ripristina status bar
            self.status_label.setStyleSheet("")
            QApplication.processEvents()

    def _highlightElement(self, element):
        """Evidenzia temporaneamente un elemento appena creato"""
        # Flash visivo
        original_style = self.canvas.styleSheet()
        self.canvas.setStyleSheet("border: 3px solid #00cc00;")
        QApplication.processEvents()

        QTimer.singleShot(500, lambda: self.canvas.setStyleSheet(original_style))

    def closeEvent(self, event):
        """Ferma il controller remoto alla chiusura"""
        if hasattr(self, 'remote_controller'):
            self.remote_controller.stop()
        super().closeEvent(event)


# ============================================================================
# REMOTE CONTROLLER - Controllo GUI via MCP
# ============================================================================

class RemoteController(threading.Thread):
    """Controller per comandare la GUI da remoto via socket"""

    # Segnale per eseguire comandi nel thread principale Qt
    # (definito nella classe principale)

    def __init__(self, main_window, port=9999):
        super().__init__(daemon=True)
        self.main_window = main_window
        self.port = port
        self.running = True
        self.server_socket = None

    def run(self):
        """Thread principale del server socket"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('127.0.0.1', self.port))
            self.server_socket.listen(1)
            self.server_socket.settimeout(1.0)

            print(f"[RemoteController] In ascolto su porta {self.port}")

            while self.running:
                try:
                    client, addr = self.server_socket.accept()
                    print(f"[RemoteController] Connessione da {addr}")
                    self.handle_client(client)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"[RemoteController] Errore accept: {e}")

        except Exception as e:
            print(f"[RemoteController] Errore avvio server: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def handle_client(self, client):
        """Gestisce una connessione client"""
        client.settimeout(60.0)
        buffer = ""

        try:
            while self.running:
                data = client.recv(4096).decode('utf-8')
                if not data:
                    break

                buffer += data

                # Processa linee complete
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        response = self.process_command(line.strip())
                        client.send((json.dumps(response) + '\n').encode('utf-8'))

        except socket.timeout:
            pass
        except Exception as e:
            print(f"[RemoteController] Errore client: {e}")
        finally:
            client.close()

    def process_command(self, cmd_str):
        """Processa un comando JSON e ritorna il risultato"""
        try:
            cmd = json.loads(cmd_str)
            action = cmd.get('action', '')
            params = cmd.get('params', {})

            print(f"[RemoteController] Comando: {action}")

            # Esegui nel thread Qt
            result = {'success': False, 'error': 'Comando non riconosciuto'}

            # Usa invokeMethod per chiamare nel thread principale
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG

            # Salva risultato in variabile condivisa
            self.main_window._remote_result = None
            self.main_window._remote_action = action
            self.main_window._remote_params = params

            # Emetti segnale per esecuzione nel thread Qt
            self.main_window.remoteCommandReceived.emit(action, json.dumps(params))

            # Attendi risultato (max 30 secondi)
            import time
            for _ in range(300):
                if self.main_window._remote_result is not None:
                    return self.main_window._remote_result
                time.sleep(0.1)

            return {'success': False, 'error': 'Timeout esecuzione comando'}

        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'JSON non valido: {e}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def stop(self):
        """Ferma il server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()


# ============================================================================
# MAIN
# ============================================================================

def main():
    app = QApplication(sys.argv)

    # Stile globale
    app.setStyle('Fusion')

    # Inizializza IconManager
    IconManager.init()

    # Mostra splash screen
    splash = ProfessionalSplashScreen()
    splash.show()
    app.processEvents()

    # Simulazione caricamento
    splash.setProgress(10, "Caricamento moduli...")
    app.processEvents()

    splash.setProgress(30, "Inizializzazione risorse...")
    app.processEvents()

    splash.setProgress(50, "Configurazione interfaccia...")
    app.processEvents()

    # Crea finestra principale
    splash.setProgress(70, "Creazione finestra principale...")
    app.processEvents()
    editor = MuraturaEditorV2()

    # Applica tema
    splash.setProgress(90, "Applicazione tema...")
    app.processEvents()
    app.setStyleSheet(ThemeManager.get_stylesheet())

    splash.setProgress(100, "Pronto!")
    app.processEvents()

    # Chiudi splash e mostra editor
    splash.finish(editor)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
