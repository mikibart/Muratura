# Muratura FEM - Sistema di Calcolo Strutturale

![Version](https://img.shields.io/badge/version-7.0--alpha-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Phase1](https://img.shields.io/badge/Fase%201-Completata-success.svg)
![Phase2](https://img.shields.io/badge/Fase%202-Completata-success.svg)
![Phase3](https://img.shields.io/badge/Fase%203-Completata-success.svg)

Sistema completo di analisi agli elementi finiti (FEM) per strutture in muratura conforme alle **Norme Tecniche per le Costruzioni NTC 2018** e **Eurocodice 8**.

🎉 **NOVITÀ v7.0-alpha**: BIM Integration + Report Generator - Import IFC e generazione automatica relazioni!

## 🎯 Caratteristiche Principali

### Analisi Murature
- ✅ **7 Metodi di Analisi**: FEM, POR, SAM, Frame Equivalente, Analisi Limite, Fiber Model, Micro-modellazione
- ✅ **Modelli Costitutivi Avanzati**: Lineare elastico, Bilineare, Parabolico, Mander, Kent-Park, Popovics
- ✅ **Analisi Dinamiche**: Modale, Pushover, Time-History con Newmark-β
- ✅ **Geometrie Complete**: Maschi murari, fasce di piano, pareti complete con aperture
- ✅ **24 Cinematismi**: Tutti i meccanismi di collasso secondo EC8/NTC2018

### 🆕 Elementi Strutturali Integrati (Fase 1 - v6.2)
- ✅ **Solai**: Latero-cemento, legno, acciaio, prefabbricati - Database materiali commerciali italiani
- ✅ **Balconi**: C.a. a sbalzo, acciaio (HEA/IPE/UPN) - ⚠️ Verifica CRITICA ancoraggio muratura
- ✅ **Scale**: Soletta rampante, sbalzo, ginocchio - Validazione geometrica DM 236/89

### 🏛️ Edifici Storici in Muratura (Fase 2 - v6.4.3) ✅ COMPLETATA!
- ✅ **Archi**: Analisi limite metodo Heyman - Thrust line, safety factor geometrico, 6 tipologie
- ✅ **Volte**: Barrel, cross, dome, cloister, sail - Heyman esteso a 3D
- ✅ **Rinforzi FRP/FRCM**: CFRP, GFRP, AFRP, C-FRCM - CNR-DT 200/215 compliant
- ✅ **Knowledge Levels**: LC1/LC2/LC3 con fattori confidenza FC secondo NTC 2018 §8.5.4

### 🔄 BIM & Report Generation (Fase 3 - v7.0) ✅ COMPLETATA!
- ✅ **IFC Import**: Import modelli BIM da Revit, ArchiCAD, Tekla (IFC 2x3/4)
  - Estrazione geometria pareti, solai, materiali
  - Material mapping automatico (masonry, concrete, steel, wood)
  - Unit conversion (mm, ft → m)
  - 13 test passing
- ✅ **Report Generator**: Generazione automatica relazioni di calcolo NTC 2018
  - Export PDF (via LaTeX), Word DOCX, Markdown
  - Sezioni conformi §10.1: premessa, normativa, materiali, azioni, verifiche
  - Grafici matplotlib integrati
  - Template Jinja2 personalizzabili
  - 17 test passing
- ✅ **IFC Export**: Export risultati → IFC Structural Analysis View
  - IfcStructuralAnalysisModel generation
  - Nodi, membri, carichi, risultati
  - IFC 2x3 e IFC 4 support
  - 21 test passing
- ✅ **Custom Templates**: LaTeX templates personalizzabili
  - ntc2018_standard.tex (edifici moderni)
  - ntc2018_historic.tex (patrimonio culturale)
  - Frontespizio, TOC, header/footer custom

### Conformità Normativa
- ✅ **NTC 2018** completa + Circolare 2019 (incl. Cap. 8 Edifici Esistenti)
- ✅ **Eurocodice 8** (EC8)
- ✅ **DM 236/89** (geometria scale)
- ✅ **CNR-DT 200 R1/2013** (rinforzi FRP) ✅
- ✅ **CNR-DT 215/2018** (rinforzi FRCM) ✅
- ✅ **Linee Guida Beni Culturali 2011**

## 📋 Requisiti

### Core Dependencies
- Python 3.8 o superiore
- NumPy >= 1.24.0
- SciPy >= 1.10.0
- Matplotlib >= 3.7.0

### Fase 3 Dependencies (BIM & Reports)
- ifcopenshell >= 0.7.0 (BIM/IFC import)
- jinja2 >= 3.1.0 (Report templates)
- python-docx >= 1.1.0 (Word generation)
- LaTeX (pdflatex) - Optional, for PDF reports

## 🚀 Installazione

### Installazione Standard

```bash
# Clona il repository
git clone https://github.com/mikibart/Muratura.git
cd Muratura

# Installa dipendenze
pip install -r requirements.txt

# Verifica installazione
python -c "from Material import MasonryFEMEngine; print('✓ Installazione OK')"
```

### Installazione per Sviluppo

```bash
# Clona e installa in modalità editable
git clone https://github.com/mikibart/Muratura.git
cd Muratura
pip install -e .

# Installa dipendenze dev
pip install pytest pytest-cov black flake8 mypy
```

## 📖 Quick Start

### Esempio 1: Analisi Pushover con Telaio Equivalente

```python
from Material.engine import MasonryFEMEngine, AnalysisMethod
from Material.materials import MaterialProperties

# Crea motore con metodo telaio equivalente
engine = MasonryFEMEngine(method=AnalysisMethod.FRAME)

# Definisci materiale (muratura di mattoni)
material = MaterialProperties(
    name="Muratura mattoni pieni",
    E=1500.0,      # MPa - Modulo elastico
    fcm=4.0,       # MPa - Resistenza a compressione
    ftm=0.15,      # MPa - Resistenza a trazione
    tau0=0.1,      # MPa - Resistenza a taglio base
    mu=0.4,        # Coefficiente di attrito
    G=500.0,       # MPa - Modulo di taglio
    weight=18.0    # kN/m³ - Peso specifico
)

# Definisci geometria parete
wall_data = {
    'length': 5.0,      # m - Lunghezza parete
    'height': 6.0,      # m - Altezza totale (2 piani)
    'thickness': 0.3,   # m - Spessore
    'n_floors': 2,      # Numero piani
    'floor_masses': {   # Masse di piano [kg]
        0: 50000,       # Piano 1: 50 ton
        1: 45000        # Piano 2: 45 ton
    }
}

# Definisci carichi
loads = {
    0: {'Fx': 0, 'Fy': -50},  # kN - Carichi verticali
    1: {'Fx': 0, 'Fy': -45}
}

# Opzioni analisi pushover
options = {
    'analysis_type': 'pushover',
    'lateral_pattern': 'triangular',  # 'triangular', 'uniform', 'modal'
    'target_drift': 0.04,             # 4% drift obiettivo
    'n_steps': 50
}

# Esegui analisi
results = engine.analyze_structure(wall_data, material, loads, options)

# Visualizza risultati
print(f"✓ Analisi completata")
print(f"  Taglio base yield: {results['performance_levels']['yield']['base_shear']:.1f} kN")
print(f"  Drift yield: {results['performance_levels']['yield']['top_drift']*100:.2f}%")
print(f"  Duttilità: {results.get('ductility', 0):.2f}")
```

### Esempio 2: Analisi Modale

```python
from Material.engine import MasonryFEMEngine, AnalysisMethod
from Material.materials import MaterialProperties

engine = MasonryFEMEngine(method=AnalysisMethod.FRAME)
material = MaterialProperties(E=1500, fcm=4.0, G=500.0, weight=18.0)

wall_data = {
    'length': 5.0,
    'height': 9.0,      # 3 piani
    'thickness': 0.3,
    'n_floors': 3,
    'floor_masses': {0: 50000, 1: 50000, 2: 40000}
}

options = {
    'analysis_type': 'modal',
    'n_modes': 6
}

results = engine.analyze_structure(wall_data, material, {}, options)

# Visualizza modi di vibrare
for i, (freq, period, mx, my) in enumerate(zip(
    results['frequencies'],
    results['periods'],
    results['mass_participation_x'],
    results['mass_participation_y']
)):
    print(f"Modo {i+1}: T={period:.3f}s, f={freq:.2f}Hz, Mx={mx*100:.1f}%, My={my*100:.1f}%")

print(f"\nMassa partecipante X: {results['total_mass_participation_x']*100:.1f}%")
print(f"Massa partecipante Y: {results['total_mass_participation_y']*100:.1f}%")
```

### Esempio 3: Analisi Time-History

```python
import numpy as np
from Material.engine import MasonryFEMEngine, AnalysisMethod
from Material.materials import MaterialProperties

engine = MasonryFEMEngine(method=AnalysisMethod.FRAME)
material = MaterialProperties(E=1500, fcm=4.0, G=500.0, weight=18.0)

# Carica accelerogramma (esempio: sinusoide)
t = np.linspace(0, 10, 1000)  # 10 secondi, dt=0.01s
accelerogram = 0.3 * 9.81 * np.sin(2 * np.pi * 2.0 * t)  # 0.3g @ 2Hz

wall_data = {
    'length': 5.0,
    'height': 6.0,
    'thickness': 0.3,
    'n_floors': 2,
    'floor_masses': {0: 50000, 1: 45000}
}

options = {
    'analysis_type': 'time_history',
    'accelerogram': accelerogram.tolist(),
    'dt': 0.01,                    # Time step [s]
    'excitation_dir': 'y',         # Direzione eccitazione
    'accel_units': 'mps2'          # m/s²
}

results = engine.analyze_structure(wall_data, material, {}, options)

print(f"✓ Analisi time-history completata")
print(f"  Drift massimo: {results['time_history']['max_drift']*100:.2f}%")
print(f"  Accelerazione max: {results['time_history']['max_acceleration']:.2f} m/s²")
print(f"  Step critico: t={results['time_history']['critical_step']['time']:.2f}s")
print(f"  Taglio base critico: {results['time_history']['critical_step']['base_shear']:.1f} kN")
```

### Esempio 4: Analisi SAM (Semplificata)

```python
from Material.engine import MasonryFEMEngine, AnalysisMethod
from Material.materials import MaterialProperties

engine = MasonryFEMEngine(method=AnalysisMethod.SAM)

# Materiale (muratura di tufo)
material = MaterialProperties(
    fk=1.4,      # MPa - Resistenza caratteristica
    fvk0=0.035,  # MPa - Resistenza a taglio senza carichi
    fvk=0.074    # MPa - Resistenza a taglio con carichi
)

# Geometria semplificata
wall_data = {
    'piers': [
        {'length': 1.0, 'height': 2.8, 'thickness': 0.4},
        {'length': 1.2, 'height': 2.8, 'thickness': 0.4}
    ],
    'spandrels': [
        {'length': 1.5, 'height': 0.5, 'thickness': 0.4}
    ]
}

# Carichi da analisi sismica
loads = {
    'vertical': 200.0,  # kN
    'moment': 50.0,     # kNm
    'shear': 30.0       # kN
}

options = {
    'gamma_m': 2.0,  # Muratura esistente
    'FC': 1.35       # Fattore di confidenza LC1
}

results = engine.analyze_structure(wall_data, material, loads, options)

if results['verified']:
    print("✓ La parete SODDISFA le verifiche di sicurezza")
else:
    print("✗ La parete NON SODDISFA le verifiche")
    print(f"  DCR max: {results.get('max_dcr', 'N/A')}")
```

## 📚 Documentazione Completa

### Metodi di Analisi Disponibili

| Metodo | Enum | Descrizione | Uso Tipico |
|--------|------|-------------|------------|
| **FEM** | `AnalysisMethod.FEM` | Elementi finiti completi | Analisi dettagliate |
| **POR** | `AnalysisMethod.POR` | Pushover | Valutazione sismica |
| **SAM** | `AnalysisMethod.SAM` | Semplificato | Verifiche rapide NTC |
| **FRAME** | `AnalysisMethod.FRAME` | Telaio equivalente | Edifici multi-piano |
| **LIMIT** | `AnalysisMethod.LIMIT` | Analisi limite | Meccanismi collasso |
| **FIBER** | `AnalysisMethod.FIBER` | Modello a fibre | Non-linearità sezione |
| **MICRO** | `AnalysisMethod.MICRO` | Micro-modello | Dettaglio blocchi |

### Proprietà Materiali

```python
from Material.materials import MaterialProperties

# Muratura esistente - Mattoni pieni e malta di calce
material = MaterialProperties(
    name="Muratura storica",
    E=1200.0,      # MPa
    fcm=2.6,       # MPa (fm)
    ftm=0.1,       # MPa
    tau0=0.056,    # MPa (fv0)
    mu=0.4,
    G=400.0,       # MPa
    weight=18.0,   # kN/m³
    epsilon_c0=0.002,  # Deformazione picco compressione
    epsilon_cu=0.0035  # Deformazione ultima
)

# Muratura nuova - Blocchi in laterizio
material_new = MaterialProperties(
    name="Muratura nuova",
    E=2400.0,
    fcm=5.0,
    ftm=0.2,
    tau0=0.15,
    mu=0.4,
    G=800.0,
    weight=16.0
)
```

### Parametri Analisi Pushover

```python
options = {
    'analysis_type': 'pushover',

    # Pattern carico laterale
    'lateral_pattern': 'triangular',  # 'triangular', 'uniform', 'modal'

    # Controllo analisi
    'target_drift': 0.04,      # Drift obiettivo (4%)
    'n_steps': 50,             # Numero step incrementali

    # Opzioni avanzate
    'include_pdelta': True,    # Effetti P-Delta
    'include_material_nonlinearity': True
}
```

### Geometrie Complesse con Aperture

```python
from Material.geometry import GeometryWall, Opening, WallType

# Parete con aperture
wall = GeometryWall(
    length=10.0,
    height=9.0,
    thickness=0.4,
    n_floors=3,
    floor_height=3.0,
    wall_type=WallType.SINGLE_LEAF
)

# Aggiungi finestre
for floor in range(3):
    # Finestra 1
    wall.add_opening(floor, Opening(
        width=1.2,
        height=1.5,
        x_center=-2.0,  # Relativo al centro parete
        y_bottom=0.8,
        type="window"
    ))

    # Finestra 2
    wall.add_opening(floor, Opening(
        width=1.2,
        height=1.5,
        x_center=2.0,
        y_bottom=0.8,
        type="window"
    ))

# La parete identifica automaticamente maschi e fasce
print(f"Maschi identificati: {len(wall.piers)}")
print(f"Fasce identificate: {len(wall.spandrels)}")
```

## 🧪 Testing

```bash
# Esegui tutti i test
pytest tests/

# Con coverage
pytest --cov=Material --cov-report=html tests/

# Test specifici
pytest tests/test_engine.py -v
pytest tests/test_materials.py -k "test_material_validation"
```

## 📁 Struttura Progetto

```
Muratura/
├── Material/                    # Modulo principale
│   ├── __init__.py
│   ├── engine.py               # Motore FEM principale
│   ├── constitutive.py         # Modelli costitutivi
│   ├── materials.py            # Proprietà materiali
│   ├── geometry.py             # Geometrie strutturali
│   ├── utils.py                # Utilità varie
│   ├── enums.py                # Enumerazioni
│   └── analyses/               # Moduli di analisi
│       ├── fem.py
│       ├── por.py
│       ├── sam.py
│       ├── limit.py
│       ├── fiber.py
│       ├── micro.py
│       └── frame/
│           ├── model.py
│           └── element.py
├── examples/                    # Esempi di utilizzo
├── tests/                       # Test suite
├── docs/                        # Documentazione
├── requirements.txt             # Dipendenze
├── setup.py                     # Installazione
├── .gitignore
├── LICENSE
└── README.md
```

## 🤝 Contribuire

Contributi sono benvenuti! Per favore:

1. Fork il repository
2. Crea un branch per la feature (`git checkout -b feature/AmazingFeature`)
3. Commit le modifiche (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Apri una Pull Request

### Linee Guida

- Segui PEP 8 (usa `black` per formattare)
- Aggiungi test per nuove funzionalità
- Aggiorna la documentazione
- Mantieni coverage > 70%

## 📄 Licenza

Questo progetto è rilasciato sotto licenza MIT. Vedi il file [LICENSE](LICENSE) per dettagli.

## 📞 Contatti & Supporto

- **Issues**: [GitHub Issues](https://github.com/mikibart/Muratura/issues)
- **Discussioni**: [GitHub Discussions](https://github.com/mikibart/Muratura/discussions)

## 🙏 Riconoscimenti

- Conforme a **NTC 2018** (D.M. 17 gennaio 2018)
- Conforme a **Eurocodice 8** (EN 1998)
- Sviluppato per ricerca e applicazioni ingegneristiche

## 📊 Roadmap

### v6.2 (Q1 2025)
- [ ] Test suite completa (coverage > 80%)
- [ ] Documentazione API con Sphinx
- [ ] Validazione con casi benchmark

### v7.0 (Q2 2025)
- [ ] GUI web-based (Streamlit/Dash)
- [ ] Export CAD/BIM (IFC)
- [ ] Analisi probabilistiche estese

### v8.0 (Future)
- [ ] Machine learning per calibrazione parametri
- [ ] Cloud computing per analisi distribuite
- [ ] Integration con SAP2000/ETABS

## ⚠️ Note Importanti

> **DISCLAIMER**: Questo software è fornito "as is" senza garanzie di alcun tipo.
> L'utente è responsabile della verifica dei risultati e della conformità alle normative vigenti.
> Per applicazioni progettuali, si raccomanda sempre la supervisione di un ingegnere strutturista qualificato.

---

**Versione**: 6.1-FINAL
**Ultimo aggiornamento**: 2025-11-14
**Autore**: Sviluppato per ricerca strutturale
**Python**: 3.8+
**Status**: Production-Ready (in fase di testing)
