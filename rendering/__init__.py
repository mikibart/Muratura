# -*- coding: utf-8 -*-
"""
Muratura Rendering Module
GPU-accelerated rendering using ModernGL

Provides Blender/FreeCAD quality rendering for 2D and 3D views.
"""

__all__ = []

# Import con gestione errori per ogni modulo
try:
    from .gl_renderer import (
        GLRenderer,
        BackgroundRenderer,
        GridRenderer,
        ElementRenderer,
    )
    __all__.extend(['GLRenderer', 'BackgroundRenderer', 'GridRenderer', 'ElementRenderer'])
except ImportError as e:
    print(f"[WARNING] gl_renderer not available: {e}")

try:
    from .canvas_gl import GLDrawingCanvas2D
    __all__.append('GLDrawingCanvas2D')
except ImportError as e:
    print(f"[WARNING] canvas_gl not available: {e}")

try:
    from .vista3d_gl import Vista3DWidgetGL
    __all__.append('Vista3DWidgetGL')
except ImportError as e:
    print(f"[WARNING] vista3d_gl not available: {e}")
