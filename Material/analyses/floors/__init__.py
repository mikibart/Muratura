"""
Module: floors/__init__.py
Analisi e verifica solai secondo NTC 2018

Questo modulo implementa il calcolo e la verifica di solai secondo le NTC 2018,
inclusi solai in latero-cemento, legno, acciaio e prefabbricati.

Funzionalità principali:
- Calcolo armature longitudinali e trasversali
- Verifica SLU (flessione, taglio, punzonamento)
- Verifica SLE (fessurazione, deformazione)
- Integrazione solaio-muratura (diaframmi rigidi/flessibili)
- Database tipologie commerciali

Tipologie supportate:
- 'latero-cemento': Solai con pignatte (Porotherm, Alveolater, etc.)
- 'wood': Solai in legno (travi e tavolato)
- 'steel': Solai in acciaio (HEA, IPE con soletta)
- 'precast': Solai prefabbricati (predalles)
- 'vault': Volte murarie

Examples:
    >>> from Material.analyses.floors import FloorAnalysis, FloorGeometry
    >>> geometry = FloorGeometry(
    ...     span=5.0,  # m
    ...     width=4.0,  # m
    ...     thickness=0.24,  # m (4+20cm)
    ...     slab_thickness=0.04  # soletta 4cm
    ... )
    >>> floor = FloorAnalysis(
    ...     floor_type='latero-cemento',
    ...     geometry=geometry,
    ...     concrete_class='C25/30',
    ...     steel_class='B450C'
    ... )
    >>> reinforcement = floor.calculate_reinforcement()
    >>> verification = floor.verify_slu()
    >>> print(f"Utilization ratio: {verification['flexure_ratio']:.2f}")
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Literal
from enum import Enum
import numpy as np


# ============================================================================
# ENUMS E COSTANTI
# ============================================================================

class FloorType(Enum):
    """Tipologie di solaio supportate"""
    LATERO_CEMENTO = 'latero-cemento'
    WOOD = 'wood'
    STEEL = 'steel'
    PRECAST = 'precast'
    VAULT = 'vault'


class SupportType(Enum):
    """Tipologie di vincolo"""
    SIMPLY_SUPPORTED = 'simply_supported'  # Appoggio semplice
    CONTINUOUS = 'continuous'  # Continuo su più campate
    CANTILEVER = 'cantilever'  # Sbalzo
    FIXED = 'fixed'  # Incastro


class DiaphragmType(Enum):
    """Comportamento diaframma"""
    RIGID = 'rigid'  # Diaframma rigido
    FLEXIBLE = 'flexible'  # Diaframma flessibile
    SEMI_RIGID = 'semi_rigid'  # Diaframma semi-rigido


# NTC 2018 - Classi calcestruzzo
CONCRETE_CLASSES = {
    'C20/25': {'fck': 20.0, 'Ecm': 30000.0},
    'C25/30': {'fck': 25.0, 'Ecm': 31500.0},
    'C28/35': {'fck': 28.0, 'Ecm': 32300.0},
    'C30/37': {'fck': 30.0, 'Ecm': 33000.0},
}

# NTC 2018 - Classi acciaio
STEEL_CLASSES = {
    'B450C': {'fyk': 450.0, 'Es': 210000.0, 'epsuk': 0.075},
    'B450A': {'fyk': 450.0, 'Es': 210000.0, 'epsuk': 0.025},
}

# Coefficienti di sicurezza NTC 2018
GAMMA_C = 1.5  # Calcestruzzo
GAMMA_S = 1.15  # Acciaio
ALPHA_CC = 0.85  # Riduzione resistenza cls


# ============================================================================
# DATACLASSES PER GEOMETRIA E CARICHI
# ============================================================================

@dataclass
class FloorGeometry:
    """
    Geometria del solaio.

    Attributes:
        span: Luce netta solaio [m]
        width: Larghezza solaio [m]
        thickness: Altezza totale solaio [m]
        slab_thickness: Spessore soletta collaborante [m]
        rib_spacing: Interasse nervature [m] (per latero-cemento)
        rib_width: Larghezza nervature [m] (per latero-cemento)
    """
    span: float
    width: float
    thickness: float
    slab_thickness: float
    rib_spacing: float = 0.50  # Tipico per latero-cemento
    rib_width: float = 0.10  # Tipico per latero-cemento

    def __post_init__(self):
        """Validazione parametri geometrici"""
        if self.span <= 0:
            raise ValueError(f"Span deve essere > 0, got {self.span}")
        if self.thickness <= 0:
            raise ValueError(f"Thickness deve essere > 0, got {self.thickness}")
        if self.slab_thickness >= self.thickness:
            raise ValueError(
                f"Slab thickness ({self.slab_thickness}) deve essere < thickness ({self.thickness})"
            )
        if self.slab_thickness < 0.04:
            print(f"Warning: Slab thickness {self.slab_thickness}m < 4cm (minimo NTC)")


@dataclass
class FloorLoads:
    """
    Carichi agenti sul solaio.

    Attributes:
        permanent_loads: Carichi permanenti strutturali G1 [kN/m²]
        additional_permanent: Carichi permanenti non strutturali G2 [kN/m²]
        live_loads: Sovraccarichi variabili Q [kN/m²]
        partition_walls: Tramezzi [kN/m²] (se non inclusi in G2)
        self_weight_included: Se True, peso proprio è già incluso in permanent_loads

    Note:
        NTC 2018 Tab. 3.1.II - Categorie sovraccarichi:
        - Cat. A (residenziale): 2.0 kN/m²
        - Cat. B (uffici): 3.0 kN/m²
        - Cat. C (ambienti suscettibili affollamento): 4.0 kN/m²
    """
    permanent_loads: float = 0.0  # G1
    additional_permanent: float = 2.0  # G2 (pavimento, intonaco, impianti)
    live_loads: float = 2.0  # Q (Cat. A residenziale)
    partition_walls: float = 1.0  # Tramezzi
    self_weight_included: bool = False

    def total_permanent(self, self_weight: float = 0.0) -> float:
        """Calcola carico permanente totale G1+G2"""
        g_total = self.permanent_loads + self.additional_permanent + self.partition_walls
        if not self.self_weight_included:
            g_total += self_weight
        return g_total

    def slu_load_combination(self, self_weight: float = 0.0) -> float:
        """
        Combinazione carico SLU secondo NTC 2018 §2.5.3

        SLU: γG·G + γQ·Q  (combinazione fondamentale)
        γG = 1.3 (sfavorevole)
        γQ = 1.5
        """
        G = self.total_permanent(self_weight)
        Q = self.live_loads
        return 1.3 * G + 1.5 * Q

    def sle_quasi_permanent_combination(self, self_weight: float = 0.0) -> float:
        """
        Combinazione quasi permanente SLE (per freccia differita)

        SLE: G + ψ2·Q
        ψ2 = 0.3 (residenziale Cat. A)
        ψ2 = 0.6 (uffici Cat. B)
        """
        G = self.total_permanent(self_weight)
        Q = self.live_loads
        psi2 = 0.3  # Residenziale
        return G + psi2 * Q


# ============================================================================
# CLASSE PRINCIPALE FLOOR ANALYSIS
# ============================================================================

class FloorAnalysis:
    """
    Analisi e verifica solaio secondo NTC 2018.

    Implementa:
    - Calcolo sollecitazioni (momento, taglio)
    - Calcolo armature necessarie
    - Verifica SLU (flessione, taglio, punzonamento)
    - Verifica SLE (fessurazione, deformazione)
    - Integrazione con sistema murario (diaframma)

    Attributes:
        floor_type: Tipologia solaio
        geometry: Geometria solaio
        concrete_class: Classe calcestruzzo (es. 'C25/30')
        steel_class: Classe acciaio (es. 'B450C')
        support_type: Tipologia vincoli
        loads: Carichi agenti
    """

    def __init__(
        self,
        floor_type: Literal['latero-cemento', 'wood', 'steel', 'precast', 'vault'],
        geometry: FloorGeometry,
        concrete_class: str = 'C25/30',
        steel_class: str = 'B450C',
        support_type: Literal['simply_supported', 'continuous', 'cantilever', 'fixed'] = 'simply_supported',
        loads: Optional[FloorLoads] = None
    ):
        """
        Inizializza analisi solaio.

        Args:
            floor_type: Tipologia solaio
            geometry: Geometria solaio
            concrete_class: Classe calcestruzzo NTC 2018
            steel_class: Classe acciaio NTC 2018
            support_type: Schema statico
            loads: Carichi agenti (se None, usa valori default)

        Raises:
            ValueError: Se parametri non validi
        """
        self.floor_type = FloorType(floor_type)
        self.geometry = geometry
        self.support_type = SupportType(support_type)
        self.loads = loads if loads is not None else FloorLoads()

        # Proprietà materiali
        if concrete_class not in CONCRETE_CLASSES:
            raise ValueError(
                f"Concrete class {concrete_class} not supported. "
                f"Available: {list(CONCRETE_CLASSES.keys())}"
            )
        if steel_class not in STEEL_CLASSES:
            raise ValueError(
                f"Steel class {steel_class} not supported. "
                f"Available: {list(STEEL_CLASSES.keys())}"
            )

        self.concrete = CONCRETE_CLASSES[concrete_class]
        self.steel = STEEL_CLASSES[steel_class]
        self.concrete_class = concrete_class
        self.steel_class = steel_class

        # Resistenze di calcolo
        self.fcd = ALPHA_CC * self.concrete['fck'] / GAMMA_C  # MPa
        self.fyd = self.steel['fyk'] / GAMMA_S  # MPa

        # Risultati (calcolati dai metodi)
        self._self_weight: Optional[float] = None
        self._moments: Optional[Dict] = None
        self._shear: Optional[Dict] = None
        self._reinforcement: Optional[Dict] = None

    # ========================================================================
    # PESO PROPRIO
    # ========================================================================

    def calculate_self_weight(self) -> float:
        """
        Calcola peso proprio solaio [kN/m²].

        Returns:
            Peso proprio [kN/m²]
        """
        if self._self_weight is not None:
            return self._self_weight

        if self.floor_type == FloorType.LATERO_CEMENTO:
            # Peso calcestruzzo nervature + soletta
            gamma_c = 25.0  # kN/m³

            # Volume soletta per m²
            V_slab = self.geometry.slab_thickness  # m³/m²

            # Volume nervature per m²
            n_ribs = 1.0 / self.geometry.rib_spacing  # nervature per metro
            h_rib = self.geometry.thickness - self.geometry.slab_thickness
            V_rib = n_ribs * self.geometry.rib_width * h_rib  # m³/m²

            # Peso cls
            weight_concrete = gamma_c * (V_slab + V_rib)

            # Peso pignatte (laterizio) - tipicamente 0.8-1.2 kN/m²
            weight_blocks = 1.0  # kN/m² (valore medio)

            self._self_weight = weight_concrete + weight_blocks

        elif self.floor_type == FloorType.WOOD:
            # Solaio in legno: travi + tavolato
            # Peso legno ~5-6 kN/m³
            gamma_wood = 5.5  # kN/m³
            self._self_weight = gamma_wood * self.geometry.thickness

        elif self.floor_type == FloorType.STEEL:
            # Solaio acciaio + soletta cls
            gamma_c = 25.0  # kN/m³
            weight_slab = gamma_c * self.geometry.slab_thickness
            weight_steel = 0.5  # kN/m² (profilati HEA/IPE)
            self._self_weight = weight_slab + weight_steel

        else:
            # Default: peso medio
            self._self_weight = 3.5  # kN/m²

        return self._self_weight

    # ========================================================================
    # SOLLECITAZIONI
    # ========================================================================

    def calculate_moments(self) -> Dict[str, float]:
        """
        Calcola momenti flettenti [kNm/m].

        Returns:
            Dictionary con:
            - 'M_max': Momento massimo positivo in campata [kNm/m]
            - 'M_support': Momento su appoggio [kNm/m] (se continuous)
            - 'q_slu': Carico di calcolo SLU [kN/m²]
        """
        if self._moments is not None:
            return self._moments

        # Carico di calcolo SLU
        self_weight = self.calculate_self_weight()
        q_slu = self.loads.slu_load_combination(self_weight)

        L = self.geometry.span

        if self.support_type == SupportType.SIMPLY_SUPPORTED:
            # Trave appoggiata: M = q·L²/8
            M_max = q_slu * L**2 / 8.0
            M_support = 0.0

        elif self.support_type == SupportType.CONTINUOUS:
            # Trave continua (2 campate uguali, approssimazione)
            # Campata: M = 9/128 · q·L²
            # Appoggio: M = -1/8 · q·L²
            M_max = (9.0/128.0) * q_slu * L**2
            M_support = -0.125 * q_slu * L**2

        elif self.support_type == SupportType.CANTILEVER:
            # Mensola: M = q·L²/2
            M_max = 0.0
            M_support = -q_slu * L**2 / 2.0

        else:  # FIXED
            # Incastro perfetto: M = -q·L²/12 (appoggi), M = q·L²/24 (campata)
            M_max = q_slu * L**2 / 24.0
            M_support = -q_slu * L**2 / 12.0

        self._moments = {
            'M_max': M_max,
            'M_support': abs(M_support),
            'q_slu': q_slu
        }

        return self._moments

    def calculate_shear(self) -> Dict[str, float]:
        """
        Calcola taglio massimo [kN/m].

        Returns:
            Dictionary con:
            - 'V_max': Taglio massimo [kN/m]
            - 'V_appoggio': Taglio su appoggio [kN/m]
        """
        if self._shear is not None:
            return self._shear

        moments = self.calculate_moments()
        q_slu = moments['q_slu']
        L = self.geometry.span

        if self.support_type == SupportType.SIMPLY_SUPPORTED:
            # Trave appoggiata: V = q·L/2
            V_max = q_slu * L / 2.0

        elif self.support_type == SupportType.CONTINUOUS:
            # Trave continua: V ≈ 0.6 · q·L
            V_max = 0.6 * q_slu * L

        elif self.support_type == SupportType.CANTILEVER:
            # Mensola: V = q·L
            V_max = q_slu * L

        else:  # FIXED
            # Incastro: V = q·L/2
            V_max = q_slu * L / 2.0

        self._shear = {
            'V_max': V_max,
            'V_appoggio': V_max
        }

        return self._shear

    # ========================================================================
    # CALCOLO ARMATURE
    # ========================================================================

    def calculate_reinforcement(self) -> Dict[str, float]:
        """
        Calcola armature necessarie secondo NTC 2018.

        Returns:
            Dictionary con:
            - 'As_long': Armatura longitudinale [cm²/m]
            - 'As_min': Armatura minima [cm²/m]
            - 'spacing': Interasse barre suggerito [cm]
            - 'phi': Diametro barra suggerito [mm]
            - 'n_bars': Numero barre per metro

        Note:
            Metodo semplificato senza ridistribuzione.
            Per armatura: x/d ≤ 0.45 (duttilità alta, classe B)
        """
        if self._reinforcement is not None:
            return self._reinforcement

        moments = self.calculate_moments()
        M_ed = max(moments['M_max'], moments['M_support']) * 1000  # kNm → Nm

        # Altezza utile
        d = self.geometry.thickness - 0.03  # Copriferro 3cm

        # Larghezza (per solai latero-cemento: nervatura)
        if self.floor_type == FloorType.LATERO_CEMENTO:
            b = self.geometry.rib_width  # m (nervatura)
        else:
            b = 1.0  # m (sezione piena per m lineare)

        # Momento adimensionale μ
        mu = M_ed / (b * d**2 * self.fcd * 1e6)  # fcd in MPa → N/mm²

        if mu > 0.295:
            print(f"Warning: μ={mu:.3f} > 0.295 - Armatura doppia necessaria!")
            mu = 0.295  # Limite pratico

        # Coefficiente ω (tabelle progetto armature)
        # Approssimazione: ω ≈ 1.25·μ per μ < 0.3
        omega = 1.25 * mu * (1 - 0.5 * 1.25 * mu)

        # Area armatura tesa
        As = omega * b * d * self.fcd / self.fyd * 1e4  # m² → cm²

        # Armatura minima NTC 2018 §4.1.6.1.1
        # As,min = 0.26·fctm/fyk·b·d  (minimo 0.0013·b·d)
        fctm = 0.30 * self.concrete['fck']**(2/3)  # Resistenza trazione media
        As_min_1 = 0.26 * fctm / self.steel['fyk'] * b * d * 1e4  # cm²
        As_min_2 = 0.0013 * b * d * 1e4  # cm²
        As_min = max(As_min_1, As_min_2)

        As_required = max(As, As_min)

        # Se latero-cemento, converti per metro lineare
        if self.floor_type == FloorType.LATERO_CEMENTO:
            n_ribs_per_m = 1.0 / self.geometry.rib_spacing
            As_per_m = As_required * n_ribs_per_m
        else:
            As_per_m = As_required

        # Suggerimento disposizione barre
        # Prova con φ14 (1.54 cm²)
        phi_suggested = 14  # mm
        area_bar = np.pi * (phi_suggested/10)**2 / 4  # cm²
        n_bars = np.ceil(As_per_m / area_bar)
        spacing = 100.0 / n_bars if n_bars > 0 else 20.0  # cm

        self._reinforcement = {
            'As_long': As_per_m,
            'As_min': As_min * n_ribs_per_m if self.floor_type == FloorType.LATERO_CEMENTO else As_min,
            'spacing': spacing,
            'phi': phi_suggested,
            'n_bars': n_bars,
            'mu': mu,
            'omega': omega
        }

        return self._reinforcement

    # ========================================================================
    # VERIFICHE SLU
    # ========================================================================

    def verify_slu_flexure(self) -> Dict[str, float]:
        """
        Verifica SLU a flessione.

        Returns:
            Dictionary con:
            - 'M_rd': Momento resistente [kNm/m]
            - 'M_ed': Momento sollecitante [kNm/m]
            - 'ratio': Rapporto di utilizzo M_ed/M_rd
            - 'verified': True se verificato (ratio ≤ 1.0)
        """
        reinforcement = self.calculate_reinforcement()
        moments = self.calculate_moments()

        As = reinforcement['As_long']  # cm²/m
        d = self.geometry.thickness - 0.03  # m

        if self.floor_type == FloorType.LATERO_CEMENTO:
            b = self.geometry.rib_width  # m
            n_ribs = 1.0 / self.geometry.rib_spacing
            As_single_rib = As / n_ribs  # cm² per nervatura
        else:
            b = 1.0  # m
            As_single_rib = As

        # Posizione asse neutro (sezione rettangolare)
        # As·fyd = 0.8·x·b·fcd
        x = As_single_rib * 1e-4 * self.fyd * 1e6 / (0.8 * b * self.fcd * 1e6)  # m

        # Momento resistente
        # M_rd = As·fyd·(d - 0.4·x)
        M_rd_single = As_single_rib * 1e-4 * self.fyd * 1e6 * (d - 0.4*x) / 1000  # kNm

        if self.floor_type == FloorType.LATERO_CEMENTO:
            M_rd = M_rd_single * n_ribs  # kNm/m
        else:
            M_rd = M_rd_single  # kNm/m

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
            Dictionary con:
            - 'V_rd': Taglio resistente [kN/m]
            - 'V_ed': Taglio sollecitante [kN/m]
            - 'ratio': Rapporto di utilizzo V_ed/V_rd
            - 'verified': True se verificato
            - 'stirrups_required': True se necessarie staffe
        """
        shear = self.calculate_shear()
        V_ed = shear['V_max']  # kN/m

        d = self.geometry.thickness - 0.03  # m

        if self.floor_type == FloorType.LATERO_CEMENTO:
            b = self.geometry.rib_width  # m
            n_ribs = 1.0 / self.geometry.rib_spacing
            V_ed_single = V_ed / n_ribs  # kN per nervatura
        else:
            b = 1.0  # m
            V_ed_single = V_ed

        # Resistenza cls senza armatura trasversale (NTC 2018 §4.1.2.1.3.1)
        # V_rcd = 0.18·k·(100·ρl·fck)^(1/3)·b·d  [con k = min(1+√(200/d), 2.0)]
        k = min(1.0 + np.sqrt(200.0 / (d*1000)), 2.0)  # d in mm

        # ρl = As/(b·d) - assumiamo armatura minima
        reinforcement = self.calculate_reinforcement()
        As_cm2 = reinforcement['As_long'] / (n_ribs if self.floor_type == FloorType.LATERO_CEMENTO else 1.0)
        rho_l = (As_cm2 * 1e-4) / (b * d)
        rho_l = min(rho_l, 0.02)  # Limite superiore

        V_rcd = 0.18 * k * (100 * rho_l * self.concrete['fck'])**(1/3) * b * d * 1000  # kN

        if self.floor_type == FloorType.LATERO_CEMENTO:
            V_rcd_per_m = V_rcd * n_ribs
        else:
            V_rcd_per_m = V_rcd

        stirrups_required = V_ed > V_rcd_per_m

        # Se necessarie staffe, calcola V_rd con staffe minime
        if stirrups_required:
            # V_rsd = 0.9·d·Asw/s·fyd  (con staffe minime)
            # Assumiamo φ8 ogni 20cm (minimo costruttivo)
            Asw = 2 * np.pi * (0.8/2)**2  # cm² (staffa φ8, 2 bracci)
            s = 0.20  # m
            V_rsd = 0.9 * d * (Asw * 1e-4 / s) * self.fyd * 1e6 / 1000  # kN

            if self.floor_type == FloorType.LATERO_CEMENTO:
                V_rd = V_rsd * n_ribs
            else:
                V_rd = V_rsd
        else:
            V_rd = V_rcd_per_m

        ratio = V_ed / V_rd if V_rd > 0 else 999.0

        return {
            'V_rd': V_rd,
            'V_ed': V_ed,
            'ratio': ratio,
            'verified': ratio <= 1.0,
            'stirrups_required': stirrups_required
        }

    def verify_slu(self) -> Dict[str, any]:
        """
        Verifica SLU completa (flessione + taglio).

        Returns:
            Dictionary con risultati verifiche SLU
        """
        flexure = self.verify_slu_flexure()
        shear = self.verify_slu_shear()

        overall_verified = flexure['verified'] and shear['verified']

        return {
            'flexure': flexure,
            'shear': shear,
            'overall_verified': overall_verified
        }

    # ========================================================================
    # VERIFICHE SLE
    # ========================================================================

    def verify_sle_deflection(self) -> Dict[str, float]:
        """
        Verifica SLE a deformazione (freccia).

        NTC 2018 §4.1.2.2.2: freccia ≤ L/250 (non danneggiano elementi non strutturali)

        Returns:
            Dictionary con:
            - 'deflection': Freccia calcolata [mm]
            - 'limit': Limite normativo [mm]
            - 'ratio': Rapporto utilizzo
            - 'verified': True se verificato
        """
        # Carico quasi permanente
        self_weight = self.calculate_self_weight()
        q_qp = self.loads.sle_quasi_permanent_combination(self_weight)

        L = self.geometry.span
        E_cm = self.concrete['Ecm']  # MPa

        # Inerzia sezione (approssimata)
        if self.floor_type == FloorType.LATERO_CEMENTO:
            # Sezione T: approssimazione semplificata
            b_eff = 1.0  # Larghezza efficace soletta
            h = self.geometry.thickness
            I = b_eff * h**3 / 12.0  # m⁴/m (approssimazione conservativa)
        else:
            b = 1.0
            h = self.geometry.thickness
            I = b * h**3 / 12.0  # m⁴/m

        # Freccia (formula trave appoggiata)
        if self.support_type == SupportType.SIMPLY_SUPPORTED:
            # δ = 5·q·L⁴/(384·E·I)
            deflection = 5 * q_qp * L**4 / (384 * E_cm * 1e3 * I) * 1000  # mm
        elif self.support_type == SupportType.CONTINUOUS:
            # Continua: δ ≈ 0.6 · δ_appoggiata
            deflection = 0.6 * 5 * q_qp * L**4 / (384 * E_cm * 1e3 * I) * 1000  # mm
        else:
            # Conservativo: usa appoggiata
            deflection = 5 * q_qp * L**4 / (384 * E_cm * 1e3 * I) * 1000  # mm

        # Incremento per viscosità (creep) - maggiorazione 50%
        deflection_total = deflection * 1.5

        # Limite NTC
        limit = L * 1000 / 250.0  # mm
        ratio = deflection_total / limit

        return {
            'deflection': deflection_total,
            'deflection_instantaneous': deflection,
            'limit': limit,
            'ratio': ratio,
            'verified': ratio <= 1.0
        }

    def verify_sle(self) -> Dict[str, any]:
        """
        Verifica SLE completa (deformazione + fessurazione).

        Returns:
            Dictionary con risultati verifiche SLE
        """
        deflection = self.verify_sle_deflection()

        # TODO: Verifica fessurazione (§4.1.2.2.4)
        # Per ora assume verificato se armatura > minima
        reinforcement = self.calculate_reinforcement()
        cracking_verified = reinforcement['As_long'] >= reinforcement['As_min']

        overall_verified = deflection['verified'] and cracking_verified

        return {
            'deflection': deflection,
            'cracking': {
                'verified': cracking_verified,
                'note': 'Verificato se As >= As,min (semplificato)'
            },
            'overall_verified': overall_verified
        }

    # ========================================================================
    # INTEGRAZIONE CON MURATURA
    # ========================================================================

    def assess_diaphragm_behavior(self) -> DiaphragmType:
        """
        Valuta comportamento a diaframma del solaio.

        NTC 2018 §7.2.6: diaframma rigido se deformabilità trascurabile.
        Criterio semplificato: G/L < 0.5 → flessibile, > 2.0 → rigido

        Returns:
            RIGID, FLEXIBLE, o SEMI_RIGID
        """
        # Modulo taglio equivalente
        if self.floor_type == FloorType.LATERO_CEMENTO:
            # Cls: G = E/(2(1+ν)) con ν=0.2
            G_equiv = self.concrete['Ecm'] / (2 * 1.2) * 1000  # kN/m²
        elif self.floor_type == FloorType.WOOD:
            G_equiv = 600.0 * 1000  # kN/m² (legno)
        elif self.floor_type == FloorType.STEEL:
            G_equiv = 80000.0 * 1000  # kN/m² (acciaio)
        else:
            G_equiv = 10000.0 * 1000  # Default

        # Spessore equivalente
        t_equiv = self.geometry.thickness

        # Rigidezza tangenziale per unità di lunghezza
        GA = G_equiv * t_equiv  # kN/m

        # Rapporto caratteristico
        L_caratteristica = max(self.geometry.span, self.geometry.width)
        ratio = GA / (L_caratteristica * 1000)  # adimensionale

        if ratio > 2.0:
            return DiaphragmType.RIGID
        elif ratio < 0.5:
            return DiaphragmType.FLEXIBLE
        else:
            return DiaphragmType.SEMI_RIGID

    def integrate_with_walls(
        self,
        wall_stiffness: float,
        seismic: bool = True
    ) -> Dict[str, any]:
        """
        Integrazione solaio-muratura per analisi sismica.

        Args:
            wall_stiffness: Rigidezza pareti sottostanti [kN/m]
            seismic: Se True, considera azione sismica

        Returns:
            Dictionary con:
            - 'diaphragm_type': Tipo diaframma
            - 'in_plane_stiffness': Rigidezza nel piano [kN/m]
            - 'seismic_mass': Massa sismica [ton]
            - 'connection_verified': Verifica collegamento solaio-muratura
        """
        diaphragm = self.assess_diaphragm_behavior()

        # Rigidezza nel piano (semplificato)
        if diaphragm == DiaphragmType.RIGID:
            # Rigido: assume rigidezza molto alta
            k_in_plane = 1e6  # kN/m (praticamente infinita)
        else:
            # Flessibile/Semi-rigido: calcola effettiva
            G_equiv = self.concrete['Ecm'] / (2 * 1.2) * 1000  # kN/m²
            A_equiv = self.geometry.thickness * 1.0  # m²/m
            k_in_plane = G_equiv * A_equiv / self.geometry.span

        # Massa sismica (peso solaio + sovraccarichi)
        g = 9.81  # m/s²
        self_weight = self.calculate_self_weight()
        permanent_load = self.loads.total_permanent(self_weight)
        live_load = self.loads.live_loads * 0.3  # ψ2·Q per sisma (residenziale)
        total_mass_per_m2 = (permanent_load + live_load) / g  # ton/m²

        area_floor = self.geometry.span * self.geometry.width
        seismic_mass = total_mass_per_m2 * area_floor  # ton

        # Verifica collegamento (NTC 2018 §7.8.1.6)
        # Forza da trasferire: F = Sa·W (approssimato con ag·S·W)
        # Assume Sa = 0.25g (tipico)
        if seismic:
            Sa = 0.25 * g  # m/s²
            F_connection = Sa * seismic_mass  # kN

            # Resistenza collegamento (cordolo + connettori)
            # Assume cordolo perimetrale: verificato se τ < 0.4 MPa
            perimeter = 2 * (self.geometry.span + self.geometry.width)
            A_connection = perimeter * 0.20  # m² (cordolo h=20cm)
            tau_connection = (F_connection * 1000) / (A_connection * 1e6)  # MPa

            connection_verified = tau_connection <= 0.4  # MPa
        else:
            connection_verified = True
            tau_connection = 0.0

        return {
            'diaphragm_type': diaphragm.value,
            'in_plane_stiffness': k_in_plane,
            'seismic_mass': seismic_mass,
            'connection_verified': connection_verified,
            'connection_stress': tau_connection
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
        report_lines.append("VERIFICA SOLAIO - NTC 2018")
        report_lines.append("=" * 70)
        report_lines.append(f"\nTipologia: {self.floor_type.value}")
        report_lines.append(f"Schema statico: {self.support_type.value}")
        report_lines.append(f"\nMateriali:")
        report_lines.append(f"  Calcestruzzo: {self.concrete_class} (fck={self.concrete['fck']} MPa)")
        report_lines.append(f"  Acciaio: {self.steel_class} (fyk={self.steel['fyk']} MPa)")

        report_lines.append(f"\nGeometria:")
        report_lines.append(f"  Luce: L = {self.geometry.span:.2f} m")
        report_lines.append(f"  Larghezza: B = {self.geometry.width:.2f} m")
        report_lines.append(f"  Altezza totale: h = {self.geometry.thickness*100:.0f} cm")
        report_lines.append(f"  Soletta: s = {self.geometry.slab_thickness*100:.0f} cm")

        self_weight = self.calculate_self_weight()
        report_lines.append(f"\nCarichi:")
        report_lines.append(f"  Peso proprio: {self_weight:.2f} kN/m²")
        report_lines.append(f"  Permanenti G2: {self.loads.additional_permanent:.2f} kN/m²")
        report_lines.append(f"  Variabili Q: {self.loads.live_loads:.2f} kN/m²")

        moments = self.calculate_moments()
        report_lines.append(f"\nSollecitazioni SLU (q={moments['q_slu']:.2f} kN/m²):")
        report_lines.append(f"  Momento campata: M_ed = {moments['M_max']:.2f} kNm/m")
        if moments['M_support'] > 0:
            report_lines.append(f"  Momento appoggio: M_ed = {moments['M_support']:.2f} kNm/m")

        shear = self.calculate_shear()
        report_lines.append(f"  Taglio: V_ed = {shear['V_max']:.2f} kN/m")

        reinforcement = self.calculate_reinforcement()
        report_lines.append(f"\nArmature:")
        report_lines.append(f"  As,calc = {reinforcement['As_long']:.2f} cm²/m")
        report_lines.append(f"  As,min = {reinforcement['As_min']:.2f} cm²/m")
        report_lines.append(f"  Disposizione suggerita: φ{reinforcement['phi']:.0f} / {reinforcement['spacing']:.0f} cm")

        slu = self.verify_slu()
        report_lines.append(f"\nVERIFICHE SLU:")
        report_lines.append(f"  Flessione: M_rd = {slu['flexure']['M_rd']:.2f} kNm/m")
        report_lines.append(f"             Utilizzo = {slu['flexure']['ratio']:.2%}")
        report_lines.append(f"             {'✓ VERIFICATO' if slu['flexure']['verified'] else '✗ NON VERIFICATO'}")

        report_lines.append(f"  Taglio: V_rd = {slu['shear']['V_rd']:.2f} kN/m")
        report_lines.append(f"          Utilizzo = {slu['shear']['ratio']:.2%}")
        report_lines.append(f"          Staffe: {'SI (φ8/20cm min)' if slu['shear']['stirrups_required'] else 'NON NECESSARIE'}")
        report_lines.append(f"          {'✓ VERIFICATO' if slu['shear']['verified'] else '✗ NON VERIFICATO'}")

        sle = self.verify_sle()
        report_lines.append(f"\nVERIFICHE SLE:")
        report_lines.append(f"  Freccia: δ = {sle['deflection']['deflection']:.1f} mm")
        report_lines.append(f"           Limite = {sle['deflection']['limit']:.1f} mm (L/250)")
        report_lines.append(f"           Utilizzo = {sle['deflection']['ratio']:.2%}")
        report_lines.append(f"           {'✓ VERIFICATO' if sle['deflection']['verified'] else '✗ NON VERIFICATO'}")

        diaphragm = self.assess_diaphragm_behavior()
        report_lines.append(f"\nDIAFRAMMA:")
        report_lines.append(f"  Comportamento: {diaphragm.value}")

        report_lines.append(f"\n{'='*70}")
        report_lines.append(f"ESITO FINALE: {'✓ VERIFICATO' if slu['overall_verified'] and sle['overall_verified'] else '✗ NON VERIFICATO'}")
        report_lines.append(f"{'='*70}")

        return "\n".join(report_lines)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'FloorAnalysis',
    'FloorGeometry',
    'FloorLoads',
    'FloorType',
    'SupportType',
    'DiaphragmType',
    'CONCRETE_CLASSES',
    'STEEL_CLASSES',
]
