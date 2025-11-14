"""
Module: reports/__init__.py
Automatic Report Generation for Muratura FEM

Questo modulo implementa la generazione automatica di relazioni di calcolo
strutturale conformi alla normativa NTC 2018, con export in PDF e Word.

Status: 🔄 IN DEVELOPMENT (Fase 3 - v7.0)
Target: Q2-Q3 2025

Moduli:
- report_generator.py: Generatore report principale ✅ IMPLEMENTATO
- templates/: Template LaTeX e Jinja2 per relazioni 🔄 IN DEVELOPMENT

Features:
- Report conformi NTC 2018 §10.1 (Relazione di calcolo)
- Export PDF (via LaTeX + pdflatex)
- Export Word DOCX (via python-docx)
- Grafici integrati (matplotlib)
- Template personalizzabili (Jinja2)
- Sezioni: materiali, carichi, analisi, verifiche

Per dettagli completi vedere:
- docs/PHASE_3_BIM_REPORTS_PLAN.md
"""

__version__ = "0.1.0-alpha"
__status__ = "Development"

# Importa moduli implementati
from .report_generator import (
    ReportGenerator,
    ReportMetadata,
    ReportSettings
)

__all__ = [
    'ReportGenerator',
    'ReportMetadata',
    'ReportSettings',
]
