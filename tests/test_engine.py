#!/usr/bin/env python3
"""
Test suite per Material.engine
"""

import pytest
from Material.engine import MasonryFEMEngine, AnalysisMethod
from Material.materials import MaterialProperties

class TestMasonryFEMEngine:
    """Test per MasonryFEMEngine"""

    @pytest.fixture
    def basic_material(self):
        """Materiale base per test"""
        return MaterialProperties(
            E=1500.0,
            fcm=4.0,
            ftm=0.15,
            tau0=0.1,
            mu=0.4,
            G=500.0,
            weight=18.0
        )

    @pytest.fixture
    def basic_wall_data(self):
        """Geometria base per test"""
        return {
            'length': 5.0,
            'height': 6.0,
            'thickness': 0.3,
            'n_floors': 2,
            'floor_masses': {0: 50000, 1: 45000}
        }

    def test_engine_creation(self):
        """Test creazione motore FEM"""
        engine = MasonryFEMEngine(method=AnalysisMethod.FRAME)
        assert engine.method == AnalysisMethod.FRAME
        assert engine.VERSION == "6.1-FINAL"

    def test_engine_all_methods(self):
        """Test creazione con tutti i metodi"""
        methods = [
            AnalysisMethod.FEM,
            AnalysisMethod.POR,
            AnalysisMethod.SAM,
            AnalysisMethod.FRAME,
            AnalysisMethod.LIMIT,
            AnalysisMethod.FIBER,
            AnalysisMethod.MICRO
        ]

        for method in methods:
            engine = MasonryFEMEngine(method=method)
            assert engine.method == method

    def test_frame_analysis_modal(self, basic_material, basic_wall_data):
        """Test analisi modale"""
        engine = MasonryFEMEngine(method=AnalysisMethod.FRAME)

        options = {
            'analysis_type': 'modal',
            'n_modes': 3
        }

        results = engine.analyze_structure(
            basic_wall_data,
            basic_material,
            {},
            options
        )

        # Verifica risultati base
        assert 'frequencies' in results
        assert 'periods' in results
        assert len(results['frequencies']) >= 1
        assert all(f > 0 for f in results['frequencies'])

    def test_frame_analysis_pushover(self, basic_material, basic_wall_data):
        """Test analisi pushover"""
        engine = MasonryFEMEngine(method=AnalysisMethod.FRAME)

        loads = {
            0: {'Fx': 0, 'Fy': -50},
            1: {'Fx': 0, 'Fy': -45}
        }

        options = {
            'analysis_type': 'pushover',
            'lateral_pattern': 'triangular',
            'target_drift': 0.02,
            'n_steps': 10
        }

        results = engine.analyze_structure(
            basic_wall_data,
            basic_material,
            loads,
            options
        )

        # Verifica risultati
        assert 'curve' in results
        assert 'performance_levels' in results
        assert len(results['curve']) > 0

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
