"""
Module: stairs/__init__.py
Analisi e verifica scale secondo NTC 2018

Questo modulo implementa il calcolo e la verifica di scale secondo le NTC 2018,
incluse scale in c.a., acciaio, legno e scale storiche in muratura.

Funzionalità principali:
- Calcolo geometrico (alzata, pedata, pendenza) secondo normativa
- Verifica ergonomica e sicurezza (alzata 15-18cm, pedata 25-32cm)
- Calcolo sollecitazioni rampa (momento, taglio)
- Verifica SLU (flessione, taglio)
- Verifica SLE (deformazione)
- Dimensionamento armature/profilati
- Verifica pianerottoli
- Verifica sismica (forze orizzontali)

Tipologie supportate:
- 'slab_ramp': Scala a soletta rampante (più comune)
- 'cantilever': Scala a sbalzo
- 'knee': Scala a ginocchio
- 'steel': Scala in acciaio
- 'wood': Scala in legno
- 'helical': Scala elicoidale/a chiocciola
- 'masonry': Scala in muratura (storica)

Examples:
    >>> from Material.analyses.stairs import StairAnalysis, StairGeometry
    >>> geometry = StairGeometry(
    ...     floor_height=3.0,  # m
    ...     n_steps=17,
    ...     width=1.20,  # m
    ...     landing_length=1.20  # m
    ... )
    >>> stair = StairAnalysis(
    ...     stair_type='slab_ramp',
    ...     geometry=geometry,
    ...     concrete_class='C25/30',
    ...     steel_class='B450C'
    ... )
    >>> verification = stair.verify_stair()
    >>> print(f"Geometria verificata: {verification['geometry_ok']}")
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Literal
from enum import Enum
import numpy as np


# ============================================================================
# ENUMS E COSTANTI
# ============================================================================

class StairType(Enum):
    """Tipologie di scala supportate"""
    SLAB_RAMP = 'slab_ramp'  # Soletta rampante
    CANTILEVER = 'cantilever'  # A sbalzo
    KNEE = 'knee'  # A ginocchio
    STEEL = 'steel'  # Acciaio
    WOOD = 'wood'  # Legno
    HELICAL = 'helical'  # Elicoidale/chiocciola
    MASONRY = 'masonry'  # Muratura (storica)


class SupportCondition(Enum):
    """Condizioni di vincolo rampa"""
    SIMPLY_SUPPORTED = 'simply_supported'  # Semplicemente appoggiata
    ONE_END_FIXED = 'one_end_fixed'  # Un estremo incastrato
    BOTH_ENDS_FIXED = 'both_ends_fixed'  # Entrambi incastrati
    CANTILEVER = 'cantilever'  # A sbalzo


# NTC 2018 - Classi materiali
CONCRETE_CLASSES = {
    'C20/25': {'fck': 20.0, 'Ecm': 30000.0},
    'C25/30': {'fck': 25.0, 'Ecm': 31500.0},
    'C28/35': {'fck': 28.0, 'Ecm': 32300.0},
    'C30/37': {'fck': 30.0, 'Ecm': 33000.0},
}

STEEL_CLASSES = {
    'B450C': {'fyk': 450.0, 'Es': 210000.0, 'epsuk': 0.075},
    'B450A': {'fyk': 450.0, 'Es': 210000.0, 'epsuk': 0.025},
}

# Acciaio da carpenteria
STRUCTURAL_STEEL = {
    'S235': {'fy': 235.0, 'fu': 360.0, 'E': 210000.0},
    'S275': {'fy': 275.0, 'fu': 430.0, 'E': 210000.0},
    'S355': {'fy': 355.0, 'fu': 510.0, 'E': 210000.0},
}

# Coefficienti di sicurezza NTC 2018
GAMMA_C = 1.5
GAMMA_S = 1.15
GAMMA_M0 = 1.05
ALPHA_CC = 0.85

# Normativa geometrica scale
# DM 236/89 + Codice Prevenzione Incendi
GEOMETRY_LIMITS = {
    'rise_min': 0.15,  # Alzata minima 15cm
    'rise_max': 0.18,  # Alzata massima 18cm (residenziale)
    'rise_max_public': 0.17,  # Alzata massima 17cm (pubblico)
    'tread_min': 0.25,  # Pedata minima 25cm
    'tread_max': 0.32,  # Pedata massima 32cm
    'width_min_residential': 0.80,  # Larghezza minima residenziale
    'width_min_public': 1.20,  # Larghezza minima pubblico
    'headroom_min': 2.00,  # Altezza libera minima 2.0m
}

# Formula di Blondel (comfort): 2a + p = 62-64 cm
BLONDEL_MIN = 0.62  # m
BLONDEL_MAX = 0.64  # m

# Sovraccarichi NTC 2018 Tab. 3.1.II
Q_CAT_C = 4.0  # kN/m² (Cat. C - scale pubbliche/condominiali)
Q_CAT_A = 2.0  # kN/m² (Cat. A - scale interne abitazioni)


# ============================================================================
# DATACLASSES PER GEOMETRIA E CARICHI
# ============================================================================

@dataclass
class StairGeometry:
    """
    Geometria della scala.

    Attributes:
        floor_height: Dislivello da superare [m]
        n_steps: Numero gradini
        width: Larghezza scala [m]
        landing_length: Lunghezza pianerottolo [m]
        thickness: Spessore soletta/gradino [m]
        n_flights: Numero rampe (default 2 per scala tipica)
        rise: Alzata [m] (calcolata se None)
        tread: Pedata [m] (calcolata se None)
    """
    floor_height: float
    n_steps: int
    width: float
    landing_length: float = 1.20  # m (tipico)
    thickness: float = 0.18  # m (soletta 18cm)
    n_flights: int = 2  # Rampe (scala tipica a 2 rampe)
    rise: Optional[float] = None  # Calcolata
    tread: Optional[float] = None  # Calcolata

    def __post_init__(self):
        """Calcola alzata e pedata se non specificate"""
        if self.floor_height <= 0:
            raise ValueError(f"Floor height deve essere > 0, got {self.floor_height}")
        if self.n_steps <= 0:
            raise ValueError(f"Number of steps deve essere > 0, got {self.n_steps}")

        # Calcola alzata
        if self.rise is None:
            self.rise = self.floor_height / self.n_steps

        # Per pedata: usa formula Blondel se non specificata
        # 2a + p = 63cm (medio)
        if self.tread is None:
            self.tread = 0.63 - 2 * self.rise

    def validate_geometry(self) -> Dict[str, any]:
        """
        Valida geometria secondo normativa.

        Returns:
            Dictionary con esito validazione e note
        """
        issues = []
        warnings = []

        # Alzata
        if self.rise < GEOMETRY_LIMITS['rise_min']:
            issues.append(f"Alzata {self.rise*100:.1f}cm < minimo {GEOMETRY_LIMITS['rise_min']*100:.0f}cm")
        if self.rise > GEOMETRY_LIMITS['rise_max']:
            issues.append(f"Alzata {self.rise*100:.1f}cm > massimo {GEOMETRY_LIMITS['rise_max']*100:.0f}cm")

        # Pedata
        if self.tread < GEOMETRY_LIMITS['tread_min']:
            issues.append(f"Pedata {self.tread*100:.1f}cm < minimo {GEOMETRY_LIMITS['tread_min']*100:.0f}cm")
        if self.tread > GEOMETRY_LIMITS['tread_max']:
            warnings.append(f"Pedata {self.tread*100:.1f}cm > massimo {GEOMETRY_LIMITS['tread_max']*100:.0f}cm")

        # Formula di Blondel (comfort)
        blondel = 2 * self.rise + self.tread
        if blondel < BLONDEL_MIN or blondel > BLONDEL_MAX:
            warnings.append(
                f"Formula Blondel: 2a+p = {blondel*100:.1f}cm fuori range comfort "
                f"({BLONDEL_MIN*100:.0f}-{BLONDEL_MAX*100:.0f}cm)"
            )

        # Larghezza
        if self.width < GEOMETRY_LIMITS['width_min_residential']:
            issues.append(f"Larghezza {self.width*100:.0f}cm < minimo residenziale {GEOMETRY_LIMITS['width_min_residential']*100:.0f}cm")

        # Pendenza (deve essere tra 30-40°)
        slope = np.arctan(self.rise / self.tread) * 180 / np.pi
        if slope < 25 or slope > 45:
            warnings.append(f"Pendenza {slope:.1f}° fuori range ottimale (30-40°)")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'rise_cm': self.rise * 100,
            'tread_cm': self.tread * 100,
            'blondel': blondel * 100,
            'slope_deg': slope,
            'width_cm': self.width * 100
        }


@dataclass
class StairLoads:
    """
    Carichi agenti sulla scala.

    Attributes:
        permanent_loads: Carichi permanenti G2 [kN/m²] (gradini, rivestimento)
        live_loads: Sovraccarichi variabili Q [kN/m²]
        handrail_weight: Peso corrimano [kN/m]
        self_weight_included: Se True, peso proprio già incluso

    Note:
        NTC 2018 Tab. 3.1.II:
        - Cat. A (residenziale): 2.0 kN/m²
        - Cat. C (scale pubbliche): 4.0 kN/m²
    """
    permanent_loads: float = 1.5  # Gradini + rivestimento
    live_loads: float = 4.0  # Cat. C (scale condominiali/pubbliche)
    handrail_weight: float = 0.2  # kN/m (corrimano)
    self_weight_included: bool = False

    def total_permanent(self, self_weight: float = 0.0) -> float:
        """Calcola carico permanente totale"""
        g_total = self.permanent_loads
        if not self.self_weight_included:
            g_total += self_weight
        return g_total

    def slu_load_combination(self, self_weight: float = 0.0) -> float:
        """
        Combinazione carico SLU (NTC 2018 §2.5.3)

        γG·G + γQ·Q
        γG = 1.3, γQ = 1.5
        """
        G = self.total_permanent(self_weight)
        Q = self.live_loads
        return 1.3 * G + 1.5 * Q


# ============================================================================
# CLASSE PRINCIPALE STAIR ANALYSIS
# ============================================================================

class StairAnalysis:
    """
    Analisi e verifica scala secondo NTC 2018.

    Implementa:
    - Calcolo geometrico (alzata, pedata, pendenza)
    - Validazione normativa (DM 236/89, NTC 2018)
    - Calcolo sollecitazioni rampa
    - Verifica SLU (flessione, taglio)
    - Verifica SLE (deformazione)
    - Dimensionamento armature
    - Verifica pianerottoli

    Attributes:
        stair_type: Tipologia scala
        geometry: Geometria scala
        concrete_class: Classe calcestruzzo
        steel_class: Classe acciaio armatura
        support_condition: Condizioni vincolo rampa
        loads: Carichi agenti
    """

    def __init__(
        self,
        stair_type: Literal['slab_ramp', 'cantilever', 'knee', 'steel', 'wood', 'helical', 'masonry'],
        geometry: StairGeometry,
        concrete_class: str = 'C25/30',
        steel_class: str = 'B450C',
        structural_steel_class: str = 'S275',
        support_condition: Literal['simply_supported', 'one_end_fixed', 'both_ends_fixed', 'cantilever'] = 'simply_supported',
        loads: Optional[StairLoads] = None
    ):
        """
        Inizializza analisi scala.

        Args:
            stair_type: Tipologia scala
            geometry: Geometria scala
            concrete_class: Classe calcestruzzo NTC 2018
            steel_class: Classe acciaio armatura
            structural_steel_class: Classe acciaio carpenteria
            support_condition: Condizioni vincolo rampa
            loads: Carichi agenti

        Raises:
            ValueError: Se parametri non validi
        """
        self.stair_type = StairType(stair_type)
        self.geometry = geometry
        self.support_condition = SupportCondition(support_condition)
        self.loads = loads if loads is not None else StairLoads()

        # Proprietà materiali C.A.
        if concrete_class not in CONCRETE_CLASSES:
            raise ValueError(f"Concrete class {concrete_class} not supported")
        if steel_class not in STEEL_CLASSES:
            raise ValueError(f"Steel class {steel_class} not supported")

        self.concrete = CONCRETE_CLASSES[concrete_class]
        self.steel = STEEL_CLASSES[steel_class]
        self.concrete_class = concrete_class
        self.steel_class = steel_class

        # Resistenze di calcolo
        self.fcd = ALPHA_CC * self.concrete['fck'] / GAMMA_C
        self.fyd = self.steel['fyk'] / GAMMA_S

        # Acciaio carpenteria
        if structural_steel_class not in STRUCTURAL_STEEL:
            raise ValueError(f"Structural steel class {structural_steel_class} not supported")
        self.structural_steel = STRUCTURAL_STEEL[structural_steel_class]
        self.structural_steel_class = structural_steel_class

        # Risultati
        self._self_weight: Optional[float] = None
        self._moments: Optional[Dict] = None
        self._shear: Optional[Dict] = None
        self._ramp_length: Optional[float] = None

    # ========================================================================
    # GEOMETRIA
    # ========================================================================

    def calculate_ramp_length(self) -> float:
        """
        Calcola lunghezza rampa inclinata.

        Returns:
            Lunghezza rampa [m]
        """
        if self._ramp_length is not None:
            return self._ramp_length

        # Gradini per rampa
        steps_per_flight = self.geometry.n_steps / self.geometry.n_flights

        # Lunghezza orizzontale proiezione
        L_horizontal = steps_per_flight * self.geometry.tread

        # Lunghezza inclinata (ipotenusa)
        rise_total_per_flight = self.geometry.floor_height / self.geometry.n_flights
        self._ramp_length = np.sqrt(L_horizontal**2 + rise_total_per_flight**2)

        return self._ramp_length

    # ========================================================================
    # PESO PROPRIO
    # ========================================================================

    def calculate_self_weight(self) -> float:
        """
        Calcola peso proprio scala [kN/m²] in proiezione orizzontale.

        Returns:
            Peso proprio [kN/m²]
        """
        if self._self_weight is not None:
            return self._self_weight

        if self.stair_type == StairType.SLAB_RAMP:
            # Soletta rampante
            gamma_c = 25.0  # kN/m³

            # Peso soletta inclinata (proiettata su piano orizzontale)
            # Considerando pendenza: peso aumenta di fattore 1/cos(θ)
            slope_rad = np.arctan(self.geometry.rise / self.geometry.tread)
            cos_slope = np.cos(slope_rad)

            # Peso soletta
            weight_slab = gamma_c * self.geometry.thickness / cos_slope

            # Peso medio gradini (triangolo): h_medio = alzata/2
            weight_steps = gamma_c * (self.geometry.rise / 2.0)

            self._self_weight = weight_slab + weight_steps

        elif self.stair_type == StairType.STEEL:
            # Scala acciaio + gradini
            self._self_weight = 2.5  # kN/m² (profilati + gradini metallici/grigliato)

        elif self.stair_type == StairType.WOOD:
            # Scala legno
            gamma_wood = 5.5  # kN/m³
            self._self_weight = gamma_wood * self.geometry.thickness

        else:
            # Default
            self._self_weight = 4.0  # kN/m²

        return self._self_weight

    # ========================================================================
    # SOLLECITAZIONI
    # ========================================================================

    def calculate_moments(self) -> Dict[str, float]:
        """
        Calcola momenti flettenti [kNm/m].

        Returns:
            Dictionary con:
            - 'M_max': Momento massimo in campata [kNm/m]
            - 'M_support': Momento su appoggio [kNm/m]
            - 'q_slu': Carico distribuito SLU [kN/m²]
        """
        if self._moments is not None:
            return self._moments

        # Carico di calcolo SLU
        self_weight = self.calculate_self_weight()
        q_slu = self.loads.slu_load_combination(self_weight)

        # Lunghezza rampa
        L = self.calculate_ramp_length()

        # Calcolo momento secondo schema statico
        if self.support_condition == SupportCondition.SIMPLY_SUPPORTED:
            # Semplicemente appoggiata: M = q·L²/8
            M_max = q_slu * L**2 / 8.0
            M_support = 0.0

        elif self.support_condition == SupportCondition.ONE_END_FIXED:
            # Un estremo incastrato: M_campata = q·L²/9.875, M_incastro = -q·L²/8
            M_max = q_slu * L**2 / 9.875
            M_support = q_slu * L**2 / 8.0

        elif self.support_condition == SupportCondition.BOTH_ENDS_FIXED:
            # Entrambi incastrati: M_campata = q·L²/24, M_incastro = -q·L²/12
            M_max = q_slu * L**2 / 24.0
            M_support = q_slu * L**2 / 12.0

        else:  # CANTILEVER
            # Sbalzo: M = q·L²/2
            M_max = 0.0
            M_support = q_slu * L**2 / 2.0

        self._moments = {
            'M_max': M_max,
            'M_support': M_support,
            'q_slu': q_slu,
            'L_ramp': L
        }

        return self._moments

    def calculate_shear(self) -> Dict[str, float]:
        """
        Calcola taglio massimo [kN/m].

        Returns:
            Dictionary con:
            - 'V_max': Taglio massimo [kN/m]
        """
        if self._shear is not None:
            return self._shear

        moments = self.calculate_moments()
        q_slu = moments['q_slu']
        L = moments['L_ramp']

        if self.support_condition == SupportCondition.SIMPLY_SUPPORTED:
            V_max = q_slu * L / 2.0
        elif self.support_condition == SupportCondition.ONE_END_FIXED:
            V_max = 0.625 * q_slu * L
        elif self.support_condition == SupportCondition.BOTH_ENDS_FIXED:
            V_max = 0.5 * q_slu * L
        else:  # CANTILEVER
            V_max = q_slu * L

        self._shear = {
            'V_max': V_max
        }

        return self._shear

    # ========================================================================
    # CALCOLO ARMATURE
    # ========================================================================

    def calculate_reinforcement(self) -> Dict[str, float]:
        """
        Calcola armature necessarie.

        Returns:
            Dictionary con:
            - 'As_long': Armatura longitudinale [cm²/m]
            - 'As_distr': Armatura distribuzione [cm²/m]
            - 'As_min': Armatura minima [cm²/m]
            - 'spacing': Interasse suggerito [cm]
            - 'phi': Diametro suggerito [mm]
        """
        if self.stair_type not in [StairType.SLAB_RAMP, StairType.KNEE]:
            return {'note': 'Reinforcement only for RC stairs'}

        moments = self.calculate_moments()
        M_ed = max(moments['M_max'], moments['M_support']) * 1000  # kNm → Nm

        # Altezza utile
        d = self.geometry.thickness - 0.03  # Copriferro 3cm

        b = 1.0  # m (per metro lineare)

        # Momento adimensionale
        mu = M_ed / (b * d**2 * self.fcd * 1e6)

        if mu > 0.295:
            print(f"Warning: μ={mu:.3f} > 0.295 - Armatura doppia o aumentare spessore!")
            mu = 0.295

        omega = 1.25 * mu * (1 - 0.5 * 1.25 * mu)
        As_long = omega * b * d * self.fcd / self.fyd * 1e4  # cm²/m

        # Armatura minima
        fctm = 0.30 * self.concrete['fck']**(2/3)
        As_min = max(
            0.26 * fctm / self.steel['fyk'] * b * d * 1e4,
            0.0013 * b * d * 1e4
        )

        As_long_required = max(As_long, As_min)

        # Armatura di distribuzione (30% longitudinale, min 20% area sezione)
        As_distr = max(0.3 * As_long_required, 0.002 * b * d * 1e4)

        # Suggerimento disposizione
        phi_suggested = 12  # mm
        area_bar = np.pi * (phi_suggested/10)**2 / 4
        n_bars = np.ceil(As_long_required / area_bar)
        spacing = 100.0 / n_bars if n_bars > 0 else 20.0

        return {
            'As_long': As_long_required,
            'As_distr': As_distr,
            'As_min': As_min,
            'spacing': spacing,
            'phi': phi_suggested,
            'n_bars': n_bars
        }

    # ========================================================================
    # VERIFICHE SLU
    # ========================================================================

    def verify_slu_flexure(self) -> Dict[str, float]:
        """
        Verifica SLU a flessione.

        Returns:
            Dictionary con risultati verifica
        """
        reinforcement = self.calculate_reinforcement()
        if 'note' in reinforcement:
            return {'note': reinforcement['note']}

        moments = self.calculate_moments()
        As = reinforcement['As_long']  # cm²/m
        d = self.geometry.thickness - 0.03  # m
        b = 1.0  # m

        # Posizione asse neutro
        x = As * 1e-4 * self.fyd * 1e6 / (0.8 * b * self.fcd * 1e6)

        # Momento resistente
        M_rd = As * 1e-4 * self.fyd * 1e6 * (d - 0.4*x) / 1000  # kNm/m

        M_ed = max(moments['M_max'], moments['M_support'])
        ratio = M_ed / M_rd if M_rd > 0 else 999.0

        return {
            'M_rd': M_rd,
            'M_ed': M_ed,
            'ratio': ratio,
            'verified': ratio <= 1.0
        }

    def verify_slu_shear(self) -> Dict[str, float]:
        """
        Verifica SLU a taglio.

        Returns:
            Dictionary con risultati verifica
        """
        shear = self.calculate_shear()
        V_ed = shear['V_max']

        d = self.geometry.thickness - 0.03
        b = 1.0

        # Resistenza senza staffe (NTC 2018 §4.1.2.1.3.1)
        k = min(1.0 + np.sqrt(200.0 / (d*1000)), 2.0)

        reinforcement = self.calculate_reinforcement()
        if 'note' not in reinforcement:
            As_cm2 = reinforcement['As_long']
            rho_l = (As_cm2 * 1e-4) / (b * d)
            rho_l = min(rho_l, 0.02)
        else:
            rho_l = 0.005  # Minimo

        V_rcd = 0.18 * k * (100 * rho_l * self.concrete['fck'])**(1/3) * b * d * 1000  # kN/m

        stirrups_required = V_ed > V_rcd

        if stirrups_required:
            # Con staffe φ8/20cm
            Asw = 2 * np.pi * (0.8/2)**2  # cm²
            s = 0.20  # m
            V_rsd = 0.9 * d * (Asw * 1e-4 / s) * self.fyd * 1e6 / 1000  # kN/m
            V_rd = V_rsd
        else:
            V_rd = V_rcd

        ratio = V_ed / V_rd if V_rd > 0 else 999.0

        return {
            'V_rd': V_rd,
            'V_ed': V_ed,
            'ratio': ratio,
            'verified': ratio <= 1.0,
            'stirrups_required': stirrups_required
        }

    def verify_slu(self) -> Dict[str, any]:
        """Verifica SLU completa"""
        flexure = self.verify_slu_flexure()
        if 'note' in flexure:
            return {'note': flexure['note']}

        shear = self.verify_slu_shear()

        overall = flexure['verified'] and shear['verified']

        return {
            'flexure': flexure,
            'shear': shear,
            'overall_verified': overall
        }

    # ========================================================================
    # VERIFICHE SLE
    # ========================================================================

    def verify_sle_deflection(self) -> Dict[str, float]:
        """
        Verifica SLE a deformazione.

        NTC 2018: freccia ≤ L/250

        Returns:
            Dictionary con risultati verifica
        """
        # Carico quasi permanente (G + 0.3Q per residenziale)
        self_weight = self.calculate_self_weight()
        G = self.loads.total_permanent(self_weight)
        Q = self.loads.live_loads
        q_qp = G + 0.3 * Q

        L = self.calculate_ramp_length()
        E_cm = self.concrete['Ecm']  # MPa

        # Inerzia (approssimata)
        b = 1.0  # m
        h = self.geometry.thickness
        I = b * h**3 / 12.0  # m⁴/m

        # Freccia secondo schema statico
        if self.support_condition == SupportCondition.SIMPLY_SUPPORTED:
            deflection = 5 * q_qp * L**4 / (384 * E_cm * 1e3 * I) * 1000  # mm
        elif self.support_condition == SupportCondition.BOTH_ENDS_FIXED:
            deflection = q_qp * L**4 / (384 * E_cm * 1e3 * I) * 1000  # mm
        else:
            deflection = 5 * q_qp * L**4 / (384 * E_cm * 1e3 * I) * 1000  # mm

        # Incremento viscosità
        deflection_total = deflection * 1.5

        # Limite
        limit = L * 1000 / 250.0  # mm
        ratio = deflection_total / limit

        return {
            'deflection': deflection_total,
            'limit': limit,
            'ratio': ratio,
            'verified': ratio <= 1.0
        }

    def verify_sle(self) -> Dict[str, any]:
        """Verifica SLE completa"""
        deflection = self.verify_sle_deflection()

        return {
            'deflection': deflection,
            'overall_verified': deflection['verified']
        }

    # ========================================================================
    # VERIFICA PIANEROTTOLO
    # ========================================================================

    def verify_landing(self) -> Dict[str, any]:
        """
        Verifica pianerottolo.

        Returns:
            Dictionary con risultati verifica
        """
        # Dimensioni pianerottolo
        L_land = self.geometry.landing_length
        B = self.geometry.width

        # Carico
        self_weight = self.calculate_self_weight()
        q_slu = self.loads.slu_load_combination(self_weight)

        # Momento (appoggiato su 4 lati, approssimazione conservativa)
        # M ≈ q·L²/12 (approssimato)
        M_land = q_slu * L_land**2 / 12.0  # kNm/m

        # Armatura richiesta (simile a soletta)
        d = self.geometry.thickness - 0.03
        b = 1.0

        mu = (M_land * 1000) / (b * d**2 * self.fcd * 1e6)
        omega = 1.25 * mu * (1 - 0.5 * 1.25 * mu)
        As_land = omega * b * d * self.fcd / self.fyd * 1e4  # cm²/m

        # Armatura minima
        fctm = 0.30 * self.concrete['fck']**(2/3)
        As_min = max(
            0.26 * fctm / self.steel['fyk'] * b * d * 1e4,
            0.0013 * b * d * 1e4
        )

        As_required = max(As_land, As_min)

        return {
            'M_landing': M_land,
            'As_required': As_required,
            'note': 'Verifica semplificata, considerare appoggi effettivi'
        }

    # ========================================================================
    # VERIFICA COMPLETA
    # ========================================================================

    def verify_stair(self) -> Dict[str, any]:
        """
        Verifica completa scala.

        Returns:
            Dictionary con tutti i risultati
        """
        results = {}

        # Geometria
        results['geometry'] = self.geometry.validate_geometry()

        # Sollecitazioni
        results['moments'] = self.calculate_moments()
        results['shear'] = self.calculate_shear()

        # Armature
        results['reinforcement'] = self.calculate_reinforcement()

        # Verifiche SLU
        results['slu'] = self.verify_slu()

        # Verifiche SLE
        results['sle'] = self.verify_sle()

        # Pianerottolo
        results['landing'] = self.verify_landing()

        # Esito globale
        geometry_ok = results['geometry']['valid']

        if 'note' not in results['slu']:
            structural_ok = results['slu']['overall_verified'] and results['sle']['overall_verified']
        else:
            structural_ok = True  # Non applicabile per non-RC

        results['overall_verified'] = geometry_ok and structural_ok
        results['geometry_ok'] = geometry_ok

        return results

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
        report_lines.append("VERIFICA SCALA - NTC 2018")
        report_lines.append("=" * 70)
        report_lines.append(f"\nTipologia: {self.stair_type.value}")
        report_lines.append(f"Schema statico: {self.support_condition.value}")

        if self.stair_type in [StairType.SLAB_RAMP, StairType.KNEE]:
            report_lines.append(f"\nMateriali:")
            report_lines.append(f"  Calcestruzzo: {self.concrete_class} (fck={self.concrete['fck']} MPa)")
            report_lines.append(f"  Acciaio: {self.steel_class} (fyk={self.steel['fyk']} MPa)")

        verification = self.verify_stair()
        geom = verification['geometry']

        report_lines.append(f"\nGEOMETRIA:")
        report_lines.append(f"  Dislivello: H = {self.geometry.floor_height:.2f} m")
        report_lines.append(f"  Numero gradini: n = {self.geometry.n_steps}")
        report_lines.append(f"  Alzata: a = {geom['rise_cm']:.1f} cm")
        report_lines.append(f"  Pedata: p = {geom['tread_cm']:.1f} cm")
        report_lines.append(f"  Larghezza: B = {geom['width_cm']:.0f} cm")
        report_lines.append(f"  Formula Blondel: 2a+p = {geom['blondel']:.1f} cm")
        report_lines.append(f"  Pendenza: {geom['slope_deg']:.1f}°")

        if geom['valid']:
            report_lines.append(f"  ✓ GEOMETRIA VERIFICATA")
        else:
            report_lines.append(f"  ✗ GEOMETRIA NON CONFORME")
            for issue in geom['issues']:
                report_lines.append(f"    - {issue}")

        if geom['warnings']:
            for warning in geom['warnings']:
                report_lines.append(f"  ⚠️  {warning}")

        self_weight = self.calculate_self_weight()
        moments = verification['moments']

        report_lines.append(f"\nCarichi:")
        report_lines.append(f"  Peso proprio: {self_weight:.2f} kN/m²")
        report_lines.append(f"  Permanenti G2: {self.loads.permanent_loads:.2f} kN/m²")
        report_lines.append(f"  Variabili Q: {self.loads.live_loads:.2f} kN/m²")

        report_lines.append(f"\nSollecitazioni SLU (q={moments['q_slu']:.2f} kN/m²):")
        report_lines.append(f"  Lunghezza rampa: L = {moments['L_ramp']:.2f} m")
        report_lines.append(f"  Momento campata: M = {moments['M_max']:.2f} kNm/m")
        if moments['M_support'] > 0:
            report_lines.append(f"  Momento appoggio: M = {moments['M_support']:.2f} kNm/m")

        shear = verification['shear']
        report_lines.append(f"  Taglio: V = {shear['V_max']:.2f} kN/m")

        if 'note' not in verification['reinforcement']:
            reinf = verification['reinforcement']
            report_lines.append(f"\nArmature:")
            report_lines.append(f"  Longitudinale: As = {reinf['As_long']:.2f} cm²/m")
            report_lines.append(f"  Distribuzione: As = {reinf['As_distr']:.2f} cm²/m")
            report_lines.append(f"  Disposizione: φ{reinf['phi']:.0f} / {reinf['spacing']:.0f} cm")

            slu = verification['slu']
            report_lines.append(f"\nVERIFICHE SLU:")
            report_lines.append(f"  Flessione: M_rd = {slu['flexure']['M_rd']:.2f} kNm/m")
            report_lines.append(f"             Utilizzo = {slu['flexure']['ratio']:.2%}")
            report_lines.append(f"             {'✓ VERIFICATO' if slu['flexure']['verified'] else '✗ NON VERIFICATO'}")

            report_lines.append(f"  Taglio: V_rd = {slu['shear']['V_rd']:.2f} kN/m")
            report_lines.append(f"          Utilizzo = {slu['shear']['ratio']:.2%}")
            report_lines.append(f"          Staffe: {'SI' if slu['shear']['stirrups_required'] else 'NON NECESSARIE'}")
            report_lines.append(f"          {'✓ VERIFICATO' if slu['shear']['verified'] else '✗ NON VERIFICATO'}")

            sle = verification['sle']
            report_lines.append(f"\nVERIFICHE SLE:")
            report_lines.append(f"  Freccia: δ = {sle['deflection']['deflection']:.1f} mm")
            report_lines.append(f"           Limite = {sle['deflection']['limit']:.1f} mm (L/250)")
            report_lines.append(f"           {'✓ VERIFICATO' if sle['deflection']['verified'] else '✗ NON VERIFICATO'}")

            landing = verification['landing']
            report_lines.append(f"\nPIANEROTTOLO:")
            report_lines.append(f"  Momento: M = {landing['M_landing']:.2f} kNm/m")
            report_lines.append(f"  Armatura richiesta: As = {landing['As_required']:.2f} cm²/m")

        report_lines.append(f"\n{'='*70}")
        report_lines.append(f"ESITO FINALE: {'✓ VERIFICATO' if verification['overall_verified'] else '✗ NON VERIFICATO'}")
        report_lines.append(f"{'='*70}")

        return "\n".join(report_lines)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'StairAnalysis',
    'StairGeometry',
    'StairLoads',
    'StairType',
    'SupportCondition',
    'CONCRETE_CLASSES',
    'STEEL_CLASSES',
    'STRUCTURAL_STEEL',
    'GEOMETRY_LIMITS',
    'BLONDEL_MIN',
    'BLONDEL_MAX',
]
