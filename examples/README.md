# Esempi di Utilizzo MasonryFEMEngine

Questa directory contiene esempi pratici di utilizzo del sistema MasonryFEMEngine.

## Elenco Esempi

### Esempio 1: Analisi SAM Base
**File:** `example_01_basic_sam.py`

Analisi di un maschio murario con il metodo SAM (Simplified Analysis of Masonry).

**Cosa imparerai:**
- Creare materiali dal database NTC 2018
- Definire geometria di un maschio murario
- Applicare carichi statici
- Interpretare i risultati (DCR, modi di rottura)

**Esegui:**
```bash
python examples/example_01_basic_sam.py
```

### Esempio 2: Analisi Pushover
**File:** `example_02_pushover.py`

Analisi pushover su edificio multipiano con telaio equivalente.

**Cosa imparerai:**
- Modellare edificio multipiano
- Configurare analisi pushover
- Interpretare curva di capacità
- Identificare livelli prestazionali

**Esegui:**
```bash
python examples/example_02_pushover.py
```

## Requisiti

Assicurati di aver installato il package:

```bash
pip install -e .
```

O installa le dipendenze:

```bash
pip install -r requirements.txt
```

## Struttura Tipo di un Esempio

```python
from muratura import MaterialProperties, MasonryFEMEngine, AnalysisMethod

# 1. Definisci materiale
material = MaterialProperties.from_ntc_table(...)

# 2. Definisci geometria
wall_data = {...}

# 3. Definisci carichi
loads = {...}

# 4. Crea motore e esegui
engine = MasonryFEMEngine(method=AnalysisMethod.SAM)
results = engine.analyze_structure(wall_data, material, loads)

# 5. Visualizza risultati
print(results)
```

## Prossimi Esempi (In Arrivo)

- Esempio 3: Analisi Time-History
- Esempio 4: Analisi Limite (24 cinematismi EC8)
- Esempio 5: Modello a Fibre
- Esempio 6: Micro-modellazione
- Esempio 7: Edificio Completo con Aperture
- Esempio 8: Ottimizzazione Rinforzi

## Supporto

Per domande o problemi con gli esempi, apri una [Issue](https://github.com/mikibart/Muratura/issues).
