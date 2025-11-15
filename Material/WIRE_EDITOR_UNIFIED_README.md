# Wire Editor Unified v6.0-rc

**Applicazione integrata per gestione coordinate fili fissi e design topologie strutturali**

Sviluppato per: Arch. Michelangelo Bartolotta
Ordine Architetti Agrigento n. 1557

---

## Panoramica

Wire Editor Unified combina le funzionalità di due applicazioni precedenti:
- **wire_editor.py** - Input tabellare coordinate, import/export, reports
- **wire_editor1.py** - Canvas grafico, design topologie, disegno interattivo

Il risultato è un'applicazione unificata con architettura multi-vista e data model condiviso.

---

## Architettura

### Data Model Unificato

Il sistema si basa su un data model centralizzato (`UnifiedModel`) che gestisce:

#### 1. **Node (Nodo)**
```python
class Node:
    id: int                    # ID univoco
    x: float                   # Coordinata X (metri)
    y: float                   # Coordinata Y (metri)
    z: float                   # Coordinata Z/quota (metri)
    description: str           # Descrizione (es: "Pilastro A1")
    level: str                 # Livello/Piano (es: "PT", "P1", "P2")
    topology_role: TopologyRole  # Ruolo topologico (FREE, CENTER, CORNER, etc.)
    snap_radius: float         # Raggio snap (metri, default 0.15)
    color: QColor              # Colore visualizzazione
    selected: bool             # Stato selezione
```

**Metodi:**
- `to_dict()` / `from_dict()` - Serializzazione JSON
- `distance_to(other)` - Distanza 2D
- `distance_3d_to(other)` - Distanza 3D

#### 2. **Edge (Collegamento)**
```python
class Edge:
    id: int                    # ID univoco
    node1_id: int              # ID nodo inizio
    node2_id: int              # ID nodo fine
    edge_type: EdgeType        # Tipo (FREE, HORIZONTAL, VERTICAL, DIAGONAL)
    color: QColor              # Colore visualizzazione
    width: int                 # Spessore linea
    selected: bool             # Stato selezione
```

#### 3. **Annotation (Annotazione Grafica)**
```python
# Classe base
class Annotation:
    type: str                  # Tipo annotazione
    color: str                 # Colore
    linewidth: int             # Spessore

# Sottoclassi
class LineAnnotation(Annotation):
    node1_id: int              # Nodo inizio
    node2_id: int              # Nodo fine
    style: str                 # 'solid', 'dashed', 'dotted'

class DimensionAnnotation(Annotation):
    node1_id: int              # Nodo inizio
    node2_id: int              # Nodo fine
    offset: float              # Offset quota (metri)
    show_text: bool            # Mostra testo distanza
```

#### 4. **UnifiedModel (Model Centrale)**
```python
class UnifiedModel:
    nodes: Dict[int, Node]                # Dizionario nodi
    edges: Dict[int, Edge]                # Dizionario edges
    annotations: List[Annotation]         # Lista annotazioni
    next_node_id: int                     # Prossimo ID nodo
    next_edge_id: int                     # Prossimo ID edge
    metadata: Dict[str, Any]              # Metadati progetto
    undo_stack: List[Command]             # Stack undo
    redo_stack: List[Command]             # Stack redo
```

**Metodi principali:**
- `add_node(x, y, z, description, level, topology_role)` → node_id
- `update_node(node_id, **kwargs)` → bool
- `delete_node(node_id)` → bool
- `add_edge(node1_id, node2_id, edge_type)` → edge_id
- `delete_edge(edge_id)` → bool
- `get_node_list()` → List[Node]
- `get_levels()` → List[str]
- `get_nodes_by_level(level)` → List[Node]
- `get_bounds()` → Dict (x_min, x_max, y_min, y_max, z_min, z_max)
- `execute_command(command)` - Esegue comando con undo/redo
- `undo()` / `redo()` - Annulla/ripristina operazioni
- `to_dict()` / `from_dict()` - Serializzazione completa

---

## Command Pattern (Undo/Redo)

Tutte le operazioni sui dati usano il **Command Pattern** per supportare undo/redo illimitato (max 50 livelli):

### Comandi Disponibili

1. **CreateNodeCommand** - Crea nuovo nodo
   ```python
   cmd = CreateNodeCommand(x, y, z, description, level, topology_role)
   node_id = model.execute_command(cmd)
   ```

2. **UpdateNodeCommand** - Modifica nodo esistente
   ```python
   cmd = UpdateNodeCommand(node_id, x=10.5, description="Nuovo nome")
   model.execute_command(cmd)
   ```

3. **DeleteNodeCommand** - Elimina nodo (e edges connessi)
   ```python
   cmd = DeleteNodeCommand(node_id)
   model.execute_command(cmd)
   ```

4. **CreateEdgeCommand** - Crea collegamento
   ```python
   cmd = CreateEdgeCommand(node1_id, node2_id, EdgeType.FREE)
   edge_id = model.execute_command(cmd)
   ```

5. **DeleteEdgeCommand** - Elimina collegamento
   ```python
   cmd = DeleteEdgeCommand(edge_id)
   model.execute_command(cmd)
   ```

**Operazioni Undo/Redo:**
```python
model.undo()          # Annulla ultima operazione
model.redo()          # Ripristina operazione annullata
model.can_undo()      # Verifica se undo disponibile
model.can_redo()      # Verifica se redo disponibile
```

---

## Interfaccia Utente - 4 Viste

### 1. **Table View** (Input Tabellare)

**Componenti:**
- `CoordinateInputPanel` - Form input coordinate (X, Y, Z, Livello, Descrizione)
- `CoordinateTable` - Tabella modificabile con 6 colonne

**Funzionalità:**
- Input rapido coordinate con auto-incremento X
- Editing inline celle tabella
- Filtro per livello
- Eliminazione nodi con DEL
- Info bounds in tempo reale
- Segnali: `node_added`, `data_changed`

**Shortcuts:**
- Enter: aggiungi nodo
- DEL: elimina nodo selezionato

### 2. **Canvas View** (Editor Grafico)

**Componente:**
- `WireCanvasView` - Canvas QPainter interattivo

**Funzionalità:**
- Rendering nodi, edges, griglia
- Conversione coordinate schermo ↔ mondo (metri)
- Zoom/Pan navigazione
- Selezione interattiva
- Drag & drop nodi
- Creazione edges visuale
- Grid toggleable
- Coordinate toggleable

**Controlli Mouse:**
- **Doppio click**: crea nuovo nodo
- **Click+Drag**: sposta nodo
- **Ctrl+Click su nodo**: inizia edge
- **Click su secondo nodo**: completa edge
- **Tasto centrale/destro**: pan vista
- **Rotella mouse**: zoom in/out

**Shortcuts:**
- F: fit to extents (adatta vista)
- DEL: elimina nodo selezionato

**Rendering:**
- Griglia: 1 quadrato = 1 metro (scalato con zoom)
- Nodi: cerchi con ID, descrizione, coordinate
- Edges: linee con lunghezza in metri
- Colori: selected (rosso), hover (verde), normale (blu)

### 3. **3D View** (Visualizzazione 3D)

**Stato:** Placeholder FASE 3
- Integrazione PlotDialog da wire_editor.py
- Matplotlib 3D scatter + wireframe
- Vista XY, XZ, YZ
- Annotazioni grafiche

### 4. **Reports** (Export e Statistiche)

**Stato:** Placeholder FASE 3
- Export PDF (reportlab)
- Export Excel (openpyxl)
- Statistiche progetto
- Tabelle formattate

---

## Formati File

### JSON (Formato Nativo)

```json
{
  "version": "6.0",
  "metadata": {
    "author": "Arch. Michelangelo Bartolotta",
    "registration": "Ordine Architetti Agrigento n. 1557",
    "project_type": "Coordinate Fili Fissi",
    "created": "2025-11-15T10:30:00",
    "modified": "2025-11-15T12:45:00",
    "project_name": "Edificio A",
    "location": "Via Roma 123",
    "notes": "Note progetto"
  },
  "nodes": [
    {
      "id": 1,
      "x": 10.5,
      "y": 20.3,
      "z": 0.0,
      "description": "Pilastro A1",
      "level": "PT",
      "topology_role": "free",
      "snap_radius": 0.15,
      "color": "#6496c8"
    }
  ],
  "edges": [
    {
      "id": 1,
      "node1_id": 1,
      "node2_id": 2,
      "edge_type": "free",
      "color": "#505050",
      "width": 2
    }
  ],
  "annotations": [],
  "next_node_id": 3,
  "next_edge_id": 2
}
```

### Import/Export Previsti (FASE 3)

- **CSV** - Coordinate tabellari
- **Excel (.xlsx)** - Tabelle formattate con stili
- **DXF** - Import da AutoCAD (POINT, TEXT, INSERT entities)
- **PDF** - Report professionale

---

## Enumerazioni

### TopologyRole
```python
class TopologyRole(Enum):
    CENTER = "center"           # Nodo centrale
    CORNER = "corner"           # Angolo
    EDGE_MIDPOINT = "edge"      # Punto medio lato
    FREE = "free"               # Libero
```

### EdgeType
```python
class EdgeType(Enum):
    HORIZONTAL = "horizontal"   # Orizzontale
    VERTICAL = "vertical"       # Verticale
    DIAGONAL = "diagonal"       # Diagonale
    FREE = "free"               # Libero
```

### Direction
```python
class Direction(Enum):
    NORTH = "north"             # Nord
    SOUTH = "south"             # Sud
    EAST = "east"               # Est
    WEST = "west"               # Ovest
    NONE = "none"               # Nessuna
```

---

## Synchronization Cross-View

Il sistema mantiene sincronizzati i dati tra le viste:

**TableView → CanvasView:**
- Aggiunta nodo da tabella → refresh canvas
- Modifica coordinate → aggiornamento posizione grafica
- Eliminazione nodo → rimozione dal canvas

**CanvasView → TableView:**
- Creazione nodo con doppio click → inserimento in tabella
- Drag nodo → aggiornamento coordinate in tabella
- Eliminazione nodo → rimozione da tabella

**Meccanismo:**
- Callback Qt signals: `node_added`, `data_changed`, `selection_changed`
- Shared UnifiedModel (single source of truth)
- Command pattern garantisce consistenza undo/redo

---

## Dipendenze

### Obbligatorie
- Python 3.x
- PyQt5

### Opzionali (Features FASE 3)
- **matplotlib** - Visualizzazione 3D
- **openpyxl** - Import/Export Excel
- **reportlab** - Generazione PDF
- **ezdxf** - Import DXF avanzato

**Installazione:**
```bash
pip install PyQt5 matplotlib openpyxl reportlab ezdxf
```

---

## Utilizzo

### Avvio Applicazione
```bash
python3 wire_editor_unified.py
```

### Workflow Tipico

1. **Input Coordinate (Table View)**
   - Inserisci coordinate in forma tabellare
   - Usa auto-incremento per input rapido
   - Filtra per livello se necessario

2. **Design Grafico (Canvas View)**
   - Visualizza nodi su canvas
   - Crea collegamenti con Ctrl+Click
   - Sposta nodi con drag & drop
   - Usa zoom/pan per navigare

3. **Verifica 3D (3D View)** [FASE 3]
   - Visualizza modello 3D
   - Ruota vista XY/XZ/YZ
   - Aggiungi annotazioni

4. **Export (Reports)** [FASE 3]
   - Genera PDF professionale
   - Esporta Excel formattato
   - Statistiche progetto

### Salvataggio Progetti

**Menu File:**
- New Project (Ctrl+N)
- Open... (Ctrl+O) - Carica .json
- Save... (Ctrl+S) - Salva .json
- Exit (Ctrl+Q)

**Menu Edit:**
- Undo (Ctrl+Z)
- Redo (Ctrl+Y)
- Project Info... - Modifica metadata

**Menu View:**
- Table View (Ctrl+1)
- Canvas View (Ctrl+2)
- 3D View (Ctrl+3)
- Reports (Ctrl+4)

---

## Struttura Codice

```
wire_editor_unified.py (1758 righe)
├── ENUMERAZIONI (linee 78-104)
│   ├── Direction
│   ├── TopologyRole
│   └── EdgeType
│
├── DATA MODEL (linee 107-520)
│   ├── Node (110-167)
│   ├── Edge (169-205)
│   ├── Annotation (208-283)
│   └── UnifiedModel (286-520)
│
├── COMMAND PATTERN (linee 523-667)
│   ├── Command base (526-535)
│   ├── CreateNodeCommand (538-560)
│   ├── UpdateNodeCommand (563-585)
│   ├── DeleteNodeCommand (588-625)
│   ├── CreateEdgeCommand (628-644)
│   └── DeleteEdgeCommand (647-666)
│
├── CANVAS VIEW (linee 670-1040)
│   └── WireCanvasView (673-1039)
│       ├── Rendering (paintEvent, draw_grid, draw_edges, draw_nodes)
│       ├── Coordinate conversion (screen_to_world, world_to_screen)
│       ├── Mouse events (press, move, release, wheel, doubleClick)
│       ├── Keyboard events (delete, fit)
│       └── Navigation (zoom, pan, fit_to_extents)
│
├── TABLE VIEW (linee 1043-1268)
│   ├── CoordinateInputPanel (1046-1152)
│   └── CoordinateTable (1155-1268)
│
├── MAIN WINDOW (linee 1271-1718)
│   └── UnifiedMainWindow (1274-1718)
│       ├── setup_ui (1293-1313)
│       ├── setup_table_tab (1315-1367)
│       ├── setup_canvas_tab (1369-1413)
│       ├── setup_viz_tab (1415-1434)
│       ├── setup_reports_tab (1436-1449)
│       ├── setup_menus (1451-1482)
│       ├── setup_toolbar (1484-1494)
│       ├── setup_statusbar (1496-1507)
│       ├── Callbacks (1611-1658)
│       └── File operations (1524-1598)
│
└── MAIN (linee 1721-1758)
    └── QApplication setup e stile
```

---

## Roadmap FASE 3

### Features Avanzate da Implementare

1. **3D Visualization Tab**
   - Integrazione PlotDialog matplotlib
   - Viste XY, XZ, YZ
   - Rotazione 3D interattiva
   - Annotazioni grafiche su plot

2. **Reports Tab**
   - Generazione PDF con reportlab
   - Export Excel formattato
   - Statistiche progetto
   - Tabelle coordinate professionali

3. **Import/Export Completo**
   - Import CSV coordinate
   - Export CSV coordinate
   - Import Excel (coordinate + metadata)
   - Export Excel (formattato con stili)
   - Import DXF (AutoCAD)
   - Export DXF

4. **Generators**
   - Griglia regolare parametrica
   - Interpiano automatico
   - Pattern topologie comuni

5. **Advanced Editing**
   - Selezione multipla
   - Trasformazioni (trasla, ruota, scala)
   - Specchia punti
   - Snap to grid
   - Trova duplicati
   - Merge nodi vicini

6. **Metadata Editor**
   - Dialog informazioni progetto
   - Campi personalizzati
   - Export metadata in PDF

---

## Changelog

### v6.0-rc (2025-11-15) - FASE 2 Complete
- ✅ Data model unificato completo
- ✅ Command pattern con undo/redo
- ✅ Table View integrato
- ✅ Canvas View interattivo
- ✅ Cross-view synchronization
- ✅ File I/O JSON
- ✅ Multi-tab architecture

### v6.0-beta (2025-11-15) - TableView
- ✅ CoordinateInputPanel
- ✅ CoordinateTable con editing inline
- ✅ Filtro livelli
- ✅ Bounds visualization

### v6.0-alpha (2025-11-15) - Foundation
- ✅ UnifiedModel base
- ✅ Command pattern structure
- ✅ MainWindow con 4 tabs
- ✅ Serializzazione JSON

### Predecessori
- **wire_editor.py v5.3** - Input tabellare, DXF, Annotazioni
- **wire_editor1.py v2.0** - Canvas topologie

---

## Note Tecniche

### Performance
- Grid rendering limitato a grid_step > 5px per performance
- Antialiasing su canvas per qualità
- Lazy refresh solo quando necessario

### Thread Safety
- Single-threaded Qt application
- No threading per semplicità
- Undo/redo stack limitato a 50 operazioni

### Coordinate System
- Origine: bottom-left (standard cartesiano)
- Unità: metri
- Griglia: 1 quadrato = 1 metro base (scalato con zoom)
- Screen Y invertito (Qt top-left → world bottom-left)

---

## Licenza e Copyright

Sviluppato per:
**Arch. Michelangelo Bartolotta**
Ordine Architetti Agrigento n. 1557

Applicazione professionale per gestione coordinate fili fissi e design topologie strutturali.

---

## Supporto

Per domande e supporto tecnico contattare:
- Arch. Michelangelo Bartolotta
- Ordine Architetti Agrigento n. 1557

**Versione:** 6.0-rc (Release Candidate)
**Data:** 2025-11-15
**Stato:** FASE 2 Completata - Ready for FASE 3
