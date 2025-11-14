#!/usr/bin/env python3
"""
Example: Balcony Design and Verification - NTC 2018
====================================================

Dimostra l'utilizzo del modulo balconies per il calcolo e verifica
di balconi a sbalzo secondo NTC 2018.

Scenario:
---------
- Edifici residenziali con balconi
- Tipologie: C.a. a sbalzo, Acciaio (IPE/HEA)
- Verifica CRITICA ancoraggio alla muratura
- Categoria sovraccarico: C (4.0 kN/m²)

⚠️  NOTA: La verifica dell'ancoraggio alla muratura è FONDAMENTALE
    per la sicurezza. Un ancoraggio insufficiente può portare al
    collasso catastrofico del balcone.
"""

import sys
from pathlib import Path

# Add Material module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Material.analyses.balconies import (
    BalconyAnalysis,
    BalconyGeometry,
    BalconyLoads,
    BalconyType
)


def example_1_rc_cantilever_standard():
    """
    Esempio 1: Balcone in c.a. standard (1.5m sbalzo)
    """
    print("\n" + "="*70)
    print("ESEMPIO 1: Balcone C.A. Standard - Sbalzo 1.5m")
    print("="*70)

    # Geometria tipica balcone residenziale
    geometry = BalconyGeometry(
        cantilever_length=1.5,  # Sbalzo 1.5m
        width=1.2,  # Larghezza 1.2m
        thickness=0.15,  # Soletta 15cm
        parapet_height=1.00,  # Parapetto 1.0m (minimo)
        parapet_weight=0.5,  # Ringhiera leggera in acciaio [kN/m]
        wall_thickness=0.40  # Muro portante 40cm
    )

    # Carichi
    loads = BalconyLoads(
        permanent_loads=1.5,  # Pavimento + impermeabilizzazione [kN/m²]
        live_loads=4.0,  # Cat. C - balconi [kN/m²]
        wind_pressure=0.8  # Pressione vento su parapetto [kN/m²]
    )

    # Analisi balcone
    balcony = BalconyAnalysis(
        balcony_type='rc_cantilever',
        geometry=geometry,
        concrete_class='C25/30',
        steel_class='B450C',
        loads=loads
    )

    # Report completo
    report = balcony.generate_report(wall_fcm=4.0)  # Muratura fcm=4 MPa
    print(report)

    # Dettagli armature
    verification = balcony.verify_cantilever(wall_fcm=4.0)
    if 'reinforcement' in verification:
        reinf = verification['reinforcement']
        print(f"\n📐 DETTAGLIO ARMATURA:")
        print(f"   Superiore (incastro): {reinf['As_top']:.2f} cm²/m")
        print(f"   → φ{reinf['phi']:.0f} ogni {reinf['spacing']:.0f} cm")
        print(f"   Inferiore (costruttiva): {reinf['As_bottom']:.2f} cm²/m")

    # Warning se ancoraggio critico
    anc = verification['anchorage']
    if not anc['anchorage_verified']:
        print(f"\n⚠️  ATTENZIONE CRITICA!")
        print(f"   Ancoraggio insufficiente: serve {anc['anchorage_length_required']:.2f}m")
        print(f"   Disponibile solo: {anc['anchorage_length_available']:.2f}m")
        print(f"   → Aumentare spessore muro o ridurre sbalzo")

    return balcony


def example_2_long_cantilever():
    """
    Esempio 2: Balcone con sbalzo lungo (2.0m) - Critico
    """
    print("\n" + "="*70)
    print("ESEMPIO 2: Balcone C.A. - Sbalzo Lungo 2.0m (CRITICO)")
    print("="*70)

    geometry = BalconyGeometry(
        cantilever_length=2.0,  # Sbalzo 2.0m - LUNGO!
        width=1.0,
        thickness=0.18,  # Soletta più spessa
        parapet_height=1.00,
        parapet_weight=0.6,  # Parapetto più pesante
        wall_thickness=0.50  # Muro più spesso necessario
    )

    loads = BalconyLoads(
        permanent_loads=2.0,  # Pavimento pesante
        live_loads=4.0,
        wind_pressure=1.0  # Vento maggiore (esposizione)
    )

    balcony = BalconyAnalysis(
        balcony_type='rc_cantilever',
        geometry=geometry,
        concrete_class='C28/35',  # Classe superiore
        steel_class='B450C',
        loads=loads
    )

    report = balcony.generate_report(wall_fcm=4.0)
    print(report)

    # Analisi deformabilità (sbalzi lunghi)
    moments = balcony.calculate_moments()
    print(f"\n📊 ANALISI SBALZO LUNGO:")
    print(f"   Momento incastro: {moments['M_cantilever']:.2f} kNm/m")
    print(f"   Carico SLU: {moments['q_slu']:.2f} kN/m²")
    print(f"   → Sbalzi > 1.8m richiedono attenzione a deformabilità")

    return balcony


def example_3_steel_balcony_ipe():
    """
    Esempio 3: Balcone in acciaio con profilati IPE
    """
    print("\n" + "="*70)
    print("ESEMPIO 3: Balcone Acciaio - Profilati IPE180")
    print("="*70)

    geometry = BalconyGeometry(
        cantilever_length=1.8,  # Sbalzo 1.8m
        width=1.5,  # Larghezza maggiore
        thickness=0.05,  # Solo grigliato (no soletta)
        parapet_height=1.00,
        parapet_weight=0.4,  # Ringhiera leggera
        wall_thickness=0.40
    )

    loads = BalconyLoads(
        permanent_loads=0.5,  # Solo grigliato (leggero)
        live_loads=4.0,
        wind_pressure=0.8
    )

    balcony = BalconyAnalysis(
        balcony_type='steel',
        geometry=geometry,
        structural_steel_class='S275',
        steel_profile='IPE180',  # Specifica profilato
        loads=loads
    )

    report = balcony.generate_report(wall_fcm=4.0)
    print(report)

    # Dettagli profilato
    verification = balcony.verify_cantilever(wall_fcm=4.0)
    if 'steel_check' in verification:
        steel = verification['steel_check']
        print(f"\n🔩 DETTAGLIO PROFILATO:")
        print(f"   Profilato: {steel['profile']}")
        print(f"   Numero: {steel['n_profiles']} profilati")
        print(f"   Spaziatura: ~{geometry.width/(steel['n_profiles']-1):.2f}m" if steel['n_profiles'] > 1 else "   Singolo profilato centrale")
        print(f"   M_rd = {steel['M_rd']:.2f} kNm per profilato")
        print(f"   Utilizzo flessione: {steel['flexure_ratio']:.1%}")

    return balcony


def example_4_steel_balcony_hea():
    """
    Esempio 4: Balcone acciaio con HEA (maggiore rigidezza)
    """
    print("\n" + "="*70)
    print("ESEMPIO 4: Balcone Acciaio - Profilati HEA160")
    print("="*70)

    geometry = BalconyGeometry(
        cantilever_length=2.0,  # Sbalzo lungo
        width=2.0,  # Balcone largo
        thickness=0.08,  # Soletta collaborante 8cm
        parapet_height=1.10,
        parapet_weight=0.8,  # Parapetto muratura/vetro
        wall_thickness=0.45
    )

    loads = BalconyLoads(
        permanent_loads=2.5,  # Soletta + pavimento
        live_loads=4.0,
        wind_pressure=1.0
    )

    balcony = BalconyAnalysis(
        balcony_type='steel',
        geometry=geometry,
        structural_steel_class='S275',
        steel_profile='HEA160',
        loads=loads
    )

    report = balcony.generate_report(wall_fcm=4.0)
    print(report)

    # Confronto con IPE
    print(f"\n📊 HEA vs IPE:")
    print(f"   HEA160: h=152mm, Wel=220 cm³, peso=30.4 kg/m")
    print(f"   IPE180: h=180mm, Wel=146 cm³, peso=18.8 kg/m")
    print(f"   → HEA: maggiore rigidezza (+50% Wel), più pesante (+62%)")

    return balcony


def example_5_anchorage_failure_case():
    """
    Esempio 5: Caso di ancoraggio insufficiente (didattico)
    """
    print("\n" + "="*70)
    print("ESEMPIO 5: CASO DIDATTICO - Ancoraggio Insufficiente ⚠️")
    print("="*70)

    # Configurazione CRITICA: muro sottile, sbalzo lungo
    geometry = BalconyGeometry(
        cantilever_length=1.8,
        width=1.2,
        thickness=0.15,
        parapet_height=1.00,
        parapet_weight=0.5,
        wall_thickness=0.25  # MURO SOTTILE! (inadeguato)
    )

    loads = BalconyLoads(
        permanent_loads=1.5,
        live_loads=4.0
    )

    balcony = BalconyAnalysis(
        balcony_type='rc_cantilever',
        geometry=geometry,
        concrete_class='C25/30',
        steel_class='B450C',
        loads=loads
    )

    print("\n⚠️  SCENARIO: Muro portante sottile (25cm) con balcone 1.8m")
    print("   Questo è un caso tipico di RISCHIO in edifici esistenti!\n")

    verification = balcony.verify_cantilever(wall_fcm=3.5)  # Muratura debole
    anc = verification['anchorage']

    print(f"VERIFICA ANCORAGGIO:")
    print(f"  Richiesto: {anc['anchorage_length_required']:.2f}m dentro al muro")
    print(f"  Disponibile: {anc['anchorage_length_available']:.2f}m (2/3 × 0.25m)")
    print(f"  Tensione: τ = {anc['anchorage_stress']:.2f} MPa")
    print(f"  Limite: τ_adm = {anc['anchorage_stress_limit']:.2f} MPa")
    print(f"  RAPPORTO: {anc['anchorage_stress']/anc['anchorage_stress_limit']:.1f}× SOPRA IL LIMITE")

    print(f"\n❌ ESITO: {'ANCORAGGIO NON VERIFICATO' if not anc['anchorage_verified'] else 'OK'}")

    if not anc['anchorage_verified']:
        print(f"\n💡 SOLUZIONI POSSIBILI:")
        print(f"   1. Aumentare spessore muro a ≥ {anc['anchorage_length_required']/0.67:.2f}m")
        print(f"   2. Ridurre sbalzo balcone a ~1.2m")
        print(f"   3. Inserire tiranti metallici attraversanti")
        print(f"   4. Rinforzo con FRP/FRCM estradosso muro")
        print(f"   5. Aggiungere mensole metalliche di supporto")

    return balcony


def example_6_existing_building_assessment():
    """
    Esempio 6: Valutazione balconi esistenti (vulnerabilità)
    """
    print("\n" + "="*70)
    print("ESEMPIO 6: Valutazione Balconi Esistenti - Vulnerabilità Sismica")
    print("="*70)

    # Configurazione tipica edificio anni '60-'70
    geometry = BalconyGeometry(
        cantilever_length=1.6,
        width=1.0,
        thickness=0.12,  # Solette sottili epoca
        parapet_height=1.00,
        parapet_weight=1.2,  # Parapetto muratura (pesante)
        wall_thickness=0.35  # Muro doppia fodera
    )

    # Carichi (considera degrado)
    loads = BalconyLoads(
        permanent_loads=2.0,  # Pavimento + strati
        live_loads=4.0,
        wind_pressure=0.8
    )

    balcony = BalconyAnalysis(
        balcony_type='rc_cantilever',
        geometry=geometry,
        concrete_class='C20/25',  # Cls epoca (bassa classe)
        steel_class='B450A',  # Acciaio liscio equivalente
        loads=loads
    )

    print("\nCONTESTO: Edificio anni '60-'70")
    print("  - Calcestruzzo C20/25 (tipico epoca)")
    print("  - Soletta sottile (12cm)")
    print("  - Parapetto muratura (pesante)")
    print("  - Possibile degrado armature (carbonatazione)\n")

    verification = balcony.verify_cantilever(wall_fcm=2.5)  # Muratura debole

    moments = verification['moments']
    anc = verification['anchorage']

    print(f"RISULTATI VALUTAZIONE:")
    print(f"  Momento incastro: {moments['M_cantilever']:.2f} kNm/m")
    print(f"  Ancoraggio verificato: {'SI ✓' if anc['anchorage_verified'] else 'NO ✗'}")
    print(f"  Safety factor ancoraggio: {anc['safety_factor']:.2f}")

    if anc['safety_factor'] < 1.5:
        print(f"\n⚠️  VULNERABILITÀ SISMICA:")
        print(f"   Safety factor basso ({anc['safety_factor']:.2f} < 1.5)")
        print(f"   Rischio distacco in caso di sisma")
        print(f"   → INTERVENTO PRIORITARIO DI MESSA IN SICUREZZA")
    elif anc['safety_factor'] < 2.0:
        print(f"\n⚠️  ATTENZIONE:")
        print(f"   Safety factor moderato ({anc['safety_factor']:.2f})")
        print(f"   Monitorare stato conservazione")
        print(f"   Considerare rinforzi preventivi")
    else:
        print(f"\n✓ Ancoraggio adeguato (FS={anc['safety_factor']:.2f})")

    return balcony


def comparison_table():
    """
    Tabella comparativa diverse configurazioni
    """
    print("\n" + "="*70)
    print("TABELLA COMPARATIVA - Configurazioni Balconi")
    print("="*70)

    configs = [
        ("C.A. L=1.5m std", 'rc_cantilever', 1.5, 0.15, None, 0.40),
        ("C.A. L=2.0m lungo", 'rc_cantilever', 2.0, 0.18, None, 0.50),
        ("Acciaio IPE180", 'steel', 1.8, 0.05, 'IPE180', 0.40),
        ("Acciaio HEA160", 'steel', 2.0, 0.08, 'HEA160', 0.45),
    ]

    print(f"\n{'Config':<20} {'Tipo':<15} {'L[m]':<8} {'h[cm]':<8} {'Ancor.[m]':<12} {'FS':<8} {'Esito':<8}")
    print("-" * 88)

    for name, bal_type, length, thickness, profile, wall_thick in configs:
        geometry = BalconyGeometry(
            cantilever_length=length,
            width=1.2,
            thickness=thickness,
            wall_thickness=wall_thick
        )

        balcony = BalconyAnalysis(
            balcony_type=bal_type,
            geometry=geometry,
            steel_profile=profile if profile else None
        )

        verification = balcony.verify_cantilever(wall_fcm=4.0)
        anc = verification['anchorage']

        esito = "✓ OK" if verification['overall_verified'] else "✗ NO"

        print(f"{name:<20} {bal_type:<15} {length:<8.1f} {thickness*100:<8.0f} "
              f"{anc['anchorage_length_required']:<12.2f} {anc['safety_factor']:<8.2f} {esito:<8}")

    print("-" * 88)


if __name__ == "__main__":
    print("\n🏗️  MURATURA FEM v6.2 - Balcony Design Module Examples")
    print("=" * 70)
    print("⚠️  ATTENZIONE: La verifica dell'ancoraggio è CRITICA per la sicurezza!")
    print("=" * 70)

    # Esegui tutti gli esempi
    balcony1 = example_1_rc_cantilever_standard()
    balcony2 = example_2_long_cantilever()
    balcony3 = example_3_steel_balcony_ipe()
    balcony4 = example_4_steel_balcony_hea()
    balcony5 = example_5_anchorage_failure_case()
    balcony6 = example_6_existing_building_assessment()

    # Tabella comparativa
    comparison_table()

    print("\n" + "="*70)
    print("✅ Tutti gli esempi completati!")
    print("="*70)
    print("\n⚠️  PROMEMORIA SICUREZZA:")
    print("  1. Ancoraggio muro SEMPRE prioritario (τ ≤ 0.4 MPa)")
    print("  2. Lunghezza ancoraggio ≥ max(30cm, 1.5×h, 2/3×muro)")
    print("  3. Sbalzi > 1.8m: verificare deformabilità")
    print("  4. Edifici esistenti: considerare degrado/carbonatazione")
    print("  5. Sisma: safety factor ≥ 1.5 su ancoraggio")
    print("\nProssimi passi:")
    print("  1. Integrare con modulo solai per analisi struttura completa")
    print("  2. Aggiungere verifica deformabilità (freccia)")
    print("  3. Implementare rinforzi (tiranti, FRP)")
    print("  4. Connessioni saldate/bullonate dettagliate")
