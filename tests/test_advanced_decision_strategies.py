#!/usr/bin/env python3
"""
Test Suite for Advanced Decision Strategies

Validates that the advanced decision strategies work correctly
and improve conversation outcomes.
"""

import asyncio
import pytest
from typing import Dict, List, Any
from datetime import datetime
import json
import sys
import os

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.advanced_decision_strategies import (
    AdvancedDecisionStrategies,
    ConversationContext,
    DecisionStrategy,
    StrategyDecision
)
from src.services.enhanced_decision_engine_service import EnhancedDecisionEngineService


class TestAdvancedStrategies:
    """Test suite for advanced decision strategies."""
    
    @pytest.fixture
    def strategies(self):
        """Create strategies instance."""
        return AdvancedDecisionStrategies()
    
    @pytest.fixture
    def engine(self):
        """Create enhanced decision engine."""
        return EnhancedDecisionEngineService()
    
    def test_strategy_selection_aggressive(self, strategies):
        """Test aggressive strategy selection for high-conversion scenarios."""
        context = ConversationContext(
            conversation_id="test_001",
            message_count=20,
            customer_sentiment=0.8,
            engagement_score=0.9,
            objection_count=0,
            price_mentioned=True,
            competitor_mentioned=False,
            decision_timeline="immediate",
            customer_profile={"business_type": "gym"},
            detected_needs=["growth", "retention"],
            conversion_probability=0.85,
            time_in_conversation=600
        )
        
        selected = strategies.select_optimal_strategy(context)
        assert selected == DecisionStrategy.AGGRESSIVE
        
        decision = strategies.execute_strategy(selected, context)
        assert decision.recommended_action == "hard_close"
        assert decision.confidence >= 0.8
        assert decision.urgency_level >= 7
    
    def test_strategy_selection_conservative(self, strategies):
        """Test conservative strategy for difficult scenarios."""
        context = ConversationContext(
            conversation_id="test_002",
            message_count=15,
            customer_sentiment=-0.5,
            engagement_score=0.2,
            objection_count=4,
            price_mentioned=True,
            competitor_mentioned=True,
            decision_timeline=None,
            customer_profile={"business_type": "trainer"},
            detected_needs=["cost_reduction"],
            conversion_probability=0.2,
            time_in_conversation=900
        )
        
        selected = strategies.select_optimal_strategy(context)
        assert selected in [DecisionStrategy.CONSERVATIVE, DecisionStrategy.EMPATHETIC]
        
        decision = strategies.execute_strategy(DecisionStrategy.CONSERVATIVE, context)
        assert decision.recommended_action == "address_concerns"
        assert decision.urgency_level <= 4
    
    def test_strategy_selection_value_focused(self, strategies):
        """Test value-focused strategy for price-sensitive customers."""
        context = ConversationContext(
            conversation_id="test_003",
            message_count=10,
            customer_sentiment=0.0,
            engagement_score=0.6,
            objection_count=1,
            price_mentioned=True,
            competitor_mentioned=True,
            decision_timeline="short_term",
            customer_profile={"business_type": "studio"},
            detected_needs=["roi", "growth"],
            conversion_probability=0.5,
            time_in_conversation=400
        )
        
        selected = strategies.select_optimal_strategy(context)
        # Should favor value-focused or adaptive
        assert selected in [DecisionStrategy.VALUE_FOCUSED, DecisionStrategy.ADAPTIVE]
        
        decision = strategies.execute_strategy(DecisionStrategy.VALUE_FOCUSED, context)
        assert decision.recommended_action in ["demonstrate_roi", "competitive_differentiation"]
    
    def test_adaptive_strategy_stages(self, strategies):
        """Test adaptive strategy adjusts to conversation stages."""
        # Early stage
        early_context = ConversationContext(
            conversation_id="test_004",
            message_count=3,
            customer_sentiment=0.0,
            engagement_score=0.5,
            objection_count=0,
            price_mentioned=False,
            competitor_mentioned=False,
            decision_timeline=None,
            customer_profile={},
            detected_needs=[],
            conversion_probability=0.5,
            time_in_conversation=60
        )
        
        decision = strategies.execute_strategy(DecisionStrategy.ADAPTIVE, early_context)
        assert decision.recommended_action == "discover_needs"
        
        # Middle stage
        early_context.message_count = 8
        decision = strategies.execute_strategy(DecisionStrategy.ADAPTIVE, early_context)
        assert decision.recommended_action == "present_solution"
        
        # Late stage
        early_context.message_count = 18
        decision = strategies.execute_strategy(DecisionStrategy.ADAPTIVE, early_context)
        assert decision.recommended_action == "close_or_followup"
    
    def test_empathetic_strategy_negative_sentiment(self, strategies):
        """Test empathetic strategy handles negative sentiment."""
        context = ConversationContext(
            conversation_id="test_005",
            message_count=7,
            customer_sentiment=-0.8,
            engagement_score=0.4,
            objection_count=2,
            price_mentioned=False,
            competitor_mentioned=False,
            decision_timeline=None,
            customer_profile={},
            detected_needs=["support", "help"],
            conversion_probability=0.3,
            time_in_conversation=300
        )
        
        decision = strategies.execute_strategy(DecisionStrategy.EMPATHETIC, context)
        assert decision.recommended_action == "deep_empathy"
        assert decision.urgency_level <= 3  # Low urgency for empathy
    
    def test_urgency_strategy_immediate_need(self, strategies):
        """Test urgency strategy for immediate decisions."""
        context = ConversationContext(
            conversation_id="test_006",
            message_count=5,
            customer_sentiment=0.3,
            engagement_score=0.8,
            objection_count=0,
            price_mentioned=False,
            competitor_mentioned=False,
            decision_timeline="immediate",
            customer_profile={"business_type": "gym"},
            detected_needs=["urgent_solution"],
            conversion_probability=0.7,
            time_in_conversation=200
        )
        
        decision = strategies.execute_strategy(DecisionStrategy.URGENCY_BASED, context)
        assert decision.recommended_action in ["limited_time_offer", "fast_value_prop"]
        assert decision.urgency_level >= 7
    
    def test_multi_strategy_recommendation(self, strategies):
        """Test getting recommendations from multiple strategies."""
        context = ConversationContext(
            conversation_id="test_007",
            message_count=12,
            customer_sentiment=0.2,
            engagement_score=0.7,
            objection_count=1,
            price_mentioned=True,
            competitor_mentioned=False,
            decision_timeline="short_term",
            customer_profile={"business_type": "studio"},
            detected_needs=["growth", "efficiency"],
            conversion_probability=0.6,
            time_in_conversation=500
        )
        
        recommendations = strategies.get_multi_strategy_recommendation(context, top_n=3)
        
        assert len(recommendations) == 3
        assert all(isinstance(r[0], DecisionStrategy) for r in recommendations)
        assert all(isinstance(r[1], StrategyDecision) for r in recommendations)
        
        # Check variety in recommendations
        actions = [r[1].recommended_action for r in recommendations]
        assert len(set(actions)) >= 2  # At least 2 different actions
    
    def test_strategy_weight_adaptation(self, strategies):
        """Test strategy weight adaptation based on performance."""
        initial_weights = strategies.strategy_weights.copy()
        
        # Simulate performance data
        performance_data = {
            "aggressive": 0.85,  # High performance
            "conservative": 0.25,  # Low performance
            "adaptive": 0.65,  # Medium performance
        }
        
        strategies.adapt_strategy_weights(performance_data)
        
        # Check weights adjusted correctly
        assert strategies.strategy_weights[DecisionStrategy.AGGRESSIVE] > initial_weights[DecisionStrategy.AGGRESSIVE]
        assert strategies.strategy_weights[DecisionStrategy.CONSERVATIVE] < initial_weights[DecisionStrategy.CONSERVATIVE]
        
        # Check weights stay in bounds
        for weight in strategies.strategy_weights.values():
            assert 0.5 <= weight <= 2.0


class TestEnhancedDecisionEngine:
    """Test enhanced decision engine integration."""
    
    @pytest.mark.asyncio
    async def test_enhanced_decision_with_strategies(self):
        """Test enhanced decision engine uses strategies correctly."""
        engine = EnhancedDecisionEngineService()
        
        # High conversion scenario
        conversation_history = [
            {"role": "user", "content": "I need to improve my gym immediately"},
            {"role": "assistant", "content": "I can help with that..."},
            {"role": "user", "content": "What's the ROI on your premium service?"},
            {"role": "assistant", "content": "Our clients see 300% ROI..."},
            {"role": "user", "content": "That sounds great! How do we start?"}
        ]
        
        user_profile = {
            "business_type": "gym",
            "size": "medium",
            "location": "urban"
        }
        
        objectives = {
            "growth": 0.9,
            "efficiency": 0.7,
            "cost_reduction": 0.3
        }
        
        decision = await engine.get_optimal_action(
            "I'm ready to move forward",
            conversation_history,
            user_profile,
            objectives
        )
        
        # Check decision includes strategy
        assert "strategy" in decision
        assert decision["strategy"]["name"] in ["aggressive", "urgency_based", "adaptive"]
        assert decision["strategy"]["confidence"] >= 0.6
        
        # Check next actions are strategic
        assert len(decision["next_actions"]) > 0
        assert decision["next_actions"][0]["priority"] == "high"
    
    @pytest.mark.asyncio
    async def test_strategy_performance_tracking(self):
        """Test strategy performance is tracked correctly."""
        engine = EnhancedDecisionEngineService()
        
        # Simulate conversation
        conversation_id = "test_conv_001"
        conversation_history = [{"conversation_id": conversation_id}]
        
        decision = await engine.get_optimal_action(
            "I'm interested",
            conversation_history,
            {},
            {}
        )
        
        # Record outcome
        await engine.record_conversation_outcome(
            conversation_id,
            "converted",
            {"revenue": 1000}
        )
        
        # Check performance tracked
        strategy_used = decision.get("strategy", {}).get("name")
        if strategy_used:
            assert strategy_used in engine.strategy_performance
            assert len(engine.strategy_performance[strategy_used]) > 0
            assert engine.strategy_performance[strategy_used][0] == 1.0  # Converted = 1.0


async def run_strategy_validation():
    """Run comprehensive strategy validation."""
    print("\n" + "="*80)
    print("🎯 ADVANCED DECISION STRATEGIES VALIDATION")
    print("="*80)
    
    # Initialize components
    strategies = AdvancedDecisionStrategies()
    engine = EnhancedDecisionEngineService()
    
    # Test scenarios
    scenarios = [
        {
            "name": "High Conversion Opportunity",
            "context": ConversationContext(
                conversation_id="val_001",
                message_count=15,
                customer_sentiment=0.7,
                engagement_score=0.8,
                objection_count=0,
                price_mentioned=True,
                competitor_mentioned=False,
                decision_timeline="immediate",
                customer_profile={"business_type": "gym", "size": "large"},
                detected_needs=["growth", "retention", "efficiency"],
                conversion_probability=0.8,
                time_in_conversation=600
            ),
            "expected_strategies": [DecisionStrategy.AGGRESSIVE, DecisionStrategy.URGENCY_BASED]
        },
        {
            "name": "Difficult Customer",
            "context": ConversationContext(
                conversation_id="val_002",
                message_count=20,
                customer_sentiment=-0.6,
                engagement_score=0.3,
                objection_count=5,
                price_mentioned=True,
                competitor_mentioned=True,
                decision_timeline="long_term",
                customer_profile={"business_type": "trainer"},
                detected_needs=["cost_reduction"],
                conversion_probability=0.2,
                time_in_conversation=1200
            ),
            "expected_strategies": [DecisionStrategy.EMPATHETIC, DecisionStrategy.CONSERVATIVE]
        },
        {
            "name": "Value Seeker",
            "context": ConversationContext(
                conversation_id="val_003",
                message_count=8,
                customer_sentiment=0.0,
                engagement_score=0.6,
                objection_count=2,
                price_mentioned=True,
                competitor_mentioned=True,
                decision_timeline="short_term",
                customer_profile={"business_type": "studio"},
                detected_needs=["roi", "comparison"],
                conversion_probability=0.5,
                time_in_conversation=400
            ),
            "expected_strategies": [DecisionStrategy.VALUE_FOCUSED, DecisionStrategy.ADAPTIVE]
        }
    ]
    
    results = []
    
    for scenario in scenarios:
        print(f"\n📋 Testing: {scenario['name']}")
        
        # Get optimal strategy
        selected_strategy = strategies.select_optimal_strategy(scenario["context"])
        print(f"  Selected Strategy: {selected_strategy.value}")
        
        # Execute strategy
        decision = strategies.execute_strategy(selected_strategy, scenario["context"])
        print(f"  Recommended Action: {decision.recommended_action}")
        print(f"  Confidence: {decision.confidence:.2f}")
        print(f"  Urgency Level: {decision.urgency_level}/10")
        
        # Check if matches expected
        success = selected_strategy in scenario["expected_strategies"]
        print(f"  Validation: {'✅ PASS' if success else '❌ FAIL'}")
        
        results.append({
            "scenario": scenario["name"],
            "selected": selected_strategy.value,
            "expected": [s.value for s in scenario["expected_strategies"]],
            "decision": decision.recommended_action,
            "confidence": decision.confidence,
            "success": success
        })
    
    # Test multi-strategy
    print("\n📊 Testing Multi-Strategy Recommendations")
    context = scenarios[0]["context"]  # Use high conversion scenario
    recommendations = strategies.get_multi_strategy_recommendation(context, top_n=3)
    
    print("  Top 3 Strategy Recommendations:")
    for i, (strategy, decision) in enumerate(recommendations, 1):
        print(f"  {i}. {strategy.value}: {decision.recommended_action} (conf: {decision.confidence:.2f})")
    
    # Summary
    successful = sum(1 for r in results if r["success"])
    total = len(results)
    
    print("\n" + "="*80)
    print("📊 VALIDATION SUMMARY")
    print("="*80)
    print(f"Total Scenarios: {total}")
    print(f"Successful: {successful}")
    print(f"Success Rate: {(successful/total)*100:.0f}%")
    
    # Save results
    report = {
        "timestamp": datetime.now().isoformat(),
        "scenarios_tested": total,
        "successful": successful,
        "success_rate": successful/total,
        "detailed_results": results,
        "multi_strategy_test": {
            "context": "high_conversion",
            "recommendations": [
                {
                    "strategy": rec[0].value,
                    "action": rec[1].recommended_action,
                    "confidence": rec[1].confidence
                }
                for rec in recommendations
            ]
        }
    }
    
    with open("advanced_strategies_validation.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Report saved to: advanced_strategies_validation.json")
    
    if successful == total:
        print("\n✅ ALL STRATEGY TESTS PASSED")
        print("   Advanced decision strategies are working correctly!")
    else:
        print("\n⚠️  SOME STRATEGY TESTS FAILED")
        print("   Review the detailed results for improvements needed")


if __name__ == "__main__":
    # Run tests
    asyncio.run(run_strategy_validation())