"""
Esempio 2: Analisi Pushover con Telaio Equivalente
===================================================

Questo esempio mostra come eseguire un'analisi pushover su un edificio
multipiano modellato con telaio equivalente.
"""

from muratura import (
    MaterialProperties,
    MasonryType,
    MortarQuality,
    MasonryFEMEngine,
    AnalysisMethod
)


def main():
    print("="*70)
    print("ESEMPIO 2: Analisi Pushover - Telaio Equivalente")
    print("="*70)

    # ========================================================================
    # STEP 1: Materiale
    # ========================================================================
    print("\n1. Definizione materiale:")
    print("-" * 40)

    material = MaterialProperties.from_ntc_table(
        MasonryType.PIETRA_SQUADRATA,
        MortarQuality.BUONA,
        position='mean'
    )

    print(f"Materiale: {material.material_type}")
    print(f"fcm = {material.fcm:.2f} MPa, E = {material.E:.0f} MPa")

    # ========================================================================
    # STEP 2: Geometria edificio
    # ========================================================================
    print("\n2. Definizione geometria edificio:")
    print("-" * 40)

    wall_data = {
        'length': 5.0,              # m - lunghezza parete
        'height': 3.0,              # m - altezza interpiano
        'thickness': 0.4,           # m - spessore muro
        'floor_masses': {           # kg - masse di piano
            0: 50000,  # Piano 1
            1: 50000,  # Piano 2
        }
    }

    n_floors = len(wall_data['floor_masses'])
    print(f"Numero piani: {n_floors}")
    print(f"Altezza interpiano: {wall_data['height']} m")
    print(f"Altezza totale: {wall_data['height'] * (n_floors+1):.1f} m")
    print(f"Spessore muri: {wall_data['thickness']} m")
    print(f"Massa totale: {sum(wall_data['floor_masses'].values())/1000:.1f} t")

    # ========================================================================
    # STEP 3: Configurazione analisi pushover
    # ========================================================================
    print("\n3. Configurazione analisi pushover:")
    print("-" * 40)

    options = {
        'analysis_type': 'pushover',
        'lateral_pattern': 'triangular',  # 'triangular', 'uniform', 'modal'
        'target_drift': 0.04,              # Drift obiettivo 4%
        'n_steps': 50,                     # Numero passi incrementali
        'direction': 'y'                   # Direzione spinta
    }

    print(f"Pattern laterale: {options['lateral_pattern']}")
    print(f"Drift target: {options['target_drift']:.1%}")
    print(f"Direzione: {options['direction'].upper()}")

    # ========================================================================
    # STEP 4: Esegui analisi
    # ========================================================================
    print("\n4. Esecuzione analisi...")
    print("-" * 40)

    engine = MasonryFEMEngine(method=AnalysisMethod.FRAME)

    results = engine.analyze_structure(
        wall_data=wall_data,
        material=material,
        loads={},  # Nessun carico esterno oltre alle masse
        options=options
    )

    # ========================================================================
    # STEP 5: Risultati
    # ========================================================================
    print("\n5. RISULTATI ANALISI PUSHOVER:")
    print("=" * 70)

    # Informazioni modello
    model_summary = results.get('model_summary', {})
    print("\nModello strutturale:")
    print(f"  Nodi: {model_summary.get('n_nodes', 0)}")
    print(f"  Maschi murari: {model_summary.get('n_piers', 0)}")
    print(f"  Fasce di piano: {model_summary.get('n_spandrels', 0)}")

    # Curva pushover
    curve = results.get('curve', [])
    if curve:
        print(f"\nCurva pushover ({len(curve)} punti):")
        print("  Drift [%]  |  Base Shear [kN]  |  Roof Disp [m]")
        print("  " + "-"*50)

        # Mostra alcuni punti caratteristici
        indices = [0, len(curve)//4, len(curve)//2, 3*len(curve)//4, -1]
        for i in indices:
            point = curve[i]
            drift = point['top_drift'] * 100
            shear = point['base_shear']
            disp = point['roof_displacement']
            print(f"  {drift:6.3f}    |  {shear:12.1f}      |  {disp:8.4f}")

    # Livelli prestazionali
    perf_levels = results.get('performance_levels', {})

    if 'yield' in perf_levels:
        y = perf_levels['yield']
        print("\nPunto di snervamento:")
        print(f"  Drift: {y['top_drift']:.3%}")
        print(f"  Base Shear: {y['base_shear']:.1f} kN")
        print(f"  Roof Displacement: {y['roof_displacement']:.4f} m")

    if 'ultimate' in perf_levels:
        u = perf_levels['ultimate']
        print("\nPunto ultimo:")
        print(f"  Drift: {u['top_drift']:.3%}")
        print(f"  Base Shear: {u['base_shear']:.1f} kN")
        print(f"  Roof Displacement: {u['roof_displacement']:.4f} m")

        if 'ductility' in u:
            print(f"\nDuttilità globale: {u['ductility']:.2f}")

    # Punto di prestazione (N2)
    if 'performance_point' in results:
        pp = results['performance_point']
        print("\nPunto di prestazione (metodo N2):")
        print(f"  Displacement: {pp['displacement']:.4f} m")
        print(f"  Base Shear: {pp['base_shear']:.1f} kN")

    # Verifiche elementi
    element_checks = results.get('element_checks', [])
    if element_checks:
        print("\nVerifica elementi critici:")
        print("  ID  |  Tipo     |  DCR Max  |  Danno")
        print("  " + "-"*45)

        # Ordina per DCR decrescente e mostra i primi 5
        sorted_checks = sorted(element_checks, key=lambda x: x['DCR_max'], reverse=True)
        for check in sorted_checks[:5]:
            elem_id = check['element_id']
            elem_type = check['element_type']
            dcr_max = check['DCR_max']
            damage = check.get('damage_level', 'Unknown')
            verified = "✓" if check['verified'] else "✗"
            print(f"  {elem_id:3d} |  {elem_type:8s} | {dcr_max:7.3f}   |  {damage:15s} {verified}")

    print("\n" + "="*70)
    print("Analisi completata")
    print("="*70)


if __name__ == '__main__':
    main()
