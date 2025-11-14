# Contributing to Muratura FEM

Grazie per l'interesse nel contribuire a Muratura FEM! Questo documento fornisce le linee guida per contribuire al progetto.

## 🎯 Come Contribuire

### Segnalare Bug

1. Controlla che il bug non sia già stato segnalato nelle [Issues](https://github.com/mikibart/Muratura/issues)
2. Apri una nuova issue con:
   - Titolo chiaro e descrittivo
   - Descrizione dettagliata del problema
   - Passi per riprodurre il bug
   - Comportamento atteso vs. comportamento attuale
   - Screenshot se applicabile
   - Informazioni ambiente (OS, Python version, etc.)

### Proporre Nuove Funzionalità

1. Apri una issue con tag `enhancement`
2. Descrivi chiaramente:
   - Problema che la funzionalità risolve
   - Soluzione proposta
   - Alternative considerate
   - Possibili impatti sul codice esistente

### Contribuire Codice

#### Setup Ambiente di Sviluppo

```bash
# Fork e clone
git clone https://github.com/TUO_USERNAME/Muratura.git
cd Muratura

# Crea virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# Installa dipendenze dev
pip install -r requirements.txt
pip install pytest pytest-cov black flake8 mypy

# Installa package in modalità editable
pip install -e .
```

#### Workflow Contribuzione

1. **Crea un branch**
   ```bash
   git checkout -b feature/nome-funzionalita
   # o
   git checkout -b fix/nome-bug
   ```

2. **Scrivi codice seguendo le linee guida**
   - Segui PEP 8
   - Aggiungi docstrings (Google style)
   - Usa type hints
   - Scrivi test per nuove funzionalità

3. **Formatta il codice**
   ```bash
   black Material/
   flake8 Material/
   mypy Material/ --ignore-missing-imports
   ```

4. **Esegui test**
   ```bash
   pytest tests/ -v --cov=Material
   ```

5. **Commit**
   ```bash
   git add .
   git commit -m "feat: Descrizione breve della modifica"
   ```

   Convenzione commit messages:
   - `feat:` Nuova funzionalità
   - `fix:` Bug fix
   - `docs:` Modifiche documentazione
   - `test:` Aggiunta/modifica test
   - `refactor:` Refactoring codice
   - `style:` Formattazione, missing semicolons, etc.
   - `perf:` Miglioramenti performance
   - `chore:` Manutenzione, dipendenze, etc.

6. **Push e Pull Request**
   ```bash
   git push origin feature/nome-funzionalita
   ```
   Apri Pull Request su GitHub con:
   - Titolo chiaro
   - Descrizione delle modifiche
   - Link a issue correlate
   - Screenshot se applicabile

## 📋 Linee Guida Codice

### Style Guide

```python
# Buono
def calculate_capacity(pier: GeometryPier,
                       material: MaterialProperties,
                       axial_load: float) -> float:
    """
    Calcola capacità taglio maschio murario secondo NTC 2018.

    Args:
        pier: Geometria maschio
        material: Proprietà materiale
        axial_load: Carico assiale [kN]

    Returns:
        Capacità a taglio [kN]

    Raises:
        ValueError: Se parametri non validi
    """
    if axial_load < 0:
        raise ValueError("Carico assiale deve essere >= 0")

    # Implementazione...
    return capacity

# Cattivo
def calc(p, m, n):  # No docstring, nomi poco chiari
    if n<0: raise ValueError("error")  # Formattazione
    return p.area*m.tau0+0.4*n  # Magic numbers, formula non chiara
```

### Testing

```python
# Test deve essere completo e documentato
def test_pier_capacity_positive_load():
    """Test capacità maschio con carico positivo"""
    # Arrange
    pier = GeometryPier(length=1.0, height=2.8, thickness=0.4)
    material = MaterialProperties(fcm=4.0, tau0=0.1, mu=0.4)

    # Act
    capacity = calculate_capacity(pier, material, axial_load=100.0)

    # Assert
    assert capacity > 0
    assert capacity < 1000  # Sanity check
```

### Documentazione

- Ogni modulo deve avere docstring di modulo
- Ogni classe deve avere docstring
- Ogni funzione pubblica deve avere docstring
- Usa esempi nei docstring quando utile

```python
"""
Module: materials.py
Gestione proprietà materiali secondo NTC 2018

Examples:
    >>> from Material.materials import MaterialProperties
    >>> mat = MaterialProperties(E=1500, fcm=4.0)
    >>> print(mat.name)
    'Default Material'
"""
```

## 🧪 Testing Requirements

- Coverage minimo: 70% per nuovo codice
- Tutti i test devono passare
- Test devono essere deterministici (no random)
- Test devono essere veloci (< 1s per unit test)

## 📚 Documentazione

Per modifiche alla documentazione:
- README.md per documentazione utente
- Docstrings inline per API reference
- examples/ per esempi pratici
- docs/ per documentazione estesa (future)

## ⚖️ Licenza

Contribuendo a Muratura FEM, accetti che i tuoi contributi saranno licenziati sotto la licenza MIT del progetto.

## 💬 Domande?

- Apri una [Discussion](https://github.com/mikibart/Muratura/discussions)
- Contatta i maintainer via issue

## 🙏 Riconoscimenti

Tutti i contributors saranno riconosciuti nel README e nei release notes.

---

Grazie per contribuire a Muratura FEM!
