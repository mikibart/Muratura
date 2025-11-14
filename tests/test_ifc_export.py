"""
Test suite per Material/bim/ifc_export.py

Test del modulo IFC Export per export risultati analisi in formato IFC.

Coverage:
- Creazione exporter
- Validazione settings
- Aggiunta nodi/membri/carichi
- Export file IFC
- Gestione errori

Run:
    pytest tests/test_ifc_export.py -v
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

# Try import
try:
    from Material.bim.ifc_export import (
        IFCExporter,
        IFCExportSettings,
        StructuralNode,
        StructuralMember,
        StructuralLoad
    )
    IFC_EXPORT_AVAILABLE = True
except ImportError:
    IFC_EXPORT_AVAILABLE = False


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def default_settings():
    """Settings di default per test."""
    return IFCExportSettings(
        ifc_version='2x3',
        schema='IFC2X3',
        organization='Test Org',
        author='Test Author',
        project_name='Test Project'
    )


@pytest.fixture
def sample_nodes():
    """Lista nodi di esempio."""
    return [
        StructuralNode(
            node_id=1,
            coordinates=(0.0, 0.0, 0.0),
            reactions={'Fx': 10.0, 'Fy': 0.0, 'Fz': -50.0},
            displacements={'Ux': 0.1, 'Uy': 0.0, 'Uz': -0.5}
        ),
        StructuralNode(
            node_id=2,
            coordinates=(5.0, 0.0, 0.0),
            reactions={'Fx': -10.0, 'Fy': 0.0, 'Fz': -50.0},
            displacements={'Ux': 0.2, 'Uy': 0.0, 'Uz': -0.6}
        ),
        StructuralNode(
            node_id=3,
            coordinates=(5.0, 0.0, 3.0),
            reactions={'Fx': 0.0, 'Fy': 0.0, 'Fz': 0.0},
            displacements={'Ux': 0.3, 'Uy': 0.05, 'Uz': -0.4}
        ),
        StructuralNode(
            node_id=4,
            coordinates=(0.0, 0.0, 3.0),
            reactions={'Fx': 0.0, 'Fy': 0.0, 'Fz': 0.0},
            displacements={'Ux': 0.25, 'Uy': 0.05, 'Uz': -0.45}
        ),
    ]


@pytest.fixture
def sample_members():
    """Lista membri di esempio."""
    return [
        StructuralMember(
            member_id='WALL_001',
            member_type='wall',
            node_ids=[1, 2, 3, 4],
            material='Masonry',
            thickness=0.30,  # m
            max_stress=1.5,  # MPa
            max_displacement=0.5,  # mm
            utilization_ratio=0.75,
            verification_status='VERIFICATO'
        ),
        StructuralMember(
            member_id='SLAB_001',
            member_type='slab',
            node_ids=[5, 6, 7, 8],
            material='Concrete',
            thickness=0.20,
            max_stress=2.0,
            max_displacement=1.2,
            utilization_ratio=0.85,
            verification_status='VERIFICATO'
        ),
    ]


@pytest.fixture
def sample_loads():
    """Lista carichi di esempio."""
    return [
        StructuralLoad(
            load_id='LOAD_DEAD_001',
            load_type='dead',
            load_case='G1',
            applied_to='WALL_001',
            distributed_load=5.0  # kN/m²
        ),
        StructuralLoad(
            load_id='LOAD_LIVE_001',
            load_type='live',
            load_case='Q1',
            applied_to='SLAB_001',
            distributed_load=2.0
        ),
        StructuralLoad(
            load_id='LOAD_POINT_001',
            load_type='dead',
            load_case='G2',
            applied_to='1',  # Node ID
            force=(0.0, 0.0, -10.0)  # kN
        ),
    ]


# ============================================================================
# TESTS - Dataclasses
# ============================================================================

def test_structural_node_creation():
    """Test creazione StructuralNode."""
    node = StructuralNode(
        node_id=1,
        coordinates=(1.0, 2.0, 3.0),
        reactions={'Fx': 10.0},
        displacements={'Ux': 0.1}
    )

    assert node.node_id == 1
    assert node.coordinates == (1.0, 2.0, 3.0)
    assert node.reactions['Fx'] == 10.0
    assert node.displacements['Ux'] == 0.1


def test_structural_member_creation():
    """Test creazione StructuralMember."""
    member = StructuralMember(
        member_id='W001',
        member_type='wall',
        node_ids=[1, 2, 3, 4],
        material='Masonry',
        thickness=0.30
    )

    assert member.member_id == 'W001'
    assert member.member_type == 'wall'
    assert len(member.node_ids) == 4
    assert member.thickness == 0.30


def test_structural_load_creation():
    """Test creazione StructuralLoad."""
    load = StructuralLoad(
        load_id='L001',
        load_type='dead',
        load_case='G1',
        applied_to='WALL_001',
        distributed_load=5.0
    )

    assert load.load_id == 'L001'
    assert load.load_type == 'dead'
    assert load.distributed_load == 5.0


def test_ifc_export_settings_defaults():
    """Test IFCExportSettings con valori di default."""
    settings = IFCExportSettings()

    assert settings.ifc_version == '2x3'
    assert settings.schema == 'IFC2X3'
    assert settings.export_loads is True
    assert settings.export_results is True
    assert settings.unit_system == 'METER'


def test_ifc_export_settings_custom():
    """Test IFCExportSettings con valori personalizzati."""
    settings = IFCExportSettings(
        ifc_version='4',
        schema='IFC4',
        export_loads=False,
        unit_system='MILLIMETER',
        organization='My Org',
        author='John Doe'
    )

    assert settings.ifc_version == '4'
    assert settings.schema == 'IFC4'
    assert settings.export_loads is False
    assert settings.unit_system == 'MILLIMETER'
    assert settings.organization == 'My Org'


# ============================================================================
# TESTS - IFCExporter Initialization
# ============================================================================

@pytest.mark.skipif(not IFC_EXPORT_AVAILABLE, reason="IFC export module not available")
@patch('Material.bim.ifc_export.ifcopenshell')
def test_exporter_initialization(mock_ifcopenshell, default_settings):
    """Test inizializzazione IFCExporter."""
    mock_file = MagicMock()
    mock_ifcopenshell.file.return_value = mock_file

    exporter = IFCExporter(default_settings)

    assert exporter.settings == default_settings
    assert exporter.nodes == []
    assert exporter.members == []
    assert exporter.loads == []
    assert exporter.ifc_nodes == {}
    assert exporter.ifc_members == {}


@pytest.mark.skipif(not IFC_EXPORT_AVAILABLE, reason="IFC export module not available")
def test_exporter_initialization_no_ifcopenshell():
    """Test inizializzazione senza ifcopenshell."""
    # Temporarily set IFC_AVAILABLE to False
    import Material.bim.ifc_export as ifc_module
    original = ifc_module.IFC_AVAILABLE
    ifc_module.IFC_AVAILABLE = False

    with pytest.raises(ImportError, match="ifcopenshell is required"):
        IFCExporter()

    # Restore
    ifc_module.IFC_AVAILABLE = original


@pytest.mark.skipif(not IFC_EXPORT_AVAILABLE, reason="IFC export module not available")
@patch('Material.bim.ifc_export.ifcopenshell')
def test_exporter_invalid_version(mock_ifcopenshell):
    """Test validazione versione IFC."""
    mock_file = MagicMock()
    mock_ifcopenshell.file.return_value = mock_file

    settings = IFCExportSettings(ifc_version='invalid')

    with pytest.raises(ValueError, match="ifc_version must be one of"):
        IFCExporter(settings)


@pytest.mark.skipif(not IFC_EXPORT_AVAILABLE, reason="IFC export module not available")
@patch('Material.bim.ifc_export.ifcopenshell')
def test_exporter_invalid_schema(mock_ifcopenshell):
    """Test validazione schema."""
    mock_file = MagicMock()
    mock_ifcopenshell.file.return_value = mock_file

    settings = IFCExportSettings(schema='INVALID')

    with pytest.raises(ValueError, match="schema must be one of"):
        IFCExporter(settings)


@pytest.mark.skipif(not IFC_EXPORT_AVAILABLE, reason="IFC export module not available")
@patch('Material.bim.ifc_export.ifcopenshell')
def test_exporter_invalid_unit_system(mock_ifcopenshell):
    """Test validazione unit system."""
    mock_file = MagicMock()
    mock_ifcopenshell.file.return_value = mock_file

    settings = IFCExportSettings(unit_system='INVALID')

    with pytest.raises(ValueError, match="unit_system must be one of"):
        IFCExporter(settings)


# ============================================================================
# TESTS - Add Data
# ============================================================================

@pytest.mark.skipif(not IFC_EXPORT_AVAILABLE, reason="IFC export module not available")
@patch('Material.bim.ifc_export.ifcopenshell')
def test_add_node(mock_ifcopenshell, default_settings, sample_nodes):
    """Test aggiunta singolo nodo."""
    mock_file = MagicMock()
    mock_ifcopenshell.file.return_value = mock_file

    exporter = IFCExporter(default_settings)
    exporter.add_node(sample_nodes[0])

    assert len(exporter.nodes) == 1
    assert exporter.nodes[0].node_id == 1


@pytest.mark.skipif(not IFC_EXPORT_AVAILABLE, reason="IFC export module not available")
@patch('Material.bim.ifc_export.ifcopenshell')
def test_add_nodes(mock_ifcopenshell, default_settings, sample_nodes):
    """Test aggiunta lista nodi."""
    mock_file = MagicMock()
    mock_ifcopenshell.file.return_value = mock_file

    exporter = IFCExporter(default_settings)
    exporter.add_nodes(sample_nodes)

    assert len(exporter.nodes) == 4
    assert exporter.nodes[0].node_id == 1
    assert exporter.nodes[3].node_id == 4


@pytest.mark.skipif(not IFC_EXPORT_AVAILABLE, reason="IFC export module not available")
@patch('Material.bim.ifc_export.ifcopenshell')
def test_add_member(mock_ifcopenshell, default_settings, sample_members):
    """Test aggiunta singolo membro."""
    mock_file = MagicMock()
    mock_ifcopenshell.file.return_value = mock_file

    exporter = IFCExporter(default_settings)
    exporter.add_member(sample_members[0])

    assert len(exporter.members) == 1
    assert exporter.members[0].member_id == 'WALL_001'


@pytest.mark.skipif(not IFC_EXPORT_AVAILABLE, reason="IFC export module not available")
@patch('Material.bim.ifc_export.ifcopenshell')
def test_add_members(mock_ifcopenshell, default_settings, sample_members):
    """Test aggiunta lista membri."""
    mock_file = MagicMock()
    mock_ifcopenshell.file.return_value = mock_file

    exporter = IFCExporter(default_settings)
    exporter.add_members(sample_members)

    assert len(exporter.members) == 2
    assert exporter.members[0].member_type == 'wall'
    assert exporter.members[1].member_type == 'slab'


@pytest.mark.skipif(not IFC_EXPORT_AVAILABLE, reason="IFC export module not available")
@patch('Material.bim.ifc_export.ifcopenshell')
def test_add_load(mock_ifcopenshell, default_settings, sample_loads):
    """Test aggiunta singolo carico."""
    mock_file = MagicMock()
    mock_ifcopenshell.file.return_value = mock_file

    exporter = IFCExporter(default_settings)
    exporter.add_load(sample_loads[0])

    assert len(exporter.loads) == 1
    assert exporter.loads[0].load_type == 'dead'


@pytest.mark.skipif(not IFC_EXPORT_AVAILABLE, reason="IFC export module not available")
@patch('Material.bim.ifc_export.ifcopenshell')
def test_add_loads(mock_ifcopenshell, default_settings, sample_loads):
    """Test aggiunta lista carichi."""
    mock_file = MagicMock()
    mock_ifcopenshell.file.return_value = mock_file

    exporter = IFCExporter(default_settings)
    exporter.add_loads(sample_loads)

    assert len(exporter.loads) == 3
    assert exporter.loads[0].load_case == 'G1'
    assert exporter.loads[2].force == (0.0, 0.0, -10.0)


# ============================================================================
# TESTS - Export
# ============================================================================

@pytest.mark.skipif(not IFC_EXPORT_AVAILABLE, reason="IFC export module not available")
@patch('Material.bim.ifc_export.ifcopenshell')
def test_export_empty_fails(mock_ifcopenshell, default_settings, tmp_path):
    """Test export senza dati fallisce."""
    mock_file = MagicMock()
    mock_ifcopenshell.file.return_value = mock_file

    exporter = IFCExporter(default_settings)
    output_file = tmp_path / "test.ifc"

    with pytest.raises(ValueError, match="No structural data to export"):
        exporter.export(str(output_file))


@pytest.mark.skipif(not IFC_EXPORT_AVAILABLE, reason="IFC export module not available")
@patch('Material.bim.ifc_export.ifcopenshell')
def test_export_with_nodes_only(mock_ifcopenshell, default_settings, sample_nodes, tmp_path):
    """Test export con solo nodi."""
    mock_file = MagicMock()
    mock_ifcopenshell.file.return_value = mock_file
    mock_ifcopenshell.guid.compress = lambda x: f"GUID_{x[:8]}"

    exporter = IFCExporter(default_settings)
    exporter.add_nodes(sample_nodes)

    output_file = tmp_path / "test.ifc"
    result = exporter.export(str(output_file))

    assert result == output_file
    # Verifica chiamata write
    mock_file.write.assert_called_once()


@pytest.mark.skipif(not IFC_EXPORT_AVAILABLE, reason="IFC export module not available")
@patch('Material.bim.ifc_export.ifcopenshell')
def test_export_with_members_only(mock_ifcopenshell, default_settings, sample_nodes, sample_members, tmp_path):
    """Test export con membri."""
    mock_file = MagicMock()
    mock_ifcopenshell.file.return_value = mock_file
    mock_ifcopenshell.guid.compress = lambda x: f"GUID_{x[:8]}"

    exporter = IFCExporter(default_settings)
    exporter.add_nodes(sample_nodes)  # Serve per coordinate
    exporter.add_members(sample_members)

    output_file = tmp_path / "test.ifc"
    result = exporter.export(str(output_file))

    assert result == output_file
    mock_file.write.assert_called_once()


# ============================================================================
# TESTS - Get Summary
# ============================================================================

@pytest.mark.skipif(not IFC_EXPORT_AVAILABLE, reason="IFC export module not available")
@patch('Material.bim.ifc_export.ifcopenshell')
def test_get_summary_empty(mock_ifcopenshell, default_settings):
    """Test riepilogo exporter vuoto."""
    mock_file = MagicMock()
    mock_ifcopenshell.file.return_value = mock_file

    exporter = IFCExporter(default_settings)
    summary = exporter.get_summary()

    assert summary['nodes_count'] == 0
    assert summary['members_count'] == 0
    assert summary['loads_count'] == 0
    assert summary['ifc_version'] == '2x3'
    assert summary['schema'] == 'IFC2X3'


@pytest.mark.skipif(not IFC_EXPORT_AVAILABLE, reason="IFC export module not available")
@patch('Material.bim.ifc_export.ifcopenshell')
def test_get_summary_with_data(mock_ifcopenshell, default_settings, sample_nodes, sample_members, sample_loads):
    """Test riepilogo exporter con dati."""
    mock_file = MagicMock()
    mock_ifcopenshell.file.return_value = mock_file

    exporter = IFCExporter(default_settings)
    exporter.add_nodes(sample_nodes)
    exporter.add_members(sample_members)
    exporter.add_loads(sample_loads)

    summary = exporter.get_summary()

    assert summary['nodes_count'] == 4
    assert summary['members_count'] == 2
    assert summary['loads_count'] == 3
    assert summary['export_loads'] is True
    assert summary['export_results'] is True
    assert summary['project_name'] == 'Test Project'


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, '-v'])
