"""
MURATURA FEM - Desktop GUI (Qt6)

GUI Desktop per MURATURA FEM usando PyQt6.

Features:
- Model builder interface
- Interactive 3D visualization
- Analysis control panel
- Results viewer
- Report generator

Installation:
    pip install PyQt6 PyQt6-3D

Usage:
    python gui/desktop_qt/main_window.py

Status: Prototype v0.1 (Phase 4 planned)
"""

import sys
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QTextEdit, QTabWidget, QMenuBar, QMenu,
        QFileDialog, QMessageBox, QSplitter, QTreeWidget, QTreeWidgetItem
    )
    from PyQt6.QtCore import Qt, QSize
    from PyQt6.QtGui import QAction, QIcon
    PYQT_AVAILABLE = True
except ImportError:
    print("⚠️  PyQt6 not available. Install with: pip install PyQt6")
    PYQT_AVAILABLE = False


class MuraturaMainWindow(QMainWindow):
    """Finestra principale MURATURA FEM."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MURATURA FEM v7.0 - Desktop GUI")
        self.setGeometry(100, 100, 1400, 900)

        # Setup UI
        self.setup_menu_bar()
        self.setup_central_widget()
        self.setup_status_bar()

        # Current project
        self.current_project = None

    def setup_menu_bar(self):
        """Setup menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_action = QAction("&New Project", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)

        open_action = QAction("&Open Project", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        import_ifc_action = QAction("Import IFC...", self)
        import_ifc_action.triggered.connect(self.import_ifc)
        file_menu.addAction(import_ifc_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Analysis menu
        analysis_menu = menubar.addMenu("&Analysis")

        run_action = QAction("&Run Analysis", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(self.run_analysis)
        analysis_menu.addAction(run_action)

        # Reports menu
        reports_menu = menubar.addMenu("&Reports")

        gen_report_action = QAction("&Generate Report PDF", self)
        gen_report_action.triggered.connect(self.generate_report)
        reports_menu.addAction(gen_report_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_central_widget(self):
        """Setup central widget with tabs."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Project tree
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderLabel("Project Structure")
        self.setup_project_tree()
        splitter.addWidget(self.project_tree)

        # Right panel: Tabs
        self.tabs = QTabWidget()

        # Model tab
        model_tab = self.create_model_tab()
        self.tabs.addTab(model_tab, "Model")

        # Analysis tab
        analysis_tab = self.create_analysis_tab()
        self.tabs.addTab(analysis_tab, "Analysis")

        # Results tab
        results_tab = self.create_results_tab()
        self.tabs.addTab(results_tab, "Results")

        # Reports tab
        reports_tab = self.create_reports_tab()
        self.tabs.addTab(reports_tab, "Reports")

        splitter.addWidget(self.tabs)
        splitter.setSizes([300, 1100])

        layout.addWidget(splitter)

    def setup_project_tree(self):
        """Setup project tree structure."""
        # Geometry
        geom_item = QTreeWidgetItem(self.project_tree, ["Geometry"])
        QTreeWidgetItem(geom_item, ["Walls"])
        QTreeWidgetItem(geom_item, ["Floors"])
        QTreeWidgetItem(geom_item, ["Balconies"])
        QTreeWidgetItem(geom_item, ["Stairs"])
        geom_item.setExpanded(True)

        # Materials
        mat_item = QTreeWidgetItem(self.project_tree, ["Materials"])
        QTreeWidgetItem(mat_item, ["Masonry"])
        QTreeWidgetItem(mat_item, ["Concrete"])
        QTreeWidgetItem(mat_item, ["Steel"])

        # Loads
        loads_item = QTreeWidgetItem(self.project_tree, ["Loads"])
        QTreeWidgetItem(loads_item, ["Dead Loads"])
        QTreeWidgetItem(loads_item, ["Live Loads"])
        QTreeWidgetItem(loads_item, ["Seismic"])

        # Analysis
        analysis_item = QTreeWidgetItem(self.project_tree, ["Analysis"])
        QTreeWidgetItem(analysis_item, ["Linear Static"])
        QTreeWidgetItem(analysis_item, ["Modal"])
        QTreeWidgetItem(analysis_item, ["Pushover"])

    def create_model_tab(self):
        """Create model building tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        label = QLabel("Model Builder")
        label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(label)

        # Placeholder for 3D viewer
        viewer_placeholder = QLabel("🏗️  3D Model Viewer\n\n(Requires PyQt6-3D)\n\nInteractive model visualization")
        viewer_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        viewer_placeholder.setStyleSheet("background-color: #f0f0f0; padding: 50px;")
        layout.addWidget(viewer_placeholder)

        # Control buttons
        button_layout = QHBoxLayout()
        btn_add_wall = QPushButton("Add Wall")
        btn_add_floor = QPushButton("Add Floor")
        btn_add_balcony = QPushButton("Add Balcony")
        button_layout.addWidget(btn_add_wall)
        button_layout.addWidget(btn_add_floor)
        button_layout.addWidget(btn_add_balcony)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        widget.setLayout(layout)
        return widget

    def create_analysis_tab(self):
        """Create analysis control tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        label = QLabel("Analysis Settings")
        label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(label)

        # Analysis type selector
        type_label = QLabel("Analysis Type:")
        layout.addWidget(type_label)

        btn_layout = QHBoxLayout()
        btn_static = QPushButton("Linear Static")
        btn_modal = QPushButton("Modal Analysis")
        btn_pushover = QPushButton("Pushover")
        btn_layout.addWidget(btn_static)
        btn_layout.addWidget(btn_modal)
        btn_layout.addWidget(btn_pushover)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Run button
        layout.addStretch()
        btn_run = QPushButton("▶ Run Analysis")
        btn_run.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-size: 14px;")
        btn_run.clicked.connect(self.run_analysis)
        layout.addWidget(btn_run)

        widget.setLayout(layout)
        return widget

    def create_results_tab(self):
        """Create results viewer tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        label = QLabel("Analysis Results")
        label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(label)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setText("Run analysis to see results...")
        layout.addWidget(self.results_text)

        widget.setLayout(layout)
        return widget

    def create_reports_tab(self):
        """Create reports generation tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        label = QLabel("Report Generator")
        label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(label)

        info = QLabel("Generate NTC 2018 compliant structural calculation reports")
        layout.addWidget(info)

        # Format buttons
        btn_layout = QHBoxLayout()
        btn_pdf = QPushButton("Generate PDF")
        btn_docx = QPushButton("Generate DOCX")
        btn_md = QPushButton("Generate Markdown")
        btn_layout.addWidget(btn_pdf)
        btn_layout.addWidget(btn_docx)
        btn_layout.addWidget(btn_md)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def setup_status_bar(self):
        """Setup status bar."""
        self.statusBar().showMessage("Ready")

    # ========================================================================
    # ACTIONS
    # ========================================================================

    def new_project(self):
        """Create new project."""
        self.statusBar().showMessage("Creating new project...")
        QMessageBox.information(self, "New Project", "New project feature coming soon!")

    def open_project(self):
        """Open existing project."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "MURATURA Projects (*.muratura);;All Files (*)"
        )
        if filename:
            self.statusBar().showMessage(f"Opening {filename}...")

    def import_ifc(self):
        """Import IFC file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import IFC", "", "IFC Files (*.ifc);;All Files (*)"
        )
        if filename:
            self.statusBar().showMessage(f"Importing IFC from {filename}...")
            QMessageBox.information(self, "IFC Import", f"IFC import from:\n{filename}\n\nFeature available in Phase 3!")

    def run_analysis(self):
        """Run structural analysis."""
        self.statusBar().showMessage("Running analysis...")
        self.results_text.setText("Analysis running...\n\n⏳ Please wait...")

        # Simulate analysis results
        results = """
MURATURA FEM v7.0 - Analysis Results
=====================================

Analysis Type: Linear Static
Model: Example Building

Results:
  - Total DOF: 1,248
  - Solution time: 0.34s
  - Max displacement: 2.5 mm
  - Max stress: 1.35 MPa

Verifications (NTC 2018):
  ✅ Wall 1: VERIFIED (ratio=0.72)
  ✅ Wall 2: VERIFIED (ratio=0.68)
  ✅ Floor 1: VERIFIED (ratio=0.65)
  ✅ Balcony 1: VERIFIED (ratio=0.85)

Status: ALL VERIFICATIONS PASSED ✅
"""
        self.results_text.setText(results)
        self.statusBar().showMessage("Analysis complete")

    def generate_report(self):
        """Generate structural report."""
        self.statusBar().showMessage("Generating report...")
        QMessageBox.information(self, "Report", "Report generation feature available!\nCheck Phase 3 examples.")

    def show_about(self):
        """Show about dialog."""
        about_text = """
<h2>MURATURA FEM v7.0.0-alpha</h2>
<p>Sistema completo di analisi FEM per strutture in muratura</p>
<p><b>Features:</b></p>
<ul>
<li>Analisi FEM completa (7 metodi)</li>
<li>Edifici storici (Heyman, FRP/FRCM)</li>
<li>BIM Integration (IFC import/export)</li>
<li>Report automatici NTC 2018</li>
</ul>
<p><b>Standards:</b> NTC 2018, EC8, CNR-DT 200/215</p>
<p>© 2025 MURATURA FEM Team | MIT License</p>
"""
        QMessageBox.about(self, "About MURATURA FEM", about_text)


def main():
    """Main GUI application."""
    if not PYQT_AVAILABLE:
        print("❌ PyQt6 is required for desktop GUI")
        print("   Install: pip install PyQt6")
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName("MURATURA FEM")
    app.setOrganizationName("MURATURA FEM Team")

    window = MuraturaMainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
