"""
Emotional Processing Mixin

Handles emotional intelligence, empathy, and personality adaptation.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from src.models.conversation import ConversationState
from src.services.emotional_intelligence_service import EmotionalIntelligenceService
from src.services.empathy_engine_service import EmpathyEngineService
from src.services.adaptive_personality_service import AdaptivePersonalityService
from src.services.nlp_integration_service import NLPIntegrationService

logger = logging.getLogger(__name__)


class EmotionalProcessingMixin:
    """Mixin for emotional intelligence and personality adaptation."""
    
    def __init__(self):
        """Initialize emotional processing components."""
        self.emotional_intelligence_service: Optional[EmotionalIntelligenceService] = None
        self.empathy_engine_service: Optional[EmpathyEngineService] = None
        self.adaptive_personality_service: Optional[AdaptivePersonalityService] = None
        self.nlp_service: Optional[NLPIntegrationService] = None
    
    def _init_emotional_services(self):
        """Initialize emotional services if not already initialized."""
        if not self.nlp_service:
            self.nlp_service = NLPIntegrationService()
        if not self.emotional_intelligence_service:
            # Inicializar sentiment_service primero
            from src.services.advanced_sentiment_service import AdvancedSentimentService
            sentiment_service = AdvancedSentimentService()  # No acepta parámetros
            self.emotional_intelligence_service = EmotionalIntelligenceService(
                nlp_service=self.nlp_service,
                sentiment_service=sentiment_service
            )
        if not self.empathy_engine_service:
            self.empathy_engine_service = EmpathyEngineService()
        if not self.adaptive_personality_service:
            self.adaptive_personality_service = AdaptivePersonalityService()
    
    async def _analyze_emotional_state(
        self,
        message_text: str,
        state: ConversationState,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analizar el estado emocional del cliente basado en su mensaje.
        
        Args:
            message_text: Mensaje del cliente
            state: Estado de la conversación
            context: Contexto adicional
            
        Returns:
            Dict con análisis emocional completo
        """
        self._init_emotional_services()
        
        try:
            # Preparar contexto para análisis
            # customer_data puede ser dict o objeto, manejar ambos casos
            if isinstance(state.customer_data, dict):
                customer_name = state.customer_data.get('name', '')
            else:
                customer_name = state.customer_data.name
            
            analysis_context = {
                "conversation_history": [msg.content for msg in state.messages[-3:]],
                "customer_name": customer_name,
                "program_type": state.program_type,
                "conversation_stage": self._determine_conversation_stage(state),
                "previous_emotions": state.emotional_journey[-3:] if state.emotional_journey else [],
                **(context or {})
            }
            
            # Realizar análisis emocional
            # TEMPORAL: Convertir a formato esperado
            messages = [{"role": "customer", "content": message_text}]
            emotional_profile = await self.emotional_intelligence_service.analyze_emotional_state(
                messages=messages,
                customer_profile=state.customer_data if isinstance(state.customer_data, dict) else None
            )
            
            # Convertir EmotionalProfile a dict para compatibilidad
            emotional_analysis = {
                "primary_emotion": emotional_profile.primary_emotion.value if hasattr(emotional_profile.primary_emotion, 'value') else str(emotional_profile.primary_emotion),
                "emotional_intensity": emotional_profile.confidence,
                "emotional_valence": "positive" if emotional_profile.confidence > 0.6 else "neutral",
                "detected_needs": [],
                "stress_indicators": emotional_profile.triggers,
                "engagement_level": "high" if emotional_profile.stability_score > 0.7 else "medium",
                "emotional_profile": emotional_profile,  # Incluir el perfil completo para el nuevo sistema
                "anxiety_level": 0.8 if emotional_profile.primary_emotion.value == "anxious" else 0.3,
                "excitement_level": 0.8 if emotional_profile.primary_emotion.value == "excited" else 0.3,
                "confusion_level": 0.8 if emotional_profile.primary_emotion.value == "confused" else 0.3
            }
            
            # Agregar al journey emocional
            emotional_entry = {
                "timestamp": datetime.now().isoformat(),
                "message_index": len(state.messages),
                "primary_emotion": emotional_analysis.get("primary_emotion"),
                "emotional_intensity": emotional_analysis.get("emotional_intensity", 0.5),
                "emotional_valence": emotional_analysis.get("emotional_valence", "neutral"),
                "detected_needs": emotional_analysis.get("detected_needs", []),
                "stress_indicators": emotional_analysis.get("stress_indicators", []),
                "engagement_level": emotional_analysis.get("engagement_level", "medium")
            }
            
            state.emotional_journey.append(emotional_entry)
            
            # Mantener solo los últimos 20 entries para eficiencia
            if len(state.emotional_journey) > 20:
                state.emotional_journey = state.emotional_journey[-20:]
            
            logger.info(
                f"Estado emocional analizado: {emotional_analysis.get('primary_emotion')} "
                f"(intensidad: {emotional_analysis.get('emotional_intensity', 0):.2f})"
            )
            
            return emotional_analysis
            
        except Exception as e:
            logger.error(f"Error analizando estado emocional: {e}")
            return {
                "primary_emotion": "neutral",
                "emotional_intensity": 0.5,
                "emotional_valence": "neutral",
                "error": str(e)
            }
    
    async def _analyze_personality(
        self,
        message_text: str,
        state: ConversationState,
        emotional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analizar la personalidad del cliente para adaptar el enfoque.
        
        Args:
            message_text: Mensaje del cliente
            state: Estado de la conversación
            emotional_context: Contexto emocional previo
            
        Returns:
            Dict con análisis de personalidad
        """
        self._init_emotional_services()
        
        try:
            # Construir perfil basado en mensajes anteriores
            conversation_text = " ".join([msg.content for msg in state.messages if msg.role == "user"])
            
            # Analizar personalidad - el método espera 'messages' no 'text'
            messages = [{"role": "customer", "content": msg.content} for msg in state.messages if msg.role == "user"]
            personality_analysis = await self.adaptive_personality_service.analyze_personality(
                messages=messages,
                customer_profile=state.customer_data if isinstance(state.customer_data, dict) else None
            )
            
            # Determinar archetype del cliente
            customer_archetype = self._determine_customer_archetype(state, message_text)
            personality_analysis["customer_archetype"] = customer_archetype
            
            logger.info(f"Personalidad analizada: {personality_analysis.get('personality_type')}")
            
            return personality_analysis
            
        except Exception as e:
            logger.error(f"Error analizando personalidad: {e}")
            return {
                "personality_type": "balanced",
                "communication_style": "direct",
                "decision_making_style": "analytical",
                "error": str(e)
            }
    
    async def _generate_empathic_response(
        self,
        message_text: str,
        emotional_analysis: Dict[str, Any],
        personality_analysis: Dict[str, Any],
        state: ConversationState
    ) -> Dict[str, Any]:
        """
        Generar respuesta empática basada en análisis emocional y de personalidad.
        
        Args:
            message_text: Mensaje del cliente
            emotional_analysis: Análisis emocional
            personality_analysis: Análisis de personalidad
            state: Estado de la conversación
            
        Returns:
            Dict con respuesta empática y adaptaciones
        """
        self._init_emotional_services()
        
        try:
            # Preparar contexto para generación empática
            empathy_context = {
                "emotional_state": emotional_analysis,
                "personality_profile": personality_analysis,
                "conversation_stage": self._determine_conversation_stage(state),
                "customer_concerns": self._extract_concerns_from_message(message_text),
                "program_type": state.program_type,
                "previous_empathic_responses": self._get_recent_empathic_responses(state)
            }
            
            # Generar respuesta empática - necesita EmotionalProfile como primer param
            from src.services.emotional_intelligence_service import EmotionalProfile
            from src.integrations.elevenlabs.advanced_voice import EmotionalState
            
            # Crear perfil emocional desde el análisis
            emotional_profile = EmotionalProfile(
                primary_emotion=EmotionalState.NEUTRAL if emotional_analysis.get("primary_emotion") == "neutral" else EmotionalState.SATISFIED,
                confidence=emotional_analysis.get("emotional_intensity", 0.5),
                emotional_journey=[emotional_analysis]
            )
            
            empathic_response = await self.empathy_engine_service.generate_empathetic_response(
                emotional_profile=emotional_profile,
                original_message=message_text,
                context=empathy_context
            )
            
            # Adaptar tono y estilo basado en personalidad
            # EmpathyResponse es un dataclass, no un dict
            response_text = f"{empathic_response.intro_phrase} {empathic_response.core_message} {empathic_response.closing_phrase}"
            
            adapted_response = await self._adapt_response_to_personality(
                response=response_text,
                personality_analysis=personality_analysis,
                emotional_state=emotional_analysis["primary_emotion"]
            )
            
            return {
                "empathic_response": adapted_response,
                "empathy_techniques": [empathic_response.technique_used.value],
                "emotional_adaptation": empathic_response.emotional_tone,
                "personality_adaptation": {
                    "communication_style": personality_analysis.get("communication_style"),
                    "adapted_tone": self._determine_optimal_tone(personality_analysis, emotional_analysis)
                }
            }
            
        except Exception as e:
            logger.error(f"Error generando respuesta empática: {e}")
            return {
                "empathic_response": "Entiendo tu punto de vista y valoro que compartas esto conmigo.",
                "error": str(e)
            }
    
    def _determine_conversation_stage(self, state: ConversationState) -> str:
        """Determinar la etapa actual de la conversación."""
        message_count = len(state.messages)
        
        if message_count <= 3:
            return "introduction"
        elif message_count <= 8:
            return "discovery"
        elif message_count <= 15:
            return "presentation"
        elif message_count <= 25:
            return "negotiation"
        else:
            return "closing"
    
    def _determine_customer_archetype(self, state: ConversationState, message_text: str) -> str:
        """
        Determinar el arquetipo del cliente basado en patrones de comunicación.
        
        Args:
            state: Estado de la conversación
            message_text: Último mensaje del cliente
            
        Returns:
            str: Arquetipo del cliente
        """
        # Analizar patrones en los mensajes
        all_messages = " ".join([msg.content for msg in state.messages if msg.role == "user"]).lower()
        
        # Palabras clave por arquetipo
        archetypes = {
            "analytical": [
                "datos", "estadísticas", "evidencia", "estudios", "investigación",
                "comprueba", "demuestra", "análisis", "comparar", "lógico"
            ],
            "driver": [
                "rápido", "eficiente", "resultados", "inmediato", "tiempo",
                "productividad", "optimizar", "maximizar", "ganar", "liderar"
            ],
            "expressive": [
                "emocionante", "increíble", "fantástico", "siento", "experiencia",
                "comunidad", "compartir", "conectar", "inspirar", "motivar"
            ],
            "amiable": [
                "seguro", "confianza", "familia", "cómodo", "gradual",
                "apoyo", "ayuda", "tranquilo", "estable", "garantía"
            ],
            "skeptical": [
                "pero", "sin embargo", "dudas", "preocupa", "riesgo",
                "problema", "difícil", "imposible", "no funciona", "estafa"
            ]
        }
        
        # Calcular puntajes
        scores = {}
        for archetype, keywords in archetypes.items():
            score = sum(1 for keyword in keywords if keyword in all_messages)
            scores[archetype] = score
        
        # Determinar arquetipo dominante
        if not scores or max(scores.values()) == 0:
            return "balanced"
        
        dominant_archetype = max(scores, key=scores.get)
        
        # Verificaciones adicionales basadas en comportamiento
        if len(state.messages) > 10 and "skeptical" in scores and scores["skeptical"] > 2:
            return "skeptical"
        
        # Si hay mucha prisa en los mensajes
        if any(word in all_messages for word in ["prisa", "rápido", "ahora", "ya"]):
            return "driver"
        
        return dominant_archetype
    
    def _extract_concerns_from_message(self, message_text: str) -> List[str]:
        """Extraer preocupaciones específicas del mensaje."""
        concerns = []
        message_lower = message_text.lower()
        
        concern_patterns = {
            "price": ["caro", "precio", "costo", "dinero", "pagar", "costoso"],
            "time": ["tiempo", "ocupado", "prisa", "agenda", "disponible"],
            "effectiveness": ["funciona", "sirve", "efectivo", "resultados", "garantía"],
            "complexity": ["complicado", "difícil", "fácil", "sencillo", "entender"],
            "trust": ["confianza", "seguro", "dudas", "riesgo", "estafa"],
            "health": ["salud", "médico", "enfermedad", "seguro", "efectos"]
        }
        
        for concern_type, keywords in concern_patterns.items():
            if any(keyword in message_lower for keyword in keywords):
                concerns.append(concern_type)
        
        return concerns
    
    def _get_recent_empathic_responses(self, state: ConversationState) -> List[str]:
        """Obtener respuestas empáticas recientes para evitar repetición."""
        recent_responses = []
        
        # Buscar respuestas del agente en los últimos 5 mensajes
        for message in state.messages[-5:]:
            if message.role == "assistant":
                # Identificar si contiene elementos empáticos
                empathic_indicators = [
                    "entiendo", "comprendo", "me imagino", "debe ser",
                    "valoro", "aprecio", "reconozco", "es natural"
                ]
                
                if any(indicator in message.content.lower() for indicator in empathic_indicators):
                    recent_responses.append(message.content[:100])  # Primeros 100 caracteres
        
        return recent_responses
    
    async def _adapt_response_to_personality(
        self,
        response: str,
        personality_analysis: Dict[str, Any],
        emotional_state: str
    ) -> str:
        """Adaptar respuesta al perfil de personalidad."""
        personality_type = personality_analysis.get("personality_type", "balanced")
        communication_style = personality_analysis.get("communication_style", "direct")
        
        # Adaptaciones por tipo de personalidad
        if personality_type == "analytical":
            # Agregar datos y lógica
            if "resultados" in response.lower() and "%" not in response:
                response = response.replace(
                    "resultados",
                    "resultados comprobados (93% de nuestros clientes reportan mejoras significativas en 30 días)"
                )
        
        elif personality_type == "driver":
            # Hacer más directo y orientado a resultados
            response = response.replace("te ayudaría", "te dará")
            response = response.replace("podrías ver", "verás")
            if len(response) > 200:
                # Acortar para drivers impacientes
                sentences = response.split(".")
                response = ". ".join(sentences[:2]) + "."
        
        elif personality_type == "expressive":
            # Agregar más entusiasmo y emoción
            if not any(emoji in response for emoji in ["🌟", "💪", "🚀", "✨"]):
                response = "✨ " + response
        
        elif personality_type == "amiable":
            # Hacer más suave y tranquilizador
            response = response.replace("debes", "podrías considerar")
            response = response.replace("necesitas", "te beneficiarías de")
        
        # Adaptaciones por estado emocional
        if emotional_state in ["frustrated", "angry"]:
            # Más calmado y comprensivo
            response = "Entiendo completamente tu perspectiva. " + response
        
        elif emotional_state in ["excited", "enthusiastic"]:
            # Mantener la energía
            if "!" not in response[-10:]:
                response = response.rstrip(".") + "!"
        
        elif emotional_state in ["worried", "anxious"]:
            # Más tranquilizador
            response += " Estamos aquí para apoyarte en cada paso del proceso."
        
        return response
    
    def _determine_optimal_tone(
        self,
        personality_analysis: Dict[str, Any],
        emotional_analysis: Dict[str, Any]
    ) -> str:
        """Determinar el tono óptimo para la respuesta."""
        personality_type = personality_analysis.get("personality_type", "balanced")
        emotional_state = emotional_analysis.get("primary_emotion", "neutral")
        
        # Mapeo de tonos por personalidad y emoción
        tone_map = {
            "analytical": {
                "neutral": "professional_data_driven",
                "skeptical": "evidence_based",
                "curious": "informative_detailed"
            },
            "driver": {
                "neutral": "direct_results_focused",
                "impatient": "concise_action_oriented",
                "excited": "energetic_decisive"
            },
            "expressive": {
                "neutral": "enthusiastic_warm",
                "excited": "very_enthusiastic",
                "worried": "supportive_encouraging"
            },
            "amiable": {
                "neutral": "gentle_reassuring",
                "worried": "very_reassuring",
                "hesitant": "patient_supportive"
            }
        }
        
        return tone_map.get(personality_type, {}).get(emotional_state, "balanced_professional")
    
    def _assess_engagement_level(self, state: ConversationState) -> str:
        """
        Evaluar el nivel de engagement del cliente.
        
        Args:
            state: Estado de la conversación
            
        Returns:
            str: Nivel de engagement (low, medium, high, very_high)
        """
        if not state.messages:
            return "medium"
        
        # Analizar últimos mensajes del usuario
        user_messages = [msg for msg in state.messages[-5:] if msg.role == "user"]
        
        if not user_messages:
            return "low"
        
        engagement_indicators = {
            "high": [
                "interesante", "me gusta", "perfecto", "exactamente", "sí",
                "cuéntame más", "dime más", "¿cómo?", "¿cuándo?", "¿dónde?"
            ],
            "medium": [
                "entiendo", "ok", "bien", "claro", "comprendo"
            ],
            "low": [
                "tal vez", "no sé", "después", "más tarde", "veré"
            ]
        }
        
        # Calcular puntaje de engagement
        engagement_score = 0
        total_words = 0
        
        for message in user_messages:
            message_lower = message.content.lower()
            total_words += len(message.content.split())
            
            for level, indicators in engagement_indicators.items():
                for indicator in indicators:
                    if indicator in message_lower:
                        if level == "high":
                            engagement_score += 2
                        elif level == "medium":
                            engagement_score += 1
                        else:  # low
                            engagement_score -= 1
        
        # Considerar longitud de mensajes
        avg_message_length = total_words / len(user_messages) if user_messages else 0
        
        if avg_message_length > 20:
            engagement_score += 1
        elif avg_message_length < 5:
            engagement_score -= 1
        
        # Determinar nivel final
        if engagement_score >= 4:
            return "very_high"
        elif engagement_score >= 2:
            return "high"
        elif engagement_score >= 0:
            return "medium"
        else:
            return "low"