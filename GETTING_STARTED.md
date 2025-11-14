# MURATURA FEM v7.0 - Getting Started Guide

Benvenuto in MURATURA FEM v7.0! Questa guida ti aiuterà a iniziare rapidamente con il sistema.

---

## 📦 Installazione

### Requisiti
- Python 3.8 o superiore
- pip (Python package manager)

### Installazione Base
```bash
# Clone repository
git clone https://github.com/mikibart/Muratura.git
cd Muratura

# Install core dependencies
pip install -r requirements.txt

# Verifica installazione
python -c "from Material import MasonryFEMEngine; print('✓ Installazione OK')"
```

### Installazione con Setup.py
```bash
# Base install (solo dipendenze core)
pip install .

# Con supporto BIM/IFC (Fase 3 - IFC Import/Export)
pip install .[bim]

# Con supporto Reports (Fase 3 - PDF/DOCX generation)
pip install .[reports]

# Development mode (con testing tools)
pip install .[dev]

# Tutto incluso
pip install .[all]
```

### Installazione Opzionale: LaTeX per PDF Reports
```bash
# Ubuntu/Debian
sudo apt-get install texlive-latex-base texlive-latex-extra

# macOS (via Homebrew)
brew install --cask mactex

# Windows
# Download MiKTeX: https://miktex.org/download
```

---

## 🚀 Quick Start

### Esempio 1: Analisi Semplice Parete in Muratura
```python
from Material import MasonryFEMEngine

# Crea modello
model = MasonryFEMEngine()

# Definisci materiale (muratura in mattoni)
model.set_material(
    f_m_k=2.4,  # MPa - Resistenza caratteristica
    E=1500,     # MPa - Modulo elastico
    w=18.0      # kN/m³ - Peso specifico
)

# Definisci geometria parete
model.add_wall(
    length=5.0,    # m
    height=3.0,    # m
    thickness=0.3  # m
)

# Applica carichi
model.add_vertical_load(100)  # kN

# Esegui analisi
model.run_analysis()

# Verifica SLU
results = model.verify_ntc2018()
print(f"Verifica: {results['status']}")
print(f"Rapporto domanda/capacità: {results['ratio']:.2f}")
```

### Esempio 2: Solaio Latero-cemento (Fase 1)
```python
from Material.floors import FloorSystem

# Crea solaio
floor = FloorSystem(
    floor_type='latero_cemento',
    span=5.0,              # m
    slab_thickness=0.04,   # m
    block_height=0.20,     # m
    joist_spacing=0.50     # m
)

# Calcola resistenza
moment_capacity = floor.calculate_moment_resistance()
shear_capacity = floor.calculate_shear_resistance()

# Verifica freccia
deflection_ok = floor.verify_deflection(
    live_load=2.0,  # kN/m²
    dead_load=5.0   # kN/m²
)

print(f"M_Rd = {moment_capacity:.2f} kNm")
print(f"V_Rd = {shear_capacity:.2f} kN")
print(f"Freccia OK: {deflection_ok}")
```

### Esempio 3: Balcone Acciaio HEA (Fase 1)
```python
from Material.balconies import Balcony

# Crea balcone
balcony = Balcony(
    balcony_type='steel',
    cantilever=1.20,  # m
    width=3.0,        # m
    profile='HEA160'
)

# ⚠️ VERIFICA CRITICA: Ancoraggio a muratura
anchorage = balcony.verify_anchorage_to_masonry(
    masonry_strength=2.0,  # MPa
    wall_thickness=0.40    # m
)

print(f"Tensione contatto: {anchorage['contact_stress']:.3f} MPa")
print(f"Safety Factor: {anchorage['safety_factor']:.2f}")
print(f"Status: {anchorage['status']}")
```

### Esempio 4: Analisi Arco Storico (Fase 2)
```python
from Material.historic.arches import Arch

# Crea arco semicircolare
arch = Arch(
    arch_type='semicircular',
    span=4.0,      # m
    rise=2.0,      # m
    thickness=0.40 # m
)

# Analisi Heyman
thrust_line = arch.calculate_thrust_line()
min_thickness = arch.find_minimum_thickness()
safety_factor = arch.calculate_safety_factor()

print(f"Spessore minimo: {min_thickness:.3f} m")
print(f"FS geometrico: {safety_factor:.2f}")
print(f"Status: {'VERIFICATO' if safety_factor > 1.5 else 'NON VERIFICATO'}")
```

### Esempio 5: Rinforzi FRP (Fase 2)
```python
from Material.historic.strengthening import FRPReinforcement

# Progetta rinforzo CFRP
frp = FRPReinforcement(
    frp_type='CFRP',
    element_type='wall',
    width=1.0,     # m
    height=2.0     # m
)

# Calcola contributo resistenza
delta_R = frp.calculate_resistance_contribution(
    substrate_strength=1.5,  # MPa (muratura)
    required_increase=0.5    # MPa
)

# Verifica debonding
debonding_ok = frp.verify_debonding()

print(f"Incremento resistenza: {delta_R:.2f} MPa")
print(f"Debonding OK: {debonding_ok}")
```

### Esempio 6: IFC Import da Revit (Fase 3)
```python
from Material.bim import IFCImporter

# Import modello BIM
importer = IFCImporter('building_model.ifc')

# Estrai pareti
walls = importer.extract_walls()
print(f"Pareti estratte: {len(walls)}")

# Estrai materiali
materials = importer.extract_materials()
for name, props in materials.items():
    print(f"- {name}: f_mk={props['f_m_k']} MPa")
```

### Esempio 7: Genera Relazione PDF (Fase 3)
```python
from Material.reports import ReportGenerator, ReportMetadata, ReportSettings

# Metadata progetto
metadata = ReportMetadata(
    project_name="Consolidamento Palazzo Storico",
    project_location="Roma (RM)",
    client_name="Soprintendenza",
    designer_name="Ing. Mario Rossi",
    designer_order="Ordine Ingegneri Roma n. A12345"
)

# Settings report
settings = ReportSettings(
    template_name='ntc2018_historic',  # Template edifici storici
    output_format='pdf',               # PDF via LaTeX
    include_graphs=True,
    include_toc=True
)

# Genera report
generator = ReportGenerator(model, metadata, settings)
generator.generate_report('relazione_calcolo.pdf')

print("✅ Report PDF generato!")
```

---

## 📁 Struttura Progetto

```
Muratura/
├── Material/                    # Core package
│   ├── constitutive.py         # Modelli costitutivi
│   ├── geometry.py             # Geometria elementi
│   ├── loads.py                # Carichi e combinazioni
│   ├── analysis.py             # Metodi analisi (FEM, Pushover, etc.)
│   │
│   ├── floors/                 # FASE 1: Solai
│   │   └── floor_system.py
│   ├── balconies/              # FASE 1: Balconi
│   │   └── balcony_system.py
│   ├── stairs/                 # FASE 1: Scale
│   │   └── stair_system.py
│   │
│   ├── historic/               # FASE 2: Edifici Storici
│   │   ├── arches.py          # Archi (Heyman)
│   │   ├── vaults.py          # Volte (Heyman 3D)
│   │   ├── strengthening.py   # Rinforzi FRP/FRCM
│   │   └── knowledge_levels.py # LC/FC (NTC §C8.5.4)
│   │
│   ├── bim/                    # FASE 3: BIM Integration
│   │   ├── ifc_import.py      # Import IFC
│   │   └── ifc_export.py      # Export IFC
│   │
│   └── reports/                # FASE 3: Report Generation
│       ├── report_generator.py
│       └── templates/
│           ├── ntc2018_standard.tex
│           └── ntc2018_historic.tex
│
├── tests/                      # Test suite (223 tests)
├── examples/                   # 15 esempi completi
├── docs/                       # Documentazione
├── requirements.txt
├── setup.py
├── CHANGELOG.md
└── README.md
```

---

## 📚 Esempi Disponibili

### Esempi Base (Core)
- `01_simple_wall_analysis.py` - Analisi parete base
- `02_masonry_panel.py` - Pannello con aperture
- `03_seismic_analysis.py` - Analisi sismica

### Fase 1: Elementi Strutturali
- `04_floor_analysis.py` - Progetto solaio completo
- `05_balcony_design.py` - Dimensionamento balcone
- `06_stair_verification.py` - Verifica scala

### Fase 2: Edifici Storici
- `07_arch_heyman_analysis.py` - Analisi arco (Heyman)
- `08_vault_stability.py` - Stabilità volta
- `09_frp_strengthening.py` - Progetto rinforzi FRP
- `10_knowledge_level_assessment.py` - Determinazione LC/FC

### Fase 3: BIM & Reports
- `11_ifc_import_bim.py` - Import da Revit/ArchiCAD
- `12_report_generation.py` - Generazione relazioni
- `13_custom_templates.py` - Template personalizzati
- `14_ifc_workflow_complete.py` - Workflow IFC completo
- `15_complete_workflow_integration.py` - **Integrazione COMPLETA Fase 1+2+3** ⭐

### Eseguire Esempi
```bash
# Esegui esempio
python examples/15_complete_workflow_integration.py

# Output verrà salvato in examples/output/
```

---

## 🧪 Testing

### Eseguire Test
```bash
# Tutti i test
pytest tests/ -v

# Test specifico modulo
pytest tests/test_ifc_import.py -v

# Con coverage
pytest tests/ -v --cov=Material --cov-report=html

# Solo Fase 3
pytest tests/test_ifc_import.py tests/test_report_generator.py tests/test_ifc_export.py -v
```

### Test Coverage
- **Total**: 223 tests, 219 passing (98.2%)
- **Fase 1**: 84/84 passing (100%)
- **Fase 2**: 84/84 passing (100%)
- **Fase 3**: 51/55 passing (92.7%, 4 skipped)

---

## 📖 Documentazione

### Guide Principali
1. **README.md** - Overview e features
2. **GETTING_STARTED.md** - Questa guida
3. **docs/PROJECT_COMPLETE_SUMMARY.md** - Documentazione completa (~850 righe)
4. **CHANGELOG.md** - Storia modifiche

### Piani di Fase
- `docs/PHASE_1_PLAN.md` - Solai, Balconi, Scale
- `docs/PHASE_2_HISTORIC_PLAN.md` - Edifici Storici
- `docs/PHASE_3_BIM_REPORTS_PLAN.md` - BIM & Reports

### API Documentation
La documentazione inline è disponibile tramite docstring:
```python
from Material.floors import FloorSystem
help(FloorSystem.calculate_moment_resistance)
```

---

## 🎯 Workflow Consigliati

### Workflow 1: Edificio Moderno
```
1. Import geometria da Revit (IFC)
2. Progetta solai (Fase 1)
3. Progetta balconi (Fase 1)
4. Progetta scale (Fase 1)
5. Esegui analisi FEM
6. Genera relazione PDF (Fase 3)
7. Export risultati IFC (Fase 3)
```

### Workflow 2: Edificio Storico
```
1. Determina LC/FC (Fase 2)
2. Analizza archi esistenti (Fase 2)
3. Analizza volte esistenti (Fase 2)
4. Progetta rinforzi FRP/FRCM (Fase 2)
5. Esegui analisi con materiali ridotti per FC
6. Genera relazione PDF con template historic (Fase 3)
```

### Workflow 3: BIM Round-Trip
```
1. IFC Import da Revit (Fase 3)
2. Analisi FEM completa
3. Report PDF/DOCX (Fase 3)
4. IFC Export risultati (Fase 3)
5. Import in Tekla/SAP2000 per review
```

---

## ⚠️ Note Importanti

### Verifica Critica: Ancoraggio Balconi
```python
# ⚠️ SEMPRE verificare ancoraggio balconi a muratura
balcony.verify_anchorage_to_masonry(...)

# Tensione ammissibile muratura: 0.3-0.6 MPa (NTC Tabella C8.5.I)
# Safety Factor minimo: 2.0
```

### LaTeX per PDF
I report PDF richiedono LaTeX installato:
```bash
# Verifica installazione
pdflatex --version

# Se non installato, usa DOCX o Markdown
settings = ReportSettings(output_format='docx')
```

### IFC Files
Gli esempi IFC Import richiedono file .ifc reali da Revit/ArchiCAD.
Per test, vedere `tests/test_ifc_import.py` per mock.

---

## 🆘 Risoluzione Problemi

### ImportError: ifcopenshell
```bash
pip install ifcopenshell
# Se fallisce, potrebbe richiedere compilazione. Vedere docs IFC.
```

### LaTeX non trovato
```bash
# Ubuntu
sudo apt-get install texlive-latex-base texlive-latex-extra

# Oppure usa DOCX/Markdown
```

### Test failing
```bash
# Reinstalla dipendenze
pip install -r requirements.txt --force-reinstall

# Pulisci cache
find . -type d -name __pycache__ -exec rm -r {} +
pytest --cache-clear
```

---

## 📞 Supporto

- **Documentazione**: `docs/` folder
- **Esempi**: `examples/` folder (15 esempi)
- **Test**: `tests/` folder (223 test)
- **Issues**: GitHub Issues

---

## 🎉 Pronto a Iniziare!

```bash
# 1. Clone e install
git clone https://github.com/mikibart/Muratura.git
cd Muratura
pip install .[all]

# 2. Esegui esempio completo
python examples/15_complete_workflow_integration.py

# 3. Esplora la documentazione
cat docs/PROJECT_COMPLETE_SUMMARY.md
```

**MURATURA FEM v7.0 - Sistema completo per analisi strutture in muratura!** 🏛️

---

*Versione: 7.0.0-alpha | Data: Gennaio 2025 | License: MIT*
