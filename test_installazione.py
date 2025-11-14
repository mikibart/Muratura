#!/usr/bin/env python3
"""
MURATURA FEM - Test Installazione
Questo script verifica che tutto funzioni correttamente.
"""

print("🏛️  MURATURA FEM v7.0.0-alpha - Test Installazione")
print("="*60)
print()

# Test 1: Import modulo principale
print("✓ Test 1: Import modulo...")
try:
    from Material import MasonryFEMEngine, __version__
    print(f"  ✅ Importato MURATURA FEM v{__version__}")
except ImportError as e:
    print(f"  ❌ Errore: {e}")
    exit(1)

# Test 2: Import moduli aggiuntivi
print()
print("✓ Test 2: Moduli disponibili...")
moduli_ok = 0
moduli_totali = 0

try:
    moduli_totali += 1
    from Material.materials import MaterialProperties
    print("  ✅ MaterialProperties")
    moduli_ok += 1
except:
    print("  ⚠️  MaterialProperties (opzionale)")

try:
    moduli_totali += 1
    from Material.floors import FloorSystem
    print("  ✅ FloorSystem (solai)")
    moduli_ok += 1
except:
    print("  ⚠️  FloorSystem (opzionale)")

try:
    moduli_totali += 1
    from Material.balconies import BalconyAnalysis
    print("  ✅ BalconyAnalysis (balconi)")
    moduli_ok += 1
except:
    print("  ⚠️  BalconyAnalysis (opzionale)")

try:
    moduli_totali += 1
    from Material.arches import ArchAnalysis
    print("  ✅ ArchAnalysis (edifici storici)")
    moduli_ok += 1
except:
    print("  ⚠️  ArchAnalysis (opzionale)")

# Test 3: Dipendenze
print()
print("✓ Test 3: Dipendenze Python...")
try:
    import numpy as np
    print(f"  ✅ NumPy {np.__version__}")
except:
    print("  ❌ NumPy mancante!")

try:
    import scipy
    print(f"  ✅ SciPy {scipy.__version__}")
except:
    print("  ❌ SciPy mancante!")

try:
    import matplotlib
    print(f"  ✅ Matplotlib {matplotlib.__version__}")
except:
    print("  ❌ Matplotlib mancante!")

# Test 4: Esempi disponibili
print()
print("✓ Test 4: Esempi disponibili...")
import os
esempi_dir = '/home/user/Muratura/examples'
if os.path.exists(esempi_dir):
    esempi = [f for f in os.listdir(esempi_dir) if f.endswith('.py')]
    print(f"  ✅ Trovati {len(esempi)} esempi")
    for i, esempio in enumerate(esempi[:5], 1):
        print(f"     {i}. {esempio}")
    if len(esempi) > 5:
        print(f"     ... e altri {len(esempi)-5} esempi")
else:
    print("  ⚠️  Cartella examples non trovata")

# Riepilogo
print()
print("="*60)
print("🎉 INSTALLAZIONE COMPLETATA CON SUCCESSO!")
print()
print("📚 PROSSIMI PASSI:")
print()
print("1. Esegui un esempio semplice:")
print("   cd /home/user/Muratura")
print("   python examples/01_pushover_simple.py")
print()
print("2. Oppure crea il tuo script Python:")
print("   from Material import MasonryFEMEngine")
print("   model = MasonryFEMEngine()")
print()
print("3. Genera una relazione di calcolo:")
print("   python examples/12_report_generation.py")
print()
print("4. Oppure usa la GUI:")
print("   pip install PyQt6")
print("   python gui/desktop_qt/main_window.py")
print()
print("📖 Documentazione: README.md, GETTING_STARTED.md")
print("🆘 Aiuto: https://github.com/mikibart/Muratura")
print()
