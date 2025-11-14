# Historic Buildings Analysis Module

**Status**: ✅ COMPLETED (Fase 2 - v6.4.3)
**Release**: November 2025

## 📋 Contenuto Pianificato

### Moduli Implementati (100%)
- [x] `arches.py` - Analisi archi metodo Heyman (limite analysis) ✅
- [x] `vaults.py` - Analisi volte (botte, crociera, cupole) ✅
- [x] `strengthening.py` - Rinforzi FRP/FRCM (CNR-DT 200/215) ✅
- [x] `knowledge_levels.py` - Knowledge Levels LC1/LC2/LC3 (NTC 2018) ✅

### Metodologie
- **Analisi Limite** (Heyman, 1966-1982)
  - Teorema statico: thrust line
  - Teorema cinematico: meccanismi collasso
  - Coefficiente sicurezza geometrico

- **DMEM** (Discrete Macro-Element Model) - Futuro
  - Modellazione non-lineare
  - Analisi pushover
  - Calibrazione sperimentale

### Tipologie Strutturali
- Archi: semicircolari, ribassati, ogivali, rampanti
- Volte: botte, crociera, padiglione, cupole, vele
- Pilastri: analisi snellezza, eccentricità

## 📚 Riferimenti Teorici

### Bibliografia Fondamentale
1. Heyman, J. (1966) "The stone skeleton"
2. Heyman, J. (1982) "The Masonry Arch"
3. Huerta, S. (2001) "Mechanics of masonry vaults"
4. Poleni, G. (1748) "Cupola del Tempio Vaticano"
5. Lagomarsino, S. (2015) "DMEM for cultural heritage"

### Normativa
- NTC 2018 Cap. 8 (Costruzioni esistenti)
- Linee Guida Beni Culturali 2011
- CNR-DT 200 R1/2013 (Rinforzi FRP)
- CNR-DT 215/2018 (Rinforzi FRCM)
- CNR-DT 212/2013 (Valutazione carichi vento)

## 🎯 Obiettivi Fase 2 - COMPLETATI AL 100%! 🎉

- [x] Pianificazione completa (✅ COMPLETATO)
- [x] Implementazione modulo archi (✅ COMPLETATO)
- [x] Implementazione modulo volte (✅ COMPLETATO)
- [x] Modulo rinforzi FRP/FRCM (✅ COMPLETATO)
- [x] Sistema Knowledge Levels LC1/LC2/LC3 (✅ COMPLETATO)
- [x] Esempi edifici storici reali (✅ 15 esempi)
- [x] Test suite completa (✅ 84 test passing)

## 📊 Timeline

**Inizio**: Post Fase 1 (v6.2 completata ✅)
**Durata stimata**: 12 settimane
**Effort**: 4 settimane archi + 3 settimane volte + 3 settimane rinforzi + 2 settimane LC

## 🔗 Integrazione

Il modulo si integrerà con:
- Moduli Fase 1: solai, balconi, scale
- Sistema murature esistente
- Analisi sismica (cinematismi)
- Knowledge levels per edifici esistenti

Vedi `docs/PHASE_2_HISTORIC_BUILDINGS_PLAN.md` per dettagli completi.
