#!/usr/bin/env python3
"""
Esempio 1: Analisi Pushover Semplice
Parete a 2 piani con telaio equivalente
"""

from Material.engine import MasonryFEMEngine, AnalysisMethod
from Material.materials import MaterialProperties

def main():
    print("=" * 60)
    print("Esempio 1: Analisi Pushover - Parete 2 Piani")
    print("=" * 60)

    # 1. Crea motore FEM
    engine = MasonryFEMEngine(method=AnalysisMethod.FRAME)

    # 2. Definisci materiale (muratura di mattoni)
    material = MaterialProperties(
        name="Muratura mattoni pieni",
        E=1500.0,      # MPa
        fcm=4.0,       # MPa
        ftm=0.15,      # MPa
        tau0=0.1,      # MPa
        mu=0.4,
        G=500.0,       # MPa
        weight=18.0    # kN/m³
    )

    # 3. Definisci geometria
    wall_data = {
        'length': 5.0,
        'height': 6.0,
        'thickness': 0.3,
        'n_floors': 2,
        'floor_masses': {
            0: 50000,  # kg
            1: 45000
        }
    }

    # 4. Carichi verticali
    loads = {
        0: {'Fx': 0, 'Fy': -50},  # kN
        1: {'Fx': 0, 'Fy': -45}
    }

    # 5. Opzioni analisi
    options = {
        'analysis_type': 'pushover',
        'lateral_pattern': 'triangular',
        'target_drift': 0.04,
        'n_steps': 50
    }

    # 6. Esegui analisi
    print("\n[1] Esecuzione analisi pushover...")
    results = engine.analyze_structure(wall_data, material, loads, options)

    # 7. Stampa risultati
    print("\n[2] RISULTATI:")
    print("-" * 60)

    if 'performance_levels' in results:
        yield_level = results['performance_levels'].get('yield', {})
        ultimate_level = results['performance_levels'].get('ultimate', {})

        print(f"\n✓ Livello di Snervamento:")
        print(f"  • Taglio base:     {yield_level.get('base_shear', 0):.1f} kN")
        print(f"  • Drift:           {yield_level.get('top_drift', 0)*100:.2f}%")
        print(f"  • Spostamento:     {yield_level.get('roof_displacement', 0)*1000:.1f} mm")

        print(f"\n✓ Livello Ultimo:")
        print(f"  • Taglio base:     {ultimate_level.get('base_shear', 0):.1f} kN")
        print(f"  • Drift:           {ultimate_level.get('top_drift', 0)*100:.2f}%")
        print(f"  • Spostamento:     {ultimate_level.get('roof_displacement', 0)*1000:.1f} mm")

        if 'ductility' in results:
            print(f"\n✓ Duttilità globale: {results['ductility']:.2f}")

    # 8. Verifica elementi
    if 'element_checks' in results:
        failed = [e for e in results['element_checks'] if not e['verified']]
        print(f"\n✓ Verifiche elementi:")
        print(f"  • Elementi totali:    {len(results['element_checks'])}")
        print(f"  • Elementi verificati: {len(results['element_checks']) - len(failed)}")
        print(f"  • Elementi non verificati: {len(failed)}")

        if failed:
            print(f"\n⚠ Elementi critici:")
            for elem in failed[:3]:  # Mostra solo primi 3
                print(f"  • Elemento {elem['element_id']} ({elem['element_type']}): "
                      f"DCR={elem['DCR_max']:.2f}")

    print("\n" + "=" * 60)
    print("✓ Analisi completata con successo!")
    print("=" * 60)

    return results

if __name__ == '__main__':
    results = main()
