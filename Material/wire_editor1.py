import sys
import json
import math
from datetime import datetime
from copy import deepcopy
from enum import Enum
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QPushButton, QVBoxLayout, 
    QHBoxLayout, QLabel, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit,
    QMessageBox, QStatusBar, QToolBar, QAction, QGroupBox, QGridLayout,
    QCheckBox, QLineEdit, QSplitter, QFrame, QScrollArea, QRadioButton,
    QButtonGroup, QSlider
)
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QIcon, QPixmap, QCursor
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal, QObject, QTimer


class Direction(Enum):
    """Direzioni cardinali per aggancio strutture"""
    NORTH = "N"
    EAST = "E"
    SOUTH = "S"
    WEST = "W"


class TopologyRole(Enum):
    """Ruoli topologici per nodi"""
    CORNER_TOP_LEFT = "corner_top_left"
    CORNER_TOP_RIGHT = "corner_top_right"
    CORNER_BOTTOM_LEFT = "corner_bottom_left"
    CORNER_BOTTOM_RIGHT = "corner_bottom_right"
    EDGE_TOP_CENTER = "edge_top_center"
    EDGE_BOTTOM_CENTER = "edge_bottom_center"
    EDGE_LEFT_CENTER = "edge_left_center"
    EDGE_RIGHT_CENTER = "edge_right_center"
    CENTER = "center"


class AttachmentProfile:
    """Profilo di aggancio per nodi strutturali"""
    
    TOPOLOGY_PROFILES = {
        TopologyRole.CORNER_TOP_LEFT: {
            "allowed_dirs": [Direction.EAST, Direction.SOUTH],
            "port_pref_order": [Direction.EAST, Direction.SOUTH],
            "orthogonal_only": True
        },
        TopologyRole.CORNER_TOP_RIGHT: {
            "allowed_dirs": [Direction.WEST, Direction.SOUTH],
            "port_pref_order": [Direction.WEST, Direction.SOUTH],
            "orthogonal_only": True
        },
        TopologyRole.CORNER_BOTTOM_LEFT: {
            "allowed_dirs": [Direction.EAST, Direction.NORTH],
            "port_pref_order": [Direction.EAST, Direction.NORTH],
            "orthogonal_only": True
        },
        TopologyRole.CORNER_BOTTOM_RIGHT: {
            "allowed_dirs": [Direction.WEST, Direction.NORTH],
            "port_pref_order": [Direction.WEST, Direction.NORTH],
            "orthogonal_only": True
        },
        TopologyRole.EDGE_TOP_CENTER: {
            "allowed_dirs": [Direction.EAST, Direction.WEST],
            "port_pref_order": [Direction.EAST, Direction.WEST],
            "orthogonal_only": True
        },
        TopologyRole.EDGE_BOTTOM_CENTER: {
            "allowed_dirs": [Direction.EAST, Direction.WEST],
            "port_pref_order": [Direction.EAST, Direction.WEST],
            "orthogonal_only": True
        },
        TopologyRole.EDGE_LEFT_CENTER: {
            "allowed_dirs": [Direction.NORTH, Direction.SOUTH],
            "port_pref_order": [Direction.NORTH, Direction.SOUTH],
            "orthogonal_only": True
        },
        TopologyRole.EDGE_RIGHT_CENTER: {
            "allowed_dirs": [Direction.NORTH, Direction.SOUTH],
            "port_pref_order": [Direction.NORTH, Direction.SOUTH],
            "orthogonal_only": True
        },
        TopologyRole.CENTER: {
            "allowed_dirs": [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST],
            "port_pref_order": [Direction.EAST, Direction.WEST, Direction.NORTH, Direction.SOUTH],
            "orthogonal_only": False
        }
    }
    
    def __init__(self, topology_role=TopologyRole.CENTER, snap_radius_m=0.15, max_edges_per_port=None):
        self.topology_role = topology_role
        self.snap_radius_m = snap_radius_m
        self.max_edges_per_port = max_edges_per_port
        
        profile = self.TOPOLOGY_PROFILES.get(topology_role, self.TOPOLOGY_PROFILES[TopologyRole.CENTER])
        self.allowed_dirs = profile["allowed_dirs"]
        self.port_pref_order = profile["port_pref_order"]
        self.orthogonal_only = profile["orthogonal_only"]
    
    def to_dict(self):
        return {
            "allowed_dirs": [d.value for d in self.allowed_dirs],
            "port_pref_order": [d.value for d in self.port_pref_order],
            "snap_radius_m": self.snap_radius_m,
            "orthogonal_only": self.orthogonal_only,
            "max_edges_per_port": self.max_edges_per_port
        }
    
    @classmethod
    def from_dict(cls, data):
        allowed_dirs = [Direction(d) for d in data.get("allowed_dirs", ["N","E","S","W"])]
        port_pref_order = [Direction(d) for d in data.get("port_pref_order", ["E","W","N","S"])]
        
        profile = cls()
        profile.allowed_dirs = allowed_dirs
        profile.port_pref_order = port_pref_order
        profile.snap_radius_m = data.get("snap_radius_m", 0.15)
        profile.orthogonal_only = data.get("orthogonal_only", True)
        profile.max_edges_per_port = data.get("max_edges_per_port", None)
        return profile


class CommandHistory:
    """Gestione Undo/Redo per le operazioni di modellazione"""
    
    def __init__(self, max_size=50):
        self.commands = []
        self.current_index = -1
        self.max_size = max_size
    
    def execute(self, command):
        """Esegue un comando e lo aggiunge alla storia"""
        if self.current_index < len(self.commands) - 1:
            self.commands = self.commands[:self.current_index + 1]
        
        self.commands.append(command)
        self.current_index += 1
        
        if len(self.commands) > self.max_size:
            self.commands.pop(0)
            self.current_index -= 1
        
        command.execute()
    
    def undo(self):
        """Annulla l'ultimo comando"""
        if self.can_undo():
            self.commands[self.current_index].undo()
            self.current_index -= 1
            return True
        return False
    
    def redo(self):
        """Ripristina il comando successivo"""
        if self.can_redo():
            self.current_index += 1
            self.commands[self.current_index].execute()
            return True
        return False
    
    def can_undo(self):
        return self.current_index >= 0
    
    def can_redo(self):
        return self.current_index < len(self.commands) - 1
    
    def clear(self):
        self.commands.clear()
        self.current_index = -1


class Command:
    """Classe base per i comandi undo/redo"""
    
    def __init__(self, editor, description=""):
        self.editor = editor
        self.description = description
    
    def execute(self):
        pass
    
    def undo(self):
        pass


class CreateNodeCommand(Command):
    def __init__(self, editor, node_data, description="Crea nodo"):
        super().__init__(editor, description)
        self.node_data = deepcopy(node_data)
        self.created_id = None
    
    def execute(self):
        self.created_id = self.editor._create_node_internal(self.node_data)
        self.editor.update()
        self.editor.mark_modified()
    
    def undo(self):
        if self.created_id:
            self.editor._remove_node_internal(self.created_id)
            self.editor.update()
            self.editor.mark_modified()


class CreateMultiNodeCommand(Command):
    """Comando per creazione multipla di nodi (es. croce centrale)"""
    
    def __init__(self, editor, nodes_data, description="Crea nodi"):
        super().__init__(editor, description)
        self.nodes_data = [deepcopy(node) for node in nodes_data]
        self.created_ids = []
    
    def execute(self):
        self.created_ids = []
        for node_data in self.nodes_data:
            node_id = self.editor._create_node_internal(node_data)
            self.created_ids.append(node_id)
        self.editor.update()
        self.editor.mark_modified()
    
    def undo(self):
        for node_id in self.created_ids:
            self.editor._remove_node_internal(node_id)
        self.created_ids = []
        self.editor.update()
        self.editor.mark_modified()


class UpdateNodeCommand(Command):
    def __init__(self, editor, node_id, old_data, new_data, description="Aggiorna nodo"):
        super().__init__(editor, description)
        self.node_id = node_id
        self.old_data = deepcopy(old_data)
        self.new_data = deepcopy(new_data)
    
    def execute(self):
        self.editor._update_node_internal(self.node_id, self.new_data)
        self.editor.update()
        self.editor.mark_modified()
    
    def undo(self):
        self.editor._update_node_internal(self.node_id, self.old_data)
        self.editor.update()
        self.editor.mark_modified()


class DeleteNodeCommand(Command):
    def __init__(self, editor, node_data, affected_edges, description="Elimina nodo"):
        super().__init__(editor, description)
        self.node_data = deepcopy(node_data)
        self.affected_edges = deepcopy(affected_edges)
    
    def execute(self):
        self.editor._remove_node_internal(self.node_data['id'])
        self.editor.update()
        self.editor.mark_modified()
    
    def undo(self):
        self.editor._restore_node_internal(self.node_data)
        for edge in self.affected_edges:
            self.editor._restore_edge_internal(edge)
        self.editor.update()
        self.editor.mark_modified()


class CreateEdgeCommand(Command):
    def __init__(self, editor, edge_data, description="Crea arco"):
        super().__init__(editor, description)
        self.edge_data = deepcopy(edge_data)
        self.created_id = None
    
    def execute(self):
        self.created_id = self.editor._create_edge_internal(self.edge_data)
        self.editor.update()
        self.editor.mark_modified()
    
    def undo(self):
        if self.created_id:
            self.editor._remove_edge_internal(self.created_id)
            self.editor.update()
            self.editor.mark_modified()


class UpdateEdgeCommand(Command):
    def __init__(self, editor, edge_id, old_data, new_data, description="Aggiorna arco"):
        super().__init__(editor, description)
        self.edge_id = edge_id
        self.old_data = deepcopy(old_data)
        self.new_data = deepcopy(new_data)
    
    def execute(self):
        self.editor._update_edge_internal(self.edge_id, self.new_data)
        self.editor.update()
        self.editor.mark_modified()
    
    def undo(self):
        self.editor._update_edge_internal(self.edge_id, self.old_data)
        self.editor.update()
        self.editor.mark_modified()


class DeleteEdgeCommand(Command):
    def __init__(self, editor, edge_data, description="Elimina arco"):
        super().__init__(editor, description)
        self.edge_data = deepcopy(edge_data)
    
    def execute(self):
        self.editor._remove_edge_internal(self.edge_data['id'])
        self.editor.update()
        self.editor.mark_modified()
    
    def undo(self):
        self.editor._restore_edge_internal(self.edge_data)
        self.editor.update()
        self.editor.mark_modified()


class WireEditor(QWidget):
    """
    Editor per modelli wireframe architettonici con sistema di tipologie e navigazione avanzata
    """
    
    # Segnali
    selection_changed = pyqtSignal(str, dict)
    node_updated = pyqtSignal(dict)
    edge_updated = pyqtSignal(dict)
    status_message = pyqtSignal(str)
    view_changed = pyqtSignal(float, QPointF)  # zoom, pan_offset
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes = []
        self.edges = []
        self.selected_node = None
        self.selected_edge = None
        
        # Contatori ID robusti
        self.next_node_id = 1
        self.next_edge_id = 1
        
        # Vista e navigazione
        self.zoom_factor = 1.0
        self.pan_offset = QPointF(0, 0)
        self.zoom_min = 0.05
        self.zoom_max = 16.0
        self.zoom_step_base = 0.10
        self.invert_wheel = False
        self.zoom_to_cursor = True
        
        # Parametri visualizzazione
        self.node_radius = 6
        self.grid_size = 50  # pixel per metro base
        self.show_grid = True
        self.show_coordinates = True
        self.show_measurements = True
        self.show_ports = False
        self.snap_enabled = True
        self.snap_step = 0.10
        self.zoom_on_new_element = True
        
        # Parametri interazione
        self.dragging = False
        self.panning = False
        self.creating_edge = False
        self.start_node = None
        self.drag_offset = QPointF(0, 0)
        self.last_mouse_pos = QPointF(0, 0)
        self.pan_mode = False
        self.orthogonal_override = False
        
        # Zoom box
        self.zoom_box_active = False
        self.zoom_box_start = QPointF(0, 0)
        self.zoom_box_end = QPointF(0, 0)
        
        # Stili
        self.node_color = QColor(0, 100, 200)
        self.edge_color = QColor(50, 50, 50)
        self.selected_color = QColor(255, 100, 100)
        self.grid_color = QColor(200, 200, 200)
        self.locked_color = QColor(150, 150, 150)
        self.port_color = QColor(0, 150, 0)
        
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Comando History
        self.command_history = CommandHistory()
        
        # Metadata progetto
        self.project_metadata = {
            "author": "Arch. Michelangelo Bartolotta",
            "registration": "Ordine Architetti Agrigento n. 1557",
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat(),
            "units": "meters",
            "scale": "1:100",
            "project_name": "",
            "description": ""
        }

    def mark_modified(self):
        """Marca il progetto come modificato"""
        self.project_metadata["modified"] = datetime.now().isoformat()

    def get_effective_grid_size(self):
        """Restituisce la dimensione griglia effettiva con zoom"""
        return self.grid_size * self.zoom_factor

    def screen_to_world(self, screen_point):
        """Converte coordinate schermo in coordinate mondo (metri)"""
        adjusted_point = (screen_point - self.pan_offset) / self.zoom_factor
        x = adjusted_point.x() / self.grid_size
        y = (self.height() - adjusted_point.y()) / self.grid_size
        return QPointF(x, y)

    def world_to_screen(self, world_point):
        """Converte coordinate mondo in coordinate schermo"""
        x = world_point.x() * self.grid_size
        y = self.height() - (world_point.y() * self.grid_size)
        screen_point = QPointF(x, y) * self.zoom_factor + self.pan_offset
        return screen_point

    def snap_to_grid(self, point):
        """Aggancia il punto alla griglia se abilitato"""
        if not self.snap_enabled:
            return point
        x = round(point.x() / self.snap_step) * self.snap_step
        y = round(point.y() / self.snap_step) * self.snap_step
        return QPointF(x, y)

    def get_direction_from_vector(self, vector):
        """Determina la direzione cardinale da un vettore"""
        if abs(vector.x()) > abs(vector.y()):
            return Direction.EAST if vector.x() > 0 else Direction.WEST
        else:
            return Direction.NORTH if vector.y() > 0 else Direction.SOUTH

    def is_direction_allowed(self, node, direction):
        """Verifica se una direzione è ammessa per un nodo"""
        if not node:
            return True
        
        attachment = self.get_node_attachment_profile(node)
        return direction in attachment.allowed_dirs

    def get_node_attachment_profile(self, node):
        """Ottiene il profilo di aggancio di un nodo"""
        topology_role_str = node.get('topology_role', 'center')
        try:
            topology_role = TopologyRole(topology_role_str)
        except ValueError:
            topology_role = TopologyRole.CENTER
        
        if 'attachment_profile' in node:
            return AttachmentProfile.from_dict(node['attachment_profile'])
        else:
            return AttachmentProfile(topology_role)

    def get_port_position(self, node, direction):
        """Calcola la posizione della porta per una direzione"""
        world_pos = QPointF(node['x'], node['y'])
        screen_pos = self.world_to_screen(world_pos)
        
        attachment = self.get_node_attachment_profile(node)
        offset_pixels = attachment.snap_radius_m * self.get_effective_grid_size()
        
        if direction == Direction.NORTH:
            return screen_pos + QPointF(0, -offset_pixels)
        elif direction == Direction.EAST:
            return screen_pos + QPointF(offset_pixels, 0)
        elif direction == Direction.SOUTH:
            return screen_pos + QPointF(0, offset_pixels)
        elif direction == Direction.WEST:
            return screen_pos + QPointF(-offset_pixels, 0)
        
        return screen_pos

    def get_node_at(self, screen_point, tolerance=10):
        """Trova il nodo più vicino al punto specificato"""
        for node in self.nodes:
            world_pos = QPointF(node['x'], node['y'])
            screen_pos = self.world_to_screen(world_pos)
            dx = screen_pos.x() - screen_point.x()
            dy = screen_pos.y() - screen_point.y()
            distance = math.sqrt(dx*dx + dy*dy)
            if distance <= tolerance:
                return node
        return None

    def get_edge_at(self, screen_point, tolerance=5):
        """Trova l'arco più vicino al punto specificato"""
        for edge in self.edges:
            n1 = self.find_node_by_id(edge['from'])
            n2 = self.find_node_by_id(edge['to'])
            
            if not n1 or not n2:
                continue
            
            p1 = self.world_to_screen(QPointF(n1['x'], n1['y']))
            p2 = self.world_to_screen(QPointF(n2['x'], n2['y']))
            
            distance = self.point_to_line_distance(screen_point, p1, p2)
            if distance <= tolerance:
                return edge
        return None

    def point_to_line_distance(self, point, line_start, line_end):
        """Calcola la distanza punto-linea"""
        line_vec = line_end - line_start
        point_vec = point - line_start
        
        line_len = math.sqrt(line_vec.x()**2 + line_vec.y()**2)
        if line_len == 0:
            return math.sqrt(point_vec.x()**2 + point_vec.y()**2)
        
        line_unitvec = QPointF(line_vec.x() / line_len, line_vec.y() / line_len)
        proj_length = point_vec.x() * line_unitvec.x() + point_vec.y() * line_unitvec.y()
        
        if proj_length < 0:
            return math.sqrt(point_vec.x()**2 + point_vec.y()**2)
        elif proj_length > line_len:
            end_vec = point - line_end
            return math.sqrt(end_vec.x()**2 + end_vec.y()**2)
        else:
            proj = QPointF(line_start.x() + proj_length * line_unitvec.x(),
                          line_start.y() + proj_length * line_unitvec.y())
            perp_vec = point - proj
            return math.sqrt(perp_vec.x()**2 + perp_vec.y()**2)

    def find_node_by_id(self, node_id):
        """Trova un nodo per ID"""
        for node in self.nodes:
            if node['id'] == node_id:
                return node
        return None

    def find_edge_by_id(self, edge_id):
        """Trova un arco per ID"""
        for edge in self.edges:
            if edge['id'] == edge_id:
                return edge
        return None

    def find_edge_between_nodes(self, from_id, to_id):
        """Trova un arco tra due nodi (bidirezionale)"""
        for edge in self.edges:
            if ((edge['from'] == from_id and edge['to'] == to_id) or
                (edge['from'] == to_id and edge['to'] == from_id)):
                return edge
        return None

    def calculate_edge_length(self, edge):
        """Calcola la lunghezza di un arco in metri"""
        n1 = self.find_node_by_id(edge['from'])
        n2 = self.find_node_by_id(edge['to'])
        
        if not n1 or not n2:
            return 0.0
            
        dx = n2['x'] - n1['x']
        dy = n2['y'] - n1['y']
        return round(math.sqrt(dx*dx + dy*dy), 4)

    def focus_on_node(self, node_id):
        """Centra la vista su un nodo specifico"""
        node = self.find_node_by_id(node_id)
        if node:
            self.selected_node = node
            self.selected_edge = None
            self.selection_changed.emit("node", node)
            
            if self.zoom_on_new_element:
                self.center_on_point(QPointF(node['x'], node['y']))
            
            self.update()
            return True
        return False

    def focus_on_edge(self, from_id, to_id):
        """Centra la vista su un arco specifico"""
        edge = self.find_edge_between_nodes(from_id, to_id)
        if edge:
            self.selected_edge = edge
            self.selected_node = None
            self.selection_changed.emit("edge", edge)
            self.update()
            return True
        return False

    def center_on_point(self, world_point):
        """Centra la vista su un punto in coordinate mondo"""
        screen_center = QPointF(self.width() / 2, self.height() / 2)
        target_screen = self.world_to_screen(world_point)
        self.pan_offset += screen_center - target_screen
        self.view_changed.emit(self.zoom_factor, self.pan_offset)

    def zoom_at_point(self, screen_point, zoom_delta):
        """Zoom centrato su un punto specifico"""
        if not self.zoom_to_cursor:
            screen_point = QPointF(self.width() / 2, self.height() / 2)
        
        old_zoom = self.zoom_factor
        
        if zoom_delta > 0:
            self.zoom_factor *= (1.0 + self.zoom_step_base)
        else:
            self.zoom_factor *= (1.0 - self.zoom_step_base)
        
        self.zoom_factor = max(self.zoom_min, min(self.zoom_max, self.zoom_factor))
        
        if old_zoom != self.zoom_factor:
            # Aggiusta il pan per mantenere il punto sotto il mouse
            zoom_ratio = self.zoom_factor / old_zoom
            adjusted_point = screen_point - self.pan_offset
            self.pan_offset = screen_point - adjusted_point * zoom_ratio
            
            self.view_changed.emit(self.zoom_factor, self.pan_offset)
            self.update()

    def fit_to_extents(self):
        """Adatta la vista a tutti gli elementi"""
        if not self.nodes:
            return
        
        xs = [node['x'] for node in self.nodes]
        ys = [node['y'] for node in self.nodes]
        
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        
        margin = 2.0  # metri di margine
        x_min -= margin
        x_max += margin
        y_min -= margin
        y_max += margin
        
        world_width = x_max - x_min
        world_height = y_max - y_min
        
        if world_width <= 0 or world_height <= 0:
            return
        
        # Calcola zoom per contenere tutto
        zoom_x = self.width() / (world_width * self.grid_size)
        zoom_y = self.height() / (world_height * self.grid_size)
        self.zoom_factor = min(zoom_x, zoom_y)
        self.zoom_factor = max(self.zoom_min, min(self.zoom_max, self.zoom_factor))
        
        # Centra
        world_center = QPointF((x_min + x_max) / 2, (y_min + y_max) / 2)
        self.center_on_point(world_center)

    def zoom_to_selection(self):
        """Adatta la vista alla selezione corrente"""
        if self.selected_node:
            self.center_on_point(QPointF(self.selected_node['x'], self.selected_node['y']))
        elif self.selected_edge:
            n1 = self.find_node_by_id(self.selected_edge['from'])
            n2 = self.find_node_by_id(self.selected_edge['to'])
            if n1 and n2:
                center = QPointF((n1['x'] + n2['x']) / 2, (n1['y'] + n2['y']) / 2)
                self.center_on_point(center)

    def reset_view(self):
        """Ripristina la vista ai valori di default"""
        self.zoom_factor = 1.0
        self.pan_offset = QPointF(0, 0)
        self.view_changed.emit(self.zoom_factor, self.pan_offset)
        self.update()

    def set_zoom_100(self):
        """Imposta zoom al 100% (1:1)"""
        screen_center = QPointF(self.width() / 2, self.height() / 2)
        world_center = self.screen_to_world(screen_center)
        
        self.zoom_factor = 1.0
        self.center_on_point(world_center)

    # Metodi interni per operazioni sui dati
    def _create_node_internal(self, node_data):
        """Crea un nodo internamente (usato dai comandi)"""
        node_data['id'] = self.next_node_id
        self.next_node_id += 1
        
        # Assicura che il nodo abbia un profilo di aggancio
        if 'topology_role' not in node_data:
            node_data['topology_role'] = TopologyRole.CENTER.value
        
        if 'attachment_profile' not in node_data:
            try:
                topology_role = TopologyRole(node_data['topology_role'])
                attachment = AttachmentProfile(topology_role)
                node_data['attachment_profile'] = attachment.to_dict()
            except ValueError:
                attachment = AttachmentProfile(TopologyRole.CENTER)
                node_data['attachment_profile'] = attachment.to_dict()
        
        self.nodes.append(node_data)
        return node_data['id']

    def _update_node_internal(self, node_id, new_data):
        """Aggiorna un nodo internamente"""
        node = self.find_node_by_id(node_id)
        if node:
            original_id = node['id']
            node.clear()
            node.update(new_data)
            node['id'] = original_id

    def _remove_node_internal(self, node_id):
        """Rimuove un nodo internamente"""
        edges_to_remove = [e['id'] for e in self.edges 
                          if e['from'] == node_id or e['to'] == node_id]
        for edge_id in edges_to_remove:
            self._remove_edge_internal(edge_id)
        
        self.nodes = [n for n in self.nodes if n['id'] != node_id]
        
        if self.selected_node and self.selected_node['id'] == node_id:
            self.selected_node = None

    def _restore_node_internal(self, node_data):
        """Ripristina un nodo internamente"""
        self.nodes.append(deepcopy(node_data))
        if node_data['id'] >= self.next_node_id:
            self.next_node_id = node_data['id'] + 1

    def _create_edge_internal(self, edge_data):
        """Crea un arco internamente"""
        edge_data['id'] = self.next_edge_id
        self.next_edge_id += 1
        self.edges.append(edge_data)
        return edge_data['id']

    def _update_edge_internal(self, edge_id, new_data):
        """Aggiorna un arco internamente"""
        edge = self.find_edge_by_id(edge_id)
        if edge:
            original_id = edge['id']
            edge.clear()
            edge.update(new_data)
            edge['id'] = original_id

    def _remove_edge_internal(self, edge_id):
        """Rimuove un arco internamente"""
        self.edges = [e for e in self.edges if e['id'] != edge_id]
        if self.selected_edge and self.selected_edge['id'] == edge_id:
            self.selected_edge = None

    def _restore_edge_internal(self, edge_data):
        """Ripristina un arco internamente"""
        self.edges.append(deepcopy(edge_data))
        if edge_data['id'] >= self.next_edge_id:
            self.next_edge_id = edge_data['id'] + 1

    # Metodi pubblici per operazioni con comandi
    def create_node_at(self, x, y, elevation=0.0, node_type='junction', description='', 
                      locked=False, topology_role=TopologyRole.CENTER):
        """Crea un nuovo nodo alle coordinate specificate"""
        if self.snap_enabled:
            world_pos = self.snap_to_grid(QPointF(x, y))
        else:
            world_pos = QPointF(x, y)
        
        # Controlla se esiste già un nodo nella posizione
        tolerance_m = 0.05  # 5cm di tolleranza
        for existing_node in self.nodes:
            existing_pos = QPointF(existing_node['x'], existing_node['y'])
            distance = math.sqrt((world_pos.x() - existing_pos.x())**2 + 
                               (world_pos.y() - existing_pos.y())**2)
            if distance < tolerance_m:
                self.status_message.emit(f"Nodo esistente trovato a {distance*1000:.1f}mm di distanza")
                return existing_node['id']
        
        attachment = AttachmentProfile(topology_role)
        
        node_data = {
            'x': world_pos.x(),
            'y': world_pos.y(),
            'type': node_type,
            'elevation': elevation,
            'description': description or f'Nodo {self.next_node_id}',
            'locked': locked,
            'topology_role': topology_role.value,
            'attachment_profile': attachment.to_dict()
        }
        
        command = CreateNodeCommand(self, node_data, f"Crea nodo ({world_pos.x():.3f}, {world_pos.y():.3f})")
        self.command_history.execute(command)
        
        # Seleziona il nuovo nodo
        new_node = self.find_node_by_id(command.created_id)
        if new_node:
            self.selected_node = new_node
            self.selected_edge = None
            self.selection_changed.emit("node", new_node)
            
            if self.zoom_on_new_element:
                self.center_on_point(world_pos)
        
        self.status_message.emit(f"Nodo creato: ID {command.created_id}")
        return command.created_id

    def create_nodes_from_topology_box(self, box_rect, margin, topology_positions):
        """Crea più nodi da un riquadro e tipologie specificate"""
        xl, yb, xr, yt = box_rect.left(), box_rect.bottom(), box_rect.right(), box_rect.top()
        
        # Applica margine
        xl_m = xl + margin
        xr_m = xr - margin
        yb_m = yb + margin
        yt_m = yt - margin
        
        if xl_m >= xr_m or yb_m >= yt_m:
            self.status_message.emit("Errore: Margine troppo grande per il riquadro")
            return []
        
        xm = (xl + xr) / 2
        ym = (yb + yt) / 2
        
        # Mappatura posizioni
        position_map = {
            TopologyRole.CORNER_TOP_LEFT: (xl_m, yt_m),
            TopologyRole.CORNER_TOP_RIGHT: (xr_m, yt_m),
            TopologyRole.CORNER_BOTTOM_LEFT: (xl_m, yb_m),
            TopologyRole.CORNER_BOTTOM_RIGHT: (xr_m, yb_m),
            TopologyRole.EDGE_TOP_CENTER: (xm, yt_m),
            TopologyRole.EDGE_BOTTOM_CENTER: (xm, yb_m),
            TopologyRole.EDGE_LEFT_CENTER: (xl_m, ym),
            TopologyRole.EDGE_RIGHT_CENTER: (xr_m, ym),
            TopologyRole.CENTER: (xm, ym)
        }
        
        nodes_data = []
        tolerance_m = 0.05
        
        for topology_role in topology_positions:
            if topology_role not in position_map:
                continue
                
            x, y = position_map[topology_role]
            
            # Controlla se esiste già un nodo
            node_exists = False
            for existing_node in self.nodes:
                distance = math.sqrt((x - existing_node['x'])**2 + (y - existing_node['y'])**2)
                if distance < tolerance_m:
                    node_exists = True
                    break
            
            if not node_exists:
                attachment = AttachmentProfile(topology_role)
                node_data = {
                    'x': x,
                    'y': y,
                    'type': 'junction',
                    'elevation': 0.0,
                    'description': f'Nodo {topology_role.value}',
                    'locked': False,
                    'topology_role': topology_role.value,
                    'attachment_profile': attachment.to_dict(),
                    'topology_box': {'xl': xl, 'yb': yb, 'xr': xr, 'yt': yt, 'margin': margin}
                }
                nodes_data.append(node_data)
        
        if nodes_data:
            command = CreateMultiNodeCommand(self, nodes_data, f"Crea {len(nodes_data)} nodi topologici")
            self.command_history.execute(command)
            self.status_message.emit(f"{len(nodes_data)} nodi creati")
            return command.created_ids
        else:
            self.status_message.emit("Nessun nuovo nodo creato (posizioni già occupate)")
            return []

    def update_node(self, node_id, **kwargs):
        """Aggiorna le proprietà di un nodo"""
        node = self.find_node_by_id(node_id)
        if not node:
            self.status_message.emit(f"Errore: Nodo ID {node_id} non trovato")
            return False
        
        old_data = deepcopy(node)
        new_data = deepcopy(node)
        
        # Gestione speciale per topology_role
        if 'topology_role' in kwargs:
            topology_role = kwargs['topology_role']
            if isinstance(topology_role, str):
                try:
                    topology_role = TopologyRole(topology_role)
                except ValueError:
                    topology_role = TopologyRole.CENTER
            
            # Aggiorna il profilo di aggancio se cambia la tipologia
            attachment = AttachmentProfile(topology_role)
            new_data['topology_role'] = topology_role.value
            new_data['attachment_profile'] = attachment.to_dict()
        
        # Applica snap se necessario per le coordinate
        if 'x' in kwargs or 'y' in kwargs:
            x = kwargs.get('x', node['x'])
            y = kwargs.get('y', node['y'])
            if self.snap_enabled:
                snapped = self.snap_to_grid(QPointF(x, y))
                kwargs['x'] = snapped.x()
                kwargs['y'] = snapped.y()
        
        new_data.update(kwargs)
        
        command = UpdateNodeCommand(self, node_id, old_data, new_data, f"Aggiorna nodo {node_id}")
        self.command_history.execute(command)
        
        updated_node = self.find_node_by_id(node_id)
        if updated_node:
            self.node_updated.emit(updated_node)
        
        self.status_message.emit(f"Nodo {node_id} aggiornato")
        return True

    def move_node_relative(self, node_id, dx, dy):
        """Sposta un nodo relativamente"""
        node = self.find_node_by_id(node_id)
        if not node:
            return False
        
        if node.get('locked', False):
            self.status_message.emit(f"Nodo {node_id} è bloccato")
            return False
        
        new_x = node['x'] + dx
        new_y = node['y'] + dy
        return self.update_node(node_id, x=new_x, y=new_y)

    def duplicate_node(self, node_id, offset_x=0.5, offset_y=0.5):
        """Duplica un nodo con offset"""
        node = self.find_node_by_id(node_id)
        if not node:
            return None
        
        new_x = node['x'] + offset_x
        new_y = node['y'] + offset_y
        
        topology_role_str = node.get('topology_role', TopologyRole.CENTER.value)
        try:
            topology_role = TopologyRole(topology_role_str)
        except ValueError:
            topology_role = TopologyRole.CENTER
        
        return self.create_node_at(
            new_x, new_y,
            elevation=node.get('elevation', 0.0),
            node_type=node.get('type', 'junction'),
            description=f"{node.get('description', '')} (copia)",
            locked=False,
            topology_role=topology_role
        )

    def delete_selected_node(self):
        """Elimina il nodo selezionato"""
        if not self.selected_node:
            return False
        
        node_data = deepcopy(self.selected_node)
        affected_edges = [deepcopy(e) for e in self.edges 
                         if e['from'] == node_data['id'] or e['to'] == node_data['id']]
        
        command = DeleteNodeCommand(self, node_data, affected_edges, f"Elimina nodo {node_data['id']}")
        self.command_history.execute(command)
        
        self.selected_node = None
        self.selection_changed.emit("none", {})
        self.status_message.emit(f"Nodo {node_data['id']} eliminato")
        return True

    def create_edge_between(self, from_id, to_id, edge_type='structural', material='acciaio'):
        """Crea un arco tra due nodi con validazione delle direzioni"""
        # Validazioni base
        if from_id == to_id:
            self.status_message.emit("Errore: impossibile creare arco su stesso nodo")
            return None
        
        n1 = self.find_node_by_id(from_id)
        n2 = self.find_node_by_id(to_id)
        if not n1 or not n2:
            self.status_message.emit("Errore: uno o entrambi i nodi non esistono")
            return None
        
        # Controlla duplicati
        if self.find_edge_between_nodes(from_id, to_id):
            self.status_message.emit("Errore: arco già esistente tra questi nodi")
            return None
        
        # Validazione direzioni se non in override
        if not self.orthogonal_override:
            # Calcola direzione dell'arco
            dx = n2['x'] - n1['x']
            dy = n2['y'] - n1['y']
            
            if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                self.status_message.emit("Errore: nodi coincidenti")
                return None
            
            vector = QPointF(dx, dy)
            direction_from = self.get_direction_from_vector(vector)
            direction_to = self.get_direction_from_vector(QPointF(-dx, -dy))
            
            # Verifica direzioni ammesse
            if not self.is_direction_allowed(n1, direction_from):
                attachment1 = self.get_node_attachment_profile(n1)
                if attachment1.orthogonal_only:
                    self.status_message.emit(f"Direzione {direction_from.value} non ammessa per nodo {from_id}. "
                                           f"Usa Alt per override o cambia tipologia.")
                    return None
            
            if not self.is_direction_allowed(n2, direction_to):
                attachment2 = self.get_node_attachment_profile(n2)
                if attachment2.orthogonal_only:
                    self.status_message.emit(f"Direzione {direction_to.value} non ammessa per nodo {to_id}. "
                                           f"Usa Alt per override o cambia tipologia.")
                    return None
        
        edge_data = {
            'from': from_id,
            'to': to_id,
            'type': edge_type,
            'material': material
        }
        
        command = CreateEdgeCommand(self, edge_data, f"Crea arco {from_id}-{to_id}")
        self.command_history.execute(command)
        
        # Seleziona il nuovo arco
        new_edge = self.find_edge_by_id(command.created_id)
        if new_edge:
            self.selected_edge = new_edge
            self.selected_node = None
            self.selection_changed.emit("edge", new_edge)
        
        self.status_message.emit(f"Arco creato: ID {command.created_id}")
        return command.created_id

    def update_edge(self, edge_id, **kwargs):
        """Aggiorna le proprietà di un arco"""
        edge = self.find_edge_by_id(edge_id)
        if not edge:
            self.status_message.emit(f"Errore: Arco ID {edge_id} non trovato")
            return False
        
        old_data = deepcopy(edge)
        new_data = deepcopy(edge)
        new_data.update(kwargs)
        
        command = UpdateEdgeCommand(self, edge_id, old_data, new_data, f"Aggiorna arco {edge_id}")
        self.command_history.execute(command)
        
        updated_edge = self.find_edge_by_id(edge_id)
        if updated_edge:
            self.edge_updated.emit(updated_edge)
        
        self.status_message.emit(f"Arco {edge_id} aggiornato")
        return True

    def invert_edge(self, edge_id):
        """Inverte la direzione di un arco"""
        edge = self.find_edge_by_id(edge_id)
        if not edge:
            return False
        
        return self.update_edge(edge_id, **{'from': edge['to'], 'to': edge['from']})

    def delete_selected_edge(self):
        """Elimina l'arco selezionato"""
        if not self.selected_edge:
            return False
        
        edge_data = deepcopy(self.selected_edge)
        command = DeleteEdgeCommand(self, edge_data, f"Elimina arco {edge_data['id']}")
        self.command_history.execute(command)
        
        self.selected_edge = None
        self.selection_changed.emit("none", {})
        self.status_message.emit(f"Arco {edge_data['id']} eliminato")
        return True

    def undo(self):
        """Annulla l'ultima operazione"""
        if self.command_history.undo():
            self.status_message.emit("Operazione annullata")
            return True
        else:
            self.status_message.emit("Nessuna operazione da annullare")
            return False

    def redo(self):
        """Ripristina l'operazione successiva"""
        if self.command_history.redo():
            self.status_message.emit("Operazione ripristinata")
            return True
        else:
            self.status_message.emit("Nessuna operazione da ripristinare")
            return False

    def mousePressEvent(self, event):
        self.last_mouse_pos = event.localPos()
        
        if event.button() == Qt.LeftButton:
            # Override ortogonale con Alt
            self.orthogonal_override = event.modifiers() & Qt.AltModifier
            
            if self.zoom_box_active:
                self.zoom_box_start = event.localPos()
                self.zoom_box_end = event.localPos()
                return
            
            if self.pan_mode or (event.modifiers() & Qt.ShiftModifier):
                self.panning = True
                self.setCursor(Qt.ClosedHandCursor)
                return
            
            clicked_node = self.get_node_at(event.localPos())
            clicked_edge = self.get_edge_at(event.localPos())
            
            if event.modifiers() & Qt.ControlModifier:
                # Modalità creazione arco
                if clicked_node:
                    if not self.creating_edge:
                        self.start_node = clicked_node
                        self.creating_edge = True
                        self.status_message.emit(f"Modalità arco attivata: da nodo {clicked_node['id']}")
                    else:
                        if clicked_node != self.start_node:
                            self.create_edge_between(self.start_node['id'], clicked_node['id'])
                        self.creating_edge = False
                        self.start_node = None
                        
            elif clicked_node:
                # Selezione/trascinamento nodo
                if not clicked_node.get('locked', False):
                    self.selected_node = clicked_node
                    self.selected_edge = None
                    self.dragging = True
                    screen_pos = self.world_to_screen(QPointF(clicked_node['x'], clicked_node['y']))
                    self.drag_offset = event.localPos() - screen_pos
                    self.selection_changed.emit("node", clicked_node)
                else:
                    self.status_message.emit(f"Nodo {clicked_node['id']} è bloccato")
                
            elif clicked_edge:
                # Selezione arco
                self.selected_edge = clicked_edge
                self.selected_node = None
                self.selection_changed.emit("edge", clicked_edge)
                
            else:
                # Creazione nuovo nodo
                world_pos = self.screen_to_world(event.localPos())
                self.create_node_at(world_pos.x(), world_pos.y())
                
        elif event.button() == Qt.MiddleButton:
            self.panning = True
            self.setCursor(Qt.ClosedHandCursor)
            
        elif event.button() == Qt.RightButton:
            # Annulla modalità creazione arco
            if self.creating_edge:
                self.creating_edge = False
                self.start_node = None
                self.status_message.emit("Modalità arco annullata")
            
        self.update()

    def mouseMoveEvent(self, event):
        if self.zoom_box_active:
            self.zoom_box_end = event.localPos()
            self.update()
            return
        
        if self.panning:
            delta = event.localPos() - self.last_mouse_pos
            self.pan_offset += delta
            self.view_changed.emit(self.zoom_factor, self.pan_offset)
            self.update()
        
        elif self.dragging and self.selected_node and not self.selected_node.get('locked', False):
            new_screen_pos = event.localPos() - self.drag_offset
            new_world_pos = self.screen_to_world(new_screen_pos)
            
            # Aggiorna posizione temporaneamente
            self.selected_node['x'] = new_world_pos.x()
            self.selected_node['y'] = new_world_pos.y()
            self.update()
        
        # Aggiorna coordinate cursore
        world_pos = self.screen_to_world(event.localPos())
        cursor_text = f"({world_pos.x():.3f}, {world_pos.y():.3f})"
        self.status_message.emit(f"Scala: {self.zoom_factor*100:.0f}% | Cursore: {cursor_text} | Snap: {'on' if self.snap_enabled else 'off'}")
        
        self.last_mouse_pos = event.localPos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.zoom_box_active:
                # Completa zoom box
                rect = QRectF(self.zoom_box_start, self.zoom_box_end).normalized()
                if rect.width() > 10 and rect.height() > 10:
                    self.zoom_to_rect(rect)
                self.zoom_box_active = False
                self.update()
                return
            
            if self.dragging and self.selected_node:
                # Applica snap finale
                if self.snap_enabled:
                    snapped_pos = self.snap_to_grid(QPointF(self.selected_node['x'], self.selected_node['y']))
                    self.selected_node['x'] = snapped_pos.x()
                    self.selected_node['y'] = snapped_pos.y()
                
                self.mark_modified()
                self.node_updated.emit(self.selected_node)
                
            self.dragging = False
            
        if self.panning:
            self.panning = False
            self.setCursor(Qt.ArrowCursor)

    def wheelEvent(self, event):
        """Gestione zoom con rotellina"""
        angle_delta = event.angleDelta().y()
        if self.invert_wheel:
            angle_delta = -angle_delta
        
        # Modifica step con modificatori
        zoom_step = self.zoom_step_base
        if event.modifiers() & Qt.ControlModifier:
            zoom_step *= 0.2  # Fine
        elif event.modifiers() & Qt.ShiftModifier:
            zoom_step *= 2.5  # Rapido
        
        old_step = self.zoom_step_base
        self.zoom_step_base = zoom_step
        
        if angle_delta > 0:
            self.zoom_at_point(event.posF(), 1)
        else:
            self.zoom_at_point(event.posF(), -1)
            
        self.zoom_step_base = old_step

    def zoom_to_rect(self, screen_rect):
        """Zoom per adattare un rettangolo in coordinate schermo"""
        world_tl = self.screen_to_world(screen_rect.topLeft())
        world_br = self.screen_to_world(screen_rect.bottomRight())
        
        world_width = abs(world_br.x() - world_tl.x())
        world_height = abs(world_br.y() - world_tl.y())
        
        if world_width <= 0 or world_height <= 0:
            return
        
        zoom_x = self.width() / (world_width * self.grid_size)
        zoom_y = self.height() / (world_height * self.grid_size)
        self.zoom_factor = min(zoom_x, zoom_y) * 0.9  # 90% per margine
        self.zoom_factor = max(self.zoom_min, min(self.zoom_max, self.zoom_factor))
        
        world_center = QPointF((world_tl.x() + world_br.x()) / 2, (world_tl.y() + world_br.y()) / 2)
        self.center_on_point(world_center)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            if self.selected_node:
                self.delete_selected_node()
            elif self.selected_edge:
                self.delete_selected_edge()
                
        elif event.key() == Qt.Key_Escape:
            self.creating_edge = False
            self.start_node = None
            self.selected_node = None
            self.selected_edge = None
            self.zoom_box_active = False
            self.selection_changed.emit("none", {})
            self.update()
            
        elif event.key() == Qt.Key_Z and event.modifiers() & Qt.ControlModifier:
            if event.modifiers() & Qt.ShiftModifier:
                self.redo()
            else:
                self.undo()
                
        elif event.key() == Qt.Key_N:
            self.selection_changed.emit("new_node_request", {})
            
        elif event.key() == Qt.Key_E and self.selected_node:
            self.selection_changed.emit("new_edge_request", {"from_id": self.selected_node['id']})
            
        elif event.key() == Qt.Key_L and self.selected_node:
            locked = not self.selected_node.get('locked', False)
            self.update_node(self.selected_node['id'], locked=locked)
            
        elif event.key() == Qt.Key_Space:
            self.pan_mode = True
            self.setCursor(Qt.OpenHandCursor)
            
        elif event.key() == Qt.Key_F:
            if event.modifiers() & Qt.ShiftModifier:
                self.zoom_to_selection()
            else:
                self.fit_to_extents()
                
        elif event.key() == Qt.Key_1 and not event.modifiers():
            self.set_zoom_100()
            
        elif event.key() == Qt.Key_Z and not event.modifiers():
            self.zoom_box_active = True
            self.setCursor(Qt.CrossCursor)
            
        # Shortcuts per tipologie di nodi
        elif event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_1:  # Angolo alto sinistro
                self.selection_changed.emit("topology_request", {"role": TopologyRole.CORNER_TOP_LEFT})
            elif event.key() == Qt.Key_2:  # Angolo alto destro
                self.selection_changed.emit("topology_request", {"role": TopologyRole.CORNER_TOP_RIGHT})
            elif event.key() == Qt.Key_3:  # Angolo basso destro
                self.selection_changed.emit("topology_request", {"role": TopologyRole.CORNER_BOTTOM_RIGHT})
            elif event.key() == Qt.Key_4:  # Angolo basso sinistro
                self.selection_changed.emit("topology_request", {"role": TopologyRole.CORNER_BOTTOM_LEFT})
            elif event.key() == Qt.Key_5:  # Alto centrale
                self.selection_changed.emit("topology_request", {"role": TopologyRole.EDGE_TOP_CENTER})
            elif event.key() == Qt.Key_6:  # Destro centrale
                self.selection_changed.emit("topology_request", {"role": TopologyRole.EDGE_RIGHT_CENTER})
            elif event.key() == Qt.Key_7:  # Basso centrale
                self.selection_changed.emit("topology_request", {"role": TopologyRole.EDGE_BOTTOM_CENTER})
            elif event.key() == Qt.Key_8:  # Sinistro centrale
                self.selection_changed.emit("topology_request", {"role": TopologyRole.EDGE_LEFT_CENTER})
            elif event.key() == Qt.Key_9:  # Centro
                self.selection_changed.emit("topology_request", {"role": TopologyRole.CENTER})
            elif event.key() == Qt.Key_0:  # Croce centrale
                self.selection_changed.emit("topology_request", {"role": "center_cross"})

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.pan_mode = False
            self.setCursor(Qt.ArrowCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Sfondo
        painter.fillRect(self.rect(), Qt.white)
        
        # Griglia
        if self.show_grid:
            self.draw_grid(painter)
        
        # Archi
        self.draw_edges(painter)
        
        # Nodi
        self.draw_nodes(painter)
        
        # Zoom box
        if self.zoom_box_active:
            painter.setPen(QPen(Qt.blue, 1, Qt.DashLine))
            painter.setBrush(QBrush(QColor(0, 0, 255, 30)))
            rect = QRectF(self.zoom_box_start, self.zoom_box_end)
            painter.drawRect(rect)
        
        # Feedback modalità creazione arco
        if self.creating_edge and self.start_node:
            painter.setPen(QPen(self.selected_color, 2, Qt.DashLine))
            start_pos = self.world_to_screen(QPointF(self.start_node['x'], self.start_node['y']))
            override_text = " (Override attivo)" if self.orthogonal_override else ""
            painter.drawText(10, 20, f"Modalità arco da nodo {self.start_node['id']}{override_text}")

    def draw_grid(self, painter):
        """Disegna la griglia di riferimento adattiva"""
        effective_grid = self.get_effective_grid_size()
        
        # Griglia adattiva: riduce densità con zoom-out
        if effective_grid < 10:
            grid_step = 5  # Ogni 5 metri
        elif effective_grid < 25:
            grid_step = 1  # Ogni metro
        else:
            grid_step = 1  # Normale
        
        painter.setPen(QPen(self.grid_color, 1))
        
        # Calcola limiti visibili
        top_left = self.screen_to_world(QPointF(0, 0))
        bottom_right = self.screen_to_world(QPointF(self.width(), self.height()))
        
        x_start = math.floor(top_left.x() / grid_step) * grid_step
        x_end = math.ceil(bottom_right.x() / grid_step) * grid_step
        y_start = math.floor(bottom_right.y() / grid_step) * grid_step
        y_end = math.ceil(top_left.y() / grid_step) * grid_step
        
        # Linee verticali
        x = x_start
        while x <= x_end:
            screen_x = int(self.world_to_screen(QPointF(x, 0)).x())
            painter.drawLine(screen_x, 0, screen_x, self.height())
            
            # Linee principali ogni 5 unità
            if abs(x % (grid_step * 5)) < 0.001:
                painter.setPen(QPen(self.grid_color.darker(120), 1))
                painter.drawLine(screen_x, 0, screen_x, self.height())
                painter.setPen(QPen(self.grid_color, 1))
            
            x += grid_step
        
        # Linee orizzontali
        y = y_start
        while y <= y_end:
            screen_y = int(self.world_to_screen(QPointF(0, y)).y())
            painter.drawLine(0, screen_y, self.width(), screen_y)
            
            if abs(y % (grid_step * 5)) < 0.001:
                painter.setPen(QPen(self.grid_color.darker(120), 1))
                painter.drawLine(0, screen_y, self.width(), screen_y)
                painter.setPen(QPen(self.grid_color, 1))
            
            y += grid_step

    def draw_edges(self, painter):
        """Disegna gli archi con gestione sicura degli ID orfani"""
        orphaned_edges = []
        valid_edges = []
        
        for edge in self.edges:
            n1 = self.find_node_by_id(edge['from'])
            n2 = self.find_node_by_id(edge['to'])
            
            if not n1 or not n2:
                orphaned_edges.append(edge)
            else:
                valid_edges.append((edge, n1, n2))
        
        # Rimuovi archi orfani
        if orphaned_edges:
            for orphaned in orphaned_edges:
                self.edges.remove(orphaned)
        
        # Disegna archi validi
        for edge, n1, n2 in valid_edges:
            p1 = self.world_to_screen(QPointF(n1['x'], n1['y']))
            p2 = self.world_to_screen(QPointF(n2['x'], n2['y']))
            
            color = self.selected_color if edge == self.selected_edge else self.edge_color
            painter.setPen(QPen(color, 2))
            painter.drawLine(p1, p2)
            
            # Etichetta lunghezza
            if self.show_measurements and self.zoom_factor > 0.5:
                length = self.calculate_edge_length(edge)
                mid_point = QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)
                painter.setPen(QPen(Qt.black, 1))
                painter.setFont(QFont("Arial", max(8, int(8 * self.zoom_factor))))
                painter.drawText(mid_point, f"{length:.3f}m")

    def draw_nodes(self, painter):
        """Disegna i nodi con porte se richiesto"""
        effective_radius = max(4, self.node_radius * self.zoom_factor)
        
        for node in self.nodes:
            screen_pos = self.world_to_screen(QPointF(node['x'], node['y']))
            
            # Colore nodo
            locked = node.get('locked', False)
            if locked:
                color = self.locked_color
            elif node == self.selected_node:
                color = self.selected_color
            elif self.creating_edge and node == self.start_node:
                color = QColor(255, 165, 0)
            else:
                color = self.node_color
                
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.black, 1))
            painter.drawEllipse(screen_pos, effective_radius, effective_radius)
            
            # Porte di aggancio
            if self.show_ports and self.zoom_factor > 0.3:
                attachment = self.get_node_attachment_profile(node)
                painter.setPen(QPen(self.port_color, 2))
                
                for direction in attachment.allowed_dirs:
                    port_pos = self.get_port_position(node, direction)
                    port_size = 3 * self.zoom_factor
                    painter.drawRect(port_pos.x() - port_size/2, port_pos.y() - port_size/2, 
                                   port_size, port_size)
            
            # Indicatore lock
            if locked:
                painter.setPen(QPen(Qt.red, 2))
                lock_size = max(2, 3 * self.zoom_factor)
                painter.drawRect(screen_pos.x() - lock_size, screen_pos.y() - lock_size, 
                               lock_size * 2, lock_size * 2)
            
            # Etichetta nodo
            if self.zoom_factor > 0.4:
                painter.setPen(QPen(Qt.black, 1))
                font_size = max(7, int(9 * self.zoom_factor))
                painter.setFont(QFont("Arial", font_size, QFont.Bold))
                label_pos = QPointF(screen_pos.x() + effective_radius + 2, 
                                   screen_pos.y() - effective_radius - 2)
                painter.drawText(label_pos, str(node['id']))
                
                # Coordinate
                if self.show_coordinates and self.zoom_factor > 0.6:
                    painter.setFont(QFont("Arial", max(6, int(7 * self.zoom_factor))))
                    coord_text = f"({node['x']:.3f}, {node['y']:.3f})"
                    coord_pos = QPointF(screen_pos.x() + effective_radius + 2, 
                                       screen_pos.y() + effective_radius + 12)
                    painter.drawText(coord_pos, coord_text)

    def clear_model(self):
        """Pulisce il modello"""
        self.nodes.clear()
        self.edges.clear()
        self.selected_node = None
        self.selected_edge = None
        self.creating_edge = False
        self.start_node = None
        self.next_node_id = 1
        self.next_edge_id = 1
        self.command_history.clear()
        self.selection_changed.emit("none", {})
        self.update()

    def export_json(self):
        """Esporta il modello in formato JSON esteso"""
        if not self.nodes:
            QMessageBox.warning(self, "Attenzione", "Nessun elemento da salvare.")
            return False

        self.mark_modified()
        self.project_metadata["node_count"] = len(self.nodes)
        self.project_metadata["edge_count"] = len(self.edges)

        total_length = sum(self.calculate_edge_length(edge) for edge in self.edges)
        self.project_metadata["total_length"] = round(total_length, 4)

        data = {
            "metadata": self.project_metadata,
            "nodes": self.nodes,
            "edges": self.edges,
            "settings": {
                "grid_size": self.grid_size,
                "show_grid": self.show_grid,
                "show_coordinates": self.show_coordinates,
                "show_measurements": self.show_measurements,
                "show_ports": self.show_ports,
                "snap_enabled": self.snap_enabled,
                "snap_step": self.snap_step,
                "zoom_on_new_element": self.zoom_on_new_element,
                "view_state": {
                    "zoom_factor": self.zoom_factor,
                    "pan_offset": {"tx": self.pan_offset.x(), "ty": self.pan_offset.y()},
                    "zoom_min": self.zoom_min,
                    "zoom_max": self.zoom_max,
                    "invert_wheel": self.invert_wheel,
                    "zoom_step_base": self.zoom_step_base,
                    "zoom_to_cursor": self.zoom_to_cursor
                },
                "id_counters": {
                    "next_node_id": self.next_node_id,
                    "next_edge_id": self.next_edge_id
                }
            }
        }

        filename, _ = QFileDialog.getSaveFileName(
            self, "Salva modello wireframe", "modello_wireframe.json", 
            "File JSON (*.json);;Tutti i file (*)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "Successo", f"Modello salvato:\n{filename}")
                return True
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Errore durante il salvataggio:\n{str(e)}")
                return False
        return False

    def import_json(self, filename):
        """Importa un modello da file JSON esteso"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.clear_model()
            
            if 'metadata' in data:
                self.project_metadata.update(data['metadata'])
            
            if 'nodes' in data:
                self.nodes = data['nodes']
                for node in self.nodes:
                    node.setdefault('locked', False)
                    node.setdefault('elevation', 0.0)
                    node.setdefault('type', 'junction')
                    node.setdefault('description', f"Nodo {node['id']}")
                    node.setdefault('topology_role', TopologyRole.CENTER.value)
                    
                    # Assicura profilo di aggancio
                    if 'attachment_profile' not in node:
                        try:
                            topology_role = TopologyRole(node['topology_role'])
                            attachment = AttachmentProfile(topology_role)
                            node['attachment_profile'] = attachment.to_dict()
                        except ValueError:
                            attachment = AttachmentProfile(TopologyRole.CENTER)
                            node['attachment_profile'] = attachment.to_dict()
            
            if 'edges' in data:
                self.edges = data['edges']
                for edge in self.edges:
                    edge.setdefault('type', 'structural')
                    edge.setdefault('material', 'acciaio')
                
            if 'settings' in data:
                settings = data['settings']
                self.grid_size = settings.get('grid_size', 50)
                self.show_grid = settings.get('show_grid', True)
                self.show_coordinates = settings.get('show_coordinates', True)
                self.show_measurements = settings.get('show_measurements', True)
                self.show_ports = settings.get('show_ports', False)
                self.snap_enabled = settings.get('snap_enabled', True)
                self.snap_step = settings.get('snap_step', 0.10)
                self.zoom_on_new_element = settings.get('zoom_on_new_element', True)
                
                # Stato vista
                view_state = settings.get('view_state', {})
                self.zoom_factor = view_state.get('zoom_factor', 1.0)
                pan_offset = view_state.get('pan_offset', {'tx': 0.0, 'ty': 0.0})
                self.pan_offset = QPointF(pan_offset['tx'], pan_offset['ty'])
                self.zoom_min = view_state.get('zoom_min', 0.05)
                self.zoom_max = view_state.get('zoom_max', 16.0)
                self.invert_wheel = view_state.get('invert_wheel', False)
                self.zoom_step_base = view_state.get('zoom_step_base', 0.10)
                self.zoom_to_cursor = view_state.get('zoom_to_cursor', True)
                
                # Contatori ID
                id_counters = settings.get('id_counters', {})
                self.next_node_id = id_counters.get('next_node_id', 1)
                self.next_edge_id = id_counters.get('next_edge_id', 1)
                
                # Verifica e correggi contatori
                if self.nodes:
                    max_node_id = max(node['id'] for node in self.nodes)
                    if max_node_id >= self.next_node_id:
                        self.next_node_id = max_node_id + 1
                        
                if self.edges:
                    max_edge_id = max(edge.get('id', 0) for edge in self.edges)
                    if max_edge_id >= self.next_edge_id:
                        self.next_edge_id = max_edge_id + 1
            
            self.command_history.clear()
            self.view_changed.emit(self.zoom_factor, self.pan_offset)
            self.update()
            QMessageBox.information(self, "Successo", f"Modello caricato:\n{filename}")
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore durante il caricamento:\n{str(e)}")
            return False


class TopologyPanel(QGroupBox):
    """Pannello per tipologie di nodi strutturali"""
    
    def __init__(self, parent=None):
        super().__init__("Tipologia Nodo", parent)
        self.editor = None
        self.topology_buttons = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # === RIQUADRO DI RIFERIMENTO ===
        ref_group = QGroupBox("Riquadro di Riferimento")
        ref_layout = QGridLayout()
        
        row = 0
        ref_layout.addWidget(QLabel("Fonte:"), row, 0)
        self.source_combo = QComboBox()
        self.source_combo.addItems([
            "Bounding box selezione",
            "Rettangolo da 2 punti",
            "Cella di griglia corrente"
        ])
        ref_layout.addWidget(self.source_combo, row, 1)
        
        row += 1
        ref_layout.addWidget(QLabel("X min (m):"), row, 0)
        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(-10000, 10000)
        self.x_min_spin.setDecimals(3)
        self.x_min_spin.setValue(-2.0)
        ref_layout.addWidget(self.x_min_spin, row, 1)
        
        row += 1
        ref_layout.addWidget(QLabel("Y min (m):"), row, 0)
        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(-10000, 10000)
        self.y_min_spin.setDecimals(3)
        self.y_min_spin.setValue(-2.0)
        ref_layout.addWidget(self.y_min_spin, row, 1)
        
        row += 1
        ref_layout.addWidget(QLabel("X max (m):"), row, 0)
        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(-10000, 10000)
        self.x_max_spin.setDecimals(3)
        self.x_max_spin.setValue(2.0)
        ref_layout.addWidget(self.x_max_spin, row, 1)
        
        row += 1
        ref_layout.addWidget(QLabel("Y max (m):"), row, 0)
        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(-10000, 10000)
        self.y_max_spin.setDecimals(3)
        self.y_max_spin.setValue(2.0)
        ref_layout.addWidget(self.y_max_spin, row, 1)
        
        row += 1
        ref_layout.addWidget(QLabel("Margine (m):"), row, 0)
        self.margin_spin = QDoubleSpinBox()
        self.margin_spin.setRange(0, 10)
        self.margin_spin.setDecimals(3)
        self.margin_spin.setValue(0.0)
        ref_layout.addWidget(self.margin_spin, row, 1)
        
        row += 1
        bbox_btn = QPushButton("Usa Bounding Box Selezione")
        bbox_btn.clicked.connect(self.use_selection_bbox)
        ref_layout.addWidget(bbox_btn, row, 0, 1, 2)
        
        ref_group.setLayout(ref_layout)
        layout.addWidget(ref_group)
        
        # === TIPOLOGIE DI POSIZIONE ===
        pos_group = QGroupBox("Tipologia di Posizione")
        pos_layout = QGridLayout()
        
        # Griglia 3x3 per posizioni
        positions = [
            ("AS", "Angolo alto sinistro", TopologyRole.CORNER_TOP_LEFT, 0, 0),
            ("AC", "Alto centrale", TopologyRole.EDGE_TOP_CENTER, 0, 1),
            ("AD", "Angolo alto destro", TopologyRole.CORNER_TOP_RIGHT, 0, 2),
            ("LSC", "Laterale sinistro", TopologyRole.EDGE_LEFT_CENTER, 1, 0),
            ("C", "Centrale", TopologyRole.CENTER, 1, 1),
            ("LDC", "Laterale destro", TopologyRole.EDGE_RIGHT_CENTER, 1, 2),
            ("BS", "Angolo basso sinistro", TopologyRole.CORNER_BOTTOM_LEFT, 2, 0),
            ("BC", "Basso centrale", TopologyRole.EDGE_BOTTOM_CENTER, 2, 1),
            ("BD", "Angolo basso destro", TopologyRole.CORNER_BOTTOM_RIGHT, 2, 2)
        ]
        
        self.button_group = QButtonGroup()
        for abbr, desc, role, row, col in positions:
            btn = QRadioButton(abbr)
            btn.setToolTip(desc)
            btn.role = role
            pos_layout.addWidget(btn, row, col)
            self.button_group.addButton(btn)
            self.topology_buttons[role] = btn
        
        # Preset croce centrale
        cross_btn = QPushButton("Croce Centrale (5 nodi)")
        cross_btn.clicked.connect(self.create_center_cross)
        pos_layout.addWidget(cross_btn, 3, 0, 1, 3)
        
        pos_group.setLayout(pos_layout)
        layout.addWidget(pos_group)
        
        # === METADATI NODO ===
        meta_group = QGroupBox("Metadati Nodo")
        meta_layout = QGridLayout()
        
        meta_layout.addWidget(QLabel("Tipo:"), 0, 0)
        self.meta_type_combo = QComboBox()
        self.meta_type_combo.addItems(['junction', 'support', 'anchor', 'load_point'])
        meta_layout.addWidget(self.meta_type_combo, 0, 1)
        
        meta_layout.addWidget(QLabel("Quota (m):"), 1, 0)
        self.meta_elevation_spin = QDoubleSpinBox()
        self.meta_elevation_spin.setRange(-1000, 1000)
        self.meta_elevation_spin.setDecimals(3)
        meta_layout.addWidget(self.meta_elevation_spin, 1, 1)
        
        meta_layout.addWidget(QLabel("Descrizione:"), 2, 0)
        self.meta_desc_edit = QLineEdit()
        meta_layout.addWidget(self.meta_desc_edit, 2, 1)
        
        self.meta_locked_check = QCheckBox("Bloccato")
        meta_layout.addWidget(self.meta_locked_check, 3, 0, 1, 2)
        
        meta_group.setLayout(meta_layout)
        layout.addWidget(meta_group)
        
        # === AZIONI ===
        actions_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("Crea Nodo")
        self.create_btn.clicked.connect(self.create_node_from_topology)
        actions_layout.addWidget(self.create_btn)
        
        self.update_btn = QPushButton("Aggiorna Selezionato")
        self.update_btn.clicked.connect(self.update_selected_node)
        self.update_btn.setEnabled(False)
        actions_layout.addWidget(self.update_btn)
        
        layout.addLayout(actions_layout)
        
        # Seleziona centro di default
        self.topology_buttons[TopologyRole.CENTER].setChecked(True)
        
        self.setLayout(layout)

    def set_editor(self, editor):
        """Collega l'editor"""
        self.editor = editor
        editor.selection_changed.connect(self.on_selection_changed)

    def on_selection_changed(self, entity_type, payload):
        """Gestisce cambi di selezione"""
        if entity_type == "node":
            self.update_btn.setEnabled(True)
            # Aggiorna tipologia selezionata se disponibile
            topology_role_str = payload.get('topology_role', TopologyRole.CENTER.value)
            try:
                topology_role = TopologyRole(topology_role_str)
                if topology_role in self.topology_buttons:
                    self.topology_buttons[topology_role].setChecked(True)
            except ValueError:
                self.topology_buttons[TopologyRole.CENTER].setChecked(True)
        elif entity_type == "topology_request":
            # Shortcut da tastiera
            role = payload.get('role')
            if role == "center_cross":
                self.create_center_cross()
            elif isinstance(role, TopologyRole) and role in self.topology_buttons:
                self.topology_buttons[role].setChecked(True)
                self.create_node_from_topology()
        else:
            self.update_btn.setEnabled(False)

    def get_selected_topology(self):
        """Ottiene la tipologia selezionata"""
        for role, btn in self.topology_buttons.items():
            if btn.isChecked():
                return role
        return TopologyRole.CENTER

    def get_reference_box(self):
        """Calcola il riquadro di riferimento"""
        source = self.source_combo.currentText()
        
        if source == "Bounding box selezione":
            return self.calculate_selection_bbox()
        elif source == "Rettangolo da 2 punti":
            # Usa valori manualmente inseriti
            pass
        elif source == "Cella di griglia corrente":
            # Per ora usa valori manuali, implementare in futuro
            pass
        
        # Default: usa valori manuali
        x_min = self.x_min_spin.value()
        y_min = self.y_min_spin.value()
        x_max = self.x_max_spin.value()
        y_max = self.y_max_spin.value()
        
        if x_min >= x_max or y_min >= y_max:
            return None
            
        return QRectF(x_min, y_min, x_max - x_min, y_max - y_min)

    def calculate_selection_bbox(self):
        """Calcola bounding box della selezione"""
        if not self.editor or not self.editor.nodes:
            return None
        
        # Se c'è una selezione, usa quella; altrimenti tutti i nodi
        if self.editor.selected_node:
            nodes_to_consider = [self.editor.selected_node]
        else:
            nodes_to_consider = self.editor.nodes
            
        if len(nodes_to_consider) < 2:
            # Con un solo nodo, crea un riquadro centrato
            if nodes_to_consider:
                node = nodes_to_consider[0]
                size = 2.0  # 2m x 2m default
                return QRectF(node['x'] - size/2, node['y'] - size/2, size, size)
            return None
        
        xs = [node['x'] for node in nodes_to_consider]
        ys = [node['y'] for node in nodes_to_consider]
        
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        
        return QRectF(x_min, y_min, x_max - x_min, y_max - y_min)

    def use_selection_bbox(self):
        """Usa il bounding box della selezione"""
        bbox = self.calculate_selection_bbox()
        if bbox:
            self.x_min_spin.setValue(bbox.left())
            self.y_min_spin.setValue(bbox.bottom())
            self.x_max_spin.setValue(bbox.right())
            self.y_max_spin.setValue(bbox.top())
            self.editor.status_message.emit("Bounding box aggiornato dalla selezione")
        else:
            self.editor.status_message.emit("Selezione insufficiente per bounding box")

    def create_node_from_topology(self):
        """Crea un nodo dalla tipologia selezionata"""
        if not self.editor:
            return
        
        topology_role = self.get_selected_topology()
        box_rect = self.get_reference_box()
        
        if not box_rect:
            self.editor.status_message.emit("Errore: riquadro di riferimento non valido")
            return
        
        margin = self.margin_spin.value()
        node_ids = self.editor.create_nodes_from_topology_box(box_rect, margin, [topology_role])
        
        if node_ids:
            # Aggiorna metadati del nodo creato
            node_id = node_ids[0]
            self.editor.update_node(
                node_id,
                type=self.meta_type_combo.currentText(),
                elevation=self.meta_elevation_spin.value(),
                description=self.meta_desc_edit.text() or f"Nodo {topology_role.value}",
                locked=self.meta_locked_check.isChecked()
            )

    def update_selected_node(self):
        """Aggiorna il nodo selezionato con la tipologia scelta"""
        if not self.editor or not self.editor.selected_node:
            return
        
        topology_role = self.get_selected_topology()
        box_rect = self.get_reference_box()
        
        if not box_rect:
            self.editor.status_message.emit("Errore: riquadro di riferimento non valido")
            return
        
        # Calcola nuova posizione
        margin = self.margin_spin.value()
        xl, yb = box_rect.left() + margin, box_rect.bottom() + margin
        xr, yt = box_rect.right() - margin, box_rect.top() - margin
        xm, ym = (box_rect.left() + box_rect.right()) / 2, (box_rect.bottom() + box_rect.top()) / 2
        
        position_map = {
            TopologyRole.CORNER_TOP_LEFT: (xl, yt),
            TopologyRole.CORNER_TOP_RIGHT: (xr, yt),
            TopologyRole.CORNER_BOTTOM_LEFT: (xl, yb),
            TopologyRole.CORNER_BOTTOM_RIGHT: (xr, yb),
            TopologyRole.EDGE_TOP_CENTER: (xm, yt),
            TopologyRole.EDGE_BOTTOM_CENTER: (xm, yb),
            TopologyRole.EDGE_LEFT_CENTER: (xl, ym),
            TopologyRole.EDGE_RIGHT_CENTER: (xr, ym),
            TopologyRole.CENTER: (xm, ym)
        }
        
        if topology_role in position_map:
            x, y = position_map[topology_role]
            self.editor.update_node(
                self.editor.selected_node['id'],
                x=x, y=y,
                topology_role=topology_role
            )

    def create_center_cross(self):
        """Crea il preset croce centrale (5 nodi)"""
        if not self.editor:
            return
        
        box_rect = self.get_reference_box()
        if not box_rect:
            self.editor.status_message.emit("Errore: riquadro di riferimento non valido")
            return
        
        margin = self.margin_spin.value()
        cross_roles = [
            TopologyRole.CENTER,
            TopologyRole.EDGE_TOP_CENTER,
            TopologyRole.EDGE_BOTTOM_CENTER,
            TopologyRole.EDGE_LEFT_CENTER,
            TopologyRole.EDGE_RIGHT_CENTER
        ]
        
        node_ids = self.editor.create_nodes_from_topology_box(box_rect, margin, cross_roles)
        
        if node_ids:
            # Aggiorna metadati per tutti i nodi creati
            for node_id in node_ids:
                self.editor.update_node(
                    node_id,
                    type=self.meta_type_combo.currentText(),
                    elevation=self.meta_elevation_spin.value(),
                    locked=self.meta_locked_check.isChecked()
                )


class PropertyPanel(QScrollArea):
    """Pannello delle proprietà esteso con tipologie"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor = None
        self.updating_from_selection = False
        
        self.main_widget = QWidget()
        self.setWidget(self.main_widget)
        self.setWidgetResizable(True)
        self.setMinimumWidth(350)
        
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self.main_widget)
        
        # === PANNELLO TIPOLOGIA ===
        self.topology_panel = TopologyPanel()
        layout.addWidget(self.topology_panel)
        
        # === GESTORE NODI (versione compatta) ===
        self.node_manager_group = QGroupBox("Gestore Nodi")
        node_mgr_layout = QGridLayout()
        
        row = 0
        node_mgr_layout.addWidget(QLabel("ID:"), row, 0)
        self.node_id_label = QLabel("-")
        self.node_id_label.setStyleSheet("font-weight: bold; color: blue;")
        node_mgr_layout.addWidget(self.node_id_label, row, 1)
        
        row += 1
        node_mgr_layout.addWidget(QLabel("X (m):"), row, 0)
        self.node_x_spin = QDoubleSpinBox()
        self.node_x_spin.setRange(-10000, 10000)
        self.node_x_spin.setDecimals(4)
        self.node_x_spin.setSingleStep(0.01)
        self.node_x_spin.valueChanged.connect(self.on_node_field_changed)
        node_mgr_layout.addWidget(self.node_x_spin, row, 1)
        
        row += 1
        node_mgr_layout.addWidget(QLabel("Y (m):"), row, 0)
        self.node_y_spin = QDoubleSpinBox()
        self.node_y_spin.setRange(-10000, 10000)
        self.node_y_spin.setDecimals(4)
        self.node_y_spin.setSingleStep(0.01)
        self.node_y_spin.valueChanged.connect(self.on_node_field_changed)
        node_mgr_layout.addWidget(self.node_y_spin, row, 1)
        
        row += 1
        node_mgr_layout.addWidget(QLabel("Quota (m):"), row, 0)
        self.node_elevation_spin = QDoubleSpinBox()
        self.node_elevation_spin.setRange(-1000, 1000)
        self.node_elevation_spin.setDecimals(3)
        self.node_elevation_spin.valueChanged.connect(self.on_node_field_changed)
        node_mgr_layout.addWidget(self.node_elevation_spin, row, 1)
        
        row += 1
        node_mgr_layout.addWidget(QLabel("Tipo:"), row, 0)
        self.node_type_combo = QComboBox()
        self.node_type_combo.addItems(['junction', 'support', 'anchor', 'load_point'])
        self.node_type_combo.currentTextChanged.connect(self.on_node_field_changed)
        node_mgr_layout.addWidget(self.node_type_combo, row, 1)
        
        row += 1
        node_mgr_layout.addWidget(QLabel("Descrizione:"), row, 0)
        self.node_desc_edit = QLineEdit()
        self.node_desc_edit.textChanged.connect(self.on_node_field_changed)
        node_mgr_layout.addWidget(self.node_desc_edit, row, 1)
        
        row += 1
        self.node_locked_check = QCheckBox("Bloccato (no drag)")
        self.node_locked_check.toggled.connect(self.on_node_field_changed)
        node_mgr_layout.addWidget(self.node_locked_check, row, 0, 1, 2)
        
        # Pulsanti
        row += 1
        node_buttons_layout = QHBoxLayout()
        
        self.new_node_btn = QPushButton("Nuovo Nodo")
        self.new_node_btn.clicked.connect(self.create_new_node)
        node_buttons_layout.addWidget(self.new_node_btn)
        
        self.update_node_btn = QPushButton("Aggiorna")
        self.update_node_btn.clicked.connect(self.update_selected_node)
        self.update_node_btn.setEnabled(False)
        node_buttons_layout.addWidget(self.update_node_btn)
        
        node_mgr_layout.addLayout(node_buttons_layout, row, 0, 1, 2)
        
        self.node_manager_group.setLayout(node_mgr_layout)
        layout.addWidget(self.node_manager_group)
        
        # === GESTORE ARCHI ===
        self.edge_manager_group = QGroupBox("Gestore Archi")
        edge_mgr_layout = QGridLayout()
        
        row = 0
        edge_mgr_layout.addWidget(QLabel("ID:"), row, 0)
        self.edge_id_label = QLabel("-")
        self.edge_id_label.setStyleSheet("font-weight: bold; color: green;")
        edge_mgr_layout.addWidget(self.edge_id_label, row, 1)
        
        row += 1
        edge_mgr_layout.addWidget(QLabel("Da nodo:"), row, 0)
        self.edge_from_spin = QSpinBox()
        self.edge_from_spin.setRange(1, 99999)
        edge_mgr_layout.addWidget(self.edge_from_spin, row, 1)
        
        row += 1
        edge_mgr_layout.addWidget(QLabel("A nodo:"), row, 0)
        self.edge_to_spin = QSpinBox()
        self.edge_to_spin.setRange(1, 99999)
        edge_mgr_layout.addWidget(self.edge_to_spin, row, 1)
        
        row += 1
        edge_mgr_layout.addWidget(QLabel("Lunghezza (m):"), row, 0)
        self.edge_length_label = QLabel("-")
        self.edge_length_label.setStyleSheet("font-weight: bold; color: purple;")
        edge_mgr_layout.addWidget(self.edge_length_label, row, 1)
        
        row += 1
        edge_mgr_layout.addWidget(QLabel("Tipo:"), row, 0)
        self.edge_type_combo = QComboBox()
        self.edge_type_combo.addItems(['structural', 'cable', 'rod', 'beam', 'truss'])
        edge_mgr_layout.addWidget(self.edge_type_combo, row, 1)
        
        row += 1
        edge_mgr_layout.addWidget(QLabel("Materiale:"), row, 0)
        self.edge_material_combo = QComboBox()
        self.edge_material_combo.addItems(['acciaio', 'calcestruzzo', 'legno', 'alluminio', 'carbonio'])
        edge_mgr_layout.addWidget(self.edge_material_combo, row, 1)
        
        # Pulsanti archi
        row += 1
        edge_buttons_layout = QHBoxLayout()
        
        self.create_edge_btn = QPushButton("Crea Arco")
        self.create_edge_btn.clicked.connect(self.create_new_edge)
        edge_buttons_layout.addWidget(self.create_edge_btn)
        
        self.update_edge_btn = QPushButton("Aggiorna")
        self.update_edge_btn.clicked.connect(self.update_selected_edge)
        self.update_edge_btn.setEnabled(False)
        edge_buttons_layout.addWidget(self.update_edge_btn)
        
        edge_mgr_layout.addLayout(edge_buttons_layout, row, 0, 1, 2)
        
        self.edge_manager_group.setLayout(edge_mgr_layout)
        layout.addWidget(self.edge_manager_group)
        
        layout.addStretch()

    def set_editor(self, editor):
        """Collega l'editor"""
        self.editor = editor
        self.topology_panel.set_editor(editor)
        editor.selection_changed.connect(self.on_selection_changed)
        editor.node_updated.connect(self.on_node_updated)
        editor.edge_updated.connect(self.on_edge_updated)

    def on_selection_changed(self, entity_type, payload):
        """Gestisce i cambi di selezione"""
        self.updating_from_selection = True
        
        if entity_type == "node":
            self.show_node_properties(payload)
        elif entity_type == "edge":
            self.show_edge_properties(payload)
        elif entity_type == "none":
            self.show_no_selection()
        elif entity_type == "new_node_request":
            self.prepare_new_node()
        elif entity_type == "new_edge_request":
            self.prepare_new_edge(payload.get('from_id'))
            
        self.updating_from_selection = False

    def show_node_properties(self, node):
        """Mostra le proprietà di un nodo selezionato"""
        self.node_id_label.setText(str(node['id']))
        self.node_x_spin.setValue(node['x'])
        self.node_y_spin.setValue(node['y'])
        self.node_elevation_spin.setValue(node.get('elevation', 0.0))
        self.node_type_combo.setCurrentText(node.get('type', 'junction'))
        self.node_desc_edit.setText(node.get('description', ''))
        self.node_locked_check.setChecked(node.get('locked', False))
        
        self.update_node_btn.setEnabled(True)
        self.clear_edge_selection()

    def show_edge_properties(self, edge):
        """Mostra le proprietà di un arco selezionato"""
        self.edge_id_label.setText(str(edge.get('id', '-')))
        self.edge_from_spin.setValue(edge['from'])
        self.edge_to_spin.setValue(edge['to'])
        self.edge_type_combo.setCurrentText(edge.get('type', 'structural'))
        self.edge_material_combo.setCurrentText(edge.get('material', 'acciaio'))
        
        if self.editor:
            length = self.editor.calculate_edge_length(edge)
            self.edge_length_label.setText(f"{length:.4f}")
        
        self.update_edge_btn.setEnabled(True)
        self.clear_node_selection()

    def show_no_selection(self):
        """Mostra stato senza selezione"""
        self.clear_node_selection()
        self.clear_edge_selection()

    def clear_node_selection(self):
        """Pulisce la selezione nodo"""
        self.update_node_btn.setEnabled(False)

    def clear_edge_selection(self):
        """Pulisce la selezione arco"""
        self.edge_id_label.setText("-")
        self.edge_length_label.setText("-")
        self.update_edge_btn.setEnabled(False)

    def prepare_new_node(self):
        """Prepara il pannello per creazione nuovo nodo"""
        self.node_id_label.setText("NUOVO")

    def prepare_new_edge(self, from_id=None):
        """Prepara il pannello per creazione nuovo arco"""
        if from_id:
            self.edge_from_spin.setValue(from_id)
        self.edge_id_label.setText("NUOVO")
        self.edge_length_label.setText("-")

    def on_node_field_changed(self):
        """Gestisce modifiche ai campi nodo"""
        if self.updating_from_selection:
            return

    def on_node_updated(self, node):
        """Risponde agli aggiornamenti nodo dall'editor"""
        if self.editor.selected_node and self.editor.selected_node['id'] == node['id']:
            self.updating_from_selection = True
            self.show_node_properties(node)
            self.updating_from_selection = False

    def on_edge_updated(self, edge):
        """Risponde agli aggiornamenti arco dall'editor"""
        if self.editor.selected_edge and self.editor.selected_edge['id'] == edge['id']:
            self.updating_from_selection = True
            self.show_edge_properties(edge)
            self.updating_from_selection = False

    def create_new_node(self):
        """Crea un nuovo nodo con i valori del pannello"""
        if not self.editor:
            return
        
        x = self.node_x_spin.value()
        y = self.node_y_spin.value()
        elevation = self.node_elevation_spin.value()
        node_type = self.node_type_combo.currentText()
        description = self.node_desc_edit.text() or f"Nodo creato da pannello"
        locked = self.node_locked_check.isChecked()
        
        self.editor.create_node_at(x, y, elevation, node_type, description, locked)

    def update_selected_node(self):
        """Aggiorna il nodo selezionato con i valori del pannello"""
        if not self.editor or not self.editor.selected_node:
            return
        
        node_id = self.editor.selected_node['id']
        
        self.editor.update_node(
            node_id,
            x=self.node_x_spin.value(),
            y=self.node_y_spin.value(),
            elevation=self.node_elevation_spin.value(),
            type=self.node_type_combo.currentText(),
            description=self.node_desc_edit.text(),
            locked=self.node_locked_check.isChecked()
        )

    def create_new_edge(self):
        """Crea un nuovo arco con i valori del pannello"""
        if not self.editor:
            return
        
        from_id = self.edge_from_spin.value()
        to_id = self.edge_to_spin.value()
        edge_type = self.edge_type_combo.currentText()
        material = self.edge_material_combo.currentText()
        
        self.editor.create_edge_between(from_id, to_id, edge_type, material)

    def update_selected_edge(self):
        """Aggiorna l'arco selezionato con i valori del pannello"""
        if not self.editor or not self.editor.selected_edge:
            return
        
        edge_id = self.editor.selected_edge['id']
        
        self.editor.update_edge(
            edge_id,
            type=self.edge_type_combo.currentText(),
            material=self.edge_material_combo.currentText()
        )


class NavigationToolbar(QToolBar):
    """Toolbar di navigazione avanzata"""
    
    def __init__(self, editor, parent=None):
        super().__init__("Navigazione", parent)
        self.editor = editor
        self.setup_tools()

    def setup_tools(self):
        """Configura gli strumenti di navigazione"""
        # Pan mode toggle
        self.pan_action = QAction("Pan", self)
        self.pan_action.setCheckable(True)
        self.pan_action.triggered.connect(self.toggle_pan_mode)
        self.addAction(self.pan_action)
        
        self.addSeparator()
        
        # Zoom tools
        zoom_in_action = QAction("Zoom +", self)
        zoom_in_action.triggered.connect(lambda: self.editor.zoom_at_point(
            QPointF(self.editor.width()/2, self.editor.height()/2), 1))
        self.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom -", self)
        zoom_out_action.triggered.connect(lambda: self.editor.zoom_at_point(
            QPointF(self.editor.width()/2, self.editor.height()/2), -1))
        self.addAction(zoom_out_action)
        
        zoom_box_action = QAction("Zoom Box", self)
        zoom_box_action.triggered.connect(self.activate_zoom_box)
        self.addAction(zoom_box_action)
        
        self.addSeparator()
        
        # Fit tools
        fit_all_action = QAction("Fit All", self)
        fit_all_action.triggered.connect(self.editor.fit_to_extents)
        self.addAction(fit_all_action)
        
        fit_selection_action = QAction("Fit Selection", self)
        fit_selection_action.triggered.connect(self.editor.zoom_to_selection)
        self.addAction(fit_selection_action)
        
        zoom_100_action = QAction("100%", self)
        zoom_100_action.triggered.connect(self.editor.set_zoom_100)
        self.addAction(zoom_100_action)
        
        reset_view_action = QAction("Reset View", self)
        reset_view_action.triggered.connect(self.editor.reset_view)
        self.addAction(reset_view_action)
        
        self.addSeparator()
        
        # Options
        self.show_ports_action = QAction("Porte", self)
        self.show_ports_action.setCheckable(True)
        self.show_ports_action.triggered.connect(self.toggle_show_ports)
        self.addAction(self.show_ports_action)
        
        self.orthogonal_override_action = QAction("Override Ortogonali", self)
        self.orthogonal_override_action.setCheckable(True)
        self.orthogonal_override_action.triggered.connect(self.toggle_orthogonal_override)
        self.addAction(self.orthogonal_override_action)

    def toggle_pan_mode(self, checked):
        """Attiva/disattiva modalità pan"""
        self.editor.pan_mode = checked
        if checked:
            self.editor.setCursor(Qt.OpenHandCursor)
        else:
            self.editor.setCursor(Qt.ArrowCursor)

    def activate_zoom_box(self):
        """Attiva modalità zoom box"""
        self.editor.zoom_box_active = True
        self.editor.setCursor(Qt.CrossCursor)

    def toggle_show_ports(self, checked):
        """Mostra/nascondi porte di aggancio"""
        self.editor.show_ports = checked
        self.editor.update()

    def toggle_orthogonal_override(self, checked):
        """Attiva/disattiva override ortogonale globale"""
        self.editor.orthogonal_override = checked
        text = "Override attivo" if checked else "Override disattivo"
        self.editor.status_message.emit(text)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wire Editor Professional - Arch. Michelangelo Bartolotta")
        self.setMinimumSize(1600, 1000)
        
        self.setup_ui()
        self.setup_menus()
        self.setup_toolbars()
        self.setup_statusbar()
        self.connect_signals()

    def setup_ui(self):
        splitter = QSplitter(Qt.Horizontal)
        
        self.editor = WireEditor()
        splitter.addWidget(self.editor)
        
        self.property_panel = PropertyPanel()
        self.property_panel.set_editor(self.editor)
        self.property_panel.setMaximumWidth(380)
        splitter.addWidget(self.property_panel)
        
        splitter.setSizes([1200, 380])
        self.setCentralWidget(splitter)

    def setup_menus(self):
        menubar = self.menuBar()
        
        # Menu File
        file_menu = menubar.addMenu('File')
        
        new_action = QAction('Nuovo', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_model)
        file_menu.addAction(new_action)
        
        open_action = QAction('Apri...', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_model)
        file_menu.addAction(open_action)
        
        save_action = QAction('Salva...', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_model)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Esci', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Menu Modifica
        edit_menu = menubar.addMenu('Modifica')
        
        self.undo_action = QAction('Annulla', self)
        self.undo_action.setShortcut('Ctrl+Z')
        self.undo_action.triggered.connect(self.editor.undo)
        self.undo_action.setEnabled(False)
        edit_menu.addAction(self.undo_action)
        
        self.redo_action = QAction('Ripristina', self)
        self.redo_action.setShortcut('Ctrl+Shift+Z')
        self.redo_action.triggered.connect(self.editor.redo)
        self.redo_action.setEnabled(False)
        edit_menu.addAction(self.redo_action)
        
        edit_menu.addSeparator()
        
        delete_action = QAction('Elimina selezione', self)
        delete_action.setShortcut('Del')
        delete_action.triggered.connect(self.delete_selection)
        edit_menu.addAction(delete_action)
        
        # Menu Visualizza
        view_menu = menubar.addMenu('Visualizza')
        
        self.grid_action = QAction('Griglia', self)
        self.grid_action.setCheckable(True)
        self.grid_action.setChecked(True)
        self.grid_action.triggered.connect(self.toggle_grid)
        view_menu.addAction(self.grid_action)
        
        self.coords_action = QAction('Coordinate', self)
        self.coords_action.setCheckable(True)
        self.coords_action.setChecked(True)
        self.coords_action.triggered.connect(self.toggle_coordinates)
        view_menu.addAction(self.coords_action)
        
        self.measurements_action = QAction('Misure', self)
        self.measurements_action.setCheckable(True)
        self.measurements_action.setChecked(True)
        self.measurements_action.triggered.connect(self.toggle_measurements)
        view_menu.addAction(self.measurements_action)
        
        self.ports_action = QAction('Porte Aggancio', self)
        self.ports_action.setCheckable(True)
        self.ports_action.triggered.connect(self.toggle_ports)
        view_menu.addAction(self.ports_action)
        
        view_menu.addSeparator()
        
        self.snap_action = QAction('Snap a Griglia', self)
        self.snap_action.setCheckable(True)
        self.snap_action.setChecked(True)
        self.snap_action.triggered.connect(self.toggle_snap)
        view_menu.addAction(self.snap_action)
        
        self.zoom_new_action = QAction('Zoom su Nuovo Elemento', self)
        self.zoom_new_action.setCheckable(True)
        self.zoom_new_action.setChecked(True)
        self.zoom_new_action.triggered.connect(self.toggle_zoom_on_new)
        view_menu.addAction(self.zoom_new_action)
        
        # Menu Navigazione
        nav_menu = menubar.addMenu('Navigazione')
        
        fit_all_action = QAction('Adatta Tutto', self)
        fit_all_action.setShortcut('F')
        fit_all_action.triggered.connect(self.editor.fit_to_extents)
        nav_menu.addAction(fit_all_action)
        
        fit_selection_action = QAction('Adatta Selezione', self)
        fit_selection_action.setShortcut('Shift+F')
        fit_selection_action.triggered.connect(self.editor.zoom_to_selection)
        nav_menu.addAction(fit_selection_action)
        
        zoom_100_action = QAction('Zoom 100%', self)
        zoom_100_action.setShortcut('1')
        zoom_100_action.triggered.connect(self.editor.set_zoom_100)
        nav_menu.addAction(zoom_100_action)
        
        zoom_box_action = QAction('Zoom Box', self)
        zoom_box_action.setShortcut('Z')
        zoom_box_action.triggered.connect(self.activate_zoom_box)
        nav_menu.addAction(zoom_box_action)
        
        # Menu Strumenti
        tools_menu = menubar.addMenu('Strumenti')
        
        stats_action = QAction('Statistiche Modello', self)
        stats_action.triggered.connect(self.show_model_stats)
        tools_menu.addAction(stats_action)
        
        validate_action = QAction('Valida Modello', self)
        validate_action.triggered.connect(self.validate_model)
        tools_menu.addAction(validate_action)

    def setup_toolbars(self):
        # Toolbar principale
        main_toolbar = self.addToolBar('Principale')
        
        new_btn = QPushButton('Nuovo')
        new_btn.clicked.connect(self.new_model)
        main_toolbar.addWidget(new_btn)
        
        open_btn = QPushButton('Apri')
        open_btn.clicked.connect(self.open_model)
        main_toolbar.addWidget(open_btn)
        
        save_btn = QPushButton('Salva')
        save_btn.clicked.connect(self.save_model)
        main_toolbar.addWidget(save_btn)
        
        main_toolbar.addSeparator()
        
        self.undo_btn = QPushButton('↶ Annulla')
        self.undo_btn.clicked.connect(self.editor.undo)
        self.undo_btn.setEnabled(False)
        main_toolbar.addWidget(self.undo_btn)
        
        self.redo_btn = QPushButton('↷ Ripristina')
        self.redo_btn.clicked.connect(self.editor.redo)
        self.redo_btn.setEnabled(False)
        main_toolbar.addWidget(self.redo_btn)
        
        main_toolbar.addSeparator()
        
        # Controlli snap
        snap_label = QLabel("Snap:")
        main_toolbar.addWidget(snap_label)
        
        self.snap_check = QCheckBox()
        self.snap_check.setChecked(True)
        self.snap_check.toggled.connect(self.toggle_snap)
        main_toolbar.addWidget(self.snap_check)
        
        self.snap_spin = QDoubleSpinBox()
        self.snap_spin.setRange(0.001, 10.0)
        self.snap_spin.setDecimals(3)
        self.snap_spin.setValue(0.10)
        self.snap_spin.setSuffix(" m")
        self.snap_spin.valueChanged.connect(self.update_snap_step)
        main_toolbar.addWidget(self.snap_spin)
        
        # Toolbar navigazione
        self.nav_toolbar = NavigationToolbar(self.editor, self)
        self.addToolBar(self.nav_toolbar)

    def setup_statusbar(self):
        self.statusBar().showMessage("Pronto - Wire Editor Professional v2.0 con Sistema Tipologie")

    def connect_signals(self):
        self.editor.status_message.connect(self.statusBar().showMessage)
        self.editor.view_changed.connect(self.on_view_changed)
        
        # Timer per UI
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui_state)
        self.update_timer.start(500)

    def update_ui_state(self):
        """Aggiorna lo stato dell'interfaccia"""
        can_undo = self.editor.command_history.can_undo()
        can_redo = self.editor.command_history.can_redo()
        
        self.undo_action.setEnabled(can_undo)
        self.redo_action.setEnabled(can_redo)
        self.undo_btn.setEnabled(can_undo)
        self.redo_btn.setEnabled(can_redo)
        
        # Aggiorna controlli
        if abs(self.snap_spin.value() - self.editor.snap_step) > 0.001:
            self.snap_spin.setValue(self.editor.snap_step)
        
        self.snap_check.setChecked(self.editor.snap_enabled)

    def on_view_changed(self, zoom_factor, pan_offset):
        """Gestisce cambi di vista"""
        pass  # Aggiornamento automatico via status bar

    def new_model(self):
        reply = QMessageBox.question(self, 'Nuovo modello', 
                                   'Vuoi creare un nuovo modello?\nI dati non salvati verranno persi.',
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.editor.clear_model()
            self.statusBar().showMessage("Nuovo modello creato")

    def open_model(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Apri modello wireframe", "", 
            "File JSON (*.json);;Tutti i file (*)"
        )
        if filename:
            if self.editor.import_json(filename):
                self.statusBar().showMessage(f"Modello caricato: {filename}")
                # Aggiorna controlli interfaccia
                self.grid_action.setChecked(self.editor.show_grid)
                self.coords_action.setChecked(self.editor.show_coordinates)
                self.measurements_action.setChecked(self.editor.show_measurements)
                self.ports_action.setChecked(self.editor.show_ports)
                self.snap_action.setChecked(self.editor.snap_enabled)
                self.zoom_new_action.setChecked(self.editor.zoom_on_new_element)
                self.snap_spin.setValue(self.editor.snap_step)

    def save_model(self):
        if self.editor.export_json():
            self.statusBar().showMessage("Modello salvato")

    def delete_selection(self):
        """Elimina l'elemento selezionato"""
        if self.editor.selected_node:
            self.editor.delete_selected_node()
        elif self.editor.selected_edge:
            self.editor.delete_selected_edge()

    def toggle_grid(self, checked):
        self.editor.show_grid = checked
        self.editor.update()

    def toggle_coordinates(self, checked):
        self.editor.show_coordinates = checked
        self.editor.update()

    def toggle_measurements(self, checked):
        self.editor.show_measurements = checked
        self.editor.update()

    def toggle_ports(self, checked):
        self.editor.show_ports = checked
        self.nav_toolbar.show_ports_action.setChecked(checked)
        self.editor.update()

    def toggle_snap(self, checked):
        self.editor.snap_enabled = checked
        self.snap_check.setChecked(checked)
        self.statusBar().showMessage(f"Snap {'abilitato' if checked else 'disabilitato'}")

    def toggle_zoom_on_new(self, checked):
        self.editor.zoom_on_new_element = checked
        self.statusBar().showMessage(f"Zoom su nuovi elementi {'abilitato' if checked else 'disabilitato'}")

    def update_snap_step(self, value):
        self.editor.snap_step = value
        self.statusBar().showMessage(f"Passo snap: {value:.3f} m")

    def activate_zoom_box(self):
        """Attiva modalità zoom box"""
        self.editor.zoom_box_active = True
        self.editor.setCursor(Qt.CrossCursor)
        self.statusBar().showMessage("Modalità Zoom Box attiva - trascina per selezionare area")

    def show_model_stats(self):
        """Mostra statistiche del modello estese"""
        if not self.editor.nodes:
            QMessageBox.information(self, "Statistiche", "Nessun elemento nel modello.")
            return
        
        node_count = len(self.editor.nodes)
        edge_count = len(self.editor.edges)
        
        total_length = sum(self.editor.calculate_edge_length(edge) for edge in self.editor.edges)
        
        locked_nodes = sum(1 for node in self.editor.nodes if node.get('locked', False))
        
        # Tipi di nodi
        node_types = {}
        for node in self.editor.nodes:
            node_type = node.get('type', 'junction')
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        # Tipologie strutturali
        topology_types = {}
        for node in self.editor.nodes:
            topology = node.get('topology_role', 'center')
            topology_types[topology] = topology_types.get(topology, 0) + 1
        
        # Tipi di archi
        edge_types = {}
        edge_materials = {}
        for edge in self.editor.edges:
            edge_type = edge.get('type', 'structural')
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
            
            material = edge.get('material', 'acciaio')
            edge_materials[material] = edge_materials.get(material, 0) + 1
        
        # Statistiche vista
        zoom_percent = self.editor.zoom_factor * 100
        
        stats_text = f"""STATISTICHE MODELLO WIREFRAME

=== NODI ===
Totale: {node_count}
  - Bloccati: {locked_nodes}
  - Per tipo: {', '.join(f'{k}:{v}' for k, v in node_types.items())}
  - Per tipologia strutturale: {', '.join(f'{k.split("_")[-1] if "_" in k else k}:{v}' for k, v in topology_types.items())}

=== ARCHI ===
Totale: {edge_count}
  - Lunghezza totale: {total_length:.3f} m
  - Per tipo: {', '.join(f'{k}:{v}' for k, v in edge_types.items())}
  - Per materiale: {', '.join(f'{k}:{v}' for k, v in edge_materials.items())}

=== VISTA ===
Zoom: {zoom_percent:.0f}%
Pan offset: ({self.editor.pan_offset.x():.1f}, {self.editor.pan_offset.y():.1f}) px
Snap: {self.editor.snap_step:.3f} m

=== PROGETTO ===
Autore: {self.editor.project_metadata.get('author', 'N/A')}
Creato: {self.editor.project_metadata.get('created', 'N/A')[:19].replace('T', ' ')}
Modificato: {self.editor.project_metadata.get('modified', 'N/A')[:19].replace('T', ' ')}
Scala: {self.editor.project_metadata.get('scale', 'N/A')}
"""
        
        QMessageBox.information(self, "Statistiche Modello", stats_text)

    def validate_model(self):
        """Valida il modello per errori strutturali e tipologie"""
        issues = []
        warnings = []
        
        # Controlla nodi isolati
        connected_nodes = set()
        for edge in self.editor.edges:
            connected_nodes.add(edge['from'])
            connected_nodes.add(edge['to'])
        
        isolated_nodes = [node['id'] for node in self.editor.nodes 
                         if node['id'] not in connected_nodes]
        
        if isolated_nodes:
            warnings.append(f"Nodi isolati: {', '.join(map(str, isolated_nodes))}")
        
        # Controlla archi duplicati
        edge_pairs = set()
        for edge in self.editor.edges:
            pair = tuple(sorted([edge['from'], edge['to']]))
            if pair in edge_pairs:
                issues.append(f"Arco duplicato: {pair[0]}-{pair[1]}")
            edge_pairs.add(pair)
        
        # Controlla nodi coincidenti
        positions = {}
        for node in self.editor.nodes:
            pos = (round(node['x'], 3), round(node['y'], 3))
            if pos in positions:
                issues.append(f"Nodi coincidenti: {positions[pos]} e {node['id']} in {pos}")
            positions[pos] = node['id']
        
        # Controlla archi di lunghezza zero
        zero_length_edges = []
        for edge in self.editor.edges:
            if self.editor.calculate_edge_length(edge) < 0.001:
                zero_length_edges.append(f"{edge['from']}-{edge['to']}")
        
        if zero_length_edges:
            issues.append(f"Archi di lunghezza zero: {', '.join(zero_length_edges)}")
        
        # Validazione tipologie strutturali
        topology_issues = []
        for edge in self.editor.edges:
            n1 = self.editor.find_node_by_id(edge['from'])
            n2 = self.editor.find_node_by_id(edge['to'])
            
            if n1 and n2:
                # Calcola direzione
                dx = n2['x'] - n1['x']
                dy = n2['y'] - n1['y']
                
                if abs(dx) > 1e-6 or abs(dy) > 1e-6:
                    vector = QPointF(dx, dy)
                    direction_from = self.editor.get_direction_from_vector(vector)
                    direction_to = self.editor.get_direction_from_vector(QPointF(-dx, -dy))
                    
                    # Verifica compatibilità
                    if not self.editor.is_direction_allowed(n1, direction_from):
                        attachment1 = self.editor.get_node_attachment_profile(n1)
                        if attachment1.orthogonal_only:
                            topology_issues.append(f"Arco {edge['from']}-{edge['to']}: direzione {direction_from.value} non ammessa per nodo {edge['from']} (tipologia: {n1.get('topology_role', 'N/A')})")
                    
                    if not self.editor.is_direction_allowed(n2, direction_to):
                        attachment2 = self.editor.get_node_attachment_profile(n2)
                        if attachment2.orthogonal_only:
                            topology_issues.append(f"Arco {edge['from']}-{edge['to']}: direzione {direction_to.value} non ammessa per nodo {edge['to']} (tipologia: {n2.get('topology_role', 'N/A')})")
        
        if topology_issues:
            warnings.extend(topology_issues)
        
        # Prepara messaggio finale
        if not issues and not warnings:
            QMessageBox.information(self, "Validazione", "✓ Modello valido - nessun problema rilevato.")
        else:
            message_parts = []
            
            if issues:
                message_parts.append("❌ ERRORI CRITICI:")
                message_parts.extend(f"• {issue}" for issue in issues)
                message_parts.append("")
            
            if warnings:
                message_parts.append("⚠️ AVVISI:")
                message_parts.extend(f"• {warning}" for warning in warnings)
            
            if topology_issues:
                message_parts.append("")
                message_parts.append("💡 SUGGERIMENTO: Usa Alt+Click per override delle restrizioni ortogonali o modifica le tipologie dei nodi.")
            
            message_text = "\n".join(message_parts)
            
            if issues:
                QMessageBox.warning(self, "Validazione Modello", message_text)
            else:
                QMessageBox.information(self, "Validazione Modello", message_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Wire Editor Professional")
    app.setApplicationVersion("2.0 - Sistema Tipologie")
    app.setOrganizationName("Arch. Michelangelo Bartolotta")
    
    # Configura stile applicazione
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())