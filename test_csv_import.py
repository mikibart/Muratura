#!/usr/bin/env python3
"""
Test script to verify CSV import functionality without GUI
"""
import csv
import sys

def test_csv_import(filename):
    """Simula l'import CSV senza GUI"""
    print(f"Testing CSV import from: {filename}\n")

    try:
        imported_count = 0
        errors = []

        with open(filename, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)

            # Verifica header
            if csv_reader.fieldnames is None:
                raise ValueError("File CSV vuoto o formato non valido")

            print(f"Headers found: {csv_reader.fieldnames}")
            print("-" * 60)

            for row_num, row in enumerate(csv_reader, start=2):
                try:
                    # Estrai valori gestendo vari formati di header
                    x_val = row.get('X') or row.get('x')
                    y_val = row.get('Y') or row.get('y')
                    z_val = row.get('Z') or row.get('z', '0.0')
                    desc_val = row.get('Descrizione') or row.get('description', '')

                    if x_val is None or y_val is None:
                        errors.append(f"Row {row_num}: Missing X or Y coordinates")
                        continue

                    # Converti esplicitamente a float/str per evitare format string errors
                    x = float(str(x_val).strip())
                    y = float(str(y_val).strip())
                    z = float(str(z_val).strip()) if z_val else 0.0
                    description = str(desc_val).strip().strip('"')

                    print(f"Row {row_num - 1}: X={x:.4f}, Y={y:.4f}, Z={z:.3f}, Desc='{description}'")
                    imported_count += 1

                except ValueError as e:
                    errors.append(f"Row {row_num}: Conversion error - {str(e)}")
                except Exception as e:
                    errors.append(f"Row {row_num}: Generic error - {str(e)}")

        print("-" * 60)
        print(f"\nSuccessfully imported {imported_count} points")

        if errors:
            print(f"\nErrors encountered ({len(errors)}):")
            for error in errors:
                print(f"  - {error}")
            return False
        else:
            print("\n✓ All rows imported successfully!")
            return True

    except Exception as e:
        print(f"✗ Import failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_file = "/home/user/Muratura/test_coordinates.csv"
    success = test_csv_import(test_file)
    sys.exit(0 if success else 1)
