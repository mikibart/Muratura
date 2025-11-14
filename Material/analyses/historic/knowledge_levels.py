"""
Module: historic/knowledge_levels.py
Sistema Knowledge Levels per edifici esistenti in muratura

Questo modulo implementa il sistema di livelli di conoscenza (LC) e fattori
di confidenza (FC) per la valutazione di edifici esistenti secondo NTC 2018.

Normativa di Riferimento:
- NTC 2018 Cap. 8: Costruzioni esistenti
- Circolare NTC 2019 §C8.5.4: Livelli di conoscenza e fattori di confidenza
- Linee Guida Beni Culturali 2011

Sistema Livelli di Conoscenza:
- LC1 (Conoscenza Limitata): FC = 1.35
  - Geometria: Rilievo sommario
  - Dettagli: Limitata verifica
  - Materiali: Prove limitate

- LC2 (Conoscenza Adeguata): FC = 1.20
  - Geometria: Rilievo completo
  - Dettagli: Verifica estesa
  - Materiali: Prove estese

- LC3 (Conoscenza Accurata): FC = 1.00
  - Geometria: Rilievo completo e dettagliato
  - Dettagli: Verifiche esaustive
  - Materiali: Prove esaustive

Il fattore di confidenza FC riduce i valori caratteristici dei materiali:
    f_d = f_k / (γ_M × FC)

dove:
- f_k: Resistenza caratteristica del materiale
- γ_M: Coefficiente parziale di sicurezza del materiale
- FC: Fattore di confidenza (1.00 ÷ 1.35)

References:
    - NTC 2018 §8.5.4
    - Circolare NTC 2019 §C8.5.4
    - Linee Guida Beni Culturali 2011
    - CNR-DT 212/2013

Examples:
    >>> from Material.analyses.historic.knowledge_levels import (
    ...     KnowledgeAssessment, InvestigationLevel
    ... )
    >>> # Valutazione edificio storico
    >>> assessment = KnowledgeAssessment()
    >>> assessment.set_geometry_investigation('complete')
    >>> assessment.set_details_investigation('extended')
    >>> assessment.set_materials_investigation('limited')
    >>>
    >>> result = assessment.calculate_knowledge_level()
    >>> print(f"Livello conoscenza: {result['level']}")
    >>> print(f"Fattore confidenza: {result['FC']}")
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Literal
from enum import Enum
import numpy as np


# ============================================================================
# ENUMS E COSTANTI
# ============================================================================

class KnowledgeLevel(Enum):
    """Livelli di conoscenza (NTC 2018 §C8.5.4)"""
    LC1 = 'LC1'  # Conoscenza Limitata
    LC2 = 'LC2'  # Conoscenza Adeguata
    LC3 = 'LC3'  # Conoscenza Accurata


class InvestigationLevel(Enum):
    """Livelli di approfondimento indagini"""
    LIMITED = 'limited'        # Limitate
    EXTENDED = 'extended'      # Estese
    EXHAUSTIVE = 'exhaustive'  # Esaustive


# Fattori di confidenza (NTC 2018 Tab. C8.5.IV)
CONFIDENCE_FACTORS = {
    KnowledgeLevel.LC1: 1.35,  # Conoscenza Limitata
    KnowledgeLevel.LC2: 1.20,  # Conoscenza Adeguata
    KnowledgeLevel.LC3: 1.00,  # Conoscenza Accurata
}


# Descrizioni livelli indagine (NTC 2018 Tab. C8.5.IV)
INVESTIGATION_DESCRIPTIONS = {
    'geometry': {
        'limited': 'Rilievo sommario: planimetrie disponibili, verifiche limitate in situ',
        'extended': 'Rilievo completo: planimetrie verificate, ispezioni estese',
        'exhaustive': 'Rilievo completo e dettagliato: rilievo geometrico completo, aperture saggi'
    },
    'details': {
        'limited': 'Verifiche limitate su dettagli costruttivi e collegamenti',
        'extended': 'Verifiche estese su dettagli costruttivi mediante saggi',
        'exhaustive': 'Verifiche esaustive su dettagli costruttivi mediante saggi e/o prove in situ'
    },
    'materials': {
        'limited': 'Prove limitate: dati bibliografici, prove in situ limitate',
        'extended': 'Prove estese: dati bibliografici + prove in situ estese',
        'exhaustive': 'Prove esaustive: dati sperimentali estesi + prove di laboratorio'
    }
}


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class InvestigationData:
    """
    Dati indagini conoscitive.

    Attributes:
        geometry_level: Livello rilievo geometrico
        details_level: Livello verifica dettagli costruttivi
        materials_level: Livello prove materiali
        notes: Note aggiuntive
    """
    geometry_level: Optional[InvestigationLevel] = None
    details_level: Optional[InvestigationLevel] = None
    materials_level: Optional[InvestigationLevel] = None
    notes: str = ""

    def is_complete(self) -> bool:
        """Verifica se tutte le categorie sono state valutate"""
        return all([
            self.geometry_level is not None,
            self.details_level is not None,
            self.materials_level is not None
        ])


@dataclass
class MaterialProperties:
    """
    Proprietà materiali con fattore di confidenza applicato.

    Attributes:
        f_m_k: Resistenza caratteristica a compressione muratura [MPa]
        f_v0_k: Resistenza caratteristica a taglio [MPa]
        tau_0_k: Resistenza caratteristica a taglio puro [MPa]
        E: Modulo elastico [MPa]
        G: Modulo di taglio [MPa]
        w: Peso specifico [kN/m³]
        FC: Fattore di confidenza applicato
    """
    f_m_k: float  # MPa
    f_v0_k: Optional[float] = None  # MPa
    tau_0_k: Optional[float] = None  # MPa
    E: Optional[float] = None  # MPa
    G: Optional[float] = None  # MPa
    w: float = 18.0  # kN/m³

    def apply_confidence_factor(self, FC: float) -> 'MaterialProperties':
        """
        Applica fattore di confidenza alle resistenze.

        Args:
            FC: Fattore di confidenza

        Returns:
            Nuove proprietà con FC applicato
        """
        return MaterialProperties(
            f_m_k=self.f_m_k / FC,
            f_v0_k=self.f_v0_k / FC if self.f_v0_k else None,
            tau_0_k=self.tau_0_k / FC if self.tau_0_k else None,
            E=self.E,  # Modulo elastico non ridotto
            G=self.G,  # Modulo taglio non ridotto
            w=self.w
        )


# ============================================================================
# CLASSE PRINCIPALE KNOWLEDGE ASSESSMENT
# ============================================================================

class KnowledgeAssessment:
    """
    Valutazione livello di conoscenza edificio esistente.

    Implementa il sistema di knowledge levels secondo NTC 2018 §C8.5.4
    per determinare il fattore di confidenza FC da applicare alle
    resistenze dei materiali.

    Attributes:
        investigation_data: Dati indagini conoscitive
        building_type: Tipologia edificio (residenziale, monumentale, etc.)
        construction_period: Periodo costruzione
    """

    def __init__(
        self,
        building_type: str = 'masonry',
        construction_period: Optional[str] = None
    ):
        """
        Inizializza valutazione conoscenza.

        Args:
            building_type: Tipologia edificio
            construction_period: Periodo costruzione (es. '1800-1900')
        """
        self.building_type = building_type
        self.construction_period = construction_period
        self.investigation_data = InvestigationData()
        self._knowledge_level: Optional[KnowledgeLevel] = None
        self._FC: Optional[float] = None

    # ========================================================================
    # IMPOSTAZIONE LIVELLI INDAGINE
    # ========================================================================

    def set_geometry_investigation(
        self,
        level: Literal['limited', 'extended', 'exhaustive']
    ) -> None:
        """
        Imposta livello rilievo geometrico.

        Args:
            level: Livello indagine geometrica
        """
        self.investigation_data.geometry_level = InvestigationLevel(level)
        self._reset_results()

    def set_details_investigation(
        self,
        level: Literal['limited', 'extended', 'exhaustive']
    ) -> None:
        """
        Imposta livello verifica dettagli costruttivi.

        Args:
            level: Livello verifica dettagli
        """
        self.investigation_data.details_level = InvestigationLevel(level)
        self._reset_results()

    def set_materials_investigation(
        self,
        level: Literal['limited', 'extended', 'exhaustive']
    ) -> None:
        """
        Imposta livello prove materiali.

        Args:
            level: Livello prove materiali
        """
        self.investigation_data.materials_level = InvestigationLevel(level)
        self._reset_results()

    def _reset_results(self) -> None:
        """Reset risultati calcolati"""
        self._knowledge_level = None
        self._FC = None

    # ========================================================================
    # CALCOLO LIVELLO DI CONOSCENZA
    # ========================================================================

    def calculate_knowledge_level(self) -> Dict[str, any]:
        """
        Calcola livello di conoscenza secondo NTC 2018 Tab. C8.5.IV.

        Returns:
            Dictionary con:
            - 'level': Livello conoscenza (LC1/LC2/LC3)
            - 'FC': Fattore di confidenza (1.00-1.35)
            - 'geometry': Livello geometria
            - 'details': Livello dettagli
            - 'materials': Livello materiali
            - 'description': Descrizione livello

        Note:
            Tabella NTC 2018 C8.5.IV:
            LC3: Geometria completa + Dettagli esaustivi + Materiali esaustivi
            LC2: Geometria completa + Dettagli estesi + Materiali estesi
            LC1: Altri casi
        """
        if not self.investigation_data.is_complete():
            raise ValueError(
                "Dati indagini incompleti. Impostare geometry, details e materials."
            )

        geom = self.investigation_data.geometry_level.value
        details = self.investigation_data.details_level.value
        materials = self.investigation_data.materials_level.value

        # Determinazione livello secondo Tab. C8.5.IV NTC 2018
        if (geom == 'exhaustive' and
            details == 'exhaustive' and
            materials == 'exhaustive'):
            # LC3: Conoscenza Accurata
            level = KnowledgeLevel.LC3

        elif (geom in ['extended', 'exhaustive'] and
              details == 'extended' and
              materials == 'extended'):
            # LC2: Conoscenza Adeguata
            level = KnowledgeLevel.LC2

        else:
            # LC1: Conoscenza Limitata (default per tutti gli altri casi)
            level = KnowledgeLevel.LC1

        FC = CONFIDENCE_FACTORS[level]

        # Salva risultati
        self._knowledge_level = level
        self._FC = FC

        return {
            'level': level.value,
            'FC': FC,
            'geometry': geom,
            'details': details,
            'materials': materials,
            'description': self._get_level_description(level)
        }

    def _get_level_description(self, level: KnowledgeLevel) -> str:
        """Ottieni descrizione livello conoscenza"""
        descriptions = {
            KnowledgeLevel.LC3: (
                "Conoscenza Accurata: Geometria completa e dettagliata, "
                "verifiche esaustive su dettagli costruttivi, prove esaustive sui materiali. "
                "FC = 1.00"
            ),
            KnowledgeLevel.LC2: (
                "Conoscenza Adeguata: Geometria completa, verifiche estese su dettagli "
                "costruttivi, prove estese sui materiali. FC = 1.20"
            ),
            KnowledgeLevel.LC1: (
                "Conoscenza Limitata: Indagini limitate su uno o più aspetti "
                "(geometria, dettagli, materiali). FC = 1.35"
            )
        }
        return descriptions[level]

    # ========================================================================
    # APPLICAZIONE FATTORE DI CONFIDENZA
    # ========================================================================

    def apply_to_material(
        self,
        material_properties: MaterialProperties
    ) -> MaterialProperties:
        """
        Applica fattore di confidenza a proprietà materiali.

        Args:
            material_properties: Proprietà materiali caratteristiche

        Returns:
            Proprietà materiali con FC applicato

        Note:
            Le resistenze sono ridotte dal fattore FC secondo:
            f_d = f_k / (γ_M × FC)
        """
        if self._FC is None:
            result = self.calculate_knowledge_level()
            FC = result['FC']
        else:
            FC = self._FC

        return material_properties.apply_confidence_factor(FC)

    # ========================================================================
    # RACCOMANDAZIONI INDAGINI
    # ========================================================================

    def get_investigation_recommendations(self) -> Dict[str, List[str]]:
        """
        Genera raccomandazioni per migliorare livello di conoscenza.

        Returns:
            Dictionary con raccomandazioni per category
        """
        if not self.investigation_data.is_complete():
            return {
                'error': ['Completare prima la valutazione delle indagini esistenti']
            }

        recommendations = {
            'geometry': [],
            'details': [],
            'materials': [],
            'general': []
        }

        geom = self.investigation_data.geometry_level.value
        details = self.investigation_data.details_level.value
        materials = self.investigation_data.materials_level.value

        # Raccomandazioni geometria
        if geom == 'limited':
            recommendations['geometry'].append(
                "Completare rilievo geometrico con misure in situ"
            )
            recommendations['geometry'].append(
                "Verificare planimetrie disponibili"
            )
        elif geom == 'extended':
            recommendations['geometry'].append(
                "Eseguire rilievo geometrico dettagliato"
            )
            recommendations['geometry'].append(
                "Aprire saggi per verificare spessori murari"
            )

        # Raccomandazioni dettagli
        if details == 'limited':
            recommendations['details'].append(
                "Eseguire saggi per verificare dettagli costruttivi"
            )
            recommendations['details'].append(
                "Verificare collegamenti (architravi, solai)"
            )
        elif details == 'extended':
            recommendations['details'].append(
                "Estendere saggi per verifiche esaustive"
            )
            recommendations['details'].append(
                "Eseguire prove in situ su collegamenti"
            )

        # Raccomandazioni materiali
        if materials == 'limited':
            recommendations['materials'].append(
                "Eseguire prove in situ (martinetti piatti, penetrometriche)"
            )
            recommendations['materials'].append(
                "Prelevare campioni per prove di laboratorio"
            )
        elif materials == 'extended':
            recommendations['materials'].append(
                "Estendere campagna prove in situ"
            )
            recommendations['materials'].append(
                "Eseguire prove di laboratorio su campioni rappresentativi"
            )

        # Raccomandazioni generali per migliorare LC
        current_level = self._knowledge_level
        if current_level == KnowledgeLevel.LC1:
            recommendations['general'].append(
                f"Livello attuale: LC1 (FC={CONFIDENCE_FACTORS[KnowledgeLevel.LC1]})"
            )
            recommendations['general'].append(
                "Per raggiungere LC2: estendere indagini su tutte le categorie"
            )
        elif current_level == KnowledgeLevel.LC2:
            recommendations['general'].append(
                f"Livello attuale: LC2 (FC={CONFIDENCE_FACTORS[KnowledgeLevel.LC2]})"
            )
            recommendations['general'].append(
                "Per raggiungere LC3: prove esaustive su tutte le categorie"
            )
        else:
            recommendations['general'].append(
                f"Livello attuale: LC3 (FC={CONFIDENCE_FACTORS[KnowledgeLevel.LC3]})"
            )
            recommendations['general'].append(
                "Massimo livello di conoscenza raggiunto"
            )

        return recommendations

    # ========================================================================
    # REPORT
    # ========================================================================

    def generate_report(self) -> str:
        """
        Genera report valutazione livello di conoscenza.

        Returns:
            Report formattato
        """
        if not self.investigation_data.is_complete():
            return "ERROR: Dati indagini incompleti. Completare valutazione."

        result = self.calculate_knowledge_level()

        report = []
        report.append("=" * 70)
        report.append("VALUTAZIONE LIVELLO DI CONOSCENZA - NTC 2018 §C8.5.4")
        report.append("=" * 70)
        report.append("")

        # EDIFICIO
        report.append("EDIFICIO:")
        report.append(f"  Tipologia: {self.building_type}")
        if self.construction_period:
            report.append(f"  Periodo costruzione: {self.construction_period}")
        report.append("")

        # INDAGINI ESEGUITE
        report.append("INDAGINI ESEGUITE (Tab. C8.5.IV NTC 2018):")
        report.append("")

        report.append("1. RILIEVO GEOMETRICO:")
        report.append(f"   Livello: {result['geometry'].upper()}")
        report.append(f"   {INVESTIGATION_DESCRIPTIONS['geometry'][result['geometry']]}")
        report.append("")

        report.append("2. DETTAGLI COSTRUTTIVI:")
        report.append(f"   Livello: {result['details'].upper()}")
        report.append(f"   {INVESTIGATION_DESCRIPTIONS['details'][result['details']]}")
        report.append("")

        report.append("3. PROPRIETÀ MATERIALI:")
        report.append(f"   Livello: {result['materials'].upper()}")
        report.append(f"   {INVESTIGATION_DESCRIPTIONS['materials'][result['materials']]}")
        report.append("")

        # RISULTATO
        report.append("=" * 70)
        report.append(f"LIVELLO DI CONOSCENZA: {result['level']}")
        report.append(f"FATTORE DI CONFIDENZA: FC = {result['FC']:.2f}")
        report.append("=" * 70)
        report.append("")
        report.append(f"{result['description']}")
        report.append("")

        # IMPATTO SU VERIFICHE
        report.append("IMPATTO SULLE VERIFICHE STRUTTURALI:")
        report.append(f"  Le resistenze dei materiali saranno ridotte di FC = {result['FC']:.2f}")
        report.append(f"  Esempio: f_m_d = f_m_k / (γ_M × {result['FC']:.2f})")
        report.append("")

        if result['FC'] > 1.0:
            impact_percent = (result['FC'] - 1.0) * 100
            report.append(f"  ⚠️  Riduzione resistenze: -{impact_percent:.0f}% rispetto a LC3")
            report.append("")

        # RACCOMANDAZIONI
        recommendations = self.get_investigation_recommendations()

        if any(recommendations.values()):
            report.append("RACCOMANDAZIONI PER MIGLIORARE IL LIVELLO DI CONOSCENZA:")
            report.append("")

            for category, recs in recommendations.items():
                if recs and category != 'general':
                    report.append(f"{category.upper()}:")
                    for rec in recs:
                        report.append(f"  - {rec}")
                    report.append("")

            if recommendations['general']:
                report.append("GENERALE:")
                for rec in recommendations['general']:
                    report.append(f"  {rec}")
                report.append("")

        report.append("=" * 70)
        report.append("NOTE:")
        report.append("  - Valutazione secondo NTC 2018 §8.5.4 e Circolare §C8.5.4")
        report.append("  - Il fattore FC riduce le resistenze caratteristiche dei materiali")
        report.append("  - Per edifici vincolati consultare Linee Guida Beni Culturali 2011")
        report.append("")

        return "\n".join(report)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'KnowledgeAssessment',
    'KnowledgeLevel',
    'InvestigationLevel',
    'InvestigationData',
    'MaterialProperties',
    'CONFIDENCE_FACTORS',
    'INVESTIGATION_DESCRIPTIONS',
]
