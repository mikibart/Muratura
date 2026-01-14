import subprocess
import json
import os

def test_mcp():
    # Avvia il server MCP
    process = subprocess.Popen(
        ['python', 'mcp_server_muratura.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    # Prepara una chiamata a un tool
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "crea_parete",
            "arguments": {
                "nome": "Muro_Verificato_MCP",
                "lunghezza": 4.5,
                "altezza": 3.2,
                "spessore": 0.4
            }
        },
        "id": 1
    }

    try:
        # Invia la richiesta
        process.stdin.write(json.dumps(request) + "\n")
        process.stdin.flush()

        # Leggi la risposta
        line = process.stdout.readline()
        if line:
            print("RISPOSTA DAL SERVER MCP:")
            print(json.dumps(json.loads(line), indent=2))
        else:
            print("Nessuna risposta dal server.")
            err = process.stderr.read()
            if err:
                print("ERRORE STDERR:", err)

    except Exception as e:
        print("Errore durante il test:", str(e))
    finally:
        process.terminate()

if __name__ == "__main__":
    test_mcp()
