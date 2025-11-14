"""
MURATURA FEM v7.0.0-alpha

Sistema completo di analisi FEM per strutture in muratura secondo NTC 2018.

Moduli principali:
- MasonryFEMEngine: Motore FEM principale
- MaterialProperties: Definizione materiali
- Geometry: Modelli geometrici
- Verifiche NTC 2018, Eurocode 8

Fasi implementate:
- Fase 1: Elementi strutturali (solai, balconi, scale)
- Fase 2: Edifici storici (archi, volte, FRP/FRCM)
- Fase 3: BIM Integration (IFC import/export, report generation)

Author: MURATURA FEM Team
License: MIT
"""

__version__ = '7.0.0-alpha'

# Import main classes
try:
    from Material.engine import MasonryFEMEngine
except ImportError:
    MasonryFEMEngine = None

try:
    from Material.materials import MaterialProperties
except ImportError:
    MaterialProperties = None

# Make them available at package level
__all__ = [
    'MasonryFEMEngine',
    'MaterialProperties',
    '__version__',
]
