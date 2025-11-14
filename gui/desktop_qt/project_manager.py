"""
MURATURA FEM - Project Manager

Gestione salvataggio e caricamento progetti.
"""

import json
import pickle
from pathlib import Path
from datetime import datetime


class Project:
    """Classe per rappresentare un progetto MURATURA FEM."""

    def __init__(self, name="Untitled Project"):
        self.name = name
        self.created = datetime.now().isoformat()
        self.modified = datetime.now().isoformat()

        # Project data
        self.walls = []
        self.floors = []
        self.balconies = []
        self.stairs = []
        self.materials = []
        self.loads = []

        # Analysis settings
        self.analysis_type = "Linear Static"
        self.analysis_settings = {
            'max_iter': 100,
            'tolerance': 1e-4
        }

        # Results
        self.results = None
        self.model_data = None

    def add_wall(self, wall_data):
        """Add wall to project."""
        self.walls.append(wall_data)
        self.modified = datetime.now().isoformat()

    def add_material(self, material_data):
        """Add material to project."""
        self.materials.append(material_data)
        self.modified = datetime.now().isoformat()

    def add_load(self, load_data):
        """Add load to project."""
        self.loads.append(load_data)
        self.modified = datetime.now().isoformat()

    def set_results(self, results):
        """Set analysis results."""
        self.results = results
        self.modified = datetime.now().isoformat()

    def get_summary(self):
        """Get project summary."""
        return {
            'name': self.name,
            'created': self.created,
            'modified': self.modified,
            'n_walls': len(self.walls),
            'n_materials': len(self.materials),
            'n_loads': len(self.loads),
            'has_results': self.results is not None
        }


class ProjectManager:
    """Manager per progetti MURATURA FEM."""

    @staticmethod
    def save_project(project, filepath):
        """Save project to file."""
        filepath = Path(filepath)

        if filepath.suffix == '.json':
            # Save as JSON (without binary data)
            data = {
                'name': project.name,
                'created': project.created,
                'modified': project.modified,
                'walls': project.walls,
                'floors': project.floors,
                'balconies': project.balconies,
                'stairs': project.stairs,
                'materials': project.materials,
                'loads': project.loads,
                'analysis_type': project.analysis_type,
                'analysis_settings': project.analysis_settings
            }

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

        else:  # .muratura (pickle)
            with open(filepath, 'wb') as f:
                pickle.dump(project, f)

        return True

    @staticmethod
    def load_project(filepath):
        """Load project from file."""
        filepath = Path(filepath)

        if filepath.suffix == '.json':
            with open(filepath, 'r') as f:
                data = json.load(f)

            project = Project(data.get('name', 'Untitled'))
            project.created = data.get('created', datetime.now().isoformat())
            project.modified = data.get('modified', datetime.now().isoformat())
            project.walls = data.get('walls', [])
            project.floors = data.get('floors', [])
            project.balconies = data.get('balconies', [])
            project.stairs = data.get('stairs', [])
            project.materials = data.get('materials', [])
            project.loads = data.get('loads', [])
            project.analysis_type = data.get('analysis_type', 'Linear Static')
            project.analysis_settings = data.get('analysis_settings', {})

        else:  # .muratura
            with open(filepath, 'rb') as f:
                project = pickle.load(f)

        return project

    @staticmethod
    def export_to_dict(project):
        """Export project to dictionary."""
        return {
            'name': project.name,
            'created': project.created,
            'modified': project.modified,
            'elements': {
                'walls': project.walls,
                'floors': project.floors,
                'balconies': project.balconies,
                'stairs': project.stairs
            },
            'materials': project.materials,
            'loads': project.loads,
            'analysis': {
                'type': project.analysis_type,
                'settings': project.analysis_settings
            }
        }

    @staticmethod
    def import_from_dict(data):
        """Import project from dictionary."""
        project = Project(data.get('name', 'Imported Project'))
        project.created = data.get('created', datetime.now().isoformat())
        project.modified = datetime.now().isoformat()

        elements = data.get('elements', {})
        project.walls = elements.get('walls', [])
        project.floors = elements.get('floors', [])
        project.balconies = elements.get('balconies', [])
        project.stairs = elements.get('stairs', [])

        project.materials = data.get('materials', [])
        project.loads = data.get('loads', [])

        analysis = data.get('analysis', {})
        project.analysis_type = analysis.get('type', 'Linear Static')
        project.analysis_settings = analysis.get('settings', {})

        return project
