# sam_building_complex_fixed.py
"""
Complesso edificio in muratura per test SAM (v7.x)
- 5 pareti: N_L1, N_L2, E_L1, W_L1, ATRIUM_ARCADE
- Include fasce ad arco e opzioni di riparto/attrito/slenderness
Esecuzione:
    python sam_building_complex_fixed.py
Output:
    sam_building_complex_results.json
    sam_building_complex_summary.csv
"""
import json
from pathlib import Path

from sam import analyze_sam, MaterialProperties  # richiede sam.py nella stessa cartella

def make_building_definition():
    # Materiali
    mattone_pieno = MaterialProperties(
        fk=2.8,     # MPa
        fvk0=0.12,  # MPa
        fvk=0.20,   # MPa
        E=1500.0,   # MPa
        G=600.0,    # MPa
        use_fvd0_for_piers=True,
        use_fvd0_for_spandrels=False
    )
    tufo = MaterialProperties(
        fk=1.6,     # MPa
        fvk0=0.050, # MPa
        fvk=0.090,  # MPa
        E=900.0,    # MPa
        G=360.0,    # MPa
        use_fvd0_for_piers=True,
        use_fvd0_for_spandrels=False
    )

    walls = {
        # Nord - Livello 1
        "N_L1": {
            "material": mattone_pieno,
            "wall_data": {
                "piers": [
                    {"length": 1.30, "height": 3.20, "thickness": 0.38},
                    {"length": 1.10, "height": 3.20, "thickness": 0.38},
                    {"length": 1.20, "height": 3.20, "thickness": 0.38},
                    {"length": 1.40, "height": 3.20, "thickness": 0.38},
                ],
                "spandrels": [
                    {"length": 1.20, "height": 0.55, "thickness": 0.30},
                    {"length": 1.30, "height": 0.55, "thickness": 0.30, "arch_rise": 0.12},
                    {"length": 1.10, "height": 0.55, "thickness": 0.30},
                ],
                "pier_spacing": 0.35
            },
            "loads": {"vertical": 520.0, "moment": -85.0, "shear": 70.0},
            "options": {
                "gamma_m": 2.0, "FC": 1.20,
                "pier_load_share": 0.7, "spandrel_load_share": 0.3,
                "vertical_load_to_piers_only": True,
                "consider_spandrel_axial": True,
                "tension_reduction_sliding": 0.5,
                "tension_reduction_diagonal": 0.7,
                "mu_friction": 0.45,
                "max_friction_absolute": 0.6,
                "slenderness_type": "OOP"
            }
        },
        # Nord - Livello 2
        "N_L2": {
            "material": mattone_pieno,
            "wall_data": {
                "piers": [
                    {"length": 1.20, "height": 3.00, "thickness": 0.30},
                    {"length": 1.00, "height": 3.00, "thickness": 0.30},
                    {"length": 1.10, "height": 3.00, "thickness": 0.30},
                    {"length": 1.30, "height": 3.00, "thickness": 0.30},
                ],
                "spandrels": [
                    {"length": 1.10, "height": 0.50, "thickness": 0.25},
                    {"length": 1.30, "height": 0.50, "thickness": 0.25},
                    {"length": 1.00, "height": 0.50, "thickness": 0.25}
                ],
                "pier_spacing": 0.30
            },
            "loads": {"vertical": 410.0, "moment": -60.0, "shear": 55.0},
            "options": {
                "gamma_m": 2.0, "FC": 1.20,
                "pier_load_share": 0.65, "spandrel_load_share": 0.35,
                "vertical_load_to_piers_only": False,
                "consider_spandrel_axial": True,
                "tension_reduction_sliding": 0.5,
                "tension_reduction_diagonal": 0.7,
                "mu_friction": 0.40,
                "max_friction_absolute": 0.5,
                "slenderness_type": "OOP"
            }
        },
        # Est - Livello 1
        "E_L1": {
            "material": tufo,
            "wall_data": {
                "piers": [
                    {"length": 1.60, "height": 3.20, "thickness": 0.45},
                    {"length": 1.20, "height": 3.20, "thickness": 0.45},
                    {"length": 1.40, "height": 3.20, "thickness": 0.45},
                ],
                "spandrels": [
                    {"length": 1.30, "height": 0.60, "thickness": 0.30}
                ],
                "pier_spacing": 0.40
            },
            "loads": {"vertical": 600.0, "moment": 95.0, "shear": 80.0},
            "options": {
                "gamma_m": 2.0, "FC": 1.35,
                "pier_load_share": 0.8, "spandrel_load_share": 0.2,
                "vertical_load_to_piers_only": True,
                "consider_spandrel_axial": False,
                "tension_reduction_sliding": 0.5,
                "tension_reduction_diagonal": 0.7,
                "mu_friction": 0.35,
                "max_friction_absolute": 0.5,
                "slenderness_type": "OOP"
            }
        },
        # Ovest - Livello 1
        "W_L1": {
            "material": tufo,
            "wall_data": {
                "piers": [
                    {"length": 0.90, "height": 3.20, "thickness": 0.30},
                    {"length": 0.80, "height": 3.20, "thickness": 0.30},
                    {"length": 0.85, "height": 3.20, "thickness": 0.30},
                    {"length": 0.95, "height": 3.20, "thickness": 0.30},
                    {"length": 1.00, "height": 3.20, "thickness": 0.30},
                ],
                "spandrels": [
                    {"length": 1.00, "height": 0.45, "thickness": 0.25},
                    {"length": 0.90, "height": 0.45, "thickness": 0.25},
                    {"length": 1.10, "height": 0.45, "thickness": 0.25},
                    {"length": 0.95, "height": 0.45, "thickness": 0.25}
                ],
                "pier_spacing": 0.25
            },
            "loads": {"vertical": 350.0, "moment": -70.0, "shear": 95.0},
            "options": {
                "gamma_m": 2.0, "FC": 1.35,
                "pier_load_share": 0.6, "spandrel_load_share": 0.4,
                "vertical_load_to_piers_only": False,
                "consider_spandrel_axial": True,
                "tension_reduction_sliding": 0.5,
                "tension_reduction_diagonal": 0.65,
                "mu_friction": 0.40,
                "max_friction_absolute": 0.5,
                "slenderness_type": "OOP"
            }
        },
        # Portico ad archi (ora con maschi sottili per evitare errore "lista maschi vuota")
        "ATRIUM_ARCADE": {
            "material": mattone_pieno,
            "wall_data": {
                "piers": [
                    {"length": 0.60, "height": 3.20, "thickness": 0.30},
                    {"length": 0.60, "height": 3.20, "thickness": 0.30},
                    {"length": 0.60, "height": 3.20, "thickness": 0.30}
                ],
                "spandrels": [
                    {"length": 2.80, "height": 0.70, "thickness": 0.30, "arch_rise": 0.35},
                    {"length": 2.60, "height": 0.70, "thickness": 0.30, "arch_rise": 0.30},
                    {"length": 2.90, "height": 0.70, "thickness": 0.30, "arch_rise": 0.32},
                ],
                "pier_spacing": 0.30
            },
            "loads": {"vertical": 180.0, "moment": 40.0, "shear": 45.0},
            "options": {
                "gamma_m": 2.0, "FC": 1.20,
                "pier_load_share": 0.3, "spandrel_load_share": 0.7,
                "vertical_load_to_piers_only": False,
                "consider_spandrel_axial": True,
                "arch_shear_reduction": 0.5,
                "tension_reduction_sliding": 0.5,
                "tension_reduction_diagonal": 0.7,
                "mu_friction": 0.45,
                "max_friction_absolute": 0.6,
                "slenderness_type": "IP"
            }
        }
    }
    return walls

def run_building_analysis():
    walls = make_building_definition()
    all_results = {}
    rows = []

    for name, cfg in walls.items():
        try:
            res = analyze_sam(cfg["wall_data"], cfg["material"], cfg["loads"], cfg["options"])
            all_results[name] = res

            summary = res.get("summary", {})
            horiz = summary.get("load_sharing", {}).get("horizontal", {})
            rows.append({
                "Parete": name,
                "n_maschi": res.get("n_piers"),
                "n_fasce": res.get("n_spandrels"),
                "DCR_globale": res.get("global_DCR"),
                "Verificata": res.get("verified"),
                "Componente_critico": summary.get("critical_component"),
                "Fail_critici": summary.get("has_critical_failures"),
                "Riparto_M": horiz.get("pier_share"),
                "Riparto_F": horiz.get("spandrel_share"),
            })
        except Exception as e:
            all_results[name] = {"error": str(e)}
            rows.append({
                "Parete": name,
                "n_maschi": None,
                "n_fasce": None,
                "DCR_globale": None,
                "Verificata": False,
                "Componente_critico": "ERROR",
                "Fail_critici": None,
                "Riparto_M": None,
                "Riparto_F": None,
            })

    # Salvataggi
    out_dir = Path(".")
    with open(out_dir / "sam_building_complex_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # CSV minimale senza dipendere da pandas
    import csv
    with open(out_dir / "sam_building_complex_summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print("Risultati salvati in: sam_building_complex_results.json, sam_building_complex_summary.csv")
    return all_results, rows

if __name__ == "__main__":
    run_building_analysis()
