"""
Advanced Decision Strategies for Decision Engine

Implements sophisticated decision-making strategies to optimize
conversation flow and maximize conversion rates.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np
from datetime import datetime


class DecisionStrategy(Enum):
    """Available decision strategies."""
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"
    ADAPTIVE = "adaptive"
    EMPATHETIC = "empathetic"
    VALUE_FOCUSED = "value_focused"
    URGENCY_BASED = "urgency_based"
    RELATIONSHIP_BUILDING = "relationship_building"


@dataclass
class ConversationContext:
    """Enhanced conversation context for decision making."""
    conversation_id: str
    message_count: int
    customer_sentiment: float  # -1 to 1
    engagement_score: float  # 0 to 1
    objection_count: int
    price_mentioned: bool
    competitor_mentioned: bool
    decision_timeline: Optional[str]
    customer_profile: Dict[str, Any]
    detected_needs: List[str]
    conversion_probability: float
    time_in_conversation: int  # seconds


@dataclass
class StrategyDecision:
    """Decision output from a strategy."""
    strategy_name: str
    recommended_action: str
    confidence: float
    reasoning: str
    fallback_action: Optional[str] = None
    urgency_level: int = 0  # 0-10


class AdvancedDecisionStrategies:
    """Advanced decision-making strategies for optimized conversations."""
    
    def __init__(self):
        self.strategy_weights = {
            DecisionStrategy.AGGRESSIVE: 1.2,
            DecisionStrategy.CONSERVATIVE: 1.1,
            DecisionStrategy.ADAPTIVE: 1.0,  # Reduced to avoid domination
            DecisionStrategy.EMPATHETIC: 1.3,
            DecisionStrategy.VALUE_FOCUSED: 1.4,
            DecisionStrategy.URGENCY_BASED: 1.3,
            DecisionStrategy.RELATIONSHIP_BUILDING: 1.1
        }
        
        self.decision_thresholds = {
            "low_engagement": 0.3,
            "high_engagement": 0.7,
            "low_sentiment": -0.3,
            "high_sentiment": 0.3,
            "early_conversation": 5,  # messages
            "late_conversation": 15,  # messages
            "quick_decision": 300,  # 5 minutes
            "long_decision": 900   # 15 minutes
        }
    
    def select_optimal_strategy(self, context: ConversationContext) -> DecisionStrategy:
        """Select the optimal strategy based on conversation context."""
        scores = {}
        
        for strategy in DecisionStrategy:
            score = self._calculate_strategy_score(strategy, context)
            scores[strategy] = score * self.strategy_weights[strategy]
        
        # Return strategy with highest score
        return max(scores, key=scores.get)
    
    def _calculate_strategy_score(
        self, 
        strategy: DecisionStrategy, 
        context: ConversationContext
    ) -> float:
        """Calculate fitness score for a strategy given context."""
        
        if strategy == DecisionStrategy.AGGRESSIVE:
            # Good for: high engagement, positive sentiment, late conversation
            score = 0.5
            if context.engagement_score > self.decision_thresholds["high_engagement"]:
                score += 0.3
            if context.customer_sentiment > self.decision_thresholds["high_sentiment"]:
                score += 0.2
            if context.message_count > self.decision_thresholds["late_conversation"]:
                score += 0.2
            if context.conversion_probability > 0.7:
                score += 0.3
            # Bonus for immediate timeline
            if context.decision_timeline == "immediate" and context.conversion_probability > 0.8:
                score += 0.3
            return min(score, 1.0)
        
        elif strategy == DecisionStrategy.CONSERVATIVE:
            # Good for: low engagement, negative sentiment, many objections
            score = 0.5
            if context.engagement_score < self.decision_thresholds["low_engagement"]:
                score += 0.3
            if context.customer_sentiment < self.decision_thresholds["low_sentiment"]:
                score += 0.3
            if context.objection_count > 2:
                score += 0.2
            if context.price_mentioned and context.conversion_probability < 0.3:
                score += 0.2
            return min(score, 1.0)
        
        elif strategy == DecisionStrategy.ADAPTIVE:
            # Good for: balanced situations without extreme indicators
            score = 0.4  # Lower base score
            
            # Only good when no extreme conditions exist
            if abs(context.customer_sentiment) < 0.5:
                score += 0.2
            if 0.3 < context.engagement_score < 0.7:
                score += 0.2
            if context.objection_count <= 2:
                score += 0.1
            if not context.price_mentioned and not context.competitor_mentioned:
                score += 0.1
            
            # Penalty for extreme situations (other strategies better)
            if context.conversion_probability > 0.8 or context.conversion_probability < 0.3:
                score -= 0.2
            if context.customer_sentiment > 0.7 or context.customer_sentiment < -0.5:
                score -= 0.2
            
            return max(0.0, min(score, 1.0))
        
        elif strategy == DecisionStrategy.EMPATHETIC:
            # Good for: negative sentiment, multiple objections, relationship building
            score = 0.4
            if context.customer_sentiment < 0:
                score += 0.4
            if context.objection_count > 1:
                score += 0.2
            if "support" in context.detected_needs or "help" in context.detected_needs:
                score += 0.3
            if context.time_in_conversation > self.decision_thresholds["long_decision"]:
                score += 0.1
            return min(score, 1.0)
        
        elif strategy == DecisionStrategy.VALUE_FOCUSED:
            # Good for: price concerns, ROI interest, business-minded customers
            score = 0.4
            if context.price_mentioned:
                score += 0.3
            if "roi" in context.detected_needs or "growth" in context.detected_needs:
                score += 0.4
            if context.customer_profile.get("business_type") in ["gym", "studio"]:
                score += 0.2
            if context.competitor_mentioned:
                score += 0.1
            return min(score, 1.0)
        
        elif strategy == DecisionStrategy.URGENCY_BASED:
            # Good for: quick decision timeline, high engagement, high conversion prob
            score = 0.3
            if context.decision_timeline == "immediate":
                score += 0.4
            if context.time_in_conversation < self.decision_thresholds["quick_decision"]:
                score += 0.2
            if context.engagement_score > self.decision_thresholds["high_engagement"]:
                score += 0.2
            # High conversion bonus
            if context.conversion_probability > 0.8:
                score += 0.3
            # End of month bonus (mock)
            if datetime.now().day > 25:
                score += 0.2
            return min(score, 1.0)
        
        elif strategy == DecisionStrategy.RELATIONSHIP_BUILDING:
            # Good for: early conversation, low engagement, long-term potential
            score = 0.5
            if context.message_count < self.decision_thresholds["early_conversation"]:
                score += 0.3
            if context.engagement_score < 0.5:
                score += 0.2
            if context.customer_profile.get("business_size") in ["large", "enterprise"]:
                score += 0.2
            return min(score, 1.0)
        
        return 0.5  # Default
    
    def execute_strategy(
        self, 
        strategy: DecisionStrategy, 
        context: ConversationContext
    ) -> StrategyDecision:
        """Execute the selected strategy and return decision."""
        
        if strategy == DecisionStrategy.AGGRESSIVE:
            return self._execute_aggressive_strategy(context)
        elif strategy == DecisionStrategy.CONSERVATIVE:
            return self._execute_conservative_strategy(context)
        elif strategy == DecisionStrategy.ADAPTIVE:
            return self._execute_adaptive_strategy(context)
        elif strategy == DecisionStrategy.EMPATHETIC:
            return self._execute_empathetic_strategy(context)
        elif strategy == DecisionStrategy.VALUE_FOCUSED:
            return self._execute_value_focused_strategy(context)
        elif strategy == DecisionStrategy.URGENCY_BASED:
            return self._execute_urgency_based_strategy(context)
        elif strategy == DecisionStrategy.RELATIONSHIP_BUILDING:
            return self._execute_relationship_building_strategy(context)
        
        # Fallback
        return StrategyDecision(
            strategy_name="default",
            recommended_action="continue_conversation",
            confidence=0.5,
            reasoning="No specific strategy matched"
        )
    
    def _execute_aggressive_strategy(self, context: ConversationContext) -> StrategyDecision:
        """Execute aggressive closing strategy."""
        if context.conversion_probability > 0.8:
            return StrategyDecision(
                strategy_name="aggressive",
                recommended_action="hard_close",
                confidence=0.9,
                reasoning="High conversion probability, time to close",
                urgency_level=8
            )
        elif context.conversion_probability > 0.6:
            return StrategyDecision(
                strategy_name="aggressive",
                recommended_action="trial_close",
                confidence=0.8,
                reasoning="Good engagement, test for close",
                fallback_action="handle_objection",
                urgency_level=6
            )
        else:
            return StrategyDecision(
                strategy_name="aggressive",
                recommended_action="create_urgency",
                confidence=0.7,
                reasoning="Need to increase urgency to close",
                urgency_level=7
            )
    
    def _execute_conservative_strategy(self, context: ConversationContext) -> StrategyDecision:
        """Execute conservative relationship-building strategy."""
        if context.objection_count > 2:
            return StrategyDecision(
                strategy_name="conservative",
                recommended_action="address_concerns",
                confidence=0.8,
                reasoning="Multiple objections need careful handling",
                urgency_level=3
            )
        elif context.customer_sentiment < 0:
            return StrategyDecision(
                strategy_name="conservative",
                recommended_action="build_rapport",
                confidence=0.7,
                reasoning="Negative sentiment requires relationship building",
                urgency_level=2
            )
        else:
            return StrategyDecision(
                strategy_name="conservative",
                recommended_action="educate_value",
                confidence=0.6,
                reasoning="Focus on education before pushing for close",
                urgency_level=4
            )
    
    def _execute_adaptive_strategy(self, context: ConversationContext) -> StrategyDecision:
        """Execute adaptive strategy based on multiple factors."""
        # Analyze conversation stage
        if context.message_count < 5:
            action = "discover_needs"
            urgency = 3
        elif context.message_count < 10:
            action = "present_solution"
            urgency = 5
        elif context.message_count < 15:
            action = "handle_objections"
            urgency = 6
        else:
            action = "close_or_followup"
            urgency = 8
        
        # Adjust based on sentiment
        if context.customer_sentiment < -0.5:
            action = "empathize_and_rebuild"
            urgency = max(2, urgency - 3)
        elif context.customer_sentiment > 0.5:
            urgency = min(10, urgency + 2)
        
        confidence = 0.7 + (context.engagement_score * 0.3)
        
        return StrategyDecision(
            strategy_name="adaptive",
            recommended_action=action,
            confidence=confidence,
            reasoning=f"Adaptive strategy for stage {context.message_count} with sentiment {context.customer_sentiment:.2f}",
            urgency_level=urgency
        )
    
    def _execute_empathetic_strategy(self, context: ConversationContext) -> StrategyDecision:
        """Execute empathetic strategy for emotional connection."""
        if context.customer_sentiment < -0.5:
            return StrategyDecision(
                strategy_name="empathetic",
                recommended_action="deep_empathy",
                confidence=0.8,
                reasoning="Customer needs emotional support",
                urgency_level=1
            )
        elif context.objection_count > 1:
            return StrategyDecision(
                strategy_name="empathetic",
                recommended_action="acknowledge_concerns",
                confidence=0.7,
                reasoning="Multiple concerns need empathetic acknowledgment",
                urgency_level=3
            )
        else:
            return StrategyDecision(
                strategy_name="empathetic",
                recommended_action="share_success_story",
                confidence=0.6,
                reasoning="Build connection through relatable stories",
                urgency_level=4
            )
    
    def _execute_value_focused_strategy(self, context: ConversationContext) -> StrategyDecision:
        """Execute value and ROI focused strategy."""
        if context.price_mentioned and context.conversion_probability < 0.5:
            return StrategyDecision(
                strategy_name="value_focused",
                recommended_action="demonstrate_roi",
                confidence=0.9,
                reasoning="Price concern needs ROI demonstration",
                urgency_level=6
            )
        elif context.competitor_mentioned:
            return StrategyDecision(
                strategy_name="value_focused",
                recommended_action="competitive_differentiation",
                confidence=0.8,
                reasoning="Highlight unique value vs competitors",
                urgency_level=7
            )
        else:
            return StrategyDecision(
                strategy_name="value_focused",
                recommended_action="quantify_benefits",
                confidence=0.7,
                reasoning="Show concrete value metrics",
                urgency_level=5
            )
    
    def _execute_urgency_based_strategy(self, context: ConversationContext) -> StrategyDecision:
        """Execute urgency-based strategy for quick decisions."""
        if context.decision_timeline == "immediate":
            return StrategyDecision(
                strategy_name="urgency_based",
                recommended_action="limited_time_offer",
                confidence=0.8,
                reasoning="Customer has immediate need",
                urgency_level=9
            )
        elif context.time_in_conversation < 300:  # Less than 5 minutes
            return StrategyDecision(
                strategy_name="urgency_based",
                recommended_action="fast_value_prop",
                confidence=0.7,
                reasoning="Quick conversation needs fast value delivery",
                urgency_level=8
            )
        else:
            return StrategyDecision(
                strategy_name="urgency_based",
                recommended_action="create_scarcity",
                confidence=0.6,
                reasoning="Create urgency through scarcity",
                urgency_level=7
            )
    
    def _execute_relationship_building_strategy(self, context: ConversationContext) -> StrategyDecision:
        """Execute long-term relationship building strategy."""
        if context.message_count < 3:
            return StrategyDecision(
                strategy_name="relationship_building",
                recommended_action="warm_welcome",
                confidence=0.8,
                reasoning="Early conversation needs warm approach",
                urgency_level=2
            )
        elif context.engagement_score < 0.3:
            return StrategyDecision(
                strategy_name="relationship_building",
                recommended_action="engage_with_questions",
                confidence=0.7,
                reasoning="Low engagement needs interactive approach",
                urgency_level=3
            )
        else:
            return StrategyDecision(
                strategy_name="relationship_building",
                recommended_action="build_trust",
                confidence=0.7,
                reasoning="Focus on trust before transaction",
                urgency_level=4
            )
    
    def get_multi_strategy_recommendation(
        self, 
        context: ConversationContext,
        top_n: int = 3
    ) -> List[Tuple[DecisionStrategy, StrategyDecision]]:
        """Get recommendations from multiple strategies for comparison."""
        recommendations = []
        
        # Calculate scores for all strategies
        strategy_scores = {}
        for strategy in DecisionStrategy:
            score = self._calculate_strategy_score(strategy, context)
            strategy_scores[strategy] = score * self.strategy_weights[strategy]
        
        # Get top N strategies
        top_strategies = sorted(
            strategy_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:top_n]
        
        # Execute each top strategy
        for strategy, score in top_strategies:
            decision = self.execute_strategy(strategy, context)
            recommendations.append((strategy, decision))
        
        return recommendations
    
    def adapt_strategy_weights(self, performance_data: Dict[str, float]):
        """Adapt strategy weights based on performance data."""
        for strategy in DecisionStrategy:
            if strategy.value in performance_data:
                # Increase weight for high-performing strategies
                performance = performance_data[strategy.value]
                if performance > 0.7:
                    self.strategy_weights[strategy] *= 1.1
                elif performance < 0.3:
                    self.strategy_weights[strategy] *= 0.9
                
                # Keep weights in reasonable range
                self.strategy_weights[strategy] = max(0.5, min(2.0, self.strategy_weights[strategy]))