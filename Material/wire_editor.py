import sys
import json
import math
import csv
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QDoubleSpinBox, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QGroupBox, QGridLayout, QFileDialog, QMessageBox,
    QHeaderView, QAbstractItemView, QDialog, QTextEdit, QDialogButtonBox,
    QInputDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class Point:
    """Punto con coordinate spaziali"""
    
    def __init__(self, point_id, x, y, z=0.0, description=""):
        self.id = point_id
        self.x = x
        self.y = y
        self.z = z
        self.description = description
        
    def to_dict(self):
        return {
            'id': self.id,
            'x': self.x,
            'y': self.y,
            'z': self.z,
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            data['id'], 
            data['x'], 
            data['y'], 
            data.get('z', 0.0),
            data.get('description', '')
        )


class CoordinateModel:
    """Modello dati per coordinate fili fissi"""
    
    def __init__(self):
        self.points = {}
        self.next_id = 1
        self.metadata = {
            "author": "Arch. Michelangelo Bartolotta",
            "registration": "Ordine Architetti Agrigento n. 1557",
            "project_type": "Coordinate Fili Fissi",
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat(),
            "project_name": "",
            "location": "",
            "notes": ""
        }
    
    def add_point(self, x, y, z=0.0, description=""):
        """Aggiunge un punto"""
        if not description:
            description = f"Punto {self.next_id}"
            
        point = Point(self.next_id, x, y, z, description)
        self.points[self.next_id] = point
        self.next_id += 1
        self._mark_modified()
        return point.id
    
    def update_point(self, point_id, **kwargs):
        """Aggiorna un punto"""
        if point_id in self.points:
            point = self.points[point_id]
            for key, value in kwargs.items():
                if hasattr(point, key):
                    setattr(point, key, value)
            self._mark_modified()
            return True
        return False
    
    def delete_point(self, point_id):
        """Elimina un punto"""
        if point_id in self.points:
            del self.points[point_id]
            self._mark_modified()
            return True
        return False
    
    def get_point_list(self):
        """Restituisce lista ordinata di punti"""
        return sorted(self.points.values(), key=lambda p: p.id)
    
    def clear(self):
        """Pulisce tutti i punti"""
        self.points.clear()
        self.next_id = 1
        self._mark_modified()
    
    def get_bounds(self):
        """Calcola i limiti delle coordinate"""
        if not self.points:
            return None

        points = list(self.points.values())
        return {
            'x_min': min(p.x for p in points),
            'x_max': max(p.x for p in points),
            'y_min': min(p.y for p in points),
            'y_max': max(p.y for p in points),
            'z_min': min(p.z for p in points),
            'z_max': max(p.z for p in points)
        }

    def duplicate_point(self, point_id, offset_x=0.0, offset_y=0.0, offset_z=0.0):
        """Duplica un punto con offset opzionale"""
        if point_id in self.points:
            original = self.points[point_id]
            new_desc = f"{original.description} (copia)" if original.description else f"Punto {self.next_id}"
            return self.add_point(
                original.x + offset_x,
                original.y + offset_y,
                original.z + offset_z,
                new_desc
            )
        return None

    def translate_all(self, dx, dy, dz):
        """Trasla tutti i punti di dx, dy, dz"""
        for point in self.points.values():
            point.x += dx
            point.y += dy
            point.z += dz
        self._mark_modified()

    def find_duplicates(self, tolerance=0.001):
        """Trova punti duplicati entro una tolleranza"""
        duplicates = []
        points_list = list(self.points.values())

        for i, p1 in enumerate(points_list):
            for p2 in points_list[i+1:]:
                dist = math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)
                if dist < tolerance:
                    duplicates.append((p1.id, p2.id, dist))

        return duplicates

    def calculate_distance(self, id1, id2):
        """Calcola distanza tra due punti"""
        if id1 in self.points and id2 in self.points:
            p1 = self.points[id1]
            p2 = self.points[id2]
            dx = p2.x - p1.x
            dy = p2.y - p1.y
            dz = p2.z - p1.z
            dist_3d = math.sqrt(dx**2 + dy**2 + dz**2)
            dist_2d = math.sqrt(dx**2 + dy**2)
            return {
                'distance_3d': dist_3d,
                'distance_2d': dist_2d,
                'dx': dx,
                'dy': dy,
                'dz': dz
            }
        return None

    def _mark_modified(self):
        self.metadata["modified"] = datetime.now().isoformat()
    
    def to_dict(self):
        """Esporta per JSON"""
        return {
            "metadata": self.metadata,
            "points": [point.to_dict() for point in self.points.values()],
            "next_id": self.next_id
        }
    
    def from_dict(self, data):
        """Importa da JSON"""
        self.clear()
        
        if "metadata" in data:
            self.metadata.update(data["metadata"])
        
        if "points" in data:
            for point_data in data["points"]:
                point = Point.from_dict(point_data)
                self.points[point.id] = point
        
        self.next_id = data.get("next_id", 1)
        
        # Correggi ID se necessario
        if self.points:
            max_id = max(self.points.keys())
            if max_id >= self.next_id:
                self.next_id = max_id + 1


class MetadataDialog(QDialog):
    """Dialog per modifica metadata progetto"""

    def __init__(self, metadata, parent=None):
        super().__init__(parent)
        self.metadata = metadata.copy()
        self.setWindowTitle("Informazioni Progetto")
        self.setup_ui()

    def setup_ui(self):
        layout = QGridLayout()

        # Nome progetto
        layout.addWidget(QLabel("Nome Progetto:"), 0, 0)
        self.project_name = QLineEdit()
        self.project_name.setText(self.metadata.get('project_name', ''))
        layout.addWidget(self.project_name, 0, 1)

        # Location
        layout.addWidget(QLabel("Localit\u00e0:"), 1, 0)
        self.location = QLineEdit()
        self.location.setText(self.metadata.get('location', ''))
        layout.addWidget(self.location, 1, 1)

        # Note
        layout.addWidget(QLabel("Note:"), 2, 0)
        self.notes = QTextEdit()
        self.notes.setPlainText(self.metadata.get('notes', ''))
        self.notes.setMaximumHeight(100)
        layout.addWidget(self.notes, 2, 1)

        # Autore (read-only)
        layout.addWidget(QLabel("Autore:"), 3, 0)
        author_label = QLabel(self.metadata.get('author', ''))
        author_label.setStyleSheet("color: gray;")
        layout.addWidget(author_label, 3, 1)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, 4, 0, 1, 2)

        self.setLayout(layout)
        self.setMinimumWidth(500)

    def get_metadata(self):
        """Restituisce metadata aggiornato"""
        self.metadata['project_name'] = self.project_name.text().strip()
        self.metadata['location'] = self.location.text().strip()
        self.metadata['notes'] = self.notes.toPlainText().strip()
        return self.metadata


class CoordinateInputPanel(QGroupBox):
    """Pannello input coordinate semplificato"""
    
    def __init__(self, model, parent=None):
        super().__init__("Input Coordinate", parent)
        self.model = model
        self.setup_ui()
    
    def setup_ui(self):
        layout = QGridLayout()
        
        # Coordinate principali
        layout.addWidget(QLabel("X (m):"), 0, 0)
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-10000, 10000)
        self.x_spin.setDecimals(4)
        self.x_spin.setSingleStep(0.1)
        self.x_spin.setMinimumWidth(120)
        layout.addWidget(self.x_spin, 0, 1)
        
        layout.addWidget(QLabel("Y (m):"), 0, 2)
        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-10000, 10000)
        self.y_spin.setDecimals(4)
        self.y_spin.setSingleStep(0.1)
        self.y_spin.setMinimumWidth(120)
        layout.addWidget(self.y_spin, 0, 3)
        
        layout.addWidget(QLabel("Z (m):"), 1, 0)
        self.z_spin = QDoubleSpinBox()
        self.z_spin.setRange(-1000, 1000)
        self.z_spin.setDecimals(3)
        self.z_spin.setSingleStep(0.1)
        self.z_spin.setMinimumWidth(120)
        layout.addWidget(self.z_spin, 1, 1)
        
        # Descrizione opzionale
        layout.addWidget(QLabel("Descrizione:"), 1, 2)
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Opzionale - es: Pilastro A1")
        layout.addWidget(self.desc_edit, 1, 3)
        
        # Pulsanti
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Aggiungi Punto")
        self.add_btn.setDefault(True)
        self.add_btn.clicked.connect(self.add_point)
        button_layout.addWidget(self.add_btn)
        
        self.clear_btn = QPushButton("Reset")
        self.clear_btn.clicked.connect(self.clear_fields)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout, 2, 0, 1, 4)
        self.setLayout(layout)
        
        # Focus su X per input rapido
        self.x_spin.setFocus()
        
        # Enter per aggiungere (solo LineEdit supporta returnPressed)
        self.desc_edit.returnPressed.connect(self.add_point)
    
    def add_point(self):
        """Aggiunge punto alle coordinate"""
        x = self.x_spin.value()
        y = self.y_spin.value()
        z = self.z_spin.value()
        description = self.desc_edit.text().strip()
        
        point_id = self.model.add_point(x, y, z, description)
        
        # Incrementa automaticamente X per input sequenziale
        self.x_spin.setValue(x + 1.0)
        self.desc_edit.clear()
        self.x_spin.setFocus()
        
        return point_id
    
    def clear_fields(self):
        """Reset tutti i campi"""
        self.x_spin.setValue(0.0)
        self.y_spin.setValue(0.0)
        self.z_spin.setValue(0.0)
        self.desc_edit.clear()
        self.x_spin.setFocus()
    
    def keyPressEvent(self, event):
        """Enter = aggiungi punto"""
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.add_point()
        super().keyPressEvent(event)


class CoordinateTable(QTableWidget):
    """Tabella coordinate con editing inline"""
    
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.setup_table()
    
    def setup_table(self):
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(['ID', 'X (m)', 'Y (m)', 'Z (m)', 'Descrizione'])
        
        # Configurazione header
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID fisso
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # X
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Y  
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Z
        header.setStretchLastSection(True)  # Descrizione espandibile
        
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        
        # Connetti modifiche
        self.cellChanged.connect(self.on_cell_changed)
    
    def refresh(self):
        """Aggiorna tabella completa"""
        points = self.model.get_point_list()
        self.setRowCount(len(points))
        
        # Blocca segnali durante refresh
        self.blockSignals(True)
        
        for row, point in enumerate(points):
            # ID (solo lettura)
            id_item = QTableWidgetItem(str(point.id))
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(row, 0, id_item)
            
            # Coordinate (modificabili con precisione)
            self.setItem(row, 1, QTableWidgetItem(f"{point.x:.4f}"))
            self.setItem(row, 2, QTableWidgetItem(f"{point.y:.4f}"))
            self.setItem(row, 3, QTableWidgetItem(f"{point.z:.3f}"))
            
            # Descrizione
            self.setItem(row, 4, QTableWidgetItem(point.description))
        
        self.blockSignals(False)
    
    def on_cell_changed(self, row, col):
        """Gestisce modifiche dirette in tabella"""
        id_item = self.item(row, 0)
        if not id_item:
            return
            
        point_id = int(id_item.text())
        item = self.item(row, col)
        
        try:
            if col == 1:  # X
                self.model.update_point(point_id, x=float(item.text()))
            elif col == 2:  # Y
                self.model.update_point(point_id, y=float(item.text()))
            elif col == 3:  # Z
                self.model.update_point(point_id, z=float(item.text()))
            elif col == 4:  # Descrizione
                self.model.update_point(point_id, description=item.text())
        except ValueError as e:
            # Valore non valido, ripristina
            QMessageBox.warning(self, "Errore", f"Valore non valido: {e}")
            self.refresh()
    
    def keyPressEvent(self, event):
        """Elimina punto con DEL"""
        if event.key() == Qt.Key_Delete:
            current_row = self.currentRow()
            if current_row >= 0:
                id_item = self.item(current_row, 0)
                if id_item:
                    point_id = int(id_item.text())
                    reply = QMessageBox.question(
                        self, 'Conferma Eliminazione', 
                        f'Eliminare il punto ID {point_id}?',
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        self.model.delete_point(point_id)
                        self.refresh()
        super().keyPressEvent(event)


class MainWindow(QMainWindow):
    """Finestra principale per input coordinate fili fissi"""
    
    def __init__(self):
        super().__init__()
        self.model = CoordinateModel()
        self.setup_ui()
        self.setup_menus()
        self.setWindowTitle("Input Coordinate Fili Fissi - Arch. Michelangelo Bartolotta")
    
    def setup_ui(self):
        self.setMinimumSize(1000, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Pannello input semplificato
        self.input_panel = CoordinateInputPanel(self.model)
        self.input_panel.add_btn.clicked.connect(self.refresh_display)
        layout.addWidget(self.input_panel)
        
        # Tabella coordinate
        table_group = QGroupBox("Elenco Coordinate")
        table_layout = QVBoxLayout()
        
        self.table = CoordinateTable(self.model)
        table_layout.addWidget(self.table)
        
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)
        
        # Barra informazioni
        info_layout = QHBoxLayout()
        
        self.info_label = QLabel("Punti: 0")
        self.info_label.setFont(QFont("Arial", 10, QFont.Bold))
        info_layout.addWidget(self.info_label)
        
        info_layout.addStretch()
        
        self.bounds_label = QLabel("")
        self.bounds_label.setFont(QFont("Arial", 9))
        info_layout.addWidget(self.bounds_label)
        
        layout.addLayout(info_layout)
        
        self.refresh_display()
    
    def setup_menus(self):
        menubar = self.menuBar()

        # Menu File
        file_menu = menubar.addMenu('File')
        file_menu.addAction('Nuovo Progetto', self.new_project, 'Ctrl+N')
        file_menu.addSeparator()
        file_menu.addAction('Apri...', self.open_file, 'Ctrl+O')
        file_menu.addAction('Salva...', self.save_file, 'Ctrl+S')
        file_menu.addSeparator()
        file_menu.addAction('Importa CSV...', self.import_csv)
        file_menu.addAction('Esporta CSV...', self.export_csv)
        file_menu.addAction('Esporta DXF...', self.export_dxf)
        file_menu.addSeparator()
        file_menu.addAction('Informazioni Progetto...', self.edit_metadata, 'Ctrl+I')
        file_menu.addSeparator()
        file_menu.addAction('Esci', self.close, 'Ctrl+Q')

        # Menu Modifica
        edit_menu = menubar.addMenu('Modifica')
        edit_menu.addAction('Duplica Punto Selezionato', self.duplicate_selected_point, 'Ctrl+D')
        edit_menu.addAction('Trasla Tutte le Coordinate...', self.translate_coordinates)
        edit_menu.addSeparator()
        edit_menu.addAction('Trova Punti Duplicati', self.find_duplicate_points)

        # Menu Strumenti
        tools_menu = menubar.addMenu('Strumenti')
        tools_menu.addAction('Calcola Distanza tra Punti', self.calculate_distance_dialog)
        tools_menu.addSeparator()
        tools_menu.addAction('Statistiche Progetto', self.show_statistics)
        tools_menu.addAction('Info Coordinate', self.show_coordinate_info)
        tools_menu.addSeparator()
        tools_menu.addAction('Elimina Tutto', self.clear_all_points)

        # Menu Aiuto
        help_menu = menubar.addMenu('Aiuto')
        help_menu.addAction('Informazioni', self.show_about)
    
    def refresh_display(self):
        """Aggiorna tutte le visualizzazioni"""
        self.table.refresh()
        count = len(self.model.points)
        self.info_label.setText(f"Punti: {count}")
        
        # Aggiorna bounds
        if count > 0:
            bounds = self.model.get_bounds()
            bounds_text = (f"Range: X({bounds['x_min']:.2f}÷{bounds['x_max']:.2f}) "
                          f"Y({bounds['y_min']:.2f}÷{bounds['y_max']:.2f}) "
                          f"Z({bounds['z_min']:.2f}÷{bounds['z_max']:.2f})")
            self.bounds_label.setText(bounds_text)
        else:
            self.bounds_label.setText("")
    
    def new_project(self):
        """Nuovo progetto"""
        if len(self.model.points) > 0:
            reply = QMessageBox.question(
                self, 'Nuovo Progetto', 
                'Eliminare tutte le coordinate esistenti?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        self.model.clear()
        self.refresh_display()
        QMessageBox.information(self, "Nuovo Progetto", "Progetto inizializzato")
    
    def save_file(self):
        """Salva coordinate su file JSON"""
        if not self.model.points:
            QMessageBox.warning(self, "Attenzione", "Nessuna coordinata da salvare")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Salva Coordinate Fili Fissi", "coordinate_fili_fissi.json", 
            "File JSON (*.json);;Tutti i file (*)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.model.to_dict(), f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "Salvataggio Completato", 
                                      f"Coordinate salvate in:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Errore Salvataggio", 
                                   f"Impossibile salvare il file:\n{e}")
    
    def open_file(self):
        """Apri file coordinate esistente"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Apri Coordinate", "", 
            "File JSON (*.json);;Tutti i file (*)"
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.model.from_dict(data)
                self.refresh_display()
                QMessageBox.information(self, "Caricamento Completato", 
                                      f"Coordinate caricate da:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Errore Caricamento", 
                                   f"Impossibile aprire il file:\n{e}")
    
    def import_csv(self):
        """Importa coordinate da file CSV"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Importa CSV", "",
            "File CSV (*.csv);;Tutti i file (*)"
        )

        if filename:
            try:
                imported = 0
                with open(filename, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            x = float(row.get('X', row.get('x', 0)))
                            y = float(row.get('Y', row.get('y', 0)))
                            z = float(row.get('Z', row.get('z', 0)))
                            desc = row.get('Descrizione', row.get('Description', row.get('descrizione', '')))
                            self.model.add_point(x, y, z, desc)
                            imported += 1
                        except (ValueError, KeyError) as e:
                            continue

                self.refresh_display()
                QMessageBox.information(self, "Importazione Completata",
                                      f"{imported} punti importati da:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Errore Importazione",
                                   f"Impossibile importare CSV:\n{e}")

    def export_csv(self):
        """Esporta coordinate in formato CSV"""
        if not self.model.points:
            QMessageBox.warning(self, "Attenzione", "Nessuna coordinata da esportare")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Esporta CSV", "coordinate_fili_fissi.csv",
            "File CSV (*.csv);;Tutti i file (*)"
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("ID,X,Y,Z,Descrizione\n")
                    for point in self.model.get_point_list():
                        f.write(f'{point.id},{point.x:.4f},{point.y:.4f},{point.z:.3f},"{point.description}"\n')
                QMessageBox.information(self, "Esportazione Completata",
                                      f"CSV esportato in:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Errore Esportazione",
                                   f"Impossibile esportare CSV:\n{e}")

    def export_dxf(self):
        """Esporta coordinate in formato DXF (semplificato)"""
        if not self.model.points:
            QMessageBox.warning(self, "Attenzione", "Nessuna coordinata da esportare")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Esporta DXF", "coordinate_fili_fissi.dxf",
            "File DXF (*.dxf);;Tutti i file (*)"
        )

        if filename:
            try:
                # Export DXF semplificato (senza libreria ezdxf)
                with open(filename, 'w', encoding='utf-8') as f:
                    # Header DXF minimale
                    f.write("  0\nSECTION\n  2\nENTITIES\n")

                    # Aggiungi punti come POINT entities
                    for point in self.model.get_point_list():
                        f.write("  0\nPOINT\n")
                        f.write(f" 10\n{point.x:.4f}\n")
                        f.write(f" 20\n{point.y:.4f}\n")
                        f.write(f" 30\n{point.z:.3f}\n")
                        # Aggiungi testo come descrizione
                        if point.description:
                            f.write("  0\nTEXT\n")
                            f.write(f" 10\n{point.x:.4f}\n")
                            f.write(f" 20\n{point.y:.4f}\n")
                            f.write(f" 30\n{point.z:.3f}\n")
                            f.write(f"  1\n{point.description}\n")
                            f.write(" 40\n0.5\n")  # Text height

                    f.write("  0\nENDSEC\n  0\nEOF\n")

                QMessageBox.information(self, "Esportazione Completata",
                                      f"DXF esportato in:\n{filename}\n\nNota: formato DXF semplificato")
            except Exception as e:
                QMessageBox.critical(self, "Errore Esportazione",
                                   f"Impossibile esportare DXF:\n{e}")

    def edit_metadata(self):
        """Modifica metadata progetto"""
        dialog = MetadataDialog(self.model.metadata, self)
        if dialog.exec_() == QDialog.Accepted:
            updated_metadata = dialog.get_metadata()
            self.model.metadata.update(updated_metadata)
            self.model._mark_modified()
            self.refresh_display()
            QMessageBox.information(self, "Metadata Aggiornato",
                                  "Le informazioni del progetto sono state aggiornate")

    def duplicate_selected_point(self):
        """Duplica punto selezionato"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Attenzione", "Seleziona un punto da duplicare")
            return

        id_item = self.table.item(current_row, 0)
        if id_item:
            point_id = int(id_item.text())

            # Chiedi offset (opzionale)
            offset_x, ok1 = QInputDialog.getDouble(self, "Offset X", "Offset X (m):", 0.0, -10000, 10000, 4)
            if not ok1:
                return
            offset_y, ok2 = QInputDialog.getDouble(self, "Offset Y", "Offset Y (m):", 0.0, -10000, 10000, 4)
            if not ok2:
                return
            offset_z, ok3 = QInputDialog.getDouble(self, "Offset Z", "Offset Z (m):", 0.0, -1000, 1000, 3)
            if not ok3:
                return

            new_id = self.model.duplicate_point(point_id, offset_x, offset_y, offset_z)
            if new_id:
                self.refresh_display()
                QMessageBox.information(self, "Punto Duplicato",
                                      f"Punto {point_id} duplicato come punto {new_id}")

    def translate_coordinates(self):
        """Trasla tutte le coordinate"""
        if not self.model.points:
            QMessageBox.warning(self, "Attenzione", "Nessun punto da traslare")
            return

        dx, ok1 = QInputDialog.getDouble(self, "Traslazione", "Offset X (m):", 0.0, -10000, 10000, 4)
        if not ok1:
            return
        dy, ok2 = QInputDialog.getDouble(self, "Traslazione", "Offset Y (m):", 0.0, -10000, 10000, 4)
        if not ok2:
            return
        dz, ok3 = QInputDialog.getDouble(self, "Traslazione", "Offset Z (m):", 0.0, -1000, 1000, 3)
        if not ok3:
            return

        if dx == 0 and dy == 0 and dz == 0:
            QMessageBox.information(self, "Traslazione", "Nessun offset applicato")
            return

        reply = QMessageBox.question(
            self, 'Conferma Traslazione',
            f'Traslare tutti i {len(self.model.points)} punti di:\nΔX={dx:.4f}m, ΔY={dy:.4f}m, ΔZ={dz:.3f}m?',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.model.translate_all(dx, dy, dz)
            self.refresh_display()
            QMessageBox.information(self, "Traslazione Completata",
                                  f"Tutti i punti sono stati traslati")

    def find_duplicate_points(self):
        """Trova punti duplicati"""
        if not self.model.points:
            QMessageBox.information(self, "Trova Duplicati", "Nessun punto da analizzare")
            return

        tolerance, ok = QInputDialog.getDouble(
            self, "Tolleranza", "Tolleranza distanza (m):", 0.001, 0.0001, 1.0, 4
        )
        if not ok:
            return

        duplicates = self.model.find_duplicates(tolerance)

        if not duplicates:
            QMessageBox.information(self, "Trova Duplicati",
                                  f"Nessun punto duplicato trovato (tolleranza: {tolerance:.4f}m)")
        else:
            msg = f"Trovati {len(duplicates)} coppie di punti duplicati:\n\n"
            for id1, id2, dist in duplicates[:10]:  # Mostra max 10
                p1 = self.model.points[id1]
                p2 = self.model.points[id2]
                msg += f"• Punto {id1} e {id2} - distanza: {dist:.4f}m\n"
            if len(duplicates) > 10:
                msg += f"\n... e altri {len(duplicates)-10} duplicati"

            QMessageBox.warning(self, "Punti Duplicati Trovati", msg)

    def calculate_distance_dialog(self):
        """Calcola distanza tra due punti"""
        if len(self.model.points) < 2:
            QMessageBox.warning(self, "Attenzione", "Servono almeno 2 punti")
            return

        # Lista ID punti
        point_ids = [str(p.id) for p in self.model.get_point_list()]

        # Selezione punto 1
        id1_str, ok1 = QInputDialog.getItem(
            self, "Punto 1", "Seleziona primo punto (ID):", point_ids, 0, False
        )
        if not ok1:
            return
        id1 = int(id1_str)

        # Selezione punto 2
        id2_str, ok2 = QInputDialog.getItem(
            self, "Punto 2", "Seleziona secondo punto (ID):", point_ids, 0, False
        )
        if not ok2:
            return
        id2 = int(id2_str)

        if id1 == id2:
            QMessageBox.warning(self, "Attenzione", "Seleziona due punti diversi")
            return

        result = self.model.calculate_distance(id1, id2)
        if result:
            p1 = self.model.points[id1]
            p2 = self.model.points[id2]

            msg = f"""DISTANZA TRA PUNTI

Punto {id1}: ({p1.x:.4f}, {p1.y:.4f}, {p1.z:.3f}) - {p1.description}
Punto {id2}: ({p2.x:.4f}, {p2.y:.4f}, {p2.z:.3f}) - {p2.description}

DIFFERENZE
ΔX: {result['dx']:.4f} m
ΔY: {result['dy']:.4f} m
ΔZ: {result['dz']:.3f} m

DISTANZE
Distanza 2D (planimetrica): {result['distance_2d']:.4f} m
Distanza 3D (spaziale): {result['distance_3d']:.4f} m
"""
            QMessageBox.information(self, "Calcolo Distanza", msg)
    
    def show_statistics(self):
        """Mostra statistiche complete del progetto"""
        points = list(self.model.points.values())
        if not points:
            QMessageBox.information(self, "Statistiche", "Nessuna coordinata inserita")
            return
        
        bounds = self.model.get_bounds()
        
        # Calcola distanze
        x_range = bounds['x_max'] - bounds['x_min']
        y_range = bounds['y_max'] - bounds['y_min']
        z_range = bounds['z_max'] - bounds['z_min']
        
        stats_text = f"""STATISTICHE COORDINATE FILI FISSI

Progetto: {self.model.metadata.get('project_name', 'Non specificato')}
Architetto: {self.model.metadata.get('author', 'N/A')}

PUNTI COORDINATI
Totale punti: {len(points)}

ESTENSIONI PLANIMETRICHE
X min: {bounds['x_min']:.4f} m    X max: {bounds['x_max']:.4f} m    Δ: {x_range:.4f} m
Y min: {bounds['y_min']:.4f} m    Y max: {bounds['y_max']:.4f} m    Δ: {y_range:.4f} m
Z min: {bounds['z_min']:.3f} m     Z max: {bounds['z_max']:.3f} m     Δ: {z_range:.3f} m

INFORMAZIONI FILE
Creato: {self.model.metadata.get('created', 'N/A')[:19]}
Modificato: {self.model.metadata.get('modified', 'N/A')[:19]}
"""
        
        QMessageBox.information(self, "Statistiche Progetto", stats_text)
    
    def show_coordinate_info(self):
        """Mostra informazioni dettagliate sulle coordinate"""
        points = list(self.model.points.values())
        if not points:
            QMessageBox.information(self, "Info Coordinate", "Nessuna coordinata disponibile")
            return
        
        # Trova punti estremi
        x_coords = [p.x for p in points]
        y_coords = [p.y for p in points]
        
        x_min_point = min(points, key=lambda p: p.x)
        x_max_point = max(points, key=lambda p: p.x)
        y_min_point = min(points, key=lambda p: p.y)
        y_max_point = max(points, key=lambda p: p.y)
        
        info_text = f"""INFORMAZIONI COORDINATE

PUNTI ESTREMI
X minima: Punto {x_min_point.id} ({x_min_point.x:.4f}, {x_min_point.y:.4f}) - {x_min_point.description}
X massima: Punto {x_max_point.id} ({x_max_point.x:.4f}, {x_max_point.y:.4f}) - {x_max_point.description}

Y minima: Punto {y_min_point.id} ({y_min_point.x:.4f}, {y_min_point.y:.4f}) - {y_min_point.description}
Y massima: Punto {y_max_point.id} ({y_max_point.x:.4f}, {y_max_point.y:.4f}) - {y_max_point.description}

COORDINATE CENTRO BARICENTRICO
X centro: {sum(x_coords)/len(x_coords):.4f} m
Y centro: {sum(y_coords)/len(y_coords):.4f} m
"""
        
        QMessageBox.information(self, "Informazioni Coordinate", info_text)
    
    def clear_all_points(self):
        """Elimina tutti i punti"""
        if not self.model.points:
            QMessageBox.information(self, "Elimina Tutto", "Nessun punto da eliminare")
            return
        
        reply = QMessageBox.question(
            self, 'Conferma Eliminazione', 
            f'Eliminare tutti i {len(self.model.points)} punti?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.model.clear()
            self.refresh_display()
            QMessageBox.information(self, "Eliminazione Completata", "Tutti i punti sono stati eliminati")
    
    def show_about(self):
        """Informazioni sull'applicazione"""
        about_text = """INPUT COORDINATE FILI FISSI

Applicazione professionale per l'inserimento e gestione delle coordinate
spaziali per la progettazione di fili fissi strutturali.

Sviluppato per:
Arch. Michelangelo Bartolotta
Ordine Architetti Agrigento n. 1557

Funzionalità:
• Input rapido coordinate X, Y, Z
• Modifica diretta in tabella
• Import/Export: JSON, CSV, DXF
• Calcolo distanze tra punti
• Duplicazione e traslazione coordinate
• Rilevamento punti duplicati
• Gestione metadata progetto
• Statistiche geometriche complete

Versione: 3.0 - Professionale
"""
        QMessageBox.about(self, "Informazioni", about_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Input Coordinate Fili Fissi")
    app.setApplicationVersion("3.0")
    
    # Stile applicazione
    app.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            border: 2px solid #cccccc;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QPushButton {
            padding: 5px 10px;
            border-radius: 3px;
        }
        QPushButton:default {
            background-color: #007acc;
            color: white;
            border: none;
        }
        QDoubleSpinBox {
            padding: 3px;
        }
    """)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())