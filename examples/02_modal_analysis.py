#!/usr/bin/env python3
"""
Esempio 2: Analisi Modale
Calcolo modi di vibrare e masse partecipanti
"""

from Material.engine import MasonryFEMEngine, AnalysisMethod
from Material.materials import MaterialProperties

def main():
    print("=" * 60)
    print("Esempio 2: Analisi Modale - Edificio 3 Piani")
    print("=" * 60)

    # Crea motore
    engine = MasonryFEMEngine(method=AnalysisMethod.FRAME)

    # Materiale
    material = MaterialProperties(
        name="Muratura mattoni",
        E=1500.0,
        fcm=4.0,
        G=500.0,
        weight=18.0
    )

    # Geometria edificio 3 piani
    wall_data = {
        'length': 6.0,
        'height': 9.0,      # 3 x 3m
        'thickness': 0.4,
        'n_floors': 3,
        'floor_masses': {
            0: 60000,  # kg - Piano 1
            1: 55000,  # kg - Piano 2
            2: 50000   # kg - Piano 3 (copertura)
        }
    }

    # Opzioni
    options = {
        'analysis_type': 'modal',
        'n_modes': 6
    }

    # Esegui
    print("\n[1] Calcolo modi di vibrare...")
    results = engine.analyze_structure(wall_data, material, {}, options)

    # Stampa risultati
    print("\n[2] MODI DI VIBRARE:")
    print("-" * 60)
    print(f"{'Modo':<6} {'Periodo':<12} {'Freq':<12} {'Mx %':<12} {'My %':<12}")
    print("-" * 60)

    for i in range(len(results['frequencies'])):
        T = results['periods'][i]
        f = results['frequencies'][i]
        mx = results['mass_participation_x'][i] * 100
        my = results['mass_participation_y'][i] * 100

        print(f"{i+1:<6} {T:<12.4f} {f:<12.3f} {mx:<12.1f} {my:<12.1f}")

    print("-" * 60)
    print(f"{'TOTALE':<6} {'':<12} {'':<12} "
          f"{results['total_mass_participation_x']*100:<12.1f} "
          f"{results['total_mass_participation_y']*100:<12.1f}")
    print("-" * 60)

    # Verifica requisito EC8/NTC (>85% massa partecipante)
    print("\n[3] VERIFICA REQUISITI NORMATIVA:")
    mx_tot = results['total_mass_participation_x'] * 100
    my_tot = results['total_mass_participation_y'] * 100

    print(f"  • Massa partecipante X: {mx_tot:.1f}% ", end="")
    print("✓" if mx_tot >= 85 else "✗ (richiesto ≥85%)")

    print(f"  • Massa partecipante Y: {my_tot:.1f}% ", end="")
    print("✓" if my_tot >= 85 else "✗ (richiesto ≥85%)")

    # Informazioni massa totale
    if 'total_mass' in results:
        mass_info = results['total_mass']
        print(f"\n[4] MASSE TOTALI:")
        print(f"  • Massa in X: {mass_info.get('x_direction', 0):.1f} ton")
        print(f"  • Massa in Y: {mass_info.get('y_direction', 0):.1f} ton")

    print("\n" + "=" * 60)
    print("✓ Analisi modale completata!")
    print("=" * 60)

    return results

if __name__ == '__main__':
    results = main()
