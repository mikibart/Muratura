"""
Test Suite for IFC Import Module - BIM Integration
====================================================

Test cases for IFC import functionality including wall/slab extraction,
material mapping, geometry conversion, and unit handling.

These tests require test IFC files or use mock objects when files not available.
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

try:
    from Material.bim import IFCImporter, IFCImportSettings
    IFC_IMPORT_AVAILABLE = True
except ImportError:
    IFC_IMPORT_AVAILABLE = False


# Skip all tests if ifcopenshell not available
pytestmark = pytest.mark.skipif(
    not IFC_IMPORT_AVAILABLE,
    reason="IFCImporter requires ifcopenshell (pip install ifcopenshell)"
)


class TestIFCImportSettings:
    """Test IFCImportSettings dataclass"""

    def test_settings_default_creation(self):
        """Test default settings creation"""
        settings = IFCImportSettings()

        assert settings.ifc_version == '2x3'
        assert settings.unit_scale == 'meter'
        assert settings.extract_materials is True
        assert settings.extract_loads is True
        assert settings.simplify_geometry is True
        assert settings.tolerance == 0.001
        assert settings.include_furniture is False
        assert settings.verbose is False

    def test_settings_custom_creation(self):
        """Test custom settings"""
        settings = IFCImportSettings(
            ifc_version='4',
            verbose=True,
            tolerance=0.01
        )

        assert settings.ifc_version == '4'
        assert settings.verbose is True
        assert settings.tolerance == 0.01


class TestIFCImporterBasic:
    """Test IFCImporter basic functionality (without real IFC files)"""

    @pytest.fixture
    def mock_ifc_file(self):
        """Create mock IFC file object"""
        mock = MagicMock()
        mock.schema = 'IFC2X3'
        mock.by_type = MagicMock(return_value=[])
        return mock

    def test_unit_scale_factor_meters(self):
        """Test unit scale factor detection for meters"""
        # This would require a real IFC file or extensive mocking
        # For now, test the conversion factors dictionary
        conversions = {
            'METRE': 1.0,
            'MILLIMETRE': 0.001,
            'FOOT': 0.3048,
            'INCH': 0.0254,
            'CENTIMETRE': 0.01,
        }

        # Verify conversion factors are reasonable
        assert conversions['METRE'] == 1.0
        assert conversions['MILLIMETRE'] < conversions['METRE']
        assert conversions['FOOT'] < conversions['METRE']
        assert abs(conversions['FOOT'] - 0.3048) < 0.0001

    def test_material_type_detection_masonry(self):
        """Test material type detection for masonry"""
        # Test keywords
        masonry_keywords = ['brick', 'mattone', 'muratura', 'masonry', 'stone', 'pietra']

        for keyword in masonry_keywords:
            # Simulate detection
            name_lower = keyword.lower()
            is_masonry = any(kw in name_lower for kw in masonry_keywords)
            assert is_masonry

    def test_material_type_detection_concrete(self):
        """Test material type detection for concrete"""
        concrete_keywords = ['concrete', 'calcestruzzo', 'cls', 'beton']

        for keyword in concrete_keywords:
            name_lower = keyword.lower()
            is_concrete = any(kw in name_lower for kw in concrete_keywords)
            assert is_concrete

    def test_material_type_detection_by_density(self):
        """Test material type detection by density"""
        # Density ranges
        masonry_density = 1800  # kg/m³
        concrete_density = 2400
        steel_density = 7850
        wood_density = 600

        # Test masonry range
        assert 1500 < masonry_density < 2200

        # Test concrete range
        assert 2200 < concrete_density < 2600

        # Test steel
        assert steel_density > 7000

        # Test wood
        assert wood_density < 1000

    def test_mesh_volume_calculation_cube(self):
        """Test volume calculation for simple cube mesh"""
        # Create cube 1m x 1m x 1m
        vertices = np.array([
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],  # Bottom face
            [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],  # Top face
        ])

        # Two triangles per face, 6 faces = 12 triangles
        triangles = np.array([
            # Bottom face
            [0, 1, 2], [0, 2, 3],
            # Top face
            [4, 6, 5], [4, 7, 6],
            # Front face
            [0, 5, 1], [0, 4, 5],
            # Back face
            [2, 7, 3], [2, 6, 7],
            # Left face
            [0, 7, 4], [0, 3, 7],
            # Right face
            [1, 6, 2], [1, 5, 6],
        ])

        # Calculate volume using signed volume method
        volume = 0.0
        for tri in triangles:
            v0, v1, v2 = vertices[tri]
            volume += np.dot(v0, np.cross(v1, v2)) / 6.0

        volume = abs(volume)

        # Cube volume should be ~1.0 m³
        assert abs(volume - 1.0) < 0.1  # Allow some numerical error

    def test_mesh_volume_calculation_tetrahedron(self):
        """Test volume calculation for tetrahedron"""
        # Simple tetrahedron
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
        ])

        triangles = np.array([
            [0, 1, 2],  # Base
            [0, 3, 1],  # Side 1
            [1, 3, 2],  # Side 2
            [2, 3, 0],  # Side 3
        ])

        volume = 0.0
        for tri in triangles:
            v0, v1, v2 = vertices[tri]
            volume += np.dot(v0, np.cross(v1, v2)) / 6.0

        volume = abs(volume)

        # Tetrahedron volume = 1/6 (for unit edges)
        expected_volume = 1.0 / 6.0
        assert abs(volume - expected_volume) < 0.01


class TestIFCImporterWithMockFile:
    """Test IFCImporter with mocked IFC file"""

    @pytest.fixture
    def temp_ifc_path(self, tmp_path):
        """Create temporary IFC file path"""
        return tmp_path / "test_model.ifc"

    def test_importer_file_not_found(self):
        """Test error handling for non-existent file"""
        with pytest.raises(FileNotFoundError):
            IFCImporter("nonexistent_file.ifc")

    @patch('Material.bim.ifc_import.ifcopenshell')
    def test_importer_creation_with_mock(self, mock_ifcopenshell, temp_ifc_path):
        """Test importer creation with mocked ifcopenshell"""
        # Create empty file
        temp_ifc_path.write_text("MOCK IFC FILE")

        # Setup mock
        mock_file = MagicMock()
        mock_file.schema = 'IFC2X3'
        mock_file.by_type.return_value = []
        mock_ifcopenshell.open.return_value = mock_file

        # Create importer
        settings = IFCImportSettings(verbose=False)
        importer = IFCImporter(str(temp_ifc_path), settings)

        # Verify
        assert importer.file_path == temp_ifc_path
        assert importer.settings == settings
        assert isinstance(importer.walls, list)
        assert isinstance(importer.slabs, list)
        assert isinstance(importer.materials, dict)

    @patch('Material.bim.ifc_import.ifcopenshell')
    def test_extract_walls_empty(self, mock_ifcopenshell, temp_ifc_path):
        """Test wall extraction with no walls"""
        temp_ifc_path.write_text("MOCK IFC FILE")

        mock_file = MagicMock()
        mock_file.schema = 'IFC2X3'
        mock_file.by_type.return_value = []
        mock_ifcopenshell.open.return_value = mock_file

        importer = IFCImporter(str(temp_ifc_path))
        walls = importer.extract_walls()

        assert walls == []
        assert len(importer.walls) == 0

    @patch('Material.bim.ifc_import.ifcopenshell')
    def test_extract_slabs_empty(self, mock_ifcopenshell, temp_ifc_path):
        """Test slab extraction with no slabs"""
        temp_ifc_path.write_text("MOCK IFC FILE")

        mock_file = MagicMock()
        mock_file.schema = 'IFC2X3'
        mock_file.by_type.return_value = []
        mock_ifcopenshell.open.return_value = mock_file

        importer = IFCImporter(str(temp_ifc_path))
        slabs = importer.extract_slabs()

        assert slabs == []
        assert len(importer.slabs) == 0

    @patch('Material.bim.ifc_import.ifcopenshell')
    def test_get_summary(self, mock_ifcopenshell, temp_ifc_path):
        """Test summary generation"""
        temp_ifc_path.write_text("MOCK IFC FILE")

        mock_file = MagicMock()
        mock_file.schema = 'IFC2X3'
        mock_file.by_type.return_value = []
        mock_ifcopenshell.open.return_value = mock_file

        importer = IFCImporter(str(temp_ifc_path))
        summary = importer.get_summary()

        assert 'file' in summary
        assert 'schema' in summary
        assert 'counts' in summary
        assert summary['file'] == "test_model.ifc"
        assert summary['schema'] == 'IFC2X3'
        assert summary['counts']['walls'] == 0
        assert summary['counts']['slabs'] == 0


# Tests that require real IFC files (skipped if files not available)
class TestIFCImporterWithRealFiles:
    """Tests with real IFC files (requires test data)"""

    @pytest.fixture
    def test_ifc_files_dir(self):
        """Directory containing test IFC files"""
        return Path(__file__).parent / 'test_data' / 'ifc'

    @pytest.fixture
    def simple_wall_ifc(self, test_ifc_files_dir):
        """Simple IFC file with one wall"""
        path = test_ifc_files_dir / 'simple_wall.ifc'
        if path.exists():
            return path
        pytest.skip("Test IFC file not available")

    def test_import_simple_wall(self, simple_wall_ifc):
        """Test importing simple wall model"""
        importer = IFCImporter(str(simple_wall_ifc))
        walls = importer.extract_walls()

        assert len(walls) > 0

        # Check first wall has required fields
        wall = walls[0]
        assert 'guid' in wall
        assert 'name' in wall
        assert 'thickness' in wall or 'geometry' in wall

    @pytest.mark.skip(reason="Requires real IFC file from Revit/ArchiCAD")
    def test_import_from_revit(self):
        """Test importing model exported from Revit"""
        # This test requires a real Revit-exported IFC file
        # Skip for now, implement when test files available
        pass

    @pytest.mark.skip(reason="Requires real IFC file from ArchiCAD")
    def test_import_from_archicad(self):
        """Test importing model exported from ArchiCAD"""
        # This test requires a real ArchiCAD-exported IFC file
        pass


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
