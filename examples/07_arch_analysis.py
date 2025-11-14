#!/usr/bin/env python3
"""
Example: Arch Analysis - Heyman Limit Analysis Method
======================================================

Esempi di analisi archi in muratura con metodo Heyman (1966-1982).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Material.analyses.historic.arches import ArchAnalysis, ArchGeometry

def example_1_roman_arch():
    """Esempio 1: Arco Romano semicircolare"""
    print("\n" + "="*70)
    print("ESEMPIO 1: Arco Romano - Ponte Antico")
    print("="*70)

    geometry = ArchGeometry(
        arch_type='semicircular',
        span=4.0,  # Luce 4m
        rise=2.0,  # Freccia 2m (semicerchio)
        thickness=0.50,  # Spessore 50cm
        width=1.0
    )

    arch = ArchAnalysis(
        geometry=geometry,
        masonry_density=22.0,  # Pietra calcarea
        n_voussoirs=30
    )

    report = arch.generate_report()
    print(report)

    return arch

def example_2_gothic_arch():
    """Esempio 2: Arco Gotico acuto"""
    print("\n" + "="*70)
    print("ESEMPIO 2: Arco Gotico Acuto - Cattedrale")
    print("="*70)

    geometry = ArchGeometry(
        arch_type='pointed',
        span=3.0,
        rise=4.0,  # rise > span/2 → arco acuto
        thickness=0.40,
        width=1.0
    )

    arch = ArchAnalysis(
        geometry=geometry,
        masonry_density=18.0,  # Mattoni
        n_voussoirs=40
    )

    report = arch.generate_report()
    print(report)

    # Safety factor
    safety = arch.calculate_safety_factor()
    print(f"\n📊 Arco gotico FS = {safety['geometric_safety_factor']:.2f}")
    print(f"   (Archi gotici tipicamente FS > 3.0 per verticalità spinta)")

    return arch

if __name__ == "__main__":
    print("\n🏛️  MURATURA FEM v6.4 - Arch Analysis Module (Heyman Method)")
    print("=" * 70)

    arch1 = example_1_roman_arch()
    arch2 = example_2_gothic_arch()

    print("\n" + "="*70)
    print("✅ Esempi completati!")
    print("="*70)
    print("\n🎯 FASE 2: Primo modulo implementato (Archi)")
    print("   Prossimi: Volte, Rinforzi, Knowledge Levels")
