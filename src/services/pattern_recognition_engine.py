"""
Pattern Recognition Engine for NGX Voice Sales Agent.

This service detects patterns in conversations to improve sales performance
and provide actionable insights.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import asyncio
from collections import defaultdict, Counter

from src.integrations.supabase.resilient_client import resilient_supabase_client as supabase_client

logger = logging.getLogger(__name__)


class PatternType:
    """Types of patterns to detect."""
    CONVERSATION_FLOW = "conversation_flow"
    OBJECTION_SEQUENCE = "objection_sequence"
    CONVERSION_PATH = "conversion_path"
    DROPOUT_TRIGGER = "dropout_trigger"
    ENGAGEMENT_PATTERN = "engagement_pattern"
    EMOTIONAL_TRANSITION = "emotional_transition"
    PRICE_SENSITIVITY = "price_sensitivity"
    CLOSING_EFFECTIVENESS = "closing_effectiveness"


class PatternRecognitionEngine:
    """
    Engine for detecting and analyzing patterns in conversations.
    """
    
    def __init__(self):
        """Initialize the pattern recognition engine."""
        self.supabase = supabase_client
        self._pattern_cache = {}
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the engine and load existing patterns."""
        if self._initialized:
            return
            
        try:
            # Load active patterns from database
            patterns = await self.supabase.select(
                table="pattern_recognitions",
                filters={"is_active": True},
                order_by="confidence_score",
                order_direction="desc"
            )
            
            # Cache patterns by type
            for pattern in patterns:
                pattern_type = pattern["pattern_type"]
                if pattern_type not in self._pattern_cache:
                    self._pattern_cache[pattern_type] = []
                self._pattern_cache[pattern_type].append(pattern)
            
            self._initialized = True
            logger.info(f"Pattern Recognition Engine initialized with {len(patterns)} active patterns")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pattern Recognition Engine: {e}")
            # Continue without cached patterns
            self._initialized = True
    
    async def detect_patterns(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Detect patterns in a conversation.
        
        Args:
            conversation_id: Conversation identifier
            messages: Conversation messages
            context: Conversation context
            
        Returns:
            List of detected patterns
        """
        detected_patterns = []
        
        try:
            # Run pattern detection for each type
            detection_tasks = [
                self._detect_conversation_flow(messages, context),
                self._detect_objection_sequence(messages, context),
                self._detect_conversion_path(messages, context),
                self._detect_dropout_triggers(messages, context),
                self._detect_engagement_patterns(messages, context),
                self._detect_emotional_transitions(messages, context),
                self._detect_price_sensitivity(messages, context),
                self._detect_closing_effectiveness(messages, context)
            ]
            
            # Run all detection tasks concurrently
            results = await asyncio.gather(*detection_tasks, return_exceptions=True)
            
            # Collect valid patterns
            for result in results:
                if isinstance(result, list):
                    detected_patterns.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Pattern detection error: {result}")
            
            # Record detected patterns
            if detected_patterns:
                await self._record_patterns(conversation_id, detected_patterns)
            
            return detected_patterns
            
        except Exception as e:
            logger.error(f"Error detecting patterns: {e}")
            return []
    
    async def _detect_conversation_flow(
        self,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect conversation flow patterns."""
        patterns = []
        
        # Analyze message sequence
        if len(messages) >= 3:
            # Extract conversation phases
            phases = []
            for i in range(0, len(messages), 2):  # Every user-assistant pair
                if i + 1 < len(messages):
                    user_msg = messages[i].get("content", "").lower()
                    assistant_msg = messages[i + 1].get("content", "").lower()
                    
                    # Identify phase
                    if any(word in user_msg for word in ["hola", "buenos", "buen"]):
                        phases.append("greeting")
                    elif any(word in user_msg for word in ["precio", "costo", "caro"]):
                        phases.append("price_inquiry")
                    elif any(word in user_msg for word in ["como", "funciona", "que es"]):
                        phases.append("information_seeking")
                    elif any(word in user_msg for word in ["si", "quiero", "empezar"]):
                        phases.append("interest_expression")
            
            # Identify flow pattern
            flow_key = "->".join(phases[:5])  # First 5 phases
            
            if len(phases) >= 3:
                patterns.append({
                    "type": PatternType.CONVERSATION_FLOW,
                    "pattern": flow_key,
                    "confidence": 0.8,
                    "data": {
                        "phases": phases,
                        "message_count": len(messages),
                        "context": context
                    }
                })
        
        return patterns
    
    async def _detect_objection_sequence(
        self,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect objection sequence patterns."""
        patterns = []
        objections = []
        
        # Find all objections in conversation
        objection_keywords = {
            "price": ["caro", "precio", "costo", "presupuesto", "economico"],
            "time": ["tiempo", "ocupado", "luego", "después"],
            "trust": ["seguro", "confiable", "garantía", "referencias"],
            "need": ["no necesito", "ya tengo", "estoy bien"]
        }
        
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "").lower()
                for obj_type, keywords in objection_keywords.items():
                    if any(kw in content for kw in keywords):
                        objections.append(obj_type)
                        break
        
        if len(objections) >= 2:
            # Create objection sequence pattern
            sequence = "->".join(objections[:3])
            patterns.append({
                "type": PatternType.OBJECTION_SEQUENCE,
                "pattern": sequence,
                "confidence": 0.75,
                "data": {
                    "objections": objections,
                    "resolved": context.get("conversion_achieved", False)
                }
            })
        
        return patterns
    
    async def _detect_conversion_path(
        self,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect successful conversion paths."""
        patterns = []
        
        # Only analyze successful conversions
        if context.get("conversion_achieved") or context.get("tier_selected"):
            # Extract key moments
            key_moments = []
            
            for i, msg in enumerate(messages):
                if msg.get("role") == "user":
                    content = msg.get("content", "").lower()
                    
                    if any(word in content for word in ["interesa", "quiero", "si"]):
                        key_moments.append(("interest", i))
                    elif any(word in content for word in ["precio", "costo"]):
                        key_moments.append(("price_inquiry", i))
                    elif any(word in content for word in ["empezar", "comenzar", "iniciar"]):
                        key_moments.append(("commitment", i))
            
            if key_moments:
                path = "->".join([moment[0] for moment in key_moments])
                patterns.append({
                    "type": PatternType.CONVERSION_PATH,
                    "pattern": path,
                    "confidence": 0.9,
                    "data": {
                        "tier_selected": context.get("tier_selected"),
                        "conversion_value": context.get("conversion_value"),
                        "message_indices": [m[1] for m in key_moments]
                    }
                })
        
        return patterns
    
    async def _detect_dropout_triggers(
        self,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect patterns that lead to conversation dropout."""
        patterns = []
        
        # Check if conversation ended without conversion
        if not context.get("conversion_achieved") and len(messages) > 4:
            # Find potential dropout triggers
            last_user_messages = [m for m in messages[-4:] if m.get("role") == "user"]
            
            if last_user_messages:
                last_msg = last_user_messages[-1].get("content", "").lower()
                
                # Common dropout triggers
                dropout_triggers = {
                    "price_shock": ["muy caro", "demasiado", "no puedo pagar"],
                    "lost_interest": ["no gracias", "ya veré", "lo pensaré"],
                    "competitor_mention": ["otro", "alternativa", "comparar"],
                    "confusion": ["no entiendo", "confuso", "complicado"]
                }
                
                for trigger_type, keywords in dropout_triggers.items():
                    if any(kw in last_msg for kw in keywords):
                        patterns.append({
                            "type": PatternType.DROPOUT_TRIGGER,
                            "pattern": trigger_type,
                            "confidence": 0.7,
                            "data": {
                                "trigger_message": last_msg,
                                "message_index": len(messages) - 1,
                                "conversation_phase": context.get("phase", "unknown")
                            }
                        })
                        break
        
        return patterns
    
    async def _detect_engagement_patterns(
        self,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect user engagement patterns."""
        patterns = []
        
        # Analyze message lengths and frequency
        user_messages = [m for m in messages if m.get("role") == "user"]
        
        if len(user_messages) >= 3:
            # Calculate engagement metrics
            avg_length = sum(len(m.get("content", "")) for m in user_messages) / len(user_messages)
            question_count = sum(1 for m in user_messages if "?" in m.get("content", ""))
            
            # Determine engagement level
            if avg_length > 50 and question_count >= 2:
                engagement_level = "high"
            elif avg_length > 20 and question_count >= 1:
                engagement_level = "medium"
            else:
                engagement_level = "low"
            
            patterns.append({
                "type": PatternType.ENGAGEMENT_PATTERN,
                "pattern": engagement_level,
                "confidence": 0.85,
                "data": {
                    "avg_message_length": avg_length,
                    "question_count": question_count,
                    "message_count": len(user_messages),
                    "conversion_correlation": context.get("conversion_achieved", False)
                }
            })
        
        return patterns
    
    async def _detect_emotional_transitions(
        self,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect emotional state transitions."""
        patterns = []
        
        # Simple emotion detection based on keywords
        emotion_keywords = {
            "positive": ["genial", "excelente", "perfecto", "me gusta", "increíble"],
            "negative": ["no", "mal", "caro", "difícil", "complicado"],
            "neutral": ["ok", "bien", "entiendo", "claro"],
            "interested": ["interesa", "quiero saber", "cuéntame", "dime más"],
            "skeptical": ["seguro", "verdad", "realmente", "duda"]
        }
        
        emotions = []
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "").lower()
                detected_emotion = "neutral"
                
                for emotion, keywords in emotion_keywords.items():
                    if any(kw in content for kw in keywords):
                        detected_emotion = emotion
                        break
                
                emotions.append(detected_emotion)
        
        # Detect transitions
        if len(emotions) >= 2:
            transitions = []
            for i in range(1, len(emotions)):
                if emotions[i] != emotions[i-1]:
                    transitions.append(f"{emotions[i-1]}->{emotions[i]}")
            
            if transitions:
                pattern_key = "|".join(transitions[:3])  # First 3 transitions
                patterns.append({
                    "type": PatternType.EMOTIONAL_TRANSITION,
                    "pattern": pattern_key,
                    "confidence": 0.7,
                    "data": {
                        "emotions": emotions,
                        "transitions": transitions,
                        "final_emotion": emotions[-1] if emotions else "neutral"
                    }
                })
        
        return patterns
    
    async def _detect_price_sensitivity(
        self,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect price sensitivity patterns."""
        patterns = []
        
        # Count price-related mentions
        price_mentions = 0
        price_concerns = []
        
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "").lower()
                if any(word in content for word in ["precio", "costo", "caro", "barato", "economico", "presupuesto", "$"]):
                    price_mentions += 1
                    
                    # Classify concern level
                    if any(word in content for word in ["muy caro", "demasiado", "no puedo"]):
                        price_concerns.append("high")
                    elif any(word in content for word in ["caro", "elevado", "mucho"]):
                        price_concerns.append("medium")
                    else:
                        price_concerns.append("low")
        
        if price_mentions > 0:
            # Determine sensitivity level
            if price_mentions >= 3 or "high" in price_concerns:
                sensitivity = "high"
            elif price_mentions >= 2 or "medium" in price_concerns:
                sensitivity = "medium"
            else:
                sensitivity = "low"
            
            patterns.append({
                "type": PatternType.PRICE_SENSITIVITY,
                "pattern": sensitivity,
                "confidence": 0.8,
                "data": {
                    "price_mentions": price_mentions,
                    "concern_levels": price_concerns,
                    "tier_selected": context.get("tier_selected"),
                    "converted": context.get("conversion_achieved", False)
                }
            })
        
        return patterns
    
    async def _detect_closing_effectiveness(
        self,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect closing technique effectiveness patterns."""
        patterns = []
        
        # Find closing attempts
        closing_keywords = ["empezar", "comenzar", "iniciar", "contratar", "adquirir", "siguiente paso"]
        closing_attempts = []
        
        for i, msg in enumerate(messages):
            if msg.get("role") == "assistant":
                content = msg.get("content", "").lower()
                if any(kw in content for kw in closing_keywords):
                    # Check user response
                    if i + 1 < len(messages):
                        user_response = messages[i + 1].get("content", "").lower()
                        
                        # Classify response
                        if any(word in user_response for word in ["si", "vamos", "empezamos", "acepto"]):
                            response_type = "positive"
                        elif any(word in user_response for word in ["no", "todavía", "pensar", "luego"]):
                            response_type = "negative"
                        else:
                            response_type = "neutral"
                        
                        closing_attempts.append({
                            "attempt_index": i,
                            "response_type": response_type,
                            "technique": self._identify_closing_technique(content)
                        })
        
        if closing_attempts:
            # Analyze effectiveness
            success_rate = sum(1 for a in closing_attempts if a["response_type"] == "positive") / len(closing_attempts)
            
            patterns.append({
                "type": PatternType.CLOSING_EFFECTIVENESS,
                "pattern": f"attempts_{len(closing_attempts)}_success_{success_rate:.1f}",
                "confidence": 0.85,
                "data": {
                    "attempts": closing_attempts,
                    "success_rate": success_rate,
                    "final_outcome": context.get("conversion_achieved", False)
                }
            })
        
        return patterns
    
    def _identify_closing_technique(self, content: str) -> str:
        """Identify the closing technique used."""
        techniques = {
            "assumptive": ["siguiente paso", "cuando empezamos", "para comenzar"],
            "urgency": ["oferta", "tiempo limitado", "últimos cupos"],
            "choice": ["cuál prefieres", "qué opción", "elige"],
            "soft": ["cuando estés listo", "sin presión", "tómate tu tiempo"]
        }
        
        for technique, keywords in techniques.items():
            if any(kw in content for kw in keywords):
                return technique
        
        return "direct"
    
    async def _record_patterns(
        self,
        conversation_id: str,
        patterns: List[Dict[str, Any]]
    ) -> None:
        """Record detected patterns in the database."""
        try:
            # Track patterns in ml_tracking_events
            for pattern in patterns:
                event_data = {
                    "event_type": "pattern_detected",
                    "event_name": f"{pattern['type']}_{pattern['pattern']}",
                    "conversation_id": conversation_id,
                    "event_data": {
                        "pattern": pattern,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                await self.supabase.insert(
                    table="ml_tracking_events",
                    data=event_data
                )
            
            # Update pattern recognition statistics
            for pattern in patterns:
                # Check if pattern exists
                existing = await self.supabase.select(
                    table="pattern_recognitions",
                    filters={
                        "pattern_type": pattern["type"],
                        "pattern_name": pattern["pattern"]
                    },
                    limit=1
                )
                
                if existing:
                    # Update existing pattern
                    pattern_id = existing[0]["id"]
                    await self.supabase.update(
                        table="pattern_recognitions",
                        data={
                            "occurrences": existing[0]["occurrences"] + 1,
                            "confidence_score": (existing[0]["confidence_score"] + pattern["confidence"]) / 2,
                            "last_seen": datetime.now().isoformat()
                        },
                        filters={"id": pattern_id}
                    )
                else:
                    # Create new pattern
                    await self.supabase.insert(
                        table="pattern_recognitions",
                        data={
                            "pattern_type": pattern["type"],
                            "pattern_name": pattern["pattern"],
                            "description": f"Auto-detected {pattern['type']} pattern",
                            "pattern_data": pattern["data"],
                            "confidence_score": pattern["confidence"],
                            "occurrences": 1,
                            "is_active": True
                        }
                    )
            
            logger.info(f"Recorded {len(patterns)} patterns for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error recording patterns: {e}")
    
    async def get_pattern_insights(
        self,
        pattern_type: Optional[str] = None,
        min_confidence: float = 0.7,
        min_occurrences: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get insights from detected patterns.
        
        Args:
            pattern_type: Filter by pattern type
            min_confidence: Minimum confidence score
            min_occurrences: Minimum number of occurrences
            
        Returns:
            List of pattern insights
        """
        try:
            filters = {
                "is_active": True,
                "confidence_score": {">=": min_confidence},
                "occurrences": {">=": min_occurrences}
            }
            
            if pattern_type:
                filters["pattern_type"] = pattern_type
            
            patterns = await self.supabase.select(
                table="pattern_recognitions",
                filters=filters,
                order_by="effectiveness_score",
                order_direction="desc",
                limit=20
            )
            
            # Generate insights
            insights = []
            for pattern in patterns:
                insight = {
                    "pattern": pattern,
                    "recommendation": self._generate_recommendation(pattern),
                    "impact_score": pattern["effectiveness_score"] * pattern["confidence_score"]
                }
                insights.append(insight)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting pattern insights: {e}")
            return []
    
    def _generate_recommendation(self, pattern: Dict[str, Any]) -> str:
        """Generate actionable recommendation from pattern."""
        pattern_type = pattern["pattern_type"]
        pattern_name = pattern["pattern_name"]
        
        recommendations = {
            PatternType.CONVERSION_PATH: f"Use the '{pattern_name}' conversation flow more often - it has {pattern['effectiveness_score']:.0%} effectiveness",
            PatternType.DROPOUT_TRIGGER: f"Avoid or better handle '{pattern_name}' - it causes {pattern['occurrences']} dropouts",
            PatternType.OBJECTION_SEQUENCE: f"Prepare specific responses for the '{pattern_name}' objection sequence",
            PatternType.ENGAGEMENT_PATTERN: f"'{pattern_name}' engagement correlates with {pattern['effectiveness_score']:.0%} conversion rate",
            PatternType.EMOTIONAL_TRANSITION: f"The emotional transition '{pattern_name}' appears in {pattern['occurrences']} conversations",
            PatternType.PRICE_SENSITIVITY: f"Customers with '{pattern_name}' price sensitivity convert at {pattern['effectiveness_score']:.0%} rate",
            PatternType.CLOSING_EFFECTIVENESS: f"The '{pattern_name}' pattern shows closing technique performance"
        }
        
        return recommendations.get(
            pattern_type,
            f"Pattern '{pattern_name}' detected {pattern['occurrences']} times with {pattern['confidence_score']:.0%} confidence"
        )


# Singleton instance
pattern_recognition_engine = PatternRecognitionEngine()