# Changelog

Tutte le modifiche significative a questo progetto saranno documentate in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/it/1.0.0/),
e questo progetto aderisce al [Semantic Versioning](https://semver.org/lang/it/).

## [1.0.0] - 2024-11-14

### Aggiunto
- Prima release pubblica di MasonryFEMEngine
- Modulo `materials.py` con database completo NTC 2018
  - Gestione 10 tipologie di muratura
  - Conversione tra sistemi di unità (SI, Tecnico, Imperiale)
  - Validazione fisica dei parametri
  - Export/Import JSON ed Excel
  - Murature multistrato con omogeneizzazione
- Modulo `geometry.py` per geometrie strutturali
  - Maschi murari (GeometryPier)
  - Fasce di piano (GeometrySpandrel)
  - Gestione aperture e irregolarità
  - Sistemi di rinforzo (FRP, FRCM, CAM, etc.)
- Modulo `engine.py` - Motore principale FEM
  - Interfaccia unificata per 7 metodi di analisi
  - Matrici sparse per efficienza computazionale
  - Analisi statiche, modali, pushover, time-history
- Moduli di analisi in `analyses/`:
  - **SAM**: Simplified Analysis of Masonry (≈30k LOC)
  - **FEM**: Finite Element Method con Q4/Q8
  - **POR**: Pushover su modello continuo
  - **Frame**: Telaio equivalente (con analisi modale robusta)
  - **Limit**: Analisi limite con 24 cinematismi EC8
  - **Fiber**: Modello a fibre con legami non lineari
  - **Micro**: Micro-modellazione blocchi-interfacce
- Modulo `constitutive.py` con 10+ legami costitutivi
- Modulo `enums.py` con enumerazioni complete NTC 2018
- Modulo `utils.py` con funzioni di utilità
- Test suite completa con pytest
- Esempi di utilizzo
- Documentazione completa (README, CHANGELOG, LICENSE)
- Setup packaging (setup.py, pyproject.toml, requirements.txt)

### Caratteristiche Tecniche
- Supporto Python 3.9+
- Dipendenze: numpy, scipy, openpyxl
- Conforme NTC 2018 e Eurocodici
- Codice documentato con docstring complete
- Type hints per maggiore sicurezza
- Gestione errori robusta

### Note
- Progetto rilasciato sotto licenza MIT
- Pronto per installazione con pip
- Compatibile con sistemi Linux, Windows, macOS
