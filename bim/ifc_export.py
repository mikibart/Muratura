# -*- coding: utf-8 -*-
"""
IFC Export/Import Module
Uses ifcopenshell for Industry Foundation Classes support

Inspired by FreeCAD's ifc_export.py
"""

import os
import math
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

try:
    import ifcopenshell
    import ifcopenshell.api
    import ifcopenshell.util.element
    import ifcopenshell.util.placement
    HAS_IFC = True
except ImportError:
    HAS_IFC = False
    ifcopenshell = None

from .components import (
    BIMComponent, BIMWall, BIMSlab, BIMColumn, BIMBeam,
    BIMFoundation, BIMRoof, BIMStairs, BIMWindow, BIMDoor,
    IFCType, Material
)


class IFCExporter:
    """
    Exports BIM components to IFC format.
    Follows IFC4 schema.
    """

    def __init__(self, project_name: str = "Muratura Project"):
        if not HAS_IFC:
            raise ImportError("ifcopenshell is required for IFC export")

        self.project_name = project_name
        self.model = None
        self.project = None
        self.site = None
        self.building = None
        self.storey = None

        # Context for geometry
        self.context = None
        self.body_context = None

    def create_model(self, author: str = "Muratura CAD") -> None:
        """Initialize IFC model with project structure"""
        # Create new IFC file
        self.model = ifcopenshell.api.run("project.create_file", version="IFC4")

        # Create project
        self.project = ifcopenshell.api.run(
            "root.create_entity",
            self.model,
            ifc_class="IfcProject",
            name=self.project_name
        )

        # Set units (millimeters)
        ifcopenshell.api.run(
            "unit.assign_unit",
            self.model,
            units=[
                {"type": "LENGTHUNIT", "name": "MILLIMETRE"},
                {"type": "AREAUNIT", "name": "SQUARE_METRE"},
                {"type": "VOLUMEUNIT", "name": "CUBIC_METRE"},
                {"type": "PLANEANGLEUNIT", "name": "DEGREE"},
            ]
        )

        # Create geometric contexts
        self.context = ifcopenshell.api.run(
            "context.add_context",
            self.model,
            context_type="Model"
        )
        self.body_context = ifcopenshell.api.run(
            "context.add_context",
            self.model,
            context_type="Model",
            context_identifier="Body",
            target_view="MODEL_VIEW",
            parent=self.context
        )

        # Create spatial structure
        self.site = ifcopenshell.api.run(
            "root.create_entity",
            self.model,
            ifc_class="IfcSite",
            name="Site"
        )
        ifcopenshell.api.run(
            "aggregate.assign_object",
            self.model,
            product=self.site,
            relating_object=self.project
        )

        self.building = ifcopenshell.api.run(
            "root.create_entity",
            self.model,
            ifc_class="IfcBuilding",
            name="Building"
        )
        ifcopenshell.api.run(
            "aggregate.assign_object",
            self.model,
            product=self.building,
            relating_object=self.site
        )

        self.storey = ifcopenshell.api.run(
            "root.create_entity",
            self.model,
            ifc_class="IfcBuildingStorey",
            name="Ground Floor"
        )
        ifcopenshell.api.run(
            "aggregate.assign_object",
            self.model,
            product=self.storey,
            relating_object=self.building
        )

        # Add owner history
        self._add_owner_history(author)

    def _add_owner_history(self, author: str) -> None:
        """Add ownership and history information"""
        person = self.model.create_entity(
            "IfcPerson",
            FamilyName=author
        )
        organization = self.model.create_entity(
            "IfcOrganization",
            Name="Muratura CAD"
        )
        person_org = self.model.create_entity(
            "IfcPersonAndOrganization",
            ThePerson=person,
            TheOrganization=organization
        )
        application = self.model.create_entity(
            "IfcApplication",
            ApplicationDeveloper=organization,
            Version="1.0",
            ApplicationFullName="Muratura Professional CAD",
            ApplicationIdentifier="Muratura"
        )
        self.model.create_entity(
            "IfcOwnerHistory",
            OwningUser=person_org,
            OwningApplication=application,
            CreationDate=int(datetime.now().timestamp())
        )

    def export_component(self, component: BIMComponent) -> Optional[Any]:
        """Export a single BIM component to IFC entity"""
        if not self.model:
            self.create_model()

        ifc_class = component.ifc_type.value

        # Create IFC entity
        element = ifcopenshell.api.run(
            "root.create_entity",
            self.model,
            ifc_class=ifc_class,
            name=component.name
        )

        # Assign to building storey
        ifcopenshell.api.run(
            "spatial.assign_container",
            self.model,
            product=element,
            relating_structure=self.storey
        )

        # Add geometry based on component type
        if isinstance(component, BIMWall):
            self._add_wall_geometry(element, component)
        elif isinstance(component, BIMSlab):
            self._add_slab_geometry(element, component)
        elif isinstance(component, BIMColumn):
            self._add_column_geometry(element, component)
        elif isinstance(component, BIMBeam):
            self._add_beam_geometry(element, component)
        else:
            # Generic extrusion for other types
            self._add_generic_geometry(element, component)

        # Add material
        if component.material:
            self._add_material(element, component.material)

        # Add property sets
        for pset in component.property_sets:
            self._add_property_set(element, pset.name, pset.properties)

        return element

    def _add_wall_geometry(self, element: Any, wall: BIMWall) -> None:
        """Add wall geometry using extrusion"""
        # Get footprint
        footprint = wall.get_footprint()
        if footprint is None:
            return

        coords = list(footprint.exterior.coords)[:-1]

        # Create profile
        profile = self.model.create_entity(
            "IfcArbitraryClosedProfileDef",
            ProfileType="AREA",
            OuterCurve=self._create_polyline_2d(coords)
        )

        # Create extrusion
        extrusion_direction = self.model.create_entity(
            "IfcDirection",
            DirectionRatios=[0.0, 0.0, 1.0]
        )

        solid = self.model.create_entity(
            "IfcExtrudedAreaSolid",
            SweptArea=profile,
            Position=self._create_axis_placement_3d(
                (0, 0, wall.base_height),
                (0, 0, 1),
                (1, 0, 0)
            ),
            ExtrudedDirection=extrusion_direction,
            Depth=wall.height
        )

        self._assign_representation(element, solid)

    def _add_slab_geometry(self, element: Any, slab: BIMSlab) -> None:
        """Add slab geometry"""
        footprint = slab.get_footprint()
        if footprint is None:
            return

        coords = list(footprint.exterior.coords)[:-1]

        profile = self.model.create_entity(
            "IfcArbitraryClosedProfileDef",
            ProfileType="AREA",
            OuterCurve=self._create_polyline_2d(coords)
        )

        extrusion_direction = self.model.create_entity(
            "IfcDirection",
            DirectionRatios=[0.0, 0.0, 1.0]
        )

        solid = self.model.create_entity(
            "IfcExtrudedAreaSolid",
            SweptArea=profile,
            Position=self._create_axis_placement_3d(
                (0, 0, slab.elevation),
                (0, 0, 1),
                (1, 0, 0)
            ),
            ExtrudedDirection=extrusion_direction,
            Depth=slab.thickness
        )

        self._assign_representation(element, solid)

    def _add_column_geometry(self, element: Any, column: BIMColumn) -> None:
        """Add column geometry"""
        if column.shape == "circular":
            profile = self.model.create_entity(
                "IfcCircleProfileDef",
                ProfileType="AREA",
                Radius=column.width / 2
            )
        else:
            profile = self.model.create_entity(
                "IfcRectangleProfileDef",
                ProfileType="AREA",
                XDim=column.width,
                YDim=column.depth
            )

        extrusion_direction = self.model.create_entity(
            "IfcDirection",
            DirectionRatios=[0.0, 0.0, 1.0]
        )

        solid = self.model.create_entity(
            "IfcExtrudedAreaSolid",
            SweptArea=profile,
            Position=self._create_axis_placement_3d(
                (column.position.x, column.position.y, column.base_elevation),
                (0, 0, 1),
                (1, 0, 0)
            ),
            ExtrudedDirection=extrusion_direction,
            Depth=column.height
        )

        self._assign_representation(element, solid)

    def _add_beam_geometry(self, element: Any, beam: BIMBeam) -> None:
        """Add beam geometry"""
        profile = self.model.create_entity(
            "IfcRectangleProfileDef",
            ProfileType="AREA",
            XDim=beam.width,
            YDim=beam.height
        )

        # Calculate beam direction
        dx = beam.end.x - beam.start.x
        dy = beam.end.y - beam.start.y
        dz = beam.end.z - beam.start.z
        length = beam.length

        if length < 0.001:
            return

        dir_x, dir_y, dir_z = dx/length, dy/length, dz/length

        extrusion_direction = self.model.create_entity(
            "IfcDirection",
            DirectionRatios=[dir_x, dir_y, dir_z]
        )

        # Calculate reference direction (perpendicular)
        if abs(dir_z) < 0.99:
            ref_x, ref_y, ref_z = 0, 0, 1
        else:
            ref_x, ref_y, ref_z = 1, 0, 0

        solid = self.model.create_entity(
            "IfcExtrudedAreaSolid",
            SweptArea=profile,
            Position=self._create_axis_placement_3d(
                (beam.start.x, beam.start.y, beam.start.z),
                (dir_x, dir_y, dir_z),
                (ref_x, ref_y, ref_z)
            ),
            ExtrudedDirection=extrusion_direction,
            Depth=length
        )

        self._assign_representation(element, solid)

    def _add_generic_geometry(self, element: Any, component: BIMComponent) -> None:
        """Add geometry from component's generated mesh"""
        vertices, normals, indices = component.get_geometry()

        if len(vertices) == 0:
            return

        # Create tessellated representation
        # (Simplified - in production use proper tessellation)
        bbox_min, bbox_max = component.get_bounding_box()

        # Create a simple bounding box for now
        width = bbox_max.x - bbox_min.x
        depth = bbox_max.y - bbox_min.y
        height = bbox_max.z - bbox_min.z

        profile = self.model.create_entity(
            "IfcRectangleProfileDef",
            ProfileType="AREA",
            XDim=width,
            YDim=depth
        )

        solid = self.model.create_entity(
            "IfcExtrudedAreaSolid",
            SweptArea=profile,
            Position=self._create_axis_placement_3d(
                ((bbox_min.x + bbox_max.x)/2, (bbox_min.y + bbox_max.y)/2, bbox_min.z),
                (0, 0, 1),
                (1, 0, 0)
            ),
            ExtrudedDirection=self.model.create_entity(
                "IfcDirection",
                DirectionRatios=[0.0, 0.0, 1.0]
            ),
            Depth=height
        )

        self._assign_representation(element, solid)

    def _create_polyline_2d(self, coords: List[Tuple[float, float]]) -> Any:
        """Create 2D polyline from coordinates"""
        points = []
        for x, y in coords:
            point = self.model.create_entity(
                "IfcCartesianPoint",
                Coordinates=[float(x), float(y)]
            )
            points.append(point)

        # Close the polyline
        points.append(points[0])

        return self.model.create_entity(
            "IfcPolyline",
            Points=points
        )

    def _create_axis_placement_3d(
        self,
        location: Tuple[float, float, float],
        axis: Tuple[float, float, float],
        ref_direction: Tuple[float, float, float]
    ) -> Any:
        """Create 3D axis placement"""
        return self.model.create_entity(
            "IfcAxis2Placement3D",
            Location=self.model.create_entity(
                "IfcCartesianPoint",
                Coordinates=list(location)
            ),
            Axis=self.model.create_entity(
                "IfcDirection",
                DirectionRatios=list(axis)
            ),
            RefDirection=self.model.create_entity(
                "IfcDirection",
                DirectionRatios=list(ref_direction)
            )
        )

    def _assign_representation(self, element: Any, solid: Any) -> None:
        """Assign geometric representation to element"""
        shape_representation = self.model.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=self.body_context,
            RepresentationIdentifier="Body",
            RepresentationType="SweptSolid",
            Items=[solid]
        )

        product_shape = self.model.create_entity(
            "IfcProductDefinitionShape",
            Representations=[shape_representation]
        )

        element.Representation = product_shape

    def _add_material(self, element: Any, material: Material) -> None:
        """Add material to element"""
        ifc_material = ifcopenshell.api.run(
            "material.add_material",
            self.model,
            name=material.name,
            category=material.category
        )

        ifcopenshell.api.run(
            "material.assign_material",
            self.model,
            product=element,
            material=ifc_material
        )

    def _add_property_set(
        self,
        element: Any,
        name: str,
        properties: Dict[str, Any]
    ) -> None:
        """Add property set to element"""
        pset = ifcopenshell.api.run(
            "pset.add_pset",
            self.model,
            product=element,
            name=name
        )

        ifcopenshell.api.run(
            "pset.edit_pset",
            self.model,
            pset=pset,
            properties=properties
        )

    def save(self, filepath: str) -> None:
        """Save IFC model to file"""
        if self.model:
            self.model.write(filepath)


class IFCImporter:
    """
    Imports IFC files to BIM components.
    """

    def __init__(self):
        if not HAS_IFC:
            raise ImportError("ifcopenshell is required for IFC import")

        self.model = None
        self.components: List[BIMComponent] = []

    def load(self, filepath: str) -> List[BIMComponent]:
        """Load IFC file and convert to BIM components"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"IFC file not found: {filepath}")

        self.model = ifcopenshell.open(filepath)
        self.components = []

        # Import walls
        for wall in self.model.by_type("IfcWall"):
            component = self._import_wall(wall)
            if component:
                self.components.append(component)

        # Import slabs
        for slab in self.model.by_type("IfcSlab"):
            component = self._import_slab(slab)
            if component:
                self.components.append(component)

        # Import columns
        for column in self.model.by_type("IfcColumn"):
            component = self._import_column(column)
            if component:
                self.components.append(component)

        # Import beams
        for beam in self.model.by_type("IfcBeam"):
            component = self._import_beam(beam)
            if component:
                self.components.append(component)

        return self.components

    def _import_wall(self, ifc_wall: Any) -> Optional[BIMWall]:
        """Import IfcWall to BIMWall"""
        try:
            # Get placement
            placement = ifcopenshell.util.placement.get_local_placement(
                ifc_wall.ObjectPlacement
            )

            # Get geometry bounds
            settings = ifcopenshell.geom.settings()
            shape = ifcopenshell.geom.create_shape(settings, ifc_wall)
            verts = shape.geometry.verts

            if len(verts) < 6:
                return None

            # Extract bounds
            xs = verts[0::3]
            ys = verts[1::3]
            zs = verts[2::3]

            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            min_z, max_z = min(zs), max(zs)

            # Create wall (simplified - assumes axis-aligned)
            wall = BIMWall(
                start=(min_x, min_y),
                end=(max_x, min_y),
                height=max_z - min_z,
                thickness=max_y - min_y,
                name=ifc_wall.Name or "Imported Wall"
            )
            wall.base_height = min_z

            return wall

        except Exception:
            return None

    def _import_slab(self, ifc_slab: Any) -> Optional[BIMSlab]:
        """Import IfcSlab to BIMSlab"""
        try:
            settings = ifcopenshell.geom.settings()
            shape = ifcopenshell.geom.create_shape(settings, ifc_slab)
            verts = shape.geometry.verts

            if len(verts) < 6:
                return None

            xs = verts[0::3]
            ys = verts[1::3]
            zs = verts[2::3]

            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            min_z, max_z = min(zs), max(zs)

            outline = [
                (min_x, min_y),
                (max_x, min_y),
                (max_x, max_y),
                (min_x, max_y),
            ]

            slab = BIMSlab(
                outline=outline,
                thickness=max_z - min_z,
                elevation=min_z,
                name=ifc_slab.Name or "Imported Slab"
            )

            return slab

        except Exception:
            return None

    def _import_column(self, ifc_column: Any) -> Optional[BIMColumn]:
        """Import IfcColumn to BIMColumn"""
        try:
            settings = ifcopenshell.geom.settings()
            shape = ifcopenshell.geom.create_shape(settings, ifc_column)
            verts = shape.geometry.verts

            if len(verts) < 6:
                return None

            xs = verts[0::3]
            ys = verts[1::3]
            zs = verts[2::3]

            center_x = (min(xs) + max(xs)) / 2
            center_y = (min(ys) + max(ys)) / 2
            min_z, max_z = min(zs), max(zs)

            column = BIMColumn(
                position=(center_x, center_y),
                width=max(xs) - min(xs),
                depth=max(ys) - min(ys),
                height=max_z - min_z,
                base_elevation=min_z,
                name=ifc_column.Name or "Imported Column"
            )

            return column

        except Exception:
            return None

    def _import_beam(self, ifc_beam: Any) -> Optional[BIMBeam]:
        """Import IfcBeam to BIMBeam"""
        try:
            settings = ifcopenshell.geom.settings()
            shape = ifcopenshell.geom.create_shape(settings, ifc_beam)
            verts = shape.geometry.verts

            if len(verts) < 6:
                return None

            xs = verts[0::3]
            ys = verts[1::3]
            zs = verts[2::3]

            # Simplified - assumes horizontal beam
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            z = (min(zs) + max(zs)) / 2

            beam = BIMBeam(
                start=(min_x, (min_y + max_y)/2, z),
                end=(max_x, (min_y + max_y)/2, z),
                width=max_y - min_y,
                height=max(zs) - min(zs),
                name=ifc_beam.Name or "Imported Beam"
            )

            return beam

        except Exception:
            return None


# Convenience functions
def export_to_ifc(
    components: List[BIMComponent],
    filepath: str,
    project_name: str = "Muratura Project",
    author: str = "Muratura CAD"
) -> None:
    """
    Export BIM components to IFC file.

    Args:
        components: List of BIM components to export
        filepath: Output IFC file path
        project_name: Name for the IFC project
        author: Author name for metadata
    """
    if not HAS_IFC:
        raise ImportError(
            "ifcopenshell is required for IFC export. "
            "Install with: pip install ifcopenshell"
        )

    exporter = IFCExporter(project_name)
    exporter.create_model(author)

    for component in components:
        exporter.export_component(component)

    exporter.save(filepath)


def import_from_ifc(filepath: str) -> List[BIMComponent]:
    """
    Import BIM components from IFC file.

    Args:
        filepath: Input IFC file path

    Returns:
        List of imported BIM components
    """
    if not HAS_IFC:
        raise ImportError(
            "ifcopenshell is required for IFC import. "
            "Install with: pip install ifcopenshell"
        )

    importer = IFCImporter()
    return importer.load(filepath)
