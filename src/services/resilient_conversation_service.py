"""
Resilient Conversation Service with Retry Mechanisms
Reduces error rates through intelligent retry strategies
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from ..utils.retry_mechanism import with_retry, RetryConfig, RetryableError
from .conversation_service import ConversationService
from ..models.conversation import ConversationState, Message
from ..integrations.supabase import supabase_client

logger = logging.getLogger(__name__)


class ResilientConversationService:
    """Enhanced conversation service with retry mechanisms."""
    
    def __init__(self):
        self.orchestrator = ConversationService()
        self.supabase = supabase_client
        
        # Configure retry policies for different operations
        self.db_retry_config = RetryConfig(
            max_attempts=3,
            initial_delay=0.5,
            retryable_errors=[ConnectionError, TimeoutError],
            retryable_status_codes=[500, 502, 503, 504]
        )
        
        self.api_retry_config = RetryConfig(
            max_attempts=3,
            initial_delay=1.0,
            exponential_base=2.0,
            max_delay=10.0
        )
        
        self.critical_retry_config = RetryConfig(
            max_attempts=5,
            initial_delay=0.2,
            max_delay=5.0,
            jitter=True
        )
    
    @with_retry(RetryConfig(max_attempts=3, initial_delay=0.5))
    async def create_conversation(
        self,
        user_id: str,
        customer_info: Dict[str, Any],
        initial_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new conversation with retry logic."""
        try:
            # Create conversation in database with retry
            conversation_data = await self._create_conversation_db(
                user_id, customer_info
            )
            
            # Initialize conversation state
            state = ConversationState(
                conversation_id=conversation_data["id"],
                user_id=user_id,
                customer_info=customer_info,
                messages=[],
                context={},
                metadata={
                    "created_at": datetime.utcnow().isoformat(),
                    "retry_enabled": True
                }
            )
            
            # Process initial message if provided
            if initial_message:
                response = await self.send_message(
                    conversation_data["id"],
                    initial_message,
                    state
                )
                return {
                    **conversation_data,
                    "response": response["content"],
                    "analytics": response.get("analytics", {})
                }
            
            return conversation_data
            
        except Exception as e:
            logger.error(f"Failed to create conversation after retries: {e}")
            raise
    
    @with_retry()
    async def _create_conversation_db(
        self,
        user_id: str,
        customer_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create conversation in database with retry."""
        response = self.supabase.table("conversations").insert({
            "user_id": user_id,
            "customer_info": customer_info,
            "status": "active",
            "retry_count": 0
        }).execute()
        
        return response.data[0]
    
    async def send_message(
        self,
        conversation_id: str,
        content: str,
        state: Optional[ConversationState] = None
    ) -> Dict[str, Any]:
        """Send message with intelligent retry and fallback."""
        try:
            # Try primary processing
            return await self._process_message_primary(
                conversation_id, content, state
            )
        except Exception as primary_error:
            logger.warning(f"Primary processing failed: {primary_error}")
            
            # Try fallback processing
            try:
                return await self._process_message_fallback(
                    conversation_id, content, state
                )
            except Exception as fallback_error:
                logger.error(f"Fallback processing also failed: {fallback_error}")
                
                # Return graceful degradation response
                return self._create_degraded_response(
                    conversation_id, content, primary_error
                )
    
    @with_retry(RetryConfig(max_attempts=3, initial_delay=0.5))
    async def _process_message_primary(
        self,
        conversation_id: str,
        content: str,
        state: Optional[ConversationState]
    ) -> Dict[str, Any]:
        """Primary message processing with retry."""
        # Get or create state
        if not state:
            state = await self._get_conversation_state(conversation_id)
        
        # Process through orchestrator
        response = await self.orchestrator.process_message(
            state, content
        )
        
        # Save to database with retry
        await self._save_message_to_db(
            conversation_id,
            "user",
            content
        )
        
        await self._save_message_to_db(
            conversation_id,
            "assistant",
            response["content"],
            response.get("metadata", {})
        )
        
        return response
    
    async def _process_message_fallback(
        self,
        conversation_id: str,
        content: str,
        state: Optional[ConversationState]
    ) -> Dict[str, Any]:
        """Fallback message processing for resilience."""
        logger.info("Using fallback message processing")
        
        # Simplified processing without ML features
        response_content = self._generate_fallback_response(content)
        
        # Try to save to database (best effort)
        try:
            await self._save_message_to_db(
                conversation_id, "user", content, {"fallback": True}
            )
            await self._save_message_to_db(
                conversation_id, "assistant", response_content, {"fallback": True}
            )
        except Exception:
            logger.warning("Failed to save fallback messages to database")
        
        return {
            "content": response_content,
            "metadata": {"fallback_mode": True},
            "analytics": {
                "sentiment": 0.0,
                "intent": "unknown",
                "conversion_probability": 0.5
            }
        }
    
    @with_retry(RetryConfig(max_attempts=5, initial_delay=0.2))
    async def _save_message_to_db(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Save message to database with aggressive retry."""
        self.supabase.table("messages").insert({
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }).execute()
    
    @with_retry(RetryConfig(max_attempts=3))
    async def _get_conversation_state(
        self,
        conversation_id: str
    ) -> ConversationState:
        """Get conversation state with retry."""
        # Get conversation data
        conv_response = self.supabase.table("conversations")\
            .select("*")\
            .eq("id", conversation_id)\
            .execute()
        
        if not conv_response.data:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        conv_data = conv_response.data[0]
        
        # Get messages
        msg_response = self.supabase.table("messages")\
            .select("*")\
            .eq("conversation_id", conversation_id)\
            .order("created_at")\
            .execute()
        
        messages = [
            Message(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["created_at"]
            )
            for msg in msg_response.data
        ]
        
        return ConversationState(
            conversation_id=conversation_id,
            user_id=conv_data["user_id"],
            customer_info=conv_data.get("customer_info", {}),
            messages=messages,
            context=conv_data.get("context", {}),
            metadata=conv_data.get("metadata", {})
        )
    
    def _generate_fallback_response(self, user_message: str) -> str:
        """Generate fallback response when all systems fail."""
        user_lower = user_message.lower()
        
        # Basic intent detection
        if any(word in user_lower for word in ["precio", "costo", "cuánto"]):
            return (
                "NGX ofrece planes desde €99/mes. Aunque estoy experimentando "
                "algunas dificultades técnicas, me encantaría contarte más sobre "
                "nuestros planes. ¿Podrías compartir tu email para enviarte "
                "información detallada?"
            )
        elif any(word in user_lower for word in ["hola", "buenos", "saludos"]):
            return (
                "¡Hola! Soy María de NGX. Disculpa, estoy teniendo algunos "
                "problemas técnicos momentáneos, pero estoy aquí para ayudarte. "
                "¿En qué puedo asistirte con tu negocio?"
            )
        elif any(word in user_lower for word in ["ayuda", "problema", "necesito"]):
            return (
                "Entiendo que necesitas ayuda. Aunque estoy experimentando "
                "dificultades técnicas, quiero asegurarme de poder asistirte. "
                "¿Podrías describir brevemente tu situación?"
            )
        else:
            return (
                "Gracias por tu mensaje. Estoy experimentando algunas dificultades "
                "técnicas temporales, pero no quiero que eso afecte nuestra conversación. "
                "¿Podrías repetir tu pregunta o contarme más sobre tu negocio?"
            )
    
    def _create_degraded_response(
        self,
        conversation_id: str,
        user_message: str,
        error: Exception
    ) -> Dict[str, Any]:
        """Create degraded response when everything fails."""
        logger.error(f"Creating degraded response due to: {error}")
        
        return {
            "content": (
                "Disculpa, estoy experimentando dificultades técnicas temporales. "
                "Tu mensaje ha sido registrado y un especialista de NGX te "
                "contactará pronto. Mientras tanto, puedes escribirnos a "
                "soporte@ngx.com o llamar al +34 900 123 456."
            ),
            "metadata": {
                "degraded_mode": True,
                "error_type": type(error).__name__,
                "conversation_id": conversation_id
            },
            "analytics": {
                "sentiment": 0.0,
                "intent": "unknown",
                "conversion_probability": 0.0,
                "requires_human_followup": True
            }
        }
    
    async def get_retry_statistics(self) -> Dict[str, Any]:
        """Get retry statistics for monitoring."""
        from ..utils.retry_mechanism import get_retry_stats
        return get_retry_stats()


# Singleton instance
_resilient_service = None


def get_resilient_conversation_service() -> ResilientConversationService:
    """Get singleton instance of resilient conversation service."""
    global _resilient_service
    if _resilient_service is None:
        _resilient_service = ResilientConversationService()
    return _resilient_service