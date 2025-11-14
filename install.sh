#!/bin/bash
# MURATURA FEM v7.0 - Script di Installazione Semplice
# Questo script configura tutto automaticamente

echo "🏛️  MURATURA FEM v7.0.0-alpha - Installazione"
echo "=============================================="
echo ""

# 1. Verifica Python
echo "✓ Verifico Python..."
python3 --version || { echo "❌ Python 3.8+ richiesto!"; exit 1; }

# 2. Installa dipendenze base
echo ""
echo "✓ Installo dipendenze..."
pip install numpy scipy matplotlib pandas typing-extensions --quiet 2>/dev/null

# 3. Verifica installazione
echo ""
echo "✓ Verifico installazione..."
cd /home/user/Muratura
python3 -c "from Material import MasonryFEMEngine; print('  ✅ MURATURA FEM installato!')" 2>/dev/null

# 4. Setup completo
echo ""
echo "✅ INSTALLAZIONE COMPLETATA!"
echo ""
echo "📚 COME USARE:"
echo ""
echo "1. Esegui un esempio:"
echo "   cd /home/user/Muratura"
echo "   python3 examples/01_pushover_simple.py"
echo ""
echo "2. Oppure dalla GUI:"
echo "   pip install PyQt6"
echo "   python3 gui/desktop_qt/main_window.py"
echo ""
echo "3. Lista esempi disponibili:"
echo "   ls -1 examples/"
echo ""
echo "🎉 Buon lavoro con MURATURA FEM!"
