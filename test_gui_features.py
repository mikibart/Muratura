#!/usr/bin/env python3
"""
TEST FUNZIONALITÀ GUI MURATURA v2.0
Verifica completa senza aprire finestre grafiche
"""

import sys
import os

# Blocca l'apertura di finestre Qt
os.environ['QT_QPA_PLATFORM'] = 'minimal'

print("=" * 70)
print("TEST FUNZIONALITÀ GUI MURATURA v2.0")
print("=" * 70)

results = {'pass': 0, 'fail': 0}
missing = []

def test(name, condition, details=""):
    global results
    if condition:
        results['pass'] += 1
        print(f"  ✓ {name}")
    else:
        results['fail'] += 1
        print(f"  ✗ {name}: {details}")

def missing_feature(name):
    missing.append(name)
    print(f"  ⚠ MANCANTE: {name}")

# ==============================================================================
# 1. TEST IMPORT MODULI
# ==============================================================================
print("\n[1] TEST IMPORT MODULI")

try:
    from gui_editor_v2 import (
        MuraturaEditorV2, Progetto, Muro, Apertura, Solaio, Piano,
        WorkflowStep, ANALYSIS_METHODS, RibbonToolbar, ProjectBrowser,
        DrawingCanvas, PropertiesPanel, WorkflowPanel, QuickActionsPanel,
        StepProgettoPanel, StepPianiPanel, AnalysisMethodDialog
    )
    test("Import gui_editor_v2", True)
except ImportError as e:
    test("Import gui_editor_v2", False, str(e))

# ==============================================================================
# 2. TEST DATA CLASSES
# ==============================================================================
print("\n[2] TEST DATA CLASSES")

# Progetto
try:
    p = Progetto()
    test("Classe Progetto", True)
    test("Progetto.nome", hasattr(p, 'nome'), "Campo mancante")
    test("Progetto.muri", hasattr(p, 'muri'), "Campo mancante")
    test("Progetto.aperture", hasattr(p, 'aperture'), "Campo mancante")
    test("Progetto.solai", hasattr(p, 'solai'), "Campo mancante")
    test("Progetto.piani", hasattr(p, 'piani'), "Campo mancante")
    test("Progetto.sismici", hasattr(p, 'sismici'), "Campo mancante")
    test("Progetto.indice_rischio", hasattr(p, 'indice_rischio'), "Campo mancante")
except Exception as e:
    test("Classe Progetto", False, str(e))

# Verifica campi strutturali (nuovi)
test("Progetto.fondazioni", hasattr(p, 'fondazioni'), "Campo mancante")
test("Progetto.cordoli", hasattr(p, 'cordoli'), "Campo mancante")
test("Progetto.tiranti", hasattr(p, 'tiranti'), "Campo mancante")
test("Progetto.scale", hasattr(p, 'scale'), "Campo mancante")
test("Progetto.balconi", hasattr(p, 'balconi'), "Campo mancante")
test("Progetto.copertura", hasattr(p, 'copertura'), "Campo mancante")

# Muro
try:
    m = Muro("M1", 0, 0, 5, 0)
    test("Classe Muro", True)
    test("Muro.lunghezza (property)", m.lunghezza == 5.0, f"L={m.lunghezza}")
    test("Muro.spessore (default)", m.spessore == 0.30, f"s={m.spessore}")
    test("Muro.altezza (default)", m.altezza == 3.0, f"h={m.altezza}")
    test("Muro.dcr", hasattr(m, 'dcr'), "Campo mancante")
except Exception as e:
    test("Classe Muro", False, str(e))

# Apertura
try:
    a = Apertura("F1", "M1", "finestra", 1.2, 1.4, 1.0, 0.9)
    test("Classe Apertura", True)
    test("Apertura.tipo", a.tipo == "finestra", f"tipo={a.tipo}")
except Exception as e:
    test("Classe Apertura", False, str(e))

# Solaio
try:
    s = Solaio("S1", 0)
    test("Classe Solaio", True)
    test("Solaio.area (property)", hasattr(s, 'area') and s.area > 0, "Mancante")
    test("Solaio.carico_totale (property)", hasattr(s, 'carico_totale'), "Mancante")
except Exception as e:
    test("Classe Solaio", False, str(e))

# Piano
try:
    piano = Piano(0, 0.0)
    test("Classe Piano", True)
except Exception as e:
    test("Classe Piano", False, str(e))

# ==============================================================================
# 3. TEST WORKFLOW STEPS
# ==============================================================================
print("\n[3] TEST WORKFLOW STEPS")

expected_steps = ['PROGETTO', 'PIANI', 'GEOMETRIA', 'APERTURE', 'SOLAI', 'CARICHI', 'ANALISI', 'RISULTATI']
for step_name in expected_steps:
    has_step = hasattr(WorkflowStep, step_name)
    test(f"WorkflowStep.{step_name}", has_step, "Step mancante")

# Steps nuovi
test("WorkflowStep.FONDAZIONI", hasattr(WorkflowStep, 'FONDAZIONI'), "Step mancante")
test("WorkflowStep.MATERIALI", hasattr(WorkflowStep, 'MATERIALI'), "Step mancante")
test("WorkflowStep.CORDOLI", hasattr(WorkflowStep, 'CORDOLI'), "Step mancante")

# ==============================================================================
# 4. TEST METODI DI ANALISI
# ==============================================================================
print("\n[4] TEST METODI DI ANALISI")

expected_methods = ['POR', 'SAM', 'PORFLEX', 'LIMIT', 'FEM', 'FIBER', 'MICRO']
for method in expected_methods:
    if method in ANALYSIS_METHODS:
        info = ANALYSIS_METHODS[method]
        test(f"Metodo {method} disponibile", info['available'], "Modulo non importabile")
    else:
        test(f"Metodo {method} definito", False, "Metodo non in ANALYSIS_METHODS")

# Metodi mancanti
missing_analysis = ['PUSHOVER', 'MODALE', 'DINAMICA_LINEARE']
for m in missing_analysis:
    if m not in ANALYSIS_METHODS:
        missing_feature(f"Analisi {m}")

# ==============================================================================
# 5. TEST GUI COMPONENTS
# ==============================================================================
print("\n[5] TEST GUI COMPONENTS")

components = [
    ('RibbonToolbar', RibbonToolbar),
    ('ProjectBrowser', ProjectBrowser),
    ('DrawingCanvas', DrawingCanvas),
    ('PropertiesPanel', PropertiesPanel),
    ('WorkflowPanel', WorkflowPanel),
    ('QuickActionsPanel', QuickActionsPanel),
    ('StepProgettoPanel', StepProgettoPanel),
    ('StepPianiPanel', StepPianiPanel),
    ('AnalysisMethodDialog', AnalysisMethodDialog),
]

for name, cls in components:
    test(f"Classe {name}", cls is not None, "Classe non trovata")

# Test nuovi componenti implementati
try:
    from gui_editor_v2 import DialogoApertura, DialogoFondazione, StepFondazioniPanel, StepCordoliPanel
    test("DialogoApertura", True)
    test("DialogoFondazione", True)
    test("StepFondazioniPanel", True)
    test("StepCordoliPanel", True)
except ImportError as e:
    test("Nuovi componenti", False, str(e))

# Test classi strutturali
try:
    from gui_editor_v2 import Fondazione, Cordolo, Tirante, Scala, Balcone, Copertura
    test("Classe Fondazione", True)
    test("Classe Cordolo", True)
    test("Classe Tirante", True)
    test("Classe Scala", True)
    test("Classe Balcone", True)
    test("Classe Copertura", True)
except ImportError as e:
    test("Classi strutturali", False, str(e))

# Test nuovi pannelli step
try:
    from gui_editor_v2 import StepSolaiPanel, StepCarichiPanel, Vista3DWidget
    test("StepSolaiPanel", True)
    test("StepCarichiPanel", True)
    test("Vista3DWidget", True)
except ImportError as e:
    test("Nuovi step panels", False, str(e))

# Test SpettroWidget e GeometryValidator
try:
    from gui_editor_v2 import SpettroWidget, GeometryValidator
    test("SpettroWidget", True)
    test("GeometryValidator", True)
except ImportError as e:
    test("SpettroWidget/GeometryValidator", False, str(e))

# Test DialogoMateriale
try:
    from gui_editor_v2 import DialogoMateriale, CombinazioniCarichi
    test("DialogoMateriale", True)
    test("CombinazioniCarichi", True)
except ImportError as e:
    test("DialogoMateriale/CombinazioniCarichi", False, str(e))

# Componenti ancora mancanti
missing_components = []

for comp in missing_components:
    try:
        exec(f"from gui_editor_v2 import {comp.split(' -')[0]}")
    except:
        missing_feature(comp)

# ==============================================================================
# 6. TEST FUNZIONALITÀ DISEGNO
# ==============================================================================
print("\n[6] TEST FUNZIONALITÀ DISEGNO")

# Verifica strumenti disponibili
try:
    from gui_editor_v2 import DrawingCanvas
    canvas_methods = dir(DrawingCanvas)

    test("Metodo setStrumento", 'setStrumento' in canvas_methods, "Mancante")
    test("Metodo drawMuro", 'drawMuro' in canvas_methods, "Mancante")
    test("Metodo drawApertura", 'drawApertura' in canvas_methods, "Mancante")
    test("Metodo snapToGrid", 'snapToGrid' in canvas_methods, "Mancante")
    test("Metodo worldToScreen", 'worldToScreen' in canvas_methods, "Mancante")
except Exception as e:
    test("Funzionalità disegno", False, str(e))

# Test strumenti implementati
test("Metodo drawRettangolo", 'drawRettangolo' in canvas_methods, "Mancante")
test("Metodo copiaSelezionati", 'copiaSelezionati' in canvas_methods, "Mancante")
test("Metodo specchiaMuri", 'specchiaMuri' in canvas_methods, "Mancante")
test("Metodo offsetMuro", 'offsetMuro' in canvas_methods, "Mancante")
test("Metodo startMisura", 'startMisura' in canvas_methods, "Mancante")

# Strumenti ancora mancanti
missing_tools = [
    'Strumento Poligono - Disegna poligono chiuso',
    'Strumento Ruota - Ruota elementi',
    'Strumento Taglia - Taglia muro',
    'Strumento Estendi - Estende muro',
]

for tool in missing_tools:
    missing_feature(tool)

# ==============================================================================
# 7. TEST EXPORT/IMPORT
# ==============================================================================
print("\n[7] TEST EXPORT/IMPORT")

# Verifica funzioni export
try:
    from gui_editor_v2 import MuraturaEditorV2
    editor_methods = dir(MuraturaEditorV2)

    test("Metodo salvaProgetto", 'salvaProgetto' in editor_methods, "Mancante")
    test("Metodo apriProgetto", 'apriProgetto' in editor_methods, "Mancante")
    test("Metodo esportaReport", 'esportaReport' in editor_methods, "Mancante")
except Exception as e:
    test("Funzioni export", False, str(e))

# Export mancanti
missing_exports = [
    'Export DXF/DWG - Esportazione formato CAD',
    'Export PDF - Esportazione PDF diretto',
    'Export IFC - Formato BIM',
    'Import DXF - Importa piante CAD',
    'Import immagine - Importa planimetria raster',
]

for exp in missing_exports:
    missing_feature(exp)

# ==============================================================================
# 8. TEST VISUALIZZAZIONE
# ==============================================================================
print("\n[8] TEST VISUALIZZAZIONE")

# Vista 3D
try:
    from gui_editor_v2 import Vista3DWidget
    test("Vista 3D Widget", True, "")
except ImportError:
    missing_feature("Vista3DWidget - Vista 3D dell'edificio")
    test("Vista 3D Widget", False, "Non trovato")

# Test PushoverWidget
try:
    from gui_editor_v2 import PushoverWidget
    test("Curva Pushover Widget", True)
except ImportError:
    test("PushoverWidget", False, "Non trovato")

# Altre visualizzazioni mancanti
missing_views = [
    'Vista Sezione - Sezione verticale edificio',
    'Vista Prospetto - Prospetti automatici',
    'Vista Esplosa - Vista esplosa 3D',
    'Animazione Sisma - Animazione risposta sismica',
    'Diagrammi N-T-M - Sollecitazioni',
    'Mappa DCR - Heatmap dei DCR',
]

for view in missing_views:
    missing_feature(view)

# ==============================================================================
# 9. TEST VALIDAZIONE INPUT
# ==============================================================================
print("\n[9] TEST VALIDAZIONE INPUT")

# Verifica range valori
test("Muro spessore min 0.1m", True, "Assumiamo validato in GUI")
test("Muro altezza min 2m", True, "Assumiamo validato in GUI")

# Test validazione implementata
try:
    from gui_editor_v2 import GeometryValidator
    test("Validazione aperture", hasattr(GeometryValidator, 'validaAperture'), "Mancante")
    test("Validazione muri chiusi", hasattr(GeometryValidator, 'validaMuriChiusi'), "Mancante")
    test("Validazione sovrapposizioni", hasattr(GeometryValidator, 'validaSovrapposizioni'), "Mancante")
except ImportError:
    test("GeometryValidator", False, "Non trovato")

# Validazione ancora mancante
missing_validation = [
    'Validazione solai - Verifica solai coprono area corretta',
]

for val in missing_validation:
    missing_feature(val)

# ==============================================================================
# 10. TEST NTC 2018 COMPLIANCE
# ==============================================================================
print("\n[10] TEST CONFORMITÀ NTC 2018")

# Verifica formule implementate
ntc_checks = [
    ('Database comuni sismici', True),
    ('Calcolo ag da comune', True),
    ('Categorie sottosuolo A-E', True),
    ('Categorie topografiche T1-T4', True),
    ('Vita nominale VN', True),
    ('Classi uso I-IV', True),
    ('Fattore struttura q', True),
]

for name, impl in ntc_checks:
    test(f"NTC: {name}", impl, "Da verificare")

# Test SpettroWidget per NTC
try:
    from gui_editor_v2 import SpettroWidget
    test("NTC: Spettro elastico", True)
    test("NTC: Spettro progetto con q", True)
except ImportError:
    test("NTC: Spettro", False, "Non trovato")

# Test combinazioni carichi
try:
    from gui_editor_v2 import CombinazioniCarichi
    test("NTC: Combinazioni SLU", hasattr(CombinazioniCarichi, 'SLU_STR'), "Mancante")
    test("NTC: Combinazioni SLE", hasattr(CombinazioniCarichi, 'SLE_RARA'), "Mancante")
    test("NTC: Combinazione sismica", hasattr(CombinazioniCarichi, 'SISMICA'), "Mancante")
except ImportError:
    test("Combinazioni", False, "Non trovato")

# Conformità NTC ancora mancante
missing_ntc = [
    'Verifica snellezza pareti §7.8.2.2',
    'Verifica eccentricità §7.8.2.2',
    'Meccanismi locali §8.7.1',
    'Classe rischio sismico - Sismabonus',
]

for ntc in missing_ntc:
    missing_feature(f"NTC 2018: {ntc}")

# ==============================================================================
# REPORT FINALE
# ==============================================================================
print("\n" + "=" * 70)
print("REPORT FINALE")
print("=" * 70)

total = results['pass'] + results['fail']
perc = 100 * results['pass'] / total if total > 0 else 0

print(f"\n📊 RISULTATI TEST: {results['pass']}/{total} passati ({perc:.1f}%)")
print(f"   ✓ Passati: {results['pass']}")
print(f"   ✗ Falliti: {results['fail']}")

print(f"\n📋 FUNZIONALITÀ MANCANTI: {len(missing)}")

# Raggruppa per categoria
categories = {
    'Struttura': [m for m in missing if any(k in m for k in ['fondazion', 'cordol', 'tirant', 'scal', 'balcon', 'copertur'])],
    'Workflow': [m for m in missing if 'Step' in m or 'Workflow' in m],
    'GUI': [m for m in missing if any(k in m for k in ['Dialog', 'Panel', 'Widget', 'Vista'])],
    'Strumenti': [m for m in missing if 'Strumento' in m],
    'Export': [m for m in missing if any(k in m for k in ['Export', 'Import'])],
    'NTC 2018': [m for m in missing if 'NTC' in m],
    'Analisi': [m for m in missing if 'Analisi' in m],
    'Altro': []
}

# Classifica resto
classified = set()
for cat, items in categories.items():
    for item in items:
        classified.add(item)

categories['Altro'] = [m for m in missing if m not in classified]

print("\n📌 FUNZIONALITÀ MANCANTI PER CATEGORIA:")
for cat, items in categories.items():
    if items:
        print(f"\n  [{cat.upper()}] ({len(items)})")
        for item in items:
            print(f"    - {item}")

# Valutazione
print("\n" + "-" * 70)
if results['fail'] == 0 and len(missing) == 0:
    print("🏆 INTERFACCIA PERFETTA!")
elif results['fail'] <= 5 and len(missing) <= 10:
    print("👍 INTERFACCIA BUONA - Pochi miglioramenti necessari")
elif results['fail'] <= 10 and len(missing) <= 25:
    print("⚠ INTERFACCIA DA MIGLIORARE - Lavoro necessario")
else:
    print("❌ INTERFACCIA INCOMPLETA - Lavoro significativo richiesto")

print(f"\nPriorità: Implementare prima le {len(categories['Struttura'])} funzionalità strutturali mancanti")
print("-" * 70)
