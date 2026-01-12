# PROGETTO MURATURA - UNIFORMAZIONE COMPLETA E STRESS TEST

## OBIETTIVO PRINCIPALE
Uniformare TUTTE le variabili, strutture dati ed enumerazioni del progetto muratura affinché i dati siano coerenti tra tutti i moduli. Eliminare duplicazioni, correggere inconsistenze e testare ogni modulo con stress test approfonditi.

## STRUTTURA PROGETTO
- **connector.py** - Interfaccia principale (1980 linee)
- **gui_editor.py** - GUI PyQt5 (2330 linee)
- **Material/dsl_parser.py** - Parser DSL (~1500 linee)
- **Material/engine.py** - Engine calcolo (1767 linee)
- **Material/materials.py** - Materiali NTC (~1800 linee)
- **Material/geometry.py** - Geometrie (~2200 linee)
- **Material/enums.py** - Enumerazioni (~300 linee)
- **Material/analyses/** - 7 moduli analisi (por, sam, fem, fiber, limit, micro, frame)

## INCONSISTENZE CRITICHE DA RISOLVERE

### IC1 - ALTA PRIORITA: Attributi Materiale
**Problema:** In dsl_parser.py e connector.py si cerca sia `masonry_type` che `material_type`, ma MaterialProperties definisce solo `masonry_type`.
**Azione:** Standardizzare a `masonry_type` ovunque. Rimuovere tutti i riferimenti a `material_type`.

### IC2 - ALTA PRIORITA: SAM Duplicato
**Problema:** sam.py e sam82.py sono identici (1962 linee ciascuno). sam72.py è legacy.
**Azione:**
1. Rimuovere sam82.py
2. Mantenere sam.py come versione principale v8.2
3. Rinominare sam72.py in sam_legacy.py o rimuoverlo se non usato
4. Aggiornare tutti gli import in engine.py e __init__.py

### IC3 - MEDIA PRIORITA: Naming Carichi
**Problema:** CaricoDef usa `permanente`, `variabile`. AnalysisOptions usa `gamma_m`, `FC`.
**Azione:** Documentare chiaramente la differenza. Aggiungere mapping in connector.py.

### IC4 - MEDIA PRIORITA: Conversione Geometrie
**Problema:** Non esiste conversione MuroDef -> GeometryPier.
**Azione:** Aggiungere factory method `GeometryPier.from_muro_def()` in geometry.py.

### IC5 - MEDIA PRIORITA: Alias Confuso gamma
**Problema:** In materials.py, `gamma` e alias di `weight` ma gamma normalmente indica coefficiente sicurezza.
**Azione:** Rinominare property `gamma` in `peso_specifico` o `unit_weight`.

### IC6 - BASSA PRIORITA: Cordoli Dict vs Dataclass
**Problema:** Cordoli gestiti sia come Dict che come CordoloDef.
**Azione:** Standardizzare tutto a CordoloDef dataclass. Aggiungere metodo `.to_dict()` se necessario.

### IC7 - BASSA PRIORITA: Enum LoadDistribution
**Problema:** POR usa `LoadDistribution.AREA`, SAM usa `LoadDistributionMethod.BY_AREA`.
**Azione:** Unificare in enums.py con un solo Enum `LoadDistribution` usato da tutti.

### IC8 - BASSA PRIORITA: DSLExporter
**Problema:** Verifica multipli attributi con hasattr.
**Azione:** Centralizzare accesso proprietà con metodi getter uniformi.

## PASSI OPERATIVI PER OGNI ITERAZIONE

### FASE 1: Analisi (Iterazioni 1-5)
1. Leggere ogni file Python del progetto
2. Catalogare TUTTE le variabili, classi, funzioni
3. Identificare naming inconsistenti
4. Documentare dipendenze tra moduli

### FASE 2: Uniformazione (Iterazioni 6-20)
1. Iniziare da enums.py - centralizzare TUTTE le enum
2. Uniformare materials.py - rimuovere alias confusi
3. Uniformare geometry.py - aggiungere factory methods
4. Uniformare dsl_parser.py - standardizzare dataclass
5. Uniformare connector.py - usare tipi uniformi
6. Uniformare engine.py - import corretti
7. Uniformare analyses/*.py - usare enum e tipi centralizzati

### FASE 3: Rimozione Duplicati (Iterazioni 21-25)
1. Rimuovere sam82.py (duplicato)
2. Gestire sam72.py (legacy)
3. Verificare nessun import rotto

### FASE 4: Test (Iterazioni 26-40)
Per OGNI modulo:
1. Creare script di test in `tests/` se non esiste
2. Testare con valori limite (0, negativi, molto grandi)
3. Testare con input malformati
4. Testare conversioni tra tipi
5. Testare tutte le analisi (POR, SAM, FEM, Fiber, Limit, Micro, Frame)
6. Verificare che DSL parsing funzioni
7. Verificare export DSL
8. Testare GUI (import senza errori)

### FASE 5: Validazione Finale (Iterazioni 41-50)
1. Eseguire tutti i test
2. Verificare nessun warning/errore
3. Testare esempio completo end-to-end
4. Documentare modifiche fatte

## CRITERI DI COMPLETAMENTO
Il progetto e COMPLETO quando:
1. TUTTE le enum sono in enums.py e usate uniformemente
2. NESSUN file duplicato (sam82.py rimosso)
3. TUTTI gli attributi hanno nomi consistenti (masonry_type, non material_type)
4. TUTTE le strutture dati usano dataclass, non Dict
5. Factory methods esistono per conversioni (MuroDef -> GeometryPier)
6. Alias confusi rimossi (gamma -> peso_specifico)
7. TUTTI i test passano senza errori
8. `python connector.py` esegue senza errori
9. `python gui_editor.py` importa senza errori
10. DSL parsing e export funzionano

## COMANDO DI VERIFICA FINALE
```python
import sys
sys.path.insert(0, 'D:/muratura')
from connector import Muratura
m = Muratura("TestProject")
m.materiale("test_mat", "MATTONI_PIENI", "M5", "buona")
m.parete("P1", lunghezza=5.0, altezza=3.0, spessore=0.45, piani=1)
m.assegna_materiale("P1", "test_mat")
result = m.pushover("P1", pattern="uniform", direzione="X", target_drift=0.003)
print("TEST PASSED" if result else "TEST FAILED")
```

Quando TUTTI i criteri sono soddisfatti, output:
```
<promise>PROGETTO MURATURA UNIFORMATO E TESTATO</promise>
```
