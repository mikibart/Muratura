# MURATURA - PIANO DI SVILUPPO PROFESSIONALE

## OBIETTIVO
Trasformare Muratura in un software professionale completo per:
1. **Progettazione nuovi edifici** in muratura
2. **Verifica sismica edifici esistenti**

Il software deve essere usabile da ingegneri e architetti senza conoscenze di programmazione.

---

## FASE 1: DATI DI PROGETTO E LOCALIZZAZIONE (Priorità ALTA)

### 1.1 Zone Sismiche e Spettri di Risposta
**Stato attuale:** Mancante
**Da implementare:**
- [ ] Database comuni italiani con coordinate (lat/lon)
- [ ] Calcolo automatico parametri sismici da coordinate:
  - ag (accelerazione di picco)
  - F0 (fattore amplificazione)
  - Tc* (periodo inizio tratto velocità costante)
- [ ] Categorie di sottosuolo (A, B, C, D, E)
- [ ] Categorie topografiche (T1, T2, T3, T4)
- [ ] Calcolo spettro di risposta elastico e di progetto
- [ ] Vita nominale (VN) e classe d'uso (I, II, III, IV)
- [ ] Calcolo periodo di ritorno per ogni stato limite (SLO, SLD, SLV, SLC)

**GUI necessaria:**
- Finestra "Localizzazione Progetto" con:
  - Ricerca comune per nome
  - Mappa interattiva Italia (opzionale)
  - Selezione categoria suolo con descrizioni
  - Selezione categoria topografica
  - Input vita nominale e classe d'uso
  - Visualizzazione spettro calcolato

### 1.2 Normativa di Riferimento
**Stato attuale:** Parziale (solo NTC 2018)
**Da implementare:**
- [ ] Selezione normativa: NTC 2018, NTC 2008, EC8
- [ ] Coefficienti parziali configurabili
- [ ] Fattori di combinazione carichi (psi0, psi1, psi2)
- [ ] Classe di duttilità (CD"A", CD"B")

---

## FASE 2: GEOMETRIA EDIFICIO (Priorità ALTA)

### 2.1 Definizione Piani
**Stato attuale:** Base
**Da implementare:**
- [ ] Altezza interpiano variabile per piano
- [ ] Quote assolute (da piano campagna)
- [ ] Piano interrato/seminterrato
- [ ] Piano sottotetto/mansarda
- [ ] Irregolarità in elevazione (setback)

**GUI necessaria:**
- Pannello "Gestione Piani" con:
  - Lista piani con altezze editabili
  - Pulsanti aggiungi/rimuovi piano
  - Visualizzazione sezione schematica

### 2.2 Pareti e Aperture
**Stato attuale:** Base
**Da implementare:**
- [ ] Disegno pareti su griglia con snap
- [ ] Pareti inclinate (non solo ortogonali)
- [ ] Pareti curve (archi)
- [ ] Aperture con architrave (tipo e dimensioni)
- [ ] Aperture ad arco
- [ ] Davanzali e soglie
- [ ] Nicchie e rientranze
- [ ] Canne fumarie e cavedi
- [ ] Muri a doppio paramento
- [ ] Ammorsamenti tra pareti (buono/scarso/assente)

**GUI necessaria:**
- Canvas 2D per ogni piano con:
  - Strumenti disegno: linea, rettangolo, poligono
  - Snap a griglia configurabile (5cm, 10cm, 25cm)
  - Snap a punti notevoli (estremi, mezzeria, intersezioni)
  - Layer separati per: pareti portanti, tramezzi, aperture
  - Quotatura automatica
  - Copia piano su piano superiore

### 2.3 Cordoli e Cerchiature
**Stato attuale:** Base (CordoloDef)
**Da implementare:**
- [ ] Cordoli in c.a. con armatura
- [ ] Cordoli in acciaio
- [ ] Cerchiature aperture
- [ ] Tiranti metallici (posizione, sezione, pretensione)
- [ ] Catene storiche

**GUI necessaria:**
- Tool "Inserisci cordolo" con wizard proprietà
- Visualizzazione 3D cordoli sulla parete

---

## FASE 3: SOLAI E COPERTURE (Priorità ALTA)

### 3.1 Tipologie Solai
**Stato attuale:** Mancante
**Da implementare:**
- [ ] Solai in laterocemento (travetti + pignatte)
  - Altezza totale, interasse travetti
  - Soletta collaborante (spessore, armatura)
  - Peso proprio calcolato automaticamente
- [ ] Solai in legno
  - Travi principali (sezione, interasse)
  - Travicelli/tavolato
  - Connettori (per collaborazione)
- [ ] Solai in acciaio (putrelle + tavelloni)
- [ ] Solai in c.a. pieno
- [ ] Volte (a botte, a crociera, a padiglione)
  - Geometria, spessore, riempimento

**Proprietà comuni:**
- [ ] Direzione orditura (parallela a quale parete)
- [ ] Rigidezza nel piano (rigido/flessibile/semi-rigido)
- [ ] Vincolo alle pareti (appoggio semplice/incastro)
- [ ] Sfalsamento quote (dislivelli)

**GUI necessaria:**
- Tool "Inserisci solaio" su pianta:
  - Selezione area (click su vano chiuso)
  - Wizard tipologia con schemi grafici
  - Freccia direzione orditura
  - Tabella riepilogativa solai per piano

### 3.2 Coperture
**Stato attuale:** Mancante
**Da implementare:**
- [ ] Copertura piana (terrazzo)
- [ ] Copertura a falde:
  - Una falda, due falde, quattro falde
  - Pendenza configurabile
  - Linea di colmo, linea di gronda
- [ ] Struttura copertura:
  - Capriate in legno (tipi: semplice, palladiana, composta)
  - Capriate in acciaio
  - Travi inclinate
- [ ] Manto di copertura (peso)
- [ ] Sottotetto praticabile/non praticabile

**GUI necessaria:**
- Editor copertura 3D semplificato
- Wizard "Tipo copertura" con preview

---

## FASE 4: CARICHI (Priorità ALTA)

### 4.1 Carichi Permanenti Strutturali (G1)
**Stato attuale:** Parziale
**Da implementare:**
- [ ] Calcolo automatico peso proprio murature
- [ ] Calcolo automatico peso solai (da tipologia)
- [ ] Calcolo automatico peso copertura
- [ ] Peso scale
- [ ] Peso balconi e sbalzi

### 4.2 Carichi Permanenti Non Strutturali (G2)
**Stato attuale:** Parziale
**Da implementare:**
- [ ] Massetti e pavimentazioni
- [ ] Intonaci (interno/esterno)
- [ ] Controsoffitti
- [ ] Impianti
- [ ] Tramezzature (carico equivalente)
- [ ] Database pesi materiali

**GUI necessaria:**
- Finestra "Stratigrafia solaio" per definire strati
- Calcolo automatico G2 da stratigrafia

### 4.3 Carichi Variabili (Q)
**Stato attuale:** Base
**Da implementare:**
- [ ] Categorie d'uso NTC (A, B, C, D, E, F, G, H)
- [ ] Valori caratteristici da normativa
- [ ] Coefficienti psi per combinazioni
- [ ] Carichi concentrati (dove richiesto)
- [ ] Affollamento (Cat. C)

**GUI necessaria:**
- Assegnazione categoria a ogni vano/locale
- Colorazione pianta per categoria

### 4.4 Neve
**Stato attuale:** Mancante
**Da implementare:**
- [ ] Calcolo qsk da zona e altitudine
- [ ] Coefficiente di forma copertura (mu)
- [ ] Coefficiente di esposizione (Ce)
- [ ] Coefficiente termico (Ct)

### 4.5 Vento
**Stato attuale:** Mancante
**Da implementare:**
- [ ] Velocità di riferimento da zona
- [ ] Categoria di esposizione
- [ ] Coefficienti di pressione (Cp) per forma edificio
- [ ] Pressione interna

### 4.6 Combinazioni di Carico
**Stato attuale:** Parziale
**Da implementare:**
- [ ] Generazione automatica combinazioni SLU
- [ ] Generazione automatica combinazioni SLE
- [ ] Combinazione sismica
- [ ] Selezione combinazione critica automatica

**GUI necessaria:**
- Tabella combinazioni con coefficienti
- Selezione manuale combinazioni da verificare

---

## FASE 5: MATERIALI E CONOSCENZA (Priorità ALTA)

### 5.1 Livelli di Conoscenza
**Stato attuale:** Parziale
**Da implementare:**
- [ ] Wizard LC1/LC2/LC3 con checklist indagini
- [ ] Fattore di confidenza automatico
- [ ] Documentazione indagini richieste
- [ ] Report livello conoscenza raggiunto

### 5.2 Materiali Muratura
**Stato attuale:** Buono (NTC Tab. C8.5.I)
**Da implementare:**
- [ ] Coefficienti correttivi:
  - Malta buona/scarsa
  - Ricorsi/listature
  - Nucleo interno scadente
  - Iniezioni consolidamento
  - Intonaco armato
  - FRP/FRCM
- [ ] Input valori da prove (se disponibili)
- [ ] Muratura storica (caratterizzazione specifica)

### 5.3 Altri Materiali
**Stato attuale:** Parziale
**Da implementare:**
- [ ] Calcestruzzo (classi C...)
- [ ] Acciaio armatura (B450C, etc.)
- [ ] Acciaio strutturale (S235, S275, S355)
- [ ] Legno (GL24h, GL28h, C24, etc.)

---

## FASE 6: ANALISI STRUTTURALE (Priorità MEDIA)

### 6.1 Modellazione
**Stato attuale:** Buono (7 metodi)
**Da implementare:**
- [ ] Scelta automatica metodo in base a regolarità
- [ ] Verifica regolarità in pianta e elevazione
- [ ] Eccentricità accidentale
- [ ] Effetti torsionali

### 6.2 Analisi Globale
**Stato attuale:** Buono
**Da implementare:**
- [ ] Analisi modale con spettro di risposta
- [ ] Combinazione effetti (CQC, SRSS)
- [ ] Analisi pushover multimodale
- [ ] Verifica q* < q (comportamento dissipativo)

### 6.3 Meccanismi Locali
**Stato attuale:** Parziale (LimitAnalysis)
**Da implementare:**
- [ ] Ribaltamento semplice parete
- [ ] Ribaltamento composto
- [ ] Flessione verticale
- [ ] Flessione orizzontale
- [ ] Ribaltamento cantonale
- [ ] Calcolo cinematismo con tiranti
- [ ] Verifica SLV meccanismi locali

---

## FASE 7: VERIFICHE (Priorità MEDIA)

### 7.1 Verifiche Elementi
**Stato attuale:** Buono
**Da completare:**
- [ ] Pressoflessione nel piano
- [ ] Taglio per fessurazione diagonale
- [ ] Taglio per scorrimento
- [ ] Pressoflessione fuori piano
- [ ] Snellezza (verifica di stabilità)
- [ ] Carichi concentrati

### 7.2 Verifiche Globali
**Stato attuale:** Parziale
**Da implementare:**
- [ ] Indice di rischio sismico (IR = PGA_c / PGA_d)
- [ ] Vita nominale residua
- [ ] Classe di rischio sismico (PAM, IS-V)
- [ ] Sismabonus (per interventi)

### 7.3 Report e Output
**Stato attuale:** Mancante
**Da implementare:**
- [ ] Relazione di calcolo automatica (Word/PDF)
- [ ] Indice con riferimenti normativi
- [ ] Capitolo dati generali
- [ ] Capitolo materiali
- [ ] Capitolo azioni
- [ ] Capitolo modello
- [ ] Capitolo risultati analisi
- [ ] Capitolo verifiche con tabelle DCR
- [ ] Allegati: piante, sezioni, schemi

---

## FASE 8: INTERFACCIA GRAFICA (Priorità CRITICA)

### 8.1 Layout Principale
**Stato attuale:** Base (gui_editor.py)
**Da implementare:**
- [ ] Menu completo:
  - File (nuovo, apri, salva, esporta, stampa)
  - Modifica (annulla, ripeti, copia, incolla)
  - Visualizza (zoom, pan, viste 3D)
  - Inserisci (pareti, aperture, solai, carichi)
  - Analisi (avvia, impostazioni)
  - Risultati (deformate, sollecitazioni, verifiche)
  - Strumenti (opzioni, unità di misura)
  - Aiuto (manuale, info)
- [ ] Toolbar con icone intuitive
- [ ] Barra di stato con coordinate e suggerimenti
- [ ] Pannello proprietà contestuale
- [ ] Explorer progetto (albero struttura)

### 8.2 Viste
**Stato attuale:** Solo pianta 2D
**Da implementare:**
- [ ] Vista pianta per piano (con tab)
- [ ] Vista sezione (generabile su qualsiasi linea)
- [ ] Vista 3D assonometrica
- [ ] Vista 3D prospettica
- [ ] Rotazione/zoom 3D con mouse
- [ ] Visualizzazione materiali con colori/texture

### 8.3 Input Guidato
**Da implementare:**
- [ ] Wizard nuovo progetto (step by step)
- [ ] Suggerimenti contestuali
- [ ] Validazione input in tempo reale
- [ ] Messaggi errore chiari e localizzati
- [ ] Tooltip su ogni campo
- [ ] Help contestuale (F1)

### 8.4 Output Grafico
**Da implementare:**
- [ ] Colorazione pareti per verifica (verde/giallo/rosso)
- [ ] Visualizzazione deformata modale
- [ ] Visualizzazione curva pushover
- [ ] Diagrammi sollecitazioni (N, T, M)
- [ ] Esportazione immagini (PNG, SVG)
- [ ] Esportazione DXF/DWG

---

## FASE 9: INTEROPERABILITÀ (Priorità BASSA)

### 9.1 Import
**Da implementare:**
- [ ] Import DXF (piante architettoniche)
- [ ] Import IFC (BIM)
- [ ] Import da altri software (3Muri XML, AEDES PCM)

### 9.2 Export
**Da implementare:**
- [ ] Export IFC
- [ ] Export relazione Word/PDF
- [ ] Export dati Excel
- [ ] Export modello per SAP2000/Midas

---

## CRITERI DI COMPLETAMENTO

Il software è PRODUCTION-READY quando:

1. [ ] Un utente può inserire un edificio completo solo con GUI (no codice)
2. [ ] Tutti i dati sismici si calcolano da posizione geografica
3. [ ] Solai e coperture sono definibili graficamente
4. [ ] Carichi si calcolano automaticamente + input manuali
5. [ ] Analisi pushover funziona end-to-end
6. [ ] Verifiche mostrano DCR con colorazione
7. [ ] Si genera relazione di calcolo PDF
8. [ ] Indice di rischio sismico calcolato
9. [ ] Nessun crash su input errati (validazione robusta)
10. [ ] Manuale utente disponibile

---

## ORDINE DI IMPLEMENTAZIONE SUGGERITO

### Sprint 1 (Fondamenta)
1. GUI: Wizard nuovo progetto
2. Localizzazione: Database comuni + calcolo spettro
3. GUI: Migliorare editor pianta (snap, quote)

### Sprint 2 (Struttura)
4. Solai: Tipologie base + inserimento GUI
5. Coperture: Tipologie base
6. Carichi: G1/G2 automatici

### Sprint 3 (Analisi)
7. Carichi: Neve, vento
8. Combinazioni: Generazione automatica
9. Analisi: Verifica regolarità

### Sprint 4 (Output)
10. Verifiche: DCR con colorazione GUI
11. Report: Generazione PDF base
12. Indice rischio sismico

### Sprint 5 (Rifinitura)
13. GUI: Vista 3D
14. GUI: Sezioni
15. Import DXF
16. Manuale utente

---

## COMANDO DI VERIFICA
```python
# Test minimo per software production-ready
from gui_editor import MuraturaEditor
from PyQt5.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
editor = MuraturaEditor()

# Deve poter:
# 1. Creare progetto con localizzazione
# 2. Disegnare pareti con snap
# 3. Inserire solai
# 4. Definire carichi
# 5. Lanciare analisi
# 6. Vedere risultati con colori
# 7. Esportare relazione

print("GUI READY" if editor else "GUI FAILED")
```

Quando TUTTE le fasi sono implementate:
```
<promise>MURATURA PRODUCTION READY</promise>
```
