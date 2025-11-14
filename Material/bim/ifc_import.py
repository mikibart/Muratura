"""
Module: ifc_import.py
IFC Import for Muratura FEM - Building Information Modeling Integration

Questo modulo implementa l'import di modelli IFC (Industry Foundation Classes)
da software BIM come Revit, ArchiCAD, Tekla, etc. per analisi strutturale.

Standard supportati:
- IFC 2x3 (ISO 16739:2013) - Standard più diffuso
- IFC 4 (ISO 16739-1:2018) - Standard recente con supporto analisi strutturale

Funzionalità principali:
- Estrazione geometria (pareti, solai, archi, volte)
- Material mapping IFC → Muratura materials
- Conversione unità (mm, ft → m)
- Coordinate transformations
- Estrazione IfcStructuralAnalysisModel

References:
- buildingSMART: https://www.buildingsmart.org/
- IfcOpenShell: http://ifcopenshell.org/
- ISO 16739-1:2018: IFC 4 specification

Author: Claude (Anthropic)
Created: 2025-11-14
Status: Development
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import numpy as np

try:
    import ifcopenshell
    import ifcopenshell.geom
except ImportError:
    raise ImportError(
        "IfcOpenShell is required for BIM/IFC import. "
        "Install it with: pip install ifcopenshell"
    )


@dataclass
class IFCImportSettings:
    """
    Impostazioni per import modelli IFC

    Attributes:
        ifc_version: Versione IFC attesa ('2x3' o '4')
        unit_scale: Unità di misura target ('meter', 'millimeter', 'foot')
        extract_materials: Se True, estrae materiali da IFC
        extract_loads: Se True, estrae carichi da IfcStructuralAnalysisModel
        simplify_geometry: Se True, semplifica geometrie complesse
        tolerance: Tolleranza geometrica in metri
        include_furniture: Se True, include elementi non strutturali
        verbose: Se True, stampa log dettagliati
    """
    ifc_version: str = '2x3'
    unit_scale: str = 'meter'
    extract_materials: bool = True
    extract_loads: bool = True
    simplify_geometry: bool = True
    tolerance: float = 0.001  # m
    include_furniture: bool = False
    verbose: bool = False


class IFCImporter:
    """
    Importatore modelli IFC per analisi strutturale in muratura

    Questa classe permette di importare modelli BIM da software come Revit,
    ArchiCAD, Tekla e convertirli in un formato utilizzabile da Muratura FEM.

    Example:
        >>> from Material.bim import IFCImporter, IFCImportSettings
        >>> settings = IFCImportSettings(verbose=True)
        >>> importer = IFCImporter('model.ifc', settings)
        >>> walls = importer.extract_walls()
        >>> slabs = importer.extract_slabs()
        >>> materials = importer.extract_materials()
        >>> print(f"Imported {len(walls)} walls, {len(slabs)} slabs")

    Attributes:
        ifc_file: File IFC aperto con ifcopenshell
        file_path: Path al file IFC
        settings: Impostazioni import
        walls: Lista pareti estratte
        slabs: Lista solai estratti
        materials: Dizionario materiali {nome: proprietà}
        project_info: Informazioni progetto IFC
    """

    def __init__(self,
                 ifc_file_path: str,
                 settings: Optional[IFCImportSettings] = None):
        """
        Inizializza importatore IFC

        Args:
            ifc_file_path: Path al file IFC da importare
            settings: Impostazioni import (default: IFCImportSettings())

        Raises:
            FileNotFoundError: Se file IFC non esiste
            RuntimeError: Se file IFC è corrotto o non valido
        """
        self.file_path = Path(ifc_file_path)

        if not self.file_path.exists():
            raise FileNotFoundError(f"IFC file not found: {ifc_file_path}")

        self.settings = settings or IFCImportSettings()

        # Apri file IFC
        try:
            self.ifc_file = ifcopenshell.open(str(self.file_path))
        except Exception as e:
            raise RuntimeError(f"Failed to open IFC file: {e}")

        # Verifica versione IFC
        self._verify_ifc_version()

        # Inizializza storage dati estratti
        self.walls: List[Dict[str, Any]] = []
        self.slabs: List[Dict[str, Any]] = []
        self.columns: List[Dict[str, Any]] = []
        self.beams: List[Dict[str, Any]] = []
        self.materials: Dict[str, Any] = {}
        self.project_info: Dict[str, str] = {}

        # Estrai informazioni progetto
        self._extract_project_info()

        if self.settings.verbose:
            print(f"✅ IFC file loaded: {self.file_path.name}")
            print(f"   Schema: {self.ifc_file.schema}")
            print(f"   Project: {self.project_info.get('name', 'N/A')}")

    def _verify_ifc_version(self):
        """Verifica versione schema IFC"""
        schema = self.ifc_file.schema

        if 'IFC2X3' in schema:
            actual_version = '2x3'
        elif 'IFC4' in schema:
            actual_version = '4'
        else:
            actual_version = 'unknown'

        if self.settings.verbose:
            if actual_version != self.settings.ifc_version:
                print(f"⚠️  Warning: Expected IFC {self.settings.ifc_version}, "
                      f"found IFC {actual_version}")

    def _extract_project_info(self):
        """Estrae informazioni progetto da IFC"""
        projects = self.ifc_file.by_type('IfcProject')

        if projects:
            project = projects[0]
            self.project_info = {
                'name': project.Name or 'Unnamed Project',
                'description': project.Description or '',
                'phase': project.Phase or '',
            }

            # Estrai site information
            sites = self.ifc_file.by_type('IfcSite')
            if sites:
                site = sites[0]
                self.project_info['site_name'] = site.Name or ''
                self.project_info['site_address'] = str(site.SiteAddress) if hasattr(site, 'SiteAddress') else ''

    def extract_walls(self) -> List[Dict[str, Any]]:
        """
        Estrae pareti murarie da modello IFC

        Supporta:
        - IfcWall
        - IfcWallStandardCase

        Returns:
            Lista dizionari con dati pareti:
            - guid: GlobalId IFC
            - name: Nome parete
            - geometry: Geometria 3D (vertices, triangles, matrix)
            - material: Nome materiale
            - thickness: Spessore [m]
            - height: Altezza [m]
            - length: Lunghezza [m]
            - area: Area [m²]
            - is_loadbearing: Se è portante (da IfcProperty)
        """
        if self.settings.verbose:
            print("🔍 Extracting walls...")

        walls = self.ifc_file.by_type('IfcWall') + self.ifc_file.by_type('IfcWallStandardCase')

        for wall in walls:
            try:
                wall_data = {
                    'guid': wall.GlobalId,
                    'name': wall.Name or f'Wall_{wall.GlobalId[:8]}',
                    'description': wall.Description or '',
                    'object_type': wall.ObjectType or '',
                }

                # Estrai geometria
                geometry = self._extract_geometry(wall)
                if geometry:
                    wall_data['geometry'] = geometry

                # Estrai materiale
                material_name = self._extract_material(wall)
                if material_name:
                    wall_data['material'] = material_name

                # Estrai dimensioni
                thickness = self._get_wall_thickness(wall)
                height = self._get_wall_height(wall)
                length = self._get_wall_length(wall)

                wall_data['thickness'] = thickness
                wall_data['height'] = height
                wall_data['length'] = length
                wall_data['area'] = height * length if height and length else None

                # Estrai proprietà custom
                is_loadbearing = self._get_property_value(wall, 'IsLoadBearing')
                wall_data['is_loadbearing'] = is_loadbearing if is_loadbearing is not None else True  # Default: portante

                self.walls.append(wall_data)

            except Exception as e:
                if self.settings.verbose:
                    print(f"⚠️  Warning: Failed to extract wall {wall.GlobalId}: {e}")
                continue

        if self.settings.verbose:
            print(f"✅ Extracted {len(self.walls)} walls")

        return self.walls

    def extract_slabs(self) -> List[Dict[str, Any]]:
        """
        Estrae solai da modello IFC

        Supporta:
        - IfcSlab (FLOOR, ROOF, LANDING)

        Returns:
            Lista dizionari con dati solai:
            - guid: GlobalId IFC
            - name: Nome solaio
            - geometry: Geometria 3D
            - material: Nome materiale
            - thickness: Spessore [m]
            - area: Area [m²]
            - predefined_type: FLOOR, ROOF, LANDING, etc.
            - elevation: Quota [m]
        """
        if self.settings.verbose:
            print("🔍 Extracting slabs...")

        slabs = self.ifc_file.by_type('IfcSlab')

        for slab in slabs:
            try:
                slab_data = {
                    'guid': slab.GlobalId,
                    'name': slab.Name or f'Slab_{slab.GlobalId[:8]}',
                    'description': slab.Description or '',
                    'predefined_type': slab.PredefinedType if hasattr(slab, 'PredefinedType') else 'NOTDEFINED',
                }

                # Estrai geometria
                geometry = self._extract_geometry(slab)
                if geometry:
                    slab_data['geometry'] = geometry

                # Estrai materiale
                material_name = self._extract_material(slab)
                if material_name:
                    slab_data['material'] = material_name

                # Estrai dimensioni
                thickness = self._get_slab_thickness(slab)
                area = self._get_slab_area(slab)
                elevation = self._get_elevation(slab)

                slab_data['thickness'] = thickness
                slab_data['area'] = area
                slab_data['elevation'] = elevation

                self.slabs.append(slab_data)

            except Exception as e:
                if self.settings.verbose:
                    print(f"⚠️  Warning: Failed to extract slab {slab.GlobalId}: {e}")
                continue

        if self.settings.verbose:
            print(f"✅ Extracted {len(self.slabs)} slabs")

        return self.slabs

    def extract_materials(self) -> Dict[str, Any]:
        """
        Estrae materiali da IFC e tenta mapping a classi Muratura

        Estrae:
        - IfcMaterial
        - IfcMaterialLayerSet (per pareti multistrato)
        - Proprietà meccaniche (se presenti in IfcPropertySet)

        Returns:
            Dizionario {nome_materiale: proprietà}
            Proprietà possono includere:
            - type: 'masonry', 'concrete', 'steel', 'wood', 'unknown'
            - density: Densità [kg/m³]
            - compressive_strength: Resistenza compressione [MPa]
            - youngs_modulus: Modulo elastico [MPa]
            - poisson_ratio: Coefficiente di Poisson
        """
        if self.settings.verbose:
            print("🔍 Extracting materials...")

        ifc_materials = self.ifc_file.by_type('IfcMaterial')

        for mat in ifc_materials:
            try:
                mat_name = mat.Name

                # Inizializza proprietà materiale
                mat_properties = {
                    'name': mat_name,
                    'description': mat.Description if hasattr(mat, 'Description') else '',
                    'category': mat.Category if hasattr(mat, 'Category') else '',
                    'type': 'unknown',
                }

                # Estrai proprietà meccaniche se presenti
                mechanical_props = self._extract_material_properties(mat)
                if mechanical_props:
                    mat_properties.update(mechanical_props)

                # Auto-detect tipo materiale
                material_type = self._detect_material_type(mat_name, mat_properties)
                mat_properties['type'] = material_type

                self.materials[mat_name] = mat_properties

            except Exception as e:
                if self.settings.verbose:
                    print(f"⚠️  Warning: Failed to extract material {mat.Name}: {e}")
                continue

        if self.settings.verbose:
            print(f"✅ Extracted {len(self.materials)} materials")
            # Conta per tipo
            type_counts = {}
            for mat in self.materials.values():
                mat_type = mat.get('type', 'unknown')
                type_counts[mat_type] = type_counts.get(mat_type, 0) + 1
            for mat_type, count in type_counts.items():
                print(f"   - {mat_type}: {count}")

        return self.materials

    def _extract_geometry(self, element) -> Optional[Dict[str, Any]]:
        """
        Estrae geometria 3D da elemento IFC

        Converte rappresentazione IFC (BREP, sweep, extrusion) in mesh triangolare.

        Args:
            element: Elemento IFC (IfcWall, IfcSlab, etc.)

        Returns:
            Dizionario con:
            - vertices: Array Nx3 coordinate vertici [m]
            - triangles: Array Mx3 indici triangoli
            - matrix: Matrice trasformazione 4x4
            - bounding_box: (min_xyz, max_xyz)
        """
        try:
            # Configura settings IfcOpenShell geometry
            settings = ifcopenshell.geom.settings()
            settings.set(settings.USE_WORLD_COORDS, True)  # Coordinate globali
            settings.set(settings.DISABLE_OPENING_SUBTRACTIONS, False)  # Sottrai aperture (porte, finestre)

            # Crea shape geometry
            shape = ifcopenshell.geom.create_shape(settings, element)

            # Estrai mesh
            verts = shape.geometry.verts  # [x1,y1,z1, x2,y2,z2, ...]
            faces = shape.geometry.faces  # [i1,i2,i3, i4,i5,i6, ...]

            # Converti a numpy arrays
            vertices = np.array(verts).reshape(-1, 3)
            triangles = np.array(faces).reshape(-1, 3)

            # Converti unità se necessario
            vertices = self._convert_vertices_to_meters(vertices)

            # Matrice trasformazione
            matrix = np.array(shape.transformation.matrix.data).reshape(4, 4)

            # Bounding box
            bbox_min = vertices.min(axis=0)
            bbox_max = vertices.max(axis=0)

            return {
                'vertices': vertices,
                'triangles': triangles,
                'matrix': matrix,
                'bounding_box': (bbox_min, bbox_max),
                'volume': self._calculate_mesh_volume(vertices, triangles),
            }

        except Exception as e:
            if self.settings.verbose:
                print(f"⚠️  Geometry extraction failed: {e}")
            return None

    def _convert_vertices_to_meters(self, vertices: np.ndarray) -> np.ndarray:
        """Converte vertici a metri basandosi su unità progetto IFC"""
        scale_factor = self._get_unit_scale_factor()
        return vertices * scale_factor

    def _get_unit_scale_factor(self) -> float:
        """
        Determina fattore conversione unità IFC → metri

        Returns:
            Fattore moltiplicativo per convertire a metri
        """
        try:
            unit_assignments = self.ifc_file.by_type('IfcUnitAssignment')

            if not unit_assignments:
                if self.settings.verbose:
                    print("⚠️  No IfcUnitAssignment found, assuming meters")
                return 1.0

            units = unit_assignments[0].Units

            for unit in units:
                if hasattr(unit, 'UnitType') and unit.UnitType == 'LENGTHUNIT':
                    if hasattr(unit, 'Name'):
                        unit_name = unit.Name.upper()

                        # Conversioni standard
                        conversions = {
                            'METRE': 1.0,
                            'METER': 1.0,
                            'MILLIMETRE': 0.001,
                            'MILLIMETER': 0.001,
                            'FOOT': 0.3048,
                            'INCH': 0.0254,
                            'CENTIMETRE': 0.01,
                            'CENTIMETER': 0.01,
                        }

                        if unit_name in conversions:
                            factor = conversions[unit_name]

                            # Considera prefix (KILO, MILLI, etc.)
                            if hasattr(unit, 'Prefix'):
                                prefix = unit.Prefix.upper() if unit.Prefix else ''
                                prefix_factors = {
                                    'KILO': 1000.0,
                                    'HECTO': 100.0,
                                    'DECA': 10.0,
                                    'DECI': 0.1,
                                    'CENTI': 0.01,
                                    'MILLI': 0.001,
                                }
                                if prefix in prefix_factors:
                                    factor *= prefix_factors[prefix]

                            return factor

        except Exception as e:
            if self.settings.verbose:
                print(f"⚠️  Unit detection failed: {e}, assuming meters")

        return 1.0  # Default: metri

    def _extract_material(self, element) -> Optional[str]:
        """
        Estrae nome materiale da elemento IFC

        Args:
            element: Elemento IFC

        Returns:
            Nome materiale o None
        """
        try:
            if not hasattr(element, 'HasAssociations'):
                return None

            for association in element.HasAssociations:
                if association.is_a('IfcRelAssociatesMaterial'):
                    material_select = association.RelatingMaterial

                    # IfcMaterial singolo
                    if material_select.is_a('IfcMaterial'):
                        return material_select.Name

                    # IfcMaterialLayerSetUsage (parete multistrato)
                    elif material_select.is_a('IfcMaterialLayerSetUsage'):
                        layer_set = material_select.ForLayerSet
                        if layer_set.MaterialLayers:
                            # Usa layer principale (più spesso)
                            thickest_layer = max(
                                layer_set.MaterialLayers,
                                key=lambda l: l.LayerThickness
                            )
                            return thickest_layer.Material.Name

                    # IfcMaterialList
                    elif material_select.is_a('IfcMaterialList'):
                        if material_select.Materials:
                            return material_select.Materials[0].Name

        except Exception as e:
            if self.settings.verbose:
                print(f"⚠️  Material extraction failed: {e}")

        return None

    def _get_wall_thickness(self, wall) -> Optional[float]:
        """Calcola spessore parete [m]"""
        try:
            # Try from MaterialLayerSet first
            if hasattr(wall, 'HasAssociations'):
                for assoc in wall.HasAssociations:
                    if assoc.is_a('IfcRelAssociatesMaterial'):
                        mat = assoc.RelatingMaterial
                        if mat.is_a('IfcMaterialLayerSetUsage'):
                            total_thickness = sum(
                                layer.LayerThickness
                                for layer in mat.ForLayerSet.MaterialLayers
                            )
                            return total_thickness * self._get_unit_scale_factor()

            # Fallback: da geometria (dimensione minima bounding box)
            geometry = self._extract_geometry(wall)
            if geometry:
                bbox_min, bbox_max = geometry['bounding_box']
                dims = bbox_max - bbox_min
                return float(np.min(dims))

        except Exception:
            pass

        return None

    def _get_wall_height(self, wall) -> Optional[float]:
        """Calcola altezza parete [m]"""
        try:
            geometry = self._extract_geometry(wall)
            if geometry:
                bbox_min, bbox_max = geometry['bounding_box']
                dims = bbox_max - bbox_min
                # Altezza è tipicamente la dimensione Z
                return float(dims[2])
        except Exception:
            pass

        return None

    def _get_wall_length(self, wall) -> Optional[float]:
        """Calcola lunghezza parete [m]"""
        try:
            geometry = self._extract_geometry(wall)
            if geometry:
                bbox_min, bbox_max = geometry['bounding_box']
                dims = bbox_max - bbox_min
                # Lunghezza è la dimensione orizzontale maggiore
                horizontal_dims = dims[:2]  # X, Y
                return float(np.max(horizontal_dims))
        except Exception:
            pass

        return None

    def _get_slab_thickness(self, slab) -> Optional[float]:
        """Calcola spessore solaio [m]"""
        # Same logic as wall thickness
        return self._get_wall_thickness(slab)

    def _get_slab_area(self, slab) -> Optional[float]:
        """Calcola area solaio [m²]"""
        try:
            geometry = self._extract_geometry(slab)
            if geometry:
                vertices = geometry['vertices']
                triangles = geometry['triangles']

                # Calcola area sommando aree triangoli proiezione XY
                total_area = 0.0
                for tri in triangles:
                    v0, v1, v2 = vertices[tri]
                    # Area triangolo in XY
                    edge1 = v1[:2] - v0[:2]
                    edge2 = v2[:2] - v0[:2]
                    area = 0.5 * abs(np.cross(edge1, edge2))
                    total_area += area

                return total_area

        except Exception:
            pass

        return None

    def _get_elevation(self, element) -> Optional[float]:
        """Ottiene quota elemento [m]"""
        try:
            geometry = self._extract_geometry(element)
            if geometry:
                bbox_min, _ = geometry['bounding_box']
                return float(bbox_min[2])  # Z minima
        except Exception:
            pass

        return None

    def _get_property_value(self, element, property_name: str) -> Any:
        """
        Estrae valore proprietà custom da IfcPropertySet

        Args:
            element: Elemento IFC
            property_name: Nome proprietà da cercare

        Returns:
            Valore proprietà o None
        """
        try:
            if not hasattr(element, 'IsDefinedBy'):
                return None

            for definition in element.IsDefinedBy:
                if definition.is_a('IfcRelDefinesByProperties'):
                    property_set = definition.RelatingPropertyDefinition

                    if property_set.is_a('IfcPropertySet'):
                        for prop in property_set.HasProperties:
                            if prop.Name == property_name:
                                if hasattr(prop, 'NominalValue'):
                                    return prop.NominalValue.wrappedValue
        except Exception:
            pass

        return None

    def _extract_material_properties(self, material) -> Dict[str, Any]:
        """Estrae proprietà meccaniche materiale se presenti"""
        props = {}

        try:
            # Cerca IfcMaterialProperties
            if hasattr(material, 'HasProperties'):
                for prop_rel in material.HasProperties:
                    if prop_rel.is_a('IfcMaterialProperties'):
                        for prop in prop_rel.Properties:
                            name = prop.Name.lower()
                            value = prop.NominalValue.wrappedValue if hasattr(prop, 'NominalValue') else None

                            if value is not None:
                                # Mappa proprietà standard
                                if 'density' in name:
                                    props['density'] = float(value)
                                elif 'compressive' in name and 'strength' in name:
                                    props['compressive_strength'] = float(value)
                                elif 'young' in name or 'elastic' in name:
                                    props['youngs_modulus'] = float(value)
                                elif 'poisson' in name:
                                    props['poisson_ratio'] = float(value)

        except Exception:
            pass

        return props

    def _detect_material_type(self, name: str, properties: Dict) -> str:
        """
        Auto-detect tipo materiale da nome e proprietà

        Returns:
            'masonry', 'concrete', 'steel', 'wood', 'unknown'
        """
        name_lower = name.lower()

        # Keyword matching
        if any(kw in name_lower for kw in ['brick', 'mattone', 'muratura', 'masonry', 'stone', 'pietra']):
            return 'masonry'
        elif any(kw in name_lower for kw in ['concrete', 'calcestruzzo', 'cls', 'beton']):
            return 'concrete'
        elif any(kw in name_lower for kw in ['steel', 'acciaio', 'iron', 'ferro']):
            return 'steel'
        elif any(kw in name_lower for kw in ['wood', 'legno', 'timber']):
            return 'wood'

        # Density-based heuristic
        density = properties.get('density')
        if density:
            if 1500 < density < 2200:
                return 'masonry'
            elif 2200 < density < 2600:
                return 'concrete'
            elif density > 7000:
                return 'steel'
            elif density < 1000:
                return 'wood'

        return 'unknown'

    def _calculate_mesh_volume(self, vertices: np.ndarray, triangles: np.ndarray) -> float:
        """
        Calcola volume mesh chiusa (metodo signed volume)

        Args:
            vertices: Array Nx3 vertici
            triangles: Array Mx3 triangoli

        Returns:
            Volume [m³]
        """
        try:
            volume = 0.0

            for tri in triangles:
                v0, v1, v2 = vertices[tri]
                # Signed volume tetrahedron origin-v0-v1-v2
                volume += np.dot(v0, np.cross(v1, v2)) / 6.0

            return abs(volume)

        except Exception:
            return 0.0

    def extract_structural_analysis_model(self) -> Optional[Dict[str, Any]]:
        """
        Estrae IfcStructuralAnalysisModel se presente

        Questo è presente solo in modelli IFC structural (da software analisi)
        o in IFC 4 con dati analisi.

        Returns:
            Dizionario con:
            - name: Nome modello
            - loads: Lista carichi
            - load_groups: Gruppi carichi (permanenti, variabili, etc.)
            - connections: Connessioni/nodi
        """
        models = self.ifc_file.by_type('IfcStructuralAnalysisModel')

        if not models:
            if self.settings.verbose:
                print("ℹ️  No IfcStructuralAnalysisModel found")
            return None

        model = models[0]

        if self.settings.verbose:
            print(f"🔍 Extracting structural analysis model: {model.Name}")

        return {
            'name': model.Name or 'Structural Model',
            'description': model.Description or '',
            'loads': [],  # TODO: Implementare estrazione carichi
            'load_groups': [],  # TODO: Implementare estrazione gruppi carichi
            'connections': [],  # TODO: Implementare estrazione connessioni
        }

    def get_summary(self) -> Dict[str, Any]:
        """
        Ottiene riassunto modello importato

        Returns:
            Dizionario con statistiche import
        """
        return {
            'file': self.file_path.name,
            'schema': self.ifc_file.schema,
            'project': self.project_info,
            'counts': {
                'walls': len(self.walls),
                'slabs': len(self.slabs),
                'materials': len(self.materials),
            },
            'materials_by_type': self._count_materials_by_type(),
        }

    def _count_materials_by_type(self) -> Dict[str, int]:
        """Conta materiali per tipo"""
        counts = {}
        for mat in self.materials.values():
            mat_type = mat.get('type', 'unknown')
            counts[mat_type] = counts.get(mat_type, 0) + 1
        return counts

    def __repr__(self) -> str:
        return (f"IFCImporter(file='{self.file_path.name}', "
                f"walls={len(self.walls)}, slabs={len(self.slabs)}, "
                f"materials={len(self.materials)})")
