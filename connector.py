#!/usr/bin/env python3
"""
CONNECTOR - Interfaccia completa per Claude Code
Gestisce tutti gli aspetti del sistema di calcolo muratura NTC 2018

Uso:
    from connector import Muratura
    m = Muratura()
    m.help()
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import pickle

# Aggiungi il percorso del modulo
sys.path.insert(0, str(Path(__file__).parent))

# ============================================================================
# CONNETTORE PRINCIPALE
# ============================================================================

class Muratura:
    """
    Connettore completo per il sistema di calcolo muratura.
    Fornisce accesso a tutte le funzionalita' del programma.
    """

    VERSION = "1.0.0"

    def __init__(self, project_name: str = "default"):
        """
        Inizializza il connettore.

        Args:
            project_name: Nome del progetto (per salvataggio/caricamento)
        """
        self.project_name = project_name
        self.project_path = Path(__file__).parent / "projects" / project_name

        # Stato corrente
        self.materiali: Dict[str, Any] = {}
        self.geometrie: Dict[str, Any] = {}
        self.pareti: Dict[str, Dict] = {}
        self.analisi: Dict[str, Dict] = {}
        self.risultati: Dict[str, Any] = {}

        # Carica moduli
        self._modules = {}
        self._load_modules()

        # Crea directory progetto
        self.project_path.mkdir(parents=True, exist_ok=True)

        print(f"Muratura Connector v{self.VERSION}")
        print(f"Progetto: {project_name}")
        self.status()

    def _load_modules(self):
        """Carica tutti i moduli disponibili"""
        modules = {
            'materials': ('Material.materials', [
                'MaterialProperties', 'MasonryType', 'MortarQuality',
                'ConservationState', 'UnitsConverter', 'CommonMaterials',
                'MultiLayerMasonry', 'LayerConnection', 'NTC_2018_DATABASE',
                'compare_materials', 'create_material_report'
            ]),
            'geometry': ('Material.geometry', [
                'GeometryPier', 'GeometrySpandrel', 'Opening', 'Lintel',
                'Reinforcement', 'ReinforcementType', 'BoundaryCondition',
                'WallType', 'ArchGeometry', 'VaultGeometry', 'MasonryColumn'
            ]),
            'enums': ('Material.enums', [
                'AnalysisMethod', 'ConstitutiveLaw'
            ]),
            'engine': ('Material.engine', [
                'MasonryFEMEngine', 'EquivalentFrame'
            ]),
            'constitutive': ('Material.constitutive', [
                'LinearElastic', 'BilinearModel', 'ParabolicModel',
                'ManderModel', 'KentParkModel'
            ]),
            'utils': ('Material.utils', [
                'calculate_damage_indices', 'distribute_vertical_loads',
                'analyze_crack_pattern', 'sensitivity_analysis_limit'
            ])
        }

        for name, (module_path, items) in modules.items():
            try:
                mod = __import__(module_path, fromlist=items)
                self._modules[name] = {'module': mod, 'items': {}}
                for item in items:
                    if hasattr(mod, item):
                        self._modules[name]['items'][item] = getattr(mod, item)
                self._modules[name]['status'] = 'OK'
            except Exception as e:
                self._modules[name] = {'status': str(e), 'items': {}}

    # ========================================================================
    # INFORMAZIONI E HELP
    # ========================================================================

    def help(self, topic: str = None):
        """
        Mostra aiuto sul sistema.

        Args:
            topic: Argomento specifico (materiali, geometria, analisi, etc.)
        """
        if topic is None:
            print("""
╔══════════════════════════════════════════════════════════════╗
║           MURATURA CONNECTOR - GUIDA COMANDI                 ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  INFORMAZIONI                                                ║
║    m.help()              - Questa guida                      ║
║    m.help('materiali')   - Aiuto sui materiali               ║
║    m.help('geometria')   - Aiuto sulla geometria             ║
║    m.help('analisi')     - Aiuto sulle analisi               ║
║    m.status()            - Stato moduli e progetto           ║
║    m.lista()             - Lista elementi definiti           ║
║                                                              ║
║  MATERIALI                                                   ║
║    m.materiale(nome, tipo, malta)  - Crea materiale NTC      ║
║    m.materiale_custom(nome, **p)   - Materiale personalizzato║
║    m.mostra_materiale(nome)        - Dettagli materiale      ║
║    m.tipi_muratura()               - Lista tipi NTC 2018     ║
║                                                              ║
║  GEOMETRIA                                                   ║
║    m.maschio(nome, L, H, t)        - Crea maschio murario    ║
║    m.fascia(nome, L, H, t)         - Crea fascia di piano    ║
║    m.apertura(geom, w, h, x, y)    - Aggiungi apertura       ║
║    m.mostra_geometria(nome)        - Dettagli geometria      ║
║                                                              ║
║  PARETI E STRUTTURE                                          ║
║    m.parete(nome, L, H, t, piani)  - Definisci parete        ║
║    m.assegna_materiale(parete, mat)- Assegna materiale       ║
║    m.massa_piano(parete, piano, kg)- Assegna massa           ║
║    m.mostra_parete(nome)           - Dettagli parete         ║
║                                                              ║
║  ANALISI                                                     ║
║    m.pushover(parete, pattern)     - Analisi pushover        ║
║    m.modale(parete, n_modi)        - Analisi modale          ║
║    m.statica(parete, carichi)      - Analisi statica         ║
║    m.time_history(parete, acc, dt) - Time history            ║
║                                                              ║
║  RISULTATI                                                   ║
║    m.risultati(analisi)            - Mostra risultati        ║
║    m.curva_pushover(analisi)       - Curva capacita'         ║
║    m.verifiche(analisi)            - Verifiche elementi      ║
║    m.esporta(analisi, formato)     - Esporta risultati       ║
║                                                              ║
║  PROGETTO                                                    ║
║    m.salva()                       - Salva progetto          ║
║    m.carica(nome)                  - Carica progetto         ║
║    m.nuovo(nome)                   - Nuovo progetto          ║
║    m.report()                      - Genera report completo  ║
║                                                              ║
║  FILE DSL (.mur)                                             ║
║    m.carica_dsl(file)              - Carica da file .mur     ║
║    m.salva_dsl(file)               - Salva in file .mur      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
        elif topic == 'materiali':
            print("""
MATERIALI - Guida dettagliata
═══════════════════════════════════════════════════════════════

TIPI MURATURA NTC 2018:
  - PIETRA_IRREGOLARE    Pietrame disordinato
  - PIETRA_SBOZZATA      Conci sbozzati
  - PIETRA_SQUADRATA     Pietre a spacco con buona tessitura
  - PIETRA_BLOCCHI       Blocchi lapidei squadrati
  - MATTONI_PIENI        Mattoni pieni e malta di calce
  - MATTONI_SEMIPIENI    Mattoni semipieni con malta cementizia
  - BLOCCHI_LATERIZIO    Blocchi laterizi con malta cementizia
  - BLOCCHI_FORATI       Blocchi laterizi forati (<45% foratura)
  - BLOCCHI_CLS          Blocchi di calcestruzzo
  - BLOCCHI_CLS_ESPANSO  Blocchi di calcestruzzo alleggerito

QUALITA' MALTA:
  - SCADENTE, BUONA, OTTIME

STATO CONSERVAZIONE:
  - CATTIVO, MEDIOCRE, BUONO, OTTIMO

ESEMPIO:
  m.materiale('mur1', 'MATTONI_PIENI', 'BUONA', 'BUONO')
  m.mostra_materiale('mur1')
""")
        elif topic == 'geometria':
            print("""
GEOMETRIA - Guida dettagliata
═══════════════════════════════════════════════════════════════

MASCHIO MURARIO:
  m.maschio(nome, lunghezza, altezza, spessore)
  - lunghezza: larghezza in pianta [m]
  - altezza: altezza interpiano [m]
  - spessore: spessore parete [m]

FASCIA DI PIANO:
  m.fascia(nome, lunghezza, altezza, spessore)

APERTURE:
  m.apertura(nome_geom, larghezza, altezza, x_centro, y_base)
  - x_centro: posizione X dal baricentro [m]
  - y_base: quota inferiore dalla base [m]

CONDIZIONI VINCOLO:
  - CANTILEVER     Mensola (base incastrata)
  - FIXED_FIXED    Doppio incastro
  - PINNED_PINNED  Cerniera-cerniera

ESEMPIO:
  m.maschio('P1', 1.2, 3.0, 0.3)
  m.apertura('P1', 1.0, 1.2, 0.0, 0.9)  # Finestra
  m.mostra_geometria('P1')
""")
        elif topic == 'analisi':
            print("""
ANALISI - Guida dettagliata
═══════════════════════════════════════════════════════════════

PUSHOVER:
  m.pushover(parete, pattern='triangular', target_drift=0.04)
  - pattern: 'triangular', 'uniform', 'modal'
  - target_drift: drift obiettivo (default 4%)

MODALE:
  m.modale(parete, n_modi=6)
  - n_modi: numero di modi da calcolare

STATICA:
  m.statica(parete, carichi)
  - carichi: {nodo: {'Fx': kN, 'Fy': kN, 'M': kNm}}

TIME HISTORY:
  m.time_history(parete, accelerogramma, dt=0.01)
  - accelerogramma: lista accelerazioni [m/s²]
  - dt: passo temporale [s]

ESEMPIO:
  m.parete('W1', 5.0, 6.0, 0.3, piani=2)
  m.assegna_materiale('W1', 'mur1')
  m.massa_piano('W1', 0, 10000)  # 10 ton al piano 1
  m.massa_piano('W1', 1, 8000)   # 8 ton al piano 2
  m.pushover('W1')
  m.curva_pushover('W1_pushover')
""")
        else:
            print(f"Argomento '{topic}' non riconosciuto. Usa: materiali, geometria, analisi")

    def status(self):
        """Mostra stato dei moduli e del progetto"""
        print("\n┌─────────────────────────────────────────────────────┐")
        print("│              STATO SISTEMA                          │")
        print("├─────────────────────────────────────────────────────┤")
        for name, data in self._modules.items():
            status = data.get('status', 'ERRORE')
            icon = "✓" if status == 'OK' else "✗"
            n_items = len(data.get('items', {}))
            if status == 'OK':
                print(f"│  {icon} {name:15} │ {n_items:2} classi caricate        │")
            else:
                err = status[:30] + "..." if len(status) > 30 else status
                print(f"│  {icon} {name:15} │ {err:30} │")
        print("├─────────────────────────────────────────────────────┤")
        print(f"│  Progetto: {self.project_name:15}                    │")
        print(f"│  Materiali: {len(self.materiali):3}  Geometrie: {len(self.geometrie):3}           │")
        print(f"│  Pareti: {len(self.pareti):3}     Analisi: {len(self.analisi):3}              │")
        print("└─────────────────────────────────────────────────────┘\n")

    def lista(self):
        """Lista tutti gli elementi definiti nel progetto"""
        print("\n=== ELEMENTI PROGETTO ===\n")

        if self.materiali:
            print("MATERIALI:")
            for nome, mat in self.materiali.items():
                print(f"  - {nome}: fcm={mat.fcm:.2f} MPa, E={mat.E:.0f} MPa")
        else:
            print("MATERIALI: (nessuno)")

        if self.geometrie:
            print("\nGEOMETRIE:")
            for nome, geom in self.geometrie.items():
                tipo = type(geom).__name__
                print(f"  - {nome}: {tipo}")
        else:
            print("\nGEOMETRIE: (nessuna)")

        if self.pareti:
            print("\nPARETI:")
            for nome, parete in self.pareti.items():
                mat = parete.get('materiale', 'N/D')
                print(f"  - {nome}: {parete['length']}x{parete['height']}m, mat={mat}")
        else:
            print("\nPARETI: (nessuna)")

        if self.analisi:
            print("\nANALISI:")
            for nome, an in self.analisi.items():
                print(f"  - {nome}: {an.get('type', 'N/D')}")
        else:
            print("\nANALISI: (nessuna)")

        print()

    # ========================================================================
    # MATERIALI
    # ========================================================================

    def tipi_muratura(self):
        """Mostra tutti i tipi di muratura NTC 2018"""
        if 'materials' not in self._modules or self._modules['materials']['status'] != 'OK':
            print("Errore: modulo materials non disponibile")
            return

        MasonryType = self._modules['materials']['items'].get('MasonryType')
        if MasonryType:
            print("\nTIPI MURATURA NTC 2018:")
            print("-" * 60)
            for t in MasonryType:
                print(f"  {t.name:25} {t.value[:35]}...")
            print()

    def materiale(self, nome: str, tipo: str = 'MATTONI_PIENI',
                  malta: str = 'BUONA', conservazione: str = 'BUONO',
                  posizione: str = 'mean') -> Any:
        """
        Crea un materiale da tabella NTC 2018.

        Args:
            nome: Nome identificativo del materiale
            tipo: Tipo muratura (es. MATTONI_PIENI, PIETRA_SQUADRATA)
            malta: Qualita' malta (SCADENTE, BUONA, OTTIME)
            conservazione: Stato conservazione (CATTIVO, MEDIOCRE, BUONO, OTTIMO)
            posizione: Posizione nell'intervallo NTC (min, mean, max)

        Returns:
            MaterialProperties creato
        """
        if 'materials' not in self._modules or self._modules['materials']['status'] != 'OK':
            print("Errore: modulo materials non disponibile")
            return None

        items = self._modules['materials']['items']
        MaterialProperties = items.get('MaterialProperties')
        MasonryType = items.get('MasonryType')
        MortarQuality = items.get('MortarQuality')
        ConservationState = items.get('ConservationState')

        # Converti stringhe in enum
        masonry = getattr(MasonryType, tipo, MasonryType.MATTONI_PIENI)
        mortar = getattr(MortarQuality, malta, MortarQuality.BUONA)
        cons = getattr(ConservationState, conservazione, ConservationState.BUONO)

        mat = MaterialProperties.from_ntc_table(
            masonry_type=masonry,
            mortar_quality=mortar,
            conservation=cons,
            position=posizione
        )

        self.materiali[nome] = mat
        print(f"Materiale '{nome}' creato: fcm={mat.fcm:.2f} MPa, E={mat.E:.0f} MPa, tau0={mat.tau0:.3f} MPa")
        return mat

    def materiale_custom(self, nome: str, **kwargs) -> Any:
        """
        Crea un materiale con parametri personalizzati.

        Args:
            nome: Nome identificativo
            **kwargs: Parametri (fcm, E, G, tau0, weight, nu, mu, etc.)

        Returns:
            MaterialProperties creato
        """
        if 'materials' not in self._modules or self._modules['materials']['status'] != 'OK':
            print("Errore: modulo materials non disponibile")
            return None

        MaterialProperties = self._modules['materials']['items'].get('MaterialProperties')
        mat = MaterialProperties(**kwargs)
        self.materiali[nome] = mat
        print(f"Materiale custom '{nome}' creato: fcm={mat.fcm:.2f} MPa, E={mat.E:.0f} MPa")
        return mat

    def mostra_materiale(self, nome: str):
        """Mostra dettagli completi di un materiale"""
        if nome not in self.materiali:
            print(f"Materiale '{nome}' non trovato")
            return

        mat = self.materiali[nome]
        print(mat.get_info())

        # Valori di progetto
        design = mat.get_design_values()
        print("\nVALORI DI PROGETTO (gamma_m=2.0, FC=1.0):")
        print(f"  fcd  = {design['fcd']:.2f} MPa")
        print(f"  fvd  = {design['fvd']:.3f} MPa")
        print(f"  fvd0 = {design['fvd0']:.3f} MPa")
        print(f"  ftd  = {design['ftd']:.3f} MPa")
        print(f"  Ed   = {design['Ed']:.0f} MPa")
        print(f"  Gd   = {design['Gd']:.0f} MPa")

    def valori_progetto(self, nome: str, gamma_m: float = 2.0, FC: float = 1.0) -> Dict:
        """
        Calcola valori di progetto per un materiale.

        Args:
            nome: Nome materiale
            gamma_m: Coefficiente sicurezza materiale
            FC: Fattore di confidenza (1.0=LC3, 1.2=LC2, 1.35=LC1)

        Returns:
            Dict con valori di progetto
        """
        if nome not in self.materiali:
            print(f"Materiale '{nome}' non trovato")
            return {}

        return self.materiali[nome].get_design_values(gamma_m, FC)

    # ========================================================================
    # GEOMETRIA
    # ========================================================================

    def maschio(self, nome: str, lunghezza: float, altezza: float,
                spessore: float, h0: float = None) -> Any:
        """
        Crea geometria maschio murario.

        Args:
            nome: Nome identificativo
            lunghezza: Larghezza in pianta [m]
            altezza: Altezza interpiano [m]
            spessore: Spessore [m]
            h0: Altezza momento nullo [m] (default: calcolato)

        Returns:
            GeometryPier creato
        """
        if 'geometry' not in self._modules or self._modules['geometry']['status'] != 'OK':
            print("Errore: modulo geometry non disponibile")
            return None

        GeometryPier = self._modules['geometry']['items'].get('GeometryPier')

        pier = GeometryPier(
            length=lunghezza,
            height=altezza,
            thickness=spessore,
            h0=h0
        )

        self.geometrie[nome] = pier
        print(f"Maschio '{nome}': {lunghezza}x{altezza}x{spessore}m, A={pier.gross_area:.3f}m², λ={pier.slenderness:.1f}")
        return pier

    def fascia(self, nome: str, lunghezza: float, altezza: float,
               spessore: float) -> Any:
        """
        Crea geometria fascia di piano.

        Args:
            nome: Nome identificativo
            lunghezza: Lunghezza fascia [m]
            altezza: Altezza fascia [m]
            spessore: Spessore [m]

        Returns:
            GeometrySpandrel creato
        """
        if 'geometry' not in self._modules or self._modules['geometry']['status'] != 'OK':
            print("Errore: modulo geometry non disponibile")
            return None

        GeometrySpandrel = self._modules['geometry']['items'].get('GeometrySpandrel')

        spandrel = GeometrySpandrel(
            length=lunghezza,
            height=altezza,
            thickness=spessore
        )

        self.geometrie[nome] = spandrel
        print(f"Fascia '{nome}': {lunghezza}x{altezza}x{spessore}m, A={spandrel.area:.3f}m²")
        return spandrel

    def apertura(self, nome_geometria: str, larghezza: float, altezza: float,
                 x_centro: float = 0.0, y_base: float = 0.0, tipo: str = 'window'):
        """
        Aggiunge un'apertura a una geometria esistente.

        Args:
            nome_geometria: Nome della geometria (maschio)
            larghezza: Larghezza apertura [m]
            altezza: Altezza apertura [m]
            x_centro: Posizione X dal baricentro [m]
            y_base: Quota inferiore dalla base [m]
            tipo: 'window', 'door', 'niche'
        """
        if nome_geometria not in self.geometrie:
            print(f"Geometria '{nome_geometria}' non trovata")
            return

        geom = self.geometrie[nome_geometria]

        Opening = self._modules['geometry']['items'].get('Opening')
        if Opening and hasattr(geom, 'add_opening'):
            op = Opening(width=larghezza, height=altezza,
                        x_center=x_centro, y_bottom=y_base, type=tipo)
            geom.add_opening(op)
            print(f"Apertura aggiunta a '{nome_geometria}': {larghezza}x{altezza}m @ ({x_centro}, {y_base})")
            print(f"  Area netta aggiornata: {geom.net_area:.3f}m²")
        else:
            print("Impossibile aggiungere apertura a questa geometria")

    def mostra_geometria(self, nome: str):
        """Mostra dettagli completi di una geometria"""
        if nome not in self.geometrie:
            print(f"Geometria '{nome}' non trovata")
            return

        geom = self.geometrie[nome]
        tipo = type(geom).__name__

        print(f"\n{'='*50}")
        print(f"GEOMETRIA: {nome} ({tipo})")
        print(f"{'='*50}")

        if hasattr(geom, 'length'):
            print(f"Lunghezza: {geom.length:.3f} m")
        if hasattr(geom, 'height'):
            print(f"Altezza: {geom.height:.3f} m")
        if hasattr(geom, 'thickness'):
            print(f"Spessore: {geom.thickness:.3f} m")

        if hasattr(geom, 'gross_area'):
            print(f"\nArea lorda: {geom.gross_area:.4f} m²")
        if hasattr(geom, 'net_area'):
            print(f"Area netta: {geom.net_area:.4f} m²")
        if hasattr(geom, 'effective_area'):
            print(f"Area efficace: {geom.effective_area:.4f} m²")

        if hasattr(geom, 'net_inertia'):
            print(f"Inerzia: {geom.net_inertia:.6f} m⁴")
        if hasattr(geom, 'slenderness'):
            print(f"Snellezza: {geom.slenderness:.2f}")
        if hasattr(geom, 'h0'):
            print(f"h0 (momento nullo): {geom.h0:.3f} m")

        if hasattr(geom, 'openings') and geom.openings:
            print(f"\nAperture ({len(geom.openings)}):")
            for i, op in enumerate(geom.openings):
                print(f"  {i+1}. {op.type}: {op.width}x{op.height}m @ ({op.x_center}, {op.y_bottom})")

        print()

    # ========================================================================
    # PARETI E STRUTTURE
    # ========================================================================

    def parete(self, nome: str, lunghezza: float, altezza: float,
               spessore: float, piani: int = 1) -> Dict:
        """
        Definisce una parete per l'analisi.

        Args:
            nome: Nome identificativo
            lunghezza: Lunghezza parete [m]
            altezza: Altezza totale [m]
            spessore: Spessore [m]
            piani: Numero di piani

        Returns:
            Dict con dati parete
        """
        parete_data = {
            'length': lunghezza,
            'height': altezza,
            'thickness': spessore,
            'n_floors': piani,
            'floor_masses': {},
            'materiale': None,
            'carichi': {}
        }

        self.pareti[nome] = parete_data
        print(f"Parete '{nome}': {lunghezza}x{altezza}x{spessore}m, {piani} piani")
        return parete_data

    def assegna_materiale(self, nome_parete: str, nome_materiale: str):
        """Assegna un materiale a una parete"""
        if nome_parete not in self.pareti:
            print(f"Parete '{nome_parete}' non trovata")
            return
        if nome_materiale not in self.materiali:
            print(f"Materiale '{nome_materiale}' non trovato")
            return

        self.pareti[nome_parete]['materiale'] = nome_materiale
        mat = self.materiali[nome_materiale]
        print(f"Materiale '{nome_materiale}' assegnato a parete '{nome_parete}'")
        print(f"  fcm={mat.fcm:.2f} MPa, E={mat.E:.0f} MPa")

    def massa_piano(self, nome_parete: str, piano: int, massa_kg: float):
        """
        Assegna massa a un piano della parete.

        Args:
            nome_parete: Nome parete
            piano: Indice piano (0 = primo piano)
            massa_kg: Massa in kg
        """
        if nome_parete not in self.pareti:
            print(f"Parete '{nome_parete}' non trovata")
            return

        self.pareti[nome_parete]['floor_masses'][piano] = massa_kg
        print(f"Massa piano {piano}: {massa_kg} kg assegnata a '{nome_parete}'")

    def mostra_parete(self, nome: str):
        """Mostra dettagli completi di una parete"""
        if nome not in self.pareti:
            print(f"Parete '{nome}' non trovata")
            return

        p = self.pareti[nome]

        print(f"\n{'='*50}")
        print(f"PARETE: {nome}")
        print(f"{'='*50}")
        print(f"Dimensioni: {p['length']} x {p['height']} x {p['thickness']} m")
        print(f"Piani: {p['n_floors']}")

        if p['materiale']:
            mat = self.materiali[p['materiale']]
            print(f"\nMateriale: {p['materiale']}")
            print(f"  fcm = {mat.fcm:.2f} MPa")
            print(f"  E = {mat.E:.0f} MPa")
            print(f"  tau0 = {mat.tau0:.3f} MPa")
        else:
            print("\nMateriale: NON ASSEGNATO")

        if p['floor_masses']:
            print("\nMasse di piano:")
            for piano, massa in p['floor_masses'].items():
                print(f"  Piano {piano}: {massa} kg")
        else:
            print("\nMasse di piano: NON DEFINITE")

        print()

    # ========================================================================
    # ANALISI
    # ========================================================================

    def _get_engine(self):
        """Ottiene istanza MasonryFEMEngine"""
        if 'engine' not in self._modules or self._modules['engine']['status'] != 'OK':
            print("Errore: modulo engine non disponibile")
            return None

        MasonryFEMEngine = self._modules['engine']['items'].get('MasonryFEMEngine')
        AnalysisMethod = self._modules['enums']['items'].get('AnalysisMethod')

        return MasonryFEMEngine(method=AnalysisMethod.FRAME)

    def pushover(self, nome_parete: str, pattern: str = 'triangular',
                 target_drift: float = 0.04, direzione: str = 'y') -> Dict:
        """
        Esegue analisi pushover.

        Args:
            nome_parete: Nome della parete da analizzare
            pattern: Distribuzione forze ('triangular', 'uniform', 'modal')
            target_drift: Drift obiettivo
            direzione: 'x' o 'y'

        Returns:
            Dict con risultati
        """
        if nome_parete not in self.pareti:
            print(f"Parete '{nome_parete}' non trovata")
            return {}

        parete = self.pareti[nome_parete]
        if not parete['materiale']:
            print("Errore: materiale non assegnato")
            return {}

        engine = self._get_engine()
        if not engine:
            return {}

        materiale = self.materiali[parete['materiale']]

        wall_data = {
            'length': parete['length'],
            'height': parete['height'],
            'thickness': parete['thickness'],
            'floor_masses': parete['floor_masses']
        }

        options = {
            'analysis_type': 'pushover',
            'target_drift': target_drift,
            'lateral_pattern': pattern,
            'direction': direzione
        }

        print(f"\nEsecuzione pushover su '{nome_parete}'...")
        print(f"  Pattern: {pattern}, Target drift: {target_drift*100:.1f}%")

        results = engine.analyze_structure(wall_data, materiale, {}, options)

        # Salva risultati
        analysis_name = f"{nome_parete}_pushover"
        self.analisi[analysis_name] = {
            'type': 'pushover',
            'parete': nome_parete,
            'options': options
        }
        self.risultati[analysis_name] = results

        # Mostra riepilogo
        if 'curve' in results and results['curve']:
            ultimo = results['curve'][-1]
            print(f"\nRisultati:")
            print(f"  Base shear max: {ultimo['base_shear']:.1f} kN")
            print(f"  Drift finale: {ultimo['top_drift']*100:.2f}%")

            if 'performance_levels' in results:
                if 'yield' in results['performance_levels']:
                    y = results['performance_levels']['yield']
                    print(f"  Snervamento: Vb={y.get('base_shear', 0):.1f} kN, drift={y.get('top_drift', 0)*100:.2f}%")
                if 'ultimate' in results['performance_levels']:
                    u = results['performance_levels']['ultimate']
                    print(f"  Ultimo: Vb={u.get('base_shear', 0):.1f} kN, drift={u.get('top_drift', 0)*100:.2f}%")

        print(f"\nRisultati salvati come '{analysis_name}'")
        return results

    def modale(self, nome_parete: str, n_modi: int = 6) -> Dict:
        """
        Esegue analisi modale.

        Args:
            nome_parete: Nome della parete
            n_modi: Numero di modi da calcolare

        Returns:
            Dict con risultati
        """
        if nome_parete not in self.pareti:
            print(f"Parete '{nome_parete}' non trovata")
            return {}

        parete = self.pareti[nome_parete]
        if not parete['materiale']:
            print("Errore: materiale non assegnato")
            return {}

        engine = self._get_engine()
        if not engine:
            return {}

        materiale = self.materiali[parete['materiale']]

        wall_data = {
            'length': parete['length'],
            'height': parete['height'],
            'thickness': parete['thickness'],
            'floor_masses': parete['floor_masses']
        }

        options = {
            'analysis_type': 'modal',
            'n_modes': n_modi
        }

        print(f"\nEsecuzione analisi modale su '{nome_parete}'...")

        results = engine.analyze_structure(wall_data, materiale, {}, options)

        # Salva risultati
        analysis_name = f"{nome_parete}_modale"
        self.analisi[analysis_name] = {
            'type': 'modal',
            'parete': nome_parete,
            'options': options
        }
        self.risultati[analysis_name] = results

        # Mostra riepilogo
        if 'frequencies' in results:
            print("\nModi propri:")
            for i, (f, T) in enumerate(zip(results['frequencies'], results['periods'])):
                print(f"  Modo {i+1}: f = {f:.2f} Hz, T = {T:.3f} s")

            print(f"\nPartecipazione massa X: {results.get('total_mass_participation_x', 0)*100:.1f}%")
            print(f"Partecipazione massa Y: {results.get('total_mass_participation_y', 0)*100:.1f}%")

        print(f"\nRisultati salvati come '{analysis_name}'")
        return results

    def statica(self, nome_parete: str, carichi: Dict) -> Dict:
        """
        Esegue analisi statica lineare.

        Args:
            nome_parete: Nome della parete
            carichi: {nodo: {'Fx': kN, 'Fy': kN, 'M': kNm}}

        Returns:
            Dict con risultati
        """
        if nome_parete not in self.pareti:
            print(f"Parete '{nome_parete}' non trovata")
            return {}

        parete = self.pareti[nome_parete]
        if not parete['materiale']:
            print("Errore: materiale non assegnato")
            return {}

        engine = self._get_engine()
        if not engine:
            return {}

        materiale = self.materiali[parete['materiale']]

        wall_data = {
            'length': parete['length'],
            'height': parete['height'],
            'thickness': parete['thickness'],
            'floor_masses': parete['floor_masses']
        }

        options = {'analysis_type': 'static'}

        print(f"\nEsecuzione analisi statica su '{nome_parete}'...")

        results = engine.analyze_structure(wall_data, materiale, carichi, options)

        # Salva risultati
        analysis_name = f"{nome_parete}_statica"
        self.analisi[analysis_name] = {
            'type': 'static',
            'parete': nome_parete,
            'carichi': carichi
        }
        self.risultati[analysis_name] = results

        if 'max_displacement' in results:
            print(f"\nSpostamento massimo: {results['max_displacement']*1000:.2f} mm")

        print(f"\nRisultati salvati come '{analysis_name}'")
        return results

    def time_history(self, nome_parete: str, accelerogramma: List[float],
                     dt: float = 0.01, direzione: str = 'y') -> Dict:
        """
        Esegue analisi time-history.

        Args:
            nome_parete: Nome della parete
            accelerogramma: Lista accelerazioni [m/s²]
            dt: Passo temporale [s]
            direzione: 'x' o 'y'

        Returns:
            Dict con risultati
        """
        if nome_parete not in self.pareti:
            print(f"Parete '{nome_parete}' non trovata")
            return {}

        parete = self.pareti[nome_parete]
        if not parete['materiale']:
            print("Errore: materiale non assegnato")
            return {}

        engine = self._get_engine()
        if not engine:
            return {}

        materiale = self.materiali[parete['materiale']]

        wall_data = {
            'length': parete['length'],
            'height': parete['height'],
            'thickness': parete['thickness'],
            'floor_masses': parete['floor_masses']
        }

        options = {
            'analysis_type': 'time_history',
            'accelerogram': accelerogramma,
            'dt': dt,
            'excitation_dir': direzione
        }

        print(f"\nEsecuzione time-history su '{nome_parete}'...")
        print(f"  Durata: {len(accelerogramma)*dt:.1f} s, dt={dt} s")

        results = engine.analyze_structure(wall_data, materiale, {}, options)

        # Salva risultati
        analysis_name = f"{nome_parete}_th"
        self.analisi[analysis_name] = {
            'type': 'time_history',
            'parete': nome_parete,
            'options': {'dt': dt, 'direzione': direzione}
        }
        self.risultati[analysis_name] = results

        if 'time_history' in results:
            th = results['time_history']
            print(f"\nRisultati:")
            print(f"  Drift massimo: {th.get('max_drift', 0)*100:.2f}%")
            print(f"  Spostamento massimo: {th.get('max_displacement', 0)*1000:.2f} mm")
            if 'critical_step' in th:
                cs = th['critical_step']
                print(f"  Step critico: t={cs.get('time', 0):.2f}s, Vb={cs.get('base_shear', 0):.1f}kN")

        print(f"\nRisultati salvati come '{analysis_name}'")
        return results

    # ========================================================================
    # RISULTATI
    # ========================================================================

    def risultato(self, nome_analisi: str) -> Dict:
        """Restituisce risultati di un'analisi"""
        if nome_analisi not in self.risultati:
            print(f"Analisi '{nome_analisi}' non trovata")
            print(f"Analisi disponibili: {list(self.risultati.keys())}")
            return {}
        return self.risultati[nome_analisi]

    def curva_pushover(self, nome_analisi: str):
        """Mostra curva pushover in formato tabellare"""
        if nome_analisi not in self.risultati:
            print(f"Analisi '{nome_analisi}' non trovata")
            return

        results = self.risultati[nome_analisi]
        if 'curve' not in results:
            print("Nessuna curva pushover disponibile")
            return

        print(f"\nCURVA PUSHOVER - {nome_analisi}")
        print("-" * 50)
        print(f"{'Step':>5} {'Vb [kN]':>12} {'Drift [%]':>12} {'d [mm]':>12}")
        print("-" * 50)

        curve = results['curve']
        step_size = max(1, len(curve) // 10)

        for i in range(0, len(curve), step_size):
            pt = curve[i]
            print(f"{i+1:>5} {pt['base_shear']:>12.1f} {pt['top_drift']*100:>12.3f} {pt['roof_displacement']*1000:>12.2f}")

        # Ultimo punto
        if len(curve) % step_size != 0:
            pt = curve[-1]
            print(f"{len(curve):>5} {pt['base_shear']:>12.1f} {pt['top_drift']*100:>12.3f} {pt['roof_displacement']*1000:>12.2f}")

        print("-" * 50)

        # Performance levels
        if 'performance_levels' in results:
            print("\nPunti caratteristici:")
            for level, data in results['performance_levels'].items():
                if isinstance(data, dict) and 'base_shear' in data:
                    print(f"  {level}: Vb={data['base_shear']:.1f} kN, drift={data.get('top_drift', 0)*100:.2f}%")

    def verifiche(self, nome_analisi: str):
        """Mostra verifiche elementi strutturali"""
        if nome_analisi not in self.risultati:
            print(f"Analisi '{nome_analisi}' non trovata")
            return

        results = self.risultati[nome_analisi]
        if 'element_checks' not in results:
            print("Nessuna verifica elementi disponibile")
            return

        checks = results['element_checks']

        print(f"\nVERIFICHE ELEMENTI - {nome_analisi}")
        print("-" * 70)
        print(f"{'Elem':>5} {'Tipo':>10} {'DCR_M':>8} {'DCR_V':>8} {'DCR_max':>8} {'Stato':>10}")
        print("-" * 70)

        for check in checks:
            stato = "OK" if check['verified'] else "NON OK"
            print(f"{check['element_id']:>5} {check['element_type']:>10} "
                  f"{check['DCR_moment']:>8.2f} {check['DCR_shear']:>8.2f} "
                  f"{check['DCR_max']:>8.2f} {stato:>10}")

        print("-" * 70)

        # Riepilogo
        n_ok = sum(1 for c in checks if c['verified'])
        n_tot = len(checks)
        print(f"\nRiepilogo: {n_ok}/{n_tot} elementi verificati")

    # ========================================================================
    # PROGETTO
    # ========================================================================

    def salva(self, nome: str = None):
        """Salva il progetto corrente"""
        if nome:
            self.project_name = nome
            self.project_path = Path(__file__).parent / "projects" / nome
            self.project_path.mkdir(parents=True, exist_ok=True)

        # Prepara dati per salvataggio
        data = {
            'project_name': self.project_name,
            'timestamp': datetime.now().isoformat(),
            'pareti': self.pareti,
            'analisi': self.analisi
        }

        # Salva JSON
        json_path = self.project_path / "project.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        # Salva materiali (pickle per oggetti complessi)
        mat_path = self.project_path / "materiali.pkl"
        with open(mat_path, 'wb') as f:
            pickle.dump(self.materiali, f)

        # Salva geometrie
        geom_path = self.project_path / "geometrie.pkl"
        with open(geom_path, 'wb') as f:
            pickle.dump(self.geometrie, f)

        # Salva risultati
        res_path = self.project_path / "risultati.pkl"
        with open(res_path, 'wb') as f:
            pickle.dump(self.risultati, f)

        print(f"Progetto salvato in: {self.project_path}")

    def carica_dsl(self, filepath: str) -> Dict:
        """
        Carica un progetto da file DSL (.mur).

        Args:
            filepath: Percorso al file .mur

        Returns:
            Dict con riepilogo progetto caricato

        Esempio file .mur:
            MATERIALE mattoni MATTONI_PIENI BUONA BUONO
            PIANO 0 3.2 12000
            PARETE P1 0 5.0 0.45 mattoni
            APERTURA P1 0 finestra 1.2 1.4 0.0 0.9
        """
        from Material.dsl_parser import DSLParser, DSLProject

        print(f"\nCaricamento file DSL: {filepath}")

        parser = DSLParser(filepath)
        project = parser.parse()

        # Aggiorna nome progetto
        self.project_name = project.nome
        self.project_path = Path(__file__).parent / "projects" / project.nome
        self.project_path.mkdir(parents=True, exist_ok=True)

        # Crea materiali
        for nome, mat_def in project.materiali.items():
            if mat_def.custom:
                self.materiale_custom(
                    nome,
                    fcm=mat_def.fcm,
                    E=mat_def.E,
                    G=mat_def.G,
                    tau0=mat_def.tau0,
                    weight=mat_def.peso
                )
            else:
                self.materiale(
                    nome,
                    tipo=mat_def.tipo,
                    malta=mat_def.malta,
                    conservazione=mat_def.conservazione
                )

        # Crea pareti raggruppate per nome
        pareti_grouped: Dict[str, List] = {}
        for parete in project.pareti:
            if parete.nome not in pareti_grouped:
                pareti_grouped[parete.nome] = []
            pareti_grouped[parete.nome].append(parete)

        for nome_parete, pareti_list in pareti_grouped.items():
            # Calcola altezza totale e numero piani
            piani_set = set(p.piano for p in pareti_list)
            n_floors = len(piani_set)

            # Usa la prima parete per dimensioni base
            p0 = pareti_list[0]
            altezza_totale = sum(
                project.piani[piano].altezza
                for piano in piani_set
                if piano in project.piani
            ) or (n_floors * 3.0)

            self.parete(nome_parete, p0.lunghezza, altezza_totale, p0.spessore, piani=n_floors)

            # Assegna materiale
            if p0.materiale in self.materiali:
                self.assegna_materiale(nome_parete, p0.materiale)

            # Assegna masse dai piani
            for piano in piani_set:
                if piano in project.piani:
                    self.massa_piano(nome_parete, piano, project.piani[piano].massa)

        # Aggiungi aperture alle geometrie
        for apertura in project.aperture:
            nome_geom = f"{apertura.parete}_P{apertura.piano}"
            if nome_geom not in self.geometrie:
                # Cerca la parete corrispondente
                for parete in project.pareti:
                    if parete.nome == apertura.parete and parete.piano == apertura.piano:
                        piano_def = project.piani.get(apertura.piano)
                        altezza = piano_def.altezza if piano_def else 3.0
                        self.maschio(nome_geom, parete.lunghezza, altezza, parete.spessore)
                        break

            if nome_geom in self.geometrie:
                self.apertura(nome_geom, apertura.larghezza, apertura.altezza,
                             apertura.x, apertura.y, apertura.tipo)

        # Salva carichi
        for piano, carico in project.carichi.items():
            for nome_parete in pareti_grouped:
                if nome_parete in self.pareti:
                    if 'carichi' not in self.pareti[nome_parete]:
                        self.pareti[nome_parete]['carichi'] = {}
                    self.pareti[nome_parete]['carichi'][piano] = {
                        'permanente': carico.permanente,
                        'variabile': carico.variabile,
                        'copertura': carico.copertura
                    }

        # Prepara analisi (non esegue, solo configura)
        for analisi in project.analisi:
            self.analisi[analisi.nome] = {
                'type': analisi.tipo.lower(),
                'options': analisi.parametri,
                'status': 'configured'
            }

        # Processa MURI (geometria con coordinate)
        if project.muri:
            # Inizializza storage per muri se non esiste
            if not hasattr(self, '_muri'):
                self._muri = {}
            if not hasattr(self, '_piani_dsl'):
                self._piani_dsl = project.piani

            # Raggruppa muri per piano (z)
            piani_z = {}
            for muro in project.muri:
                z_key = round(muro.z, 2)
                if z_key not in piani_z:
                    piani_z[z_key] = []
                piani_z[z_key].append(muro)

            # Crea pareti dai muri
            for muro in project.muri:
                # Calcola lunghezza muro
                import math
                lunghezza = math.sqrt((muro.x2 - muro.x1)**2 + (muro.y2 - muro.y1)**2)

                # Determina piano dalla quota z
                piano_idx = 0
                z_accum = 0
                for p_idx in sorted(project.piani.keys()):
                    if muro.z >= z_accum:
                        piano_idx = p_idx
                    z_accum += project.piani[p_idx].altezza

                # Salva muro con coordinate
                self._muri[muro.nome] = {
                    'x1': muro.x1, 'y1': muro.y1,
                    'x2': muro.x2, 'y2': muro.y2,
                    'z': muro.z,
                    'altezza': muro.altezza,
                    'spessore': muro.spessore,
                    'materiale': muro.materiale,
                    'lunghezza': lunghezza,
                    'piano': piano_idx
                }

                # Crea geometria maschio per ogni muro
                nome_geom = f"{muro.nome}"
                self.maschio(nome_geom, lunghezza, muro.altezza, muro.spessore)

                # Assegna materiale
                if muro.materiale in self.materiali:
                    if nome_geom not in self.pareti:
                        self.parete(nome_geom, lunghezza, muro.altezza, muro.spessore, piani=1)
                    self.assegna_materiale(nome_geom, muro.materiale)

            print(f"  Muri caricati: {len(project.muri)}")
            print(f"  Piani definiti: {len(project.piani)}")

        # Riepilogo
        print(f"\nProgetto '{project.nome}' caricato da DSL:")
        print(f"  Materiali: {len(self.materiali)}")
        print(f"  Pareti: {len(self.pareti)}")
        print(f"  Geometrie: {len(self.geometrie)}")
        print(f"  Analisi configurate: {len(self.analisi)}")

        if parser.warnings:
            print("\nAvvisi:")
            for w in parser.warnings:
                print(f"  {w}")

        return {
            'nome': project.nome,
            'materiali': len(self.materiali),
            'pareti': len(self.pareti),
            'geometrie': len(self.geometrie),
            'analisi': len(self.analisi)
        }

    def salva_dsl(self, filepath: str = None) -> str:
        """
        Salva il progetto corrente in formato DSL (.mur).

        Args:
            filepath: Percorso file output (default: project_name.mur)

        Returns:
            Percorso file salvato
        """
        from Material.dsl_parser import DSLExporter

        exporter = DSLExporter(self)
        output_path = exporter.save(filepath)

        print(f"Progetto salvato in formato DSL: {output_path}")
        return output_path

    def carica(self, nome: str):
        """Carica un progetto esistente"""
        project_path = Path(__file__).parent / "projects" / nome

        if not project_path.exists():
            print(f"Progetto '{nome}' non trovato")
            return False

        try:
            # Carica JSON
            json_path = project_path / "project.json"
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.pareti = data.get('pareti', {})
                self.analisi = data.get('analisi', {})

            # Carica materiali
            mat_path = project_path / "materiali.pkl"
            if mat_path.exists():
                with open(mat_path, 'rb') as f:
                    self.materiali = pickle.load(f)

            # Carica geometrie
            geom_path = project_path / "geometrie.pkl"
            if geom_path.exists():
                with open(geom_path, 'rb') as f:
                    self.geometrie = pickle.load(f)

            # Carica risultati
            res_path = project_path / "risultati.pkl"
            if res_path.exists():
                with open(res_path, 'rb') as f:
                    self.risultati = pickle.load(f)

            self.project_name = nome
            self.project_path = project_path

            print(f"Progetto '{nome}' caricato")
            self.lista()
            return True

        except Exception as e:
            print(f"Errore caricamento: {e}")
            return False

    def nuovo(self, nome: str):
        """Crea un nuovo progetto vuoto"""
        self.project_name = nome
        self.project_path = Path(__file__).parent / "projects" / nome
        self.project_path.mkdir(parents=True, exist_ok=True)

    def import_edl(self, filepath: str, crea_materiale: bool = True) -> Dict:
        """
        Importa progetto da file Edilus (.EDL).

        Args:
            filepath: Percorso file .EDL
            crea_materiale: Se True, crea materiale di default

        Returns:
            Dict con info progetto importato
        """
        from edl_parser import EDLParser, EDLProject

        print(f"\nImportazione file EDL: {filepath}")

        parser = EDLParser(filepath)
        project = parser.parse()

        print(parser.summary())

        # Aggiorna nome progetto
        self.project_name = project.nome
        self.project_path = Path(__file__).parent / "projects" / project.nome
        self.project_path.mkdir(parents=True, exist_ok=True)

        # Crea materiale di default se richiesto
        if crea_materiale and project.materiali:
            mat_tipo = 'MATTONI_PIENI'
            if 'Pietra' in project.materiali:
                mat_tipo = 'PIETRA_SQUADRATA'
            elif 'Tufo' in project.materiali:
                mat_tipo = 'PIETRA_IRREGOLARE'
            elif 'Laterizio' in project.materiali:
                mat_tipo = 'BLOCCHI_LATERIZIO'

            self.materiale('mat_edl', mat_tipo, 'BUONA')

        # Importa pareti
        for p in project.pareti:
            # Stima dimensioni se non disponibili
            altezza = p.altezza if p.altezza > 0 else 3.0
            spessore = p.spessore if p.spessore > 0 else 0.3
            lunghezza = p.lunghezza if p.lunghezza > 0 else 5.0

            nome_parete = p.nome.replace(' ', '_')
            self.parete(nome_parete, lunghezza, altezza, spessore, piani=1)

            if crea_materiale:
                self.assegna_materiale(nome_parete, 'mat_edl')

        print(f"\nProgetto '{project.nome}' importato:")
        print(f"  {len(self.pareti)} pareti create")
        print(f"  {project.n_maschi} maschi rilevati nel file originale")
        print(f"  {project.n_fasce} fasce rilevate nel file originale")

        return {
            'nome': project.nome,
            'n_pareti': len(self.pareti),
            'n_maschi_originali': project.n_maschi,
            'n_fasce_originali': project.n_fasce,
            'materiali_rilevati': project.materiali
        }

    def import_edl_con_ifc(self, edl_path: str, ifc_path: str,
                            crea_materiale: bool = True) -> Dict:
        """
        Importa EDL usando IFC come riferimento per geometrie precise.

        Args:
            edl_path: Percorso file .EDL
            ifc_path: Percorso file .IFC con geometrie
            crea_materiale: Se True, crea materiale di default

        Returns:
            Dict con info progetto
        """
        from edl_parser_v2 import EDLParserV2

        print(f"\nImportazione EDL con riferimento IFC...")

        parser = EDLParserV2(edl_path, ifc_path)
        project = parser.parse()

        print(parser.summary())

        # Aggiorna progetto
        self.project_name = project.nome
        self.project_path = Path(__file__).parent / "projects" / project.nome
        self.project_path.mkdir(parents=True, exist_ok=True)

        # Crea materiale
        if crea_materiale:
            self.materiale('mat_muratura', 'MATTONI_PIENI', 'BUONA')

        # Importa pareti con geometrie precise
        pareti_data = parser.to_connector_format()
        for nome, p in pareti_data.items():
            self.pareti[nome] = p
            if crea_materiale:
                self.pareti[nome]['materiale'] = 'mat_muratura'

        # Salva riferimento
        self._edl_project = project

        print(f"\nProgetto importato con geometrie IFC:")
        print(f"  {len(self.pareti)} pareti con coordinate precise")
        print(f"  {project.n_maschi} maschi")
        print(f"  {project.n_fasce} fasce")

        return {
            'nome': project.nome,
            'n_pareti': len(self.pareti),
            'n_maschi': project.n_maschi,
            'n_fasce': project.n_fasce,
            'piani': project.piani
        }

    def import_ifc(self, filepath: str, crea_materiale: bool = True) -> Dict:
        """
        Importa progetto da file IFC con geometrie precise.

        Args:
            filepath: Percorso file .IFC
            crea_materiale: Se True, crea materiale di default

        Returns:
            Dict con info progetto importato
        """
        from ifc_parser import IFCParser

        print(f"\nImportazione file IFC: {filepath}")

        parser = IFCParser(filepath)
        project = parser.parse()

        print(parser.summary())

        # Aggiorna nome progetto
        self.project_name = project.nome
        self.project_path = Path(__file__).parent / "projects" / project.nome
        self.project_path.mkdir(parents=True, exist_ok=True)

        # Crea materiale di default
        if crea_materiale:
            self.materiale('mat_ifc', 'MATTONI_PIENI', 'BUONA')

        # Importa pareti con geometria precisa
        pareti_data = parser.to_connector_format()

        for nome, p in pareti_data.items():
            self.pareti[nome] = p
            if crea_materiale:
                self.pareti[nome]['materiale'] = 'mat_ifc'

        # Salva aperture per visualizzazione
        self._ifc_aperture = {nome: p.get('aperture', []) for nome, p in pareti_data.items()}
        self._ifc_project = project

        print(f"\nProgetto '{project.nome}' importato da IFC:")
        print(f"  {len(self.pareti)} pareti")
        print(f"  {len(project.aperture)} aperture")
        print(f"  {len(project.solai)} solai")
        print(f"  {len(project.piani)} piani")

        return {
            'nome': project.nome,
            'n_pareti': len(self.pareti),
            'n_aperture': len(project.aperture),
            'n_solai': len(project.solai),
            'n_piani': len(project.piani),
            'bbox': project.bbox
        }

    def vista3d_ifc(self, apri_browser: bool = True) -> str:
        """
        Visualizza progetto IFC con posizioni reali dal modello BIM.

        Returns:
            Percorso file HTML
        """
        from viewer3d import MuraturaViewer3D
        import webbrowser

        if not hasattr(self, '_ifc_project'):
            print("Nessun progetto IFC caricato. Usa import_ifc() prima.")
            return ""

        project = self._ifc_project
        viewer = MuraturaViewer3D()

        print(f"\nGenerazione vista 3D da IFC - {len(project.pareti)} pareti...")

        # Aggiungi pareti con posizioni reali
        for parete in project.pareti:
            # Trova aperture
            aperture = []
            for ap in project.aperture:
                if ap.parete_id == parete.id:
                    aperture.append({
                        'x': ap.x - parete.x,
                        'y': ap.z - parete.z,
                        'w': ap.larghezza,
                        'h': ap.altezza,
                        'tipo': ap.tipo
                    })

            viewer.add_parete(
                nome=parete.nome,
                x=parete.x,
                y=parete.y,
                z=parete.z,
                lunghezza=parete.lunghezza,
                altezza=parete.altezza,
                spessore=parete.spessore,
                angolo=parete.angolo,
                aperture=aperture
            )

        viewer.build_figure(f"Modello 3D IFC - {project.nome}")

        html_path = self.project_path / f"{project.nome}_ifc_3d.html"
        viewer.save_html(str(html_path))

        if apri_browser:
            webbrowser.open(f"file://{html_path}")

        print(f"Vista 3D IFC salvata: {html_path}")
        return str(html_path)

    def vista3d_accurata(self, filepath_ifc: str = None,
                         pareti: bool = True, solai: bool = True,
                         travi: bool = True, aperture: bool = False,
                         apri_browser: bool = True) -> str:
        """
        Visualizza modello IFC con mesh reali ad alta precisione.

        Args:
            filepath_ifc: Percorso file IFC (usa ultimo importato se None)
            pareti: Mostra pareti
            solai: Mostra solai
            travi: Mostra travi
            aperture: Mostra aperture
            apri_browser: Apri nel browser

        Returns:
            Percorso file HTML
        """
        from viewer3d_ifc import IFCViewer3D

        if filepath_ifc is None:
            if hasattr(self, '_ifc_project'):
                filepath_ifc = self._ifc_project.filepath
            else:
                print("Nessun file IFC. Specifica il percorso o usa import_ifc() prima.")
                return ""

        print(f"\nGenerazione vista 3D accurata da: {filepath_ifc}")

        viewer = IFCViewer3D(filepath_ifc)
        viewer.build_model(
            include_walls=pareti,
            include_slabs=solai,
            include_beams=travi,
            include_openings=aperture
        )

        html_path = self.project_path / f"{self.project_name}_3d_accurata.html"
        viewer.save_html(str(html_path))

        if apri_browser:
            import webbrowser
            webbrowser.open(f"file://{html_path}")

        return str(html_path)

    def vista3d(self, layout: str = 'auto', apri_browser: bool = True) -> str:
        """
        Visualizza il progetto in 3D nel browser.

        Args:
            layout: Disposizione pareti ('auto', 'linear', 'square', 'L')
            apri_browser: Se True, apre automaticamente nel browser

        Returns:
            Percorso file HTML generato
        """
        from viewer3d import MuraturaViewer3D, visualizza_progetto

        if not self.pareti:
            print("Nessuna parete definita. Importa un progetto o crea pareti.")
            return ""

        print(f"\nGenerazione vista 3D - {len(self.pareti)} pareti...")

        html_path = visualizza_progetto(
            self.pareti,
            nome=self.project_name,
            layout=layout,
            apri_browser=apri_browser
        )

        print(f"Vista 3D salvata: {html_path}")
        return html_path

    def vista3d_dettagliata(self, aperture: Dict[str, List] = None,
                            apri_browser: bool = True) -> str:
        """
        Visualizza progetto con aperture e dettagli.

        Args:
            aperture: Dict {nome_parete: [{x, y, w, h, tipo}, ...]}
            apri_browser: Se True, apre nel browser

        Returns:
            Percorso file HTML
        """
        from viewer3d import MuraturaViewer3D

        viewer = MuraturaViewer3D()

        # Calcola layout automatico
        x_offset = 0
        y_offset = 0
        max_length = max((p['length'] for p in self.pareti.values()), default=5)

        for i, (nome, p) in enumerate(self.pareti.items()):
            # Disponi pareti in griglia
            row = i // 4
            col = i % 4

            if col < 2:
                # Pareti lungo X
                viewer.add_parete(
                    nome=nome,
                    x=col * (max_length + 1),
                    y=row * (max_length + 1),
                    z=0,
                    lunghezza=p['length'],
                    altezza=p['height'],
                    spessore=p['thickness'],
                    angolo=0,
                    aperture=aperture.get(nome, []) if aperture else []
                )
            else:
                # Pareti lungo Y
                viewer.add_parete(
                    nome=nome,
                    x=(col-2) * (max_length + 1) + max_length,
                    y=row * (max_length + 1),
                    z=0,
                    lunghezza=p['length'],
                    altezza=p['height'],
                    spessore=p['thickness'],
                    angolo=90,
                    aperture=aperture.get(nome, []) if aperture else []
                )

        viewer.build_figure(f"Modello 3D Dettagliato - {self.project_name}")

        html_path = self.project_path / f"{self.project_name}_3d_dettagliato.html"
        viewer.save_html(str(html_path))

        if apri_browser:
            import webbrowser
            webbrowser.open(f"file://{html_path}")

        return str(html_path)

    def esporta(self, nome_analisi: str, formato: str = 'json',
                percorso: str = None) -> str:
        """
        Esporta risultati di un'analisi.

        Args:
            nome_analisi: Nome dell'analisi
            formato: 'json', 'csv', 'txt'
            percorso: Percorso file output (opzionale)

        Returns:
            Percorso file creato
        """
        if nome_analisi not in self.risultati:
            print(f"Analisi '{nome_analisi}' non trovata")
            return ""

        results = self.risultati[nome_analisi]

        if percorso is None:
            percorso = self.project_path / f"{nome_analisi}.{formato}"
        else:
            percorso = Path(percorso)

        if formato == 'json':
            with open(percorso, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        elif formato == 'csv':
            if 'curve' in results:
                with open(percorso, 'w', encoding='utf-8') as f:
                    f.write("step,base_shear_kN,drift_percent,displacement_mm\n")
                    for i, pt in enumerate(results['curve']):
                        f.write(f"{i+1},{pt['base_shear']:.2f},{pt['top_drift']*100:.4f},{pt['roof_displacement']*1000:.3f}\n")

        elif formato == 'txt':
            with open(percorso, 'w', encoding='utf-8') as f:
                f.write(f"RISULTATI ANALISI: {nome_analisi}\n")
                f.write("=" * 50 + "\n\n")
                f.write(json.dumps(results, indent=2, ensure_ascii=False, default=str))

        print(f"Risultati esportati in: {percorso}")
        return str(percorso)

    def report(self, percorso: str = None) -> str:
        """
        Genera report completo del progetto.

        Args:
            percorso: Percorso file output (opzionale)

        Returns:
            Testo del report
        """
        if percorso is None:
            percorso = self.project_path / f"report_{self.project_name}.txt"

        lines = []
        lines.append("=" * 70)
        lines.append(f"REPORT PROGETTO: {self.project_name}")
        lines.append(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 70)

        # Materiali
        lines.append("\n\nMATERIALI")
        lines.append("-" * 70)
        for nome, mat in self.materiali.items():
            lines.append(f"\n{nome}:")
            lines.append(f"  Tipo: {mat.material_type}")
            lines.append(f"  fcm = {mat.fcm:.2f} MPa")
            lines.append(f"  E = {mat.E:.0f} MPa")
            lines.append(f"  tau0 = {mat.tau0:.3f} MPa")

        # Pareti
        lines.append("\n\nPARETI")
        lines.append("-" * 70)
        for nome, p in self.pareti.items():
            lines.append(f"\n{nome}:")
            lines.append(f"  Dimensioni: {p['length']} x {p['height']} x {p['thickness']} m")
            lines.append(f"  Piani: {p['n_floors']}")
            lines.append(f"  Materiale: {p['materiale']}")
            if p['floor_masses']:
                masses = ", ".join([f"P{k}:{v}kg" for k, v in p['floor_masses'].items()])
                lines.append(f"  Masse: {masses}")

        # Analisi
        lines.append("\n\nANALISI")
        lines.append("-" * 70)
        for nome, an in self.analisi.items():
            lines.append(f"\n{nome}:")
            lines.append(f"  Tipo: {an['type']}")
            lines.append(f"  Parete: {an['parete']}")

            if nome in self.risultati:
                res = self.risultati[nome]
                if 'curve' in res and res['curve']:
                    ultimo = res['curve'][-1]
                    lines.append(f"  Base shear max: {ultimo['base_shear']:.1f} kN")
                    lines.append(f"  Drift max: {ultimo['top_drift']*100:.2f}%")
                if 'frequencies' in res:
                    lines.append(f"  Periodo fondamentale: {res['periods'][0]:.3f} s")

        lines.append("\n\n" + "=" * 70)
        lines.append("Fine report")
        lines.append("=" * 70)

        report_text = "\n".join(lines)

        with open(percorso, 'w', encoding='utf-8') as f:
            f.write(report_text)

        print(f"Report salvato in: {percorso}")
        return report_text


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Test rapido
    m = Muratura("test_project")
    m.help()
