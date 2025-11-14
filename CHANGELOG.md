# Changelog

Tutte le modifiche rilevanti al progetto saranno documentate in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
e questo progetto segue [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [6.1.0] - 2025-11-14

### Added
- **Infrastruttura Production-Ready completa**
  - requirements.txt con dipendenze specificate
  - README.md completo con esempi
  - LICENSE (MIT) con disclaimer ingegneria
  - setup.py per installazione package
  - Dockerfile per containerizzazione
  - GitHub Actions CI/CD pipeline
  - Test suite base con pytest
  - File configurazione YAML

- **Implementazioni Complete**
  - Funzione `create_frame_from_wall_data` completa (era TODO)
  - Algoritmo identificazione automatica maschi murari
  - Algoritmo identificazione automatica fasce di piano
  - Assegnazione automatica nodi a elementi

- **Esempi di Utilizzo**
  - 01_pushover_simple.py - Analisi pushover base
  - 02_modal_analysis.py - Analisi modale
  - 03_sam_verification.py - Verifica SAM NTC2018

- **Test**
  - test_materials.py - Test proprietà materiali
  - test_engine.py - Test motore FEM

### Fixed
- Rimosso frammento codice duplicato in constitutive.py (righe 1-25)
- Corretto errore sintassi SyntaxError in constitutive.py
- Corretta assegnazione nodi vuota in geometry.py

### Changed
- Aggiornato .gitignore per escludere __pycache__

### Documentation
- README completo con Quick Start
- Esempi di utilizzo per tutti i metodi principali
- Documentazione API inline migliorata
- CONTRIBUTING guidelines

## [6.0.0] - 2025-11-13

### Added
- Motore FEM v6.1 completo
- 7 metodi di analisi (FEM, POR, SAM, FRAME, LIMIT, FIBER, MICRO)
- Modelli costitutivi secondo NTC 2018
- Analisi modale con masse partecipanti
- Analisi pushover con pattern multipli
- Analisi time-history con Newmark-β
- 24 cinematismi di collasso EC8/NTC2018
- Geometrie complete (pier, spandrel, wall)
- Verifiche automatiche secondo normativa

### Known Issues
- Test coverage ancora bassa (da implementare)
- Alcuni print() da sostituire con logger
- Documentazione API da completare con Sphinx

---

## Tipi di Modifiche

- `Added` per nuove funzionalità
- `Changed` per modifiche a funzionalità esistenti
- `Deprecated` per funzionalità che saranno rimosse
- `Removed` per funzionalità rimosse
- `Fixed` per bug fix
- `Security` per vulnerabilità di sicurezza
