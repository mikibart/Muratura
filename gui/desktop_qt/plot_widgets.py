"""
MURATURA FEM - Plot Widgets

Widget matplotlib per visualizzazione grafici.
"""

try:
    import matplotlib
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    FigureCanvas = object

import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


class PlotWidget(QWidget):
    """Base widget per grafici matplotlib."""

    def __init__(self, parent=None):
        super().__init__(parent)

        if not MATPLOTLIB_AVAILABLE:
            layout = QVBoxLayout()
            label = QLabel("Matplotlib not available\nInstall: pip install matplotlib")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
            self.setLayout(layout)
            return

        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def clear(self):
        """Clear figure."""
        if MATPLOTLIB_AVAILABLE:
            self.figure.clear()
            self.canvas.draw()


class PushoverPlotWidget(PlotWidget):
    """Widget per grafico pushover curve."""

    def plot_pushover_curve(self, displacement, force, title="Pushover Curve"):
        """Plot pushover curve."""
        if not MATPLOTLIB_AVAILABLE:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        ax.plot(displacement, force, 'b-', linewidth=2, label='Capacity Curve')
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Displacement (mm)', fontsize=12)
        ax.set_ylabel('Base Shear (kN)', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend()

        # Mark key points
        if len(displacement) > 0:
            # Yield point (approximated)
            idx_yield = len(displacement) // 3
            ax.plot(displacement[idx_yield], force[idx_yield], 'ro',
                   markersize=8, label=f'Yield ({displacement[idx_yield]:.1f} mm)')

            # Ultimate point
            ax.plot(displacement[-1], force[-1], 'gs',
                   markersize=8, label=f'Ultimate ({displacement[-1]:.1f} mm)')

            ax.legend()

        self.canvas.draw()

    def plot_example_data(self):
        """Plot example pushover curve."""
        # Generate example data
        disp = np.linspace(0, 50, 100)
        force = 200 * (1 - np.exp(-disp/10)) + np.random.normal(0, 2, 100)
        force = np.maximum(force, 0)

        self.plot_pushover_curve(disp, force, "Example Pushover Curve")


class ModalPlotWidget(PlotWidget):
    """Widget per modal shapes."""

    def plot_modal_shapes(self, modes, frequencies, n_modes=3):
        """Plot modal shapes."""
        if not MATPLOTLIB_AVAILABLE:
            return

        self.figure.clear()

        n_rows = (n_modes + 1) // 2

        for i in range(min(n_modes, len(modes))):
            ax = self.figure.add_subplot(n_rows, 2, i+1)

            # Simple visualization of mode shape
            mode_data = modes[i]
            x = np.arange(len(mode_data))

            ax.plot(x, mode_data, 'b-', linewidth=2)
            ax.axhline(y=0, color='k', linestyle='--', alpha=0.3)
            ax.grid(True, alpha=0.3)
            ax.set_title(f'Mode {i+1}: f={frequencies[i]:.2f} Hz', fontsize=10)
            ax.set_xlabel('DOF')
            ax.set_ylabel('Amplitude')

        self.figure.tight_layout()
        self.canvas.draw()

    def plot_example_modes(self):
        """Plot example modal shapes."""
        # Generate example modes
        n_dof = 20
        modes = []
        frequencies = [2.5, 5.8, 9.2]

        for i in range(3):
            mode = np.sin(np.linspace(0, (i+1)*np.pi, n_dof))
            modes.append(mode)

        self.plot_modal_shapes(modes, frequencies)


class StressPlotWidget(PlotWidget):
    """Widget per stress distribution."""

    def plot_stress_distribution(self, elements, stresses, title="Stress Distribution"):
        """Plot stress distribution."""
        if not MATPLOTLIB_AVAILABLE:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Bar plot of stresses
        colors = ['green' if s < 2.0 else 'orange' if s < 3.0 else 'red'
                 for s in stresses]

        bars = ax.bar(elements, stresses, color=colors, alpha=0.7, edgecolor='black')
        ax.axhline(y=2.0, color='orange', linestyle='--', label='Design limit', linewidth=2)
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_xlabel('Element', fontsize=12)
        ax.set_ylabel('Stress (MPa)', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend()

        # Add value labels on bars
        for bar, stress in zip(bars, stresses):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{stress:.2f}',
                   ha='center', va='bottom', fontsize=9)

        self.canvas.draw()

    def plot_example_stresses(self):
        """Plot example stress distribution."""
        elements = [f'E{i+1}' for i in range(10)]
        stresses = np.random.uniform(0.5, 3.5, 10)
        self.plot_stress_distribution(elements, stresses)


class DeformationPlotWidget(PlotWidget):
    """Widget per deformed shape."""

    def plot_deformed_shape(self, original_coords, deformed_coords, scale=1.0):
        """Plot deformed shape vs original."""
        if not MATPLOTLIB_AVAILABLE:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Plot original shape
        ax.plot(original_coords[:, 0], original_coords[:, 1],
               'b--', linewidth=1.5, alpha=0.5, label='Original')

        # Plot deformed shape
        ax.plot(deformed_coords[:, 0], deformed_coords[:, 1],
               'r-', linewidth=2, label=f'Deformed (scale={scale}x)')

        ax.grid(True, alpha=0.3)
        ax.set_xlabel('X (m)', fontsize=12)
        ax.set_ylabel('Y (m)', fontsize=12)
        ax.set_title('Deformed Shape', fontsize=14, fontweight='bold')
        ax.legend()
        ax.axis('equal')

        self.canvas.draw()

    def plot_example_deformation(self):
        """Plot example deformed shape."""
        # Generate example structure
        n_points = 20
        x = np.linspace(0, 5, n_points)
        y_orig = np.zeros(n_points)

        # Add deformation (cantilever-like)
        y_def = -0.05 * (x / 5.0) ** 2

        original = np.column_stack([x, y_orig])
        deformed = np.column_stack([x, y_def])

        self.plot_deformed_shape(original, deformed, scale=10)


class ResultsSummaryWidget(QWidget):
    """Widget per summary tabella risultati."""

    def __init__(self, parent=None):
        super().__init__(parent)

        if not MATPLOTLIB_AVAILABLE:
            layout = QVBoxLayout()
            label = QLabel("Matplotlib not available")
            layout.addWidget(label)
            self.setLayout(layout)
            return

        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def plot_verification_summary(self, elements, ratios, limits):
        """Plot verification summary table."""
        if not MATPLOTLIB_AVAILABLE:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.axis('off')

        # Create table data
        table_data = []
        colors = []

        for elem, ratio, limit in zip(elements, ratios, limits):
            status = "✅ OK" if ratio <= 1.0 else "❌ FAIL"
            table_data.append([elem, f"{ratio:.3f}", f"{limit:.3f}", status])

            if ratio <= 0.8:
                colors.append(['lightgreen'] * 4)
            elif ratio <= 1.0:
                colors.append(['yellow'] * 4)
            else:
                colors.append(['lightcoral'] * 4)

        # Create table
        table = ax.table(cellText=table_data,
                        colLabels=['Element', 'D/C Ratio', 'Limit', 'Status'],
                        cellLoc='center',
                        loc='center',
                        cellColours=colors)

        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)

        # Style header
        for i in range(4):
            table[(0, i)].set_facecolor('#4CAF50')
            table[(0, i)].set_text_props(weight='bold', color='white')

        ax.set_title('NTC 2018 Verification Summary',
                    fontsize=14, fontweight='bold', pad=20)

        self.canvas.draw()

    def plot_example_summary(self):
        """Plot example verification summary."""
        elements = [f'Wall {i+1}' for i in range(5)] + \
                  [f'Floor {i+1}' for i in range(3)] + \
                  ['Balcony 1', 'Stair 1']

        ratios = np.random.uniform(0.5, 1.2, 10)
        limits = np.ones(10)

        self.plot_verification_summary(elements, ratios, limits)
