# 🔄 MURATURA FEM - COMPLETE WORKFLOW & ALL METHODS IMPLEMENTATION

**MURATURA FEM v7.0 - Complete End-to-End Workflow**

**Date**: 2025-11-14
**Status**: Implementation Plan for All 7 Analysis Methods
**Goal**: Complete, standardized, interoperable workflow

---

## 🎯 OBIETTIVO

Implementare un flusso di lavoro completo che supporti TUTTI i 7 metodi di analisi:
1. ✅ **FRAME** - Telaio Equivalente (già implementato)
2. ❌ **FEM** - Finite Element Method (da implementare)
3. ❌ **POR** - Pushover on Continuum (da implementare)
4. ❌ **SAM** - Simplified Analysis Method (da implementare)
5. ⚠️ **LIMIT** - Analisi Limite (completare)
6. ⚠️ **FIBER** - Modello a Fibre (completare)
7. ⚠️ **MICRO** - Micro-modellazione (completare)

---

## 📐 STANDARD API - TUTTI I METODI

Ogni metodo deve implementare questa interfaccia standard:

```python
def analyze_<method>(
    wall_data: Dict,
    material: MaterialProperties,
    loads: Dict,
    options: Dict
) -> Dict:
    """
    Standard analysis function signature.

    Args:
        wall_data: Geometry dictionary
            Required: 'length', 'height', 'thickness'
            Optional: method-specific fields
        material: MaterialProperties object (complete)
        loads: Loads dictionary {floor_id: {'Fx', 'Fy', 'M'}}
        options: Analysis options
            Required: 'analysis_type' (str)
            Optional: method-specific options

    Returns:
        Results dictionary with standard structure:
        {
            'method': str,              # Method name
            'success': bool,            # True if converged
            'error': str,               # Error message if failed
            'displacements': ndarray,   # Nodal displacements
            'max_displacement': float,  # Maximum displacement
            'stresses': ndarray,        # Element stresses (if applicable)
            'max_stress': float,        # Maximum stress
            'element_checks': List[Dict],  # Verifications per element
            'performance_levels': Dict,    # Performance points (pushover)
            'frequencies': List[float],    # Modal frequencies (modal)
            'mode_shapes': List,           # Mode shapes (modal)
            # Method-specific additional fields
        }
    """
```

---

## 🔧 IMPLEMENTAZIONE PER METODO

### 1. FRAME - Telaio Equivalente ✅

**Status**: COMPLETO
**File**: `Material/engine.py` (linee 888-972)
**Implementazione**: Locale, embedded in engine

**Caratteristiche**:
- Equivalente frame con maschi e fasce
- Analisi: static, modal, pushover, time_history
- Modello: EquivalentFrame class
- Mesh: auto-generated da geometria
- Verifiche: NTC 2018 complete

**Data requirements**:
```python
wall_data = {
    'length': float,
    'height': float,
    'thickness': float,
    'n_floors': int,            # Optional (default 1)
    'floor_masses': Dict,       # Optional {floor_id: mass_kg}
    'pier_width': float         # Optional (auto-calculated)
}

options = {
    'analysis_type': 'static'|'modal'|'pushover'|'time_history',

    # For pushover:
    'lateral_pattern': 'triangular'|'uniform'|'modal',
    'target_drift': float,
    'n_steps': int,

    # For modal:
    'n_modes': int,

    # For time_history:
    'accelerogram': List[float],
    'dt': float,
    'excitation_dir': 'x'|'y',
    'accel_units': 'mps2'|'g'|'gal'
}
```

**Use in GUI**: ✅ Fully functional via real_fem_integration.py

---

### 2. FEM - Finite Element Method ❌

**Status**: NON IMPLEMENTATO
**File**: `Material/analyses/fem.py` (da creare)
**Type**: Full FEM with Q4/Q8/Q9 elements

**Descrizione**:
- Modello continuo 2D/3D
- Elementi: quadrilaterali (Q4, Q8, Q9)
- Analisi: static, modal, nonlinear
- Mesh: user-defined or auto

**Data requirements**:
```python
wall_data = {
    'length': float,
    'height': float,
    'thickness': float,
    'mesh_size': float,         # Required - element size (m)
    'element_type': str,        # Required - 'Q4'|'Q8'|'Q9'
    'n_elements_x': int,        # Optional (from mesh_size)
    'n_elements_y': int,        # Optional (from mesh_size)
    'openings': List[Dict]      # Optional - holes in mesh
}

options = {
    'analysis_type': 'static'|'modal'|'nonlinear_static',
    'constitutive_law': ConstitutiveLaw,  # For nonlinear
    'solver': 'sparse'|'iterative',
    'max_iter': int,
    'tolerance': float,
    'n_modes': int              # For modal
}
```

**Implementation approach**:
1. Mesh generation (structured grid)
2. Element stiffness matrices (Q4 Gauss integration)
3. Global assembly (sparse matrices)
4. Boundary conditions (penalty or elimination)
5. Solver (scipy.sparse.linalg)
6. Post-processing (stresses, strains)

**Output**:
```python
{
    'method': 'FEM',
    'success': True,
    'mesh': {
        'n_nodes': int,
        'n_elements': int,
        'nodes': ndarray,       # (n_nodes, 2) coordinates
        'elements': ndarray     # (n_elem, 4/8/9) connectivity
    },
    'displacements': ndarray,   # (n_nodes*2,) Ux, Uy per node
    'stresses': ndarray,        # (n_elem, 3) σx, σy, τxy per element
    'strains': ndarray,         # (n_elem, 3) εx, εy, γxy per element
    'max_displacement': float,
    'max_stress': float,
    'element_checks': [...]     # Verification per element
}
```

---

### 3. POR - Pushover on Continuum ❌

**Status**: NON IMPLEMENTATO
**File**: `Material/analyses/por.py` (da creare)
**Type**: Pushover analysis on continuous model

**Descrizione**:
- Pushover su modello continuo (non frame)
- Incremento di carico laterale
- Tracking limit points
- Adattivo (path-following)

**Data requirements**:
```python
wall_data = {
    'length': float,
    'height': float,
    'thickness': float,
    'mesh_size': float,
    'element_type': str
}

options = {
    'analysis_type': 'pushover',
    'lateral_pattern': 'triangular'|'uniform'|'modal',
    'target_drift': float,
    'n_steps': int,
    'constitutive_law': ConstitutiveLaw,
    'path_following': bool,     # Use arc-length method
    'snap_through': bool        # Allow snap-through/back
}
```

**Implementation approach**:
1. Build FEM model (reuse FEM mesh)
2. Incremental lateral load application
3. Newton-Raphson iteration per step
4. Track pushover curve points
5. Identify performance levels (yield, ultimate)
6. Damage tracking (element-wise)

**Output**:
```python
{
    'method': 'POR',
    'success': True,
    'pushover_curve': [
        {'base_shear': float, 'roof_displacement': float, 'step': int},
        ...
    ],
    'performance_levels': {
        'yield': {'base_shear': float, 'roof_displacement': float},
        'ultimate': {'base_shear': float, 'roof_displacement': float}
    },
    'ductility': float,
    'damage_map': ndarray,      # Per-element damage index
    'collapse_mechanism': str   # 'flexure'|'shear'|'combined'
}
```

---

### 4. SAM - Simplified Analysis Method ❌

**Status**: NON IMPLEMENTATO
**File**: `Material/analyses/sam.py` (da creare)
**Type**: Simplified NTC/EC8 method

**Descrizione**:
- Metodo semplificato per verifiche rapide
- Formule chiuse (no FEM)
- Verifica maschi murari secondo NTC
- Verifica globale edificio

**Data requirements**:
```python
wall_data = {
    'length': float,
    'height': float,
    'thickness': float,
    'n_floors': int,
    'openings_ratio': float     # % area openings
}

loads = {
    floor_id: {
        'vertical': float,      # Carico verticale totale piano [kN]
        'seismic': float        # Forza sismica piano [kN]
    }
}

options = {
    'analysis_type': 'sam',
    'seismic_zone': int,        # 1, 2, 3, 4
    'soil_category': str,       # 'A', 'B', 'C', 'D', 'E'
    'behavior_factor': float,   # q (default from regularity)
    'regularity': bool,         # Struttura regolare
    'knowledge_level': str      # 'LC1', 'LC2', 'LC3'
}
```

**Implementation approach**:
1. Calculate pier capacity (NTC formulas)
   - M_Rd = resistenza pressoflessione
   - V_Rd = resistenza taglio (diagonal/sliding)
2. Calculate seismic demand
   - Base shear from spectrum
   - Distribution to floors (triangular)
3. Check D/C ratios per pier
4. Global verification (torsion, soft-story)
5. Drift check

**Formulas**:
```python
# Compressione (NTC 4.5.6.2)
σ_0d = N_Ed / (t * l)
σ_Rd = f_d / (1.5)
check_compression = σ_0d ≤ σ_Rd

# Pressoflessione (NTC 4.5.6.2)
M_Rd = l²·t·f_d / 2 · (1 - σ_0d/f_d)

# Taglio diagonale (NTC 4.5.6.2)
V_Rd,diag = l·t / b · √(f_td·τ_0d)
b = h/l (shear aspect ratio)

# Taglio scorrimento (NTC 4.5.6.2)
V_Rd,slid = l·t·(f_vd0 + μ·σ_0d)
```

**Output**:
```python
{
    'method': 'SAM',
    'success': True,
    'global_verification': {
        'base_shear_capacity': float,       # kN
        'base_shear_demand': float,         # kN
        'safety_factor_global': float,      # V_Rd / V_Ed
        'first_mode_period': float,         # s
        'spectral_acceleration': float      # g
    },
    'pier_verifications': [
        {
            'pier_id': int,
            'N_Ed': float,                  # kN
            'M_Ed': float,                  # kNm
            'V_Ed': float,                  # kN
            'N_Rd': float,
            'M_Rd': float,
            'V_Rd': float,
            'DCR_compression': float,
            'DCR_flexure': float,
            'DCR_shear': float,
            'verified': bool,
            'failure_mode': str             # 'flexure'|'shear_diag'|'shear_slid'
        },
        ...
    ],
    'drift_verification': {
        'max_drift': float,                 # %
        'limit_drift_SLD': float,           # % (0.3% NTC)
        'limit_drift_SLV': float,           # % (0.5% NTC)
        'verified': bool
    }
}
```

---

### 5. LIMIT - Analisi Limite ⚠️

**Status**: BASE IMPLEMENTATA, da completare
**File**: `Material/engine.py` (linee 1454-1520) + esterno `analyses/limit.py`
**Type**: Kinematic limit analysis

**Descrizione**:
- Analisi cinematica dei meccanismi di collasso
- 24 cinematismi EC8 (vedi KinematicMechanism in enums.py)
- Calcolo moltiplicatore α per ogni meccanismo
- Identificazione meccanismo critico

**Current implementation**: Basic fallback
**To complete**:
1. Implementare classe LimitAnalysis completa
2. Tutti i 24 cinematismi EC8
3. Calcolo α per ogni cinematismo
4. Ottimizzazione rinforzi (FRP/FRCM)
5. Analisi probabilistica

**Data requirements**:
```python
wall_data = {
    'length': float,
    'height': float,
    'thickness': float,
    'wall_type': str,           # 'single_leaf'|'double_leaf'|'three_leaf'
    'openings': List[Dict],     # [{x, y, width, height}, ...]
    'arch': Dict,               # {rise, span, thickness} if present
    'vault': Dict,              # {rise, span, type} if present
    'n_floors': int,
    'floor_heights': List[float]
}

options = {
    'analysis_type': 'limit',
    'mechanisms': List[str],    # Which mechanisms to analyze (or 'all')
    'probabilistic': bool,
    'optimize_strengthening': bool,
    'target_alpha': float       # Target safety factor
}
```

**Cinematismi implementare** (priorità):
1. **Out-of-plane** (più critici):
   - OVERTURNING_SIMPLE (ribaltamento semplice)
   - OVERTURNING_COMPOUND (ribaltamento composto)
   - VERTICAL_FLEXURE (flessione verticale)
   - HORIZONTAL_FLEXURE (flessione orizzontale)

2. **In-plane**:
   - ROCKING_PIER (rocking maschio)
   - FLEXURAL_PIER (flessione maschio)
   - DIAGONAL_CRACKING (fessurazione diagonale)

3. **Local**:
   - ARCH_THRUST (spinta archi)
   - PARAPET_OVERTURNING (parapetto)

**Formule**:
```python
# Ribaltamento semplice (overturning)
# Principio dei lavori virtuali: α·F·δ_F = W·δ_W

# Forze stabilizzanti (peso)
W_stab = sum(W_i · x_i)  # Momenti stabilizzanti

# Forze ribaltanti (sisma)
F_destab = sum(F_i · h_i)  # Momenti ribaltanti

# Moltiplicatore
α = W_stab / F_destab

# Verificato se α ≥ α_min (α_min dipende da SL)
```

**Output**:
```python
{
    'method': 'LIMIT',
    'success': True,
    'mechanisms_analyzed': List[str],
    'critical_mechanism': {
        'type': str,                # 'OVERTURNING_SIMPLE'
        'alpha': float,             # Moltiplicatore critico
        'verified': bool,           # α ≥ α_min
        'safety_margin': float,     # (α - α_min) / α_min
        'collapse_description': str # Descrizione meccanismo
    },
    'all_mechanisms': [
        {
            'type': str,
            'alpha': float,
            'verified': bool,
            'activation_sequence': List[str]  # Sequenza rottura
        },
        ...
    ],
    'strengthening': Dict,          # If optimize_strengthening=True
    'probabilistic': Dict           # If probabilistic=True
}
```

---

### 6. FIBER - Modello a Fibre ⚠️

**Status**: BASE IMPLEMENTATA, da completare
**File**: `Material/engine.py` (linee 1522-1578) + esterno `analyses/fiber.py`
**Type**: Fiber section model

**Descrizione**:
- Discretizzazione sezione in fibre
- Legame costitutivo non lineare per fibra
- Integrazione curve M-χ
- Pushover o ciclico

**Current implementation**: Basic fallback
**To complete**:
1. Classe FiberModel completa
2. Discretizzazione sezione
3. Integrazione M-χ
4. Pushover con fibre
5. Analisi ciclica (hysteresis)

**Data requirements**:
```python
wall_data = {
    'pier_width': float,        # Larghezza maschio (sezione)
    'height': float,
    'thickness': float,
    'n_fibers': int             # Numero fibre (default 40)
}

options = {
    'analysis_type': 'pushover'|'cyclic',
    'constitutive_law': ConstitutiveLaw,  # Law per fibre

    # For pushover:
    'lateral_pattern': str,
    'max_drift': float,

    # For cyclic:
    'protocol': List[float]     # Displacement protocol [m]
}
```

**Implementation approach**:
```python
class FiberSection:
    def __init__(self, width, thickness, n_fibers, material):
        # Discretizza sezione in n_fibers
        self.fibers = []
        fiber_width = width / n_fibers

        for i in range(n_fibers):
            x_i = -width/2 + (i + 0.5) * fiber_width
            A_i = fiber_width * thickness
            self.fibers.append({
                'position': x_i,
                'area': A_i,
                'stress': 0.0,
                'strain': 0.0
            })

    def compute_M_chi(self, chi):
        """Compute moment for given curvature."""
        N = 0.0  # Assiale (imposto = 0 per solo M)
        M = 0.0

        # Iterate on fibers
        for fiber in self.fibers:
            # Strain from curvature
            epsilon = chi * fiber['position']

            # Stress from constitutive law
            sigma = self.constitutive_law(epsilon)

            # Update fiber
            fiber['strain'] = epsilon
            fiber['stress'] = sigma

            # Integrate
            N += sigma * fiber['area']
            M += sigma * fiber['area'] * fiber['position']

        # Adjust chi to get N=0 (Newton-Raphson)
        # ...

        return M

    def pushover(self, vertical_load, max_drift):
        """Pushover analysis with fiber model."""
        curve = []

        for step in range(n_steps):
            # Increment lateral displacement
            delta = step * max_drift / n_steps

            # Compute curvature
            chi = delta / (height**2)  # Simplified

            # Compute moment
            M = self.compute_M_chi(chi)

            # Compute base shear
            V = M / height

            curve.append({
                'displacement': delta,
                'base_shear': V,
                'curvature': chi
            })

        return curve
```

**Output**:
```python
{
    'method': 'FIBER',
    'success': True,
    'constitutive_law': str,
    'section': {
        'n_fibers': int,
        'width': float,
        'thickness': float
    },
    'pushover_curve': [
        {'displacement': float, 'base_shear': float, 'curvature': float},
        ...
    ],
    'moment_curvature': [
        {'curvature': float, 'moment': float},
        ...
    ],
    'performance_levels': {
        'yield': {...},
        'ultimate': {...}
    },
    'damage_indices': {
        'ductility': float,
        'energy_dissipation': float,
        'stiffness_degradation': float
    }
}
```

---

### 7. MICRO - Micro-modellazione ⚠️

**Status**: BASE IMPLEMENTATA, da completare
**File**: `Material/engine.py` (linee 1598-1682) + esterno `analyses/micro.py`
**Type**: Detailed micro-model (blocks + mortar + interfaces)

**Descrizione**:
- Modello dettagliato: mattoni, malta, interfacce
- Elementi continui per blocchi e malta
- Elementi interfaccia per giunti
- Analisi statica o omogeneizzazione

**Current implementation**: Basic fallback
**To complete**:
1. Classe MicroModel completa
2. Generazione mesh micro (blocks + mortar)
3. Interfacce Mohr-Coulomb
4. Analisi statica con danneggiamento
5. Omogeneizzazione (REV approach)

**Data requirements**:
```python
wall_data = {
    'length': float,
    'height': float,
    'thickness': float
}

options = {
    'analysis_type': 'static'|'homogenization',

    # Material properties
    'block_properties': {
        'E': float,             # MPa
        'fc': float,            # MPa
        'ft': float,            # MPa
        'weight': float         # kN/m³
    },
    'mortar_properties': {
        'E': float,
        'fc': float,
        'ft': float,
        'cohesion': float,      # MPa
        'friction': float       # tan(φ)
    },
    'interface_properties': {
        'k_normal': float,      # kN/m³ (stiffness)
        'k_tangent': float,     # kN/m³
        'cohesion': float,      # MPa
        'friction': float,      # tan(φ)
        'tensile_strength': float,  # MPa
        'shear_strength': float     # MPa
    },

    # Geometry
    'block_size': {
        'length': float,        # m (es. 0.25)
        'height': float,        # m (es. 0.12)
        'mortar_thickness': float  # m (es. 0.01)
    }
}
```

**Implementation approach**:
```python
class MicroModel:
    def __init__(self, block_props, mortar_props, interface_props):
        self.blocks = []
        self.mortar = []
        self.interfaces = []

    def generate_micro_mesh(self, wall_data, block_size):
        """Generate detailed micro mesh."""
        L = wall_data['length']
        H = wall_data['height']

        b_length = block_size['length']
        b_height = block_size['height']
        m_thick = block_size['mortar_thickness']

        # Rows and columns
        n_rows = int(H / (b_height + m_thick))
        n_cols = int(L / (b_length + m_thick))

        # Create blocks (Q4 elements)
        for row in range(n_rows):
            y_base = row * (b_height + m_thick)

            # Staggered pattern (running bond)
            offset = (b_length / 2) if row % 2 == 1 else 0

            for col in range(n_cols):
                x_base = col * (b_length + m_thick) + offset

                block = create_Q4_element(
                    x=x_base,
                    y=y_base,
                    width=b_length,
                    height=b_height,
                    material=self.block_props
                )
                self.blocks.append(block)

        # Create mortar joints (Q4 elements)
        # Horizontal joints
        for row in range(n_rows - 1):
            y = row * (b_height + m_thick) + b_height
            for col in range(n_cols):
                mortar = create_Q4_element(
                    x=col * (b_length + m_thick),
                    y=y,
                    width=b_length,
                    height=m_thick,
                    material=self.mortar_props
                )
                self.mortar.append(mortar)

        # Create interfaces (zero-thickness elements)
        # Between blocks and mortar
        for block in self.blocks:
            for mortar in self.mortar:
                if are_adjacent(block, mortar):
                    interface = create_interface(
                        block, mortar,
                        properties=self.interface_props
                    )
                    self.interfaces.append(interface)

    def analyze_micro(self, loads, boundary):
        """Micro-scale analysis with interface damage."""
        # Assembly
        K = assemble_stiffness_micro(self.blocks, self.mortar, self.interfaces)
        F = apply_loads(loads)

        # Apply boundary conditions
        K, F = apply_boundary(K, F, boundary)

        # Solve (may need iteration for interface nonlinearity)
        u = solve(K, F)

        # Post-process
        stresses_blocks = compute_stresses(u, self.blocks)
        stresses_mortar = compute_stresses(u, self.mortar)
        interface_status = check_interfaces(u, self.interfaces)

        return {
            'displacements': u,
            'stresses_blocks': stresses_blocks,
            'stresses_mortar': stresses_mortar,
            'interface_damage': interface_status,
            'crack_pattern': identify_cracks(interface_status)
        }

    def homogenization(self):
        """Homogenize micro-model to get equivalent continuum properties."""
        # REV (Representative Element Volume) approach

        # Apply unit strains
        epsilon_xx = apply_unit_strain_x(self)
        epsilon_yy = apply_unit_strain_y(self)
        gamma_xy = apply_unit_shear(self)

        # Compute average stresses
        sigma_xx_avg, sigma_yy_avg, tau_xy_avg = ...

        # Compute equivalent moduli
        E_eq_x = sigma_xx_avg / epsilon_xx
        E_eq_y = sigma_yy_avg / epsilon_yy
        G_eq = tau_xy_avg / gamma_xy

        # Compute equivalent strengths (limit analysis on REV)
        fc_eq = ...
        ft_eq = ...

        return MaterialProperties(
            E=(E_eq_x + E_eq_y) / 2,
            G=G_eq,
            fcm=fc_eq,
            ftm=ft_eq,
            ...
        )
```

**Output**:
```python
{
    'method': 'MICRO',
    'success': True,
    'mesh': {
        'n_blocks': int,
        'n_mortar': int,
        'n_interfaces': int,
        'total_dof': int
    },
    'displacements': ndarray,
    'stresses_blocks': ndarray,
    'stresses_mortar': ndarray,
    'interface_status': [
        {
            'interface_id': int,
            'damaged': bool,
            'crack_opening': float,     # mm
            'sliding': float,           # mm
            'mode': 'tensile'|'shear'|'mixed'
        },
        ...
    ],
    'crack_pattern': {
        'crack_paths': List,            # Continuous crack lines
        'total_crack_length': float,    # mm
        'damage_index': float           # 0-1
    },

    # If homogenization:
    'homogenized_properties': {
        'E_eq': float,
        'G_eq': float,
        'fc_eq': float,
        'ft_eq': float,
        'tau0_eq': float
    }
}
```

---

## 🔄 WORKFLOW COMPLETO END-TO-END

### Step 1: GUI Input
```
User actions:
1. File → New Project
2. Model → Add Material (dialog)
3. Model → Add Wall (dialog)
4. Model → Add Load (dialog)
5. Analysis → Select Method (FRAME/FEM/POR/SAM/LIMIT/FIBER/MICRO)
6. Analysis → Set Options (method-specific dialog)
7. Analysis → Run Analysis
```

### Step 2: Data Standardization
```python
from Material.data_standardizer import convert_gui_to_engine

# Convert GUI project to engine inputs
wall_data, material, loads, options, errors = convert_gui_to_engine(
    gui_project,
    analysis_method
)

# Validate
if errors:
    show_error_dialog(errors)
    return
```

### Step 3: Engine Analysis
```python
from Material import MasonryFEMEngine

# Create engine with selected method
engine = MasonryFEMEngine(method=analysis_method)

# Run analysis (standard API)
results = engine.analyze_structure(wall_data, material, loads, options)

# Check success
if not results.get('success'):
    show_error_dialog(results.get('error'))
    return
```

### Step 4: Results Display
```python
# Display in GUI
display_results_text(results)

# Update plots
if 'pushover_curve' in results:
    plot_pushover(results['pushover_curve'])

if 'mode_shapes' in results:
    plot_modal_shapes(results['mode_shapes'], results['frequencies'])

if 'element_checks' in results:
    plot_verification_table(results['element_checks'])

# Method-specific visualizations
if analysis_method == AnalysisMethod.MICRO:
    plot_crack_pattern(results['crack_pattern'])

if analysis_method == AnalysisMethod.LIMIT:
    plot_mechanism(results['critical_mechanism'])
```

### Step 5: Report Generation
```python
from Material.report import ReportGenerator

# Generate NTC 2018 report
report = ReportGenerator()
report.add_section('Project Info', project_data)
report.add_section('Material Properties', material)
report.add_section('Geometry', wall_data)
report.add_section('Loads', loads)
report.add_section('Analysis Results', results)
report.add_section('Verifications', results['element_checks'])

# Export
report.generate_pdf('report.pdf')
report.generate_docx('report.docx')
```

---

## 📋 IMPLEMENTATION PLAN

### Phase 1: Complete Missing Methods (Week 1-2)

**Priority 1: SAM** (Most useful for practice)
- [ ] Implement analyze_sam()
- [ ] NTC formulas (compression, flexure, shear)
- [ ] Seismic demand from spectrum
- [ ] D/C ratio checks
- [ ] Testing

**Priority 2: LIMIT** (Complete existing)
- [ ] Complete LimitAnalysis class
- [ ] Implement 9 critical mechanisms (out-of-plane + in-plane)
- [ ] Virtual work calculation
- [ ] α calculation per mechanism
- [ ] Testing

**Priority 3: FEM** (Most general)
- [ ] Mesh generation (structured Q4)
- [ ] Element stiffness (Gauss integration)
- [ ] Global assembly (sparse)
- [ ] Solver
- [ ] Post-processing
- [ ] Testing

### Phase 2: Complete Nonlinear Methods (Week 3)

**Priority 4: FIBER**
- [ ] FiberSection class
- [ ] M-χ integration
- [ ] Pushover with fibers
- [ ] Cyclic analysis
- [ ] Testing

**Priority 5: POR**
- [ ] Reuse FEM mesh
- [ ] Incremental pushover
- [ ] Newton-Raphson per step
- [ ] Performance levels
- [ ] Testing

**Priority 6: MICRO**
- [ ] Micro mesh generation (blocks + mortar)
- [ ] Interface elements
- [ ] Damage tracking
- [ ] Homogenization
- [ ] Testing

### Phase 3: Integration & Testing (Week 4)

- [ ] Integrate all methods in engine.py
- [ ] Update DataStandardizer for all methods
- [ ] Update GUI for method selection
- [ ] Method-specific options dialogs
- [ ] Complete workflow testing
- [ ] Documentation

---

## ✅ SUCCESS CRITERIA

1. **All 7 methods implemented** and functional
2. **Standard API** followed by all methods
3. **DataStandardizer** supports all methods
4. **GUI** can launch any method
5. **Results** displayed correctly for each method
6. **Tests** pass for all methods
7. **Documentation** complete
8. **Workflow** smooth end-to-end

---

**Next Action**: Start implementing SAM (simplest and most useful)

---

© 2025 MURATURA FEM Team | Complete Workflow Specification v1.0
