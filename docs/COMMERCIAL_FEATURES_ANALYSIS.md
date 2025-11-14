# Analisi Funzionalità Software Commerciali - Muratura FEM

## 📊 Executive Summary

Analisi comparativa delle funzionalità presenti nei principali software commerciali italiani per il calcolo strutturale di murature secondo NTC 2018/2019.

**Data Analisi**: 2025-11-14
**Software Analizzati**: 3Muri Project, Aedes.PCM/SAV/ACM, CDSWin/CDMa Win, IperWall BIM, TRAVILOG, DomusWall

---

## 🎯 Software Commerciali - Panoramica

### 1. 3Muri Project (S.T.A. DATA)
**Leader di mercato** - Software più diffuso in Italia

**Funzionalità Distintive**:
- 🤖 **AI Assistant** - Assistente intelligente per modellazione
- 🏗️ **BIM Integration** - Import/export IFC, Revit
- 📐 **CAD Parametrico** - Modellazione grafica avanzata
- 🔄 **Analisi Dinamica Completa** - Modale, pushover, time-history
- 🧱 **Murature Miste** - Muratura + RC + Acciaio + Legno
- 🏛️ **Edifici Storici** - Archi, volte, pilastri
- 📊 **Relazioni Automatiche** - Generazione automatica relazioni di calcolo

### 2. Aedes.PCM / SAV / ACM (Aedes Software)
**Prima software house dedicata** (dal 1997)

**Funzionalità Distintive**:
- 🏗️ **Structural BIM** - Approccio BIM nativo
- 🔍 **Knowledge Levels** - Gestione completa LC1, LC2, LC3
- 🎚️ **Confidence Factors** - Calcolo automatico FC
- 🏛️ **Aedes.SAV** - Analisi limite archi, volte, ponti
- 🔧 **Aedes.ACM** - Rinforzi FRP, FRCM, CRM
- 📈 **Analisi Vulnerabilità** - Valutazione sismica edifici esistenti

### 3. CDSWin / CDMa Win (STS Software)
**Sistema Modulare Completo**

**Funzionalità Distintive**:
- 🧩 **Modulare** - Acquisto moduli separati
- 🔄 **Strutture Irregolari** - Analisi non-linearità geometrica
- 🌊 **Pushover Avanzato** - Curve multiple, ADRS
- 🏗️ **Strutture Miste** - Integrazione muratura/c.a./acciaio
- 📊 **Post-Processing** - Visualizzazione deformate 3D

### 4. IperWall BIM (Soft.Lab)
**Specializzato Muratura Esistente**

**Funzionalità Distintive**:
- 🎯 **Non-Linear Analysis** - Pushover con plasticità concentrata
- 📋 **NTC 2018 Compliant** - Verifica automatica normativa
- 🧱 **Irregular Masonry** - Murature irregolari/storiche
- 🔍 **Dettaglio Elementi** - Verifica maschi, fasce, nodi

---

## 🏗️ Funzionalità per Categoria

### A. SOLAI (Floors/Slabs)

#### Funzionalità Commercial Standard:
1. **Tipologie Supportate**:
   - Solai in latero-cemento (pignatte)
   - Solai prefabbricati (predalles)
   - Solai in legno (travi e tavolato)
   - Solai collaboranti con lamiera
   - Solai in acciaio (HEA, IPE)
   - Volte e volte a padiglione

2. **Calcolo e Verifica**:
   - Calcolo armature longitudinali e trasversali
   - Verifica SLU (flessione, taglio, punzonamento)
   - Verifica SLE (fessurazione, deformazione)
   - Verifica freccia istantanea e differita
   - Analisi carichi permanenti e accidentali
   - Integrazione sisma (diaframmi rigidi/flessibili)

3. **Features Specifici**:
   - Database pignatte commerciali (Porotherm, Alveolater, etc.)
   - Calcolo automatico peso proprio
   - Verifica aperture in solaio
   - Cordoli di piano integrati
   - Collegamento solaio-muratura

#### Software Specifici:
- **ANDILSolai** - Design prefabbricati
- **3Muri** - Diaframmi rigidi/flessibili
- **Aedes** - Solai storici in legno

**Status Muratura FEM**: ❌ **ASSENTE** - Nessun modulo solai

---

### B. BALCONI (Balconies)

#### Funzionalità Commercial Standard:
1. **Tipologie Supportate**:
   - Balconi in c.a. a sbalzo
   - Balconi in acciaio (HEA, IPE, UPN)
   - Balconi in pietra (storici)
   - Balconi prefabbricati

2. **Calcolo e Verifica**:
   - Verifica SLU sbalzo (flessione, taglio, torsione)
   - Verifica ancoraggi alla muratura
   - Verifica parapetti e ringhiere
   - Calcolo sovraccarichi (folle, neve, vento)
   - Verifica connessioni saldate/bullonate
   - Verifica corrosione (vita utile)

3. **Features Specifici**:
   - Calcolo mensole di supporto
   - Verifica inserimento in muratura
   - Dettagli costruttivi automatici

#### Software Specifici:
- **BCS Balconi** (Madosoft) - Specializzato
- **3Muri** - Balconi in muratura/c.a.

**Status Muratura FEM**: ❌ **ASSENTE** - Nessun modulo balconi

---

### C. SCALE (Stairs)

#### Funzionalità Commercial Standard:
1. **Tipologie Supportate**:
   - Scale in c.a. a soletta rampante
   - Scale a ginocchio
   - Scale a sbalzo
   - Scale in acciaio
   - Scale in legno
   - Scale in muratura (storiche)
   - Scale elicoidali

2. **Calcolo e Verifica**:
   - Calcolo geometrico (alzata, pedata, pendenza)
   - Verifica SLU rampa (flessione, taglio)
   - Verifica pianerottoli
   - Calcolo armature longitudinali e trasversali
   - Verifica SLE (fessurazione, deformazione)
   - Verifica sismica (forze orizzontali)

3. **Features Specifici**:
   - Input grafico geometria scala
   - Calcolo automatico gradini
   - Vincoli variabili (incastro, appoggio, sbalzo)
   - Tavole esecutive automatiche

#### Software Specifici:
- **TRAVILOG Scale** - Modulo dedicato
- **CDSWin** - Scale multiple tipologie

**Status Muratura FEM**: ❌ **ASSENTE** - Nessun modulo scale

---

### D. EDIFICI STORICI (Historic Buildings)

#### Funzionalità Commercial Standard:
1. **Elementi Strutturali**:
   - Archi (tutto sesto, ribassati, ogivali)
   - Volte a botte, a crociera, a padiglione
   - Cupole e tamburi
   - Pilastri e colonne in muratura
   - Torri e campanili
   - Contrafforti

2. **Metodi di Analisi**:
   - **Analisi Limite** - Cinematismi di collasso
   - **DMEM** (Discrete Macro-Element Model)
   - **FEM Non-Lineare** - Plasticità diffusa
   - **Analisi Storica** - Metodi classici (Heyman)

3. **Rinforzi e Consolidamento**:
   - FRP (Fiber Reinforced Polymers)
   - FRCM (Fiber Reinforced Cementitious Matrix)
   - CRM (Composite Reinforced Mortar)
   - Tirantature metalliche
   - Cordoli e cerchiature
   - Cuciture attive

#### Software Specifici:
- **Aedes.SAV** - Archi e volte
- **Histra Arches And Vaults** - DMEM approach
- **Mapei Structural Design** - FRP/FRCM
- **Aedes.ACM** - Rinforzi compositi

**Status Muratura FEM**: ⚠️ **PARZIALE** - Solo 24 cinematismi, no archi/volte

---

### E. BIM E INTEGRAZIONE CAD

#### Funzionalità Commercial Standard:
1. **Import/Export**:
   - IFC 2x3, IFC 4
   - Revit (via plugin)
   - AutoCAD DWG/DXF
   - Allplan, ArchiCAD

2. **Modellazione Grafica**:
   - Input CAD 2D/3D interattivo
   - Snap geometrici
   - Layer e gruppi
   - Viste 3D navigabili
   - Rendering elementi strutturali

3. **Interoperabilità**:
   - Collegamento architettonico-strutturale
   - Aggiornamento modello da BIM
   - Export disegni esecutivi

**Status Muratura FEM**: ❌ **ASSENTE** - Solo input dati alfanumerico

---

### F. ANALISI AVANZATE

#### Funzionalità Commercial Standard:
1. **Analisi Dinamica**:
   - Analisi modale con massa partecipante
   - Analisi spettro di risposta (NTC 2018)
   - Analisi time-history (accelerogrammi)
   - Analisi pushover (pattern multipli)
   - Analisi dinamica incrementale (IDA)

2. **Non-Linearità**:
   - Materiale (plasticità, softening)
   - Geometrica (P-Δ, grandi spostamenti)
   - Contatto (unilateralità, apertura giunti)

3. **Soil-Structure Interaction**:
   - Molle alla Winkler
   - Analisi fondazioni
   - Liquefazione terreni

**Status Muratura FEM**: ✅ **PRESENTE** - Modale, pushover, time-history implementati

---

## 📊 Gap Analysis - Muratura FEM v6.1

### ✅ Funzionalità Presenti (Competitive)

| Funzionalità | Status | Note |
|-------------|--------|------|
| Analisi Modale | ✅ Completa | 7 metodi, massa partecipante |
| Analisi Pushover | ✅ Completa | Pattern multipli, curve capacità |
| Analisi Time-History | ✅ Completa | Newmark-β integration |
| SAM (Simplified) | ✅ Completa | Magenes-Calvi method |
| 24 Cinematismi | ✅ Completa | EC8/NTC2018 compliant |
| Telaio Equivalente | ✅ Completa | Mesh automatica |
| NTC 2018 Verification | ✅ Completa | Coefficienti sicurezza |
| Materiali NTC | ✅ Completa | Database parametri |

### ❌ Funzionalità Assenti (Critical Gaps)

| Funzionalità | Priorità | Impatto Business |
|-------------|----------|------------------|
| **Modulo Solai** | 🔴 CRITICA | ALTO - Essenziale per mercato italiano |
| **Modulo Balconi** | 🔴 CRITICA | ALTO - Richiesto in 80% progetti |
| **Modulo Scale** | 🟡 ALTA | MEDIO - Richiesto in 60% progetti |
| **Archi e Volte** | 🟡 ALTA | MEDIO - Edifici storici (30% mercato) |
| **BIM Integration** | 🟡 ALTA | ALTO - Standard di settore 2025 |
| **CAD Grafico** | 🟢 MEDIA | ALTO - UX migliorata |
| **Rinforzi FRP/FRCM** | 🟢 MEDIA | MEDIO - Consolidamento |
| **AI Assistant** | 🟢 BASSA | MEDIO - Differenziazione |

### ⚠️ Funzionalità Parziali (Needs Enhancement)

| Funzionalità | Status Attuale | Gap |
|-------------|---------------|-----|
| Strutture Miste | Parziale | No integrazione c.a./acciaio automatica |
| Knowledge Levels | Assente | No gestione LC1/LC2/LC3 |
| Confidence Factors | Assente | No calcolo automatico FC |
| Relazioni Calcolo | Assente | No export automatico report |
| Post-Processing | Basic | No 3D rendering, deformate animate |

---

## 🚀 Roadmap Integrazione Funzionalità

### FASE 1: CORE MISSING FEATURES (v6.2 - Q1 2025)
**Obiettivo**: Raggiungere feature parity base con commercial software

#### 1.1 Modulo Solai
**Priorità**: 🔴 CRITICA
**Effort**: 3-4 settimane
**Deliverables**:
```python
# Material/analyses/floors/__init__.py
class FloorAnalysis:
    """Analisi e verifica solai secondo NTC 2018"""

    def __init__(self, floor_type, geometry, materials, loads):
        # Tipologie: 'latero-cemento', 'wood', 'steel', 'precast'
        pass

    def calculate_reinforcement(self):
        """Calcolo armature longitudinali e trasversali"""
        # SLU: flessione, taglio
        return {'As_long': ..., 'As_trasv': ...}

    def verify_slu(self):
        """Verifica SLU (flessione, taglio, punzonamento)"""
        return {'flexure_ratio': ..., 'shear_ratio': ...}

    def verify_sle(self):
        """Verifica SLE (fessurazione, deformazione)"""
        return {'crack_width': ..., 'deflection': ...}

    def integrate_with_walls(self, wall_system):
        """Integrazione solaio-muratura (diaframma rigido/flessibile)"""
        pass
```

**Files to Create**:
- `Material/analyses/floors/__init__.py`
- `Material/analyses/floors/slab_types.py` (tipologie)
- `Material/analyses/floors/reinforcement.py` (armature)
- `Material/analyses/floors/verification.py` (verifiche)
- `Material/data/floor_database.yaml` (database pignatte)
- `tests/test_floors.py`
- `examples/04_floor_design.py`

#### 1.2 Modulo Balconi
**Priorità**: 🔴 CRITICA
**Effort**: 2-3 settimane
**Deliverables**:
```python
# Material/analyses/balconies/__init__.py
class BalconyAnalysis:
    """Analisi e verifica balconi secondo NTC 2018"""

    def __init__(self, balcony_type, cantilever_length, supports):
        # Tipologie: 'rc_cantilever', 'steel', 'stone'
        pass

    def calculate_moments_shear(self, loads):
        """Calcolo sollecitazioni a sbalzo"""
        return {'M_max': ..., 'V_max': ..., 'T': ...}

    def verify_cantilever(self):
        """Verifica resistenza sbalzo"""
        pass

    def verify_anchorage_to_wall(self, wall):
        """Verifica ancoraggio alla muratura"""
        pass
```

**Files to Create**:
- `Material/analyses/balconies/__init__.py`
- `Material/analyses/balconies/cantilever.py`
- `Material/analyses/balconies/anchorage.py`
- `tests/test_balconies.py`
- `examples/05_balcony_verification.py`

#### 1.3 Modulo Scale
**Priorità**: 🟡 ALTA
**Effort**: 3 settimane
**Deliverables**:
```python
# Material/analyses/stairs/__init__.py
class StairAnalysis:
    """Analisi e verifica scale secondo NTC 2018"""

    def __init__(self, stair_type, geometry, support_conditions):
        # Tipologie: 'slab_ramp', 'cantilever', 'steel', 'historic'
        pass

    def calculate_geometry(self, height, n_steps):
        """Calcolo geometrico (alzata, pedata, pendenza)"""
        return {'rise': ..., 'tread': ..., 'slope': ...}

    def calculate_loads(self):
        """Carichi permanenti + accidentali (Cat. C)"""
        pass

    def verify_ramp(self):
        """Verifica SLU rampa"""
        pass
```

**Files to Create**:
- `Material/analyses/stairs/__init__.py`
- `Material/analyses/stairs/geometry.py`
- `Material/analyses/stairs/ramp_verification.py`
- `tests/test_stairs.py`
- `examples/06_stair_design.py`

---

### FASE 2: HISTORIC BUILDINGS (v6.3 - Q2 2025)
**Obiettivo**: Penetrare mercato edifici storici

#### 2.1 Archi e Volte
**Effort**: 4 settimane
**Deliverables**:
```python
# Material/analyses/historic/arches.py
class ArchAnalysis:
    """Analisi archi con metodo analisi limite"""

    def __init__(self, arch_type, geometry, masonry):
        # Tipologie: 'semicircular', 'pointed', 'flat'
        pass

    def limit_analysis(self):
        """Analisi limite (teorema cinematico/statico)"""
        # Heyman assumptions: no tensile, infinite compression, no sliding
        return {'thrust_line': ..., 'safety_factor': ...}

    def seismic_capacity(self):
        """Capacità sismica con cinematismi"""
        pass

# Material/analyses/historic/vaults.py
class VaultAnalysis:
    """Analisi volte (botte, crociera, padiglione)"""
    pass
```

#### 2.2 Rinforzi e Consolidamento
**Effort**: 3 settimane
**Deliverables**:
```python
# Material/analyses/strengthening/__init__.py
class StrengtheningAnalysis:
    """Analisi rinforzi FRP, FRCM, CRM"""

    def design_frp_reinforcement(self, element, deficiency):
        """Dimensionamento rinforzo FRP"""
        pass

    def verify_debonding(self):
        """Verifica delaminazione"""
        pass
```

---

### FASE 3: BIM & ADVANCED FEATURES (v7.0 - Q3 2025)
**Obiettivo**: Raggiungere standard commerciale completo

#### 3.1 BIM Integration
**Effort**: 6 settimane
**Technologies**: IfcOpenShell, Revit API
**Deliverables**:
- Import IFC 2x3/4
- Export IFC structural
- Revit plugin (basic)

#### 3.2 Knowledge Levels & Confidence Factors
**Effort**: 2 settimane
**Deliverables**:
```python
# Material/codes/ntc2018/knowledge.py
class KnowledgeLevel:
    """Gestione Livelli di Conoscenza NTC 2018 C8.5.4"""

    LC1 = {'FC': 1.35, 'requirements': {...}}
    LC2 = {'FC': 1.20, 'requirements': {...}}
    LC3 = {'FC': 1.00, 'requirements': {...}}

    def assess_level(self, inspections, tests):
        """Valuta livello conoscenza acquisito"""
        pass
```

#### 3.3 Automatic Report Generation
**Effort**: 4 settimane
**Technologies**: Jinja2, LaTeX, Markdown
**Deliverables**:
- Template relazioni calcolo
- Export PDF/Word
- Grafici integrati

---

### FASE 4: UI/UX & AI (v8.0 - Q4 2025)
**Obiettivo**: Differenziazione competitiva

#### 4.1 CAD Grafico
**Effort**: 8 settimane
**Technologies**: PyQt/PySide, VTK/matplotlib
**Deliverables**:
- GUI desktop application
- Modellazione grafica 2D/3D
- Visualizzazione risultati interattiva

#### 4.2 AI Assistant
**Effort**: 6 settimane
**Technologies**: GPT-4 API, RAG
**Deliverables**:
- Assistente conversazionale
- Suggerimenti modellazione
- Interpretazione normativa

---

## 💰 Analisi Costi-Benefici

### Investimento Stimato per Fase

| Fase | Effort (settimane) | Costo Dev* | ROI Atteso |
|------|-------------------|------------|------------|
| Fase 1 (Solai/Balconi/Scale) | 8-10 | €20,000 | ALTO - Feature parity base |
| Fase 2 (Historic) | 7 | €15,000 | MEDIO - Mercato nicchia (30%) |
| Fase 3 (BIM/Advanced) | 12 | €28,000 | ALTO - Standard settore |
| Fase 4 (UI/AI) | 14 | €35,000 | MEDIO - Differenziazione |
| **TOTALE** | **41-43** | **€98,000** | - |

*Assumendo €2,000/settimana developer senior

### Market Positioning Post-Implementation

**Attuale (v6.1)**:
- Segmento: Academic/Research tool
- Competitors: N/A (open source)
- Market share: <1%

**Post Fase 1-2 (v6.3)**:
- Segmento: Professional alternative
- Competitors: 3Muri, Aedes, CDSWin
- Market share potenziale: 5-8%
- Pricing: €500-800/anno (vs €2,000-4,000 commercial)

**Post Fase 3-4 (v8.0)**:
- Segmento: Professional/Enterprise
- Market share potenziale: 15-20%
- Pricing: €1,200-1,500/anno

---

## 🎯 Raccomandazioni Strategiche

### Priorità Immediate (Next 3 Months)

1. **IMPLEMENTARE MODULO SOLAI** ← START HERE
   - Rationale: Essenziale per 95% progetti muratura italiani
   - Blocco attuale per adozione professionale
   - ROI immediato

2. **IMPLEMENTARE MODULO BALCONI**
   - Rationale: Richiesto in 80% progetti residenziali
   - Differenziatore vs. tool accademici

3. **CREARE ESEMPI COMPLETI**
   - Edificio residenziale completo (muratura + solai + scale)
   - Validazione vs. software commerciale

### Approccio Incrementale

```
v6.1 (ATTUALE) → v6.2 (Solai) → v6.3 (Balconi+Scale) → v6.4 (Archi) → v7.0 (BIM)
     ↓              ↓                ↓                    ↓              ↓
   Academic    Semi-Pro         Professional        Historic       Enterprise
```

### Quick Wins (1-2 settimane ciascuno)

1. ✅ Knowledge Levels & FC - Enum + calcolo automatico
2. ✅ Mixed Structures - Integrazione elementi RC/Steel
3. ✅ Report Export - Template base Markdown/PDF
4. ✅ Material Database - Ampliamento con materiali storici

---

## 📚 References

### Software Analyzed
- 3Muri Project: https://www.3muri.com
- Aedes Software: https://www.aedes.it
- CDSWin (STS): https://www.stsweb.it
- IperWall BIM: https://www.softlab.it
- TRAVILOG: https://www.logical.it

### Standards
- NTC 2018: D.M. 17 gennaio 2018
- Circolare NTC 2019: n. 7/2019
- Eurocode 8: EN 1998-1:2004

### Scientific Papers
- Magenes, G., & Calvi, G. M. (1997). In-plane seismic response of brick masonry walls
- Heyman, J. (1966). The stone skeleton - Structural analysis of masonry
- D'Ayala, D., & Speranza, E. (2003). Definition of collapse mechanisms

---

## 📝 Conclusion

Muratura FEM v6.1 ha un **eccellente core tecnico** (motore FEM, analisi avanzate) ma **gap critici** per mercato professionale italiano:

**MUST HAVE** (per adozione professionale):
- ✅ Solai (floors) - CRITICO
- ✅ Balconi (balconies) - CRITICO
- ✅ Scale (stairs) - IMPORTANTE

**NICE TO HAVE** (per competitività):
- Archi e volte (edifici storici)
- BIM integration
- CAD grafico
- AI assistant

**Raccomandazione**: Implementare FASE 1 (Solai+Balconi+Scale) nei prossimi 2-3 mesi per raggiungere feature parity base con commercial software e sbloccare adozione professionale.
