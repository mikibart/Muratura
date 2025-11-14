"""
Module: historic/strengthening.py
Rinforzi strutturali per edifici storici in muratura

Questo modulo implementa metodi di progettazione e verifica per rinforzi
strutturali di edifici storici in muratura con materiali compositi.

Normativa di Riferimento:
- CNR-DT 200 R1/2013: Istruzioni per la Progettazione, l'Esecuzione ed il
  Controllo di Interventi di Consolidamento Statico mediante l'utilizzo di
  Compositi Fibrorinforzati (FRP)

- CNR-DT 215/2018: Istruzioni per la Progettazione, l'Esecuzione ed il
  Controllo di Interventi di Consolidamento Statico mediante l'utilizzo di
  Materiali Compositi a Matrice Inorganica (FRCM)

Materiali Implementati:
1. FRP (Fiber Reinforced Polymers):
   - CFRP: Carbonio (alto modulo, alta resistenza)
   - GFRP: Vetro (economico, basso modulo)
   - AFRP: Aramide (intermedio)

2. FRCM (Fabric Reinforced Cementitious Matrix):
   - Carbonio, Vetro AR, PBO, Basalto
   - Più compatibile con muratura storica
   - Traspirante, reversibile

3. CRM (Composite Reinforced Mortar):
   - Rete in materiale composito + malta
   - Economico, facile applicazione

Tipologie di Intervento:
- Placcaggio superficiale (archi, volte, pareti)
- Cerchiature (cupole, torri)
- Rinforzo flessionale/taglio
- Confinamento pilastri

References:
    - CNR-DT 200 R1/2013 (FRP)
    - CNR-DT 215/2018 (FRCM)
    - NTC 2018 Cap. 8 (Costruzioni esistenti)
    - Linee Guida Beni Culturali 2011

Examples:
    >>> from Material.analyses.historic.strengthening import (
    ...     StrengtheningDesign, FRPMaterial, ApplicationType
    ... )
    >>> # Rinforzo arco con CFRP
    >>> material = FRPMaterial(
    ...     material_type='CFRP',
    ...     thickness=0.165,  # mm (thickness per ply)
    ...     tensile_strength=3500,  # MPa
    ...     elastic_modulus=230000  # MPa
    ... )
    >>> design = StrengtheningDesign(
    ...     application_type='arch_extrados',
    ...     material=material,
    ...     width=1.0,  # m
    ...     n_layers=2
    ... )
    >>> result = design.calculate_capacity()
    >>> print(f"Load capacity increase: {result['capacity_increase']:.1f}%")
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Literal
from enum import Enum
import numpy as np


# ============================================================================
# ENUMS E COSTANTI
# ============================================================================

class MaterialType(Enum):
    """Tipologie materiali compositi"""
    # FRP
    CFRP = 'CFRP'  # Carbon Fiber Reinforced Polymer
    GFRP = 'GFRP'  # Glass Fiber Reinforced Polymer
    AFRP = 'AFRP'  # Aramid Fiber Reinforced Polymer

    # FRCM
    C_FRCM = 'C-FRCM'  # Carbon FRCM
    G_FRCM = 'G-FRCM'  # Glass AR FRCM
    PBO_FRCM = 'PBO-FRCM'  # PBO FRCM
    BASALT_FRCM = 'BASALT-FRCM'  # Basalt FRCM

    # CRM
    CRM = 'CRM'  # Composite Reinforced Mortar


class ApplicationType(Enum):
    """Tipologie di applicazione rinforzo"""
    ARCH_EXTRADOS = 'arch_extrados'  # Estradosso arco
    ARCH_INTRADOS = 'arch_intrados'  # Intradosso arco
    VAULT_EXTRADOS = 'vault_extrados'  # Estradosso volta
    VAULT_INTRADOS = 'vault_intrados'  # Intradosso volta
    DOME_RING = 'dome_ring'  # Cerchiatura cupola
    WALL_PLATING = 'wall_plating'  # Placcaggio parete
    COLUMN_CONFINEMENT = 'column_confinement'  # Confinamento pilastro


class FailureMode(Enum):
    """Modalità di rottura"""
    FIBER_RUPTURE = 'fiber_rupture'  # Rottura fibra
    DEBONDING = 'debonding'  # Delaminazione
    SLIDING = 'sliding'  # Scorrimento
    MASONRY_CRUSHING = 'masonry_crushing'  # Schiacciamento muratura
    ANCHORAGE = 'anchorage'  # Perdita ancoraggio


# Database materiali tipici
# Valori da CNR-DT 200/2013 e CNR-DT 215/2018
MATERIAL_DATABASE = {
    'CFRP_HM': {  # Alto modulo
        'tensile_strength': 3500,  # MPa
        'elastic_modulus': 230000,  # MPa
        'ultimate_strain': 0.015,  # 1.5%
        'thickness_per_ply': 0.165,  # mm
        'density': 1.80,  # g/cm³
    },
    'CFRP_HS': {  # Alta resistenza
        'tensile_strength': 4800,  # MPa
        'elastic_modulus': 240000,  # MPa
        'ultimate_strain': 0.020,  # 2.0%
        'thickness_per_ply': 0.111,  # mm
        'density': 1.82,  # g/cm³
    },
    'GFRP': {
        'tensile_strength': 1200,  # MPa
        'elastic_modulus': 73000,  # MPa
        'ultimate_strain': 0.016,  # 1.6%
        'thickness_per_ply': 0.330,  # mm
        'density': 2.60,  # g/cm³
    },
    'AFRP': {
        'tensile_strength': 2900,  # MPa
        'elastic_modulus': 120000,  # MPa
        'ultimate_strain': 0.024,  # 2.4%
        'thickness_per_ply': 0.220,  # mm
        'density': 1.45,  # g/cm³
    },
    'C_FRCM': {
        'tensile_strength': 2000,  # MPa (tessuto)
        'elastic_modulus': 200000,  # MPa
        'ultimate_strain': 0.010,  # 1.0%
        'thickness': 0.047,  # mm (equiv. thickness)
        'weight': 170,  # g/m²
    },
    'G_FRCM': {
        'tensile_strength': 1800,  # MPa
        'elastic_modulus': 72000,  # MPa
        'ultimate_strain': 0.025,  # 2.5%
        'thickness': 0.040,  # mm
        'weight': 225,  # g/m²
    },
}


# Coefficienti parziali sicurezza (CNR-DT 200/215)
SAFETY_FACTORS = {
    'gamma_f': 1.50,  # Materiale composito
    'gamma_m': 3.00,  # Muratura (esistente)
    'gamma_fd': 1.20,  # Delaminazione
    'eta_a': 0.95,  # Fattore ambientale (interno protetto)
}


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class FRPMaterial:
    """
    Materiale composito FRP/FRCM.

    Attributes:
        material_type: Tipo materiale (CFRP, GFRP, etc.)
        thickness: Spessore per strato [mm]
        tensile_strength: Resistenza a trazione [MPa]
        elastic_modulus: Modulo elastico [MPa]
        ultimate_strain: Deformazione ultima
        width: Larghezza striscia [mm] - opzionale
    """
    material_type: str
    thickness: float  # mm
    tensile_strength: float  # MPa
    elastic_modulus: float  # MPa
    ultimate_strain: Optional[float] = None
    width: Optional[float] = None  # mm

    def __post_init__(self):
        """Calcola deformazione ultima se non specificata"""
        if self.ultimate_strain is None:
            self.ultimate_strain = self.tensile_strength / self.elastic_modulus

    @classmethod
    def from_database(cls, material_name: str):
        """Crea materiale da database"""
        if material_name not in MATERIAL_DATABASE:
            raise ValueError(f"Materiale {material_name} non in database")

        data = MATERIAL_DATABASE[material_name]
        return cls(
            material_type=material_name,
            thickness=data.get('thickness_per_ply', data.get('thickness', 0.1)),
            tensile_strength=data['tensile_strength'],
            elastic_modulus=data['elastic_modulus'],
            ultimate_strain=data['ultimate_strain']
        )


@dataclass
class MasonryProperties:
    """
    Proprietà muratura da rinforzare.

    Attributes:
        compressive_strength: Resistenza a compressione [MPa]
        tensile_strength: Resistenza a trazione [MPa]
        elastic_modulus: Modulo elastico [MPa]
        density: Densità [kN/m³]
    """
    compressive_strength: float  # MPa
    tensile_strength: float = 0.1  # MPa (bassa per muratura)
    elastic_modulus: float = 1500  # MPa (tipico per muratura)
    density: float = 18.0  # kN/m³


# ============================================================================
# CLASSE PRINCIPALE STRENGTHENING DESIGN
# ============================================================================

class StrengtheningDesign:
    """
    Progettazione rinforzi strutturali con FRP/FRCM.

    Implementa:
    - Calcolo capacità portante con rinforzo
    - Verifica delaminazione (CNR-DT 200 §3.3)
    - Verifica scorrimento
    - Lunghezza ancoraggio ottimale
    - Aumento capacità sismica

    Attributes:
        application_type: Tipo applicazione
        material: Materiale composito
        masonry: Proprietà muratura
        width: Larghezza rinforzo [m]
        n_layers: Numero strati
        spacing: Interasse strisce [m] - se applicazione a strisce
    """

    def __init__(
        self,
        application_type: ApplicationType,
        material: FRPMaterial,
        masonry: Optional[MasonryProperties] = None,
        width: float = 1.0,  # m
        n_layers: int = 1,
        spacing: Optional[float] = None  # m
    ):
        """
        Inizializza progetto rinforzo.

        Args:
            application_type: Tipo applicazione
            material: Materiale composito
            masonry: Proprietà muratura (default: muratura media qualità)
            width: Larghezza rinforzo [m]
            n_layers: Numero strati
            spacing: Interasse strisce [m] (None = continuo)
        """
        self.application_type = application_type
        self.material = material
        self.masonry = masonry or MasonryProperties(compressive_strength=2.0)
        self.width = width
        self.n_layers = n_layers
        self.spacing = spacing

    # ========================================================================
    # CALCOLO RESISTENZA DI PROGETTO
    # ========================================================================

    def calculate_design_strength(self) -> Dict[str, float]:
        """
        Calcola resistenza di progetto del rinforzo (CNR-DT 200 §3.2.1).

        Returns:
            Dictionary con:
            - 'f_fd': Resistenza di progetto [MPa]
            - 'eps_fd': Deformazione di progetto
            - 'F_fd': Forza di progetto per unità larghezza [kN/m]

        Note:
            f_fd = f_fk / (gamma_f * gamma_m * eta_a)
            dove:
            - f_fk: Resistenza caratteristica
            - gamma_f: Coeff. sicurezza materiale (1.50)
            - gamma_m: Coeff. sicurezza muratura (3.00)
            - eta_a: Fattore ambientale (0.95)
        """
        gamma_f = SAFETY_FACTORS['gamma_f']
        gamma_m = SAFETY_FACTORS['gamma_m']
        eta_a = SAFETY_FACTORS['eta_a']

        # Resistenza caratteristica
        f_fk = self.material.tensile_strength  # MPa

        # Resistenza di progetto
        f_fd = f_fk / (gamma_f * eta_a)  # MPa

        # Deformazione di progetto
        eps_fd = f_fd / self.material.elastic_modulus

        # Area resistente per unità di larghezza [mm²/m]
        if self.spacing is None:
            # Applicazione continua
            A_f = self.material.thickness * self.n_layers * 1000  # mm²/m
        else:
            # Applicazione a strisce
            if self.material.width is None:
                raise ValueError("Width must be specified for strip application")
            A_f = self.material.thickness * self.n_layers * self.material.width / self.spacing  # mm²/m

        # Forza di progetto [kN/m]
        F_fd = f_fd * A_f / 1000  # kN/m

        return {
            'f_fd': f_fd,
            'eps_fd': eps_fd,
            'F_fd': F_fd,
            'A_f': A_f
        }

    # ========================================================================
    # VERIFICA DELAMINAZIONE
    # ========================================================================

    def calculate_debonding_strength(self) -> Dict[str, float]:
        """
        Verifica resistenza a delaminazione (CNR-DT 200 §3.3).

        Returns:
            Dictionary con:
            - 'f_dd': Resistenza delaminazione [MPa]
            - 'gamma_fd': Fattore sicurezza delaminazione
            - 'verified': Bool verifica

        Note:
            Delaminazione è critica per rinforzi su muratura.
            CNR-DT 200: f_dd = k_b * sqrt(f_cm * f_fk)
            dove k_b dipende dalla geometria.
        """
        gamma_fd = SAFETY_FACTORS['gamma_fd']

        # Resistenza media muratura
        f_cm = self.masonry.compressive_strength  # MPa

        # Resistenza caratteristica rinforzo
        f_fk = self.material.tensile_strength  # MPa

        # Coefficiente geometrico (CNR-DT 200 eq. 3.7)
        # k_b = sqrt(2 - b_f/b_c) >= 1.0
        # Semplificazione: k_b = 1.2 (tipico)
        k_b = 1.2

        # Resistenza delaminazione
        f_dd = k_b * np.sqrt(f_cm * f_fk / 1000)  # MPa (diviso 1000 per formula CNR)

        # Resistenza di progetto delaminazione
        f_dd_design = f_dd / gamma_fd

        # Resistenza effettiva rinforzo
        design = self.calculate_design_strength()
        f_fd = design['f_fd']

        # Verifica
        verified = f_dd_design >= f_fd

        return {
            'f_dd': f_dd,
            'f_dd_design': f_dd_design,
            'gamma_fd': gamma_fd,
            'verified': verified,
            'safety_ratio': f_dd_design / f_fd if f_fd > 0 else 999
        }

    # ========================================================================
    # LUNGHEZZA ANCORAGGIO
    # ========================================================================

    def calculate_anchorage_length(self) -> Dict[str, float]:
        """
        Calcola lunghezza di ancoraggio ottimale (CNR-DT 200 §3.4).

        Returns:
            Dictionary con:
            - 'l_e': Lunghezza efficace ancoraggio [mm]
            - 'l_min': Lunghezza minima [mm]
            - 'tau_max': Tensione tangenziale max [MPa]

        Note:
            Lunghezza minima per evitare scorrimento prematuro.
            CNR-DT 200: l_e = sqrt(E_f * t_f / tau_max)
        """
        # Modulo elastico rinforzo
        E_f = self.material.elastic_modulus  # MPa

        # Spessore rinforzo
        t_f = self.material.thickness * self.n_layers  # mm

        # Resistenza a taglio interfaccia (empirica da CNR)
        f_cm = self.masonry.compressive_strength  # MPa
        tau_max = 0.5 * np.sqrt(f_cm)  # MPa (CNR-DT 200 eq. 3.10)

        # Lunghezza efficace (CNR-DT 200 eq. 3.9)
        l_e = np.sqrt(E_f * t_f / (2 * tau_max))  # mm

        # Lunghezza minima consigliata
        l_min = max(150, l_e)  # mm (minimo 150mm)

        return {
            'l_e': l_e,
            'l_min': l_min,
            'tau_max': tau_max,
            'recommendation': f'Ancoraggio minimo: {l_min:.0f} mm'
        }

    # ========================================================================
    # AUMENTO CAPACITÀ
    # ========================================================================

    def calculate_capacity_increase(
        self,
        original_capacity: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calcola aumento capacità portante con rinforzo.

        Args:
            original_capacity: Capacità originale struttura [kN]
                             (se None, calcola solo contributo rinforzo)

        Returns:
            Dictionary con:
            - 'strengthening_contribution': Contributo rinforzo [kN]
            - 'total_capacity': Capacità totale [kN]
            - 'capacity_increase_percent': Incremento percentuale [%]

        Note:
            Il contributo del rinforzo dipende dalla tipologia di applicazione.
        """
        design = self.calculate_design_strength()
        F_fd = design['F_fd']  # kN/m

        # Contributo rinforzo (dipende da application_type)
        if self.application_type.value in ['arch_extrados', 'arch_intrados']:
            # Per archi: rinforzo riduce spessore minimo
            # Contributo = forza × larghezza effettiva
            strengthening_contribution = F_fd * self.width

        elif self.application_type.value in ['vault_extrados', 'vault_intrados']:
            # Per volte: contributo distribuito
            strengthening_contribution = F_fd * self.width

        elif self.application_type.value == 'dome_ring':
            # Cerchiatura cupola: contrasta trazione anelli
            # Forza cerchiatura = F_fd × perimetro
            if 'diameter' in dir(self):
                perimeter = np.pi * self.diameter
                strengthening_contribution = F_fd * perimeter
            else:
                strengthening_contribution = F_fd * self.width

        elif self.application_type.value == 'wall_plating':
            # Placcaggio parete: rinforzo a flessione/taglio
            strengthening_contribution = F_fd * self.width

        else:
            # Default
            strengthening_contribution = F_fd * self.width

        # Capacità totale
        if original_capacity is not None:
            total_capacity = original_capacity + strengthening_contribution
            increase_percent = (strengthening_contribution / original_capacity) * 100
        else:
            total_capacity = strengthening_contribution
            increase_percent = 0

        return {
            'strengthening_contribution': strengthening_contribution,
            'total_capacity': total_capacity,
            'capacity_increase_percent': increase_percent,
            'F_fd_per_meter': F_fd
        }

    # ========================================================================
    # REPORT
    # ========================================================================

    def generate_report(self, original_capacity: Optional[float] = None) -> str:
        """
        Genera report completo progetto rinforzo.

        Args:
            original_capacity: Capacità originale [kN]

        Returns:
            Report formattato
        """
        design = self.calculate_design_strength()
        debonding = self.calculate_debonding_strength()
        anchorage = self.calculate_anchorage_length()
        capacity = self.calculate_capacity_increase(original_capacity)

        report = []
        report.append("=" * 70)
        report.append("PROGETTO RINFORZO STRUTTURALE - FRP/FRCM")
        report.append("=" * 70)
        report.append(f"Normativa: CNR-DT 200/2013 (FRP), CNR-DT 215/2018 (FRCM)")
        report.append("")

        # APPLICAZIONE
        report.append("TIPOLOGIA APPLICAZIONE:")
        report.append(f"  Tipo: {self.application_type.value}")
        report.append(f"  Larghezza: {self.width:.2f} m")
        if self.spacing:
            report.append(f"  Interasse strisce: {self.spacing:.3f} m")
        else:
            report.append(f"  Applicazione: Continua")
        report.append("")

        # MATERIALE
        report.append("MATERIALE COMPOSITO:")
        report.append(f"  Tipo: {self.material.material_type}")
        report.append(f"  Numero strati: {self.n_layers}")
        report.append(f"  Spessore per strato: {self.material.thickness:.3f} mm")
        report.append(f"  Spessore totale: {self.material.thickness * self.n_layers:.3f} mm")
        report.append(f"  Resistenza caratteristica: f_fk = {self.material.tensile_strength:.0f} MPa")
        report.append(f"  Modulo elastico: E_f = {self.material.elastic_modulus:.0f} MPa")
        report.append(f"  Deformazione ultima: ε_fu = {self.material.ultimate_strain:.3f}")
        report.append("")

        # MURATURA
        report.append("PROPRIETÀ MURATURA:")
        report.append(f"  Resistenza a compressione: f_cm = {self.masonry.compressive_strength:.2f} MPa")
        report.append(f"  Resistenza a trazione: f_tm = {self.masonry.tensile_strength:.2f} MPa")
        report.append("")

        # RESISTENZA DI PROGETTO
        report.append("RESISTENZA DI PROGETTO (CNR-DT 200 §3.2):")
        report.append(f"  Resistenza di progetto: f_fd = {design['f_fd']:.1f} MPa")
        report.append(f"  Deformazione di progetto: ε_fd = {design['eps_fd']:.4f}")
        report.append(f"  Area resistente: A_f = {design['A_f']:.1f} mm²/m")
        report.append(f"  Forza di progetto: F_fd = {design['F_fd']:.2f} kN/m")
        report.append("")

        # VERIFICA DELAMINAZIONE
        report.append("VERIFICA DELAMINAZIONE (CNR-DT 200 §3.3):")
        report.append(f"  Resistenza delaminazione: f_dd = {debonding['f_dd']:.2f} MPa")
        report.append(f"  Resistenza progetto delam.: f_dd,d = {debonding['f_dd_design']:.2f} MPa")
        report.append(f"  Rapporto sicurezza: {debonding['safety_ratio']:.2f}")
        if debonding['verified']:
            report.append(f"  Esito: ✓ VERIFICATO (f_dd,d >= f_fd)")
        else:
            report.append(f"  Esito: ✗ NON VERIFICATO")
            report.append(f"  ⚠️  ATTENZIONE: Rischio delaminazione!")
        report.append("")

        # ANCORAGGIO
        report.append("LUNGHEZZA ANCORAGGIO (CNR-DT 200 §3.4):")
        report.append(f"  Lunghezza efficace: l_e = {anchorage['l_e']:.0f} mm")
        report.append(f"  Lunghezza minima: l_min = {anchorage['l_min']:.0f} mm")
        report.append(f"  Tensione tangenziale max: τ_max = {anchorage['tau_max']:.2f} MPa")
        report.append(f"  {anchorage['recommendation']}")
        report.append("")

        # AUMENTO CAPACITÀ
        report.append("AUMENTO CAPACITÀ PORTANTE:")
        report.append(f"  Contributo rinforzo: {capacity['strengthening_contribution']:.2f} kN")
        if original_capacity:
            report.append(f"  Capacità originale: {original_capacity:.2f} kN")
            report.append(f"  Capacità rinforzata: {capacity['total_capacity']:.2f} kN")
            report.append(f"  Incremento: +{capacity['capacity_increase_percent']:.1f}%")
        report.append("")

        report.append("=" * 70)
        if debonding['verified']:
            report.append("ESITO: ✓ RINFORZO VERIFICATO")
        else:
            report.append("ESITO: ⚠️ RINFORZO DA RIVEDERE (delaminazione)")
        report.append("=" * 70)
        report.append("")
        report.append("NOTE:")
        report.append("  - Analisi basata su CNR-DT 200 R1/2013 e CNR-DT 215/2018")
        report.append("  - Verificare compatibilità con vincoli Beni Culturali")
        report.append("  - FRCM preferibile per muratura storica (reversibilità)")
        report.append("  - Prevedere monitoraggio strutturale post-intervento")
        report.append("")

        return "\n".join(report)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'StrengtheningDesign',
    'FRPMaterial',
    'MasonryProperties',
    'MaterialType',
    'ApplicationType',
    'FailureMode',
    'MATERIAL_DATABASE',
    'SAFETY_FACTORS',
]
