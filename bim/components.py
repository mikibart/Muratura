# -*- coding: utf-8 -*-
"""
BIM Components - Parametric structural elements
Inspired by FreeCAD's ArchComponent.py

Classes for walls, slabs, columns, beams, and other BIM elements
with full 3D geometry generation and IFC type mapping.
"""

import math
import numpy as np
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

try:
    from shapely.geometry import LineString, Polygon, Point, box
    from shapely.ops import unary_union
    from shapely import affinity
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False
    # Fallback types per type hints
    LineString = None
    Polygon = None
    Point = None
    box = None

try:
    from mathutils import Vector, Matrix, Quaternion
    HAS_MATHUTILS = True
except ImportError:
    HAS_MATHUTILS = False
    # Fallback Vector class
    class Vector:
        def __init__(self, coords=(0, 0, 0)):
            if len(coords) == 2:
                self.x, self.y = coords
                self.z = 0
            else:
                self.x, self.y, self.z = coords[:3]

        def __iter__(self):
            return iter([self.x, self.y, self.z])

        def __repr__(self):
            return f"Vector({self.x}, {self.y}, {self.z})"


class IFCType(Enum):
    """IFC entity types for BIM elements"""
    WALL = "IfcWall"
    WALL_STANDARD = "IfcWallStandardCase"
    SLAB = "IfcSlab"
    COLUMN = "IfcColumn"
    BEAM = "IfcBeam"
    FOOTING = "IfcFooting"
    ROOF = "IfcRoof"
    STAIR = "IfcStair"
    STAIR_FLIGHT = "IfcStairFlight"
    WINDOW = "IfcWindow"
    DOOR = "IfcDoor"
    OPENING = "IfcOpeningElement"
    MEMBER = "IfcMember"
    PLATE = "IfcPlate"
    RAILING = "IfcRailing"
    COVERING = "IfcCovering"
    BUILDING_ELEMENT_PROXY = "IfcBuildingElementProxy"


@dataclass
class Material:
    """Material definition for BIM elements"""
    name: str
    color: Tuple[float, float, float] = (0.8, 0.8, 0.8)  # RGB 0-1
    density: float = 2400.0  # kg/m³ (default: concrete)
    thermal_conductivity: float = 1.0  # W/(m·K)
    category: str = "Generic"

    # Common materials
    @classmethod
    def concrete(cls):
        return cls("Concrete", (0.7, 0.7, 0.7), 2400.0, 1.7, "Concrete")

    @classmethod
    def brick(cls):
        return cls("Brick", (0.76, 0.38, 0.28), 1800.0, 0.84, "Masonry")

    @classmethod
    def steel(cls):
        return cls("Steel", (0.6, 0.6, 0.65), 7850.0, 50.0, "Steel")

    @classmethod
    def wood(cls):
        return cls("Wood", (0.65, 0.45, 0.25), 600.0, 0.13, "Wood")

    @classmethod
    def glass(cls):
        return cls("Glass", (0.4, 0.6, 0.8), 2500.0, 1.0, "Glass")


@dataclass
class PropertySet:
    """IFC Property Set for BIM elements"""
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)


class BIMComponent(ABC):
    """
    Base class for all BIM components.
    Inspired by FreeCAD's ArchComponent.

    Provides:
    - Parametric geometry generation
    - IFC type mapping
    - Material assignment
    - Property sets for IFC export
    """

    def __init__(self, name: str = "BIMComponent"):
        self.name = name
        self.ifc_type: IFCType = IFCType.BUILDING_ELEMENT_PROXY
        self.material: Optional[Material] = None
        self.property_sets: List[PropertySet] = []

        # Geometry cache
        self._vertices: Optional[np.ndarray] = None
        self._normals: Optional[np.ndarray] = None
        self._indices: Optional[np.ndarray] = None
        self._dirty = True

        # Transform
        self.position = Vector((0, 0, 0))
        self.rotation = (0, 0, 0)  # Euler angles in degrees

        # Visualization
        self.visible = True
        self.selected = False
        self.color: Optional[Tuple[float, float, float]] = None

    @abstractmethod
    def _generate_geometry(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate 3D geometry for this component.

        Returns:
            vertices: np.ndarray of shape (N, 3) - vertex positions
            normals: np.ndarray of shape (N, 3) - vertex normals
            indices: np.ndarray of shape (M, 3) - triangle indices
        """
        pass

    def get_geometry(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Get cached geometry, regenerating if dirty"""
        if self._dirty or self._vertices is None:
            self._vertices, self._normals, self._indices = self._generate_geometry()
            self._dirty = False
        return self._vertices, self._normals, self._indices

    def invalidate_geometry(self):
        """Mark geometry as needing regeneration"""
        self._dirty = True

    def get_color(self) -> Tuple[float, float, float]:
        """Get display color (custom or from material)"""
        if self.color:
            return self.color
        if self.material:
            return self.material.color
        return (0.8, 0.8, 0.8)

    @abstractmethod
    def get_footprint(self) -> Optional[Polygon]:
        """Get 2D footprint as Shapely Polygon"""
        pass

    @abstractmethod
    def get_bounding_box(self) -> Tuple[Vector, Vector]:
        """Get axis-aligned bounding box (min, max)"""
        pass

    def add_property_set(self, name: str, properties: Dict[str, Any]):
        """Add an IFC property set"""
        self.property_sets.append(PropertySet(name, properties))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for saving"""
        return {
            'type': self.__class__.__name__,
            'name': self.name,
            'ifc_type': self.ifc_type.value,
            'position': list(self.position),
            'rotation': self.rotation,
            'material': self.material.name if self.material else None,
            'color': self.color,
            'visible': self.visible,
        }


class BIMWall(BIMComponent):
    """
    Parametric wall element.
    Inspired by FreeCAD's ArchWall.py

    A wall is defined by:
    - Base line (start and end points)
    - Height
    - Thickness
    - Offset (alignment: left, center, right)
    """

    def __init__(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        height: float = 3000.0,  # mm
        thickness: float = 300.0,  # mm
        offset: str = "center",  # "left", "center", "right"
        name: str = "Wall"
    ):
        super().__init__(name)
        self.ifc_type = IFCType.WALL_STANDARD

        self.start = Vector((start[0], start[1], 0))
        self.end = Vector((end[0], end[1], 0))
        self.height = height
        self.thickness = thickness
        self.offset = offset
        self.base_height = 0.0  # Height from ground

        self.material = Material.brick()

        # Openings (windows, doors)
        self.openings: List['BIMOpening'] = []

    @property
    def length(self) -> float:
        """Wall length"""
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        return math.sqrt(dx*dx + dy*dy)

    @property
    def direction(self) -> Vector:
        """Normalized wall direction"""
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        length = self.length
        if length < 0.001:
            return Vector((1, 0, 0))
        return Vector((dx/length, dy/length, 0))

    @property
    def normal(self) -> Vector:
        """Wall normal (perpendicular to direction)"""
        d = self.direction
        return Vector((-d.y, d.x, 0))

    def _get_offset_lines(self) -> Tuple[LineString, LineString]:
        """Get the two parallel lines defining wall edges"""
        half_t = self.thickness / 2

        if self.offset == "left":
            offset1, offset2 = 0, self.thickness
        elif self.offset == "right":
            offset1, offset2 = -self.thickness, 0
        else:  # center
            offset1, offset2 = -half_t, half_t

        n = self.normal
        s, e = self.start, self.end

        line1 = LineString([
            (s.x + n.x * offset1, s.y + n.y * offset1),
            (e.x + n.x * offset1, e.y + n.y * offset1)
        ])
        line2 = LineString([
            (s.x + n.x * offset2, s.y + n.y * offset2),
            (e.x + n.x * offset2, e.y + n.y * offset2)
        ])

        return line1, line2

    def get_footprint(self) -> Optional[Polygon]:
        """Get 2D footprint"""
        if not HAS_SHAPELY:
            return None

        line1, line2 = self._get_offset_lines()
        coords1 = list(line1.coords)
        coords2 = list(line2.coords)

        # Create polygon from the four corners
        polygon_coords = coords1 + list(reversed(coords2)) + [coords1[0]]
        return Polygon(polygon_coords)

    def get_bounding_box(self) -> Tuple[Vector, Vector]:
        """Get 3D bounding box"""
        footprint = self.get_footprint()
        if footprint:
            minx, miny, maxx, maxy = footprint.bounds
        else:
            minx = min(self.start.x, self.end.x) - self.thickness/2
            miny = min(self.start.y, self.end.y) - self.thickness/2
            maxx = max(self.start.x, self.end.x) + self.thickness/2
            maxy = max(self.start.y, self.end.y) + self.thickness/2

        return (
            Vector((minx, miny, self.base_height)),
            Vector((maxx, maxy, self.base_height + self.height))
        )

    def _generate_geometry(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate wall box geometry"""
        footprint = self.get_footprint()
        if footprint is None:
            # Fallback simple box
            return self._generate_simple_box()

        coords = list(footprint.exterior.coords)[:-1]  # Remove closing point
        z0 = self.base_height
        z1 = self.base_height + self.height

        vertices = []
        normals = []
        indices = []

        # Bottom face (4 vertices)
        for x, y in coords:
            vertices.append([x, y, z0])
            normals.append([0, 0, -1])

        # Top face (4 vertices)
        for x, y in coords:
            vertices.append([x, y, z1])
            normals.append([0, 0, 1])

        # Bottom triangles
        indices.extend([[0, 1, 2], [0, 2, 3]])
        # Top triangles
        indices.extend([[4, 6, 5], [4, 7, 6]])

        # Side faces (4 sides, each with 4 vertices)
        n_base = 8
        for i in range(4):
            i_next = (i + 1) % 4

            # Calculate face normal
            p0 = coords[i]
            p1 = coords[i_next]
            dx, dy = p1[0] - p0[0], p1[1] - p0[1]
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0.001:
                nx, ny = -dy/length, dx/length
            else:
                nx, ny = 0, 1

            # 4 vertices for this face
            base_idx = n_base + i * 4
            vertices.extend([
                [p0[0], p0[1], z0],
                [p1[0], p1[1], z0],
                [p1[0], p1[1], z1],
                [p0[0], p0[1], z1],
            ])
            normals.extend([
                [nx, ny, 0],
                [nx, ny, 0],
                [nx, ny, 0],
                [nx, ny, 0],
            ])
            indices.extend([
                [base_idx, base_idx+1, base_idx+2],
                [base_idx, base_idx+2, base_idx+3],
            ])

        return (
            np.array(vertices, dtype=np.float32),
            np.array(normals, dtype=np.float32),
            np.array(indices, dtype=np.uint32)
        )

    def _generate_simple_box(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Fallback box geometry without Shapely"""
        half_t = self.thickness / 2
        n = self.normal
        s, e = self.start, self.end
        z0 = self.base_height
        z1 = self.base_height + self.height

        # 4 corners of footprint
        corners = [
            (s.x - n.x * half_t, s.y - n.y * half_t),
            (e.x - n.x * half_t, e.y - n.y * half_t),
            (e.x + n.x * half_t, e.y + n.y * half_t),
            (s.x + n.x * half_t, s.y + n.y * half_t),
        ]

        # Generate box vertices (24 for proper normals)
        vertices = []
        normals = []

        # Each face has 4 vertices with same normal
        # Bottom (z=z0)
        for x, y in corners:
            vertices.append([x, y, z0])
            normals.append([0, 0, -1])
        # Top (z=z1)
        for x, y in corners:
            vertices.append([x, y, z1])
            normals.append([0, 0, 1])

        indices = [
            # Bottom
            [0, 1, 2], [0, 2, 3],
            # Top
            [4, 6, 5], [4, 7, 6],
        ]

        # 4 side faces
        for i in range(4):
            j = (i + 1) % 4
            c0, c1 = corners[i], corners[j]
            dx, dy = c1[0] - c0[0], c1[1] - c0[1]
            length = math.sqrt(dx*dx + dy*dy)
            nx, ny = (-dy/length, dx/length) if length > 0 else (0, 1)

            base = len(vertices)
            vertices.extend([
                [c0[0], c0[1], z0],
                [c1[0], c1[1], z0],
                [c1[0], c1[1], z1],
                [c0[0], c0[1], z1],
            ])
            normals.extend([[nx, ny, 0]] * 4)
            indices.extend([
                [base, base+1, base+2],
                [base, base+2, base+3],
            ])

        return (
            np.array(vertices, dtype=np.float32),
            np.array(normals, dtype=np.float32),
            np.array(indices, dtype=np.uint32)
        )

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'start': (self.start.x, self.start.y),
            'end': (self.end.x, self.end.y),
            'height': self.height,
            'thickness': self.thickness,
            'offset': self.offset,
            'base_height': self.base_height,
        })
        return data


class BIMSlab(BIMComponent):
    """
    Parametric slab/floor element.
    Inspired by FreeCAD's ArchFloor/BIM_Slab
    """

    def __init__(
        self,
        outline: List[Tuple[float, float]],
        thickness: float = 200.0,  # mm
        elevation: float = 0.0,  # mm from ground
        name: str = "Slab"
    ):
        super().__init__(name)
        self.ifc_type = IFCType.SLAB

        self.outline = outline  # 2D polygon vertices
        self.thickness = thickness
        self.elevation = elevation

        self.material = Material.concrete()

    def get_footprint(self) -> Optional[Polygon]:
        if not HAS_SHAPELY or len(self.outline) < 3:
            return None
        return Polygon(self.outline)

    def get_bounding_box(self) -> Tuple[Vector, Vector]:
        xs = [p[0] for p in self.outline]
        ys = [p[1] for p in self.outline]
        return (
            Vector((min(xs), min(ys), self.elevation)),
            Vector((max(xs), max(ys), self.elevation + self.thickness))
        )

    def _generate_geometry(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate slab geometry by extruding footprint"""
        if len(self.outline) < 3:
            return np.array([]), np.array([]), np.array([])

        coords = self.outline
        z0 = self.elevation
        z1 = self.elevation + self.thickness
        n = len(coords)

        vertices = []
        normals = []
        indices = []

        # Bottom face
        for x, y in coords:
            vertices.append([x, y, z0])
            normals.append([0, 0, -1])

        # Top face
        for x, y in coords:
            vertices.append([x, y, z1])
            normals.append([0, 0, 1])

        # Triangulate polygon (simple fan for convex)
        for i in range(1, n - 1):
            indices.append([0, i + 1, i])  # Bottom (flipped for outward normal)
            indices.append([n, n + i, n + i + 1])  # Top

        # Side faces
        base = 2 * n
        for i in range(n):
            j = (i + 1) % n
            c0, c1 = coords[i], coords[j]
            dx, dy = c1[0] - c0[0], c1[1] - c0[1]
            length = math.sqrt(dx*dx + dy*dy)
            nx, ny = (-dy/length, dx/length) if length > 0 else (0, 1)

            idx = base + i * 4
            vertices.extend([
                [c0[0], c0[1], z0],
                [c1[0], c1[1], z0],
                [c1[0], c1[1], z1],
                [c0[0], c0[1], z1],
            ])
            normals.extend([[nx, ny, 0]] * 4)
            indices.extend([
                [idx, idx+1, idx+2],
                [idx, idx+2, idx+3],
            ])

        return (
            np.array(vertices, dtype=np.float32),
            np.array(normals, dtype=np.float32),
            np.array(indices, dtype=np.uint32)
        )

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'outline': self.outline,
            'thickness': self.thickness,
            'elevation': self.elevation,
        })
        return data


class BIMColumn(BIMComponent):
    """
    Parametric column element.
    Inspired by FreeCAD's ArchStructure (column type)
    """

    def __init__(
        self,
        position: Tuple[float, float],
        width: float = 300.0,  # mm
        depth: float = 300.0,  # mm
        height: float = 3000.0,  # mm
        base_elevation: float = 0.0,
        shape: str = "rectangular",  # "rectangular", "circular"
        name: str = "Column"
    ):
        super().__init__(name)
        self.ifc_type = IFCType.COLUMN

        self.position = Vector((position[0], position[1], base_elevation))
        self.width = width
        self.depth = depth
        self.height = height
        self.base_elevation = base_elevation
        self.shape = shape

        self.material = Material.concrete()

    def get_footprint(self) -> Optional[Polygon]:
        if not HAS_SHAPELY:
            return None

        x, y = self.position.x, self.position.y
        hw, hd = self.width / 2, self.depth / 2

        if self.shape == "circular":
            return Point(x, y).buffer(self.width / 2, resolution=16)
        else:
            return box(x - hw, y - hd, x + hw, y + hd)

    def get_bounding_box(self) -> Tuple[Vector, Vector]:
        x, y = self.position.x, self.position.y
        hw, hd = self.width / 2, self.depth / 2
        return (
            Vector((x - hw, y - hd, self.base_elevation)),
            Vector((x + hw, y + hd, self.base_elevation + self.height))
        )

    def _generate_geometry(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate column geometry"""
        if self.shape == "circular":
            return self._generate_cylinder()
        else:
            return self._generate_box()

    def _generate_box(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        x, y = self.position.x, self.position.y
        hw, hd = self.width / 2, self.depth / 2
        z0 = self.base_elevation
        z1 = self.base_elevation + self.height

        corners = [
            (x - hw, y - hd),
            (x + hw, y - hd),
            (x + hw, y + hd),
            (x - hw, y + hd),
        ]

        vertices = []
        normals = []
        indices = []

        # Bottom and top faces
        for cx, cy in corners:
            vertices.append([cx, cy, z0])
            normals.append([0, 0, -1])
        for cx, cy in corners:
            vertices.append([cx, cy, z1])
            normals.append([0, 0, 1])

        indices = [
            [0, 1, 2], [0, 2, 3],  # Bottom
            [4, 6, 5], [4, 7, 6],  # Top
        ]

        # Side faces
        face_normals = [(0, -1, 0), (1, 0, 0), (0, 1, 0), (-1, 0, 0)]
        base = 8
        for i in range(4):
            j = (i + 1) % 4
            c0, c1 = corners[i], corners[j]
            fn = face_normals[i]

            idx = base + i * 4
            vertices.extend([
                [c0[0], c0[1], z0],
                [c1[0], c1[1], z0],
                [c1[0], c1[1], z1],
                [c0[0], c0[1], z1],
            ])
            normals.extend([list(fn)] * 4)
            indices.extend([
                [idx, idx+1, idx+2],
                [idx, idx+2, idx+3],
            ])

        return (
            np.array(vertices, dtype=np.float32),
            np.array(normals, dtype=np.float32),
            np.array(indices, dtype=np.uint32)
        )

    def _generate_cylinder(self, segments: int = 24) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate cylindrical column"""
        x, y = self.position.x, self.position.y
        r = self.width / 2
        z0 = self.base_elevation
        z1 = self.base_elevation + self.height

        vertices = []
        normals = []
        indices = []

        # Generate circle vertices
        angles = [2 * math.pi * i / segments for i in range(segments)]
        circle = [(x + r * math.cos(a), y + r * math.sin(a)) for a in angles]

        # Bottom face
        vertices.append([x, y, z0])  # Center
        normals.append([0, 0, -1])
        for cx, cy in circle:
            vertices.append([cx, cy, z0])
            normals.append([0, 0, -1])

        # Bottom triangles (fan)
        for i in range(segments):
            j = (i + 1) % segments
            indices.append([0, i + 2 if j > 0 else 1, i + 1])

        # Top face
        top_center = len(vertices)
        vertices.append([x, y, z1])
        normals.append([0, 0, 1])
        for cx, cy in circle:
            vertices.append([cx, cy, z1])
            normals.append([0, 0, 1])

        for i in range(segments):
            j = (i + 1) % segments
            indices.append([top_center, top_center + i + 1, top_center + j + 1])

        # Side faces
        side_base = len(vertices)
        for i in range(segments):
            j = (i + 1) % segments
            c0, c1 = circle[i], circle[j]

            # Normal for this segment
            nx0 = math.cos(angles[i])
            ny0 = math.sin(angles[i])
            nx1 = math.cos(angles[j])
            ny1 = math.sin(angles[j])

            idx = side_base + i * 4
            vertices.extend([
                [c0[0], c0[1], z0],
                [c1[0], c1[1], z0],
                [c1[0], c1[1], z1],
                [c0[0], c0[1], z1],
            ])
            normals.extend([
                [nx0, ny0, 0],
                [nx1, ny1, 0],
                [nx1, ny1, 0],
                [nx0, ny0, 0],
            ])
            indices.extend([
                [idx, idx+1, idx+2],
                [idx, idx+2, idx+3],
            ])

        return (
            np.array(vertices, dtype=np.float32),
            np.array(normals, dtype=np.float32),
            np.array(indices, dtype=np.uint32)
        )

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'position': (self.position.x, self.position.y),
            'width': self.width,
            'depth': self.depth,
            'height': self.height,
            'base_elevation': self.base_elevation,
            'shape': self.shape,
        })
        return data


class BIMBeam(BIMComponent):
    """
    Parametric beam element.
    Inspired by FreeCAD's ArchStructure (beam type)
    """

    def __init__(
        self,
        start: Tuple[float, float, float],
        end: Tuple[float, float, float],
        width: float = 300.0,  # mm
        height: float = 500.0,  # mm
        name: str = "Beam"
    ):
        super().__init__(name)
        self.ifc_type = IFCType.BEAM

        self.start = Vector(start)
        self.end = Vector(end)
        self.width = width
        self.height = height

        self.material = Material.concrete()

    @property
    def length(self) -> float:
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        dz = self.end.z - self.start.z
        return math.sqrt(dx*dx + dy*dy + dz*dz)

    def get_footprint(self) -> Optional[Polygon]:
        """2D footprint (projection on XY plane)"""
        if not HAS_SHAPELY:
            return None

        s, e = self.start, self.end
        dx, dy = e.x - s.x, e.y - s.y
        length_2d = math.sqrt(dx*dx + dy*dy)
        if length_2d < 0.001:
            return Point(s.x, s.y).buffer(self.width / 2)

        # Perpendicular vector
        nx, ny = -dy / length_2d, dx / length_2d
        hw = self.width / 2

        return Polygon([
            (s.x - nx * hw, s.y - ny * hw),
            (e.x - nx * hw, e.y - ny * hw),
            (e.x + nx * hw, e.y + ny * hw),
            (s.x + nx * hw, s.y + ny * hw),
        ])

    def get_bounding_box(self) -> Tuple[Vector, Vector]:
        s, e = self.start, self.end
        hw, hh = self.width / 2, self.height / 2
        return (
            Vector((
                min(s.x, e.x) - hw,
                min(s.y, e.y) - hw,
                min(s.z, e.z) - hh
            )),
            Vector((
                max(s.x, e.x) + hw,
                max(s.y, e.y) + hw,
                max(s.z, e.z) + hh
            ))
        )

    def _generate_geometry(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate beam geometry (box along axis)"""
        # For simplicity, generate horizontal beam and apply transform
        # In production, use proper 3D orientation

        s, e = self.start, self.end
        hw, hh = self.width / 2, self.height / 2

        # Direction and perpendicular
        dx, dy, dz = e.x - s.x, e.y - s.y, e.z - s.z
        length = self.length
        if length < 0.001:
            return np.array([]), np.array([]), np.array([])

        # Normalized direction
        d = (dx / length, dy / length, dz / length)

        # Perpendicular in XY plane
        len_xy = math.sqrt(d[0]*d[0] + d[1]*d[1])
        if len_xy > 0.001:
            px, py = -d[1] / len_xy, d[0] / len_xy
        else:
            px, py = 1, 0

        # Up vector (perpendicular to both)
        ux = d[1] * 0 - d[2] * py
        uy = d[2] * px - d[0] * 0
        uz = d[0] * py - d[1] * px
        ul = math.sqrt(ux*ux + uy*uy + uz*uz)
        if ul > 0:
            ux, uy, uz = ux/ul, uy/ul, uz/ul
        else:
            ux, uy, uz = 0, 0, 1

        # 8 corners of beam box
        corners_start = [
            (s.x - px*hw - ux*hh, s.y - py*hw - uy*hh, s.z - uz*hh),
            (s.x + px*hw - ux*hh, s.y + py*hw - uy*hh, s.z - uz*hh),
            (s.x + px*hw + ux*hh, s.y + py*hw + uy*hh, s.z + uz*hh),
            (s.x - px*hw + ux*hh, s.y - py*hw + uy*hh, s.z + uz*hh),
        ]
        corners_end = [
            (e.x - px*hw - ux*hh, e.y - py*hw - uy*hh, e.z - uz*hh),
            (e.x + px*hw - ux*hh, e.y + py*hw - uy*hh, e.z - uz*hh),
            (e.x + px*hw + ux*hh, e.y + py*hw + uy*hh, e.z + uz*hh),
            (e.x - px*hw + ux*hh, e.y - py*hw + uy*hh, e.z + uz*hh),
        ]

        vertices = []
        normals = []
        indices = []

        # Start face
        for c in corners_start:
            vertices.append(list(c))
            normals.append([-d[0], -d[1], -d[2]])

        # End face
        for c in corners_end:
            vertices.append(list(c))
            normals.append([d[0], d[1], d[2]])

        indices = [
            [0, 2, 1], [0, 3, 2],  # Start
            [4, 5, 6], [4, 6, 7],  # End
        ]

        # Side faces
        face_normals = [
            (-ux, -uy, -uz),  # Bottom
            (px, py, 0),      # Right
            (ux, uy, uz),     # Top
            (-px, -py, 0),    # Left
        ]
        edge_pairs = [(0, 1), (1, 2), (2, 3), (3, 0)]

        base = 8
        for i, (i0, i1) in enumerate(edge_pairs):
            fn = face_normals[i]
            idx = base + i * 4
            vertices.extend([
                list(corners_start[i0]),
                list(corners_start[i1]),
                list(corners_end[i1]),
                list(corners_end[i0]),
            ])
            normals.extend([list(fn)] * 4)
            indices.extend([
                [idx, idx+1, idx+2],
                [idx, idx+2, idx+3],
            ])

        return (
            np.array(vertices, dtype=np.float32),
            np.array(normals, dtype=np.float32),
            np.array(indices, dtype=np.uint32)
        )

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'start': (self.start.x, self.start.y, self.start.z),
            'end': (self.end.x, self.end.y, self.end.z),
            'width': self.width,
            'height': self.height,
        })
        return data


class BIMFoundation(BIMComponent):
    """Parametric foundation element"""

    def __init__(
        self,
        outline: List[Tuple[float, float]],
        depth: float = 500.0,  # mm
        elevation: float = -500.0,  # mm (below ground)
        name: str = "Foundation"
    ):
        super().__init__(name)
        self.ifc_type = IFCType.FOOTING

        self.outline = outline
        self.depth = depth
        self.elevation = elevation

        self.material = Material.concrete()

    def get_footprint(self) -> Optional[Polygon]:
        if not HAS_SHAPELY or len(self.outline) < 3:
            return None
        return Polygon(self.outline)

    def get_bounding_box(self) -> Tuple[Vector, Vector]:
        xs = [p[0] for p in self.outline]
        ys = [p[1] for p in self.outline]
        return (
            Vector((min(xs), min(ys), self.elevation)),
            Vector((max(xs), max(ys), self.elevation + self.depth))
        )

    def _generate_geometry(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        # Same as slab but with different elevation
        slab = BIMSlab(self.outline, self.depth, self.elevation)
        return slab._generate_geometry()


class BIMRoof(BIMComponent):
    """Parametric roof element (flat roof for now)"""

    def __init__(
        self,
        outline: List[Tuple[float, float]],
        thickness: float = 300.0,
        elevation: float = 3000.0,
        name: str = "Roof"
    ):
        super().__init__(name)
        self.ifc_type = IFCType.ROOF

        self.outline = outline
        self.thickness = thickness
        self.elevation = elevation

        self.material = Material.concrete()

    def get_footprint(self) -> Optional[Polygon]:
        if not HAS_SHAPELY or len(self.outline) < 3:
            return None
        return Polygon(self.outline)

    def get_bounding_box(self) -> Tuple[Vector, Vector]:
        xs = [p[0] for p in self.outline]
        ys = [p[1] for p in self.outline]
        return (
            Vector((min(xs), min(ys), self.elevation)),
            Vector((max(xs), max(ys), self.elevation + self.thickness))
        )

    def _generate_geometry(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        slab = BIMSlab(self.outline, self.thickness, self.elevation)
        return slab._generate_geometry()


class BIMStairs(BIMComponent):
    """Parametric stairs element"""

    def __init__(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        width: float = 1200.0,
        height: float = 3000.0,
        riser_height: float = 175.0,
        tread_depth: float = 280.0,
        name: str = "Stairs"
    ):
        super().__init__(name)
        self.ifc_type = IFCType.STAIR

        self.start = Vector((start[0], start[1], 0))
        self.end = Vector((end[0], end[1], 0))
        self.width = width
        self.height = height
        self.riser_height = riser_height
        self.tread_depth = tread_depth

        self.material = Material.concrete()

    @property
    def num_risers(self) -> int:
        return max(1, int(self.height / self.riser_height))

    @property
    def actual_riser_height(self) -> float:
        return self.height / self.num_risers

    def get_footprint(self) -> Optional[Polygon]:
        if not HAS_SHAPELY:
            return None

        s, e = self.start, self.end
        dx, dy = e.x - s.x, e.y - s.y
        length = math.sqrt(dx*dx + dy*dy)
        if length < 0.001:
            return None

        # Perpendicular for width
        nx, ny = -dy / length, dx / length
        hw = self.width / 2

        return Polygon([
            (s.x - nx * hw, s.y - ny * hw),
            (e.x - nx * hw, e.y - ny * hw),
            (e.x + nx * hw, e.y + ny * hw),
            (s.x + nx * hw, s.y + ny * hw),
        ])

    def get_bounding_box(self) -> Tuple[Vector, Vector]:
        footprint = self.get_footprint()
        if footprint:
            minx, miny, maxx, maxy = footprint.bounds
        else:
            minx = min(self.start.x, self.end.x) - self.width/2
            miny = min(self.start.y, self.end.y) - self.width/2
            maxx = max(self.start.x, self.end.x) + self.width/2
            maxy = max(self.start.y, self.end.y) + self.width/2

        return (
            Vector((minx, miny, 0)),
            Vector((maxx, maxy, self.height))
        )

    def _generate_geometry(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate stair steps geometry"""
        # Simplified: just generate boxes for each step
        vertices = []
        normals = []
        indices = []

        s, e = self.start, self.end
        dx, dy = e.x - s.x, e.y - s.y
        length = math.sqrt(dx*dx + dy*dy)
        if length < 0.001:
            return np.array([]), np.array([]), np.array([])

        # Direction and perpendicular
        dir_x, dir_y = dx / length, dy / length
        nx, ny = -dir_y, dir_x
        hw = self.width / 2

        n_steps = self.num_risers
        step_length = length / n_steps
        riser_h = self.actual_riser_height

        for i in range(n_steps):
            # Step position
            t0 = i / n_steps
            t1 = (i + 1) / n_steps
            x0 = s.x + dx * t0
            y0 = s.y + dy * t0
            x1 = s.x + dx * t1
            y1 = s.y + dy * t1
            z0 = i * riser_h
            z1 = (i + 1) * riser_h

            # 8 corners of step box
            corners_back = [
                (x0 - nx*hw, y0 - ny*hw, z0),
                (x0 + nx*hw, y0 + ny*hw, z0),
                (x0 + nx*hw, y0 + ny*hw, z1),
                (x0 - nx*hw, y0 - ny*hw, z1),
            ]
            corners_front = [
                (x1 - nx*hw, y1 - ny*hw, z0),
                (x1 + nx*hw, y1 + ny*hw, z0),
                (x1 + nx*hw, y1 + ny*hw, z1),
                (x1 - nx*hw, y1 - ny*hw, z1),
            ]

            base_idx = len(vertices)

            # Add all vertices
            for c in corners_back + corners_front:
                vertices.append(list(c))

            # Normals and indices for each face (simplified)
            # Back face
            normals.extend([[-dir_x, -dir_y, 0]] * 4)
            # Front face
            normals.extend([[dir_x, dir_y, 0]] * 4)

            indices.extend([
                [base_idx, base_idx+1, base_idx+2],
                [base_idx, base_idx+2, base_idx+3],
                [base_idx+4, base_idx+6, base_idx+5],
                [base_idx+4, base_idx+7, base_idx+6],
            ])

            # Top face
            top_base = len(vertices)
            vertices.extend([
                corners_back[3], corners_back[2],
                corners_front[2], corners_front[3]
            ])
            normals.extend([[0, 0, 1]] * 4)
            indices.extend([
                [top_base, top_base+1, top_base+2],
                [top_base, top_base+2, top_base+3],
            ])

        return (
            np.array(vertices, dtype=np.float32),
            np.array(normals, dtype=np.float32),
            np.array(indices, dtype=np.uint32)
        )


class BIMWindow(BIMComponent):
    """Window opening element"""

    def __init__(
        self,
        position: Tuple[float, float, float],
        width: float = 1200.0,
        height: float = 1500.0,
        sill_height: float = 900.0,
        name: str = "Window"
    ):
        super().__init__(name)
        self.ifc_type = IFCType.WINDOW

        self.position = Vector(position)
        self.width = width
        self.height = height
        self.sill_height = sill_height

        self.material = Material.glass()

    def get_footprint(self) -> Optional[Polygon]:
        return None  # Windows don't have floor footprint

    def get_bounding_box(self) -> Tuple[Vector, Vector]:
        x, y, z = self.position.x, self.position.y, self.position.z
        return (
            Vector((x - self.width/2, y - 100, z + self.sill_height)),
            Vector((x + self.width/2, y + 100, z + self.sill_height + self.height))
        )

    def _generate_geometry(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        # Simple glass pane
        x, y, z = self.position.x, self.position.y, self.position.z
        hw = self.width / 2
        z0 = z + self.sill_height
        z1 = z0 + self.height

        vertices = np.array([
            [x - hw, y, z0],
            [x + hw, y, z0],
            [x + hw, y, z1],
            [x - hw, y, z1],
        ], dtype=np.float32)

        normals = np.array([
            [0, 1, 0],
            [0, 1, 0],
            [0, 1, 0],
            [0, 1, 0],
        ], dtype=np.float32)

        indices = np.array([
            [0, 1, 2],
            [0, 2, 3],
        ], dtype=np.uint32)

        return vertices, normals, indices


class BIMDoor(BIMComponent):
    """Door opening element"""

    def __init__(
        self,
        position: Tuple[float, float, float],
        width: float = 900.0,
        height: float = 2100.0,
        name: str = "Door"
    ):
        super().__init__(name)
        self.ifc_type = IFCType.DOOR

        self.position = Vector(position)
        self.width = width
        self.height = height

        self.material = Material.wood()

    def get_footprint(self) -> Optional[Polygon]:
        if not HAS_SHAPELY:
            return None
        x, y = self.position.x, self.position.y
        hw = self.width / 2
        return box(x - hw, y - 50, x + hw, y + 50)

    def get_bounding_box(self) -> Tuple[Vector, Vector]:
        x, y, z = self.position.x, self.position.y, self.position.z
        return (
            Vector((x - self.width/2, y - 100, z)),
            Vector((x + self.width/2, y + 100, z + self.height))
        )

    def _generate_geometry(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        # Simple door panel
        x, y, z = self.position.x, self.position.y, self.position.z
        hw = self.width / 2
        t = 50  # Door thickness

        # Box geometry
        vertices = []
        normals = []
        indices = []

        corners = [
            (x - hw, y - t/2),
            (x + hw, y - t/2),
            (x + hw, y + t/2),
            (x - hw, y + t/2),
        ]

        # Bottom and top
        for cx, cy in corners:
            vertices.append([cx, cy, z])
            normals.append([0, 0, -1])
        for cx, cy in corners:
            vertices.append([cx, cy, z + self.height])
            normals.append([0, 0, 1])

        indices = [
            [0, 1, 2], [0, 2, 3],
            [4, 6, 5], [4, 7, 6],
        ]

        # Sides
        face_normals = [(0, -1, 0), (1, 0, 0), (0, 1, 0), (-1, 0, 0)]
        base = 8
        for i in range(4):
            j = (i + 1) % 4
            c0, c1 = corners[i], corners[j]
            fn = face_normals[i]

            idx = base + i * 4
            vertices.extend([
                [c0[0], c0[1], z],
                [c1[0], c1[1], z],
                [c1[0], c1[1], z + self.height],
                [c0[0], c0[1], z + self.height],
            ])
            normals.extend([list(fn)] * 4)
            indices.extend([
                [idx, idx+1, idx+2],
                [idx, idx+2, idx+3],
            ])

        return (
            np.array(vertices, dtype=np.float32),
            np.array(normals, dtype=np.float32),
            np.array(indices, dtype=np.uint32)
        )


# Alias for compatibility
BIMOpening = BIMWindow  # Openings are similar to windows
