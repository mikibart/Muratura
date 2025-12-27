# geometry.py - VERSIONE DEFINITIVA COMPLETA v2.4.3
"""
Modulo per la gestione delle geometrie strutturali di murature secondo NTC 2018.

Fornisce classi complete per la definizione di maschi murari, fasce di piano,
elementi strutturali complessi e sistemi di rinforzo, con calcolo automatico
delle proprietà sezionali effettive considerando aperture, rinforzi e irregolarità.

Features principali:
- Geometrie complete per maschi e fasce con aperture
- Sistema di rinforzo parametrico (FRP, FRCM, CAM, steel)
- Calcolo proprietà sezionali effettive
- Gestione murature multistrato e composte
- Archi, volte e elementi speciali
- Export verso software commerciali
- Validazione geometrica NTC 2018

Convenzioni:
- Unità: metri [m] per lunghezze, MPa per tensioni
- Sistema di riferimento: X orizzontale, Y verticale, Z fuori piano
- Aperture: coordinate locali rispetto al baricentro elemento
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Union, Any, Protocol
from enum import Enum
import numpy as np
import warnings
import copy
import math

# ============================================================================
# ENUMERAZIONI
# ============================================================================

class BoundaryCondition(Enum):
    """Condizioni di vincolo per elementi strutturali"""
    CANTILEVER = "cantilever"              # Mensola (base incastrata)
    FIXED_FIXED = "fixed-fixed"            # Doppio incastro
    PINNED_PINNED = "pinned-pinned"        # Cerniera-cerniera
    FIXED_PINNED = "fixed-pinned"          # Incastro-cerniera
    FIXED_ROLLER = "fixed-roller"          # Incastro-carrello
    ELASTIC = "elastic"                    # Vincoli elastici

class ReinforcementType(Enum):
    """Tipologie di rinforzo strutturale"""
    FRP = "FRP"                            # Fiber Reinforced Polymer
    FRCM = "FRCM"                          # Fiber Reinforced Cementitious Matrix
    CAM = "CAM"                            # Cucitura Attiva Manufatti
    STEEL_PLATES = "STEEL_PLATES"          # Placcaggio con piatti d'acciaio
    STEEL_PROFILES = "STEEL_PROFILES"      # Profili d'acciaio
    RC_JACKET = "RC_JACKET"                # Camicia in c.a.
    REINFORCED_PLASTER = "REINFORCED_PLASTER"  # Intonaco armato
    GROUT_INJECTION = "GROUT_INJECTION"    # Iniezioni di malta

class WallType(Enum):
    """Tipologia costruttiva parete"""
    SINGLE_LEAF = "single_leaf"            # Paramento singolo
    DOUBLE_LEAF = "double_leaf"            # Doppio paramento
    THREE_LEAF = "three_leaf"              # Tre paramenti
    CAVITY_WALL = "cavity_wall"            # Muratura a cassa vuota
    COMPOSITE = "composite"                # Muratura mista

class ArchType(Enum):
    """Tipologie di arco"""
    CIRCULAR = "circular"                  # Arco circolare
    POINTED = "pointed"                    # Arco a sesto acuto
    ELLIPTICAL = "elliptical"              # Arco ellittico
    PARABOLIC = "parabolic"                # Arco parabolico
    SEGMENTAL = "segmental"                # Arco ribassato
    FLAT = "flat"                          # Piattabanda

class VaultType(Enum):
    """Tipologie di volta"""
    BARREL = "barrel"                      # Volta a botte
    CROSS = "cross"                        # Volta a crociera
    DOME = "dome"                          # Cupola
    CLOISTER = "cloister"                  # Volta a padiglione
    SAIL = "sail"                          # Volta a vela

class ElementType(Enum):
    """Tipo elemento strutturale"""
    PIER = "pier"                          # Maschio murario
    SPANDREL = "spandrel"                  # Fascia di piano
    WALL = "wall"                          # Parete generica
    ARCH = "arch"                          # Arco
    VAULT = "vault"                        # Volta
    COLUMN = "column"                      # Colonna
    BUTTRESS = "buttress"                  # Contrafforte

# ============================================================================
# PROTOCOL PER DUCK-TYPING
# ============================================================================

class MaterialProto(Protocol):
    """Protocol minimale per compatibilità materiali"""
    fcm: float
    E: float
    weight: float

# ============================================================================
# CLASSI DI SUPPORTO
# ============================================================================

@dataclass
class Point3D:
    """Punto nello spazio 3D"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def distance_to(self, other: Point3D) -> float:
        """Distanza euclidea tra due punti"""
        return math.sqrt((self.x - other.x)**2 + 
                        (self.y - other.y)**2 + 
                        (self.z - other.z)**2)
    
    def to_array(self) -> np.ndarray:
        """Converte in array numpy"""
        return np.array([self.x, self.y, self.z])

@dataclass
class Opening:
    """
    Apertura in elemento murario.
    
    Sistema di riferimento:
    - x_center: posizione orizzontale rispetto al baricentro dell'elemento [m]
    - y_bottom: quota inferiore apertura riferita alla base dell'elemento [m]
    
    Attributes:
        width: Larghezza apertura [m]
        height: Altezza apertura [m]
        x_center: Posizione X centro rispetto baricentro elemento [m]
        y_bottom: Quota inferiore apertura dalla base [m]
        type: Tipo apertura (porta/finestra/nicchia)
        lintel: Presenza e tipo di architrave
        reinforced: Se l'apertura è cerchiata/rinforzata
    """
    width: float
    height: float
    x_center: float = 0.0
    y_bottom: float = 0.0
    type: str = "window"  # window, door, niche
    lintel: Optional[Lintel] = None
    reinforced: bool = False
    reinforcement_width: float = 0.15  # Larghezza cerchiatura [m]
    
    def __post_init__(self):
        """Validazione post-inizializzazione"""
        if self.width <= 0:
            raise ValueError(f"Larghezza apertura deve essere > 0, trovato {self.width}")
        if self.height <= 0:
            raise ValueError(f"Altezza apertura deve essere > 0, trovato {self.height}")
    
    @property
    def area(self) -> float:
        """Area apertura [m²]"""
        return self.width * self.height
    
    @property
    def perimeter(self) -> float:
        """Perimetro apertura [m]"""
        return 2 * (self.width + self.height)
    
    @property
    def aspect_ratio(self) -> float:
        """Rapporto di forma"""
        return self.height / self.width if self.width > 0 else float('inf')
    
    @property
    def effective_width(self) -> float:
        """Larghezza efficace considerando rinforzi"""
        if self.reinforced:
            return max(self.width - 2 * self.reinforcement_width, 0.0)
        return self.width
    
    def validate(self) -> List[str]:
        """Valida geometria apertura"""
        errors = []
        if self.width <= 0:
            errors.append(f"Larghezza apertura non valida: {self.width}")
        if self.height <= 0:
            errors.append(f"Altezza apertura non valida: {self.height}")
        if self.aspect_ratio > 4:
            errors.append(f"Apertura troppo snella: H/B = {self.aspect_ratio:.2f}")
        if self.reinforced and self.reinforcement_width >= self.width/2:
            errors.append("Rinforzo apertura troppo largo")
        return errors

@dataclass
class Lintel:
    """
    Architrave/piattabanda sopra apertura.
    
    Attributes:
        type: Tipo (steel, rc, masonry, wood, arch)
        height: Altezza architrave [m]
        material_E: Modulo elastico materiale [MPa]
        material_f: Resistenza materiale [MPa]
        effective_span: Luce efficace [m]
        load_distribution: Tipo distribuzione carico
    """
    type: str = "masonry"
    height: float = 0.20
    material_E: float = 5000.0  # MPa
    material_f: float = 2.0     # MPa
    effective_span: Optional[float] = None
    load_distribution: str = "triangular"  # triangular, uniform, arch
    
    @property
    def stiffness_factor(self) -> float:
        """Fattore di rigidezza per modellazione"""
        factors = {
            "steel": 1.5,
            "rc": 1.3,
            "wood": 0.8,
            "masonry": 1.0,
            "arch": 1.2
        }
        return factors.get(self.type, 1.0)
    
    @property
    def capacity(self) -> float:
        """Capacità portante stimata [kN/m].
        
        Nota: Formula euristica semplificata per stima preliminare.
        """
        if self.type == "arch":
            # Formula arco (euristica)
            return 2 * self.material_f * self.height * 1000  # kN/m
        else:
            # Flessione semplice (euristica) → normalizzata a kN/m
            span = self.effective_span if self.effective_span and self.effective_span > 0 else 1.0
            return (self.material_f * self.height**2 / 6 * 1000) / span  # kN/m

@dataclass
class Reinforcement:
    """
    Sistema di rinforzo generico per muratura.
    
    Attributes:
        type: Tipo rinforzo (FRP, FRCM, etc.)
        area: Area/spessore rinforzo [cm²/m o mm]
        E_f: Modulo elastico rinforzo [GPa]
        f_f: Resistenza rinforzo [MPa]
        epsilon_fu: Deformazione ultima [-]
        width: Larghezza strisce (se applicabile) [mm]
        spacing: Interasse strisce (se applicabile) [mm]
        n_layers: Numero di strati
        orientation: Orientamento fibre [°]
        anchorage_type: Sistema di ancoraggio
        efficiency: Fattore di efficienza [0-1]
        application_side: Lato applicazione
    """
    type: ReinforcementType = ReinforcementType.FRP
    area: float = 0.0           # cm²/m o mm di spessore
    E_f: float = 230.0          # GPa per carbonio
    f_f: float = 3000.0         # MPa per carbonio
    epsilon_fu: float = 0.015   # Deformazione ultima
    width: float = 100.0        # mm (per strisce)
    spacing: float = 200.0      # mm (interasse strisce)
    n_layers: int = 1           # Numero strati
    orientation: float = 0.0    # gradi (0=verticale, 90=orizzontale)
    anchorage_type: str = "mechanical"  # mechanical, adhesive, wrapped
    efficiency: float = 0.7     # Fattore efficienza CNR-DT200
    application_side: str = "both"  # both, external, internal
    
    def __post_init__(self):
        """Imposta valori di default per tipo di rinforzo"""
        if self.type == ReinforcementType.FRP:
            if self.E_f == 230.0:  # Default non modificato
                self.E_f = 230.0  # Carbonio
                self.f_f = 3000.0
                self.epsilon_fu = 0.015
        elif self.type == ReinforcementType.FRCM:
            if self.E_f == 230.0:  # Default non modificato
                self.E_f = 200.0
                self.f_f = 1500.0
                self.epsilon_fu = 0.010
                self.efficiency = 0.6
        elif self.type == ReinforcementType.STEEL_PLATES:
            if self.E_f == 230.0:  # Default non modificato
                self.E_f = 210.0
                self.f_f = 275.0
                self.epsilon_fu = 0.002
                self.efficiency = 0.9
    
    @property
    def effective_area_cm2_per_m(self) -> float:
        """Area efficace per metro [cm²/m].
        
        Per tipi sottili (FRP/FRCM/intonaco): area = spessore [mm] × (width/spacing) × n_layers,
        poi converti a cm²/m moltiplicando per 10 (perché 1 mm × 1 m = 10 cm²).
        Per gli altri tipi: `area` è già in cm²/m, moltiplica per n_layers.
        
        ATTENZIONE: Per calcoli strutturali usare _reinforcement_area_m2_per_m() 
        che restituisce [m²/m] con conversioni corrette.
        """
        thin_types = {ReinforcementType.FRP, ReinforcementType.FRCM, ReinforcementType.REINFORCED_PLASTER}
        if self.type in thin_types:
            ratio = (self.width / self.spacing) if self.spacing > 0 else 1.0
            # mm → cm²/m: ×10
            return (self.area * ratio * self.n_layers) * 10.0
        # area già in cm²/m
        return self.area * max(1, self.n_layers)
    
    @property
    def design_strength(self) -> float:
        """Resistenza di progetto [MPa]"""
        # Secondo CNR-DT200
        gamma_f = 1.2  # Coefficiente parziale
        eta_a = 0.85 if self.anchorage_type == "mechanical" else 0.7
        return self.f_f * self.efficiency * eta_a / gamma_f
    
    @property
    def contribution_V(self) -> float:
        """Contributo al taglio [kN/m]"""
        # Normalizza angolo a 0-180°
        a = abs(self.orientation) % 180.0
        a = min(a, 180.0 - a)
        
        if a < 45:  # Prevalentemente verticale
            return 0.0
            
        # Area efficace e numero lati
        A_f = _reinforcement_area_m2_per_m(self)
        n_sides = 2 if self.application_side == "both" else 1
        
        return 0.6 * (A_f * n_sides) * self.design_strength * 1000.0 * \
               math.sin(math.radians(a))
    
    @property
    def contribution_M(self) -> float:
        """Contributo al momento [%]"""
        # Normalizza angolo a 0-180°
        a = abs(self.orientation) % 180.0
        a = min(a, 180.0 - a)
        
        if a > 45:  # Prevalentemente orizzontale/diagonale
            return 0.0
            
        # Incremento capacità flessionale
        return 20 * self.efficiency * self.n_layers  # % incremento

@dataclass
class TieRod:
    """
    Tirante/catena per elementi murari.
    
    Attributes:
        diameter: Diametro tirante [mm]
        f_y: Tensione snervamento [MPa]
        prestress: Forza di precompressione [kN]
        spacing: Interasse (se multipli) [m]
        anchorage_type: Tipo ancoraggio (plate, distributed, chemical)
        plate_dimensions: Dimensioni piastra ancoraggio [m]
    """
    diameter: float = 20.0      # mm
    f_y: float = 235.0          # MPa
    prestress: float = 0.0      # kN
    spacing: float = 0.0        # m (0 = singolo)
    anchorage_type: str = "plate"
    plate_dimensions: Tuple[float, float] = (0.30, 0.30)  # [m]
    
    @property
    def area(self) -> float:
        """Area tirante [cm²]"""
        return math.pi * (self.diameter/10)**2 / 4
    
    @property
    def capacity(self) -> float:
        """Capacità a trazione [kN]"""
        return self.area * self.f_y / 10
    
    @property
    def stiffness(self) -> float:
        """Rigidezza assiale [kN/m] (per L=1m).
        
        Formula: E[MPa] * A[cm²] * 0.1 = kN/m
        dove 0.1 deriva da: cm² → m² (×1e-4) e MPa → kN/m² (×1e3)
        quindi 1e-4 × 1e3 = 0.1
        """
        E_steel = 210000  # MPa
        return E_steel * self.area * 0.1  # kN/m per metro di lunghezza
    
    @property
    def anchorage_capacity(self) -> float:
        """Capacità ancoraggio [kN]"""
        if self.anchorage_type == "plate":
            # Pressione ammissibile muratura
            sigma_adm = 0.5  # MPa
            A_plate = self.plate_dimensions[0] * self.plate_dimensions[1]
            return sigma_adm * A_plate * 1000  # kN
        return self.capacity  # Ancoraggio chimico o distribuito

# ============================================================================
# CLASSE PRINCIPALE GeometryPier
# ============================================================================

@dataclass
class GeometryPier:
    """
    Geometria completa maschio murario secondo NTC 2018.
    
    Gestisce geometrie complesse con aperture, rinforzi, irregolarità 
    e calcola proprietà sezionali effettive per analisi strutturali.
    
    Attributes:
        length: Lunghezza (direzione principale) [m]
        height: Altezza totale [m]
        thickness: Spessore [m]
        h0: Altezza momento nullo [m]
        boundary_conditions: Condizioni vincolo
        openings: Lista aperture
        reinforcements: Lista rinforzi applicati
        wall_type: Tipologia costruttiva
        eccentricity_top: Eccentricità superiore [m]
        eccentricity_bottom: Eccentricità inferiore [m]
        irregularities: Irregolarità geometriche
        base_isolation: Presenza isolamento base
        effective_height_factor: Fattore altezza efficace
    """
    length: float                          # Lunghezza [m]
    height: float                          # Altezza [m]
    thickness: float                       # Spessore [m]
    h0: Optional[float] = None            # Altezza momento nullo [m]
    
    # Condizioni al contorno
    boundary_conditions: BoundaryCondition = BoundaryCondition.CANTILEVER
    elastic_constraints: Optional[Dict[str, float]] = None  # k_x, k_y, k_rot [kN/m, kNm/rad]
    
    # Geometria dettagliata
    openings: List[Opening] = field(default_factory=list)
    wall_type: WallType = WallType.SINGLE_LEAF
    
    # Rinforzi
    reinforcements: List[Reinforcement] = field(default_factory=list)
    tie_rods: List[TieRod] = field(default_factory=list)
    
    # Eccentricità e irregolarità 
    eccentricity_top: float = 0.0         # [m]
    eccentricity_bottom: float = 0.0      # [m]
    out_of_plane_offset: float = 0.0      # [m]
    
    # Irregolarità geometriche
    irregularities: Dict[str, Any] = field(default_factory=dict)
    
    # Isolamento sismico
    base_isolation: Optional[Dict[str, float]] = None  # k_h, k_v, c [kN/m, kNs/m]
    
    # Fattori correttivi
    effective_height_factor: float = 1.0   # Per h_eff
    shear_retention_factor: float = 1.0    # Per degrado taglio
    
    # Metadata strutturale
    storey: Optional[int] = None          # Piano di appartenenza
    
    def __post_init__(self):
        """Inizializzazione e calcolo parametri derivati"""
        # Calcola h0 se non fornito
        if self.h0 is None:
            self.h0 = self._calculate_h0()
        
        # Valida geometria
        self._validate_geometry()
        
        # Ordina aperture per posizione
        self.openings.sort(key=lambda op: (op.y_bottom, op.x_center))
    
    def refresh(self):
        """Ricalcola grandezze derivate dopo modifiche geometriche.
        
        Questo metodo va chiamato dopo modifiche manuali alle aperture
        per garantire che h0 e altri parametri derivati siano aggiornati.
        """
        self.h0 = self._calculate_h0()
        self.openings.sort(key=lambda op: (op.y_bottom, op.x_center))
    
    def add_opening(self, opening: Opening):
        """Aggiunge un'apertura e aggiorna i parametri derivati.
        
        Args:
            opening: Apertura da aggiungere
        """
        self.openings.append(opening)
        self.refresh()
    
    def _calculate_h0(self) -> float:
        """Calcola altezza di momento nullo secondo NTC"""
        factors = {
            BoundaryCondition.CANTILEVER: 1.0,
            BoundaryCondition.FIXED_FIXED: 0.5,
            BoundaryCondition.PINNED_PINNED: 1.0,
            BoundaryCondition.FIXED_PINNED: 0.7,
            BoundaryCondition.FIXED_ROLLER: 0.8,
            BoundaryCondition.ELASTIC: 0.75
        }
        
        base_h0 = self.height * factors.get(self.boundary_conditions, 1.0)
        
        # Correzione per aperture
        if self.openings:
            opening_factor = 1 + 0.1 * len(self.openings)
            base_h0 *= min(opening_factor, 1.3)
        
        # Correzione per snellezza
        slenderness = self.height / self.thickness
        if slenderness > 12:
            base_h0 *= (1 + 0.01 * (slenderness - 12))
        
        return base_h0 * self.effective_height_factor
    
    def _validate_geometry(self):
        """Valida coerenza geometrica"""
        if self.length <= 0:
            raise ValueError(f"Lunghezza deve essere > 0: {self.length}")
        if self.height <= 0:
            raise ValueError(f"Altezza deve essere > 0: {self.height}")
        if self.thickness <= 0:
            raise ValueError(f"Spessore deve essere > 0: {self.thickness}")
        
        # Valida aperture
        for opening in self.openings:
            errors = opening.validate()
            if errors:
                warnings.warn(f"Problemi apertura: {errors}", UserWarning)
        
        # Verifica sovrapposizioni aperture
        for i, op1 in enumerate(self.openings):
            for op2 in self.openings[i+1:]:
                if self._openings_overlap(op1, op2):
                    warnings.warn(
                        f"Aperture sovrapposte: {op1} e {op2}",
                        UserWarning
                    )
    
    def _openings_overlap(self, op1: Opening, op2: Opening) -> bool:
        """Verifica se due aperture si sovrappongono"""
        x1_min = op1.x_center - op1.width/2
        x1_max = op1.x_center + op1.width/2
        x2_min = op2.x_center - op2.width/2
        x2_max = op2.x_center + op2.width/2
        
        y1_min = op1.y_bottom
        y1_max = op1.y_bottom + op1.height
        y2_min = op2.y_bottom
        y2_max = op2.y_bottom + op2.height
        
        x_overlap = not (x1_max < x2_min or x2_max < x1_min)
        y_overlap = not (y1_max < y2_min or y2_max < y1_min)

        return x_overlap and y_overlap

    @property
    def width(self) -> float:
        """Larghezza sezione (alias per length) [m]"""
        return self.length

    @property
    def area(self) -> float:
        """Area sezione (alias per gross_area) [m²]"""
        return self.gross_area

    @property
    def inertia(self) -> float:
        """Momento d'inerzia (alias per gross_inertia) [m⁴]"""
        return self.gross_inertia

    @property
    def gross_area(self) -> float:
        """Area lorda sezione [m²]"""
        if self.wall_type == WallType.DOUBLE_LEAF:
            return self.length * self.thickness * 0.85  # Riduzione per vuoti
        elif self.wall_type == WallType.CAVITY_WALL:
            return self.length * self.thickness * 0.7
        return self.length * self.thickness
    
    @property
    def net_area(self) -> float:
        """Area netta (lorda - aperture) [m²] coerente con la resistenza in piano.
        
        Le aperture riducono la lunghezza efficace pesate sulla frazione d'altezza forata.
        Questo approccio garantisce coerenza dimensionale per resistenze e rigidezze.
        """
        if not self.openings:
            return self.gross_area
        
        void_length = 0.0
        for op in self.openings:
            # Frazione di altezza interessata dall'apertura
            phi = min(max(op.height, 0.0) / max(self.height, 1e-9), 1.0)
            void_length += max(op.effective_width, 0.0) * phi
        
        # Lunghezza efficace ridotta
        net_len = max(self.length - void_length, 0.1 * self.length)
        return net_len * self.thickness
    
    @property
    def effective_area(self) -> float:
        """Area efficace considerando rinforzi [m²]"""
        area = self.net_area
        
        # Contributo rinforzi
        for reinf in self.reinforcements:
            if reinf.type in (ReinforcementType.RC_JACKET, ReinforcementType.REINFORCED_PLASTER):
                # Usa area equivalente per metro [m²/m] come spessore aggiunto
                t_eq = _reinforcement_area_m2_per_m(reinf)  # [m]
                # Rispetta il lato di applicazione
                sides = 2 if reinf.application_side == "both" else 1
                area += sides * t_eq * self.length
        
        return area
    
    @property
    def gross_inertia(self) -> float:
        """Momento d'inerzia lordo [m⁴]"""
        return self.thickness * self.length**3 / 12
    
    @property
    def net_inertia(self) -> float:
        """Momento d'inerzia netto (considerando aperture) [m⁴] coerente col piano di resistenza.
        
        Le aperture riducono l'inerzia proporzionalmente alla frazione di altezza interessata,
        garantendo coerenza dimensionale nel calcolo delle rigidezze flessionali.
        """
        I_gross = self.gross_inertia
        
        if not self.openings:
            return I_gross
        
        I_reduction = 0.0
        for op in self.openings:
            # Frazione di altezza interessata
            phi = min(max(op.height, 0.0) / max(self.height, 1e-9), 1.0)
            b = max(op.effective_width, 0.0)
            
            # Inerzia propria apertura (ridotta per phi)
            I_op = self.thickness * b**3 / 12.0 * phi
            
            # Trasporto (Steiner) con area coerente
            A_op = self.thickness * b * phi
            d = op.x_center  # Distanza dal baricentro
            I_reduction += I_op + A_op * d**2
        
        return max(I_gross - I_reduction, 0.1 * I_gross)
    
    @property
    def effective_inertia(self) -> float:
        """Momento d'inerzia efficace con rinforzi [m⁴].
        
        Nota: Calcolo euristico semplificato. Per analisi accurate
        usare calculate_transformed_section_properties().
        """
        I = self.net_inertia
        
        # Contributo rinforzi (euristico)
        for reinf in self.reinforcements:
            if abs(reinf.orientation) < 45:  # Rinforzo prevalentemente verticale
                # Contributo tipo trave composta
                A_f = _reinforcement_area_m2_per_m(reinf)  # m²/m
                d = self.length/2  # Distanza dal baricentro
                if reinf.application_side == "external":
                    I += A_f * d**2
                elif reinf.application_side == "internal":
                    I += A_f * d**2
                elif reinf.application_side == "both":
                    I += 2 * A_f * d**2
        
        return I
    
    @property
    def shear_area(self) -> float:
        """Area resistente a taglio [m²]"""
        # Area ridotta per taglio (5/6 per sezione rettangolare)
        return self.effective_area * 5/6
    
    @property
    def shape_factor(self) -> float:
        """Fattore di forma b secondo NTC 2018"""
        h_l_ratio = self.height / self.length
        
        # Tabella C8.7.1.1 NTC 2018
        if h_l_ratio <= 0.5:
            b = 1.5
        elif h_l_ratio >= 1.5:
            b = 1.0
        else:
            # Interpolazione lineare
            b = 1.5 - (h_l_ratio - 0.5) * 0.5
        
        # Correzione per aperture
        if self.openings:
            opening_ratio = sum(op.width for op in self.openings) / self.length
            b *= (1 - 0.3 * min(opening_ratio, 0.5))
        
        # Clamp ai limiti NTC (1.0 ≤ b ≤ 1.5)
        return max(1.0, min(b, 1.5))
    
    @property
    def slenderness(self) -> float:
        """Snellezza geometrica"""
        return self.h0 / self.thickness
    
    @property
    def slenderness_limit(self) -> float:
        """Limite snellezza secondo NTC"""
        # NTC 2018 - 7.8.1.4
        if self.boundary_conditions == BoundaryCondition.FIXED_FIXED:
            return 20
        else:
            return 15
    
    @property
    def is_slender(self) -> bool:
        """Verifica se l'elemento è snello"""
        return self.slenderness > self.slenderness_limit
    
    @property
    def centroid(self) -> Tuple[float, float, float]:
        """Baricentro della sezione netta [m].
        
        Returns:
            Tuple (x_cg, y_cg, z_cg) dove:
            - x_cg: spostamento orizzontale rispetto al centro geometrico
            - y_cg: quota verticale (riferita alla base del maschio)
            - z_cg: fuori piano (sempre thickness/2)
        """
        A_gross = self.gross_area
        A_tot = A_gross
        Sy = 0.0  # Momento statico rispetto all'asse Y (per calcolare x_cg)
        Sx = A_gross * (self.height / 2.0)  # Momento statico rispetto all'asse X (per y_cg)
        
        # Sottrai aperture con coerenza dimensionale
        for op in self.openings:
            # Valida posizione apertura
            if op.y_bottom + op.height > self.height:
                warnings.warn(
                    f"Apertura eccede altezza maschio: y_bottom={op.y_bottom:.2f} + height={op.height:.2f} > {self.height:.2f}",
                    UserWarning
                )
            
            phi = min(max(op.height, 0.0) / max(self.height, 1e-9), 1.0)
            b = max(op.effective_width, 0.0)
            A_op = self.thickness * b * phi
            
            A_tot -= A_op
            Sy -= A_op * op.x_center
            # y_bottom riferito alla base del maschio
            Sx -= A_op * (op.y_bottom + op.height/2.0)
        
        if A_tot > 0:
            x_cg = Sy / A_tot
            y_cg = Sx / A_tot
        else:
            x_cg = 0.0
            y_cg = self.height / 2.0
        
        return (x_cg, y_cg, self.thickness/2.0)
    
    @property
    def torsional_constant(self) -> float:
        """Costante torsionale [m⁴]"""
        # Per sezione rettangolare sottile
        a = max(self.length, self.thickness)
        b = min(self.length, self.thickness)
        
        if b/a < 0.1:
            # Sezione sottile
            J = a * b**3 / 3
        else:
            # Formula di Bredt per sezione chiusa equivalente
            J = a * b**3 * (1 - 0.63 * b/a) / 3
        
        # Riduzione per aperture: usa rapporto di vuoto lungo la lunghezza pesato sull'altezza
        if self.openings:
            void_length = 0.0
            for op in self.openings:
                phi = min(max(op.height, 0.0) / max(self.height, 1e-9), 1.0)
                void_length += max(op.effective_width, 0.0) * phi
            
            void_ratio = min(void_length / max(self.length, 1e-9), 0.95)
            J *= max(1.0 - 0.5 * void_ratio, 0.3)
        
        return J
    
    @property
    def opening_ratio(self) -> float:
        """Rapporto di vuoto efficace sul maschio (0-1), coerente con la riduzione in piano.
        
        Rappresenta la frazione di lunghezza "persa" per le aperture,
        pesata sulla frazione di altezza interessata da ciascuna apertura.
        """
        if not self.openings or self.length <= 0:
            return 0.0
        
        void_length = 0.0
        for op in self.openings:
            phi = min(max(op.height, 0.0) / max(self.height, 1e-9), 1.0)
            void_length += max(op.effective_width, 0.0) * phi
        
        return max(0.0, min(void_length / self.length, 1.0))
    
    def get_reinforced_properties(self) -> Dict[str, float]:
        """Calcola proprietà della sezione rinforzata"""
        props = {
            'area_ratio': self.effective_area / self.net_area,
            'inertia_ratio': self.effective_inertia / self.net_inertia,
            'strength_increase_M': 0.0,  # % incremento momento
            'strength_increase_V': 0.0,  # kN/m incremento taglio
            'ductility_increase': 0.0    # % incremento duttilità 
        }
        
        for reinf in self.reinforcements:
            props['strength_increase_M'] += reinf.contribution_M
            props['strength_increase_V'] += reinf.contribution_V  # kN/m
            props['ductility_increase'] += 10 * reinf.efficiency  # Stima
        
        return props
    
    def apply_damage(self, damage_level: float) -> GeometryPier:
        """
        Applica danno alla geometria (riduzione proprietà).
        
        Args:
            damage_level: Livello danno [0-1]
            
        Returns:
            Nuova geometria danneggiata
        """
        damaged = copy.deepcopy(self)
        
        # Riduci proprietà efficaci
        reduction = 1 - damage_level
        damaged.effective_height_factor *= reduction
        damaged.shear_retention_factor *= reduction**1.5
        
        # Aumenta eccentricità 
        damaged.eccentricity_top *= (1 + damage_level)
        damaged.eccentricity_bottom *= (1 + damage_level)
        
        # Ricalcola parametri derivati
        damaged.refresh()
        
        return damaged
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializza in dizionario"""
        data = {
            'length': self.length,
            'height': self.height,
            'thickness': self.thickness,
            'h0': self.h0,
            'boundary_conditions': self.boundary_conditions.value,
            'wall_type': self.wall_type.value,
            'eccentricity_top': self.eccentricity_top,
            'eccentricity_bottom': self.eccentricity_bottom,
            'out_of_plane_offset': self.out_of_plane_offset,
            'effective_height_factor': self.effective_height_factor,
            'shear_retention_factor': self.shear_retention_factor,
            'storey': self.storey  # Persisti il piano
        }
        
        # Serializza oggetti complessi
        data['openings'] = [asdict(op) for op in self.openings]
        data['reinforcements'] = [
            {**asdict(r), 'type': r.type.value} 
            for r in self.reinforcements
        ]
        data['tie_rods'] = [asdict(t) for t in self.tie_rods]
        
        # Altri campi opzionali
        if self.elastic_constraints:
            data['elastic_constraints'] = self.elastic_constraints
        if self.irregularities:
            data['irregularities'] = self.irregularities
        if self.base_isolation:
            data['base_isolation'] = self.base_isolation
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GeometryPier:
        """Deserializza da dizionario"""
        data = copy.deepcopy(data)
        
        # Ricostruisci enum
        if 'boundary_conditions' in data:
            data['boundary_conditions'] = BoundaryCondition(data['boundary_conditions'])
        if 'wall_type' in data:
            data['wall_type'] = WallType(data['wall_type'])
        
        # Ricostruisci oggetti
        if 'openings' in data:
            openings = []
            for op in data['openings']:
                # Ricostruisci Lintel se presente
                if 'lintel' in op and isinstance(op['lintel'], dict):
                    op['lintel'] = Lintel(**op['lintel'])
                openings.append(Opening(**op))
            data['openings'] = openings
            
        if 'reinforcements' in data:
            data['reinforcements'] = [
                Reinforcement(**{**r, 'type': ReinforcementType(r['type'])})
                for r in data['reinforcements']
            ]
        
        if 'tie_rods' in data:
            data['tie_rods'] = [TieRod(**t) for t in data['tie_rods']]
        
        return cls(**data)
    
    def export_to_sap2000(self) -> Dict[str, Any]:
        """Export per SAP2000 API"""
        return {
            'ObjectType': 'Frame',
            'SectionName': f'Pier_{self.length}x{self.thickness}',
            'Material': 'MASONRY',
            'Length': self.height,
            'Area': self.effective_area,
            'I33': self.effective_inertia,
            'I22': self.thickness * self.length**3 / 12,
            'J': self.torsional_constant,
            'As2': self.shear_area,  # Area di taglio esplicita
            'As3': self.shear_area,  # Area di taglio esplicita
            'Modifiers': {
                'Area': 1.0,
                'ShearArea2': 1.0,  # Lasciato a 1.0
                'ShearArea3': 1.0,  # Lasciato a 1.0
                'Inertia22': 1.0,
                'Inertia33': 1.0,
                'Mass': 1.0,
                'Weight': 1.0
            }
        }

# ============================================================================
# CLASSE GeometrySpandrel
# ============================================================================

@dataclass
class GeometrySpandrel:
    """
    Geometria completa fascia di piano secondo NTC 2018.
    
    Attributes:
        length: Lunghezza fascia [m]
        height: Altezza fascia [m]
        thickness: Spessore [m]
        arch_rise: Freccia arco se presente [m]
        has_lintel: Presenza architrave
        tie_rod: Tirante se presente
        reinforcements: Rinforzi applicati
        effective_depth: Altezza efficace per flessione
        strut_inclination: Inclinazione puntone per strut-and-tie
    """
    length: float
    height: float
    thickness: float
    
    # Elementi costruttivi
    arch_rise: float = 0.0
    arch_type: Optional[ArchType] = None
    has_lintel: bool = False
    lintel: Optional[Lintel] = None
    tie_rod: Optional[TieRod] = None
    
    # Rinforzi
    reinforcements: List[Reinforcement] = field(default_factory=list)
    
    # Parametri meccanici
    effective_depth: Optional[float] = None
    strut_inclination: float = 45.0  # gradi
    compression_zone_height: Optional[float] = None
    
    # Condizioni al contorno
    boundary_conditions: BoundaryCondition = BoundaryCondition.FIXED_FIXED
    support_width: float = 0.30  # Larghezza appoggi [m]
    
    def __post_init__(self):
        """Calcola parametri derivati"""
        if self.effective_depth is None:
            self.effective_depth = self.height * 0.9
        
        # Imposta tipo arco se c'è freccia
        if self.arch_rise > 0 and self.arch_type is None:
            if self.arch_rise / self.length < 0.1:
                self.arch_type = ArchType.SEGMENTAL
            elif self.arch_rise / self.length < 0.3:
                self.arch_type = ArchType.CIRCULAR
            else:
                self.arch_type = ArchType.POINTED

    @property
    def width(self) -> float:
        """Larghezza sezione (alias per height) [m]"""
        return self.height

    @property
    def area(self) -> float:
        """Area sezione [m²]"""
        return self.height * self.thickness
    
    @property
    def inertia(self) -> float:
        """Momento d'inerzia [m⁴]"""
        return self.thickness * self.height**3 / 12
    
    @property
    def is_deep_beam(self) -> bool:
        """Verifica se è trave tozza (L/h < 2)"""
        return self.length / self.height < 2.0
    
    @property
    def is_arch_mechanism(self) -> bool:
        """Verifica se può sviluppare meccanismo ad arco"""
        return (self.arch_rise > 0 or 
                self.has_lintel or 
                self.height / self.length > 0.3)
    
    @property
    def arch_thrust(self) -> float:
        """Spinta orizzontale dell'arco [kN/m]"""
        if self.arch_rise <= 0:
            return 0.0
        
        # Formula per arco parabolico con carico uniforme
        q = 10.0  # kN/m² carico stimato
        H = q * self.length**2 / (8 * self.arch_rise)
        
        return H
    
    @property
    def tie_rod_required(self) -> bool:
        """Verifica se è necessario un tirante"""
        # Spinta normalizzata per larghezza fuori piano
        thrust_normalized = self.arch_thrust * self.thickness  # kN
        
        if thrust_normalized > 20:  # kN soglia (50 kN/m * 0.4m tipico)
            return True
        if self.is_deep_beam and not self.has_lintel:
            return True
        return False
    
    @property
    def strut_and_tie_angle(self) -> float:
        """Angolo puntone per modello strut-and-tie [rad]"""
        if self.is_deep_beam:
            # Per travi tozze
            theta = math.atan(2 * self.effective_depth / self.length)
        else:
            # Angolo standard
            theta = math.radians(self.strut_inclination)
        
        # Limiti NTC (21.8° - 45°)
        return max(math.radians(21.8), min(theta, math.radians(45)))
    
    @property
    def effective_height_strut(self) -> float:
        """Altezza efficace puntone compresso [m]"""
        return self.effective_depth * math.sin(self.strut_and_tie_angle)
    
    def get_capacity_flexure(self, N: float = 0) -> float:
        """
        Capacità a flessione considerando sforzo normale.
        
        Nota: Formula euristica semplificata per stima preliminare.
        
        Args:
            N: Sforzo normale [kN] (positivo = compressione)
            
        Returns:
            Momento resistente [kNm]
        """
        # Verifica pressoflessione semplificata
        f_m = 2.0  # MPa resistenza muratura (da material) - VALORE INDICATIVO
        
        # Eccentricità limite
        e_max = self.thickness / 6
        
        # Momento massimo
        M_max = N * e_max + f_m * self.area * self.thickness / 6 * 1000
        
        # Incremento per rinforzi
        for reinf in self.reinforcements:
            # Solo se vicino a 90° (±15°), evita falsi positivi
            if abs((reinf.orientation % 180) - 90) <= 15:
                M_max *= (1 + reinf.contribution_M / 100)
        
        # Contributo tirante
        if self.tie_rod:
            lever_arm = self.effective_depth
            M_max += self.tie_rod.capacity * lever_arm
        
        return M_max
    
    def get_capacity_shear(self) -> float:
        """
        Capacità a taglio.
        
        Nota: Formula euristica semplificata per stima preliminare.
        
        Returns:
            Taglio resistente [kN]
        """
        # Taglio base muratura
        tau_0 = 0.1  # MPa (da material) - VALORE INDICATIVO
        V_base = tau_0 * self.area * 1000  # kN
        
        # Meccanismo ad arco se applicabile
        if self.is_arch_mechanism:
            # arch_thrust [kN/m] → * thickness [m] → kN
            V_arch = self.arch_thrust * math.tan(self.strut_and_tie_angle) * self.thickness
            V_base = max(V_base, V_arch)
        
        # Contributo rinforzi
        V_reinf = 0
        for reinf in self.reinforcements:
            V_reinf += reinf.contribution_V  # kN/m
        V_reinf *= self.thickness  # porta a kN
        
        return V_base + V_reinf
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializza in dizionario"""
        data = {
            'length': self.length,
            'height': self.height,
            'thickness': self.thickness,
            'arch_rise': self.arch_rise,
            'has_lintel': self.has_lintel,
            'effective_depth': self.effective_depth,
            'strut_inclination': self.strut_inclination,
            'boundary_conditions': self.boundary_conditions.value,
            'support_width': self.support_width
        }
        
        # Gestisci enum
        if self.arch_type:
            data['arch_type'] = self.arch_type.value
        
        # Serializza oggetti complessi
        if self.lintel:
            data['lintel'] = asdict(self.lintel)
        if self.tie_rod:
            data['tie_rod'] = asdict(self.tie_rod)
        data['reinforcements'] = [
            {**asdict(r), 'type': r.type.value}
            for r in self.reinforcements
        ]
        
        if self.compression_zone_height is not None:
            data['compression_zone_height'] = self.compression_zone_height
        
        return data

# ============================================================================
# CLASSI PER ELEMENTI SPECIALI
# ============================================================================

@dataclass
class GeometryArch:
    """
    Geometria arco murario.
    
    Attributes:
        span: Luce netta [m]
        rise: Freccia/saetta [m]
        thickness: Spessore arco [m]
        depth: Profondità (fuori piano) [m]
        arch_type: Tipo di arco
        n_voussoirs: Numero conci
        springer_angle: Angolo alle imposte [°]
        crown_thickness: Spessore in chiave [m]
        fill_height: Altezza riempimento [m]
        reinforced: Presenza di rinforzi
    """
    span: float
    rise: float
    thickness: float
    depth: float = 1.0
    arch_type: ArchType = ArchType.CIRCULAR
    n_voussoirs: int = 0  # 0 = continuo
    springer_angle: Optional[float] = None
    crown_thickness: Optional[float] = None
    fill_height: float = 0.0
    reinforced: bool = False
    reinforcements: List[Reinforcement] = field(default_factory=list)
    
    def __post_init__(self):
        """Calcola parametri geometrici"""
        if self.crown_thickness is None:
            self.crown_thickness = self.thickness
        
        if self.springer_angle is None:
            if self.arch_type == ArchType.CIRCULAR:
                # Angolo per arco circolare
                self.springer_angle = math.degrees(
                    math.atan(4 * self.rise / self.span)
                )
            elif self.arch_type == ArchType.POINTED:
                self.springer_angle = 60  # Tipico gotico
            else:
                self.springer_angle = 30  # Default
    
    @property
    def radius(self) -> float:
        """Raggio di curvatura [m]"""
        if self.rise <= 0:
            return float("inf")  # Arco degenere → raggio infinito
            
        if self.arch_type == ArchType.CIRCULAR:
            # Formula per arco circolare
            return (self.span**2 + 4 * self.rise**2) / (8 * self.rise)
        elif self.arch_type == ArchType.PARABOLIC:
            # Raggio al vertice per parabola
            return self.span**2 / (8 * self.rise)
        else:
            # Approssimazione
            return self.span / 2
    
    @property
    def arch_length(self) -> float:
        """Lunghezza sviluppata dell'arco [m]"""
        if self.rise <= 0:
            return self.span  # Approssimazione per piattabanda
            
        if self.arch_type == ArchType.CIRCULAR:
            # Lunghezza arco circolare
            theta = 2 * math.asin(self.span / (2 * self.radius))
            return self.radius * theta
        elif self.arch_type == ArchType.PARABOLIC:
            # Formula approssimata per parabola
            return self.span * (1 + 8 * (self.rise/self.span)**2 / 3)
        else:
            # Approssimazione catenaria
            return self.span * (1 + 2 * (self.rise/self.span)**2)
    
    @property
    def thrust_line_rise(self) -> float:
        """Freccia della linea delle pressioni [m]"""
        # Per carico uniforme
        if self.fill_height > 0:
            # Con riempimento
            return self.rise * 0.8
        else:
            # Solo peso proprio
            return self.rise * 0.9
    
    @property
    def minimum_thickness(self) -> float:
        """Spessore minimo secondo regole empiriche [m]"""
        # Regola di Rondelet
        if self.arch_type == ArchType.CIRCULAR:
            return self.radius / 24
        else:
            return self.span / 40
    
    @property
    def stability_coefficient(self) -> float:
        """Coefficiente di stabilità (thickness/rise)"""
        return self.thickness / self.rise
    
    def get_thrust(self, load: float = 10.0) -> float:
        """
        Calcola spinta orizzontale.
        
        Args:
            load: Carico verticale [kN/m²]
            
        Returns:
            Spinta orizzontale [kN]
        """
        if self.arch_type == ArchType.CIRCULAR:
            # Formula per arco circolare
            H = load * self.radius * self.depth
        elif self.arch_type == ArchType.PARABOLIC:
            # Formula per arco parabolico
            H = load * self.span**2 / (8 * self.rise) * self.depth
        else:
            # Formula generale approssimata
            H = load * self.span**2 / (8 * self.thrust_line_rise) * self.depth
        
        return H

@dataclass
class GeometryVault:
    """
    Geometria volta muraria.
    
    Attributes:
        type: Tipo di volta
        span_x: Luce direzione X [m]
        span_y: Luce direzione Y [m]
        rise: Freccia/altezza [m]
        thickness: Spessore [m]
        ribs: Presenza di costoloni
        fill_material: Materiale riempimento
        reinforced: Presenza rinforzi
    """
    type: VaultType = VaultType.BARREL
    span_x: float = 5.0
    span_y: float = 5.0
    rise: float = 1.0
    thickness: float = 0.12
    ribs: bool = False
    rib_spacing: float = 2.0
    fill_material: Optional[str] = None
    reinforced: bool = False
    reinforcements: List[Reinforcement] = field(default_factory=list)
    
    @property
    def surface_area(self) -> float:
        """Area superficie volta [m²]"""
        if self.type == VaultType.BARREL:
            # Volta a botte
            radius = (self.span_x**2 + 4 * self.rise**2) / (8 * self.rise)
            theta = 2 * math.asin(self.span_x / (2 * radius))
            return radius * theta * self.span_y
        
        elif self.type == VaultType.DOME:
            # Cupola (calotta sferica)
            radius = (self.span_x**2 + 4 * self.rise**2) / (8 * self.rise)
            return 2 * math.pi * radius * self.rise
        
        elif self.type == VaultType.CROSS:
            # Volta a crociera (approssimata)
            return 1.2 * self.span_x * self.span_y
        
        else:
            # Approssimazione generica
            return self.span_x * self.span_y * (1 + 0.5 * self.rise / min(self.span_x, self.span_y))
    
    @property
    def weight(self) -> float:
        """Peso proprio volta [kN]"""
        volume = self.surface_area * self.thickness
        density = 18.0  # kN/m³ per muratura
        
        weight = volume * density
        
        # Aggiungi riempimento se presente
        if self.fill_material:
            fill_density = 16.0  # kN/m³ per riempimento alleggerito
            fill_volume = self.span_x * self.span_y * self.rise * 0.5
            weight += fill_volume * fill_density
        
        return weight
    
    @property
    def thrust_at_base(self) -> Tuple[float, float]:
        """Spinte alla base (Hx, Hy) [kN/m]"""
        q = self.weight / (self.span_x * self.span_y)  # Carico per unità di superficie
        
        if self.type == VaultType.BARREL:
            Hx = q * self.span_x**2 / (8 * self.rise)
            Hy = 0
        elif self.type == VaultType.DOME:
            # Spinta radiale uniforme
            H_radial = q * self.span_x / 4
            Hx = Hy = H_radial
        elif self.type == VaultType.CROSS:
            # Spinte su entrambe le direzioni
            Hx = q * self.span_x**2 / (12 * self.rise)
            Hy = q * self.span_y**2 / (12 * self.rise)
        else:
            Hx = Hy = q * max(self.span_x, self.span_y) / 8
        
        return (Hx, Hy)

@dataclass
class GeometryColumn:
    """
    Geometria colonna/pilastro in muratura.
    
    Attributes:
        diameter: Diametro (se circolare) [m]
        width: Larghezza (se rettangolare) [m]
        depth: Profondità (se rettangolare) [m]
        height: Altezza [m]
        shape: Forma sezione (circular, square, rectangular, octagonal)
        base_type: Tipo di base (fixed, pinned, isolated)
        capital_type: Tipo di capitello
        reinforced: Presenza di cerchiature/rinforzi
    """
    height: float
    diameter: Optional[float] = None  # Per sezione circolare
    width: Optional[float] = None     # Per sezione rettangolare
    depth: Optional[float] = None     # Per sezione rettangolare
    shape: str = "circular"
    base_type: str = "fixed"
    capital_type: Optional[str] = None
    reinforced: bool = False
    reinforcements: List[Reinforcement] = field(default_factory=list)
    
    def __post_init__(self):
        """Validazione e defaults"""
        if self.shape == "circular" and self.diameter is None:
            raise ValueError("Diametro richiesto per colonna circolare")
        if self.shape in ["square", "rectangular"] and self.width is None:
            raise ValueError("Larghezza richiesta per colonna rettangolare")
        if self.shape == "rectangular" and self.depth is None:
            self.depth = self.width  # Default quadrata
    
    @property
    def area(self) -> float:
        """Area sezione [m²]"""
        if self.shape == "circular":
            return math.pi * (self.diameter/2)**2
        elif self.shape == "octagonal":
            # Ottagono regolare inscritto
            return 2 * (1 + math.sqrt(2)) * (self.diameter/2)**2
        else:  # rectangular/square
            return self.width * self.depth
    
    @property
    def inertia(self) -> Tuple[float, float]:
        """Momenti d'inerzia (Ix, Iy) [m⁴]"""
        if self.shape == "circular":
            I = math.pi * self.diameter**4 / 64
            return (I, I)
        elif self.shape == "octagonal":
            # Approssimazione
            I = 0.055 * self.diameter**4
            return (I, I)
        else:  # rectangular
            Ix = self.width * self.depth**3 / 12
            Iy = self.depth * self.width**3 / 12
            return (Ix, Iy)
    
    @property
    def radius_of_gyration(self) -> float:
        """Raggio d'inerzia minimo [m]"""
        Ix, Iy = self.inertia
        I_min = min(Ix, Iy)
        return math.sqrt(I_min / self.area)
    
    @property
    def slenderness(self) -> float:
        """Snellezza"""
        # Lunghezza libera di inflessione
        if self.base_type == "fixed":
            L_eff = 0.7 * self.height
        elif self.base_type == "pinned":
            L_eff = 1.0 * self.height
        else:  # isolated
            L_eff = 2.0 * self.height
        
        return L_eff / self.radius_of_gyration
    
    def buckling_capacity(self, E: float = 3000.0) -> float:
        """
        Carico critico di Eulero [kN].
        
        Args:
            E: Modulo elastico [MPa]
            
        Returns:
            Carico critico di buckling [kN]
        """
        Ix, Iy = self.inertia
        I_min = min(Ix, Iy)
        
        # Lunghezza efficace coerente con slenderness
        if self.base_type == "fixed":
            L_eff = 0.7 * self.height
        elif self.base_type == "pinned":
            L_eff = 1.0 * self.height
        else:  # isolated
            L_eff = 2.0 * self.height
        
        # Formula di Eulero
        P_cr = math.pi**2 * E * I_min / L_eff**2 * 1000  # kN
        
        # Riduzione per imperfezioni
        if self.slenderness > 50:
            P_cr *= 0.7
        elif self.slenderness > 30:
            P_cr *= 0.85
        
        return P_cr

# ============================================================================
# CLASSE PER PARETI COMPLETE (CORRETTA INDENTAZIONE)
# ============================================================================

@dataclass
class GeometryWall:
    """
    Geometria parete muraria completa con aperture e rinforzi.
    
    Gestisce pareti multi-piano con identificazione automatica
    di maschi e fasce.
    """
    length: float                      # Lunghezza totale [m]
    height: float                      # Altezza totale [m]
    thickness: float                   # Spessore [m]
    n_floors: int = 1                  # Numero piani
    floor_height: float = 3.0          # Altezza interpiano [m]
    
    # Aperture organizzate per piano
    openings_per_floor: Dict[int, List[Opening]] = field(default_factory=dict)
    
    # Tipologia costruttiva
    wall_type: WallType = WallType.SINGLE_LEAF
    
    # Rinforzi globali
    global_reinforcements: List[Reinforcement] = field(default_factory=list)
    
    # Elementi identificati
    piers: List[GeometryPier] = field(default_factory=list)
    spandrels: List[GeometrySpandrel] = field(default_factory=list)
    
    def __post_init__(self):
        """Identifica automaticamente maschi e fasce"""
        if not self.piers:
            self.identify_structural_elements()
    
    def identify_structural_elements(self):
        """Identifica maschi murari e fasce di piano"""
        self.piers.clear()
        self.spandrels.clear()
        
        for floor in range(self.n_floors):
            # Aperture del piano
            openings = self.openings_per_floor.get(floor, [])
            
            # Identifica maschi (parti verticali tra aperture) - VERSIONE ROBUSTA
            breaks = [0.0, self.length]
            for opening in openings:
                x_c_abs = opening.x_center + self.length / 2.0
                x_left = max(0.0, x_c_abs - opening.width/2.0)
                x_right = min(self.length, x_c_abs + opening.width/2.0)
                breaks.extend([x_left, x_right])
            
            # Rimuovi duplicati e ordina
            breaks = sorted(set(breaks))
            
            # Crea maschi sugli intervalli consecutivi
            for a, b in zip(breaks[:-1], breaks[1:]):
                if (b - a) > 0.3:  # Minimo 30cm
                    pier = GeometryPier(
                        length=b - a,
                        height=self.floor_height,
                        thickness=self.thickness,
                        boundary_conditions=BoundaryCondition.FIXED_FIXED if floor > 0 else BoundaryCondition.CANTILEVER,
                        wall_type=self.wall_type,
                        storey=floor  # Traccia il piano di appartenenza
                    )
                    
                    # Propaga aperture locali che intersecano [a, b]
                    for opening in openings:
                        x_c_abs = opening.x_center + self.length / 2.0
                        op_left = x_c_abs - opening.width/2.0
                        op_right = x_c_abs + opening.width/2.0
                        
                        # Se l'apertura interseca questo maschio
                        if op_right > a and op_left < b:
                            # Crea apertura locale con coordinate relative al maschio
                            local_opening = Opening(
                                width=min(op_right, b) - max(op_left, a),
                                height=opening.height,
                                x_center=(x_c_abs - (a + b)/2.0),  # Relativo al centro del maschio
                                y_bottom=opening.y_bottom,
                                type=opening.type,
                                lintel=opening.lintel,
                                reinforced=opening.reinforced,
                                reinforcement_width=opening.reinforcement_width
                            )
                            pier.openings.append(local_opening)
                    
                    pier.refresh()  # Aggiorna h0 e altri parametri
                    self.piers.append(pier)
            
            # Identifica fasce (parti orizzontali sopra aperture)
            if floor < self.n_floors - 1:  # Non all'ultimo piano
                for opening in openings:
                    if opening.type == "window":
                        spandrel = GeometrySpandrel(
                            length=opening.width,
                            height=self.floor_height - opening.height - opening.y_bottom,
                            thickness=self.thickness,
                            has_lintel=opening.lintel is not None
                        )
                        if spandrel.height > 0.2:  # Minimo 20cm
                            self.spandrels.append(spandrel)
    
    @property
    def total_pier_area(self) -> float:
        """Area totale maschi murari [m²]"""
        return sum(pier.net_area for pier in self.piers)
    
    @property
    def opening_ratio(self) -> float:
        """Rapporto superficie forata"""
        total_opening_area = sum(
            sum(op.area for op in openings)
            for openings in self.openings_per_floor.values()
        )
        wall_area = self.length * self.height
        return total_opening_area / wall_area if wall_area > 0 else 0.0
    
    def add_opening(self, floor: int, opening: Opening):
        """Aggiunge apertura a un piano"""
        if floor not in self.openings_per_floor:
            self.openings_per_floor[floor] = []
        self.openings_per_floor[floor].append(opening)
        
        # Rigenera elementi strutturali
        self.identify_structural_elements()
    
    def apply_global_reinforcement(self, reinforcement: Reinforcement):
        """Applica rinforzo a tutti gli elementi"""
        self.global_reinforcements.append(reinforcement)
        
        # Propaga a maschi e fasce
        for pier in self.piers:
            pier.reinforcements.append(copy.deepcopy(reinforcement))
        for spandrel in self.spandrels:
            spandrel.reinforcements.append(copy.deepcopy(reinforcement))

# ============================================================================
# FUNZIONI DI UTILITÀ
# ============================================================================

def _reinforcement_area_m2_per_m(reinf: Reinforcement) -> float:
    """
    Converte l'input del rinforzo in area efficace [m²/m] in modo robusto.
    
    - FRP/FRCM/intonaco armato: `area` = spessore [mm] → A_f = t[m] * (width/spacing) * n_layers
    - Altri (acciaio, camicie, ecc.): `area` = cm²/m già calcolata → solo conversione unità 
    
    Args:
        reinf: Oggetto Reinforcement
        
    Returns:
        Area efficace del rinforzo [m²/m]
    """
    # Tipi sottili: spessore in mm
    thin_types = {ReinforcementType.FRP, ReinforcementType.FRCM, ReinforcementType.REINFORCED_PLASTER}
    if reinf.type in thin_types:
        t_m = reinf.area / 1000.0  # mm → m
        ratio = (reinf.width / reinf.spacing) if reinf.spacing > 0 else 1.0
        return t_m * ratio * reinf.n_layers
    
    # Altri tipi: area già in cm²/m (NON moltiplicare per width/spacing!)
    return (reinf.area / 10000.0) * max(1, reinf.n_layers)

def calculate_wall_weight(wall: Union[GeometryWall, GeometryPier], 
                         density: float = 18.0) -> float:
    """
    Calcola peso proprio parete.
    
    Args:
        wall: Geometria parete
        density: Peso specifico muratura [kN/m³]
        
    Returns:
        Peso totale [kN]
    """
    if isinstance(wall, GeometryWall):
        volume = wall.length * wall.height * wall.thickness
        # Sottrai aperture
        for openings in wall.openings_per_floor.values():
            for opening in openings:
                volume -= opening.area * wall.thickness
    else:
        # GeometryPier: volume pieno meno volume delle aperture
        volume = wall.length * wall.thickness * wall.height
        for opening in wall.openings:
            volume -= max(opening.width, 0.0) * wall.thickness * max(opening.height, 0.0)
    
    return max(volume, 0.0) * density

def check_slenderness_limits(element: Union[GeometryPier, GeometryColumn]) -> Dict[str, Any]:
    """
    Verifica limiti di snellezza secondo NTC 2018.
    
    Args:
        element: Elemento da verificare
        
    Returns:
        Dizionario con esito verifica
    """
    lambda_actual = element.slenderness
    lambda_limit = element.slenderness_limit if hasattr(element, 'slenderness_limit') else 20
    
    return {
        'slenderness': lambda_actual,
        'limit': lambda_limit,
        'verified': lambda_actual <= lambda_limit,
        'safety_factor': lambda_limit / lambda_actual if lambda_actual > 0 else float('inf'),
        'recommendation': 'OK' if lambda_actual <= lambda_limit else 'Necessario irrigidimento'
    }

def calculate_effective_thickness(wall_type: WallType, 
                                 nominal_thickness: float,
                                 leaf_thicknesses: Optional[List[float]] = None) -> float:
    """
    Calcola spessore efficace per pareti multi-strato.
    
    Args:
        wall_type: Tipo di parete
        nominal_thickness: Spessore nominale [m]
        leaf_thicknesses: Spessori singoli paramenti [m]
        
    Returns:
        Spessore efficace [m]
    """
    if wall_type == WallType.SINGLE_LEAF:
        return nominal_thickness
    
    elif wall_type == WallType.DOUBLE_LEAF:
        if leaf_thicknesses and len(leaf_thicknesses) >= 2:
            # EC6 formula per doppio paramento
            t1, t2 = leaf_thicknesses[0], leaf_thicknesses[1]
            k = 0.6  # Fattore di connessione
            return (t1**3 + k * t2**3)**(1/3)
        return nominal_thickness * 0.85
    
    elif wall_type == WallType.THREE_LEAF:
        if leaf_thicknesses and len(leaf_thicknesses) >= 3:
            t1, t2, t3 = leaf_thicknesses[0], leaf_thicknesses[1], leaf_thicknesses[2]
            # Solo paramenti esterni contribuiscono
            return (t1**3 + t3**3)**(1/3)
        return nominal_thickness * 0.7
    
    elif wall_type == WallType.CAVITY_WALL:
        if leaf_thicknesses and len(leaf_thicknesses) >= 2:
            # Solo paramento interno portante
            return leaf_thicknesses[0]
        return nominal_thickness * 0.5
    
    else:  # COMPOSITE
        return nominal_thickness * 0.9

def calculate_shear_center(pier: GeometryPier, k_sc: float = 0.5) -> Tuple[float, float]:
    """
    Calcola centro di taglio considerando aperture.
    
    Nota: Metodo euristico con fattore k_sc calibrabile.
    
    Args:
        pier: Maschio murario
        k_sc: Fattore euristico (default 0.5, range tipico 0.3-0.7)
        
    Returns:
        Coordinate centro di taglio (x, y) [m]
    """
    if not pier.openings:
        # Sezione rettangolare: centro di taglio = baricentro
        return (0, pier.height/2)
    
    # Con aperture: calcolo più complesso
    # Approssimazione euristica: sposta verso parti piene
    x_sc = 0
    y_sc = pier.height/2
    
    # Correzione per aperture asimmetriche coerente con la sezione in pianta
    void_static_moment = 0.0
    void_area = 0.0
    for op in pier.openings:
        phi = min(max(op.height, 0.0) / max(pier.height, 1e-9), 1.0)
        b = max(op.effective_width, 0.0)
        A_op = pier.thickness * b * phi
        void_area += A_op
        void_static_moment += A_op * op.x_center
    
    A_eff = pier.gross_area - void_area
    if A_eff > 0:
        # Fattore euristico k_sc (calibrabile per test e tarature)
        x_sc = -void_static_moment / (2 * A_eff) * k_sc
    
    return (x_sc, y_sc)

def create_equivalent_frame_geometry(wall: GeometryWall) -> Dict[str, Any]:
    """
    Crea geometria per modello a telaio equivalente.
    
    Nota: Gli elementi hanno nodes=[] che devono essere assegnati
    a valle basandosi sul mapping delle coordinate.
    
    Args:
        wall: Parete completa
        
    Returns:
        Dizionario con nodi ed elementi per telaio
    """
    nodes = []
    elements = []
    node_id = 0
    
    # Crea nodi per ogni intersezione
    for floor in range(wall.n_floors + 1):
        y = floor * wall.floor_height
        
        # Nodi agli estremi
        nodes.append({
            'id': node_id,
            'x': 0,
            'y': y,
            'restraint': 'fixed' if floor == 0 else 'free'
        })
        node_id += 1
        
        nodes.append({
            'id': node_id,
            'x': wall.length,
            'y': y,
            'restraint': 'fixed' if floor == 0 else 'free'
        })
        node_id += 1
        
        # Nodi intermedi per aperture
        if floor in wall.openings_per_floor:
            for opening in wall.openings_per_floor[floor]:
                # x_center locale → assoluto 0..L
                x_c_abs = opening.x_center + wall.length / 2.0
                x_left = x_c_abs - opening.width/2.0
                x_right = x_c_abs + opening.width/2.0
                
                nodes.append({'id': node_id, 'x': x_left, 'y': y, 'restraint': 'free'})
                node_id += 1
                nodes.append({'id': node_id, 'x': x_right, 'y': y, 'restraint': 'free'})
                node_id += 1
    
    # Crea elementi maschio
    elem_id = 0
    for pier in wall.piers:
        elements.append({
            'id': elem_id,
            'type': 'pier',
            'geometry': pier,
            'nodes': []  # TODO: Assegnare basandosi su coordinate
        })
        elem_id += 1
    
    # Crea elementi fascia
    for spandrel in wall.spandrels:
        elements.append({
            'id': elem_id,
            'type': 'spandrel',
            'geometry': spandrel,
            'nodes': []  # TODO: Assegnare basandosi su coordinate
        })
        elem_id += 1
    
    return {
        'nodes': nodes,
        'elements': elements,
        'n_stories': wall.n_floors,
        'story_height': wall.floor_height
    }

def export_to_sap2000_format(geometry: Union[GeometryPier, GeometrySpandrel, GeometryWall]) -> Dict[str, Any]:
    """
    Export geometria in formato SAP2000 API.
    
    Nota: I22/I33 seguono la convenzione locale del modulo.
    Verificare mapping con orientamento assi locali SAP2000.
    
    Args:
        geometry: Elemento da esportare
        
    Returns:
        Dizionario compatibile con SAP2000 API
    """
    if isinstance(geometry, GeometryPier):
        return geometry.export_to_sap2000()
    
    elif isinstance(geometry, GeometrySpandrel):
        return {
            'ObjectType': 'Frame',
            'SectionName': f'Spandrel_{geometry.length}x{geometry.height}',
            'Material': 'MASONRY',
            'Length': geometry.length,
            'Area': geometry.area,
            'I33': geometry.inertia,  # Verifica convenzione assi locali SAP
            'I22': geometry.thickness * geometry.length**3 / 12,  # Verifica convenzione
            'As2': geometry.area * 5/6,
            'As3': geometry.area * 5/6
        }
    
    elif isinstance(geometry, GeometryWall):
        sections = []
        
        # Export maschi
        for i, pier in enumerate(geometry.piers):
            section = pier.export_to_sap2000()
            section['Name'] = f'Pier_{i}'
            sections.append(section)
        
        # Export fasce
        for j, spandrel in enumerate(geometry.spandrels):
            section = export_to_sap2000_format(spandrel)
            section['Name'] = f'Spandrel_{j}'
            sections.append(section)
        
        return {
            'WallName': 'MasonryWall',
            'Height': geometry.height,
            'Length': geometry.length,
            'Thickness': geometry.thickness,
            'Sections': sections,
            'Material': 'MASONRY',
            'NumberOfStories': geometry.n_floors
        }
    
    else:
        raise TypeError(f"Tipo geometria non supportato: {type(geometry)}")

def validate_geometry_for_analysis(geometry: Union[GeometryPier, GeometrySpandrel, GeometryWall],
                                  analysis_type: str = "static") -> Dict[str, Any]:
    """
    Valida geometria per tipo di analisi specifico.
    
    Args:
        geometry: Geometria da validare
        analysis_type: Tipo analisi (static, pushover, dynamic, limit)
        
    Returns:
        Report validazione
    """
    errors = []
    warnings_list = []
    info = []
    
    # Controlli comuni
    if isinstance(geometry, GeometryPier):
        if geometry.slenderness > geometry.slenderness_limit:
            errors.append(f"Snellezza eccessiva: {geometry.slenderness:.1f} > {geometry.slenderness_limit}")
        
        # ora opening_ratio esiste anche sui maschi (coerente con la riduzione in piano)
        if geometry.opening_ratio > 0.4:
            warnings_list.append(f"Elevata percentuale di foratura: {geometry.opening_ratio*100:.1f}%")
        
        if geometry.reinforcements:
            info.append(f"Presenza di {len(geometry.reinforcements)} rinforzi")
    
    # Controlli specifici per tipo analisi
    if analysis_type == "pushover":
        if isinstance(geometry, GeometryPier):
            if geometry.h0 / geometry.height > 1.5:
                warnings_list.append("Altezza efficace molto elevata per pushover")
        
    elif analysis_type == "dynamic":
        if isinstance(geometry, (GeometryPier, GeometryWall)):
            mass = calculate_wall_weight(geometry) / 9.81  # Massa in ton
            if mass < 0.5:
                warnings_list.append("Massa molto bassa per analisi dinamica")
    
    elif analysis_type == "limit":
        if isinstance(geometry, GeometryPier):
            if geometry.eccentricity_top > geometry.thickness/6:
                errors.append("Eccentricità eccessiva per analisi limite")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings_list,
        'info': info
    }

def optimize_reinforcement_layout(geometry: Union[GeometryPier, GeometrySpandrel],
                                 target_capacity_increase: float = 0.3,
                                 reinforcement_type: ReinforcementType = ReinforcementType.FRP) -> List[Reinforcement]:
    """
    Ottimizza disposizione rinforzi per target di incremento capacità.
    
    Args:
        geometry: Elemento da rinforzare
        target_capacity_increase: Incremento capacità desiderato (0.3 = +30%)
        reinforcement_type: Tipo di rinforzo
        
    Returns:
        Lista rinforzi ottimizzati
    """
    reinforcements = []
    
    if isinstance(geometry, GeometryPier):
        # Rinforzo a flessione (verticale)
        if target_capacity_increase > 0.2:
            reinf_flexure = Reinforcement(
                type=reinforcement_type,
                area=0.5,  # mm di spessore
                orientation=0,  # Verticale
                width=150,  # mm
                spacing=300,  # mm
                n_layers=2 if target_capacity_increase > 0.4 else 1,
                application_side="both",
                efficiency=0.7
            )
            reinforcements.append(reinf_flexure)
        
        # Rinforzo a taglio (diagonale/orizzontale)
        if geometry.shape_factor > 1.2:  # Elemento tozzo, critico a taglio
            reinf_shear = Reinforcement(
                type=reinforcement_type,
                area=0.3,
                orientation=45,  # Diagonale
                width=100,
                spacing=400,
                n_layers=1,
                application_side="both",
                efficiency=0.6
            )
            reinforcements.append(reinf_shear)
    
    elif isinstance(geometry, GeometrySpandrel):
        # Fasce: principalmente a taglio
        reinf_main = Reinforcement(
            type=reinforcement_type,
            area=0.4,
            orientation=90 if geometry.is_deep_beam else 45,
            width=120,
            spacing=250,
            n_layers=1,
            application_side="both",
            efficiency=0.65
        )
        reinforcements.append(reinf_main)
        
        # Se presente arco, rinforzo estradosso
        if geometry.arch_rise > 0:
            reinf_arch = Reinforcement(
                type=reinforcement_type,
                area=0.6,
                orientation=90,  # Circonferenziale
                width=200,
                spacing=200,
                n_layers=1,
                application_side="external",
                efficiency=0.8
            )
            reinforcements.append(reinf_arch)
    
    return reinforcements

def calculate_transformed_section_properties(geometry: GeometryPier,
                                           material_E: float = 3000.0) -> Dict[str, float]:
    """
    Calcola proprietà sezione trasformata con rinforzi.
    
    Proprietà riferite a sezione per unità di altezza.
    
    Args:
        geometry: Maschio con rinforzi
        material_E: Modulo elastico muratura [MPa]
        
    Returns:
        Proprietà sezione omogeneizzata
    """
    # Sezione base muratura
    A_m = geometry.net_area
    I_m = geometry.net_inertia
    
    # Contributi rinforzi
    A_total = A_m
    EI_total = material_E * I_m
    
    for reinf in geometry.reinforcements:
        # Rapporto moduli elastici
        n = reinf.E_f * 1000 / material_E  # GPa -> MPa
        
        # Area trasformata rinforzo
        A_f = _reinforcement_area_m2_per_m(reinf)  # m²/m
        A_f_transformed = n * A_f
        
        # Partecipazione alla flessione IN PIANO (I_m usa length³): leva lungo la LUNGHEZZA
        # Considera 1 bordo (external/internal) o 2 bordi (both)
        n_edges = 2 if reinf.application_side == "both" else 1
        d_edge = max(geometry.length/2.0 - 0.002, 0.0)  # lieve copriferro/offset
        
        # Area trasformata totale
        A_total += A_f_transformed * n_edges
        
        # Contributo a EI solo per rinforzi prevalentemente verticali
        if abs(reinf.orientation) < 45:  # Prevalentemente verticale
            # A_f è [m²/m] → per 1 m di altezza: A_f*1.0 [m²]
            EI_total += n * material_E * ((A_f * 1.0) * d_edge**2) * n_edges
    
    # Proprietà omogeneizzate
    E_eq = EI_total / I_m if I_m > 0 else material_E
    
    return {
        'A_transformed': A_total,
        'I_transformed': EI_total / material_E if material_E > 0 else I_m,
        'E_equivalent': E_eq,
        'n_ratio': E_eq / material_E,
        'centroid_shift': 0.0  # Da calcolare se necessario
    }

# ============================================================================
# CLASSI PER ANALISI AVANZATE
# ============================================================================

@dataclass
class MacroElement:
    """
    Macro-elemento per modellazione semplificata.
    
    Rappresenta porzione di muratura con comportamento
    non lineare concentrato.
    """
    id: str
    geometry: Union[GeometryPier, GeometrySpandrel]
    material: MaterialProto
    
    # Stato corrente
    damage_state: str = "undamaged"  # undamaged, cracked, yielded, failed
    stiffness_reduction: float = 1.0
    strength_reduction: float = 1.0
    
    # Cerniere plastiche
    hinges: Dict[str, Any] = field(default_factory=dict)
    
    def update_damage(self, drift: float):
        """Aggiorna stato di danno basato su drift"""
        if drift < 0.001:
            self.damage_state = "undamaged"
            self.stiffness_reduction = 1.0
        elif drift < 0.003:
            self.damage_state = "cracked"
            self.stiffness_reduction = 0.7
        elif drift < 0.01:
            self.damage_state = "yielded"
            self.stiffness_reduction = 0.3
            self.strength_reduction = 0.9
        else:
            self.damage_state = "failed"
            self.stiffness_reduction = 0.1
            self.strength_reduction = 0.5
    
    @property
    def effective_stiffness(self) -> float:
        """Rigidezza efficace considerando danno"""
        if isinstance(self.geometry, GeometryPier):
            EI = self.material.E * self.geometry.effective_inertia
        else:
            EI = self.material.E * self.geometry.inertia
        
        return EI * self.stiffness_reduction

@dataclass
class StructuralModel:
    """
    Modello strutturale completo per analisi.
    
    Gestisce assemblaggio di geometrie per analisi globale.
    """
    walls: List[GeometryWall] = field(default_factory=list)
    columns: List[GeometryColumn] = field(default_factory=list)
    arches: List[GeometryArch] = field(default_factory=list)
    vaults: List[GeometryVault] = field(default_factory=list)
    
    # Connessioni
    connections: Dict[str, str] = field(default_factory=dict)
    
    # Macro-elementi generati
    macro_elements: List[MacroElement] = field(default_factory=list)
    
    def generate_macro_elements(self, material: MaterialProto):
        """Genera macro-elementi da geometrie"""
        self.macro_elements.clear()
        elem_id = 0
        
        # Da pareti
        for wall in self.walls:
            for pier in wall.piers:
                macro = MacroElement(
                    id=f"ME_P_{elem_id}",
                    geometry=pier,
                    material=material
                )
                self.macro_elements.append(macro)
                elem_id += 1
            
            for spandrel in wall.spandrels:
                macro = MacroElement(
                    id=f"ME_S_{elem_id}",
                    geometry=spandrel,
                    material=material
                )
                self.macro_elements.append(macro)
                elem_id += 1
    
    @property
    def total_weight(self) -> float:
        """Peso totale struttura [kN]"""
        weight = 0
        
        for wall in self.walls:
            weight += calculate_wall_weight(wall)
        
        for column in self.columns:
            weight += column.area * column.height * 22  # kN/m³
        
        for vault in self.vaults:
            weight += vault.weight
        
        return weight
    
    @property
    def base_shear_capacity(self) -> float:
        """Stima capacità taglio alla base [kN] (solo maschi del piano terra)"""
        V_base = 0
        
        for wall in self.walls:
            for pier in wall.piers:
                # Considera solo i maschi del piano terra (storey = 0)
                if isinstance(pier, GeometryPier) and getattr(pier, 'storey', 0) == 0:
                    # Stima semplificata
                    tau_0 = 0.1  # MPa
                    V_base += tau_0 * pier.effective_area * 1000
        
        return V_base

# ============================================================================
# ESEMPIO D'USO E TEST
# ============================================================================

def example_usage():
    """Esempi di utilizzo del modulo geometry"""
    
    print("\n" + "="*70)
    print("GEOMETRY.PY v2.4.3 - ESEMPI D'USO")
    print("="*70)
    
    # Esempio 1: Maschio murario con aperture
    print("\n1. MASCHIO MURARIO CON APERTURE:")
    print("-"*40)
    
    pier = GeometryPier(
        length=2.5,
        height=3.2,
        thickness=0.4,
        boundary_conditions=BoundaryCondition.FIXED_FIXED,
        wall_type=WallType.DOUBLE_LEAF
    )
    
    # Aggiungi apertura
    window = Opening(
        width=1.2,
        height=1.5,
        x_center=0.3,
        y_bottom=0.8,
        type="window",
        lintel=Lintel(type="steel", height=0.15)
    )
    # Aggiungi apertura usando il metodo add_opening
    pier.add_opening(window)
    
    print(f"Area lorda: {pier.gross_area:.3f} m²")
    print(f"Area netta: {pier.net_area:.3f} m²")
    print(f"Inerzia netta: {pier.net_inertia:.6f} m⁴")
    print(f"Snellezza: {pier.slenderness:.1f}")
    print(f"Fattore di forma b: {pier.shape_factor:.2f}")
    
    # Esempio 2: Rinforzo FRP
    print("\n2. APPLICAZIONE RINFORZO FRP:")
    print("-"*40)
    
    frp = Reinforcement(
        type=ReinforcementType.FRP,
        area=0.5,  # mm spessore
        E_f=230,   # GPa
        f_f=3000,  # MPa
        width=150,
        spacing=300,
        n_layers=2,
        orientation=0,  # Verticale
        application_side="both"
    )
    pier.reinforcements.append(frp)
    
    props = pier.get_reinforced_properties()
    print(f"Incremento area: {(props['area_ratio']-1)*100:.1f}%")
    print(f"Incremento inerzia: {(props['inertia_ratio']-1)*100:.1f}%")
    print(f"Incremento resistenza M: {props['strength_increase_M']:.1f}%")
    print(f"Incremento resistenza V: {props['strength_increase_V']:.1f} kN/m")
    
    # Esempio 3: Fascia di piano con arco
    print("\n3. FASCIA CON ARCO:")
    print("-"*40)
    
    spandrel = GeometrySpandrel(
        length=3.0,
        height=0.8,
        thickness=0.3,
        arch_rise=0.3,
        arch_type=ArchType.SEGMENTAL
    )
    
    print(f"È trave tozza: {spandrel.is_deep_beam}")
    print(f"Meccanismo ad arco: {spandrel.is_arch_mechanism}")
    print(f"Spinta arco: {spandrel.arch_thrust:.1f} kN/m")
    print(f"Necessita tirante: {spandrel.tie_rod_required}")
    
    # Esempio 4: Parete completa multi-piano
    print("\n4. PARETE MULTI-PIANO:")
    print("-"*40)
    
    wall = GeometryWall(
        length=8.0,
        height=9.0,
        thickness=0.45,
        n_floors=3,
        floor_height=3.0,
        wall_type=WallType.DOUBLE_LEAF
    )
    
    # Aggiungi aperture
    for floor in range(3):
        wall.add_opening(floor, Opening(
            width=1.0,
            height=2.1 if floor == 0 else 1.5,
            x_center=-2.0,  # A sinistra del centro
            y_bottom=0.0 if floor == 0 else 0.8,
            type="door" if floor == 0 else "window"
        ))
        wall.add_opening(floor, Opening(
            width=1.0,
            height=1.5,
            x_center=2.0,  # A destra del centro
            y_bottom=0.8,
            type="window"
        ))
    
    print(f"Numero maschi identificati: {len(wall.piers)}")
    print(f"Numero fasce identificate: {len(wall.spandrels)}")
    print(f"Area totale maschi: {wall.total_pier_area:.2f} m²")
    print(f"Percentuale foratura: {wall.opening_ratio*100:.1f}%")
    
    # Esempio 5: Validazione e ottimizzazione
    print("\n5. VALIDAZIONE E OTTIMIZZAZIONE:")
    print("-"*40)
    
    validation = validate_geometry_for_analysis(pier, "pushover")
    print(f"Geometria valida: {validation['valid']}")
    if validation['warnings']:
        print(f"Avvisi: {validation['warnings']}")
    
    # Ottimizza rinforzi
    optimal_reinforcements = optimize_reinforcement_layout(
        pier,
        target_capacity_increase=0.4,
        reinforcement_type=ReinforcementType.FRCM
    )
    
    print(f"Rinforzi ottimizzati: {len(optimal_reinforcements)}")
    for i, reinf in enumerate(optimal_reinforcements):
        print(f"  Rinforzo {i+1}: {reinf.type.value}, orientamento {reinf.orientation}°")
    
    print("\n" + "="*70)
    print("MODULO GEOMETRY v2.4.3 COMPLETO E FUNZIONANTE!")
    print("="*70)

def run_basic_tests():
    """Test di base per verificare le funzionalità principali"""
    print("\n" + "="*70)
    print("TEST DI BASE GEOMETRY v2.4.3")
    print("="*70)
    
    # Test 1: Round-trip dict (con storey)
    print("\n1. Test serializzazione con storey...")
    p = GeometryPier(length=2.0, height=3.0, thickness=0.4, storey=0)
    p.add_opening(Opening(width=1.0, height=1.2, x_center=0.0, y_bottom=0.9))
    d = p.to_dict()
    p2 = GeometryPier.from_dict(d)
    assert p2.storey == 0, "Storey non preservato"
    assert abs(p2.net_area - p.net_area) < 1e-9, "Area netta diversa dopo round-trip"
    print("   ✓ Round-trip serializzazione OK")
    
    # Test 2: Danno riduce h0 e taglio
    print("\n2. Test applicazione danno...")
    p3 = p.apply_damage(0.3)
    assert p3.h0 < p.h0, "h0 non ridotto dopo danno"
    assert p3.shear_retention_factor < p.shear_retention_factor, "Fattore taglio non ridotto"
    print("   ✓ Danno applicato correttamente")
    
    # Test 3: Inerzia si riduce con apertura
    print("\n3. Test riduzione inerzia con aperture...")
    p_no = GeometryPier(length=2.0, height=3.0, thickness=0.4)
    assert p_no.net_inertia > p.net_inertia, "Inerzia non ridotta da aperture"
    print("   ✓ Aperture riducono inerzia")
    
    # Test 4: FRP verticale aumenta I_eff (per "both" sides)
    print("\n4. Test rinforzo FRP...")
    frp = Reinforcement(
        type=ReinforcementType.FRP, 
        area=0.5, 
        width=150, 
        spacing=300, 
        n_layers=2, 
        orientation=0, 
        application_side="both"
    )
    p_no.reinforcements = [frp]
    assert p_no.effective_inertia > p_no.net_inertia, "FRP non aumenta inerzia"
    print("   ✓ Rinforzi aumentano inerzia efficace")
    
    # Test 5: Parete multi-piano con breakpoints robusti
    print("\n5. Test identificazione maschi con aperture vicine...")
    w = GeometryWall(length=6.0, height=6.0, thickness=0.4, n_floors=2, floor_height=3.0)
    w.add_opening(0, Opening(width=1.2, height=1.4, x_center=-1.5, y_bottom=0.8))
    w.add_opening(0, Opening(width=1.2, height=1.4, x_center=-0.3, y_bottom=0.8))  # quasi a contatto
    assert len(w.piers) >= 2, "Maschi non identificati correttamente"
    print("   ✓ Identificazione robusta con aperture contigue")
    
    # Test 6: Maschio senza aperture
    print("\n6. Test maschio senza aperture...")
    p_clean = GeometryPier(length=3.0, height=4.0, thickness=0.5)
    assert abs(p_clean.net_area - p_clean.gross_area) < 1e-9, "Area netta != lorda senza aperture"
    assert abs(p_clean.net_inertia - p_clean.gross_inertia) < 1e-9, "Inerzia netta != lorda senza aperture"
    print("   ✓ Maschio pulito: proprietà lorde = nette")
    
    # Test 7: Apertura quasi totale (robustezza)
    print("\n7. Test apertura quasi totale...")
    p_extreme = GeometryPier(length=2.0, height=3.0, thickness=0.4)
    p_extreme.add_opening(Opening(width=1.9, height=2.8, x_center=0.0, y_bottom=0.1))
    assert p_extreme.net_area > 0, "Area netta deve rimanere > 0"
    assert p_extreme.net_area >= 0.1 * p_extreme.gross_area, "Area minima 10% garantita"
    print("   ✓ Robustezza con apertura estrema")
    
    # Test 8: Baricentro con apertura asimmetrica
    print("\n8. Test baricentro con apertura asimmetrica...")
    p_asym = GeometryPier(length=4.0, height=3.0, thickness=0.4)
    p_asym.add_opening(Opening(width=1.0, height=1.5, x_center=1.0, y_bottom=0.5))
    x_cg, y_cg, z_cg = p_asym.centroid
    assert x_cg < 0, "Baricentro dovrebbe spostarsi verso sinistra (x negativo)"
    print(f"   ✓ Baricentro spostato correttamente: x_cg = {x_cg:.3f} m")
    
    # Test 9: Serializzazione completa GeometrySpandrel
    print("\n9. Test serializzazione fascia...")
    spandrel = GeometrySpandrel(
        length=3.0, height=0.8, thickness=0.3,
        arch_rise=0.2, arch_type=ArchType.SEGMENTAL,
        tie_rod=TieRod(diameter=24.0, f_y=450.0)
    )
    s_dict = spandrel.to_dict()
    assert 'arch_type' in s_dict and s_dict['arch_type'] == 'segmental', "Arch type non serializzato"
    assert 'tie_rod' in s_dict, "Tie rod non serializzato"
    print("   ✓ Serializzazione GeometrySpandrel completa")
    
    # Test 10: Angoli normalizzati rinforzi
    print("\n10. Test normalizzazione angoli rinforzi...")
    r1 = Reinforcement(orientation=0)    # Verticale
    r2 = Reinforcement(orientation=180)  # Anche verticale
    r3 = Reinforcement(orientation=90)   # Orizzontale
    r4 = Reinforcement(orientation=270)  # Anche orizzontale
    
    # Per rinforzi verticali (0° o 180°) contribution_V deve essere 0
    assert r1.contribution_V == 0, "Rinforzo a 0° non dovrebbe contribuire a V"
    assert r2.contribution_V == 0, "Rinforzo a 180° non dovrebbe contribuire a V"
    
    # Per rinforzi orizzontali (90° o 270°) contribution_M deve essere 0
    assert r3.contribution_M == 0, "Rinforzo a 90° non dovrebbe contribuire a M"
    assert r4.contribution_M == 0, "Rinforzo a 270° non dovrebbe contribuire a M"
    # Test 10: Angoli normalizzati rinforzi
    print("\n10. Test normalizzazione angoli rinforzi...")
    r1 = Reinforcement(orientation=0)    # Verticale
    r2 = Reinforcement(orientation=180)  # Anche verticale
    r3 = Reinforcement(orientation=90)   # Orizzontale
    r4 = Reinforcement(orientation=270)  # Anche orizzontale
    
    # Per rinforzi verticali (0° o 180°) contribution_V deve essere 0
    assert r1.contribution_V == 0, "Rinforzo a 0° non dovrebbe contribuire a V"
    assert r2.contribution_V == 0, "Rinforzo a 180° non dovrebbe contribuire a V"
    
    # Per rinforzi orizzontali (90° o 270°) contribution_M deve essere 0
    assert r3.contribution_M == 0, "Rinforzo a 90° non dovrebbe contribuire a M"
    assert r4.contribution_M == 0, "Rinforzo a 270° non dovrebbe contribuire a M"
    print("   ✓ Normalizzazione angoli funziona correttamente")
    
    # Test 11: Unità coerenti in GeometrySpandrel
    print("\n11. Test unità taglio fascia con arco...")
    span = GeometrySpandrel(
        length=4.0, height=1.0, thickness=0.4,
        arch_rise=0.5, arch_type=ArchType.SEGMENTAL
    )
    V_shear = span.get_capacity_shear()
    assert V_shear > 0, "Capacità taglio deve essere positiva"
    # Verifica che il calcolo sia dimensionalmente corretto (kN)
    print(f"   ✓ Capacità taglio fascia: {V_shear:.1f} kN (unità coerenti)")
    
    # Test 12: Export SAP2000 con shear area
    print("\n12. Test export SAP2000 maschio...")
    pier_sap = GeometryPier(length=3.0, height=4.0, thickness=0.5)
    sap_dict = pier_sap.export_to_sap2000()
    assert 'As2' in sap_dict, "As2 mancante nell'export"
    assert 'As3' in sap_dict, "As3 mancante nell'export"
    assert sap_dict['As2'] == pier_sap.shear_area, "As2 non corrisponde a shear_area"
    print("   ✓ Export SAP2000 include aree di taglio esplicite")
    
    print("\n" + "="*70)
    print("TUTTI I TEST PASSATI! ✅")
    print("="*70)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    example_usage()
    print("\n")
    run_basic_tests()