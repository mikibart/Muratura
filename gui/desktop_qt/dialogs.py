"""
MURATURA FEM - Input Dialogs

Dialog windows per input di dati strutturali.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QDoubleSpinBox, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt


class AddWallDialog(QDialog):
    """Dialog per aggiungere una parete."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Wall")
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Form layout
        form = QFormLayout()

        # Name
        self.name_input = QLineEdit("Wall 1")
        form.addRow("Name:", self.name_input)

        # Geometry
        geom_group = QGroupBox("Geometry")
        geom_layout = QFormLayout()

        self.length_input = QDoubleSpinBox()
        self.length_input.setRange(0.1, 100.0)
        self.length_input.setValue(5.0)
        self.length_input.setSuffix(" m")
        self.length_input.setDecimals(2)
        geom_layout.addRow("Length:", self.length_input)

        self.height_input = QDoubleSpinBox()
        self.height_input.setRange(0.1, 50.0)
        self.height_input.setValue(3.0)
        self.height_input.setSuffix(" m")
        self.height_input.setDecimals(2)
        geom_layout.addRow("Height:", self.height_input)

        self.thickness_input = QDoubleSpinBox()
        self.thickness_input.setRange(0.05, 2.0)
        self.thickness_input.setValue(0.3)
        self.thickness_input.setSuffix(" m")
        self.thickness_input.setDecimals(2)
        geom_layout.addRow("Thickness:", self.thickness_input)

        geom_group.setLayout(geom_layout)
        layout.addWidget(geom_group)

        # Material
        mat_group = QGroupBox("Material")
        mat_layout = QFormLayout()

        self.material_combo = QComboBox()
        self.material_combo.addItems([
            "Masonry - Brick (f_mk=2.4 MPa)",
            "Masonry - Stone (f_mk=1.8 MPa)",
            "Masonry - Tuff (f_mk=1.2 MPa)",
            "Custom..."
        ])
        mat_layout.addRow("Material:", self.material_combo)

        mat_group.setLayout(mat_layout)
        layout.addWidget(mat_group)

        # Buttons
        button_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_values(self):
        """Get wall parameters."""
        return {
            'name': self.name_input.text(),
            'length': self.length_input.value(),
            'height': self.height_input.value(),
            'thickness': self.thickness_input.value(),
            'material': self.material_combo.currentText()
        }


class AddMaterialDialog(QDialog):
    """Dialog per aggiungere un materiale."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Material")
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Material type
        type_group = QGroupBox("Material Type")
        type_layout = QFormLayout()

        self.name_input = QLineEdit("Muratura Mattoni")
        type_layout.addRow("Name:", self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Masonry", "Concrete", "Steel"])
        self.type_combo.currentTextChanged.connect(self.update_defaults)
        type_layout.addRow("Type:", self.type_combo)

        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # Mechanical properties
        mech_group = QGroupBox("Mechanical Properties")
        mech_layout = QFormLayout()

        self.fmk_input = QDoubleSpinBox()
        self.fmk_input.setRange(0.1, 20.0)
        self.fmk_input.setValue(2.4)
        self.fmk_input.setSuffix(" MPa")
        self.fmk_input.setDecimals(2)
        mech_layout.addRow("f_mk (Compressive):", self.fmk_input)

        self.E_input = QDoubleSpinBox()
        self.E_input.setRange(100, 50000)
        self.E_input.setValue(1500)
        self.E_input.setSuffix(" MPa")
        self.E_input.setDecimals(0)
        mech_layout.addRow("E (Elastic Modulus):", self.E_input)

        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(1.0, 30.0)
        self.weight_input.setValue(18.0)
        self.weight_input.setSuffix(" kN/m³")
        self.weight_input.setDecimals(1)
        mech_layout.addRow("γ (Weight):", self.weight_input)

        mech_group.setLayout(mech_layout)
        layout.addWidget(mech_group)

        # Buttons
        button_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def update_defaults(self, material_type):
        """Update default values based on material type."""
        if material_type == "Masonry":
            self.fmk_input.setValue(2.4)
            self.E_input.setValue(1500)
            self.weight_input.setValue(18.0)
        elif material_type == "Concrete":
            self.fmk_input.setValue(25.0)
            self.E_input.setValue(31000)
            self.weight_input.setValue(25.0)
        elif material_type == "Steel":
            self.fmk_input.setValue(355.0)
            self.E_input.setValue(210000)
            self.weight_input.setValue(78.5)

    def get_values(self):
        """Get material parameters."""
        return {
            'name': self.name_input.text(),
            'type': self.type_combo.currentText(),
            'f_mk': self.fmk_input.value(),
            'E': self.E_input.value(),
            'weight': self.weight_input.value()
        }


class AddLoadDialog(QDialog):
    """Dialog per aggiungere un carico."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Load")
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Load type
        type_group = QGroupBox("Load Type")
        type_layout = QFormLayout()

        self.name_input = QLineEdit("Load 1")
        type_layout.addRow("Name:", self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Vertical (Gravity)",
            "Horizontal (Seismic)",
            "Distributed",
            "Point Load"
        ])
        type_layout.addRow("Type:", self.type_combo)

        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # Load values
        value_group = QGroupBox("Load Values")
        value_layout = QFormLayout()

        self.value_input = QDoubleSpinBox()
        self.value_input.setRange(0.1, 10000.0)
        self.value_input.setValue(100.0)
        self.value_input.setSuffix(" kN")
        self.value_input.setDecimals(1)
        value_layout.addRow("Magnitude:", self.value_input)

        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["Z (Vertical)", "X (Horizontal)", "Y (Horizontal)"])
        value_layout.addRow("Direction:", self.direction_combo)

        value_group.setLayout(value_layout)
        layout.addWidget(value_group)

        # Buttons
        button_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_values(self):
        """Get load parameters."""
        return {
            'name': self.name_input.text(),
            'type': self.type_combo.currentText(),
            'value': self.value_input.value(),
            'direction': self.direction_combo.currentText()
        }


class AnalysisSettingsDialog(QDialog):
    """Dialog per impostazioni analisi."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Analysis Settings")
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Analysis type
        type_group = QGroupBox("Analysis Type")
        type_layout = QFormLayout()

        self.analysis_combo = QComboBox()
        self.analysis_combo.addItems([
            "Linear Static",
            "Modal Analysis",
            "Pushover (Nonlinear)",
            "SAM Verification"
        ])
        type_layout.addRow("Method:", self.analysis_combo)

        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # Settings
        settings_group = QGroupBox("Settings")
        settings_layout = QFormLayout()

        self.max_iter_input = QDoubleSpinBox()
        self.max_iter_input.setRange(10, 1000)
        self.max_iter_input.setValue(100)
        self.max_iter_input.setDecimals(0)
        settings_layout.addRow("Max Iterations:", self.max_iter_input)

        self.tolerance_input = QDoubleSpinBox()
        self.tolerance_input.setRange(1e-6, 1e-2)
        self.tolerance_input.setValue(1e-4)
        self.tolerance_input.setDecimals(6)
        settings_layout.addRow("Tolerance:", self.tolerance_input)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Buttons
        button_layout = QHBoxLayout()
        btn_ok = QPushButton("Run")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_values(self):
        """Get analysis settings."""
        return {
            'method': self.analysis_combo.currentText(),
            'max_iter': int(self.max_iter_input.value()),
            'tolerance': self.tolerance_input.value()
        }
