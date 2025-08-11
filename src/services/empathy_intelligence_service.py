"""
Empathy Intelligence Service - Consolidated empathy and emotional intelligence functionality.

This service consolidates functionality from:
- advanced_empathy_engine.py
- empathy_engine_service.py
- empathy_prompt_manager.py
- intelligent_empathy_prompt_manager.py
- ultra_empathy_greetings.py
- ultra_empathy_price_handler.py
- emotional_intelligence_service.py

Provides:
- Advanced contextual empathy with learning capabilities
- Emotional state detection and analysis
- Empathetic response generation
- Personalized greeting and price objection handling
- Dynamic prompt management for empathetic responses
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import re
from collections import defaultdict

from src.models.conversation import ConversationState, CustomerData
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)


class EmotionalState(str, Enum):
    """Customer emotional states."""
    ANXIOUS = "anxious"
    FRUSTRATED = "frustrated"
    CONFUSED = "confused"
    SKEPTICAL = "skeptical"
    EXCITED = "excited"
    HESITANT = "hesitant"
    CONFIDENT = "confident"
    DISAPPOINTED = "disappointed"
    CURIOUS = "curious"
    OVERWHELMED = "overwhelmed"
    IMPATIENT = "impatient"
    SATISFIED = "satisfied"


class EmpathyTechnique(str, Enum):
    """Advanced empathy techniques for intelligent responses."""
    VALIDATION = "validation"
    MIRRORING = "mirroring"
    REFRAMING = "reframing"
    NORMALIZATION = "normalization"
    ACKNOWLEDGMENT = "acknowledgment"
    REASSURANCE = "reassurance"
    EMPOWERMENT = "empowerment"
    BRIDGING = "bridging"
    ANTICIPATION = "anticipation"
    EMOTIONAL_LABELING = "emotional_labeling"
    PROGRESSIVE_DISCLOSURE = "progressive_disclosure"
    COLLABORATIVE = "collaborative"


class VoicePersona(str, Enum):
    """Voice personas for different situations."""
    SUPPORTER = "supporter"
    CONSULTANT = "consultant"
    EDUCATOR = "educator"
    MOTIVATOR = "motivator"
    FRIEND = "friend"
    EXPERT = "expert"


@dataclass
class EmotionalProfile:
    """Customer's emotional profile."""
    primary_state: EmotionalState
    intensity: float  # 0.0 to 1.0
    triggers: List[str] = field(default_factory=list)
    patterns: Dict[str, Any] = field(default_factory=dict)
    history: List[EmotionalState] = field(default_factory=list)
    cultural_context: Optional[str] = None


@dataclass
class MicroSignal:
    """Micro-signals detected in customer text."""
    signal_type: str
    confidence: float
    context: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EmpathyStrategy:
    """Personalized empathy strategy."""
    primary_technique: EmpathyTechnique
    secondary_techniques: List[EmpathyTechnique]
    voice_persona: VoicePersona
    tone_adjustments: Dict[str, float]
    cultural_adaptations: List[str]
    confidence: float


@dataclass
class EmpathyResponse:
    """Complete empathetic response structure."""
    intro_phrase: str
    core_message: str
    closing_phrase: str
    technique_used: EmpathyTechnique
    voice_persona: VoicePersona
    emotional_tone: str
    confidence: float
    personalization_factors: List[str]


class EmpathyIntelligenceService:
    """
    Unified empathy and emotional intelligence service.
    
    Features:
    - Advanced emotional state detection
    - Contextual empathy response generation
    - Personalized greeting and objection handling
    - Dynamic prompt management
    - Cultural and demographic adaptations
    - Learning from interaction patterns
    """
    
    def __init__(self):
        """Initialize empathy intelligence service."""
        self.emotional_patterns = self._initialize_emotional_patterns()
        self.empathy_templates = self._initialize_empathy_templates()
        self.greeting_templates = self._initialize_greeting_templates()
        self.price_objection_templates = self._initialize_price_objection_templates()
        self.cultural_adaptations = self._initialize_cultural_adaptations()
        self.micro_signals = self._initialize_micro_signals()
        self.learned_patterns: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        logger.info("EmpathyIntelligenceService initialized")
    
    def _initialize_emotional_patterns(self) -> Dict[EmotionalState, Dict[str, Any]]:
        """Initialize emotional detection patterns."""
        return {
            EmotionalState.ANXIOUS: {
                "keywords": ["preocupa", "nervioso", "ansiedad", "miedo", "temor", "inseguro", "dudas"],
                "phrases": ["no estoy seguro", "me da miedo", "qué pasa si", "no sé si"],
                "patterns": [r"no\s+sé\s+si", r"qué\s+pasa\s+si", r"tengo\s+miedo"],
                "intensity_indicators": ["muy", "mucho", "bastante", "demasiado"]
            },
            EmotionalState.FRUSTRATED: {
                "keywords": ["molesto", "enojado", "frustrado", "harto", "cansado", "irritado"],
                "phrases": ["no funciona", "ya probé todo", "esto es imposible", "no entiendo por qué"],
                "patterns": [r"ya\s+probé\s+todo", r"esto\s+no\s+funciona", r"no\s+entiendo\s+por\s+qué"],
                "intensity_indicators": ["muy", "extremadamente", "súper", "demasiado"]
            },
            EmotionalState.CONFUSED: {
                "keywords": ["confundido", "perdido", "enredado", "complicado", "difícil", "complejo"],
                "phrases": ["no entiendo", "es muy complicado", "me perdí", "no me queda claro"],
                "patterns": [r"no\s+entiendo", r"me\s+perdí", r"no\s+me\s+queda\s+claro"],
                "intensity_indicators": ["muy", "totalmente", "completamente"]
            },
            EmotionalState.SKEPTICAL: {
                "keywords": ["dudo", "sospecho", "desconfianza", "esceptico", "increíble", "imposible"],
                "phrases": ["no me lo creo", "suena demasiado bueno", "no puede ser", "es imposible"],
                "patterns": [r"no\s+me\s+lo\s+creo", r"suena\s+demasiado\s+bueno", r"es\s+imposible"],
                "intensity_indicators": ["muy", "totalmente", "completamente", "imposible"]
            },
            EmotionalState.EXCITED: {
                "keywords": ["emocionado", "genial", "increíble", "fantástico", "perfecto", "excelente"],
                "phrases": ["esto es genial", "me encanta", "perfecto", "exactamente lo que necesito"],
                "patterns": [r"esto\s+es\s+genial", r"me\s+encanta", r"exactamente\s+lo\s+que"],
                "intensity_indicators": ["muy", "súper", "extremadamente", "increíblemente"]
            }
        }
    
    def _initialize_empathy_templates(self) -> Dict[EmotionalState, Dict[str, Any]]:
        """Initialize empathy response templates."""
        return {
            EmotionalState.ANXIOUS: {
                "intro_phrases": [
                    "Entiendo perfectamente tu preocupación",
                    "Es completamente normal sentirse así",
                    "Comprendo que esto puede generar inquietud",
                    "Tu preocupación es totalmente válida"
                ],
                "core_messages": [
                    "Te voy a acompañar paso a paso para que te sientas completamente seguro",
                    "Vamos a resolver esto juntos, no tienes que preocuparte por nada",
                    "Permíteme mostrarte exactamente cómo funciona para que estés tranquilo"
                ],
                "closing_phrases": [
                    "¿Te parece si empezamos por ahí para que te sientas más cómodo?",
                    "¿Qué tal si vemos esto con calma?",
                    "¿Te ayudaría si empezamos por lo más simple?"
                ],
                "techniques": [EmpathyTechnique.VALIDATION, EmpathyTechnique.REASSURANCE],
                "voice_persona": VoicePersona.SUPPORTER,
                "tone": "calmante y tranquilizador"
            },
            EmotionalState.FRUSTRATED: {
                "intro_phrases": [
                    "Lamento mucho que estés experimentando esto",
                    "Entiendo tu frustración, es totalmente válida",
                    "Comprendo lo molesto que debe ser esto para ti",
                    "Siento que hayas tenido esta experiencia"
                ],
                "core_messages": [
                    "Déjame ayudarte a resolver esto de manera definitiva",
                    "Voy a asegurarme de que esto funcione perfectamente para ti",
                    "Tengo la solución exacta para lo que estás viviendo"
                ],
                "closing_phrases": [
                    "¿Te parece si lo resolvemos ahora mismo?",
                    "¿Quieres que empecemos a solucionarlo ya?",
                    "¿Te ayudo a que esto funcione como debe ser?"
                ],
                "techniques": [EmpathyTechnique.ACKNOWLEDGMENT, EmpathyTechnique.REFRAMING],
                "voice_persona": VoicePersona.CONSULTANT,
                "tone": "comprensivo y solucionador"
            },
            EmotionalState.CONFUSED: {
                "intro_phrases": [
                    "Permíteme aclararte esto de manera más simple",
                    "Es normal tener dudas, déjame explicártelo mejor",
                    "Entiendo que puede parecer complejo, vamos paso a paso",
                    "Te voy a explicar esto de una forma súper clara"
                ],
                "core_messages": [
                    "Voy a dividir esto en pasos simples para que sea súper fácil de entender",
                    "Te explico todo paso a paso, sin complicaciones",
                    "Déjame hacértelo súper sencillo"
                ],
                "closing_phrases": [
                    "¿Te parece si empezamos por el paso uno?",
                    "¿Vamos paso a paso para que quede clarísimo?",
                    "¿Te explico primero lo básico?"
                ],
                "techniques": [EmpathyTechnique.NORMALIZATION, EmpathyTechnique.BRIDGING],
                "voice_persona": VoicePersona.EDUCATOR,
                "tone": "claro y paciente"
            },
            EmotionalState.CURIOUS: {
                "intro_phrases": [
                    "Me alegra ver tu interés",
                    "Excelente pregunta",
                    "Qué bueno que quieras saber más"
                ],
                "core_messages": [
                    "Te voy a explicar todo lo que necesitas saber",
                    "Déjame mostrarte cómo funciona exactamente",
                    "Voy a darte toda la información que buscas"
                ],
                "closing_phrases": [
                    "¿Te gustaría que profundicemos en algún aspecto específico?",
                    "¿Hay algo más que te interese saber?",
                    "¿Qué otros detalles te gustaría conocer?"
                ],
                "techniques": [EmpathyTechnique.EMPOWERMENT, EmpathyTechnique.BRIDGING],
                "voice_persona": VoicePersona.EDUCATOR,
                "tone": "entusiasta y educativo"
            }
        }
    
    def _initialize_greeting_templates(self) -> Dict[str, List[str]]:
        """Initialize ultra-empathy greeting templates."""
        return {
            "morning": [
                "¡Buenos días! Espero que tengas un día increíble. Estoy aquí para ayudarte con todo lo que necesites sobre NGX.",
                "¡Hola! ¿Cómo amaneciste? Me da muchísimo gusto poder platicar contigo hoy sobre cómo NGX puede transformar tu gimnasio.",
                "¡Buenos días! Qué alegría poder conectar contigo. Estoy emocionado de mostrarte todo lo que NGX puede hacer por ti."
            ],
            "afternoon": [
                "¡Buenas tardes! Espero que estés teniendo un excelente día. Estoy aquí para ayudarte a descubrir cómo NGX puede revolucionar tu negocio.",
                "¡Hola! ¿Cómo va tu tarde? Me emociona mucho poder platicar contigo sobre las increíbles posibilidades que NGX tiene para ti.",
                "¡Buenas tardes! Qué gusto poder hablar contigo. Estoy aquí para mostrarte exactamente cómo NGX puede transformar tu gimnasio."
            ],
            "evening": [
                "¡Buenas noches! Espero que hayas tenido un día productivo. Estoy aquí para ayudarte a descubrir todo el potencial de NGX.",
                "¡Hola! ¿Cómo estuvo tu día? Me da mucho gusto poder platicar contigo sobre cómo NGX puede llevar tu negocio al siguiente nivel.",
                "¡Buenas noches! Qué alegría poder conectar contigo. Estoy emocionado de mostrarte las increíbles capacidades de NGX."
            ],
            "default": [
                "¡Hola! Qué gusto poder platicar contigo. Estoy súper emocionado de mostrarte todo lo que NGX puede hacer por tu gimnasio.",
                "¡Hola! Me da muchísimo gusto poder hablar contigo hoy. Estoy aquí para ayudarte a descubrir cómo NGX puede transformar tu negocio.",
                "¡Hola! Qué alegría poder conectar contigo. Estoy emocionado de mostrarte exactamente cómo NGX puede revolucionar tu gimnasio."
            ]
        }
    
    def _initialize_price_objection_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize ultra-empathy price objection handling."""
        return {
            "expensive": {
                "empathy_intro": [
                    "Entiendo perfectamente tu preocupación sobre la inversión",
                    "Comprendo que quieras asegurarte de que sea una inversión inteligente",
                    "Es totalmente válido que quieras evaluar el costo-beneficio"
                ],
                "reframe": [
                    "déjame mostrarte por qué NGX en realidad te va a ahorrar dinero",
                    "permíteme explicarte cómo esta inversión se paga sola en menos de 3 meses",
                    "te voy a mostrar exactamente cómo NGX multiplica tus ingresos"
                ],
                "roi_focus": [
                    "Con NGX, nuestros clientes ven un retorno de inversión del 400-800%",
                    "La mayoría de nuestros clientes recuperan su inversión en 60-90 días",
                    "NGX genera entre 3x y 8x más ingresos de los que cuesta"
                ]
            },
            "budget_constraints": {
                "empathy_intro": [
                    "Entiendo completamente la situación del presupuesto",
                    "Comprendo que hay que ser inteligente con las inversiones",
                    "Es normal querer asegurarse de que sea el momento adecuado"
                ],
                "reframe": [
                    "déjame mostrarte nuestras opciones de inversión flexibles",
                    "tenemos planes que se adaptan a diferentes situaciones",
                    "podemos estructurar esto de una forma que funcione para ti"
                ],
                "value_proposition": [
                    "NGX se paga solo - es una inversión que genera ingresos inmediatos",
                    "Con NGX, tu gimnasio puede generar $5,000-$20,000 adicionales al mes",
                    "La pregunta real es: ¿te puedes permitir no tener NGX?"
                ]
            }
        }
    
    def _initialize_cultural_adaptations(self) -> Dict[str, Dict[str, Any]]:
        """Initialize cultural adaptation patterns."""
        return {
            "mexican": {
                "formal_address": True,
                "warmth_level": "high",
                "family_references": True,
                "phrases": ["por favor", "con mucho gusto", "para servirle"],
                "avoid": ["aggressive sales language"]
            },
            "american": {
                "formal_address": False,
                "warmth_level": "medium",
                "efficiency_focus": True,
                "phrases": ["absolutely", "perfect", "exactly"],
                "avoid": ["overly formal language"]
            },
            "latin_america": {
                "formal_address": True,
                "warmth_level": "high",
                "relationship_focus": True,
                "phrases": ["con todo gusto", "por supuesto", "perfecto"],
                "avoid": ["cold or impersonal language"]
            }
        }
    
    def _initialize_micro_signals(self) -> Dict[str, Dict[str, Any]]:
        """Initialize micro-signal detection patterns."""
        return {
            "urgency": {
                "patterns": [r"necesito\s+ya", r"urgente", r"rápido", r"pronto"],
                "confidence": 0.8,
                "action": "accelerate_process"
            },
            "price_sensitivity": {
                "patterns": [r"caro", r"costo", r"precio", r"presupuesto", r"dinero"],
                "confidence": 0.7,
                "action": "focus_on_roi"
            },
            "skepticism": {
                "patterns": [r"no\s+creo", r"imposible", r"dudo", r"sospechoso"],
                "confidence": 0.9,
                "action": "provide_proof"
            },
            "interest": {
                "patterns": [r"interesante", r"genial", r"perfecto", r"me\s+gusta"],
                "confidence": 0.8,
                "action": "accelerate_close"
            }
        }
    
    async def analyze_emotional_state(
        self,
        message: str,
        conversation_history: Optional[List[str]] = None,
        customer_profile: Optional[CustomerData] = None
    ) -> EmotionalProfile:
        """
        Analyze customer's emotional state from their message.
        
        Args:
            message: Customer's message
            conversation_history: Previous messages for context
            customer_profile: Customer profile for personalization
            
        Returns:
            Emotional profile with detected state and patterns
        """
        message_lower = message.lower()
        detected_emotions: Dict[EmotionalState, float] = {}
        
        # Analyze against each emotional pattern
        for state, patterns in self.emotional_patterns.items():
            confidence = 0.0
            
            # Keyword matching
            keyword_matches = sum(1 for keyword in patterns["keywords"] if keyword in message_lower)
            if keyword_matches > 0:
                confidence += keyword_matches * 0.2
            
            # Phrase matching
            phrase_matches = sum(1 for phrase in patterns["phrases"] if phrase in message_lower)
            if phrase_matches > 0:
                confidence += phrase_matches * 0.3
            
            # Pattern matching (regex)
            pattern_matches = sum(1 for pattern in patterns["patterns"] if re.search(pattern, message_lower))
            if pattern_matches > 0:
                confidence += pattern_matches * 0.4
            
            # Intensity modifiers
            intensity_matches = sum(1 for indicator in patterns["intensity_indicators"] if indicator in message_lower)
            if intensity_matches > 0:
                confidence += intensity_matches * 0.1
            
            if confidence > 0:
                detected_emotions[state] = min(confidence, 1.0)
        
        # Determine primary emotional state
        if detected_emotions:
            primary_state = max(detected_emotions.items(), key=lambda x: x[1])[0]
            intensity = detected_emotions[primary_state]
        else:
            primary_state = EmotionalState.CURIOUS  # Default state
            intensity = 0.5
        
        # Detect micro-signals
        micro_signals = self._detect_micro_signals(message)
        
        # Build emotional profile
        profile = EmotionalProfile(
            primary_state=primary_state,
            intensity=intensity,
            triggers=micro_signals,
            patterns=detected_emotions,
            cultural_context=customer_profile.preferred_language if customer_profile else "spanish"
        )
        
        logger.info(f"Emotional analysis: {primary_state} (intensity: {intensity:.2f})")
        return profile
    
    def _detect_micro_signals(self, message: str) -> List[str]:
        """Detect micro-signals in customer message."""
        signals = []
        message_lower = message.lower()
        
        for signal_type, config in self.micro_signals.items():
            for pattern in config["patterns"]:
                if re.search(pattern, message_lower):
                    signals.append(signal_type)
                    break
        
        return signals
    
    async def generate_empathy_strategy(
        self,
        emotional_profile: EmotionalProfile,
        conversation_context: Dict[str, Any],
        customer_profile: Optional[CustomerData] = None
    ) -> EmpathyStrategy:
        """
        Generate personalized empathy strategy.
        
        Args:
            emotional_profile: Customer's emotional state
            conversation_context: Current conversation context
            customer_profile: Customer profile for personalization
            
        Returns:
            Complete empathy strategy
        """
        primary_state = emotional_profile.primary_state
        template = self.empathy_templates.get(primary_state, self.empathy_templates[EmotionalState.CURIOUS])
        
        # Select primary technique
        primary_technique = template["techniques"][0]
        secondary_techniques = template["techniques"][1:] if len(template["techniques"]) > 1 else []
        
        # Select voice persona
        voice_persona = template["voice_persona"]
        
        # Cultural adaptations
        cultural_context = emotional_profile.cultural_context or "spanish"
        cultural_adaptations = self.cultural_adaptations.get(cultural_context, {})
        
        # Calculate confidence based on emotional intensity
        confidence = emotional_profile.intensity * 0.8 + 0.2  # Minimum 20% confidence
        
        strategy = EmpathyStrategy(
            primary_technique=primary_technique,
            secondary_techniques=secondary_techniques,
            voice_persona=voice_persona,
            tone_adjustments={"warmth": emotional_profile.intensity},
            cultural_adaptations=list(cultural_adaptations.keys()) if cultural_adaptations else [],
            confidence=confidence
        )
        
        logger.info(f"Generated empathy strategy: {primary_technique} with {voice_persona}")
        return strategy
    
    async def generate_empathy_response(
        self,
        message: str,
        emotional_profile: EmotionalProfile,
        empathy_strategy: EmpathyStrategy,
        conversation_context: Dict[str, Any]
    ) -> EmpathyResponse:
        """
        Generate complete empathetic response.
        
        Args:
            message: Customer's message
            emotional_profile: Customer's emotional state
            empathy_strategy: Empathy strategy to apply
            conversation_context: Conversation context
            
        Returns:
            Complete empathy response
        """
        primary_state = emotional_profile.primary_state
        template = self.empathy_templates.get(primary_state, self.empathy_templates[EmotionalState.CURIOUS])
        
        # Select components based on strategy
        intro_phrase = self._select_random_item(template["intro_phrases"])
        core_message = self._select_random_item(template["core_messages"])
        closing_phrase = self._select_random_item(template["closing_phrases"])
        
        # Apply cultural adaptations
        if "formal_address" in empathy_strategy.cultural_adaptations:
            intro_phrase = self._apply_formal_address(intro_phrase)
            closing_phrase = self._apply_formal_address(closing_phrase)
        
        response = EmpathyResponse(
            intro_phrase=intro_phrase,
            core_message=core_message,
            closing_phrase=closing_phrase,
            technique_used=empathy_strategy.primary_technique,
            voice_persona=empathy_strategy.voice_persona,
            emotional_tone=template["tone"],
            confidence=empathy_strategy.confidence,
            personalization_factors=empathy_strategy.cultural_adaptations
        )
        
        logger.info(f"Generated empathy response with technique: {empathy_strategy.primary_technique}")
        return response
    
    def _select_random_item(self, items: List[str]) -> str:
        """Select random item from list."""
        import random
        return random.choice(items) if items else ""
    
    def _apply_formal_address(self, text: str) -> str:
        """Apply formal address to text."""
        # Simple formal address conversion
        text = text.replace("tu ", "su ")
        text = text.replace("tus ", "sus ")
        text = text.replace("te ", "le ")
        return text
    
    async def generate_ultra_empathy_greeting(
        self,
        customer_profile: Optional[CustomerData] = None,
        time_context: Optional[str] = None
    ) -> str:
        """
        Generate ultra-empathy greeting.
        
        Args:
            customer_profile: Customer profile for personalization
            time_context: Time of day context (morning/afternoon/evening)
            
        Returns:
            Personalized empathetic greeting
        """
        # Determine time context
        if not time_context:
            current_hour = datetime.now().hour
            if 5 <= current_hour < 12:
                time_context = "morning"
            elif 12 <= current_hour < 18:
                time_context = "afternoon"
            elif 18 <= current_hour < 22:
                time_context = "evening"
            else:
                time_context = "default"
        
        # Select greeting template
        templates = self.greeting_templates.get(time_context, self.greeting_templates["default"])
        greeting = self._select_random_item(templates)
        
        # Personalize if customer profile available
        if customer_profile and customer_profile.name:
            greeting = greeting.replace("contigo", f"contigo, {customer_profile.name}")
        
        logger.info(f"Generated ultra-empathy greeting for {time_context}")
        return greeting
    
    async def handle_price_objection_with_empathy(
        self,
        objection_message: str,
        customer_profile: Optional[CustomerData] = None
    ) -> str:
        """
        Handle price objections with ultra-empathy.
        
        Args:
            objection_message: Customer's price objection
            customer_profile: Customer profile for personalization
            
        Returns:
            Empathetic price objection response
        """
        objection_lower = objection_message.lower()
        
        # Determine objection type
        objection_type = "expensive"  # default
        if any(word in objection_lower for word in ["presupuesto", "dinero", "no puedo", "budget"]):
            objection_type = "budget_constraints"
        
        template = self.price_objection_templates[objection_type]
        
        # Build response
        empathy_intro = self._select_random_item(template["empathy_intro"])
        reframe = self._select_random_item(template["reframe"])
        value_prop = self._select_random_item(template.get("roi_focus", template.get("value_proposition", [])))
        
        response = f"{empathy_intro}, {reframe}. {value_prop}"
        
        logger.info(f"Generated empathetic price objection response for type: {objection_type}")
        return response
    
    async def learn_from_interaction(
        self,
        customer_id: str,
        emotional_profile: EmotionalProfile,
        empathy_strategy: EmpathyStrategy,
        customer_response: str,
        outcome_positive: bool
    ) -> None:
        """
        Learn from customer interaction outcomes.
        
        Args:
            customer_id: Customer identifier
            emotional_profile: Emotional profile used
            empathy_strategy: Empathy strategy applied
            customer_response: Customer's response
            outcome_positive: Whether outcome was positive
        """
        # Store learning data
        if customer_id not in self.learned_patterns:
            self.learned_patterns[customer_id] = {
                "successful_strategies": [],
                "failed_strategies": [],
                "emotional_patterns": [],
                "preferences": {}
            }
        
        strategy_data = {
            "technique": empathy_strategy.primary_technique.value,
            "voice_persona": empathy_strategy.voice_persona.value,
            "emotional_state": emotional_profile.primary_state.value,
            "intensity": emotional_profile.intensity,
            "timestamp": datetime.now().isoformat()
        }
        
        if outcome_positive:
            self.learned_patterns[customer_id]["successful_strategies"].append(strategy_data)
        else:
            self.learned_patterns[customer_id]["failed_strategies"].append(strategy_data)
        
        # Update emotional patterns
        self.learned_patterns[customer_id]["emotional_patterns"].append({
            "state": emotional_profile.primary_state.value,
            "intensity": emotional_profile.intensity,
            "triggers": emotional_profile.triggers,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"Learning recorded for customer {customer_id}: {'positive' if outcome_positive else 'negative'}")
    
    async def get_personalized_strategy(
        self,
        customer_id: str,
        current_emotional_profile: EmotionalProfile
    ) -> Optional[EmpathyStrategy]:
        """
        Get personalized strategy based on learned patterns.
        
        Args:
            customer_id: Customer identifier
            current_emotional_profile: Current emotional state
            
        Returns:
            Personalized empathy strategy or None if no learning data
        """
        if customer_id not in self.learned_patterns:
            return None
        
        patterns = self.learned_patterns[customer_id]
        successful_strategies = patterns["successful_strategies"]
        
        if not successful_strategies:
            return None
        
        # Find strategies that worked for similar emotional states
        matching_strategies = [
            s for s in successful_strategies
            if s["emotional_state"] == current_emotional_profile.primary_state.value
        ]
        
        if not matching_strategies:
            # Fallback to any successful strategy
            matching_strategies = successful_strategies
        
        # Use most recent successful strategy
        latest_strategy = max(matching_strategies, key=lambda x: x["timestamp"])
        
        # Create strategy from learned data
        strategy = EmpathyStrategy(
            primary_technique=EmpathyTechnique(latest_strategy["technique"]),
            secondary_techniques=[],
            voice_persona=VoicePersona(latest_strategy["voice_persona"]),
            tone_adjustments={"warmth": current_emotional_profile.intensity},
            cultural_adaptations=[],
            confidence=0.9  # High confidence for learned strategies
        )
        
        logger.info(f"Using personalized strategy for customer {customer_id}")
        return strategy
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get empathy service statistics."""
        return {
            "total_customers_learned": len(self.learned_patterns),
            "emotional_patterns_count": len(self.emotional_patterns),
            "empathy_techniques_count": len(EmpathyTechnique),
            "voice_personas_count": len(VoicePersona),
            "greeting_templates": sum(len(templates) for templates in self.greeting_templates.values()),
            "price_objection_templates": len(self.price_objection_templates),
            "micro_signals_count": len(self.micro_signals)
        }