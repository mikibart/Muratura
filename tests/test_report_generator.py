"""
Test Suite for Report Generator Module
========================================

Test cases for automatic report generation including PDF, DOCX, and Markdown
output formats with NTC 2018 compliance.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import tempfile

try:
    from Material.reports import ReportGenerator, ReportMetadata, ReportSettings
    REPORT_GENERATOR_AVAILABLE = True
except ImportError:
    REPORT_GENERATOR_AVAILABLE = False


# Skip all tests if report generator not available
pytestmark = pytest.mark.skipif(
    not REPORT_GENERATOR_AVAILABLE,
    reason="ReportGenerator requires jinja2 and matplotlib"
)


class TestReportMetadata:
    """Test ReportMetadata dataclass"""

    def test_metadata_creation_minimal(self):
        """Test metadata creation with minimal required fields"""
        metadata = ReportMetadata(
            project_name="Test Project",
            project_location="Rome (RM)",
            client_name="Test Client",
            designer_name="Ing. Test",
            designer_order="Order n. 12345"
        )

        assert metadata.project_name == "Test Project"
        assert metadata.project_location == "Rome (RM)"
        assert metadata.client_name == "Test Client"
        assert metadata.designer_name == "Ing. Test"
        assert metadata.designer_order == "Order n. 12345"
        assert metadata.revision == "0"  # Default
        assert metadata.report_type == "calcolo"  # Default

    def test_metadata_creation_complete(self):
        """Test metadata creation with all fields"""
        metadata = ReportMetadata(
            project_name="Complete Project",
            project_location="Milan (MI)",
            project_address="Via Test 123",
            client_name="Client SpA",
            client_address="Via Cliente 456",
            designer_name="Ing. Designer",
            designer_order="Order Engineers Milan n. 54321",
            designer_address="Via Studio 789",
            report_date="01/01/2025",
            revision="1",
            report_type="sismica"
        )

        assert metadata.project_address == "Via Test 123"
        assert metadata.client_address == "Via Cliente 456"
        assert metadata.designer_address == "Via Studio 789"
        assert metadata.report_date == "01/01/2025"
        assert metadata.revision == "1"
        assert metadata.report_type == "sismica"

    def test_metadata_auto_date(self):
        """Test that report_date is auto-generated if not provided"""
        metadata = ReportMetadata(
            project_name="Test",
            project_location="Test",
            client_name="Test",
            designer_name="Test",
            designer_order="Test"
        )

        # Should have a date in format DD/MM/YYYY
        assert len(metadata.report_date) == 10
        assert metadata.report_date.count('/') == 2


class TestReportSettings:
    """Test ReportSettings dataclass"""

    def test_settings_default_creation(self):
        """Test default settings"""
        settings = ReportSettings()

        assert settings.template_name == 'ntc2018_standard'
        assert settings.output_format == 'pdf'
        assert settings.include_graphs is True
        assert settings.include_tables is True
        assert settings.include_toc is True
        assert settings.include_appendix is False
        assert settings.language == 'it'
        assert settings.page_size == 'A4'
        assert settings.font_size == 11

    def test_settings_custom_creation(self):
        """Test custom settings"""
        settings = ReportSettings(
            template_name='ntc2018_historic',
            output_format='docx',
            include_graphs=False,
            font_size=12
        )

        assert settings.template_name == 'ntc2018_historic'
        assert settings.output_format == 'docx'
        assert settings.include_graphs is False
        assert settings.font_size == 12


class TestReportGeneratorBasic:
    """Test ReportGenerator basic functionality"""

    @pytest.fixture
    def mock_model(self):
        """Create mock structural model"""
        model = Mock()
        model.building_type = 'Masonry building'
        model.usage = 'Residential'
        model.num_stories = 3
        model.materials = []
        model.verification_results = []
        return model

    @pytest.fixture
    def test_metadata(self):
        """Create test metadata"""
        return ReportMetadata(
            project_name="Test Structural Report",
            project_location="Rome (RM)",
            client_name="Municipality of Rome",
            designer_name="Eng. Mario Rossi",
            designer_order="Order of Engineers of Rome n. 12345"
        )

    @pytest.fixture
    def test_settings(self):
        """Create test settings"""
        return ReportSettings(output_format='md')  # Markdown easiest to test

    def test_generator_creation(self, mock_model, test_metadata):
        """Test generator creation"""
        generator = ReportGenerator(mock_model, test_metadata)

        assert generator.model == mock_model
        assert generator.metadata == test_metadata
        assert generator.settings.output_format == 'pdf'  # Default
        assert isinstance(generator.figures, list)
        assert len(generator.figures) == 0

    def test_generator_with_settings(self, mock_model, test_metadata, test_settings):
        """Test generator with custom settings"""
        generator = ReportGenerator(mock_model, test_metadata, test_settings)

        assert generator.settings == test_settings
        assert generator.settings.output_format == 'md'

    def test_metadata_validation_missing_required(self, mock_model):
        """Test validation fails with missing required fields"""
        incomplete_metadata = ReportMetadata(
            project_name="",  # Empty - should fail
            project_location="Rome",
            client_name="Client",
            designer_name="Designer",
            designer_order="Order"
        )

        with pytest.raises(ValueError):
            ReportGenerator(mock_model, incomplete_metadata)

    def test_context_preparation(self, mock_model, test_metadata, test_settings):
        """Test _prepare_context() generates all required sections"""
        generator = ReportGenerator(mock_model, test_metadata, test_settings)
        context = generator._prepare_context()

        # Check all required sections present
        assert 'metadata' in context
        assert 'introduction' in context
        assert 'building_description' in context
        assert 'codes' in context
        assert 'materials' in context
        assert 'loads' in context
        assert 'verifications' in context
        assert 'conclusions' in context

        # Check metadata fields
        assert context['metadata']['project_name'] == "Test Structural Report"
        assert context['metadata']['client_name'] == "Municipality of Rome"

    def test_get_applicable_codes(self, mock_model, test_metadata):
        """Test normative codes list generation"""
        generator = ReportGenerator(mock_model, test_metadata)
        codes = generator._get_applicable_codes()

        assert isinstance(codes, list)
        assert len(codes) >= 4  # At minimum NTC 2018, Circ, EC6, EC8

        # Check key codes present
        codes_str = ' '.join(codes)
        assert 'NTC 2018' in codes_str
        assert 'Circolare' in codes_str
        assert 'Eurocodice' in codes_str

    def test_get_materials_summary_empty_model(self, mock_model, test_metadata):
        """Test materials summary with model without materials"""
        mock_model.materials = []
        generator = ReportGenerator(mock_model, test_metadata)

        materials = generator._get_materials_summary()

        # Should have at least placeholder material
        assert isinstance(materials, list)
        assert len(materials) > 0
        assert 'name' in materials[0]
        assert 'type' in materials[0]

    def test_get_verifications_summary(self, mock_model, test_metadata):
        """Test verifications summary generation"""
        # Add mock verification result
        mock_result = Mock()
        mock_result.element_id = 'Wall 1'
        mock_result.type = 'SLU'
        mock_result.demand = 1.5
        mock_result.capacity = 2.0

        mock_model.verification_results = [mock_result]

        generator = ReportGenerator(mock_model, test_metadata)
        verifications = generator._get_verifications_summary()

        assert isinstance(verifications, list)
        assert len(verifications) >= 1

        verif = verifications[0]
        assert verif['element'] == 'Wall 1'
        assert verif['demand'] == 1.5
        assert verif['capacity'] == 2.0
        assert verif['ratio'] == 0.75
        assert verif['status'] == 'VERIFICATO'

    def test_conclusions_all_passed(self, mock_model, test_metadata):
        """Test conclusions with all verifications passed"""
        generator = ReportGenerator(mock_model, test_metadata)
        conclusions = generator._get_conclusions()

        assert isinstance(conclusions, str)
        assert len(conclusions) > 0

        # Should contain positive message if all verifications pass
        # (default mock has 1 passing verification)
        assert 'SODDISFATTE' in conclusions or 'soddisfatte' in conclusions

    def test_get_tables(self, mock_model, test_metadata, test_settings):
        """Test table generation"""
        test_settings.include_tables = True
        generator = ReportGenerator(mock_model, test_metadata, test_settings)

        tables = generator._get_tables()

        assert isinstance(tables, list)

        if tables:
            table = tables[0]
            assert 'number' in table
            assert 'caption' in table
            assert 'headers' in table
            assert 'rows' in table


class TestReportGeneratorMarkdown:
    """Test Markdown report generation (easiest to test)"""

    @pytest.fixture
    def mock_model(self):
        model = Mock()
        model.building_type = 'Masonry'
        model.materials = []
        model.verification_results = []
        return model

    @pytest.fixture
    def test_metadata(self):
        return ReportMetadata(
            project_name="MD Test Project",
            project_location="Test City",
            client_name="Test Client",
            designer_name="Test Designer",
            designer_order="Test Order"
        )

    def test_generate_markdown_report(self, mock_model, test_metadata, tmp_path):
        """Test Markdown report generation"""
        settings = ReportSettings(output_format='md', include_graphs=False)
        generator = ReportGenerator(mock_model, test_metadata, settings)

        output_file = tmp_path / "test_report.md"
        result = generator.generate_report(str(output_file))

        # Check file created
        assert Path(result).exists()
        assert Path(result) == output_file

        # Check content
        content = output_file.read_text(encoding='utf-8')
        assert 'RELAZIONE DI CALCOLO' in content
        assert 'MD Test Project' in content
        assert 'Test Client' in content
        assert 'PREMESSA' in content
        assert 'NORMATIVA' in content


class TestReportGeneratorPDF:
    """Test PDF report generation (requires LaTeX)"""

    @pytest.fixture
    def mock_model(self):
        model = Mock()
        model.building_type = 'Masonry'
        model.materials = []
        model.verification_results = []
        return model

    @pytest.fixture
    def test_metadata(self):
        return ReportMetadata(
            project_name="PDF Test",
            project_location="Rome",
            client_name="Client",
            designer_name="Designer",
            designer_order="Order"
        )

    @pytest.mark.skip(reason="Requires LaTeX installation (pdflatex)")
    def test_generate_pdf_report(self, mock_model, test_metadata, tmp_path):
        """Test PDF generation (requires pdflatex)"""
        settings = ReportSettings(output_format='pdf', include_graphs=False)
        generator = ReportGenerator(mock_model, test_metadata, settings)

        output_file = tmp_path / "test_report.pdf"
        result = generator.generate_report(str(output_file))

        # Check file created
        assert Path(result).exists()
        assert Path(result).suffix == '.pdf'

    def test_minimal_latex_template(self, mock_model, test_metadata):
        """Test minimal LaTeX template generation"""
        generator = ReportGenerator(mock_model, test_metadata)
        template = generator._get_minimal_latex_template()

        # Check template is valid Jinja2 template
        assert template is not None

        # Render with minimal context
        context = {
            'settings': ReportSettings(),
            'metadata': {
                'project_name': 'Test',
                'designer_name': 'Test',
                'designer_order': 'Test',
                'report_date': '01/01/2025',
            },
            'introduction': 'Test intro',
            'building_description': {'text': 'Test desc'},
            'codes': ['NTC 2018'],
            'tables': [],
            'conclusions': 'Test conclusions',
        }

        rendered = template.render(**context)

        # Check LaTeX structure
        assert r'\documentclass' in rendered
        assert r'\begin{document}' in rendered
        assert r'\end{document}' in rendered
        assert 'Test' in rendered


class TestReportGeneratorDOCX:
    """Test DOCX report generation"""

    @pytest.fixture
    def mock_model(self):
        model = Mock()
        model.building_type = 'Masonry'
        model.materials = []
        model.verification_results = []
        return model

    @pytest.fixture
    def test_metadata(self):
        return ReportMetadata(
            project_name="DOCX Test",
            project_location="Milan",
            client_name="Client",
            designer_name="Designer",
            designer_order="Order"
        )

    @pytest.mark.skipif(
        not REPORT_GENERATOR_AVAILABLE,
        reason="Requires python-docx"
    )
    def test_generate_docx_report(self, mock_model, test_metadata, tmp_path):
        """Test DOCX generation"""
        settings = ReportSettings(output_format='docx', include_graphs=False)
        generator = ReportGenerator(mock_model, test_metadata, settings)

        output_file = tmp_path / "test_report.docx"
        result = generator.generate_report(str(output_file))

        # Check file created
        assert Path(result).exists()
        assert Path(result).suffix == '.docx'

        # Check file size (should be > 0)
        assert Path(result).stat().st_size > 0


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
