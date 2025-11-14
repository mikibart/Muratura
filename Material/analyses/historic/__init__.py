"""
Module: historic/__init__.py
Analisi edifici storici in muratura

Questo modulo implementa metodi avanzati per l'analisi di strutture storiche
in muratura secondo teoria dell'analisi limite (Heyman) e approcci moderni.

Status: 🔄 IN DEVELOPMENT (Fase 2 - v6.4)
Target: Q2 2025

Moduli:
- arches.py: Analisi archi metodo Heyman ✅ IMPLEMENTATO
- vaults.py: Analisi volte (botte, crociera, cupole) ✅ IMPLEMENTATO
- towers.py: Analisi torri e pilastri snelli 🔄 TODO

Per dettagli completi vedere:
- docs/PHASE_2_HISTORIC_BUILDINGS_PLAN.md
- Material/analyses/historic/README.md
"""

__version__ = "0.2.0-alpha"
__status__ = "Development"

# Importa moduli implementati
from .arches import (
    ArchAnalysis,
    ArchGeometry,
    ArchType,
    FailureMode as ArchFailureMode,
    MASONRY_DENSITIES
)

from .vaults import (
    VaultAnalysis,
    VaultGeometry,
    VaultType,
    FailureMode as VaultFailureMode
)

__all__ = [
    # Arches
    'ArchAnalysis',
    'ArchGeometry',
    'ArchType',
    'ArchFailureMode',
    # Vaults
    'VaultAnalysis',
    'VaultGeometry',
    'VaultType',
    'VaultFailureMode',
    # Common
    'MASONRY_DENSITIES',
]

# TODO Fase 2:
# from .towers import TowerAnalysis
