#!/usr/bin/env python3
"""
Test suite per Material.materials
"""

import pytest
from Material.materials import MaterialProperties

class TestMaterialProperties:
    """Test per MaterialProperties"""

    def test_material_creation_valid(self):
        """Test creazione materiale con parametri validi"""
        mat = MaterialProperties(
            name="Test Material",
            E=1500.0,
            fcm=4.0,
            ftm=0.15,
            G=500.0,
            weight=18.0
        )

        assert mat.name == "Test Material"
        assert mat.E == 1500.0
        assert mat.fcm == 4.0
        assert mat.ftm == 0.15

    def test_material_validation_positive_E(self):
        """Test validazione modulo elastico positivo"""
        with pytest.raises((ValueError, AssertionError)):
            MaterialProperties(E=-1000.0, fcm=4.0)

    def test_material_validation_positive_fcm(self):
        """Test validazione resistenza compressione positiva"""
        with pytest.raises((ValueError, AssertionError)):
            MaterialProperties(E=1500.0, fcm=-4.0)

    def test_material_default_values(self):
        """Test valori di default"""
        mat = MaterialProperties(E=1500.0, fcm=4.0)

        # Verifica che abbia valori di default ragionevoli
        assert mat.weight > 0
        assert mat.G > 0 or mat.G is None

    def test_material_comparison(self):
        """Test confronto tra materiali"""
        mat1 = MaterialProperties(E=1500.0, fcm=4.0)
        mat2 = MaterialProperties(E=1500.0, fcm=4.0)
        mat3 = MaterialProperties(E=2000.0, fcm=5.0)

        # Stessa configurazione
        assert mat1.E == mat2.E
        assert mat1.fcm == mat2.fcm

        # Configurazione diversa
        assert mat1.E != mat3.E
        assert mat1.fcm != mat3.fcm

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
