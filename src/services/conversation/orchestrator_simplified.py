"""
Simplified Conversation Orchestrator

Streamlined version that reduces processing layers and improves performance.
"""

import logging
import asyncio
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime
import uuid

from src.models.conversation import ConversationState, CustomerData, Message
from src.integrations.openai_client import get_openai_client
from src.conversation.prompts.unified_prompts import UNIFIED_SYSTEM_PROMPT
from src.config.empathy_config import EmpathyConfig
from src.services.ultra_empathy_price_handler import get_price_handler, PriceObjectionContext

logger = logging.getLogger(__name__)


class SimplifiedOrchestrator:
    """
    Simplified orchestrator that consolidates all processing into fewer steps.
    
    Key improvements:
    - Single GPT-4o call for all analysis and response
    - No redundant processing layers
    - Faster response times
    - More coherent responses
    """
    
    def __init__(self):
        self.openai_client = get_openai_client()
        self.price_handler = get_price_handler()
        
    async def process_message(
        self,
        message_text: str,
        state: ConversationState
    ) -> Dict[str, Any]:
        """
        Process message with simplified flow.
        
        1. Quick context analysis (price objection, emotional state)
        2. Single GPT-4o call with all context
        3. Post-processing only if needed
        """
        try:
            # Add user message to state
            user_message = Message(
                role="user",
                content=message_text,
                timestamp=datetime.now().isoformat()
            )
            state.messages.append(user_message)
            
            # Quick analysis - no separate service calls
            context_analysis = self._quick_analyze_context(message_text, state)
            
            # Handle price objections with specialized handler
            if context_analysis["has_price_objection"]:
                price_context = PriceObjectionContext(
                    objection_text=message_text,
                    customer_name=state.customer_data.get("name", ""),
                    detected_emotion=context_analysis["primary_emotion"],
                    tier_mentioned=state.context.get("tier", "pro"),
                    conversation_phase=state.phase,
                    previous_objections=[]
                )
                price_response = self.price_handler.generate_ultra_empathetic_response(price_context)
                final_response = price_response["response"]
                
                # Add follow-up question if provided
                if price_response.get("follow_up_question"):
                    final_response += f"\n\n{price_response['follow_up_question']}"
            else:
                # Single GPT-4o call with all context
                final_response = await self._generate_unified_response(
                    message_text, state, context_analysis
                )
            
            # Add assistant message
            assistant_message = Message(
                role="assistant",
                content=final_response,
                timestamp=datetime.now().isoformat()
            )
            state.messages.append(assistant_message)
            
            # Update conversation phase if needed
            self._update_conversation_phase(state, message_text, final_response)
            
            return {
                "response": final_response,
                "conversation_id": state.conversation_id,
                "sales_phase": state.phase,
                "emotional_context": context_analysis
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "response": "Disculpa, hubo un problema procesando tu mensaje. ¿Podrías repetirlo?",
                "error": str(e)
            }
    
    def _quick_analyze_context(self, message_text: str, state: ConversationState) -> Dict[str, Any]:
        """
        Quick context analysis without external service calls.
        """
        text_lower = message_text.lower()
        
        # Detect price objection
        price_keywords = ["precio", "costo", "caro", "dinero", "pagar", "inversión", "presupuesto"]
        has_price_objection = any(keyword in text_lower for keyword in price_keywords)
        
        # Detect primary emotion
        emotion_keywords = {
            "frustrated": ["frustrado", "cansado", "agotado", "harto", "estresado"],
            "excited": ["emocionado", "entusiasmado", "motivado", "listo", "decidido"],
            "skeptical": ["dudo", "no creo", "escéptico", "no estoy seguro", "desconfío"],
            "anxious": ["preocupado", "ansioso", "nervioso", "miedo", "temor"],
            "hopeful": ["esperanza", "espero", "ojalá", "me gustaría", "quisiera"]
        }
        
        primary_emotion = "neutral"
        for emotion, keywords in emotion_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                primary_emotion = emotion
                break
        
        # Detect urgency
        urgency_keywords = ["urgente", "ya", "ahora", "rápido", "pronto", "inmediato"]
        has_urgency = any(keyword in text_lower for keyword in urgency_keywords)
        
        return {
            "has_price_objection": has_price_objection,
            "primary_emotion": primary_emotion,
            "has_urgency": has_urgency,
            "message_length": len(message_text),
            "conversation_length": len(state.messages)
        }
    
    async def _generate_unified_response(
        self,
        message_text: str,
        state: ConversationState,
        context_analysis: Dict[str, Any]
    ) -> str:
        """
        Generate response with single GPT-4o call.
        """
        # Build system prompt with context
        customer_age = state.customer_data.get('age', 35)
        age_range = "25-35" if customer_age < 35 else "35-45" if customer_age < 45 else "45-55" if customer_age < 55 else "55+"
        
        system_prompt = UNIFIED_SYSTEM_PROMPT.format(
            initial_score=state.context.get('initial_score', 75),
            age_range=age_range,
            initial_interests=['optimización', 'rendimiento'] if state.program_type == "PRIME" else ['bienestar', 'longevidad'],
            lead_source=state.context.get('lead_source', 'direct')
        )
        
        # Add emotional context to prompt
        if context_analysis["primary_emotion"] != "neutral":
            system_prompt += f"\n\nESTADO EMOCIONAL DETECTADO: {context_analysis['primary_emotion']}"
            system_prompt += "\nAJUSTA tu respuesta para conectar con este estado emocional."
        
        if context_analysis["has_urgency"]:
            system_prompt += "\n\nURGENCIA DETECTADA: El cliente muestra señales de urgencia."
            system_prompt += "\nSé más directo y orientado a la acción."
        
        # Get conversation history (last 5 messages for context)
        messages = [{"role": "system", "content": system_prompt}]
        for msg in state.messages[-5:]:
            messages.append({"role": msg.role, "content": msg.content})
        
        # Determine empathy context
        empathy_context = "general"
        if state.phase == "greeting":
            empathy_context = "greeting"
        elif context_analysis["primary_emotion"] in ["frustrated", "anxious"]:
            empathy_context = "emotional_moment"
        
        # Get optimized parameters
        model_params = EmpathyConfig.get_context_params(empathy_context)
        
        # Single API call
        response = await self.openai_client.create_chat_completion(
            messages=messages,
            **model_params
        )
        
        if response and response.get('choices'):
            return response['choices'][0]['message']['content']
        
        return "Gracias por compartir eso conmigo. ¿Podrías contarme más sobre tu situación?"
    
    def _update_conversation_phase(self, state: ConversationState, message: str, response: str):
        """
        Update conversation phase based on content.
        """
        # Simple phase detection
        if len(state.messages) <= 2:
            state.phase = "greeting"
        elif any(word in message.lower() for word in ["precio", "costo", "caro"]):
            state.phase = "objection_handling"
        elif any(word in response.lower() for word in ["empezar", "comenzar", "inscribir"]):
            state.phase = "closing"
        else:
            state.phase = "exploration"