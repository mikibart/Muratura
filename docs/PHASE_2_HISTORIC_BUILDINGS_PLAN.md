# Muratura FEM - Fase 2: Edifici Storici
## Piano di Implementazione v6.4

**Status**: In pianificazione
**Data**: 2025-11-14
**Prerequisiti**: Fase 1 completata ✅ (solai, balconi, scale)

---

## 🎯 Obiettivi Fase 2

### Obiettivo Principale
Implementare funzionalità avanzate per l'**analisi e verifica di edifici storici in muratura**, colmando il gap con software specializzati come Aedes.SAV, Histra, e moduli storici di 3Muri/CDSWin.

### Target Market
- 🏛️ **Patrimonio storico italiano** (~30% mercato professionale)
- 🏰 **Restauro e consolidamento** edifici vincolati
- 📜 **Progettazione interventi** su edifici esistenti protetti
- 🔍 **Valutazione vulnerabilità sismica** centri storici

### Competitori da Analizzare
- **Aedes.SAV** - Analisi limite archi, volte, ponti
- **Histra Arches And Vaults** - DMEM approach (Discrete Macro-Element Model)
- **3Muri Project** - Modulo edifici storici (archi, volte, pilastri)
- **Mapei Structural Design** - Rinforzi FRP/FRCM
- **LimitState:RING** - Software specializzato analisi limite archi/volte

---

## 📚 Background Tecnico

### 1. Analisi Limite per Archi e Volte

#### Teoria di Heyman (1966-1982)
**Assunzioni fondamentali** ("The Stone Skeleton"):
1. **No tensile strength**: La muratura NON resiste a trazione (σ_t = 0)
2. **Infinite compressive strength**: Resistenza a compressione infinita (semplificazione conservativa)
3. **No sliding**: Attrito sufficiente a impedire scorrimento tra conci

**Teorema Statico** (Safe Theorem):
> Se esiste UNA linea delle pressioni contenuta nello spessore dell'arco,
> allora l'arco è in equilibrio sotto i carichi applicati.

**Teorema Cinematico** (Kinematic Theorem):
> Il carico di collasso è il minimo tra tutti i possibili cinematismi di collasso
> (formazione di 4 cerniere per arco circolare → meccanismo).

**Applicazioni**:
- Calcolo del **coefficiente di sicurezza geometrico** (h_min / h_actual)
- Determinazione **thrust line** (linea delle spinte)
- Identificazione **punti critici** (formazione cerniere plastiche)
- Valutazione **capacità sismica** (metodo dei cinematismi)

#### Metodo DMEM (Discrete Macro-Element Model)
Sviluppato da Università di Genova (Lagomarsino, Cattari, 2015)

**Caratteristiche**:
- Discretizzazione arco/volta in **macro-elementi rigidi**
- Interfacce con **comportamento non-lineare** (apertura/compressione)
- Consente **analisi pushover** non-lineare
- Modella **danneggiamento progressivo**

**Vantaggi**:
- Più accurato di analisi limite pura
- Considera deformabilità (assente in Heyman)
- Calibrabile su prove sperimentali
- Integrato in software commerciali (Histra)

#### FEM Non-Lineare
Approccio più sofisticato:
- Elementi finiti con **costitutivo non-lineare** (no-tension material)
- Criteri di rottura: **Mohr-Coulomb** con tensione nulla
- Richiede **mesh raffinata** e **solver robusto**
- Computazionalmente costoso

**Scelta per Muratura FEM**:
Implementare **Analisi Limite metodo Heyman** come approccio primario (veloce, robusto, conservativo) + indicazioni per approccio DMEM come sviluppo futuro.

---

### 2. Tipologie Strutturali Storiche

#### 2.1 Archi

**Tipologie geometriche**:
- **Arco a tutto sesto** (semicircolare) - Romano/Romanico
- **Arco ribassato** (ellittico, tre-centri) - Rinascimento
- **Arco acuto/ogivale** - Gotico
- **Arco rampante** - Strutture di contrasto laterale

**Parametri geometrici**:
- Luce (span) L
- Freccia (rise) f
- Spessore (thickness) t
- Raggio di curvatura R (per arco circolare)

**Failure modes**:
1. **Four-hinge mechanism**: 4 cerniere plastiche (tipico)
2. **Crushing**: Schiacciamento muratura (raro, se assunzione 2 Heyman valida)
3. **Sliding**: Scorrimento conci (raro se giunto asciutto ben vincolato)

#### 2.2 Volte

**Tipologie architettoniche**:
- **Volta a botte** (barrel vault): Estrusione arco semicircolare
- **Volta a crociera** (cross vault): Intersezione 2 volte a botte ortogonali
- **Volta a padiglione** (cloister vault): 4 spicchi convergenti
- **Cupola** (dome): Rivoluzione arco semicircolare
- **Volta a vela**: Porzione sferica su base quadrata

**Complessità analisi**:
- Volta a botte → analisi 2D semplificata (come arco per sezione)
- Volta a crociera → analisi 3D (effetto membranale)
- Cupola → analisi assialsimmetrica (Poleni, 1748 - San Pietro)

**Meccanismi di collasso**:
- Fessurazioni meridiane (cupole)
- Separazione spicchi (volte a crociera)
- Collasso localizzato chiave (volte sottili)

#### 2.3 Pilastri e Torri

**Problematiche specifiche**:
- **Snellezza**: Verifica stabilità (NTC §4.5.6.2)
- **Eccentricità carichi**: Da archi/volte convergenti
- **Tensioni di taglio**: Azioni sismiche orizzontali
- **Fuori piombo**: Edifici storici spesso inclinati

---

### 3. Rinforzi e Consolidamento

#### 3.1 Materiali Innovativi

**FRP (Fiber Reinforced Polymers)**:
- Fibre: Carbonio (CFRP), Vetro (GFRP), Basalto (BFRP)
- Matrice: Epossidica
- Applicazione: Laminazione esterna
- Vantaggi: Alta resistenza, basso peso, durabilità
- Svantaggi: Costo, reversibilità limitata, incompatibilità termica

**FRCM (Fiber Reinforced Cementitious Matrix)**:
- Fibre: Carbonio, Vetro, PBO, Basalto
- Matrice: Malta cementizia/pozzolanica
- Vantaggi: Traspirabilità, compatibilità muratura, reversibilità
- Normativa: Linee Guida CNR-DT 215/2018

**CRM (Composite Reinforced Mortar)**:
- Rete in fibra di vetro/carbonio + malta
- Simile a FRCM, normativa CNR-DT 200

#### 3.2 Tecniche Tradizionali

**Tirantature metalliche**:
- Barre/catene acciaio (diametro 16-30mm)
- Ancoraggi: capichiave, piastre
- Pre-tensionamento: contrasto spinte archi/volte

**Cuciture attive**:
- Perforazioni armate (ϕ 24-32mm)
- Iniezioni di malta cementizia/calce
- Ripristino continuità muraria

**Cordoli e cerchiature**:
- Cordoli sommitali in c.a. o acciaio
- Cerchiature perimetrali (riduzione spinte orizzontali)

---

### 4. Livelli di Conoscenza (Knowledge Levels)

#### Normativa NTC 2018 §C8.5.4

**LC1 - Conoscenza Limitata**:
- Requisiti:
  - Geometria: Da rilievo visivo
  - Dettagli costruttivi: Limitate verifiche in situ
  - Proprietà materiali: Valori da letteratura, limitate prove
- **FC (Confidence Factor)**: 1.35
- Applicabilità: Interventi locali, non incremento carico

**LC2 - Conoscenza Adeguata**:
- Requisiti:
  - Geometria: Rilievo completo
  - Dettagli costruttivi: Estese verifiche in situ
  - Proprietà materiali: Estese prove in situ o in lab
- **FC**: 1.20
- Applicabilità: Maggioranza interventi di miglioramento

**LC3 - Conoscenza Accurata**:
- Requisiti:
  - Geometria: Rilievo completo e dettagliato
  - Dettagli costruttivi: Esaustive verifiche in situ, saggi
  - Proprietà materiali: Esaustive prove in situ e in lab
- **FC**: 1.00
- Applicabilità: Interventi di adeguamento sismico

**Implementazione software**:
- Input: Tipo di indagini eseguite (rilievo, prove, saggi)
- Output: Livello conoscenza automatico + FC
- Applicazione FC: Riduzione resistenze materiali (f_d = f_k / (γ_M × FC))

---

## 🗺️ Piano di Implementazione

### Modulo 1: Archi (Arches) - Priority 🔴 ALTA

**File**: `Material/analyses/historic/arches.py`

**Classi**:
```python
class ArchGeometry:
    """Geometria arco (circolare, ellittico, ogivale)"""
    span: float  # Luce [m]
    rise: float  # Freccia [m]
    thickness: float  # Spessore [m]
    arch_type: Literal['semicircular', 'pointed', 'elliptical', 'flat']

class ArchAnalysis:
    """Analisi limite arco metodo Heyman"""

    def calculate_thrust_line(self, loads):
        """Calcola linea delle pressioni"""

    def find_minimum_thickness(self):
        """Teorema statico: t_min per equilibrio"""

    def calculate_collapse_mechanism(self):
        """Teorema cinematico: carico collasso, 4 cerniere"""

    def geometric_safety_factor(self):
        """FS = t_actual / t_min"""

    def seismic_capacity(self, ag):
        """Capacità sismica metodo cinematismi"""
```

**Features**:
- ✅ Calcolo linea delle pressioni (funicular polygon)
- ✅ Spessore minimo per equilibrio
- ✅ Identificazione punti formazione cerniere
- ✅ Coefficiente sicurezza geometrico
- ✅ Analisi cinematica per sisma
- ✅ Visualizzazione grafica thrust line

**Effort stimato**: 4 settimane

---

### Modulo 2: Volte (Vaults) - Priority 🟡 MEDIA

**File**: `Material/analyses/historic/vaults.py`

**Classi**:
```python
class VaultGeometry:
    """Geometria volta"""
    vault_type: Literal['barrel', 'cross', 'dome', 'cloister']
    span_x: float
    span_y: float  # Per volte a crociera
    rise: float
    thickness: float

class VaultAnalysis:
    """Analisi volte"""

    def analyze_barrel_vault(self):
        """Volta a botte: analisi come arco per sezione"""

    def analyze_dome_meridian(self):
        """Cupola: analisi meridiano (Poleni)"""

    def estimate_3d_capacity(self):
        """Stima capacità 3D (semplificato)"""
```

**Effort stimato**: 3 settimane

---

### Modulo 3: Rinforzi (Strengthening) - Priority 🟡 MEDIA

**File**: `Material/analyses/strengthening/__init__.py`

**Classi**:
```python
class FRPReinforcement:
    """Dimensionamento rinforzi FRP/FRCM"""

    def design_frp_strips(self, element, deficiency):
        """Dimensiona strisce FRP per deficit resistenza"""

    def verify_debonding(self):
        """Verifica delaminazione (CNR-DT 200)"""

    def verify_anchorage(self):
        """Verifica ancoraggio terminale"""

class TieRodDesign:
    """Dimensionamento tiranti metallici"""

    def calculate_required_tension(self, thrust):
        """Calcola trazione richiesta per contrasto spinta"""

    def design_anchorage(self):
        """Dimensiona ancoraggi (capichiave, piastre)"""
```

**Effort stimato**: 3 settimane

---

### Modulo 4: Knowledge Levels - Priority 🟢 BASSA

**File**: `Material/codes/ntc2018/knowledge.py`

**Implementazione**:
```python
class KnowledgeLevel:
    """Gestione livelli conoscenza NTC §C8.5.4"""

    LC1 = KnowledgeLevelData(
        FC=1.35,
        requirements={
            'geometry': 'visual_survey',
            'details': 'limited_inspection',
            'materials': 'literature_values'
        }
    )

    def assess_level(self, investigations: Dict) -> str:
        """Valuta LC in base a indagini eseguite"""

    def apply_confidence_factor(self, fk: float, LC: str) -> float:
        """Applica FC: fd = fk / (γM × FC)"""
```

**Effort stimato**: 2 settimane

---

## 📊 Timeline e Milestones

### Sprint 1 (Settimane 1-4): Archi
- ✅ Implementazione ArchGeometry, ArchAnalysis
- ✅ Calcolo thrust line (algoritmo funicular)
- ✅ Analisi limite (teoremi statico/cinematico)
- ✅ Test suite (15+ test cases)
- ✅ Esempio: Ponte romano, Arco gotico

**Deliverable**: Modulo archi production-ready

### Sprint 2 (Settimane 5-7): Volte
- ✅ Implementazione VaultGeometry, VaultAnalysis
- ✅ Analisi volta a botte (2D)
- ✅ Analisi cupola (Poleni)
- ✅ Esempio: Cupola Brunelleschi (semplificato)

**Deliverable**: Modulo volte funzionante

### Sprint 3 (Settimane 8-10): Rinforzi
- ✅ FRP/FRCM design secondo CNR-DT
- ✅ Tiranti metallici
- ✅ Esempio: Consolidamento arco lesionato

**Deliverable**: Modulo rinforzi completo

### Sprint 4 (Settimane 11-12): Knowledge Levels + Integrazione
- ✅ Sistema LC1/LC2/LC3
- ✅ Integrazione con moduli esistenti
- ✅ Documentazione completa
- ✅ Release v6.4

**Deliverable**: Fase 2 completata

**Timeline totale**: 12 settimane (~3 mesi)

---

## 📖 Bibliografia e Riferimenti

### Testi Fondamentali

1. **Heyman, J. (1966)**
   "The stone skeleton"
   International Journal of Solids and Structures
   → Base teorica analisi limite

2. **Heyman, J. (1982)**
   "The Masonry Arch"
   Ellis Horwood, Chichester
   → Trattazione completa archi

3. **Huerta, S. (2001)**
   "Mechanics of masonry vaults: The equilibrium approach"
   Historical Constructions, Guimarães
   → Estensione metodo Heyman a volte

4. **Lagomarsino, S., Cattari, S. (2015)**
   "PERPETUATE guidelines for seismic performance-based assessment of cultural heritage masonry structures"
   Bulletin of Earthquake Engineering
   → DMEM e approcci moderni

5. **Poleni, G. (1748)**
   "Memorie istoriche della gran cupola del Tempio Vaticano"
   → Analisi storica cupola San Pietro (primo uso analisi limite)

### Normativa Tecnica

6. **NTC 2018**
   Capitolo 8 - Costruzioni esistenti
   §C8.5.4 - Livelli di conoscenza

7. **CNR-DT 200 R1/2013**
   "Istruzioni per la Progettazione, l'Esecuzione ed il Controllo di Interventi di Consolidamento Statico mediante l'utilizzo di Compositi Fibrorinforzati"

8. **CNR-DT 215/2018**
   "Istruzioni per la Progettazione, l'Esecuzione ed il Controllo di Interventi di Consolidamento Statico mediante l'utilizzo di Compositi Fibrorinforzati a Matrice Inorganica"

### Software di Riferimento

9. **LimitState:RING**
   https://www.limitstate.com/ring
   → Software commerciale specializzato analisi limite

10. **Aedes.SAV**
    https://www.aedes.it/sav
    → Modulo professionale italiano

---

## 🎯 Success Criteria

### Criteri Tecnici
- [ ] Implementazione conforme a teoria Heyman
- [ ] Validazione su casi test letteratura
- [ ] Accuratezza ±10% vs software commerciali
- [ ] Performance: analisi arco < 1 secondo

### Criteri Business
- [ ] Copertura 80% casi d'uso edifici storici
- [ ] Documentazione completa per professionisti
- [ ] Esempi pratici (≥5) su edifici reali
- [ ] Conformità normativa NTC 2018 Cap. 8

### Criteri Qualità
- [ ] Test coverage ≥ 75%
- [ ] Zero errori critici
- [ ] Documentazione API completa
- [ ] Esempi eseguibili senza errori

---

## 💡 Note Implementative

### Sfide Tecniche Previste

1. **Calcolo linea delle pressioni**
   - Algoritmo: Funicular polygon (Culmann, 1866)
   - Librerie: NumPy per calcolo vettoriale
   - Validazione: Confronto con soluzioni analitiche

2. **Identificazione cerniere plastiche**
   - Metodo: Iterazione su posizioni possibili
   - Ottimizzazione: Minimizzazione carico collasso

3. **Visualizzazione risultati**
   - Matplotlib per grafici 2D thrust line
   - Possibile integrazione VTK per 3D (futuro)

### Decisioni Architetturali

- Separare `historic/` da moduli moderni (solai, balconi)
- Mantenere interfaccia coerente con moduli esistenti
- Permettere future estensioni (DMEM, FEM non-lineare)

---

## 📅 Next Steps Immediati

1. ✅ Completare questo documento di pianificazione
2. 🔄 Ricerca algoritmi funicular polygon (2-3 fonti)
3. 🔄 Implementare ArchGeometry class (base)
4. 🔄 Implementare calcolo thrust line (core algorithm)
5. 🔄 Test su arco semicircolare semplice (validazione)

---

**Documento creato**: 2025-11-14
**Ultima modifica**: 2025-11-14
**Autore**: Claude (Anthropic)
**Revisione**: v1.0
