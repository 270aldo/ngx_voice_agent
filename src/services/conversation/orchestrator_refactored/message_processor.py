"""
Message Processor

Processes incoming messages, analyzes intent, and determines appropriate responses.
Single responsibility: Message processing and analysis.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from src.models.conversation import Message, ConversationState
from src.services.intent_analysis_service import IntentAnalysisService
from src.services.enhanced_intent_analysis_service import EnhancedIntentAnalysisService
from src.services.nlp_integration_service import NLPIntegrationService
from src.services.objection_prediction_service import ObjectionPredictionService
from src.services.needs_prediction_service import NeedsPredictionService

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Processes messages and analyzes user intent."""
    
    def __init__(self):
        """Initialize the message processor with required services."""
        self.intent_analyzer = IntentAnalysisService()
        self.enhanced_intent_analyzer = EnhancedIntentAnalysisService()
        self.nlp_service = NLPIntegrationService()
        
        # ML prediction services
        self.objection_predictor = ObjectionPredictionService()
        self.needs_predictor = NeedsPredictionService()
        
        # Initialize services
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize all services."""
        try:
            # Initialize ML services with training if needed
            if not self.objection_predictor.model:
                self.objection_predictor.train_model()
            if not self.needs_predictor.model:
                self.needs_predictor.train_model()
        except Exception as e:
            logger.warning(f"Failed to initialize ML services: {e}")
    
    async def process_message(
        self,
        message: str,
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """
        Process an incoming message and analyze it.
        
        Args:
            message: The message content
            conversation_state: Current conversation state
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Basic intent analysis
            intent = await self._analyze_intent(message, conversation_state)
            
            # Enhanced NLP analysis
            nlp_analysis = await self._analyze_nlp(message, conversation_state)
            
            # Predict potential objections
            objection_prediction = await self._predict_objections(message, conversation_state)
            
            # Predict customer needs
            needs_prediction = await self._predict_needs(message, conversation_state)
            
            # Combine all analyses
            analysis = {
                "intent": intent,
                "nlp": nlp_analysis,
                "objection_likelihood": objection_prediction,
                "predicted_needs": needs_prediction,
                "sentiment": nlp_analysis.get("sentiment", "neutral"),
                "key_topics": nlp_analysis.get("topics", []),
                "requires_human": self._check_human_handoff(intent, nlp_analysis),
                "confidence": self._calculate_confidence(intent, nlp_analysis),
                "processed_at": datetime.utcnow().isoformat()
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "intent": {"type": "unknown", "confidence": 0.0},
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }
    
    async def _analyze_intent(
        self,
        message: str,
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Analyze message intent."""
        try:
            # Use enhanced analyzer if available
            if self.enhanced_intent_analyzer:
                result = await self.enhanced_intent_analyzer.analyze(
                    message,
                    conversation_state.context
                )
            else:
                result = await self.intent_analyzer.analyze(message)
            
            return {
                "type": result.get("intent", "unknown"),
                "confidence": result.get("confidence", 0.0),
                "entities": result.get("entities", []),
                "sub_intents": result.get("sub_intents", [])
            }
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            return {"type": "unknown", "confidence": 0.0}
    
    async def _analyze_nlp(
        self,
        message: str,
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Perform NLP analysis on the message."""
        try:
            if not self.nlp_service:
                return {}
            
            # Get conversation context
            context = self._get_conversation_context(conversation_state)
            
            # Perform NLP analysis
            result = await self.nlp_service.analyze_text(
                message,
                context=context
            )
            
            return {
                "sentiment": result.get("sentiment", "neutral"),
                "sentiment_score": result.get("sentiment_score", 0.0),
                "topics": result.get("topics", []),
                "entities": result.get("entities", []),
                "keywords": result.get("keywords", []),
                "language": result.get("language", "en")
            }
        except Exception as e:
            logger.error(f"NLP analysis failed: {e}")
            return {"sentiment": "neutral", "topics": []}
    
    async def _predict_objections(
        self,
        message: str,
        conversation_state: ConversationState
    ) -> float:
        """Predict likelihood of objections."""
        try:
            if not self.objection_predictor or not self.objection_predictor.model:
                return 0.0
            
            # Prepare features for prediction
            features = self._extract_features_for_objection(message, conversation_state)
            
            # Get prediction
            probability = self.objection_predictor.predict_objection_probability(features)
            
            return probability
        except Exception as e:
            logger.error(f"Objection prediction failed: {e}")
            return 0.0
    
    async def _predict_needs(
        self,
        message: str,
        conversation_state: ConversationState
    ) -> List[str]:
        """Predict customer needs from the message."""
        try:
            if not self.needs_predictor or not self.needs_predictor.model:
                return []
            
            # Prepare features for prediction
            features = self._extract_features_for_needs(message, conversation_state)
            
            # Get predictions
            needs = self.needs_predictor.predict_needs(features)
            
            return needs if isinstance(needs, list) else []
        except Exception as e:
            logger.error(f"Needs prediction failed: {e}")
            return []
    
    def _check_human_handoff(
        self,
        intent: Dict[str, Any],
        nlp_analysis: Dict[str, Any]
    ) -> bool:
        """Check if human handoff is required."""
        # Triggers for human handoff
        triggers = [
            intent.get("type") == "complaint",
            intent.get("type") == "technical_issue",
            intent.get("confidence", 1.0) < 0.3,
            nlp_analysis.get("sentiment") == "very_negative",
            nlp_analysis.get("sentiment_score", 0) < -0.7
        ]
        
        return any(triggers)
    
    def _calculate_confidence(
        self,
        intent: Dict[str, Any],
        nlp_analysis: Dict[str, Any]
    ) -> float:
        """Calculate overall confidence in the analysis."""
        intent_confidence = intent.get("confidence", 0.0)
        sentiment_confidence = abs(nlp_analysis.get("sentiment_score", 0.0))
        
        # Weighted average
        overall_confidence = (intent_confidence * 0.7 + sentiment_confidence * 0.3)
        
        return min(max(overall_confidence, 0.0), 1.0)
    
    def _get_conversation_context(
        self,
        conversation_state: ConversationState
    ) -> str:
        """Get conversation context for analysis."""
        # Get last few messages for context
        recent_messages = conversation_state.messages[-5:] if conversation_state.messages else []
        
        context_parts = []
        for msg in recent_messages:
            context_parts.append(f"{msg.role}: {msg.content}")
        
        return "\n".join(context_parts)
    
    def _extract_features_for_objection(
        self,
        message: str,
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Extract features for objection prediction."""
        return {
            "message_length": len(message),
            "question_marks": message.count("?"),
            "exclamation_marks": message.count("!"),
            "negative_words": self._count_negative_words(message),
            "conversation_duration": len(conversation_state.messages),
            "sales_phase": conversation_state.sales_phase or "discovery",
            "previous_objections": conversation_state.context.get("objection_count", 0)
        }
    
    def _extract_features_for_needs(
        self,
        message: str,
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Extract features for needs prediction."""
        return {
            "message": message,
            "customer_type": conversation_state.customer_data.customer_type if conversation_state.customer_data else "unknown",
            "conversation_phase": conversation_state.sales_phase or "discovery",
            "mentioned_keywords": self._extract_keywords(message),
            "context": conversation_state.context
        }
    
    def _count_negative_words(self, message: str) -> int:
        """Count negative words in the message."""
        negative_words = [
            "no", "not", "never", "cant", "won't", "don't",
            "expensive", "costly", "problem", "issue", "difficult"
        ]
        
        message_lower = message.lower()
        count = sum(1 for word in negative_words if word in message_lower)
        
        return count
    
    def _extract_keywords(self, message: str) -> List[str]:
        """Extract relevant keywords from the message."""
        keywords = []
        
        # Business-related keywords
        business_keywords = [
            "price", "cost", "feature", "benefit", "service",
            "support", "training", "implementation", "integration"
        ]
        
        message_lower = message.lower()
        for keyword in business_keywords:
            if keyword in message_lower:
                keywords.append(keyword)
        
        return keywords
    
    def validate_message(self, message: str) -> Tuple[bool, str]:
        """
        Validate an incoming message.
        
        Args:
            message: Message to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not message:
            return False, "Message cannot be empty"
        
        if len(message) > 4000:
            return False, "Message too long (max 4000 characters)"
        
        # Check for potential injection attacks
        dangerous_patterns = ["<script", "javascript:", "onclick=", "onerror="]
        message_lower = message.lower()
        
        for pattern in dangerous_patterns:
            if pattern in message_lower:
                return False, "Message contains potentially dangerous content"
        
        return True, ""