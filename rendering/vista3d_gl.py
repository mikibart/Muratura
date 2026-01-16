# -*- coding: utf-8 -*-
"""
OpenGL 3D Vista - GPU-accelerated 3D view
Professional quality rendering inspired by FreeCAD/Blender.

NOTA: Su Windows con PyQt5, il rendering GPU con moderngl può avere problemi.
Questa versione usa SEMPRE il fallback QPainter per massima compatibilità.
"""

import math
import numpy as np
from typing import Optional, Tuple, List, Any

try:
    from PyQt5.QtWidgets import QWidget
    from PyQt5.QtCore import Qt, QPoint, pyqtSignal
    from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient, QPolygon
    HAS_QT = True
except ImportError:
    HAS_QT = False


class Vista3DWidgetGL(QWidget):
    """
    Professional 3D view with isometric rendering.
    Features:
    - Blender-style gradient background
    - Simple shading for depth perception
    - Smooth camera rotation
    - Multi-level grid on ground plane
    - Compatible with all platforms (uses QPainter)
    """

    # Signals
    elementClicked = pyqtSignal(object)
    viewChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Disable GPU - use QPainter fallback for compatibility
        self.ctx = None
        self.renderer = None
        self.use_gpu = False  # Force QPainter rendering

        # Project
        self.progetto = None
        self.needs_update = True

        # Camera parameters
        self.camera_distance = 30.0
        self.camera_rotation_h = 45.0  # Horizontal angle (degrees)
        self.camera_rotation_v = 30.0  # Vertical angle (degrees)
        self.camera_target = np.array([0.0, 0.0, 1.5], dtype='f4')  # Look-at point

        # Projection
        self.fov = 45.0
        self.near_plane = 0.1
        self.far_plane = 1000.0
        self.use_perspective = True

        # Interaction
        self.last_mouse_pos = None
        self.rotating = False
        self.panning = False

        # Visual options
        self.show_grid = True
        self.show_axes = True
        self.show_shadows = True
        self.background_style = 'blender'

        # Lighting
        self.light_direction = np.array([0.5, 0.3, 1.0], dtype='f4')
        self.light_direction = self.light_direction / np.linalg.norm(self.light_direction)

        # Element colors (RGB)
        self.wall_color = (200, 160, 120)      # Brick-like
        self.foundation_color = (140, 140, 140)  # Concrete gray
        self.slab_color = (180, 200, 180)        # Light green-gray
        self.beam_color = (180, 180, 190)        # Steel gray

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(400, 400)

        print("[Vista3D] Inizializzato con rendering QPainter (compatibilità)")

    def paintEvent(self, event):
        """Main paint event - uses QPainter for compatibility"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # Draw background gradient
        self._draw_background(painter)

        # Draw grid
        if self.show_grid:
            self._draw_grid(painter)

        # Draw 3D elements
        if self.progetto:
            self._draw_isometric_scene(painter)
        else:
            # Show "no project" message
            painter.setPen(QColor(200, 200, 200))
            painter.setFont(QFont("Arial", 12))
            painter.drawText(self.rect(), Qt.AlignCenter, "Nessun progetto caricato\n\nCarica o crea un progetto")

        # Draw axes indicator
        if self.show_axes:
            self._draw_axes_indicator(painter)

        painter.end()

    def _draw_background(self, painter: QPainter):
        """Draw gradient background (Blender/FreeCAD style)"""
        gradient = QLinearGradient(0, 0, 0, self.height())

        if self.background_style == 'blender':
            # Blender default - soft blue gradient
            gradient.setColorAt(0, QColor(100, 137, 177))   # Top - lighter blue
            gradient.setColorAt(1, QColor(43, 52, 64))      # Bottom - dark blue
        else:
            # FreeCAD style - inverted
            gradient.setColorAt(0, QColor(60, 72, 90))      # Top - dark
            gradient.setColorAt(1, QColor(167, 180, 194))   # Bottom - light

        painter.fillRect(self.rect(), QBrush(gradient))

    def _draw_grid(self, painter: QPainter):
        """Draw ground plane grid"""
        # Grid settings
        grid_size = 20  # Grid extends from -grid_size to +grid_size
        grid_step = 1.0  # 1 meter between lines
        major_step = 5   # Major lines every 5 meters

        scale = self._get_view_scale()

        # Draw minor grid lines
        painter.setPen(QPen(QColor(100, 100, 100, 60), 1))
        for i in range(-grid_size, grid_size + 1):
            if i % major_step == 0:
                continue  # Skip major lines

            # Lines parallel to X
            p1 = self._project_point(i * grid_step, -grid_size * grid_step, 0)
            p2 = self._project_point(i * grid_step, grid_size * grid_step, 0)
            painter.drawLine(p1[0], p1[1], p2[0], p2[1])

            # Lines parallel to Y
            p1 = self._project_point(-grid_size * grid_step, i * grid_step, 0)
            p2 = self._project_point(grid_size * grid_step, i * grid_step, 0)
            painter.drawLine(p1[0], p1[1], p2[0], p2[1])

        # Draw major grid lines
        painter.setPen(QPen(QColor(100, 100, 100, 100), 1))
        for i in range(-grid_size // major_step, grid_size // major_step + 1):
            coord = i * major_step * grid_step

            # Lines parallel to X
            p1 = self._project_point(coord, -grid_size * grid_step, 0)
            p2 = self._project_point(coord, grid_size * grid_step, 0)
            painter.drawLine(p1[0], p1[1], p2[0], p2[1])

            # Lines parallel to Y
            p1 = self._project_point(-grid_size * grid_step, coord, 0)
            p2 = self._project_point(grid_size * grid_step, coord, 0)
            painter.drawLine(p1[0], p1[1], p2[0], p2[1])

        # Draw X axis (red)
        painter.setPen(QPen(QColor(200, 80, 80), 2))
        p1 = self._project_point(-grid_size * grid_step, 0, 0)
        p2 = self._project_point(grid_size * grid_step, 0, 0)
        painter.drawLine(p1[0], p1[1], p2[0], p2[1])

        # Draw Y axis (green)
        painter.setPen(QPen(QColor(80, 200, 80), 2))
        p1 = self._project_point(0, -grid_size * grid_step, 0)
        p2 = self._project_point(0, grid_size * grid_step, 0)
        painter.drawLine(p1[0], p1[1], p2[0], p2[1])

    def _draw_axes_indicator(self, painter: QPainter):
        """Draw small XYZ axes indicator in corner"""
        # Position in bottom-left corner
        cx, cy = 50, self.height() - 50
        axis_len = 30

        # Calculate axis directions based on camera rotation
        h_rad = math.radians(self.camera_rotation_h)
        v_rad = math.radians(self.camera_rotation_v)

        # X axis (red)
        dx = axis_len * math.cos(h_rad)
        dy = -axis_len * math.sin(h_rad) * math.cos(v_rad)
        painter.setPen(QPen(QColor(255, 80, 80), 2))
        painter.drawLine(cx, cy, int(cx + dx), int(cy + dy))
        painter.drawText(int(cx + dx + 5), int(cy + dy), "X")

        # Y axis (green)
        dx = axis_len * math.sin(h_rad)
        dy = axis_len * math.cos(h_rad) * math.cos(v_rad)
        painter.setPen(QPen(QColor(80, 255, 80), 2))
        painter.drawLine(cx, cy, int(cx + dx), int(cy - dy))
        painter.drawText(int(cx + dx + 5), int(cy - dy), "Y")

        # Z axis (blue)
        dz = axis_len * math.sin(v_rad)
        painter.setPen(QPen(QColor(80, 80, 255), 2))
        painter.drawLine(cx, cy, cx, int(cy - dz - 20))
        painter.drawText(cx + 5, int(cy - dz - 25), "Z")

    def _get_view_scale(self) -> float:
        """Get scale factor for view"""
        return min(self.width(), self.height()) / (self.camera_distance * 2)

    def _project_point(self, x: float, y: float, z: float) -> Tuple[int, int, float]:
        """Project 3D point to screen coordinates with depth"""
        # Apply camera rotation
        h_rad = math.radians(self.camera_rotation_h)
        v_rad = math.radians(self.camera_rotation_v)

        # Center on camera target
        x -= self.camera_target[0]
        y -= self.camera_target[1]
        z -= self.camera_target[2]

        # Rotate around Z axis (horizontal rotation)
        rx = x * math.cos(h_rad) - y * math.sin(h_rad)
        ry = x * math.sin(h_rad) + y * math.cos(h_rad)
        rz = z

        # Rotate around X axis (vertical rotation)
        ry2 = ry * math.cos(v_rad) - rz * math.sin(v_rad)
        rz2 = ry * math.sin(v_rad) + rz * math.cos(v_rad)

        # Scale and center on screen
        scale = self._get_view_scale()
        sx = rx * scale + self.width() / 2
        sy = -rz2 * scale + self.height() / 2

        return int(sx), int(sy), ry2  # ry2 is depth for sorting

    def _draw_isometric_scene(self, painter: QPainter):
        """Draw all 3D elements with isometric projection"""
        # Collect all elements with depth
        elements = []

        # Walls
        for muro in self.progetto.muri:
            cx = (muro.x1 + muro.x2) / 2
            cy = (muro.y1 + muro.y2) / 2
            cz = muro.z + muro.altezza / 2
            _, _, depth = self._project_point(cx, cy, cz)
            elements.append(('wall', muro, depth))

        # Foundations
        for fond in getattr(self.progetto, 'fondazioni', []):
            cx = (fond.x1 + fond.x2) / 2
            cy = (fond.y1 + fond.y2) / 2
            cz = -fond.profondita / 2
            _, _, depth = self._project_point(cx, cy, cz)
            elements.append(('foundation', fond, depth))

        # Sort by depth (far to near - painter's algorithm)
        elements.sort(key=lambda e: e[2], reverse=True)

        # Draw elements
        for elem_type, elem, _ in elements:
            if elem_type == 'wall':
                self._draw_wall_3d(painter, elem)
            elif elem_type == 'foundation':
                self._draw_foundation_3d(painter, elem)

    def _draw_wall_3d(self, painter: QPainter, muro):
        """Draw 3D wall with shading"""
        # Wall geometry
        dx = muro.x2 - muro.x1
        dy = muro.y2 - muro.y1
        length = math.sqrt(dx*dx + dy*dy)

        if length < 0.001:
            return

        # Calculate perpendicular offset for wall thickness
        nx = -dy / length * muro.spessore / 2
        ny = dx / length * muro.spessore / 2

        z0 = muro.z
        z1 = muro.z + muro.altezza

        # 8 corners of the wall box
        corners = [
            (muro.x1 - nx, muro.y1 - ny, z0),  # 0 - bottom front left
            (muro.x1 + nx, muro.y1 + ny, z0),  # 1 - bottom front right
            (muro.x2 + nx, muro.y2 + ny, z0),  # 2 - bottom back right
            (muro.x2 - nx, muro.y2 - ny, z0),  # 3 - bottom back left
            (muro.x1 - nx, muro.y1 - ny, z1),  # 4 - top front left
            (muro.x1 + nx, muro.y1 + ny, z1),  # 5 - top front right
            (muro.x2 + nx, muro.y2 + ny, z1),  # 6 - top back right
            (muro.x2 - nx, muro.y2 - ny, z1),  # 7 - top back left
        ]

        # Project all corners
        projected = [self._project_point(*c) for c in corners]

        # Define faces with colors based on lighting
        # Colors with simple shading based on face orientation
        base_r, base_g, base_b = self.wall_color

        faces_data = [
            # (indices, brightness multiplier for shading)
            ([4, 5, 6, 7], 1.0),    # Top - brightest
            ([0, 3, 7, 4], 0.85),   # Left side
            ([1, 2, 6, 5], 0.75),   # Right side
            ([0, 1, 5, 4], 0.80),   # Front end
            ([3, 2, 6, 7], 0.70),   # Back end
        ]

        # Calculate face depths and sort
        face_render_data = []
        for indices, brightness in faces_data:
            avg_depth = sum(projected[i][2] for i in indices) / len(indices)
            face_render_data.append((indices, brightness, avg_depth))

        # Sort by depth (far to near)
        face_render_data.sort(key=lambda x: x[2], reverse=True)

        # Draw faces
        for indices, brightness, _ in face_render_data:
            points = [QPoint(projected[i][0], projected[i][1]) for i in indices]

            # Apply shading
            r = int(base_r * brightness)
            g = int(base_g * brightness)
            b = int(base_b * brightness)

            painter.setPen(QPen(QColor(80, 60, 40), 1))
            painter.setBrush(QBrush(QColor(r, g, b)))
            painter.drawPolygon(QPolygon(points))

    def _draw_foundation_3d(self, painter: QPainter, fond):
        """Draw 3D foundation with shading"""
        dx = fond.x2 - fond.x1
        dy = fond.y2 - fond.y1
        length = math.sqrt(dx*dx + dy*dy)

        if length < 0.001:
            return

        # Calculate perpendicular offset
        nx = -dy / length * fond.larghezza / 2
        ny = dx / length * fond.larghezza / 2

        z0 = -fond.profondita
        z1 = 0  # Ground level

        # 8 corners
        corners = [
            (fond.x1 - nx, fond.y1 - ny, z0),
            (fond.x1 + nx, fond.y1 + ny, z0),
            (fond.x2 + nx, fond.y2 + ny, z0),
            (fond.x2 - nx, fond.y2 - ny, z0),
            (fond.x1 - nx, fond.y1 - ny, z1),
            (fond.x1 + nx, fond.y1 + ny, z1),
            (fond.x2 + nx, fond.y2 + ny, z1),
            (fond.x2 - nx, fond.y2 - ny, z1),
        ]

        projected = [self._project_point(*c) for c in corners]

        base_r, base_g, base_b = self.foundation_color

        faces_data = [
            ([4, 5, 6, 7], 1.0),
            ([0, 3, 7, 4], 0.85),
            ([1, 2, 6, 5], 0.75),
            ([0, 1, 5, 4], 0.80),
            ([3, 2, 6, 7], 0.70),
        ]

        face_render_data = []
        for indices, brightness in faces_data:
            avg_depth = sum(projected[i][2] for i in indices) / len(indices)
            face_render_data.append((indices, brightness, avg_depth))

        face_render_data.sort(key=lambda x: x[2], reverse=True)

        for indices, brightness, _ in face_render_data:
            points = [QPoint(projected[i][0], projected[i][1]) for i in indices]

            r = int(base_r * brightness)
            g = int(base_g * brightness)
            b = int(base_b * brightness)

            painter.setPen(QPen(QColor(60, 60, 60), 1))
            painter.setBrush(QBrush(QColor(r, g, b)))
            painter.drawPolygon(QPolygon(points))

    def setProgetto(self, progetto):
        """Set project to display"""
        self.progetto = progetto
        self.needs_update = True

        # Center view on model
        if progetto and progetto.muri:
            xs = [m.x1 for m in progetto.muri] + [m.x2 for m in progetto.muri]
            ys = [m.y1 for m in progetto.muri] + [m.y2 for m in progetto.muri]
            zs = [m.z + m.altezza/2 for m in progetto.muri]

            self.camera_target = np.array([
                (min(xs) + max(xs)) / 2,
                (min(ys) + max(ys)) / 2,
                sum(zs) / len(zs) if zs else 1.5
            ], dtype='f4')

            # Adjust distance to fit model
            size = max(max(xs) - min(xs), max(ys) - min(ys), 5)
            self.camera_distance = size * 2

        self.update()

    # Mouse events
    def wheelEvent(self, event):
        """Zoom with wheel"""
        delta = event.angleDelta().y()
        if delta > 0:
            self.camera_distance = max(5.0, self.camera_distance / 1.15)
        else:
            self.camera_distance = min(200.0, self.camera_distance * 1.15)
        self.update()
        self.viewChanged.emit()

    def mousePressEvent(self, event):
        """Start rotation or pan"""
        self.last_mouse_pos = event.pos()

        if event.button() == Qt.LeftButton:
            self.rotating = True
        elif event.button() == Qt.MiddleButton:
            self.panning = True
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        """Handle mouse drag"""
        if not self.last_mouse_pos:
            return

        delta = event.pos() - self.last_mouse_pos
        self.last_mouse_pos = event.pos()

        if self.rotating:
            # Rotate camera
            self.camera_rotation_h += delta.x() * 0.5
            self.camera_rotation_v = max(-89, min(89, self.camera_rotation_v + delta.y() * 0.5))
            self.update()
            self.viewChanged.emit()

        elif self.panning:
            # Pan camera target
            # Calculate pan vectors based on camera orientation
            h_rad = math.radians(self.camera_rotation_h)
            right = np.array([math.sin(h_rad), -math.cos(h_rad), 0], dtype='f4')
            up = np.array([0, 0, 1], dtype='f4')

            pan_speed = self.camera_distance / 500.0
            self.camera_target -= right * delta.x() * pan_speed
            self.camera_target += up * delta.y() * pan_speed
            self.update()
            self.viewChanged.emit()

    def mouseReleaseEvent(self, event):
        """End interaction"""
        self.rotating = False
        self.panning = False
        self.last_mouse_pos = None
        self.setCursor(Qt.ArrowCursor)

    def keyPressEvent(self, event):
        """Keyboard shortcuts"""
        if event.key() == Qt.Key_Home:
            # Reset view
            self.camera_rotation_h = 45.0
            self.camera_rotation_v = 30.0
            self.camera_distance = 30.0
            if self.progetto:
                self.setProgetto(self.progetto)
            self.update()
        elif event.key() == Qt.Key_1:
            # Front view
            self.camera_rotation_h = 0
            self.camera_rotation_v = 0
            self.update()
        elif event.key() == Qt.Key_3:
            # Right view
            self.camera_rotation_h = 90
            self.camera_rotation_v = 0
            self.update()
        elif event.key() == Qt.Key_7:
            # Top view
            self.camera_rotation_h = 0
            self.camera_rotation_v = 89
            self.update()
        elif event.key() == Qt.Key_5:
            # Toggle perspective/ortho
            self.use_perspective = not self.use_perspective
            self.update()
        elif event.key() == Qt.Key_G:
            self.show_grid = not self.show_grid
            self.update()
