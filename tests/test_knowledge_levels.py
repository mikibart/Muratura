"""
Test Suite for Knowledge Levels Module - NTC 2018
=================================================

Test cases for knowledge level assessment and confidence factors
according to NTC 2018 §8.5.4 and Circolare §C8.5.4.
"""

import pytest
from Material.analyses.historic.knowledge_levels import (
    KnowledgeAssessment,
    KnowledgeLevel,
    InvestigationLevel,
    MaterialProperties,
    CONFIDENCE_FACTORS,
    INVESTIGATION_DESCRIPTIONS
)


class TestKnowledgeLevel:
    """Test KnowledgeLevel enum"""

    def test_knowledge_levels_defined(self):
        """Test that knowledge levels are defined"""
        assert KnowledgeLevel.LC1.value == 'LC1'
        assert KnowledgeLevel.LC2.value == 'LC2'
        assert KnowledgeLevel.LC3.value == 'LC3'


class TestInvestigationLevel:
    """Test InvestigationLevel enum"""

    def test_investigation_levels_defined(self):
        """Test that investigation levels are defined"""
        assert InvestigationLevel.LIMITED.value == 'limited'
        assert InvestigationLevel.EXTENDED.value == 'extended'
        assert InvestigationLevel.EXHAUSTIVE.value == 'exhaustive'


class TestConfidenceFactors:
    """Test confidence factors database"""

    def test_confidence_factors_defined(self):
        """Test that confidence factors are defined for all levels"""
        assert KnowledgeLevel.LC1 in CONFIDENCE_FACTORS
        assert KnowledgeLevel.LC2 in CONFIDENCE_FACTORS
        assert KnowledgeLevel.LC3 in CONFIDENCE_FACTORS

    def test_confidence_factors_values(self):
        """Test confidence factor values according to NTC 2018"""
        assert CONFIDENCE_FACTORS[KnowledgeLevel.LC1] == 1.35
        assert CONFIDENCE_FACTORS[KnowledgeLevel.LC2] == 1.20
        assert CONFIDENCE_FACTORS[KnowledgeLevel.LC3] == 1.00

    def test_confidence_factors_order(self):
        """Test that FC decreases with increasing knowledge"""
        FC_LC1 = CONFIDENCE_FACTORS[KnowledgeLevel.LC1]
        FC_LC2 = CONFIDENCE_FACTORS[KnowledgeLevel.LC2]
        FC_LC3 = CONFIDENCE_FACTORS[KnowledgeLevel.LC3]

        assert FC_LC1 > FC_LC2 > FC_LC3


class TestMaterialProperties:
    """Test MaterialProperties dataclass"""

    def test_material_creation(self):
        """Test material properties creation"""
        material = MaterialProperties(
            f_m_k=2.5,
            f_v0_k=0.12,
            tau_0_k=0.06,
            E=1500,
            w=18.0
        )
        assert material.f_m_k == 2.5
        assert material.f_v0_k == 0.12
        assert material.E == 1500

    def test_apply_confidence_factor(self):
        """Test applying confidence factor to material"""
        material = MaterialProperties(f_m_k=2.4, tau_0_k=0.06)

        # Apply FC for LC1
        reduced = material.apply_confidence_factor(1.35)

        # Resistances should be reduced
        assert reduced.f_m_k < material.f_m_k
        assert reduced.tau_0_k < material.tau_0_k

        # Check exact reduction
        expected_fm = 2.4 / 1.35
        assert abs(reduced.f_m_k - expected_fm) < 0.001

    def test_elastic_modulus_not_reduced(self):
        """Test that elastic modulus is not reduced by FC"""
        material = MaterialProperties(f_m_k=2.0, E=1500)

        reduced = material.apply_confidence_factor(1.35)

        # E should remain the same
        assert reduced.E == material.E


class TestKnowledgeAssessment:
    """Test KnowledgeAssessment class"""

    def test_assessment_creation(self):
        """Test knowledge assessment creation"""
        assessment = KnowledgeAssessment(
            building_type='masonry',
            construction_period='1800-1900'
        )
        assert assessment.building_type == 'masonry'
        assert assessment.construction_period == '1800-1900'

    def test_set_geometry_investigation(self):
        """Test setting geometry investigation level"""
        assessment = KnowledgeAssessment()
        assessment.set_geometry_investigation('limited')

        assert assessment.investigation_data.geometry_level == InvestigationLevel.LIMITED

    def test_set_details_investigation(self):
        """Test setting details investigation level"""
        assessment = KnowledgeAssessment()
        assessment.set_details_investigation('extended')

        assert assessment.investigation_data.details_level == InvestigationLevel.EXTENDED

    def test_set_materials_investigation(self):
        """Test setting materials investigation level"""
        assessment = KnowledgeAssessment()
        assessment.set_materials_investigation('exhaustive')

        assert assessment.investigation_data.materials_level == InvestigationLevel.EXHAUSTIVE

    def test_calculate_lc1(self):
        """Test calculation of LC1 (Limited Knowledge)"""
        assessment = KnowledgeAssessment()
        assessment.set_geometry_investigation('limited')
        assessment.set_details_investigation('limited')
        assessment.set_materials_investigation('limited')

        result = assessment.calculate_knowledge_level()

        assert result['level'] == 'LC1'
        assert result['FC'] == 1.35

    def test_calculate_lc2(self):
        """Test calculation of LC2 (Adequate Knowledge)"""
        assessment = KnowledgeAssessment()
        assessment.set_geometry_investigation('extended')
        assessment.set_details_investigation('extended')
        assessment.set_materials_investigation('extended')

        result = assessment.calculate_knowledge_level()

        assert result['level'] == 'LC2'
        assert result['FC'] == 1.20

    def test_calculate_lc3(self):
        """Test calculation of LC3 (Accurate Knowledge)"""
        assessment = KnowledgeAssessment()
        assessment.set_geometry_investigation('exhaustive')
        assessment.set_details_investigation('exhaustive')
        assessment.set_materials_investigation('exhaustive')

        result = assessment.calculate_knowledge_level()

        assert result['level'] == 'LC3'
        assert result['FC'] == 1.00

    def test_incomplete_data_raises_error(self):
        """Test that incomplete investigation data raises error"""
        assessment = KnowledgeAssessment()
        assessment.set_geometry_investigation('limited')
        # Missing details and materials

        with pytest.raises(ValueError):
            assessment.calculate_knowledge_level()

    def test_mixed_investigation_levels_lc1(self):
        """Test that mixed levels typically result in LC1"""
        assessment = KnowledgeAssessment()
        assessment.set_geometry_investigation('exhaustive')
        assessment.set_details_investigation('limited')  # One limited
        assessment.set_materials_investigation('extended')

        result = assessment.calculate_knowledge_level()

        # With one limited, should be LC1
        assert result['level'] == 'LC1'

    def test_apply_to_material(self):
        """Test applying knowledge level to material properties"""
        assessment = KnowledgeAssessment()
        assessment.set_geometry_investigation('limited')
        assessment.set_details_investigation('limited')
        assessment.set_materials_investigation('limited')

        material = MaterialProperties(f_m_k=2.4)
        reduced = assessment.apply_to_material(material)

        # Should apply LC1 factor (1.35)
        expected = 2.4 / 1.35
        assert abs(reduced.f_m_k - expected) < 0.001

    def test_get_investigation_recommendations(self):
        """Test getting investigation recommendations"""
        assessment = KnowledgeAssessment()
        assessment.set_geometry_investigation('limited')
        assessment.set_details_investigation('limited')
        assessment.set_materials_investigation('limited')

        # Calculate level first
        assessment.calculate_knowledge_level()

        recommendations = assessment.get_investigation_recommendations()

        assert 'geometry' in recommendations
        assert 'details' in recommendations
        assert 'materials' in recommendations
        assert 'general' in recommendations

        # Should have recommendations for all limited categories
        assert len(recommendations['geometry']) > 0
        assert len(recommendations['details']) > 0
        assert len(recommendations['materials']) > 0

    def test_generate_report(self):
        """Test report generation"""
        assessment = KnowledgeAssessment(
            building_type='masonry',
            construction_period='1800-1900'
        )
        assessment.set_geometry_investigation('extended')
        assessment.set_details_investigation('extended')
        assessment.set_materials_investigation('extended')

        report = assessment.generate_report()

        assert isinstance(report, str)
        assert len(report) > 100
        assert 'LC2' in report or 'LC3' in report or 'LC1' in report
        assert 'NTC 2018' in report
        assert 'FATTORE DI CONFIDENZA' in report

    def test_progressive_improvement_lc(self):
        """Test that improving investigations improves LC"""
        # Start with LC1
        assessment1 = KnowledgeAssessment()
        assessment1.set_geometry_investigation('limited')
        assessment1.set_details_investigation('limited')
        assessment1.set_materials_investigation('limited')
        result1 = assessment1.calculate_knowledge_level()

        # Improve to LC2
        assessment2 = KnowledgeAssessment()
        assessment2.set_geometry_investigation('extended')
        assessment2.set_details_investigation('extended')
        assessment2.set_materials_investigation('extended')
        result2 = assessment2.calculate_knowledge_level()

        # Improve to LC3
        assessment3 = KnowledgeAssessment()
        assessment3.set_geometry_investigation('exhaustive')
        assessment3.set_details_investigation('exhaustive')
        assessment3.set_materials_investigation('exhaustive')
        result3 = assessment3.calculate_knowledge_level()

        # FC should decrease (better knowledge)
        assert result1['FC'] > result2['FC'] > result3['FC']

    def test_impact_on_design_strength(self):
        """Test impact of FC on design strength"""
        material = MaterialProperties(f_m_k=2.0)

        # LC1
        assessment_lc1 = KnowledgeAssessment()
        assessment_lc1.set_geometry_investigation('limited')
        assessment_lc1.set_details_investigation('limited')
        assessment_lc1.set_materials_investigation('limited')
        reduced_lc1 = assessment_lc1.apply_to_material(material)

        # LC3
        assessment_lc3 = KnowledgeAssessment()
        assessment_lc3.set_geometry_investigation('exhaustive')
        assessment_lc3.set_details_investigation('exhaustive')
        assessment_lc3.set_materials_investigation('exhaustive')
        reduced_lc3 = assessment_lc3.apply_to_material(material)

        # LC3 should have higher strength (FC=1.00 vs FC=1.35)
        assert reduced_lc3.f_m_k > reduced_lc1.f_m_k

        # Check exact ratio
        ratio = reduced_lc3.f_m_k / reduced_lc1.f_m_k
        expected_ratio = 1.35 / 1.00
        assert abs(ratio - expected_ratio) < 0.01


class TestInvestigationDescriptions:
    """Test investigation descriptions database"""

    def test_descriptions_available(self):
        """Test that descriptions are available for all categories"""
        assert 'geometry' in INVESTIGATION_DESCRIPTIONS
        assert 'details' in INVESTIGATION_DESCRIPTIONS
        assert 'materials' in INVESTIGATION_DESCRIPTIONS

    def test_descriptions_complete(self):
        """Test that descriptions exist for all levels"""
        for category in ['geometry', 'details', 'materials']:
            assert 'limited' in INVESTIGATION_DESCRIPTIONS[category]
            assert 'extended' in INVESTIGATION_DESCRIPTIONS[category]
            assert 'exhaustive' in INVESTIGATION_DESCRIPTIONS[category]


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
