#!/usr/bin/env python3
"""
Example: Stair Design and Verification - NTC 2018
==================================================

Esempi di calcolo e verifica scale secondo NTC 2018 e DM 236/89.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Material.analyses.stairs import StairAnalysis, StairGeometry, StairLoads

def example_1_residential_stair():
    """Esempio 1: Scala residenziale interna (Cat. A)"""
    print("\n" + "="*70)
    print("ESEMPIO 1: Scala Residenziale Interna")
    print("="*70)

    geometry = StairGeometry(
        floor_height=3.0,  # Interpiano 3m
        n_steps=17,  # 17 gradini
        width=1.00,  # Larghezza 1m
        landing_length=1.00,
        thickness=0.18
    )

    loads = StairLoads(
        permanent_loads=1.5,
        live_loads=2.0  # Cat. A residenziale
    )

    stair = StairAnalysis(
        stair_type='slab_ramp',
        geometry=geometry,
        loads=loads
    )

    report = stair.generate_report()
    print(report)

    return stair

def example_2_public_stair():
    """Esempio 2: Scala pubblica/condominiale (Cat. C)"""
    print("\n" + "="*70)
    print("ESEMPIO 2: Scala Pubblica/Condominiale")
    print("="*70)

    geometry = StairGeometry(
        floor_height=3.20,
        n_steps=18,
        width=1.20,  # Larghezza maggiore
        landing_length=1.20,
        thickness=0.20
    )

    loads = StairLoads(
        permanent_loads=2.0,
        live_loads=4.0  # Cat. C
    )

    stair = StairAnalysis(
        stair_type='slab_ramp',
        geometry=geometry,
        support_condition='one_end_fixed',
        loads=loads
    )

    report = stair.generate_report()
    print(report)

    return stair

if __name__ == "__main__":
    print("\n🏗️  MURATURA FEM v6.3 - Stair Design Module Examples")
    print("=" * 70)

    stair1 = example_1_residential_stair()
    stair2 = example_2_public_stair()

    print("\n" + "="*70)
    print("✅ Esempi completati!")
    print("="*70)
    print("\n📊 FASE 1 ROADMAP: 100% COMPLETATA")
    print("  ✅ Solai (floors)")
    print("  ✅ Balconi (balconies)")
    print("  ✅ Scale (stairs)")
    print("\n→ Feature parity BASE raggiunta con software commerciali!")
