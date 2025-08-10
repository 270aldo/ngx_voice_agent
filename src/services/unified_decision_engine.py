"""
Unified Decision Engine Service - Consolidated from multiple implementations.
Combines caching, optimization, and advanced strategies in a single, maintainable service.
"""

import asyncio
import hashlib
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .base_predictive_service import BasePredictiveService
from .advanced_decision_strategies import (
    AdvancedDecisionStrategies,
    ConversationContext,
    DecisionStrategy
)
from .cache.decision_cache import DecisionCacheLayer
from ..utils.metrics import track_ml_prediction
from .circuit_breaker_service import circuit_breaker

logger = logging.getLogger(__name__)


class OptimizationMode(Enum):
    """Optimization modes for the decision engine."""
    STANDARD = "standard"      # Balanced performance and accuracy
    FAST = "fast"             # Optimized for speed
    ACCURATE = "accurate"     # Optimized for accuracy
    CACHED = "cached"         # Maximum caching


@dataclass
class DecisionConfig:
    """Configuration for decision engine behavior."""
    enable_cache: bool = True
    cache_ttl: int = 300
    enable_circuit_breaker: bool = True
    optimization_mode: OptimizationMode = OptimizationMode.STANDARD
    timeout_seconds: float = 2.0
    enable_advanced_strategies: bool = True
    parallel_processing: bool = True
    max_retries: int = 3


class UnifiedDecisionEngine(BasePredictiveService):
    """
    Unified Decision Engine that combines:
    - Advanced decision strategies
    - Multi-layer caching
    - Circuit breaker protection
    - Performance optimization
    - Parallel processing
    """
    
    def __init__(
        self,
        conversion_predictor=None,
        objection_predictor=None,
        needs_predictor=None,
        config: Optional[DecisionConfig] = None
    ):
        """Initialize the unified decision engine."""
        super().__init__()
        
        # Configuration
        self.config = config or DecisionConfig()
        
        # Core services
        self._conversion_predictor = conversion_predictor
        self._objection_predictor = objection_predictor
        self._needs_predictor = needs_predictor
        
        # Advanced strategies
        if self.config.enable_advanced_strategies:
            self.strategies = AdvancedDecisionStrategies()
        else:
            self.strategies = None
        
        # Caching layer
        if self.config.enable_cache:
            self.cache = DecisionCacheLayer(
                ttl=self.config.cache_ttl,
                max_size=1000
            )
        else:
            self.cache = None
        
        # Metrics tracking
        self._call_count = 0
        self._cache_hits = 0
        self._cache_misses = 0
        
        logger.info(f"Unified Decision Engine initialized with config: {self.config}")
    
    @circuit_breaker(
        name="decision_engine",
        failure_threshold=5,
        recovery_timeout=30
    )
    async def make_decision(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a decision based on conversation state.
        
        This is the main entry point that delegates to appropriate strategies
        and optimizations based on configuration.
        """
        start_time = asyncio.get_event_loop().time()
        self._call_count += 1
        
        try:
            # Generate cache key if caching enabled
            cache_key = None
            if self.cache:
                cache_key = self._generate_cache_key(messages, customer_profile, context)
                cached_result = await self._get_cached_decision(cache_key)
                if cached_result:
                    self._cache_hits += 1
                    return cached_result
                self._cache_misses += 1
            
            # Execute decision logic based on optimization mode
            if self.config.optimization_mode == OptimizationMode.FAST:
                result = await self._make_fast_decision(messages, customer_profile, context)
            elif self.config.optimization_mode == OptimizationMode.ACCURATE:
                result = await self._make_accurate_decision(messages, customer_profile, context)
            else:
                result = await self._make_standard_decision(messages, customer_profile, context)
            
            # Cache result if enabled
            if self.cache and cache_key:
                await self._cache_decision(cache_key, result)
            
            # Track metrics
            duration = asyncio.get_event_loop().time() - start_time
            track_ml_prediction("decision_engine")
            
            return result
            
        except asyncio.TimeoutError:
            logger.error("Decision engine timeout")
            return self._get_timeout_fallback()
        except Exception as e:
            logger.error(f"Decision engine error: {e}")
            return self._get_error_fallback()
    
    async def _make_standard_decision(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Standard decision making with balanced performance."""
        # Parallel prediction if enabled
        if self.config.parallel_processing:
            predictions = await self._get_parallel_predictions(messages, customer_profile)
        else:
            predictions = await self._get_sequential_predictions(messages, customer_profile)
        
        # Use advanced strategies if enabled
        if self.strategies and self.config.enable_advanced_strategies:
            strategy_decision = await self._apply_advanced_strategy(
                messages, customer_profile, predictions
            )
            predictions["strategy"] = strategy_decision
        
        # Determine action based on predictions
        decision = self._determine_best_action(predictions, customer_profile)
        
        return {
            **decision,
            "predictions": predictions,
            "optimization_mode": self.config.optimization_mode.value,
            "cache_stats": {
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "hit_rate": self._cache_hits / max(1, self._call_count)
            }
        }
    
    async def _make_fast_decision(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Fast decision making with minimal processing."""
        # Only get conversion probability for speed
        try:
            conversion_prob = await asyncio.wait_for(
                self._get_conversion_probability(messages, customer_profile),
                timeout=self.config.timeout_seconds / 2
            )
        except asyncio.TimeoutError:
            conversion_prob = 0.5
        
        # Simple threshold-based decision
        if conversion_prob > 0.7:
            action = "close_deal"
            urgency = 8
        elif conversion_prob > 0.4:
            action = "nurture_lead"
            urgency = 5
        else:
            action = "qualify_further"
            urgency = 3
        
        return {
            "action": action,
            "confidence": 0.7,  # Lower confidence for fast decisions
            "urgency_level": urgency,
            "reasoning": "Fast decision based on conversion probability",
            "conversion_probability": conversion_prob,
            "optimization_mode": "fast"
        }
    
    async def _make_accurate_decision(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Accurate decision making with comprehensive analysis."""
        # Get all predictions with extended timeout
        predictions = await asyncio.wait_for(
            self._get_parallel_predictions(messages, customer_profile),
            timeout=self.config.timeout_seconds * 2
        )
        
        # Apply multiple strategies and compare
        if self.strategies:
            context_obj = self._build_conversation_context(messages, customer_profile, predictions)
            strategy_recommendations = self.strategies.get_multi_strategy_recommendation(
                context_obj, top_n=3
            )
            
            # Aggregate recommendations
            best_strategy, best_decision = self._aggregate_strategy_recommendations(
                strategy_recommendations
            )
            
            predictions["strategy"] = {
                "selected": best_strategy.value,
                "decision": best_decision.recommended_action,
                "confidence": best_decision.confidence,
                "alternatives": [
                    {"strategy": s.value, "action": d.recommended_action}
                    for s, d in strategy_recommendations[1:]
                ]
            }
        
        # Enhanced decision with multiple factors
        decision = self._determine_best_action_comprehensive(predictions, customer_profile)
        
        return {
            **decision,
            "predictions": predictions,
            "optimization_mode": "accurate",
            "analysis_depth": "comprehensive"
        }
    
    async def _get_parallel_predictions(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get all predictions in parallel for better performance."""
        tasks = []
        
        # Create prediction tasks
        if self._conversion_predictor:
            tasks.append(self._get_conversion_probability(messages, customer_profile))
        else:
            tasks.append(asyncio.create_task(asyncio.sleep(0, result=0.5)))
        
        if self._objection_predictor:
            tasks.append(self._get_objection_probability(messages, customer_profile))
        else:
            tasks.append(asyncio.create_task(asyncio.sleep(0, result=[])))
        
        if self._needs_predictor:
            tasks.append(self._get_needs_analysis(messages, customer_profile))
        else:
            tasks.append(asyncio.create_task(asyncio.sleep(0, result=[])))
        
        # Wait for all predictions
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        predictions = {
            "conversion_probability": results[0] if not isinstance(results[0], Exception) else 0.5,
            "objections": results[1] if not isinstance(results[1], Exception) else [],
            "needs": results[2] if not isinstance(results[2], Exception) else []
        }
        
        return predictions
    
    async def _get_sequential_predictions(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get predictions sequentially (fallback mode)."""
        predictions = {}
        
        try:
            predictions["conversion_probability"] = await self._get_conversion_probability(
                messages, customer_profile
            )
        except Exception as e:
            logger.error(f"Conversion prediction failed: {e}")
            predictions["conversion_probability"] = 0.5
        
        try:
            predictions["objections"] = await self._get_objection_probability(
                messages, customer_profile
            )
        except Exception as e:
            logger.error(f"Objection prediction failed: {e}")
            predictions["objections"] = []
        
        try:
            predictions["needs"] = await self._get_needs_analysis(
                messages, customer_profile
            )
        except Exception as e:
            logger.error(f"Needs analysis failed: {e}")
            predictions["needs"] = []
        
        return predictions
    
    async def _apply_advanced_strategy(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]],
        predictions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply advanced decision strategies."""
        # Build conversation context
        context = self._build_conversation_context(messages, customer_profile, predictions)
        
        # Select optimal strategy
        selected_strategy = self.strategies.select_optimal_strategy(context)
        
        # Execute strategy
        decision = self.strategies.execute_strategy(selected_strategy, context)
        
        return {
            "strategy": selected_strategy.value,
            "action": decision.recommended_action,
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
            "urgency": decision.urgency_level
        }
    
    def _build_conversation_context(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]],
        predictions: Dict[str, Any]
    ) -> ConversationContext:
        """Build context object for strategy evaluation."""
        # Calculate metrics
        sentiment = self._calculate_sentiment(messages)
        engagement = self._calculate_engagement(messages)
        objection_count = len(predictions.get("objections", []))
        
        # Detect features
        price_mentioned = any("precio" in msg.get("content", "").lower() for msg in messages)
        competitor_mentioned = any("competidor" in msg.get("content", "").lower() for msg in messages)
        
        return ConversationContext(
            conversation_id=customer_profile.get("conversation_id", "unknown"),
            message_count=len(messages),
            customer_sentiment=sentiment,
            engagement_score=engagement,
            objection_count=objection_count,
            price_mentioned=price_mentioned,
            competitor_mentioned=competitor_mentioned,
            decision_timeline=customer_profile.get("timeline", "unknown"),
            customer_profile=customer_profile or {},
            detected_needs=predictions.get("needs", []),
            conversion_probability=predictions.get("conversion_probability", 0.5),
            time_in_conversation=self._calculate_conversation_duration(messages)
        )
    
    def _determine_best_action(
        self,
        predictions: Dict[str, Any],
        customer_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Determine best action based on predictions (standard mode)."""
        conversion_prob = predictions.get("conversion_probability", 0.5)
        objections = predictions.get("objections", [])
        needs = predictions.get("needs", [])
        
        # Decision logic
        if conversion_prob > 0.8 and len(objections) == 0:
            return {
                "action": "close_deal",
                "confidence": 0.9,
                "urgency_level": 9,
                "reasoning": "High conversion probability with no objections"
            }
        elif conversion_prob > 0.6:
            if objections:
                return {
                    "action": "address_objections",
                    "confidence": 0.8,
                    "urgency_level": 7,
                    "reasoning": f"Good conversion potential but need to address: {objections[0]}"
                }
            else:
                return {
                    "action": "present_offer",
                    "confidence": 0.8,
                    "urgency_level": 8,
                    "reasoning": "Good conversion probability, time to present offer"
                }
        elif needs:
            return {
                "action": "explore_needs",
                "confidence": 0.7,
                "urgency_level": 5,
                "reasoning": f"Focus on understanding needs: {', '.join(needs[:2])}"
            }
        else:
            return {
                "action": "build_rapport",
                "confidence": 0.6,
                "urgency_level": 4,
                "reasoning": "Need to build stronger connection and trust"
            }
    
    def _determine_best_action_comprehensive(
        self,
        predictions: Dict[str, Any],
        customer_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Comprehensive action determination for accurate mode."""
        # Extract all relevant factors
        conversion_prob = predictions.get("conversion_probability", 0.5)
        objections = predictions.get("objections", [])
        needs = predictions.get("needs", [])
        strategy_decision = predictions.get("strategy", {})
        
        # Multi-factor scoring
        scores = {
            "close_deal": 0,
            "present_offer": 0,
            "address_objections": 0,
            "explore_needs": 0,
            "build_rapport": 0,
            "create_urgency": 0
        }
        
        # Score based on conversion probability
        if conversion_prob > 0.8:
            scores["close_deal"] += 0.4
            scores["create_urgency"] += 0.2
        elif conversion_prob > 0.6:
            scores["present_offer"] += 0.3
            scores["address_objections"] += 0.2
        else:
            scores["explore_needs"] += 0.3
            scores["build_rapport"] += 0.2
        
        # Adjust for objections
        if objections:
            scores["address_objections"] += 0.3 * len(objections)
            scores["close_deal"] -= 0.1 * len(objections)
        
        # Adjust for needs
        if needs:
            scores["explore_needs"] += 0.2 * len(needs)
            scores["present_offer"] += 0.1 * len(needs)
        
        # Incorporate strategy recommendation
        if strategy_decision:
            recommended_action = strategy_decision.get("action", "")
            if recommended_action in scores:
                scores[recommended_action] += 0.3
        
        # Select best action
        best_action = max(scores, key=scores.get)
        confidence = min(0.95, scores[best_action])
        
        # Determine urgency
        urgency_map = {
            "close_deal": 9,
            "create_urgency": 8,
            "present_offer": 7,
            "address_objections": 6,
            "explore_needs": 5,
            "build_rapport": 4
        }
        
        return {
            "action": best_action,
            "confidence": confidence,
            "urgency_level": urgency_map.get(best_action, 5),
            "reasoning": self._generate_reasoning(best_action, predictions, scores),
            "alternative_actions": self._get_alternative_actions(scores, best_action)
        }
    
    def _generate_reasoning(
        self,
        action: str,
        predictions: Dict[str, Any],
        scores: Dict[str, Any]
    ) -> str:
        """Generate reasoning for the decision."""
        reasons = []
        
        if action == "close_deal":
            reasons.append(f"High conversion probability ({predictions['conversion_probability']:.0%})")
            if not predictions.get("objections"):
                reasons.append("No significant objections detected")
        elif action == "address_objections":
            objections = predictions.get("objections", [])
            reasons.append(f"Need to address {len(objections)} objection(s)")
            if objections:
                reasons.append(f"Primary concern: {objections[0]}")
        elif action == "explore_needs":
            needs = predictions.get("needs", [])
            reasons.append(f"Identified {len(needs)} customer need(s)")
            if needs:
                reasons.append(f"Focus on: {', '.join(needs[:2])}")
        
        return "; ".join(reasons)
    
    def _get_alternative_actions(
        self,
        scores: Dict[str, Any],
        selected_action: str
    ) -> List[Dict[str, Any]]:
        """Get alternative actions ranked by score."""
        alternatives = []
        sorted_actions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        for action, score in sorted_actions[:3]:
            if action != selected_action:
                alternatives.append({
                    "action": action,
                    "score": score,
                    "confidence": min(0.95, score)
                })
        
        return alternatives
    
    def _aggregate_strategy_recommendations(
        self,
        recommendations: List[Tuple[DecisionStrategy, Any]]
    ) -> Tuple[DecisionStrategy, Any]:
        """Aggregate multiple strategy recommendations."""
        # For now, return the top recommendation
        # Could implement voting or weighted averaging in the future
        if recommendations:
            return recommendations[0]
        return DecisionStrategy.ADAPTIVE, None
    
    # Caching methods
    def _generate_cache_key(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Generate cache key for decision."""
        # Create a deterministic key from inputs
        key_data = {
            "messages": [(m.get("role"), m.get("content", "")[:100]) for m in messages[-5:]],
            "profile": customer_profile.get("id") if customer_profile else None,
            "context": context.get("session_id") if context else None
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def _get_cached_decision(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached decision if available."""
        if self.cache:
            return self.cache.get(cache_key)
        return None
    
    async def _cache_decision(self, cache_key: str, decision: Dict[str, Any]):
        """Cache decision result."""
        if self.cache:
            self.cache.set(cache_key, decision)
    
    # Helper methods
    def _calculate_sentiment(self, messages: List[Dict[str, Any]]) -> float:
        """Calculate overall sentiment from messages."""
        # Simplified sentiment calculation
        positive_words = ["genial", "excelente", "perfecto", "gracias", "bien"]
        negative_words = ["no", "problema", "dificil", "caro", "mal"]
        
        sentiment_sum = 0
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "").lower()
                positive_count = sum(1 for word in positive_words if word in content)
                negative_count = sum(1 for word in negative_words if word in content)
                sentiment_sum += positive_count - negative_count
        
        # Normalize to -1 to 1
        return max(-1, min(1, sentiment_sum / max(len(messages), 1)))
    
    def _calculate_engagement(self, messages: List[Dict[str, Any]]) -> float:
        """Calculate engagement score from messages."""
        if not messages:
            return 0.0
        
        # Factors: message length, question frequency, response time
        user_messages = [m for m in messages if m.get("role") == "user"]
        if not user_messages:
            return 0.0
        
        # Average message length (normalized)
        avg_length = sum(len(m.get("content", "")) for m in user_messages) / len(user_messages)
        length_score = min(1.0, avg_length / 100)
        
        # Question frequency
        question_count = sum(1 for m in user_messages if "?" in m.get("content", ""))
        question_score = min(1.0, question_count / len(user_messages))
        
        # Combine scores
        return (length_score + question_score) / 2
    
    def _calculate_conversation_duration(self, messages: List[Dict[str, Any]]) -> int:
        """Calculate conversation duration in seconds."""
        # Simplified: estimate 30 seconds per message exchange
        return len(messages) * 30
    
    # Fallback methods
    def _get_timeout_fallback(self) -> Dict[str, Any]:
        """Fallback response for timeout scenarios."""
        return {
            "action": "continue_conversation",
            "confidence": 0.5,
            "urgency_level": 5,
            "reasoning": "Decision timeout - continuing with safe default",
            "error": "timeout",
            "fallback": True
        }
    
    def _get_error_fallback(self) -> Dict[str, Any]:
        """Fallback response for error scenarios."""
        return {
            "action": "build_rapport",
            "confidence": 0.4,
            "urgency_level": 3,
            "reasoning": "Decision error - falling back to relationship building",
            "error": "processing_error",
            "fallback": True
        }
    
    # Prediction helper methods (implement actual logic based on your predictors)
    async def _get_conversion_probability(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]]
    ) -> float:
        """Get conversion probability from predictor."""
        if self._conversion_predictor:
            try:
                result = await self._conversion_predictor.predict_conversion(
                    conversation_id=customer_profile.get("conversation_id", ""),
                    messages=messages,
                    customer_profile=customer_profile
                )
                return result.get("probability", 0.5)
            except Exception as e:
                logger.error(f"Conversion prediction error: {e}")
        return 0.5
    
    async def _get_objection_probability(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Get objection predictions from predictor."""
        if self._objection_predictor:
            try:
                result = await self._objection_predictor.predict_objections(
                    conversation_id=customer_profile.get("conversation_id", ""),
                    messages=messages,
                    customer_profile=customer_profile
                )
                return result.get("objections", [])
            except Exception as e:
                logger.error(f"Objection prediction error: {e}")
        return []
    
    async def _get_needs_analysis(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Get needs analysis from predictor."""
        if self._needs_predictor:
            try:
                result = await self._needs_predictor.predict_needs(
                    conversation_id=customer_profile.get("conversation_id", ""),
                    messages=messages,
                    customer_profile=customer_profile
                )
                return result.get("needs", [])
            except Exception as e:
                logger.error(f"Needs prediction error: {e}")
        return []
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            "total_calls": self._call_count,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": self._cache_hits / max(1, self._call_count),
            "optimization_mode": self.config.optimization_mode.value,
            "features": {
                "caching": self.config.enable_cache,
                "circuit_breaker": self.config.enable_circuit_breaker,
                "advanced_strategies": self.config.enable_advanced_strategies,
                "parallel_processing": self.config.parallel_processing
            }
        }