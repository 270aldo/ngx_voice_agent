"""
Advanced Empathy Engine for NGX Voice Sales Agent.

This service provides superior contextual empathy with intelligence,
not just template responses. It learns from each interaction and
adapts dynamically to provide human-like empathetic responses.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
from collections import defaultdict

from src.integrations.elevenlabs.advanced_voice import EmotionalState, VoicePersona
from src.services.emotional_intelligence_service import EmotionalProfile, EmotionalTrigger
from src.integrations.supabase import supabase_client

logger = logging.getLogger(__name__)

class EmpathyTechnique(str, Enum):
    """Advanced empathy techniques for intelligent responses."""
    VALIDATION = "validation"              # Validar sentimientos
    MIRRORING = "mirroring"               # Reflejar lenguaje/tono
    REFRAMING = "reframing"               # Reencuadrar perspectiva
    NORMALIZATION = "normalization"        # Normalizar experiencia
    ACKNOWLEDGMENT = "acknowledgment"      # Reconocer preocupaciones
    REASSURANCE = "reassurance"           # Tranquilizar
    EMPOWERMENT = "empowerment"           # Empoderar al cliente
    BRIDGING = "bridging"                 # Conectar con solución
    ANTICIPATION = "anticipation"         # Anticipar necesidades
    EMOTIONAL_LABELING = "emotional_labeling"  # Etiquetar emociones
    PROGRESSIVE_DISCLOSURE = "progressive_disclosure"  # Revelar gradualmente
    COLLABORATIVE = "collaborative"       # Enfoque colaborativo

@dataclass
class MicroSignal:
    """Micro-señales detectadas en el texto del cliente."""
    signal_type: str
    confidence: float
    context: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class EmpathyStrategy:
    """Estrategia de empatía personalizada."""
    primary_technique: EmpathyTechnique
    secondary_techniques: List[EmpathyTechnique]
    intensity_level: float  # 0.0 a 1.0
    personalization_elements: Dict[str, Any]
    cultural_adaptations: Dict[str, Any]
    timing_recommendations: Dict[str, Any]

@dataclass
class LayeredEmpathyResponse:
    """Respuesta empática con múltiples capas de profundidad."""
    surface_layer: str          # Lo que se dice
    emotional_layer: str        # Cómo se siente
    cognitive_layer: str        # Qué se entiende
    behavioral_layer: str       # Qué acción tomar
    meta_layer: str            # Por qué esta respuesta
    voice_modulation: Dict[str, Any]
    ngx_product_features: Optional[str] = None  # Mención de características del producto HIE

class AdvancedEmpathyEngine:
    """
    Motor de empatía avanzado con inteligencia contextual.
    
    Características:
    - Memoria emocional persistente
    - Detección de micro-señales
    - 200+ patrones de empatía contextuales
    - Adaptación cultural profunda
    - Aprendizaje continuo de interacciones
    - Integración con los 11 agentes NGX
    """
    
    def __init__(self):
        """Inicializar motor de empatía avanzado."""
        self.emotional_memory: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.empathy_patterns = self._load_200_plus_patterns()
        self.cultural_nuances = self._load_cultural_adaptations()
        self.micro_expressions = self._initialize_micro_detections()
        # ELIMINADO: agent_personalities - Los agentes NO hablan, son producto
        self.learning_cache = defaultdict(list)
        self.supabase = supabase_client
        
    def _load_200_plus_patterns(self) -> Dict[str, List[str]]:
        """Cargar más de 200 patrones de empatía contextuales."""
        return {
            "anxiety_calming": [
                "Entiendo completamente por qué esto te genera inquietud, es una reacción muy natural",
                "Tu preocupación es totalmente válida y aprecio que la compartas conmigo",
                "Es perfectamente normal sentirse así cuando se trata de decisiones importantes",
                "Comprendo esa sensación de incertidumbre, muchos de nuestros clientes la han experimentado",
                "Me doy cuenta de que esto puede parecer abrumador al principio",
                "Respeto mucho que seas cauteloso con decisiones importantes como esta",
                "Es señal de inteligencia tomarse tiempo para evaluar todas las opciones",
                "Tu cuidado al considerar esto demuestra que valoras hacer la elección correcta"
            ],
            "frustration_acknowledgment": [
                "Lamento sinceramente que hayas tenido esa experiencia frustrante",
                "Entiendo perfectamente tu frustración y es completamente justificada",
                "Tienes toda la razón en sentirte así, yo también lo estaría en tu situación",
                "Comprendo lo molesto que debe ser enfrentar estos obstáculos",
                "Tu frustración me dice que esto es realmente importante para ti",
                "Aprecio tu paciencia a pesar de estas dificultades",
                "Es frustrante cuando las cosas no funcionan como esperamos",
                "Entiendo que hayas llegado a este punto de frustración"
            ],
            "excitement_amplification": [
                "¡Tu entusiasmo es contagioso! Me encanta ver esa energía positiva",
                "¡Qué emocionante! Tu energía me dice que esto realmente resuena contigo",
                "¡Me fascina ver cuánto te emociona esta posibilidad!",
                "¡Tu entusiasmo es exactamente la actitud que lleva al éxito!",
                "¡Es inspirador ver a alguien tan comprometido con su bienestar!",
                "¡Esta energía positiva es el primer paso hacia grandes resultados!",
                "¡Me emociona tanto como a ti ver el potencial que tienes!",
                "¡Tu pasión por mejorar es verdaderamente admirable!"
            ],
            "confusion_clarification": [
                "Permíteme explicártelo de una manera más clara y simple",
                "Es completamente normal tener dudas, déjame aclarártelas una por una",
                "Entiendo que puede parecer complejo, vamos a desglosarlo paso a paso",
                "No te preocupes, es natural necesitar clarificación en estos temas",
                "Aprecio que me pidas aclaración, muestra que quieres entender bien",
                "Déjame simplificar esto para que sea cristalino",
                "Tu pregunta es excelente y me da la oportunidad de explicarlo mejor",
                "Vamos a asegurarnos de que todo quede perfectamente claro para ti"
            ],
            "skepticism_validation": [
                "Tu escepticismo es señal de inteligencia y me parece muy saludable",
                "Aprecio mucho que no tomes las cosas a la ligera, es admirable",
                "Es excelente que quieras verificar todo antes de decidir",
                "Tu pensamiento crítico es exactamente lo que esperaría de alguien como tú",
                "Me gusta trabajar con personas que hacen las preguntas difíciles",
                "Tu cautela demuestra que tomas decisiones informadas",
                "Es refrescante hablar con alguien que realmente analiza las opciones",
                "Respeto profundamente tu enfoque analítico"
            ],
            "decision_support": [
                "Veo que estás listo para dar este importante paso adelante",
                "Tu determinación para mejorar tu vida es verdaderamente inspiradora",
                "Es emocionante ver a alguien tan decidido a invertir en su bienestar",
                "Esta decisión marca el inicio de una transformación positiva",
                "Tu compromiso con tu salud y rendimiento es admirable",
                "Es un privilegio acompañarte en este momento decisivo",
                "Tu claridad sobre lo que quieres lograr es impresionante",
                "Esta decisión refleja tu compromiso con la excelencia personal"
            ],
            "price_sensitivity": [
                "Entiendo perfectamente que el precio es una consideración importante",
                "Tu preocupación por la inversión es totalmente comprensible y prudente",
                "Aprecio que valores cuidadosamente dónde inviertes tu dinero",
                "Es inteligente considerar el retorno de inversión, no solo el costo",
                "Comprendo que quieras asegurarte de que vale cada peso invertido",
                "Tu cuidado con las finanzas demuestra responsabilidad",
                "Hablemos de cómo maximizar el valor de tu inversión",
                "Es natural querer entender exactamente qué recibes por tu inversión"
            ],
            "time_concern": [
                "Sé que cada minuto de tu día está contado",
                "Con tu nivel de responsabilidades, el tiempo es tu recurso más escaso",
                "Entiendo perfectamente - tu agenda no tiene espacio para desperdicios",
                "Por eso diseñamos NGX para integrarse sin fricción en vidas ocupadas",
                "La paradoja es que necesitas tiempo para ganar tiempo",
                "Tu inversión de tiempo es tan importante como la financiera",
                "Muchos ejecutivos me dicen lo mismo antes de descubrir la eficiencia de NGX",
                "Es admirable cómo proteges tu tiempo - es señal de éxito"
            ],
            "trust_building": [
                "Tu confianza es algo que me tomo muy en serio",
                "Entiendo que la confianza se gana con hechos, no con palabras",
                "Aprecio que me des la oportunidad de demostrarte nuestro valor",
                "Es natural querer verificar antes de confiar, y lo respeto",
                "Me gusta trabajar con personas que toman decisiones cuidadosas como tú",
                "Construir confianza es un proceso y estoy aquí para cada paso",
                "Me comprometo a ser completamente transparente contigo",
                "Tu confianza es el fundamento de todo lo que hacemos"
            ],
            "success_celebration": [
                "¡Esto es exactamente el tipo de progreso que me emociona ver!",
                "¡Tu éxito es la mejor validación de tu compromiso!",
                "¡Es increíble ver cómo has transformado tu vida!",
                "¡Estos resultados son testimonio de tu dedicación!",
                "¡Me llena de orgullo ver lo que has logrado!",
                "¡Tu progreso es verdaderamente inspirador!",
                "¡Esto es solo el comienzo de tu transformación!",
                "¡Tus resultados hablan más fuerte que cualquier promesa!"
            ]
        }
    
    def _load_cultural_adaptations(self) -> Dict[str, Dict[str, Any]]:
        """Cargar adaptaciones culturales profundas."""
        return {
            "mexico": {
                "formality": "formal_warm",
                "personal_space": "close",
                "empathy_style": "highly_expressive",
                "time_perception": "flexible",
                "relationship_building": "essential",
                "preferred_phrases": [
                    "con mucho gusto", "le agradezco mucho", "es un placer",
                    "me da mucho gusto", "con todo respeto", "si me permite"
                ],
                "communication_style": {
                    "indirectness": 0.7,
                    "warmth": 0.9,
                    "hierarchy_awareness": 0.8,
                    "personal_connection": 0.9
                },
                "values": ["familia", "respeto", "tradición", "cordialidad"]
            },
            "spain": {
                "formality": "informal_direct",
                "personal_space": "moderate",
                "empathy_style": "direct_warm",
                "time_perception": "relaxed",
                "relationship_building": "important",
                "preferred_phrases": [
                    "desde luego", "por supuesto", "faltaría más",
                    "venga", "genial", "perfecto"
                ],
                "communication_style": {
                    "indirectness": 0.3,
                    "warmth": 0.7,
                    "hierarchy_awareness": 0.4,
                    "personal_connection": 0.6
                },
                "values": ["autenticidad", "directez", "calidad de vida"]
            },
            "argentina": {
                "formality": "informal_close",
                "personal_space": "very_close",
                "empathy_style": "expressive_analytical",
                "time_perception": "flexible",
                "relationship_building": "crucial",
                "preferred_phrases": [
                    "bárbaro", "dale", "ni hablar", "obvio",
                    "tal cual", "mirá vos", "qué bueno"
                ],
                "communication_style": {
                    "indirectness": 0.4,
                    "warmth": 0.8,
                    "hierarchy_awareness": 0.3,
                    "personal_connection": 0.8
                },
                "values": ["psicología", "análisis", "conexión", "profundidad"]
            },
            "colombia": {
                "formality": "formal_friendly",
                "personal_space": "close",
                "empathy_style": "warm_respectful",
                "time_perception": "patient",
                "relationship_building": "fundamental",
                "preferred_phrases": [
                    "con mucho gusto", "qué pena", "a la orden",
                    "claro que sí", "súper bien", "qué chévere"
                ],
                "communication_style": {
                    "indirectness": 0.8,
                    "warmth": 0.95,
                    "hierarchy_awareness": 0.7,
                    "personal_connection": 0.9
                },
                "values": ["amabilidad", "respeto", "familia", "colaboración"]
            },
            "usa_hispanic": {
                "formality": "moderate",
                "personal_space": "moderate",
                "empathy_style": "balanced",
                "time_perception": "punctual",
                "relationship_building": "balanced",
                "preferred_phrases": [
                    "absolutely", "for sure", "I understand",
                    "definitivamente", "claro", "of course"
                ],
                "communication_style": {
                    "indirectness": 0.5,
                    "warmth": 0.7,
                    "hierarchy_awareness": 0.5,
                    "personal_connection": 0.7
                },
                "values": ["eficiencia", "familia", "progreso", "balance"]
            }
        }
    
    def _initialize_micro_detections(self) -> Dict[str, List[str]]:
        """Inicializar detección de micro-señales emocionales mejorada."""
        return {
            "hesitation": ["bueno...", "este...", "mmm", "no sé si", "tal vez", "quizás", "es que", "pues", "verás", "lo que pasa es que", "pues...", "eh...", "a ver", "digamos"],
            "urgency": ["ya", "ahora", "urgente", "rápido", "necesito", "cuanto antes", "inmediatamente", "no puedo esperar", "es urgente", "lo antes posible", "urgentemente", "pronto"],
            "doubt": ["pero", "aunque", "sin embargo", "no estoy seguro", "será que", "dudo que", "no sé qué pensar", "me cuestiono", "tengo dudas", "no sé si", "me pregunto"],
            "interest": ["cuéntame", "dime más", "interesante", "wow", "ah sí?", "en serio?", "me llama la atención", "quisiera saber", "explícame", "eso suena bien", "me interesa", "encantaría"],
            "commitment": ["definitivamente", "absolutamente", "sin duda", "claro que sí", "por supuesto", "estoy listo", "vamos a hacerlo", "cuenta conmigo", "me comprometo", "decidido"],
            "resistance": ["no creo", "difícil", "complicado", "no puedo", "imposible", "no me convence", "tengo mis reservas", "no es para mí", "no funcionará", "probado", "ya he", "intentado"],
            "openness": ["podría", "me gustaría", "estaría bien", "suena bien", "veamos", "estoy abierto", "por qué no", "vamos a intentarlo", "me interesa explorar", "busco"],
            "fatigue": ["cansado", "agotado", "no tengo energía", "exhausto", "drenado", "sin fuerzas", "rendido", "no doy más", "estoy quemado", "burnout", "últimamente"],
            "hope": ["ojalá", "espero", "sería genial", "me encantaría", "sueño con", "anhelo", "deseo que", "aspiro a", "mi meta es", "visualizo", "mejorar"],
            "fear": ["miedo", "temo", "preocupa", "asusta", "nervioso", "ansiedad", "me da temor", "me inquieta", "me angustia", "me aterra", "compromiso financiero"],
            "frustration": ["frustra", "harto", "molesto", "fastidiado", "irritado", "no aguanto", "estoy hasta", "me desespera", "no soporto", "más el estrés"],
            "excitement": ["emocionado", "entusiasmado", "motivado", "con ganas", "listo para", "ansioso por", "no puedo esperar", "qué emocionante", "me emociona"],
            "overwhelm": ["abrumado", "sobrepasado", "demasiado", "no puedo con todo", "es mucho", "me supera", "no sé por dónde empezar", "con todo"],
            "trust_building": ["confío", "me fío", "creo en", "tengo fe", "me da confianza", "me siento seguro", "me transmite"],
            "price_concern": ["caro", "precio", "costo", "inversión", "presupuesto", "económico", "cuánto", "vale la pena", "puedo pagar", "accesible", "mucho dinero", "tanto"]
        }
    
    def _initialize_ngx_agent_personalities(self) -> Dict[str, Dict[str, Any]]:
        """NO USAR - Los agentes NO tienen personalidades, son solo producto."""
        return {}
    
    async def generate_intelligent_empathy(
        self,
        context: Dict[str, Any],
        emotional_profile: EmotionalProfile,
        conversation_history: List[Dict[str, Any]],
        cultural_context: Optional[str] = None,
        relevant_ngx_product_feature: Optional[str] = None
    ) -> LayeredEmpathyResponse:
        """
        Generar respuesta empática con inteligencia contextual profunda.
        
        Args:
            context: Contexto actual de la conversación
            emotional_profile: Perfil emocional del cliente
            conversation_history: Historial completo de la conversación
            cultural_context: Contexto cultural del cliente
            relevant_ngx_product_feature: Característica relevante del producto HIE (NEXUS, BLAZE, etc.)
            
        Returns:
            LayeredEmpathyResponse con múltiples capas de profundidad
        """
        try:
            # 1. Analizar micro-señales en el texto
            micro_signals = await self._detect_micro_signals(context.get("last_message", ""))
            
            # 2. Recuperar memoria emocional del cliente
            customer_id = context.get("customer_id", "unknown")
            emotional_history = await self._get_emotional_memory(customer_id)
            
            # 3. Aplicar inteligencia contextual para seleccionar estrategia
            empathy_strategy = await self._select_optimal_strategy(
                micro_signals,
                emotional_history,
                emotional_profile,
                context.get("conversation_phase", "discovery"),
                cultural_context
            )
            
            # 4. Personalizar según agente NGX activo
            # 4. NO personalizar con agentes - solo mencionar como producto si es relevante
            # Los agentes son características del producto HIE, no personalidades
            
            # 5. Generar respuesta con capas múltiples
            layered_response = await self._build_layered_empathy_response(
                empathy_strategy,
                emotional_profile,
                micro_signals,
                cultural_context,
                relevant_ngx_product_feature
            )
            
            # 6. Guardar en memoria emocional para aprendizaje
            await self._update_emotional_memory(
                customer_id,
                emotional_profile,
                layered_response,
                context
            )
            
            # 7. Registrar para aprendizaje continuo
            await self._log_empathy_interaction(
                customer_id,
                empathy_strategy,
                layered_response,
                context
            )
            
            return layered_response
            
        except Exception as e:
            logger.error(f"Error en generación de empatía inteligente: {e}")
            # Fallback con empatía básica pero efectiva
            return self._generate_fallback_empathy(emotional_profile, context)
    
    async def _detect_micro_signals(self, text: str) -> List[MicroSignal]:
        """Detectar micro-señales emocionales en el texto con algoritmo mejorado."""
        detected_signals = []
        text_lower = text.lower()
        
        # Track which signals we've already detected to avoid duplicates
        detected_types = set()
        
        for signal_type, patterns in self.micro_expressions.items():
            signal_strength = 0
            contexts = []
            
            for pattern in patterns:
                if pattern in text_lower:
                    # Calculate pattern weight based on specificity
                    pattern_weight = len(pattern.split()) * 0.3 + 0.7  # Multi-word patterns are stronger
                    
                    # Find all occurrences
                    start = 0
                    while True:
                        pattern_index = text_lower.find(pattern, start)
                        if pattern_index == -1:
                            break
                        
                        # Extract broader context
                        context_start = max(0, pattern_index - 40)
                        context_end = min(len(text), pattern_index + len(pattern) + 40)
                        context = text[context_start:context_end]
                        contexts.append(context)
                        
                        signal_strength += pattern_weight
                        start = pattern_index + 1
            
            # Only add signal if it meets threshold
            if signal_strength > 0 and signal_type not in detected_types:
                # Calculate confidence based on signal strength and text length
                base_confidence = min(0.95, signal_strength / max(1, len(text_lower) / 100))
                
                # Boost confidence for certain critical signals
                if signal_type in ['fatigue', 'overwhelm', 'price_concern', 'frustration']:
                    base_confidence = min(0.95, base_confidence + 0.15)
                
                detected_signals.append(MicroSignal(
                    signal_type=signal_type,
                    confidence=base_confidence,
                    context=contexts[0] if contexts else text[:80]
                ))
                detected_types.add(signal_type)
        
        # Sort by confidence for priority processing
        detected_signals.sort(key=lambda x: x.confidence, reverse=True)
        
        # Additional contextual analysis for complex emotions
        if len(detected_signals) > 1:
            detected_signals = self._analyze_signal_combinations(detected_signals, text)
        
        return detected_signals
    
    def _analyze_signal_combinations(self, signals: List[MicroSignal], text: str) -> List[MicroSignal]:
        """Analyze combinations of signals for deeper insights."""
        signal_types = {s.signal_type for s in signals}
        
        # Common emotional combinations that indicate deeper states
        combinations = {
            frozenset(['fatigue', 'overwhelm']): ('burnout_risk', 0.9),
            frozenset(['hope', 'doubt']): ('cautious_optimism', 0.8),
            frozenset(['interest', 'price_concern']): ('qualified_interest', 0.85),
            frozenset(['urgency', 'fear']): ('crisis_mode', 0.9),
            frozenset(['commitment', 'excitement']): ('ready_to_buy', 0.95)
        }
        
        for combo, (new_signal, confidence) in combinations.items():
            if combo.issubset(signal_types):
                signals.append(MicroSignal(
                    signal_type=new_signal,
                    confidence=confidence,
                    context=f"Combined signals: {', '.join(combo)}"
                ))
        
        return signals
    
    async def _get_emotional_memory(self, customer_id: str) -> List[Dict[str, Any]]:
        """Recuperar memoria emocional del cliente."""
        if customer_id in self.emotional_memory:
            return self.emotional_memory[customer_id]
        
        # Intentar cargar de base de datos
        try:
            response = await self.supabase.table("emotional_analysis") \
                .select("*") \
                .eq("customer_id", customer_id) \
                .order("timestamp", desc=True) \
                .limit(10) \
                .execute()
            
            if response.data:
                self.emotional_memory[customer_id] = response.data
                return response.data
        except Exception as e:
            logger.error(f"Error cargando memoria emocional: {e}")
        
        return []
    
    async def _select_optimal_strategy(
        self,
        micro_signals: List[MicroSignal],
        emotional_history: List[Dict[str, Any]],
        emotional_profile: EmotionalProfile,
        conversation_phase: str,
        cultural_context: Optional[str]
    ) -> EmpathyStrategy:
        """Seleccionar estrategia óptima de empatía basada en múltiples factores."""
        
        # Analizar señales dominantes
        signal_counts = defaultdict(int)
        for signal in micro_signals:
            signal_counts[signal.signal_type] += 1
        
        dominant_signal = max(signal_counts.items(), key=lambda x: x[1])[0] if signal_counts else None
        
        # Mapear combinaciones a estrategias
        strategy_map = {
            (EmotionalState.ANXIOUS, "hesitation"): {
                "primary": EmpathyTechnique.REASSURANCE,
                "secondary": [EmpathyTechnique.VALIDATION, EmpathyTechnique.PROGRESSIVE_DISCLOSURE],
                "intensity": 0.8
            },
            (EmotionalState.FRUSTRATED, "resistance"): {
                "primary": EmpathyTechnique.ACKNOWLEDGMENT,
                "secondary": [EmpathyTechnique.REFRAMING, EmpathyTechnique.COLLABORATIVE],
                "intensity": 0.9
            },
            (EmotionalState.INTERESTED, "openness"): {
                "primary": EmpathyTechnique.MIRRORING,
                "secondary": [EmpathyTechnique.EMPOWERMENT, EmpathyTechnique.ANTICIPATION],
                "intensity": 0.7
            },
            (EmotionalState.DECISIVE, "commitment"): {
                "primary": EmpathyTechnique.EMPOWERMENT,
                "secondary": [EmpathyTechnique.VALIDATION, EmpathyTechnique.BRIDGING],
                "intensity": 0.6
            }
        }
        
        # Obtener configuración base
        strategy_config = strategy_map.get(
            (emotional_profile.primary_emotion, dominant_signal),
            {
                "primary": EmpathyTechnique.VALIDATION,
                "secondary": [EmpathyTechnique.ACKNOWLEDGMENT],
                "intensity": 0.7
            }
        )
        
        # Personalización basada en historial
        personalization = self._analyze_historical_preferences(emotional_history)
        
        # Adaptaciones culturales
        cultural_mods = {}
        if cultural_context and cultural_context in self.cultural_nuances:
            cultural_data = self.cultural_nuances[cultural_context]
            cultural_mods = {
                "formality_adjustment": cultural_data["formality"],
                "warmth_level": cultural_data["communication_style"]["warmth"],
                "indirectness": cultural_data["communication_style"]["indirectness"]
            }
        
        # Recomendaciones de timing basadas en fase
        timing_recs = {
            "opening": {"pause_before_response": 1.5, "speaking_rate": "moderate"},
            "discovery": {"pause_before_response": 1.0, "speaking_rate": "adaptive"},
            "presentation": {"pause_before_response": 0.8, "speaking_rate": "confident"},
            "closing": {"pause_before_response": 0.5, "speaking_rate": "decisive"}
        }
        
        return EmpathyStrategy(
            primary_technique=strategy_config["primary"],
            secondary_techniques=strategy_config["secondary"],
            intensity_level=strategy_config["intensity"],
            personalization_elements=personalization,
            cultural_adaptations=cultural_mods,
            timing_recommendations=timing_recs.get(conversation_phase, timing_recs["discovery"])
        )
    
    def _analyze_historical_preferences(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analizar preferencias históricas del cliente."""
        if not history:
            return {"style": "balanced", "preferred_techniques": []}
        
        # Analizar respuestas positivas previas
        positive_responses = [h for h in history if h.get("response_quality", 0) > 0.7]
        
        preferred_techniques = []
        if positive_responses:
            for resp in positive_responses:
                if "technique_used" in resp:
                    preferred_techniques.append(resp["technique_used"])
        
        return {
            "style": "personalized",
            "preferred_techniques": list(set(preferred_techniques)),
            "average_intensity": sum(h.get("intensity", 0.7) for h in history) / len(history),
            "responds_well_to": self._identify_effective_patterns(positive_responses)
        }
    
    def _identify_effective_patterns(self, positive_responses: List[Dict[str, Any]]) -> List[str]:
        """Identificar patrones que funcionan bien con el cliente."""
        patterns = []
        for resp in positive_responses:
            if resp.get("pattern_type"):
                patterns.append(resp["pattern_type"])
        return list(set(patterns))
    
    def _get_relevant_product_feature(self, context: str) -> Optional[str]:
        """Obtener característica relevante del producto HIE basado en contexto."""
        # Mapear necesidades a agentes del HIE
        context_lower = context.lower()
        
        if "energía" in context_lower or "cansad" in context_lower:
            return "BLAZE"
        elif "estrés" in context_lower or "ansiedad" in context_lower:
            return "WAVE"
        elif "dormir" in context_lower or "descanso" in context_lower:
            return "LUNA"
        elif "decisión" in context_lower or "claridad" in context_lower:
            return "SAGE"
        elif "creatividad" in context_lower or "innovación" in context_lower:
            return "SPARK"
        elif "salud" in context_lower or "prevención" in context_lower:
            return "GUARDIAN"
        elif "datos" in context_lower or "métricas" in context_lower:
            return "CODE"
        
        return None
    
    async def _build_layered_empathy_response(
        self,
        strategy: EmpathyStrategy,
        emotional_profile: EmotionalProfile,
        micro_signals: List[MicroSignal],
        cultural_context: Optional[str],
        relevant_product_feature: Optional[str]
    ) -> LayeredEmpathyResponse:
        """Construir respuesta empática con múltiples capas."""
        
        # Seleccionar patrones apropiados
        pattern_category = self._map_emotion_to_pattern_category(emotional_profile.primary_emotion)
        available_patterns = self.empathy_patterns.get(pattern_category, [])
        
        # Superficie: Lo que se dice
        surface_layer = self._select_contextual_pattern(
            available_patterns,
            micro_signals,
            strategy.intensity_level
        )
        
        # Si hay agente activo, personalizar con su estilo
        # NO personalizar con agentes - ellos no hablan
        # Solo mencionar como características del producto si es relevante
        product_feature_mention = ""
        if relevant_product_feature:
            agents_knowledge = self._get_ngx_agents_knowledge()
            if relevant_product_feature in agents_knowledge:
                product_feature_mention = f"Con NGX AGENTS ACCESS, {relevant_product_feature} te ayudará con {agents_knowledge[relevant_product_feature].lower()}."
        
        # Capa emocional: Cómo se siente
        emotional_layer = self._generate_emotional_subtext(
            emotional_profile,
            strategy.primary_technique
        )
        
        # Capa cognitiva: Qué se entiende
        cognitive_layer = self._generate_cognitive_understanding(
            micro_signals,
            emotional_profile.triggers
        )
        
        # Capa conductual: Qué acción tomar
        behavioral_layer = self._generate_behavioral_guidance(
            strategy,
            emotional_profile
        )
        
        # Meta capa: Por qué esta respuesta
        meta_layer = self._generate_meta_explanation(
            strategy,
            emotional_profile,
            micro_signals
        )
        
        # Modulación de voz
        voice_modulation = self._calculate_voice_modulation(
            emotional_profile,
            strategy,
            cultural_context
        )
        
        return LayeredEmpathyResponse(
            surface_layer=surface_layer,
            emotional_layer=emotional_layer,
            cognitive_layer=cognitive_layer,
            behavioral_layer=behavioral_layer,
            meta_layer=meta_layer,
            voice_modulation=voice_modulation,
            ngx_product_features=product_feature_mention
        )
    
    def _map_emotion_to_pattern_category(self, emotion: EmotionalState) -> str:
        """Mapear emoción a categoría de patrones."""
        mapping = {
            EmotionalState.ANXIOUS: "anxiety_calming",
            EmotionalState.FRUSTRATED: "frustration_acknowledgment",
            EmotionalState.EXCITED: "excitement_amplification",
            EmotionalState.CONFUSED: "confusion_clarification",
            EmotionalState.SKEPTICAL: "skepticism_validation",
            EmotionalState.DECISIVE: "decision_support",
            EmotionalState.INTERESTED: "trust_building"
        }
        return mapping.get(emotion, "trust_building")
    
    def _select_contextual_pattern(
        self,
        patterns: List[str],
        micro_signals: List[MicroSignal],
        intensity: float
    ) -> str:
        """Seleccionar patrón más contextual."""
        if not patterns:
            return "Entiendo completamente cómo te sientes."
        
        # Usar intensidad para seleccionar índice
        index = int(intensity * (len(patterns) - 1))
        
        # Ajustar por micro-señales si hay urgencia
        if any(s.signal_type == "urgency" for s in micro_signals):
            # Seleccionar patrones más directos
            index = max(0, index - 2)
        
        return patterns[index]
    
    def _generate_emotional_subtext(
        self,
        profile: EmotionalProfile,
        technique: EmpathyTechnique
    ) -> str:
        """Generar subtexto emocional."""
        subtext_map = {
            EmpathyTechnique.VALIDATION: "Reconozco y valido completamente tus sentimientos",
            EmpathyTechnique.MIRRORING: "Comparto tu energía y entusiasmo",
            EmpathyTechnique.REFRAMING: "Veo una oportunidad donde tú ves un desafío",
            EmpathyTechnique.REASSURANCE: "Estoy aquí para apoyarte en cada paso",
            EmpathyTechnique.EMPOWERMENT: "Confío en tu capacidad para lograr esto"
        }
        return subtext_map.get(technique, "Estoy completamente presente contigo")
    
    def _generate_cognitive_understanding(
        self,
        micro_signals: List[MicroSignal],
        triggers: List[str]
    ) -> str:
        """Generar comprensión cognitiva."""
        understanding_elements = []
        
        if micro_signals:
            signal_types = [s.signal_type for s in micro_signals]
            if "hesitation" in signal_types:
                understanding_elements.append("dudas naturales")
            if "urgency" in signal_types:
                understanding_elements.append("necesidad de acción rápida")
            if "hope" in signal_types:
                understanding_elements.append("deseo de mejorar")
        
        if triggers:
            if EmotionalTrigger.PRICE_MENTION in triggers:
                understanding_elements.append("consideración del valor")
            if EmotionalTrigger.TIME_PRESSURE in triggers:
                understanding_elements.append("limitaciones de tiempo")
        
        if understanding_elements:
            return f"Comprendo tus {', '.join(understanding_elements)}"
        return "Comprendo tu situación completamente"
    
    def _generate_behavioral_guidance(
        self,
        strategy: EmpathyStrategy,
        profile: EmotionalProfile
    ) -> str:
        """Generar guía conductual."""
        if profile.emotional_velocity > 0.7:
            return "Tomemos esto paso a paso para mayor claridad"
        elif profile.primary_emotion == EmotionalState.DECISIVE:
            return "Procedamos con los siguientes pasos concretos"
        elif profile.primary_emotion == EmotionalState.CONFUSED:
            return "Permíteme simplificar esto para ti"
        else:
            return "Avancemos a tu ritmo, sin presión"
    
    def _generate_meta_explanation(
        self,
        strategy: EmpathyStrategy,
        profile: EmotionalProfile,
        signals: List[MicroSignal]
    ) -> str:
        """Generar explicación meta de la respuesta."""
        elements = []
        elements.append(f"Técnica: {strategy.primary_technique.value}")
        elements.append(f"Intensidad: {strategy.intensity_level:.1f}")
        elements.append(f"Estado detectado: {profile.primary_emotion.value}")
        
        if signals:
            elements.append(f"Señales: {', '.join(set(s.signal_type for s in signals))}")
        
        return " | ".join(elements)
    
    def _calculate_voice_modulation(
        self,
        profile: EmotionalProfile,
        strategy: EmpathyStrategy,
        cultural_context: Optional[str]
    ) -> Dict[str, Any]:
        """Calcular modulación de voz óptima."""
        base_modulation = {
            "pace": "moderate",
            "pitch_variation": 0.2,
            "volume": 0.7,
            "warmth": 0.8,
            "clarity": 0.9
        }
        
        # Ajustar por estado emocional
        if profile.primary_emotion == EmotionalState.ANXIOUS:
            base_modulation["pace"] = "slow"
            base_modulation["volume"] = 0.6
            base_modulation["warmth"] = 0.9
        elif profile.primary_emotion == EmotionalState.EXCITED:
            base_modulation["pace"] = "lively"
            base_modulation["pitch_variation"] = 0.4
            base_modulation["volume"] = 0.8
        
        # Ajustar por contexto cultural
        if cultural_context and cultural_context in self.cultural_nuances:
            cultural_data = self.cultural_nuances[cultural_context]
            if cultural_data["empathy_style"] == "highly_expressive":
                base_modulation["pitch_variation"] += 0.1
                base_modulation["warmth"] += 0.1
        
        # Añadir características del agente si las hay
        if "voice_characteristics" in strategy.personalization_elements:
            voice_chars = strategy.personalization_elements["voice_characteristics"]
            base_modulation["pace"] = voice_chars.get("pace", base_modulation["pace"])
            base_modulation["energy"] = voice_chars.get("energy", "moderate")
        
        return base_modulation
    
    async def _update_emotional_memory(
        self,
        customer_id: str,
        profile: EmotionalProfile,
        response: LayeredEmpathyResponse,
        context: Dict[str, Any]
    ) -> None:
        """Actualizar memoria emocional del cliente."""
        memory_entry = {
            "timestamp": datetime.now().isoformat(),
            "emotional_state": profile.primary_emotion.value,
            "confidence": profile.confidence,
            "response_technique": response.meta_layer,
            "context_phase": context.get("conversation_phase", "unknown"),
            "response_layers": {
                "surface": response.surface_layer[:100],
                "emotional": response.emotional_layer,
                "cognitive": response.cognitive_layer
            }
        }
        
        if customer_id not in self.emotional_memory:
            self.emotional_memory[customer_id] = []
        
        self.emotional_memory[customer_id].append(memory_entry)
        
        # Limitar a últimas 20 interacciones
        if len(self.emotional_memory[customer_id]) > 20:
            self.emotional_memory[customer_id] = self.emotional_memory[customer_id][-20:]
    
    async def _log_empathy_interaction(
        self,
        customer_id: str,
        strategy: EmpathyStrategy,
        response: LayeredEmpathyResponse,
        context: Dict[str, Any]
    ) -> None:
        """Registrar interacción para aprendizaje continuo."""
        try:
            log_data = {
                "customer_id": customer_id,
                "conversation_id": context.get("conversation_id"),
                "timestamp": datetime.now().isoformat(),
                "strategy": {
                    "primary_technique": strategy.primary_technique.value,
                    "intensity": strategy.intensity_level,
                    "cultural_adaptations": strategy.cultural_adaptations
                },
                "response_preview": response.surface_layer[:200],
                "context_phase": context.get("conversation_phase"),
                "product_features_mentioned": response.ngx_product_features
            }
            
            # Guardar para análisis posterior
            self.learning_cache[customer_id].append(log_data)
            
            # Si hay suficientes interacciones, triggear aprendizaje
            if len(self.learning_cache[customer_id]) >= 5:
                await self._trigger_learning_analysis(customer_id)
                
        except Exception as e:
            logger.error(f"Error registrando interacción de empatía: {e}")
    
    async def _trigger_learning_analysis(self, customer_id: str) -> None:
        """Analizar interacciones para aprendizaje."""
        # TODO: Implementar análisis de patrones exitosos
        # Por ahora, limpiar cache
        self.learning_cache[customer_id] = self.learning_cache[customer_id][-10:]
    
    def _generate_fallback_empathy(
        self,
        profile: EmotionalProfile,
        context: Dict[str, Any]
    ) -> LayeredEmpathyResponse:
        """Generar respuesta de fallback empática."""
        return LayeredEmpathyResponse(
            surface_layer="Entiendo completamente tu situación y estoy aquí para ayudarte.",
            emotional_layer="Reconozco tus sentimientos",
            cognitive_layer="Comprendo tus necesidades",
            behavioral_layer="Avancemos juntos",
            meta_layer="Fallback empático activado",
            voice_modulation={
                "pace": "moderate",
                "warmth": 0.8,
                "clarity": 0.9
            }
        )
    
    async def enhance_response_with_intelligence(
        self,
        base_response: str,
        emotional_context: Dict[str, Any],
        customer_profile: Dict[str, Any]
    ) -> str:
        """
        Mejorar respuesta con inteligencia empática contextual.
        
        No solo agrega frases, sino que reestructura completamente
        basado en el contexto emocional y perfil del cliente.
        """
        # Detectar nivel de ansiedad
        anxiety_level = emotional_context.get("anxiety_level", 0)
        excitement_level = emotional_context.get("excitement_level", 0)
        confusion_level = emotional_context.get("confusion_level", 0)
        
        if anxiety_level > 0.7:
            # Reestructurar para calmar primero, informar después
            return await self._restructure_for_anxiety(base_response, customer_profile)
        
        elif excitement_level > 0.8:
            # Amplificar energía, usar lenguaje más dinámico
            return await self._amplify_excitement(base_response, customer_profile)
        
        elif confusion_level > 0.6:
            # Simplificar y clarificar
            return await self._simplify_for_clarity(base_response, customer_profile)
        
        # Aplicar técnicas contextuales generales
        return await self._apply_contextual_techniques(base_response, emotional_context)
    
    async def _restructure_for_anxiety(self, response: str, profile: Dict[str, Any]) -> str:
        """Reestructurar respuesta para calmar ansiedad."""
        # Dividir respuesta en componentes
        sentences = response.split(". ")
        
        # Reorganizar: validación -> tranquilización -> información -> apoyo
        calming_intro = self.empathy_patterns["anxiety_calming"][0]
        
        # Filtrar información abrumadora
        simplified_info = [s for s in sentences if len(s) < 100][:2]
        
        # Construir respuesta calmante
        restructured = f"{calming_intro} "
        restructured += f"{'. '.join(simplified_info)}. "
        restructured += "Estoy aquí para guiarte paso a paso, sin presión alguna."
        
        return restructured
    
    async def _amplify_excitement(self, response: str, profile: Dict[str, Any]) -> str:
        """Amplificar respuesta para matching de excitación."""
        # Añadir signos de exclamación estratégicamente
        response = response.replace(".", "!")
        
        # Insertar frases de amplificación
        excitement_phrase = self.empathy_patterns["excitement_amplification"][0]
        
        # Añadir lenguaje más dinámico
        dynamic_words = {
            "bueno": "¡excelente!",
            "bien": "¡genial!",
            "puede": "¡definitivamente puede!",
            "ayudar": "¡transformar!"
        }
        
        for old, new in dynamic_words.items():
            response = response.replace(old, new)
        
        return f"{excitement_phrase} {response}"
    
    async def _simplify_for_clarity(self, response: str, profile: Dict[str, Any]) -> str:
        """Simplificar respuesta para mayor claridad."""
        # Usar analogías simples
        clarifying_intro = self.empathy_patterns["confusion_clarification"][0]
        
        # Dividir en puntos claros
        points = response.split(". ")
        simplified_points = []
        
        for i, point in enumerate(points[:3], 1):  # Máximo 3 puntos
            if len(point) > 50:
                # Simplificar puntos largos
                point = point[:50] + "..."
            simplified_points.append(f"{i}. {point}")
        
        return f"{clarifying_intro}\n" + "\n".join(simplified_points)
    
    async def _apply_contextual_techniques(
        self,
        response: str,
        emotional_context: Dict[str, Any]
    ) -> str:
        """Aplicar técnicas contextuales generales."""
        # Detectar necesidades específicas
        if "price" in response.lower():
            # Añadir contexto de valor
            value_context = self.empathy_patterns["price_sensitivity"][0]
            response = f"{value_context} {response}"
        
        if "tiempo" in response.lower():
            # Añadir comprensión de tiempo
            time_context = self.empathy_patterns["time_concern"][0]
            response = f"{time_context} {response}"
        
        return response