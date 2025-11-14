import logging
from sam import analyze_sam, MaterialProperties

# Configurare il logging per vedere i dettagli
logging.basicConfig(level=logging.INFO)

# Caso reale: parete in muratura di tufo
wall_data = {
    'piers': [
        {'length': 1.0, 'height': 2.8, 'thickness': 1},
        {'length': 1.0, 'height': 2.8, 'thickness': 1}
    ],
    'spandrels': [
        {'length': 1.5, 'height': 0.5, 'thickness': 1}
    ]
}

# Muratura di tufo (valori tipici)
material = MaterialProperties(
    fk=1.4,     # MPa
    fvk0=0.035, # MPa
    fvk=0.074   # MPa
)

# Carichi da analisi sismica
loads = {
    'vertical': 200.0,  # kN
    'moment': 50.0,     # kNm
    'shear': 30.0       # kN
}

# Analisi con parametri NTC2018
options = {
    'gamma_m': 2.0,  # Muratura esistente
    'FC': 1.35       # LC1
}

# Eseguire verifica
results = analyze_sam(wall_data, material, loads, options)

# Report per relazione tecnica
if results['verified']:
    print("✓ La parete SODDISFA le verifiche di sicurezza")
else:
    print("✗ La parete NON SODDISFA le verifiche di sicurezza")
    print(f"  Necessario intervento di rinforzo")