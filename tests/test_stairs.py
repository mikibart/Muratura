"""
Test Suite for Stairs Module - NTC 2018
========================================

Test cases for stair analysis and verification.
"""

import pytest
from Material.analyses.stairs import (
    StairAnalysis,
    StairGeometry,
    StairLoads,
    GEOMETRY_LIMITS,
    BLONDEL_MIN,
    BLONDEL_MAX
)


class TestStairGeometry:
    """Test StairGeometry dataclass"""

    def test_geometry_creation_valid(self):
        """Test valid geometry creation"""
        geometry = StairGeometry(
            floor_height=3.0,
            n_steps=17,
            width=1.00,
            landing_length=1.00,
            thickness=0.18
        )
        assert geometry.floor_height == 3.0
        assert geometry.n_steps == 17
        # Rise should be calculated
        assert geometry.rise is not None
        assert abs(geometry.rise - 3.0/17) < 0.01

    def test_geometry_rise_calculation(self):
        """Test automatic rise calculation"""
        geometry = StairGeometry(
            floor_height=3.0,
            n_steps=17,
            width=1.00
        )
        expected_rise = 3.0 / 17
        assert abs(geometry.rise - expected_rise) < 0.001

    def test_geometry_tread_blondel(self):
        """Test tread calculation using Blondel formula"""
        geometry = StairGeometry(
            floor_height=3.0,
            n_steps=17,
            width=1.00
        )
        # 2a + p = 63cm
        expected_tread = 0.63 - 2 * geometry.rise
        assert abs(geometry.tread - expected_tread) < 0.001

    def test_geometry_validation(self):
        """Test geometry validation"""
        geometry = StairGeometry(
            floor_height=3.0,
            n_steps=17,
            width=1.00
        )
        validation = geometry.validate_geometry()

        assert 'valid' in validation
        assert 'rise_cm' in validation
        assert 'tread_cm' in validation
        assert 'blondel' in validation
        assert 'slope_deg' in validation


class TestStairAnalysis:
    """Test StairAnalysis class"""

    @pytest.fixture
    def basic_geometry(self):
        return StairGeometry(
            floor_height=3.0,
            n_steps=17,
            width=1.00,
            landing_length=1.00,
            thickness=0.18
        )

    @pytest.fixture
    def basic_loads(self):
        return StairLoads(
            permanent_loads=1.5,
            live_loads=2.0
        )

    def test_stair_creation(self, basic_geometry, basic_loads):
        """Test stair creation"""
        stair = StairAnalysis(
            stair_type='slab_ramp',
            geometry=basic_geometry,
            loads=basic_loads
        )
        assert stair.stair_type.value == 'slab_ramp'

    def test_ramp_length_calculation(self, basic_geometry, basic_loads):
        """Test ramp length calculation"""
        stair = StairAnalysis(
            stair_type='slab_ramp',
            geometry=basic_geometry,
            loads=basic_loads
        )
        L = stair.calculate_ramp_length()
        assert L > 0
        # Should be longer than horizontal projection
        assert L > (basic_geometry.n_steps / 2) * basic_geometry.tread

    def test_self_weight_calculation(self, basic_geometry, basic_loads):
        """Test self weight calculation"""
        stair = StairAnalysis(
            stair_type='slab_ramp',
            geometry=basic_geometry,
            loads=basic_loads
        )
        self_weight = stair.calculate_self_weight()
        # Should be reasonable for RC stair
        assert 3.0 < self_weight < 8.0  # kN/m²

    def test_moments_calculation(self, basic_geometry, basic_loads):
        """Test moments calculation"""
        stair = StairAnalysis(
            stair_type='slab_ramp',
            geometry=basic_geometry,
            loads=basic_loads
        )
        moments = stair.calculate_moments()

        assert 'M_max' in moments
        assert 'q_slu' in moments
        assert 'L_ramp' in moments
        assert moments['M_max'] > 0

    def test_reinforcement_calculation(self, basic_geometry, basic_loads):
        """Test reinforcement calculation"""
        stair = StairAnalysis(
            stair_type='slab_ramp',
            geometry=basic_geometry,
            loads=basic_loads
        )
        reinforcement = stair.calculate_reinforcement()

        assert 'As_long' in reinforcement
        assert 'As_distr' in reinforcement
        assert 'As_min' in reinforcement
        assert reinforcement['As_long'] >= reinforcement['As_min']

    def test_verify_stair(self, basic_geometry, basic_loads):
        """Test complete stair verification"""
        stair = StairAnalysis(
            stair_type='slab_ramp',
            geometry=basic_geometry,
            loads=basic_loads
        )
        verification = stair.verify_stair()

        assert 'geometry' in verification
        assert 'slu' in verification
        assert 'sle' in verification
        assert 'overall_verified' in verification

    def test_generate_report(self, basic_geometry, basic_loads):
        """Test report generation"""
        stair = StairAnalysis(
            stair_type='slab_ramp',
            geometry=basic_geometry,
            loads=basic_loads
        )
        report = stair.generate_report()

        assert isinstance(report, str)
        assert len(report) > 100
        assert "VERIFICA SCALA" in report


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
