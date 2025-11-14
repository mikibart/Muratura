# MasonryFEMEngine

> **Sistema completo di analisi strutturale per murature secondo NTC 2018**

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 📋 Descrizione

**MasonryFEMEngine** è un motore di calcolo avanzato per l'analisi strutturale di edifici in muratura, conforme alle **Norme Tecniche per le Costruzioni NTC 2018** e agli **Eurocodici**.

Offre implementazioni di molteplici metodi di analisi:
- **FEM** - Finite Element Method
- **SAM** - Simplified Analysis of Masonry
- **POR** - Pushover su modello continuo
- **Frame** - Telaio equivalente
- **Limit** - Analisi limite cinematica
- **Fiber** - Modello a fibre
- **Micro** - Micro-modellazione

## 🚀 Caratteristiche Principali

- ✅ **Conforme NTC 2018**: Database materiali completo da Tabella C8.5.I
- ✅ **Metodi multipli**: 7 metodi di analisi implementati
- ✅ **Modelli costitutivi**: 10+ legami costitutivi non lineari
- ✅ **Analisi dinamiche**: Modale, time-history, pushover
- ✅ **24 cinematismi EC8**: Analisi di tutti i meccanismi di collasso
- ✅ **Validazione completa**: Controllo fisico e coerenza parametri
- ✅ **Export/Import**: JSON, Excel, formati commerciali
- ✅ **Murature complesse**: Multistrato, rinforzi, aperture

## 📦 Installazione

### Da sorgente

```bash
git clone https://github.com/yourusername/Muratura.git
cd Muratura
pip install -e .
```

### Dipendenze

```bash
pip install -r requirements.txt
```

## 🔧 Quick Start

### Esempio 1: Analisi Maschio Murario con SAM

```python
from muratura import MaterialProperties, MasonryType, MortarQuality
from muratura import MasonryFEMEngine, AnalysisMethod

# Definisci materiale da database NTC
material = MaterialProperties.from_ntc_table(
    MasonryType.MATTONI_PIENI,
    MortarQuality.BUONA,
    position='mean'
)

# Crea motore di analisi
engine = MasonryFEMEngine(method=AnalysisMethod.SAM)

# Definisci geometria e carichi
wall_data = {
    'length': 1.2,      # m - larghezza maschio
    'height': 3.0,      # m - altezza maschio
    'thickness': 0.3,   # m - spessore
}

loads = {
    'N': -150,          # kN - Sforzo normale (compressione negativa)
    'V': 50,            # kN - Taglio
    'M': 75             # kNm - Momento
}

# Esegui analisi
results = engine.analyze_structure(wall_data, material, loads)

# Visualizza risultati
print(f"Modo di rottura: {results['failure_mode']}")
print(f"DCR Flessione: {results['DCR_flexure']:.2f}")
print(f"DCR Taglio: {results['DCR_shear']:.2f}")
print(f"Verificato: {results['verified']}")
```

### Esempio 2: Analisi Pushover con Telaio Equivalente

```python
from muratura import MasonryFEMEngine, AnalysisMethod

engine = MasonryFEMEngine(method=AnalysisMethod.FRAME)

wall_data = {
    'length': 5.0,
    'height': 3.0,
    'thickness': 0.3,
    'floor_masses': {0: 50000}  # kg per piano
}

loads = {}  # Carichi verticali distribuiti automaticamente
options = {
    'analysis_type': 'pushover',
    'lateral_pattern': 'triangular',
    'target_drift': 0.04
}

results = engine.analyze_structure(wall_data, material, loads, options)

# Curva di capacità
for point in results['curve']:
    print(f"Drift: {point['top_drift']:.4f}, "
          f"Base Shear: {point['base_shear']:.1f} kN")

# Punto di snervamento
yield_point = results['performance_levels']['yield']
print(f"\nSnervamento a drift: {yield_point['top_drift']:.3%}")
```

### Esempio 3: Analisi Dinamica Time-History

```python
import numpy as np

# Genera o carica accelerogramma
dt = 0.01  # s
duration = 10  # s
t = np.arange(0, duration, dt)
accelerogram = 0.15 * 9.81 * np.sin(2*np.pi*2.0*t)  # sinusoide 2Hz, 0.15g

options = {
    'analysis_type': 'time_history',
    'accelerogram': accelerogram.tolist(),
    'dt': dt,
    'excitation_dir': 'y',
    'accel_units': 'mps2'
}

results = engine.analyze_structure(wall_data, material, loads, options)

print(f"Max drift: {results['time_history']['max_drift']:.3%}")
print(f"Critical time: {results['time_history']['critical_step']['time']:.2f} s")
```

## 📚 Documentazione

### Struttura del Progetto

```
Muratura/
├── muratura/              # Package principale
│   ├── __init__.py       # API principale
│   ├── materials.py      # Gestione materiali
│   ├── geometry.py       # Geometrie strutturali
│   ├── engine.py         # Motore principale
│   ├── enums.py          # Enumerazioni
│   ├── constitutive.py   # Legami costitutivi
│   ├── utils.py          # Utilities
│   └── analyses/         # Moduli di analisi
│       ├── __init__.py
│       ├── sam.py        # Simplified Analysis
│       ├── fem.py        # FEM
│       ├── por.py        # Pushover
│       ├── limit.py      # Analisi limite
│       ├── fiber.py      # Modello a fibre
│       ├── micro.py      # Micro-modellazione
│       └── frame/        # Telaio equivalente
│           ├── __init__.py
│           ├── model.py
│           └── element.py
├── tests/                # Test suite
├── examples/             # Esempi di utilizzo
├── docs/                 # Documentazione
├── setup.py              # Setup package
├── requirements.txt      # Dipendenze
├── README.md             # Questo file
└── LICENSE               # Licenza MIT
```

### Moduli Principali

#### **materials.py**
Gestione completa delle proprietà dei materiali murari:
- Database NTC 2018 completo
- Conversione tra sistemi di unità (SI, Tecnico, Imperiale)
- Validazione fisica dei parametri
- Export/Import JSON ed Excel
- Murature multistrato
- Effetti di temperatura e umidità

#### **geometry.py**
Definizione geometrie strutturali:
- Maschi murari (GeometryPier)
- Fasce di piano (GeometrySpandrel)
- Aperture e irregolarità
- Sistemi di rinforzo (FRP, FRCM, CAM)
- Archi e volte
- Calcolo proprietà sezionali effettive

#### **engine.py**
Motore principale di calcolo:
- Interfaccia unificata per tutti i metodi
- Assemblaggio matrici (sparse)
- Analisi statiche, modali, dinamiche
- Gestione vincoli e condizioni al contorno
- Post-processing risultati

#### **analyses/**
Moduli specializzati per ciascun metodo:
- **sam.py**: Analisi semplificata per componenti (≈30,000 linee)
- **fem.py**: Elementi finiti Q4/Q8
- **por.py**: Pushover continuo
- **limit.py**: 24 cinematismi EC8
- **fiber.py**: Discretizzazione a fibre
- **micro.py**: Blocchi e interfacce
- **frame/**: Telaio equivalente con elementi beam

## 🔬 Metodi di Analisi

### 1. SAM - Simplified Analysis of Masonry

Analisi per componenti secondo approccio NTC 2018:
- Verifica maschi murari (5 modi di rottura)
- Verifica fasce di piano (3 modi di rottura)
- Interazione taglio-flessione
- Effetti del secondo ordine
- Rigidezza effettive fessurate

**Quando usarlo**: Analisi preliminari, verifiche di singoli elementi

### 2. FEM - Finite Element Method

Analisi agli elementi finiti con elementi Q4/Q8:
- Stati tensionali e deformativi completi
- Concentrazioni di tensione
- Pattern di fessurazione
- Analisi non lineare (opzionale)

**Quando usarlo**: Analisi dettagliate, geometrie complesse

### 3. Frame - Telaio Equivalente

Modello strutturale globale:
- Maschi come elementi beam verticali
- Fasce come elementi beam orizzontali
- Analisi modale (con masse partecipanti)
- Pushover (pattern multipli)
- Time-history (Newmark-β)

**Quando usarlo**: Analisi globale edificio, analisi sismiche

### 4. Limit - Analisi Limite

Approccio cinematico EC8:
- 24 meccanismi di collasso
- Coefficiente di attivazione α
- Ottimizzazione rinforzi
- Analisi probabilistica

**Quando usarlo**: Meccanismi locali, edifici storici

### 5. Fiber - Modello a Fibre

Discretizzazione sezione in fibre:
- Legami costitutivi non lineari
- Cicli isteretici
- Analisi pushover incrementale
- Calcolo duttilità

**Quando usarlo**: Comportamento post-elastico, cicli di carico

### 6. Micro - Micro-modellazione

Modellazione esplicita di blocchi e giunti:
- Interfacce con attrito e coesione
- Pattern di fessurazione nei giunti
- Omogeneizzazione proprietà
- Analisi di dettaglio

**Quando usarlo**: Ricerca, validazione parametri, dettagli costruttivi

## 🧪 Testing

```bash
# Esegui tutti i test
pytest tests/

# Con coverage
pytest --cov=muratura tests/

# Test specifico
pytest tests/test_materials.py
```

## 🤝 Contribuire

Contributi benvenuti! Per favore:
1. Fork del repository
2. Crea branch per la feature (`git checkout -b feature/amazing-feature`)
3. Commit delle modifiche (`git commit -m 'Add amazing feature'`)
4. Push al branch (`git push origin feature/amazing-feature`)
5. Apri una Pull Request

## 📄 Licenza

Questo progetto è rilasciato sotto licenza **MIT**. Vedi il file [LICENSE](LICENSE) per dettagli.

## 📖 Riferimenti

### Normative
- **NTC 2018** - Norme Tecniche per le Costruzioni (D.M. 17/01/2018)
- **Circolare NTC 2019** - Circolare esplicativa (C.S.LL.PP. 21/01/2019)
- **Eurocodice 6** - Design of masonry structures (EN 1996)
- **Eurocodice 8** - Design of structures for earthquake resistance (EN 1998)

### Bibliografia
- Magenes, G., & Calvi, G. M. (1997). *In-plane seismic response of brick masonry walls*
- Lagomarsino, S., et al. (2013). *TREMURI program: Seismic analysis of 3D masonry buildings*
- Roca, P., et al. (2010). *Structural Analysis of Masonry Historical Constructions*

## 👥 Autori

- **MasonryFEM Contributors** - Sviluppo iniziale

## 📧 Contatti

Per domande, bug report o feature request, apri una [Issue](https://github.com/yourusername/Muratura/issues).

---

**Made with ❤️ for structural engineering**
