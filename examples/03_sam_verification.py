#!/usr/bin/env python3
"""
Esempio 3: Verifica SAM (Analisi Semplificata)
Secondo NTC 2018 - Muratura esistente
"""

from Material.engine import MasonryFEMEngine, AnalysisMethod
from Material.materials import MaterialProperties

def main():
    print("=" * 60)
    print("Esempio 3: Verifica SAM - Muratura Storica")
    print("=" * 60)

    # Motore SAM
    engine = MasonryFEMEngine(method=AnalysisMethod.SAM)

    # Muratura di tufo (tipica muratura storica)
    material = MaterialProperties(
        name="Muratura di tufo",
        fk=1.4,      # MPa - Resistenza caratteristica
        fvk0=0.035,  # MPa - Res. taglio senza carichi
        fvk=0.074    # MPa - Res. taglio con carichi
    )

    # Geometria semplificata
    wall_data = {
        'piers': [
            {'length': 1.0, 'height': 2.8, 'thickness': 0.6},  # Maschio 1
            {'length': 1.2, 'height': 2.8, 'thickness': 0.6}   # Maschio 2
        ],
        'spandrels': [
            {'length': 1.5, 'height': 0.5, 'thickness': 0.6}   # Fascia
        ]
    }

    # Carichi da analisi sismica
    loads = {
        'vertical': 180.0,  # kN
        'moment': 45.0,     # kNm
        'shear': 28.0       # kN
    }

    # Parametri NTC2018
    options = {
        'gamma_m': 2.0,  # Muratura esistente
        'FC': 1.35       # Fattore confidenza LC1
    }

    # Esegui verifica
    print("\n[1] Esecuzione verifica SAM...")
    results = engine.analyze_structure(wall_data, material, loads, options)

    # Stampa risultati
    print("\n[2] RISULTATI VERIFICA:")
    print("-" * 60)

    if results.get('verified'):
        print("\n✓ LA PARETE SODDISFA LE VERIFICHE DI SICUREZZA")
    else:
        print("\n✗ LA PARETE NON SODDISFA LE VERIFICHE")
        print("  È necessario un intervento di rinforzo")

    # Dettagli verifiche
    if 'element_checks' in results:
        print(f"\n[3] DETTAGLIO VERIFICHE ELEMENTI:")
        print("-" * 60)

        for i, check in enumerate(results['element_checks']):
            elem_type = check.get('element_type', 'unknown')
            verified = check.get('verified', False)
            dcr = check.get('DCR_max', 0)

            status = "✓" if verified else "✗"
            print(f"  {status} Elemento {i+1} ({elem_type}): DCR = {dcr:.2f}")

    # Raccomandazioni
    if not results.get('verified'):
        max_dcr = results.get('max_dcr', 0)
        print(f"\n[4] RACCOMANDAZIONI:")
        print(f"  • DCR massimo: {max_dcr:.2f}")
        print(f"  • Sovraccarico: {(max_dcr-1.0)*100:.0f}%")
        print(f"\n  Possibili interventi:")
        print(f"  • Rinforzo con rete in fibra di vetro/carbonio")
        print(f"  • Iniezioni di malta cementizia")
        print(f"  • Cordoli in c.a. ai piani")
        print(f"  • Riduzione carichi di esercizio")

    print("\n" + "=" * 60)
    print("✓ Verifica completata!")
    print("=" * 60)

    return results

if __name__ == '__main__':
    results = main()
