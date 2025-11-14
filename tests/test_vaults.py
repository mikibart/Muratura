"""
Test Suite for Vaults Module - Heyman Limit Analysis
=====================================================

Test cases for vault analysis using Heyman's method extended to 3D.
"""

import pytest
import numpy as np
from Material.analyses.historic.vaults import (
    VaultAnalysis,
    VaultGeometry,
    VaultType,
    MASONRY_DENSITIES
)


class TestVaultGeometry:
    """Test VaultGeometry dataclass"""

    def test_geometry_creation_barrel(self):
        """Test barrel vault geometry creation"""
        geometry = VaultGeometry(
            vault_type='barrel',
            span=6.0,
            rise=3.0,
            length=12.0,
            thickness=0.40
        )
        assert geometry.span == 6.0
        assert geometry.rise == 3.0
        assert geometry.length == 12.0
        assert geometry.thickness == 0.40

    def test_geometry_creation_dome(self):
        """Test dome geometry creation"""
        geometry = VaultGeometry(
            vault_type='dome',
            span=10.0,
            rise=5.0,
            thickness=0.60
        )
        assert geometry.span == 10.0
        assert geometry.rise == 5.0
        assert geometry.thickness == 0.60
        assert geometry.opening_angle == 90.0  # default

    def test_geometry_creation_cross(self):
        """Test cross vault geometry creation"""
        geometry = VaultGeometry(
            vault_type='cross',
            span=8.0,
            rise=4.0,
            length=10.0,
            thickness=0.35
        )
        assert geometry.vault_type == 'cross'
        assert geometry.length == 10.0

    def test_geometry_validation_barrel_no_length(self):
        """Test that barrel vault requires length"""
        with pytest.raises(ValueError):
            VaultGeometry(
                vault_type='barrel',
                span=6.0,
                rise=3.0,
                thickness=0.40
                # Missing length
            )

    def test_radius_calculation_dome(self):
        """Test radius calculation for dome"""
        geometry = VaultGeometry(
            vault_type='dome',
            span=10.0,
            rise=5.0,
            thickness=0.60
        )
        R = geometry.calculate_radius()
        # For hemisphere: R = span/2
        assert abs(R - 5.0) < 0.01

    def test_radius_calculation_barrel(self):
        """Test radius calculation for barrel vault"""
        geometry = VaultGeometry(
            vault_type='barrel',
            span=6.0,
            rise=3.0,
            length=12.0,
            thickness=0.40
        )
        R = geometry.calculate_radius()
        # For semicircular barrel: R ≈ span/2
        assert R > 0
        assert R < geometry.span  # Sensible value

    def test_volume_calculation_barrel(self):
        """Test volume calculation for barrel vault"""
        geometry = VaultGeometry(
            vault_type='barrel',
            span=6.0,
            rise=3.0,
            length=12.0,
            thickness=0.40
        )
        volume = geometry.calculate_volume()
        assert volume > 0
        # Volume should be reasonable (not negative, not enormous)
        assert volume < geometry.span * geometry.length * geometry.rise

    def test_volume_calculation_dome(self):
        """Test volume calculation for dome"""
        geometry = VaultGeometry(
            vault_type='dome',
            span=10.0,
            rise=5.0,
            thickness=0.60
        )
        volume = geometry.calculate_volume()
        assert volume > 0


class TestVaultAnalysis:
    """Test VaultAnalysis class"""

    @pytest.fixture
    def barrel_vault(self):
        """Basic barrel vault for tests"""
        geometry = VaultGeometry(
            vault_type='barrel',
            span=6.0,
            rise=3.0,
            length=12.0,
            thickness=0.40
        )
        return VaultAnalysis(geometry=geometry, masonry_density=20.0)

    @pytest.fixture
    def dome_vault(self):
        """Basic dome for tests"""
        geometry = VaultGeometry(
            vault_type='dome',
            span=10.0,
            rise=5.0,
            thickness=0.60
        )
        return VaultAnalysis(geometry=geometry, masonry_density=20.0)

    @pytest.fixture
    def cross_vault(self):
        """Basic cross vault for tests"""
        geometry = VaultGeometry(
            vault_type='cross',
            span=8.0,
            rise=4.0,
            length=10.0,
            thickness=0.35
        )
        return VaultAnalysis(geometry=geometry, masonry_density=22.0)

    def test_vault_creation(self, barrel_vault):
        """Test vault creation"""
        assert barrel_vault.geometry.span == 6.0
        assert barrel_vault.masonry_density == 20.0

    def test_self_weight_calculation_barrel(self, barrel_vault):
        """Test self weight calculation for barrel vault"""
        weight = barrel_vault.calculate_self_weight_per_area()
        assert weight > 0
        # Should be reasonable for masonry vault
        assert 2.0 < weight < 25.0  # kN/m² (wider range for different geometries)

    def test_self_weight_calculation_dome(self, dome_vault):
        """Test self weight calculation for dome"""
        weight = dome_vault.calculate_self_weight_per_area()
        assert weight > 0
        assert 2.0 < weight < 30.0  # kN/m² (domes can have higher weight projection)

    def test_total_load_calculation(self, barrel_vault):
        """Test total load calculation"""
        loads = barrel_vault.calculate_total_load()

        assert 'self_weight' in loads
        assert 'fill_weight' in loads
        assert 'live_load' in loads
        assert 'total' in loads

        assert loads['self_weight'] > 0
        assert loads['total'] >= loads['self_weight']

    def test_total_load_with_fill(self):
        """Test total load calculation with fill"""
        geometry = VaultGeometry(
            vault_type='barrel',
            span=6.0,
            rise=3.0,
            length=12.0,
            thickness=0.40
        )
        vault = VaultAnalysis(
            geometry=geometry,
            masonry_density=20.0,
            fill_height=0.5,  # 0.5m fill
            fill_density=16.0,
            live_load=2.0
        )

        loads = vault.calculate_total_load()
        assert loads['fill_weight'] == 0.5 * 16.0  # 8.0 kN/m²
        assert loads['live_load'] == 2.0
        assert loads['total'] > loads['self_weight']

    def test_minimum_thickness_barrel(self, barrel_vault):
        """Test minimum thickness calculation for barrel vault"""
        t_min = barrel_vault.calculate_minimum_thickness()

        assert t_min > 0
        # Should be less than actual thickness for stable vault
        assert t_min < barrel_vault.geometry.thickness

        # Check reasonable t/R ratio (Heyman: 0.02-0.04 for barrel)
        R = barrel_vault.geometry.calculate_radius()
        t_R_ratio = t_min / R
        assert 0.01 < t_R_ratio < 0.10

    def test_minimum_thickness_dome(self, dome_vault):
        """Test minimum thickness calculation for dome"""
        t_min = dome_vault.calculate_minimum_thickness()

        assert t_min > 0
        assert t_min < dome_vault.geometry.thickness

        # Check reasonable t/R ratio (Heyman: 0.01-0.02 for domes)
        R = dome_vault.geometry.calculate_radius()
        t_R_ratio = t_min / R
        assert 0.005 < t_R_ratio < 0.05

    def test_minimum_thickness_cross(self, cross_vault):
        """Test minimum thickness calculation for cross vault"""
        t_min = cross_vault.calculate_minimum_thickness()

        assert t_min > 0
        # Cross vaults are typically stable
        assert t_min < cross_vault.geometry.thickness

    def test_safety_factor_barrel(self, barrel_vault):
        """Test safety factor calculation for barrel vault"""
        safety = barrel_vault.calculate_safety_factor()

        assert 'geometric_safety_factor' in safety
        assert 't_actual' in safety
        assert 't_min' in safety
        assert 't_to_R_ratio' in safety
        assert 'verdict' in safety

        # Safety factor should be > 1.0 for stable vault
        assert safety['geometric_safety_factor'] > 1.0

    def test_safety_factor_dome(self, dome_vault):
        """Test safety factor calculation for dome"""
        safety = dome_vault.calculate_safety_factor()

        assert safety['geometric_safety_factor'] > 1.0
        assert safety['verdict'] in ['VERY_SAFE', 'SAFE', 'MARGINALLY_SAFE', 'UNSAFE']

    def test_safety_factor_with_loads(self):
        """Test that loads reduce safety factor"""
        geometry = VaultGeometry(
            vault_type='barrel',
            span=6.0,
            rise=3.0,
            length=12.0,
            thickness=0.40
        )

        # Vault without extra loads
        vault1 = VaultAnalysis(geometry=geometry, masonry_density=20.0)
        safety1 = vault1.calculate_safety_factor()

        # Vault with fill and live load
        vault2 = VaultAnalysis(
            geometry=geometry,
            masonry_density=20.0,
            fill_height=1.0,
            fill_density=16.0,
            live_load=2.0
        )
        safety2 = vault2.calculate_safety_factor()

        # Safety factor should be lower with extra loads
        assert safety2['geometric_safety_factor'] < safety1['geometric_safety_factor']

    def test_seismic_capacity(self, barrel_vault):
        """Test seismic capacity estimation"""
        seismic = barrel_vault.calculate_seismic_capacity()

        assert 'ag_capacity' in seismic
        assert 'PGA_capacity' in seismic
        assert seismic['ag_capacity'] >= 0
        assert seismic['ag_capacity'] <= 0.5  # Maximum realistic value

    def test_seismic_capacity_correlation_with_FS(self):
        """Test that higher FS leads to higher seismic capacity"""
        geometry = VaultGeometry(
            vault_type='dome',
            span=10.0,
            rise=5.0,
            thickness=0.80  # Thick dome
        )
        vault_thick = VaultAnalysis(geometry=geometry, masonry_density=20.0)

        geometry_thin = VaultGeometry(
            vault_type='dome',
            span=10.0,
            rise=5.0,
            thickness=0.10  # Thin dome
        )
        vault_thin = VaultAnalysis(geometry=geometry_thin, masonry_density=20.0)

        seismic_thick = vault_thick.calculate_seismic_capacity()
        seismic_thin = vault_thin.calculate_seismic_capacity()

        # Thicker vault should have higher seismic capacity
        assert seismic_thick['ag_capacity'] >= seismic_thin['ag_capacity']

    def test_generate_report_barrel(self, barrel_vault):
        """Test report generation for barrel vault"""
        report = barrel_vault.generate_report()

        assert isinstance(report, str)
        assert len(report) > 100
        assert "HEYMAN" in report
        assert "barrel" in report
        assert "Safety Factor" in report

    def test_generate_report_dome(self, dome_vault):
        """Test report generation for dome"""
        report = dome_vault.generate_report()

        assert isinstance(report, str)
        assert "dome" in report
        assert "Angolo apertura" in report or "apertura" in report

    def test_generate_report_cross(self, cross_vault):
        """Test report generation for cross vault"""
        report = cross_vault.generate_report()

        assert isinstance(report, str)
        assert "cross" in report


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
