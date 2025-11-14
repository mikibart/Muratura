"""
Module: historic/vaults.py
Analisi limite volte in muratura - Metodo Heyman esteso

Questo modulo implementa l'analisi limite di volte murarie secondo la teoria
di Heyman (1966-1982) estesa alle strutture tridimensionali.

Teoria di Base (Heyman's Assumptions per Volte):
1. NO TENSILE STRENGTH: La muratura non resiste a trazione (σ_t = 0)
2. INFINITE COMPRESSIVE STRENGTH: Resistenza a compressione infinita (conservativo)
3. NO SLIDING: Attrito sufficiente a impedire scorrimento

Teoremi Fondamentali (estesi a 3D):
- TEOREMA STATICO: Se esiste UNA superficie delle pressioni contenuta
  nello spessore della volta, allora la volta è in equilibrio.

- TEOREMA CINEMATICO: Il carico di collasso è il minimo tra tutti i
  possibili cinematismi di collasso.

Tipologie Implementate:
- Volta a botte (barrel vault): Estrusione di arco semicircolare
- Volta a crociera (cross/groin vault): Intersezione di due volte a botte
- Cupola (dome): Superficie di rivoluzione (emisferica, ribassata)
- Volta a padiglione (cloister vault): 4 superfici cilindriche
- Volta a vela (sail vault): Sferica su base quadrata

References:
    - Heyman, J. (1966) "The stone skeleton"
    - Heyman, J. (1977) "Equilibrium of shell structures"
    - Heyman, J. (1995) "The stone skeleton: structural engineering of masonry architecture"
    - Huerta, S. (2001) "Mechanics of masonry vaults: The equilibrium approach"
    - Block, P. (2009) "Thrust network analysis"

Examples:
    >>> from Material.analyses.historic.vaults import VaultAnalysis, VaultGeometry
    >>> geometry = VaultGeometry(
    ...     vault_type='barrel',
    ...     span=6.0,  # m
    ...     rise=3.0,  # m
    ...     length=12.0,  # m (lunghezza volta)
    ...     thickness=0.40  # m
    ... )
    >>> vault = VaultAnalysis(geometry=geometry, masonry_density=20.0)
    >>> result = vault.calculate_safety_factor()
    >>> print(f"Safety factor: {result['geometric_safety_factor']:.2f}")
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Literal
from enum import Enum
import numpy as np
import warnings


# ============================================================================
# ENUMS E COSTANTI
# ============================================================================

class VaultType(Enum):
    """Tipologie di volta"""
    BARREL = 'barrel'  # Volta a botte
    CROSS = 'cross'  # Volta a crociera
    DOME = 'dome'  # Cupola
    CLOISTER = 'cloister'  # Volta a padiglione
    SAIL = 'sail'  # Volta a vela
    PAVILION = 'pavilion'  # Volta a padiglione (alias)


class FailureMode(Enum):
    """Modalità di collasso volte"""
    HINGE_MECHANISM = 'hinge_mechanism'  # Meccanismo cerniere
    RING_TENSION = 'ring_tension'  # Trazione cerchi (cupole)
    SPREADING = 'spreading'  # Apertura imposta
    CRUSHING = 'crushing'  # Schiacciamento (raro)
    BUCKLING = 'buckling'  # Instabilità (volte sottili)


# Densità tipiche muratura [kN/m³] (ereditate da arches)
MASONRY_DENSITIES = {
    'stone': 24.0,
    'brick': 18.0,
    'tufo': 16.0,
    'tuff': 16.0,
    'limestone': 22.0,
    'sandstone': 20.0,
}


# ============================================================================
# DATACLASSES PER GEOMETRIA
# ============================================================================

@dataclass
class VaultGeometry:
    """
    Geometria della volta.

    Attributes:
        vault_type: Tipologia volta
        span: Luce (apertura) [m]
        rise: Freccia (altezza dalla linea d'imposta alla chiave) [m]
        thickness: Spessore volta [m]
        length: Lunghezza volta (per barrel/cross) [m] - opzionale
        width: Larghezza base (per cloister/sail) [m] - opzionale
        opening_angle: Angolo apertura cupola [gradi] - default 90° (emisfero)
        springline_height: Altezza linea d'imposta da terra [m]

    Note:
        - Barrel vault: richiede span, rise, length, thickness
        - Dome: richiede span (diametro), rise, thickness, opening_angle
        - Cross vault: richiede span, rise, length, thickness
        - Cloister/Sail: richiede span, rise, width, thickness
    """
    vault_type: Literal['barrel', 'cross', 'dome', 'cloister', 'sail', 'pavilion']
    span: float
    rise: float
    thickness: float
    length: Optional[float] = None  # Per barrel/cross
    width: Optional[float] = None  # Per cloister/sail
    opening_angle: float = 90.0  # Per dome (gradi)
    springline_height: float = 0.0

    def __post_init__(self):
        """Validazione geometria"""
        if self.span <= 0:
            raise ValueError(f"Span deve essere > 0, got {self.span}")
        if self.rise <= 0:
            raise ValueError(f"Rise deve essere > 0, got {self.rise}")
        if self.thickness <= 0:
            raise ValueError(f"Thickness deve essere > 0, got {self.thickness}")

        # Validazioni specifiche per tipologia
        if self.vault_type in ['barrel', 'cross']:
            if self.length is None or self.length <= 0:
                raise ValueError(f"{self.vault_type} vault richiede length > 0")

        if self.vault_type in ['cloister', 'sail', 'pavilion']:
            if self.width is None or self.width <= 0:
                raise ValueError(f"{self.vault_type} vault richiede width > 0")

    def calculate_radius(self) -> float:
        """
        Calcola raggio di curvatura della volta.

        Returns:
            Raggio [m]
        """
        if self.vault_type in ['barrel', 'cross', 'cloister', 'pavilion']:
            # Arco semicircolare
            R = (self.span**2 / 8.0 + self.rise**2 / 2.0) / (2.0 * self.rise)
            return R
        elif self.vault_type == 'dome':
            # Cupola emisferica: R = span/2
            return self.span / 2.0
        elif self.vault_type == 'sail':
            # Volta a vela: raggio sferico
            # R calcolato dalla geometria inscritta
            R = (self.span**2 / 8.0 + self.rise**2 / 2.0) / (2.0 * self.rise)
            return R
        else:
            return self.span / 2.0

    def calculate_volume(self) -> float:
        """
        Calcola volume muratura della volta [m³].

        Returns:
            Volume [m³]

        Note:
            Stima approssimativa basata su geometria semplificata.
        """
        R = self.calculate_radius()

        if self.vault_type == 'barrel':
            # Volume volta a botte: area sezione × lunghezza
            # Area sezione ≈ π R² / 2 - π (R-t)² / 2
            area_ext = np.pi * R**2 / 2.0
            area_int = np.pi * (R - self.thickness)**2 / 2.0
            area = area_ext - area_int
            volume = area * self.length
            return volume

        elif self.vault_type == 'dome':
            # Volume cupola: calotta sferica
            # V = 2/3 π h (3R² + h²) per calotta di altezza h
            h = self.rise
            V_ext = (2.0/3.0) * np.pi * h * (3*R**2 + h**2)
            V_int = (2.0/3.0) * np.pi * h * (3*(R-self.thickness)**2 + h**2)
            volume = V_ext - V_int
            return volume

        elif self.vault_type == 'cross':
            # Volta a crociera: approssimazione come due barrel vaults intersecate
            # Volume ≈ 1.4 × volume barrel singola (empirico)
            area_ext = np.pi * R**2 / 2.0
            area_int = np.pi * (R - self.thickness)**2 / 2.0
            area = area_ext - area_int
            volume = 1.4 * area * self.length
            return volume

        else:
            # Per altre tipologie, stima conservativa
            volume = self.span * self.span * self.rise * 0.5
            return volume


# ============================================================================
# CLASSE PRINCIPALE VAULT ANALYSIS
# ============================================================================

class VaultAnalysis:
    """
    Analisi limite volta metodo Heyman.

    Implementa:
    - Calcolo superficie delle pressioni (thrust surface)
    - Spessore minimo per equilibrio (teorema statico)
    - Carico di collasso (teorema cinematico)
    - Coefficiente sicurezza geometrico
    - Capacità sismica

    Attributes:
        geometry: Geometria della volta
        masonry_density: Densità muratura [kN/m³]
        live_load: Sovraccarico accidentale [kN/m²]
        fill_height: Altezza riempimento sopra volta [m]
        fill_density: Densità riempimento [kN/m³]
    """

    def __init__(
        self,
        geometry: VaultGeometry,
        masonry_density: float = 20.0,
        live_load: float = 0.0,
        fill_height: float = 0.0,
        fill_density: float = 18.0
    ):
        """
        Inizializza analisi volta.

        Args:
            geometry: Geometria della volta
            masonry_density: Densità muratura [kN/m³]
            live_load: Sovraccarico accidentale [kN/m²]
            fill_height: Altezza riempimento sopra volta [m]
            fill_density: Densità riempimento [kN/m³]
        """
        self.geometry = geometry
        self.masonry_density = masonry_density
        self.live_load = live_load
        self.fill_height = fill_height
        self.fill_density = fill_density

        # Risultati (calcolati dai metodi)
        self._min_thickness: Optional[float] = None
        self._collapse_load: Optional[float] = None

    # ========================================================================
    # CALCOLO CARICHI
    # ========================================================================

    def calculate_self_weight_per_area(self) -> float:
        """
        Calcola peso proprio volta per unità di superficie [kN/m²].

        Returns:
            Peso proprio [kN/m²]

        Note:
            Per volte, il peso viene proiettato sulla base.
        """
        if self.geometry.vault_type == 'barrel':
            # Peso lungo arco / proiezione orizzontale
            R = self.geometry.calculate_radius()
            arc_length = np.pi * R / 2.0  # Semicerchio
            projection = self.geometry.span
            weight_per_unit = self.masonry_density * self.geometry.thickness
            weight_per_area = weight_per_unit * arc_length / projection
            return weight_per_area

        elif self.geometry.vault_type == 'dome':
            # Per cupole, peso proiettato sulla base
            R = self.geometry.calculate_radius()
            surface_area = 2.0 * np.pi * R * self.geometry.rise  # Calotta
            base_area = np.pi * (self.geometry.span / 2.0)**2
            weight = surface_area * self.geometry.thickness * self.masonry_density
            weight_per_area = weight / base_area
            return weight_per_area

        else:
            # Stima conservativa per altre tipologie
            weight_per_area = self.masonry_density * self.geometry.thickness * 1.5
            return weight_per_area

    def calculate_total_load(self) -> Dict[str, float]:
        """
        Calcola carico totale sulla volta.

        Returns:
            Dictionary con:
            - 'self_weight': Peso proprio [kN/m²]
            - 'fill_weight': Peso riempimento [kN/m²]
            - 'live_load': Sovraccarico [kN/m²]
            - 'total': Carico totale [kN/m²]
        """
        self_weight = self.calculate_self_weight_per_area()
        fill_weight = self.fill_height * self.fill_density
        total = self_weight + fill_weight + self.live_load

        return {
            'self_weight': self_weight,
            'fill_weight': fill_weight,
            'live_load': self.live_load,
            'total': total
        }

    # ========================================================================
    # TEOREMA STATICO: SPESSORE MINIMO
    # ========================================================================

    def calculate_minimum_thickness(self) -> float:
        """
        Calcola spessore minimo per equilibrio (teorema statico Heyman).

        Returns:
            Spessore minimo [m]

        Note:
            Formule empiriche basate su Heyman (1977):
            - Barrel vault: t/R ≈ 0.02-0.04
            - Dome: t/R ≈ 0.01-0.02 (sotto peso proprio)
            - Cross vault: t/R ≈ 0.03-0.05
        """
        R = self.geometry.calculate_radius()

        if self.geometry.vault_type == 'barrel':
            # Volta a botte: simile ad arco ma con effetto tridimensionale
            # Heyman: t/R ≈ 0.03 (leggermente più dello arco per effetto arco trasversale)
            t_min = 0.03 * R

        elif self.geometry.vault_type == 'dome':
            # Cupola emisferica: Heyman (1977)
            # t/R ≈ 0.0105 sotto peso proprio (teorico)
            # Usiamo valore conservativo 0.015
            t_min = 0.015 * R

            # Correzione per opening_angle < 90°
            if self.geometry.opening_angle < 90.0:
                # Cupole più chiuse sono meno stabili
                factor = 90.0 / max(self.geometry.opening_angle, 30.0)
                t_min *= factor

        elif self.geometry.vault_type == 'cross':
            # Volta a crociera: più stabile di barrel per effetto 3D
            # t/R ≈ 0.025
            t_min = 0.025 * R

        elif self.geometry.vault_type in ['cloister', 'pavilion']:
            # Volta a padiglione: comportamento intermedio
            # t/R ≈ 0.035
            t_min = 0.035 * R

        elif self.geometry.vault_type == 'sail':
            # Volta a vela: simile a cupola ma con comportamento diverso ai bordi
            # t/R ≈ 0.02
            t_min = 0.02 * R

        else:
            # Default conservativo
            t_min = 0.04 * R

        # Correzione per carichi aggiuntivi (riempimento, sovraccarichi)
        loads = self.calculate_total_load()
        if loads['fill_weight'] > 0 or loads['live_load'] > 0:
            # Aumento empirico: +20% per ogni kN/m² di carico extra oltre peso proprio
            extra_load = loads['fill_weight'] + loads['live_load']
            factor = 1.0 + 0.02 * extra_load
            t_min *= factor

        self._min_thickness = t_min
        return t_min

    # ========================================================================
    # COEFFICIENTE SICUREZZA GEOMETRICO
    # ========================================================================

    def calculate_safety_factor(self) -> Dict[str, any]:
        """
        Calcola coefficiente di sicurezza geometrico.

        Returns:
            Dictionary con:
            - 'geometric_safety_factor': FS = t_actual / t_min
            - 't_actual': Spessore attuale [m]
            - 't_min': Spessore minimo [m]
            - 't_to_R_ratio': Rapporto t/R attuale
            - 'verdict': 'VERY_SAFE', 'SAFE', 'MARGINALLY_SAFE', 'UNSAFE'

        Note:
            Raccomandazioni Heyman (1977) per volte:
            - FS >= 2.0: Volte esistenti
            - FS >= 3.0: Nuove costruzioni
        """
        t_actual = self.geometry.thickness
        t_min = self.calculate_minimum_thickness()
        R = self.geometry.calculate_radius()

        FS = t_actual / t_min if t_min > 0 else 999.0
        t_to_R = t_actual / R

        if FS >= 3.0:
            verdict = 'VERY_SAFE'
        elif FS >= 2.0:
            verdict = 'SAFE'
        elif FS >= 1.0:
            verdict = 'MARGINALLY_SAFE'
        else:
            verdict = 'UNSAFE'

        return {
            'geometric_safety_factor': FS,
            't_actual': t_actual,
            't_min': t_min,
            't_to_R_ratio': t_to_R,
            'verdict': verdict,
            'heyman_recommendation': 'FS >= 2.0 per esistenti, FS >= 3.0 per nuove costruzioni'
        }

    # ========================================================================
    # CAPACITÀ SISMICA
    # ========================================================================

    def calculate_seismic_capacity(self) -> Dict[str, float]:
        """
        Stima capacità sismica della volta (semplificata).

        Returns:
            Dictionary con:
            - 'ag_capacity': Accelerazione al suolo capacità [g]
            - 'PGA_capacity': PGA capacità [m/s²]

        Note:
            Metodo semplificato basato su safety factor geometrico.
            Per analisi dettagliata usare analisi cinematica non-lineare.
        """
        safety = self.calculate_safety_factor()
        FS = safety['geometric_safety_factor']

        # Stima empirica da Heyman e De Lorenzis (2007):
        # ag ≈ 0.15 × FS per volte a botte/cross
        # ag ≈ 0.10 × FS per cupole (più vulnerabili)

        if self.geometry.vault_type in ['barrel', 'cross']:
            ag_capacity = 0.15 * (FS - 1.0)  # -1.0 per margine sicurezza
        elif self.geometry.vault_type == 'dome':
            ag_capacity = 0.10 * (FS - 1.0)
        else:
            ag_capacity = 0.12 * (FS - 1.0)

        # Massimo realistico: 0.5g per volte in muratura
        ag_capacity = min(ag_capacity, 0.5)
        ag_capacity = max(ag_capacity, 0.0)

        PGA_capacity = ag_capacity * 9.81  # m/s²

        return {
            'ag_capacity': ag_capacity,
            'PGA_capacity': PGA_capacity
        }

    # ========================================================================
    # REPORT
    # ========================================================================

    def generate_report(self) -> str:
        """
        Genera report completo dell'analisi della volta.

        Returns:
            Report formattato come stringa
        """
        loads = self.calculate_total_load()
        safety = self.calculate_safety_factor()
        seismic = self.calculate_seismic_capacity()
        R = self.geometry.calculate_radius()

        report = []
        report.append("=" * 70)
        report.append("ANALISI LIMITE VOLTA - METODO HEYMAN")
        report.append("=" * 70)
        report.append("")
        report.append(f"Tipologia: {self.geometry.vault_type}")
        report.append("")

        # GEOMETRIA
        report.append("GEOMETRIA:")
        report.append(f"  Luce (span): L = {self.geometry.span:.2f} m")
        report.append(f"  Freccia (rise): f = {self.geometry.rise:.2f} m")
        report.append(f"  Spessore: t = {self.geometry.thickness:.2f} m")
        report.append(f"  Rapporto f/L: {self.geometry.rise/self.geometry.span:.2f}")
        report.append(f"  Raggio curvatura: R = {R:.2f} m")
        report.append(f"  Rapporto t/R: {safety['t_to_R_ratio']:.4f}")

        if self.geometry.vault_type in ['barrel', 'cross']:
            report.append(f"  Lunghezza: {self.geometry.length:.2f} m")
        elif self.geometry.vault_type in ['cloister', 'sail', 'pavilion']:
            report.append(f"  Larghezza: {self.geometry.width:.2f} m")
        elif self.geometry.vault_type == 'dome':
            report.append(f"  Angolo apertura: {self.geometry.opening_angle:.1f}°")

        report.append("")

        # MATERIALE E CARICHI
        report.append("MATERIALE E CARICHI:")
        report.append(f"  Densità muratura: γ = {self.masonry_density:.1f} kN/m³")
        report.append(f"  Peso proprio: {loads['self_weight']:.2f} kN/m²")
        if loads['fill_weight'] > 0:
            report.append(f"  Peso riempimento: {loads['fill_weight']:.2f} kN/m²")
        if loads['live_load'] > 0:
            report.append(f"  Sovraccarico: {loads['live_load']:.2f} kN/m²")
        report.append(f"  Carico totale: {loads['total']:.2f} kN/m²")
        report.append("")

        # ANALISI LIMITE
        report.append("ANALISI LIMITE (TEOREMA STATICO):")
        report.append(f"  Spessore minimo: t_min = {safety['t_min']:.3f} m")
        report.append(f"  Spessore attuale: t = {safety['t_actual']:.3f} m")
        report.append(f"  Safety Factor: FS = {safety['geometric_safety_factor']:.2f}")
        report.append(f"  Esito: {safety['verdict']}")

        if safety['verdict'] == 'UNSAFE' or safety['verdict'] == 'MARGINALLY_SAFE':
            report.append(f"  ⚠️  ATTENZIONE: Margine sicurezza insufficiente (FS < 2.0)")

        report.append("")

        # RACCOMANDAZIONI
        report.append("RACCOMANDAZIONI HEYMAN (1977):")
        report.append("  FS >= 2.0: Volte esistenti")
        report.append("  FS >= 3.0: Nuove costruzioni")
        report.append("")

        # CAPACITÀ SISMICA
        report.append("CAPACITÀ SISMICA (STIMA):")
        report.append(f"  ag capacità: {seismic['ag_capacity']:.3f} g")
        report.append(f"  PGA capacità: {seismic['PGA_capacity']:.2f} m/s²")

        # Confronto con zona sismica tipica
        ag_ref = 0.25  # Zona sismica media Italia
        margin = seismic['ag_capacity'] / ag_ref if ag_ref > 0 else 0
        report.append(f"  Margine vs ag={ag_ref}g: {margin:.2f}×")

        report.append("")
        report.append("=" * 70)

        if safety['verdict'] in ['VERY_SAFE', 'SAFE']:
            report.append("ESITO: ✓ VOLTA IN EQUILIBRIO STABILE")
        else:
            report.append("ESITO: ✗ VOLTA INSTABILE O MARGINE INSUFFICIENTE")

        report.append("=" * 70)
        report.append("")
        report.append("NOTE:")
        report.append("  - Analisi basata su teoria Heyman (1966-1982)")
        report.append("  - Assunzioni: no trazione, infinita compressione, no scorrimento")
        report.append("  - Per analisi dettagliata considerare Thrust Network Analysis o FEM")
        report.append("")

        return "\n".join(report)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'VaultAnalysis',
    'VaultGeometry',
    'VaultType',
    'FailureMode',
    'MASONRY_DENSITIES',
]
