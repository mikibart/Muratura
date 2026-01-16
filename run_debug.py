# -*- coding: utf-8 -*-
"""Debug launcher for Muratura - catches all errors"""
import sys
import traceback
import os

# Crea file di log
log_path = 'C:/Muratura/debug_output.txt'
log_file = open(log_path, 'w', encoding='utf-8', buffering=1)  # Line buffering

class LogWriter:
    def __init__(self, file, original):
        self.file = file
        self.original = original

    def write(self, text):
        self.file.write(text)
        self.file.flush()
        if self.original:
            self.original.write(text)

    def flush(self):
        self.file.flush()
        if self.original:
            self.original.flush()

sys.stdout = LogWriter(log_file, sys.__stdout__)
sys.stderr = LogWriter(log_file, sys.__stderr__)

print("Starting Muratura in debug mode...")
print(f"Log file: {log_path}")
print("=" * 50)

try:
    print("Importing gui_editor_v2...")
    from gui_editor_v2 import main
    print("Import OK, starting main()...")
    main()
except Exception as e:
    print("\n" + "=" * 50)
    print("ERRORE CATTURATO:")
    print("=" * 50)
    traceback.print_exc()
finally:
    print("\n" + "=" * 50)
    print("Application closed")
    log_file.close()
