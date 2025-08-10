"""
Base Conversation Service

Contains core conversation functionality and state management.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from src.models.conversation import ConversationState, CustomerData, Message
from src.models.platform_context import PlatformContext, PlatformInfo
from src.core.agent_factory import agent_factory, AgentInterface
from src.integrations.supabase.resilient_client import resilient_supabase_client as supabase_client
from src.services.ngx_cache_manager import NGXCacheManager
from src.core.dependencies import get_ngx_cache_manager

logger = logging.getLogger(__name__)


class BaseConversationService:
    """Base class for conversation management."""
    
    def __init__(self, industry: str = 'salud'):
        """Initialize base conversation service."""
        self.industry = industry
        self._current_agent: Optional[AgentInterface] = None
        self._initialized = False
        self._cache_manager: Optional[NGXCacheManager] = None
        
        # Verificar adaptadores disponibles
        available_adapters = agent_factory.get_available_adapters()
        logger.info(f"Adaptadores de agente disponibles: {available_adapters}")
    
    async def _ensure_initialized(self) -> None:
        """Ensure the service is initialized before use."""
        if not self._initialized:
            await self.initialize()
    
    async def initialize(self) -> None:
        """Initialize method to be overridden by subclasses."""
        # Initialize cache manager
        self._cache_manager = await get_ngx_cache_manager()
        if self._cache_manager:
            logger.info("Cache manager initialized for conversation service")
        else:
            logger.warning("Running without cache - Redis not available")
    
    async def _get_conversation_state(self, conversation_id: str) -> Optional[ConversationState]:
        """
        Recuperar el estado de una conversación de la base de datos.
        
        Args:
            conversation_id: ID de la conversación
            
        Returns:
            ConversationState si existe, None si no
        """
        # Try cache first
        if self._cache_manager:
            cached_state = await self._cache_manager.get_conversation(conversation_id)
            if cached_state:
                logger.debug(f"Conversation {conversation_id} retrieved from cache")
                return cached_state
        
        try:
            # Buscar en la base de datos
            response = await supabase_client.select(
                table="conversations",
                filters={"conversation_id": conversation_id}
            )
            
            # Handle both list and dict responses from Supabase
            if response:
                if isinstance(response, list):
                    # If response is a list, take the first item if available
                    if len(response) > 0:
                        conversation_data = response[0]
                    else:
                        logger.warning(f"No se encontró la conversación: {conversation_id}")
                        return None
                elif isinstance(response, dict) and response.get('data'):
                    # If response is a dict with 'data' field
                    data = response['data']
                    if isinstance(data, list) and len(data) > 0:
                        conversation_data = data[0]
                    else:
                        conversation_data = data
                else:
                    logger.warning(f"Formato de respuesta inesperado: {type(response)}")
                    return None
                
                # Reconstruir CustomerData
                customer_data = CustomerData(
                    id=conversation_data.get('customer_id', ''),
                    name=conversation_data.get('customer_name', ''),
                    email=conversation_data.get('customer_email'),
                    phone=conversation_data.get('customer_phone'),
                    age=conversation_data.get('customer_age'),
                    initial_message=conversation_data.get('initial_message', '')
                )
                
                # Reconstruir Messages
                messages = []
                if conversation_data.get('messages'):
                    for msg in conversation_data['messages']:
                        messages.append(Message(
                            role=msg.get('role', 'user'),
                            content=msg.get('content', ''),
                            timestamp=msg.get('timestamp', datetime.now().isoformat())
                        ))
                
                # Crear ConversationState
                state = ConversationState(
                    conversation_id=conversation_id,
                    customer_data=customer_data.model_dump() if hasattr(customer_data, 'model_dump') else customer_data.dict(),
                    messages=messages,
                    context=conversation_data.get('context', {}),
                    lead_score=conversation_data.get('lead_score', 0),
                    intent=conversation_data.get('intent'),
                    human_transfer_needed=conversation_data.get('human_transfer_needed', False),
                    program_type=conversation_data.get('program_type', 'LONGEVITY'),
                    tier_detected=conversation_data.get('tier_detected'),
                    tier_confidence=conversation_data.get('tier_confidence', 0.0),
                    emotional_journey=conversation_data.get('emotional_journey', []),
                    experiment_assignments=conversation_data.get('experiment_assignments', []),
                    ml_tracking_enabled=conversation_data.get('ml_tracking_enabled', True)
                )
                
                logger.info(f"Estado de conversación recuperado: {conversation_id}")
                
                # Cache the conversation state
                if self._cache_manager:
                    await self._cache_manager.set_conversation(conversation_id, state)
                    logger.debug(f"Conversation {conversation_id} cached")
                
                return state
                
            else:
                logger.warning(f"No se encontró la conversación: {conversation_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error recuperando estado de conversación: {e}")
            return None
    
    async def _save_conversation_state(self, state: ConversationState) -> bool:
        """
        Guardar el estado de la conversación en la base de datos.
        
        Args:
            state: Estado de la conversación a guardar
            
        Returns:
            bool: True si se guardó exitosamente
        """
        try:
            # Preparar datos para guardar
            # customer_data puede ser un dict o un objeto CustomerData
            if isinstance(state.customer_data, dict):
                customer_id = state.customer_data.get('id', '')
                customer_name = state.customer_data.get('name', '')
                customer_email = state.customer_data.get('email', '')
                customer_phone = state.customer_data.get('phone', '')
                customer_age = state.customer_data.get('age')
                initial_message = state.customer_data.get('initial_message', '')
            else:
                customer_id = state.customer_data.id
                customer_name = state.customer_data.name
                customer_email = state.customer_data.email
                customer_phone = state.customer_data.phone
                customer_age = getattr(state.customer_data, 'age', None)
                initial_message = getattr(state.customer_data, 'initial_message', '')
            
            conversation_data = {
                "conversation_id": state.conversation_id,
                "customer_id": customer_id,
                "customer_name": customer_name,
                "customer_email": customer_email,
                "customer_phone": customer_phone,
                "customer_age": customer_age,
                "initial_message": initial_message,
                "messages": [
                    {
                        **msg.dict(), 
                        "timestamp": msg.timestamp.isoformat() if hasattr(msg.timestamp, 'isoformat') else str(msg.timestamp)
                    } 
                    for msg in state.messages
                ],
                "context": state.context,
                "lead_score": state.lead_score,
                "intent": state.intent,
                "human_transfer_needed": state.human_transfer_needed,
                "program_type": state.program_type,
                "phase": state.phase,  # Agregado el campo phase requerido
                "tier_detected": state.tier_detected,
                "tier_confidence": state.tier_confidence,
                "emotional_journey": state.emotional_journey,
                "experiment_assignments": state.experiment_assignments,
                "ml_tracking_enabled": state.ml_tracking_enabled,
                "status": "active",
                "updated_at": datetime.now().isoformat(),
                "message_count": len(state.messages),
                "last_message_at": datetime.now().isoformat()
            }
            
            # Guardar o actualizar en la base de datos
            await supabase_client.upsert(
                table="conversations",
                data=conversation_data
            )
            
            logger.info(f"Estado de conversación guardado: {state.conversation_id}")
            
            # Invalidate cache for this conversation
            if self._cache_manager:
                await self._cache_manager.delete_conversation(state.conversation_id)
                logger.debug(f"Cache invalidated for conversation {state.conversation_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error guardando estado de conversación: {e}")
            return False
    
    async def _restore_agent_from_state(self, state: ConversationState) -> None:
        """
        Restaurar el agente desde un estado de conversación existente.
        
        Args:
            state: Estado de la conversación
        """
        try:
            # Crear agente del tipo apropiado
            platform_info = PlatformInfo(
                source=state.context.get('platform_source', 'web'),
                device_type=state.context.get('device_type', 'desktop'),
                browser=state.context.get('browser'),
                os=state.context.get('os')
            )
            
            # NO CREAR AGENTE - usar OpenAI directamente
            self._current_agent = None
            
            # Restaurar el historial de mensajes en el agente si es posible
            if hasattr(self._current_agent, 'restore_context'):
                await self._current_agent.restore_context(state.messages, state.context)
            
            logger.info(f"Agente restaurado para conversación: {state.conversation_id}")
            
        except Exception as e:
            logger.error(f"Error restaurando agente: {e}")
            raise RuntimeError(f"No se pudo restaurar el agente: {e}")
    
    def _generate_greeting(self, customer_data: CustomerData, program_type: str) -> str:
        """
        Generar un saludo personalizado basado en los datos del cliente.
        
        Args:
            customer_data: Datos del cliente
            program_type: Tipo de programa ("PRIME" o "LONGEVITY")
            
        Returns:
            str: Mensaje de saludo personalizado
        """
        # Determinar el nombre a usar
        name = customer_data.name if customer_data.name and customer_data.name != "Unknown" else ""
        
        # Generar saludo basado en el programa
        if program_type == "PRIME":
            greeting = f"¡Hola{' ' + name if name else ''}! 🌟 Bienvenido a NGX. "
            greeting += "Soy tu consultor especializado en optimización del rendimiento humano. "
            greeting += "¿Estás listo para descubrir cómo el programa PRIME puede transformar tu rendimiento "
            greeting += "y llevarte al siguiente nivel en tu carrera?"
        else:  # LONGEVITY
            greeting = f"¡Hola{' ' + name if name else ''}! 🌿 Bienvenido a NGX. "
            greeting += "Soy tu consultor en bienestar y longevidad. "
            greeting += "¿Te gustaría conocer cómo nuestro programa LONGEVITY puede ayudarte a "
            greeting += "vivir más años con mejor calidad de vida, energía y vitalidad?"
        
        return greeting
    
    async def _should_continue_conversation(self, state: ConversationState) -> bool:
        """
        Determinar si la conversación debe continuar basado en varias condiciones.
        
        Args:
            state: Estado actual de la conversación
            
        Returns:
            bool: True si debe continuar, False si debe terminar
        """
        # Verificar número máximo de mensajes
        if len(state.messages) > 50:
            logger.info("Conversación alcanzó el límite máximo de mensajes")
            return False
        
        # Verificar si se necesita transferencia humana
        if state.human_transfer_needed:
            logger.info("Transferencia humana solicitada")
            return False
        
        # Verificar duración de la conversación (30 minutos máximo)
        if state.messages:
            # Handle both string and datetime timestamp
            timestamp = state.messages[0].timestamp
            if isinstance(timestamp, str):
                first_message_time = datetime.fromisoformat(timestamp)
            else:
                first_message_time = timestamp
            current_time = datetime.now()
            duration = (current_time - first_message_time).total_seconds() / 60
            
            if duration > 30:
                logger.info(f"Conversación excedió el tiempo máximo: {duration:.1f} minutos")
                return False
        
        # Verificar señales de finalización en el último mensaje
        if state.messages:
            last_message = state.messages[-1].content.lower()
            end_signals = [
                "adiós", "adios", "hasta luego", "bye", "chao", 
                "gracias por todo", "no gracias", "no me interesa",
                "déjame pensarlo", "lo voy a pensar"
            ]
            
            if any(signal in last_message for signal in end_signals):
                logger.info("Señal de finalización detectada en el mensaje")
                return False
        
        return True