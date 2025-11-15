#!/usr/bin/env python3
"""
Wire Editor Unified v6.0
Applicazione integrata per gestione coordinate fili fissi

Combina funzionalità di:
- wire_editor.py (input tabellare, import/export, reports)
- wire_editor1.py (canvas grafico, topologie, disegno interattivo)

Arch. Michelangelo Bartolotta
Ordine Architetti Agrigento n. 1557
"""

import sys
import json
import math
import csv
from datetime import datetime
from enum import Enum
from copy import deepcopy
from typing import Dict, List, Optional, Tuple, Any

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QDoubleSpinBox, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QGroupBox, QGridLayout, QFileDialog, QMessageBox,
    QHeaderView, QAbstractItemView, QDialog, QTextEdit, QDialogButtonBox,
    QInputDialog, QComboBox, QSpinBox, QCheckBox, QTabWidget, QToolBar,
    QAction, QSplitter, QScrollArea, QDockWidget
)
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal, QTimer
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QIcon, QCursor,
    QPixmap, QPalette
)

# Matplotlib imports (opzionali)
try:
    import matplotlib
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Openpyxl imports (opzionali)
try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font as XLFont, PatternFill, Alignment, Border, Side
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

# Reportlab imports (opzionali)
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Ezdxf imports (opzionali)
try:
    import ezdxf
    EZDXF_AVAILABLE = True
except ImportError:
    EZDXF_AVAILABLE = False


# ============================================================================
# ENUMERAZIONI E COSTANTI
# ============================================================================

class Direction(Enum):
    """Direzione per edges"""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    NONE = "none"


class TopologyRole(Enum):
    """Ruolo topologico del nodo"""
    CENTER = "center"
    CORNER = "corner"
    EDGE_MIDPOINT = "edge"
    FREE = "free"


class EdgeType(Enum):
    """Tipo di collegamento"""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    DIAGONAL = "diagonal"
    FREE = "free"


# ============================================================================
# DATA MODEL UNIFICATO
# ============================================================================

class Node:
    """Nodo unificato - combina Point (wire_editor.py) e Node (wire_editor1.py)"""

    def __init__(self, node_id: int, x: float, y: float, z: float = 0.0,
                 description: str = "", level: str = "",
                 topology_role: TopologyRole = TopologyRole.FREE):
        self.id = node_id
        self.x = x
        self.y = y
        self.z = z
        self.description = description
        self.level = level  # Livello/Piano (es: "PT", "P1", "P2")

        # Proprietà topologiche (da wire_editor1.py)
        self.topology_role = topology_role
        self.snap_radius = 0.15  # metri
        self.color = QColor(100, 150, 200)
        self.selected = False

    def to_dict(self) -> Dict[str, Any]:
        """Serializzazione per JSON"""
        return {
            'id': self.id,
            'x': self.x,
            'y': self.y,
            'z': self.z,
            'description': self.description,
            'level': self.level,
            'topology_role': self.topology_role.value if self.topology_role else TopologyRole.FREE.value,
            'snap_radius': self.snap_radius,
            'color': self.color.name()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Node':
        """Deserializzazione da JSON"""
        node = cls(
            data['id'],
            data['x'],
            data['y'],
            data.get('z', 0.0),
            data.get('description', ''),
            data.get('level', ''),
            TopologyRole(data.get('topology_role', 'free'))
        )
        node.snap_radius = data.get('snap_radius', 0.15)
        if 'color' in data:
            node.color = QColor(data['color'])
        return node

    def distance_to(self, other: 'Node') -> float:
        """Distanza 2D ad altro nodo"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def distance_3d_to(self, other: 'Node') -> float:
        """Distanza 3D ad altro nodo"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)


class Edge:
    """Collegamento tra nodi (da wire_editor1.py)"""

    def __init__(self, edge_id: int, node1_id: int, node2_id: int,
                 edge_type: EdgeType = EdgeType.FREE):
        self.id = edge_id
        self.node1_id = node1_id
        self.node2_id = node2_id
        self.edge_type = edge_type
        self.color = QColor(80, 80, 80)
        self.width = 2
        self.selected = False

    def to_dict(self) -> Dict[str, Any]:
        """Serializzazione per JSON"""
        return {
            'id': self.id,
            'node1_id': self.node1_id,
            'node2_id': self.node2_id,
            'edge_type': self.edge_type.value,
            'color': self.color.name(),
            'width': self.width
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Edge':
        """Deserializzazione da JSON"""
        edge = cls(
            data['id'],
            data['node1_id'],
            data['node2_id'],
            EdgeType(data.get('edge_type', 'free'))
        )
        if 'color' in data:
            edge.color = QColor(data['color'])
        edge.width = data.get('width', 2)
        return edge


class Annotation:
    """Annotazione grafica (da wire_editor.py)"""

    def __init__(self, annotation_type: str, color: str = 'red', linewidth: int = 2):
        self.type = annotation_type
        self.color = color
        self.linewidth = linewidth

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type,
            'color': self.color,
            'linewidth': self.linewidth
        }


class LineAnnotation(Annotation):
    """Linea tra due nodi"""

    def __init__(self, node1_id: int, node2_id: int, color: str = 'red',
                 linewidth: int = 2, style: str = 'solid'):
        super().__init__('line', color, linewidth)
        self.node1_id = node1_id
        self.node2_id = node2_id
        self.style = style  # 'solid', 'dashed', 'dotted'

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'node1_id': self.node1_id,
            'node2_id': self.node2_id,
            'style': self.style
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LineAnnotation':
        return cls(
            data['node1_id'],
            data['node2_id'],
            data.get('color', 'red'),
            data.get('linewidth', 2),
            data.get('style', 'solid')
        )


class DimensionAnnotation(Annotation):
    """Quota/dimensione tra due nodi"""

    def __init__(self, node1_id: int, node2_id: int, offset: float = 0.5,
                 color: str = 'blue', show_text: bool = True):
        super().__init__('dimension', color, 1)
        self.node1_id = node1_id
        self.node2_id = node2_id
        self.offset = offset
        self.show_text = show_text

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'node1_id': self.node1_id,
            'node2_id': self.node2_id,
            'offset': self.offset,
            'show_text': self.show_text
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DimensionAnnotation':
        return cls(
            data['node1_id'],
            data['node2_id'],
            data.get('offset', 0.5),
            data.get('color', 'blue'),
            data.get('show_text', True)
        )


class UnifiedModel:
    """Model unificato - gestisce nodi, edges, annotazioni"""

    def __init__(self):
        self.nodes: Dict[int, Node] = {}
        self.edges: Dict[int, Edge] = {}
        self.annotations: List[Annotation] = []

        self.next_node_id = 1
        self.next_edge_id = 1

        self.metadata = {
            "author": "Arch. Michelangelo Bartolotta",
            "registration": "Ordine Architetti Agrigento n. 1557",
            "project_type": "Coordinate Fili Fissi",
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat(),
            "project_name": "",
            "location": "",
            "notes": ""
        }

        # Undo/Redo
        self.undo_stack: List['Command'] = []
        self.redo_stack: List['Command'] = []
        self.max_undo_levels = 50

    # === Gestione Nodi ===

    def add_node(self, x: float, y: float, z: float = 0.0,
                 description: str = "", level: str = "",
                 topology_role: TopologyRole = TopologyRole.FREE) -> int:
        """Aggiunge un nodo (interno - usare execute_command per undo/redo)"""
        if not description:
            description = f"Node {self.next_node_id}"

        node = Node(self.next_node_id, x, y, z, description, level, topology_role)
        self.nodes[self.next_node_id] = node
        node_id = self.next_node_id
        self.next_node_id += 1
        self._mark_modified()
        return node_id

    def update_node(self, node_id: int, **kwargs) -> bool:
        """Aggiorna un nodo"""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            for key, value in kwargs.items():
                if hasattr(node, key):
                    setattr(node, key, value)
            self._mark_modified()
            return True
        return False

    def delete_node(self, node_id: int) -> bool:
        """Elimina un nodo e tutti gli edge connessi"""
        if node_id in self.nodes:
            # Elimina edges connessi
            edges_to_delete = [eid for eid, edge in self.edges.items()
                             if edge.node1_id == node_id or edge.node2_id == node_id]
            for eid in edges_to_delete:
                del self.edges[eid]

            # Elimina nodo
            del self.nodes[node_id]
            self._mark_modified()
            return True
        return False

    def get_node_list(self) -> List[Node]:
        """Restituisce lista ordinata nodi"""
        return sorted(self.nodes.values(), key=lambda n: n.id)

    # === Gestione Edges ===

    def add_edge(self, node1_id: int, node2_id: int,
                 edge_type: EdgeType = EdgeType.FREE) -> Optional[int]:
        """Aggiunge un edge tra due nodi"""
        if node1_id not in self.nodes or node2_id not in self.nodes:
            return None

        # Verifica se edge già esiste
        for edge in self.edges.values():
            if (edge.node1_id == node1_id and edge.node2_id == node2_id) or \
               (edge.node1_id == node2_id and edge.node2_id == node1_id):
                return None  # Edge già esiste

        edge = Edge(self.next_edge_id, node1_id, node2_id, edge_type)
        self.edges[self.next_edge_id] = edge
        edge_id = self.next_edge_id
        self.next_edge_id += 1
        self._mark_modified()
        return edge_id

    def delete_edge(self, edge_id: int) -> bool:
        """Elimina un edge"""
        if edge_id in self.edges:
            del self.edges[edge_id]
            self._mark_modified()
            return True
        return False

    # === Utility ===

    def get_levels(self) -> List[str]:
        """Restituisce lista livelli unici ordinati"""
        levels = set(n.level for n in self.nodes.values() if n.level)
        return sorted(levels)

    def get_nodes_by_level(self, level: str) -> List[Node]:
        """Restituisce nodi di un livello specifico"""
        return [n for n in self.nodes.values() if n.level == level]

    def get_bounds(self) -> Optional[Dict[str, float]]:
        """Calcola bounds delle coordinate"""
        if not self.nodes:
            return None

        nodes = list(self.nodes.values())
        return {
            'x_min': min(n.x for n in nodes),
            'x_max': max(n.x for n in nodes),
            'y_min': min(n.y for n in nodes),
            'y_max': max(n.y for n in nodes),
            'z_min': min(n.z for n in nodes),
            'z_max': max(n.z for n in nodes)
        }

    def clear(self):
        """Pulisce tutti i dati"""
        self.nodes.clear()
        self.edges.clear()
        self.annotations.clear()
        self.next_node_id = 1
        self.next_edge_id = 1
        self._mark_modified()

    def _mark_modified(self):
        """Marca come modificato"""
        self.metadata["modified"] = datetime.now().isoformat()

    # === Serializzazione ===

    def to_dict(self) -> Dict[str, Any]:
        """Esporta per JSON"""
        return {
            "version": "6.0",
            "metadata": self.metadata,
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges.values()],
            "annotations": [ann.to_dict() for ann in self.annotations],
            "next_node_id": self.next_node_id,
            "next_edge_id": self.next_edge_id
        }

    def from_dict(self, data: Dict[str, Any]):
        """Importa da JSON"""
        self.clear()

        if "metadata" in data:
            self.metadata.update(data["metadata"])

        if "nodes" in data:
            for node_data in data["nodes"]:
                node = Node.from_dict(node_data)
                self.nodes[node.id] = node

        if "edges" in data:
            for edge_data in data["edges"]:
                edge = Edge.from_dict(edge_data)
                self.edges[edge.id] = edge

        if "annotations" in data:
            for ann_data in data["annotations"]:
                ann_type = ann_data.get('type')
                if ann_type == 'line':
                    self.annotations.append(LineAnnotation.from_dict(ann_data))
                elif ann_type == 'dimension':
                    self.annotations.append(DimensionAnnotation.from_dict(ann_data))

        self.next_node_id = data.get("next_node_id", 1)
        self.next_edge_id = data.get("next_edge_id", 1)

        # Correggi ID se necessario
        if self.nodes:
            max_id = max(self.nodes.keys())
            if max_id >= self.next_node_id:
                self.next_node_id = max_id + 1

        if self.edges:
            max_id = max(self.edges.keys())
            if max_id >= self.next_edge_id:
                self.next_edge_id = max_id + 1

    # === Undo/Redo ===

    def execute_command(self, command: 'Command') -> Any:
        """Esegue comando e aggiunge a undo stack"""
        result = command.execute(self)
        self.undo_stack.append(command)
        if len(self.undo_stack) > self.max_undo_levels:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        return result

    def undo(self) -> bool:
        """Annulla ultima operazione"""
        if not self.undo_stack:
            return False
        command = self.undo_stack.pop()
        command.undo(self)
        self.redo_stack.append(command)
        self._mark_modified()
        return True

    def redo(self) -> bool:
        """Ripristina operazione annullata"""
        if not self.redo_stack:
            return False
        command = self.redo_stack.pop()
        command.execute(self)
        self.undo_stack.append(command)
        self._mark_modified()
        return True

    def can_undo(self) -> bool:
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self.redo_stack) > 0

    def clear_undo_history(self):
        self.undo_stack.clear()
        self.redo_stack.clear()


# ============================================================================
# COMMAND PATTERN UNIFICATO
# ============================================================================

class Command:
    """Classe base per comandi Undo/Redo"""

    def execute(self, model: UnifiedModel) -> Any:
        """Esegue il comando"""
        raise NotImplementedError

    def undo(self, model: UnifiedModel):
        """Annulla il comando"""
        raise NotImplementedError


class CreateNodeCommand(Command):
    """Comando per creare un nodo"""

    def __init__(self, x: float, y: float, z: float = 0.0,
                 description: str = "", level: str = "",
                 topology_role: TopologyRole = TopologyRole.FREE):
        self.x = x
        self.y = y
        self.z = z
        self.description = description
        self.level = level
        self.topology_role = topology_role
        self.node_id = None

    def execute(self, model: UnifiedModel) -> int:
        self.node_id = model.add_node(self.x, self.y, self.z,
                                     self.description, self.level,
                                     self.topology_role)
        return self.node_id

    def undo(self, model: UnifiedModel):
        if self.node_id:
            model.delete_node(self.node_id)


class UpdateNodeCommand(Command):
    """Comando per aggiornare un nodo"""

    def __init__(self, node_id: int, **kwargs):
        self.node_id = node_id
        self.new_values = kwargs
        self.old_values = {}

    def execute(self, model: UnifiedModel) -> bool:
        if self.node_id in model.nodes:
            node = model.nodes[self.node_id]
            # Salva valori vecchi
            for key in self.new_values.keys():
                if hasattr(node, key):
                    self.old_values[key] = getattr(node, key)
            # Applica nuovi valori
            model.update_node(self.node_id, **self.new_values)
            return True
        return False

    def undo(self, model: UnifiedModel):
        if self.old_values:
            model.update_node(self.node_id, **self.old_values)


class DeleteNodeCommand(Command):
    """Comando per eliminare un nodo"""

    def __init__(self, node_id: int):
        self.node_id = node_id
        self.saved_node = None
        self.saved_edges = []

    def execute(self, model: UnifiedModel) -> bool:
        if self.node_id in model.nodes:
            # Salva nodo
            node = model.nodes[self.node_id]
            self.saved_node = node.to_dict()

            # Salva edges connessi
            for eid, edge in list(model.edges.items()):
                if edge.node1_id == self.node_id or edge.node2_id == self.node_id:
                    self.saved_edges.append(edge.to_dict())

            # Elimina
            model.delete_node(self.node_id)
            return True
        return False

    def undo(self, model: UnifiedModel):
        if self.saved_node:
            # Ripristina nodo
            node = Node.from_dict(self.saved_node)
            model.nodes[node.id] = node
            if node.id >= model.next_node_id:
                model.next_node_id = node.id + 1

            # Ripristina edges
            for edge_data in self.saved_edges:
                edge = Edge.from_dict(edge_data)
                model.edges[edge.id] = edge
                if edge.id >= model.next_edge_id:
                    model.next_edge_id = edge.id + 1


class CreateEdgeCommand(Command):
    """Comando per creare un edge"""

    def __init__(self, node1_id: int, node2_id: int,
                 edge_type: EdgeType = EdgeType.FREE):
        self.node1_id = node1_id
        self.node2_id = node2_id
        self.edge_type = edge_type
        self.edge_id = None

    def execute(self, model: UnifiedModel) -> Optional[int]:
        self.edge_id = model.add_edge(self.node1_id, self.node2_id, self.edge_type)
        return self.edge_id

    def undo(self, model: UnifiedModel):
        if self.edge_id:
            model.delete_edge(self.edge_id)


class DeleteEdgeCommand(Command):
    """Comando per eliminare un edge"""

    def __init__(self, edge_id: int):
        self.edge_id = edge_id
        self.saved_edge = None

    def execute(self, model: UnifiedModel) -> bool:
        if self.edge_id in model.edges:
            self.saved_edge = model.edges[self.edge_id].to_dict()
            model.delete_edge(self.edge_id)
            return True
        return False

    def undo(self, model: UnifiedModel):
        if self.saved_edge:
            edge = Edge.from_dict(self.saved_edge)
            model.edges[edge.id] = edge
            if edge.id >= model.next_edge_id:
                model.next_edge_id = edge.id + 1


# ============================================================================
# TABLE VIEW COMPONENTS (da wire_editor.py)
# ============================================================================

class CoordinateInputPanel(QGroupBox):
    """Pannello input coordinate per UnifiedModel"""

    node_added = pyqtSignal(int)  # Segnale quando aggiunto nodo

    def __init__(self, model: UnifiedModel, parent=None):
        super().__init__("Input Coordinate", parent)
        self.model = model
        self.setup_ui()

    def setup_ui(self):
        layout = QGridLayout()

        # Coordinate principali
        layout.addWidget(QLabel("X (m):"), 0, 0)
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-10000, 10000)
        self.x_spin.setDecimals(4)
        self.x_spin.setSingleStep(0.1)
        self.x_spin.setMinimumWidth(120)
        layout.addWidget(self.x_spin, 0, 1)

        layout.addWidget(QLabel("Y (m):"), 0, 2)
        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-10000, 10000)
        self.y_spin.setDecimals(4)
        self.y_spin.setSingleStep(0.1)
        self.y_spin.setMinimumWidth(120)
        layout.addWidget(self.y_spin, 0, 3)

        layout.addWidget(QLabel("Z (m):"), 1, 0)
        self.z_spin = QDoubleSpinBox()
        self.z_spin.setRange(-1000, 1000)
        self.z_spin.setDecimals(3)
        self.z_spin.setSingleStep(0.1)
        self.z_spin.setMinimumWidth(120)
        layout.addWidget(self.z_spin, 1, 1)

        # Livello
        layout.addWidget(QLabel("Livello:"), 1, 2)
        self.level_edit = QLineEdit()
        self.level_edit.setPlaceholderText("es: PT, P1, P2")
        self.level_edit.setMaximumWidth(120)
        layout.addWidget(self.level_edit, 1, 3)

        # Descrizione
        layout.addWidget(QLabel("Descrizione:"), 2, 0)
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Opzionale - es: Pilastro A1")
        layout.addWidget(self.desc_edit, 2, 1, 1, 3)

        # Pulsanti
        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("Aggiungi Nodo")
        self.add_btn.setDefault(True)
        self.add_btn.clicked.connect(self.add_node)
        button_layout.addWidget(self.add_btn)

        self.clear_btn = QPushButton("Reset")
        self.clear_btn.clicked.connect(self.clear_fields)
        button_layout.addWidget(self.clear_btn)

        layout.addLayout(button_layout, 3, 0, 1, 4)
        self.setLayout(layout)

        # Focus su X per input rapido
        self.x_spin.setFocus()

        # Enter per aggiungere
        self.desc_edit.returnPressed.connect(self.add_node)

    def add_node(self):
        """Aggiunge nodo usando Command pattern"""
        x = self.x_spin.value()
        y = self.y_spin.value()
        z = self.z_spin.value()
        description = self.desc_edit.text().strip()
        level = self.level_edit.text().strip()

        # Usa Command per undo/redo
        cmd = CreateNodeCommand(x, y, z, description, level, TopologyRole.FREE)
        node_id = self.model.execute_command(cmd)

        # Emetti segnale
        self.node_added.emit(node_id)

        # Incrementa automaticamente X per input sequenziale
        self.x_spin.setValue(x + 1.0)
        self.desc_edit.clear()
        self.x_spin.setFocus()

        return node_id

    def clear_fields(self):
        """Reset tutti i campi"""
        self.x_spin.setValue(0.0)
        self.y_spin.setValue(0.0)
        self.z_spin.setValue(0.0)
        self.level_edit.clear()
        self.desc_edit.clear()
        self.x_spin.setFocus()

    def keyPressEvent(self, event):
        """Enter = aggiungi nodo"""
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.add_node()
        super().keyPressEvent(event)


class CoordinateTable(QTableWidget):
    """Tabella coordinate con editing inline per UnifiedModel"""

    data_changed = pyqtSignal()  # Segnale quando dati cambiano

    def __init__(self, model: UnifiedModel, parent=None):
        super().__init__(parent)
        self.model = model
        self.setup_table()

    def setup_table(self):
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(['ID', 'X (m)', 'Y (m)', 'Z (m)', 'Livello', 'Descrizione'])

        # Configurazione header
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID fisso
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # X
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Y
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Z
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Livello
        header.setStretchLastSection(True)  # Descrizione espandibile

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)

        # Connetti modifiche
        self.cellChanged.connect(self.on_cell_changed)

    def refresh(self, filter_level: Optional[str] = None):
        """Aggiorna tabella completa con filtro opzionale per livello"""
        nodes = self.model.get_node_list()

        # Applica filtro livello se specificato
        if filter_level and filter_level != "Tutti":
            nodes = [n for n in nodes if n.level == filter_level]

        self.setRowCount(len(nodes))

        # Blocca segnali durante refresh
        self.blockSignals(True)

        for row, node in enumerate(nodes):
            # ID (solo lettura)
            id_item = QTableWidgetItem(str(node.id))
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(row, 0, id_item)

            # Coordinate (modificabili con precisione)
            self.setItem(row, 1, QTableWidgetItem(f"{node.x:.4f}"))
            self.setItem(row, 2, QTableWidgetItem(f"{node.y:.4f}"))
            self.setItem(row, 3, QTableWidgetItem(f"{node.z:.3f}"))

            # Livello
            self.setItem(row, 4, QTableWidgetItem(node.level))

            # Descrizione
            self.setItem(row, 5, QTableWidgetItem(node.description))

        self.blockSignals(False)
        self.data_changed.emit()

    def on_cell_changed(self, row: int, col: int):
        """Gestisce modifiche dirette in tabella usando Command pattern"""
        id_item = self.item(row, 0)
        if not id_item:
            return

        node_id = int(id_item.text())
        item = self.item(row, col)

        try:
            if col == 1:  # X
                cmd = UpdateNodeCommand(node_id, x=float(item.text()))
                self.model.execute_command(cmd)
            elif col == 2:  # Y
                cmd = UpdateNodeCommand(node_id, y=float(item.text()))
                self.model.execute_command(cmd)
            elif col == 3:  # Z
                cmd = UpdateNodeCommand(node_id, z=float(item.text()))
                self.model.execute_command(cmd)
            elif col == 4:  # Livello
                cmd = UpdateNodeCommand(node_id, level=item.text())
                self.model.execute_command(cmd)
            elif col == 5:  # Descrizione
                cmd = UpdateNodeCommand(node_id, description=item.text())
                self.model.execute_command(cmd)

            self.data_changed.emit()
        except ValueError as e:
            # Valore non valido, ripristina
            QMessageBox.warning(self, "Errore", f"Valore non valido: {e}")
            self.refresh()

    def keyPressEvent(self, event):
        """Elimina nodo con DEL"""
        if event.key() == Qt.Key_Delete:
            current_row = self.currentRow()
            if current_row >= 0:
                id_item = self.item(current_row, 0)
                if id_item:
                    node_id = int(id_item.text())
                    reply = QMessageBox.question(
                        self, 'Conferma Eliminazione',
                        f'Eliminare il nodo ID {node_id}?',
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        cmd = DeleteNodeCommand(node_id)
                        self.model.execute_command(cmd)
                        self.refresh()
                        self.data_changed.emit()
        super().keyPressEvent(event)


# ============================================================================
# MAIN WINDOW UNIFICATA
# ============================================================================

class UnifiedMainWindow(QMainWindow):
    """Finestra principale unificata con tab per diverse viste"""

    def __init__(self):
        super().__init__()
        self.model = UnifiedModel()
        self.setWindowTitle("Wire Editor Unified v6.0 - Arch. Michelangelo Bartolotta")
        self.setMinimumSize(1400, 900)

        self.setup_ui()
        self.setup_menus()
        self.setup_toolbar()
        self.setup_statusbar()

    def setup_ui(self):
        """Setup interfaccia con tab"""
        # Central widget con tab
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # Tab 1: Table View (da wire_editor.py)
        self.table_tab = QWidget()
        self.setup_table_tab()
        self.tabs.addTab(self.table_tab, "📊 Table View")

        # Tab 2: Canvas View (da wire_editor1.py)
        self.canvas_tab = QWidget()
        self.setup_canvas_tab()
        self.tabs.addTab(self.canvas_tab, "🎨 Canvas View")

        # Tab 3: 3D Visualization
        self.viz_tab = QWidget()
        self.setup_viz_tab()
        self.tabs.addTab(self.viz_tab, "📈 3D View")

        # Tab 4: Reports
        self.reports_tab = QWidget()
        self.setup_reports_tab()
        self.tabs.addTab(self.reports_tab, "📄 Reports")

        self.setCentralWidget(self.tabs)

    def setup_table_tab(self):
        """Setup tab vista tabellare (integrato da wire_editor.py)"""
        layout = QVBoxLayout()

        # Pannello input coordinate
        self.input_panel = CoordinateInputPanel(self.model)
        self.input_panel.node_added.connect(self.on_node_added)
        layout.addWidget(self.input_panel)

        # Tabella coordinate con filtro
        table_group = QGroupBox("Elenco Nodi")
        table_layout = QVBoxLayout()

        self.coord_table = CoordinateTable(self.model)
        self.coord_table.data_changed.connect(self.on_table_data_changed)
        table_layout.addWidget(self.coord_table)

        table_group.setLayout(table_layout)
        layout.addWidget(table_group)

        # Barra informazioni e filtri
        info_layout = QHBoxLayout()

        self.table_info_label = QLabel("Nodi: 0")
        self.table_info_label.setFont(QFont("Arial", 10, QFont.Bold))
        info_layout.addWidget(self.table_info_label)

        info_layout.addStretch()

        # Filtro livello
        info_layout.addWidget(QLabel("Filtro Livello:"))
        self.level_filter = QComboBox()
        self.level_filter.addItem("Tutti")
        self.level_filter.currentTextChanged.connect(self.on_level_filter_changed)
        self.level_filter.setMinimumWidth(120)
        info_layout.addWidget(self.level_filter)

        info_layout.addStretch()

        self.bounds_label = QLabel("")
        self.bounds_label.setFont(QFont("Arial", 9))
        info_layout.addWidget(self.bounds_label)

        layout.addLayout(info_layout)

        self.table_tab.setLayout(layout)

        # Refresh iniziale
        self.refresh_table_view()

    def setup_canvas_tab(self):
        """Setup tab canvas grafico"""
        layout = QVBoxLayout()

        # Placeholder per ora
        label = QLabel("Canvas View - Design grafico topologie")
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 16))
        layout.addWidget(label)

        info = QLabel("FASE 2: Qui verrà integrato WireEditor canvas da wire_editor1.py")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)

        self.canvas_tab.setLayout(layout)

    def setup_viz_tab(self):
        """Setup tab visualizzazione 3D"""
        layout = QVBoxLayout()

        # Placeholder per ora
        label = QLabel("3D Visualization - Vista matplotlib 3D")
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 16))
        layout.addWidget(label)

        if MATPLOTLIB_AVAILABLE:
            info = QLabel("FASE 3: Qui verrà integrato PlotDialog da wire_editor.py")
        else:
            info = QLabel("⚠️ Matplotlib non disponibile - installare con: pip install matplotlib")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)

        self.viz_tab.setLayout(layout)

    def setup_reports_tab(self):
        """Setup tab reports"""
        layout = QVBoxLayout()

        # Placeholder per ora
        label = QLabel("Reports - Export PDF/Excel, Statistiche")
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 16))
        layout.addWidget(label)

        info = QLabel("FASE 3: Export PDF, Excel, statistiche")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)

        self.reports_tab.setLayout(layout)

    def setup_menus(self):
        """Setup menu bar unificato"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('File')
        file_menu.addAction('New Project', self.new_project, 'Ctrl+N')
        file_menu.addSeparator()
        file_menu.addAction('Open...', self.open_file, 'Ctrl+O')
        file_menu.addAction('Save...', self.save_file, 'Ctrl+S')
        file_menu.addSeparator()
        file_menu.addAction('Exit', self.close, 'Ctrl+Q')

        # Edit menu
        edit_menu = menubar.addMenu('Edit')
        self.undo_action = edit_menu.addAction('Undo', self.undo, 'Ctrl+Z')
        self.redo_action = edit_menu.addAction('Redo', self.redo, 'Ctrl+Y')
        edit_menu.addSeparator()
        edit_menu.addAction('Project Info...', self.edit_metadata)

        # View menu
        view_menu = menubar.addMenu('View')
        view_menu.addAction('Table View', lambda: self.tabs.setCurrentIndex(0), 'Ctrl+1')
        view_menu.addAction('Canvas View', lambda: self.tabs.setCurrentIndex(1), 'Ctrl+2')
        view_menu.addAction('3D View', lambda: self.tabs.setCurrentIndex(2), 'Ctrl+3')
        view_menu.addAction('Reports', lambda: self.tabs.setCurrentIndex(3), 'Ctrl+4')

        # Help menu
        help_menu = menubar.addMenu('Help')
        help_menu.addAction('About', self.show_about)

        # Aggiorna stato undo/redo
        self.update_undo_redo_actions()

    def setup_toolbar(self):
        """Setup toolbar"""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        # Actions base
        toolbar.addAction("New", self.new_project)
        toolbar.addAction("Open", self.open_file)
        toolbar.addAction("Save", self.save_file)
        toolbar.addSeparator()
        toolbar.addAction("Undo", self.undo)
        toolbar.addAction("Redo", self.redo)

    def setup_statusbar(self):
        """Setup status bar"""
        self.status_label = QLabel("Ready - Wire Editor Unified v6.0")
        self.statusBar().addWidget(self.status_label)

        self.node_count_label = QLabel("Nodes: 0")
        self.statusBar().addPermanentWidget(self.node_count_label)

        self.edge_count_label = QLabel("Edges: 0")
        self.statusBar().addPermanentWidget(self.edge_count_label)

    def update_status(self):
        """Aggiorna status bar"""
        self.node_count_label.setText(f"Nodes: {len(self.model.nodes)}")
        self.edge_count_label.setText(f"Edges: {len(self.model.edges)}")

    def update_undo_redo_actions(self):
        """Aggiorna stato azioni undo/redo"""
        self.undo_action.setEnabled(self.model.can_undo())
        self.redo_action.setEnabled(self.model.can_redo())

        undo_count = len(self.model.undo_stack)
        redo_count = len(self.model.redo_stack)
        self.undo_action.setText(f"Undo ({undo_count})" if undo_count > 0 else "Undo")
        self.redo_action.setText(f"Redo ({redo_count})" if redo_count > 0 else "Redo")

    # === Slot menu ===

    def new_project(self):
        """Nuovo progetto"""
        if len(self.model.nodes) > 0 or len(self.model.edges) > 0:
            reply = QMessageBox.question(
                self, 'New Project',
                'Clear all data and start new project?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        self.model.clear()
        self.model.clear_undo_history()
        self.update_status()
        self.update_undo_redo_actions()
        QMessageBox.information(self, "New Project", "Project initialized")

    def open_file(self):
        """Apri file progetto"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "",
            "JSON Files (*.json);;All Files (*)"
        )

        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.model.from_dict(data)
                self.model.clear_undo_history()
                self.update_status()
                self.update_undo_redo_actions()
                QMessageBox.information(self, "Open Project",
                                      f"Project loaded from:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error",
                                   f"Cannot open file:\n{e}")

    def save_file(self):
        """Salva file progetto"""
        if not self.model.nodes and not self.model.edges:
            QMessageBox.warning(self, "Warning", "No data to save")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "project.json",
            "JSON Files (*.json);;All Files (*)"
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.model.to_dict(), f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "Save Project",
                                      f"Project saved to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error",
                                   f"Cannot save file:\n{e}")

    def undo(self):
        """Annulla ultima operazione"""
        if self.model.undo():
            self.update_status()
            self.update_undo_redo_actions()
        else:
            QMessageBox.information(self, "Undo", "Nothing to undo")

    def redo(self):
        """Ripristina operazione"""
        if self.model.redo():
            self.update_status()
            self.update_undo_redo_actions()
        else:
            QMessageBox.information(self, "Redo", "Nothing to redo")

    def edit_metadata(self):
        """Modifica metadata progetto"""
        # TODO: Implementare dialog metadata
        QMessageBox.information(self, "Project Info", "FASE 2: Metadata editor")

    def on_tab_changed(self, index: int):
        """Gestisce cambio tab"""
        tab_names = ["Table View", "Canvas View", "3D View", "Reports"]
        if index < len(tab_names):
            self.status_label.setText(f"Active: {tab_names[index]}")

    # === Callbacks Table View ===

    def on_node_added(self, node_id: int):
        """Callback quando aggiunto nodo"""
        self.refresh_table_view()
        self.update_status()
        self.update_undo_redo_actions()

    def on_table_data_changed(self):
        """Callback quando dati tabella cambiano"""
        self.refresh_table_view()
        self.update_status()
        self.update_undo_redo_actions()

    def on_level_filter_changed(self, level: str):
        """Gestisce cambio filtro livello"""
        self.coord_table.refresh(level if level != "Tutti" else None)
        self.update_table_info()

    def refresh_table_view(self):
        """Aggiorna vista tabellare completa"""
        current_filter = self.level_filter.currentText()
        self.coord_table.refresh(current_filter if current_filter != "Tutti" else None)

        # Aggiorna combo livelli
        self.level_filter.blockSignals(True)
        current_selection = self.level_filter.currentText()
        self.level_filter.clear()
        self.level_filter.addItem("Tutti")
        for level in self.model.get_levels():
            self.level_filter.addItem(level)
        # Ripristina selezione se esiste ancora
        index = self.level_filter.findText(current_selection)
        if index >= 0:
            self.level_filter.setCurrentIndex(index)
        self.level_filter.blockSignals(False)

        self.update_table_info()

    def update_table_info(self):
        """Aggiorna info tabella"""
        count = len(self.model.nodes)
        self.table_info_label.setText(f"Nodi: {count}")

        # Aggiorna bounds
        if count > 0:
            bounds = self.model.get_bounds()
            bounds_text = (f"Range: X({bounds['x_min']:.2f}÷{bounds['x_max']:.2f}) "
                          f"Y({bounds['y_min']:.2f}÷{bounds['y_max']:.2f}) "
                          f"Z({bounds['z_min']:.2f}÷{bounds['z_max']:.2f})")
            self.bounds_label.setText(bounds_text)
        else:
            self.bounds_label.setText("")

    def show_about(self):
        """Mostra informazioni"""
        about_text = f"""WIRE EDITOR UNIFIED v6.0

Applicazione integrata per gestione coordinate fili fissi
e design topologie strutturali.

Combina funzionalità di:
• wire_editor.py (input tabellare, import/export, reports)
• wire_editor1.py (canvas grafico, topologie)

Sviluppato per:
Arch. Michelangelo Bartolotta
Ordine Architetti Agrigento n. 1557

Librerie Opzionali:
Matplotlib: {"✓ Disponibile" if MATPLOTLIB_AVAILABLE else "✗ Non installato"}
Openpyxl: {"✓ Disponibile" if OPENPYXL_AVAILABLE else "✗ Non installato"}
Reportlab: {"✓ Disponibile" if REPORTLAB_AVAILABLE else "✗ Non installato"}
Ezdxf: {"✓ Disponibile" if EZDXF_AVAILABLE else "✗ Non installato"}

Versione: 6.0-beta (FASE 2 - TableView Integrato)
"""
        QMessageBox.about(self, "About", about_text)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Wire Editor Unified")
    app.setApplicationVersion("6.0-beta")
    app.setOrganizationName("Arch. Michelangelo Bartolotta")

    # Stile applicazione
    app.setStyleSheet("""
        QTabWidget::pane {
            border: 1px solid #cccccc;
            border-radius: 3px;
        }
        QTabBar::tab {
            background: #e0e0e0;
            padding: 8px 16px;
            margin-right: 2px;
            border: 1px solid #cccccc;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background: white;
            font-weight: bold;
        }
        QTabBar::tab:hover {
            background: #f0f0f0;
        }
    """)

    window = UnifiedMainWindow()
    window.show()

    sys.exit(app.exec_())
