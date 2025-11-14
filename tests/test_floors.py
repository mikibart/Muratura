"""
Test Suite for Floors Module - NTC 2018
========================================

Test cases for floor analysis and verification according to NTC 2018.
"""

import pytest
import numpy as np
from Material.analyses.floors import (
    FloorAnalysis,
    FloorGeometry,
    FloorLoads,
    FloorType,
    SupportType,
    DiaphragmType,
    CONCRETE_CLASSES,
    STEEL_CLASSES
)


class TestFloorGeometry:
    """Test FloorGeometry dataclass"""

    def test_geometry_creation_valid(self):
        """Test valid geometry creation"""
        geometry = FloorGeometry(
            span=5.0,
            width=4.0,
            thickness=0.24,
            slab_thickness=0.04
        )
        assert geometry.span == 5.0
        assert geometry.width == 4.0
        assert geometry.thickness == 0.24
        assert geometry.slab_thickness == 0.04

    def test_geometry_validation_negative_span(self):
        """Test geometry validation for negative span"""
        with pytest.raises(ValueError, match="Span deve essere > 0"):
            FloorGeometry(
                span=-5.0,
                width=4.0,
                thickness=0.24,
                slab_thickness=0.04
            )

    def test_geometry_validation_slab_too_thick(self):
        """Test geometry validation for slab thicker than total"""
        with pytest.raises(ValueError, match="Slab thickness.*deve essere < thickness"):
            FloorGeometry(
                span=5.0,
                width=4.0,
                thickness=0.20,
                slab_thickness=0.25  # > thickness
            )

    def test_geometry_warning_thin_slab(self, capsys):
        """Test warning for thin slab"""
        geometry = FloorGeometry(
            span=5.0,
            width=4.0,
            thickness=0.20,
            slab_thickness=0.03  # < 4cm
        )
        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "4cm" in captured.out


class TestFloorLoads:
    """Test FloorLoads dataclass"""

    def test_loads_default_values(self):
        """Test default load values"""
        loads = FloorLoads()
        assert loads.permanent_loads == 0.0
        assert loads.additional_permanent == 2.0
        assert loads.live_loads == 2.0
        assert loads.partition_walls == 1.0
        assert not loads.self_weight_included

    def test_total_permanent_without_self_weight(self):
        """Test total permanent loads without self weight"""
        loads = FloorLoads(
            permanent_loads=1.0,
            additional_permanent=2.0,
            partition_walls=1.0
        )
        total = loads.total_permanent(self_weight=0.0)
        assert total == 4.0  # 1.0 + 2.0 + 1.0

    def test_total_permanent_with_self_weight(self):
        """Test total permanent loads with self weight"""
        loads = FloorLoads(
            permanent_loads=1.0,
            additional_permanent=2.0,
            partition_walls=1.0
        )
        total = loads.total_permanent(self_weight=3.0)
        assert total == 7.0  # 1.0 + 2.0 + 1.0 + 3.0

    def test_slu_load_combination(self):
        """Test SLU load combination (γG=1.3, γQ=1.5)"""
        loads = FloorLoads(
            permanent_loads=2.0,
            additional_permanent=2.0,
            live_loads=2.0,
            partition_walls=1.0
        )
        # G = 2 + 2 + 1 = 5, Q = 2
        # SLU = 1.3*5 + 1.5*2 = 6.5 + 3.0 = 9.5
        slu = loads.slu_load_combination(self_weight=0.0)
        assert abs(slu - 9.5) < 0.01

    def test_sle_quasi_permanent_combination(self):
        """Test SLE quasi-permanent combination (ψ2=0.3)"""
        loads = FloorLoads(
            permanent_loads=2.0,
            additional_permanent=2.0,
            live_loads=2.0,
            partition_walls=1.0
        )
        # G = 5, Q = 2, ψ2 = 0.3
        # SLE_QP = 5 + 0.3*2 = 5.6
        sle = loads.sle_quasi_permanent_combination(self_weight=0.0)
        assert abs(sle - 5.6) < 0.01


class TestFloorAnalysis:
    """Test FloorAnalysis class"""

    @pytest.fixture
    def basic_geometry(self):
        """Basic floor geometry for tests"""
        return FloorGeometry(
            span=5.0,
            width=4.0,
            thickness=0.24,
            slab_thickness=0.04,
            rib_spacing=0.50,
            rib_width=0.10
        )

    @pytest.fixture
    def basic_loads(self):
        """Basic floor loads for tests"""
        return FloorLoads(
            additional_permanent=2.0,
            live_loads=2.0,
            partition_walls=1.0
        )

    def test_floor_creation_valid(self, basic_geometry, basic_loads):
        """Test valid floor creation"""
        floor = FloorAnalysis(
            floor_type='latero-cemento',
            geometry=basic_geometry,
            concrete_class='C25/30',
            steel_class='B450C',
            loads=basic_loads
        )
        assert floor.floor_type == FloorType.LATERO_CEMENTO
        assert floor.support_type == SupportType.SIMPLY_SUPPORTED
        assert floor.concrete_class == 'C25/30'
        assert floor.steel_class == 'B450C'

    def test_floor_invalid_concrete_class(self, basic_geometry):
        """Test floor creation with invalid concrete class"""
        with pytest.raises(ValueError, match="Concrete class.*not supported"):
            FloorAnalysis(
                floor_type='latero-cemento',
                geometry=basic_geometry,
                concrete_class='C50/60',  # Not in database
            )

    def test_floor_invalid_steel_class(self, basic_geometry):
        """Test floor creation with invalid steel class"""
        with pytest.raises(ValueError, match="Steel class.*not supported"):
            FloorAnalysis(
                floor_type='latero-cemento',
                geometry=basic_geometry,
                steel_class='S275',  # Not in database
            )

    def test_self_weight_latero_cemento(self, basic_geometry, basic_loads):
        """Test self weight calculation for latero-cemento floor"""
        floor = FloorAnalysis(
            floor_type='latero-cemento',
            geometry=basic_geometry,
            loads=basic_loads
        )
        self_weight = floor.calculate_self_weight()

        # Expected: ~3.0-3.5 kN/m² for h=24cm
        assert 2.5 < self_weight < 4.0

        # Check caching
        self_weight2 = floor.calculate_self_weight()
        assert self_weight == self_weight2

    def test_self_weight_wood(self, basic_geometry, basic_loads):
        """Test self weight for wood floor"""
        floor = FloorAnalysis(
            floor_type='wood',
            geometry=basic_geometry,
            loads=basic_loads
        )
        self_weight = floor.calculate_self_weight()

        # Wood is lighter: ~1.3-1.5 kN/m²
        assert 1.0 < self_weight < 2.0

    def test_moments_simply_supported(self, basic_geometry, basic_loads):
        """Test moment calculation for simply supported floor"""
        floor = FloorAnalysis(
            floor_type='latero-cemento',
            geometry=basic_geometry,
            support_type='simply_supported',
            loads=basic_loads
        )
        moments = floor.calculate_moments()

        # M = q·L²/8
        assert 'M_max' in moments
        assert 'M_support' in moments
        assert 'q_slu' in moments
        assert moments['M_max'] > 0
        assert moments['M_support'] == 0  # Simply supported

        # Sanity check: M should be reasonable
        L = basic_geometry.span
        q = moments['q_slu']
        M_expected = q * L**2 / 8.0
        assert abs(moments['M_max'] - M_expected) < 0.01

    def test_moments_continuous(self, basic_geometry, basic_loads):
        """Test moment calculation for continuous floor"""
        floor = FloorAnalysis(
            floor_type='latero-cemento',
            geometry=basic_geometry,
            support_type='continuous',
            loads=basic_loads
        )
        moments = floor.calculate_moments()

        # Continuous beam has support moment
        assert moments['M_support'] > 0
        assert moments['M_max'] < moments['M_support']  # Support moment dominates

    def test_shear_calculation(self, basic_geometry, basic_loads):
        """Test shear force calculation"""
        floor = FloorAnalysis(
            floor_type='latero-cemento',
            geometry=basic_geometry,
            support_type='simply_supported',
            loads=basic_loads
        )
        shear = floor.calculate_shear()

        assert 'V_max' in shear
        assert shear['V_max'] > 0

        # V = q·L/2 for simply supported
        moments = floor.calculate_moments()
        V_expected = moments['q_slu'] * basic_geometry.span / 2.0
        assert abs(shear['V_max'] - V_expected) < 0.01

    def test_reinforcement_calculation(self, basic_geometry, basic_loads):
        """Test reinforcement calculation"""
        floor = FloorAnalysis(
            floor_type='latero-cemento',
            geometry=basic_geometry,
            loads=basic_loads
        )
        reinforcement = floor.calculate_reinforcement()

        assert 'As_long' in reinforcement
        assert 'As_min' in reinforcement
        assert 'spacing' in reinforcement
        assert 'phi' in reinforcement

        # As should be >= As_min
        assert reinforcement['As_long'] >= reinforcement['As_min']

        # Reasonable values
        assert 2.0 < reinforcement['As_long'] < 20.0  # cm²/m
        assert 10 < reinforcement['spacing'] < 30  # cm

    def test_verify_slu_flexure(self, basic_geometry, basic_loads):
        """Test SLU flexure verification"""
        floor = FloorAnalysis(
            floor_type='latero-cemento',
            geometry=basic_geometry,
            loads=basic_loads
        )
        verification = floor.verify_slu_flexure()

        assert 'M_rd' in verification
        assert 'M_ed' in verification
        assert 'ratio' in verification
        assert 'verified' in verification

        # M_rd should be > M_ed for design
        assert verification['M_rd'] > 0
        assert verification['M_ed'] > 0
        assert verification['ratio'] == verification['M_ed'] / verification['M_rd']

    def test_verify_slu_shear(self, basic_geometry, basic_loads):
        """Test SLU shear verification"""
        floor = FloorAnalysis(
            floor_type='latero-cemento',
            geometry=basic_geometry,
            loads=basic_loads
        )
        verification = floor.verify_slu_shear()

        assert 'V_rd' in verification
        assert 'V_ed' in verification
        assert 'ratio' in verification
        assert 'verified' in verification
        assert 'stirrups_required' in verification

        assert verification['V_rd'] > 0
        assert verification['V_ed'] > 0

    def test_verify_slu_complete(self, basic_geometry, basic_loads):
        """Test complete SLU verification"""
        floor = FloorAnalysis(
            floor_type='latero-cemento',
            geometry=basic_geometry,
            loads=basic_loads
        )
        slu = floor.verify_slu()

        assert 'flexure' in slu
        assert 'shear' in slu
        assert 'overall_verified' in slu

        # Overall verified only if both flexure and shear verified
        assert slu['overall_verified'] == (
            slu['flexure']['verified'] and slu['shear']['verified']
        )

    def test_verify_sle_deflection(self, basic_geometry, basic_loads):
        """Test SLE deflection verification"""
        floor = FloorAnalysis(
            floor_type='latero-cemento',
            geometry=basic_geometry,
            loads=basic_loads
        )
        verification = floor.verify_sle_deflection()

        assert 'deflection' in verification
        assert 'deflection_instantaneous' in verification
        assert 'limit' in verification
        assert 'ratio' in verification
        assert 'verified' in verification

        # Limit = L/250
        L = basic_geometry.span * 1000  # mm
        assert abs(verification['limit'] - L/250.0) < 0.1

        # Deflection with creep should be > instantaneous
        assert verification['deflection'] > verification['deflection_instantaneous']

    def test_verify_sle_complete(self, basic_geometry, basic_loads):
        """Test complete SLE verification"""
        floor = FloorAnalysis(
            floor_type='latero-cemento',
            geometry=basic_geometry,
            loads=basic_loads
        )
        sle = floor.verify_sle()

        assert 'deflection' in sle
        assert 'cracking' in sle
        assert 'overall_verified' in sle

    def test_assess_diaphragm_behavior(self, basic_geometry, basic_loads):
        """Test diaphragm behavior assessment"""
        floor = FloorAnalysis(
            floor_type='latero-cemento',
            geometry=basic_geometry,
            loads=basic_loads
        )
        diaphragm = floor.assess_diaphragm_behavior()

        # Should be one of the enum values
        assert diaphragm in [DiaphragmType.RIGID, DiaphragmType.FLEXIBLE, DiaphragmType.SEMI_RIGID]

        # Latero-cemento typically behaves as rigid
        assert diaphragm == DiaphragmType.RIGID

    def test_assess_diaphragm_flexible(self, basic_geometry, basic_loads):
        """Test flexible diaphragm (wood)"""
        floor = FloorAnalysis(
            floor_type='wood',
            geometry=basic_geometry,
            loads=basic_loads
        )
        diaphragm = floor.assess_diaphragm_behavior()

        # Wood more likely to be flexible/semi-rigid
        assert diaphragm in [DiaphragmType.FLEXIBLE, DiaphragmType.SEMI_RIGID]

    def test_integrate_with_walls(self, basic_geometry, basic_loads):
        """Test integration with wall system"""
        floor = FloorAnalysis(
            floor_type='latero-cemento',
            geometry=basic_geometry,
            loads=basic_loads
        )

        wall_stiffness = 50000.0  # kN/m (typical masonry)
        integration = floor.integrate_with_walls(
            wall_stiffness=wall_stiffness,
            seismic=True
        )

        assert 'diaphragm_type' in integration
        assert 'in_plane_stiffness' in integration
        assert 'seismic_mass' in integration
        assert 'connection_verified' in integration
        assert 'connection_stress' in integration

        # Seismic mass should be positive
        assert integration['seismic_mass'] > 0

        # Rigid diaphragm should have high stiffness
        if integration['diaphragm_type'] == 'rigid':
            assert integration['in_plane_stiffness'] > 1e5

    def test_generate_report(self, basic_geometry, basic_loads):
        """Test report generation"""
        floor = FloorAnalysis(
            floor_type='latero-cemento',
            geometry=basic_geometry,
            loads=basic_loads
        )
        report = floor.generate_report()

        # Report should be a non-empty string
        assert isinstance(report, str)
        assert len(report) > 100

        # Should contain key sections
        assert "VERIFICA SOLAIO" in report
        assert "NTC 2018" in report
        assert "Geometria" in report
        assert "Carichi" in report
        assert "VERIFICHE SLU" in report
        assert "VERIFICHE SLE" in report
        assert "ESITO FINALE" in report


class TestFloorTypes:
    """Test different floor types"""

    @pytest.fixture
    def geometry(self):
        return FloorGeometry(
            span=5.0,
            width=4.0,
            thickness=0.24,
            slab_thickness=0.04
        )

    @pytest.fixture
    def loads(self):
        return FloorLoads()

    def test_all_floor_types_instantiation(self, geometry, loads):
        """Test that all floor types can be instantiated"""
        for floor_type in ['latero-cemento', 'wood', 'steel', 'precast', 'vault']:
            floor = FloorAnalysis(
                floor_type=floor_type,
                geometry=geometry,
                loads=loads
            )
            assert floor.floor_type.value == floor_type

    def test_concrete_classes_available(self):
        """Test that concrete classes are properly defined"""
        assert 'C20/25' in CONCRETE_CLASSES
        assert 'C25/30' in CONCRETE_CLASSES
        assert 'C28/35' in CONCRETE_CLASSES
        assert 'C30/37' in CONCRETE_CLASSES

        # Check structure
        for cls_name, properties in CONCRETE_CLASSES.items():
            assert 'fck' in properties
            assert 'Ecm' in properties

    def test_steel_classes_available(self):
        """Test that steel classes are properly defined"""
        assert 'B450C' in STEEL_CLASSES
        assert 'B450A' in STEEL_CLASSES

        # Check structure
        for cls_name, properties in STEEL_CLASSES.items():
            assert 'fyk' in properties
            assert 'Es' in properties
            assert 'epsuk' in properties


class TestEdgeCases:
    """Test edge cases and limits"""

    def test_very_short_span(self):
        """Test floor with very short span"""
        geometry = FloorGeometry(
            span=2.0,  # Very short
            width=3.0,
            thickness=0.20,
            slab_thickness=0.04
        )
        floor = FloorAnalysis(
            floor_type='latero-cemento',
            geometry=geometry
        )

        # Should still calculate correctly
        moments = floor.calculate_moments()
        assert moments['M_max'] > 0
        assert moments['M_max'] < 10.0  # Small moment for short span

    def test_long_span(self):
        """Test floor with long span"""
        geometry = FloorGeometry(
            span=8.0,  # Long span
            width=5.0,
            thickness=0.32,  # Thicker
            slab_thickness=0.05
        )
        floor = FloorAnalysis(
            floor_type='precast',
            geometry=geometry
        )

        # Should calculate
        reinforcement = floor.calculate_reinforcement()
        # Long span requires more reinforcement
        assert reinforcement['As_long'] > 5.0  # cm²/m

    def test_heavy_loads(self):
        """Test floor with heavy loads (industrial)"""
        geometry = FloorGeometry(
            span=5.0,
            width=4.0,
            thickness=0.26,
            slab_thickness=0.05
        )
        loads = FloorLoads(
            additional_permanent=3.0,
            live_loads=6.0,  # Heavy industrial (Cat. E)
            partition_walls=0.0
        )
        floor = FloorAnalysis(
            floor_type='latero-cemento',
            geometry=geometry,
            concrete_class='C30/37',  # Higher class
            loads=loads
        )

        # High loads should require more reinforcement
        reinforcement = floor.calculate_reinforcement()
        slu = floor.verify_slu()

        # Should calculate without errors
        assert reinforcement['As_long'] > 3.0
        assert slu['flexure']['ratio'] < 1.5  # May not verify, but should calculate


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
