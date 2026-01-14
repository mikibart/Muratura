#!/usr/bin/env python3
"""
Test del controllo remoto GUI via socket

Uso:
1. Avviare la GUI: python gui_editor_v2.py
2. Eseguire questo test: python test_remote_control.py
"""

import socket
import json
import time

HOST = '127.0.0.1'
PORT = 9999

def send_command(action: str, params: dict = None) -> dict:
    """Invia un comando alla GUI"""
    if params is None:
        params = {}

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(30.0)
    sock.connect((HOST, PORT))

    cmd = json.dumps({'action': action, 'params': params})
    print(f"→ {action}: {params}")
    sock.send((cmd + '\n').encode('utf-8'))

    response = b''
    while b'\n' not in response:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk

    sock.close()

    result = json.loads(response.decode('utf-8').strip())
    print(f"← {result}")
    return result


def main():
    print("=" * 60)
    print("TEST CONTROLLO REMOTO GUI MURATURA")
    print("=" * 60)
    print()

    try:
        # Test 1: Crea nuovo progetto
        print("1. Creazione nuovo progetto...")
        result = send_command('nuovo_progetto', {
            'nome': 'Casa Test Remoto',
            'committente': 'Test Automatico',
            'indirizzo': 'Via del Test 123'
        })
        time.sleep(0.5)

        # Test 2: Vai a step geometria
        print("\n2. Navigazione a GEOMETRIA...")
        send_command('vai_step', {'step': 'GEOMETRIA'})
        time.sleep(0.5)

        # Test 3: Disegna rettangolo (4 muri)
        print("\n3. Disegno pianta rettangolare 10x8m...")
        result = send_command('disegna_rettangolo', {
            'x': 0, 'y': 0,
            'larghezza': 10,
            'profondita': 8,
            'spessore': 0.30
        })
        time.sleep(0.5)

        # Test 4: Zoom fit
        print("\n4. Adatta vista...")
        send_command('zoom_fit')
        time.sleep(0.5)

        # Test 5: Aggiungi aperture
        print("\n5. Aggiunta aperture...")
        send_command('aggiungi_apertura', {
            'muro': 'M1',
            'tipo': 'porta',
            'larghezza': 0.9,
            'altezza': 2.1,
            'posizione': 1.0
        })
        time.sleep(0.3)

        send_command('aggiungi_apertura', {
            'muro': 'M1',
            'tipo': 'finestra',
            'larghezza': 1.2,
            'altezza': 1.4,
            'posizione': 4.0,
            'quota': 0.9
        })
        time.sleep(0.3)

        send_command('aggiungi_apertura', {
            'muro': 'M3',
            'tipo': 'finestra',
            'larghezza': 1.5,
            'altezza': 1.4,
            'posizione': 2.0,
            'quota': 0.9
        })
        time.sleep(0.5)

        # Test 6: Genera fondazioni
        print("\n6. Generazione fondazioni...")
        send_command('genera_fondazioni')
        time.sleep(0.5)

        # Test 7: Genera cordoli
        print("\n7. Generazione cordoli...")
        send_command('genera_cordoli')
        time.sleep(0.5)

        # Test 8: Genera solai
        print("\n8. Generazione solai...")
        send_command('genera_solai')
        time.sleep(0.5)

        # Test 9: Stato finale
        print("\n9. Stato finale progetto:")
        result = send_command('get_stato')
        time.sleep(0.5)

        # Test 10: Vista 3D
        print("\n10. Mostra vista 3D...")
        send_command('mostra_3d')

        print("\n" + "=" * 60)
        print("TEST COMPLETATO CON SUCCESSO!")
        print("=" * 60)

    except ConnectionRefusedError:
        print("\n❌ ERRORE: GUI non in esecuzione!")
        print("   Avviare prima: python gui_editor_v2.py")
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")


if __name__ == "__main__":
    main()
