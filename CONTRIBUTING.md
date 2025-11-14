# Contribuire a MasonryFEMEngine

Grazie per il tuo interesse nel contribuire a MasonryFEMEngine! 🎉

## Come Contribuire

### Segnalare Bug

Se trovi un bug, per favore apri una [Issue](https://github.com/mikibart/Muratura/issues) includendo:
- Descrizione dettagliata del problema
- Passi per riprodurre il bug
- Comportamento atteso vs comportamento osservato
- Versione di Python e sistema operativo
- Traceback dell'errore (se disponibile)

### Proporre Nuove Funzionalità

Per proporre nuove funzionalità:
1. Apri una Issue descrivendo la funzionalità
2. Spiega il caso d'uso e i benefici
3. Attendi feedback prima di iniziare l'implementazione

### Inviare Pull Request

1. **Fork** il repository
2. **Crea un branch** per la tua feature:
   ```bash
   git checkout -b feature/nome-feature
   ```
3. **Implementa** le modifiche
4. **Aggiungi test** per la nuova funzionalità
5. **Esegui i test** esistenti:
   ```bash
   pytest tests/
   ```
6. **Commit** con messaggi descrittivi:
   ```bash
   git commit -m "Aggiungi supporto per X"
   ```
7. **Push** al tuo fork:
   ```bash
   git push origin feature/nome-feature
   ```
8. Apri una **Pull Request** su GitHub

## Standard di Codice

### Stile

- Segui [PEP 8](https://pep8.org/)
- Usa type hints dove possibile
- Docstring in formato NumPy/Google
- Linea max 100 caratteri (configurato in black)

### Formattazione

Usa `black` per la formattazione automatica:
```bash
black muratura/
```

### Test

- Scrivi test per ogni nuova funzionalità
- Mantieni la copertura > 80%
- Usa pytest per i test

```bash
pytest tests/ --cov=muratura
```

### Documentazione

- Documenta funzioni pubbliche con docstring complete
- Aggiorna README.md se necessario
- Aggiungi esempi per funzionalità complesse

## Processo di Review

1. Un maintainer revisionerà la tua PR
2. Potrebbero essere richieste modifiche
3. Una volta approvata, la PR sarà merged

## Licenza

Contribuendo a questo progetto, accetti che i tuoi contributi siano
rilasciati sotto la licenza MIT.

## Domande?

Se hai domande, apri una Issue o contatta i maintainer.

Grazie per il tuo contributo! 🙏
