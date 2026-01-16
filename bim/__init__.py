# -*- coding: utf-8 -*-
"""
Muratura BIM Module
Inspired by FreeCAD's Arch/BIM workbench

This module provides parametric BIM components with IFC support.
"""

from .components import (
    BIMComponent,
    BIMWall,
    BIMSlab,
    BIMColumn,
    BIMBeam,
    BIMFoundation,
    BIMRoof,
    BIMStairs,
    BIMWindow,
    BIMDoor,
)

from .ifc_export import export_to_ifc, import_from_ifc

__all__ = [
    'BIMComponent',
    'BIMWall',
    'BIMSlab',
    'BIMColumn',
    'BIMBeam',
    'BIMFoundation',
    'BIMRoof',
    'BIMStairs',
    'BIMWindow',
    'BIMDoor',
    'export_to_ifc',
    'import_from_ifc',
]
