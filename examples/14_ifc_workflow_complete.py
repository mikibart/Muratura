"""
MURATURA FEM - Complete IFC Workflow Example
Workflow completo BIM: IFC Import → Analysis → IFC Export

Questo script dimostra il workflow completo di integrazione BIM:
1. Import modello IFC da software BIM (Revit, ArchiCAD, etc.)
2. Analisi strutturale con Muratura FEM
3. Export risultati in formato IFC Structural Analysis View

Workflow:
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  Revit/     │      │  MURATURA    │      │  Tekla/     │
│  ArchiCAD   │ IFC  │  FEM         │ IFC  │  SAP2000    │
│  (Model)    │ ───> │  (Analysis)  │ ───> │  (Results)  │
└─────────────┘      └──────────────┘      └─────────────┘

Questo esempio usa dati mock per dimostrare il concetto.
In produzione, si userebbero modelli IFC reali.

Status: ✅ IMPLEMENTATO (Fase 3 - Module 4)
"""

from pathlib import Path
from unittest.mock import Mock
import tempfile

try:
    from Material.bim import (
        IFCImporter,
        IFCImportSettings,
        IFCExporter,
        IFCExportSettings,
        StructuralNode,
        StructuralMember,
        StructuralLoad
    )
    IFC_AVAILABLE = True
except ImportError:
    print("⚠️  IFC modules not available")
    print("   Install: pip install ifcopenshell")
    IFC_AVAILABLE = False
    exit(1)


def print_header(title: str):
    """Stampa intestazione esempio."""
    print("\n" + "=" * 70)
    print(f"ESEMPIO: {title}")
    print("=" * 70)


def create_mock_ifc_file():
    """
    Crea file IFC mock per dimostrazione.

    In produzione, questo sarebbe un vero file IFC esportato da Revit/ArchiCAD.
    """
    # In un caso reale, si importerebbe un file IFC esistente
    # Per questo esempio, usiamo dati mock
    return None


def analyze_structure(walls, materials):
    """
    Simula analisi strutturale.

    In produzione, questa funzione eseguirebbe l'analisi FEM completa
    usando i moduli Material.floors, Material.historic, etc.

    Args:
        walls: Lista pareti importate da IFC
        materials: Materiali importati da IFC

    Returns:
        Risultati analisi (nodi, membri con risultati, carichi)
    """
    print("\n🔧 Simulating structural analysis...")

    # Crea nodi strutturali (in reale: da mesh FEM)
    nodes = [
        StructuralNode(
            node_id=1,
            coordinates=(0.0, 0.0, 0.0),
            reactions={'Fx': 15.5, 'Fy': 0.0, 'Fz': -125.0},
            displacements={'Ux': 0.05, 'Uy': 0.0, 'Uz': -0.3}
        ),
        StructuralNode(
            node_id=2,
            coordinates=(6.0, 0.0, 0.0),
            reactions={'Fx': -15.5, 'Fy': 0.0, 'Fz': -125.0},
            displacements={'Ux': 0.08, 'Uy': 0.0, 'Uz': -0.35}
        ),
        StructuralNode(
            node_id=3,
            coordinates=(6.0, 0.0, 3.0),
            reactions={'Fx': 0.0, 'Fy': 0.0, 'Fz': 0.0},
            displacements={'Ux': 0.15, 'Uy': 0.02, 'Uz': -0.25}
        ),
        StructuralNode(
            node_id=4,
            coordinates=(0.0, 0.0, 3.0),
            reactions={'Fx': 0.0, 'Fy': 0.0, 'Fz': 0.0},
            displacements={'Ux': 0.12, 'Uy': 0.02, 'Uz': -0.28}
        ),
    ]

    # Crea membri strutturali con risultati analisi
    members = [
        StructuralMember(
            member_id='WALL_PERIMETER_NORTH',
            member_type='wall',
            node_ids=[1, 2, 3, 4],
            material='Muratura mattoni pieni malta calce',
            thickness=0.40,  # m
            max_stress=1.35,  # MPa
            max_displacement=0.35,  # mm
            utilization_ratio=0.68,  # 68% capacità
            verification_status='VERIFICATO'
        ),
        StructuralMember(
            member_id='WALL_INTERNAL_001',
            member_type='wall',
            node_ids=[5, 6, 7, 8],
            material='Muratura mattoni pieni malta calce',
            thickness=0.30,
            max_stress=0.95,
            max_displacement=0.25,
            utilization_ratio=0.48,
            verification_status='VERIFICATO'
        ),
        StructuralMember(
            member_id='SLAB_FLOOR_01',
            member_type='slab',
            node_ids=[9, 10, 11, 12],
            material='Calcestruzzo C25/30',
            thickness=0.20,
            max_stress=3.2,
            max_displacement=2.5,
            utilization_ratio=0.72,
            verification_status='VERIFICATO'
        ),
    ]

    # Crea carichi applicati
    loads = [
        StructuralLoad(
            load_id='DEAD_LOAD_G1_WALL_N',
            load_type='dead',
            load_case='G1',
            applied_to='WALL_PERIMETER_NORTH',
            distributed_load=7.2  # kN/m²
        ),
        StructuralLoad(
            load_id='DEAD_LOAD_G2_SLAB',
            load_type='dead',
            load_case='G2',
            applied_to='SLAB_FLOOR_01',
            distributed_load=2.5
        ),
        StructuralLoad(
            load_id='LIVE_LOAD_Q_SLAB',
            load_type='live',
            load_case='Q',
            applied_to='SLAB_FLOOR_01',
            distributed_load=2.0
        ),
        StructuralLoad(
            load_id='SEISMIC_LOAD_EX',
            load_type='seismic',
            load_case='Ex',
            applied_to='1',  # Node
            force=(50.0, 0.0, 0.0)  # kN
        ),
    ]

    print(f"✅ Analysis completed:")
    print(f"   - Nodes: {len(nodes)}")
    print(f"   - Structural members: {len(members)}")
    print(f"   - Loads: {len(loads)}")

    return nodes, members, loads


def main():
    print("🏛️  MURATURA FEM v7.0 - Complete IFC Workflow")
    print("=" * 70)
    print("BIM Integration: Import → Analysis → Export")
    print("=" * 70)

    # Crea directory output
    output_dir = Path(__file__).parent / 'output' / 'ifc_workflow'
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📁 Output directory: {output_dir}")

    # ========================================================================
    # STEP 1: IFC IMPORT (da Revit/ArchiCAD/Tekla)
    # ========================================================================
    print_header("Step 1: IFC Import - Modello Architettonico")

    print("\n📥 Importing architectural model from IFC...")
    print("   Source: Revit 2024 / ArchiCAD 26 / Tekla Structures")
    print("   Format: IFC 2x3 Coordination View 2.0\n")

    # In produzione, si userebbe un file IFC reale:
    # importer = IFCImporter('building_model.ifc', settings)
    # walls = importer.extract_walls()
    # materials = importer.extract_materials()

    # Per questo esempio, usiamo dati mock
    print("⚠️  Using mock data (in production: use real IFC file)")

    mock_walls = [
        {
            'guid': 'WALL_001_GUID',
            'name': 'Parete perimetrale Nord',
            'material': 'Muratura mattoni pieni malta calce',
            'thickness': 0.40,
            'height': 3.0,
            'length': 6.0
        },
        {
            'guid': 'WALL_002_GUID',
            'name': 'Parete interna 001',
            'material': 'Muratura mattoni pieni malta calce',
            'thickness': 0.30,
            'height': 3.0,
            'length': 4.5
        }
    ]

    mock_materials = {
        'Muratura mattoni pieni malta calce': {
            'f_m_k': 2.4,  # MPa
            'E': 1500,  # MPa
            'density': 1800  # kg/m³
        }
    }

    print(f"✅ IFC Import completed:")
    print(f"   - Walls extracted: {len(mock_walls)}")
    print(f"   - Materials: {len(mock_materials)}")

    for wall in mock_walls:
        print(f"   - {wall['name']}: {wall['thickness']*1000:.0f}cm thick, {wall['length']:.1f}m long")

    # ========================================================================
    # STEP 2: STRUCTURAL ANALYSIS
    # ========================================================================
    print_header("Step 2: Structural Analysis - MURATURA FEM")

    print("\n🔬 Performing FEM analysis...")
    print("   Analysis type: Linear static + Seismic (SLV)")
    print("   Code: NTC 2018 - Cap. 7 (Seismic design)")
    print("   Material model: Masonry (nonlinear optional)")

    # Esegui analisi (mock)
    nodes, members, loads = analyze_structure(mock_walls, mock_materials)

    # Mostra risultati
    print("\n📊 Analysis Results:")
    for member in members:
        status_symbol = "✅" if member.verification_status == 'VERIFICATO' else "❌"
        print(f"   {status_symbol} {member.member_id}:")
        print(f"      - Max stress: {member.max_stress:.2f} MPa")
        print(f"      - Max displacement: {member.max_displacement:.2f} mm")
        print(f"      - Utilization: {member.utilization_ratio*100:.1f}%")
        print(f"      - Status: {member.verification_status}")

    # ========================================================================
    # STEP 3: IFC EXPORT (verso Tekla/SAP2000/Results Viewer)
    # ========================================================================
    print_header("Step 3: IFC Export - Structural Analysis Results")

    print("\n📤 Exporting results to IFC Structural Analysis View...")
    print("   Target: Tekla Structural Designer / SAP2000 / Results Viewer")
    print("   Format: IFC 2x3 Structural Analysis View\n")

    # Configura exporter
    export_settings = IFCExportSettings(
        ifc_version='2x3',
        schema='IFC2X3',
        export_loads=True,
        export_results=True,
        export_reinforcement=False,  # TODO: Fase 3 future
        unit_system='METER',
        organization='Studio Tecnico Esempio',
        author='Ing. Mario Rossi',
        project_name='Consolidamento Palazzo Storico - Roma',
        project_description='Analisi strutturale sismica - NTC 2018'
    )

    # Crea exporter
    try:
        exporter = IFCExporter(export_settings)

        # Aggiungi dati
        exporter.add_nodes(nodes)
        exporter.add_members(members)
        exporter.add_loads(loads)

        # Export file
        output_file = output_dir / 'structural_analysis_results.ifc'
        result_file = exporter.export(str(output_file))

        print(f"✅ IFC Export completed: {result_file.name}")
        print(f"   File size: {result_file.stat().st_size / 1024:.1f} KB")

        # Mostra riepilogo
        summary = exporter.get_summary()
        print(f"\n📋 Export Summary:")
        print(f"   - IFC Version: {summary['ifc_version']}")
        print(f"   - Schema: {summary['schema']}")
        print(f"   - Nodes exported: {summary['nodes_count']}")
        print(f"   - Members exported: {summary['members_count']}")
        print(f"   - Loads exported: {summary['loads_count']}")
        print(f"   - Results included: {summary['export_results']}")

    except ImportError as e:
        print(f"❌ IFC export failed: {e}")
        print("   Install ifcopenshell: pip install ifcopenshell")
    except Exception as e:
        print(f"❌ Export error: {e}")

    # ========================================================================
    # STEP 4: WORKFLOW SUMMARY
    # ========================================================================
    print_header("Workflow Summary - Complete BIM Integration")

    print("\n✅ Workflow completato con successo!\n")

    print("📦 Data Flow:")
    print("   1. Revit/ArchiCAD → IFC 2x3 (architectural model)")
    print("   2. IFC Import → MURATURA FEM (geometry + materials)")
    print("   3. FEM Analysis → Results (stress, displacement, verifications)")
    print("   4. IFC Export → IFC Structural Analysis View")
    print("   5. Tekla/SAP2000 → Load results for review/reporting")

    print("\n🎯 Benefits of BIM Integration:")
    print("   ✅ No manual re-modeling (import geometry from architects)")
    print("   ✅ Consistent material properties across disciplines")
    print("   ✅ Automated updates when architectural model changes")
    print("   ✅ Structural results visible in BIM coordination software")
    print("   ✅ Clash detection with other disciplines (MEP, architecture)")
    print("   ✅ Full digital twin of building (as-built + analysis)")

    print("\n📁 Output Files:")
    for f in output_dir.iterdir():
        if f.is_file():
            size_kb = f.stat().st_size / 1024
            print(f"   - {f.name} ({size_kb:.1f} KB)")

    print("\n🎯 FASE 3 - Module 4: IFC Export COMPLETATO!")
    print("   ✅ StructuralNode, StructuralMember, StructuralLoad classes")
    print("   ✅ IFCExporter with full project structure")
    print("   ✅ IfcStructuralAnalysisModel generation")
    print("   ✅ Export loads (point actions, surface actions)")
    print("   ✅ Export results as property sets")
    print("   ✅ IFC 2x3 and IFC 4 support")

    print("\n📚 Next Steps:")
    print("   - Test with real IFC files from Revit/ArchiCAD")
    print("   - Validate exported IFC in IFC viewer (Solibri, BIMvision)")
    print("   - Integration testing: Fase 1 + 2 + 3 together")
    print("   - Performance optimization for large models")
    print()


if __name__ == "__main__":
    if not IFC_AVAILABLE:
        exit(1)
    main()
