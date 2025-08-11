"""
Tier Management Mixin

Handles tier detection, adjustment, and upselling strategies.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from src.models.conversation import ConversationState
from src.services.tier_detection_service import TierDetectionService
from src.services.enhanced_price_objection_service import EnhancedPriceObjectionService

logger = logging.getLogger(__name__)


class TierManagementMixin:
    """Mixin for tier detection and management functionality."""
    
    def __init__(self):
        """Initialize tier management components."""
        self.tier_detection_service: Optional[TierDetectionService] = None
        self.price_objection_service: Optional[EnhancedPriceObjectionService] = None
    
    def _init_tier_services(self):
        """Initialize tier services if not already initialized."""
        if not self.tier_detection_service:
            self.tier_detection_service = TierDetectionService()
        if not self.price_objection_service:
            self.price_objection_service = EnhancedPriceObjectionService()
    
    async def _detect_optimal_tier(
        self, 
        message_text: str, 
        state: ConversationState
    ) -> Dict[str, Any]:
        """
        Detectar el tier óptimo para el cliente basado en el contexto.
        
        Args:
            message_text: Mensaje del usuario
            state: Estado de la conversación
            
        Returns:
            Dict con tier detectado y confianza
        """
        self._init_tier_services()
        
        try:
            # Preparar contexto para detección
            # customer_data puede ser dict o objeto, manejar ambos casos
            if isinstance(state.customer_data, dict):
                customer_age = state.customer_data.get('age')
                customer_data_dict = state.customer_data
            else:
                customer_age = getattr(state.customer_data, 'age', None)
                customer_data_dict = state.customer_data.dict()
            
            context = {
                "message": message_text,
                "conversation_history": [msg.content for msg in state.messages[-5:]],
                "customer_age": customer_age,
                "program_type": state.program_type,
                "current_tier": state.tier_detected,
                "message_count": len(state.messages)
            }
            
            # Detectar tier - el método espera user_message, user_profile, conversation_history
            messages_for_history = [
                {"role": msg.role, "content": msg.content} 
                for msg in state.messages[-5:]  # Últimos 5 mensajes
            ]
            
            tier_result = await self.tier_detection_service.detect_optimal_tier(
                user_message=message_text,
                user_profile=customer_data_dict,
                conversation_history=messages_for_history
            )
            
            # Si tier_result es un TierDetectionResult object, convertir a dict
            if hasattr(tier_result, 'recommended_tier'):
                result_dict = {
                    "tier": tier_result.recommended_tier.value if hasattr(tier_result.recommended_tier, 'value') else str(tier_result.recommended_tier),
                    "confidence": tier_result.confidence,
                    "reasoning": tier_result.reasoning,
                    "price_point": tier_result.price_point,
                    "upsell_potential": tier_result.upsell_potential,
                    "detected_archetype": tier_result.detected_archetype.value if hasattr(tier_result.detected_archetype, 'value') else str(tier_result.detected_archetype)
                }
                logger.info(
                    f"Tier detectado: {result_dict['tier']} "
                    f"(confianza: {result_dict['confidence']:.2f})"
                )
                return result_dict
            else:
                # Ya es un dict
                logger.info(
                    f"Tier detectado: {tier_result.get('tier', 'Unknown')} "
                    f"(confianza: {tier_result.get('confidence', 0):.2f})"
                )
                return tier_result
            
        except Exception as e:
            logger.error(f"Error detectando tier: {e}")
            return {
                "tier": state.tier_detected or "AGENTS ACCESS",
                "confidence": 0.5,
                "error": str(e)
            }
    
    async def detect_tier_and_adjust_strategy(
        self,
        message_text: str,
        state: ConversationState
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Detectar tier del cliente y ajustar estrategia de ventas.
        
        Args:
            message_text: Mensaje del usuario
            state: Estado de la conversación
            
        Returns:
            Tuple de (tier detectado, ajustes de estrategia)
        """
        self._init_tier_services()
        
        # Detectar tier óptimo
        tier_detection = await self._detect_optimal_tier(message_text, state)
        
        # Solo actualizar si la confianza es alta
        if tier_detection['confidence'] > 0.7:
            state.tier_detected = tier_detection['tier']
            state.tier_confidence = tier_detection['confidence']
            
            # Ajustar estrategia basada en el tier
            strategy_adjustments = self._adjust_sales_strategy(tier_detection, state)
            
            # Registrar métricas ML si está habilitado
            if state.ml_tracking_enabled and hasattr(self, '_update_ml_conversation_metrics'):
                await self._update_ml_conversation_metrics(
                    state.conversation_id,
                    {
                        "tier_detected": tier_detection['tier'],
                        "tier_confidence": tier_detection['confidence'],
                        "tier_change": tier_detection.get('previous_tier') != tier_detection['tier']
                    }
                )
            
            return tier_detection['tier'], strategy_adjustments
        
        return state.tier_detected or "AGENTS ACCESS", {}
    
    def _adjust_sales_strategy(
        self, 
        tier_detection: Dict[str, Any], 
        state: ConversationState
    ) -> Dict[str, Any]:
        """
        Ajustar la estrategia de ventas basada en el tier detectado.
        
        Args:
            tier_detection: Resultado de la detección de tier
            state: Estado de la conversación
            
        Returns:
            Dict con ajustes de estrategia
        """
        tier = tier_detection['tier']
        adjustments = {
            "tier": tier,
            "approach": "",
            "key_benefits": [],
            "price_anchoring": "",
            "urgency_level": "medium",
            "objection_handling": ""
        }
        
        if state.program_type == "LONGEVITY":
            if tier == "ESSENTIAL":
                adjustments.update({
                    "approach": "value_focused",
                    "key_benefits": [
                        "Acceso básico a HIE para mejorar tu salud",
                        "Plan nutricional personalizado",
                        "Seguimiento mensual de progreso"
                    ],
                    "price_anchoring": "$47/mes - menos que una consulta médica",
                    "urgency_level": "medium",
                    "objection_handling": "emphasize_accessibility"
                })
            elif tier == "PRO":
                adjustments.update({
                    "approach": "transformation_focused",
                    "key_benefits": [
                        "HIE completo con análisis biométrico avanzado",
                        "Coaching semanal personalizado",
                        "Acceso a comunidad exclusiva de biohackers"
                    ],
                    "price_anchoring": "$147/mes - inversión en tu longevidad",
                    "urgency_level": "high",
                    "objection_handling": "roi_demonstration"
                })
            elif tier == "ELITE":
                adjustments.update({
                    "approach": "exclusive_premium",
                    "key_benefits": [
                        "Acceso VIP a todo el ecosistema HIE",
                        "Consultoría directa con expertos",
                        "Protocolos avanzados de optimización celular",
                        "Eventos exclusivos y retiros de bienestar"
                    ],
                    "price_anchoring": "$597/mes - para líderes que priorizan su salud",
                    "urgency_level": "medium",
                    "objection_handling": "exclusive_positioning"
                })
        
        elif state.program_type == "PRIME":
            if tier == "AGENTS ACCESS":
                adjustments.update({
                    "approach": "productivity_focused",
                    "key_benefits": [
                        "11 agentes IA especializados",
                        "Automatización de tareas repetitivas",
                        "Aumento de productividad garantizado"
                    ],
                    "price_anchoring": "$97/mes - recupera 10+ horas semanales",
                    "urgency_level": "high",
                    "objection_handling": "time_value_demonstration"
                })
            elif tier == "HYBRID COACHING":
                adjustments.update({
                    "approach": "comprehensive_transformation",
                    "key_benefits": [
                        "Agentes IA + Coaching humano semanal",
                        "Plan de transformación de 90 días",
                        "Métricas de rendimiento en tiempo real",
                        "Acceso a red de alto rendimiento"
                    ],
                    "price_anchoring": "$497/mes - transformación completa",
                    "urgency_level": "very_high",
                    "objection_handling": "transformation_guarantee"
                })
        
        # Agregar factores de personalización basados en el historial
        if len(state.messages) > 10:
            adjustments["urgency_level"] = "very_high"
            adjustments["approach"] += "_with_scarcity"
        
        return adjustments
    
    async def handle_price_objection_with_tier_adjustment(
        self,
        objection_text: str,
        state: ConversationState,
        current_tier: str
    ) -> Dict[str, Any]:
        """
        Manejar objeción de precio con posible ajuste de tier.
        
        Args:
            objection_text: Texto de la objeción
            state: Estado de la conversación
            current_tier: Tier actual ofrecido
            
        Returns:
            Dict con respuesta y posible tier alternativo
        """
        self._init_tier_services()
        
        try:
            # Analizar la objeción
            # customer_data puede ser dict o objeto, manejar ambos casos
            if isinstance(state.customer_data, dict):
                customer_name = state.customer_data.get('name', '')
                customer_age = state.customer_data.get('age')
            else:
                customer_name = state.customer_data.name
                customer_age = getattr(state.customer_data, 'age', None)
            
            objection_analysis = await self.price_objection_service.analyze_objection(
                objection_text=objection_text,
                customer_profile={
                    "name": customer_name,
                    "age": customer_age,
                    "program_type": state.program_type,
                    "current_tier": current_tier
                },
                conversation_context={
                    "messages": len(state.messages),
                    "duration_minutes": self._calculate_conversation_duration(state),
                    "emotional_state": state.emotional_journey[-1] if state.emotional_journey else None
                }
            )
            
            # Generar respuesta
            response_data = await self.price_objection_service.generate_response(
                objection_analysis=objection_analysis,
                use_biological_roi=True,
                include_guarantee=len(state.messages) > 15
            )
            
            # Si sugiere downsell, ajustar tier
            if response_data.get('suggested_action') == 'downsell':
                new_tier = self._get_downsell_tier(current_tier, state.program_type)
                if new_tier:
                    response_data['alternative_tier'] = new_tier
                    response_data['tier_adjustment'] = self._generate_tier_adjustment_response(
                        current_tier, new_tier, state.program_type
                    )
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error manejando objeción de precio: {e}")
            return {
                "response": "Entiendo tu preocupación. ¿Qué aspecto específico del precio te genera dudas?",
                "error": str(e)
            }
    
    def _generate_tier_adjustment_response(
        self,
        current_tier: str,
        new_tier: str,
        program_type: str
    ) -> str:
        """
        Generar respuesta para ajuste de tier.
        
        Args:
            current_tier: Tier actual
            new_tier: Nuevo tier sugerido
            program_type: Tipo de programa
            
        Returns:
            Mensaje de ajuste de tier
        """
        if program_type == "LONGEVITY":
            tier_messages = {
                ("ELITE", "PRO"): (
                    "Entiendo perfectamente. Muchos de nuestros clientes más exitosos "
                    "comenzaron con el plan PRO y luego升级 cuando vieron los resultados. "
                    "Con PRO aún tienes acceso completo a HIE y coaching semanal por $147/mes."
                ),
                ("PRO", "ESSENTIAL"): (
                    "Te comprendo. El plan ESSENTIAL es perfecto para comenzar tu "
                    "transformación con HIE. Por solo $47/mes tendrás las herramientas "
                    "fundamentales para mejorar tu salud y longevidad."
                ),
                ("ELITE", "ESSENTIAL"): (
                    "Aprecio tu honestidad. Comienza con ESSENTIAL y experimenta el "
                    "poder de HIE. Siempre puedes升级 cuando estés listo. "
                    "¿Te gustaría conocer más sobre este plan?"
                )
            }
        else:  # PRIME
            tier_messages = {
                ("HYBRID COACHING", "AGENTS ACCESS"): (
                    "Entiendo tu situación. AGENTS ACCESS te da acceso completo a "
                    "nuestros 11 agentes IA por $97/mes. Es una excelente forma de "
                    "comenzar a automatizar y optimizar tu productividad."
                )
            }
        
        return tier_messages.get(
            (current_tier, new_tier),
            f"Tenemos opciones más accesibles como {new_tier} que podrían ajustarse mejor a tu presupuesto actual."
        )
    
    async def suggest_upsell_opportunity(
        self,
        state: ConversationState,
        current_performance: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Sugerir oportunidad de upsell basada en el rendimiento.
        
        Args:
            state: Estado de la conversación
            current_performance: Métricas de rendimiento actual
            
        Returns:
            Dict con sugerencia de upsell o None
        """
        # Solo sugerir upsell si:
        # 1. La conversación va bien (alta engagement)
        # 2. El cliente no está en el tier más alto
        # 3. Han pasado al menos 10 mensajes
        
        if len(state.messages) < 10:
            return None
        
        current_tier = state.tier_detected or "AGENTS ACCESS"
        
        # Verificar si hay oportunidad de upsell
        upsell_tier = self._get_upsell_tier(current_tier, state.program_type)
        
        if not upsell_tier:
            return None
        
        # Calcular probabilidad de éxito
        engagement_score = current_performance.get('engagement_score', 0.5)
        emotional_state = state.emotional_journey[-1] if state.emotional_journey else None
        
        upsell_probability = self._calculate_upsell_probability(
            engagement_score, emotional_state, state
        )
        
        if upsell_probability > 0.6:
            benefits = self._get_upsell_benefits(current_tier, upsell_tier)
            
            return {
                "suggested_tier": upsell_tier,
                "probability": upsell_probability,
                "benefits": benefits,
                "message": self._generate_upsell_message(
                    current_tier, upsell_tier, benefits
                )
            }
        
        return None
    
    def _get_downsell_tier(self, current_tier: str, program_type: str) -> Optional[str]:
        """Get the next lower tier."""
        downsell_map = {
            "LONGEVITY": {
                "ELITE": "PRO",
                "PRO": "ESSENTIAL"
            },
            "PRIME": {
                "HYBRID COACHING": "AGENTS ACCESS"
            }
        }
        
        return downsell_map.get(program_type, {}).get(current_tier)
    
    def _get_upsell_tier(self, current_tier: str, program_type: str) -> Optional[str]:
        """Get the next higher tier."""
        upsell_map = {
            "LONGEVITY": {
                "ESSENTIAL": "PRO",
                "PRO": "ELITE"
            },
            "PRIME": {
                "AGENTS ACCESS": "HYBRID COACHING"
            }
        }
        
        return upsell_map.get(program_type, {}).get(current_tier)
    
    def _get_upsell_benefits(self, current_tier: str, suggested_tier: str) -> List[str]:
        """Get benefits of upgrading to a higher tier."""
        benefits_map = {
            ("ESSENTIAL", "PRO"): [
                "Coaching semanal personalizado",
                "Análisis biométrico avanzado",
                "Acceso a comunidad exclusiva",
                "Protocolos de optimización avanzados"
            ],
            ("PRO", "ELITE"): [
                "Acceso VIP completo",
                "Consultoría directa con expertos",
                "Eventos y retiros exclusivos",
                "Soporte prioritario 24/7"
            ],
            ("AGENTS ACCESS", "HYBRID COACHING"): [
                "Coaching humano semanal",
                "Plan de transformación personalizado",
                "Métricas avanzadas de rendimiento",
                "Red de networking de alto nivel"
            ]
        }
        
        return benefits_map.get((current_tier, suggested_tier), [])
    
    def _generate_upsell_message(
        self, 
        current_tier: str, 
        suggested_tier: str, 
        benefits: List[str]
    ) -> str:
        """Generate an upsell message."""
        benefits_text = "\\n".join([f"✓ {benefit}" for benefit in benefits[:3]])
        
        return (
            f"Basado en tus objetivos ambiciosos, creo que {suggested_tier} "
            f"sería perfecto para ti. Además de todo lo que ya incluye {current_tier}, "
            f"tendrías:\\n\\n{benefits_text}\\n\\n"
            f"¿Te gustaría conocer más sobre esta opción premium?"
        )
    
    def _calculate_upsell_probability(
        self,
        engagement_score: float,
        emotional_state: Optional[str],
        state: ConversationState
    ) -> float:
        """Calculate probability of successful upsell."""
        base_probability = engagement_score
        
        # Ajustar por estado emocional
        if emotional_state in ["excited", "interested", "curious"]:
            base_probability += 0.2
        elif emotional_state in ["skeptical", "frustrated", "confused"]:
            base_probability -= 0.3
        
        # Ajustar por duración de conversación
        if len(state.messages) > 20:
            base_probability += 0.1
        
        # Ajustar por menciones de precio previas
        price_mentions = sum(
            1 for msg in state.messages 
            if any(word in msg.content.lower() for word in ["precio", "costo", "caro", "barato"])
        )
        
        if price_mentions > 2:
            base_probability -= 0.2
        
        return max(0.0, min(1.0, base_probability))
    
    def _calculate_conversation_duration(self, state: ConversationState) -> float:
        """Calculate conversation duration in minutes."""
        if not state.messages or len(state.messages) < 2:
            return 0.0
        
        try:
            # Manejar timestamps como string o datetime
            start_timestamp = state.messages[0].timestamp
            if isinstance(start_timestamp, str):
                start_time = datetime.fromisoformat(start_timestamp)
            else:
                start_time = start_timestamp
                
            end_timestamp = state.messages[-1].timestamp
            if isinstance(end_timestamp, str):
                end_time = datetime.fromisoformat(end_timestamp)
            else:
                end_time = end_timestamp
                
            duration = (end_time - start_time).total_seconds() / 60
            return duration
        except (ValueError, AttributeError, IndexError) as e:
            logger.warning(f"Error calculating conversation duration: {e}")
            return 0.0