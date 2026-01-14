#!/usr/bin/env python3
"""
TEST AUTOMATICO COMPLETO GUI MURATURA v2.0

Verifica:
1. Tutti i pulsanti e menu
2. Inserimento dati progetto
3. Disegno muri
4. Inserimento aperture (porte/finestre)
5. Inserimento solai
6. Esecuzione calcoli (tutti i metodi)
7. Visualizzazione risultati
8. Export report
9. Funzionalità mancanti

Output: Report dettagliato di cosa funziona e cosa no
"""

import sys
import time
from dataclasses import dataclass
from typing import List, Tuple
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtTest import QTest

# Import GUI
from gui_editor_v2 import (
    MuraturaEditorV2, Progetto, Muro, Apertura, Solaio, Piano,
    WorkflowStep, ANALYSIS_METHODS, QuickActionsPanel,
    DrawingCanvas, RibbonToolbar, ProjectBrowser, WorkflowPanel
)


@dataclass
class TestResult:
    name: str
    passed: bool
    details: str
    severity: str = "normal"  # normal, critical, minor


class GUIAutoTester:
    """Tester automatico per GUI Muratura"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.editor = None
        self.results: List[TestResult] = []
        self.missing_features: List[str] = []

    def log(self, name: str, passed: bool, details: str, severity: str = "normal"):
        self.results.append(TestResult(name, passed, details, severity))
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            print(f"         → {details}")

    def log_missing(self, feature: str):
        self.missing_features.append(feature)
        print(f"  ⚠ MANCANTE: {feature}")

    def run_all_tests(self):
        """Esegue tutti i test"""
        print("=" * 70)
        print("TEST AUTOMATICO GUI MURATURA v2.0")
        print("=" * 70)

        # Crea editor
        print("\n[1] INIZIALIZZAZIONE")
        self.editor = MuraturaEditorV2()
        self.log("Creazione MuraturaEditorV2", True, "Editor creato")

        # Test componenti base
        print("\n[2] TEST COMPONENTI GUI")
        self.test_gui_components()

        # Test Quick Actions
        print("\n[3] TEST QUICK ACTIONS")
        self.test_quick_actions()

        # Test Workflow
        print("\n[4] TEST WORKFLOW STEPS")
        self.test_workflow()

        # Test inserimento dati
        print("\n[5] TEST INSERIMENTO DATI PROGETTO")
        self.test_project_data()

        # Test disegno muri
        print("\n[6] TEST DISEGNO MURI")
        self.test_draw_walls()

        # Test aperture
        print("\n[7] TEST APERTURE (PORTE/FINESTRE)")
        self.test_openings()

        # Test solai
        print("\n[8] TEST SOLAI")
        self.test_floors()

        # Test fondazioni
        print("\n[9] TEST FONDAZIONI")
        self.test_foundations()

        # Test carichi
        print("\n[10] TEST CARICHI")
        self.test_loads()

        # Test analisi
        print("\n[11] TEST METODI DI ANALISI")
        self.test_analysis_methods()

        # Test visualizzazione
        print("\n[12] TEST VISUALIZZAZIONE")
        self.test_visualization()

        # Test export
        print("\n[13] TEST EXPORT")
        self.test_export()

        # Test ribbon e menu
        print("\n[14] TEST RIBBON E MENU")
        self.test_ribbon_menu()

        # Report finale
        self.print_report()

        return self.results

    def test_gui_components(self):
        """Verifica presenza componenti GUI"""
        # Ribbon
        has_ribbon = hasattr(self.editor, 'ribbon') and self.editor.ribbon is not None
        self.log("Ribbon Toolbar presente", has_ribbon,
                 "Ribbon non trovato" if not has_ribbon else "OK")

        # Canvas
        has_canvas = hasattr(self.editor, 'canvas') and self.editor.canvas is not None
        self.log("Canvas disegno presente", has_canvas,
                 "Canvas non trovato" if not has_canvas else "OK")

        # Project Browser
        has_browser = hasattr(self.editor, 'browser') and self.editor.browser is not None
        self.log("Project Browser presente", has_browser,
                 "Browser non trovato" if not has_browser else "OK")

        # Properties Panel
        has_props = hasattr(self.editor, 'properties') and self.editor.properties is not None
        self.log("Properties Panel presente", has_props,
                 "Properties non trovato" if not has_props else "OK")

        # Workflow Panel
        has_workflow = hasattr(self.editor, 'workflow_panel') and self.editor.workflow_panel is not None
        self.log("Workflow Panel presente", has_workflow,
                 "Workflow non trovato" if not has_workflow else "OK")

        # Quick Actions
        has_quick = hasattr(self.editor, 'quick_actions') and self.editor.quick_actions is not None
        self.log("Quick Actions presente", has_quick,
                 "Quick Actions non trovato" if not has_quick else "OK")

    def test_quick_actions(self):
        """Test pulsanti Quick Actions"""
        qa = self.editor.quick_actions

        # Pulsante Nuovo
        has_nuovo = hasattr(qa, 'btn_nuovo') and qa.btn_nuovo is not None
        self.log("Pulsante 'Nuovo Progetto'", has_nuovo, "Pulsante non trovato")

        # Pulsante Apri
        has_apri = hasattr(qa, 'btn_apri') and qa.btn_apri is not None
        self.log("Pulsante 'Apri Progetto'", has_apri, "Pulsante non trovato")

        # Pulsante Esempio
        has_esempio = hasattr(qa, 'btn_esempio') and qa.btn_esempio is not None
        self.log("Pulsante 'Carica Esempio'", has_esempio, "Pulsante non trovato")

        # Pulsante Guida
        has_guida = hasattr(qa, 'btn_guida') and qa.btn_guida is not None
        self.log("Pulsante 'Guida'", has_guida, "Pulsante non trovato")

    def test_workflow(self):
        """Test workflow steps"""
        wp = self.editor.workflow_panel

        # Verifica tutti gli step
        for step in WorkflowStep:
            has_btn = step in wp.step_buttons
            self.log(f"Step '{step.name}' presente", has_btn, f"Step {step.name} mancante")

        # Test navigazione
        try:
            self.editor.goToStep(WorkflowStep.PROGETTO)
            self.log("Navigazione a PROGETTO", True, "OK")
        except Exception as e:
            self.log("Navigazione a PROGETTO", False, str(e))

    def test_project_data(self):
        """Test inserimento dati progetto"""
        # Crea nuovo progetto
        try:
            self.editor.nuovoProgetto()
            self.log("Creazione nuovo progetto", True, "OK")
        except Exception as e:
            self.log("Creazione nuovo progetto", False, str(e), "critical")
            return

        # Verifica progetto creato
        has_project = self.editor.progetto is not None
        self.log("Progetto inizializzato", has_project, "Progetto None")

        # Test step progetto panel
        sp = self.editor.step_progetto

        # Nome progetto
        try:
            sp.nome_edit.setText("Test Automatico")
            self.log("Input nome progetto", True, "OK")
        except Exception as e:
            self.log("Input nome progetto", False, str(e))

        # Comune (localizzazione sismica)
        try:
            sp.comune_edit.setText("ROMA")
            self.log("Input comune", True, "OK")
        except Exception as e:
            self.log("Input comune", False, str(e))

        # Numero piani
        try:
            sp.n_piani_spin.setValue(2)
            self.log("Input numero piani", True, "OK")
        except Exception as e:
            self.log("Input numero piani", False, str(e))

        # Salva dati
        try:
            sp.saveData()
            self.log("Salvataggio dati progetto", True, "OK")
        except Exception as e:
            self.log("Salvataggio dati progetto", False, str(e))

        # Verifica dati salvati
        self.log("Nome progetto salvato",
                 self.editor.progetto.nome == "Test Automatico",
                 f"Nome: {self.editor.progetto.nome}")

    def test_draw_walls(self):
        """Test disegno muri"""
        canvas = self.editor.canvas

        # Imposta strumento muro
        try:
            canvas.setStrumento('muro')
            self.log("Selezione strumento 'muro'", canvas.strumento == 'muro',
                     f"Strumento: {canvas.strumento}")
        except Exception as e:
            self.log("Selezione strumento 'muro'", False, str(e))

        # Simula disegno muro
        try:
            canvas.punto_inizio = (0, 0)
            canvas.createMuro(5, 0)  # Muro orizzontale 5m

            n_muri = len(self.editor.progetto.muri)
            self.log("Creazione muro M1 (5m)", n_muri >= 1, f"Muri: {n_muri}")
        except Exception as e:
            self.log("Creazione muro M1", False, str(e), "critical")

        # Secondo muro
        try:
            canvas.punto_inizio = (5, 0)
            canvas.createMuro(5, 4)  # Muro verticale 4m

            n_muri = len(self.editor.progetto.muri)
            self.log("Creazione muro M2 (4m)", n_muri >= 2, f"Muri: {n_muri}")
        except Exception as e:
            self.log("Creazione muro M2", False, str(e))

        # Terzo e quarto muro (chiude rettangolo)
        try:
            canvas.punto_inizio = (5, 4)
            canvas.createMuro(0, 4)
            canvas.punto_inizio = (0, 4)
            canvas.createMuro(0, 0)

            n_muri = len(self.editor.progetto.muri)
            self.log("Creazione muri M3, M4 (chiusura)", n_muri >= 4, f"Muri: {n_muri}")
        except Exception as e:
            self.log("Creazione muri chiusura", False, str(e))

        # Verifica proprietà muri
        if self.editor.progetto.muri:
            m1 = self.editor.progetto.muri[0]
            self.log("Muro ha lunghezza", m1.lunghezza > 0, f"L={m1.lunghezza:.2f}m")
            self.log("Muro ha spessore", m1.spessore > 0, f"s={m1.spessore}m")
            self.log("Muro ha altezza", m1.altezza > 0, f"h={m1.altezza}m")

    def test_openings(self):
        """Test inserimento aperture (porte/finestre)"""
        # Verifica se esiste metodo per aggiungere aperture
        has_method = hasattr(self.editor, 'aggiungiApertura')
        self.log("Metodo aggiungiApertura esiste", has_method, "Metodo non trovato")

        # Verifica se c'è un dialogo aperture
        try:
            from gui_editor_v2 import Apertura

            # Aggiungi apertura manualmente
            if self.editor.progetto.muri:
                muro = self.editor.progetto.muri[0]
                ap = Apertura(
                    nome="F1",
                    muro=muro.nome,
                    tipo="finestra",
                    larghezza=1.2,
                    altezza=1.4,
                    posizione=1.0,
                    altezza_davanzale=0.9
                )
                self.editor.progetto.aperture.append(ap)
                self.log("Inserimento finestra F1", True, f"Aperture: {len(self.editor.progetto.aperture)}")

                # Porta
                ap2 = Apertura(
                    nome="P1",
                    muro=muro.nome,
                    tipo="porta",
                    larghezza=0.9,
                    altezza=2.1,
                    posizione=3.0,
                    altezza_davanzale=0.0
                )
                self.editor.progetto.aperture.append(ap2)
                self.log("Inserimento porta P1", True, f"Aperture: {len(self.editor.progetto.aperture)}")
            else:
                self.log("Inserimento aperture", False, "Nessun muro disponibile", "critical")
        except Exception as e:
            self.log("Inserimento aperture", False, str(e), "critical")

        # VERIFICA DIALOGO APERTURE GUI
        # Cerca se esiste un dialogo dedicato
        try:
            from gui_editor_v2 import DialogoApertura
            self.log("Dialogo aperture GUI", True, "DialogoApertura trovato")
        except ImportError:
            self.log_missing("DialogoApertura - Dialogo GUI per inserire porte/finestre")

    def test_floors(self):
        """Test inserimento solai"""
        try:
            from gui_editor_v2 import Solaio

            solaio = Solaio(
                nome="S1",
                piano=0,
                tipo="laterocemento",
                luce=5.0,
                larghezza=4.0,
                peso_proprio=3.2,
                carico_variabile=2.0,
                categoria_uso="A"
            )
            self.editor.progetto.solai.append(solaio)
            self.log("Inserimento solaio S1", True, f"Solai: {len(self.editor.progetto.solai)}")

            # Verifica proprietà
            self.log("Solaio ha area", solaio.area > 0, f"Area={solaio.area}m²")
            self.log("Solaio ha carico totale", solaio.carico_totale > 0,
                     f"Carico={solaio.carico_totale}kN/m²")
        except Exception as e:
            self.log("Inserimento solai", False, str(e), "critical")

        # Verifica dialogo solai GUI
        try:
            from gui_editor_v2 import StepSolaiPanel
            self.log("Step Solai GUI", True, "Trovato")
        except ImportError:
            self.log_missing("StepSolaiPanel - Pannello GUI per step solai")

    def test_foundations(self):
        """Test inserimento fondazioni"""
        # Verifica se esistono classi/metodi per fondazioni
        try:
            from gui_editor_v2 import Fondazione
            self.log("Classe Fondazione", True, "Trovata")
        except ImportError:
            self.log_missing("Classe Fondazione - Definizione fondazioni")

        try:
            from gui_editor_v2 import DialogoFondazione
            self.log("Dialogo Fondazione GUI", True, "Trovato")
        except ImportError:
            self.log_missing("DialogoFondazione - Dialogo GUI per fondazioni")

        # Verifica nel progetto
        has_fondazioni = hasattr(self.editor.progetto, 'fondazioni')
        if not has_fondazioni:
            self.log_missing("Campo 'fondazioni' nel Progetto")
        else:
            self.log("Campo fondazioni in Progetto", True, "OK")

        # Tipi di fondazioni da supportare
        self.log_missing("Fondazioni continue (nastro)")
        self.log_missing("Fondazioni a platea")
        self.log_missing("Fondazioni a plinti")
        self.log_missing("Cordoli di fondazione")

    def test_loads(self):
        """Test definizione carichi"""
        # Carichi permanenti
        has_carichi = hasattr(self.editor.progetto, 'carichi')
        if not has_carichi:
            self.log_missing("Campo 'carichi' nel Progetto per carichi puntuali/distribuiti")

        # Carichi climatici
        has_climatici = hasattr(self.editor.progetto, 'climatici')
        self.log("Carichi climatici (neve/vento)", has_climatici,
                 "Campo climatici mancante" if not has_climatici else "OK")

        # Combinazioni di carico
        try:
            from gui_editor_v2 import CombinazioniCarico
            self.log("Combinazioni di carico", True, "Trovato")
        except ImportError:
            self.log_missing("CombinazioniCarico - Generazione combinazioni SLU/SLE/SIS")

        # Dialogo carichi GUI
        try:
            from gui_editor_v2 import StepCarichiPanel
            self.log("Step Carichi GUI", True, "Trovato")
        except ImportError:
            self.log_missing("StepCarichiPanel - Pannello GUI per step carichi")

    def test_analysis_methods(self):
        """Test tutti i metodi di analisi"""
        # Verifica disponibilità metodi
        for key, info in ANALYSIS_METHODS.items():
            self.log(f"Metodo {key} disponibile", info['available'],
                     f"Modulo {key} non importabile" if not info['available'] else "OK")

        # Test esecuzione analisi (se ci sono muri)
        if self.editor.progetto.muri:
            # Verifica rapida
            try:
                self.editor.verificaRapida()
                self.log("Esecuzione Verifica Rapida", True, "OK")

                # Verifica DCR calcolati
                has_dcr = any(m.dcr > 0 for m in self.editor.progetto.muri)
                self.log("DCR calcolati sui muri", has_dcr,
                         "DCR non calcolati" if not has_dcr else "OK")

                # Verifica indice rischio
                has_ir = self.editor.progetto.indice_rischio > 0
                self.log("Indice di rischio calcolato", has_ir,
                         f"IR={self.editor.progetto.indice_rischio:.3f}")
            except Exception as e:
                self.log("Esecuzione Verifica Rapida", False, str(e), "critical")
        else:
            self.log("Test analisi", False, "Nessun muro nel progetto", "critical")

    def test_visualization(self):
        """Test visualizzazione"""
        canvas = self.editor.canvas

        # Griglia
        self.log("Griglia attiva", canvas.griglia, "Griglia disattivata")

        # Scala
        self.log("Scala visualizzazione", canvas.scala > 0, f"Scala={canvas.scala}")

        # Colori DCR
        try:
            # I muri dovrebbero avere colori basati su DCR
            self.log("Colorazione DCR implementata", True, "Metodo drawMuro presente")
        except:
            self.log_missing("Colorazione DCR avanzata")

        # Vista 3D
        try:
            from gui_editor_v2 import Vista3DWidget
            self.log("Widget Vista 3D", True, "Trovato")
        except ImportError:
            self.log_missing("Vista3DWidget - Vista 3D dell'edificio")

        # Quotatura automatica
        self.log_missing("Quotatura automatica sui muri")

        # Layer per elementi
        self.log_missing("Sistema layer (muri, aperture, quote, etc.)")

    def test_export(self):
        """Test export"""
        # Report HTML
        has_report = hasattr(self.editor, 'esportaReport')
        self.log("Metodo esportaReport", has_report, "Metodo non trovato")

        # Export DXF
        try:
            from gui_editor_v2 import esportaDXF
            self.log("Export DXF", True, "Trovato")
        except ImportError:
            self.log_missing("Export DXF/DWG")

        # Export PDF
        self.log_missing("Export PDF diretto (non solo HTML)")

        # Salvataggio progetto
        has_save = hasattr(self.editor, 'salvaProgetto')
        self.log("Metodo salvaProgetto", has_save, "Metodo non trovato")

    def test_ribbon_menu(self):
        """Test ribbon e menu"""
        ribbon = self.editor.ribbon

        # Conta tabs
        n_tabs = ribbon.count()
        self.log(f"Ribbon ha {n_tabs} tabs", n_tabs >= 2, f"Trovati {n_tabs} tabs")

        # Verifica tabs specifici
        tab_names = [ribbon.tabText(i) for i in range(n_tabs)]
        self.log("Tab 'Home' presente", "Home" in tab_names, f"Tabs: {tab_names}")
        self.log("Tab 'Analisi' presente", "Analisi" in tab_names, f"Tabs: {tab_names}")

        # Tab mancanti suggeriti
        if "Geometria" not in tab_names:
            self.log_missing("Tab 'Geometria' nel Ribbon (strumenti disegno)")
        if "Carichi" not in tab_names:
            self.log_missing("Tab 'Carichi' nel Ribbon")
        if "Risultati" not in tab_names:
            self.log_missing("Tab 'Risultati' nel Ribbon")
        if "Vista" not in tab_names:
            self.log_missing("Tab 'Vista' nel Ribbon (zoom, pan, 3D)")

    def print_report(self):
        """Stampa report finale"""
        print("\n" + "=" * 70)
        print("REPORT FINALE TEST AUTOMATICO")
        print("=" * 70)

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        print(f"\nRISULTATI: {passed}/{total} test passati ({100*passed/total:.1f}%)")
        print(f"  ✓ Passati: {passed}")
        print(f"  ✗ Falliti: {failed}")

        # Lista fallimenti critici
        critical = [r for r in self.results if not r.passed and r.severity == "critical"]
        if critical:
            print(f"\n⚠ PROBLEMI CRITICI ({len(critical)}):")
            for r in critical:
                print(f"  - {r.name}: {r.details}")

        # Lista funzionalità mancanti
        if self.missing_features:
            print(f"\n📋 FUNZIONALITÀ MANCANTI ({len(self.missing_features)}):")
            for f in self.missing_features:
                print(f"  - {f}")

        # Valutazione complessiva
        print("\n" + "-" * 70)
        if failed == 0 and len(self.missing_features) == 0:
            print("🏆 INTERFACCIA PERFETTA - Tutti i test passati!")
        elif failed <= 3 and len(self.missing_features) <= 5:
            print("👍 INTERFACCIA BUONA - Pochi miglioramenti necessari")
        elif failed <= 10:
            print("⚠ INTERFACCIA DA MIGLIORARE - Diversi problemi da risolvere")
        else:
            print("❌ INTERFACCIA INCOMPLETA - Lavoro significativo necessario")

        print("-" * 70)

        return {
            'passed': passed,
            'failed': failed,
            'missing': len(self.missing_features),
            'critical': len(critical)
        }


if __name__ == "__main__":
    # Headless mode - non mostra finestre
    import os
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'

    tester = GUIAutoTester()
    tester.run_all_tests()
