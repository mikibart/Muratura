# Wire Editor Unified - Data Types Documentation

**Documentazione completa dei tipi di dati di input/output**

---

## Indice

1. [Tipi di Dati Primitivi](#tipi-di-dati-primitivi)
2. [Classi Data Model](#classi-data-model)
3. [Enumerazioni](#enumerazioni)
4. [Strutture JSON](#strutture-json)
5. [Formati Import/Export](#formati-importexport)
6. [Command Pattern Types](#command-pattern-types)
7. [Qt Signal Types](#qt-signal-types)

---

## Tipi di Dati Primitivi

### Coordinate Spaziali
```python
x: float          # Coordinata X in metri [-10000, 10000]
y: float          # Coordinata Y in metri [-10000, 10000]
z: float          # Coordinata Z/quota in metri [-1000, 1000]
```

**Precisione:**
- X, Y: 4 decimali (0.0001m = 0.1mm)
- Z: 3 decimali (0.001m = 1mm)

### Identificatori
```python
node_id: int      # ID univoco nodo (auto-incrementale, >= 1)
edge_id: int      # ID univoco edge (auto-incrementale, >= 1)
```

### Stringhe Descrittive
```python
description: str  # Descrizione nodo (max consigliato: 50 caratteri)
                  # Esempio: "Pilastro A1", "Punto angolo NE"

level: str        # Livello/Piano (formato libero)
                  # Convenzioni: "PT" (piano terra), "P1", "P2", "-1" (interrato)
                  # Max consigliato: 10 caratteri
```

### Parametri Visualizzazione
```python
snap_radius: float      # Raggio snap in metri (default: 0.15)
node_radius: int        # Raggio nodo in pixel (default: 8)
grid_size: int          # Dimensione griglia in pixel/metro (default: 50)
zoom_factor: float      # Fattore zoom (range: 0.1 - 10.0)
```

### Colori
```python
color: QColor           # Colore Qt
color_hex: str          # Colore esadecimale "#RRGGBB"
                        # Esempio: "#6496c8" (blu nodi)
```

---

## Classi Data Model

### 1. Node (Nodo)

**Definizione Completa:**
```python
@dataclass
class Node:
    """Nodo unificato - combina Point e Node properties"""

    # Identificatore
    id: int                           # ID univoco (>= 1)

    # Coordinate spaziali
    x: float                          # X in metri
    y: float                          # Y in metri
    z: float = 0.0                    # Z in metri (default 0)

    # Descrittori
    description: str = ""             # Descrizione opzionale
    level: str = ""                   # Livello/Piano

    # Proprietà topologiche
    topology_role: TopologyRole = TopologyRole.FREE
    snap_radius: float = 0.15         # Raggio snap (metri)

    # Visualizzazione
    color: QColor = QColor(100, 150, 200)  # Colore blu default
    selected: bool = False            # Stato selezione
```

**Serializzazione JSON:**
```python
def to_dict(self) -> Dict[str, Any]:
    return {
        'id': int,
        'x': float,
        'y': float,
        'z': float,
        'description': str,
        'level': str,
        'topology_role': str,          # Enum.value
        'snap_radius': float,
        'color': str                    # Hex "#RRGGBB"
    }
```

**Esempio JSON:**
```json
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
```

**Metodi:**
```python
distance_to(other: Node) -> float        # Distanza 2D (metri)
distance_3d_to(other: Node) -> float     # Distanza 3D (metri)
to_dict() -> Dict[str, Any]              # Serializzazione
from_dict(data: Dict) -> Node            # Deserializzazione (classmethod)
```

---

### 2. Edge (Collegamento)

**Definizione Completa:**
```python
@dataclass
class Edge:
    """Collegamento tra due nodi"""

    # Identificatore
    id: int                           # ID univoco (>= 1)

    # Topologia
    node1_id: int                     # ID nodo inizio
    node2_id: int                     # ID nodo fine
    edge_type: EdgeType = EdgeType.FREE

    # Visualizzazione
    color: QColor = QColor(80, 80, 80)  # Colore grigio default
    width: int = 2                    # Spessore linea (pixel)
    selected: bool = False            # Stato selezione
```

**Serializzazione JSON:**
```python
def to_dict(self) -> Dict[str, Any]:
    return {
        'id': int,
        'node1_id': int,
        'node2_id': int,
        'edge_type': str,              # Enum.value
        'color': str,                  # Hex "#RRGGBB"
        'width': int
    }
```

**Esempio JSON:**
```json
{
  "id": 1,
  "node1_id": 1,
  "node2_id": 2,
  "edge_type": "free",
  "color": "#505050",
  "width": 2
}
```

**Vincoli:**
- `node1_id != node2_id` (no self-loops)
- Entrambi i nodi devono esistere in `UnifiedModel.nodes`
- Non permessi edge duplicati tra stessa coppia di nodi

---

### 3. Annotation (Annotazione Grafica)

#### 3.1 Annotation Base

```python
@dataclass
class Annotation:
    """Classe base annotazione"""
    type: str                         # 'line' | 'dimension'
    color: str = 'red'                # Colore (nome o hex)
    linewidth: int = 2                # Spessore linea
```

#### 3.2 LineAnnotation

```python
@dataclass
class LineAnnotation(Annotation):
    """Linea di annotazione tra due nodi"""
    type: str = 'line'                # Fisso
    node1_id: int                     # ID nodo inizio
    node2_id: int                     # ID nodo fine
    color: str = 'red'
    linewidth: int = 2
    style: str = 'solid'              # 'solid' | 'dashed' | 'dotted'
```

**Esempio JSON:**
```json
{
  "type": "line",
  "node1_id": 1,
  "node2_id": 2,
  "color": "red",
  "linewidth": 2,
  "style": "dashed"
}
```

#### 3.3 DimensionAnnotation

```python
@dataclass
class DimensionAnnotation(Annotation):
    """Quota/dimensione tra due nodi"""
    type: str = 'dimension'           # Fisso
    node1_id: int                     # ID nodo inizio
    node2_id: int                     # ID nodo fine
    offset: float = 0.5               # Offset perpendicolare (metri)
    color: str = 'blue'
    show_text: bool = True            # Mostra distanza in metri
```

**Esempio JSON:**
```json
{
  "type": "dimension",
  "node1_id": 1,
  "node2_id": 2,
  "offset": 0.5,
  "color": "blue",
  "show_text": true
}
```

---

### 4. UnifiedModel (Container Principale)

**Definizione Completa:**
```python
class UnifiedModel:
    """Model unificato - single source of truth"""

    # Dati principali
    nodes: Dict[int, Node]                    # Mappa ID → Node
    edges: Dict[int, Edge]                    # Mappa ID → Edge
    annotations: List[Annotation]             # Lista annotazioni

    # Contatori
    next_node_id: int                         # Prossimo ID nodo disponibile
    next_edge_id: int                         # Prossimo ID edge disponibile

    # Metadata progetto
    metadata: Dict[str, Any] = {
        "author": str,                        # Nome autore
        "registration": str,                  # Numero iscrizione ordine
        "project_type": str,                  # Tipo progetto
        "created": str,                       # ISO datetime
        "modified": str,                      # ISO datetime
        "project_name": str,                  # Nome progetto
        "location": str,                      # Località
        "notes": str                          # Note
    }

    # Undo/Redo
    undo_stack: List[Command]                 # Stack comandi undo
    redo_stack: List[Command]                 # Stack comandi redo
    max_undo_levels: int = 50                 # Max operazioni undo
```

**Metodi di Accesso Dati:**
```python
# Nodi
add_node(x: float, y: float, z: float = 0.0,
         description: str = "", level: str = "",
         topology_role: TopologyRole = TopologyRole.FREE) -> int

update_node(node_id: int, **kwargs) -> bool

delete_node(node_id: int) -> bool

get_node_list() -> List[Node]                 # Lista ordinata per ID

# Edges
add_edge(node1_id: int, node2_id: int,
         edge_type: EdgeType = EdgeType.FREE) -> Optional[int]

delete_edge(edge_id: int) -> bool

# Utility
get_levels() -> List[str]                      # Livelli unici ordinati

get_nodes_by_level(level: str) -> List[Node]

get_bounds() -> Optional[Dict[str, float]]     # x_min, x_max, y_min, y_max, z_min, z_max

clear() -> None                                # Cancella tutto

# Undo/Redo
execute_command(command: Command) -> Any       # Esegui con undo

undo() -> bool                                 # Annulla

redo() -> bool                                 # Ripristina

can_undo() -> bool

can_redo() -> bool

clear_undo_history() -> None

# Serializzazione
to_dict() -> Dict[str, Any]

from_dict(data: Dict[str, Any]) -> None
```

---

## Enumerazioni

### TopologyRole

**Valori:**
```python
class TopologyRole(Enum):
    CENTER = "center"              # Nodo centrale
    CORNER = "corner"              # Nodo angolo
    EDGE_MIDPOINT = "edge"         # Punto medio lato
    FREE = "free"                  # Nodo libero (default)
```

**Utilizzo:**
```python
node.topology_role = TopologyRole.CORNER
role_str = node.topology_role.value  # "corner"
role_enum = TopologyRole("corner")   # Da stringa
```

### EdgeType

**Valori:**
```python
class EdgeType(Enum):
    HORIZONTAL = "horizontal"      # Edge orizzontale
    VERTICAL = "vertical"          # Edge verticale
    DIAGONAL = "diagonal"          # Edge diagonale
    FREE = "free"                  # Edge libero (default)
```

### Direction

**Valori:**
```python
class Direction(Enum):
    NORTH = "north"                # Nord (Y+)
    SOUTH = "south"                # Sud (Y-)
    EAST = "east"                  # Est (X+)
    WEST = "west"                  # Ovest (X-)
    NONE = "none"                  # Nessuna direzione
```

---

## Strutture JSON

### Progetto Completo

**Schema JSON v6.0:**
```typescript
{
  "version": string,                    // "6.0"

  "metadata": {
    "author": string,
    "registration": string,
    "project_type": string,
    "created": string,                  // ISO 8601 datetime
    "modified": string,                 // ISO 8601 datetime
    "project_name": string,
    "location": string,
    "notes": string
  },

  "nodes": [
    {
      "id": number,                     // >= 1
      "x": number,                      // float, 4 decimali
      "y": number,                      // float, 4 decimali
      "z": number,                      // float, 3 decimali
      "description": string,
      "level": string,
      "topology_role": "free" | "center" | "corner" | "edge",
      "snap_radius": number,            // float, default 0.15
      "color": string                   // "#RRGGBB"
    }
  ],

  "edges": [
    {
      "id": number,                     // >= 1
      "node1_id": number,               // FK to nodes[].id
      "node2_id": number,               // FK to nodes[].id
      "edge_type": "free" | "horizontal" | "vertical" | "diagonal",
      "color": string,                  // "#RRGGBB"
      "width": number                   // int, pixel
    }
  ],

  "annotations": [
    {
      "type": "line" | "dimension",
      "node1_id": number,               // FK to nodes[].id
      "node2_id": number,               // FK to nodes[].id
      "color": string,
      "linewidth": number,

      // LineAnnotation
      "style"?: "solid" | "dashed" | "dotted",

      // DimensionAnnotation
      "offset"?: number,                // float, metri
      "show_text"?: boolean
    }
  ],

  "next_node_id": number,               // >= 1
  "next_edge_id": number                // >= 1
}
```

**Esempio Completo:**
```json
{
  "version": "6.0",
  "metadata": {
    "author": "Arch. Michelangelo Bartolotta",
    "registration": "Ordine Architetti Agrigento n. 1557",
    "project_type": "Coordinate Fili Fissi",
    "created": "2025-11-15T10:00:00",
    "modified": "2025-11-15T12:30:00",
    "project_name": "Edificio Residenziale A",
    "location": "Via Roma 123, Agrigento",
    "notes": "Piano terra - configurazione iniziale"
  },
  "nodes": [
    {
      "id": 1,
      "x": 0.0,
      "y": 0.0,
      "z": 0.0,
      "description": "Origine",
      "level": "PT",
      "topology_role": "corner",
      "snap_radius": 0.15,
      "color": "#6496c8"
    },
    {
      "id": 2,
      "x": 10.0,
      "y": 0.0,
      "z": 0.0,
      "description": "Pilastro A1",
      "level": "PT",
      "topology_role": "free",
      "snap_radius": 0.15,
      "color": "#6496c8"
    },
    {
      "id": 3,
      "x": 10.0,
      "y": 8.0,
      "z": 0.0,
      "description": "Pilastro A2",
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
      "edge_type": "horizontal",
      "color": "#505050",
      "width": 2
    },
    {
      "id": 2,
      "node1_id": 2,
      "node2_id": 3,
      "edge_type": "vertical",
      "color": "#505050",
      "width": 2
    }
  ],
  "annotations": [
    {
      "type": "dimension",
      "node1_id": 1,
      "node2_id": 2,
      "offset": 0.5,
      "color": "blue",
      "show_text": true
    }
  ],
  "next_node_id": 4,
  "next_edge_id": 3
}
```

---

## Formati Import/Export

### CSV (Coordinate)

**Formato Input:**
```csv
ID,X,Y,Z,Livello,Descrizione
1,0.0,0.0,0.0,PT,Origine
2,10.0,0.0,0.0,PT,Pilastro A1
3,10.0,8.0,0.0,PT,Pilastro A2
```

**Specifiche:**
- Header obbligatorio
- Separatore: virgola (`,`)
- Encoding: UTF-8
- Decimali: punto (`.`)
- ID opzionale (auto-generato se omesso)

### Excel (.xlsx)

**Struttura Foglio "Coordinate":**

| ID | X (m) | Y (m) | Z (m) | Livello | Descrizione |
|----|-------|-------|-------|---------|-------------|
| 1  | 0.0   | 0.0   | 0.0   | PT      | Origine     |
| 2  | 10.0  | 0.0   | 0.0   | PT      | Pilastro A1 |

**Stili:**
- Header: Font bold, background blu chiaro
- Coordinate: formato numerico 4 decimali
- Livello: testo centrato
- Descrizione: testo allineato a sinistra

### DXF (AutoCAD)

**Entità Supportate:**

**POINT:**
```
0
POINT
8
LAYER_NAME
10
X_COORDINATE
20
Y_COORDINATE
30
Z_COORDINATE
```

**TEXT:**
```
0
TEXT
8
LAYER_NAME
10
X_POSITION
20
Y_POSITION
30
Z_POSITION
1
TEXT_CONTENT
```

**Mapping:**
- Layer (group 8) → Node.level
- X (group 10) → Node.x
- Y (group 20) → Node.y
- Z (group 30) → Node.z
- TEXT content (group 1) → Node.description

---

## Command Pattern Types

### Command Base Class

```python
class Command:
    """Classe base comandi undo/redo"""

    def execute(self, model: UnifiedModel) -> Any:
        """Esegue comando, ritorna risultato"""
        raise NotImplementedError

    def undo(self, model: UnifiedModel) -> None:
        """Annulla comando"""
        raise NotImplementedError
```

### CreateNodeCommand

**Input:**
```python
CreateNodeCommand(
    x: float,                          # Coordinata X
    y: float,                          # Coordinata Y
    z: float = 0.0,                    # Coordinata Z (opzionale)
    description: str = "",             # Descrizione (opzionale)
    level: str = "",                   # Livello (opzionale)
    topology_role: TopologyRole = TopologyRole.FREE
)
```

**Output:**
```python
execute(model) -> int                  # Ritorna node_id creato
```

**Stato Salvato:**
```python
node_id: Optional[int]                 # ID nodo creato (per undo)
```

### UpdateNodeCommand

**Input:**
```python
UpdateNodeCommand(
    node_id: int,                      # ID nodo da modificare
    **kwargs                           # Campi da aggiornare
                                       # es: x=10.5, description="Nuovo"
)
```

**Output:**
```python
execute(model) -> bool                 # True se successo
```

**Stato Salvato:**
```python
old_values: Dict[str, Any]             # Valori originali (per undo)
```

### DeleteNodeCommand

**Input:**
```python
DeleteNodeCommand(
    node_id: int                       # ID nodo da eliminare
)
```

**Output:**
```python
execute(model) -> bool                 # True se successo
```

**Stato Salvato:**
```python
saved_node: Optional[Dict]             # Dati nodo (per undo)
saved_edges: List[Dict]                # Edges connessi (per undo)
```

### CreateEdgeCommand

**Input:**
```python
CreateEdgeCommand(
    node1_id: int,                     # ID primo nodo
    node2_id: int,                     # ID secondo nodo
    edge_type: EdgeType = EdgeType.FREE
)
```

**Output:**
```python
execute(model) -> Optional[int]        # Ritorna edge_id o None
```

**Stato Salvato:**
```python
edge_id: Optional[int]                 # ID edge creato (per undo)
```

### DeleteEdgeCommand

**Input:**
```python
DeleteEdgeCommand(
    edge_id: int                       # ID edge da eliminare
)
```

**Output:**
```python
execute(model) -> bool                 # True se successo
```

**Stato Salvato:**
```python
saved_edge: Optional[Dict]             # Dati edge (per undo)
```

---

## Qt Signal Types

### CoordinateInputPanel

```python
node_added = pyqtSignal(int)           # Emesso quando aggiunto nodo
                                       # Parametro: node_id
```

### CoordinateTable

```python
data_changed = pyqtSignal()            # Emesso quando dati modificati
                                       # Nessun parametro
```

### WireCanvasView

```python
selection_changed = pyqtSignal(int, str)  # Emesso quando selezione cambia
                                          # Parametri:
                                          #   node_id: int (o -1 se nessuno)
                                          #   sel_type: str ('node'|'edge'|'none')
```

---

## Validazione Dati

### Constraint Validations

**Node:**
```python
# ID
assert node.id >= 1, "ID deve essere >= 1"

# Coordinate
assert -10000 <= node.x <= 10000, "X fuori range"
assert -10000 <= node.y <= 10000, "Y fuori range"
assert -1000 <= node.z <= 1000, "Z fuori range"

# Snap radius
assert node.snap_radius > 0, "Snap radius deve essere positivo"

# Topology role
assert node.topology_role in TopologyRole, "Topology role non valido"
```

**Edge:**
```python
# ID
assert edge.id >= 1, "ID deve essere >= 1"

# Nodi
assert edge.node1_id in model.nodes, "node1_id non esiste"
assert edge.node2_id in model.nodes, "node2_id non esiste"
assert edge.node1_id != edge.node2_id, "Self-loop non permesso"

# Edge type
assert edge.edge_type in EdgeType, "Edge type non valido"

# Width
assert edge.width > 0, "Width deve essere positivo"
```

### Data Integrity

**Referential Integrity:**
- Ogni `Edge.node1_id` deve esistere in `UnifiedModel.nodes`
- Ogni `Edge.node2_id` deve esistere in `UnifiedModel.nodes`
- Ogni `Annotation.node1_id` deve esistere in `UnifiedModel.nodes`
- Ogni `Annotation.node2_id` deve esistere in `UnifiedModel.nodes`

**Uniqueness:**
- `Node.id` univoco in `UnifiedModel.nodes`
- `Edge.id` univoco in `UnifiedModel.edges`
- No edge duplicati tra stessa coppia di nodi

**Cascading Delete:**
- Eliminazione `Node` → elimina tutti `Edge` connessi
- Eliminazione `Node` → elimina tutte `Annotation` connesse

---

## Type Hints Summary

```python
# Primitivi
NodeID = int
EdgeID = int
Coordinate = float          # Metri
PixelSize = int
ColorHex = str              # "#RRGGBB"
ISODateTime = str           # "2025-11-15T12:30:00"

# Collections
NodeDict = Dict[int, Node]
EdgeDict = Dict[int, Edge]
AnnotationList = List[Annotation]
MetadataDict = Dict[str, Any]

# Optional Returns
OptionalNodeID = Optional[int]
OptionalEdgeID = Optional[int]
OptionalNode = Optional[Node]
OptionalBounds = Optional[Dict[str, float]]

# Callbacks
NodeCallback = Callable[[int], None]
DataCallback = Callable[[], None]
SelectionCallback = Callable[[int, str], None]

# Command Results
CommandResult = Any             # Tipo dipende dal comando specifico
UndoResult = bool
RedoResult = bool
```

---

## Best Practices

### Input Validation

1. **Sempre validare input utente:**
   ```python
   try:
       x = float(input_text)
       if not -10000 <= x <= 10000:
           raise ValueError("X fuori range")
   except ValueError as e:
       show_error(f"Input non valido: {e}")
   ```

2. **Usa Command pattern per operazioni modificanti:**
   ```python
   # ✓ Corretto
   cmd = CreateNodeCommand(x, y, z, desc, level)
   node_id = model.execute_command(cmd)

   # ✗ Errato (bypassa undo/redo)
   node_id = model.add_node(x, y, z, desc, level)
   ```

3. **Serializza con gestione errori:**
   ```python
   try:
       with open(filename, 'w') as f:
           json.dump(model.to_dict(), f, indent=2, ensure_ascii=False)
   except Exception as e:
       show_error(f"Errore salvataggio: {e}")
   ```

### Type Checking

Usare type hints per auto-completamento e validazione:

```python
from typing import Dict, List, Optional, Any

def process_nodes(nodes: Dict[int, Node]) -> List[Node]:
    """Process nodes and return sorted list"""
    return sorted(nodes.values(), key=lambda n: n.id)

def find_node(model: UnifiedModel, node_id: int) -> Optional[Node]:
    """Find node by ID, returns None if not found"""
    return model.nodes.get(node_id)
```

---

## Versioning

**Formato Versione:** `major.minor.patch-status`

- **major**: 6 (architettura unificata)
- **minor**: 0 (prima release unificata)
- **patch**: incrementale per bugfix
- **status**: `alpha` | `beta` | `rc` | (empty for stable)

**Compatibilità JSON:**
- v6.0 può leggere file v5.x (wire_editor.py) tramite conversione
- v6.0 può leggere file v2.x (wire_editor1.py) tramite conversione
- Retro-compatibilità garantita per minor versions (v6.1 legge v6.0)

**Schema Version Field:**
```json
{
  "version": "6.0",
  "metadata": { ... },
  "nodes": [ ... ]
}
```

---

## Changelog Data Types

### v6.0 (2025-11-15)
- ✅ Node unificato (combina Point + Node)
- ✅ Edge con EdgeType enum
- ✅ Annotation base + LineAnnotation + DimensionAnnotation
- ✅ UnifiedModel con undo/redo
- ✅ Command pattern types
- ✅ Qt signal types
- ✅ JSON schema v6.0

### Predecessori
- **v5.x (wire_editor.py)**: Point, CoordinateModel
- **v2.x (wire_editor1.py)**: Node dict, Edge dict, WireEditor

---

**Documento:** DATA_TYPES_DOCUMENTATION.md
**Versione:** 1.0
**Data:** 2025-11-15
**Autore:** Arch. Michelangelo Bartolotta - Ordine Architetti Agrigento n. 1557
