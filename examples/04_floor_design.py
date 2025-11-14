#!/usr/bin/env python3
"""
Example: Floor Design and Verification - NTC 2018
==================================================

Dimostra l'utilizzo del modulo floors per il calcolo e verifica
di solai in latero-cemento secondo NTC 2018.

Scenario:
---------
- Edificio residenziale (Cat. A)
- Solaio in latero-cemento interpiano
- Luce 5.0 m
- Altezza solaio 24 cm (20+4)
- Calcestruzzo C25/30
- Acciaio B450C

"""

import sys
from pathlib import Path

# Add Material module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Material.analyses.floors import (
    FloorAnalysis,
    FloorGeometry,
    FloorLoads,
    FloorType,
    SupportType
)


def example_1_simply_supported_residential():
    """
    Esempio 1: Solaio residenziale semplicemente appoggiato
    """
    print("\n" + "="*70)
    print("ESEMPIO 1: Solaio Residenziale - Schema Appoggiato")
    print("="*70)

    # Definizione geometria
    geometry = FloorGeometry(
        span=5.0,  # Luce 5 m
        width=4.0,  # Larghezza 4 m
        thickness=0.24,  # Altezza totale 24 cm
        slab_thickness=0.04,  # Soletta 4 cm
        rib_spacing=0.50,  # Interasse nervature 50 cm
        rib_width=0.10  # Larghezza nervatura 10 cm
    )

    # Definizione carichi
    loads = FloorLoads(
        permanent_loads=0.0,  # Calcolato automaticamente (peso proprio)
        additional_permanent=2.0,  # Pavimento, intonaco, impianti [kN/m²]
        live_loads=2.0,  # Residenziale Cat. A [kN/m²]
        partition_walls=1.0,  # Tramezzi [kN/m²]
        self_weight_included=False
    )

    # Crea analisi solaio
    floor = FloorAnalysis(
        floor_type='latero-cemento',
        geometry=geometry,
        concrete_class='C25/30',
        steel_class='B450C',
        support_type='simply_supported',
        loads=loads
    )

    # Genera report completo
    report = floor.generate_report()
    print(report)

    # Dettagli armature
    reinforcement = floor.calculate_reinforcement()
    print(f"\n📐 DETTAGLIO ARMATURA:")
    print(f"   Armatura necessaria: {reinforcement['As_long']:.2f} cm²/m")
    print(f"   Disposizione: φ{reinforcement['phi']:.0f} ogni {reinforcement['spacing']:.0f} cm")
    print(f"   (≈ {int(reinforcement['n_bars'])} barre per metro)")

    return floor


def example_2_continuous_floor():
    """
    Esempio 2: Solaio continuo su 2 campate
    """
    print("\n" + "="*70)
    print("ESEMPIO 2: Solaio Continuo (2 campate)")
    print("="*70)

    geometry = FloorGeometry(
        span=4.5,
        width=5.0,
        thickness=0.24,
        slab_thickness=0.04,
        rib_spacing=0.50,
        rib_width=0.10
    )

    loads = FloorLoads(
        additional_permanent=2.5,  # Maggiore finitura
        live_loads=2.0,
        partition_walls=1.0
    )

    floor = FloorAnalysis(
        floor_type='latero-cemento',
        geometry=geometry,
        concrete_class='C25/30',
        steel_class='B450C',
        support_type='continuous',  # Continuo
        loads=loads
    )

    # Genera report
    report = floor.generate_report()
    print(report)

    # Confronto momenti
    moments = floor.calculate_moments()
    print(f"\n📊 CONFRONTO MOMENTI:")
    print(f"   Momento in campata: {moments['M_max']:.2f} kNm/m")
    print(f"   Momento su appoggio: {moments['M_support']:.2f} kNm/m")
    print(f"   → Momento su appoggio maggiore (richiede armatura superiore)")

    return floor


def example_3_office_building():
    """
    Esempio 3: Solaio uffici (Cat. B) con maggiori sovraccarichi
    """
    print("\n" + "="*70)
    print("ESEMPIO 3: Solaio Uffici - Categoria B")
    print("="*70)

    geometry = FloorGeometry(
        span=6.0,  # Luce maggiore
        width=5.0,
        thickness=0.26,  # Altezza maggiore (22+4)
        slab_thickness=0.04,
        rib_spacing=0.50,
        rib_width=0.12  # Nervatura più larga
    )

    loads = FloorLoads(
        additional_permanent=2.0,
        live_loads=3.0,  # Categoria B uffici
        partition_walls=1.5  # Maggiori tramezzi
    )

    floor = FloorAnalysis(
        floor_type='latero-cemento',
        geometry=geometry,
        concrete_class='C28/35',  # Classe superiore
        steel_class='B450C',
        support_type='simply_supported',
        loads=loads
    )

    report = floor.generate_report()
    print(report)

    # Verifica deformazione
    sle = floor.verify_sle()
    print(f"\n📏 VERIFICA DEFORMABILITÀ:")
    print(f"   Freccia calcolata: {sle['deflection']['deflection']:.1f} mm")
    print(f"   Limite L/250: {sle['deflection']['limit']:.1f} mm")
    print(f"   Rapporto utilizzo: {sle['deflection']['ratio']:.1%}")
    print(f"   Status: {'✓ OK' if sle['deflection']['verified'] else '✗ NON OK'}")

    return floor


def example_4_seismic_integration():
    """
    Esempio 4: Integrazione con analisi sismica (diaframma)
    """
    print("\n" + "="*70)
    print("ESEMPIO 4: Integrazione Sismica - Diaframma")
    print("="*70)

    geometry = FloorGeometry(
        span=5.0,
        width=8.0,  # Edificio allungato
        thickness=0.24,
        slab_thickness=0.04,
        rib_spacing=0.50,
        rib_width=0.10
    )

    loads = FloorLoads(
        additional_permanent=2.0,
        live_loads=2.0,
        partition_walls=1.0
    )

    floor = FloorAnalysis(
        floor_type='latero-cemento',
        geometry=geometry,
        concrete_class='C25/30',
        steel_class='B450C',
        support_type='simply_supported',
        loads=loads
    )

    # Valuta comportamento diaframma
    diaphragm = floor.assess_diaphragm_behavior()
    print(f"\n🏗️  COMPORTAMENTO DIAFRAMMA:")
    print(f"   Tipo: {diaphragm.value}")

    # Integrazione con muratura (assume rigidezza pareti)
    wall_stiffness = 50000.0  # kN/m (tipico per muratura)
    integration = floor.integrate_with_walls(
        wall_stiffness=wall_stiffness,
        seismic=True
    )

    print(f"\n📊 INTEGRAZIONE SOLAIO-MURATURA:")
    print(f"   Rigidezza nel piano: {integration['in_plane_stiffness']:.0f} kN/m")
    print(f"   Massa sismica: {integration['seismic_mass']:.2f} ton")
    print(f"   Tensione collegamento: {integration['connection_stress']:.3f} MPa")
    print(f"   Collegamento verificato: {'✓ SI' if integration['connection_verified'] else '✗ NO'}")

    return floor


def example_5_wood_floor():
    """
    Esempio 5: Solaio in legno (edifici storici)
    """
    print("\n" + "="*70)
    print("ESEMPIO 5: Solaio in Legno - Edificio Storico")
    print("="*70)

    geometry = FloorGeometry(
        span=3.5,  # Luce ridotta (storico)
        width=4.0,
        thickness=0.25,  # Travi + tavolato
        slab_thickness=0.05,  # Tavolato
        rib_spacing=0.40,  # Interasse travi
        rib_width=0.15  # Larghezza trave
    )

    loads = FloorLoads(
        additional_permanent=1.5,  # Finitura leggera
        live_loads=2.0,
        partition_walls=0.5  # Pochi tramezzi
    )

    floor = FloorAnalysis(
        floor_type='wood',
        geometry=geometry,
        concrete_class='C25/30',  # Non usato per legno
        steel_class='B450C',  # Non usato per legno
        support_type='simply_supported',
        loads=loads
    )

    # Solo calcolo carichi e peso proprio
    self_weight = floor.calculate_self_weight()
    moments = floor.calculate_moments()

    print(f"\n🌲 SOLAIO IN LEGNO:")
    print(f"   Peso proprio: {self_weight:.2f} kN/m²")
    print(f"   Carico totale SLU: {moments['q_slu']:.2f} kN/m²")
    print(f"   Momento massimo: {moments['M_max']:.2f} kNm/m")
    print(f"\n   Note: Verifica secondo CNR DT 206/2007 per legno")

    return floor


def comparison_table():
    """
    Tabella comparativa diverse tipologie
    """
    print("\n" + "="*70)
    print("TABELLA COMPARATIVA - Diverse Tipologie di Solaio")
    print("="*70)

    configs = [
        ("Residenziale L=5m", 5.0, 0.24, 2.0),
        ("Uffici L=6m", 6.0, 0.26, 3.0),
        ("Residenziale L=4m", 4.0, 0.22, 2.0),
    ]

    print(f"\n{'Tipo':<20} {'L[m]':<8} {'h[cm]':<8} {'Q[kN/m²]':<10} {'As[cm²/m]':<12} {'δ[mm]':<10} {'Verif':<8}")
    print("-" * 88)

    for name, span, thickness, live_load in configs:
        geometry = FloorGeometry(
            span=span,
            width=4.0,
            thickness=thickness,
            slab_thickness=0.04
        )
        loads = FloorLoads(
            additional_permanent=2.0,
            live_loads=live_load,
            partition_walls=1.0
        )
        floor = FloorAnalysis(
            floor_type='latero-cemento',
            geometry=geometry,
            loads=loads
        )

        reinforcement = floor.calculate_reinforcement()
        sle = floor.verify_sle()
        slu = floor.verify_slu()

        verified = "✓ OK" if (slu['overall_verified'] and sle['overall_verified']) else "✗ NO"

        print(f"{name:<20} {span:<8.1f} {thickness*100:<8.0f} {live_load:<10.1f} "
              f"{reinforcement['As_long']:<12.2f} {sle['deflection']['deflection']:<10.1f} {verified:<8}")

    print("-" * 88)


if __name__ == "__main__":
    print("\n🏗️  MURATURA FEM v6.2 - Floor Design Module Examples")
    print("=" * 70)

    # Esegui tutti gli esempi
    floor1 = example_1_simply_supported_residential()
    floor2 = example_2_continuous_floor()
    floor3 = example_3_office_building()
    floor4 = example_4_seismic_integration()
    floor5 = example_5_wood_floor()

    # Tabella comparativa
    comparison_table()

    print("\n" + "="*70)
    print("✅ Tutti gli esempi completati con successo!")
    print("="*70)
    print("\nProssimi passi:")
    print("  1. Integrare con MasonryFEMEngine per analisi complete")
    print("  2. Implementare database pignatte commerciali")
    print("  3. Aggiungere verifica punzonamento (pilastri)")
    print("  4. Implementare solaio misto (acciaio + cls)")
    print("  5. Export disegni esecutivi (DXF)")
