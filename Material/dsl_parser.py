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
    """Definizione parete (senza coordinate)"""
    nome: str
    piano: int
    lunghezza: float  # m
    spessore: float  # m
    materiale: str  # riferimento a MaterialeDef


@dataclass
class MuroDef:
    """Definizione muro con coordinate assolute"""
    nome: str
    x1: float  # m - punto iniziale X
    y1: float  # m - punto iniziale Y
    x2: float  # m - punto finale X
    y2: float  # m - punto finale Y
    z: float   # m - quota base (0 = terra)
    altezza: float  # m
    spessore: float  # m
    materiale: str

    @property
    def lunghezza(self) -> float:
        """Calcola lunghezza dalla distanza tra i punti"""
        import math
        return math.sqrt((self.x2 - self.x1)**2 + (self.y2 - self.y1)**2)

    @property
    def angolo(self) -> float:
        """Calcola angolo in gradi rispetto all'asse X"""
        import math
        return math.degrees(math.atan2(self.y2 - self.y1, self.x2 - self.x1))

    @property
    def centro(self) -> tuple:
        """Restituisce il punto centrale (x, y)"""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


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
class CordoloDef:
    """Definizione cordolo (ring beam)"""
    nome: str
    piano: int  # piano su cui è posizionato (alla sommità)
    base: float  # larghezza sezione [m]
    altezza: float  # altezza sezione [m]
    materiale: str  # es. calcestruzzo, acciaio
    # Coordinate opzionali (se None, cordolo perimetrale)
    x1: Optional[float] = None
    y1: Optional[float] = None
    x2: Optional[float] = None
    y2: Optional[float] = None

    @property
    def is_perimetrale(self) -> bool:
        """True se è un cordolo perimetrale (senza coordinate specifiche)"""
        return self.x1 is None

    @property
    def area(self) -> float:
        """Area sezione [m²]"""
        return self.base * self.altezza

    @property
    def inerzia(self) -> float:
        """Momento d'inerzia [m⁴]"""
        return self.base * self.altezza**3 / 12


@dataclass
class SolaioDef:
    """Definizione solaio"""
    nome: str
    piano: int                      # Piano (0 = terra)
    tipo: str = "laterocemento"     # laterocemento, legno, acciaio, ca_pieno, volta
    preset: str = "LAT_20+4"        # Preset dal database

    # Geometria
    luce: float = 5.0               # Luce [m]
    larghezza: float = 5.0          # Larghezza [m]
    orditura: float = 0.0           # Angolo orditura [gradi]

    # Carichi
    peso_proprio: float = 3.2       # G1 [kN/m2]
    peso_finiture: float = 1.5      # G2 [kN/m2]
    carico_variabile: float = 2.0   # Qk [kN/m2]
    categoria_uso: str = "A"        # Categoria NTC

    # Rigidezza
    rigidezza: str = "rigido"       # rigido, semi_rigido, flessibile

    @property
    def Gk(self) -> float:
        """Carico permanente totale [kN/m2]"""
        return self.peso_proprio + self.peso_finiture

    @property
    def carico_totale(self) -> float:
        """Carico totale caratteristico [kN/m2]"""
        return self.Gk + self.carico_variabile


@dataclass
class DSLProject:
    """Progetto completo parsato dal DSL"""
    nome: str = "Senza nome"
    autore: str = ""
    data: str = ""
    materiali: Dict[str, MaterialeDef] = field(default_factory=dict)
    piani: Dict[int, PianoDef] = field(default_factory=dict)
    pareti: List[PareteDef] = field(default_factory=list)
    muri: List[MuroDef] = field(default_factory=list)  # Muri con coordinate
    aperture: List[AperturaDef] = field(default_factory=list)
    cordoli: List[CordoloDef] = field(default_factory=list)  # Cordoli
    solai: List[SolaioDef] = field(default_factory=list)  # Solai
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
            f"Pareti: {len(self.pareti)}" if self.pareti else "",
            f"Muri: {len(self.muri)}" if self.muri else "",
            f"Aperture: {len(self.aperture)}",
            f"Cordoli: {len(self.cordoli)}" if self.cordoli else "",
            f"Solai: {len(self.solai)}" if self.solai else "",
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
        'PROGETTO', 'MATERIALE', 'MATERIALE_CUSTOM', 'PIANO', 'PIANI',
        'PARETE', 'MURO', 'APERTURA', 'FINESTRA', 'PORTA',
        'CARICO', 'CARICHI', 'EDIFICIO',
        'PUSHOVER', 'MODALE', 'STATICA',
        'CORDOLO', 'CORDOLO_LINEA',
        'SOLAIO'
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
            elif command == 'PIANI':
                self._parse_piani(args, line_num)
            elif command == 'PARETE':
                self._parse_parete(args, line_num)
            elif command == 'MURO':
                self._parse_muro(args, line_num)
            elif command == 'APERTURA':
                self._parse_apertura(args, line_num)
            elif command == 'FINESTRA':
                self._parse_finestra(args, line_num)
            elif command == 'PORTA':
                self._parse_porta(args, line_num)
            elif command == 'CARICO':
                self._parse_carico(args, line_num)
            elif command == 'CARICHI':
                self._parse_carichi(args, line_num)
            elif command == 'EDIFICIO':
                self._parse_edificio(args, line_num)
            elif command == 'PUSHOVER':
                self._parse_pushover(args, line_num)
            elif command == 'MODALE':
                self._parse_modale(args, line_num)
            elif command == 'STATICA':
                self._parse_statica(args, line_num)
            elif command == 'CORDOLO':
                self._parse_cordolo(args, line_num)
            elif command == 'CORDOLO_LINEA':
                self._parse_cordolo_linea(args, line_num)
            elif command == 'SOLAIO':
                self._parse_solaio(args, line_num)
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

    def _parse_piani(self, args: List[str], line_num: int):
        """
        PIANI n_piani altezza massa
        Crea n piani tutti uguali (indici 0 a n-1)

        Oppure con altezze/masse diverse:
        PIANI 3 ALTEZZE 3.2,3.0,2.8 MASSE 12000,10000,8000
        """
        if len(args) < 3:
            raise DSLParseError(
                f"PIANI richiede almeno 3 parametri (n_piani altezza massa)",
                line_num
            )

        try:
            n_piani = int(args[0])

            # Controlla se ci sono liste di valori
            altezze = []
            masse = []

            i = 1
            while i < len(args):
                if args[i].upper() == 'ALTEZZE' and i + 1 < len(args):
                    altezze = [float(x) for x in args[i + 1].split(',')]
                    i += 2
                elif args[i].upper() == 'MASSE' and i + 1 < len(args):
                    masse = [float(x) for x in args[i + 1].split(',')]
                    i += 2
                else:
                    # Formato semplice: PIANI n altezza massa
                    if not altezze:
                        altezze = [float(args[1])] * n_piani
                    if not masse:
                        masse = [float(args[2])] * n_piani
                    break

            # Crea i piani
            for idx in range(n_piani):
                alt = altezze[idx] if idx < len(altezze) else altezze[-1]
                mas = masse[idx] if idx < len(masse) else masse[-1]
                self.project.piani[idx] = PianoDef(indice=idx, altezza=alt, massa=mas)

        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

    def _parse_carichi(self, args: List[str], line_num: int):
        """
        CARICHI permanente variabile [copertura_ultimo]
        Applica gli stessi carichi a tutti i piani definiti
        """
        if len(args) < 2:
            raise DSLParseError(
                f"CARICHI richiede almeno 2 parametri (permanente variabile)",
                line_num
            )

        try:
            permanente = float(args[0])
            variabile = float(args[1])
            copertura_ultimo = len(args) > 2 and args[2].lower() in ('copertura', 'true', 'si')
        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

        # Applica a tutti i piani
        piani = list(self.project.piani.keys()) if self.project.piani else [0]
        for piano in piani:
            is_ultimo = (piano == max(piani)) if piani else False
            self.project.carichi[piano] = CaricoDef(
                piano=piano,
                permanente=permanente,
                variabile=variabile,
                copertura=copertura_ultimo and is_ultimo
            )

    def _parse_edificio(self, args: List[str], line_num: int):
        """
        EDIFICIO n_piani altezza_piano massa_piano materiale pareti

        Esempio:
        EDIFICIO 3 3.0 10000 mattoni P1:5.0:0.45,P2:4.0:0.45,P3:3.5:0.30

        Crea automaticamente:
        - 3 piani (0, 1, 2) con altezza 3.0m e massa 10000kg
        - Pareti P1, P2, P3 su tutti i piani con le dimensioni specificate
        """
        if len(args) < 5:
            raise DSLParseError(
                f"EDIFICIO richiede 5 parametri (n_piani altezza massa materiale pareti)",
                line_num
            )

        try:
            n_piani = int(args[0])
            altezza = float(args[1])
            massa = float(args[2])
            materiale = args[3]
            pareti_str = args[4]

            # Crea i piani
            for idx in range(n_piani):
                self.project.piani[idx] = PianoDef(
                    indice=idx,
                    altezza=altezza,
                    massa=massa
                )

            # Parsa le pareti: P1:5.0:0.45,P2:4.0:0.45
            for parete_def in pareti_str.split(','):
                parts = parete_def.split(':')
                if len(parts) >= 3:
                    nome = parts[0]
                    lunghezza = float(parts[1])
                    spessore = float(parts[2])

                    # Crea la parete su tutti i piani
                    for piano in range(n_piani):
                        self.project.pareti.append(PareteDef(
                            nome=nome,
                            piano=piano,
                            lunghezza=lunghezza,
                            spessore=spessore,
                            materiale=materiale
                        ))

        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

    def _parse_muro(self, args: List[str], line_num: int):
        """
        MURO nome x1 y1 x2 y2 z altezza spessore materiale

        Esempio:
        MURO PN 0 0 8.5 0 0 3.2 0.45 mattoni      # Parete nord piano terra
        MURO PN 0 0 8.5 0 3.2 3.0 0.30 mattoni    # Parete nord piano 1 (z=3.2)
        MURO PS 0 6 8.5 6 0 3.2 0.45 mattoni      # Parete sud
        """
        if len(args) < 9:
            raise DSLParseError(
                f"MURO richiede 9 parametri (nome x1 y1 x2 y2 z altezza spessore materiale), trovati {len(args)}",
                line_num
            )

        try:
            nome = args[0]
            x1 = float(args[1])
            y1 = float(args[2])
            x2 = float(args[3])
            y2 = float(args[4])
            z = float(args[5])
            altezza = float(args[6])
            spessore = float(args[7])
            materiale = args[8]
        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

        self.project.muri.append(MuroDef(
            nome=nome,
            x1=x1, y1=y1,
            x2=x2, y2=y2,
            z=z,
            altezza=altezza,
            spessore=spessore,
            materiale=materiale
        ))

    def _parse_finestra(self, args: List[str], line_num: int):
        """
        FINESTRA muro larghezza altezza distanza_da_inizio quota_da_z

        Esempio:
        FINESTRA PN 1.2 1.4 2.0 0.9   # Finestra su muro PN, larga 1.2, alta 1.4
                                       # a 2.0m dall'inizio del muro, 0.9m da terra
        """
        if len(args) < 5:
            raise DSLParseError(
                f"FINESTRA richiede 5 parametri (muro larghezza altezza distanza quota), trovati {len(args)}",
                line_num
            )

        try:
            muro = args[0]
            larghezza = float(args[1])
            altezza = float(args[2])
            distanza = float(args[3])  # distanza dall'inizio del muro
            quota = float(args[4])      # quota dalla base del muro
        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

        # Trova il muro di riferimento per calcolare la posizione x
        muro_ref = next((m for m in self.project.muri if m.nome == muro), None)
        if muro_ref:
            # Calcola posizione x relativa al centro del muro
            x_centro = distanza - muro_ref.lunghezza / 2
            # Usa z del muro come riferimento piano
            piano = int(muro_ref.z / 3.0)  # Stima piano dalla quota
        else:
            x_centro = distanza
            piano = 0

        self.project.aperture.append(AperturaDef(
            parete=muro,
            piano=piano,
            tipo='finestra',
            larghezza=larghezza,
            altezza=altezza,
            x=x_centro,
            y=quota
        ))

    def _parse_porta(self, args: List[str], line_num: int):
        """
        PORTA muro larghezza altezza distanza_da_inizio

        Esempio:
        PORTA PN 0.9 2.1 4.0   # Porta su muro PN, a 4.0m dall'inizio
        """
        if len(args) < 4:
            raise DSLParseError(
                f"PORTA richiede 4 parametri (muro larghezza altezza distanza), trovati {len(args)}",
                line_num
            )

        try:
            muro = args[0]
            larghezza = float(args[1])
            altezza = float(args[2])
            distanza = float(args[3])
        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

        muro_ref = next((m for m in self.project.muri if m.nome == muro), None)
        if muro_ref:
            x_centro = distanza - muro_ref.lunghezza / 2
            piano = int(muro_ref.z / 3.0)
        else:
            x_centro = distanza
            piano = 0

        self.project.aperture.append(AperturaDef(
            parete=muro,
            piano=piano,
            tipo='porta',
            larghezza=larghezza,
            altezza=altezza,
            x=x_centro,
            y=0.0  # Porte partono da terra
        ))

    def _parse_range(self, value: str) -> List[int]:
        """
        Parsa un range di piani: '0:2' o '0-2' -> [0, 1, 2], '1' -> [1]
        Supporta anche '*' per tutti i piani definiti.
        """
        value = value.strip()
        if value == '*':
            return list(self.project.piani.keys()) if self.project.piani else [0]
        if ':' in value:
            start, end = value.split(':')
            return list(range(int(start), int(end) + 1))
        if '-' in value and not value.startswith('-'):
            start, end = value.split('-')
            return list(range(int(start), int(end) + 1))
        return [int(value)]

    def _parse_parete(self, args: List[str], line_num: int):
        """
        PARETE nome piano lunghezza spessore materiale
        Supporta range piani: PARETE P1 0:2 5.0 0.45 mattoni
        """
        if len(args) < 5:
            raise DSLParseError(
                f"PARETE richiede 5 parametri (nome piano lunghezza spessore materiale), trovati {len(args)}",
                line_num
            )

        try:
            nome = args[0]
            piani = self._parse_range(args[1])
            lunghezza = float(args[2])
            spessore = float(args[3])
            materiale = args[4]
        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

        # Crea una parete per ogni piano nel range
        for piano in piani:
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
        Supporta range piani: APERTURA P1 0:2 finestra 1.2 1.4 0 0.9
        """
        if len(args) < 7:
            raise DSLParseError(
                f"APERTURA richiede 7 parametri (parete piano tipo larghezza altezza x y), trovati {len(args)}",
                line_num
            )

        try:
            parete = args[0]
            piani = self._parse_range(args[1])
            tipo = args[2].lower()
            larghezza = float(args[3])
            altezza = float(args[4])
            x = float(args[5])
            y = float(args[6])
        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

        # Crea un'apertura per ogni piano nel range
        for piano in piani:
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

    def _parse_cordolo(self, args: List[str], line_num: int):
        """
        CORDOLO nome piano base altezza [materiale]

        Cordolo perimetrale su tutto il piano (alla sommità delle pareti).
        Se materiale non specificato, usa 'calcestruzzo'.

        Esempio:
        CORDOLO C1 0 0.30 0.25                  # Piano 0, sezione 30x25cm, cls
        CORDOLO C2 1 0.30 0.25 calcestruzzo    # Piano 1, sezione 30x25cm
        CORDOLO C3 2 0.25 0.20 acciaio         # Piano 2, sezione 25x20cm, acciaio
        """
        if len(args) < 4:
            raise DSLParseError(
                f"CORDOLO richiede almeno 4 parametri (nome piano base altezza [materiale]), "
                f"trovati {len(args)}",
                line_num
            )

        try:
            nome = args[0]
            piano = int(args[1])
            base = float(args[2])
            altezza = float(args[3])
            materiale = args[4] if len(args) > 4 else 'calcestruzzo'
        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

        self.project.cordoli.append(CordoloDef(
            nome=nome,
            piano=piano,
            base=base,
            altezza=altezza,
            materiale=materiale
        ))

    def _parse_cordolo_linea(self, args: List[str], line_num: int):
        """
        CORDOLO_LINEA nome piano base altezza materiale x1 y1 x2 y2

        Cordolo con coordinate specifiche (non perimetrale).

        Esempio:
        CORDOLO_LINEA CL1 0 0.30 0.25 calcestruzzo 0 0 10 0
        # Piano 0, sezione 30x25cm, da (0,0) a (10,0)
        """
        if len(args) < 9:
            raise DSLParseError(
                f"CORDOLO_LINEA richiede 9 parametri "
                f"(nome piano base altezza materiale x1 y1 x2 y2), "
                f"trovati {len(args)}",
                line_num
            )

        try:
            nome = args[0]
            piano = int(args[1])
            base = float(args[2])
            altezza = float(args[3])
            materiale = args[4]
            x1 = float(args[5])
            y1 = float(args[6])
            x2 = float(args[7])
            y2 = float(args[8])

        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

        self.project.cordoli.append(CordoloDef(
            nome=nome,
            piano=piano,
            base=base,
            altezza=altezza,
            materiale=materiale,
            x1=x1, y1=y1,
            x2=x2, y2=y2
        ))

    def _parse_solaio(self, args: List[str], line_num: int):
        """
        SOLAIO nome piano tipo preset luce larghezza orditura G1 G2 Qk categoria rigidezza

        Definisce un solaio con tutti i parametri.

        Esempio:
        SOLAIO S1 1 laterocemento LAT_20+4 5.00 4.00 0.0 3.20 1.50 2.00 A rigido
        """
        if len(args) < 12:
            raise DSLParseError(
                f"SOLAIO richiede 12 parametri "
                f"(nome piano tipo preset luce larghezza orditura G1 G2 Qk categoria rigidezza), "
                f"trovati {len(args)}",
                line_num
            )

        try:
            nome = args[0]
            piano = int(args[1])
            tipo = args[2]
            preset = args[3]
            luce = float(args[4])
            larghezza = float(args[5])
            orditura = float(args[6])
            peso_proprio = float(args[7])
            peso_finiture = float(args[8])
            carico_variabile = float(args[9])
            categoria_uso = args[10]
            rigidezza = args[11]

        except ValueError as e:
            raise DSLParseError(f"Valori numerici non validi: {e}", line_num)

        self.project.solai.append(SolaioDef(
            nome=nome,
            piano=piano,
            tipo=tipo,
            preset=preset,
            luce=luce,
            larghezza=larghezza,
            orditura=orditura,
            peso_proprio=peso_proprio,
            peso_finiture=peso_finiture,
            carico_variabile=carico_variabile,
            categoria_uso=categoria_uso,
            rigidezza=rigidezza
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

        # Verifica riferimenti materiali nei muri
        for muro in self.project.muri:
            if muro.materiale not in self.project.materiali:
                self.errors.append(
                    f"Muro '{muro.nome}' z={muro.z}: "
                    f"materiale '{muro.materiale}' non definito"
                )

        # Verifica riferimenti piani nelle pareti
        for parete in self.project.pareti:
            if parete.piano not in self.project.piani:
                self.warnings.append(
                    f"Parete '{parete.nome}': piano {parete.piano} non definito esplicitamente"
                )

        # Verifica riferimenti pareti/muri nelle aperture
        parete_keys = {(p.nome, p.piano) for p in self.project.pareti}
        muro_nomi = {m.nome for m in self.project.muri}

        for apertura in self.project.aperture:
            # Se esiste un muro con quel nome, l'apertura e' valida
            if apertura.parete in muro_nomi:
                continue
            # Altrimenti cerca nelle pareti tradizionali
            if (apertura.parete, apertura.piano) not in parete_keys:
                self.errors.append(
                    f"Apertura su parete '{apertura.parete}' piano {apertura.piano}: "
                    f"parete non definita"
                )

        # Verifica cordoli
        for cordolo in self.project.cordoli:
            # I cordoli usano materiali speciali (calcestruzzo, acciaio) non nella lista materiali muratura
            # quindi non verifichiamo il materiale, ma solo il piano
            if cordolo.piano not in self.project.piani and self.project.piani:
                self.warnings.append(
                    f"Cordolo '{cordolo.nome}': piano {cordolo.piano} non definito esplicitamente"
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
                # NOTA: MaterialProperties usa 'material_type' come stringa descrittiva
                is_custom = False
                tipo_str = "MATTONI_PIENI"

                # Usa material_type (attributo standard di MaterialProperties)
                tipo_attr = getattr(mat, 'material_type', None)
                if tipo_attr is not None and tipo_attr != "":
                    if hasattr(tipo_attr, 'name'):
                        # Se e' un enum
                        tipo_str = tipo_attr.name
                    else:
                        tipo_str = str(tipo_attr)
                        if 'custom' in tipo_str.lower() or 'multistrato' in tipo_str.lower():
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

        # Cordoli
        if hasattr(self.m, 'cordoli') and self.m.cordoli:
            lines.append("# CORDOLI")
            for cordolo in self.m.cordoli:
                if isinstance(cordolo, dict):
                    nome = cordolo.get('nome', 'C1')
                    piano = cordolo.get('piano', 0)
                    base = cordolo.get('base', 0.3)
                    altezza = cordolo.get('altezza', 0.25)
                    materiale = cordolo.get('materiale', 'calcestruzzo')
                    x1 = cordolo.get('x1')
                    y1 = cordolo.get('y1')
                    x2 = cordolo.get('x2')
                    y2 = cordolo.get('y2')
                else:
                    # Se è un oggetto CordoloDef
                    nome = cordolo.nome
                    piano = cordolo.piano
                    base = cordolo.base
                    altezza = cordolo.altezza
                    materiale = cordolo.materiale
                    x1 = cordolo.x1
                    y1 = cordolo.y1
                    x2 = cordolo.x2
                    y2 = cordolo.y2

                if x1 is not None:
                    # Cordolo con coordinate
                    lines.append(f"CORDOLO_LINEA {nome} {piano} {base:.2f} {altezza:.2f} {materiale} {x1:.2f} {y1:.2f} {x2:.2f} {y2:.2f}")
                else:
                    # Cordolo perimetrale
                    lines.append(f"CORDOLO {nome} {piano} {base:.2f} {altezza:.2f} {materiale}")
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
# WIZARD INTERATTIVO
# ============================================================================

def genera_edificio(
    nome_progetto: str,
    n_piani: int,
    pareti: List[Dict],
    materiale: str = "MATTONI_PIENI",
    malta: str = "BUONA",
    conservazione: str = "BUONO",
    altezza_piano: float = 3.0,
    massa_piano: float = 10000,
    carico_permanente: float = 5.0,
    carico_variabile: float = 2.0,
    output_file: str = None
) -> str:
    """
    Genera un file DSL per un edificio completo.

    Args:
        nome_progetto: Nome del progetto
        n_piani: Numero di piani
        pareti: Lista di dict con definizione pareti:
                [{'nome': 'P1', 'lunghezza': 5.0, 'spessore': 0.45}, ...]
        materiale: Tipo muratura NTC (default: MATTONI_PIENI)
        malta: Qualita' malta (default: BUONA)
        conservazione: Stato conservazione (default: BUONO)
        altezza_piano: Altezza interpiano in m (default: 3.0)
        massa_piano: Massa per piano in kg (default: 10000)
        carico_permanente: Carico permanente kN/m2 (default: 5.0)
        carico_variabile: Carico variabile kN/m2 (default: 2.0)
        output_file: Percorso file output (opzionale)

    Returns:
        Contenuto del file DSL generato

    Esempio:
        content = genera_edificio(
            "Casa Rossi",
            n_piani=3,
            pareti=[
                {'nome': 'PN', 'lunghezza': 8.0, 'spessore': 0.45},
                {'nome': 'PS', 'lunghezza': 8.0, 'spessore': 0.45},
                {'nome': 'PE', 'lunghezza': 6.0, 'spessore': 0.45},
                {'nome': 'PO', 'lunghezza': 6.0, 'spessore': 0.45},
            ],
            output_file="casa_rossi.mur"
        )
    """
    lines = []

    # Header
    lines.append("# " + "=" * 60)
    lines.append(f"# Progetto: {nome_progetto}")
    lines.append(f"# Generato automaticamente con genera_edificio()")
    lines.append("# " + "=" * 60)
    lines.append("")

    # Progetto
    lines.append(f'PROGETTO "{nome_progetto}"')
    lines.append("")

    # Materiale
    lines.append("# MATERIALE")
    lines.append(f"MATERIALE muratura {materiale} {malta} {conservazione}")
    lines.append("")

    # Piani (usando sintassi compatta)
    lines.append("# PIANI")
    lines.append(f"PIANI {n_piani} {altezza_piano} {massa_piano}")
    lines.append("")

    # Pareti (usando range)
    lines.append("# PARETI")
    for p in pareti:
        nome = p.get('nome', 'P')
        lunghezza = p.get('lunghezza', 5.0)
        spessore = p.get('spessore', 0.45)
        lines.append(f"PARETE {nome} 0:{n_piani-1} {lunghezza} {spessore} muratura")
    lines.append("")

    # Carichi
    lines.append("# CARICHI")
    lines.append(f"CARICHI {carico_permanente} {carico_variabile} copertura")
    lines.append("")

    # Analisi standard
    lines.append("# ANALISI")
    lines.append("PUSHOVER push_X X triangular 0.04")
    lines.append("PUSHOVER push_Y Y triangular 0.04")
    lines.append("MODALE modale 6")
    lines.append("")

    content = "\n".join(lines)

    # Salva su file se richiesto
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"File generato: {output_file}")

    return content


def wizard_dsl() -> str:
    """
    Wizard interattivo per creare un file DSL.

    Returns:
        Contenuto del file DSL generato
    """
    print("\n" + "=" * 60)
    print("   WIZARD CREAZIONE EDIFICIO IN MURATURA")
    print("=" * 60 + "\n")

    # Nome progetto
    nome = input("Nome progetto: ").strip() or "Nuovo Edificio"

    # Piani
    while True:
        try:
            n_piani = int(input("Numero di piani [3]: ").strip() or "3")
            break
        except ValueError:
            print("Inserisci un numero valido")

    altezza = float(input("Altezza interpiano in m [3.0]: ").strip() or "3.0")
    massa = float(input("Massa per piano in kg [10000]: ").strip() or "10000")

    # Materiale
    print("\nTipi muratura disponibili:")
    tipi = [
        "MATTONI_PIENI", "MATTONI_SEMIPIENI", "PIETRA_SQUADRATA",
        "PIETRA_IRREGOLARE", "BLOCCHI_LATERIZIO", "BLOCCHI_CLS"
    ]
    for i, t in enumerate(tipi, 1):
        print(f"  {i}. {t}")

    scelta = input("Scegli tipo muratura [1]: ").strip() or "1"
    materiale = tipi[int(scelta) - 1] if scelta.isdigit() and 1 <= int(scelta) <= len(tipi) else tipi[0]

    # Pareti
    print("\nDefinisci le pareti (invio vuoto per terminare):")
    pareti = []
    i = 1
    while True:
        nome_p = input(f"  Nome parete {i} (es. PN, PS, PE, PO): ").strip()
        if not nome_p:
            if not pareti:
                print("  Devi definire almeno una parete!")
                continue
            break

        lungh = float(input(f"  Lunghezza {nome_p} in m [5.0]: ").strip() or "5.0")
        spess = float(input(f"  Spessore {nome_p} in m [0.45]: ").strip() or "0.45")

        pareti.append({'nome': nome_p, 'lunghezza': lungh, 'spessore': spess})
        i += 1

    # Carichi
    print("\nCarichi:")
    perm = float(input("  Carico permanente kN/m2 [5.0]: ").strip() or "5.0")
    var = float(input("  Carico variabile kN/m2 [2.0]: ").strip() or "2.0")

    # Output
    output = input("\nFile output (invio per solo visualizzare): ").strip() or None

    # Genera
    content = genera_edificio(
        nome_progetto=nome,
        n_piani=n_piani,
        pareti=pareti,
        materiale=materiale,
        altezza_piano=altezza,
        massa_piano=massa,
        carico_permanente=perm,
        carico_variabile=var,
        output_file=output
    )

    print("\n" + "=" * 60)
    print("FILE DSL GENERATO:")
    print("=" * 60)
    print(content)

    return content


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
