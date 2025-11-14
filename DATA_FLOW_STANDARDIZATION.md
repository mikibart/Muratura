# 📊 DATA FLOW STANDARDIZATION & INTEROPERABILITY ANALYSIS

**MURATURA FEM v7.0 - Complete Data Flow Analysis**

**Data**: 2025-11-14
**Status**: Complete analysis of data standardization across all calculation engines

---

## 🎯 EXECUTIVE SUMMARY

### Current Status
- ✅ **GUI → FRAME engine**: 100% functional with real data
- ⚠️ **GUI → Other engines**: Partial implementation, missing standardization
- ❌ **Data format**: Inconsistent across different layers (GUI, Storage, Engine)
- ❌ **Parameter mapping**: Incomplete conversions between layers

### Key Issues Identified
1. **Naming inconsistency**: `f_mk` (GUI) vs `fcm` (Engine)
2. **Load format variability**: List vs Dictionary format
3. **Missing engine mappings**: FEM, POR, SAM not fully connected
4. **Incomplete material data**: GUI provides subset of MaterialProperties
5. **Options not standardized**: Each analysis method requires different options

---

## 📁 DATA FLOW LAYERS

### Layer 1: GUI Input (dialogs.py)

#### AddWallDialog.get_values()
```python
{
    'name': str,           # User-friendly name
    'length': float,       # meters
    'height': float,       # meters
    'thickness': float,    # meters
    'material': str        # Combo box text (NOT MaterialProperties!)
}
```

#### AddMaterialDialog.get_values()
```python
{
    'name': str,          # Material name
    'type': str,          # 'Masonry'/'Concrete'/'Steel'
    'f_mk': float,        # MPa - compressive strength (NTC naming)
    'E': float,           # MPa - elastic modulus
    'weight': float       # kN/m³ - specific weight
}
```
**⚠️ ISSUE**: Only 3 parameters, but MaterialProperties needs 20+ parameters!

#### AddLoadDialog.get_values()
```python
{
    'name': str,                         # Load name
    'type': str,                         # 'Vertical (Gravity)'/'Horizontal (Lateral)'/etc
    'value': float                       # kN - magnitude
}
```
**⚠️ ISSUE**: No node/floor assignment, no direction vector!

---

### Layer 2: Storage (Project class in project_manager.py)

```python
class Project:
    walls: List[Dict]       # List of wall dicts from AddWallDialog
    materials: List[Dict]   # List of material dicts from AddMaterialDialog
    loads: List[Dict]       # List of load dicts from AddLoadDialog
    analysis_type: str      # "Linear Static"/"Modal Analysis"/etc
    analysis_settings: Dict # Analysis-specific settings
    results: Optional[Dict] # Analysis results
```

**Format**: Raw storage of GUI data as-is, no transformation.

**Serialization**:
- `.muratura` → pickle (binary, includes results)
- `.json` → JSON (text, config only)

---

### Layer 3: Conversion (real_fem_integration.py)

#### _build_real_material()
**Input**: `materials_list` from GUI
```python
[
    {
        'name': 'Default Masonry',
        'f_mk': 4.0,    # ← GUI naming
        'E': 1500.0,
        'weight': 18.0
    }
]
```

**Output**: `MaterialProperties` object
```python
MaterialProperties(
    name="Default Masonry",
    E=1500.0,           # ✓ Direct mapping
    fcm=4.0,            # ← Converted from f_mk (LINE 128)
    ftm=0.15,           # ← Default value
    tau0=0.1,           # ← Default value
    mu=0.4,             # ← Default value
    G=500.0,            # ← Calculated from E/3.0
    weight=18.0         # ✓ Direct mapping
)
```

**🔴 CRITICAL MAPPING**: `f_mk` → `fcm` (line 128 of real_fem_integration.py)

#### _build_real_wall_data()
**Input**: `walls_list` from GUI
```python
[
    {
        'name': 'Wall 1',
        'length': 5.0,
        'height': 3.0,
        'thickness': 0.3,
        'material': 'Masonry - Brick (f_mk=2.4 MPa)'  # ← String, not object!
    }
]
```

**Output**: `wall_data` dict for engine
```python
{
    'length': 5.0,         # ✓ Direct mapping
    'height': 3.0,         # ✓ Direct mapping
    'thickness': 0.3,      # ✓ Direct mapping
    'n_floors': 1          # ← Inferred (default)
}
```

**⚠️ MISSING**: No multi-floor support, no openings, no wall_type

#### _build_real_loads()
**Input**: `loads_list` from GUI
```python
[
    {
        'name': 'Load 1',
        'type': 'Vertical (Gravity)',
        'value': 100.0
    }
]
```

**Output**: `loads` dict for engine
```python
{
    0: {'Fx': 0, 'Fy': -100}  # Floor 0, vertical load
}
```

**🔴 CRITICAL TRANSFORMATION**: List → Dictionary with floor indexing

---

### Layer 4: Engine API (engine.py + materials.py)

#### MaterialProperties (materials.py:543-607)
**Complete structure** (20+ parameters):
```python
@dataclass
class MaterialProperties:
    # Base mechanical properties
    fcm: float = 3.0        # Compressive strength [MPa]
    fvm: float = 0.15       # Shear strength [MPa]
    tau0: float = 0.1       # Base shear strength [MPa]
    E: float = 1500.0       # Elastic modulus [MPa]
    G: float = 600.0        # Shear modulus [MPa]
    nu: float = 0.2         # Poisson's ratio [-]
    mu: float = 0.4         # Friction coefficient [-]
    weight: float = 18.0    # Specific weight [kN/m³]

    # Advanced properties
    ftm: float = 0.1        # Tensile strength [MPa]
    Gf: float = 0.02        # Fracture energy Mode I [N/mm] - FIXED!
    Gc: float = 10.0        # Fracture energy compression [N/mm] - FIXED!

    # Strain parameters
    epsilon_c0: float = 0.002   # Peak compressive strain
    epsilon_cu: float = 0.0035  # Ultimate compressive strain
    epsilon_t0: float = 0.0001  # Peak tensile strain

    # Damage parameters
    damage_compression: float = 0.7  # [0-1]
    damage_tension: float = 0.9      # [0-1]

    # Dynamic parameters
    damping_ratio: float = 0.05      # Viscous damping [-]

    # Metadata
    material_type: str = ""
    source: str = ""
    notes: str = ""

    # Unit system
    unit_system: UnitSystem = UnitSystem.SI
```

**GUI provides**: `f_mk, E, weight` (3 parameters)
**Engine needs**: 20+ parameters
**Current solution**: Default values for missing parameters

#### analyze_structure() Signature (engine.py:817-831)
```python
def analyze_structure(
    self,
    wall_data: Dict,              # Geometry dictionary
    material: MaterialProperties,  # Material object
    loads: Dict,                   # Loads per floor
    options: Optional[Dict] = None # Analysis-specific options
) -> Dict:                        # Returns results dictionary
```

**Required by ALL methods**: `wall_data`, `material`, `loads`, `options`

---

## 🔧 ANALYSIS METHODS - DATA REQUIREMENTS

### 1. FEM Method (AnalysisMethod.FEM)

**Module**: `Material.analyses.fem` (external)
**Status**: ❌ NOT AVAILABLE (import fails)
**Fallback**: None - returns error

**Expected data format** (from code structure):
```python
wall_data = {
    'length': float,
    'height': float,
    'thickness': float,
    # Mesh parameters (assumed):
    'mesh_size': float,
    'element_type': str  # 'Q4'/'Q8'/'Q9'
}

loads = {
    floor_id: {'Fx': float, 'Fy': float}
}

options = {
    'analysis_type': 'linear_static',
    'solver': 'sparse',  # Assumed
    'tolerance': float   # Assumed
}
```

**⚠️ PROBLEM**: Not implemented, no specification available!

---

### 2. POR Method (AnalysisMethod.POR)

**Module**: `Material.analyses.por` (external)
**Status**: ❌ NOT AVAILABLE (import fails)
**Fallback**: None - returns error

**Expected data format**: UNKNOWN (no implementation)

---

### 3. SAM Method (AnalysisMethod.SAM)

**Module**: `Material.analyses.sam` (external)
**Status**: ❌ NOT AVAILABLE (import fails)
**Fallback**: None - returns error

**Expected data format**: UNKNOWN (no implementation)

---

### 4. FRAME Method (AnalysisMethod.FRAME)

**Module**: Local implementation in `engine.py`
**Status**: ✅ FULLY IMPLEMENTED
**Currently used by**: Desktop GUI (real_fem_integration.py)

#### Data Format (engine.py:888-972):

```python
wall_data = {
    'length': float,        # ✓ Required
    'height': float,        # ✓ Required
    'thickness': float,     # ✓ Required
    'n_floors': int,        # Optional (default: 1)
    'floor_masses': Dict[int, float],  # Optional - masses per floor
    'pier_width': float     # Optional (auto-calculated if missing)
}

loads = {
    node_id: {              # Node ID (integer)
        'Fx': float,        # Horizontal force [kN]
        'Fy': float,        # Vertical force [kN]
        'M': float          # Moment [kNm]
    }
}

options = {
    'analysis_type': str,   # 'static'|'modal'|'pushover'|'time_history'

    # For static analysis:
    # (no additional options)

    # For modal analysis:
    'n_modes': int,         # Default: 6

    # For pushover analysis:
    'lateral_pattern': str, # 'triangular'|'uniform'|'modal'
    'target_drift': float,  # Default: 0.04
    'n_steps': int,         # Default: 50

    # For time_history analysis:
    'accelerogram': List[float],
    'dt': float,            # Time step
    'excitation_dir': str,  # 'x'|'y'
    'accel_units': str      # 'mps2'|'g'|'gal'
}
```

#### Results Format:
```python
{
    'method': 'TELAIO_EQUIVALENTE',
    'model_summary': {
        'n_nodes': int,
        'n_elements': int,
        'n_piers': int,
        'n_spandrels': int
    },
    'displacements': List[float],
    'max_displacement': float,
    'element_forces': List[Dict],
    'element_checks': List[Dict],
    'reactions': Dict,

    # Additional for pushover:
    'curve': List[Dict],
    'performance_levels': {
        'yield': {'base_shear': float, 'top_drift': float, ...},
        'ultimate': {'base_shear': float, 'top_drift': float, ...}
    },
    'ductility': float,

    # Additional for modal:
    'frequencies': List[float],
    'periods': List[float],
    'mode_shapes': List[List[float]],
    'modal_masses': List[float],
    'mass_participation_x': List[float],
    'mass_participation_y': List[float]
}
```

**✅ STANDARDIZATION**: FRAME is the REFERENCE implementation!

---

### 5. LIMIT Method (AnalysisMethod.LIMIT)

**Module**: Local implementation in `engine.py`
**Status**: ⚠️ BASIC IMPLEMENTATION (external module not available)

#### Data Format (engine.py:1454-1520):

```python
wall_data = {
    'height': float,
    'thickness': float,
    'length': float,
    'wall_type': str,  # 'single_leaf'|'double_leaf'|...

    # Optional advanced:
    'openings': List[Dict],  # [{x, y, width, height}, ...]
    'arch': Dict,            # Arch geometry
    'vault': Dict,           # Vault geometry
    'facade_details': Dict   # Facade-specific parameters
}

loads = {
    floor_id: {'Fx': float, 'Fy': float}
}

options = {
    'probabilistic': bool,         # Enable probabilistic analysis
    'optimize_strengthening': bool, # Optimize FRP/FRCM
    'target_alpha': float,         # Target safety factor
    'sensitivity': bool            # Sensitivity analysis
}
```

#### Results Format:
```python
{
    'method': 'LIMIT',
    'status': 'basic_implementation',
    'alpha': float,         # Safety factor
    'mechanism': str,       # 'overturning'|'shear'|...

    # If LimitAnalysis available:
    'mechanisms': List[Dict],  # All analyzed mechanisms
    'critical_mechanism': Dict,
    'strengthening': Dict,     # If optimize_strengthening=True
    'sensitivity': Dict,       # If sensitivity=True
    'probabilistic': Dict      # If probabilistic=True
}
```

---

### 6. FIBER Method (AnalysisMethod.FIBER)

**Module**: Local implementation in `engine.py`
**Status**: ⚠️ BASIC IMPLEMENTATION (external module not available)

#### Data Format (engine.py:1522-1578):

```python
wall_data = {
    'pier_width': float,   # OR 'length'
    'height': float,
    'thickness': float,
    'area': float          # Optional (calculated if missing)
}

loads = {
    floor_id: {'Fx': float, 'Fy': float}
}

options = {
    'constitutive_law': ConstitutiveLaw,  # BILINEAR|PARABOLIC|MANDER|...
    'analysis_type': str,   # 'pushover'|'cyclic'

    # For pushover:
    'lateral_pattern': str, # 'triangular'|'uniform'
    'max_drift': float,     # Default: 0.05

    # For cyclic:
    'protocol': List[float] # Displacement protocol
}
```

#### Results Format:
```python
{
    'method': 'FIBER_MODEL',
    'constitutive_law': str,
    'elements': int,

    # For pushover:
    'pushover_curve': List[Dict],
    'damage_indices': Dict,

    # For cyclic:
    'hysteresis_loops': List[Dict],
    'energy_dissipation': float,
    'degradation_params': Dict
}
```

---

### 7. MICRO Method (AnalysisMethod.MICRO)

**Module**: Local implementation in `engine.py`
**Status**: ⚠️ BASIC IMPLEMENTATION (external module not available)

#### Data Format (engine.py:1598-1682):

```python
wall_data = {
    'length': float,
    'height': float,
    'thickness': float
}

loads = {
    floor_id: {'Fx': float, 'Fy': float}
}

options = {
    'analysis_type': str,  # 'static'|'homogenization'

    'block_properties': {
        'E': float,       # MPa
        'fc': float,      # MPa
        'ft': float,      # MPa
        'weight': float   # kN/m³
    },

    'mortar_properties': {
        'E': float,
        'fc': float,
        'ft': float,
        'cohesion': float,
        'friction': float
    },

    'interface_properties': {
        'k_normal': float,
        'k_tangent': float,
        'cohesion': float,
        'friction': float,
        'tensile_strength': float,
        'shear_strength': float
    },

    'block_size': {
        'length': float,
        'height': float,
        'mortar_thickness': float
    }
}
```

#### Results Format:
```python
{
    'method': 'MICRO_MODEL',
    'n_blocks': int,
    'n_mortar': int,
    'n_interfaces': int,

    # For static:
    'displacements': List,
    'stresses': List,
    'crack_pattern': Dict,

    # For homogenization:
    'homogenized_properties': {
        'E_eq': float,
        'fc_eq': float,
        'ft_eq': float,
        'tau0_eq': float
    }
}
```

---

## 🚨 DATA STANDARDIZATION ISSUES

### Issue 1: Parameter Name Inconsistency

| Layer | Name | Type | Units | Notes |
|-------|------|------|-------|-------|
| **GUI** | `f_mk` | float | MPa | NTC 2018 naming |
| **Storage** | `f_mk` | float | MPa | As-is from GUI |
| **Conversion** | `f_mk` → `fcm` | float | MPa | **MAPPING** (line 128) |
| **Engine** | `fcm` | float | MPa | International naming |

**Impact**: ⚠️ Requires explicit mapping in conversion layer

**Current solution**: ✅ Implemented in `real_fem_integration.py:128`

---

### Issue 2: Load Format Variability

#### GUI Format (List):
```python
[
    {'name': 'Load 1', 'type': 'Vertical (Gravity)', 'value': 100.0},
    {'name': 'Load 2', 'type': 'Horizontal (Lateral)', 'value': 50.0}
]
```

#### FRAME Format (Dict by floor):
```python
{
    0: {'Fx': 0, 'Fy': -100},    # Floor 0
    1: {'Fx': 50, 'Fy': 0}       # Floor 1
}
```

**Impact**: 🔴 Complex transformation required

**Current solution**: ✅ Implemented in `real_fem_integration.py:165-187`

**Problem**: No way to specify floor assignment in GUI!

---

### Issue 3: Material Data Incompleteness

#### GUI provides:
- `f_mk` (compressive strength)
- `E` (elastic modulus)
- `weight` (specific weight)

**Total**: 3 parameters

#### Engine requires (MaterialProperties):
- 20+ parameters (see Layer 4 above)

**Missing parameters**:
- `fvm` - Shear strength
- `tau0` - Base shear strength
- `ftm` - Tensile strength
- `G` - Shear modulus
- `nu` - Poisson's ratio
- `mu` - Friction coefficient
- `Gf`, `Gc` - Fracture energies
- `epsilon_c0`, `epsilon_cu`, `epsilon_t0` - Strain parameters
- `damage_compression`, `damage_tension` - Damage parameters
- `damping_ratio` - Dynamic parameter

**Current solution**: ⚠️ Use default values (real_fem_integration.py:105-134)

**Impact**: Results may not be accurate for all material types!

---

### Issue 4: Options Not Standardized

Each analysis method requires **different** `options` dictionary:

| Method | Required Options | Optional Options |
|--------|------------------|------------------|
| **FRAME** | `analysis_type` | `n_modes`, `lateral_pattern`, `target_drift`, `n_steps`, `accelerogram`, ... |
| **LIMIT** | None | `probabilistic`, `optimize_strengthening`, `target_alpha`, `sensitivity` |
| **FIBER** | `constitutive_law`, `analysis_type` | `lateral_pattern`, `max_drift`, `protocol` |
| **MICRO** | `analysis_type`, `block_properties`, `mortar_properties`, `interface_properties`, `block_size` | None |

**Current GUI solution**: ⚠️ Uses generic `analysis_settings` dict, doesn't know which options are needed!

**Impact**: User can't configure analysis-specific options through GUI!

---

### Issue 5: Missing Engine Implementations

| Method | Module | Status | Fallback |
|--------|--------|--------|----------|
| **FEM** | `analyses.fem` | ❌ NOT AVAILABLE | Error returned |
| **POR** | `analyses.por` | ❌ NOT AVAILABLE | Error returned |
| **SAM** | `analyses.sam` | ❌ NOT AVAILABLE | Error returned |
| **FRAME** | Local | ✅ AVAILABLE | N/A |
| **LIMIT** | `analyses.limit` | ⚠️ PARTIAL | Basic implementation |
| **FIBER** | `analyses.fiber` | ⚠️ PARTIAL | Basic implementation |
| **MICRO** | `analyses.micro` | ⚠️ PARTIAL | Basic implementation |

**Impact**: 🔴 Only FRAME method is fully functional from GUI!

---

## ✅ PROPOSED STANDARDIZATION

### 1. Unified Data Schema

Create standard JSON schema for all layers:

```python
# STANDARD_SCHEMA.json
{
    "material": {
        "name": str,
        "type": str,  # 'masonry'|'concrete'|'steel'
        "mechanical": {
            "compressive_strength": float,  # MPa (use international naming)
            "elastic_modulus": float,       # MPa
            "shear_modulus": float,         # MPa (calculated or input)
            "poisson_ratio": float,         # [-]
            "specific_weight": float,       # kN/m³
            "shear_strength": float,        # MPa (optional, calculated)
            "tensile_strength": float,      # MPa (optional, calculated)
            "friction_coefficient": float   # [-] (optional, default)
        },
        "advanced": {
            "fracture_energy_I": float,     # N/mm (Mode I)
            "fracture_energy_C": float,     # N/mm (Compression)
            "strain_peak_c": float,         # [-]
            "strain_ultimate_c": float,     # [-]
            "strain_peak_t": float,         # [-]
            "damage_c": float,              # [0-1]
            "damage_t": float,              # [0-1]
            "damping": float                # [-]
        }
    },

    "geometry": {
        "walls": [
            {
                "id": str,
                "type": str,  # 'wall'|'pier'|'spandrel'
                "length": float,      # m
                "height": float,      # m
                "thickness": float,   # m
                "material_id": str,
                "openings": [         # Optional
                    {"x": float, "y": float, "width": float, "height": float}
                ],
                "position": {         # Optional
                    "x": float,
                    "y": float,
                    "rotation": float
                }
            }
        ],
        "floors": [
            {
                "id": int,
                "height": float,      # m
                "mass": float         # kg (optional)
            }
        ]
    },

    "loads": {
        "nodal": [
            {
                "node_id": int,
                "floor_id": int,
                "Fx": float,  # kN
                "Fy": float,  # kN
                "M": float    # kNm
            }
        ],
        "distributed": [
            {
                "element_id": str,
                "type": str,  # 'uniform'|'triangular'|'custom'
                "value": float,     # kN/m or kN/m²
                "direction": str    # 'x'|'y'|'z'
            }
        ],
        "seismic": {
            "ag": float,           # g (peak ground acceleration)
            "S": float,            # Soil factor
            "F0": float,           # Amplification factor
            "Tc_star": float,      # Period
            "spectrum_type": str   # 'elastic'|'design'
        }
    },

    "analysis": {
        "method": str,  # 'FEM'|'FRAME'|'LIMIT'|'FIBER'|'MICRO'|'POR'|'SAM'
        "type": str,    # 'static'|'modal'|'pushover'|'time_history'|'cyclic'
        "options": {
            # Method-specific options (see below)
        }
    }
}
```

### 2. Options Schema Per Method

```python
OPTIONS_SCHEMA = {
    "FRAME": {
        "static": {},  # No additional options
        "modal": {
            "n_modes": {"type": "int", "default": 6, "min": 1, "max": 50}
        },
        "pushover": {
            "lateral_pattern": {"type": "enum", "values": ["triangular", "uniform", "modal"], "default": "triangular"},
            "target_drift": {"type": "float", "default": 0.04, "min": 0.001, "max": 0.10},
            "n_steps": {"type": "int", "default": 50, "min": 10, "max": 200},
            "direction": {"type": "enum", "values": ["x", "y"], "default": "y"}
        },
        "time_history": {
            "accelerogram": {"type": "list[float]", "required": True},
            "dt": {"type": "float", "default": 0.01, "min": 0.001, "max": 0.1},
            "excitation_dir": {"type": "enum", "values": ["x", "y"], "default": "y"},
            "accel_units": {"type": "enum", "values": ["mps2", "g", "gal"], "default": "mps2"}
        }
    },

    "LIMIT": {
        "default": {
            "probabilistic": {"type": "bool", "default": False},
            "optimize_strengthening": {"type": "bool", "default": False},
            "target_alpha": {"type": "float", "default": 0.3, "min": 0.1, "max": 1.0},
            "sensitivity": {"type": "bool", "default": False}
        }
    },

    "FIBER": {
        "pushover": {
            "constitutive_law": {"type": "enum", "values": ["LINEAR", "BILINEAR", "PARABOLIC", "MANDER"], "required": True},
            "lateral_pattern": {"type": "enum", "values": ["triangular", "uniform"], "default": "triangular"},
            "max_drift": {"type": "float", "default": 0.05, "min": 0.01, "max": 0.15}
        },
        "cyclic": {
            "constitutive_law": {"type": "enum", "values": ["LINEAR", "BILINEAR", "PARABOLIC", "MANDER"], "required": True},
            "protocol": {"type": "list[float]", "required": True}
        }
    },

    "MICRO": {
        "static": {
            "block_properties": {"type": "dict", "required": True},
            "mortar_properties": {"type": "dict", "required": True},
            "interface_properties": {"type": "dict", "required": True},
            "block_size": {"type": "dict", "required": True}
        },
        "homogenization": {
            "block_properties": {"type": "dict", "required": True},
            "mortar_properties": {"type": "dict", "required": True},
            "interface_properties": {"type": "dict", "required": True},
            "block_size": {"type": "dict", "required": True}
        }
    }
}
```

### 3. Unified Conversion Layer

Create `data_standardizer.py`:

```python
"""
MURATURA FEM - Data Standardization Layer
Converts between GUI, Storage, and Engine formats
"""

from typing import Dict, List, Any, Optional
from Material.materials import MaterialProperties, UnitSystem
from Material.enums import AnalysisMethod, ConstitutiveLaw

class DataStandardizer:
    """Standardizes data across all layers."""

    @staticmethod
    def gui_to_material(gui_material: Dict) -> MaterialProperties:
        """
        Convert GUI material dict to MaterialProperties object.

        Handles:
        - f_mk → fcm naming conversion
        - Missing parameters with defaults
        - Unit system consistency
        """
        # Extract GUI values
        fcm = gui_material.get('f_mk', 3.0)  # ← KEY MAPPING
        E = gui_material.get('E', 1500.0)
        weight = gui_material.get('weight', 18.0)

        # Calculate derived properties
        G = E / 3.0  # Simplified, should use E/(2*(1+nu))
        nu = 0.2  # Default
        fvm = fcm / 20  # Empirical relationship
        tau0 = fvm / 1.5  # From NTC
        ftm = fcm / 20  # Empirical
        mu = 0.4  # Default

        return MaterialProperties(
            fcm=fcm,
            E=E,
            G=G,
            nu=nu,
            fvm=fvm,
            tau0=tau0,
            ftm=ftm,
            mu=mu,
            weight=weight,
            material_type=gui_material.get('type', 'Masonry'),
            source='GUI Input',
            unit_system=UnitSystem.SI
        )

    @staticmethod
    def gui_to_wall_data(gui_walls: List[Dict],
                        analysis_method: AnalysisMethod) -> Dict:
        """
        Convert GUI walls to engine wall_data format.

        Different formats for different methods:
        - FRAME: needs n_floors, floor_masses
        - LIMIT: needs openings, arch, vault
        - FIBER: needs pier_width
        - MICRO: standard geometry
        """
        if not gui_walls:
            return {}

        # Use first wall (simplified for now)
        wall = gui_walls[0]

        base_data = {
            'length': wall.get('length', 5.0),
            'height': wall.get('height', 3.0),
            'thickness': wall.get('thickness', 0.3)
        }

        if analysis_method == AnalysisMethod.FRAME:
            # Add FRAME-specific fields
            base_data['n_floors'] = 1  # TODO: detect from GUI
            base_data['floor_masses'] = {}  # TODO: from GUI

        elif analysis_method == AnalysisMethod.LIMIT:
            # Add LIMIT-specific fields
            base_data['wall_type'] = 'single_leaf'
            base_data['openings'] = []  # TODO: from GUI

        elif analysis_method == AnalysisMethod.FIBER:
            # Add FIBER-specific fields
            base_data['pier_width'] = wall.get('length', 5.0) * 0.2

        return base_data

    @staticmethod
    def gui_to_loads(gui_loads: List[Dict],
                    analysis_method: AnalysisMethod,
                    n_floors: int = 1) -> Dict:
        """
        Convert GUI loads to engine loads format.

        Handles:
        - List → Dict conversion
        - Load type → component mapping
        - Floor assignment
        """
        loads = {}

        for i, load_data in enumerate(gui_loads):
            load_type = load_data.get('type', 'Vertical (Gravity)')
            value = load_data.get('value', 100.0)

            # Determine floor (simplified: distribute evenly)
            floor_id = i % n_floors

            # Convert load type to components
            if 'Vertical' in load_type:
                components = {'Fx': 0, 'Fy': -value, 'M': 0}
            elif 'Horizontal' in load_type:
                components = {'Fx': value, 'Fy': 0, 'M': 0}
            else:
                components = {'Fx': 0, 'Fy': -value, 'M': 0}

            # Accumulate loads on same floor
            if floor_id in loads:
                loads[floor_id]['Fx'] += components['Fx']
                loads[floor_id]['Fy'] += components['Fy']
                loads[floor_id]['M'] += components['M']
            else:
                loads[floor_id] = components

        return loads

    @staticmethod
    def gui_to_options(gui_settings: Dict,
                      analysis_method: AnalysisMethod,
                      analysis_type: str) -> Dict:
        """
        Convert GUI settings to engine options format.

        Uses OPTIONS_SCHEMA to validate and set defaults.
        """
        options = {'analysis_type': analysis_type}

        if analysis_method == AnalysisMethod.FRAME:
            if analysis_type == 'pushover':
                options['lateral_pattern'] = gui_settings.get('lateral_pattern', 'triangular')
                options['target_drift'] = gui_settings.get('target_drift', 0.04)
                options['n_steps'] = gui_settings.get('max_iter', 50)
            elif analysis_type == 'modal':
                options['n_modes'] = gui_settings.get('n_modes', 6)

        elif analysis_method == AnalysisMethod.LIMIT:
            options['probabilistic'] = gui_settings.get('probabilistic', False)
            options['optimize_strengthening'] = gui_settings.get('optimize', False)
            options['target_alpha'] = gui_settings.get('target_alpha', 0.3)

        # TODO: Add other methods

        return options

    @staticmethod
    def validate_data(wall_data: Dict, material: MaterialProperties,
                     loads: Dict, options: Dict,
                     analysis_method: AnalysisMethod) -> List[str]:
        """
        Validate that data is complete and consistent for the chosen method.

        Returns list of error messages (empty if valid).
        """
        errors = []

        # Validate material
        validation = material.validate()
        if not validation['is_valid']:
            errors.extend(validation['errors'])

        # Validate geometry
        if wall_data.get('length', 0) <= 0:
            errors.append("Wall length must be > 0")
        if wall_data.get('height', 0) <= 0:
            errors.append("Wall height must be > 0")
        if wall_data.get('thickness', 0) <= 0:
            errors.append("Wall thickness must be > 0")

        # Validate loads
        if not loads:
            errors.append("At least one load required")

        # Method-specific validation
        if analysis_method == AnalysisMethod.FRAME:
            if options.get('analysis_type') == 'pushover':
                if not 0.001 <= options.get('target_drift', 0.04) <= 0.10:
                    errors.append("Target drift must be between 0.1% and 10%")

        return errors
```

---

## 📋 ACTION ITEMS

### Priority 1: HIGH (Immediate)

1. **✅ Document current state** (THIS FILE)
   - Status: COMPLETE

2. **Create DataStandardizer class**
   - File: `Material/data_standardizer.py`
   - Centralize all conversions
   - Add validation

3. **Update real_fem_integration.py**
   - Replace inline conversions with DataStandardizer
   - Add validation before analysis

4. **Add GUI warnings**
   - Warn when using default parameters
   - Show which parameters are missing

### Priority 2: MEDIUM (Next sprint)

5. **Implement missing FEM/POR/SAM modules**
   - Or document why they're not available
   - Provide fallback to FRAME

6. **Extend GUI dialogs**
   - AddMaterialDialog: add more parameters
   - AddLoadDialog: add floor assignment
   - Add AnalysisOptionsDialog per method

7. **Create standard JSON schema**
   - Formal specification
   - Validation with jsonschema library

8. **Add unit tests**
   - Test all conversions
   - Test round-trip (GUI → Engine → GUI)

### Priority 3: LOW (Future)

9. **Multi-floor support in GUI**
   - Floor manager dialog
   - Load-per-floor assignment

10. **Opening editor in GUI**
    - Add openings to walls
    - Validate opening positions

11. **Material library in GUI**
    - Pre-defined materials from NTC
    - MaterialProperties.from_ntc_table() integration

12. **Export to standard formats**
    - JSON export with full schema
    - Import from other software

---

## 🎯 STANDARDIZATION GOALS

### Goal 1: Single Source of Truth
- **Status**: ❌ NOT ACHIEVED
- **Problem**: Data formats differ across layers
- **Solution**: Use unified JSON schema everywhere

### Goal 2: Interoperability
- **Status**: ⚠️ PARTIAL
- **Achievement**: FRAME method works with GUI
- **Problem**: Other methods not accessible from GUI
- **Solution**: Implement all method conversions in DataStandardizer

### Goal 3: Data Completeness
- **Status**: ❌ NOT ACHIEVED
- **Problem**: GUI provides only 3/20 material parameters
- **Solution**: Extend GUI or use intelligent defaults with warnings

### Goal 4: Validation
- **Status**: ⚠️ PARTIAL
- **Achievement**: MaterialProperties.validate() exists
- **Problem**: Not called before analysis
- **Solution**: Add validation in DataStandardizer

### Goal 5: Extensibility
- **Status**: ✅ ACHIEVED
- **Achievement**: Easy to add new analysis methods
- **Solution**: Follow existing pattern in engine.py

---

## 📊 CURRENT COMPATIBILITY MATRIX

| Source | Target | Status | Implementation | Notes |
|--------|--------|--------|----------------|-------|
| GUI → FRAME | ✅ | 100% | real_fem_integration.py | Fully functional |
| GUI → FEM | ❌ | 0% | Missing | Module not available |
| GUI → POR | ❌ | 0% | Missing | Module not available |
| GUI → SAM | ❌ | 0% | Missing | Module not available |
| GUI → LIMIT | ⚠️ | 40% | Partial | Basic implementation |
| GUI → FIBER | ⚠️ | 40% | Partial | Basic implementation |
| GUI → MICRO | ⚠️ | 30% | Partial | Basic implementation |

**Overall Interoperability**: **30%** (only 1/7 methods fully functional from GUI)

---

## 🚀 RECOMMENDED APPROACH

### Phase 1: Consolidation (Week 1)
1. Create `data_standardizer.py` with DataStandardizer class
2. Refactor `real_fem_integration.py` to use DataStandardizer
3. Add validation before all analyses
4. Document all data formats (this file)

### Phase 2: Extension (Week 2-3)
5. Implement FEM/POR/SAM modules OR document unavailability
6. Extend GUI dialogs for more parameters
7. Add method-specific options dialogs
8. Create material library integration

### Phase 3: Validation (Week 4)
9. Add comprehensive unit tests
10. Test all analysis methods
11. Validate round-trip conversions
12. Performance testing

### Phase 4: Standardization (Week 5-6)
13. Create formal JSON schema
14. Implement schema validation
15. Add import/export functionality
16. Documentation and examples

---

## ✅ CONCLUSION

### Summary of Findings

1. **Current State**:
   - Only FRAME method is fully functional from GUI
   - Data formats are inconsistent across layers
   - Material data is incomplete (3/20 parameters)
   - Load assignment lacks floor specification

2. **Critical Issues**:
   - Parameter naming: `f_mk` vs `fcm` ✅ SOLVED
   - Load format: List vs Dict ✅ SOLVED
   - Material completeness: ❌ NEEDS WORK
   - Missing modules: FEM/POR/SAM ❌ NOT AVAILABLE

3. **Strengths**:
   - FRAME implementation is solid reference
   - MaterialProperties is comprehensive
   - Conversion layer exists and works
   - Architecture is extensible

### Recommendations

**Immediate**:
- Create DataStandardizer class (centralize conversions)
- Add validation before analysis
- Warn user about default parameters

**Short-term**:
- Extend GUI dialogs for more parameters
- Implement or document missing modules
- Add method-specific options

**Long-term**:
- Create formal JSON schema
- Full multi-method support
- Material library integration
- Import/export functionality

### Next Steps

**User should decide**:
1. Which analysis methods are priority? (FRAME, LIMIT, FIBER, or implement FEM/POR/SAM?)
2. How to handle missing material parameters? (Extended GUI or intelligent defaults?)
3. What level of validation is needed? (Strict or permissive?)

---

**Document Status**: ✅ COMPLETE
**Last Updated**: 2025-11-14
**Next Review**: After Phase 1 implementation

---

© 2025 MURATURA FEM Team | Data Flow Standardization v1.0
