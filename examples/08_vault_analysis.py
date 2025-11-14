"""
MURATURA FEM - Vault Analysis Examples
Esempi analisi volte in muratura - Metodo Heyman

Questo script dimostra l'uso del modulo vaults per l'analisi di volte storiche
in muratura secondo il metodo di analisi limite di Heyman.

Esempi:
1. Volta a botte (barrel vault) - Cantina romana
2. Cupola emisferica (dome) - Pantheon style
3. Volta a crociera (cross vault) - Cattedrale gotica
4. Cupola con riempimento - Scenario reale edificio storico
"""

from Material.analyses.historic.vaults import (
    VaultAnalysis,
    VaultGeometry,
    MASONRY_DENSITIES
)


def print_header(title: str):
    """Stampa intestazione esempio"""
    print("\n" + "=" * 70)
    print(f"ESEMPIO: {title}")
    print("=" * 70)


def main():
    print("🏛️  MURATURA FEM v6.4 - Vault Analysis Module (Heyman Method)")
    print("=" * 70)

    # ========================================================================
    # ESEMPIO 1: Volta a Botte - Cantina Romana
    # ========================================================================
    print_header("Volta a Botte - Cantina Romana")
    print("\nGeometria:")
    print("  Luce: 6.0 m")
    print("  Freccia: 3.0 m (semicircolare)")
    print("  Lunghezza: 12.0 m")
    print("  Spessore: 0.40 m")
    print("  Materiale: Pietra naturale (γ = 22 kN/m³)")
    print()

    geometry_barrel = VaultGeometry(
        vault_type='barrel',
        span=6.0,  # m
        rise=3.0,  # m
        length=12.0,  # m
        thickness=0.40  # m
    )

    vault_barrel = VaultAnalysis(
        geometry=geometry_barrel,
        masonry_density=MASONRY_DENSITIES['stone']
    )

    # Genera report
    report = vault_barrel.generate_report()
    print(report)

    # Informazioni addizionali
    safety = vault_barrel.calculate_safety_factor()
    print(f"📊 Volta a botte FS = {safety['geometric_safety_factor']:.2f}")
    print(f"   t/R ratio = {safety['t_to_R_ratio']:.4f}")
    print()

    # ========================================================================
    # ESEMPIO 2: Cupola Emisferica - Stile Pantheon
    # ========================================================================
    print_header("Cupola Emisferica - Stile Pantheon")
    print("\nGeometria:")
    print("  Diametro: 10.0 m")
    print("  Freccia: 5.0 m (emisferica)")
    print("  Spessore: 0.60 m")
    print("  Angolo apertura: 90° (emisfero)")
    print("  Materiale: Calcestruzzo romano (γ = 20 kN/m³)")
    print()

    geometry_dome = VaultGeometry(
        vault_type='dome',
        span=10.0,  # m (diametro)
        rise=5.0,  # m
        thickness=0.60,  # m
        opening_angle=90.0  # gradi (emisfero completo)
    )

    vault_dome = VaultAnalysis(
        geometry=geometry_dome,
        masonry_density=20.0  # Calcestruzzo romano
    )

    report = vault_dome.generate_report()
    print(report)

    safety = vault_dome.calculate_safety_factor()
    print(f"📊 Cupola emisferica FS = {safety['geometric_safety_factor']:.2f}")
    print(f"   t/R ratio = {safety['t_to_R_ratio']:.4f}")
    print(f"   (Pantheon reale: D=43.3m, t=1.2-6.0m variabile)")
    print()

    # ========================================================================
    # ESEMPIO 3: Volta a Crociera - Cattedrale Gotica
    # ========================================================================
    print_header("Volta a Crociera - Cattedrale Gotica")
    print("\nGeometria:")
    print("  Luce: 8.0 m")
    print("  Freccia: 4.5 m")
    print("  Lunghezza: 10.0 m")
    print("  Spessore: 0.35 m")
    print("  Materiale: Pietra calcarea (γ = 22 kN/m³)")
    print()

    geometry_cross = VaultGeometry(
        vault_type='cross',
        span=8.0,  # m
        rise=4.5,  # m
        length=10.0,  # m
        thickness=0.35  # m
    )

    vault_cross = VaultAnalysis(
        geometry=geometry_cross,
        masonry_density=MASONRY_DENSITIES['limestone']
    )

    report = vault_cross.generate_report()
    print(report)

    safety = vault_cross.calculate_safety_factor()
    print(f"📊 Volta a crociera FS = {safety['geometric_safety_factor']:.2f}")
    print(f"   Volte a crociera sono più stabili delle barrel vaults")
    print(f"   grazie all'effetto arco incrociato 3D")
    print()

    # ========================================================================
    # ESEMPIO 4: Cupola con Riempimento - Scenario Reale
    # ========================================================================
    print_header("Cupola Ribassata con Riempimento - Edificio Storico")
    print("\nGeometria:")
    print("  Diametro: 6.0 m")
    print("  Freccia: 2.5 m (ribassata)")
    print("  Spessore: 0.30 m")
    print("  Angolo apertura: 60° (ribassata)")
    print("  Riempimento: h = 0.80 m, γ = 16 kN/m³")
    print("  Sovraccarico: 1.5 kN/m² (calpestio)")
    print("  Materiale: Mattoni pieni (γ = 18 kN/m³)")
    print()

    geometry_dome_fill = VaultGeometry(
        vault_type='dome',
        span=6.0,  # m
        rise=2.5,  # m
        thickness=0.30,  # m
        opening_angle=60.0  # gradi (ribassata)
    )

    vault_dome_fill = VaultAnalysis(
        geometry=geometry_dome_fill,
        masonry_density=MASONRY_DENSITIES['brick'],
        fill_height=0.80,  # m
        fill_density=16.0,  # kN/m³ (terra, detriti)
        live_load=1.5  # kN/m² (calpestio)
    )

    report = vault_dome_fill.generate_report()
    print(report)

    safety = vault_dome_fill.calculate_safety_factor()
    seismic = vault_dome_fill.calculate_seismic_capacity()

    print(f"📊 Cupola con riempimento FS = {safety['geometric_safety_factor']:.2f}")
    print(f"   Riempimento riduce significativamente il margine di sicurezza")
    print(f"   Capacità sismica: ag = {seismic['ag_capacity']:.3f}g")

    if safety['verdict'] == 'MARGINALLY_SAFE' or safety['verdict'] == 'UNSAFE':
        print("\n⚠️  ATTENZIONE: Margine sicurezza insufficiente!")
        print("   Raccomandazioni:")
        print("   - Rimozione riempimento se possibile")
        print("   - Rinforzi con FRP/FRCM")
        print("   - Monitoraggio strutturale")
        print("   - Limitazione carichi accidentali")
    print()

    # ========================================================================
    # RIEPILOGO COMPARATIVO
    # ========================================================================
    print("=" * 70)
    print("RIEPILOGO COMPARATIVO")
    print("=" * 70)
    print()
    print(f"{'Tipologia':<25} {'FS':<10} {'t/R':<10} {'Esito':<15}")
    print("-" * 70)

    examples = [
        ("Volta a botte", vault_barrel.calculate_safety_factor()),
        ("Cupola emisferica", vault_dome.calculate_safety_factor()),
        ("Volta a crociera", vault_cross.calculate_safety_factor()),
        ("Cupola con riempimento", vault_dome_fill.calculate_safety_factor()),
    ]

    for name, result in examples:
        FS = result['geometric_safety_factor']
        t_R = result['t_to_R_ratio']
        verdict = result['verdict']
        print(f"{name:<25} {FS:<10.2f} {t_R:<10.4f} {verdict:<15}")

    print()
    print("=" * 70)
    print("✅ Esempi completati!")
    print("=" * 70)
    print()
    print("🎯 FASE 2: Moduli implementati")
    print("   ✅ Archi (arches)")
    print("   ✅ Volte (vaults)")
    print("   🔄 Rinforzi (TODO)")
    print("   🔄 Knowledge Levels (TODO)")
    print()
    print("📚 Bibliografia:")
    print("   - Heyman, J. (1977) 'Equilibrium of shell structures'")
    print("   - Heyman, J. (1995) 'The stone skeleton'")
    print("   - Huerta, S. (2001) 'Mechanics of masonry vaults'")
    print("   - Block, P. (2009) 'Thrust network analysis'")
    print()


if __name__ == "__main__":
    main()
