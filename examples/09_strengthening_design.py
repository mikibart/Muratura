"""
MURATURA FEM - Strengthening Design Examples
Esempi progettazione rinforzi FRP/FRCM per edifici storici

Questo script dimostra l'uso del modulo strengthening per la progettazione
di interventi di consolidamento su edifici storici in muratura.

Normativa:
- CNR-DT 200 R1/2013 (FRP)
- CNR-DT 215/2018 (FRCM)

Esempi:
1. Rinforzo arco con CFRP (estradosso)
2. Rinforzo arco con C-FRCM (più compatibile per Beni Culturali)
3. Cerchiatura cupola con CFRP
4. Rinforzo volta a botte con GFRP
5. Confronto materiali (CFRP vs FRCM)
"""

from Material.analyses.historic.strengthening import (
    StrengtheningDesign,
    FRPMaterial,
    MasonryProperties,
    ApplicationType,
    MATERIAL_DATABASE
)


def print_header(title: str):
    """Stampa intestazione esempio"""
    print("\n" + "=" * 70)
    print(f"ESEMPIO: {title}")
    print("=" * 70)


def main():
    print("🏛️  MURATURA FEM v6.4 - Strengthening Design Module")
    print("="* 70)
    print("Normativa: CNR-DT 200 R1/2013 (FRP), CNR-DT 215/2018 (FRCM)")
    print("=" * 70)

    # ========================================================================
    # ESEMPIO 1: Rinforzo Arco con CFRP Alto Modulo
    # ========================================================================
    print_header("Rinforzo Arco Storico con CFRP (Estradosso)")
    print("\nSce nario:")
    print("  Arco in muratura di mattoni, luce 4.0m, rise 2.0m")
    print("  Fessurazioni all'intradosso (trazione)")
    print("  Intervento: Rinforzo estradosso con CFRP alto modulo")
    print("  Applicazione: 2 strati continui, larghezza 1.0m")
    print()

    # Materiale CFRP da database
    cfrp_hm = FRPMaterial.from_database('CFRP_HM')

    # Proprietà muratura (mattoni, qualità media)
    masonry_brick = MasonryProperties(
        compressive_strength=2.5,  # MPa
        tensile_strength=0.1,  # MPa
        elastic_modulus=1500  # MPa
    )

    # Progetto rinforzo
    design_arch_cfrp = StrengtheningDesign(
        application_type=ApplicationType.ARCH_EXTRADOS,
        material=cfrp_hm,
        masonry=masonry_brick,
        width=1.0,  # m
        n_layers=2
    )

    # Genera report
    report = design_arch_cfrp.generate_report(original_capacity=15.0)  # 15 kN capacità originale
    print(report)

    # ========================================================================
    # ESEMPIO 2: Rinforzo Arco con C-FRCM (Beni Culturali)
    # ========================================================================
    print_header("Rinforzo Arco Vincolato (C-FRCM)")
    print("\nScenario:")
    print("  Arco in edificio vincolato Soprintendenza")
    print("  Necessità materiale compatibile e reversibile")
    print("  Intervento: Rinforzo intradosso con C-FRCM")
    print("  Vantaggio: Traspirante, reversibile, minimo impatto estetico")
    print()

    # Materiale C-FRCM da database
    c_frcm = FRPMaterial.from_database('C_FRCM')

    # Muratura pietra (edificio storico)
    masonry_stone = MasonryProperties(
        compressive_strength=3.0,  # MPa
        tensile_strength=0.15,  # MPa
        elastic_modulus=1800  # MPa
    )

    # Progetto rinforzo
    design_arch_frcm = StrengtheningDesign(
        application_type=ApplicationType.ARCH_INTRADOS,
        material=c_frcm,
        masonry=masonry_stone,
        width=1.0,  # m
        n_layers=3  # 3 strati FRCM
    )

    report = design_arch_frcm.generate_report(original_capacity=18.0)
    print(report)

    print("📊 CONFRONTO CFRP vs C-FRCM per archi:")
    cap_cfrp = design_arch_cfrp.calculate_capacity_increase(original_capacity=15.0)
    cap_frcm = design_arch_frcm.calculate_capacity_increase(original_capacity=18.0)

    print(f"  CFRP (2 strati):   +{cap_cfrp['capacity_increase_percent']:.1f}%")
    print(f"  C-FRCM (3 strati): +{cap_frcm['capacity_increase_percent']:.1f}%")
    print()
    print("  Note:")
    print("  - CFRP: Maggiore incremento, ma non reversibile")
    print("  - FRCM: Compatibile Beni Culturali, traspirante, reversibile")
    print("  - Per edifici vincolati: preferire FRCM")
    print()

    # ========================================================================
    # ESEMPIO 3: Cerchiatura Cupola con CFRP
    # ========================================================================
    print_header("Cerchiatura Cupola con CFRP")
    print("\nScenario:")
    print("  Cupola emisferica D=8.0m, fessurazioni meridiane")
    print("  Causa: Trazione negli anelli inferiori")
    print("  Intervento: Cerchiatura con strisce CFRP")
    print("  Applicazione: 3 anelli di rinforzo all'estradosso")
    print()

    # CFRP alta resistenza per cerchiature
    cfrp_hs = FRPMaterial.from_database('CFRP_HS')

    # Muratura tufo (cupola napoletana)
    masonry_tuff = MasonryProperties(
        compressive_strength=1.8,  # MPa (tufo)
        tensile_strength=0.08,  # MPa
        elastic_modulus=1200  # MPa
    )

    # Progetto cerchiatura
    design_dome = StrengtheningDesign(
        application_type=ApplicationType.DOME_RING,
        material=cfrp_hs,
        masonry=masonry_tuff,
        width=0.50,  # m (larghezza striscia)
        n_layers=2
    )

    report = design_dome.generate_report()
    print(report)

    print("📊 Cerchiature multiple:")
    print("  Si consigliano 3 anelli di cerchiatura:")
    print("  - Anello 1: All'imposta (più critico)")
    print("  - Anello 2: A 1/3 altezza")
    print("  - Anello 3: A 2/3 altezza")
    print()

    # ========================================================================
    # ESEMPIO 4: Rinforzo Volta a Botte con GFRP (Economico)
    # ========================================================================
    print_header("Rinforzo Volta a Botte con GFRP (Soluzione Economica)")
    print("\nScenario:")
    print("  Volta a botte cantina, L=6.0m, span=4.0m")
    print("  Budget limitato, non vincolata")
    print("  Intervento: Rinforzo estradosso con GFRP")
    print("  Vantaggio: Economico, efficace per carichi moderati")
    print()

    # GFRP (economico)
    gfrp = FRPMaterial.from_database('GFRP')

    # Muratura mattoni
    design_vault_gfrp = StrengtheningDesign(
        application_type=ApplicationType.VAULT_EXTRADOS,
        material=gfrp,
        masonry=masonry_brick,
        width=6.0,  # m (lunghezza volta)
        n_layers=2
    )

    report = design_vault_gfrp.generate_report(original_capacity=80.0)
    print(report)

    # ========================================================================
    # ESEMPIO 5: Confronto Economico Materiali
    # ========================================================================
    print_header("Confronto Materiali per Rinforzo")

    print("\nCaratteristiche materiali:")
    print()
    print(f"{'Materiale':<15} {'f_fk [MPa]':<12} {'E_f [GPa]':<12} {'ε_fu':<10} {'Costo':<12}")
    print("-" * 70)

    materials_comparison = [
        ('CFRP_HM', 'Alto'),
        ('CFRP_HS', 'Alto'),
        ('AFRP', 'Medio-Alto'),
        ('GFRP', 'Basso'),
        ('C_FRCM', 'Medio'),
        ('G_FRCM', 'Basso')
    ]

    for mat_name, cost in materials_comparison:
        data = MATERIAL_DATABASE[mat_name]
        f_fk = data['tensile_strength']
        E_f = data['elastic_modulus'] / 1000  # GPa
        eps_fu = data['ultimate_strain']

        print(f"{mat_name:<15} {f_fk:<12.0f} {E_f:<12.0f} {eps_fu:<10.3f} {cost:<12}")

    print()
    print("Raccomandazioni:")
    print()
    print("  🏛️  EDIFICI VINCOLATI (Soprintendenza):")
    print("      → C-FRCM o G-FRCM (compatibili, reversibili)")
    print()
    print("  💰 BUDGET LIMITATO:")
    print("      → GFRP o G-FRCM (economici)")
    print()
    print("  ⚡ ALTA PERFORMANCE:")
    print("      → CFRP alto modulo o alta resistenza")
    print()
    print("  🔨 APPLICAZIONE SEMPLICE:")
    print("      → FRCM (malta inorganica, traspirante)")
    print()

    # ========================================================================
    # RIEPILOGO
    # ========================================================================
    print("=" * 70)
    print("RIEPILOGO RINFORZI")
    print("=" * 70)
    print()

    examples = [
        ("Arco CFRP", design_arch_cfrp, 15.0),
        ("Arco C-FRCM", design_arch_frcm, 18.0),
        ("Cupola CFRP HS", design_dome, None),
        ("Volta GFRP", design_vault_gfrp, 80.0)
    ]

    print(f"{'Applicazione':<20} {'Materiale':<12} {'F_fd [kN/m]':<15} {'Incremento':<15}")
    print("-" * 70)

    for name, design, orig_cap in examples:
        mat = design.material.material_type
        strength = design.calculate_design_strength()
        F_fd = strength['F_fd']

        if orig_cap:
            cap = design.calculate_capacity_increase(orig_cap)
            inc = f"+{cap['capacity_increase_percent']:.1f}%"
        else:
            inc = "N/A"

        print(f"{name:<20} {mat:<12} {F_fd:<15.2f} {inc:<15}")

    print()
    print("=" * 70)
    print("✅ Esempi completati!")
    print("=" * 70)
    print()
    print("🎯 FASE 2: Moduli implementati")
    print("   ✅ Archi (arches)")
    print("   ✅ Volte (vaults)")
    print("   ✅ Rinforzi (strengthening)")
    print("   🔄 Knowledge Levels (TODO)")
    print()
    print("📚 Normativa:")
    print("   - CNR-DT 200 R1/2013: FRP")
    print("   - CNR-DT 215/2018: FRCM")
    print("   - NTC 2018 Cap. 8: Costruzioni esistenti")
    print("   - Linee Guida Beni Culturali 2011")
    print()


if __name__ == "__main__":
    main()
