"""
Test Suite for Arches Module - Heyman Limit Analysis
=====================================================

Test cases for arch analysis using Heyman's method.
"""

import pytest
import numpy as np
from Material.analyses.historic.arches import (
    ArchAnalysis,
    ArchGeometry,
    ArchType,
    MASONRY_DENSITIES
)


class TestArchGeometry:
    """Test ArchGeometry dataclass"""

    def test_geometry_creation_semicircular(self):
        """Test semicircular arch geometry"""
        geometry = ArchGeometry(
            arch_type='semicircular',
            span=4.0,
            rise=2.0,
            thickness=0.50
        )
        assert geometry.span == 4.0
        assert geometry.rise == 2.0
        assert geometry.thickness == 0.50

    def test_radius_calculation_semicircular(self):
        """Test radius calculation for semicircular arch"""
        geometry = ArchGeometry(
            arch_type='semicircular',
            span=4.0,
            rise=2.0,
            thickness=0.50
        )
        R = geometry.calculate_radius()
        # For semicircle: R = span/2
        assert abs(R - 2.0) < 0.01

    def test_intrados_extrados_calculation(self):
        """Test intrados/extrados coordinate calculation"""
        geometry = ArchGeometry(
            arch_type='semicircular',
            span=4.0,
            rise=2.0,
            thickness=0.50
        )
        intrados, extrados = geometry.calculate_intrados_extrados(n_points=50)

        assert intrados.shape == (50, 2)
        assert extrados.shape == (50, 2)
        # Extrados should be above intrados
        assert np.all(extrados[:, 1] >= intrados[:, 1])


class TestArchAnalysis:
    """Test ArchAnalysis class"""

    @pytest.fixture
    def basic_arch(self):
        """Basic semicircular arch for tests"""
        geometry = ArchGeometry(
            arch_type='semicircular',
            span=4.0,
            rise=2.0,
            thickness=0.50
        )
        return ArchAnalysis(geometry=geometry, masonry_density=20.0)

    def test_arch_creation(self, basic_arch):
        """Test arch creation"""
        assert basic_arch.geometry.span == 4.0
        assert basic_arch.masonry_density == 20.0

    def test_discretize_arch(self, basic_arch):
        """Test arch discretization into voussoirs"""
        voussoirs = basic_arch.discretize_arch()

        assert len(voussoirs) > 0
        assert all('weight' in v for v in voussoirs)
        assert all('x_center' in v for v in voussoirs)
        assert all(v['weight'] > 0 for v in voussoirs)

    def test_thrust_line_calculation(self, basic_arch):
        """Test thrust line calculation"""
        thrust_line = basic_arch.calculate_thrust_line()

        assert thrust_line is not None
        assert thrust_line.shape[1] == 2  # (x, y) coordinates
        # Thrust line should start at left springline
        assert abs(thrust_line[0, 0]) < 0.1

    def test_minimum_thickness(self, basic_arch):
        """Test minimum thickness calculation"""
        t_min = basic_arch.calculate_minimum_thickness()

        assert t_min > 0
        # Should be less than actual thickness for stable arch
        assert t_min < basic_arch.geometry.thickness

    def test_safety_factor(self, basic_arch):
        """Test geometric safety factor calculation"""
        safety = basic_arch.calculate_safety_factor()

        assert 'geometric_safety_factor' in safety
        assert 't_actual' in safety
        assert 't_min' in safety
        assert 'verdict' in safety

        # Safety factor should be > 1.0 for stable arch
        assert safety['geometric_safety_factor'] > 1.0

    def test_seismic_capacity(self, basic_arch):
        """Test seismic capacity estimation"""
        seismic = basic_arch.calculate_seismic_capacity()

        assert 'ag_capacity' in seismic
        assert 'PGA_capacity' in seismic
        assert seismic['ag_capacity'] >= 0

    def test_generate_report(self, basic_arch):
        """Test report generation"""
        report = basic_arch.generate_report()

        assert isinstance(report, str)
        assert len(report) > 100
        assert "HEYMAN" in report
        assert "Safety Factor" in report


class TestMasonryDensities:
    """Test masonry densities database"""

    def test_densities_available(self):
        """Test that masonry densities are defined"""
        assert 'stone' in MASONRY_DENSITIES
        assert 'brick' in MASONRY_DENSITIES
        assert 'tufo' in MASONRY_DENSITIES

        # Check reasonable values
        assert 15.0 < MASONRY_DENSITIES['brick'] < 25.0


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
