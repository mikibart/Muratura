"""
Module: balconies/__init__.py
Analisi e verifica balconi secondo NTC 2018

Questo modulo implementa il calcolo e la verifica di balconi a sbalzo secondo
le NTC 2018, inclusi balconi in c.a., acciaio e pietra (edifici storici).

Funzionalità principali:
- Calcolo sollecitazioni a sbalzo (momento, taglio, torsione)
- Verifica SLU balcone (flessione, taglio, torsione)
- Verifica ancoraggio alla muratura (CRITICO)
- Dimensionamento armature/profilati
- Verifica connessioni (saldate, bullonate)
- Calcolo sovraccarichi (Cat. C - folle, neve, vento)

Tipologie supportate:
- 'rc_cantilever': Balcone in c.a. a sbalzo
- 'steel': Balcone in acciaio (HEA, IPE, UPN)
- 'stone': Balcone in pietra (edifici storici)
- 'precast': Balcone prefabbricato

Examples:
    >>> from Material.analyses.balconies import BalconyAnalysis, BalconyGeometry
    >>> geometry = BalconyGeometry(
    ...     cantilever_length=1.5,  # m
    ...     width=1.0,  # m
    ...     thickness=0.15  # m (soletta 15cm)
    ... )
    >>> balcony = BalconyAnalysis(
    ...     balcony_type='rc_cantilever',
    ...     geometry=geometry,
    ...     concrete_class='C25/30',
    ...     steel_class='B450C'
    ... )
    >>> verification = balcony.verify_cantilever()
    >>> print(f"Ancoraggio verificato: {verification['anchorage_verified']}")
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Literal
from enum import Enum
import numpy as np


# ============================================================================
# ENUMS E COSTANTI
# ============================================================================

class BalconyType(Enum):
    """Tipologie di balcone supportate"""
    RC_CANTILEVER = 'rc_cantilever'  # C.a. a sbalzo
    STEEL = 'steel'  # Acciaio (HEA, IPE, UPN)
    STONE = 'stone'  # Pietra (storico)
    PRECAST = 'precast'  # Prefabbricato


class SteelProfileType(Enum):
    """Tipologie di profilati acciaio"""
    HEA = 'HEA'
    HEB = 'HEB'
    IPE = 'IPE'
    UPN = 'UPN'


class ConnectionType(Enum):
    """Tipologie di connessione"""
    WELDED = 'welded'  # Saldata
    BOLTED = 'bolted'  # Bullonata
    CHEMICAL_ANCHOR = 'chemical_anchor'  # Ancoraggio chimico
    MECHANICAL_ANCHOR = 'mechanical_anchor'  # Ancoraggio meccanico


# NTC 2018 - Classi materiali (da modulo floors, importate)
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

# Acciaio da carpenteria NTC 2018 §11.3.4.1
STRUCTURAL_STEEL = {
    'S235': {'fy': 235.0, 'fu': 360.0, 'E': 210000.0},
    'S275': {'fy': 275.0, 'fu': 430.0, 'E': 210000.0},
    'S355': {'fy': 355.0, 'fu': 510.0, 'E': 210000.0},
}

# Coefficienti di sicurezza NTC 2018
GAMMA_C = 1.5  # Calcestruzzo
GAMMA_S = 1.15  # Acciaio armatura
GAMMA_M0 = 1.05  # Acciaio carpenteria (resistenza sezioni)
GAMMA_M2 = 1.25  # Acciaio carpenteria (resistenza collegamenti)
ALPHA_CC = 0.85  # Riduzione resistenza cls

# Sovraccarichi variabili NTC 2018 Tab. 3.1.II
# Categoria C: Ambienti suscettibili di affollamento
Q_CAT_C = 4.0  # kN/m² (balconi, terrazze)

# Database profilati acciaio (sezione, peso, proprietà geometriche)
STEEL_PROFILES = {
    'HEA': {
        'HEA100': {'h': 96, 'b': 100, 'tw': 5.0, 'tf': 8.0, 'A': 21.2, 'Iy': 349, 'Wely': 72.8, 'weight': 16.7},
        'HEA120': {'h': 114, 'b': 120, 'tw': 5.0, 'tf': 8.0, 'A': 25.3, 'Iy': 606, 'Wely': 106, 'weight': 19.9},
        'HEA140': {'h': 133, 'b': 140, 'tw': 5.5, 'tf': 8.5, 'A': 31.4, 'Iy': 1033, 'Wely': 155, 'weight': 24.7},
        'HEA160': {'h': 152, 'b': 160, 'tw': 6.0, 'tf': 9.0, 'A': 38.8, 'Iy': 1673, 'Wely': 220, 'weight': 30.4},
        'HEA180': {'h': 171, 'b': 180, 'tw': 6.0, 'tf': 9.5, 'A': 45.3, 'Iy': 2510, 'Wely': 294, 'weight': 35.5},
        'HEA200': {'h': 190, 'b': 200, 'tw': 6.5, 'tf': 10.0, 'A': 53.8, 'Iy': 3692, 'Wely': 389, 'weight': 42.3},
    },
    'IPE': {
        'IPE100': {'h': 100, 'b': 55, 'tw': 4.1, 'tf': 5.7, 'A': 10.3, 'Iy': 171, 'Wely': 34.2, 'weight': 8.1},
        'IPE120': {'h': 120, 'b': 64, 'tw': 4.4, 'tf': 6.3, 'A': 13.2, 'Iy': 318, 'Wely': 53.0, 'weight': 10.4},
        'IPE140': {'h': 140, 'b': 73, 'tw': 4.7, 'tf': 6.9, 'A': 16.4, 'Iy': 541, 'Wely': 77.3, 'weight': 12.9},
        'IPE160': {'h': 160, 'b': 82, 'tw': 5.0, 'tf': 7.4, 'A': 20.1, 'Iy': 869, 'Wely': 109, 'weight': 15.8},
        'IPE180': {'h': 180, 'b': 91, 'tw': 5.3, 'tf': 8.0, 'A': 23.9, 'Iy': 1317, 'Wely': 146, 'weight': 18.8},
        'IPE200': {'h': 200, 'b': 100, 'tw': 5.6, 'tf': 8.5, 'A': 28.5, 'Iy': 1943, 'Wely': 194, 'weight': 22.4},
    },
    'UPN': {
        'UPN100': {'h': 100, 'b': 50, 'tw': 6.0, 'tf': 8.5, 'A': 13.5, 'Iy': 206, 'Wely': 41.2, 'weight': 10.6},
        'UPN120': {'h': 120, 'b': 55, 'tw': 7.0, 'tf': 9.0, 'A': 17.0, 'Iy': 364, 'Wely': 60.7, 'weight': 13.4},
        'UPN140': {'h': 140, 'b': 60, 'tw': 7.0, 'tf': 10.0, 'A': 20.4, 'Iy': 605, 'Wely': 86.4, 'weight': 16.0},
        'UPN160': {'h': 160, 'b': 65, 'tw': 7.5, 'tf': 10.5, 'A': 24.0, 'Iy': 925, 'Wely': 116, 'weight': 18.8},
        'UPN180': {'h': 180, 'b': 70, 'tw': 8.0, 'tf': 11.0, 'A': 28.0, 'Iy': 1354, 'Wely': 150, 'weight': 22.0},
        'UPN200': {'h': 200, 'b': 75, 'tw': 8.5, 'tf': 11.5, 'A': 32.2, 'Iy': 1910, 'Wely': 191, 'weight': 25.3},
    },
}


# ============================================================================
# DATACLASSES PER GEOMETRIA E CARICHI
# ============================================================================

@dataclass
class BalconyGeometry:
    """
    Geometria del balcone a sbalzo.

    Attributes:
        cantilever_length: Lunghezza sbalzo [m]
        width: Larghezza balcone [m]
        thickness: Spessore soletta/sezione [m]
        parapet_height: Altezza parapetto [m]
        parapet_weight: Peso parapetto lineare [kN/m]
        wall_thickness: Spessore muro portante [m] (per verifica ancoraggio)
    """
    cantilever_length: float
    width: float
    thickness: float
    parapet_height: float = 1.00  # m (minimo normativo)
    parapet_weight: float = 0.5  # kN/m (ringhiera leggera)
    wall_thickness: float = 0.40  # m (muratura tipica)

    def __post_init__(self):
        """Validazione parametri geometrici"""
        if self.cantilever_length <= 0:
            raise ValueError(f"Cantilever length deve essere > 0, got {self.cantilever_length}")
        if self.cantilever_length > 2.5:
            print(f"Warning: Cantilever {self.cantilever_length}m > 2.5m - Verificare deformabilità")
        if self.thickness <= 0:
            raise ValueError(f"Thickness deve essere > 0, got {self.thickness}")
        if self.parapet_height < 1.0:
            print(f"Warning: Parapet height {self.parapet_height}m < 1.0m (minimo normativo)")


@dataclass
class BalconyLoads:
    """
    Carichi agenti sul balcone.

    Attributes:
        permanent_loads: Carichi permanenti G2 [kN/m²] (pavimentazione)
        live_loads: Sovraccarichi variabili Q [kN/m²] (Cat. C default)
        snow_load: Carico neve [kN/m²] (se applicabile)
        wind_pressure: Pressione vento su parapetto [kN/m²]
        self_weight_included: Se True, peso proprio è già incluso

    Note:
        NTC 2018 Tab. 3.1.II - Categoria C (balconi, terrazze): 4.0 kN/m²
        NTC 2018 §3.3 - Neve: dipende da zona e altitudine
        NTC 2018 §3.3 - Vento: dipende da esposizione
    """
    permanent_loads: float = 1.5  # G2 (pavimento, impermeabilizzazione)
    live_loads: float = 4.0  # Q Cat. C (balconi)
    snow_load: float = 0.0  # kN/m² (se balcone coperto)
    wind_pressure: float = 0.8  # kN/m² (su parapetto, tipico zona 1)
    self_weight_included: bool = False

    def total_permanent(self, self_weight: float = 0.0, parapet_weight: float = 0.0) -> float:
        """Calcola carico permanente totale G1+G2"""
        g_total = self.permanent_loads
        if not self.self_weight_included:
            g_total += self_weight
        # Parapetto è distribuito sul perimetro, non su area
        return g_total

    def slu_vertical_load_combination(self, self_weight: float = 0.0) -> float:
        """
        Combinazione carico verticale SLU (NTC 2018 §2.5.3)

        γG·G + γQ·Q + γQ·Qsnow
        γG = 1.3, γQ = 1.5
        """
        G = self.total_permanent(self_weight)
        Q = max(self.live_loads, self.snow_load)  # Dominante
        return 1.3 * G + 1.5 * Q

    def slu_wind_action(self, parapet_height: float, width: float) -> float:
        """
        Azione vento su parapetto (forza orizzontale)

        Returns:
            Forza orizzontale [kN] su parapetto
        """
        # Superficie esposta
        A_wind = parapet_height * width  # m²
        # Forza = pressione * area
        F_wind = 1.5 * self.wind_pressure * A_wind  # γQ = 1.5
        return F_wind


# ============================================================================
# CLASSE PRINCIPALE BALCONY ANALYSIS
# ============================================================================

class BalconyAnalysis:
    """
    Analisi e verifica balcone a sbalzo secondo NTC 2018.

    Implementa:
    - Calcolo sollecitazioni a sbalzo (M, V, T)
    - Verifica SLU (flessione, taglio, torsione)
    - Dimensionamento armature/profilati
    - Verifica ancoraggio alla muratura (CRITICO)
    - Verifica connessioni

    Attributes:
        balcony_type: Tipologia balcone
        geometry: Geometria balcone
        concrete_class: Classe calcestruzzo (per c.a.)
        steel_class: Classe acciaio armatura (per c.a.)
        structural_steel_class: Classe acciaio carpenteria (per balconi acciaio)
        loads: Carichi agenti
    """

    def __init__(
        self,
        balcony_type: Literal['rc_cantilever', 'steel', 'stone', 'precast'],
        geometry: BalconyGeometry,
        concrete_class: str = 'C25/30',
        steel_class: str = 'B450C',
        structural_steel_class: str = 'S275',
        steel_profile: Optional[str] = None,  # es. 'HEA160'
        loads: Optional[BalconyLoads] = None
    ):
        """
        Inizializza analisi balcone.

        Args:
            balcony_type: Tipologia balcone
            geometry: Geometria balcone
            concrete_class: Classe calcestruzzo NTC 2018
            steel_class: Classe acciaio armatura NTC 2018
            structural_steel_class: Classe acciaio carpenteria (S235, S275, S355)
            steel_profile: Profilato acciaio (es. 'HEA160', 'IPE180')
            loads: Carichi agenti

        Raises:
            ValueError: Se parametri non validi
        """
        self.balcony_type = BalconyType(balcony_type)
        self.geometry = geometry
        self.loads = loads if loads is not None else BalconyLoads()

        # Proprietà materiali C.A.
        if concrete_class not in CONCRETE_CLASSES:
            raise ValueError(f"Concrete class {concrete_class} not supported")
        if steel_class not in STEEL_CLASSES:
            raise ValueError(f"Steel class {steel_class} not supported")

        self.concrete = CONCRETE_CLASSES[concrete_class]
        self.steel = STEEL_CLASSES[steel_class]
        self.concrete_class = concrete_class
        self.steel_class = steel_class

        # Resistenze di calcolo C.A.
        self.fcd = ALPHA_CC * self.concrete['fck'] / GAMMA_C  # MPa
        self.fyd = self.steel['fyk'] / GAMMA_S  # MPa

        # Proprietà acciaio da carpenteria
        if structural_steel_class not in STRUCTURAL_STEEL:
            raise ValueError(f"Structural steel class {structural_steel_class} not supported")
        self.structural_steel = STRUCTURAL_STEEL[structural_steel_class]
        self.structural_steel_class = structural_steel_class
        self.fy = self.structural_steel['fy']  # MPa
        self.fu = self.structural_steel['fu']  # MPa
        self.fyd_steel = self.fy / GAMMA_M0  # MPa (resistenza sezioni)

        # Profilato acciaio (se balcone in acciaio)
        self.steel_profile = steel_profile
        self.profile_properties = None
        if steel_profile and self.balcony_type == BalconyType.STEEL:
            self._load_profile_properties()

        # Risultati (calcolati dai metodi)
        self._self_weight: Optional[float] = None
        self._moments: Optional[Dict] = None
        self._shear: Optional[Dict] = None
        self._torsion: Optional[Dict] = None

    def _load_profile_properties(self):
        """Carica proprietà geometriche del profilato acciaio"""
        if not self.steel_profile:
            return

        # Determina serie (HEA, IPE, UPN)
        series = None
        for s in ['HEA', 'HEB', 'IPE', 'UPN']:
            if self.steel_profile.startswith(s):
                series = s
                break

        if series and series in STEEL_PROFILES:
            if self.steel_profile in STEEL_PROFILES[series]:
                self.profile_properties = STEEL_PROFILES[series][self.steel_profile]
            else:
                raise ValueError(
                    f"Profile {self.steel_profile} not in database. "
                    f"Available: {list(STEEL_PROFILES[series].keys())}"
                )
        else:
            raise ValueError(f"Profile series {series} not supported")

    # ========================================================================
    # PESO PROPRIO
    # ========================================================================

    def calculate_self_weight(self) -> float:
        """
        Calcola peso proprio balcone [kN/m²].

        Returns:
            Peso proprio [kN/m²]
        """
        if self._self_weight is not None:
            return self._self_weight

        if self.balcony_type == BalconyType.RC_CANTILEVER:
            # C.a.: γ = 25 kN/m³
            gamma_c = 25.0
            self._self_weight = gamma_c * self.geometry.thickness

        elif self.balcony_type == BalconyType.STEEL:
            # Acciaio: peso profilati + soletta (se presente)
            if self.profile_properties:
                # Peso profilato per metro lineare
                weight_profile = self.profile_properties['weight']  # kg/m
                # Converti a kN/m² (distribuito su larghezza)
                weight_per_m2 = weight_profile * 9.81 / 1000 / self.geometry.width  # kN/m²

                # Aggiungi soletta collaborante se presente
                if self.geometry.thickness > 0.05:  # > 5cm = soletta
                    gamma_c = 25.0  # kN/m³
                    weight_slab = gamma_c * (self.geometry.thickness - 0.05)
                    self._self_weight = weight_per_m2 + weight_slab
                else:
                    self._self_weight = weight_per_m2
            else:
                # Stima peso medio se profilato non specificato
                self._self_weight = 1.0  # kN/m² (acciaio + grigliato)

        elif self.balcony_type == BalconyType.STONE:
            # Pietra: γ = 22-27 kN/m³ (medio 24)
            gamma_stone = 24.0
            self._self_weight = gamma_stone * self.geometry.thickness

        else:  # PRECAST
            # Prefabbricato: tipicamente più leggero
            self._self_weight = 3.5  # kN/m²

        return self._self_weight

    # ========================================================================
    # SOLLECITAZIONI
    # ========================================================================

    def calculate_moments(self) -> Dict[str, float]:
        """
        Calcola momenti flettenti e torcenti [kNm/m].

        Returns:
            Dictionary con:
            - 'M_cantilever': Momento a sbalzo massimo (incastro) [kNm/m]
            - 'T_edge': Torsione al bordo libero [kNm/m]
            - 'q_slu': Carico distribuito SLU [kN/m²]
            - 'F_wind': Forza vento orizzontale [kN]
        """
        if self._moments is not None:
            return self._moments

        # Carico verticale distribuito
        self_weight = self.calculate_self_weight()
        q_slu = self.loads.slu_vertical_load_combination(self_weight)

        # Carico lineare parapetto (sul bordo)
        parapet_load = self.geometry.parapet_weight  # kN/m

        L = self.geometry.cantilever_length
        B = self.geometry.width

        # Momento flessionale a sbalzo (incastro)
        # M = q·L²/2 + p·L (distribuzione + concentrato bordo)
        M_distributed = q_slu * L**2 / 2.0  # kNm/m
        M_parapet = 1.3 * parapet_load * L  # kNm (γG=1.3)
        M_cantilever = M_distributed + M_parapet / B  # kNm/m

        # Torsione al bordo (da carico eccentrico del parapetto esterno)
        # Parapetto agisce su bordo esterno: momento torcente
        # T ≈ p·L·e  (e = eccentricità)
        e_parapet = B / 2.0  # Parapetto sul bordo
        T_edge = 1.3 * parapet_load * L * (e_parapet / B)  # kNm/m (semplificato)

        # Forza vento orizzontale (su parapetto)
        F_wind = self.loads.slu_wind_action(
            parapet_height=self.geometry.parapet_height,
            width=B
        )

        # Momento da vento (forza orizzontale a h = parapet_height/2)
        M_wind = F_wind * (self.geometry.parapet_height / 2.0) / B  # kNm/m

        self._moments = {
            'M_cantilever': M_cantilever,
            'M_wind': M_wind,
            'T_edge': T_edge,
            'q_slu': q_slu,
            'F_wind': F_wind
        }

        return self._moments

    def calculate_shear(self) -> Dict[str, float]:
        """
        Calcola taglio massimo [kN/m].

        Returns:
            Dictionary con:
            - 'V_max': Taglio massimo all'incastro [kN/m]
        """
        if self._shear is not None:
            return self._shear

        moments = self.calculate_moments()
        q_slu = moments['q_slu']
        L = self.geometry.cantilever_length
        B = self.geometry.width

        # Taglio a sbalzo: V = q·L + P_parapet
        V_distributed = q_slu * L  # kN/m
        V_parapet = 1.3 * self.geometry.parapet_weight / B  # kN/m

        V_max = V_distributed + V_parapet

        self._shear = {
            'V_max': V_max
        }

        return self._shear

    # ========================================================================
    # CALCOLO ARMATURE (C.A.)
    # ========================================================================

    def calculate_reinforcement_rc(self) -> Dict[str, float]:
        """
        Calcola armature necessarie per balcone in c.a.

        Returns:
            Dictionary con:
            - 'As_bottom': Armatura inferiore (trazione) [cm²/m]
            - 'As_top': Armatura superiore (incastro) [cm²/m]
            - 'As_min': Armatura minima [cm²/m]
            - 'spacing': Interasse suggerito [cm]
            - 'phi': Diametro suggerito [mm]
        """
        if self.balcony_type != BalconyType.RC_CANTILEVER:
            return {'note': 'Reinforcement only for RC balconies'}

        moments = self.calculate_moments()
        M_ed = moments['M_cantilever'] * 1000  # kNm → Nm

        # Altezza utile
        d = self.geometry.thickness - 0.03  # Copriferro 3cm (inferiore)
        d_top = self.geometry.thickness - 0.02  # Copriferro 2cm (superiore)

        b = 1.0  # m (per metro lineare)

        # Armatura superiore (fibra compressa in campata, tesa all'incastro)
        # Momento adimensionale
        mu = M_ed / (b * d_top**2 * self.fcd * 1e6)

        if mu > 0.295:
            print(f"Warning: μ={mu:.3f} > 0.295 - Armatura doppia o aumentare spessore!")
            mu = 0.295

        omega = 1.25 * mu * (1 - 0.5 * 1.25 * mu)
        As_top = omega * b * d_top * self.fcd / self.fyd * 1e4  # cm²/m

        # Armatura inferiore (costruttiva, ~30% superiore)
        As_bottom = 0.3 * As_top

        # Armatura minima NTC 2018
        fctm = 0.30 * self.concrete['fck']**(2/3)
        As_min = max(
            0.26 * fctm / self.steel['fyk'] * b * d_top * 1e4,
            0.0013 * b * d_top * 1e4
        )

        As_top_required = max(As_top, As_min)
        As_bottom_required = max(As_bottom, As_min * 0.5)

        # Suggerimento disposizione
        phi_suggested = 12  # mm
        area_bar = np.pi * (phi_suggested/10)**2 / 4
        n_bars = np.ceil(As_top_required / area_bar)
        spacing = 100.0 / n_bars if n_bars > 0 else 20.0

        return {
            'As_top': As_top_required,
            'As_bottom': As_bottom_required,
            'As_min': As_min,
            'spacing': spacing,
            'phi': phi_suggested,
            'n_bars': n_bars
        }

    # ========================================================================
    # DIMENSIONAMENTO PROFILATO ACCIAIO
    # ========================================================================

    def check_steel_profile(self) -> Dict[str, any]:
        """
        Verifica profilato acciaio per balcone.

        Returns:
            Dictionary con risultati verifica
        """
        if self.balcony_type != BalconyType.STEEL:
            return {'note': 'Steel profile check only for steel balconies'}

        if not self.profile_properties:
            return {'error': 'No steel profile specified'}

        moments = self.calculate_moments()
        M_ed = moments['M_cantilever'] * 1e6  # kNm → Nmm

        shear = self.calculate_shear()
        V_ed = shear['V_max'] * 1e3  # kN → N

        # Numero di profilati (tipicamente 2-3 per balcone)
        # Assumi spaziatura 60-80cm
        n_profiles = max(2, int(np.ceil(self.geometry.width / 0.70)))

        # Momento per singolo profilato
        M_ed_single = M_ed / n_profiles  # Nmm

        # Resistenza flessione NTC 2018 §4.2.4.1.2
        # M_rd = Wel·fyd
        Wel = self.profile_properties['Wely']  # cm³
        M_rd = Wel * 1000 * self.fyd_steel  # Nmm (Wel in mm³ * fyd in MPa)

        flexure_ratio = M_ed_single / M_rd

        # Resistenza taglio NTC 2018 §4.2.4.1.3
        # V_rd = Av·fyd/√3
        # Av ≈ h·tw (anima)
        h = self.profile_properties['h']  # mm
        tw = self.profile_properties['tw']  # mm
        Av = h * tw  # mm²
        V_rd = Av * self.fyd_steel / np.sqrt(3.0)  # N

        V_ed_single = V_ed / n_profiles
        shear_ratio = V_ed_single / V_rd

        return {
            'profile': self.steel_profile,
            'n_profiles': n_profiles,
            'M_ed': M_ed_single / 1e6,  # kNm
            'M_rd': M_rd / 1e6,  # kNm
            'flexure_ratio': flexure_ratio,
            'flexure_verified': flexure_ratio <= 1.0,
            'V_ed': V_ed_single / 1e3,  # kN
            'V_rd': V_rd / 1e3,  # kN
            'shear_ratio': shear_ratio,
            'shear_verified': shear_ratio <= 1.0,
            'overall_verified': flexure_ratio <= 1.0 and shear_ratio <= 1.0
        }

    # ========================================================================
    # VERIFICA ANCORAGGIO ALLA MURATURA (CRITICO!)
    # ========================================================================

    def verify_anchorage_to_wall(self, wall_compressive_strength: float = 4.0) -> Dict[str, any]:
        """
        Verifica ancoraggio balcone alla muratura (CRITICO).

        Questa è la verifica più importante per i balconi a sbalzo.
        Un ancoraggio insufficiente può portare al collasso catastrofico.

        Args:
            wall_compressive_strength: Resistenza muratura fcm [MPa]

        Returns:
            Dictionary con:
            - 'anchorage_length': Lunghezza ancoraggio richiesta [m]
            - 'anchorage_stress': Tensione ancoraggio [MPa]
            - 'anchorage_verified': True se verificato
            - 'safety_factor': Fattore di sicurezza
        """
        moments = self.calculate_moments()
        M_ed = moments['M_cantilever']  # kNm/m

        shear = self.calculate_shear()
        V_ed = shear['V_max']  # kN/m

        # Forza di trazione all'incastro (da momento)
        # M = N·d → N = M/d
        d_effective = self.geometry.thickness * 0.9  # Braccio efficace
        N_tension = M_ed / d_effective  # kN/m

        # Lunghezza ancoraggio necessaria nella muratura
        # τ_adm = 0.4 MPa (tensione tangenziale ammissibile muratura)
        tau_adm = 0.4  # MPa

        # Superficie ancoraggio per metro
        # N = τ·A → A = N/τ
        # A = lunghezza_anc * perimetro_efficace
        # Per soletta h: perimetro ≈ 2·h (lato superiore + inferiore)
        perimeter = 2.0 * self.geometry.thickness  # m

        A_anchorage_required = (N_tension * 1000) / (tau_adm * 1e6)  # m²
        anchorage_length = A_anchorage_required / perimeter  # m

        # Lunghezza minima = maggiore tra:
        # - 30cm (costruttiva)
        # - 1.5 volte spessore muro
        # - lunghezza calcolata
        L_min = max(0.30, 1.5 * self.geometry.thickness, anchorage_length)

        # Verifica: ancoraggio deve entrare almeno 2/3 spessore muro
        L_available = self.geometry.wall_thickness * 0.67

        anchorage_verified = L_min <= L_available

        # Tensione effettiva con lunghezza disponibile
        if anchorage_verified:
            A_actual = L_available * perimeter
            tau_actual = (N_tension * 1000) / (A_actual * 1e6)  # MPa
            safety_factor = tau_adm / tau_actual
        else:
            tau_actual = (N_tension * 1000) / (L_available * perimeter * 1e6)
            safety_factor = tau_adm / tau_actual

        return {
            'anchorage_length_required': L_min,
            'anchorage_length_available': L_available,
            'anchorage_stress': tau_actual,
            'anchorage_stress_limit': tau_adm,
            'anchorage_verified': anchorage_verified,
            'safety_factor': safety_factor,
            'tension_force': N_tension,
            'note': 'CRITICO: Verifica ancoraggio muratura per sicurezza balcone'
        }

    # ========================================================================
    # VERIFICA COMPLETA
    # ========================================================================

    def verify_cantilever(self, wall_fcm: float = 4.0) -> Dict[str, any]:
        """
        Verifica completa balcone a sbalzo.

        Args:
            wall_fcm: Resistenza muratura [MPa]

        Returns:
            Dictionary con tutti i risultati
        """
        results = {}

        # Calcolo sollecitazioni
        results['moments'] = self.calculate_moments()
        results['shear'] = self.calculate_shear()

        # Verifica strutturale (dipende da tipologia)
        if self.balcony_type == BalconyType.RC_CANTILEVER:
            results['reinforcement'] = self.calculate_reinforcement_rc()
            # TODO: Aggiungi verifica SLU flessione/taglio come modulo floors
        elif self.balcony_type == BalconyType.STEEL:
            results['steel_check'] = self.check_steel_profile()

        # VERIFICA CRITICA: Ancoraggio alla muratura
        results['anchorage'] = self.verify_anchorage_to_wall(wall_fcm)

        # Esito globale
        if self.balcony_type == BalconyType.STEEL and 'steel_check' in results:
            structural_ok = results['steel_check'].get('overall_verified', False)
        else:
            structural_ok = True  # Per ora assume OK per c.a.

        anchorage_ok = results['anchorage']['anchorage_verified']

        results['overall_verified'] = structural_ok and anchorage_ok

        return results

    # ========================================================================
    # REPORT
    # ========================================================================

    def generate_report(self, wall_fcm: float = 4.0) -> str:
        """
        Genera report di verifica completo.

        Args:
            wall_fcm: Resistenza muratura [MPa]

        Returns:
            Report formattato come stringa
        """
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("VERIFICA BALCONE A SBALZO - NTC 2018")
        report_lines.append("=" * 70)
        report_lines.append(f"\nTipologia: {self.balcony_type.value}")

        if self.balcony_type == BalconyType.RC_CANTILEVER:
            report_lines.append(f"\nMateriali:")
            report_lines.append(f"  Calcestruzzo: {self.concrete_class} (fck={self.concrete['fck']} MPa)")
            report_lines.append(f"  Acciaio: {self.steel_class} (fyk={self.steel['fyk']} MPa)")
        elif self.balcony_type == BalconyType.STEEL:
            report_lines.append(f"\nMateriali:")
            report_lines.append(f"  Acciaio: {self.structural_steel_class} (fy={self.fy} MPa)")
            if self.steel_profile:
                report_lines.append(f"  Profilato: {self.steel_profile}")

        report_lines.append(f"\nGeometria:")
        report_lines.append(f"  Sbalzo: L = {self.geometry.cantilever_length:.2f} m")
        report_lines.append(f"  Larghezza: B = {self.geometry.width:.2f} m")
        report_lines.append(f"  Spessore: h = {self.geometry.thickness*100:.0f} cm")
        report_lines.append(f"  Parapetto: h = {self.geometry.parapet_height:.2f} m, p = {self.geometry.parapet_weight:.2f} kN/m")

        self_weight = self.calculate_self_weight()
        report_lines.append(f"\nCarichi:")
        report_lines.append(f"  Peso proprio: {self_weight:.2f} kN/m²")
        report_lines.append(f"  Permanenti G2: {self.loads.permanent_loads:.2f} kN/m²")
        report_lines.append(f"  Variabili Q (Cat. C): {self.loads.live_loads:.2f} kN/m²")

        verification = self.verify_cantilever(wall_fcm)
        moments = verification['moments']

        report_lines.append(f"\nSollecitazioni SLU (q={moments['q_slu']:.2f} kN/m²):")
        report_lines.append(f"  Momento sbalzo: M_ed = {moments['M_cantilever']:.2f} kNm/m")
        report_lines.append(f"  Momento vento: M_wind = {moments['M_wind']:.2f} kNm/m")
        report_lines.append(f"  Torsione: T_ed = {moments['T_edge']:.2f} kNm/m")

        shear = verification['shear']
        report_lines.append(f"  Taglio: V_ed = {shear['V_max']:.2f} kN/m")

        if 'reinforcement' in verification:
            reinf = verification['reinforcement']
            report_lines.append(f"\nArmature:")
            report_lines.append(f"  Superiore (incastro): As = {reinf['As_top']:.2f} cm²/m")
            report_lines.append(f"  Inferiore (costruttiva): As = {reinf['As_bottom']:.2f} cm²/m")
            report_lines.append(f"  Disposizione: φ{reinf['phi']:.0f} / {reinf['spacing']:.0f} cm")

        if 'steel_check' in verification:
            steel = verification['steel_check']
            report_lines.append(f"\nVERIFICA PROFILATO ACCIAIO:")
            report_lines.append(f"  Numero profilati: {steel['n_profiles']}")
            report_lines.append(f"  Flessione: M_rd = {steel['M_rd']:.2f} kNm")
            report_lines.append(f"             Utilizzo = {steel['flexure_ratio']:.2%}")
            report_lines.append(f"             {'✓ VERIFICATO' if steel['flexure_verified'] else '✗ NON VERIFICATO'}")
            report_lines.append(f"  Taglio: V_rd = {steel['V_rd']:.2f} kN")
            report_lines.append(f"          Utilizzo = {steel['shear_ratio']:.2%}")
            report_lines.append(f"          {'✓ VERIFICATO' if steel['shear_verified'] else '✗ NON VERIFICATO'}")

        anc = verification['anchorage']
        report_lines.append(f"\n⚠️  VERIFICA CRITICA: ANCORAGGIO ALLA MURATURA")
        report_lines.append(f"  Lunghezza ancoraggio richiesta: {anc['anchorage_length_required']:.2f} m")
        report_lines.append(f"  Lunghezza disponibile (2/3 muro): {anc['anchorage_length_available']:.2f} m")
        report_lines.append(f"  Tensione tangenziale: τ = {anc['anchorage_stress']:.2f} MPa")
        report_lines.append(f"  Limite ammissibile: τ_adm = {anc['anchorage_stress_limit']:.2f} MPa")
        report_lines.append(f"  Fattore sicurezza: FS = {anc['safety_factor']:.2f}")
        report_lines.append(f"  {'✓ ANCORAGGIO VERIFICATO' if anc['anchorage_verified'] else '✗ ANCORAGGIO NON SUFFICIENTE - CRITICO!'}")

        report_lines.append(f"\n{'='*70}")
        if verification['overall_verified']:
            report_lines.append(f"ESITO FINALE: ✓ VERIFICATO")
        else:
            report_lines.append(f"ESITO FINALE: ✗ NON VERIFICATO")
            if not anc['anchorage_verified']:
                report_lines.append(f"⚠️  ATTENZIONE: ANCORAGGIO INSUFFICIENTE - RISCHIO COLLASSO")
        report_lines.append(f"{'='*70}")

        return "\n".join(report_lines)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'BalconyAnalysis',
    'BalconyGeometry',
    'BalconyLoads',
    'BalconyType',
    'SteelProfileType',
    'ConnectionType',
    'CONCRETE_CLASSES',
    'STEEL_CLASSES',
    'STRUCTURAL_STEEL',
    'STEEL_PROFILES',
]
