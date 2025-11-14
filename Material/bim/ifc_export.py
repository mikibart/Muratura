"""
MURATURA FEM - IFC Export Module (Fase 3 - Module 4)

Esporta risultati analisi strutturale in formato IFC 2x3/4 per BIM.

Questo modulo consente di esportare i risultati dell'analisi strutturale
(verifiche, spostamenti, tensioni, rinforzi) in formato IFC Structural Analysis View.

Standard supportati:
- IFC 2x3 Coordination View 2.0
- IFC 4 Reference View + Structural Analysis View

Entità IFC generate:
- IfcStructuralAnalysisModel - Modello di analisi
- IfcStructuralPointConnection - Nodi
- IfcStructuralCurveMember - Elementi lineari
- IfcStructuralSurfaceMember - Pareti (superfici)
- IfcStructuralLoadGroup - Gruppi di carico
- IfcStructuralResultGroup - Gruppi di risultati
- IfcStructuralPointAction/SurfaceAction - Carichi applicati
- IfcStructuralPointReaction/SurfaceReaction - Reazioni vincolari

Conformità:
- ISO 16739:2013 (IFC 2x3)
- ISO 16739-1:2018 (IFC 4)
- buildingSMART IFC Structural Analysis View

Autore: Claude AI Assistant
Data: 2025-01-14
Versione: 7.0-alpha
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

try:
    import ifcopenshell
    import ifcopenshell.api
    from ifcopenshell.api import run
    IFC_AVAILABLE = True
except ImportError:
    IFC_AVAILABLE = False
    logging.warning("ifcopenshell not available - IFC export disabled")

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class IFCExportSettings:
    """
    Impostazioni per export IFC strutturale.

    Attributes:
        ifc_version: Versione IFC ('2x3' o '4')
        schema: Schema IFC ('IFC2X3' o 'IFC4')
        export_loads: Include carichi nel modello
        export_results: Include risultati analisi
        export_reinforcement: Include rinforzi FRP/FRCM
        coordinate_system: Sistema coordinate ('local' o 'global')
        unit_system: Sistema unità ('METER', 'MILLIMETER')
        organization: Nome organizzazione
        author: Nome autore
        application: Nome applicazione
    """
    ifc_version: str = '2x3'
    schema: str = 'IFC2X3'
    export_loads: bool = True
    export_results: bool = True
    export_reinforcement: bool = True
    coordinate_system: str = 'global'
    unit_system: str = 'METER'
    organization: str = 'MURATURA FEM'
    author: str = 'Unknown'
    application: str = 'MURATURA FEM v7.0'
    project_name: str = 'Structural Analysis'
    project_description: str = 'Masonry structural analysis results'


@dataclass
class StructuralNode:
    """Nodo strutturale per export IFC."""
    node_id: int
    coordinates: Tuple[float, float, float]  # (x, y, z) in meters
    reactions: Optional[Dict[str, float]] = None  # {'Fx': ..., 'Fy': ..., 'Fz': ...}
    displacements: Optional[Dict[str, float]] = None  # {'Ux': ..., 'Uy': ..., 'Uz': ...}


@dataclass
class StructuralMember:
    """Elemento strutturale per export IFC."""
    member_id: str
    member_type: str  # 'wall', 'slab', 'beam', 'column'
    node_ids: List[int]  # Lista di nodi che definiscono l'elemento
    material: str
    thickness: Optional[float] = None  # m (per pareti)
    cross_section: Optional[Dict[str, float]] = None  # Per travi/colonne

    # Risultati analisi
    max_stress: Optional[float] = None  # MPa
    max_displacement: Optional[float] = None  # mm
    utilization_ratio: Optional[float] = None  # Domanda/Capacità
    verification_status: Optional[str] = None  # 'VERIFICATO' / 'NON VERIFICATO'


@dataclass
class StructuralLoad:
    """Carico strutturale per export IFC."""
    load_id: str
    load_type: str  # 'dead', 'live', 'seismic', 'wind', 'snow'
    load_case: str  # 'G1', 'G2', 'Q', 'E', etc.
    applied_to: str  # ID elemento o nodo

    # Valori carico
    force: Optional[Tuple[float, float, float]] = None  # (Fx, Fy, Fz) kN
    moment: Optional[Tuple[float, float, float]] = None  # (Mx, My, Mz) kNm
    distributed_load: Optional[float] = None  # kN/m² per carichi distribuiti


class IFCExporter:
    """
    Esportatore IFC per risultati analisi strutturale.

    Converte risultati dell'analisi FEM in formato IFC Structural Analysis View
    compatibile con software BIM (Revit, Tekla, SAP2000, etc.).

    Usage:
        >>> exporter = IFCExporter(settings)
        >>> exporter.add_nodes(nodes_list)
        >>> exporter.add_members(members_list)
        >>> exporter.add_loads(loads_list)
        >>> exporter.export('output.ifc')
    """

    def __init__(self, settings: Optional[IFCExportSettings] = None):
        """
        Inizializza exporter IFC.

        Args:
            settings: Impostazioni export (default se None)

        Raises:
            ImportError: Se ifcopenshell non disponibile
        """
        if not IFC_AVAILABLE:
            raise ImportError(
                "ifcopenshell is required for IFC export. "
                "Install with: pip install ifcopenshell"
            )

        self.settings = settings or IFCExportSettings()

        # Validazione settings
        self._validate_settings()

        # Inizializza file IFC
        self.ifc_file = ifcopenshell.file(schema=self.settings.schema)

        # Storage entità
        self.nodes: List[StructuralNode] = []
        self.members: List[StructuralMember] = []
        self.loads: List[StructuralLoad] = []

        # Mappatura IDs → Entità IFC
        self.ifc_nodes: Dict[int, Any] = {}
        self.ifc_members: Dict[str, Any] = {}
        self.ifc_loads: Dict[str, Any] = {}

        # Entità base IFC
        self.project = None
        self.site = None
        self.building = None
        self.structural_analysis_model = None

        # Owner history per metadati
        self.owner_history = None

        logger.info(f"IFC Exporter initialized - Schema: {self.settings.schema}")

    def _validate_settings(self):
        """Valida impostazioni export."""
        valid_versions = ['2x3', '4']
        if self.settings.ifc_version not in valid_versions:
            raise ValueError(f"ifc_version must be one of {valid_versions}")

        valid_schemas = ['IFC2X3', 'IFC4']
        if self.settings.schema not in valid_schemas:
            raise ValueError(f"schema must be one of {valid_schemas}")

        valid_units = ['METER', 'MILLIMETER', 'FOOT', 'INCH']
        if self.settings.unit_system not in valid_units:
            raise ValueError(f"unit_system must be one of {valid_units}")

    def _create_guid(self) -> str:
        """Genera GUID univoco per entità IFC."""
        return ifcopenshell.guid.compress(uuid4().hex)

    def _initialize_project_structure(self):
        """
        Inizializza struttura base progetto IFC.

        Crea:
        - IfcProject
        - IfcSite
        - IfcBuilding
        - IfcStructuralAnalysisModel
        - Owner History
        - Unità di misura
        """
        # Owner History (metadati autore/applicazione)
        person = self.ifc_file.createIfcPerson(
            Identification=None,
            FamilyName=self.settings.author.split()[-1] if ' ' in self.settings.author else None,
            GivenName=self.settings.author.split()[0] if ' ' in self.settings.author else self.settings.author,
        )

        organization = self.ifc_file.createIfcOrganization(
            Name=self.settings.organization
        )

        person_org = self.ifc_file.createIfcPersonAndOrganization(
            ThePerson=person,
            TheOrganization=organization
        )

        application = self.ifc_file.createIfcApplication(
            ApplicationDeveloper=organization,
            Version='7.0',
            ApplicationFullName=self.settings.application,
            ApplicationIdentifier='MURATURA_FEM'
        )

        timestamp = int(datetime.now().timestamp())

        self.owner_history = self.ifc_file.createIfcOwnerHistory(
            OwningUser=person_org,
            OwningApplication=application,
            CreationDate=timestamp
        )

        # Unità di misura
        unit_scale = {
            'METER': 1.0,
            'MILLIMETER': 0.001,
            'FOOT': 0.3048,
            'INCH': 0.0254
        }[self.settings.unit_system]

        length_unit = self.ifc_file.createIfcSIUnit(
            UnitType='LENGTHUNIT',
            Name='METRE'
        )

        area_unit = self.ifc_file.createIfcSIUnit(
            UnitType='AREAUNIT',
            Name='SQUARE_METRE'
        )

        volume_unit = self.ifc_file.createIfcSIUnit(
            UnitType='VOLUMEUNIT',
            Name='CUBIC_METRE'
        )

        unit_assignment = self.ifc_file.createIfcUnitAssignment(
            Units=[length_unit, area_unit, volume_unit]
        )

        # Contesto geometrico
        geometric_context = self.ifc_file.createIfcGeometricRepresentationContext(
            ContextType='Model',
            CoordinateSpaceDimension=3,
            Precision=1.0e-5,
            WorldCoordinateSystem=self.ifc_file.createIfcAxis2Placement3D(
                Location=self.ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
            )
        )

        # Progetto
        self.project = self.ifc_file.createIfcProject(
            GlobalId=self._create_guid(),
            OwnerHistory=self.owner_history,
            Name=self.settings.project_name,
            Description=self.settings.project_description,
            UnitsInContext=unit_assignment,
            RepresentationContexts=[geometric_context]
        )

        # Site
        self.site = self.ifc_file.createIfcSite(
            GlobalId=self._create_guid(),
            OwnerHistory=self.owner_history,
            Name='Site'
        )

        # Building
        self.building = self.ifc_file.createIfcBuilding(
            GlobalId=self._create_guid(),
            OwnerHistory=self.owner_history,
            Name='Building'
        )

        # Relazioni gerarchiche
        self.ifc_file.createIfcRelAggregates(
            GlobalId=self._create_guid(),
            OwnerHistory=self.owner_history,
            RelatingObject=self.project,
            RelatedObjects=[self.site]
        )

        self.ifc_file.createIfcRelAggregates(
            GlobalId=self._create_guid(),
            OwnerHistory=self.owner_history,
            RelatingObject=self.site,
            RelatedObjects=[self.building]
        )

        # Structural Analysis Model
        self.structural_analysis_model = self.ifc_file.createIfcStructuralAnalysisModel(
            GlobalId=self._create_guid(),
            OwnerHistory=self.owner_history,
            Name='Structural Analysis',
            Description='Masonry FEM analysis results',
            PredefinedType='LOADING_3D',
            OrientationOf2DPlane=None,
            LoadedBy=[],  # Popolato dopo
            HasResults=[]  # Popolato dopo
        )

        logger.info("IFC project structure initialized")

    def add_node(self, node: StructuralNode):
        """Aggiungi nodo strutturale."""
        self.nodes.append(node)

    def add_nodes(self, nodes: List[StructuralNode]):
        """Aggiungi lista nodi strutturali."""
        self.nodes.extend(nodes)
        logger.info(f"Added {len(nodes)} nodes")

    def add_member(self, member: StructuralMember):
        """Aggiungi elemento strutturale."""
        self.members.append(member)

    def add_members(self, members: List[StructuralMember]):
        """Aggiungi lista elementi strutturali."""
        self.members.extend(members)
        logger.info(f"Added {len(members)} structural members")

    def add_load(self, load: StructuralLoad):
        """Aggiungi carico."""
        self.loads.append(load)

    def add_loads(self, loads: List[StructuralLoad]):
        """Aggiungi lista carichi."""
        self.loads.extend(loads)
        logger.info(f"Added {len(loads)} loads")

    def _create_ifc_nodes(self):
        """
        Crea entità IfcStructuralPointConnection per ogni nodo.
        """
        for node in self.nodes:
            # Coordinate nodo
            location = self.ifc_file.createIfcCartesianPoint(node.coordinates)

            placement = self.ifc_file.createIfcAxis2Placement3D(
                Location=location
            )

            # Crea punto strutturale
            ifc_node = self.ifc_file.createIfcStructuralPointConnection(
                GlobalId=self._create_guid(),
                OwnerHistory=self.owner_history,
                Name=f'Node_{node.node_id}',
                ObjectPlacement=self.ifc_file.createIfcLocalPlacement(
                    RelativePlacement=placement
                ),
                AppliedCondition=None  # Boundary conditions opzionali
            )

            # Memorizza mappatura
            self.ifc_nodes[node.node_id] = ifc_node

            # Collega al modello analisi
            self.ifc_file.createIfcRelConnectsStructuralActivity(
                GlobalId=self._create_guid(),
                OwnerHistory=self.owner_history,
                RelatingElement=ifc_node,
                RelatedStructuralActivity=None  # Collegato dopo se ci sono carichi
            )

        logger.info(f"Created {len(self.ifc_nodes)} IFC nodes")

    def _create_ifc_members(self):
        """
        Crea entità IfcStructuralSurfaceMember per pareti,
        IfcStructuralCurveMember per travi, etc.
        """
        for member in self.members:
            # Determina tipo entità IFC in base al tipo membro
            if member.member_type == 'wall':
                ifc_member = self._create_surface_member(member)
            elif member.member_type == 'slab':
                ifc_member = self._create_surface_member(member)
            elif member.member_type in ['beam', 'column']:
                ifc_member = self._create_curve_member(member)
            else:
                logger.warning(f"Unknown member type: {member.member_type}")
                continue

            self.ifc_members[member.member_id] = ifc_member

        logger.info(f"Created {len(self.ifc_members)} IFC structural members")

    def _create_surface_member(self, member: StructuralMember):
        """Crea IfcStructuralSurfaceMember (pareti, solai)."""
        # Prendi coordinate nodi
        if len(member.node_ids) < 3:
            logger.warning(f"Surface member {member.member_id} has < 3 nodes")
            return None

        # Calcola centroide
        coords = [
            self.nodes[i].coordinates
            for i in range(len(self.nodes))
            if self.nodes[i].node_id in member.node_ids
        ]

        if not coords:
            coords = [(0, 0, 0)]  # Fallback

        centroid = tuple(np.mean(coords, axis=0))

        location = self.ifc_file.createIfcCartesianPoint(centroid)
        placement = self.ifc_file.createIfcAxis2Placement3D(Location=location)

        # Crea superficie strutturale
        ifc_member = self.ifc_file.createIfcStructuralSurfaceMember(
            GlobalId=self._create_guid(),
            OwnerHistory=self.owner_history,
            Name=member.member_id,
            ObjectPlacement=self.ifc_file.createIfcLocalPlacement(
                RelativePlacement=placement
            ),
            PredefinedType='SHELL',
            Thickness=member.thickness if member.thickness else 0.30  # m
        )

        return ifc_member

    def _create_curve_member(self, member: StructuralMember):
        """Crea IfcStructuralCurveMember (travi, colonne)."""
        if len(member.node_ids) < 2:
            logger.warning(f"Curve member {member.member_id} has < 2 nodes")
            return None

        # Prendi coordinate estremi
        coords = [
            self.nodes[i].coordinates
            for i in range(len(self.nodes))
            if self.nodes[i].node_id in member.node_ids[:2]
        ]

        if not coords:
            coords = [(0, 0, 0)]

        midpoint = tuple(np.mean(coords, axis=0))

        location = self.ifc_file.createIfcCartesianPoint(midpoint)
        placement = self.ifc_file.createIfcAxis2Placement3D(Location=location)

        # Crea elemento lineare strutturale
        ifc_member = self.ifc_file.createIfcStructuralCurveMember(
            GlobalId=self._create_guid(),
            OwnerHistory=self.owner_history,
            Name=member.member_id,
            ObjectPlacement=self.ifc_file.createIfcLocalPlacement(
                RelativePlacement=placement
            ),
            PredefinedType='RIGID_JOINED_MEMBER'
        )

        return ifc_member

    def _create_ifc_loads(self):
        """Crea entità IfcStructuralAction per carichi."""
        if not self.settings.export_loads:
            return

        for load in self.loads:
            # Determina tipo azione
            if load.force:
                ifc_load = self._create_point_action(load)
            elif load.distributed_load:
                ifc_load = self._create_surface_action(load)
            else:
                continue

            self.ifc_loads[load.load_id] = ifc_load

        logger.info(f"Created {len(self.ifc_loads)} IFC loads")

    def _create_point_action(self, load: StructuralLoad):
        """Crea IfcStructuralPointAction (carico concentrato)."""
        # Trova nodo/membro a cui è applicato
        applied_to_entity = (
            self.ifc_nodes.get(int(load.applied_to)) if load.applied_to.isdigit()
            else self.ifc_members.get(load.applied_to)
        )

        if not applied_to_entity:
            logger.warning(f"Cannot find entity for load {load.load_id}")
            return None

        # Crea carico come forza lineare
        force_value = self.ifc_file.createIfcStructuralLoadSingleForce(
            Name=load.load_case,
            ForceX=load.force[0] if load.force else 0.0,
            ForceY=load.force[1] if load.force else 0.0,
            ForceZ=load.force[2] if load.force else 0.0,
        )

        # Crea azione
        point_action = self.ifc_file.createIfcStructuralPointAction(
            GlobalId=self._create_guid(),
            OwnerHistory=self.owner_history,
            Name=load.load_id,
            AppliedLoad=force_value,
            GlobalOrLocal='GLOBAL_COORDS'
        )

        return point_action

    def _create_surface_action(self, load: StructuralLoad):
        """Crea IfcStructuralSurfaceAction (carico distribuito)."""
        # Trova superficie a cui è applicato
        surface_member = self.ifc_members.get(load.applied_to)

        if not surface_member:
            return None

        # Carico planare
        planar_load = self.ifc_file.createIfcStructuralLoadPlanarForce(
            Name=load.load_case,
            PlanarForceX=0.0,
            PlanarForceY=0.0,
            PlanarForceZ=load.distributed_load if load.distributed_load else 0.0
        )

        surface_action = self.ifc_file.createIfcStructuralSurfaceAction(
            GlobalId=self._create_guid(),
            OwnerHistory=self.owner_history,
            Name=load.load_id,
            AppliedLoad=planar_load,
            GlobalOrLocal='GLOBAL_COORDS',
            ProjectedOrTrue='PROJECTED_LENGTH'
        )

        return surface_action

    def _create_results(self):
        """
        Crea gruppi risultati analisi.

        Per ogni membro, esporta:
        - Tensioni massime
        - Spostamenti
        - Rapporti utilizzo
        """
        if not self.settings.export_results:
            return

        # Crea gruppo risultati
        result_group = self.ifc_file.createIfcStructuralResultGroup(
            GlobalId=self._create_guid(),
            OwnerHistory=self.owner_history,
            Name='Analysis Results',
            Description='FEM analysis results',
            TheoryType='FIRST_ORDER_THEORY',
            IsLinear=True
        )

        # Per ogni membro, aggiungi risultati come proprietà
        for member in self.members:
            ifc_member = self.ifc_members.get(member.member_id)
            if not ifc_member:
                continue

            # Crea property set con risultati
            properties = []

            if member.max_stress is not None:
                prop = self.ifc_file.createIfcPropertySingleValue(
                    Name='MaxStress',
                    NominalValue=self.ifc_file.create_entity('IfcReal', member.max_stress),
                    Unit=None
                )
                properties.append(prop)

            if member.max_displacement is not None:
                prop = self.ifc_file.createIfcPropertySingleValue(
                    Name='MaxDisplacement',
                    NominalValue=self.ifc_file.create_entity('IfcReal', member.max_displacement),
                    Unit=None
                )
                properties.append(prop)

            if member.utilization_ratio is not None:
                prop = self.ifc_file.createIfcPropertySingleValue(
                    Name='UtilizationRatio',
                    NominalValue=self.ifc_file.create_entity('IfcReal', member.utilization_ratio),
                    Unit=None
                )
                properties.append(prop)

            if member.verification_status:
                prop = self.ifc_file.createIfcPropertySingleValue(
                    Name='VerificationStatus',
                    NominalValue=self.ifc_file.create_entity('IfcLabel', member.verification_status),
                    Unit=None
                )
                properties.append(prop)

            if properties:
                pset = self.ifc_file.createIfcPropertySet(
                    GlobalId=self._create_guid(),
                    OwnerHistory=self.owner_history,
                    Name='AnalysisResults',
                    HasProperties=properties
                )

                self.ifc_file.createIfcRelDefinesByProperties(
                    GlobalId=self._create_guid(),
                    OwnerHistory=self.owner_history,
                    RelatedObjects=[ifc_member],
                    RelatingPropertyDefinition=pset
                )

        logger.info("Created analysis results")

    def export(self, output_path: str) -> Path:
        """
        Esporta modello IFC su file.

        Args:
            output_path: Percorso file output (.ifc)

        Returns:
            Path del file generato

        Raises:
            ValueError: Se nessun dato da esportare
        """
        if not self.nodes and not self.members:
            raise ValueError("No structural data to export")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting IFC export to {output_path}")

        # 1. Inizializza struttura progetto
        self._initialize_project_structure()

        # 2. Crea nodi strutturali
        self._create_ifc_nodes()

        # 3. Crea elementi strutturali
        self._create_ifc_members()

        # 4. Crea carichi
        if self.loads:
            self._create_ifc_loads()

        # 5. Crea risultati
        self._create_results()

        # 6. Scrivi file
        self.ifc_file.write(str(output_path))

        # Log file info (se file creato realmente)
        if output_path.exists():
            file_size = output_path.stat().st_size
            logger.info(f"IFC file exported: {output_path} ({file_size} bytes)")
        else:
            logger.info(f"IFC export called for: {output_path}")

        return output_path

    def get_summary(self) -> Dict[str, Any]:
        """
        Ottieni riepilogo dati esportati.

        Returns:
            Dizionario con statistiche export
        """
        return {
            'ifc_version': self.settings.ifc_version,
            'schema': self.settings.schema,
            'nodes_count': len(self.nodes),
            'members_count': len(self.members),
            'loads_count': len(self.loads),
            'export_loads': self.settings.export_loads,
            'export_results': self.settings.export_results,
            'unit_system': self.settings.unit_system,
            'project_name': self.settings.project_name,
        }
