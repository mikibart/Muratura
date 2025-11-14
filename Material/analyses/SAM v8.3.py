"""
SAM v8.3 - Plugin Architecture
Estensioni non-breaking per il core v8.2
Mantiene 100% compatibilità numerica e API

PRINCIPI:
- Il core v8.2 resta INTATTO (stesso file, stesse formule)
- I plugin NON modificano il core, solo estendono
- Con plugins=[] ottieni esattamente v8.2
- Inversione di dipendenza: plugin importano core, mai viceversa
"""

import logging
import time
import json
from typing import Dict, List, Any, Optional, Protocol, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod
import copy

# Import del core v8.2 (invariato)
# from sam_core_v82 import analyze_sam, MaterialProperties, AnalysisConfig

logger = logging.getLogger(__name__)

# ===============================
# MODELLI DATI (Wrapper Non-Breaking)
# ===============================

@dataclass
class SAMModel:
    """
    Wrapper immutabile per input modello SAM
    Compatibile con analyze_sam(wall_data, material, loads, options)
    """
    wall_data: Dict[str, Any]
    material: Any  # MaterialProperties dal core
    loads: Dict[str, Any]
    options: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Serializzazione JSON-compatible"""
        return {
            'wall_data': self.wall_data,
            'material': asdict(self.material) if hasattr(self.material, '__dataclass_fields__') else self.material,
            'loads': self.loads,
            'options': self.options,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SAMModel':
        """Deserializzazione da JSON"""
        return cls(
            wall_data=data['wall_data'],
            material=data['material'],  # Ricostruire MaterialProperties se necessario
            loads=data['loads'],
            options=data.get('options'),
            metadata=data.get('metadata', {})
        )
    
    def clone(self) -> 'SAMModel':
        """Crea copia profonda per modifiche sicure"""
        return SAMModel(
            wall_data=copy.deepcopy(self.wall_data),
            material=copy.deepcopy(self.material),
            loads=copy.deepcopy(self.loads),
            options=copy.deepcopy(self.options),
            metadata=copy.deepcopy(self.metadata)
        )

@dataclass
class SAMResult:
    """
    Wrapper per risultati con metodi utility
    Mantiene schema v8.2 invariato
    """
    data: Dict[str, Any]
    plugin_data: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def verified(self) -> bool:
        return self.data.get('verified', False)
    
    @property
    def global_dcr(self) -> float:
        return self.data.get('global_DCR', 0.0)
    
    @property
    def critical_component(self) -> str:
        summary = self.data.get('summary', {})
        return summary.get('critical_component', 'none')
    
    def to_dict(self) -> Dict:
        """Serializzazione compatibile v8.2"""
        result = self.data.copy()
        if self.plugin_data:
            result['plugin_extensions'] = self.plugin_data
        if self.metrics:
            result['performance_metrics'] = self.metrics
        return result
    
    @classmethod
    def from_core_result(cls, core_result: Dict) -> 'SAMResult':
        """Wrap risultato dal core v8.2"""
        return cls(data=core_result)

# ===============================
# SISTEMA HOOK (Inversione Dipendenza)
# ===============================

class HookPhase(Enum):
    """Fasi di esecuzione per plugin - NON modifica il flusso core"""
    PRE_ANALYSIS = "pre_analysis"      # Prima di analyze_sam
    POST_COMPONENTS = "post_components" # Dopo identificazione componenti
    POST_LOADS = "post_loads"          # Dopo distribuzione carichi
    POST_CAPACITY = "post_capacity"    # Dopo calcolo capacità
    PRE_SUMMARY = "pre_summary"        # Prima del summary finale
    POST_ANALYSIS = "post_analysis"    # Dopo analyze_sam completo

@dataclass
class HookContext:
    """
    Contesto read-only passato ai plugin
    Contiene snapshot dei dati in ogni fase
    """
    phase: HookPhase
    model: SAMModel
    config: Any  # AnalysisConfig
    # Dati specifici per fase (read-only snapshots)
    components: Optional[Dict] = None
    load_distribution: Optional[Dict] = None
    capacities: Optional[Dict] = None
    results: Optional[Dict] = None
    
    def get_read_only_data(self) -> Dict:
        """Restituisce vista immutabile dei dati"""
        return {
            'phase': self.phase.value,
            'model': self.model.to_dict(),
            'components': copy.deepcopy(self.components),
            'load_distribution': copy.deepcopy(self.load_distribution),
            'capacities': copy.deepcopy(self.capacities),
            'results': copy.deepcopy(self.results)
        }

class PluginUpdate:
    """Aggiornamento proposto da un plugin"""
    def __init__(self, plugin_name: str, updates: Dict[str, Any]):
        self.plugin_name = plugin_name
        self.updates = updates
        self.timestamp = time.time()
    
    def is_safe(self) -> bool:
        """Verifica se l'update è sicuro (non rompe invarianti)"""
        # Solo modifiche a campi estensione sono sicure
        safe_keys = ['metadata', 'plugin_data', 'reinforcement_additions']
        return all(k in safe_keys for k in self.updates.keys())

# ===============================
# PROTOCOLLO PLUGIN
# ===============================

class SAMPlugin(Protocol):
    """Interfaccia che ogni plugin deve implementare"""
    name: str
    version: str
    priority: int  # 0-100, alta priorità eseguita prima
    
    def can_handle(self, phase: HookPhase, context: HookContext) -> bool:
        """Verifica se il plugin gestisce questa fase"""
        ...
    
    def process(self, context: HookContext) -> Optional[PluginUpdate]:
        """
        Processa il contesto e restituisce eventuali updates
        
        Returns:
            PluginUpdate con modifiche proposte o None
        """
        ...
    
    def validate_requirements(self) -> Tuple[bool, str]:
        """Verifica dipendenze e requisiti"""
        ...

# ===============================
# PLUGIN MANAGER
# ===============================

@dataclass
class PluginConfig:
    """Configurazione plugin con limiti risorse"""
    enabled_plugins: List[str] = field(default_factory=list)
    max_execution_time_ms: int = 1000  # Per plugin
    max_memory_mb: int = 100
    allow_model_updates: bool = False  # Di default read-only
    plugin_log_level: str = "INFO"
    telemetry_enabled: bool = True

class PluginManager:
    """
    Gestore centrale dei plugin
    - Registra e ordina plugin per priorità
    - Esegue hook nelle fasi appropriate
    - Applica updates in modo controllato
    - Monitora performance e risorse
    """
    
    def __init__(self, config: Optional[PluginConfig] = None):
        self.config = config or PluginConfig()
        self.plugins: List[SAMPlugin] = []
        self.metrics: Dict[str, Dict] = {}
        self._setup_logging()
    
    def _setup_logging(self):
        """Configura logger separato per plugin"""
        self.plugin_logger = logging.getLogger(f"{__name__}.plugins")
        self.plugin_logger.setLevel(self.config.plugin_log_level)
    
    def register(self, plugin: SAMPlugin) -> bool:
        """
        Registra un plugin se abilitato e valido
        
        Returns:
            True se registrato con successo
        """
        # Check se abilitato
        if plugin.name not in self.config.enabled_plugins:
            self.plugin_logger.debug(f"Plugin {plugin.name} non abilitato")
            return False
        
        # Valida requisiti
        valid, msg = plugin.validate_requirements()
        if not valid:
            self.plugin_logger.warning(f"Plugin {plugin.name} requisiti non soddisfatti: {msg}")
            return False
        
        self.plugins.append(plugin)
        self.plugins.sort(key=lambda p: p.priority, reverse=True)
        self.plugin_logger.info(f"Plugin {plugin.name} v{plugin.version} registrato (priority={plugin.priority})")
        return True
    
    def execute_phase(self, phase: HookPhase, context: HookContext) -> List[PluginUpdate]:
        """
        Esegue tutti i plugin per una fase
        
        Returns:
            Lista di updates proposti dai plugin
        """
        updates = []
        phase_start = time.time()
        
        for plugin in self.plugins:
            if not plugin.can_handle(phase, context):
                continue
            
            plugin_start = time.time()
            try:
                # Esegui con timeout
                update = self._execute_with_timeout(plugin, context)
                if update and update.is_safe():
                    updates.append(update)
                    self.plugin_logger.debug(f"{plugin.name} proposto update per {phase.value}")
                
                # Metriche
                exec_time = (time.time() - plugin_start) * 1000
                self._record_metric(plugin.name, phase, exec_time)
                
                if exec_time > self.config.max_execution_time_ms:
                    self.plugin_logger.warning(
                        f"{plugin.name} superato timeout: {exec_time:.1f}ms > {self.config.max_execution_time_ms}ms"
                    )
                    
            except Exception as e:
                self.plugin_logger.error(f"Errore in {plugin.name}: {e}")
                self._record_error(plugin.name, phase, str(e))
        
        phase_time = (time.time() - phase_start) * 1000
        self.plugin_logger.debug(f"Fase {phase.value} completata in {phase_time:.1f}ms con {len(updates)} updates")
        return updates
    
    def _execute_with_timeout(self, plugin: SAMPlugin, context: HookContext) -> Optional[PluginUpdate]:
        """Esegue plugin con timeout (simplified - in prod usare threading/asyncio)"""
        # Versione semplificata - in produzione usare concurrent.futures
        return plugin.process(context)
    
    def apply_updates(self, model: SAMModel, updates: List[PluginUpdate]) -> SAMModel:
        """
        Applica updates al modello in modo sicuro
        
        Returns:
            Nuovo modello con updates applicati (o originale se non permesso)
        """
        if not self.config.allow_model_updates:
            self.plugin_logger.debug("Updates non permessi da config")
            return model
        
        if not updates:
            return model
        
        # Clona per non modificare originale
        updated_model = model.clone()
        
        for update in updates:
            if update.is_safe():
                # Applica solo updates sicuri
                for key, value in update.updates.items():
                    if key == 'metadata':
                        updated_model.metadata.update(value)
                    elif key == 'reinforcement_additions':
                        # Esempio: aggiornamento rinforzi
                        self._apply_reinforcement_updates(updated_model, value)
                
                self.plugin_logger.debug(f"Applicato update da {update.plugin_name}")
        
        return updated_model
    
    def _apply_reinforcement_updates(self, model: SAMModel, reinforcements: Dict):
        """Applica modifiche rinforzi (es. cerchiature)"""
        # Esempio: modifica reinforcement_ratio delle fasce
        if 'spandrels' in model.wall_data:
            for i, spandrel_id in enumerate(reinforcements.get('spandrels', [])):
                if i < len(model.wall_data['spandrels']):
                    # Incrementa rinforzo
                    current = model.wall_data['spandrels'][i].get('reinforcement_ratio', 0.002)
                    model.wall_data['spandrels'][i]['reinforcement_ratio'] = current * 1.5
    
    def _record_metric(self, plugin_name: str, phase: HookPhase, exec_time_ms: float):
        """Registra metriche performance"""
        if plugin_name not in self.metrics:
            self.metrics[plugin_name] = {
                'executions': 0,
                'total_time_ms': 0,
                'by_phase': {}
            }
        
        self.metrics[plugin_name]['executions'] += 1
        self.metrics[plugin_name]['total_time_ms'] += exec_time_ms
        
        phase_key = phase.value
        if phase_key not in self.metrics[plugin_name]['by_phase']:
            self.metrics[plugin_name]['by_phase'][phase_key] = {
                'count': 0,
                'total_ms': 0,
                'avg_ms': 0
            }
        
        phase_metrics = self.metrics[plugin_name]['by_phase'][phase_key]
        phase_metrics['count'] += 1
        phase_metrics['total_ms'] += exec_time_ms
        phase_metrics['avg_ms'] = phase_metrics['total_ms'] / phase_metrics['count']
    
    def _record_error(self, plugin_name: str, phase: HookPhase, error: str):
        """Registra errori"""
        if plugin_name not in self.metrics:
            self.metrics[plugin_name] = {'errors': []}
        
        self.metrics[plugin_name].setdefault('errors', []).append({
            'phase': phase.value,
            'error': error,
            'timestamp': time.time()
        })
    
    def get_metrics_summary(self) -> Dict:
        """Riassunto metriche per telemetria"""
        summary = {
            'total_plugins': len(self.plugins),
            'enabled_plugins': [p.name for p in self.plugins],
            'plugin_metrics': self.metrics,
            'config': {
                'max_time_ms': self.config.max_execution_time_ms,
                'allow_updates': self.config.allow_model_updates
            }
        }
        return summary

# ===============================
# ANALIZZATORE ESTESO (Wrapper del Core)
# ===============================

class ExtendedSAMAnalyzer:
    """
    Wrapper che aggiunge plugin al core v8.2
    Mantiene 100% compatibilità: con plugins=[] è identico a v8.2
    """
    
    def __init__(self, plugin_manager: Optional[PluginManager] = None):
        self.plugin_manager = plugin_manager or PluginManager(
            PluginConfig(enabled_plugins=[])  # Default: nessun plugin
        )
        self.last_metrics = {}
    
    def analyze(self, model: SAMModel, config: Any = None) -> SAMResult:
        """
        Analisi SAM con supporto plugin
        
        Args:
            model: Modello SAM wrapped
            config: AnalysisConfig dal core
            
        Returns:
            SAMResult con eventuali estensioni plugin
        """
        start_time = time.time()
        
        # PRE_ANALYSIS hooks
        context = HookContext(
            phase=HookPhase.PRE_ANALYSIS,
            model=model,
            config=config
        )
        pre_updates = self.plugin_manager.execute_phase(HookPhase.PRE_ANALYSIS, context)
        
        # Applica eventuali pre-modifiche (es. preprocessori)
        if pre_updates:
            model = self.plugin_manager.apply_updates(model, pre_updates)
        
        # CORE ANALYSIS (v8.2 intatto)
        # Import dinamico per evitare dipendenza circolare
        from sam_core_v82 import analyze_sam
        
        core_result = analyze_sam(
            wall_data=model.wall_data,
            material=model.material,
            loads=model.loads,
            options=model.options
        )
        
        # Wrap risultato
        result = SAMResult.from_core_result(core_result)
        
        # POST_ANALYSIS hooks
        context = HookContext(
            phase=HookPhase.POST_ANALYSIS,
            model=model,
            config=config,
            results=core_result
        )
        post_updates = self.plugin_manager.execute_phase(HookPhase.POST_ANALYSIS, context)
        
        # Aggiungi dati plugin al risultato
        for update in post_updates:
            if 'plugin_data' in update.updates:
                result.plugin_data[update.plugin_name] = update.updates['plugin_data']
        
        # Metriche finali
        analysis_time = (time.time() - start_time) * 1000
        result.metrics = {
            'analysis_time_ms': analysis_time,
            'core_time_ms': analysis_time - sum(
                m.get('total_time_ms', 0) 
                for m in self.plugin_manager.metrics.values()
            ),
            'plugin_metrics': self.plugin_manager.get_metrics_summary()
        }
        
        self.last_metrics = result.metrics
        logger.info(f"Analisi completata in {analysis_time:.1f}ms")
        
        return result
    
    def analyze_legacy(self, wall_data: Dict, material: Any, 
                      loads: Dict, options: Dict = None) -> Dict:
        """
        API legacy per compatibilità v8.2
        
        Returns:
            Dict risultato standard v8.2
        """
        model = SAMModel(wall_data, material, loads, options)
        result = self.analyze(model)
        return result.to_dict()

# ===============================
# PLUGIN DI ESEMPIO
# ===============================

class ValidationPlugin:
    """Plugin esempio: validazione extra pre-analisi"""
    
    name = "validation_extra"
    version = "1.0.0"
    priority = 90  # Alta priorità, esegue prima
    
    def can_handle(self, phase: HookPhase, context: HookContext) -> bool:
        return phase == HookPhase.PRE_ANALYSIS
    
    def process(self, context: HookContext) -> Optional[PluginUpdate]:
        """Valida geometrie e materiali extra"""
        warnings = []
        
        # Check aspect ratio maschi
        for pier in context.model.wall_data.get('piers', []):
            aspect_ratio = pier['height'] / pier['length']
            if aspect_ratio > 5:
                warnings.append(f"Maschio snello: H/L = {aspect_ratio:.1f}")
        
        if warnings:
            return PluginUpdate(
                plugin_name=self.name,
                updates={
                    'metadata': {
                        'validation_warnings': warnings
                    }
                }
            )
        return None
    
    def validate_requirements(self) -> Tuple[bool, str]:
        return True, "OK"

class SeismicPlugin:
    """Plugin esempio: calcoli sismici aggiuntivi"""
    
    name = "seismic_advanced"
    version = "2.0.0"
    priority = 50
    
    def can_handle(self, phase: HookPhase, context: HookContext) -> bool:
        return phase == HookPhase.POST_ANALYSIS
    
    def process(self, context: HookContext) -> Optional[PluginUpdate]:
        """Aggiunge verifiche sismiche"""
        if not context.results:
            return None
        
        # Calcolo q-factor dinamico
        dcr = context.results.get('global_DCR', 1.0)
        q_factor = min(3.0, 1.0 / max(dcr, 0.33))
        
        seismic_data = {
            'q_factor': q_factor,
            'seismic_class': self._get_seismic_class(q_factor),
            'ductility_check': q_factor > 1.5
        }
        
        return PluginUpdate(
            plugin_name=self.name,
            updates={
                'plugin_data': seismic_data
            }
        )
    
    def _get_seismic_class(self, q_factor: float) -> str:
        if q_factor >= 2.5:
            return "High Ductility"
        elif q_factor >= 1.5:
            return "Medium Ductility"
        else:
            return "Low Ductility"
    
    def validate_requirements(self) -> Tuple[bool, str]:
        return True, "OK"

# ===============================
# SCHEMA I/O
# ===============================

class SAMSchemaV1:
    """
    Schema JSON v1 con retrocompatibilità
    """
    
    VERSION = "1.0"
    
    @staticmethod
    def validate(data: Dict) -> Tuple[bool, List[str]]:
        """Valida schema input/output"""
        errors = []
        
        # Check campi richiesti
        required_input = ['wall_data', 'material', 'loads']
        for field in required_input:
            if field not in data:
                errors.append(f"Campo richiesto mancante: {field}")
        
        # Valida struttura
        if 'wall_data' in data:
            if 'piers' in data['wall_data']:
                if not isinstance(data['wall_data']['piers'], list):
                    errors.append("'piers' deve essere una lista")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def migrate_from_legacy(old_data: Dict) -> Dict:
        """
        Migra da formati precedenti
        
        Mappings:
        - 'maschi' -> 'piers'
        - 'traversi' -> 'spandrels'
        """
        migrated = copy.deepcopy(old_data)
        
        if 'wall_data' in migrated:
            wd = migrated['wall_data']
            # Alias legacy
            if 'maschi' in wd and 'piers' not in wd:
                wd['piers'] = wd.pop('maschi')
            if 'traversi' in wd and 'spandrels' not in wd:
                wd['spandrels'] = wd.pop('traversi')
        
        return migrated
    
    @staticmethod
    def export(result: SAMResult, include_plugins: bool = True) -> str:
        """Esporta risultato in JSON"""
        data = result.to_dict()
        
        if not include_plugins:
            data.pop('plugin_extensions', None)
            data.pop('performance_metrics', None)
        
        # Aggiungi metadata schema
        data['_schema'] = {
            'version': SAMSchemaV1.VERSION,
            'timestamp': time.time()
        }
        
        return json.dumps(data, indent=2, default=str)

# ===============================
# ESEMPIO D'USO
# ===============================

def example_usage():
    """Esempio di utilizzo con e senza plugin"""
    
    # Setup
    from sam_core_v82 import MaterialProperties, AnalysisConfig
    
    # 1. MODALITÀ LEGACY (identica a v8.2)
    print("=== Modalità Legacy (v8.2 pura) ===")
    
    wall_data = {
        'piers': [
            {'length': 1.0, 'height': 3.0, 'thickness': 0.3},
            {'length': 1.2, 'height': 3.0, 'thickness': 0.3}
        ]
    }
    material = MaterialProperties(fk=2.4, fvk0=0.1)
    loads = {'moment': 100, 'shear': 50, 'vertical': -200}
    
    # Analisi diretta core
    from sam_core_v82 import analyze_sam
    result_legacy = analyze_sam(wall_data, material, loads)
    print(f"DCR Legacy: {result_legacy['global_DCR']:.3f}")
    
    # 2. MODALITÀ EXTENDED (con plugin)
    print("\n=== Modalità Extended (con plugin) ===")
    
    # Configura plugin
    plugin_config = PluginConfig(
        enabled_plugins=['validation_extra', 'seismic_advanced'],
        allow_model_updates=True
    )
    
    # Crea manager e registra plugin
    manager = PluginManager(plugin_config)
    manager.register(ValidationPlugin())
    manager.register(SeismicPlugin())
    
    # Analizzatore esteso
    analyzer = ExtendedSAMAnalyzer(manager)
    
    # Crea modello
    model = SAMModel(wall_data, material, loads)
    config = AnalysisConfig()
    
    # Analisi con plugin
    result_extended = analyzer.analyze(model, config)
    
    print(f"DCR Extended: {result_extended.global_dcr:.3f}")
    print(f"Plugin data: {result_extended.plugin_data}")
    print(f"Metrics: {result_extended.metrics}")
    
    # 3. VERIFICA IDENTITÀ NUMERICA
    print("\n=== Verifica Compatibilità ===")
    
    # Senza plugin deve dare stesso risultato
    analyzer_no_plugins = ExtendedSAMAnalyzer()  # Nessun plugin
    result_no_plugins = analyzer_no_plugins.analyze(model, config)
    
    assert abs(result_no_plugins.global_dcr - result_legacy['global_DCR']) < 1e-10
    print("✓ Risultati identici senza plugin")
    
    # 4. EXPORT JSON
    print("\n=== Export JSON ===")
    json_output = SAMSchemaV1.export(result_extended)
    print(json_output[:200] + "...")

if __name__ == "__main__":
    example_usage()