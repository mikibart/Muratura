"""
MURATURA FEM - Knowledge Levels Examples
Esempi valutazione livelli di conoscenza edifici esistenti

Questo script dimostra l'uso del modulo knowledge_levels per la valutazione
del livello di conoscenza (LC) e fattore di confidenza (FC) secondo NTC 2018.

Normativa:
- NTC 2018 §8.5.4
- Circolare NTC 2019 §C8.5.4
- Linee Guida Beni Culturali 2011

Esempi:
1. LC1 - Conoscenza Limitata (FC=1.35)
2. LC2 - Conoscenza Adeguata (FC=1.20)
3. LC3 - Conoscenza Accurata (FC=1.00)
4. Applicazione FC a proprietà materiali
5. Comparazione impatto FC su verifiche
"""

from Material.analyses.historic.knowledge_levels import (
    KnowledgeAssessment,
    KnowledgeLevel,
    MaterialProperties,
    CONFIDENCE_FACTORS
)


def print_header(title: str):
    """Stampa intestazione esempio"""
    print("\n" + "=" * 70)
    print(f"ESEMPIO: {title}")
    print("=" * 70)


def main():
    print("🏛️  MURATURA FEM v6.4 - Knowledge Levels Module")
    print("=" * 70)
    print("Normativa: NTC 2018 §8.5.4, Circolare §C8.5.4")
    print("=" * 70)

    # ========================================================================
    # ESEMPIO 1: LC1 - Conoscenza Limitata
    # ========================================================================
    print_header("LC1 - Conoscenza Limitata (FC = 1.35)")
    print("\nScenario:")
    print("  Edificio storico, prima valutazione")
    print("  Indagini disponibili:")
    print("  - Geometria: Planimetrie catastali, sopralluogo sommario")
    print("  - Dettagli: Ispezione visiva limitata")
    print("  - Materiali: Dati bibliografici, nessuna prova in situ")
    print()

    assessment_lc1 = KnowledgeAssessment(
        building_type='masonry',
        construction_period='1800-1850'
    )

    # Imposta livelli indagine
    assessment_lc1.set_geometry_investigation('limited')
    assessment_lc1.set_details_investigation('limited')
    assessment_lc1.set_materials_investigation('limited')

    # Genera report
    report = assessment_lc1.generate_report()
    print(report)

    # ========================================================================
    # ESEMPIO 2: LC2 - Conoscenza Adeguata
    # ========================================================================
    print_header("LC2 - Conoscenza Adeguata (FC = 1.20)")
    print("\nScenario:")
    print("  Edificio storico, campagna indagini standard")
    print("  Indagini disponibili:")
    print("  - Geometria: Rilievo completo verificato in situ")
    print("  - Dettagli: Saggi su collegamenti e dettagli costruttivi")
    print("  - Materiali: Prove martinetti piatti + dati bibliografici")
    print()

    assessment_lc2 = KnowledgeAssessment(
        building_type='masonry',
        construction_period='1800-1850'
    )

    assessment_lc2.set_geometry_investigation('extended')
    assessment_lc2.set_details_investigation('extended')
    assessment_lc2.set_materials_investigation('extended')

    report = assessment_lc2.generate_report()
    print(report)

    # ========================================================================
    # ESEMPIO 3: LC3 - Conoscenza Accurata
    # ========================================================================
    print_header("LC3 - Conoscenza Accurata (FC = 1.00)")
    print("\nScenario:")
    print("  Edificio monumentale, campagna indagini estesa")
    print("  Indagini disponibili:")
    print("  - Geometria: Rilievo laser scanner + apertura saggi")
    print("  - Dettagli: Saggi estesi + prove in situ su collegamenti")
    print("  - Materiali: Martinetti + prove lab su campioni rappresentativi")
    print()

    assessment_lc3 = KnowledgeAssessment(
        building_type='masonry',
        construction_period='1600-1700'  # Edificio più antico
    )

    assessment_lc3.set_geometry_investigation('exhaustive')
    assessment_lc3.set_details_investigation('exhaustive')
    assessment_lc3.set_materials_investigation('exhaustive')

    report = assessment_lc3.generate_report()
    print(report)

    # ========================================================================
    # ESEMPIO 4: Applicazione FC a Proprietà Materiali
    # ========================================================================
    print_header("Applicazione Fattore di Confidenza a Materiali")
    print("\nScenario:")
    print("  Muratura in mattoni pieni e malta di calce")
    print("  Resistenze caratteristiche da prove:")
    print("  - f_m,k = 2.4 MPa (compressione)")
    print("  - τ_0,k = 0.06 MPa (taglio puro)")
    print()

    # Proprietà materiale caratteristiche
    masonry = MaterialProperties(
        f_m_k=2.4,  # MPa
        f_v0_k=0.12,  # MPa
        tau_0_k=0.06,  # MPa
        E=1500,  # MPa
        w=18.0  # kN/m³
    )

    print(f"{'Livello':<10} {'FC':<8} {'f_m,d [MPa]':<15} {'τ_0,d [MPa]':<15} {'Riduzione':<12}")
    print("-" * 70)

    for level, FC in CONFIDENCE_FACTORS.items():
        reduced = masonry.apply_confidence_factor(FC)
        reduction = (1 - reduced.f_m_k / masonry.f_m_k) * 100

        print(f"{level.value:<10} {FC:<8.2f} {reduced.f_m_k:<15.3f} "
              f"{reduced.tau_0_k:<15.4f} {reduction:<12.1f}%")

    print()
    print("Note:")
    print("  - Il modulo elastico E non è ridotto dal FC")
    print("  - La riduzione influenza direttamente le verifiche strutturali")
    print("  - Per LC1: riduzione del 35% rispetto a LC3")
    print("  - Per LC2: riduzione del 20% rispetto a LC3")
    print()

    # ========================================================================
    # ESEMPIO 5: Caso Reale - Miglioramento Livello Conoscenza
    # ========================================================================
    print_header("Caso Reale - Miglioramento Progressivo LC")
    print("\nScenario:")
    print("  Palazzo storico vincolato, necessità adeguamento sismico")
    print("  Valutazione progressiva con campagna indagini")
    print()

    # Fase 1: Prima valutazione (solo documenti)
    print("FASE 1: Valutazione preliminare (solo documenti storici)")
    print("-" * 70)

    assessment_fase1 = KnowledgeAssessment(
        building_type='masonry',
        construction_period='1700-1750'
    )
    assessment_fase1.set_geometry_investigation('limited')
    assessment_fase1.set_details_investigation('limited')
    assessment_fase1.set_materials_investigation('limited')

    result_fase1 = assessment_fase1.calculate_knowledge_level()
    print(f"Livello: {result_fase1['level']}, FC = {result_fase1['FC']}")
    print()

    # Fase 2: Dopo rilievo e saggi
    print("FASE 2: Dopo rilievo geometrico e primi saggi")
    print("-" * 70)

    assessment_fase2 = KnowledgeAssessment(
        building_type='masonry',
        construction_period='1700-1750'
    )
    assessment_fase2.set_geometry_investigation('extended')
    assessment_fase2.set_details_investigation('extended')
    assessment_fase2.set_materials_investigation('limited')  # Ancora limitate

    result_fase2 = assessment_fase2.calculate_knowledge_level()
    print(f"Livello: {result_fase2['level']}, FC = {result_fase2['FC']}")

    # Check raccomandazioni
    recs = assessment_fase2.get_investigation_recommendations()
    if recs['materials']:
        print("\nRaccomandazioni per migliorare LC:")
        for rec in recs['materials']:
            print(f"  - {rec}")
    print()

    # Fase 3: Dopo campagna prove completa
    print("FASE 3: Dopo campagna prove completa")
    print("-" * 70)

    assessment_fase3 = KnowledgeAssessment(
        building_type='masonry',
        construction_period='1700-1750'
    )
    assessment_fase3.set_geometry_investigation('extended')
    assessment_fase3.set_details_investigation('extended')
    assessment_fase3.set_materials_investigation('extended')

    result_fase3 = assessment_fase3.calculate_knowledge_level()
    print(f"Livello: {result_fase3['level']}, FC = {result_fase3['FC']}")
    print()

    # Confronto impatto su verifiche
    print("IMPATTO SU VERIFICHE STRUTTURALI:")
    print("-" * 70)

    masonry_example = MaterialProperties(f_m_k=2.0, tau_0_k=0.05)

    print(f"{'Fase':<10} {'LC':<10} {'FC':<8} {'f_m,d [MPa]':<15} {'Miglioramento':<15}")
    print("-" * 70)

    phases = [
        ("Fase 1", result_fase1),
        ("Fase 2", result_fase2),
        ("Fase 3", result_fase3)
    ]

    prev_fm = None
    for phase_name, result in phases:
        FC = result['FC']
        reduced = masonry_example.apply_confidence_factor(FC)
        fm_d = reduced.f_m_k

        if prev_fm is not None:
            improvement = ((fm_d - prev_fm) / prev_fm) * 100
            improvement_str = f"+{improvement:.1f}%"
        else:
            improvement_str = "-"

        print(f"{phase_name:<10} {result['level']:<10} {FC:<8.2f} "
              f"{fm_d:<15.3f} {improvement_str:<15}")

        prev_fm = fm_d

    print()
    print("💡 OSSERVAZIONI:")
    print("  - Da LC1 a LC2: incremento resistenze +12.5%")
    print("  - Da LC2 a LC3: incremento resistenze +20.0%")
    print("  - Da LC1 a LC3: incremento resistenze +35.0%")
    print("  - Investire in indagini può evitare rinforzi strutturali costosi!")
    print()

    # ========================================================================
    # RIEPILOGO
    # ========================================================================
    print("=" * 70)
    print("RIEPILOGO KNOWLEDGE LEVELS")
    print("=" * 70)
    print()
    print(f"{'Livello':<12} {'FC':<8} {'Descrizione':<50}")
    print("-" * 70)

    levels_desc = {
        'LC1': 'Conoscenza Limitata - Indagini minime',
        'LC2': 'Conoscenza Adeguata - Indagini standard',
        'LC3': 'Conoscenza Accurata - Indagini esaustive'
    }

    for level, FC in CONFIDENCE_FACTORS.items():
        desc = levels_desc[level.value]
        print(f"{level.value:<12} {FC:<8.2f} {desc:<50}")

    print()
    print("=" * 70)
    print("✅ Esempi completati!")
    print("=" * 70)
    print()
    print("🎯 FASE 2: COMPLETATA AL 100%!")
    print("   ✅ Archi (arches)")
    print("   ✅ Volte (vaults)")
    print("   ✅ Rinforzi (strengthening)")
    print("   ✅ Knowledge Levels (knowledge_levels)")
    print()
    print("📚 Normativa:")
    print("   - NTC 2018 §8.5.4: Livelli di conoscenza")
    print("   - Circolare NTC 2019 §C8.5.4: Fattori di confidenza")
    print("   - Linee Guida Beni Culturali 2011")
    print()
    print("🎓 Utilizzo:")
    print("   - Valutazione preliminare edifici esistenti")
    print("   - Pianificazione campagne indagini")
    print("   - Ottimizzazione costi indagini vs rinforzi")
    print("   - Documentazione livello conoscenza per progetto")
    print()


if __name__ == "__main__":
    main()
