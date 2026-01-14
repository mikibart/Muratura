#!/usr/bin/env python3
"""
MCP Server per Muratura - Controllo GUI da Claude

Questo server MCP permette a Claude di controllare l'interfaccia grafica
di Muratura come se fosse un utente. Claude può creare progetti completi
e l'utente vede tutto a schermo in tempo reale.

Uso:
1. Avviare prima la GUI: python gui_editor_v2.py
2. Poi avviare il server MCP (o configurarlo in Claude)
"""

import sys
import json
import socket

# Connessione alla GUI
GUI_HOST = '127.0.0.1'
GUI_PORT = 9999

def send_gui_command(action: str, params: dict = None) -> dict:
    """Invia un comando alla GUI e riceve la risposta"""
    if params is None:
        params = {}

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(35.0)
        sock.connect((GUI_HOST, GUI_PORT))

        cmd = json.dumps({'action': action, 'params': params})
        sock.send((cmd + '\n').encode('utf-8'))

        response = b''
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            if b'\n' in response:
                break

        sock.close()

        if response:
            return json.loads(response.decode('utf-8').strip())
        return {'success': False, 'error': 'Nessuna risposta dalla GUI'}

    except ConnectionRefusedError:
        return {'success': False, 'error': 'GUI non in esecuzione. Avviare prima: python gui_editor_v2.py'}
    except socket.timeout:
        return {'success': False, 'error': 'Timeout comunicazione con GUI'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ============================================================================
# DEFINIZIONE TOOLS MCP
# ============================================================================

TOOLS = [
    # --- Progetto ---
    {
        "name": "nuovo_progetto",
        "description": "Crea un nuovo progetto di calcolo strutturale. La GUI mostrerà la creazione in tempo reale.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nome": {"type": "string", "description": "Nome del progetto"},
                "committente": {"type": "string", "description": "Nome del committente"},
                "indirizzo": {"type": "string", "description": "Indirizzo dell'edificio"}
            },
            "required": ["nome"]
        }
    },
    {
        "name": "get_stato",
        "description": "Ottiene lo stato corrente del progetto: numero muri, aperture, piani, ecc.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "vai_step",
        "description": "Naviga a uno step specifico del workflow",
        "inputSchema": {
            "type": "object",
            "properties": {
                "step": {
                    "type": "string",
                    "enum": ["PROGETTO", "PIANI", "GEOMETRIA", "APERTURE", "FONDAZIONI",
                            "CORDOLI", "SOLAI", "CARICHI", "MATERIALI", "ANALISI", "RISULTATI"],
                    "description": "Step del workflow"
                }
            },
            "required": ["step"]
        }
    },

    # --- Piani ---
    {
        "name": "aggiungi_piano",
        "description": "Aggiunge un nuovo piano all'edificio",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "vai_piano",
        "description": "Seleziona un piano per le operazioni successive",
        "inputSchema": {
            "type": "object",
            "properties": {
                "piano": {"type": "integer", "description": "Numero del piano (0 = terra)"}
            },
            "required": ["piano"]
        }
    },

    # --- Geometria ---
    {
        "name": "disegna_muro",
        "description": "Disegna un muro specificando le coordinate. L'utente vedrà il muro apparire sulla GUI.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x1": {"type": "number", "description": "Coordinata X inizio (metri)"},
                "y1": {"type": "number", "description": "Coordinata Y inizio (metri)"},
                "x2": {"type": "number", "description": "Coordinata X fine (metri)"},
                "y2": {"type": "number", "description": "Coordinata Y fine (metri)"},
                "spessore": {"type": "number", "description": "Spessore muro (default 0.30m)"},
                "altezza": {"type": "number", "description": "Altezza muro (default 3.0m)"}
            },
            "required": ["x1", "y1", "x2", "y2"]
        }
    },
    {
        "name": "disegna_rettangolo",
        "description": "Disegna 4 muri a formare un rettangolo (pianta edificio). L'animazione mostrerà ogni muro.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "number", "description": "Coordinata X angolo sud-ovest"},
                "y": {"type": "number", "description": "Coordinata Y angolo sud-ovest"},
                "larghezza": {"type": "number", "description": "Larghezza in X (metri)"},
                "profondita": {"type": "number", "description": "Profondità in Y (metri)"},
                "spessore": {"type": "number", "description": "Spessore muri (default 0.30m)"}
            },
            "required": ["x", "y", "larghezza", "profondita"]
        }
    },

    # --- Aperture ---
    {
        "name": "aggiungi_apertura",
        "description": "Aggiunge una porta o finestra a un muro esistente",
        "inputSchema": {
            "type": "object",
            "properties": {
                "muro": {"type": "string", "description": "Nome del muro (es. M1)"},
                "tipo": {"type": "string", "enum": ["finestra", "porta", "porta-finestra"]},
                "larghezza": {"type": "number", "description": "Larghezza apertura (m)"},
                "altezza": {"type": "number", "description": "Altezza apertura (m)"},
                "posizione": {"type": "number", "description": "Distanza dal bordo sinistro (m)"},
                "quota": {"type": "number", "description": "Altezza davanzale da terra (m)"}
            },
            "required": ["muro", "tipo", "larghezza", "altezza"]
        }
    },

    # --- Fondazioni ---
    {
        "name": "genera_fondazioni",
        "description": "Genera automaticamente fondazioni per tutti i muri",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "aggiungi_fondazione",
        "description": "Aggiunge una fondazione sotto un muro specifico",
        "inputSchema": {
            "type": "object",
            "properties": {
                "muro": {"type": "string", "description": "Nome del muro (es. M1)"},
                "tipo": {"type": "string", "enum": ["trave_rovescia", "plinto", "platea"]},
                "larghezza": {"type": "number", "description": "Larghezza fondazione (m)"},
                "altezza": {"type": "number", "description": "Altezza fondazione (m)"},
                "profondita": {"type": "number", "description": "Profondità interramento (m)"}
            },
            "required": ["muro"]
        }
    },

    # --- Cordoli ---
    {
        "name": "genera_cordoli",
        "description": "Genera automaticamente cordoli su tutti i muri dell'ultimo piano",
        "inputSchema": {"type": "object", "properties": {}}
    },

    # --- Solai ---
    {
        "name": "genera_solai",
        "description": "Genera automaticamente solai per tutti i piani",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "aggiungi_solaio",
        "description": "Aggiunge un solaio a un piano specifico",
        "inputSchema": {
            "type": "object",
            "properties": {
                "piano": {"type": "integer", "description": "Numero del piano"},
                "tipo": {"type": "string", "description": "Tipo solaio (es. Laterocemento 20+5)"},
                "luce": {"type": "number", "description": "Luce del solaio (m)"},
                "larghezza": {"type": "number", "description": "Larghezza campo (m)"},
                "categoria": {"type": "string", "enum": ["A", "B", "C1", "C2", "C3", "D1", "D2", "E", "F", "H"]}
            },
            "required": ["piano"]
        }
    },

    # --- Analisi ---
    {
        "name": "esegui_analisi",
        "description": "Avvia l'analisi POR (Push-Over Ridotto) secondo NTC 2018",
        "inputSchema": {"type": "object", "properties": {}}
    },

    # --- Vista ---
    {
        "name": "zoom_fit",
        "description": "Adatta la vista per mostrare tutti gli elementi",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "mostra_3d",
        "description": "Mostra la vista 3D dell'edificio",
        "inputSchema": {"type": "object", "properties": {}}
    },

    # --- Utility ---
    {
        "name": "copia_piano",
        "description": "Copia tutti i muri e aperture da un piano all'altro",
        "inputSchema": {
            "type": "object",
            "properties": {
                "da_piano": {"type": "integer", "description": "Piano sorgente"},
                "a_piano": {"type": "integer", "description": "Piano destinazione"}
            },
            "required": ["da_piano", "a_piano"]
        }
    },
    {
        "name": "salva_progetto",
        "description": "Salva il progetto su file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Percorso completo del file"}
            },
            "required": ["filepath"]
        }
    },
    {
        "name": "help",
        "description": "Mostra l'elenco dei comandi disponibili",
        "inputSchema": {"type": "object", "properties": {}}
    }
]


# ============================================================================
# GESTIONE RICHIESTE MCP
# ============================================================================

def process_request(request):
    """Processa una richiesta MCP JSON-RPC"""
    method = request.get("method")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "muratura-gui-controller",
                    "version": "2.0.0"
                }
            }
        }

    elif method == "notifications/initialized":
        return None

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS}
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        # Invia comando alla GUI
        result = send_gui_command(tool_name, tool_args)

        # Formatta risposta
        if result.get('success'):
            text = json.dumps(result, indent=2, ensure_ascii=False)
        else:
            text = f"❌ Errore: {result.get('error', 'Sconosciuto')}"

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": text}]
            }
        }

    elif method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    return None


def main():
    """Loop principale server MCP su stdio"""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line)
            response = process_request(request)

            if response:
                sys.stdout.write(json.dumps(response) + '\n')
                sys.stdout.flush()

        except json.JSONDecodeError:
            continue
        except Exception as e:
            sys.stderr.write(f"Errore: {e}\n")
            sys.stderr.flush()


if __name__ == "__main__":
    main()
