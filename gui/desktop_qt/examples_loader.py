"""
MURATURA FEM - Examples Loader

Caricamento e esecuzione esempi predefiniti.
"""

import sys
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QTextEdit, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class ExampleRunnerThread(QThread):
    """Thread per eseguire esempi in background."""

    output_ready = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, example_path):
        super().__init__()
        self.example_path = example_path

    def run(self):
        """Run example script."""
        try:
            result = subprocess.run(
                [sys.executable, str(self.example_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=Path(self.example_path).parent.parent
            )

            output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            self.output_ready.emit(output)

            if result.returncode == 0:
                self.finished_signal.emit(True, "Example completed successfully!")
            else:
                self.finished_signal.emit(False, f"Example failed with code {result.returncode}")

        except subprocess.TimeoutExpired:
            self.finished_signal.emit(False, "Example timed out (>30s)")
        except Exception as e:
            self.finished_signal.emit(False, f"Error: {str(e)}")


class ExamplesDialog(QDialog):
    """Dialog per selezionare e eseguire esempi."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load Example")
        self.setModal(True)
        self.resize(800, 600)
        self.setup_ui()
        self.load_examples()
        self.runner_thread = None

    def setup_ui(self):
        layout = QVBoxLayout()

        # Title
        title = QLabel("📚 MURATURA FEM Examples")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        info = QLabel("Select an example to view details or run it directly.")
        layout.addWidget(info)

        # Examples list
        self.examples_list = QListWidget()
        self.examples_list.currentItemChanged.connect(self.on_example_selected)
        layout.addWidget(self.examples_list)

        # Description
        desc_label = QLabel("Description:")
        desc_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(desc_label)

        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setMaximumHeight(100)
        layout.addWidget(self.description_text)

        # Output
        output_label = QLabel("Output:")
        output_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(output_label)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(150)
        layout.addWidget(self.output_text)

        # Buttons
        button_layout = QHBoxLayout()

        self.btn_run = QPushButton("▶ Run Example")
        self.btn_run.clicked.connect(self.run_example)
        self.btn_run.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        button_layout.addWidget(self.btn_run)

        self.btn_load = QPushButton("Load into GUI")
        self.btn_load.clicked.connect(self.load_into_gui)
        button_layout.addWidget(self.btn_load)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.reject)
        button_layout.addWidget(btn_close)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_examples(self):
        """Load available examples."""
        self.examples = {
            "01 - Pushover Analysis": {
                "file": "examples/01_pushover_simple.py",
                "desc": "Simple pushover analysis for seismic assessment of masonry building."
            },
            "02 - Modal Analysis": {
                "file": "examples/02_modal_analysis.py",
                "desc": "Modal analysis to compute natural frequencies and mode shapes."
            },
            "03 - SAM Verification": {
                "file": "examples/03_sam_verification.py",
                "desc": "Simplified Analysis Method (SAM) verification according to NTC 2018."
            },
            "04 - Floor Design": {
                "file": "examples/04_floor_design.py",
                "desc": "Design of latero-cemento floor system with reinforcement calculation."
            },
            "05 - Balcony Design": {
                "file": "examples/05_balcony_design.py",
                "desc": "Balcony design with critical anchorage verification."
            },
            "06 - Stair Design": {
                "file": "examples/06_stair_design.py",
                "desc": "Stair design according to DM 236/89 and NTC 2018."
            },
            "07 - Arch Analysis": {
                "file": "examples/07_arch_analysis.py",
                "desc": "Historic arch analysis using Heyman's limit analysis."
            },
            "08 - Vault Analysis": {
                "file": "examples/08_vault_analysis.py",
                "desc": "3D vault analysis with innovative Heyman method."
            },
            "09 - FRP/FRCM Strengthening": {
                "file": "examples/09_strengthening_design.py",
                "desc": "FRP and FRCM strengthening design according to CNR-DT 200/215."
            },
            "10 - Knowledge Levels": {
                "file": "examples/10_knowledge_levels.py",
                "desc": "Knowledge levels (LC1/LC2/LC3) for existing buildings."
            },
            "11 - IFC Import": {
                "file": "examples/11_ifc_import_bim.py",
                "desc": "Import BIM model from Revit/ArchiCAD IFC file."
            },
            "12 - Report Generation": {
                "file": "examples/12_report_generation.py",
                "desc": "Generate NTC 2018 compliant PDF structural calculation report."
            },
            "13 - Custom Templates": {
                "file": "examples/13_custom_templates.py",
                "desc": "Custom LaTeX templates for report generation."
            },
            "14 - IFC Workflow": {
                "file": "examples/14_ifc_workflow_complete.py",
                "desc": "Complete IFC workflow: import → analysis → export."
            },
            "15 - Complete Workflow": {
                "file": "examples/15_complete_workflow_integration.py",
                "desc": "⭐ COMPLETE: BIM import → FEM analysis → Report generation → IFC export."
            }
        }

        for name in self.examples.keys():
            self.examples_list.addItem(name)

    def on_example_selected(self, current, previous):
        """Handle example selection."""
        if current:
            example_name = current.text()
            example_data = self.examples.get(example_name, {})
            self.description_text.setText(example_data.get('desc', ''))
            self.output_text.clear()

    def run_example(self):
        """Run selected example."""
        current_item = self.examples_list.currentItem()
        if not current_item:
            self.output_text.setText("⚠️ Please select an example first!")
            return

        example_name = current_item.text()
        example_data = self.examples.get(example_name, {})
        example_file = example_data.get('file', '')

        if not example_file:
            self.output_text.setText("❌ Example file not found!")
            return

        example_path = Path(__file__).parent.parent.parent / example_file

        if not example_path.exists():
            self.output_text.setText(f"❌ Example file not found:\n{example_path}")
            return

        # Disable button during execution
        self.btn_run.setEnabled(False)
        self.btn_run.setText("⏳ Running...")
        self.output_text.setText(f"🏃 Running: {example_file}\n\nPlease wait...")

        # Run in thread
        self.runner_thread = ExampleRunnerThread(example_path)
        self.runner_thread.output_ready.connect(self.on_output_ready)
        self.runner_thread.finished_signal.connect(self.on_run_finished)
        self.runner_thread.start()

    def on_output_ready(self, output):
        """Handle output from example."""
        self.output_text.setText(output)

    def on_run_finished(self, success, message):
        """Handle example completion."""
        self.btn_run.setEnabled(True)
        self.btn_run.setText("▶ Run Example")

        current_output = self.output_text.toPlainText()
        status = "✅ SUCCESS" if success else "❌ FAILED"
        self.output_text.setText(f"{current_output}\n\n{status}: {message}")

    def load_into_gui(self):
        """Load example configuration into GUI."""
        current_item = self.examples_list.currentItem()
        if not current_item:
            self.output_text.setText("⚠️ Please select an example first!")
            return

        # This would load example parameters into main GUI
        # For now, just show message
        self.output_text.setText("📥 Loading example into GUI...\n\n⚠️ Feature coming soon!\nFor now, use 'Run Example' to execute the example.")

    def get_selected_example(self):
        """Get selected example file path."""
        current_item = self.examples_list.currentItem()
        if current_item:
            example_name = current_item.text()
            example_data = self.examples.get(example_name, {})
            return example_data.get('file', None)
        return None
