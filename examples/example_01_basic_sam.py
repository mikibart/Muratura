"""
Esempio 1: Analisi SAM di un maschio murario semplice
======================================================

Questo esempio mostra come eseguire un'analisi SAM (Simplified Analysis of Masonry)
su un maschio murario con geometria e carichi tipici.
"""

from muratura import (
    MaterialProperties,
    MasonryType,
    MortarQuality,
    ConservationState,
    MasonryFEMEngine,
    AnalysisMethod
)


def main():
    print("="*70)
    print("ESEMPIO 1: Analisi SAM Maschio Murario")
    print("="*70)

    # ========================================================================
    # STEP 1: Definisci materiale da database NTC 2018
    # ========================================================================
    print("\n1. Definizione materiale:")
    print("-" * 40)

    material = MaterialProperties.from_ntc_table(
        masonry_type=MasonryType.MATTONI_PIENI,
        mortar_quality=MortarQuality.BUONA,
        conservation=ConservationState.BUONO,
        position='mean'  # 'min', 'mean', o 'max' nell'intervallo NTC
    )

    print(f"Tipo: {material.material_type}")
    print(f"fcm = {material.fcm:.2f} MPa")
    print(f"fvm = {material.fvm:.3f} MPa")
    print(f"E = {material.E:.0f} MPa")
    print(f"G = {material.G:.0f} MPa")
    print(f"Peso = {material.weight:.1f} kN/m³")

    # Validazione materiale
    validation = material.validate()
    print(f"\nMateriale valido: {validation['is_valid']}")
    if validation['warnings']:
        print("Avvisi:")
        for w in validation['warnings']:
            print(f"  - {w}")

    # ========================================================================
    # STEP 2: Definisci geometria maschio murario
    # ========================================================================
    print("\n2. Definizione geometria:")
    print("-" * 40)

    wall_data = {
        'length': 1.2,      # m - larghezza maschio
        'height': 3.0,      # m - altezza maschio
        'thickness': 0.3,   # m - spessore muro
    }

    print(f"Larghezza maschio: {wall_data['length']} m")
    print(f"Altezza maschio: {wall_data['height']} m")
    print(f"Spessore: {wall_data['thickness']} m")

    # Calcola alcune proprietà geometriche
    area = wall_data['length'] * wall_data['thickness']
    slenderness = wall_data['height'] / wall_data['thickness']
    print(f"\nArea sezione: {area:.3f} m²")
    print(f"Snellezza (h/t): {slenderness:.1f}")

    # ========================================================================
    # STEP 3: Definisci i carichi agenti
    # ========================================================================
    print("\n3. Definizione carichi:")
    print("-" * 40)

    loads = {
        'N': -150.0,        # kN - Sforzo normale (negativo = compressione)
        'V': 50.0,          # kN - Taglio
        'M': 75.0           # kNm - Momento flettente
    }

    print(f"Sforzo normale N = {loads['N']:.1f} kN")
    print(f"Taglio V = {loads['V']:.1f} kN")
    print(f"Momento M = {loads['M']:.1f} kNm")

    # Calcola tensioni medie
    sigma_0 = abs(loads['N']) / (area * 1000)  # N/mm² = MPa
    tau_0 = abs(loads['V']) / (area * 1000)    # N/mm² = MPa

    print(f"\nTensione normale media σ₀ = {sigma_0:.2f} MPa")
    print(f"Tensione tangenziale media τ₀ = {tau_0:.3f} MPa")

    # ========================================================================
    # STEP 4: Crea motore di analisi e esegui calcolo
    # ========================================================================
    print("\n4. Analisi strutturale:")
    print("-" * 40)

    engine = MasonryFEMEngine(method=AnalysisMethod.SAM)

    results = engine.analyze_structure(
        wall_data=wall_data,
        material=material,
        loads=loads
    )

    # ========================================================================
    # STEP 5: Visualizza risultati
    # ========================================================================
    print("\n5. RISULTATI ANALISI:")
    print("=" * 70)

    # Risultati principali
    print(f"\nModo di rottura critico: {results.get('failure_mode', 'N/A')}")
    print(f"DCR Flessione: {results.get('DCR_flexure', 0):.3f}")
    print(f"DCR Taglio: {results.get('DCR_shear', 0):.3f}")
    print(f"DCR Massimo: {results.get('DCR_max', 0):.3f}")

    # Interpretazione risultati
    print("\nINTERPRETAZIONE:")
    print("-" * 40)

    verified = results.get('verified', False)
    dcr_max = results.get('DCR_max', 999)

    if verified:
        print("✓ VERIFICA SODDISFATTA")
        if dcr_max < 0.5:
            print("  Elemento fortemente sovradimensionato")
        elif dcr_max < 0.8:
            print("  Elemento con buon margine di sicurezza")
        else:
            print("  Elemento al limite ma verificato")
    else:
        print("✗ VERIFICA NON SODDISFATTA")
        if dcr_max < 1.2:
            print("  Lieve superamento, possibile intervento leggero")
        elif dcr_max < 1.5:
            print("  Superamento moderato, rinforzo necessario")
        else:
            print("  Superamento elevato, rinforzo significativo necessario")

    # Suggerimenti
    if not verified:
        print("\nSUGGERIMENTI:")
        print("-" * 40)
        failure_mode = results.get('failure_mode', '')

        if 'FLEXURE' in failure_mode or 'FLESSIONE' in failure_mode:
            print("  • Considerare rinforzo FRP/FRCM in zona tesa")
            print("  • Valutare iniezioni di malta per migliorare fcm")
        elif 'SHEAR' in failure_mode or 'TAGLIO' in failure_mode:
            print("  • Considerare ristilatura armata dei giunti")
            print("  • Valutare intonaco armato o placcaggio con FRP")
        elif 'CRUSHING' in failure_mode or 'SCHIACCIAMENTO' in failure_mode:
            print("  • Ridurre i carichi verticali se possibile")
            print("  • Considerare cerchiatura o confinamento")

    # Dettagli capacità
    if 'capacity_flexure' in results and 'capacity_shear' in results:
        print("\nCAPACITÀ ELEMENTO:")
        print("-" * 40)
        print(f"Momento resistente: {results['capacity_flexure']:.1f} kNm")
        print(f"Taglio resistente: {results['capacity_shear']:.1f} kN")

    print("\n" + "="*70)
    print("Analisi completata")
    print("="*70)


if __name__ == '__main__':
    main()
