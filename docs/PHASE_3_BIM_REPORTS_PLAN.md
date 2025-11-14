# Muratura FEM - Fase 3: BIM Integration & Report Generation
## Piano di Implementazione v7.0

**Status**: 🔄 IN PLANNING
**Data Inizio**: 2025-11-14
**Prerequisiti**:
- ✅ Fase 1 completata (solai, balconi, scale)
- ✅ Fase 2 completata (archi, volte, rinforzi, knowledge levels)

---

## 🎯 Obiettivi Fase 3

### Obiettivo Principale
Implementare **integrazione BIM** e **generazione automatica report** per raggiungere standard commerciale professionale completo, allineandosi con software leader di mercato (3Muri, Aedes, CDSWin).

### Target Market
- 🏢 **Studi professionali** che usano workflow BIM
- 📐 **Progettisti integrati** in team multidisciplinari
- 📄 **Necessità report professionali** per deposito pratiche
- 🔄 **Interoperabilità** con Revit, ArchiCAD, Tekla

### Competitori da Analizzare
- **3Muri Project** - Import/export IFC, report automatici
- **Aedes.PCM** - Generazione relazioni calcolo
- **CDSWin** - Export IFC structural, template personalizzabili
- **MidasGen** - BIM integration avanzata
- **Tekla Structures** - Standard IFC 4 reference

---

## 📚 Background Tecnico

### 1. Building Information Modeling (BIM)

#### 1.1 Standard IFC (Industry Foundation Classes)

**IFC 2x3** (ISO 16739:2013):
- Standard attuale più diffuso
- Supporto completo Revit, ArchiCAD
- Classi rilevanti per muratura:
  - `IfcWall`, `IfcWallStandardCase`
  - `IfcSlab`, `IfcRoof`
  - `IfcColumn`, `IfcBeam`
  - `IfcMaterial`, `IfcMaterialLayerSet`

**IFC 4** (ISO 16739-1:2018):
- Standard più recente
- Migliore supporto analisi strutturale
- `IfcStructuralAnalysisModel`
- `IfcStructuralLoadGroup`
- Classi specifiche per edifici storici

**IFC 4.3** (2024 - in adozione):
- Supporto infrastrutture
- Migliore geolocalizzazione
- Non ancora prioritario per muratura

#### 1.2 Coordinate Reference Systems (CRS)

**Problemi comuni**:
- Revit usa coordinate interne (feet/mm a seconda)
- ArchiCAD usa metri
- IFC supporta unità multiple

**Soluzione**:
- Normalizzazione a metri (SI)
- Trasformazioni matriciali per rotazioni
- `IfcGeometricRepresentationContext`

#### 1.3 IFC per Analisi Strutturale

**IfcStructuralAnalysisModel**:
```
IfcStructuralAnalysisModel
├── IfcStructuralLoadGroup (carichi permanenti, variabili)
├── IfcStructuralResultGroup (risultati analisi)
├── IfcStructuralSurfaceMember (pareti, solai)
├── IfcStructuralCurveMember (travi, cordoli)
└── IfcStructuralPointConnection (nodi)
```

**Material Mapping**:
- `IfcMaterial` → `MasonryMaterial`
- `IfcMaterialLayerSet` → composizione parete multistrato
- Proprietà custom tramite `IfcPropertySet`

---

### 2. Report Generation

#### 2.1 Requisiti Normativi

**NTC 2018 - Relazione di Calcolo**:
Contenuti obbligatori (§10.1):
1. **Descrizione opere**: Geometria, destinazione d'uso
2. **Normativa applicata**: NTC 2018, EC8
3. **Criteri progettazione**: Stati limite, combinazioni carichi
4. **Modellazione strutturale**: Ipotesi, software utilizzato
5. **Materiali**: Proprietà, certificazioni
6. **Azioni**: Carichi permanenti, variabili, sismici
7. **Analisi strutturale**: Metodi, risultati
8. **Verifiche**: Resistenza, deformabilità, dettagli costruttivi
9. **Elaborati grafici**: Piante, sezioni, particolari

#### 2.2 Template Professionali

**Struttura tipo relazione**:
```
1. PREMESSA
2. DESCRIZIONE DELL'OPERA
3. NORMATIVA DI RIFERIMENTO
4. CARATTERIZZAZIONE MATERIALI
   4.1 Muratura
   4.2 Solai
   4.3 Elementi strutturali secondari
5. AZIONI DI PROGETTO
   5.1 Carichi permanenti G1, G2
   5.2 Carichi variabili Q
   5.3 Azione sismica
6. MODELLAZIONE STRUTTURALE
   6.1 Software utilizzato
   6.2 Ipotesi di calcolo
   6.3 Discretizzazione
7. ANALISI STRUTTURALE
   7.1 Analisi carichi verticali
   7.2 Analisi sismica (lineare/non-lineare)
8. VERIFICHE
   8.1 Verifiche murature (SLU, SLE)
   8.2 Verifiche solai
   8.3 Verifiche altri elementi
9. CONCLUSIONI
ALLEGATI: Tabulati, grafici, elaborati
```

#### 2.3 Formati Output

**PDF** (prioritario):
- Standard professionale
- LaTeX + Jinja2 → PDF (via pdflatex)
- Matplotlib/Seaborn per grafici
- Tabulate per tabelle

**Word/DOCX** (opzionale):
- Richiesto da alcuni studi
- python-docx per generazione
- Template .dotx personalizzabili

**Markdown** (interno):
- Formato intermedio
- Facile conversione Pandoc
- Preview in editors

---

## 🗺️ Piano di Implementazione

### Modulo 1: IFC Import - Priority 🔴 ALTA

**File**: `Material/bim/ifc_import.py`

**Obiettivi**:
- Importare modelli IFC da Revit, ArchiCAD
- Estrarre geometria murature, solai
- Convertire materiali IFC → Muratura classes
- Gestire coordinate transformations

**Classi principali**:
```python
from dataclasses import dataclass
from typing import List, Dict, Optional
import ifcopenshell
import ifcopenshell.geom
import numpy as np

@dataclass
class IFCImportSettings:
    """Impostazioni import IFC"""
    ifc_version: str = '2x3'  # '2x3' or '4'
    unit_scale: str = 'meter'  # Normalizza a metri
    extract_materials: bool = True
    extract_loads: bool = True
    simplify_geometry: bool = True
    tolerance: float = 0.001  # m

class IFCImporter:
    """Import modelli IFC per analisi strutturale"""

    def __init__(self, ifc_file_path: str, settings: Optional[IFCImportSettings] = None):
        self.ifc_file = ifcopenshell.open(ifc_file_path)
        self.settings = settings or IFCImportSettings()
        self.walls: List[Dict] = []
        self.slabs: List[Dict] = []
        self.materials: Dict[str, any] = {}

    def extract_walls(self) -> List[Dict]:
        """Estrae pareti murarie da IFC"""
        walls = self.ifc_file.by_type('IfcWall') + self.ifc_file.by_type('IfcWallStandardCase')

        for wall in walls:
            wall_data = {
                'guid': wall.GlobalId,
                'name': wall.Name,
                'geometry': self._extract_geometry(wall),
                'material': self._extract_material(wall),
                'thickness': self._get_wall_thickness(wall),
                'height': self._get_wall_height(wall),
                'length': self._get_wall_length(wall),
            }
            self.walls.append(wall_data)

        return self.walls

    def extract_slabs(self) -> List[Dict]:
        """Estrae solai da IFC"""
        slabs = self.ifc_file.by_type('IfcSlab')

        for slab in slabs:
            slab_data = {
                'guid': slab.GlobalId,
                'name': slab.Name,
                'geometry': self._extract_geometry(slab),
                'material': self._extract_material(slab),
                'thickness': self._get_slab_thickness(slab),
                'area': self._get_slab_area(slab),
                'predefined_type': slab.PredefinedType,  # FLOOR, ROOF, etc.
            }
            self.slabs.append(slab_data)

        return self.slabs

    def extract_materials(self) -> Dict[str, any]:
        """Estrae materiali da IFC e mappa a classi Muratura"""
        ifc_materials = self.ifc_file.by_type('IfcMaterial')

        for mat in ifc_materials:
            # Converti IfcMaterial → MasonryMaterial o ConcreteMaterial
            mat_properties = self._extract_material_properties(mat)

            # Auto-detect tipo materiale da nome/proprietà
            if self._is_masonry_material(mat):
                self.materials[mat.Name] = self._create_masonry_material(mat_properties)
            elif self._is_concrete_material(mat):
                self.materials[mat.Name] = self._create_concrete_material(mat_properties)

        return self.materials

    def extract_structural_analysis_model(self) -> Optional[Dict]:
        """Estrae IfcStructuralAnalysisModel se presente"""
        models = self.ifc_file.by_type('IfcStructuralAnalysisModel')

        if not models:
            return None

        model = models[0]  # Primo modello

        return {
            'name': model.Name,
            'loads': self._extract_loads(model),
            'load_groups': self._extract_load_groups(model),
            'connections': self._extract_connections(model),
        }

    def _extract_geometry(self, element) -> Dict:
        """Estrae geometria 3D elemento"""
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)

        shape = ifcopenshell.geom.create_shape(settings, element)

        # Converti a mesh triangolare
        verts = shape.geometry.verts  # [x1,y1,z1, x2,y2,z2, ...]
        faces = shape.geometry.faces  # [i1,i2,i3, i4,i5,i6, ...]

        vertices = np.array(verts).reshape(-1, 3)
        triangles = np.array(faces).reshape(-1, 3)

        return {
            'vertices': vertices,
            'triangles': triangles,
            'matrix': np.array(shape.transformation.matrix.data).reshape(4, 4),
        }

    def _extract_material(self, element) -> Optional[str]:
        """Estrae nome materiale da elemento"""
        material_select = None

        # Diverse modalità IFC per assegnare materiali
        if hasattr(element, 'HasAssociations'):
            for association in element.HasAssociations:
                if association.is_a('IfcRelAssociatesMaterial'):
                    material_select = association.RelatingMaterial
                    break

        if material_select:
            if material_select.is_a('IfcMaterial'):
                return material_select.Name
            elif material_select.is_a('IfcMaterialLayerSetUsage'):
                # Multi-layer wall: usa layer principale
                layer_set = material_select.ForLayerSet
                if layer_set.MaterialLayers:
                    return layer_set.MaterialLayers[0].Material.Name

        return None

    def _get_wall_thickness(self, wall) -> float:
        """Calcola spessore parete da geometria o material layers"""
        # Try from MaterialLayerSet first
        if hasattr(wall, 'HasAssociations'):
            for assoc in wall.HasAssociations:
                if assoc.is_a('IfcRelAssociatesMaterial'):
                    mat = assoc.RelatingMaterial
                    if mat.is_a('IfcMaterialLayerSetUsage'):
                        total_thickness = sum(
                            layer.LayerThickness
                            for layer in mat.ForLayerSet.MaterialLayers
                        )
                        return self._convert_to_meters(total_thickness)

        # Fallback: calcola da bounding box geometria
        geometry = self._extract_geometry(wall)
        vertices = geometry['vertices']

        # Stima spessore da dimensione minima bounding box
        bbox_dims = vertices.max(axis=0) - vertices.min(axis=0)
        thickness = np.min(bbox_dims)

        return thickness

    def _convert_to_meters(self, value: float) -> float:
        """Converte valore a metri basandosi su unità progetto IFC"""
        # IFC può usare millimeters, feet, inches...
        units = self.ifc_file.by_type('IfcUnitAssignment')[0]

        for unit in units.Units:
            if hasattr(unit, 'UnitType') and unit.UnitType == 'LENGTHUNIT':
                if hasattr(unit, 'Name'):
                    if unit.Name == 'METRE':
                        return value
                    elif unit.Name == 'MILLIMETRE':
                        return value / 1000.0
                    elif unit.Name == 'FOOT':
                        return value * 0.3048

        # Default: assume metri
        return value

    def convert_to_muratura_model(self):
        """Converte IFC → Muratura FEM model completo"""
        # TODO: Implementare conversione completa
        pass
```

**Dependencies**:
- `ifcopenshell` - Parsing IFC files
- `numpy` - Geometria vettoriale
- `scipy` (opzionale) - Semplificazione mesh

**Test cases** (15+):
1. Import file IFC 2x3 da Revit
2. Import file IFC 4 da ArchiCAD
3. Estrazione pareti murarie
4. Estrazione solai (floor, roof)
5. Conversione unità (mm → m, ft → m)
6. Estrazione materiali multistrato
7. Material mapping → MasonryMaterial
8. Gestione coordinate transformations
9. Semplificazione geometria complessa
10. Import modello con IfcStructuralAnalysisModel

**Effort stimato**: 6 settimane

---

### Modulo 2: IFC Export - Priority 🟡 MEDIA

**File**: `Material/bim/ifc_export.py`

**Obiettivi**:
- Esportare risultati analisi → IFC structural
- Permettere round-trip BIM workflow
- Export per software visualizzazione (Solibri, BIMcollab)

**Classi principali**:
```python
class IFCExporter:
    """Export modello analizzato verso IFC structural"""

    def __init__(self, muratura_model, output_path: str):
        self.model = muratura_model
        self.output_path = output_path
        self.ifc_file = self._create_ifc_file()

    def export_structural_model(self):
        """Esporta modello strutturale con risultati"""
        # Crea IfcStructuralAnalysisModel
        analysis_model = self._create_analysis_model()

        # Aggiungi membri strutturali (pareti, solai)
        for wall in self.model.walls:
            self._add_structural_surface_member(wall, analysis_model)

        # Aggiungi carichi
        self._add_load_groups(analysis_model)

        # Aggiungi risultati (stress, displacement)
        self._add_results(analysis_model)

        # Scrivi file IFC
        self.ifc_file.write(self.output_path)

    def _create_analysis_model(self):
        """Crea IfcStructuralAnalysisModel container"""
        pass

    def _add_structural_surface_member(self, wall, analysis_model):
        """Aggiunge parete come IfcStructuralSurfaceMember"""
        pass
```

**Effort stimato**: 4 settimane

---

### Modulo 3: Report Generation - Priority 🔴 ALTA

**File**: `Material/reports/report_generator.py`

**Obiettivi**:
- Generazione automatica relazioni di calcolo
- Template conformi NTC 2018
- Export PDF professionale
- Grafici integrati

**Classi principali**:
```python
from dataclasses import dataclass
from typing import List, Dict, Optional
from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import subprocess
from pathlib import Path

@dataclass
class ReportMetadata:
    """Metadata relazione di calcolo"""
    project_name: str
    project_location: str
    client_name: str
    designer_name: str
    designer_order: str  # Ordine professionale
    report_date: str
    revision: str = "0"

@dataclass
class ReportSettings:
    """Impostazioni generazione report"""
    template_name: str = 'ntc2018_standard'
    output_format: str = 'pdf'  # 'pdf', 'docx', 'md'
    include_graphs: bool = True
    include_tables: bool = True
    language: str = 'it'
    logo_path: Optional[str] = None

class ReportGenerator:
    """Generatore automatico relazioni di calcolo"""

    def __init__(self,
                 model,
                 metadata: ReportMetadata,
                 settings: Optional[ReportSettings] = None):
        self.model = model
        self.metadata = metadata
        self.settings = settings or ReportSettings()

        # Setup Jinja2 environment
        template_dir = Path(__file__).parent / 'templates'
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

        self.figures: List[plt.Figure] = []

    def generate_report(self, output_path: str) -> str:
        """Genera relazione completa"""

        # 1. Prepara dati per template
        context = self._prepare_context()

        # 2. Genera grafici
        self._generate_figures()

        # 3. Rendi template
        if self.settings.output_format == 'pdf':
            return self._generate_pdf(context, output_path)
        elif self.settings.output_format == 'docx':
            return self._generate_docx(context, output_path)
        else:  # markdown
            return self._generate_markdown(context, output_path)

    def _prepare_context(self) -> Dict:
        """Prepara contesto dati per template Jinja2"""
        return {
            'metadata': self.metadata,

            # Sezione 2: Descrizione opera
            'building_description': self._get_building_description(),

            # Sezione 3: Normativa
            'codes': self._get_applicable_codes(),

            # Sezione 4: Materiali
            'materials': self._get_materials_summary(),

            # Sezione 5: Azioni
            'loads': self._get_loads_summary(),
            'seismic_action': self._get_seismic_parameters(),

            # Sezione 6: Modellazione
            'modeling_assumptions': self._get_modeling_info(),

            # Sezione 7: Analisi
            'analysis_results': self._get_analysis_results(),

            # Sezione 8: Verifiche
            'verifications': self._get_verifications_summary(),

            # Figure e tabelle
            'figures': self._get_figure_references(),
            'tables': self._get_tables(),
        }

    def _generate_figures(self):
        """Genera tutti i grafici per il report"""

        # Figura 1: Pianta strutturale
        fig1 = self._plot_structural_plan()
        self.figures.append(fig1)

        # Figura 2: Diagramma carichi
        fig2 = self._plot_load_diagram()
        self.figures.append(fig2)

        # Figura 3: Deformata struttura
        if hasattr(self.model, 'displacement_results'):
            fig3 = self._plot_displacement()
            self.figures.append(fig3)

        # Figura 4: Stress distribution
        if hasattr(self.model, 'stress_results'):
            fig4 = self._plot_stress()
            self.figures.append(fig4)

    def _generate_pdf(self, context: Dict, output_path: str) -> str:
        """Genera PDF via LaTeX"""

        # 1. Rendi template LaTeX
        template = self.env.get_template(f'{self.settings.template_name}.tex')
        latex_content = template.render(**context)

        # 2. Scrivi file .tex temporaneo
        tex_path = Path(output_path).with_suffix('.tex')
        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(latex_content)

        # 3. Salva figure come PDF
        figures_dir = tex_path.parent / 'figures'
        figures_dir.mkdir(exist_ok=True)

        for i, fig in enumerate(self.figures):
            fig_path = figures_dir / f'figure_{i+1}.pdf'
            fig.savefig(fig_path, format='pdf', bbox_inches='tight')

        # 4. Compila LaTeX → PDF (2 passaggi per references)
        try:
            subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', str(tex_path)],
                cwd=tex_path.parent,
                check=True,
                capture_output=True
            )
            # Secondo passaggio per TOC e references
            subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', str(tex_path)],
                cwd=tex_path.parent,
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"LaTeX compilation failed: {e.stderr.decode()}")

        # 5. Cleanup file ausiliari
        for ext in ['.aux', '.log', '.out', '.toc']:
            aux_file = tex_path.with_suffix(ext)
            if aux_file.exists():
                aux_file.unlink()

        pdf_path = tex_path.with_suffix('.pdf')
        return str(pdf_path)

    def _generate_docx(self, context: Dict, output_path: str) -> str:
        """Genera Word DOCX"""
        from docx import Document
        from docx.shared import Inches, Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()

        # Titolo
        title = doc.add_heading(f'RELAZIONE DI CALCOLO STRUTTURALE', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Metadata
        doc.add_heading('Dati Generali', level=1)
        table = doc.add_table(rows=5, cols=2)
        table.style = 'Light Grid Accent 1'

        data = [
            ('Progetto', self.metadata.project_name),
            ('Committente', self.metadata.client_name),
            ('Progettista', self.metadata.designer_name),
            ('Data', self.metadata.report_date),
            ('Revisione', self.metadata.revision),
        ]

        for i, (label, value) in enumerate(data):
            table.rows[i].cells[0].text = label
            table.rows[i].cells[1].text = str(value)

        # Sezioni
        for section_title, section_data in [
            ('NORMATIVA DI RIFERIMENTO', context['codes']),
            ('MATERIALI', context['materials']),
            ('AZIONI DI PROGETTO', context['loads']),
            ('VERIFICHE', context['verifications']),
        ]:
            doc.add_heading(section_title, level=1)
            doc.add_paragraph(str(section_data))

        # Aggiungi figure
        if self.settings.include_graphs:
            doc.add_heading('ELABORATI GRAFICI', level=1)
            for i, fig in enumerate(self.figures):
                # Salva figura come PNG temporanea
                temp_img = Path(output_path).parent / f'temp_fig_{i}.png'
                fig.savefig(temp_img, dpi=300, bbox_inches='tight')

                doc.add_picture(str(temp_img), width=Inches(6))
                doc.add_paragraph(f'Figura {i+1}', style='Caption')

                temp_img.unlink()  # Cleanup

        # Salva DOCX
        doc.save(output_path)
        return output_path

    def _get_building_description(self) -> str:
        """Genera descrizione opera"""
        return f"""
L'edificio oggetto di intervento è situato in {self.metadata.project_location}.
La struttura è realizzata in muratura portante...
        """

    def _get_applicable_codes(self) -> List[str]:
        """Normativa applicata"""
        return [
            'NTC 2018 - D.M. 17 gennaio 2018',
            'Circolare NTC 2019 - Circolare 21 gennaio 2019 n. 7',
            'Eurocodice 8 - EN 1998-1',
            'CNR-DT 200 R1/2013 (Rinforzi FRP)',
            'CNR-DT 215/2018 (Rinforzi FRCM)',
        ]

    def _get_materials_summary(self) -> List[Dict]:
        """Riassunto materiali utilizzati"""
        materials = []

        # Estrai materiali dal modello
        for element in self.model.elements:
            if hasattr(element, 'material'):
                mat = element.material
                materials.append({
                    'type': mat.__class__.__name__,
                    'f_k': getattr(mat, 'f_m_k', None),
                    'description': str(mat),
                })

        return materials

    def _get_loads_summary(self) -> Dict:
        """Riassunto carichi"""
        return {
            'permanent_G1': 'Peso proprio struttura',
            'permanent_G2': 'Carichi permanenti portati',
            'variable_Q': 'Sovraccarichi variabili',
            'seismic': 'Azione sismica',
        }

    def _get_verifications_summary(self) -> List[Dict]:
        """Riassunto verifiche eseguite"""
        verifications = []

        # Collect all verifications from model
        if hasattr(self.model, 'verification_results'):
            for result in self.model.verification_results:
                verifications.append({
                    'element': result.element_id,
                    'verification_type': result.type,
                    'demand': result.demand,
                    'capacity': result.capacity,
                    'ratio': result.demand / result.capacity,
                    'status': 'VERIFICATO' if result.demand <= result.capacity else 'NON VERIFICATO',
                })

        return verifications

    def _plot_structural_plan(self) -> plt.Figure:
        """Plotta pianta strutturale"""
        fig, ax = plt.subplots(figsize=(10, 8))

        # Plot walls
        for wall in self.model.walls:
            # Simplified 2D representation
            ax.plot([wall.x1, wall.x2], [wall.y1, wall.y2],
                   'k-', linewidth=wall.thickness * 100)

        ax.set_xlabel('X [m]')
        ax.set_ylabel('Y [m]')
        ax.set_title('Pianta Strutturale')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')

        return fig
```

**Templates LaTeX**:
- `templates/ntc2018_standard.tex` - Template base NTC 2018
- `templates/ntc2018_historic.tex` - Template edifici storici
- `templates/header.tex` - Intestazione comune
- `templates/sections/` - Sezioni riutilizzabili

**Effort stimato**: 4 settimane

---

### Modulo 4: Revit Plugin (Basic) - Priority 🟢 BASSA

**File**: `plugins/revit/MuraturaFEM.py` (IronPython)

**Obiettivi**:
- Plugin base per Revit
- Export modello Revit → Muratura FEM
- Import risultati analisi → Revit (visualizzazione)

**Note**:
- Revit API usa IronPython (Python 2.7 + .NET)
- Necessita pyRevit framework
- Complessità maggiore per compatibilità

**Effort stimato**: 3 settimane (opzionale, può essere posposto)

---

## 📊 Timeline e Milestones

### Sprint 1 (Settimane 1-3): IFC Import Foundation
**Obiettivi**:
- Setup ifcopenshell
- Import IFC 2x3 base (walls, slabs)
- Conversione unità e coordinate
- Estrazione materiali base

**Deliverable**: Prototipo import IFC funzionante

### Sprint 2 (Settimane 4-6): IFC Import Advanced
**Obiettivi**:
- Import IFC 4
- IfcStructuralAnalysisModel parsing
- Material mapping completo
- Conversione → Muratura model

**Deliverable**: Modulo IFC import production-ready

### Sprint 3 (Settimane 7-8): Report Generation - Template
**Obiettivi**:
- Setup Jinja2 + LaTeX
- Template NTC 2018 base
- Sezioni fondamentali (1-5)
- Test generazione PDF

**Deliverable**: Template report funzionante

### Sprint 4 (Settimane 9-10): Report Generation - Complete
**Obiettivi**:
- Grafici matplotlib integrati
- Sezioni analisi e verifiche (6-8)
- Export DOCX
- Personalizzazione template

**Deliverable**: Sistema report completo

### Sprint 5 (Settimane 11-12): IFC Export + Integration
**Obiettivi**:
- Export IFC structural
- Round-trip testing
- Integrazione con Fase 1/2 modules
- Documentazione completa

**Deliverable**: Fase 3 completata, release v7.0

**Timeline totale**: 12 settimane (~3 mesi)

---

## 📖 Bibliografia e Riferimenti

### Standard BIM

1. **ISO 16739-1:2018**
   "Industry Foundation Classes (IFC) for data sharing in the construction and facility management industries"
   → Standard IFC 4

2. **buildingSMART International**
   https://www.buildingsmart.org/
   → Documentazione IFC, esempi, validator

3. **IfcOpenShell Documentation**
   http://ifcopenshell.org/
   → API reference, esempi Python

### LaTeX e Report Generation

4. **LaTeX Wikibook**
   https://en.wikibooks.org/wiki/LaTeX
   → Riferimento completo LaTeX

5. **Jinja2 Documentation**
   https://jinja.palletsprojects.com/
   → Template engine

### Software di Riferimento

6. **Solibri Model Checker**
   → IFC validation reference

7. **BIMcollab Zoom**
   → IFC viewer free

---

## 🎯 Success Criteria

### Criteri Tecnici
- [ ] Import IFC 2x3/4 con accuratezza ≥95%
- [ ] Report PDF conforme NTC 2018
- [ ] Generazione report < 30 secondi
- [ ] Export IFC structural valido (Solibri pass)

### Criteri Business
- [ ] Compatibilità Revit 2020-2024
- [ ] Compatibilità ArchiCAD 24-27
- [ ] Template report personalizzabili
- [ ] Esempi pratici (≥3) workflow BIM completo

### Criteri Qualità
- [ ] Test coverage ≥70%
- [ ] Documentazione API completa
- [ ] User guide per workflow BIM
- [ ] Video tutorial (opzionale)

---

## 💡 Note Implementative

### Sfide Tecniche Previste

1. **IFC Geometry Complexity**
   - Geometrie complesse da Revit (sweep, extrusion, CSG)
   - Semplificazione necessaria per FEM
   - Tolleranze geometriche

2. **Material Mapping**
   - Naming inconsistente tra software
   - Proprietà custom IfcPropertySet
   - Database materiali di riferimento

3. **LaTeX Installation**
   - Richiede TeXLive/MiKTeX installato
   - Dipendenza pesante (~2GB)
   - Alternativa: Pandoc per Markdown → PDF

4. **Coordinate Systems**
   - Revit coordinate interne vs. project base point
   - ArchiCAD survey point
   - Trasformazioni matriciali 4x4

### Decisioni Architetturali

- **IfcOpenShell vs. alternative**: IfcOpenShell è standard de facto, mature
- **LaTeX vs. Reportlab**: LaTeX per qualità tipografica professionale
- **Template approach**: Jinja2 per massima flessibilità
- **Plugin Revit**: Opzionale, priorità su import/export standalone

---

## 📅 Next Steps Immediati

1. 🔄 Setup ambiente sviluppo (ifcopenshell, LaTeX)
2. 🔄 Ricerca esempi IFC test files
3. 🔄 Prototipo import base IFC
4. 🔄 Design template LaTeX NTC 2018
5. 🔄 Test integrazione con moduli Fase 1/2

---

**Documento creato**: 2025-11-14
**Ultima modifica**: 2025-11-14
**Autore**: Claude (Anthropic)
**Revisione**: v1.0
