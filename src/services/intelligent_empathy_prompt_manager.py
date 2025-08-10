"""
Intelligent Empathy Prompt Manager for NGX Voice Sales Agent.

This manager provides dynamic prompt enhancement with emotional validation,
not just phrase addition. It restructures responses based on emotional context
and ensures genuine, human-like empathy.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import re
from datetime import datetime

from src.services.emotional_intelligence_service import EmotionalProfile, EmotionalTrigger
from src.integrations.elevenlabs.advanced_voice import EmotionalState

logger = logging.getLogger(__name__)


class ResponseTransformationType(str, Enum):
    """Types of response transformations."""
    ANXIETY_CALMING = "anxiety_calming"
    EXCITEMENT_AMPLIFICATION = "excitement_amplification"
    CONFUSION_CLARIFICATION = "confusion_clarification"
    TRUST_BUILDING = "trust_building"
    OBJECTION_SOFTENING = "objection_softening"
    DECISION_SUPPORT = "decision_support"
    RAPPORT_DEEPENING = "rapport_deepening"


@dataclass
class EmotionalContext:
    """Comprehensive emotional context for response transformation."""
    anxiety_level: float = 0.0
    excitement_level: float = 0.0
    confusion_level: float = 0.0
    trust_level: float = 0.5
    engagement_level: float = 0.5
    decision_readiness: float = 0.0
    primary_concern: Optional[str] = None
    conversation_momentum: float = 0.5
    cultural_factors: Dict[str, Any] = None


class IntelligentEmpathyPromptManager:
    """
    Manager for intelligent prompt enhancement with deep empathy.
    
    This goes beyond simple phrase addition to completely restructure
    responses based on emotional and contextual needs.
    """
    
    def __init__(self):
        """Initialize the intelligent empathy prompt manager."""
        self.transformation_strategies = self._initialize_transformation_strategies()
        self.emotional_validators = self._initialize_emotional_validators()
        self.connection_phrases = self._initialize_connection_phrases()
        self.technical_softeners = self._initialize_technical_softeners()
        self.warmth_metrics = self._initialize_warmth_metrics()
        
    def _initialize_transformation_strategies(self) -> Dict[str, Any]:
        """Initialize response transformation strategies."""
        return {
            ResponseTransformationType.ANXIETY_CALMING: {
                "structure": ["validation", "simplification", "reassurance", "next_step"],
                "pacing": "slow",
                "information_density": "low",
                "technical_level": "minimal",
                "emotional_tone": "soothing"
            },
            ResponseTransformationType.EXCITEMENT_AMPLIFICATION: {
                "structure": ["mirror_energy", "build_momentum", "vision_casting", "action"],
                "pacing": "energetic",
                "information_density": "medium",
                "technical_level": "moderate",
                "emotional_tone": "enthusiastic"
            },
            ResponseTransformationType.CONFUSION_CLARIFICATION: {
                "structure": ["acknowledge", "simplify", "analogize", "check_understanding"],
                "pacing": "patient",
                "information_density": "chunked",
                "technical_level": "elementary",
                "emotional_tone": "educational"
            },
            ResponseTransformationType.TRUST_BUILDING: {
                "structure": ["relate", "evidence", "transparency", "invitation"],
                "pacing": "steady",
                "information_density": "balanced",
                "technical_level": "appropriate",
                "emotional_tone": "authentic"
            },
            ResponseTransformationType.OBJECTION_SOFTENING: {
                "structure": ["validate_concern", "reframe", "evidence", "alternative"],
                "pacing": "measured",
                "information_density": "focused",
                "technical_level": "relevant",
                "emotional_tone": "understanding"
            },
            ResponseTransformationType.DECISION_SUPPORT: {
                "structure": ["affirm_readiness", "summarize_value", "clear_path", "support"],
                "pacing": "confident",
                "information_density": "consolidated",
                "technical_level": "outcome-focused",
                "emotional_tone": "empowering"
            }
        }
    
    def _initialize_emotional_validators(self) -> Dict[str, List[str]]:
        """Initialize emotional validation phrases by context."""
        return {
            "price_concern": [
                "Entiendo que el precio es una consideración importante para ti",
                "Tu preocupación sobre la inversión es completamente válida",
                "Aprecio que seas cuidadoso con tus decisiones financieras",
                "Es inteligente evaluar el valor antes de comprometerse"
            ],
            "time_worry": [
                "Sé que tu tiempo es extremadamente valioso",
                "Comprendo la presión de añadir algo más a tu agenda",
                "Tu preocupación sobre el tiempo es muy real y la respeto",
                "Entiendo perfectamente - ya tienes demasiado en tu plato"
            ],
            "skepticism": [
                "Tu escepticismo es una señal de inteligencia",
                "Me gusta que no tomes las cosas a la ligera",
                "Es refrescante hablar con alguien que piensa críticamente",
                "Tu cautela demuestra que tomas decisiones informadas"
            ],
            "overwhelm": [
                "Puedo ver que esto se siente abrumador ahora mismo",
                "Es completamente normal sentirse así con tanta información",
                "Entiendo esa sensación de 'es demasiado'",
                "No estás solo en sentirte así - es una reacción natural"
            ],
            "frustration": [
                "Lamento que hayas tenido esa experiencia frustrante",
                "Tu frustración está completamente justificada",
                "Entiendo por qué esto te ha causado molestia",
                "Tienes todo el derecho de sentirte así"
            ]
        }
    
    def _initialize_connection_phrases(self) -> Dict[str, List[str]]:
        """Initialize personal connection phrases."""
        return {
            "shared_experience": [
                "Muchos de nuestros clientes más exitosos comenzaron exactamente donde estás",
                "He visto esta misma situación transformarse positivamente muchas veces",
                "Tu experiencia es más común de lo que piensas, y hay solución",
                "Conozco personalmente a varios que han superado esto mismo"
            ],
            "understanding": [
                "Esto me dice mucho sobre lo que es importante para ti",
                "Puedo escuchar en tus palabras que esto realmente te importa",
                "Tu perspectiva me ayuda a entender mejor tu situación",
                "Aprecio que compartas esto conmigo - es muy revelador"
            ],
            "support": [
                "Estoy aquí para apoyarte en cada paso del camino",
                "Mi compromiso es hacer esto lo más fácil posible para ti",
                "Juntos vamos a encontrar la mejor solución para ti",
                "No estás solo en este proceso - tienes todo mi apoyo"
            ],
            "vision": [
                "Puedo ver claramente el potencial que tienes",
                "Imagina cómo se sentirá cuando hayas logrado esto",
                "Tu visión de un mejor futuro es completamente alcanzable",
                "Me emociona pensar en lo que vas a lograr"
            ]
        }
    
    def _initialize_technical_softeners(self) -> Dict[str, str]:
        """Initialize technical term softeners."""
        return {
            "algoritmo": "nuestro sistema inteligente",
            "optimización": "mejora personalizada",
            "biomarcadores": "indicadores de tu salud",
            "protocolos": "pasos personalizados",
            "análisis predictivo": "anticipación de necesidades",
            "machine learning": "aprendizaje continuo",
            "datos biométricos": "información de tu cuerpo",
            "sincronización circadiana": "ajuste a tus ritmos naturales",
            "adaptógenos": "elementos naturales anti-estrés",
            "nootrópicos": "potenciadores cognitivos naturales"
        }
    
    def _initialize_warmth_metrics(self) -> Dict[str, float]:
        """Initialize metrics for measuring response warmth."""
        return {
            "personal_pronouns": 0.2,  # "tu", "ti", "nosotros"
            "emotion_words": 0.3,      # "sentir", "emocionar", "importar"
            "support_phrases": 0.3,    # "estoy aquí", "juntos", "apoyo"
            "validation_words": 0.2    # "entiendo", "comprendo", "válido"
        }
    
    async def enhance_response_with_empathy(
        self,
        base_response: str,
        emotional_context: EmotionalContext,
        customer_profile: Dict[str, Any],
        conversation_phase: str = "discovery"
    ) -> str:
        """
        Enhance response with intelligent empathy based on emotional context.
        
        This method completely restructures responses, not just adds phrases.
        
        Args:
            base_response: Original response text
            emotional_context: Comprehensive emotional context
            customer_profile: Customer profile information
            conversation_phase: Current phase of conversation
            
        Returns:
            Enhanced response with deep empathy
        """
        # Determine primary transformation needed
        transformation_type = self._determine_transformation_type(emotional_context)
        
        # Apply transformation strategy
        if transformation_type == ResponseTransformationType.ANXIETY_CALMING:
            return await self._restructure_for_anxiety(
                base_response, emotional_context, customer_profile
            )
        elif transformation_type == ResponseTransformationType.EXCITEMENT_AMPLIFICATION:
            return await self._amplify_excitement(
                base_response, emotional_context, customer_profile
            )
        elif transformation_type == ResponseTransformationType.CONFUSION_CLARIFICATION:
            return await self._simplify_for_clarity(
                base_response, emotional_context, customer_profile
            )
        elif transformation_type == ResponseTransformationType.OBJECTION_SOFTENING:
            return await self._soften_objection_response(
                base_response, emotional_context, customer_profile
            )
        elif transformation_type == ResponseTransformationType.DECISION_SUPPORT:
            return await self._support_decision_making(
                base_response, emotional_context, customer_profile
            )
        else:
            # Apply general contextual enhancement
            return await self._apply_contextual_techniques(
                base_response, emotional_context, customer_profile, conversation_phase
            )
    
    def _determine_transformation_type(self, context: EmotionalContext) -> ResponseTransformationType:
        """Determine the primary transformation type needed."""
        # Priority-based selection
        if context.anxiety_level > 0.7:
            return ResponseTransformationType.ANXIETY_CALMING
        elif context.excitement_level > 0.8:
            return ResponseTransformationType.EXCITEMENT_AMPLIFICATION
        elif context.confusion_level > 0.6:
            return ResponseTransformationType.CONFUSION_CLARIFICATION
        elif context.trust_level < 0.4:
            return ResponseTransformationType.TRUST_BUILDING
        elif context.decision_readiness > 0.7:
            return ResponseTransformationType.DECISION_SUPPORT
        elif context.primary_concern in ["price", "cost", "expensive"]:
            return ResponseTransformationType.OBJECTION_SOFTENING
        else:
            return ResponseTransformationType.RAPPORT_DEEPENING
    
    async def _restructure_for_anxiety(
        self,
        response: str,
        context: EmotionalContext,
        profile: Dict[str, Any]
    ) -> str:
        """Restructure response to calm anxiety."""
        # 1. Start with deep validation
        customer_name = profile.get("name", "")
        validation = f"{customer_name}, entiendo completamente tu situación y respeto profundamente lo que sientes. "
        validation += self._select_contextual_validator("overwhelm", context)
        
        # 2. Normalize their experience
        normalization = " Esto es completamente natural y común entre personas como tú."
        
        # 3. Simplify the message with warmth
        simplified = self._simplify_message(response)
        simplified = f"Te lo explico de manera simple: {simplified}"
        
        # 4. Add strong reassurance with personalization
        reassurance = f"No hay presión alguna, {customer_name}. Estoy aquí para apoyarte y vamos a tu ritmo, paso a paso. Tu bienestar es mi prioridad."
        
        # 5. Provide clear next step with care
        next_step = f"¿Qué aspecto te gustaría que te aclare primero para que te sientas completamente cómodo, {customer_name}?"
        
        # Restructure with enhanced calming flow
        return f"{validation}{normalization}\n\n{simplified}\n\n{reassurance}\n\n{next_step}"
    
    async def _amplify_excitement(
        self,
        response: str,
        context: EmotionalContext,
        profile: Dict[str, Any]
    ) -> str:
        """Amplify response to match excitement."""
        # Add energy markers
        response = self._add_energy_markers(response)
        
        # Insert vision-casting
        vision = self.connection_phrases["vision"][0]
        
        # Add momentum builders
        momentum = "¡Esto es exactamente la energía que lleva al éxito!"
        
        # Structure for excitement
        return f"¡{vision}! {response} {momentum}"
    
    async def _simplify_for_clarity(
        self,
        response: str,
        context: EmotionalContext,
        profile: Dict[str, Any]
    ) -> str:
        """Simplify response for maximum clarity."""
        # Acknowledge confusion
        acknowledgment = self.emotional_validators["overwhelm"][0]
        
        # Break into simple points
        points = self._extract_key_points(response, max_points=3)
        
        # Add analogies if helpful
        simplified_points = []
        for i, point in enumerate(points, 1):
            # Soften technical terms
            point = self._soften_technical_language(point)
            simplified_points.append(f"{i}. {point}")
        
        # Check understanding
        check = "¿Esto tiene más sentido ahora? ¿Qué parte te gustaría que aclare más?"
        
        return f"{acknowledgment}\n\n" + "\n".join(simplified_points) + f"\n\n{check}"
    
    async def _soften_objection_response(
        self,
        response: str,
        context: EmotionalContext,
        profile: Dict[str, Any]
    ) -> str:
        """Soften response to objections."""
        # Validate the concern
        if context.primary_concern == "price":
            validation = self.emotional_validators["price_concern"][0]
        elif context.primary_concern == "time":
            validation = self.emotional_validators["time_worry"][0]
        else:
            validation = "Entiendo completamente tu preocupación"
        
        # Reframe the response
        reframed = self._reframe_value_proposition(response, context.primary_concern)
        
        # Offer alternatives
        alternative = self._suggest_alternative_approach(context.primary_concern)
        
        return f"{validation}. {reframed}\n\n{alternative}"
    
    async def _support_decision_making(
        self,
        response: str,
        context: EmotionalContext,
        profile: Dict[str, Any]
    ) -> str:
        """Support decision-making process."""
        # Affirm their readiness
        affirmation = "Veo que estás listo para dar este importante paso"
        
        # Summarize key value points
        value_summary = self._extract_value_summary(response)
        
        # Provide clear path forward
        clear_path = "Los siguientes pasos son simples y los haremos juntos"
        
        # Express support
        support = self.connection_phrases["support"][0]
        
        return f"{affirmation}. {value_summary}\n\n{clear_path}. {support}"
    
    async def _apply_contextual_techniques(
        self,
        response: str,
        context: EmotionalContext,
        profile: Dict[str, Any],
        phase: str
    ) -> str:
        """Apply general contextual enhancement techniques."""
        customer_name = profile.get("name", "")
        
        # Always inject warmth and personalization
        response = self._increase_warmth(response)
        
        # Add personal connection for trust building
        if context.trust_level < 0.6:
            connection = self.connection_phrases["shared_experience"][0]
            response = f"{customer_name}, {connection.lower()} {response}"
        else:
            # Add personalized opening even if trust is good
            response = f"{customer_name}, {response}"
        
        # Soften technical language
        response = self._soften_technical_language(response)
        
        # Add validation and support phrases
        if "comprendo" not in response.lower() and "entiendo" not in response.lower():
            response = f"Comprendo perfectamente tu perspectiva. {response}"
        
        # Add support commitment
        if "apoyo" not in response.lower() and "aquí para" not in response.lower():
            response += " Estoy aquí para apoyarte en cada paso del camino."
        
        # Add appropriate closing based on phase with personalization
        if phase == "discovery":
            response += f"\n\n¿Qué más te gustaría que te explique, {customer_name}?"
        elif phase == "presentation":
            response += f"\n\n¿Cómo resuena esto contigo, {customer_name}?"
        elif phase == "closing":
            response += f"\n\n¿Qué dudas finales tienes antes de dar este paso, {customer_name}?"
        
        return response
    
    def _select_contextual_validator(self, concern_type: str, context: EmotionalContext) -> str:
        """Select appropriate emotional validator."""
        validators = self.emotional_validators.get(concern_type, ["Entiendo tu punto"])
        # Use context to select most appropriate
        index = int(context.conversation_momentum * (len(validators) - 1))
        return validators[index]
    
    def _simplify_message(self, message: str) -> str:
        """Simplify message for anxious customers."""
        # Remove complex sentences
        sentences = message.split(". ")
        simplified = []
        
        for sentence in sentences:
            if len(sentence) < 100 and not any(term in sentence.lower() for term in self.technical_softeners.keys()):
                simplified.append(sentence)
        
        return ". ".join(simplified[:3])  # Max 3 simple sentences
    
    def _add_energy_markers(self, text: str) -> str:
        """Add energy markers for excitement."""
        # Strategic exclamation points
        text = re.sub(r'\.(\s+[A-Z])', r'!\1', text, count=2)
        
        # Energy words
        energy_replacements = {
            "bueno": "¡excelente!",
            "puede": "definitivamente puede",
            "ayudar": "transformar",
            "mejorar": "revolucionar",
            "cambio": "transformación"
        }
        
        for old, new in energy_replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def _extract_key_points(self, text: str, max_points: int = 3) -> List[str]:
        """Extract key points from text."""
        sentences = text.split(". ")
        key_points = []
        
        for sentence in sentences:
            # Prioritize sentences with key information
            if any(marker in sentence.lower() for marker in ["importante", "clave", "principal", "beneficio"]):
                key_points.append(sentence)
        
        # If not enough key points, take first sentences
        if len(key_points) < max_points:
            key_points.extend(sentences[:max_points - len(key_points)])
        
        return key_points[:max_points]
    
    def _soften_technical_language(self, text: str) -> str:
        """Replace technical terms with softer alternatives."""
        for technical, softer in self.technical_softeners.items():
            text = text.replace(technical, softer)
            text = text.replace(technical.capitalize(), softer.capitalize())
        
        return text
    
    def _reframe_value_proposition(self, response: str, concern: str) -> str:
        """Reframe value proposition based on concern."""
        if concern == "price":
            return response.replace("costo", "inversión en tu bienestar").replace("precio", "valor")
        elif concern == "time":
            return response.replace("tiempo", "momentos estratégicos").replace("requiere", "optimiza")
        else:
            return response
    
    def _suggest_alternative_approach(self, concern: str) -> str:
        """Suggest alternative approach for concerns."""
        alternatives = {
            "price": "¿Te gustaría explorar nuestras opciones más accesibles? Tenemos alternativas que se ajustan a diferentes presupuestos.",
            "time": "¿Qué tal si empezamos con solo 10 minutos al día? NGX se adapta a tu disponibilidad.",
            "trust": "¿Te gustaría ver testimonios de personas como tú? O podemos empezar con una prueba sin compromiso.",
            "complexity": "Podemos simplificar todo al máximo. ¿Prefieres que nos enfoquemos en un solo aspecto primero?"
        }
        return alternatives.get(concern, "¿Qué enfoque funcionaría mejor para ti?")
    
    def _extract_value_summary(self, text: str) -> str:
        """Extract and summarize key value points."""
        # Look for value indicators
        value_markers = ["beneficio", "resultado", "lograr", "mejorar", "optimizar"]
        value_sentences = []
        
        for sentence in text.split(". "):
            if any(marker in sentence.lower() for marker in value_markers):
                value_sentences.append(sentence)
        
        if value_sentences:
            return "En resumen: " + ". ".join(value_sentences[:2])
        else:
            return "Lo más importante es que lograrás tus objetivos de bienestar"
    
    def _increase_warmth(self, text: str) -> str:
        """Increase warmth in response aggressively."""
        # Add personal pronouns and warmth
        text = text.replace("el cliente", "tú")
        text = text.replace("las personas", "personas como tú")
        text = text.replace("la gente", "personas como tú")
        text = text.replace("uno", "tú")
        
        # Add emotional connection and personalization
        text = text.replace("importante", "importante para ti")
        text = text.replace("necesario", "necesario para ti")
        text = text.replace("útil", "útil para ti")
        text = text.replace("beneficioso", "beneficioso para ti")
        
        # Add warmth words where appropriate
        if "entiendo" not in text.lower():
            text = f"Entiendo perfectamente. {text}"
        
        # Add validation phrases
        if not any(phrase in text.lower() for phrase in ["comprendo", "respeto", "valoro"]):
            text = f"Valoro mucho tu perspectiva. {text}"
        
        # Add support commitment
        if not any(phrase in text.lower() for phrase in ["estoy aquí", "juntos", "apoyo", "acompañar"]):
            text += " Estoy completamente aquí para acompañarte en este proceso."
        
        return text
    
    def measure_empathy_quality(self, response: str) -> Dict[str, float]:
        """
        Measure the empathy quality of a response.
        
        Returns metrics on various empathy dimensions.
        """
        metrics = {
            "warmth_score": 0.0,
            "validation_score": 0.0,
            "personalization_score": 0.0,
            "clarity_score": 0.0,
            "support_score": 0.0
        }
        
        # Enhanced warmth detection
        warmth_indicators = [
            "entiendo", "comprendo", "aprecio", "me alegra", "juntos", "respeto", 
            "valoro", "reconozco", "admiro", "importante para ti", "siento", 
            "completamente", "profundamente", "natural", "normal", "común"
        ]
        warmth_count = sum(1 for indicator in warmth_indicators if indicator in response.lower())
        metrics["warmth_score"] = min(warmth_count / 5, 1.0)  # Target 5+ warmth indicators
        
        # Enhanced validation detection
        validation_indicators = [
            "válido", "natural", "normal", "tiene sentido", "razón", "justificado",
            "comprensible", "entendible", "común", "esperado", "apropiado",
            "correcto", "adecuado", "lógico"
        ]
        validation_count = sum(1 for indicator in validation_indicators if indicator in response.lower())
        metrics["validation_score"] = min(validation_count / 3, 1.0)  # Target 3+ validation indicators
        
        # Enhanced personalization detection
        personal_pronouns = ["tu", "tú", "ti", "tuyo", "tuya", "contigo", "para ti"]
        pronoun_count = sum(response.lower().count(pronoun) for pronoun in personal_pronouns)
        metrics["personalization_score"] = min(pronoun_count / 8, 1.0)  # Target 8+ personal references
        
        # Improved clarity measurement
        sentences = response.split(".")
        if len(sentences) > 0:
            avg_sentence_length = len(response.split()) / len(sentences)
            # Score higher for moderate sentence length (10-20 words)
            if 10 <= avg_sentence_length <= 20:
                metrics["clarity_score"] = 1.0
            elif avg_sentence_length < 10:
                metrics["clarity_score"] = 0.8
            else:
                metrics["clarity_score"] = max(0.3, 1 - (avg_sentence_length - 20) / 40)
        else:
            metrics["clarity_score"] = 0.5
        
        # Enhanced support detection
        support_indicators = [
            "ayudar", "apoyar", "aquí para", "conmigo", "acompañar", "guiar",
            "asistir", "facilitar", "colaborar", "trabajar juntos", "resolver juntos"
        ]
        support_count = sum(1 for indicator in support_indicators if indicator in response.lower())
        metrics["support_score"] = min(support_count / 2, 1.0)  # Target 2+ support indicators
        
        # Calculate overall empathy score with weighted importance
        weights = {
            "warmth_score": 0.25,
            "validation_score": 0.25,
            "personalization_score": 0.2,
            "clarity_score": 0.15,
            "support_score": 0.15
        }
        
        metrics["overall_score"] = sum(metrics[key] * weights[key] for key in weights.keys())
        
        return metrics
    
    def generate_empathy_report(self, response: str) -> str:
        """Generate a report on empathy quality."""
        metrics = self.measure_empathy_quality(response)
        
        report = f"""
        Empathy Quality Report:
        - Overall Score: {metrics['overall_score']:.2f}/1.0
        - Warmth: {metrics['warmth_score']:.2f}
        - Validation: {metrics['validation_score']:.2f}
        - Personalization: {metrics['personalization_score']:.2f}
        - Clarity: {metrics['clarity_score']:.2f}
        - Support: {metrics['support_score']:.2f}
        
        Recommendations:
        """
        
        if metrics['warmth_score'] < 0.5:
            report += "\n- Add more warm, understanding language"
        if metrics['validation_score'] < 0.5:
            report += "\n- Include more validation of customer feelings"
        if metrics['personalization_score'] < 0.5:
            report += "\n- Use more personal pronouns (tú, ti)"
        if metrics['clarity_score'] < 0.5:
            report += "\n- Simplify sentences for better clarity"
        if metrics['support_score'] < 0.5:
            report += "\n- Express more supportive intentions"
        
        return report