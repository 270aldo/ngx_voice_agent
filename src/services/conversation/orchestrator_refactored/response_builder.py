"""
Response Builder

Builds and formats responses based on analysis and business logic.
Single responsibility: Response generation and formatting.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import json

from src.models.conversation import ConversationState, Message
from src.services.personalization_service import PersonalizationService
from src.services.advanced_empathy_engine import AdvancedEmpathyEngine
from src.services.ultra_empathy_greetings import get_greeting_engine, GreetingContext
from src.services.ultra_empathy_price_handler import get_price_handler, PriceObjectionContext
from src.services.conversation.response_cache import response_cache
from src.services.response_precomputation_service import ResponsePrecomputationService
from src.config.empathy_config import EmpathyConfig

logger = logging.getLogger(__name__)


class ResponseBuilder:
    """Builds appropriate responses based on context and analysis."""
    
    def __init__(self):
        """Initialize response builder with required services."""
        self.personalization_service = None
        self.empathy_engine = None
        self.greeting_engine = None
        self.price_handler = None
        self.response_cache = response_cache
        self.precomputation_service = None
        self.empathy_config = EmpathyConfig()
        
        # Response templates
        self.templates = self._load_response_templates()
        
        # Initialize services
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize all response generation services."""
        try:
            self.personalization_service = PersonalizationService()
        except Exception as e:
            logger.warning(f"Failed to initialize PersonalizationService: {e}")
        
        try:
            self.empathy_engine = AdvancedEmpathyEngine()
        except Exception as e:
            logger.warning(f"Failed to initialize AdvancedEmpathyEngine: {e}")
        
        try:
            self.greeting_engine = get_greeting_engine()
        except Exception as e:
            logger.warning(f"Failed to initialize greeting engine: {e}")
        
        try:
            self.price_handler = get_price_handler()
        except Exception as e:
            logger.warning(f"Failed to initialize price handler: {e}")
        
        try:
            self.precomputation_service = ResponsePrecomputationService()
        except Exception as e:
            logger.warning(f"Failed to initialize ResponsePrecomputationService: {e}")
    
    async def build_response(
        self,
        analysis: Dict[str, Any],
        conversation_state: ConversationState,
        ai_response: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build a complete response based on analysis.
        
        Args:
            analysis: Message analysis results
            conversation_state: Current conversation state
            ai_response: Optional AI-generated response
            
        Returns:
            Complete response with text, audio, and metadata
        """
        try:
            # Check cache first
            cache_key = self._generate_cache_key(analysis, conversation_state)
            cached_response = await self._check_cache(cache_key)
            if cached_response:
                logger.info("Using cached response")
                return cached_response
            
            # Determine response type
            response_type = self._determine_response_type(analysis, conversation_state)
            
            # Build response based on type
            if response_type == "greeting":
                response = await self._build_greeting_response(conversation_state)
            elif response_type == "price_objection":
                response = await self._build_price_objection_response(analysis, conversation_state)
            elif response_type == "empathy":
                response = await self._build_empathy_response(analysis, conversation_state)
            elif response_type == "qualification":
                response = await self._build_qualification_response(analysis, conversation_state)
            elif response_type == "closing":
                response = await self._build_closing_response(conversation_state)
            elif response_type == "ai_generated":
                response = await self._build_ai_response(ai_response, conversation_state)
            else:
                response = await self._build_default_response(analysis, conversation_state)
            
            # Add personalization
            response = await self._personalize_response(response, conversation_state)
            
            # Add metadata
            response = self._add_metadata(response, analysis, response_type)
            
            # Cache the response
            await self._cache_response(cache_key, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error building response: {e}")
            return self._build_error_response(str(e))
    
    async def _build_greeting_response(
        self,
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Build a greeting response."""
        if self.greeting_engine:
            try:
                context = GreetingContext(
                    time_of_day=self._get_time_of_day(),
                    customer_name=conversation_state.customer_data.name if conversation_state.customer_data else None,
                    is_returning=conversation_state.context.get("is_returning", False)
                )
                
                greeting = await self.greeting_engine.generate_greeting(context)
                
                return {
                    "text": greeting.text,
                    "tone": greeting.tone,
                    "personalization_level": greeting.personalization_level,
                    "suggested_follow_up": greeting.suggested_follow_up
                }
            except Exception as e:
                logger.error(f"Failed to generate greeting: {e}")
        
        # Fallback greeting
        return {
            "text": "Hello! Welcome to NGX. How can I help you today?",
            "tone": "friendly",
            "personalization_level": "low"
        }
    
    async def _build_price_objection_response(
        self,
        analysis: Dict[str, Any],
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Build a price objection response."""
        if self.price_handler:
            try:
                context = PriceObjectionContext(
                    price_mentioned=analysis.get("price_mentioned"),
                    customer_tier=conversation_state.context.get("tier", "standard"),
                    conversation_stage=conversation_state.sales_phase
                )
                
                response = await self.price_handler.handle_price_objection(context)
                
                return {
                    "text": response.response_text,
                    "strategy": response.strategy_used,
                    "value_props": response.value_propositions,
                    "alternative_offers": response.alternative_offers
                }
            except Exception as e:
                logger.error(f"Failed to handle price objection: {e}")
        
        # Fallback response
        return {
            "text": "I understand price is important. Let me show you the value you'll receive...",
            "strategy": "value_focus"
        }
    
    async def _build_empathy_response(
        self,
        analysis: Dict[str, Any],
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Build an empathetic response."""
        if self.empathy_engine:
            try:
                emotional_state = analysis.get("nlp", {}).get("sentiment", "neutral")
                
                response = await self.empathy_engine.generate_empathetic_response(
                    emotional_state=emotional_state,
                    context=conversation_state.context,
                    customer_message=conversation_state.last_user_message
                )
                
                return {
                    "text": response.text,
                    "empathy_level": response.empathy_level,
                    "emotional_validation": response.emotional_validation,
                    "support_offered": response.support_offered
                }
            except Exception as e:
                logger.error(f"Failed to generate empathy response: {e}")
        
        # Fallback response
        return {
            "text": "I understand how you feel. Let's work together to find the best solution for you.",
            "empathy_level": "medium"
        }
    
    async def _build_qualification_response(
        self,
        analysis: Dict[str, Any],
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Build a qualification response."""
        questions = self._get_qualification_questions(conversation_state)
        
        return {
            "text": questions[0] if questions else "Can you tell me more about your needs?",
            "questions": questions,
            "qualification_stage": conversation_state.context.get("qualification_stage", "initial")
        }
    
    async def _build_closing_response(
        self,
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Build a closing response."""
        tier = conversation_state.context.get("tier", "standard")
        
        closing_templates = {
            "premium": "Based on everything we've discussed, I'd recommend our Elite package. Shall we get you started today?",
            "standard": "I think our Pro package would be perfect for you. Ready to begin?",
            "basic": "Our Essential package fits your needs well. Would you like to proceed?",
            "trial": "Why don't we start with a free trial so you can experience the value firsthand?"
        }
        
        return {
            "text": closing_templates.get(tier, closing_templates["standard"]),
            "call_to_action": "sign_up",
            "urgency_level": "medium",
            "incentive_offered": tier == "trial"
        }
    
    async def _build_ai_response(
        self,
        ai_response: Optional[str],
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Build response from AI-generated text."""
        if not ai_response:
            ai_response = "I'm here to help you. Could you please tell me more?"
        
        return {
            "text": ai_response,
            "source": "ai_generated",
            "model": "gpt-4-turbo-preview"
        }
    
    async def _build_default_response(
        self,
        analysis: Dict[str, Any],
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Build a default response."""
        intent = analysis.get("intent", {}).get("type", "unknown")
        
        default_responses = {
            "question": "That's a great question. Let me help you with that.",
            "concern": "I understand your concern. Let's address that together.",
            "interest": "I'm glad you're interested! Let me share more details.",
            "unknown": "I want to make sure I understand you correctly. Could you elaborate?"
        }
        
        return {
            "text": default_responses.get(intent, default_responses["unknown"]),
            "intent_matched": intent
        }
    
    async def _personalize_response(
        self,
        response: Dict[str, Any],
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Add personalization to the response."""
        if self.personalization_service and conversation_state.customer_data:
            try:
                personalized = await self.personalization_service.personalize(
                    response=response,
                    customer_data=conversation_state.customer_data.dict(),
                    context=conversation_state.context
                )
                
                response.update(personalized)
            except Exception as e:
                logger.error(f"Failed to personalize response: {e}")
        
        return response
    
    def _add_metadata(
        self,
        response: Dict[str, Any],
        analysis: Dict[str, Any],
        response_type: str
    ) -> Dict[str, Any]:
        """Add metadata to the response."""
        response["metadata"] = {
            "response_type": response_type,
            "confidence": analysis.get("confidence", 0.0),
            "intent": analysis.get("intent", {}).get("type"),
            "sentiment": analysis.get("nlp", {}).get("sentiment"),
            "generated_at": datetime.utcnow().isoformat(),
            "requires_human": analysis.get("requires_human", False)
        }
        
        return response
    
    def _determine_response_type(
        self,
        analysis: Dict[str, Any],
        conversation_state: ConversationState
    ) -> str:
        """Determine the type of response needed."""
        # Check for specific triggers
        if len(conversation_state.messages) == 0:
            return "greeting"
        
        intent = analysis.get("intent", {}).get("type", "")
        
        if "price" in intent or "cost" in intent:
            return "price_objection"
        
        if analysis.get("nlp", {}).get("sentiment") in ["negative", "very_negative"]:
            return "empathy"
        
        if conversation_state.sales_phase == "qualification":
            return "qualification"
        
        if conversation_state.sales_phase == "closing":
            return "closing"
        
        if analysis.get("ai_response"):
            return "ai_generated"
        
        return "default"
    
    def _get_qualification_questions(
        self,
        conversation_state: ConversationState
    ) -> List[str]:
        """Get appropriate qualification questions."""
        stage = conversation_state.context.get("qualification_stage", "initial")
        
        questions = {
            "initial": [
                "What brings you to NGX today?",
                "What are your main goals?",
                "How many clients do you currently work with?"
            ],
            "needs": [
                "What challenges are you facing in your business?",
                "What would success look like for you?",
                "What's your timeline for implementing a solution?"
            ],
            "budget": [
                "What's your budget range for this investment?",
                "How do you typically evaluate ROI?",
                "Are you the decision maker for this purchase?"
            ]
        }
        
        return questions.get(stage, questions["initial"])
    
    def _get_time_of_day(self) -> str:
        """Get current time of day."""
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"
    
    def _generate_cache_key(
        self,
        analysis: Dict[str, Any],
        conversation_state: ConversationState
    ) -> str:
        """Generate cache key for response."""
        key_parts = [
            analysis.get("intent", {}).get("type", "unknown"),
            conversation_state.sales_phase or "discovery",
            conversation_state.context.get("tier", "standard"),
            str(len(conversation_state.messages))
        ]
        
        return ":".join(key_parts)
    
    async def _check_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Check if response is cached."""
        if self.response_cache:
            try:
                cached = await self.response_cache.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.debug(f"Cache check failed: {e}")
        
        return None
    
    async def _cache_response(
        self,
        cache_key: str,
        response: Dict[str, Any]
    ) -> None:
        """Cache the response."""
        if self.response_cache:
            try:
                await self.response_cache.set(
                    cache_key,
                    json.dumps(response),
                    ttl=300  # 5 minutes
                )
            except Exception as e:
                logger.debug(f"Failed to cache response: {e}")
    
    def _build_error_response(self, error_message: str) -> Dict[str, Any]:
        """Build an error response."""
        return {
            "text": "I apologize, but I'm having trouble processing that. Let me connect you with someone who can help.",
            "error": error_message,
            "requires_human": True,
            "metadata": {
                "response_type": "error",
                "generated_at": datetime.utcnow().isoformat()
            }
        }
    
    def _load_response_templates(self) -> Dict[str, str]:
        """Load response templates."""
        return {
            "greeting": "Hello! Welcome to NGX. I'm here to help you transform your fitness business.",
            "qualification": "To better understand how I can help, could you tell me about your current challenges?",
            "value_prop": "NGX helps fitness professionals like you save 20+ hours per week while scaling your business.",
            "objection_handle": "I understand your concern. Many of our successful clients had the same question initially.",
            "closing": "Based on what you've shared, I believe NGX is perfect for you. Shall we get started?",
            "follow_up": "I'll follow up with you shortly with more information.",
            "transfer": "Let me connect you with one of our specialists who can better assist you."
        }