"""
Test suite for materials module
"""

import pytest
import numpy as np
from muratura import (
    MaterialProperties,
    MasonryType,
    MortarQuality,
    ConservationState,
    UnitSystem,
    UnitsConverter
)


class TestMaterialProperties:
    """Test MaterialProperties class"""

    def test_from_ntc_table(self):
        """Test creation from NTC table"""
        mat = MaterialProperties.from_ntc_table(
            MasonryType.MATTONI_PIENI,
            MortarQuality.BUONA
        )

        assert mat.fcm > 0
        assert mat.E > 0
        assert mat.G > 0
        assert mat.weight > 0

    def test_validation(self):
        """Test material validation"""
        mat = MaterialProperties(
            fcm=3.0,
            E=1500.0,
            G=600.0,
            nu=0.2
        )

        validation = mat.validate()
        assert validation['is_valid'] is True

    def test_invalid_material(self):
        """Test validation fails for invalid material"""
        mat = MaterialProperties(
            fcm=-1.0,  # Invalid: negative
            E=1500.0,
            G=600.0
        )

        validation = mat.validate()
        assert validation['is_valid'] is False
        assert len(validation['errors']) > 0

    def test_unit_conversion(self):
        """Test unit conversion"""
        mat_si = MaterialProperties(fcm=3.0, E=1500.0, weight=18.0)
        mat_tech = mat_si.convert_to(UnitSystem.TECHNICAL)

        # Check conversion is applied
        assert mat_tech.fcm != mat_si.fcm
        assert mat_tech.E != mat_si.E

        # Check Gf and Gc are NOT converted
        assert mat_tech.Gf == mat_si.Gf
        assert mat_tech.Gc == mat_si.Gc

    def test_json_export_import(self):
        """Test JSON export/import roundtrip"""
        mat1 = MaterialProperties.from_ntc_table(
            MasonryType.MATTONI_PIENI,
            MortarQuality.BUONA
        )

        json_str = mat1.to_json()
        mat2 = MaterialProperties.from_json(json_str=json_str)

        assert mat1.fcm == mat2.fcm
        assert mat1.E == mat2.E
        assert mat1.unit_system == mat2.unit_system

    def test_quick_creation(self):
        """Test quick creation with aliases"""
        mat = MaterialProperties.quick('MP', 'buona')

        assert mat.material_type == MasonryType.MATTONI_PIENI.value
        assert mat.fcm > 0


class TestUnitsConverter:
    """Test UnitsConverter class"""

    def test_stress_conversion(self):
        """Test stress unit conversion"""
        value_mpa = 10.0
        value_kgf = UnitsConverter.convert(value_mpa, 'MPa', 'kgf/cm2')

        assert abs(value_kgf - value_mpa * 10.197) < 0.01

    def test_reverse_conversion(self):
        """Test reverse conversion"""
        value = 100.0
        converted = UnitsConverter.convert(value, 'MPa', 'kPa')
        back = UnitsConverter.convert(converted, 'kPa', 'MPa')

        assert abs(back - value) < 0.001

    def test_same_unit(self):
        """Test conversion with same unit"""
        value = 50.0
        result = UnitsConverter.convert(value, 'MPa', 'MPa')

        assert result == value


class TestMaterialDatabase:
    """Test MaterialDatabase functionality"""

    def test_database_operations(self):
        """Test database add/get/search"""
        from muratura import MaterialDatabase
        import tempfile
        import os

        # Use temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            db_path = f.name

        try:
            db = MaterialDatabase(db_path)

            # Add material
            mat = MaterialProperties.quick('MP')
            db.add('test_material', mat)

            # Get material
            retrieved = db.get('test_material')
            assert retrieved is not None
            assert retrieved.fcm == mat.fcm

            # Search
            results = db.search(fcm=(2.0, 4.0))
            assert len(results) > 0

        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
