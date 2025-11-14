"""
Module: bim/__init__.py
BIM Integration for Muratura FEM

Questo modulo implementa funzionalità di integrazione BIM (Building Information Modeling)
per import/export di modelli IFC e interoperabilità con software BIM (Revit, ArchiCAD, etc.).

Status: 🔄 IN DEVELOPMENT (Fase 3 - v7.0)
Target: Q2-Q3 2025

Moduli:
- ifc_import.py: Import modelli IFC → Muratura FEM ✅ IMPLEMENTATO
- ifc_export.py: Export risultati → IFC structural ✅ IMPLEMENTATO
- revit_plugin.py: Plugin base per Autodesk Revit 🔄 TODO

Per dettagli completi vedere:
- docs/PHASE_3_BIM_REPORTS_PLAN.md
"""

__version__ = "0.1.0-alpha"
__status__ = "Development"

# Importa moduli implementati
from .ifc_import import (
    IFCImporter,
    IFCImportSettings
)

from .ifc_export import (
    IFCExporter,
    IFCExportSettings,
    StructuralNode,
    StructuralMember,
    StructuralLoad
)

__all__ = [
    'IFCImporter',
    'IFCImportSettings',
    'IFCExporter',
    'IFCExportSettings',
    'StructuralNode',
    'StructuralMember',
    'StructuralLoad',
]
