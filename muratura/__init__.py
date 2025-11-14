"""
MasonryFEMEngine - Sistema di Analisi Strutturale per Murature
================================================================

Un motore completo di calcolo FEM per l'analisi strutturale di murature
secondo le Norme Tecniche per le Costruzioni NTC 2018.

Moduli principali:
- materials: Gestione proprietà dei materiali murari
- geometry: Definizione geometrie strutturali
- engine: Motore di calcolo principale
- analyses: Moduli di analisi (FEM, SAM, POR, limite, fiber, micro, frame)
- enums: Enumerazioni e costanti
- constitutive: Modelli costitutivi
- utils: Funzioni di utilità

Esempio:
    >>> from muratura import MaterialProperties, MasonryFEMEngine, AnalysisMethod
    >>> material = MaterialProperties.from_ntc_table(
    ...     MasonryType.MATTONI_PIENI,
    ...     MortarQuality.BUONA
    ... )
    >>> engine = MasonryFEMEngine(method=AnalysisMethod.SAM)
    >>> results = engine.analyze_structure(wall_data, material, loads)
"""

__version__ = "1.0.0"
__author__ = "MasonryFEM Contributors"
__license__ = "MIT"

from .materials import (
    MaterialProperties,
    MasonryType,
    MortarQuality,
    ConservationState,
    UnitSystem,
    UnitsConverter,
    MaterialDatabase,
    CommonMaterials,
    compare_materials,
    create_material_report
)

from .geometry import (
    GeometryPier,
    GeometrySpandrel,
    BoundaryCondition,
    ReinforcementType,
    WallType
)

from .engine import (
    MasonryFEMEngine
)

from .enums import (
    AnalysisMethod,
    AnalysisType,
    FailureMode,
    DamageLevel,
    ConstitutiveLaw,
    KinematicMechanism,
    LoadType,
    LoadCombination,
    LimitState,
    PerformanceLevel,
    KnowledgeLevel,
    get_fc_from_knowledge_level,
    get_behavior_factor
)

__all__ = [
    # Version
    '__version__',
    '__author__',
    '__license__',

    # Materials
    'MaterialProperties',
    'MasonryType',
    'MortarQuality',
    'ConservationState',
    'UnitSystem',
    'UnitsConverter',
    'MaterialDatabase',
    'CommonMaterials',
    'compare_materials',
    'create_material_report',

    # Geometry
    'GeometryPier',
    'GeometrySpandrel',
    'BoundaryCondition',
    'ReinforcementType',
    'WallType',

    # Engine
    'MasonryFEMEngine',

    # Enums
    'AnalysisMethod',
    'AnalysisType',
    'FailureMode',
    'DamageLevel',
    'ConstitutiveLaw',
    'KinematicMechanism',
    'LoadType',
    'LoadCombination',
    'LimitState',
    'PerformanceLevel',
    'KnowledgeLevel',
    'get_fc_from_knowledge_level',
    'get_behavior_factor'
]
