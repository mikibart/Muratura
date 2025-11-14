"""
MURATURA FEM - Data Standardization Layer
==========================================

Centralizes all data conversions between GUI, Storage, and Engine layers.
Ensures data consistency and interoperability across all analysis methods.

Usage:
    from Material.data_standardizer import DataStandardizer

    # Convert GUI data to engine format
    material = DataStandardizer.gui_to_material(gui_material_dict)
    wall_data = DataStandardizer.gui_to_wall_data(gui_walls, method)
    loads = DataStandardizer.gui_to_loads(gui_loads, method, n_floors)
    options = DataStandardizer.gui_to_options(gui_settings, method, analysis_type)

    # Validate before analysis
    errors = DataStandardizer.validate_data(wall_data, material, loads, options, method)
    if errors:
        print("Validation errors:", errors)

Author: MURATURA FEM Team
Version: 1.0.0
Date: 2025-11-14
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import asdict
import logging

from .materials import MaterialProperties, UnitSystem
from .enums import AnalysisMethod, ConstitutiveLaw

logger = logging.getLogger(__name__)


class DataStandardizer:
    """
    Standardizes data across all layers (GUI, Storage, Engine).

    Responsibilities:
    - Convert GUI formats to Engine API formats
    - Handle parameter name mappings (f_mk → fcm)
    - Provide intelligent defaults for missing parameters
    - Validate data completeness and consistency
    - Support all analysis methods (FRAME, LIMIT, FIBER, MICRO, FEM, POR, SAM)
    """

    # ========================================================================
    # PARAMETER MAPPINGS
    # ========================================================================

    # GUI parameter names → MaterialProperties parameter names
    MATERIAL_MAPPING = {
        'f_mk': 'fcm',         # NTC naming → International naming
        'f_m': 'fcm',          # Alternative
        'compressive_strength': 'fcm',
        'E': 'E',              # Direct mapping
        'elastic_modulus': 'E',
        'weight': 'weight',    # Direct mapping
        'specific_weight': 'weight',
        'gamma': 'weight',     # Alternative
    }

    # Load type strings → Force components
    LOAD_TYPE_MAPPING = {
        'Vertical (Gravity)': {'Fx': 0, 'Fy': -1, 'M': 0},
        'Vertical': {'Fx': 0, 'Fy': -1, 'M': 0},
        'Gravity': {'Fx': 0, 'Fy': -1, 'M': 0},
        'Horizontal (Lateral)': {'Fx': 1, 'Fy': 0, 'M': 0},
        'Horizontal': {'Fx': 1, 'Fy': 0, 'M': 0},
        'Lateral': {'Fx': 1, 'Fy': 0, 'M': 0},
        'Seismic X': {'Fx': 1, 'Fy': 0, 'M': 0},
        'Seismic Y': {'Fx': 0, 'Fy': 1, 'M': 0},
        'Distributed': {'Fx': 0, 'Fy': -1, 'M': 0},
    }

    # ========================================================================
    # MATERIAL CONVERSION
    # ========================================================================

    @classmethod
    def gui_to_material(cls, gui_material: Dict,
                       warn_defaults: bool = True) -> MaterialProperties:
        """
        Convert GUI material dict to MaterialProperties object.

        Handles:
        - Parameter name mapping (f_mk → fcm)
        - Missing parameters with intelligent defaults
        - Unit system consistency
        - Warnings for default values

        Args:
            gui_material: Material dictionary from GUI
                Expected keys: 'name', 'type', 'f_mk', 'E', 'weight'
                Optional keys: 'f_vm', 'tau0', 'f_tm', 'G', 'nu', 'mu'
            warn_defaults: If True, log warnings for default parameters

        Returns:
            MaterialProperties object ready for engine

        Example:
            >>> gui_mat = {'name': 'Brick', 'f_mk': 2.4, 'E': 1500, 'weight': 18}
            >>> material = DataStandardizer.gui_to_material(gui_mat)
            >>> material.fcm  # 2.4 (converted from f_mk)
        """
        # Extract GUI values with mapping
        fcm = cls._get_mapped_value(gui_material, ['f_mk', 'f_m', 'compressive_strength'], 3.0)
        E = cls._get_mapped_value(gui_material, ['E', 'elastic_modulus'], 1500.0)
        weight = cls._get_mapped_value(gui_material, ['weight', 'specific_weight', 'gamma'], 18.0)

        # Optional direct parameters
        fvm = gui_material.get('f_vm', None)
        tau0 = gui_material.get('tau0', None)
        ftm = gui_material.get('f_tm', None)
        G = gui_material.get('G', None)
        nu = gui_material.get('nu', 0.2)
        mu = gui_material.get('mu', 0.4)

        # Calculate derived properties with intelligent defaults
        defaults_used = []

        # Shear modulus
        if G is None:
            if nu is not None and nu > 0:
                G = E / (2 * (1 + nu))
            else:
                G = E / 3.0  # Simplified default
            defaults_used.append('G')

        # Shear strength (empirical relationships)
        if fvm is None:
            fvm = fcm / 20  # Typical masonry relationship
            defaults_used.append('fvm')

        if tau0 is None:
            tau0 = fvm / 1.5  # From NTC empirical rule
            defaults_used.append('tau0')

        # Tensile strength
        if ftm is None:
            ftm = fcm / 20  # Typical masonry relationship
            defaults_used.append('ftm')

        # Fracture energies (Hillerborg-based)
        Gf = 0.025 * (ftm ** 0.7) if ftm > 0 else 0.02
        Gc = 15 * (fcm ** 0.7) if fcm > 0 else 10

        # Strain parameters (NTC defaults)
        epsilon_c0 = 0.002
        epsilon_cu = 0.0035
        epsilon_t0 = ftm / E if E > 0 else 0.0001

        # Log warnings if requested
        if warn_defaults and defaults_used:
            logger.warning(
                f"Material '{gui_material.get('name', 'Unknown')}': "
                f"Using default values for: {', '.join(defaults_used)}"
            )

        return MaterialProperties(
            fcm=fcm,
            fvm=fvm,
            tau0=tau0,
            E=E,
            G=G,
            nu=nu,
            mu=mu,
            weight=weight,
            ftm=ftm,
            Gf=Gf,
            Gc=Gc,
            epsilon_c0=epsilon_c0,
            epsilon_cu=epsilon_cu,
            epsilon_t0=epsilon_t0,
            damage_compression=0.7,
            damage_tension=0.9,
            damping_ratio=0.05,
            material_type=gui_material.get('type', 'Masonry'),
            source='GUI Input',
            notes=f"Converted from GUI (defaults: {', '.join(defaults_used) if defaults_used else 'none'})",
            unit_system=UnitSystem.SI
        )

    @staticmethod
    def _get_mapped_value(data: Dict, keys: List[str], default: float) -> float:
        """Get value from dict with fallback through multiple possible keys."""
        for key in keys:
            if key in data and data[key] is not None:
                return float(data[key])
        return default

    # ========================================================================
    # GEOMETRY CONVERSION
    # ========================================================================

    @classmethod
    def gui_to_wall_data(cls, gui_walls: List[Dict],
                        analysis_method: AnalysisMethod,
                        analysis_type: Optional[str] = None) -> Dict:
        """
        Convert GUI walls to engine wall_data format.

        Different analysis methods require different wall_data formats:
        - FRAME: needs n_floors, floor_masses, pier_width
        - LIMIT: needs openings, arch, vault, wall_type
        - FIBER: needs pier_width, area
        - MICRO: standard geometry
        - FEM/POR/SAM: standard geometry (assumed)

        Args:
            gui_walls: List of wall dictionaries from GUI
                Expected keys: 'name', 'length', 'height', 'thickness'
                Optional: 'material', 'openings', 'position'
            analysis_method: Target analysis method
            analysis_type: Specific analysis type (e.g., 'pushover', 'modal')

        Returns:
            wall_data dictionary in engine format

        Example:
            >>> gui_walls = [{'length': 5.0, 'height': 3.0, 'thickness': 0.3}]
            >>> wall_data = DataStandardizer.gui_to_wall_data(gui_walls, AnalysisMethod.FRAME)
            >>> wall_data['n_floors']  # 1 (inferred)
        """
        if not gui_walls:
            logger.warning("No walls provided, using default geometry")
            return {
                'length': 5.0,
                'height': 3.0,
                'thickness': 0.3
            }

        # Use first wall as base (TODO: handle multiple walls)
        wall = gui_walls[0]

        base_data = {
            'length': wall.get('length', 5.0),
            'height': wall.get('height', 3.0),
            'thickness': wall.get('thickness', 0.3)
        }

        # Method-specific additions
        if analysis_method == AnalysisMethod.FRAME:
            # Infer number of floors from total height
            total_height = sum(w.get('height', 3.0) for w in gui_walls)
            typical_floor_height = 3.0
            n_floors = max(1, int(round(total_height / typical_floor_height)))

            base_data['n_floors'] = n_floors

            # Floor masses (if not provided, leave empty for default handling)
            base_data['floor_masses'] = {}

            # Pier width (auto-calculated if not provided)
            if 'pier_width' not in wall:
                # 20% of length, clamped between 0.3m and 1.0m
                pier_width = max(0.3, min(1.0, 0.2 * base_data['length']))
                base_data['pier_width'] = pier_width

        elif analysis_method == AnalysisMethod.LIMIT:
            # LIMIT-specific fields
            base_data['wall_type'] = wall.get('wall_type', 'single_leaf')

            # Openings
            base_data['openings'] = wall.get('openings', [])

            # Arch/Vault/Facade details if present
            if 'arch' in wall:
                base_data['arch'] = wall['arch']
            if 'vault' in wall:
                base_data['vault'] = wall['vault']
            if 'facade_details' in wall:
                base_data.update(wall['facade_details'])

        elif analysis_method == AnalysisMethod.FIBER:
            # FIBER-specific fields
            if 'pier_width' not in wall:
                # Estimate pier width as 20% of length
                base_data['pier_width'] = base_data['length'] * 0.2

            # Area (if not provided, calculated from geometry)
            base_data['area'] = base_data.get('pier_width', 1.0) * base_data['thickness']

        elif analysis_method == AnalysisMethod.MICRO:
            # MICRO uses standard geometry (no additions needed)
            pass

        elif analysis_method in (AnalysisMethod.FEM, AnalysisMethod.POR, AnalysisMethod.SAM):
            # FEM/POR/SAM assumed to use standard geometry
            # (actual requirements unknown as modules not available)
            pass

        return base_data

    # ========================================================================
    # LOADS CONVERSION
    # ========================================================================

    @classmethod
    def gui_to_loads(cls, gui_loads: List[Dict],
                    analysis_method: AnalysisMethod,
                    n_floors: int = 1) -> Dict:
        """
        Convert GUI loads to engine loads format.

        Handles:
        - List → Dict conversion (floor-indexed)
        - Load type string → force components
        - Floor assignment (currently simplified)

        Args:
            gui_loads: List of load dictionaries from GUI
                Expected keys: 'name', 'type', 'value'
                Optional: 'floor', 'node', 'direction'
            analysis_method: Target analysis method
            n_floors: Number of floors for distribution

        Returns:
            loads dictionary in engine format {floor_id: {Fx, Fy, M}}

        Example:
            >>> gui_loads = [{'type': 'Vertical (Gravity)', 'value': 100.0}]
            >>> loads = DataStandardizer.gui_to_loads(gui_loads, AnalysisMethod.FRAME)
            >>> loads[0]  # {'Fx': 0, 'Fy': -100, 'M': 0}
        """
        if not gui_loads:
            logger.warning("No loads provided, using default load")
            return {0: {'Fx': 0, 'Fy': -100, 'M': 0}}

        loads = {}

        for i, load_data in enumerate(gui_loads):
            load_type = load_data.get('type', 'Vertical (Gravity)')
            value = load_data.get('value', 100.0)

            # Floor assignment
            # Priority: explicit 'floor' key > distribute evenly
            if 'floor' in load_data:
                floor_id = int(load_data['floor'])
            else:
                # Distribute loads evenly across floors
                floor_id = i % n_floors

            # Convert load type to components
            components = cls._load_type_to_components(load_type, value)

            # Accumulate loads on same floor
            if floor_id in loads:
                loads[floor_id]['Fx'] += components['Fx']
                loads[floor_id]['Fy'] += components['Fy']
                loads[floor_id]['M'] += components['M']
            else:
                loads[floor_id] = components.copy()

        return loads

    @classmethod
    def _load_type_to_components(cls, load_type: str, value: float) -> Dict[str, float]:
        """Convert load type string to force components."""
        # Check for exact match first
        if load_type in cls.LOAD_TYPE_MAPPING:
            template = cls.LOAD_TYPE_MAPPING[load_type]
        else:
            # Fuzzy match (contains)
            template = None
            for key, tmpl in cls.LOAD_TYPE_MAPPING.items():
                if key.lower() in load_type.lower():
                    template = tmpl
                    break

            if template is None:
                logger.warning(f"Unknown load type '{load_type}', assuming vertical")
                template = {'Fx': 0, 'Fy': -1, 'M': 0}

        return {
            'Fx': template['Fx'] * value,
            'Fy': template['Fy'] * value,
            'M': template['M'] * value
        }

    # ========================================================================
    # OPTIONS CONVERSION
    # ========================================================================

    @classmethod
    def gui_to_options(cls, gui_settings: Dict,
                      analysis_method: AnalysisMethod,
                      analysis_type: str) -> Dict:
        """
        Convert GUI settings to engine options format.

        Different methods and analysis types require different options.
        Uses intelligent defaults for missing values.

        Args:
            gui_settings: Settings dictionary from GUI
                Common keys: 'max_iter', 'tolerance', 'lateral_pattern', ...
            analysis_method: Target analysis method
            analysis_type: Specific analysis type ('static', 'modal', 'pushover', ...)

        Returns:
            options dictionary in engine format

        Example:
            >>> settings = {'lateral_pattern': 'triangular', 'max_iter': 50}
            >>> options = DataStandardizer.gui_to_options(
            ...     settings, AnalysisMethod.FRAME, 'pushover'
            ... )
            >>> options['analysis_type']  # 'pushover'
        """
        options = {'analysis_type': analysis_type}

        if analysis_method == AnalysisMethod.FRAME:
            if analysis_type == 'pushover':
                options['lateral_pattern'] = gui_settings.get('lateral_pattern', 'triangular')
                options['target_drift'] = gui_settings.get('target_drift', 0.04)
                options['n_steps'] = gui_settings.get('max_iter', 50)
                options['direction'] = gui_settings.get('direction', 'y')

            elif analysis_type == 'modal':
                options['n_modes'] = gui_settings.get('n_modes', 6)

            elif analysis_type == 'time_history':
                # Requires accelerogram (must be in gui_settings)
                if 'accelerogram' not in gui_settings:
                    raise ValueError("time_history analysis requires 'accelerogram' in settings")
                options['accelerogram'] = gui_settings['accelerogram']
                options['dt'] = gui_settings.get('dt', 0.01)
                options['excitation_dir'] = gui_settings.get('excitation_dir', 'y')
                options['accel_units'] = gui_settings.get('accel_units', 'mps2')

        elif analysis_method == AnalysisMethod.LIMIT:
            options['probabilistic'] = gui_settings.get('probabilistic', False)
            options['optimize_strengthening'] = gui_settings.get('optimize_strengthening', False)
            options['target_alpha'] = gui_settings.get('target_alpha', 0.3)
            options['sensitivity'] = gui_settings.get('sensitivity', False)

        elif analysis_method == AnalysisMethod.FIBER:
            # Constitutive law (required for FIBER)
            law_str = gui_settings.get('constitutive_law', 'BILINEAR')
            try:
                options['constitutive_law'] = ConstitutiveLaw[law_str]
            except KeyError:
                logger.warning(f"Unknown constitutive law '{law_str}', using BILINEAR")
                options['constitutive_law'] = ConstitutiveLaw.BILINEAR

            if analysis_type == 'pushover':
                options['lateral_pattern'] = gui_settings.get('lateral_pattern', 'triangular')
                options['max_drift'] = gui_settings.get('max_drift', 0.05)

            elif analysis_type == 'cyclic':
                if 'protocol' not in gui_settings:
                    # Default cyclic protocol
                    options['protocol'] = [0.001, 0.002, 0.005, 0.01, 0.02, 0.03]
                else:
                    options['protocol'] = gui_settings['protocol']

        elif analysis_method == AnalysisMethod.MICRO:
            # MICRO requires detailed material properties
            # Check if provided, otherwise use defaults
            options['block_properties'] = gui_settings.get('block_properties', {
                'E': 2000.0,
                'fc': 6.0,
                'ft': 0.3,
                'weight': 20.0
            })

            options['mortar_properties'] = gui_settings.get('mortar_properties', {
                'E': 800.0,
                'fc': 1.5,
                'ft': 0.1,
                'cohesion': 0.1,
                'friction': 0.6
            })

            options['interface_properties'] = gui_settings.get('interface_properties', {
                'k_normal': 1e6,
                'k_tangent': 1e5,
                'cohesion': 0.1,
                'friction': 0.6,
                'tensile_strength': 0.05,
                'shear_strength': 0.1
            })

            options['block_size'] = gui_settings.get('block_size', {
                'length': 0.25,
                'height': 0.12,
                'mortar_thickness': 0.01
            })

        elif analysis_method in (AnalysisMethod.FEM, AnalysisMethod.POR, AnalysisMethod.SAM):
            # Unknown options (modules not available)
            # Pass through any provided settings
            options.update(gui_settings)

        return options

    # ========================================================================
    # VALIDATION
    # ========================================================================

    @classmethod
    def validate_data(cls, wall_data: Dict, material: MaterialProperties,
                     loads: Dict, options: Dict,
                     analysis_method: AnalysisMethod) -> List[str]:
        """
        Validate that data is complete and consistent for the chosen method.

        Checks:
        - Material validity (using MaterialProperties.validate())
        - Geometry constraints (positive dimensions)
        - Load completeness (at least one load)
        - Method-specific requirements

        Args:
            wall_data: Wall geometry dictionary
            material: MaterialProperties object
            loads: Loads dictionary
            options: Options dictionary
            analysis_method: Analysis method to validate for

        Returns:
            List of error messages (empty list if valid)

        Example:
            >>> errors = DataStandardizer.validate_data(
            ...     wall_data, material, loads, options, AnalysisMethod.FRAME
            ... )
            >>> if errors:
            ...     print("Validation failed:", errors)
        """
        errors = []

        # 1. Validate material
        validation = material.validate()
        if not validation['is_valid']:
            errors.extend([f"Material: {e}" for e in validation['errors']])

        # 2. Validate geometry
        length = wall_data.get('length', 0)
        height = wall_data.get('height', 0)
        thickness = wall_data.get('thickness', 0)

        if length <= 0:
            errors.append("Wall length must be > 0")
        if height <= 0:
            errors.append("Wall height must be > 0")
        if thickness <= 0:
            errors.append("Wall thickness must be > 0")

        # Geometric reasonableness
        if length > 100:
            errors.append(f"Wall length {length}m seems unreasonably large (>100m)")
        if height > 50:
            errors.append(f"Wall height {height}m seems unreasonably large (>50m)")
        if thickness > 2:
            errors.append(f"Wall thickness {thickness}m seems unreasonably large (>2m)")
        if thickness < 0.1:
            errors.append(f"Wall thickness {thickness}m seems unreasonably small (<0.1m)")

        # 3. Validate loads
        if not loads:
            errors.append("At least one load is required")
        else:
            for floor_id, load in loads.items():
                total_force = abs(load.get('Fx', 0)) + abs(load.get('Fy', 0))
                if total_force == 0:
                    errors.append(f"Load on floor {floor_id} has zero magnitude")

        # 4. Method-specific validation
        if analysis_method == AnalysisMethod.FRAME:
            analysis_type = options.get('analysis_type', 'static')

            if analysis_type == 'pushover':
                target_drift = options.get('target_drift', 0.04)
                if not 0.001 <= target_drift <= 0.10:
                    errors.append(f"Target drift {target_drift} out of valid range [0.001, 0.10]")

                n_steps = options.get('n_steps', 50)
                if not 10 <= n_steps <= 200:
                    errors.append(f"Number of steps {n_steps} out of valid range [10, 200]")

            elif analysis_type == 'modal':
                n_modes = options.get('n_modes', 6)
                if not 1 <= n_modes <= 50:
                    errors.append(f"Number of modes {n_modes} out of valid range [1, 50]")

            elif analysis_type == 'time_history':
                if 'accelerogram' not in options:
                    errors.append("Time history analysis requires accelerogram")
                else:
                    accel = options['accelerogram']
                    if not isinstance(accel, (list, tuple)) or len(accel) < 10:
                        errors.append("Accelerogram must be list/tuple with at least 10 points")

        elif analysis_method == AnalysisMethod.LIMIT:
            if 'openings' in wall_data:
                # Validate opening positions
                for opening in wall_data['openings']:
                    if opening.get('x', 0) < 0 or opening.get('y', 0) < 0:
                        errors.append("Opening position must be >= 0")
                    if opening.get('x', 0) + opening.get('width', 0) > length:
                        errors.append("Opening exceeds wall length")
                    if opening.get('y', 0) + opening.get('height', 0) > height:
                        errors.append("Opening exceeds wall height")

        elif analysis_method == AnalysisMethod.FIBER:
            if 'constitutive_law' not in options:
                errors.append("FIBER analysis requires constitutive_law in options")

        elif analysis_method == AnalysisMethod.MICRO:
            # Validate micro-modeling parameters
            required_micro_options = ['block_properties', 'mortar_properties',
                                     'interface_properties', 'block_size']
            for opt in required_micro_options:
                if opt not in options:
                    errors.append(f"MICRO analysis requires '{opt}' in options")

        # 5. Structural compatibility checks
        # Check that loads are reasonable for geometry
        for floor_id, load in loads.items():
            total_load = abs(load.get('Fx', 0)) + abs(load.get('Fy', 0))
            area = length * thickness
            stress = total_load / (area * 1000)  # Convert to MPa

            if stress > material.fcm * 2:
                errors.append(
                    f"Load on floor {floor_id} ({total_load:.1f} kN) produces "
                    f"stress ({stress:.2f} MPa) exceeding 2× material strength ({material.fcm:.2f} MPa)"
                )

        return errors

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    @staticmethod
    def get_analysis_method_from_string(method_str: str) -> Optional[AnalysisMethod]:
        """Convert method string to AnalysisMethod enum."""
        method_map = {
            'FEM': AnalysisMethod.FEM,
            'FRAME': AnalysisMethod.FRAME,
            'Telaio Equivalente': AnalysisMethod.FRAME,
            'LIMIT': AnalysisMethod.LIMIT,
            'Analisi Limite': AnalysisMethod.LIMIT,
            'FIBER': AnalysisMethod.FIBER,
            'Modello a Fibre': AnalysisMethod.FIBER,
            'MICRO': AnalysisMethod.MICRO,
            'Micro-Modellazione': AnalysisMethod.MICRO,
            'POR': AnalysisMethod.POR,
            'SAM': AnalysisMethod.SAM
        }

        return method_map.get(method_str)

    @staticmethod
    def material_to_gui(material: MaterialProperties) -> Dict:
        """Convert MaterialProperties object to GUI format."""
        return {
            'name': material.material_type or 'Material',
            'type': 'Masonry',  # Simplified
            'f_mk': material.fcm,  # ← Reverse mapping
            'E': material.E,
            'weight': material.weight,
            # Additional fields if GUI supports them:
            'f_vm': material.fvm,
            'tau0': material.tau0,
            'f_tm': material.ftm,
            'G': material.G,
            'nu': material.nu,
            'mu': material.mu
        }

    @classmethod
    def get_method_required_options(cls, analysis_method: AnalysisMethod,
                                   analysis_type: str) -> List[str]:
        """Get list of required option keys for a method/type combination."""
        required = []

        if analysis_method == AnalysisMethod.FRAME:
            if analysis_type == 'time_history':
                required.extend(['accelerogram', 'dt'])

        elif analysis_method == AnalysisMethod.FIBER:
            required.append('constitutive_law')
            if analysis_type == 'cyclic':
                required.append('protocol')

        elif analysis_method == AnalysisMethod.MICRO:
            required.extend(['block_properties', 'mortar_properties',
                           'interface_properties', 'block_size'])

        return required

    @classmethod
    def get_method_optional_options(cls, analysis_method: AnalysisMethod,
                                    analysis_type: str) -> Dict[str, Any]:
        """Get dictionary of optional options with their default values."""
        defaults = {}

        if analysis_method == AnalysisMethod.FRAME:
            if analysis_type == 'pushover':
                defaults = {
                    'lateral_pattern': 'triangular',
                    'target_drift': 0.04,
                    'n_steps': 50,
                    'direction': 'y'
                }
            elif analysis_type == 'modal':
                defaults = {'n_modes': 6}

        elif analysis_method == AnalysisMethod.LIMIT:
            defaults = {
                'probabilistic': False,
                'optimize_strengthening': False,
                'target_alpha': 0.3,
                'sensitivity': False
            }

        elif analysis_method == AnalysisMethod.FIBER:
            if analysis_type == 'pushover':
                defaults = {
                    'lateral_pattern': 'triangular',
                    'max_drift': 0.05
                }

        return defaults


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def convert_gui_to_engine(gui_project: Dict,
                         analysis_method: AnalysisMethod) -> Tuple[Dict, MaterialProperties, Dict, Dict, List[str]]:
    """
    One-shot conversion from GUI project to engine inputs.

    Args:
        gui_project: Complete project dict from GUI
            Expected keys: 'walls', 'materials', 'loads', 'analysis_type', 'analysis_settings'
        analysis_method: Target analysis method

    Returns:
        Tuple of (wall_data, material, loads, options, validation_errors)

    Example:
        >>> gui_project = {
        ...     'walls': [...],
        ...     'materials': [...],
        ...     'loads': [...],
        ...     'analysis_type': 'pushover',
        ...     'analysis_settings': {...}
        ... }
        >>> wall_data, material, loads, options, errors = convert_gui_to_engine(
        ...     gui_project, AnalysisMethod.FRAME
        ... )
        >>> if not errors:
        ...     results = engine.analyze_structure(wall_data, material, loads, options)
    """
    standardizer = DataStandardizer()

    # Convert material
    materials = gui_project.get('materials', [])
    material = standardizer.gui_to_material(materials[0] if materials else {})

    # Convert geometry
    walls = gui_project.get('walls', [])
    wall_data = standardizer.gui_to_wall_data(walls, analysis_method)

    # Determine n_floors for load distribution
    n_floors = wall_data.get('n_floors', 1)

    # Convert loads
    loads_list = gui_project.get('loads', [])
    loads = standardizer.gui_to_loads(loads_list, analysis_method, n_floors)

    # Convert options
    analysis_type = gui_project.get('analysis_type', 'static')
    settings = gui_project.get('analysis_settings', {})
    options = standardizer.gui_to_options(settings, analysis_method, analysis_type)

    # Validate
    errors = standardizer.validate_data(wall_data, material, loads, options, analysis_method)

    return wall_data, material, loads, options, errors


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    # Quick test
    print("Testing DataStandardizer...")

    # Test material conversion
    gui_mat = {
        'name': 'Test Brick',
        'type': 'Masonry',
        'f_mk': 2.4,
        'E': 1500.0,
        'weight': 18.0
    }

    material = DataStandardizer.gui_to_material(gui_mat)
    print(f"\n✓ Material conversion: f_mk={gui_mat['f_mk']} → fcm={material.fcm}")

    # Test wall conversion
    gui_walls = [{'length': 5.0, 'height': 3.0, 'thickness': 0.3}]
    wall_data = DataStandardizer.gui_to_wall_data(gui_walls, AnalysisMethod.FRAME)
    print(f"✓ Wall conversion: n_floors={wall_data['n_floors']}")

    # Test load conversion
    gui_loads = [{'type': 'Vertical (Gravity)', 'value': 100.0}]
    loads = DataStandardizer.gui_to_loads(gui_loads, AnalysisMethod.FRAME)
    print(f"✓ Load conversion: floor 0 → Fy={loads[0]['Fy']} kN")

    # Test validation
    options = {'analysis_type': 'static'}
    errors = DataStandardizer.validate_data(wall_data, material, loads, options, AnalysisMethod.FRAME)
    print(f"✓ Validation: {len(errors)} errors")

    if not errors:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Validation errors:", errors)
