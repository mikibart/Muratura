# utils.py - VERSIONE COMPLETA v3.0
"""
Modulo di utilità per sistema FEM Muratura secondo NTC 2018.

Fornisce funzioni di supporto per analisi strutturali, post-processing,
validazione, ottimizzazione e gestione dati per tutti i metodi di analisi.

Categorie principali:
- Calcolo indici di danno e duttilità
- Analisi probabilistiche e sensibilità
- Gestione mesh e elementi finiti
- Post-processing risultati
- Validazione normativa
- Utilità geometriche e numeriche
- Export/import dati
- Visualizzazione e report
"""

import logging
import numpy as np
import copy
import json
import warnings
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from scipy.stats import norm, lognorm
from scipy.interpolate import interp1d
from scipy.optimize import minimize
import datetime
import os

# Import locali con gestione errori
try:
    from .materials import MaterialProperties
    from .geometry import GeometryPier, GeometrySpandrel, GeometryWall
    from .enums import (
        KinematicMechanism, FailureMode, DamageLevel, 
        LoadType, LimitState, AnalysisMethod
    )
except ImportError as e:
    warnings.warn(f"Import locale fallito: {e}. Alcune funzionalità potrebbero non essere disponibili.", ImportWarning)

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# COSTANTI E CONFIGURAZIONI
# ============================================================================

# Parametri NTC 2018
NTC_PARAMS = {
    'gamma_M': 2.0,      # Coefficiente parziale muratura
    'FC': {              # Fattori di confidenza
        'LC1': 1.35,
        'LC2': 1.20,
        'LC3': 1.00
    },
    'q_factors': {       # Fattori di comportamento
        'unreinforced_regular': 1.5,
        'unreinforced_irregular': 1.0,
        'confined_regular': 2.0,
        'confined_irregular': 1.5,
        'reinforced_regular': 2.5,
        'reinforced_irregular': 2.0
    },
    'return_periods': {  # Periodi di ritorno [anni]
        'SLO': 30,
        'SLD': 50,
        'SLV': 475,
        'SLC': 975
    }
}

# Limiti prestazionali
PERFORMANCE_LIMITS = {
    'drift': {
        'IO': 0.002,     # Immediate Occupancy
        'DC': 0.004,     # Damage Control
        'LS': 0.010,     # Life Safety
        'CP': 0.020      # Collapse Prevention
    },
    'ductility': {
        'brittle': 1.5,
        'limited': 2.5,
        'moderate': 4.0,
        'high': 6.0
    }
}

# ============================================================================
# INDICI DI DANNO E DUTTILITÀ
# ============================================================================

def calculate_damage_indices(pushover_results: Dict, method: str = 'park_ang') -> Dict:
    """
    Calcola indici di danno globali e locali con diversi metodi.
    
    Args:
        pushover_results: Risultati analisi pushover
        method: Metodo calcolo ('park_ang', 'modified_park_ang', 'kunnath', 'fajfar')
        
    Returns:
        Dizionario con indici di danno
    """
    indices = {
        'global': {},
        'local': {},
        'method': method,
        'timestamp': datetime.datetime.now().isoformat()
    }
    
    # Estrai parametri chiave
    if 'performance_levels' not in pushover_results or not pushover_results['performance_levels']:
        logger.warning("Performance levels mancanti, uso valori di default")
        delta_y = 0.001
        delta_u = 0.05
        F_y = 100.0
    else:
        delta_y = pushover_results['performance_levels'].get('yield', {}).get('top_drift', 0.001)
        delta_u = pushover_results['performance_levels'].get('ultimate', {}).get('top_drift', 0.05)
        F_y = pushover_results['performance_levels'].get('yield', {}).get('base_shear', 100.0)
    
    # Dall'ultima curva
    if pushover_results.get('curve'):
        delta_max = pushover_results['curve'][-1]['top_drift']
    else:
        delta_max = delta_u
    
    # Park-Ang damage index
    if method == 'park_ang':
        # Parte di deformazione
        D_delta = max(0, (delta_max - delta_y) / (delta_u - delta_y)) if delta_u > delta_y else 0
        
        # Parte di energia
        beta = 0.15  # Parametro calibrazione per muratura
        
        # Calcola energia isteretica
        E_h = 0
        if 'curve' in pushover_results and len(pushover_results['curve']) > 1:
            curve = pushover_results['curve']
            for i in range(1, len(curve)):
                dF = curve[i]['base_shear'] - curve[i-1]['base_shear']
                dd = curve[i]['top_drift'] - curve[i-1]['top_drift']
                E_h += abs(dF * dd)
        
        D_E = beta * E_h / (F_y * delta_u) if F_y * delta_u > 0 else 0
        
        indices['global']['park_ang'] = min(D_delta + D_E, 1.0)
        indices['global']['D_delta'] = D_delta
        indices['global']['D_energy'] = D_E
        
    elif method == 'modified_park_ang':
        # Versione modificata per muratura
        D_delta = max(0, (delta_max / delta_u) ** 1.5) if delta_u > 0 else 0
        
        # Considera degrado di rigidezza
        if 'curve' in pushover_results and len(pushover_results['curve']) > 1:
            K_initial = pushover_results['curve'][0]['base_shear'] / pushover_results['curve'][0]['top_drift'] if pushover_results['curve'][0]['top_drift'] > 0 else 1000
            K_final = pushover_results['curve'][-1]['base_shear'] / pushover_results['curve'][-1]['top_drift'] if pushover_results['curve'][-1]['top_drift'] > 0 else K_initial
            stiffness_ratio = K_final / K_initial if K_initial > 0 else 1
        else:
            stiffness_ratio = 1
        
        D_stiffness = 1 - stiffness_ratio
        
        indices['global']['modified_park_ang'] = min(0.7 * D_delta + 0.3 * D_stiffness, 1.0)
        
    elif method == 'kunnath':
        # Metodo Kunnath et al.
        mu = delta_max / delta_y if delta_y > 0 else 1
        
        # Energia normalizzata
        E_norm = 0
        if 'curve' in pushover_results:
            for i, point in enumerate(pushover_results['curve']):
                if i > 0:
                    E_norm += abs(point['base_shear'] * point['top_drift'])
        
        E_norm /= (F_y * delta_y) if F_y * delta_y > 0 else 1
        
        # Parametri calibrati per muratura
        a = 1.1
        c = 0.38
        
        indices['global']['kunnath'] = min((mu - 1) / (a * mu) + c * E_norm / (a * mu), 1.0)
        
    elif method == 'fajfar':
        # Metodo Fajfar
        mu = delta_max / delta_y if delta_y > 0 else 1
        
        if mu <= 1:
            indices['global']['fajfar'] = 0
        elif mu <= 4:
            indices['global']['fajfar'] = (mu - 1) / 3
        else:
            indices['global']['fajfar'] = min(1 + 0.13 * (mu - 4), 1.0)
    
    # Indici locali per elemento
    if 'element_checks' in pushover_results:
        for elem in pushover_results['element_checks']:
            elem_id = elem.get('element_id', f"elem_{elem.get('element_id', 0)}")
            
            # DCR come proxy per danno locale
            DCR_max = elem.get('DCR_max', 0)
            
            if DCR_max < 0.5:
                local_damage = 0
            elif DCR_max < 1.0:
                local_damage = 0.1 + 0.4 * (DCR_max - 0.5) / 0.5
            elif DCR_max < 2.0:
                local_damage = 0.5 + 0.35 * (DCR_max - 1.0)
            else:
                local_damage = min(0.85 + 0.15 * (DCR_max - 2.0) / 2.0, 1.0)
            
            indices['local'][elem_id] = {
                'damage': local_damage,
                'DCR': DCR_max,
                'failure_mode': elem.get('failure_mode', 'unknown'),
                'damage_level': elem.get('damage_level', 'None')
            }
    
    # Classificazione danno globale
    D_global = indices['global'].get(method, indices['global'].get('park_ang', 0))
    
    if D_global < 0.1:
        indices['global']['damage_state'] = 'D0 - No Damage'
    elif D_global < 0.25:
        indices['global']['damage_state'] = 'D1 - Slight'
    elif D_global < 0.4:
        indices['global']['damage_state'] = 'D2 - Moderate'
    elif D_global < 0.6:
        indices['global']['damage_state'] = 'D3 - Extensive'
    elif D_global < 0.8:
        indices['global']['damage_state'] = 'D4 - Very Heavy'
    else:
        indices['global']['damage_state'] = 'D5 - Collapse'
    
    # Statistiche aggiuntive
    if indices['local']:
        local_damages = [elem['damage'] for elem in indices['local'].values()]
        indices['statistics'] = {
            'mean_local_damage': np.mean(local_damages),
            'max_local_damage': np.max(local_damages),
            'std_local_damage': np.std(local_damages),
            'n_damaged_elements': sum(1 for d in local_damages if d > 0.1)
        }
    
    return indices

def calculate_ductility(results: Dict, level: str = 'global') -> Dict:
    """
    Calcola duttilità a diversi livelli.
    
    Args:
        results: Risultati analisi
        level: 'global', 'story', 'element'
        
    Returns:
        Dizionario con valori di duttilità
    """
    ductility = {}
    
    if level == 'global':
        if 'performance_levels' in results:
            delta_y = results['performance_levels'].get('yield', {}).get('top_drift', 0.001)
            delta_u = results['performance_levels'].get('ultimate', {}).get('top_drift', delta_y)
            
            ductility['displacement'] = delta_u / delta_y if delta_y > 0 else 1.0
            
            # Duttilità in curvatura se disponibile
            if 'curvature' in results:
                chi_y = results['curvature'].get('yield', 0.001)
                chi_u = results['curvature'].get('ultimate', chi_y)
                ductility['curvature'] = chi_u / chi_y if chi_y > 0 else 1.0
            
            # Classificazione
            mu = ductility['displacement']
            if mu < 1.5:
                ductility['class'] = 'brittle'
            elif mu < 2.5:
                ductility['class'] = 'limited'
            elif mu < 4.0:
                ductility['class'] = 'moderate'
            else:
                ductility['class'] = 'high'
                
    elif level == 'story':
        # Duttilità di piano
        if 'story_drifts' in results:
            for story, drifts in results['story_drifts'].items():
                if 'yield' in drifts and 'ultimate' in drifts:
                    ductility[story] = drifts['ultimate'] / drifts['yield'] if drifts['yield'] > 0 else 1.0
                    
    elif level == 'element':
        # Duttilità elementi
        if 'element_ductility' in results:
            ductility = results['element_ductility']
        elif 'element_checks' in results:
            for elem in results['element_checks']:
                elem_id = elem.get('element_id', 0)
                # Stima dalla DCR
                DCR = elem.get('DCR_max', 0)
                if DCR > 0:
                    # Relazione empirica DCR-duttilità
                    mu_est = 1.0 + 2.0 * max(0, 1 - 1/DCR) if DCR > 1 else 1.0
                    ductility[f'elem_{elem_id}'] = mu_est
    
    return ductility

def calculate_section_ductility(mc_diagram: Dict) -> Dict:
    """
    Calcola duttilità sezionale da diagramma M-chi.
    
    Args:
        mc_diagram: Diagramma momento-curvatura
        
    Returns:
        Duttilità e parametri caratteristici
    """
    M = np.array(mc_diagram['moment'])
    chi = np.array(mc_diagram['curvature'])
    
    if len(M) < 3:
        return {'mu_chi': 1.0}
        
    # Trova punto di snervamento (primo cambio pendenza significativo)
    # Derivata seconda
    d2M_dchi2 = np.gradient(np.gradient(M))
    
    # Punto di massima variazione di pendenza
    idx_yield = np.argmax(np.abs(d2M_dchi2[1:-1])) + 1
    
    chi_y = chi[idx_yield]
    M_y = M[idx_yield]
    
    # Punto ultimo (85% del massimo momento)
    M_max = np.max(M)
    idx_after_peak = np.where(M > M_max)[0][-1] if np.any(M > M_max) else len(M)-1
    
    M_85 = 0.85 * M_max
    idx_ultimate = idx_after_peak
    
    for i in range(idx_after_peak, len(M)):
        if M[i] <= M_85:
            idx_ultimate = i
            break
            
    chi_u = chi[idx_ultimate]
    
    # Duttilità
    mu_chi = chi_u / chi_y if chi_y > 0 else 1.0
    
    return {
        'mu_chi': mu_chi,
        'chi_y': chi_y,
        'chi_u': chi_u,
        'M_y': M_y,
        'M_max': M_max
    }

# ============================================================================
# ANALISI CICLICHE E ISTERETICHE
# ============================================================================

def extract_hysteretic_params(cyclic_results: Dict) -> Dict:
    """
    Estrae parametri isteretici da analisi ciclica.
    
    Args:
        cyclic_results: Risultati analisi ciclica
        
    Returns:
        Parametri isteretici
    """
    params = {
        'cumulative_energy': 0,
        'equivalent_damping': [],
        'stiffness_degradation': [],
        'strength_degradation': [],
        'pinching_factor': [],
        'residual_deformation': []
    }
    
    if 'cycles' not in cyclic_results:
        return params
    
    # Energia cumulativa
    params['cumulative_energy'] = sum(
        cycle.get('energy', 0) for cycle in cyclic_results['cycles']
    )
    
    # Parametri per ciclo
    K_initial = None
    V_max_initial = None
    
    for i, cycle in enumerate(cyclic_results['cycles']):
        # Rigidezza secante
        if 'stiffness' in cycle:
            K_current = cycle['stiffness']
            if K_initial is None:
                K_initial = K_current
            if K_initial > 0:
                params['stiffness_degradation'].append(K_current / K_initial)
        
        # Resistenza massima
        V_max = max(
            abs(cycle.get('positive', {}).get('base_shear', 0)),
            abs(cycle.get('negative', {}).get('base_shear', 0))
        )
        if V_max_initial is None:
            V_max_initial = V_max
        if V_max_initial > 0:
            params['strength_degradation'].append(V_max / V_max_initial)
        
        # Smorzamento equivalente
        if cycle.get('energy', 0) > 0 and cycle.get('elastic_energy', 0) > 0:
            xi_eq = cycle['energy'] / (4 * np.pi * cycle['elastic_energy'])
            params['equivalent_damping'].append(xi_eq)
        
        # Pinching
        if 'area_ratio' in cycle:
            params['pinching_factor'].append(cycle['area_ratio'])
        
        # Deformazione residua
        if 'residual_drift' in cycle:
            params['residual_deformation'].append(cycle['residual_drift'])
    
    # Parametri medi
    if params['equivalent_damping']:
        params['avg_damping'] = np.mean(params['equivalent_damping'])
    
    if params['stiffness_degradation']:
        # Fit esponenziale per degrado rigidezza
        x = np.arange(len(params['stiffness_degradation']))
        y = np.array(params['stiffness_degradation'])
        if len(x) > 1:
            # k(n) = k0 * exp(-alpha * n)
            log_y = np.log(np.maximum(y, 1e-6))
            alpha = -np.polyfit(x, log_y, 1)[0]
            params['stiffness_degradation_rate'] = alpha
    
    return params

def calculate_cumulative_damage(time_history: Dict, material: MaterialProperties) -> Dict:
    """
    Calcola danno cumulativo da time-history.
    
    Args:
        time_history: Risultati analisi time-history
        material: Proprietà materiale
        
    Returns:
        Indici di danno cumulativo
    """
    damage = {
        'fatigue_index': 0,
        'energy_index': 0,
        'plastic_deformation': 0,
        'n_cycles': 0
    }
    
    if 'displacements' not in time_history:
        return damage
    
    # Converti in array
    displacements = np.array(time_history['displacements'])
    if 'accelerations' in time_history:
        accelerations = np.array(time_history['accelerations'])
    else:
        accelerations = np.zeros_like(displacements)
    
    # Conta cicli (attraversamenti dello zero)
    if displacements.ndim > 1:
        # Usa spostamento del tetto
        roof_disp = displacements[:, -1] if displacements.shape[1] > 0 else displacements
    else:
        roof_disp = displacements
    
    zero_crossings = np.where(np.diff(np.sign(roof_disp)))[0]
    damage['n_cycles'] = len(zero_crossings) // 2
    
    # Indice di fatica (Miner)
    if damage['n_cycles'] > 0:
        # Curva S-N semplificata per muratura
        N_f = 1000  # Cicli a rottura di riferimento
        damage['fatigue_index'] = damage['n_cycles'] / N_f
    
    # Energia dissipata
    if 'energy' in time_history:
        E_total = time_history['energy']
        # Energia di rottura stimata
        E_failure = material.fcm * material.epsilon_cu * 1000  # kJ
        damage['energy_index'] = min(E_total / E_failure, 1.0) if E_failure > 0 else 0
    
    # Deformazione plastica accumulata
    if roof_disp.size > 1:
        # Stima componente plastica (semplificata)
        elastic_limit = 0.001  # 0.1% drift elastico
        plastic_disp = np.maximum(np.abs(roof_disp) - elastic_limit, 0)
        damage['plastic_deformation'] = np.sum(np.abs(np.diff(plastic_disp)))
    
    return damage

# ============================================================================
# ANALISI PROBABILISTICHE
# ============================================================================

def probabilistic_analysis(analysis_func: Callable, 
                          base_params: Dict,
                          uncertain_params: Dict,
                          n_simulations: int = 1000,
                          method: str = 'monte_carlo') -> Dict:
    """
    Analisi probabilistica generica.
    
    Args:
        analysis_func: Funzione di analisi da chiamare
        base_params: Parametri base deterministici
        uncertain_params: Parametri incerti con distribuzioni
        n_simulations: Numero simulazioni
        method: 'monte_carlo', 'latin_hypercube', 'FORM'
        
    Returns:
        Risultati probabilistici
    """
    results = {
        'method': method,
        'n_simulations': n_simulations,
        'samples': [],
        'outputs': [],
        'statistics': {},
        'failure_probability': {}
    }
    
    # Genera campioni
    if method == 'monte_carlo':
        samples = generate_monte_carlo_samples(uncertain_params, n_simulations)
    elif method == 'latin_hypercube':
        samples = generate_latin_hypercube_samples(uncertain_params, n_simulations)
    else:
        raise ValueError(f"Metodo {method} non supportato")
    
    # Esegui simulazioni
    for i, sample in enumerate(samples):
        # Aggiorna parametri
        params = copy.deepcopy(base_params)
        for key, value in sample.items():
            set_nested_dict_value(params, key, value)
        
        try:
            # Esegui analisi
            output = analysis_func(**params)
            results['outputs'].append(output)
            results['samples'].append(sample)
        except Exception as e:
            logger.warning(f"Simulazione {i} fallita: {e}")
            continue
    
    # Statistiche
    if results['outputs']:
        # Estrai variabile di output principale
        output_values = extract_output_values(results['outputs'])
        
        results['statistics'] = {
            'mean': np.mean(output_values),
            'std': np.std(output_values),
            'min': np.min(output_values),
            'max': np.max(output_values),
            'percentiles': {
                '5%': np.percentile(output_values, 5),
                '50%': np.percentile(output_values, 50),
                '95%': np.percentile(output_values, 95)
            }
        }
        
        # Probabilità di failure per diversi limiti
        limits = [0.1, 0.2, 0.3, 0.4, 0.5]
        for limit in limits:
            p_f = np.sum(output_values < limit) / len(output_values)
            results['failure_probability'][f'limit_{limit}'] = p_f
    
    return results

def generate_monte_carlo_samples(params_dist: Dict, n_samples: int) -> List[Dict]:
    """Genera campioni Monte Carlo."""
    samples = []
    
    for _ in range(n_samples):
        sample = {}
        for param, dist in params_dist.items():
            if dist['type'] == 'normal':
                value = np.random.normal(dist['mean'], dist['std'])
            elif dist['type'] == 'lognormal':
                # Parametri lognormale da media e COV
                mean = dist['mean']
                cov = dist.get('cov', 0.1)
                variance = (mean * cov) ** 2
                mu = np.log(mean / np.sqrt(1 + variance/mean**2))
                sigma = np.sqrt(np.log(1 + variance/mean**2))
                value = np.random.lognormal(mu, sigma)
            elif dist['type'] == 'uniform':
                value = np.random.uniform(dist['min'], dist['max'])
            elif dist['type'] == 'beta':
                value = np.random.beta(dist['a'], dist['b'])
                value = dist['min'] + value * (dist['max'] - dist['min'])
            else:
                value = dist.get('mean', dist.get('default', 0))
            
            sample[param] = value
        samples.append(sample)
    
    return samples

def generate_latin_hypercube_samples(params_dist: Dict, n_samples: int) -> List[Dict]:
    """Genera campioni Latin Hypercube."""
    n_params = len(params_dist)
    
    # Crea griglia LHS
    intervals = np.linspace(0, 1, n_samples + 1)
    samples_uniform = np.zeros((n_samples, n_params))
    
    for j in range(n_params):
        perm = np.random.permutation(n_samples)
        for i in range(n_samples):
            lower = intervals[perm[i]]
            upper = intervals[perm[i] + 1]
            samples_uniform[i, j] = np.random.uniform(lower, upper)
    
    # Trasforma in distribuzioni target
    samples = []
    param_names = list(params_dist.keys())
    
    for i in range(n_samples):
        sample = {}
        for j, (param, dist) in enumerate(params_dist.items()):
            u = samples_uniform[i, j]
            
            if dist['type'] == 'normal':
                value = norm.ppf(u, dist['mean'], dist['std'])
            elif dist['type'] == 'lognormal':
                mean = dist['mean']
                cov = dist.get('cov', 0.1)
                variance = (mean * cov) ** 2
                mu = np.log(mean / np.sqrt(1 + variance/mean**2))
                sigma = np.sqrt(np.log(1 + variance/mean**2))
                value = lognorm.ppf(u, sigma, scale=np.exp(mu))
            elif dist['type'] == 'uniform':
                value = dist['min'] + u * (dist['max'] - dist['min'])
            else:
                value = dist.get('mean', 0)
            
            sample[param] = value
        samples.append(sample)
    
    return samples

def reliability_analysis(limit_state_func: Callable,
                        random_vars: Dict,
                        n_simulations: int = 10000) -> Dict:
    """
    Analisi di affidabilità strutturale.
    
    Args:
        limit_state_func: Funzione stato limite g(X) = R - S
        random_vars: Variabili aleatorie con distribuzioni
        n_simulations: Numero simulazioni
        
    Returns:
        Indici di affidabilità
    """
    # Monte Carlo per stato limite
    samples = generate_monte_carlo_samples(random_vars, n_simulations)
    g_values = []
    
    for sample in samples:
        g = limit_state_func(**sample)
        g_values.append(g)
    
    g_values = np.array(g_values)
    
    # Probabilità di failure
    p_f = np.sum(g_values <= 0) / n_simulations
    
    # Indice di affidabilità
    if 0 < p_f < 1:
        beta = -norm.ppf(p_f)
    else:
        beta = np.inf if p_f == 0 else -np.inf
    
    # FORM approximation (se richiesto)
    mean_g = np.mean(g_values)
    std_g = np.std(g_values)
    beta_form = mean_g / std_g if std_g > 0 else np.inf
    
    return {
        'probability_failure': p_f,
        'reliability_index': beta,
        'beta_FORM': beta_form,
        'mean_limit_state': mean_g,
        'std_limit_state': std_g,
        'n_failures': np.sum(g_values <= 0),
        'n_simulations': n_simulations
    }

def probabilistic_limit_analysis(limit_model, loads: Dict, options: Dict) -> Dict:
    """
    Analisi limite probabilistica (Monte Carlo).
    
    Args:
        limit_model: Modello di analisi limite
        loads: Carichi applicati
        options: Opzioni analisi
        
    Returns:
        Risultati probabilistici
    """
    n_simulations = options.get('n_simulations', 1000)
    
    results = {
        'alpha_distribution': [],
        'failure_probability': {},
        'reliability_index': {}
    }
    
    # Parametri con incertezza
    param_variations = {
        'fc': {'mean': limit_model.material.fcm, 'cov': 0.15},
        'weight': {'mean': limit_model.material.weight, 'cov': 0.05},
        'thickness': {'mean': limit_model.geometry['thickness'], 'cov': 0.10}
    }
    
    # Monte Carlo
    for i in range(n_simulations):
        # Campiona parametri
        sampled_params = {}
        for param, stats in param_variations.items():
            mean = stats['mean']
            std = mean * stats['cov']
            sampled_params[param] = np.random.normal(mean, std)
            
        # Aggiorna modello
        temp_material = copy.deepcopy(limit_model.material)
        temp_material.fcm = sampled_params['fc']
        temp_material.weight = sampled_params['weight']
        
        temp_geometry = copy.deepcopy(limit_model.geometry)
        temp_geometry['thickness'] = sampled_params['thickness']
        
        # Analizza
        from .analyses.limit import LimitAnalysis, KinematicMechanism
        temp_model = LimitAnalysis(temp_geometry, temp_material)
        alpha = temp_model._analyze_mechanism(
            KinematicMechanism.OVERTURNING_SIMPLE, loads
        )
        
        results['alpha_distribution'].append(alpha)
        
    # Statistiche
    alpha_array = np.array(results['alpha_distribution'])
    
    # Probabilità di collasso per diversi PGA
    pga_levels = [0.1, 0.2, 0.3, 0.4, 0.5]
    for pga in pga_levels:
        p_failure = np.sum(alpha_array < pga/9.81) / n_simulations
        results['failure_probability'][f'PGA_{pga}g'] = p_failure
        
        # Indice di affidabilità
        if 0 < p_failure < 1:
            beta = -norm.ppf(p_failure)
            results['reliability_index'][f'PGA_{pga}g'] = beta
            
    alpha_clean = alpha_array[np.isfinite(alpha_array) & (alpha_array > 0)]
    
    if alpha_clean.size > 0:
        mean_alpha = np.mean(alpha_clean)
        std_alpha = np.std(alpha_clean)
        cov_alpha = std_alpha / mean_alpha if mean_alpha > 0 else np.nan
        percentiles = {
            '5%': np.percentile(alpha_clean, 5),
            '50%': np.percentile(alpha_clean, 50),
            '95%': np.percentile(alpha_clean, 95)
        }
    else:
        mean_alpha = std_alpha = cov_alpha = np.nan
        percentiles = {'5%': np.nan, '50%': np.nan, '95%': np.nan}
    
    results['statistics'] = {
        'mean': mean_alpha,
        'std': std_alpha,
        'cov': cov_alpha,
        'percentiles': percentiles
    }
    
    return results

# ============================================================================
# ANALISI DI SENSIBILITÀ
# ============================================================================

def sensitivity_analysis(model_func: Callable,
                        base_params: Dict,
                        param_ranges: Dict,
                        method: str = 'local',
                        n_samples: int = 100) -> Dict:
    """
    Analisi di sensibilità parametrica.
    
    Args:
        model_func: Funzione del modello
        base_params: Parametri base
        param_ranges: Range variazione parametri
        method: 'local', 'global', 'morris', 'sobol'
        n_samples: Numero campioni per metodi globali
        
    Returns:
        Indici di sensibilità
    """
    sensitivity = {
        'method': method,
        'parameters': {},
        'rankings': {}
    }
    
    # Output base
    base_output = model_func(**base_params)
    base_value = extract_scalar_output(base_output)
    
    if method == 'local':
        # Sensibilità locale (derivate)
        for param, range_info in param_ranges.items():
            base_val = get_nested_dict_value(base_params, param)
            delta = range_info.get('delta', 0.01 * base_val)
            
            # Perturbazione positiva
            params_plus = copy.deepcopy(base_params)
            set_nested_dict_value(params_plus, param, base_val + delta)
            output_plus = model_func(**params_plus)
            value_plus = extract_scalar_output(output_plus)
            
            # Perturbazione negativa
            params_minus = copy.deepcopy(base_params)
            set_nested_dict_value(params_minus, param, base_val - delta)
            output_minus = model_func(**params_minus)
            value_minus = extract_scalar_output(output_minus)
            
            # Derivata centrale
            derivative = (value_plus - value_minus) / (2 * delta)
            
            # Sensibilità normalizzata
            if base_value != 0 and base_val != 0:
                normalized = derivative * base_val / base_value
            else:
                normalized = 0
            
            sensitivity['parameters'][param] = {
                'derivative': derivative,
                'normalized': normalized,
                'elasticity': abs(normalized)
            }
    
    elif method == 'global':
        # Sensibilità globale (variance-based)
        samples = []
        outputs = []
        
        # Genera campioni
        for _ in range(n_samples):
            sample_params = copy.deepcopy(base_params)
            for param, range_info in param_ranges.items():
                base_val = get_nested_dict_value(base_params, param)
                min_val = range_info.get('min', 0.8 * base_val)
                max_val = range_info.get('max', 1.2 * base_val)
                value = np.random.uniform(min_val, max_val)
                set_nested_dict_value(sample_params, param, value)
            
            output = model_func(**sample_params)
            outputs.append(extract_scalar_output(output))
            samples.append(sample_params)
        
        # Calcola indici di Sobol (approssimati)
        outputs = np.array(outputs)
        total_variance = np.var(outputs)
        
        for param in param_ranges.keys():
            param_values = [get_nested_dict_value(s, param) for s in samples]
            
            # Regressione per stimare effetto principale
            if len(set(param_values)) > 1:  # Evita parametri costanti
                correlation = np.corrcoef(param_values, outputs)[0, 1]
                sensitivity['parameters'][param] = {
                    'correlation': correlation,
                    'variance_contribution': correlation**2,
                    'first_order_index': correlation**2  # Approssimazione
                }
    
    elif method == 'morris':
        # Morris screening
        # Implementazione semplificata
        ee_list = {param: [] for param in param_ranges.keys()}
        
        for _ in range(n_samples // len(param_ranges)):
            # Traiettoria casuale
            trajectory_params = copy.deepcopy(base_params)
            
            for param in param_ranges.keys():
                base_val = get_nested_dict_value(trajectory_params, param)
                delta = param_ranges[param].get('delta', 0.1 * base_val)
                
                # Output prima
                output_before = model_func(**trajectory_params)
                value_before = extract_scalar_output(output_before)
                
                # Perturba parametro
                new_val = base_val + delta * np.random.choice([-1, 1])
                set_nested_dict_value(trajectory_params, param, new_val)
                
                # Output dopo
                output_after = model_func(**trajectory_params)
                value_after = extract_scalar_output(output_after)
                
                # Elementary effect
                ee = (value_after - value_before) / delta
                ee_list[param].append(ee)
        
        # Statistiche Morris
        for param in param_ranges.keys():
            if ee_list[param]:
                sensitivity['parameters'][param] = {
                    'mu': np.mean(ee_list[param]),
                    'mu_star': np.mean(np.abs(ee_list[param])),
                    'sigma': np.std(ee_list[param])
                }
    
    # Ranking parametri
    if sensitivity['parameters']:
        # Ordina per importanza
        importance_metric = 'elasticity' if method == 'local' else 'variance_contribution'
        if method == 'morris':
            importance_metric = 'mu_star'
        
        ranked = sorted(
            sensitivity['parameters'].items(),
            key=lambda x: abs(x[1].get(importance_metric, 0)),
            reverse=True
        )
        
        sensitivity['rankings'] = {
            param: i+1 for i, (param, _) in enumerate(ranked)
        }
    
    return sensitivity

def sensitivity_analysis_limit(limit_model, loads: Dict) -> Dict:
    """
    Analisi di sensibilità per parametri chiave analisi limite.
    
    Args:
        limit_model: Modello analisi limite
        loads: Carichi applicati
        
    Returns:
        Sensibilità parametrica
    """
    from .enums import KinematicMechanism
    base_alpha = limit_model._analyze_mechanism(
        KinematicMechanism.OVERTURNING_SIMPLE, loads
    )
    
    sensitivity = {}
    
    # Parametri da variare
    parameters = {
        'thickness': {'range': [0.8, 1.2], 'unit': 'm'},
        'height': {'range': [0.9, 1.1], 'unit': 'm'},
        'weight': {'range': [0.9, 1.1], 'unit': 'kN/m³'},
        'friction': {'range': [0.5, 1.5], 'unit': '-'}
    }
    
    for param, info in parameters.items():
        alphas = []
        values = np.linspace(info['range'][0], info['range'][1], 10)
        
        for factor in values:
            # Modifica parametro
            temp_model = copy.deepcopy(limit_model)
            
            if param == 'thickness':
                temp_model.geometry['thickness'] *= factor
            elif param == 'height':
                temp_model.geometry['height'] *= factor
            elif param == 'weight':
                temp_model.material.weight *= factor
            elif param == 'friction':
                temp_model.material.mu *= factor
                
            # Ricalcola
            alpha = temp_model._analyze_mechanism(
                KinematicMechanism.OVERTURNING_SIMPLE, loads
            )
            alphas.append(alpha)
            
        # Calcola sensibilità
        d_alpha_d_param = np.gradient(alphas) / np.gradient(values)
        
        sensitivity[param] = {
            'values': values.tolist(),
            'alphas': alphas,
            'gradient': d_alpha_d_param.tolist(),
            'average_sensitivity': np.mean(np.abs(d_alpha_d_param))
        }
        
    return sensitivity

# ============================================================================
# GESTIONE MESH E ELEMENTI
# ============================================================================

def generate_mesh_Q4(geometry: GeometryWall, nx: int, ny: int) -> Dict:
    """
    Genera mesh Q4 per parete.
    
    Args:
        geometry: Geometria parete
        nx: Numero elementi in X
        ny: Numero elementi in Y
        
    Returns:
        Mesh con nodi ed elementi
    """
    mesh = {
        'nodes': [],
        'elements': [],
        'node_sets': {},
        'element_sets': {}
    }
    
    # Dimensioni
    Lx = geometry.length
    Ly = geometry.height
    dx = Lx / nx
    dy = Ly / ny
    
    # Genera nodi
    node_id = 0
    node_map = {}
    
    for j in range(ny + 1):
        for i in range(nx + 1):
            x = i * dx
            y = j * dy
            mesh['nodes'].append({
                'id': node_id,
                'x': x,
                'y': y,
                'z': 0.0
            })
            node_map[(i, j)] = node_id
            node_id += 1
    
    # Genera elementi Q4
    elem_id = 0
    
    for j in range(ny):
        for i in range(nx):
            # Nodi elemento (CCW)
            n1 = node_map[(i, j)]
            n2 = node_map[(i+1, j)]
            n3 = node_map[(i+1, j+1)]
            n4 = node_map[(i, j+1)]
            
            mesh['elements'].append({
                'id': elem_id,
                'type': 'Q4',
                'nodes': [n1, n2, n3, n4],
                'material_id': 0
            })
            elem_id += 1
    
    # Node sets per condizioni al contorno
    mesh['node_sets']['bottom'] = [node_map[(i, 0)] for i in range(nx + 1)]
    mesh['node_sets']['top'] = [node_map[(i, ny)] for i in range(nx + 1)]
    mesh['node_sets']['left'] = [node_map[(0, j)] for j in range(ny + 1)]
    mesh['node_sets']['right'] = [node_map[(nx, j)] for j in range(ny + 1)]
    
    # Gestione aperture
    if hasattr(geometry, 'openings_per_floor'):
        for floor, openings in geometry.openings_per_floor.items():
            for opening in openings:
                # Trova elementi nell'apertura
                x_c = opening.x_center + Lx/2
                x_min = x_c - opening.width/2
                x_max = x_c + opening.width/2
                y_min = opening.y_bottom + floor * geometry.floor_height
                y_max = y_min + opening.height
                
                void_elements = []
                for elem in mesh['elements']:
                    # Centro elemento
                    nodes = elem['nodes']
                    x_elem = np.mean([mesh['nodes'][n]['x'] for n in nodes])
                    y_elem = np.mean([mesh['nodes'][n]['y'] for n in nodes])
                    
                    if x_min <= x_elem <= x_max and y_min <= y_elem <= y_max:
                        void_elements.append(elem['id'])
                
                # Marca elementi vuoti
                for elem_id in void_elements:
                    mesh['elements'][elem_id]['material_id'] = -1  # Vuoto
    
    return mesh

def refine_mesh_adaptive(mesh: Dict, error_estimate: Dict, target_elements: int) -> Dict:
    """
    Raffina mesh adattivamente basandosi su stima errore.
    
    Args:
        mesh: Mesh corrente
        error_estimate: Stima errore per elemento
        target_elements: Numero target elementi
        
    Returns:
        Mesh raffinata
    """
    refined_mesh = copy.deepcopy(mesh)
    
    # Identifica elementi da raffinare
    errors = []
    for elem_id, error in error_estimate.items():
        errors.append((elem_id, error))
    
    # Ordina per errore
    errors.sort(key=lambda x: x[1], reverse=True)
    
    # Raffina top N% elementi
    n_refine = min(len(errors) // 4, target_elements - len(mesh['elements']))
    elements_to_refine = [e[0] for e in errors[:n_refine]]
    
    # Raffinamento (split Q4 in 4 Q4)
    new_nodes = []
    new_elements = []
    
    for elem_id in elements_to_refine:
        elem = refined_mesh['elements'][elem_id]
        if elem['type'] != 'Q4':
            continue
        
        # Nodi elemento
        n = elem['nodes']
        coords = [[refined_mesh['nodes'][ni]['x'], 
                  refined_mesh['nodes'][ni]['y']] for ni in n]
        
        # Crea nodo centrale
        x_c = np.mean([c[0] for c in coords])
        y_c = np.mean([c[1] for c in coords])
        
        new_node_id = len(refined_mesh['nodes']) + len(new_nodes)
        new_nodes.append({
            'id': new_node_id,
            'x': x_c,
            'y': y_c,
            'z': 0.0
        })
        
        # Crea 4 sotto-elementi
        # ... (implementazione dettagliata omessa per brevità)
    
    # Aggiungi nuovi nodi ed elementi
    refined_mesh['nodes'].extend(new_nodes)
    refined_mesh['elements'].extend(new_elements)
    
    return refined_mesh

def compute_shape_functions_Q4(xi: float, eta: float) -> np.ndarray:
    """
    Calcola funzioni di forma Q4.
    
    Args:
        xi, eta: Coordinate naturali [-1, 1]
        
    Returns:
        Vettore funzioni di forma [N1, N2, N3, N4]
    """
    N = np.array([
        (1 - xi) * (1 - eta) / 4,
        (1 + xi) * (1 - eta) / 4,
        (1 + xi) * (1 + eta) / 4,
        (1 - xi) * (1 + eta) / 4
    ])
    return N

def compute_B_matrix_Q4(coords: np.ndarray, xi: float, eta: float) -> Tuple[np.ndarray, float]:
    """
    Calcola matrice B (strain-displacement) per Q4.
    
    Args:
        coords: Coordinate nodali [[x1,y1], [x2,y2], ...]
        xi, eta: Coordinate naturali
        
    Returns:
        B matrix e Jacobiano
    """
    # Derivate funzioni di forma
    dN_dxi = np.array([
        -(1 - eta) / 4,
        (1 - eta) / 4,
        (1 + eta) / 4,
        -(1 + eta) / 4
    ])
    
    dN_deta = np.array([
        -(1 - xi) / 4,
        -(1 + xi) / 4,
        (1 + xi) / 4,
        (1 - xi) / 4
    ])
    
    # Jacobiano
    J = np.zeros((2, 2))
    J[0, 0] = np.dot(dN_dxi, coords[:, 0])
    J[0, 1] = np.dot(dN_dxi, coords[:, 1])
    J[1, 0] = np.dot(dN_deta, coords[:, 0])
    J[1, 1] = np.dot(dN_deta, coords[:, 1])
    
    det_J = np.linalg.det(J)
    
    if abs(det_J) < 1e-10:
        raise ValueError("Jacobiano singolare")
    
    # Inverse Jacobiano
    J_inv = np.linalg.inv(J)
    
    # Derivate globali
    dN_dx = J_inv[0, 0] * dN_dxi + J_inv[0, 1] * dN_deta
    dN_dy = J_inv[1, 0] * dN_dxi + J_inv[1, 1] * dN_deta
    
    # Matrice B
    B = np.zeros((3, 8))
    
    for i in range(4):
        B[0, 2*i] = dN_dx[i]      # eps_xx
        B[1, 2*i+1] = dN_dy[i]    # eps_yy
        B[2, 2*i] = dN_dy[i]      # gamma_xy
        B[2, 2*i+1] = dN_dx[i]
    
    return B, det_J

# ============================================================================
# POST-PROCESSING E VISUALIZZAZIONE
# ============================================================================

def post_process_results(results: Dict, analysis_type: str) -> Dict:
    """
    Post-processa risultati analisi.
    
    Args:
        results: Risultati grezzi
        analysis_type: Tipo di analisi
        
    Returns:
        Risultati processati
    """
    processed = {
        'analysis_type': analysis_type,
        'timestamp': datetime.datetime.now().isoformat(),
        'summary': {},
        'details': {}
    }
    
    if analysis_type == 'pushover':
        # Estrai curve bilineare equivalente
        if 'curve' in results:
            bilinear = extract_bilinear_curve(results['curve'])
            processed['bilinear_curve'] = bilinear
            
            # Parametri chiave
            processed['summary'] = {
                'V_max': max(p['base_shear'] for p in results['curve']),
                'delta_max': max(p['top_drift'] for p in results['curve']),
                'K_initial': bilinear.get('K_elastic', 0),
                'ductility': results.get('ductility', 1.0)
            }
        
        # Performance points
        if 'performance_levels' in results:
            processed['performance_points'] = results['performance_levels']
        
        # Damage assessment
        processed['damage'] = calculate_damage_indices(results)
        
    elif analysis_type == 'modal':
        # Parametri modali
        if 'periods' in results:
            processed['summary'] = {
                'T1': results['periods'][0] if results['periods'] else 0,
                'n_modes': len(results['periods']),
                'mass_participation_x': results.get('total_mass_participation_x', 0),
                'mass_participation_y': results.get('total_mass_participation_y', 0)
            }
        
        # Verifica partecipazione massa
        if processed['summary']['mass_participation_x'] < 0.85:
            processed['warnings'] = processed.get('warnings', [])
            processed['warnings'].append("Massa partecipante X < 85%")
        
    elif analysis_type == 'time_history':
        # Risposta massima
        if 'displacements' in results:
            disp = np.array(results['displacements'])
            processed['summary'] = {
                'max_displacement': np.max(np.abs(disp)),
                'max_drift': results.get('max_drift', 0),
                'max_acceleration': results.get('max_acceleration', 0),
                'base_shear_max': results.get('critical_step', {}).get('base_shear', 0)
            }
        
        # Danno cumulativo
        if 'material' in results:
            processed['cumulative_damage'] = calculate_cumulative_damage(
                results, results['material']
            )
    
    return processed

def extract_bilinear_curve(pushover_curve: List[Dict]) -> Dict:
    """
    Estrae curva bilineare equivalente da pushover.
    
    Args:
        pushover_curve: Punti curva pushover
        
    Returns:
        Parametri curva bilineare
    """
    if len(pushover_curve) < 3:
        return {}
    
    # Estrai arrays
    V = np.array([p['base_shear'] for p in pushover_curve])
    d = np.array([p['top_drift'] for p in pushover_curve])
    
    # Trova punto di massimo
    idx_max = np.argmax(V)
    V_max = V[idx_max]
    d_max = d[idx_max]
    
    # Punto al 70% del massimo (per trovare snervamento)
    V_70 = 0.7 * V_max
    idx_70 = np.argmax(V >= V_70)
    
    # Rigidezza elastica (origine -> 70% Vmax)
    if d[idx_70] > 0:
        K_elastic = V[idx_70] / d[idx_70]
    else:
        K_elastic = V[1] / d[1] if len(V) > 1 and d[1] > 0 else 1000
    
    # Trova snervamento con criterio energetico
    # Area sotto curva = Area bilineare equivalente
    area_actual = np.trapz(V[:idx_max+1], d[:idx_max+1])
    
    # Iterazione per trovare dy
    d_y = d_max / 3  # Stima iniziale
    
    for _ in range(10):
        V_y = K_elastic * d_y
        if V_y > V_max:
            V_y = V_max
            d_y = V_max / K_elastic
        
        # Area bilineare
        area_bilinear = 0.5 * V_y * d_y + V_y * (d_max - d_y)
        
        # Aggiusta d_y
        if area_bilinear > area_actual:
            d_y *= 0.9
        else:
            d_y *= 1.1
        
        if abs(area_bilinear - area_actual) / area_actual < 0.01:
            break
    
    # Rigidezza post-elastica
    if d_max > d_y:
        K_post = (V_max - K_elastic * d_y) / (d_max - d_y)
    else:
        K_post = 0
    
    return {
        'K_elastic': K_elastic,
        'K_post': K_post,
        'd_y': d_y,
        'V_y': K_elastic * d_y,
        'd_max': d_max,
        'V_max': V_max,
        'ductility': d_max / d_y if d_y > 0 else 1.0,
        'alpha': K_post / K_elastic if K_elastic > 0 else 0
    }

def generate_report(results: Dict, format: str = 'text') -> str:
    """
    Genera report risultati.
    
    Args:
        results: Risultati analisi
        format: 'text', 'html', 'json'
        
    Returns:
        Report formattato
    """
    if format == 'json':
        return json.dumps(results, indent=2, default=str)
    
    elif format == 'html':
        html = ['<html><head><title>Report Analisi FEM</title></head><body>']
        html.append('<h1>Report Analisi Strutturale</h1>')
        
        # Summary
        if 'summary' in results:
            html.append('<h2>Sommario</h2>')
            html.append('<table border="1">')
            for key, value in results['summary'].items():
                html.append(f'<tr><td>{key}</td><td>{value}</td></tr>')
            html.append('</table>')
        
        # Performance levels
        if 'performance_levels' in results:
            html.append('<h2>Livelli Prestazionali</h2>')
            html.append('<ul>')
            for level, data in results['performance_levels'].items():
                html.append(f'<li>{level}: drift={data.get("top_drift", 0):.3f}</li>')
            html.append('</ul>')
        
        html.append('</body></html>')
        return '\n'.join(html)
    
    else:  # text
        lines = []
        lines.append("="*70)
        lines.append("REPORT ANALISI STRUTTURALE")
        lines.append("="*70)
        lines.append(f"Data: {datetime.datetime.now()}")
        lines.append("")
        
        # Summary
        if 'summary' in results:
            lines.append("SOMMARIO:")
            lines.append("-"*40)
            for key, value in results['summary'].items():
                lines.append(f"  {key}: {value}")
            lines.append("")
        
        # Performance
        if 'performance_levels' in results:
            lines.append("LIVELLI PRESTAZIONALI:")
            lines.append("-"*40)
            for level, data in results['performance_levels'].items():
                lines.append(f"  {level}:")
                for k, v in data.items():
                    lines.append(f"    {k}: {v}")
            lines.append("")
        
        # Damage
        if 'damage' in results:
            lines.append("VALUTAZIONE DANNO:")
            lines.append("-"*40)
            if 'global' in results['damage']:
                lines.append(f"  Danno globale: {results['damage']['global'].get('damage_state', 'Unknown')}")
            lines.append("")
        
        lines.append("="*70)
        
        return '\n'.join(lines)

# ============================================================================
# VALIDAZIONE E VERIFICHE NORMATIVE
# ============================================================================

def check_ntc2018_compliance(results: Dict, structure_type: str = 'masonry') -> Dict:
    """
    Verifica conformità NTC 2018.
    
    Args:
        results: Risultati analisi
        structure_type: Tipo struttura
        
    Returns:
        Report conformità
    """
    compliance = {
        'verified': True,
        'checks': {},
        'warnings': [],
        'violations': []
    }
    
    # Verifica drifts
    if 'max_drift' in results:
        drift = results['max_drift']
        
        # Limiti NTC per muratura
        limits = {
            'SLO': 0.002,
            'SLD': 0.003,
            'SLV': 0.005
        }
        
        for state, limit in limits.items():
            verified = drift <= limit
            compliance['checks'][f'drift_{state}'] = {
                'value': drift,
                'limit': limit,
                'verified': verified,
                'safety_factor': limit / drift if drift > 0 else float('inf')
            }
            
            if not verified:
                compliance['violations'].append(f"Drift {state} non verificato")
                compliance['verified'] = False
    
    # Verifica resistenze
    if 'element_checks' in results:
        n_failed = sum(1 for e in results['element_checks'] if not e.get('verified', True))
        n_total = len(results['element_checks'])
        
        compliance['checks']['elements'] = {
            'n_verified': n_total - n_failed,
            'n_total': n_total,
            'percentage_verified': (n_total - n_failed) / n_total * 100 if n_total > 0 else 100
        }
        
        if n_failed > 0:
            compliance['warnings'].append(f"{n_failed} elementi non verificati")
            if n_failed / n_total > 0.1:  # Più del 10% non verificato
                compliance['verified'] = False
                compliance['violations'].append("Troppe verifiche locali non soddisfatte")
    
    # Verifica regolarità
    if 'regularity' in results:
        if not results['regularity'].get('in_plan', True):
            compliance['warnings'].append("Irregolarità in pianta")
        if not results['regularity'].get('in_elevation', True):
            compliance['warnings'].append("Irregolarità in elevazione")
    
    return compliance

def classify_seismic_risk(vulnerability: float, hazard: float, exposure: float) -> Dict:
    """
    Classifica rischio sismico.
    
    Args:
        vulnerability: Indice vulnerabilità [0-1]
        hazard: Pericolosità sismica [0-1]
        exposure: Esposizione [0-1]
        
    Returns:
        Classificazione rischio
    """
    # Rischio = V * H * E
    risk = vulnerability * hazard * exposure
    
    # Classificazione
    if risk < 0.1:
        risk_class = 'A'  # Molto basso
    elif risk < 0.25:
        risk_class = 'B'  # Basso
    elif risk < 0.45:
        risk_class = 'C'  # Medio
    elif risk < 0.65:
        risk_class = 'D'  # Alto
    elif risk < 0.85:
        risk_class = 'E'  # Molto alto
    else:
        risk_class = 'F'  # Estremo
    
    # Indice di sicurezza
    IS = 1 - risk
    
    # Tempo di ritorno corrispondente
    if IS > 0:
        TR_C = 475 * IS**(-1.41)  # Relazione empirica
    else:
        TR_C = 30
    
    return {
        'risk_index': risk,
        'risk_class': risk_class,
        'safety_index': IS,
        'return_period': TR_C,
        'components': {
            'vulnerability': vulnerability,
            'hazard': hazard,
            'exposure': exposure
        }
    }

# ============================================================================
# UTILITÀ GEOMETRICHE E NUMERICHE
# ============================================================================

def compute_centroid(points: np.ndarray) -> np.ndarray:
    """Calcola centroide di un poligono."""
    return np.mean(points, axis=0)

def compute_area_polygon(points: np.ndarray) -> float:
    """Calcola area poligono con formula di Shoelace."""
    n = len(points)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i, 0] * points[j, 1]
        area -= points[j, 0] * points[i, 1]
    return abs(area) / 2.0

def compute_inertia_rectangle(b: float, h: float) -> Tuple[float, float]:
    """Calcola momenti d'inerzia rettangolo."""
    Ix = b * h**3 / 12
    Iy = h * b**3 / 12
    return Ix, Iy

def rotate_tensor_2d(tensor: np.ndarray, angle: float) -> np.ndarray:
    """Ruota tensore 2D di un angolo."""
    c = np.cos(angle)
    s = np.sin(angle)
    R = np.array([[c, -s], [s, c]])
    return R @ tensor @ R.T

def principal_values_2d(tensor: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Calcola autovalori e autovettori tensore 2D."""
    eigenvalues, eigenvectors = np.linalg.eig(tensor)
    # Ordina per valore decrescente
    idx = eigenvalues.argsort()[::-1]
    return eigenvalues[idx], eigenvectors[:, idx]

# ============================================================================
# FUNZIONI ANALISI SPECIFICHE
# ============================================================================

def distribute_vertical_loads(loads: Dict, elements: List[Dict]) -> Dict:
    """
    Distribuisce carichi verticali sugli elementi.
    
    Args:
        loads: Carichi totali
        elements: Lista elementi strutturali
        
    Returns:
        Carichi distribuiti per elemento
    """
    total_area = sum(e['geometry'].area for e in elements if e['type'] == 'pier')
    N_total = loads.get('vertical', 0)
    
    distributed = {}
    
    for elem in elements:
        if elem['type'] == 'pier':
            # Proporzionale all'area
            distributed[elem['id']] = N_total * elem['geometry'].area / total_area if total_area > 0 else 0
        else:
            distributed[elem['id']] = 0
            
    return distributed

def get_micro_boundary_conditions(wall_data: Dict) -> Dict:
    """
    Definisce condizioni al contorno per micro-modello.
    
    Args:
        wall_data: Dati parete
        
    Returns:
        Condizioni al contorno
    """
    return {
        'bottom': 'fixed',
        'top': 'free',
        'left': 'free',
        'right': 'free',
        'prescribed_displacements': {},
        'prescribed_forces': {}
    }

def analyze_crack_pattern(micro_results: Dict) -> Dict:
    """
    Analizza pattern di fessurazione.
    
    Args:
        micro_results: Risultati micro-modello
        
    Returns:
        Analisi fessure
    """
    cracks = micro_results.get('crack_pattern', [])
    
    if not cracks:
        return {'n_cracks': 0}
        
    # Classifica fessure
    crack_types = {
        'tensile': 0,
        'sliding': 0,
        'mixed': 0
    }
    
    for crack in cracks:
        crack_types[crack['type']] += 1
        
    # Orientamento prevalente
    orientations = []
    for crack in cracks:
        if 'orientation' in crack:
            orientations.append(crack['orientation'])
            
    if orientations:
        mean_orientation = np.mean(orientations)
        
        if abs(mean_orientation) < 30:
            pattern_type = 'vertical'
        elif abs(mean_orientation - 90) < 30:
            pattern_type = 'horizontal'
        elif 30 <= mean_orientation <= 60:
            pattern_type = 'diagonal_positive'
        else:
            pattern_type = 'diagonal_negative'
    else:
        pattern_type = 'undefined'
        
    return {
        'n_cracks': len(cracks),
        'crack_types': crack_types,
        'pattern_type': pattern_type,
        'total_crack_length': sum(c.get('width', 0) for c in cracks),
        'max_crack_width': max((c.get('width', 0) for c in cracks), default=0)
    }

def compare_constitutive_laws(elements: List[Dict], 
                              material: MaterialProperties,
                              loads: Dict) -> Dict:
    """
    Confronta diversi legami costitutivi.
    
    Args:
        elements: Elementi strutturali
        material: Proprietà materiale
        loads: Carichi applicati
        
    Returns:
        Confronto risultati
    """
    from .enums import ConstitutiveLaw
    laws_to_compare = [
        ConstitutiveLaw.LINEAR,
        ConstitutiveLaw.BILINEAR,
        ConstitutiveLaw.MANDER,
        ConstitutiveLaw.KENT_PARK,
        ConstitutiveLaw.POPOVICS
    ]
    
    comparison = {}
    
    for law in laws_to_compare:
        # Crea modello con legame specifico
        from .analyses.fiber import FiberModel
        temp_model = FiberModel(elements, material, law)
        
        # Analisi pushover veloce
        vertical = distribute_vertical_loads(loads, elements)
        results = temp_model.pushover_analysis(vertical, max_drift=0.03)
        
        # Estrai parametri chiave
        if results['performance_levels']:
            comparison[law.value] = {
                'V_max': max(step['base_shear'] for step in results['curve']),
                'delta_u': results['curve'][-1]['top_drift'] if results['curve'] else 0,
                'ductility': results['performance_levels'].get('collapse', {}).get('ductility', 1.0),
                'n_hinges': len(results.get('hinge_sequence', []))
            }
        else:
            comparison[law.value] = {
                'V_max': 0,
                'delta_u': 0,
                'ductility': 1.0,
                'n_hinges': 0
            }
            
    return comparison

# ============================================================================
# FUNZIONI DI SUPPORTO INTERNE
# ============================================================================

def set_nested_dict_value(d: Dict, key_path: str, value: Any):
    """Imposta valore in dizionario nested."""
    keys = key_path.split('.')
    current = d
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value

def get_nested_dict_value(d: Dict, key_path: str, default: Any = None) -> Any:
    """Ottiene valore da dizionario nested."""
    keys = key_path.split('.')
    current = d
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current

def extract_output_values(outputs: List[Dict]) -> np.ndarray:
    """Estrae valori scalari da lista di output."""
    values = []
    for output in outputs:
        value = extract_scalar_output(output)
        values.append(value)
    return np.array(values)

def extract_scalar_output(output: Dict) -> float:
    """Estrae valore scalare principale da output."""
    # Cerca chiavi comuni
    for key in ['alpha', 'base_shear', 'max_displacement', 'value', 'result']:
        if key in output:
            return float(output[key])
    
    # Se è un numero diretto
    if isinstance(output, (int, float)):
        return float(output)
    
    # Cerca nel summary
    if 'summary' in output and isinstance(output['summary'], dict):
        for key in ['max', 'mean', 'value']:
            if key in output['summary']:
                return float(output['summary'][key])
    
    # Default
    return 0.0

# ============================================================================
# EXPORT/IMPORT
# ============================================================================

def export_to_json(data: Any, filename: str):
    """Esporta dati in JSON."""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def import_from_json(filename: str) -> Dict:
    """Importa dati da JSON."""
    with open(filename, 'r') as f:
        return json.load(f)

def export_to_csv(data: Dict, filename: str):
    """Esporta dati tabulari in CSV."""
    import csv
    
    # Estrai dati tabulari
    if 'curve' in data:
        table_data = data['curve']
    elif 'results' in data:
        table_data = data['results']
    else:
        table_data = [data]
    
    if not table_data:
        return
    
    # Scrivi CSV
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=table_data[0].keys())
        writer.writeheader()
        writer.writerows(table_data)

# ============================================================================
# MAIN E TEST
# ============================================================================

def run_tests():
    """Esegue test di base."""
    print("="*70)
    print("TEST MODULO UTILS")
    print("="*70)
    
    # Test 1: Damage indices
    print("\n1. Test calcolo indici di danno...")
    pushover_results = {
        'curve': [
            {'base_shear': 0, 'top_drift': 0},
            {'base_shear': 100, 'top_drift': 0.001},
            {'base_shear': 200, 'top_drift': 0.005},
            {'base_shear': 150, 'top_drift': 0.01}
        ],
        'performance_levels': {
            'yield': {'base_shear': 100, 'top_drift': 0.001},
            'ultimate': {'base_shear': 200, 'top_drift': 0.005}
        }
    }
    
    damage = calculate_damage_indices(pushover_results)
    print(f"   Park-Ang index: {damage['global'].get('park_ang', 0):.3f}")
    print(f"   Damage state: {damage['global'].get('damage_state', 'Unknown')}")
    
    # Test 2: Ductility
    print("\n2. Test calcolo duttilità...")
    ductility = calculate_ductility(pushover_results)
    print(f"   Duttilità: {ductility.get('displacement', 1.0):.2f}")
    print(f"   Classe: {ductility.get('class', 'unknown')}")
    
    # Test 3: Monte Carlo sampling
    print("\n3. Test generazione campioni Monte Carlo...")
    params = {
        'fc': {'type': 'normal', 'mean': 2.0, 'std': 0.3},
        'E': {'type': 'lognormal', 'mean': 1500, 'cov': 0.15}
    }
    samples = generate_monte_carlo_samples(params, 100)
    print(f"   Generati {len(samples)} campioni")
    print(f"   fc medio: {np.mean([s['fc'] for s in samples]):.2f}")
    
    # Test 4: Mesh generation
    print("\n4. Test generazione mesh...")
    from .geometry import GeometryWall
    wall = GeometryWall(length=5.0, height=3.0, thickness=0.3)
    mesh = generate_mesh_Q4(wall, nx=4, ny=3)
    print(f"   Nodi: {len(mesh['nodes'])}")
    print(f"   Elementi: {len(mesh['elements'])}")
    
    # Test 5: Bilinear curve
    print("\n5. Test estrazione curva bilineare...")
    bilinear = extract_bilinear_curve(pushover_results['curve'])
    print(f"   K_elastic: {bilinear.get('K_elastic', 0):.0f}")
    print(f"   Duttilità: {bilinear.get('ductility', 1.0):.2f}")
    
    print("\n" + "="*70)
    print("TEST COMPLETATI")
    print("="*70)

if __name__ == "__main__":
    run_tests()