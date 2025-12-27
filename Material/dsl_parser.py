#!/usr/bin/env python3
"""
DSL Parser per Muratura - Caricamento dati testuali

Sintassi compatta su singola riga per definire edifici in muratura.
Estensione file: .mur

Esempio:
    MATERIALE mattoni MATTONI_PIENI BUONA BUONO
    PIANO 0 3.2 12000
    PARETE P1 0 5.0 0.45 mattoni
    APERTURA P1 0 finestra 1.2 1.4 0.0 0.9
"""

import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime


# ============================================================================
# ECCEZIONI
# ============================================================================

class DSLParseError(Exception):
    """Errore di parsing DSL con informazioni sulla riga"""
    def __init__(self, message: str, line_num: int = 0, line_content: str = ""):
        self.line_num = line_num
        self.line_content = line_content
        super().__init__(f"Riga {line_num}: {message}")


class DSLValidationError(Exception):
    """Errore di validazione semantica"""
    pass


# ============================================================================
# STRUTTURE DATI
# ============================================================================

@dataclass
class MaterialeDef:
    """Definizione materiale da tabella NTC"""
    nome: str
    tipo: str  # es. MATTONI_PIENI
    malta: str  # es. BUONA
    conservazione: str  # es. BUONO
    custom: bool = False
    # Parametri custom (solo se custom=True)
    fcm: float = 0.0
    E: float = 0.0
    G: float = 0.0
    tau0: float = 0.0
    peso: float = 0.0


@dataclass
class PianoDef:
    """Definizione piano"""
    indice: int
    altezza: float  # m
    massa: float  # kg


@dataclass
class PareteDef:
    """Definizione parete"""
    nome: str
    piano: int
    lunghezza: float  # m
    spessore: float  # m
    materiale: str  # riferimento a MaterialeDef


@dataclass
class AperturaDef:
    """Definizione apertura"""
    parete: str
    piano: int
    tipo: str  # finestra, porta, nicchia
    larghezza: float  # m
    altezza: float  # m
    x: float  # m dal centro
    y: float  # m dalla base


@dataclass
class CaricoDef:
    """Definizione carico di piano"""
    piano: int
    permanente: float  # kN/m2
    variabile: float  # kN/m2
    copertura: bool = False


@dataclass
class AnalisiDef:
    """Definizione analisi"""
    nome: str
    tipo: str  # PUSHOVER, MODALE, STATICA
    parametri: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DSLProject:
    """Progetto completo parsato dal DSL"""
    nome: str = "Senza nome"
    autore: str = ""
    data: str = ""
    materiali: Dict[str, MaterialeDef] = field(default_factory=dict)
    piani: Dict[int, PianoDef] = field(default_factory=dict)
    pareti: List[PareteDef] = field(default_factory=list)
    aperture: List[AperturaDef] = field(default_factory=list)
    carichi: Dict[int, CaricoDef] = field(default_factory=dict)
    analisi: List[AnalisiDef] = field(default_factory=list)

    def summary(self) -> str:
        """Restituisce un riepilogo del progetto"""
        lines = [
            f"Progetto: {self.nome}",
            f"Autore: {self.autore}" if self.autore else "",
            f"Data: {self.data}" if self.data else "",
            f"Materiali: {len(self.materiali)}",
            f"Piani: {len(self.piani)}",
            f"Pareti: {len(self.pareti)}",
            f"Aperture: {len(self.aperture)}",
            f"Carichi: {len(self.carichi)}",
            f"Analisi: {len(self.analisi)}",
        ]
        return "\n".join(l for l in lines if l)


# ============================================================================
# PARSER
# ============================================================================

class DSLParser:
    """
    Parser per file DSL muratura (.mur)

    Uso:
        parser = DSLParser("edificio.mur")
        project = parser.parse()
    """

    # Comandi riconosciuti
    COMMANDS = {
        'PROGETTO', 'MATERIALE', 'MATERIALE_CUSTOM', 'PIANO',
        'PARETE', 'APERTURA', 'CARICO', 'PUSHOVER', 'MODALE', 'STATICA'
    }

    def __init__(self, filepath: str):
        """
        Inizializza il parser.

        Args:
            filepath: Percorso al file .mur
        """
        self.filepath = Path(filepath)
        self.project = DSLProject()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self._current_line = 0

    def parse(self) -> DSLProject:
        """
        Esegue il parsing del file.

        Returns:
            DSLProject con tutti i dati parsati

        Raises:
            DSLParseError: Se ci sono errori di parsing
            FileNotFoundError: Se il file non esiste
        """
        if not self.filepath.exists():
            raise FileNotFoundError(f"File non trovato: {self.filepath}")

        with open(self.filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            self._current_line = i
            self._parse_line(line.strip(), i)

        # Validazione finale
        self._validate()

        if self.errors:
            raise DSLParseError(
                f"Trovati {len(self.errors)} errori:\n" + "\n".join(self.errors)
            )

        return self.project

    def _tokenize(self, line: str) -> List[str]:
        """
        Divide la riga in token, preservando stringhe tra virgolette.

        Args:
            line: Riga da tokenizzare

        Returns:
            Lista di token
        """
        # Pattern per match stringhe tra virgolette o parole
        pattern = r'"[^"]*"|\'[^\']*\'|\S+'
        tokens = re.findall(pattern, line)
        # Rimuovi virgolette dalle stringhe
        return [t.strip('"\'') for t in tokens]

    def _parse_value(self, value: str) -> Union[int, float, str, bool]:
        """Converte stringa nel tipo appropriato"""
        # Bool
        if value.lower() in ('true', 'vero', 'si'):
            return True
        if value.lower() in ('false', 'falso', 'no'):
            return False
        # Numero
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            return value

    def _parse_line(self, line: str, line_num: int):
        """Parsa una singola riga"""
        # Ignora righe vuote e commenti
        if not line or line.startswith('#'):
            return

        # Rimuovi commenti inline
        if '#' in line:
            line = line[:line.index('#')].strip()
            if not line:
                return

        tokens = self._tokenize(line)
        if not tokens:
            return

        command = tokens[0].upper()
        args = tokens[1:]

        try:
            if command == 'PROGETTO':
                self._parse_progetto(args, line_num)
            elif command == 'MATERIALE':
                self._parse_materiale(args, line_num)
            elif command == 'MATERIALE_CUSTOM':
                self._parse_materiale_custom(args, line_num)
            elif command == 'PIANO':
                self._parse_piano(args, line_num)
            elif command == 'PARETE':
                self._parse_parete(args, line_num)
            elif command == 'APERTURA':
                self._parse_apertura(args, line_num)
            elif command == 'CARICO':
                self._parse_carico(args, line_num)
            elif command == 'PUSHOVER':
                self._parse_pushover(args, line_num)
            elif command == 'MODALE':
                self._parse_modale(args, line_num)
            elif command == 'STATICA':
                self._parse_statica(args, line_num)
            else:
                self.warnings.append(f"Riga {line_num}: Comando sconosciuto '{command}'")
        except Exception as e:
            self.errors.append(f"Riga {line_num}: {str(e)}")

    def _parse_progetto(self, args: List[str], line_num: int):
        """
        PROGETTO "Nome" [AUTORE "autore"] [DATA data]
        """
        i = 0
        while i < len(args):
            if i == 0:
                self.project.nome = args[i]
            elif args[i].upper() == 'AUTORE' and i + 1 < len(args):
                self.project.autore = args[i + 1]
                i += 1
            elif args[i].upper() == 'DATA' and i + 1 < len(args):
                self.project.data = args[i + 1]
                i += 1
            i += 1

    def _parse_materiale(self, args: List[str], line_num: int):
        """
        MATERIALE nome tipo malta conservazione
        """
        if len(args) < 4:
            raise DSLParseError(
                f"MATERIALE richiede 4 parametri (nome tipo malta conservazione), trovati {len(args)}",
                line_num
            )

        nome, tipo, malta, conservazione = args[0], args[1].upper(), args[2].upper(), args[3].upper()

        self.project.materiali[nome] = MaterialeDef(
            nome=nome,
            tipo=tipo,
            malta=malta,
            conservazione=conservazione
        )

    def _parse_materiale_custom(self, args: List[str], line_num: int):
        """
        MATERIALE_CUSTOM nome fcm E G tau0 peso
        """
        if len(args) < 6:
            raise DSLParseError(
                f"MATERIALE_CUSTOM richiede 6 parametri (nome fcm E G tau0 peso), trovati {len(args)}",
                line_num
            )

        nome = args[0]
        try:
            fcm = float(args[1])
            E = float(args[2])
            G = float(args[3])
            tau0 = float(args[4])
            peso = float(args[5])
        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

        self.project.materiali[nome] = MaterialeDef(
            nome=nome,
            tipo="CUSTOM",
            malta="",
            conservazione="",
            custom=True,
            fcm=fcm,
            E=E,
            G=G,
            tau0=tau0,
            peso=peso
        )

    def _parse_piano(self, args: List[str], line_num: int):
        """
        PIANO indice altezza massa_kg
        """
        if len(args) < 3:
            raise DSLParseError(
                f"PIANO richiede 3 parametri (indice altezza massa), trovati {len(args)}",
                line_num
            )

        try:
            indice = int(args[0])
            altezza = float(args[1])
            massa = float(args[2])
        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

        self.project.piani[indice] = PianoDef(
            indice=indice,
            altezza=altezza,
            massa=massa
        )

    def _parse_parete(self, args: List[str], line_num: int):
        """
        PARETE nome piano lunghezza spessore materiale
        """
        if len(args) < 5:
            raise DSLParseError(
                f"PARETE richiede 5 parametri (nome piano lunghezza spessore materiale), trovati {len(args)}",
                line_num
            )

        try:
            nome = args[0]
            piano = int(args[1])
            lunghezza = float(args[2])
            spessore = float(args[3])
            materiale = args[4]
        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

        self.project.pareti.append(PareteDef(
            nome=nome,
            piano=piano,
            lunghezza=lunghezza,
            spessore=spessore,
            materiale=materiale
        ))

    def _parse_apertura(self, args: List[str], line_num: int):
        """
        APERTURA parete piano tipo larghezza altezza x y
        """
        if len(args) < 7:
            raise DSLParseError(
                f"APERTURA richiede 7 parametri (parete piano tipo larghezza altezza x y), trovati {len(args)}",
                line_num
            )

        try:
            parete = args[0]
            piano = int(args[1])
            tipo = args[2].lower()
            larghezza = float(args[3])
            altezza = float(args[4])
            x = float(args[5])
            y = float(args[6])
        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

        self.project.aperture.append(AperturaDef(
            parete=parete,
            piano=piano,
            tipo=tipo,
            larghezza=larghezza,
            altezza=altezza,
            x=x,
            y=y
        ))

    def _parse_carico(self, args: List[str], line_num: int):
        """
        CARICO piano permanente variabile [copertura]
        """
        if len(args) < 3:
            raise DSLParseError(
                f"CARICO richiede almeno 3 parametri (piano permanente variabile), trovati {len(args)}",
                line_num
            )

        try:
            piano = int(args[0])
            permanente = float(args[1])
            variabile = float(args[2])
            copertura = len(args) > 3 and args[3].lower() in ('copertura', 'true', 'si')
        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

        self.project.carichi[piano] = CaricoDef(
            piano=piano,
            permanente=permanente,
            variabile=variabile,
            copertura=copertura
        )

    def _parse_pushover(self, args: List[str], line_num: int):
        """
        PUSHOVER nome direzione pattern target_drift
        """
        if len(args) < 4:
            raise DSLParseError(
                f"PUSHOVER richiede 4 parametri (nome direzione pattern target_drift), trovati {len(args)}",
                line_num
            )

        try:
            nome = args[0]
            direzione = args[1].upper()
            pattern = args[2].lower()
            target_drift = float(args[3])
        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

        self.project.analisi.append(AnalisiDef(
            nome=nome,
            tipo='PUSHOVER',
            parametri={
                'direzione': direzione,
                'pattern': pattern,
                'target_drift': target_drift
            }
        ))

    def _parse_modale(self, args: List[str], line_num: int):
        """
        MODALE nome n_modi
        """
        if len(args) < 2:
            raise DSLParseError(
                f"MODALE richiede 2 parametri (nome n_modi), trovati {len(args)}",
                line_num
            )

        try:
            nome = args[0]
            n_modi = int(args[1])
        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

        self.project.analisi.append(AnalisiDef(
            nome=nome,
            tipo='MODALE',
            parametri={'n_modi': n_modi}
        ))

    def _parse_statica(self, args: List[str], line_num: int):
        """
        STATICA nome {carichi_json}
        """
        if len(args) < 2:
            raise DSLParseError(
                f"STATICA richiede almeno 2 parametri (nome carichi_json), trovati {len(args)}",
                line_num
            )

        nome = args[0]
        # Ricomponi il JSON (potrebbe essere stato splittato)
        json_str = ' '.join(args[1:])
        try:
            carichi = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise DSLParseError(f"JSON carichi non valido: {e}", line_num)

        self.project.analisi.append(AnalisiDef(
            nome=nome,
            tipo='STATICA',
            parametri={'carichi': carichi}
        ))

    def _validate(self):
        """Validazione semantica del progetto"""
        # Verifica riferimenti materiali nelle pareti
        for parete in self.project.pareti:
            if parete.materiale not in self.project.materiali:
                self.errors.append(
                    f"Parete '{parete.nome}' piano {parete.piano}: "
                    f"materiale '{parete.materiale}' non definito"
                )

        # Verifica riferimenti piani nelle pareti
        for parete in self.project.pareti:
            if parete.piano not in self.project.piani:
                self.warnings.append(
                    f"Parete '{parete.nome}': piano {parete.piano} non definito esplicitamente"
                )

        # Verifica riferimenti pareti nelle aperture
        parete_keys = {(p.nome, p.piano) for p in self.project.pareti}
        for apertura in self.project.aperture:
            if (apertura.parete, apertura.piano) not in parete_keys:
                self.errors.append(
                    f"Apertura su parete '{apertura.parete}' piano {apertura.piano}: "
                    f"parete non definita"
                )


# ============================================================================
# ESPORTATORE
# ============================================================================

class DSLExporter:
    """
    Esportatore per generare file .mur da oggetto Muratura

    Uso:
        exporter = DSLExporter(muratura_instance)
        content = exporter.export()
        exporter.save("output.mur")
    """

    def __init__(self, muratura):
        """
        Args:
            muratura: Istanza della classe Muratura da connector.py
        """
        self.m = muratura

    def export(self) -> str:
        """
        Genera il contenuto del file DSL.

        Returns:
            Stringa con contenuto file .mur
        """
        lines = []

        # Header
        lines.append("# " + "=" * 60)
        lines.append(f"# Progetto: {self.m.project_name}")
        lines.append(f"# Generato: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"# Muratura Connector v{self.m.VERSION}")
        lines.append("# " + "=" * 60)
        lines.append("")

        # Progetto
        lines.append(f'PROGETTO "{self.m.project_name}"')
        lines.append("")

        # Materiali
        if self.m.materiali:
            lines.append("# MATERIALI")
            for nome, mat in self.m.materiali.items():
                # Determina se e' un materiale custom
                is_custom = False
                tipo_str = "MATTONI_PIENI"

                if hasattr(mat, 'masonry_type'):
                    tipo_attr = getattr(mat, 'masonry_type', None)
                    if tipo_attr is not None:
                        if hasattr(tipo_attr, 'name'):
                            tipo_str = tipo_attr.name
                        else:
                            tipo_str = str(tipo_attr)
                elif hasattr(mat, 'material_type'):
                    tipo_attr = getattr(mat, 'material_type', None)
                    if tipo_attr is not None:
                        if hasattr(tipo_attr, 'name'):
                            tipo_str = tipo_attr.name
                        else:
                            tipo_str = str(tipo_attr)
                            if 'custom' in tipo_str.lower():
                                is_custom = True

                if is_custom or tipo_str == "CUSTOM":
                    # Materiale custom
                    fcm = getattr(mat, 'fcm', 0)
                    E = getattr(mat, 'E', 0)
                    G = getattr(mat, 'G', 0)
                    tau0 = getattr(mat, 'tau0', 0)
                    peso = getattr(mat, 'weight', 18)
                    lines.append(f"MATERIALE_CUSTOM {nome} {fcm} {E} {G} {tau0} {peso}")
                else:
                    # Materiale da tabella NTC
                    malta = getattr(mat, 'mortar_quality', 'BUONA')
                    cons = getattr(mat, 'conservation', 'BUONO')
                    # Estrai nome enum se necessario
                    if hasattr(malta, 'name'):
                        malta = malta.name
                    if hasattr(cons, 'name'):
                        cons = cons.name
                    lines.append(f"MATERIALE {nome} {tipo_str} {malta} {cons}")
            lines.append("")

        # Piani e Pareti
        if self.m.pareti:
            # Raggruppa per piano
            piani_dict: Dict[int, List] = {}
            for nome, p in self.m.pareti.items():
                n_floors = p.get('n_floors', 1)
                for piano in range(n_floors):
                    if piano not in piani_dict:
                        piani_dict[piano] = []
                    piani_dict[piano].append((nome, p, piano))

            # Esporta piani
            lines.append("# PIANI")
            for piano in sorted(piani_dict.keys()):
                pareti_piano = piani_dict[piano]
                if pareti_piano:
                    p = pareti_piano[0][1]
                    altezza = p['height'] / p.get('n_floors', 1)
                    massa = p.get('floor_masses', {}).get(piano, 0)
                    lines.append(f"PIANO {piano} {altezza:.2f} {massa:.0f}")
            lines.append("")

            # Esporta pareti
            lines.append("# PARETI")
            for nome, p in self.m.pareti.items():
                mat = p.get('materiale', 'default')
                n_floors = p.get('n_floors', 1)
                lunghezza = p['length']
                spessore = p['thickness']
                for piano in range(n_floors):
                    lines.append(f"PARETE {nome} {piano} {lunghezza:.2f} {spessore:.2f} {mat}")
            lines.append("")

        # Carichi (evita duplicati)
        if self.m.pareti:
            carichi_unici: Dict[int, Dict] = {}
            for nome, p in self.m.pareti.items():
                carichi = p.get('carichi', {})
                for piano, c in carichi.items():
                    if piano not in carichi_unici:
                        carichi_unici[piano] = c

            if carichi_unici:
                lines.append("# CARICHI")
                for piano in sorted(carichi_unici.keys()):
                    c = carichi_unici[piano]
                    perm = c.get('permanente', 0)
                    var = c.get('variabile', 0)
                    cop = 'copertura' if c.get('copertura') else ''
                    lines.append(f"CARICO {piano} {perm:.1f} {var:.1f} {cop}".strip())
                lines.append("")

        # Analisi
        if self.m.analisi:
            lines.append("# ANALISI")
            for nome, an in self.m.analisi.items():
                tipo = an.get('type', '').lower()
                opts = an.get('options', {})
                if tipo == 'pushover':
                    # Supporta entrambi i formati di parametri
                    dir_ = opts.get('direzione', opts.get('direction', 'Y'))
                    pat = opts.get('pattern', opts.get('lateral_pattern', 'triangular'))
                    drift = opts.get('target_drift', 0.04)
                    lines.append(f"PUSHOVER {nome} {dir_} {pat} {drift}")
                elif tipo in ('modal', 'modale'):
                    n_modi = opts.get('n_modi', opts.get('n_modes', 6))
                    lines.append(f"MODALE {nome} {n_modi}")
                elif tipo in ('static', 'statica'):
                    carichi_data = an.get('carichi', opts.get('carichi', {}))
                    carichi = json.dumps(carichi_data)
                    lines.append(f"STATICA {nome} {carichi}")
            lines.append("")

        return "\n".join(lines)

    def save(self, filepath: str = None) -> str:
        """
        Salva il file DSL.

        Args:
            filepath: Percorso file output (default: project_name.mur)

        Returns:
            Percorso file salvato
        """
        if filepath is None:
            filepath = self.m.project_path / f"{self.m.project_name}.mur"

        filepath = Path(filepath)
        content = self.export()

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return str(filepath)


# ============================================================================
# FUNZIONI HELPER
# ============================================================================

def load_dsl(filepath: str) -> DSLProject:
    """
    Carica un file DSL e restituisce il progetto.

    Args:
        filepath: Percorso al file .mur

    Returns:
        DSLProject con i dati parsati
    """
    parser = DSLParser(filepath)
    return parser.parse()


def parse_dsl_string(content: str) -> DSLProject:
    """
    Parsa una stringa DSL (utile per test).

    Args:
        content: Contenuto DSL come stringa

    Returns:
        DSLProject con i dati parsati
    """
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mur', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name

    try:
        return load_dsl(temp_path)
    finally:
        Path(temp_path).unlink()


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    # Test del parser
    test_content = """
# Test edificio
PROGETTO "Edificio Test" AUTORE "Test" DATA 2024-01-15

# Materiali
MATERIALE mattoni MATTONI_PIENI BUONA BUONO
MATERIALE pietra PIETRA_SQUADRATA BUONA MEDIOCRE
MATERIALE_CUSTOM cls 25.0 30000 12500 0.3 25

# Piani
PIANO 0 3.2 12000
PIANO 1 3.0 10000

# Pareti
PARETE P1 0 5.0 0.45 mattoni
PARETE P2 0 4.0 0.45 pietra
PARETE P1 1 5.0 0.30 mattoni

# Aperture
APERTURA P1 0 finestra 1.2 1.4 0.0 0.9
APERTURA P1 0 porta 0.9 2.1 -1.5 0.0

# Carichi
CARICO 0 5.0 2.0
CARICO 1 4.0 2.0 copertura

# Analisi
PUSHOVER analisi_x X triangular 0.04
MODALE modale1 6
"""

    print("Test DSL Parser")
    print("=" * 60)

    project = parse_dsl_string(test_content)
    print(project.summary())
    print()
    print("Materiali:", list(project.materiali.keys()))
    print("Piani:", list(project.piani.keys()))
    print("Pareti:", [(p.nome, p.piano) for p in project.pareti])
    print("Aperture:", [(a.parete, a.piano, a.tipo) for a in project.aperture])
    print("Analisi:", [(a.nome, a.tipo) for a in project.analisi])
