"""
Test Suite for Strengthening Module - FRP/FRCM Design
======================================================

Test cases for structural strengthening design using FRP and FRCM
according to CNR-DT 200/2013 and CNR-DT 215/2018.
"""

import pytest
import numpy as np
from Material.analyses.historic.strengthening import (
    StrengtheningDesign,
    FRPMaterial,
    MasonryProperties,
    ApplicationType,
    MaterialType,
    MATERIAL_DATABASE,
    SAFETY_FACTORS
)


class TestFRPMaterial:
    """Test FRPMaterial dataclass"""

    def test_material_creation_manual(self):
        """Test manual material creation"""
        material = FRPMaterial(
            material_type='CFRP',
            thickness=0.165,
            tensile_strength=3500,
            elastic_modulus=230000
        )
        assert material.material_type == 'CFRP'
        assert material.thickness == 0.165
        assert material.tensile_strength == 3500
        assert material.elastic_modulus == 230000

    def test_material_from_database_cfrp(self):
        """Test CFRP material from database"""
        material = FRPMaterial.from_database('CFRP_HM')
        assert material.tensile_strength == 3500
        assert material.elastic_modulus == 230000
        assert material.ultimate_strain is not None

    def test_material_from_database_gfrp(self):
        """Test GFRP material from database"""
        material = FRPMaterial.from_database('GFRP')
        assert material.tensile_strength == 1200
        assert material.elastic_modulus == 73000

    def test_material_from_database_frcm(self):
        """Test FRCM material from database"""
        material = FRPMaterial.from_database('C_FRCM')
        assert material.tensile_strength == 2000
        assert material.elastic_modulus == 200000

    def test_ultimate_strain_calculation(self):
        """Test automatic ultimate strain calculation"""
        material = FRPMaterial(
            material_type='CFRP',
            thickness=0.165,
            tensile_strength=3500,
            elastic_modulus=230000
        )
        expected_strain = 3500 / 230000
        assert abs(material.ultimate_strain - expected_strain) < 0.0001


class TestMasonryProperties:
    """Test MasonryProperties dataclass"""

    def test_masonry_creation(self):
        """Test masonry properties creation"""
        masonry = MasonryProperties(
            compressive_strength=2.5,
            tensile_strength=0.1,
            elastic_modulus=1500
        )
        assert masonry.compressive_strength == 2.5
        assert masonry.tensile_strength == 0.1
        assert masonry.elastic_modulus == 1500

    def test_masonry_defaults(self):
        """Test default masonry properties"""
        masonry = MasonryProperties(compressive_strength=2.0)
        assert masonry.tensile_strength == 0.1  # default
        assert masonry.elastic_modulus == 1500  # default


class TestStrengtheningDesign:
    """Test StrengtheningDesign class"""

    @pytest.fixture
    def cfrp_material(self):
        """CFRP material for tests"""
        return FRPMaterial.from_database('CFRP_HM')

    @pytest.fixture
    def frcm_material(self):
        """FRCM material for tests"""
        return FRPMaterial.from_database('C_FRCM')

    @pytest.fixture
    def masonry(self):
        """Basic masonry for tests"""
        return MasonryProperties(compressive_strength=2.5)

    @pytest.fixture
    def arch_design_cfrp(self, cfrp_material, masonry):
        """Basic arch strengthening with CFRP"""
        return StrengtheningDesign(
            application_type=ApplicationType.ARCH_EXTRADOS,
            material=cfrp_material,
            masonry=masonry,
            width=1.0,
            n_layers=2
        )

    def test_design_creation(self, arch_design_cfrp):
        """Test strengthening design creation"""
        assert arch_design_cfrp.width == 1.0
        assert arch_design_cfrp.n_layers == 2
        assert arch_design_cfrp.application_type == ApplicationType.ARCH_EXTRADOS

    def test_calculate_design_strength(self, arch_design_cfrp):
        """Test design strength calculation"""
        result = arch_design_cfrp.calculate_design_strength()

        assert 'f_fd' in result
        assert 'eps_fd' in result
        assert 'F_fd' in result
        assert 'A_f' in result

        # Design strength should be less than characteristic
        f_fk = arch_design_cfrp.material.tensile_strength
        assert result['f_fd'] < f_fk

        # Design strength should be positive
        assert result['f_fd'] > 0
        assert result['F_fd'] > 0

    def test_safety_factor_applied(self, arch_design_cfrp):
        """Test that safety factors are correctly applied"""
        result = arch_design_cfrp.calculate_design_strength()

        f_fk = arch_design_cfrp.material.tensile_strength
        gamma_f = SAFETY_FACTORS['gamma_f']
        eta_a = SAFETY_FACTORS['eta_a']

        expected_f_fd = f_fk / (gamma_f * eta_a)

        assert abs(result['f_fd'] - expected_f_fd) < 0.1

    def test_calculate_debonding_strength(self, arch_design_cfrp):
        """Test debonding strength calculation"""
        result = arch_design_cfrp.calculate_debonding_strength()

        assert 'f_dd' in result
        assert 'f_dd_design' in result
        assert 'verified' in result
        assert 'safety_ratio' in result

        # Debonding strength should be positive
        assert result['f_dd'] > 0
        assert result['f_dd_design'] > 0

    def test_debonding_verification_calculation(self, cfrp_material):
        """Test debonding verification calculation"""
        # Test with different masonry qualities
        good_masonry = MasonryProperties(compressive_strength=5.0)

        design = StrengtheningDesign(
            application_type=ApplicationType.ARCH_EXTRADOS,
            material=cfrp_material,
            masonry=good_masonry,
            width=1.0,
            n_layers=1  # Single layer
        )

        result = design.calculate_debonding_strength()
        # Just verify calculation runs and returns valid results
        assert 'verified' in result
        assert result['f_dd'] > 0
        assert result['f_dd_design'] > 0
        # Note: With high-strength CFRP, debonding can still be critical
        # even with good masonry

    def test_calculate_anchorage_length(self, arch_design_cfrp):
        """Test anchorage length calculation"""
        result = arch_design_cfrp.calculate_anchorage_length()

        assert 'l_e' in result
        assert 'l_min' in result
        assert 'tau_max' in result

        # Anchorage length should be reasonable
        assert result['l_e'] > 0
        assert result['l_min'] >= 150  # Minimum 150mm per CNR
        assert result['l_min'] >= result['l_e']

    def test_calculate_capacity_increase(self, arch_design_cfrp):
        """Test capacity increase calculation"""
        original_capacity = 20.0  # kN

        result = arch_design_cfrp.calculate_capacity_increase(original_capacity)

        assert 'strengthening_contribution' in result
        assert 'total_capacity' in result
        assert 'capacity_increase_percent' in result

        # Strengthening should increase capacity
        assert result['total_capacity'] > original_capacity
        assert result['capacity_increase_percent'] > 0

    def test_capacity_increase_no_original(self, arch_design_cfrp):
        """Test capacity calculation without original capacity"""
        result = arch_design_cfrp.calculate_capacity_increase()

        assert result['strengthening_contribution'] > 0
        assert result['capacity_increase_percent'] == 0

    def test_generate_report(self, arch_design_cfrp):
        """Test report generation"""
        report = arch_design_cfrp.generate_report()

        assert isinstance(report, str)
        assert len(report) > 100
        assert "CNR-DT 200" in report
        assert "RINFORZO STRUTTURALE" in report
        assert "VERIFICA DELAMINAZIONE" in report

    def test_generate_report_with_capacity(self, arch_design_cfrp):
        """Test report with original capacity"""
        report = arch_design_cfrp.generate_report(original_capacity=20.0)

        assert "Capacità originale" in report
        assert "Incremento" in report

    def test_different_application_types(self, cfrp_material, masonry):
        """Test different application types"""
        types = [
            ApplicationType.ARCH_EXTRADOS,
            ApplicationType.ARCH_INTRADOS,
            ApplicationType.VAULT_EXTRADOS,
            ApplicationType.DOME_RING,
            ApplicationType.WALL_PLATING
        ]

        for app_type in types:
            design = StrengtheningDesign(
                application_type=app_type,
                material=cfrp_material,
                masonry=masonry,
                width=1.0,
                n_layers=1
            )

            # Should calculate without errors
            strength = design.calculate_design_strength()
            assert strength['F_fd'] > 0

    def test_multiple_layers_increase_capacity(self, cfrp_material, masonry):
        """Test that more layers increase capacity"""
        design_1_layer = StrengtheningDesign(
            application_type=ApplicationType.ARCH_EXTRADOS,
            material=cfrp_material,
            masonry=masonry,
            width=1.0,
            n_layers=1
        )

        design_2_layers = StrengtheningDesign(
            application_type=ApplicationType.ARCH_EXTRADOS,
            material=cfrp_material,
            masonry=masonry,
            width=1.0,
            n_layers=2
        )

        cap_1 = design_1_layer.calculate_capacity_increase()
        cap_2 = design_2_layers.calculate_capacity_increase()

        # 2 layers should provide ~2x capacity
        assert cap_2['strengthening_contribution'] > cap_1['strengthening_contribution']
        assert abs(cap_2['strengthening_contribution'] / cap_1['strengthening_contribution'] - 2.0) < 0.1

    def test_cfrp_vs_gfrp_comparison(self, masonry):
        """Test that CFRP provides more capacity than GFRP"""
        cfrp = FRPMaterial.from_database('CFRP_HM')
        gfrp = FRPMaterial.from_database('GFRP')

        design_cfrp = StrengtheningDesign(
            application_type=ApplicationType.ARCH_EXTRADOS,
            material=cfrp,
            masonry=masonry,
            width=1.0,
            n_layers=1
        )

        design_gfrp = StrengtheningDesign(
            application_type=ApplicationType.ARCH_EXTRADOS,
            material=gfrp,
            masonry=masonry,
            width=1.0,
            n_layers=1
        )

        cap_cfrp = design_cfrp.calculate_capacity_increase()
        cap_gfrp = design_gfrp.calculate_capacity_increase()

        # CFRP should provide more capacity (higher strength)
        assert cap_cfrp['strengthening_contribution'] > cap_gfrp['strengthening_contribution']


class TestMaterialDatabase:
    """Test material database"""

    def test_database_contains_materials(self):
        """Test that database contains expected materials"""
        assert 'CFRP_HM' in MATERIAL_DATABASE
        assert 'CFRP_HS' in MATERIAL_DATABASE
        assert 'GFRP' in MATERIAL_DATABASE
        assert 'AFRP' in MATERIAL_DATABASE
        assert 'C_FRCM' in MATERIAL_DATABASE
        assert 'G_FRCM' in MATERIAL_DATABASE

    def test_database_values_reasonable(self):
        """Test that database values are reasonable"""
        for mat_name, data in MATERIAL_DATABASE.items():
            # Tensile strength should be positive and reasonable
            assert 1000 <= data['tensile_strength'] <= 5000  # MPa

            # Elastic modulus should be positive and reasonable
            assert 50000 <= data['elastic_modulus'] <= 300000  # MPa

            # Ultimate strain should be positive
            assert 0.005 <= data['ultimate_strain'] <= 0.030


class TestSafetyFactors:
    """Test safety factors"""

    def test_safety_factors_defined(self):
        """Test that safety factors are defined"""
        assert 'gamma_f' in SAFETY_FACTORS
        assert 'gamma_m' in SAFETY_FACTORS
        assert 'gamma_fd' in SAFETY_FACTORS
        assert 'eta_a' in SAFETY_FACTORS

    def test_safety_factors_reasonable(self):
        """Test that safety factors have reasonable values"""
        assert SAFETY_FACTORS['gamma_f'] >= 1.0
        assert SAFETY_FACTORS['gamma_m'] >= 1.0
        assert SAFETY_FACTORS['gamma_fd'] >= 1.0
        assert 0.5 <= SAFETY_FACTORS['eta_a'] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
