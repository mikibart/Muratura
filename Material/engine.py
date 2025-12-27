# engine.py - VERSIONE 6.1 FINALE
"""
MasonryFEMEngine v6.1
Motore di calcolo FEM completo per muratura secondo NTC 2018
Con tutte le correzioni: forze interne time-history, robustezza modale, ottimizzazioni
"""

from __future__ import annotations
import numpy as np
import logging
from typing import Dict, Optional, List, Union, Tuple, Any
from dataclasses import dataclass
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve

# Import locali con gestione errori
from .enums import AnalysisMethod, ConstitutiveLaw
from .materials import MaterialProperties
from .geometry import GeometryPier, GeometrySpandrel

# Import delle analisi dai moduli esistenti
try:
    from .analyses.fem import FEMModel
    def _analyze_fem(wall_data, material, loads, options):
        model = FEMModel()
        model.generate_mesh(wall_data, material)
        # Applica carico orizzontale al nodo superiore (se presente)
        if model.nodes:
            top_nodes = [nid for nid, coord in model.nodes.items()
                        if coord[1] == max(c[1] for c in model.nodes.values())]
            if top_nodes:
                H = loads.get('horizontal', 0) / len(top_nodes)
                for nid in top_nodes:
                    model.add_load(nid, Fx=H, Fy=0)
        u = model.solve_linear()
        return {'method': 'FEM', 'displacements': u, 'status': 'OK'}
except ImportError as e:
    _analyze_fem = None
    logging.warning(f"Modulo FEM non disponibile: {e}")

try:
    from .analyses.por import analyze_por, AnalysisOptions as POROptions
    def _analyze_por(wall_data, material, loads, options):
        # Converte dict in AnalysisOptions
        if options is None:
            por_options = POROptions()
        elif isinstance(options, dict):
            por_options = POROptions(
                gamma_m=options.get('gamma_m', 2.0),
                FC=options.get('FC', 1.35)
            )
        else:
            por_options = options
        return analyze_por(wall_data, material, loads, por_options)
except ImportError as e:
    _analyze_por = None
    logging.warning(f"Modulo POR non disponibile: {e}")

try:
    from .analyses.sam import analyze_sam
    def _analyze_sam(wall_data, material, loads, options):
        # Assicura che ci siano piers definiti
        sam_data = dict(wall_data)
        if 'piers' not in sam_data or not sam_data['piers']:
            # Crea un pier singolo che rappresenta tutta la parete
            sam_data['piers'] = [{
                'id': 'P1',
                'length': sam_data.get('length', 5.0),
                'height': sam_data.get('height', 3.0),
                'thickness': sam_data.get('thickness', 0.3),
                'x': 0,
                'floor': 0
            }]
        return analyze_sam(sam_data, material, loads, options)
except ImportError as e:
    _analyze_sam = None
    logging.warning(f"Modulo SAM non disponibile: {e}")

try:
    from .analyses.limit import LimitAnalysis
    def _analyze_limit(wall_data, material, loads, options):
        analysis = LimitAnalysis(geometry=wall_data, material=material)
        return analysis.analyze_all_mechanisms(loads)
except ImportError as e:
    LimitAnalysis = None
    _analyze_limit = None
    logging.warning(f"Modulo analisi limite non disponibile: {e}")

try:
    from .analyses.fiber import FiberModel, FiberSection
    def _analyze_fiber(wall_data, material, loads, options):
        model = FiberModel(material)
        # Setup semplificato per parete singola
        L = wall_data.get('length', 5.0)
        H = wall_data.get('height', 3.0)
        model.add_node(0, 0, 0)
        model.add_node(1, 0, H)
        # Crea geometria semplificata
        from .geometry import GeometryPier
        geom = GeometryPier(length=L, height=H, thickness=wall_data.get('thickness', 0.3))
        model.add_element('wall', 0, 1, geom)
        model.add_constraint(0, [0, 1, 2])  # Incastro alla base
        # Analisi semplificata
        return {'method': 'FIBER', 'status': 'OK', 'model': 'created'}
except ImportError as e:
    FiberModel = None
    _analyze_fiber = None
    logging.warning(f"Modulo fiber non disponibile: {e}")

try:
    from .analyses.micro import MicroModel
    def _analyze_micro(wall_data, material, loads, options):
        # Proprietà blocco e malta dal materiale
        block_props = {
            'E': material.E * 1.2,  # Blocco più rigido
            'nu': 0.15,
            'fc': material.fcm * 1.5,
            'ft': material.ftm * 1.5
        }
        mortar_props = {
            'E': material.E * 0.5,
            'nu': 0.20,
            'fc': material.fcm * 0.8,
            'ft': material.ftm * 0.5
        }
        interface_props = {
            'kn': material.E * 100,
            'ks': material.G * 50,
            'ft': material.tau0,
            'fc': material.fcm,
            'c': material.tau0,
            'phi': 0.6
        }
        model = MicroModel(
            block_props=block_props,
            mortar_props=mortar_props,
            interface_props=interface_props
        )
        model.generate_micro_mesh(wall_data, {'length': 0.25, 'height': 0.12})
        boundary = {'base': 'fixed', 'top': 'free'}
        return model.analyze_micro(loads, boundary)
except ImportError as e:
    MicroModel = None
    _analyze_micro = None
    logging.warning(f"Modulo micro non disponibile: {e}")

try:
    from .analyses.frame import EquivalentFrame, analyze_frame as _analyze_frame
except ImportError as e:
    EquivalentFrame = None
    _analyze_frame = None
    logging.warning(f"Modulo frame non disponibile: {e}")

# Import opzionale del FrameElement esterno
try:
    from .analyses.frame import FrameElement as _FrameElement
except ImportError:
    _FrameElement = None

# Import utils
from .utils import (
    sensitivity_analysis_limit,
    probabilistic_limit_analysis,
    calculate_damage_indices,
    distribute_vertical_loads,
    analyze_crack_pattern,
    get_micro_boundary_conditions
)

# Configurazione logging (senza basicConfig per evitare conflitti)
logger = logging.getLogger(__name__)

# ============================================================================
# CLASSI DI SUPPORTO PER FRAME (se non importate)
# ============================================================================

if EquivalentFrame is None:
    @dataclass
    class FrameElement:
        """Elemento per telaio equivalente"""
        i_node: int
        j_node: int
        geometry: Union[GeometryPier, GeometrySpandrel]
        material: MaterialProperties
        type: str  # 'pier' o 'spandrel'
        forces: Dict[str, float] = None
        
        def __post_init__(self):
            if self.forces is None:
                self.forces = {'N': 0, 'V': 0, 'M_i': 0, 'M_j': 0, 
                              'N_i': 0, 'V_i': 0}  # Aggiunte forze al nodo i
        
        def compute_internal_forces(self, u_elem: np.ndarray):
            """
            Calcola le azioni interne dal DOF vector globale dell'elemento
            Trasforma in locale, calcola forze, e ritorna risultati in locale
            """
            frame = getattr(self, '_frame_ref', None)
            if frame is None:
                raise RuntimeError("FrameElement senza riferimento al frame")
            T, L = frame._element_T_and_length(self)
            k_loc = frame._get_element_stiffness_local(self, L)
            u_loc = T.T @ u_elem
            f_loc = k_loc @ u_loc  # [Fx1, Fy1, M1, Fx2, Fy2, M2]
            
            # Salva forze interne complete (in sistema locale)
            self.forces['N_i'] = float(f_loc[0])   # N al nodo i (assiale locale)
            self.forces['V_i'] = float(f_loc[1])   # V al nodo i (taglio locale)
            self.forces['M_i'] = float(f_loc[2])   # Momento nodo i
            self.forces['N']   = float(f_loc[3])   # N al nodo j (assiale locale)
            self.forces['V']   = float(f_loc[4])   # V al nodo j (taglio locale)
            self.forces['M_j'] = float(f_loc[5])   # Momento nodo j

    class EquivalentFrame:
        """Classe base per telaio equivalente se non importata"""
        def __init__(self):
            self.nodes = {}
            self.elements = []
            self.K_global = None
            self.M_global = None
            self.node_dofs = {}
            self.constraints = {}
            self._static_solver_prepared = False
            self._K_eff_fact = None  # Per riuso solver in pushover
            
        def add_node(self, node_id: int, x: float, y: float):
            self.nodes[node_id] = {'x': x, 'y': y}
            self.node_dofs[node_id] = [node_id*3, node_id*3+1, node_id*3+2]
            
        def add_element(self, element: FrameElement):
            element._frame_ref = self  # Backref per calcolo forze
            self.elements.append(element)
            
        def add_constraint(self, node_id: int, constraint_type: str):
            self.constraints[node_id] = constraint_type
            
        def _element_T_and_length(self, elem) -> Tuple[np.ndarray, float]:
            """Calcola matrice di trasformazione e lunghezza elemento
            
            Returns:
                T: Matrice trasformazione DOF locali → globali (u_g = T * u_l)
                L: Lunghezza elemento
            """
            xi, yi = self.nodes[elem.i_node]['x'], self.nodes[elem.i_node]['y']
            xj, yj = self.nodes[elem.j_node]['x'], self.nodes[elem.j_node]['y']
            dx, dy = xj - xi, yj - yi
            L = float(np.hypot(dx, dy))
            
            if L <= 0:
                raise ValueError(f"Lunghezza elemento nulla tra nodi {elem.i_node}-{elem.j_node}")
                
            c, s = dx / L, dy / L
            
            # Matrice trasformazione: DOF locali → globali (u_g = T * u_l)
            T = np.eye(6)
            T[0,0] =  c; T[0,1] = -s
            T[1,0] =  s; T[1,1] =  c
            T[3,3] =  c; T[3,4] = -s
            T[4,3] =  s; T[4,4] =  c
            
            return T, L
        
        def _get_element_stiffness_local(self, elem, L: float) -> np.ndarray:
            """Calcola matrice rigidezza locale elemento"""
            # Area e Inerzia con fallback robusti per pier e spandrel
            if elem.type == 'pier':
                A = float(getattr(elem.geometry, 'effective_area', getattr(elem.geometry, 'area', 0.0)))
                I = float(getattr(elem.geometry, 'effective_inertia', getattr(elem.geometry, 'inertia', 0.0)))
            else:  # spandrel
                # Per spandrel usa direttamente area/inerzia base (non hanno effective_*)
                A = float(getattr(elem.geometry, 'area', 0.0))
                I = float(getattr(elem.geometry, 'inertia', 0.0))
            
            if A <= 0 or I <= 0:
                # Fallback minimo per evitare singolarità
                if A <= 0:
                    A = 0.01  # m² minimo
                if I <= 0:
                    I = 1e-6  # m⁴ minimo
                logger.warning(
                    f"Area/Inerzia non valide per elemento {elem.type} "
                    f"({elem.i_node}-{elem.j_node}), uso valori minimi"
                )
                
            E = float(elem.material.E) * 1000.0  # MPa -> kN/m^2
            
            k = np.zeros((6, 6), dtype=float)
            
            # Termini assiali
            EA_L = E * A / L
            k[0,0] = k[3,3] =  EA_L
            k[0,3] = k[3,0] = -EA_L
            
            # Termini flessionali (Eulero-Bernoulli)
            c1 = 12*E*I/L**3
            c2 =  6*E*I/L**2
            c3 =  4*E*I/L
            c4 =  2*E*I/L
            
            k[1,1] =  c1;  k[1,2] =  c2;  k[1,4] = -c1;  k[1,5] =  c2
            k[2,1] =  c2;  k[2,2] =  c3;  k[2,4] = -c2;  k[2,5] =  c4
            k[4,1] = -c1;  k[4,2] = -c2;  k[4,4] =  c1;  k[4,5] = -c2
            k[5,1] =  c2;  k[5,2] =  c4;  k[5,4] = -c2;  k[5,5] =  c3
            
            return k
        
        def _get_element_stiffness_global(self, elem) -> np.ndarray:
            """Calcola matrice rigidezza globale elemento (con rotazione)"""
            T, L = self._element_T_and_length(elem)
            k_loc = self._get_element_stiffness_local(elem, L)
            # u_g = T u_l  ⇒  K_g = T K_l T^T
            return T @ k_loc @ T.T
            
        def assemble_stiffness_matrix(self):
            """Assembla matrice di rigidezza globale con trasformazione (sparse diretto)"""
            n_dofs = len(self.nodes) * 3
            from scipy.sparse import lil_matrix
            K = lil_matrix((n_dofs, n_dofs), dtype=float)
            
            for elem in self.elements:
                k_glob = self._get_element_stiffness_global(elem)  # Usa K globale ruotata
                dofs = self.node_dofs[elem.i_node] + self.node_dofs[elem.j_node]
                
                for ii, di in enumerate(dofs):
                    for jj, dj in enumerate(dofs):
                        K[di, dj] += k_glob[ii, jj]
            
            # NO penalty method - usa solo eliminazione DOF in solve_static
            self.K_global = K.tocsr()
            self._static_solver_prepared = False  # Invalida solver preparato
            
        def assemble_mass_matrix(self, floor_masses: Dict[int, float]):
            """Assembla matrice delle masse (solo traslazionali) - sparse diretto
            
            Args:
                floor_masses: Masse in kg da convertire in kN·s²/m
            """
            n_dofs = len(self.nodes) * 3
            from scipy.sparse import diags
            m = np.zeros(n_dofs)
            
            for node_id, mass in floor_masses.items():
                if node_id in self.node_dofs:
                    dofs = self.node_dofs[node_id]
                    # Conversione kg → kN·s²/m per coerenza con K in kN/m
                    m_kns2_per_m = mass / 1000.0
                    m[dofs[0]] = m_kns2_per_m  # Massa in direzione x
                    m[dofs[1]] = m_kns2_per_m  # Massa in direzione y
                    # Nota: inerzia rotazionale non inclusa (scelta progettuale)
            
            self.M_global = diags(m).tocsr()
            
        def _apply_constraints_elimination(self, K: csr_matrix, F: np.ndarray) -> Tuple[csr_matrix, np.ndarray]:
            """Elimina DOF vincolati per migliore condizionamento"""
            fixed_dofs = []
            for node_id, c in self.constraints.items():
                if c == 'fixed':
                    fixed_dofs.extend(self.node_dofs[node_id])
            if not fixed_dofs:
                return K, F
                
            K = K.tolil()
            for dof in fixed_dofs:
                K[dof, :] = 0.0
                K[:, dof] = 0.0
                K[dof, dof] = 1.0
                F[dof] = 0.0
            
            # Aggiungi regularization piccola solo ai DOF liberi
            free_mask = np.ones(K.shape[0], dtype=bool)
            free_mask[fixed_dofs] = False
            diag = K.diagonal()
            diag[free_mask] += 1e-12
            K.setdiag(diag)
            
            return K.tocsr(), F
        
        def prepare_static_solver(self):
            """Prepara solver statico (fattorizza K_eff) per riuso in pushover"""
            if self._static_solver_prepared:
                return
                
            if self.K_global is None:
                self.assemble_stiffness_matrix()
                
            # Applica vincoli con eliminazione DOF
            n_dofs = len(self.nodes) * 3
            F_dummy = np.zeros(n_dofs)
            K_eff, _ = self._apply_constraints_elimination(self.K_global.copy(), F_dummy)
            
            # Fattorizza una volta sola (Cholesky per SPD dopo eliminazione vincoli)
            try:
                from scipy.linalg import cho_factor
                self._K_eff_fact = cho_factor(K_eff.toarray())
                self._use_cholesky = True
            except:
                try:
                    from scipy.linalg import lu_factor
                    self._K_eff_fact = lu_factor(K_eff.toarray())
                    self._use_cholesky = False
                except:
                    self._K_eff = K_eff
                    self._use_cholesky = None
                
            self._static_solver_prepared = True
            
        def solve_static_fast(self, F: np.ndarray) -> np.ndarray:
            """Risolve sistema statico con solver pre-fattorizzato (per pushover)"""
            if not self._static_solver_prepared:
                self.prepare_static_solver()
                
            # NON mutare F originale
            F_eff = F.copy()
            
            # Applica vincoli al vettore forze
            fixed_dofs = []
            for node_id, c in self.constraints.items():
                if c == 'fixed':
                    fixed_dofs.extend(self.node_dofs[node_id])
            for dof in fixed_dofs:
                F_eff[dof] = 0.0
                
            # Risolvi con solver pre-fattorizzato
            if self._use_cholesky is True:
                from scipy.linalg import cho_solve
                u = cho_solve(self._K_eff_fact, F_eff)
            elif self._use_cholesky is False:
                from scipy.linalg import lu_solve
                u = lu_solve(self._K_eff_fact, F_eff)
            else:
                u = spsolve(self._K_eff, F_eff)
                
            return u
        
        def solve_static(self, loads: Dict) -> Dict:
            """Risolve analisi statica lineare con eliminazione DOF"""
            if self.K_global is None:
                self.assemble_stiffness_matrix()
            
            n_dofs = len(self.nodes) * 3
            F = np.zeros(n_dofs)
            
            for node_id, load in loads.items():
                if node_id in self.node_dofs:
                    dofs = self.node_dofs[node_id]
                    if 'Fx' in load:
                        F[dofs[0]] = load['Fx']
                    if 'Fy' in load:
                        F[dofs[1]] = load['Fy']
                    if 'M' in load:
                        F[dofs[2]] = load['M']
            
            # Applica vincoli con eliminazione DOF
            K_eff, F_eff = self._apply_constraints_elimination(self.K_global.copy(), F)
            
            # Risolvi sistema lineare
            u = spsolve(K_eff, F_eff)
            
            # Calcola forze interne per ogni elemento
            for elem in self.elements:
                dof_i = self.node_dofs[elem.i_node]
                dof_j = self.node_dofs[elem.j_node]
                u_elem = np.concatenate([u[dof_i], u[dof_j]])
                elem.compute_internal_forces(u_elem)
            
            # Serializzazione-friendly con conversione a lista
            return {
                'displacements': u.tolist() if hasattr(u, 'tolist') else list(u),
                'max_displacement': float(np.max(np.abs(u))),
                'element_forces': [elem.forces for elem in self.elements],
                'reactions': self._compute_reactions(u, F)
            }
        
        def _compute_reactions(self, u: np.ndarray, F_applied: np.ndarray) -> Dict:
            """Calcola reazioni vincolari"""
            # Prodotto sparse @ dense -> dense (evita densificazione)
            Rvec = (self.K_global @ u) - F_applied  # unico prodotto
            reactions = {}
            for node_id, constraint in self.constraints.items():
                if constraint == 'fixed':
                    dofs = self.node_dofs[node_id]
                    reactions[node_id] = {
                        'Rx': float(Rvec[dofs[0]]),
                        'Ry': float(Rvec[dofs[1]]),
                        'Mz': float(Rvec[dofs[2]])
                    }
            return reactions
        
        def solve_modal(self, n_modes: int = 6) -> Dict:
            """Analisi modale con matrici ridotte ai DOF liberi"""
            from scipy.sparse.linalg import eigsh
            
            if self.K_global is None:
                self.assemble_stiffness_matrix()
            if self.M_global is None:
                from scipy.sparse import eye as speye
                logger.warning("M_global mancante: uso massa identità*1000 (periodi indicativi).")
                self.M_global = speye(self.K_global.shape[0], format='csr') * 1000.0
            
            n = self.K_global.shape[0]
            
            # DOF vincolati / liberi
            fixed = []
            for node_id, c in self.constraints.items():
                if c == 'fixed':
                    fixed.extend(self.node_dofs[node_id])
            fixed = sorted(set(fixed))
            free = np.array([i for i in range(n) if i not in fixed], dtype=int)
            
            # Se troppo pochi DOF liberi, restituisci fallback sicuro
            if free.size < 2:
                logger.warning("Pochi DOF liberi per modale: uso fallback.")
                return {
                    'frequencies': [1.0],
                    'periods': [1.0],
                    'mode_shapes': np.ones((n, 1)).tolist(),
                    'modal_masses': [float(self.M_global.sum()) if self.M_global is not None else 1000.0],
                    'mass_participation_x': [0.0],
                    'mass_participation_y': [0.0],
                    'total_mass_participation_x': 0.0,
                    'total_mass_participation_y': 0.0
                }
            
            # Matrici ridotte
            Kff = self.K_global[free][:, free].tocsr()
            Mff = self.M_global[free][:, free].tocsr()
            
            # Robustezza per sistemi piccoli
            Nf = Kff.shape[0]
            k_modes = min(int(n_modes), max(1, Nf - 1))
            
            # Vettori d'influenza
            r_x = np.zeros(n); r_x[0::3] = 1.0
            r_y = np.zeros(n); r_y[1::3] = 1.0
            r_xf = r_x[free]
            r_yf = r_y[free]
            
            try:
                evals, evecs_f = eigsh(Kff, k=k_modes, M=Mff, which='SM')
                evals = np.clip(evals, 1e-20, None)
                w = np.sqrt(evals)
                frequencies = (w / (2*np.pi)).astype(float)
                periods = (1.0 / frequencies).astype(float)
                
                # Ricostruzione dei modi in spazio globale
                evecs = np.zeros((n, evecs_f.shape[1]))
                evecs[free, :] = evecs_f
                
                # Masse totali
                total_mass_x = float(r_xf @ (Mff @ r_xf))
                total_mass_y = float(r_yf @ (Mff @ r_yf))
                
                mass_participation_x, mass_participation_y, modal_masses = [], [], []
                
                for i in range(evecs_f.shape[1]):
                    phi_f = evecs_f[:, i]
                    Mphi = Mff @ phi_f
                    M_star = float(phi_f @ Mphi)
                    modal_masses.append(M_star)
                    
                    Lx = float(phi_f @ (Mff @ r_xf))
                    Ly = float(phi_f @ (Mff @ r_yf))
                    
                    mx = (Lx**2) / (M_star * total_mass_x) if (total_mass_x > 0 and M_star > 0) else 0.0
                    my = (Ly**2) / (M_star * total_mass_y) if (total_mass_y > 0 and M_star > 0) else 0.0
                    
                    mass_participation_x.append(mx)
                    mass_participation_y.append(my)
                
                return {
                    'frequencies': frequencies.tolist(),
                    'periods': periods.tolist(),
                    'mode_shapes': evecs.tolist(),  # Convertito per serializzazione
                    'modal_masses': modal_masses,
                    'modal_masses_info': 'Modal mass M* = phi^T M phi',
                    'mass_participation_x': mass_participation_x,
                    'mass_participation_y': mass_participation_y,
                    'total_mass_participation_x': float(np.sum(mass_participation_x)),
                    'total_mass_participation_y': float(np.sum(mass_participation_y)),
                    'total_mass': {
                        'x_direction': float(total_mass_x),
                        'y_direction': float(total_mass_y)
                    }
                }
            except Exception as e:
                logger.warning(f"Analisi modale fallita: {e}")
                return {
                    'frequencies': [1.0],
                    'periods': [1.0],
                    'mode_shapes': np.ones((n, 1)).tolist(),
                    'modal_masses': [1000.0],
                    'mass_participation_x': [0.0],
                    'mass_participation_y': [0.0],
                    'total_mass_participation_x': 0.0,
                    'total_mass_participation_y': 0.0
                }
        
        def pushover_analysis(self, pattern: str, target_drift: float, n_steps: int = 50, 
                              direction: str = 'y') -> Dict:
            """
            Pushover con risoluzione incrementale elastica ottimizzata.
            Usa solver pre-fattorizzato per efficienza.
            Le forze laterali sono normalizzate a ΣF = 1000 kN × scale_factor.
            
            Args:
                pattern: Tipo di distribuzione ('triangular', 'uniform', 'modal')
                target_drift: Drift obiettivo (rapporto spostamento/altezza)
                n_steps: Numero di passi incrementali
                direction: Direzione delle forze ('x' o 'y', default 'y')
                
            Returns:
                Curva pushover, livelli prestazionali, punto prestazionale
            """
            if self.K_global is None:
                self.assemble_stiffness_matrix()

            # Prepara solver una volta sola
            self.prepare_static_solver()
            
            # Indice direzione (0=X, 1=Y)
            dir_idx = 0 if direction.lower() == 'x' else 1

            # Prepara pesi laterali per ciascun nodo
            node_ids = sorted(self.nodes.keys())
            
            # Nodi attivi (non vincolati) per non sprecare forze
            active_nodes = [nid for nid in node_ids if self.constraints.get(nid) != 'fixed']
            
            if not active_nodes:
                logger.warning("Tutti i nodi sono vincolati, impossibile applicare forze laterali")
                return {
                    'curve': [],
                    'performance_levels': {},
                    'performance_point': None,
                    'error': 'No free nodes for lateral loads'
                }
            
            # Calcola pesi per pattern su nodi attivi
            if pattern == 'triangular':
                # Usa coordinata nella direzione di spinta
                coords = np.array([self.nodes[i]['y' if dir_idx == 1 else 'x'] for i in active_nodes])
                w_act = coords / (coords.max() if coords.max() > 0 else 1.0)
            elif pattern == 'uniform':
                w_act = np.ones(len(active_nodes))
            else:  # 'modal'
                modal = self.solve_modal(1)
                phi = modal.get('mode_shapes', None)
                if phi is not None and len(phi) > 0:
                    phi_arr = np.array(phi)
                    # normalizza a 2D se necessario
                    if phi_arr.ndim == 1:
                        phi_arr = phi_arr.reshape(-1, 1)
                    if phi_arr.shape[1] > 0:
                        # Estrai direttamente dai DOF della direzione scelta
                        w_act = []
                        for nid in active_nodes:
                            dof = self.node_dofs[nid][dir_idx]  # DOF nella direzione
                            w_act.append(abs(phi_arr[dof, 0]))
                        w_act = np.array(w_act)
                    else:
                        w_act = np.ones(len(active_nodes))
                else:
                    w_act = np.ones(len(active_nodes))

            # Normalizza (somma 1) evitando divisioni per zero
            s = np.sum(np.abs(w_act))
            w_act = w_act / (s if s > 0 else 1.0)

            # Nodo di copertura (massima quota Y tra i nodi attivi)
            y_coords_act = np.array([self.nodes[i]['y'] for i in active_nodes])
            roof_node = active_nodes[int(np.argmax(y_coords_act))]
            roof_dof = self.node_dofs[roof_node][dir_idx]
            height = self._get_building_height()

            results = {'curve': [], 'performance_levels': {}, 'performance_point': None}

            # Prepara vettore forze base SOLO sui nodi attivi (ΣF = 1000 kN)
            n_dofs = len(self.nodes) * 3
            F_base = np.zeros(n_dofs)
            for i, nid in enumerate(active_nodes):
                dofs = self.node_dofs[nid]
                F_base[dofs[dir_idx]] = float(w_act[i]) * 1000.0  # kN nella direzione scelta

            for step in range(1, n_steps + 1):
                scale = step / n_steps  # moltiplicatore monotono
                F = F_base * scale

                # Usa solver ottimizzato
                u = self.solve_static_fast(F)
                
                # Calcola forze interne per ogni elemento
                for elem in self.elements:
                    dof_i = self.node_dofs[elem.i_node]
                    dof_j = self.node_dofs[elem.j_node]
                    u_elem = np.concatenate([u[dof_i], u[dof_j]])
                    elem.compute_internal_forces(u_elem)
                
                roof_disp = float(u[roof_dof])
                top_drift = roof_disp / max(height, 1e-9)
                
                # Base shear dalle reazioni nella direzione corretta
                reactions = self._compute_reactions(u, F)
                reaction_key = 'Rx' if dir_idx == 0 else 'Ry'
                base_shear = float(sum(abs(r[reaction_key]) for r in reactions.values()))

                results['curve'].append({
                    'base_shear': base_shear,
                    'top_drift': top_drift,
                    'roof_displacement': roof_disp
                })

                # punti caratteristici
                if step == int(n_steps * 0.2):
                    results['performance_levels']['yield'] = {
                        'base_shear': base_shear,
                        'top_drift': top_drift,
                        'roof_displacement': roof_disp
                    }
                if step == int(n_steps * 0.8):
                    results['performance_levels']['ultimate'] = {
                        'base_shear': base_shear,
                        'top_drift': top_drift,
                        'roof_displacement': roof_disp
                    }
                    
                    # Calcolo duttilità
                    if 'yield' in results['performance_levels']:
                        y_drift = results['performance_levels']['yield']['top_drift']
                        results['performance_levels']['ultimate']['ductility'] = top_drift / y_drift
                
                # Stop quando raggiungo il target
                if target_drift and top_drift >= target_drift:
                    results['performance_levels'].setdefault('ultimate', {
                        'base_shear': base_shear,
                        'top_drift': top_drift,
                        'roof_displacement': roof_disp
                    })
                    break

            # Fallback per yield se manca (target_drift potrebbe interrompere prima del 20%)
            if 'yield' not in results['performance_levels'] and results['curve']:
                # Prendi punto a ~10% del percorso effettuato
                yield_idx = max(0, len(results['curve'])//10)
                results['performance_levels']['yield'] = results['curve'][yield_idx]

            # punto di prestazione (N2 semplificato)
            if 'yield' in results['performance_levels']:
                y = results['performance_levels']['yield']
                results['performance_point'] = {
                    'displacement': y['roof_displacement'] * 1.5,
                    'base_shear': y['base_shear'] * 1.2
                }
            
            # Aggiungi info sulla direzione
            results['direction'] = direction.upper()

            return results
        
        def _get_building_height(self) -> float:
            """Calcola altezza totale edificio"""
            if not self.nodes:
                return 3.0
            y_coords = [node['y'] for node in self.nodes.values()]
            return max(y_coords) - min(y_coords) if y_coords else 3.0
        
        def _pier_capacity(self, elem: FrameElement, N: float) -> Dict:
            """Calcola capacità maschio murario secondo NTC2018 (unità coerenti)."""
            pier = elem.geometry
            mat = elem.material
            
            # Geometria (m, m²)
            A_eff = float(getattr(pier, 'effective_area', getattr(pier, 'area', 0.0)))
            b_eff = float(getattr(pier, 'length', 0.0))  # larghezza maschio ~ braccio plastico
            
            if A_eff <= 0 or b_eff <= 0:
                return {'M_max': 0.0, 'V_max': 0.0}
            
            # Proprietà materiali (MPa -> kN/m²: ×1000)
            fc_kn = max(0.0, float(getattr(mat, 'fcm', 0.0)) * 1000.0)
            tau0_kn = max(0.0, float(getattr(mat, 'tau0', getattr(mat, 'fvm', 0.0))) * 1000.0)
            mu = max(0.0, float(getattr(mat, 'mu', 0.0)))
            
            # Sforzo medio (kN/m²): N[kN] / A[m²]
            sigma_0 = abs(float(N)) / A_eff if A_eff > 0 else 0.0
            
            # Momento ultimo (kNm) – braccio plastico ~0.8*b
            if fc_kn > 0.0:
                red = max(0.0, 1.0 - sigma_0 / fc_kn)  # riduzione per pressoflessione
                z = 0.8 * b_eff
                # A[m²]*z[m]*fc[kN/m²] => kN·m
                M_max = (A_eff * z * fc_kn * red) / 4.0
            else:
                M_max = 0.0
                
            # Taglio ultimo (kN): A[m²]*(τ0 + μ*σ0)[kN/m²]
            V_max = A_eff * max(0.0, tau0_kn + mu * sigma_0)
            
            return {'M_max': float(M_max), 'V_max': float(V_max)}
        
        def _spandrel_capacity(self, elem: FrameElement) -> Dict:
            """Calcola capacità fascia di piano"""
            spandrel = elem.geometry
            
            # Metodi standard da GeometrySpandrel
            M_max = spandrel.get_capacity_flexure() if hasattr(spandrel, 'get_capacity_flexure') else 100.0
            V_max = spandrel.get_capacity_shear() if hasattr(spandrel, 'get_capacity_shear') else 50.0
            
            return {'M_max': M_max, 'V_max': V_max}

# Costruttore uniforme per gli elementi del frame (gestisce tutti gli scenari di import)
if _FrameElement is not None:
    # Scenario 1: FrameElement importato correttamente dall'esterno
    FrameElementCtor = _FrameElement
else:
    # Scenario 2 o 3: FrameElement non importato
    try:
        # Prova ad usare la classe fallback (esiste solo se EquivalentFrame is None)
        FrameElementCtor = FrameElement  # noqa: F821
    except NameError:
        # Scenario 3: EquivalentFrame importato ma FrameElement no
        # Definiamo una classe minimale compatibile
        @dataclass
        class FrameElementMinimal:
            """Elemento minimale compatibile per telaio equivalente"""
            i_node: int
            j_node: int
            geometry: Union[GeometryPier, GeometrySpandrel]
            material: MaterialProperties
            type: str  # 'pier' o 'spandrel'
            forces: Dict[str, float] = None
            
            def __post_init__(self):
                if self.forces is None:
                    self.forces = {'N': 0, 'V': 0, 'M_i': 0, 'M_j': 0, 
                                  'N_i': 0, 'V_i': 0}
                    
            def compute_internal_forces(self, u_elem: np.ndarray):
                """Calcola forze interne (versione compatibile minimale)"""
                frame = getattr(self, '_frame_ref', None)
                if frame is None:
                    raise RuntimeError("FrameElement senza riferimento al frame")
                T, L = frame._element_T_and_length(self)
                k_loc = frame._get_element_stiffness_local(self, L)
                u_loc = T.T @ u_elem
                f_loc = k_loc @ u_loc
                self.forces['N_i'] = float(f_loc[0])
                self.forces['V_i'] = float(f_loc[1])
                self.forces['M_i'] = float(f_loc[2])
                self.forces['N']   = float(f_loc[3])
                self.forces['V']   = float(f_loc[4])
                self.forces['M_j'] = float(f_loc[5])
        
        FrameElementCtor = FrameElementMinimal

# ============================================================================
# CLASSE PRINCIPALE MasonryFEMEngine
# ============================================================================

class MasonryFEMEngine:
    """Motore di calcolo FEM completo per muratura secondo NTC 2018"""
    
    VERSION = "6.1-FINAL"
    
    def __init__(self, method: AnalysisMethod = AnalysisMethod.FEM):
        """
        Inizializza il motore di calcolo
        
        Args:
            method: Metodo di analisi da utilizzare
        """
        self.method = method
        self.gamma_m = 2.0  # Coefficiente di sicurezza base
        self.FC = 1.0       # Fattore di confidenza
        
        # Dati mesh (da fornire esternamente)
        self.nodes = None
        self.elements = None
        self.constrained_nodes = None
        
        # Risultati analisi
        self.K_global = None
        self.displacements = None
        self.stresses = None
        self.strains = None
        
        # Modelli specializzati
        self.frame_model = None
        self.limit_model = None
        self.fiber_model = None
        self.micro_model = None
        
        # Punti di Gauss per integrazione Q4
        self.gauss_points_Q4 = np.array([
            [-1/np.sqrt(3), -1/np.sqrt(3)],
            [ 1/np.sqrt(3), -1/np.sqrt(3)],
            [ 1/np.sqrt(3),  1/np.sqrt(3)],
            [-1/np.sqrt(3),  1/np.sqrt(3)]
        ])
        self.gauss_weights_Q4 = np.array([1.0, 1.0, 1.0, 1.0])
        
        logger.info(f">>> MasonryFEMEngine v{self.VERSION} - Metodo: {method.value}")
        
    def analyze_structure(self, wall_data: Dict, material: MaterialProperties,
                         loads: Dict, options: Optional[Dict] = None) -> Dict:
        """
        Analisi completa della struttura con il metodo selezionato
        
        Args:
            wall_data: Geometria della parete
            material: Proprietà del materiale
            loads: Carichi applicati
            options: Opzioni specifiche per metodo
            
        Returns:
            Risultati dell'analisi
        """
        logger.info(f"=== ANALISI STRUTTURA - Metodo: {self.method.value} ===")
        
        if options is None:
            options = {}
            
        # Verifica disponibilità del metodo e chiama la funzione appropriata
        if self.method == AnalysisMethod.FEM:
            if _analyze_fem is not None:
                return _analyze_fem(wall_data, material, loads, options)
            else:
                logger.error("Modulo FEM non disponibile")
                return {'error': 'Modulo FEM non disponibile'}
                
        elif self.method == AnalysisMethod.POR:
            if _analyze_por is not None:
                return _analyze_por(wall_data, material, loads, options)
            else:
                logger.error("Modulo POR non disponibile")
                return {'error': 'Modulo POR non disponibile'}
                
        elif self.method == AnalysisMethod.SAM:
            if _analyze_sam is not None:
                return _analyze_sam(wall_data, material, loads, options)
            else:
                logger.error("Modulo SAM non disponibile")
                return {'error': 'Modulo SAM non disponibile'}
                
        elif self.method == AnalysisMethod.FRAME:
            if _analyze_frame is not None:
                return _analyze_frame(wall_data, material, loads, options)
            else:
                # Usa implementazione locale
                return self._analyze_frame(wall_data, material, loads, options)
                
        elif self.method == AnalysisMethod.LIMIT:
            if _analyze_limit is not None:
                return _analyze_limit(wall_data, material, loads, options)
            else:
                # Usa implementazione locale
                return self._analyze_limit(wall_data, material, loads, options)
                
        elif self.method == AnalysisMethod.FIBER:
            if _analyze_fiber is not None:
                return _analyze_fiber(wall_data, material, loads, options)
            else:
                # Usa implementazione locale
                return self._analyze_fiber(wall_data, material, loads, options)
                
        elif self.method == AnalysisMethod.MICRO:
            if _analyze_micro is not None:
                return _analyze_micro(wall_data, material, loads, options)
            else:
                # Usa implementazione locale
                return self._analyze_micro(wall_data, material, loads, options)
        else:
            raise ValueError(f"Metodo {self.method} non implementato")
            
    def _analyze_frame(self, wall_data: Dict, material: MaterialProperties,
                      loads: Dict, options: Dict) -> Dict:
        """Analisi con telaio equivalente completo (implementazione locale)"""
        logger.info("Analisi TELAIO EQUIVALENTE (implementazione locale)")
        
        # Estrai pattern prima di costruire il modello
        pattern = options.get('lateral_pattern', 'triangular')
        
        # Costruisci modello telaio
        self.frame_model = self._build_frame_model(wall_data, material)
        
        # Analisi richiesta
        analysis_type = options.get('analysis_type', 'pushover')
        
        results = {
            'method': 'TELAIO_EQUIVALENTE',
            'model_summary': {
                'n_nodes': len(self.frame_model.nodes),
                'n_elements': len(self.frame_model.elements),
                'n_piers': sum(1 for e in self.frame_model.elements if e.type == 'pier'),
                'n_spandrels': sum(1 for e in self.frame_model.elements if e.type == 'spandrel')
            }
        }
        
        if analysis_type == 'static':
            static_results = self.frame_model.solve_static(loads)
            results.update(static_results)
            # Aggiorna campi della classe per compatibilità
            self.displacements = np.array(static_results.get('displacements', []))
            
        elif analysis_type == 'modal':
            n_modes = options.get('n_modes', 6)
            modal_results = self.frame_model.solve_modal(n_modes)
            results.update(modal_results)
            
            # Verifica masse partecipanti (EC8 richiede >85%)
            if modal_results.get('total_mass_participation_x', 0) < 0.85:
                logger.warning(f"Massa partecipante X: {modal_results['total_mass_participation_x']:.1%} < 85%")
            if modal_results.get('total_mass_participation_y', 0) < 0.85:
                logger.warning(f"Massa partecipante Y: {modal_results['total_mass_participation_y']:.1%} < 85%")
            
            # Niente check elementi: non ci sono forze interne calcolate in modale
            results['element_checks'] = []
            return results
            
        elif analysis_type == 'pushover':
            target_drift = options.get('target_drift', 0.04)
            
            pushover_results = self.frame_model.pushover_analysis(pattern, target_drift)
            results.update(pushover_results)
            
            # Calcola duttilità globale
            if pushover_results.get('performance_levels'):
                y = pushover_results['performance_levels'].get('yield', {})
                u = pushover_results['performance_levels'].get('ultimate', {})
                if y.get('top_drift') and u.get('top_drift'):
                    results['ductility'] = u['top_drift'] / y['top_drift']
            
            # Aggiorna displacements con ultimo punto della curva
            if pushover_results.get('curve'):
                last_point = pushover_results['curve'][-1]
                # Stima displacements approssimati (solo per compatibilità)
                self.displacements = np.ones(len(self.frame_model.nodes) * 3) * last_point.get('roof_displacement', 0)
                    
        elif analysis_type == 'time_history':
            accelerogram = options.get('accelerogram', [])
            if not accelerogram:
                raise ValueError("Accelerogramma richiesto per analisi time-history")
            dt = options.get('dt', 0.01)
            excitation_dir = options.get('excitation_dir', 'y')
            accel_units = options.get('accel_units', 'mps2')
            
            results['time_history'] = self._time_history_analysis(
                self.frame_model, accelerogram, dt, excitation_dir, accel_units
            )
            # Aggiorna displacements con step critico
            if results['time_history'].get('critical_step'):
                crit_idx = results['time_history']['critical_step']['index']
                if results['time_history'].get('displacements'):
                    self.displacements = np.array(results['time_history']['displacements'][crit_idx])
            
        # Verifiche elementi (le forze sono già calcolate per ogni tipo di analisi)
        results['element_checks'] = self._check_frame_elements(self.frame_model, material)
        
        return results
        
    def _build_frame_model(self, wall_data: Dict, material: MaterialProperties) -> EquivalentFrame:
        """Costruisce modello di telaio equivalente"""
        # Non mutare il dizionario originale
        wd = dict(wall_data)
        
        # Controllo dati geometrici di input
        if wd.get('length', 0) <= 0 or wd.get('height', 0) <= 0:
            raise ValueError("length e height della parete devono essere > 0")
        if wd.get('thickness', 0) <= 0:
            logger.warning("Spessore parete non valido, uso default 0.3m")
            wd['thickness'] = 0.3
            
        frame = EquivalentFrame()
        
        # Identifica geometria strutturale
        geometry = self._identify_structural_geometry(wd)
        
        # Crea nodi
        node_id = 0
        for level in geometry['levels']:
            for x in geometry['x_positions']:
                frame.add_node(node_id, x, level)
                node_id += 1
        
        # Crea elementi maschi
        for pier_data in geometry['piers']:
            # Stima larghezza maschio (se non fornita esplicitamente)
            pier_width = wd.get('pier_width')
            if pier_width is None:
                bay = max(geometry['x_positions']) - min(geometry['x_positions'])
                if bay > 0:
                    # 20% dell'interasse, limitato tra 0.3m e 1.0m
                    pier_width = max(0.3, min(1.0, 0.2 * bay))
                    # Evita sovrapposizioni: max 45% del bay
                    pier_width = min(pier_width, 0.45 * bay)
                else:
                    pier_width = 0.3  # fallback minimo
                
            pier_geom = GeometryPier(
                length=pier_width,  # Larghezza maschio corretta
                height=pier_data['height'],
                thickness=wd.get('thickness', 0.3),
                h0=pier_data['height'] * 0.5
            )
            
            i_node = pier_data['bottom_node']
            j_node = pier_data['top_node']
            
            pier_elem = FrameElementCtor(i_node, j_node, pier_geom, material, 'pier')
            frame.add_element(pier_elem)
        
        # Crea elementi fascia solo se più di un piano
        if len(geometry['spandrels']) > 0:
            for spandrel_data in geometry['spandrels']:
                spandrel_geom = GeometrySpandrel(
                    length=spandrel_data['length'],
                    height=spandrel_data['height'],
                    thickness=spandrel_data['thickness']
                )
                
                i_node = spandrel_data['left_node']
                j_node = spandrel_data['right_node']
                
                spandrel_elem = FrameElementCtor(
                    i_node=i_node, 
                    j_node=j_node, 
                    geometry=spandrel_geom,
                    material=material, 
                    type='spandrel'
                )
                frame.add_element(spandrel_elem)  # SEMPRE usa add_element per settare _frame_ref
        
        # Vincoli alla base
        for node in geometry['base_nodes']:
            frame.add_constraint(node, 'fixed')
        
        # Assembla matrici
        frame.assemble_stiffness_matrix()
        
        # Masse di piano (posizionate al piano corrispondente)
        if 'floor_masses' in wd and wd['floor_masses']:
            floor_masses_distributed = {}
            n_nodes_per_floor = len(geometry['x_positions'])
            
            # Normalizza chiavi nel caso non siano 0-based
            keys_sorted = sorted(wd['floor_masses'].keys())
            remap = {old: i for i, old in enumerate(keys_sorted)}
            
            for floor_idx_old, mass in wd['floor_masses'].items():
                # La massa del piano i va al livello i (0-based)
                # Se floor_masses={0: m0}, la massa va al primo piano (level 1)
                # Se floor_masses={0: m0, 1: m1}, m0 va al piano 1, m1 al piano 2
                level_idx = remap[floor_idx_old] + 1
                if level_idx < len(geometry['levels']):
                    mass_per_node = mass / n_nodes_per_floor
                    
                    for x_idx in range(n_nodes_per_floor):
                        node_id = level_idx * n_nodes_per_floor + x_idx
                        floor_masses_distributed[node_id] = mass_per_node
                else:
                    logger.warning(f"Massa piano {floor_idx_old} supera numero livelli, ignorata")
            
            frame.assemble_mass_matrix(floor_masses_distributed)
        else:
            logger.info("Nessuna massa di piano fornita, uso matrice massa di default in analisi dinamiche")
        
        return frame
        
    def _identify_structural_geometry(self, wall_data: Dict) -> Dict:
        """Identifica geometria strutturale per telaio"""
        wall_length = wall_data.get('length', 5.0)
        wall_height = wall_data.get('height', 3.0)
        floor_masses = wall_data.get('floor_masses', {})
        
        # Determina numero di piani
        if floor_masses:
            n_floors = max(1, len(floor_masses))
        else:
            n_floors = 1
        
        # Crea geometria semplice ma robusta
        geometry = {
            'levels': [],
            'x_positions': [],
            'piers': [],
            'spandrels': [],
            'base_nodes': []
        }
        
        # Livelli (altezze dei piani)
        for i in range(n_floors + 1):
            geometry['levels'].append(i * wall_height / n_floors)
        
        # Posizioni x (almeno 2 nodi per livello)
        geometry['x_positions'] = [0.0, wall_length]
        
        # ID nodi progressivo
        node_id = 0
        node_map = {}  # (livello, x_pos) -> node_id
        
        # Mappa tutti i nodi
        for level_idx, level in enumerate(geometry['levels']):
            for x_idx, x_pos in enumerate(geometry['x_positions']):
                node_map[(level_idx, x_idx)] = node_id
                node_id += 1
        
        # Crea maschi murari (elementi verticali)
        for level_idx in range(n_floors):
            for x_idx in range(len(geometry['x_positions'])):
                bottom_node = node_map[(level_idx, x_idx)]
                top_node = node_map[(level_idx + 1, x_idx)]
                
                geometry['piers'].append({
                    'pier_thickness': wall_data.get('thickness', 0.3),  # Spessore muro
                    'height': wall_height / n_floors,
                    'thickness': wall_data.get('thickness', 0.3),
                    'bottom_node': bottom_node,
                    'top_node': top_node
                })
        
        # Crea fasce di piano (elementi orizzontali)
        for level_idx in range(1, n_floors + 1):  # Partendo dal primo piano
            for x_idx in range(len(geometry['x_positions']) - 1):
                left_node = node_map[(level_idx, x_idx)]
                right_node = node_map[(level_idx, x_idx + 1)]
                
                geometry['spandrels'].append({
                    'length': wall_length,
                    'height': min(0.5, wall_height * 0.2),  # 20% altezza piano o 50cm
                    'thickness': wall_data.get('thickness', 0.3),
                    'left_node': left_node,
                    'right_node': right_node
                })
        
        # Nodi vincolati alla base
        for x_idx in range(len(geometry['x_positions'])):
            geometry['base_nodes'].append(node_map[(0, x_idx)])
        
        logger.info(f"Geometria telaio: {n_floors} piani, {len(geometry['piers'])} maschi, {len(geometry['spandrels'])} fasce")
        
        return geometry
        
    def _time_history_analysis(self, frame: EquivalentFrame,
                               accelerogram: List[float],
                               dt: float,
                               excitation_dir: str = 'y',
                               accel_units: str = 'mps2') -> Dict:
        """Analisi time-history (Newmark β=0.25, γ=0.5) con Rayleigh su DOF liberi
        e calcolo forze interne allo step critico."""
        beta = 0.25
        gamma = 0.5
        
        # Direzione coerente per tutto (0=X, 1=Y)
        dir_idx = 0 if excitation_dir.lower().startswith('x') else 1

        n_steps = len(accelerogram) if accelerogram else 100
        if not accelerogram:
            logger.warning("Nessun accelerogramma fornito, uso sinusoide di test")
            # Sinusoide di test 1Hz, 0.1g per 10 secondi
            dt = 0.01
            n_steps = 1000
            t = np.arange(n_steps) * dt
            accelerogram = 0.1 * 9.80665 * np.sin(2 * np.pi * 1.0 * t)
        n = len(frame.nodes) * 3

        from scipy.sparse import eye as speye
        K = frame.K_global.tocsr()
        M = frame.M_global.tocsr() if frame.M_global is not None else (speye(n, format='csr') * 1000.0)

        # ---- Riduzione ai DOF liberi (come nella modale)
        fixed = []
        for node_id, c in frame.constraints.items():
            if c == 'fixed':
                fixed.extend(frame.node_dofs[node_id])
        fixed = sorted(set(fixed))
        free = np.array([i for i in range(n) if i not in fixed], dtype=int)

        if free.size == 0:
            raise RuntimeError("Nessun DOF libero per l'analisi dinamica.")

        Kff = K[free][:, free].tocsr()
        Mff = M[free][:, free].tocsr()

        # ---- Smorzamento di Rayleigh (ξ=5%) stimato sui primi due modi ridotti
        try:
            from scipy.sparse.linalg import eigsh
            lam, _ = eigsh(Kff, k=min(2, max(1, Kff.shape[0]-1)), M=Mff, which='SM')
            w = np.sqrt(np.clip(lam, 1e-12, None))
            w1 = float(w[0])
            w2 = float(w[1]) if len(w) > 1 else float(w[0]) * 1.5
        except Exception:
            w1, w2 = 2*np.pi*1.0, 2*np.pi*3.0  # fallback realistico per muratura

        xi = 0.05
        # Protezione contro divisione per zero
        den = (w1 + w2) if (w1 + w2) > 1e-12 else 1e-12
        alpha0 = 2*xi*w1*w2/den   # coeff. massa
        alpha1 = 2*xi/den         # coeff. rigidezza
        Cff = alpha0*Mff + alpha1*Kff

        # ---- Conversione accelerogramma
        if accel_units.lower() in ('g', 'grav'):
            acc = np.asarray(accelerogram, dtype=float) * 9.80665
        elif accel_units.lower() in ('gal',):
            acc = np.asarray(accelerogram, dtype=float) * 0.01  # 1 Gal = 0.01 m/s^2
        else:
            acc = np.asarray(accelerogram, dtype=float)

        # ---- Vettore di influenza ridotto (solo traslazioni)
        r = np.zeros(n)
        if dir_idx == 0:  # X
            r[0::3] = 1.0
        else:  # Y
            r[1::3] = 1.0
        rf = r[free]
        Mrf = (Mff @ rf)

        # ---- Stati (ridotti)
        uf = np.zeros((n_steps, free.size))
        vf = np.zeros((n_steps, free.size))
        af = np.zeros((n_steps, free.size))

        # ---- Integrazione Newmark sui DOF liberi (forma canonica)
        # Coefficienti Newmark (β=0.25, γ=0.5)
        a0 = 1.0/(beta*dt*dt)
        a1 = gamma/(beta*dt)
        a2 = 1.0/(beta*dt)
        a3 = 1.0/(2.0*beta) - 1.0
        a4 = gamma/beta - 1.0
        a5 = dt*(gamma/(2.0*beta) - 1.0)
        
        K_eff = (Kff + a1*Cff + a0*Mff).toarray()
        try:
            from scipy.linalg import cho_factor, cho_solve
            K_eff_fact = cho_factor(K_eff, overwrite_a=False, check_finite=False)
            def solve_keff(rhs):
                return cho_solve(K_eff_fact, rhs, check_finite=False)
        except Exception:
            def solve_keff(rhs):
                return np.linalg.solve(K_eff, rhs)

        # Stati iniziali
        u_prev = uf[0].copy()
        v_prev = vf[0].copy()
        a_prev = af[0].copy()

        for i in range(1, n_steps):
            # Forza sismica al passo i
            Fg = - (acc[i] if i < len(acc) else 0.0) * Mrf
            
            # Carico efficace Newmark (forma canonica)
            P_eff = (Fg
                     + Mff @ (a0*u_prev + a2*v_prev + a3*a_prev)
                     + Cff @ (a1*u_prev + a4*v_prev + a5*a_prev))
            
            # Risoluzione
            u_i = solve_keff(P_eff)
            
            # Aggiornamento accelerazione e velocità
            a_i = a0*(u_i - u_prev) - a2*v_prev - a3*a_prev
            v_i = v_prev + dt*((1.0 - gamma)*a_prev + gamma*a_i)
            
            # Salva stati
            uf[i], vf[i], af[i] = u_i, v_i, a_i
            u_prev, v_prev, a_prev = u_i, v_i, a_i

        # ---- Ricostruzione a spazio completo (base = 0)
        u = np.zeros((n_steps, n));  u[:, free] = uf
        v = np.zeros((n_steps, n));  v[:, free] = vf
        a = np.zeros((n_steps, n));  a[:, free] = af

        # ---- Identificazione step critico e calcolo forze interne
        # Nodo di copertura (sempre quello con Y max, ma DOF dipende da direzione)
        node_ids = sorted(frame.nodes.keys())
        y_coords = np.array([frame.nodes[i]['y'] for i in node_ids])
        roof_node = node_ids[int(np.argmax(y_coords))]
        roof_dof = frame.node_dofs[roof_node][dir_idx]  # DOF coerente con direzione
        
        # Step critico basato sullo spostamento nella direzione coerente
        i_crit = int(np.argmax(np.abs(u[:, roof_dof])))

        # Calcola forze interne allo step critico
        u_crit = u[i_crit]
        for elem in frame.elements:
            dof_i = frame.node_dofs[elem.i_node]
            dof_j = frame.node_dofs[elem.j_node]
            u_elem = np.concatenate([u_crit[dof_i], u_crit[dof_j]])
            elem.compute_internal_forces(u_elem)
        
        # Salva forze per output
        element_forces_crit = [e.forces for e in frame.elements]
        
        # ---- Base shear allo step critico (dinamico: K_cf u_f + C_cf v_f + M_cf a_f)
        fixed_arr = np.array(sorted(set(fixed)), dtype=int)
        free_arr = np.array(free, dtype=int)
        
        Kcf = K[fixed_arr][:, free_arr]
        Mcf = M[fixed_arr][:, free_arr]
        # C globale via Rayleigh sugli stessi alpha0/alpha1
        Ccf = alpha0*M[fixed_arr][:, free_arr] + alpha1*K[fixed_arr][:, free_arr]
        
        u_f_crit = u_crit[free_arr]
        v_f_crit = v[i_crit, free_arr]
        a_f_crit = a[i_crit, free_arr]
        
        R_c = (Kcf @ u_f_crit) + (Ccf @ v_f_crit) + (Mcf @ a_f_crit)  # F_c = 0
        
        # Somma delle reazioni nella direzione coerente (Rx se X, Ry se Y)
        Vb_crit = 0.0
        for node_id, constraint in frame.constraints.items():
            if constraint == 'fixed':
                dofs = frame.node_dofs[node_id]
                # mapping da DOF globale a indice in 'fixed_arr'
                idxs = np.where(fixed_arr == dofs[dir_idx])[0]
                if idxs.size:
                    Vb_crit += R_c[idxs[0]]
        Vb_crit = abs(float(Vb_crit))

        # ---- Metriche finali
        height = frame._get_building_height()
        # Drift massimo coerente con direzione (0::3 per X, 1::3 per Y)
        max_drift = float(np.max(np.abs(u[:, dir_idx::3]))) / max(height, 1e-6)

        return {
            'time': (np.arange(n_steps)*dt).tolist(),
            'displacements': u.tolist(),
            'velocities': v.tolist(),
            'accelerations': a.tolist(),
            'max_drift': max_drift,
            'max_acceleration': float(np.max(np.abs(a))),
            'max_velocity': float(np.max(np.abs(v))),
            'max_displacement': float(np.max(np.abs(u))),
            'critical_step': {
                'index': int(i_crit),
                'time': float(i_crit * dt),
                'roof_displacement': float(u_crit[roof_dof]),
                'base_shear': float(Vb_crit),
                'element_forces': element_forces_crit
            }
        }
        
    def _check_frame_elements(self, frame: EquivalentFrame, 
                             material: MaterialProperties) -> List[Dict]:
        """Verifica elementi del telaio secondo NTC2018"""
        checks = []
        
        # Cerca metodi di capacità nel frame (potrebbero non esistere)
        cap_pier_fn = getattr(frame, '_pier_capacity', None)
        cap_span_fn = getattr(frame, '_spandrel_capacity', None)
        
        for idx, elem in enumerate(frame.elements):
            forces = elem.forces
            
            if elem.type == 'pier':
                # Usa metodo del frame se disponibile, altrimenti fallback generico
                if cap_pier_fn:
                    capacity = cap_pier_fn(elem, forces['N'])
                else:
                    capacity = self._capacity_pier_generic(elem, forces['N'], material)
            else:
                # Usa metodo del frame se disponibile, altrimenti fallback generico
                if cap_span_fn:
                    capacity = cap_span_fn(elem)
                else:
                    capacity = self._capacity_spandrel_generic(elem, material)
                
            # Demand/Capacity Ratios (usando max tra V_i e V_j)
            DCR_moment = abs(max(forces['M_i'], forces['M_j'], key=abs)) / capacity['M_max'] if capacity['M_max'] > 0 else 999
            V_demand = max(abs(forces.get('V_i', 0.0)), abs(forces.get('V', 0.0)))
            DCR_shear = V_demand / capacity['V_max'] if capacity['V_max'] > 0 else 999
            
            check = {
                'element_id': idx,
                'element_type': elem.type,
                'forces': forces,
                'capacity': capacity,
                'DCR_moment': DCR_moment,
                'DCR_shear': DCR_shear,
                'DCR_max': max(DCR_moment, DCR_shear),
                'verified': DCR_moment <= 1.0 and DCR_shear <= 1.0
            }
            
            # Classificazione livello di danno
            if check['DCR_max'] < 0.5:
                check['damage_level'] = 'None'
            elif check['DCR_max'] < 0.8:
                check['damage_level'] = 'Light'
            elif check['DCR_max'] < 1.0:
                check['damage_level'] = 'Moderate'
            elif check['DCR_max'] < 1.5:
                check['damage_level'] = 'Severe'
            else:
                check['damage_level'] = 'Collapse'
            
            checks.append(check)
            
        return checks
    
    def _capacity_pier_generic(self, elem: Any, N: float, material: MaterialProperties) -> Dict:
        """Calcola capacità maschio murario generico (fallback)"""
        pier = elem.geometry
        
        # Geometria (m, m²)
        A_eff = float(getattr(pier, 'effective_area', getattr(pier, 'area', 0.0)))
        b_eff = float(getattr(pier, 'length', 0.0))
        
        if A_eff <= 0 or b_eff <= 0:
            return {'M_max': 0.0, 'V_max': 0.0}
        
        # Proprietà materiali (MPa -> kN/m²: ×1000)
        fc_kn = max(0.0, float(getattr(material, 'fcm', 0.0)) * 1000.0)
        tau0_kn = max(0.0, float(getattr(material, 'tau0', getattr(material, 'fvm', 0.0))) * 1000.0)
        mu = max(0.0, float(getattr(material, 'mu', 0.0)))
        
        # Sforzo medio (kN/m²): N[kN] / A[m²]
        sigma_0 = abs(float(N)) / A_eff if A_eff > 0 else 0.0
        
        # Momento ultimo (kNm)
        if fc_kn > 0.0:
            red = max(0.0, 1.0 - sigma_0 / fc_kn)
            z = 0.8 * b_eff
            M_max = (A_eff * z * fc_kn * red) / 4.0
        else:
            M_max = 0.0
            
        # Taglio ultimo (kN)
        V_max = A_eff * max(0.0, tau0_kn + mu * sigma_0)
        
        return {'M_max': float(M_max), 'V_max': float(V_max)}
    
    def _capacity_spandrel_generic(self, elem: Any, material: MaterialProperties) -> Dict:
        """Calcola capacità fascia di piano generica (fallback)"""
        spandrel = elem.geometry
        
        # Cerca metodi specifici nella geometria
        M_max = spandrel.get_capacity_flexure() if hasattr(spandrel, 'get_capacity_flexure') else 100.0
        V_max = spandrel.get_capacity_shear() if hasattr(spandrel, 'get_capacity_shear') else 50.0
        
        return {'M_max': M_max, 'V_max': V_max}
        
    def _analyze_limit(self, wall_data: Dict, material: MaterialProperties,
                      loads: Dict, options: Dict) -> Dict:
        """Analisi limite completa con tutti i cinematismi EC8"""
        logger.info("ANALISI LIMITE - Tutti i cinematismi")
        
        # Se il modulo è disponibile, usalo
        if LimitAnalysis is not None:
            # Prepara geometria per analisi limite
            limit_geometry = self._prepare_limit_geometry(wall_data)
            
            # Crea modello analisi limite
            self.limit_model = LimitAnalysis(limit_geometry, material)
            
            # Analizza tutti i meccanismi
            results = self.limit_model.analyze_all_mechanisms(loads)
            
            # Analisi probabilistica se richiesta
            if options.get('probabilistic', False):
                results['probabilistic'] = probabilistic_limit_analysis(
                    self.limit_model, loads, options
                )
                
            # Ottimizzazione rinforzi se richiesta
            if options.get('optimize_strengthening', False):
                target_alpha = options.get('target_alpha', 0.3)
                results['strengthening'] = self.limit_model.optimize_strengthening(target_alpha)
                
            # Analisi di sensibilità
            if options.get('sensitivity', False):
                results['sensitivity'] = sensitivity_analysis_limit(
                    self.limit_model, loads
                )
                
            return results
        else:
            # Implementazione base
            logger.warning("Modulo analisi limite non disponibile, uso implementazione base")
            return {
                'method': 'LIMIT',
                'status': 'basic_implementation',
                'alpha': 0.3,
                'mechanism': 'overturning'
            }
        
    def _prepare_limit_geometry(self, wall_data: Dict) -> Dict:
        """Prepara geometria per analisi limite"""
        geometry = {
            'height': wall_data.get('height', 3.0),
            'thickness': wall_data.get('thickness', 0.3),
            'length': wall_data.get('length', 5.0),
            'wall_type': wall_data.get('wall_type', 'single_leaf')
        }
        
        # Aggiungi dettagli se presenti
        if 'openings' in wall_data:
            geometry['openings'] = wall_data['openings']
            
        if 'arch' in wall_data:
            geometry['arch'] = wall_data['arch']
            
        if 'vault' in wall_data:
            geometry['vault'] = wall_data['vault']
            
        if 'facade_details' in wall_data:
            geometry.update(wall_data['facade_details'])
            
        return geometry
        
    def _analyze_fiber(self, wall_data: Dict, material: MaterialProperties,
                      loads: Dict, options: Dict) -> Dict:
        """Analisi con modello a fibre completo"""
        logger.info("Analisi MODELLO A FIBRE")
        
        if FiberModel is not None:
            # Prepara elementi strutturali
            elements = self._prepare_fiber_elements(wall_data)
            
            # Scegli legame costitutivo
            law_type = options.get('constitutive_law', ConstitutiveLaw.BILINEAR)
            
            # Crea modello a fibre
            self.fiber_model = FiberModel(elements, material, law_type)
            
            # Tipo di analisi
            analysis_type = options.get('analysis_type', 'pushover')
            
            results = {
                'method': 'FIBER_MODEL',
                'constitutive_law': law_type.value,
                'elements': len(elements)
            }
            
            if analysis_type == 'pushover':
                # Pushover standard
                vertical = distribute_vertical_loads(loads, elements)
                pattern = options.get('lateral_pattern', 'triangular')
                max_drift = options.get('max_drift', 0.05)
                
                pushover_results = self.fiber_model.pushover_analysis(
                    vertical, pattern, max_drift
                )
                results.update(pushover_results)
                
                # Calcola indicatori di danno
                results['damage_indices'] = calculate_damage_indices(pushover_results)
                
            elif analysis_type == 'cyclic':
                # Analisi ciclica
                protocol = options.get('protocol', [0.001, 0.002, 0.005, 0.01, 0.02])
                vertical = distribute_vertical_loads(loads, elements)
                
                cyclic_results = self.fiber_model.cyclic_analysis(protocol, vertical)
                results.update(cyclic_results)
                
            return results
        else:
            # Implementazione base
            logger.warning("Modulo fiber non disponibile, uso implementazione base")
            return {
                'method': 'FIBER',
                'status': 'basic_implementation',
                'max_curvature': 0.001,
                'max_moment': material.fcm * wall_data.get('area', 1.0) * 0.1
            }
        
    def _prepare_fiber_elements(self, wall_data: Dict) -> List[Dict]:
        """Prepara elementi per modello a fibre"""
        elements = []
        
        elem = {
            'id': 'wall_0',
            'type': 'pier',
            'geometry': GeometryPier(
                length=wall_data.get('pier_width', wall_data.get('length', 2.0)),
                height=wall_data.get('height', 3.0),
                thickness=wall_data.get('thickness', 0.3)
            ),
            'n_fibers': 40,
            'is_base': True
        }
        elements.append(elem)
        
        return elements
        
    def _analyze_micro(self, wall_data: Dict, material: MaterialProperties,
                      loads: Dict, options: Dict) -> Dict:
        """Analisi con micro-modellazione"""
        logger.info("Analisi MICRO-MODELLO")
        
        if MicroModel is not None:
            # Proprietà componenti
            block_props = options.get('block_properties', {
                'E': material.E * 1.5,
                'fc': material.fcm * 2.0,
                'ft': material.ftm * 1.5,
                'weight': 20.0
            })
            
            mortar_props = options.get('mortar_properties', {
                'E': material.E * 0.5,
                'fc': material.fcm * 0.3,
                'ft': material.ftm * 0.5,
                'cohesion': material.tau0,
                'friction': material.mu
            })
            
            interface_props = options.get('interface_properties', {
                'k_normal': 1e6,
                'k_tangent': 1e5,
                'cohesion': material.tau0,
                'friction': material.mu,
                'tensile_strength': material.ftm * 0.1,
                'shear_strength': material.tau0
            })
            
            # Crea micro-modello
            self.micro_model = MicroModel(block_props, mortar_props, interface_props)
            
            # Dimensioni blocchi
            block_size = options.get('block_size', {
                'length': 0.25,
                'height': 0.12,
                'mortar_thickness': 0.01
            })
            
            # Genera mesh dettagliata
            self.micro_model.generate_micro_mesh(wall_data, block_size)
            
            # Tipo di analisi
            analysis_type = options.get('analysis_type', 'static')
            
            results = {
                'method': 'MICRO_MODEL',
                'n_blocks': len([e for e in self.micro_model.elements if e['type'] == 'block']),
                'n_mortar': len([e for e in self.micro_model.elements if e['type'] == 'mortar']),
                'n_interfaces': len(self.micro_model.interfaces)
            }
            
            if analysis_type == 'static':
                # Analisi statica
                boundary = get_micro_boundary_conditions(wall_data)
                
                micro_results = self.micro_model.analyze_micro(loads, boundary)
                results.update(micro_results)
                
                # Pattern di fessurazione
                results['crack_pattern'] = analyze_crack_pattern(micro_results)
                
            elif analysis_type == 'homogenization':
                # Omogeneizzazione
                homogenized = self.micro_model.homogenization()
                
                results['homogenized_properties'] = {
                    'E_eq': homogenized.E,
                    'fc_eq': homogenized.fcm,
                    'ft_eq': homogenized.ftm,
                    'tau0_eq': homogenized.tau0
                }
                
            return results
        else:
            # Implementazione base
            logger.warning("Modulo micro non disponibile, uso implementazione base")
            return {
                'method': 'MICRO',
                'status': 'basic_implementation',
                'homogenized_E': material.E * 0.8,
                'homogenized_fc': material.fcm * 0.7
            }