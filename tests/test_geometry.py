"""
Test suite for geometry module
"""

import pytest
from muratura import GeometryPier, GeometrySpandrel, BoundaryCondition


class TestGeometryPier:
    """Test GeometryPier class"""

    def test_basic_creation(self):
        """Test basic pier creation"""
        pier = GeometryPier(
            length=1.2,
            height=3.0,
            thickness=0.3
        )

        assert pier.length == 1.2
        assert pier.height == 3.0
        assert pier.thickness == 0.3

    def test_area_calculation(self):
        """Test area calculation"""
        pier = GeometryPier(
            length=1.2,
            height=3.0,
            thickness=0.3
        )

        expected_area = 1.2 * 0.3
        assert abs(pier.area - expected_area) < 0.001

    def test_slenderness(self):
        """Test slenderness ratio calculation"""
        pier = GeometryPier(
            length=1.0,
            height=4.0,
            thickness=0.3
        )

        # Slenderness = h0/t where h0 is effective height
        assert pier.slenderness_ratio > 0


class TestGeometrySpandrel:
    """Test GeometrySpandrel class"""

    def test_basic_creation(self):
        """Test basic spandrel creation"""
        spandrel = GeometrySpandrel(
            length=3.0,
            height=0.6,
            thickness=0.3
        )

        assert spandrel.length == 3.0
        assert spandrel.height == 0.6
        assert spandrel.thickness == 0.3

    def test_area_calculation(self):
        """Test area calculation"""
        spandrel = GeometrySpandrel(
            length=3.0,
            height=0.6,
            thickness=0.3
        )

        expected_area = 0.6 * 0.3
        assert abs(spandrel.area - expected_area) < 0.001


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
