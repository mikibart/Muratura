# -*- coding: utf-8 -*-
"""
OpenGL Drawing Canvas - 2D view with GPU rendering
Blender-style quality with ModernGL.
"""

import math
import numpy as np
from typing import Optional, Tuple, List, Any

# PyQt imports con fallback robusto
HAS_QT = False
HAS_QGL = False
HAS_MODERNGL = False
QWidget = object  # Default fallback

try:
    from PyQt5.QtWidgets import QWidget, QOpenGLWidget
    from PyQt5.QtCore import Qt, QPoint, QPointF, pyqtSignal
    from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygonF
    HAS_QT = True
except ImportError:
    pass

try:
    from PyQt5.QtOpenGL import QGLWidget
    HAS_QGL = True
except ImportError:
    QGLWidget = QWidget

try:
    import moderngl
    HAS_MODERNGL = True
except ImportError:
    moderngl = None

from .gl_renderer import GLRenderer, BackgroundRenderer, GridRenderer, ElementRenderer

# Determina la classe base
_BaseClass = QWidget
if HAS_QGL and HAS_MODERNGL:
    _BaseClass = QGLWidget


class GLDrawingCanvas2D(_BaseClass):
    """
    Professional 2D drawing canvas with GPU acceleration.
    Features:
    - Blender-style gamma-corrected background gradient
    - Multi-level LOD grid with smooth transitions
    - Anti-aliased rendering
    - Efficient batch rendering via VBOs
    """

    # Signals
    elementClicked = pyqtSignal(object)  # Emitted when element is clicked
    viewChanged = pyqtSignal()  # Emitted when view (pan/zoom) changes

    def __init__(self, parent=None):
        super().__init__(parent)

        # OpenGL context and renderers
        self.ctx = None
        self.renderer = None
        self.use_gpu = HAS_MODERNGL and HAS_QGL

        # View parameters
        self.scala = 40.0  # Pixels per meter
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.min_scale = 5.0
        self.max_scale = 500.0

        # Project reference
        self.progetto = None
        self.needs_update = True

        # Geometry buffers
        self._wall_vertices = []
        self._wall_colors = []
        self._wall_selected = []

        # Interaction
        self.last_mouse_pos = None
        self.panning = False
        self.selected_elements = set()

        # Visual options
        self.show_grid = True
        self.show_axes = True
        self.show_dimensions = True
        self.background_style = 'light'  # 'light', 'dark', 'blender', 'freecad'

        # Grid settings
        self.grid_base_size = 1.0  # 1 meter
        self.grid_subdivisions = 10

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def initializeGL(self):
        """Initialize OpenGL context and shaders"""
        if not self.use_gpu:
            return

        try:
            self.ctx = moderngl.create_context()
            self.renderer = GLRenderer(self.ctx)

            # Set default background style
            self.set_background_style(self.background_style)

            # Configure grid
            self.renderer.grid.base_grid_size = self.grid_base_size
            self.renderer.grid.grid_subdivisions = self.grid_subdivisions

        except Exception as e:
            print(f"OpenGL initialization error: {e}")
            self.use_gpu = False

    def resizeGL(self, width: int, height: int):
        """Handle resize"""
        if self.ctx:
            self.ctx.viewport = (0, 0, width, height)

        # Center view on first resize
        if self.offset_x == 0 and self.offset_y == 0:
            self.offset_x = width / 2
            self.offset_y = height / 2

    def paintGL(self):
        """Render the scene"""
        if not self.use_gpu or not self.ctx:
            self.paintFallback()
            return

        # Clear and render background
        self.renderer.clear((0, 0, 0, 1))
        self.renderer.render_background()

        # Render grid
        if self.show_grid:
            self.renderer.render_grid_2d(
                self.scala, self.offset_x, self.offset_y,
                self.width(), self.height()
            )

        # Update geometry if needed
        if self.needs_update:
            self._update_geometry()

        # Render elements
        self.renderer.render_elements_2d(
            self.scala, self.offset_x, self.offset_y,
            self.width(), self.height()
        )

    def paintFallback(self):
        """Fallback rendering with QPainter"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background gradient
        from PyQt5.QtGui import QLinearGradient
        gradient = QLinearGradient(0, 0, 0, self.height())

        if self.background_style == 'dark':
            gradient.setColorAt(0, QColor(60, 70, 85))
            gradient.setColorAt(1, QColor(35, 40, 50))
        elif self.background_style == 'blender':
            gradient.setColorAt(0, QColor(100, 137, 177))
            gradient.setColorAt(1, QColor(43, 52, 64))
        else:  # light
            gradient.setColorAt(0, QColor(245, 245, 250))
            gradient.setColorAt(1, QColor(225, 230, 240))

        painter.fillRect(self.rect(), QBrush(gradient))

        # Draw grid
        if self.show_grid:
            self._draw_grid_fallback(painter)

        # Draw elements
        if self.progetto:
            self._draw_elements_fallback(painter)

        painter.end()

    def _draw_grid_fallback(self, painter: QPainter):
        """Draw grid with QPainter fallback"""
        # Calculate grid spacing based on zoom
        base_spacing = self.grid_base_size * self.scala

        # Find appropriate grid level
        while base_spacing < 20:
            base_spacing *= self.grid_subdivisions
        while base_spacing > 200:
            base_spacing /= self.grid_subdivisions

        # Grid color
        painter.setPen(QPen(QColor(180, 180, 180, 100), 1))

        # Vertical lines
        start_x = self.offset_x % base_spacing
        x = start_x
        while x < self.width():
            painter.drawLine(int(x), 0, int(x), self.height())
            x += base_spacing

        # Horizontal lines
        start_y = self.offset_y % base_spacing
        y = start_y
        while y < self.height():
            painter.drawLine(0, int(y), self.width(), int(y))
            y += base_spacing

        # Draw axes
        if self.show_axes:
            # X axis (red)
            if 0 < self.offset_y < self.height():
                painter.setPen(QPen(QColor(200, 80, 80), 2))
                painter.drawLine(0, int(self.offset_y), self.width(), int(self.offset_y))

            # Y axis (green)
            if 0 < self.offset_x < self.width():
                painter.setPen(QPen(QColor(80, 200, 80), 2))
                painter.drawLine(int(self.offset_x), 0, int(self.offset_x), self.height())

    def _draw_elements_fallback(self, painter: QPainter):
        """Draw elements with QPainter fallback"""
        if not self.progetto:
            return

        # Draw walls
        for muro in self.progetto.muri:
            self._draw_wall_fallback(painter, muro)

    def _draw_wall_fallback(self, painter: QPainter, muro):
        """Draw single wall with QPainter"""
        # Calculate wall polygon
        dx = muro.x2 - muro.x1
        dy = muro.y2 - muro.y1
        length = math.sqrt(dx*dx + dy*dy)

        if length < 0.001:
            return

        # Normal vector for thickness
        nx = -dy / length * muro.spessore / 2
        ny = dx / length * muro.spessore / 2

        # Transform to screen coordinates
        def to_screen(x, y):
            return QPointF(
                x * self.scala + self.offset_x,
                -y * self.scala + self.offset_y  # Flip Y
            )

        # Wall corners
        points = [
            to_screen(muro.x1 - nx, muro.y1 - ny),
            to_screen(muro.x1 + nx, muro.y1 + ny),
            to_screen(muro.x2 + nx, muro.y2 + ny),
            to_screen(muro.x2 - nx, muro.y2 - ny),
        ]

        # Color based on selection/DCR
        if hasattr(muro, 'nome') and muro.nome in self.selected_elements:
            fill_color = QColor(255, 180, 100, 200)
            pen_color = QColor(255, 120, 0)
        else:
            # Use DCR color if available
            if hasattr(muro, 'dcr_color') and muro.dcr_color:
                r, g, b = muro.dcr_color
                fill_color = QColor(int(r*255), int(g*255), int(b*255), 180)
                pen_color = QColor(int(r*200), int(g*200), int(b*200))
            else:
                fill_color = QColor(100, 150, 200, 180)
                pen_color = QColor(50, 100, 150)

        painter.setPen(QPen(pen_color, 2))
        painter.setBrush(QBrush(fill_color))
        painter.drawPolygon(QPolygonF(points))

    def _update_geometry(self):
        """Update GPU geometry buffers"""
        if not self.use_gpu or not self.renderer or not self.progetto:
            self.needs_update = False
            return

        vertices = []
        colors = []
        selected = []

        for muro in self.progetto.muri:
            # Calculate wall geometry
            dx = muro.x2 - muro.x1
            dy = muro.y2 - muro.y1
            length = math.sqrt(dx*dx + dy*dy)

            if length < 0.001:
                continue

            nx = -dy / length * muro.spessore / 2
            ny = dx / length * muro.spessore / 2

            # 4 corners
            p1 = (muro.x1 - nx, muro.y1 - ny)
            p2 = (muro.x1 + nx, muro.y1 + ny)
            p3 = (muro.x2 + nx, muro.y2 + ny)
            p4 = (muro.x2 - nx, muro.y2 - ny)

            # Two triangles
            for p in [p1, p2, p3, p1, p3, p4]:
                vertices.extend(p)

            # Color
            if hasattr(muro, 'dcr_color') and muro.dcr_color:
                color = muro.dcr_color
            else:
                color = (0.4, 0.6, 0.8)  # Default blue

            for _ in range(6):
                colors.extend(color)

            # Selection state
            is_selected = 1.0 if (hasattr(muro, 'nome') and muro.nome in self.selected_elements) else 0.0
            selected.extend([is_selected] * 6)

        # Update renderer geometry
        if vertices:
            self.renderer.elements_2d.update_geometry_2d(
                np.array(vertices, dtype='f4'),
                np.array(colors, dtype='f4'),
                np.array(selected, dtype='f4')
            )

        self.needs_update = False

    def setProgetto(self, progetto):
        """Set the project to display"""
        self.progetto = progetto
        self.needs_update = True
        self.update()

    def set_background_style(self, style: str):
        """Set background gradient style"""
        self.background_style = style

        if self.renderer:
            if style == 'blender':
                self.renderer.background.set_blender_style()
            elif style == 'freecad':
                self.renderer.background.set_freecad_style()
            elif style == 'dark':
                self.renderer.background.set_colors(
                    (0.25, 0.28, 0.35),
                    (0.12, 0.14, 0.18)
                )
            else:  # light
                self.renderer.background.set_light_style()

        self.update()

    def world_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        """Convert world coordinates to screen coordinates"""
        sx = x * self.scala + self.offset_x
        sy = -y * self.scala + self.offset_y
        return (sx, sy)

    def screen_to_world(self, sx: float, sy: float) -> Tuple[float, float]:
        """Convert screen coordinates to world coordinates"""
        x = (sx - self.offset_x) / self.scala
        y = -(sy - self.offset_y) / self.scala
        return (x, y)

    def zoom_to_fit(self):
        """Zoom to fit all elements"""
        if not self.progetto or not self.progetto.muri:
            return

        # Calculate bounding box
        xs = []
        ys = []
        for muro in self.progetto.muri:
            xs.extend([muro.x1, muro.x2])
            ys.extend([muro.y1, muro.y2])

        if not xs:
            return

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        # Add padding
        padding = 2.0  # meters
        min_x -= padding
        max_x += padding
        min_y -= padding
        max_y += padding

        # Calculate scale to fit
        width = max_x - min_x
        height = max_y - min_y

        if width > 0 and height > 0:
            scale_x = (self.width() - 100) / width
            scale_y = (self.height() - 100) / height
            self.scala = min(scale_x, scale_y, self.max_scale)
            self.scala = max(self.scala, self.min_scale)

        # Center view
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        self.offset_x = self.width() / 2 - center_x * self.scala
        self.offset_y = self.height() / 2 + center_y * self.scala

        self.update()
        self.viewChanged.emit()

    # Mouse events
    def wheelEvent(self, event):
        """Zoom with mouse wheel"""
        # Get mouse position for zoom center
        mouse_pos = event.pos()
        world_x, world_y = self.screen_to_world(mouse_pos.x(), mouse_pos.y())

        # Calculate new scale
        delta = event.angleDelta().y()
        if delta > 0:
            new_scale = min(self.scala * 1.15, self.max_scale)
        else:
            new_scale = max(self.scala / 1.15, self.min_scale)

        # Adjust offset to zoom towards mouse position
        self.offset_x = mouse_pos.x() - world_x * new_scale
        self.offset_y = mouse_pos.y() + world_y * new_scale
        self.scala = new_scale

        self.update()
        self.viewChanged.emit()

    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.MiddleButton or \
           (event.button() == Qt.LeftButton and event.modifiers() & Qt.ShiftModifier):
            self.panning = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        elif event.button() == Qt.LeftButton:
            # Check for element selection
            world_pos = self.screen_to_world(event.pos().x(), event.pos().y())
            element = self._element_at(world_pos)
            if element:
                if event.modifiers() & Qt.ControlModifier:
                    # Toggle selection
                    if element.nome in self.selected_elements:
                        self.selected_elements.discard(element.nome)
                    else:
                        self.selected_elements.add(element.nome)
                else:
                    # Single selection
                    self.selected_elements = {element.nome}
                self.needs_update = True
                self.elementClicked.emit(element)
            else:
                if not (event.modifiers() & Qt.ControlModifier):
                    self.selected_elements.clear()
                    self.needs_update = True
            self.update()

    def mouseMoveEvent(self, event):
        """Handle mouse move"""
        if self.panning and self.last_mouse_pos:
            delta = event.pos() - self.last_mouse_pos
            self.offset_x += delta.x()
            self.offset_y += delta.y()
            self.last_mouse_pos = event.pos()
            self.update()
            self.viewChanged.emit()

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MiddleButton or event.button() == Qt.LeftButton:
            self.panning = False
            self.last_mouse_pos = None
            self.setCursor(Qt.ArrowCursor)

    def _element_at(self, world_pos: Tuple[float, float]) -> Optional[Any]:
        """Find element at world position"""
        if not self.progetto:
            return None

        x, y = world_pos

        # Check walls
        for muro in self.progetto.muri:
            if self._point_in_wall(x, y, muro):
                return muro

        return None

    def _point_in_wall(self, x: float, y: float, muro) -> bool:
        """Check if point is inside wall polygon"""
        dx = muro.x2 - muro.x1
        dy = muro.y2 - muro.y1
        length = math.sqrt(dx*dx + dy*dy)

        if length < 0.001:
            return False

        nx = -dy / length * muro.spessore / 2
        ny = dx / length * muro.spessore / 2

        # Wall corners
        corners = [
            (muro.x1 - nx, muro.y1 - ny),
            (muro.x1 + nx, muro.y1 + ny),
            (muro.x2 + nx, muro.y2 + ny),
            (muro.x2 - nx, muro.y2 - ny),
        ]

        # Point in polygon test
        n = len(corners)
        inside = False
        j = n - 1

        for i in range(n):
            xi, yi = corners[i]
            xj, yj = corners[j]

            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside

    def keyPressEvent(self, event):
        """Handle keyboard input"""
        if event.key() == Qt.Key_Home:
            self.zoom_to_fit()
        elif event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            self.scala = min(self.scala * 1.2, self.max_scale)
            self.update()
        elif event.key() == Qt.Key_Minus:
            self.scala = max(self.scala / 1.2, self.min_scale)
            self.update()
        elif event.key() == Qt.Key_G:
            self.show_grid = not self.show_grid
            self.update()
        elif event.key() == Qt.Key_Escape:
            self.selected_elements.clear()
            self.needs_update = True
            self.update()
