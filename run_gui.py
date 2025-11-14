#!/usr/bin/env python3
"""
MURATURA FEM - GUI Launcher

Quick launcher for MURATURA FEM Desktop GUI.

Usage:
    python run_gui.py

Features:
    - Automatic dependency check
    - Enhanced GUI with real analysis
    - 15 predefined examples
    - Matplotlib plots
    - Project save/load
    - IFC import/export
    - PDF report generation

Requirements:
    pip install PyQt6 matplotlib
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_dependencies():
    """Check required dependencies."""
    missing = []

    try:
        import PyQt6
    except ImportError:
        missing.append("PyQt6")

    try:
        import matplotlib
    except ImportError:
        missing.append("matplotlib")

    try:
        from Material import MasonryFEMEngine
    except ImportError:
        print("⚠️  Warning: Material package not properly installed")
        print("   GUI will work but analysis features may be limited")

    if missing:
        print("❌ Missing required dependencies:")
        for dep in missing:
            print(f"   - {dep}")
        print("\n📦 Install with:")
        print(f"   pip install {' '.join(missing)}")
        return False

    return True


def main():
    """Launch GUI."""
    print("🏛️  MURATURA FEM v7.0.0-alpha - Desktop GUI")
    print("=" * 60)
    print()

    # Check dependencies
    if not check_dependencies():
        print("\n❌ Cannot start GUI - missing dependencies")
        return 1

    print("✅ All dependencies OK")
    print()
    print("🚀 Launching Enhanced GUI...")
    print()

    # Import and run GUI
    try:
        from gui.desktop_qt.main_window_enhanced import main as gui_main
        return gui_main()
    except Exception as e:
        print(f"❌ Error launching GUI: {e}")
        print()
        print("Trying to run from gui directory...")

        # Try alternative import
        gui_dir = project_root / "gui" / "desktop_qt"
        sys.path.insert(0, str(gui_dir))

        try:
            from main_window_enhanced import main as gui_main
            return gui_main()
        except Exception as e2:
            print(f"❌ Failed: {e2}")
            print("\n💡 Try running directly:")
            print("   cd gui/desktop_qt")
            print("   python main_window_enhanced.py")
            return 1


if __name__ == "__main__":
    sys.exit(main())
