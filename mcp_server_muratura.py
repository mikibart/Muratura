import sys
import json
import traceback
import io
import contextlib

# Utilità per silenziare i print del motore originale durante l'avvio
@contextlib.contextmanager
def suppress_stdout():
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        yield

# Importiamo il motore proteggendo lo stdout
# Nota: Quando spostato in D:\Muratura, questo import funzionerà
with suppress_stdout():
    try:
        from connector import Muratura
    except ImportError:
        # Fallback se le path non sono ancora settate (durante i test)
        sys.path.append('.')
        try:
            from connector import Muratura
        except ImportError:
            pass # Gestiremo l'errore nell'init reale se manca

# Inizializziamo il motore (silenzioso)
engine = None
def get_engine():
    global engine
    if engine is None:
        with suppress_stdout():
            try:
                engine = Muratura("MCP_Session")
            except Exception as e:
                return None, str(e)
    return engine, None

def run_tool(name, args):
    """Esegue i comandi sul motore Muratura e cattura l'output"""
    eng, err = get_engine()
    if err:
        return f"Errore inizializzazione motore: {err}"
    
    # Cattura output testuale dei comandi (es. m.status())
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        try:
            if name == "crea_materiale":
                eng.materiale(
                    args["nome"],
                    args["tipo_ntc"],
                    args.get("qualita_malta", "BUONA")
                )
                return f"Materiale '{args['nome']}' creato con successo."

            elif name == "crea_parete":
                eng.parete(
                    args["nome"],
                    float(args["lunghezza"]),
                    float(args["altezza"]),
                    float(args["spessore"]),
                    int(args.get("piani", 1))
                )
                return f"Parete '{args['nome']}' creata."

            elif name == "lista_elementi":
                eng.lista()
                return f.getvalue()

            elif name == "assegna_materiale":
                eng.assegna_materiale(args["nome_parete"], args["nome_materiale"])
                return f"Materiale {args['nome_materiale']} assegnato a {args['nome_parete']}"

            elif name == "calcola_spettro":
                # Simula una chiamata a funzioni sismiche se disponibili
                # In futuro collegheremo Material.seismic
                return "Calcolo spettro eseguito (Simulazione: Ag=0.25g, Tc=0.4s)"

            elif name == "stato_progetto":
                eng.status()
                return f.getvalue()
            
            else:
                return f"Strumento '{name}' non trovato."

        except Exception as e:
            return f"Errore durante l'esecuzione: {str(e)}\n{traceback.format_exc()}"

def process_request(request):
    method = request.get("method")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "Muratura-MCP-Server",
                    "version": "1.0.0"
                }
            }
        }

    elif method == "notifications/initialized":
        return None

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "crea_materiale",
                        "description": "Crea un nuovo materiale muratura secondo NTC 2018",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "nome": {"type": "string"},
                                "tipo_ntc": {"type": "string", "description": "Es: MATTONI_PIENI, PIETRA_IRREGOLARE"},
                                "qualita_malta": {"type": "string", "enum": ["SCADENTE", "BUONA", "OTTIMA"]}
                            },
                            "required": ["nome", "tipo_ntc"]
                        }
                    },
                    {
                        "name": "crea_parete",
                        "description": "Definisce una nuova parete strutturale",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "nome": {"type": "string"},
                                "lunghezza": {"type": "number"},
                                "altezza": {"type": "number"},
                                "spessore": {"type": "number"},
                                "piani": {"type": "integer"}
                            },
                            "required": ["nome", "lunghezza", "altezza", "spessore"]
                        }
                    },
                    {
                        "name": "assegna_materiale",
                        "description": "Assegna un materiale esistente ad una parete",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "nome_parete": {"type": "string"},
                                "nome_materiale": {"type": "string"}
                            },
                            "required": ["nome_parete", "nome_materiale"]
                        }
                    },
                    {
                        "name": "lista_elementi",
                        "description": "Elenca tutti i materiali e le pareti presenti nel progetto",
                        "inputSchema": {"type": "object", "properties": {}}
                    },
                    {
                        "name": "stato_progetto",
                        "description": "Mostra lo stato del motore e dei moduli caricati",
                        "inputSchema": {"type": "object", "properties": {}}
                    }
                ]
            }
        }

    elif method == "tools/call":
        result = run_tool(params.get("name"), params.get("arguments", {}))
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": str(result)}]
            }
        }

    elif method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    return None

def main():
    # Loop principale di lettura/scrittura su Stdio
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            request = json.loads(line)
            response = process_request(request)
            
            if response:
                print(json.dumps(response))
                sys.stdout.flush()
                
        except json.JSONDecodeError:
            continue
        except Exception:
            # Loggare su stderr per non rompere il protocollo JSON su stdout
            sys.stderr.write(traceback.format_exc())
            sys.stderr.flush()

if __name__ == "__main__":
    main()
