# 🧪 File di Test - Wire Editor Unified v6.1

Questa directory contiene file di esempio per testare le funzionalità di **import** del Wire Editor Unified.

## 📁 File Disponibili

### 1. **test_coordinates.csv**
- **Formato:** CSV completo con ID
- **Punti:** 15 nodi
- **Livelli:** PT, P1, P2, COPERTURA
- **Struttura:** `ID,X,Y,Z,Livello,Descrizione`
- **Uso:** Testa import CSV con tutti i campi

### 2. **test_simple.csv**
- **Formato:** CSV semplificato senza ID
- **Punti:** 8 nodi
- **Livelli:** PT, P1
- **Struttura:** `X,Y,Z,Livello,Descrizione`
- **Uso:** Testa auto-generazione ID durante import

### 3. **test_drawing.dxf**
- **Formato:** DXF (AutoCAD Drawing Exchange Format)
- **Punti:** 9 punti con descrizioni
- **Livelli:** PT, P1, P2, COPERTURA (come layer DXF)
- **Entità:** POINT + TEXT (descrizioni)
- **Uso:** Testa import da CAD

### 4. **create_excel_test.py** ⚡
- **Script Python** per generare `test_coordinates.xlsx`
- **Richiede:** `openpyxl` installato
- **Eseguire:** `python create_excel_test.py`

## 🚀 Come Usare i File di Test

### Passo 1: Avvia Wire Editor Unified
```bash
python WIRE_EDITOR_UNIFIED.py
```

### Passo 2: Vai al Tab "Reports"
Nella finestra principale, clicca sul tab **"Reports"** in alto.

### Passo 3: Sezione "Import Dati"
Troverai 3 pulsanti:
- 📄 **Import CSV**
- 📊 **Import Excel**
- 📐 **Import DXF**

### Passo 4: Testa gli Import

#### 📄 Test CSV Completo
1. Click su "Import CSV"
2. Seleziona `test_coordinates.csv`
3. ✅ Dovrebbero essere importati **15 nodi**
4. Verifica nella tabella che gli ID siano 1-15

#### 📄 Test CSV Semplice (Auto-ID)
1. Click su "Import CSV"
2. Seleziona `test_simple.csv`
3. ✅ Dovrebbero essere importati **8 nodi**
4. Verifica che gli ID siano auto-generati (partendo dal prossimo disponibile)

#### 📊 Test Excel (genera prima il file!)
1. Esegui `python create_excel_test.py` in questa directory
2. Click su "Import Excel" in Wire Editor
3. Seleziona `test_coordinates.xlsx`
4. ✅ Dovrebbero essere importati **15 nodi** con formattazione

#### 📐 Test DXF
1. Click su "Import DXF"
2. Seleziona `test_drawing.dxf`
3. ✅ Dovrebbero essere importati **9 punti** da CAD
4. Nota: i TEXT vengono associati ai POINT vicini come descrizioni

## 📊 Dataset di Esempio

I file rappresentano un **edificio a 3 piani** (5.5m × 8.25m):

- **PT (Piano Terra):** 4 angoli dell'edificio (Z=0.0m)
- **P1 (Piano 1):** 4 fili fissi a H=3.2m
- **P2 (Piano 2):** 5 fili fissi a H=6.4m
- **COPERTURA:** 2 punti sommitali a H=9.6m

### Coordinate Edificio
```
   Nord (Y=0)
   ┌─────────────┐
   │   5.5m      │
O  │             │  E
v  │   8.25m     │  s
e  │             │  t
s  └─────────────┘
t     Sud (Y=8.25)
```

## ✅ Verifica Risultati

Dopo ogni import, verifica:

1. **Tab Table View:** tutti i nodi sono nella tabella
2. **Tab Canvas View:** visualizzazione 2D XY
3. **Tab 3D View:** visualizzazione 3D completa
4. **Tab Reports → Statistiche:** conteggi corretti

### Statistiche Attese (test_coordinates.csv)
```
Totale Nodi: 15
Livelli: PT (4), P1 (4), P2 (5), COPERTURA (2)
X: 0.00 ÷ 5.50 (Δ=5.50m)
Y: 0.00 ÷ 8.25 (Δ=8.25m)
Z: 0.00 ÷ 9.60 (Δ=9.60m)
```

## 🔧 Troubleshooting

### "Openpyxl non disponibile"
```bash
pip install openpyxl
```

### "Ezdxf non disponibile, usato parser manuale"
È normale! Il parser manuale funziona ugualmente.
Per funzionalità avanzate DXF:
```bash
pip install ezdxf
```

### Errori durante import
- Controlla il formato del file
- Verifica encoding UTF-8
- Leggi il messaggio di errore dettagliato con numero riga

## 💡 Suggerimenti

- **Testa Undo/Redo:** dopo import, prova Ctrl+Z per annullare
- **Combina import:** importa più file per costruire progetti complessi
- **Esporta dopo import:** verifica round-trip CSV→Import→Export→CSV
- **Modifica in tabella:** cambia coordinate e descrizioni inline

## 📝 Crea i Tuoi File di Test

### Formato CSV Minimo
```csv
X,Y,Z
0.0,0.0,0.0
10.0,0.0,0.0
10.0,10.0,0.0
```

### Formato CSV Completo
```csv
ID,X,Y,Z,Livello,Descrizione
1,0.0,0.0,0.0,PT,Descrizione punto
```

Buon testing! 🎉
