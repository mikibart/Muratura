"""
Module: historic/arches.py
Analisi limite archi in muratura - Metodo Heyman

Questo modulo implementa l'analisi limite di archi murari secondo la teoria
sviluppata da Jacques Heyman (1966-1982) nel suo lavoro fondamentale
"The Stone Skeleton".

Teoria di Base (Heyman's Assumptions):
1. NO TENSILE STRENGTH: La muratura non resiste a trazione (σ_t = 0)
2. INFINITE COMPRESSIVE STRENGTH: Resistenza a compressione infinita (conservativo)
3. NO SLIDING: Attrito sufficiente a impedire scorrimento tra conci

Teoremi Fondamentali:
- TEOREMA STATICO (Safe Theorem): Se esiste UNA linea delle pressioni contenuta
  nello spessore dell'arco, allora l'arco è in equilibrio.

- TEOREMA CINEMATICO (Kinematic Theorem): Il carico di collasso è il minimo
  tra tutti i possibili cinematismi di collasso (tipicamente 4 cerniere).

References:
    - Heyman, J. (1966) "The stone skeleton", Int. J. Solids Structures
    - Heyman, J. (1982) "The Masonry Arch", Ellis Horwood
    - Huerta, S. (2001) "Mechanics of masonry vaults"

Examples:
    >>> from Material.analyses.historic.arches import ArchAnalysis, ArchGeometry
    >>> geometry = ArchGeometry(
    ...     arch_type='semicircular',
    ...     span=4.0,  # m
    ...     rise=2.0,  # m
    ...     thickness=0.50  # m
    ... )
    >>> arch = ArchAnalysis(geometry=geometry, masonry_density=20.0)
    >>> result = arch.calculate_safety_factor()
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

class ArchType(Enum):
    """Tipologie di arco"""
    SEMICIRCULAR = 'semicircular'  # Arco a tutto sesto (Romano/Romanico)
    POINTED = 'pointed'  # Arco acuto/ogivale (Gotico)
    ELLIPTICAL = 'elliptical'  # Arco ellittico (Rinascimento)
    FLAT = 'flat'  # Arco ribassato (piattabanda)
    SEGMENTAL = 'segmental'  # Arco a sesto ribassato
    HORSESHOE = 'horseshoe'  # Arco a ferro di cavallo (Islamico)


class FailureMode(Enum):
    """Modalità di collasso"""
    FOUR_HINGE = 'four_hinge'  # 4 cerniere plastiche (tipico)
    THREE_HINGE = 'three_hinge'  # 3 cerniere (raro)
    CRUSHING = 'crushing'  # Schiacciamento muratura (molto raro)
    SLIDING = 'sliding'  # Scorrimento (molto raro se giunto asciutto)


# Densità tipiche muratura [kN/m³]
MASONRY_DENSITIES = {
    'stone': 24.0,  # Pietra naturale
    'brick': 18.0,  # Mattoni pieni
    'tufo': 16.0,  # Tufo
    'tuff': 16.0,  # Tufo (alias)
    'limestone': 22.0,  # Calcare
    'sandstone': 20.0,  # Arenaria
}


# ============================================================================
# DATACLASSES PER GEOMETRIA
# ============================================================================

@dataclass
class ArchGeometry:
    """
    Geometria dell'arco.

    Attributes:
        arch_type: Tipologia arco
        span: Luce (apertura) [m]
        rise: Freccia (altezza dalla linea d'imposta alla chiave) [m]
        thickness: Spessore arco [m]
        width: Larghezza arco (profondità) [m] - default 1.0 per analisi 2D
        springline_height: Altezza linea d'imposta da terra [m]

    Note:
        Per arco semicircolare: rise = span/2
        Per arco ribassato: rise < span/2
        Per arco acuto: rise > span/2
    """
    arch_type: Literal['semicircular', 'pointed', 'elliptical', 'flat', 'segmental', 'horseshoe']
    span: float
    rise: float
    thickness: float
    width: float = 1.0  # Larghezza per analisi 2D
    springline_height: float = 0.0  # Altezza imposta

    def __post_init__(self):
        """Validazione geometria"""
        if self.span <= 0:
            raise ValueError(f"Span deve essere > 0, got {self.span}")
        if self.rise <= 0:
            raise ValueError(f"Rise deve essere > 0, got {self.rise}")
        if self.thickness <= 0:
            raise ValueError(f"Thickness deve essere > 0, got {self.thickness}")

        # Warning per geometrie non standard
        if self.arch_type == 'semicircular':
            expected_rise = self.span / 2.0
            if abs(self.rise - expected_rise) > 0.1:
                warnings.warn(
                    f"Arco semicircolare: rise={self.rise:.2f}m, "
                    f"atteso {expected_rise:.2f}m (span/2)"
                )

    def calculate_radius(self) -> float:
        """
        Calcola raggio di curvatura (per archi circolari).

        Returns:
            Raggio [m]

        Note:
            Per arco semicircolare: R = span/2
            Per arco circolare generale: R = (span²/8 + rise²/2) / (2*rise)
        """
        if self.arch_type == 'semicircular':
            # Per semicerchio: raggio = metà della luce
            return self.span / 2.0
        elif self.arch_type == 'segmental':
            # Formula per segmento circolare generico
            R = (self.span**2 / 8.0 + self.rise**2 / 2.0) / (2.0 * self.rise)
            return R
        else:
            # Per altri tipi, stima approssimativa
            return self.span / 2.0

    def calculate_intrados_extrados(self, n_points: int = 50) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calcola coordinate intradosso (interno) ed estradosso (esterno) dell'arco.

        Args:
            n_points: Numero punti discretizzazione

        Returns:
            Tuple di (intrados_points, extrados_points), ciascuno shape (n_points, 2) [x, y]
        """
        # Parametro angolare da 0 a π (semicerchio)
        if self.arch_type == 'semicircular':
            R = self.calculate_radius()
            # Centro arco
            x_c = self.span / 2.0
            y_c = self.springline_height + R - self.rise

            # Angoli
            theta = np.linspace(np.pi, 0, n_points)  # Da sinistra a destra

            # Intradosso (raggio interno)
            x_int = x_c + R * np.cos(theta)
            y_int = y_c + R * np.sin(theta)

            # Estradosso (raggio esterno)
            R_ext = R + self.thickness
            x_ext = x_c + R_ext * np.cos(theta)
            y_ext = y_c + R_ext * np.sin(theta)

            intrados = np.column_stack((x_int, y_int))
            extrados = np.column_stack((x_ext, y_ext))

            return intrados, extrados

        elif self.arch_type == 'pointed':
            # Arco ogivale: due centri
            # Semplificazione: centri a 2/3 della luce
            R = self.span * 2.0 / 3.0

            # Centro sinistro
            x_c1 = self.span / 3.0
            y_c1 = self.springline_height

            # Centro destro
            x_c2 = 2.0 * self.span / 3.0
            y_c2 = self.springline_height

            # Metà sinistra (centro 1)
            theta1 = np.linspace(np.arcsin((self.span/2 - x_c1)/R), np.pi/2, n_points//2)
            x_int1 = x_c1 + R * np.cos(theta1)
            y_int1 = y_c1 + R * np.sin(theta1)

            # Metà destra (centro 2)
            theta2 = np.linspace(np.pi/2, np.pi - np.arcsin((x_c2 - self.span/2)/R), n_points//2)
            x_int2 = x_c2 + R * np.cos(theta2)
            y_int2 = y_c2 + R * np.sin(theta2)

            # Combina
            x_int = np.concatenate([x_int1, x_int2])
            y_int = np.concatenate([y_int1, y_int2])

            # Estradosso (approssimazione parallela)
            norm_x = -np.gradient(y_int)
            norm_y = np.gradient(x_int)
            norm_len = np.sqrt(norm_x**2 + norm_y**2)
            norm_x /= norm_len
            norm_y /= norm_len

            x_ext = x_int + self.thickness * norm_x
            y_ext = y_int + self.thickness * norm_y

            intrados = np.column_stack((x_int, y_int))
            extrados = np.column_stack((x_ext, y_ext))

            return intrados, extrados

        else:
            # Tipo non ancora implementato - placeholder
            x = np.linspace(0, self.span, n_points)

            # Parabola approssimativa
            y_int = self.springline_height + 4 * self.rise * x * (self.span - x) / self.span**2
            y_ext = y_int + self.thickness

            intrados = np.column_stack((x, y_int))
            extrados = np.column_stack((x, y_ext))

            return intrados, extrados


# ============================================================================
# CLASSE PRINCIPALE ARCH ANALYSIS
# ============================================================================

class ArchAnalysis:
    """
    Analisi limite arco metodo Heyman.

    Implementa:
    - Calcolo linea delle pressioni (thrust line)
    - Spessore minimo per equilibrio (teorema statico)
    - Carico di collasso (teorema cinematico)
    - Coefficiente sicurezza geometrico
    - Capacità sismica

    Attributes:
        geometry: Geometria arco
        masonry_density: Densità muratura [kN/m³]
        live_load: Sovraccarico distribuito sull'arco [kN/m²]
    """

    def __init__(
        self,
        geometry: ArchGeometry,
        masonry_density: float = 20.0,
        live_load: float = 0.0,
        n_voussoirs: int = 30
    ):
        """
        Inizializza analisi arco.

        Args:
            geometry: Geometria arco
            masonry_density: Densità muratura [kN/m³]
            live_load: Sovraccarico [kN/m²]
            n_voussoirs: Numero conci per discretizzazione

        Raises:
            ValueError: Se parametri non validi
        """
        self.geometry = geometry
        self.masonry_density = masonry_density
        self.live_load = live_load
        self.n_voussoirs = n_voussoirs

        # Risultati (calcolati dai metodi)
        self._thrust_line: Optional[np.ndarray] = None
        self._min_thickness: Optional[float] = None
        self._collapse_load: Optional[float] = None

    # ========================================================================
    # DISCRETIZZAZIONE ARCO IN CONCI (VOUSSOIRS)
    # ========================================================================

    def discretize_arch(self) -> List[Dict]:
        """
        Discretizza arco in conci (voussoirs) per analisi.

        Returns:
            Lista di conci, ciascuno con:
            - 'weight': Peso concio [kN]
            - 'x_center': Coordinata x centro massa [m]
            - 'y_center': Coordinata y centro massa [m]
            - 'angle': Angolo normale superfice [rad]

        Note:
            Metodo semplificato: assume conci di eguale angolo
        """
        intrados, extrados = self.geometry.calculate_intrados_extrados(self.n_voussoirs)

        voussoirs = []

        for i in range(self.n_voussoirs - 1):
            # Vertici concio (quadrilatero)
            p1_int = intrados[i]
            p2_int = intrados[i+1]
            p2_ext = extrados[i+1]
            p1_ext = extrados[i]

            # Area concio (shoelace formula)
            x = [p1_int[0], p2_int[0], p2_ext[0], p1_ext[0]]
            y = [p1_int[1], p2_int[1], p2_ext[1], p1_ext[1]]

            area = 0.5 * abs(
                x[0]*y[1] - x[1]*y[0] +
                x[1]*y[2] - x[2]*y[1] +
                x[2]*y[3] - x[3]*y[2] +
                x[3]*y[0] - x[0]*y[3]
            )

            # Volume = area × width
            volume = area * self.geometry.width  # m³

            # Peso = volume × densità
            weight = volume * self.masonry_density  # kN

            # Centro massa (centroide quadrilatero)
            x_center = np.mean(x)
            y_center = np.mean(y)

            # Angolo normale (dalla tangente intradosso)
            dx = p2_int[0] - p1_int[0]
            dy = p2_int[1] - p1_int[1]
            tangent_angle = np.arctan2(dy, dx)
            normal_angle = tangent_angle + np.pi/2

            voussoirs.append({
                'weight': weight,
                'x_center': x_center,
                'y_center': y_center,
                'angle': normal_angle,
                'area': area
            })

        return voussoirs

    # ========================================================================
    # THRUST LINE (LINEA DELLE PRESSIONI)
    # ========================================================================

    def calculate_thrust_line(
        self,
        horizontal_thrust: Optional[float] = None
    ) -> np.ndarray:
        """
        Calcola linea delle pressioni (thrust line) usando metodo del poligono funicolare.

        Args:
            horizontal_thrust: Spinta orizzontale [kN]. Se None, usa metodo grafico standard.

        Returns:
            Array (n_points, 2) con coordinate (x, y) della thrust line

        Note:
            Metodo del poligono funicolare (Culmann, 1866):
            - Dato un sistema di forze verticali (pesi conci)
            - E una spinta orizzontale H costante
            - La thrust line è determinata dall'equilibrio dei momenti
        """
        voussoirs = self.discretize_arch()
        total_weight = sum(v['weight'] for v in voussoirs)

        # Se spinta non specificata, usa stima empirica
        if horizontal_thrust is None:
            # Per archi sotto peso proprio: H ≈ 0.5-0.6 × peso totale
            # (valore tipico per archi semicircolari e ribassati)
            horizontal_thrust = 0.5 * total_weight

        H = horizontal_thrust

        # Punto iniziale thrust line (imposta sinistra, a metà spessore)
        x0 = 0.0
        y0 = self.geometry.springline_height + self.geometry.thickness / 2.0

        thrust_points = [(x0, y0)]

        # Costruisci thrust line: equilibrio momenti cumulativo
        # Solo considera conci con centro a x >= 0 (sopra la linea di supporto)
        relevant_voussoirs = [v for v in voussoirs if v['x_center'] >= 0]

        cumulative_moment = 0.0  # Momento cumulativo dei pesi

        for voussoir in relevant_voussoirs:
            W = voussoir['weight']
            x_w = voussoir['x_center']

            # Aggiungi momento del concio corrente rispetto al punto iniziale (x0)
            cumulative_moment += W * (x_w - x0)

            # Dalla equazione equilibrio momenti: M = H × (y - y0)
            # y = y0 + M / H
            x_next = x_w
            y_next = y0 + cumulative_moment / H

            thrust_points.append((x_next, y_next))

        self._thrust_line = np.array(thrust_points)
        return self._thrust_line

    # ========================================================================
    # TEOREMA STATICO: SPESSORE MINIMO
    # ========================================================================

    def calculate_minimum_thickness(self) -> float:
        """
        Calcola spessore minimo per equilibrio (teorema statico Heyman).

        Returns:
            Spessore minimo [m]

        Note:
            Per archi semicircolari sotto peso proprio, usa formula empirica Heyman:
            t_min/R ≈ 0.0105 (valore teorico per arco perfetto)

            Per altri tipi, usa iterazione numerica sulla thrust line.
        """
        # Per arco semicircolare, usa formula teorica di Heyman (1969)
        if self.geometry.arch_type == 'semicircular':
            R = self.geometry.calculate_radius()
            # Heyman (1969): "The safety of masonry arches"
            # Per arco semicircolare sotto peso proprio: t/R ≈ 0.0105
            # Usiamo valore leggermente conservativo: 0.02
            t_min = 0.02 * R
            self._min_thickness = t_min
            return t_min

        # Per altri tipi di arco, usa metodo numerico
        voussoirs = self.discretize_arch()
        total_weight = sum(v['weight'] for v in voussoirs)

        # Range spinte orizzontali da esplorare
        H_values = np.linspace(0.2 * total_weight, 1.0 * total_weight, 80)

        max_eccentricity = 0.0

        for H_trial in H_values:
            try:
                thrust_line = self.calculate_thrust_line(horizontal_thrust=H_trial)

                # Ottieni intradosso ed estradosso
                n_pts = len(thrust_line)
                intrados, extrados = self.geometry.calculate_intrados_extrados(n_pts)

                # Per ogni punto thrust line, calcola eccentricità rispetto asse arco
                for i in range(min(len(thrust_line), len(intrados))):
                    x_t, y_t = thrust_line[i]

                    # Trova il punto più vicino sull'arco con stesso x
                    idx = np.argmin(np.abs(intrados[:, 0] - x_t))
                    y_int = intrados[idx, 1]
                    y_ext = extrados[idx, 1]

                    # Verifica se thrust line è dentro l'arco
                    if y_int <= y_t <= y_ext:
                        # Asse centrale dell'arco
                        y_center = (y_int + y_ext) / 2.0
                        eccentricity = abs(y_t - y_center)

                        max_eccentricity = max(max_eccentricity, eccentricity)

            except Exception:
                continue

        # Spessore minimo = 2 × eccentricità massima
        t_min = 2.0 * max_eccentricity if max_eccentricity > 0 else 0.02

        self._min_thickness = t_min
        return t_min

    # ========================================================================
    # COEFFICIENTE SICUREZZA GEOMETRICO
    # ========================================================================

    def calculate_safety_factor(self) -> Dict[str, float]:
        """
        Calcola coefficiente di sicurezza geometrico.

        Returns:
            Dictionary con:
            - 'geometric_safety_factor': FS = t_actual / t_min
            - 't_actual': Spessore attuale [m]
            - 't_min': Spessore minimo [m]
            - 'verdict': 'SAFE' se FS >= 1.0, 'UNSAFE' altrimenti

        Note:
            Heyman (1982): FS >= 2.0 raccomandato per archi esistenti
            FS >= 3.0 per nuove costruzioni
        """
        t_actual = self.geometry.thickness
        t_min = self.calculate_minimum_thickness()

        FS = t_actual / t_min if t_min > 0 else 999.0

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
            'verdict': verdict
        }

    # ========================================================================
    # TEOREMA CINEMATICO: COLLASSO (SEMPLIFICATO)
    # ========================================================================

    def calculate_collapse_mechanism(self) -> Dict[str, any]:
        """
        Calcola meccanismo di collasso (4 cerniere) - SEMPLIFICATO.

        Returns:
            Dictionary con:
            - 'collapse_load': Carico di collasso [kN/m²]
            - 'hinge_locations': Posizioni cerniere [m]
            - 'mechanism': 'four_hinge'

        Note:
            Implementazione semplificata. Per analisi completa serve ottimizzazione
            per trovare configurazione che minimizza carico collasso.
        """
        # Placeholder: implementazione completa richiede ottimizzazione
        # Per ora restituisce stima approssimativa

        # Carico collasso approssimativo (formula empirica Heyman)
        # q_collapse ≈ (γ × t / L) × (rise/span) × fattore_forma

        gamma = self.masonry_density
        t = self.geometry.thickness
        L = self.geometry.span
        f = self.geometry.rise

        # Fattore forma (dipende da geometria)
        if self.geometry.arch_type == 'semicircular':
            shape_factor = 4.0
        elif self.geometry.arch_type == 'pointed':
            shape_factor = 6.0  # Più resistente
        else:
            shape_factor = 3.0

        q_collapse = shape_factor * (gamma * t / L) * (f / L)

        # Posizioni cerniere (approssimate per arco semicircolare)
        # Tipicamente: 0°, ~50°, ~130°, 180° (dall'imposta)
        hinge_angles = [0, 50, 130, 180]  # gradi
        hinge_locations_x = []

        if self.geometry.arch_type == 'semicircular':
            R = self.geometry.calculate_radius()
            x_c = self.geometry.span / 2.0
            y_c = self.geometry.springline_height + R - self.geometry.rise

            for angle_deg in hinge_angles:
                angle_rad = np.deg2rad(180 - angle_deg)  # Converti
                x_hinge = x_c + R * np.cos(angle_rad)
                hinge_locations_x.append(x_hinge)

        self._collapse_load = q_collapse

        return {
            'collapse_load': q_collapse,
            'hinge_locations_x': hinge_locations_x,
            'mechanism': 'four_hinge',
            'note': 'Implementazione semplificata - per analisi accurata serve ottimizzazione'
        }

    # ========================================================================
    # CAPACITÀ SISMICA (SEMPLIFICATO)
    # ========================================================================

    def calculate_seismic_capacity(self, importance_factor: float = 1.0) -> Dict[str, float]:
        """
        Stima capacità sismica arco (analisi cinematica semplificata).

        Args:
            importance_factor: Fattore importanza edificio (NTC)

        Returns:
            Dictionary con:
            - 'ag_capacity': Accelerazione sismica capacità [g]
            - 'PGA_capacity': PGA capacità [m/s²]
            - 'safety_margin': Margine sicurezza rispetto ag progetto

        Note:
            Metodo semplificato basato su coefficiente sicurezza geometrico.
            Per analisi accurata serve metodo dei cinematismi (NTC §C8.7.1).
        """
        safety = self.calculate_safety_factor()
        FS = safety['geometric_safety_factor']

        # Stima accelerazione capacità (correlazione empirica)
        # ag ≈ (FS - 1) × fattore × g
        # fattore dipende da geometria (snellezza arco)

        slenderness = self.geometry.span / self.geometry.rise

        if slenderness < 2.0:
            geometry_factor = 0.3  # Arco tozzo, più resistente
        elif slenderness < 4.0:
            geometry_factor = 0.2  # Arco medio
        else:
            geometry_factor = 0.1  # Arco snello, meno resistente

        ag_capacity = (FS - 1.0) * geometry_factor  # [g]
        ag_capacity = max(0.0, ag_capacity)  # Non negativo

        PGA_capacity = ag_capacity * 9.81  # [m/s²]

        # Margine sicurezza rispetto a ag tipico (es. 0.25g per zona sismica media)
        ag_design = 0.25  # g (esempio)
        safety_margin = ag_capacity / ag_design if ag_design > 0 else 0.0

        return {
            'ag_capacity': ag_capacity,
            'PGA_capacity': PGA_capacity,
            'safety_margin': safety_margin,
            'note': 'Stima semplificata - per progetto usare metodo cinematico completo NTC §C8.7.1'
        }

    # ========================================================================
    # REPORT
    # ========================================================================

    def generate_report(self) -> str:
        """
        Genera report di verifica completo.

        Returns:
            Report formattato come stringa
        """
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("ANALISI LIMITE ARCO - METODO HEYMAN")
        report_lines.append("=" * 70)

        report_lines.append(f"\nTipologia: {self.geometry.arch_type}")

        report_lines.append(f"\nGEOMETRIA:")
        report_lines.append(f"  Luce (span): L = {self.geometry.span:.2f} m")
        report_lines.append(f"  Freccia (rise): f = {self.geometry.rise:.2f} m")
        report_lines.append(f"  Spessore: t = {self.geometry.thickness:.2f} m")
        report_lines.append(f"  Rapporto f/L: {self.geometry.rise/self.geometry.span:.2f}")

        if self.geometry.arch_type == 'semicircular':
            R = self.geometry.calculate_radius()
            report_lines.append(f"  Raggio: R = {R:.2f} m")

        report_lines.append(f"\nMATERIALE:")
        report_lines.append(f"  Densità: γ = {self.masonry_density:.1f} kN/m³")

        if self.live_load > 0:
            report_lines.append(f"  Sovraccarico: q = {self.live_load:.2f} kN/m²")

        # Sicurezza geometrica
        safety = self.calculate_safety_factor()

        report_lines.append(f"\nANALISI LIMITE (TEOREMA STATICO):")
        report_lines.append(f"  Spessore minimo: t_min = {safety['t_min']:.3f} m")
        report_lines.append(f"  Spessore attuale: t = {safety['t_actual']:.3f} m")
        report_lines.append(f"  Safety Factor: FS = {safety['geometric_safety_factor']:.2f}")
        report_lines.append(f"  Esito: {safety['verdict']}")

        if safety['verdict'] == 'UNSAFE':
            report_lines.append(f"  ⚠️  ATTENZIONE: Arco NON in equilibrio stabile!")
        elif safety['verdict'] == 'MARGINALLY_SAFE':
            report_lines.append(f"  ⚠️  ATTENZIONE: Margine sicurezza insufficiente (FS < 2.0)")

        # Raccomandazioni Heyman
        report_lines.append(f"\nRACCOMANDAZIONI HEYMAN (1982):")
        report_lines.append(f"  FS >= 2.0: Archi esistenti")
        report_lines.append(f"  FS >= 3.0: Nuove costruzioni")

        # Capacità sismica
        seismic = self.calculate_seismic_capacity()
        report_lines.append(f"\nCAPACITÀ SISMICA (STIMA):")
        report_lines.append(f"  ag capacità: {seismic['ag_capacity']:.3f} g")
        report_lines.append(f"  PGA capacità: {seismic['PGA_capacity']:.2f} m/s²")
        report_lines.append(f"  Margine vs ag=0.25g: {seismic['safety_margin']:.2f}×")

        report_lines.append(f"\n{'='*70}")
        if safety['verdict'] in ['SAFE', 'VERY_SAFE']:
            report_lines.append(f"ESITO: ✓ ARCO IN EQUILIBRIO STABILE")
        else:
            report_lines.append(f"ESITO: ✗ ARCO INSTABILE O MARGINE INSUFFICIENTE")
        report_lines.append(f"{'='*70}")

        report_lines.append(f"\nNOTE:")
        report_lines.append(f"  - Analisi basata su teoria Heyman (1966-1982)")
        report_lines.append(f"  - Assunzioni: no trazione, infinita compressione, no scorrimento")
        report_lines.append(f"  - Per analisi dettagliata considerare DMEM o FEM non-lineare")

        return "\n".join(report_lines)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'ArchAnalysis',
    'ArchGeometry',
    'ArchType',
    'FailureMode',
    'MASONRY_DENSITIES',
]
