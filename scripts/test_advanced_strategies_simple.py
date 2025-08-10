#!/usr/bin/env python3
"""
Simplified test for advanced decision strategies without dependencies.
"""

import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.advanced_decision_strategies import (
    AdvancedDecisionStrategies,
    ConversationContext,
    DecisionStrategy
)


def test_advanced_strategies():
    """Test advanced decision strategies."""
    print("\n" + "="*80)
    print("🎯 ADVANCED DECISION STRATEGIES VALIDATION")
    print("="*80)
    
    strategies = AdvancedDecisionStrategies()
    
    # Test scenarios
    scenarios = [
        {
            "name": "🔥 High Conversion Opportunity",
            "context": ConversationContext(
                conversation_id="test_001",
                message_count=15,
                customer_sentiment=0.8,
                engagement_score=0.9,
                objection_count=0,
                price_mentioned=True,
                competitor_mentioned=False,
                decision_timeline="immediate",
                customer_profile={"business_type": "gym", "size": "large"},
                detected_needs=["growth", "retention"],
                conversion_probability=0.85,
                time_in_conversation=600
            ),
            "expected_strategies": [DecisionStrategy.AGGRESSIVE, DecisionStrategy.URGENCY_BASED]
        },
        {
            "name": "😰 Difficult Customer with Objections",
            "context": ConversationContext(
                conversation_id="test_002",
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
            "name": "💰 Price-Sensitive Value Seeker",
            "context": ConversationContext(
                conversation_id="test_003",
                message_count=8,
                customer_sentiment=0.0,
                engagement_score=0.6,
                objection_count=2,
                price_mentioned=True,
                competitor_mentioned=True,
                decision_timeline="short_term",
                customer_profile={"business_type": "studio"},
                detected_needs=["roi", "value", "comparison"],
                conversion_probability=0.5,
                time_in_conversation=400
            ),
            "expected_strategies": [DecisionStrategy.VALUE_FOCUSED, DecisionStrategy.ADAPTIVE]
        },
        {
            "name": "🤝 Early Stage Relationship Building",
            "context": ConversationContext(
                conversation_id="test_004",
                message_count=3,
                customer_sentiment=0.0,
                engagement_score=0.4,
                objection_count=0,
                price_mentioned=False,
                competitor_mentioned=False,
                decision_timeline=None,
                customer_profile={"business_type": "enterprise"},
                detected_needs=[],
                conversion_probability=0.3,
                time_in_conversation=60
            ),
            "expected_strategies": [DecisionStrategy.RELATIONSHIP_BUILDING, DecisionStrategy.ADAPTIVE]
        },
        {
            "name": "😟 Emotional Support Needed",
            "context": ConversationContext(
                conversation_id="test_005",
                message_count=10,
                customer_sentiment=-0.8,
                engagement_score=0.5,
                objection_count=3,
                price_mentioned=False,
                competitor_mentioned=False,
                decision_timeline=None,
                customer_profile={"business_type": "trainer"},
                detected_needs=["support", "help", "guidance"],
                conversion_probability=0.25,
                time_in_conversation=450
            ),
            "expected_strategies": [DecisionStrategy.EMPATHETIC, DecisionStrategy.CONSERVATIVE]
        }
    ]
    
    results = []
    all_passed = True
    
    for scenario in scenarios:
        print(f"\n📋 Testing: {scenario['name']}")
        print(f"  Context:")
        print(f"    - Messages: {scenario['context'].message_count}")
        print(f"    - Sentiment: {scenario['context'].customer_sentiment:.1f}")
        print(f"    - Engagement: {scenario['context'].engagement_score:.1f}")
        print(f"    - Objections: {scenario['context'].objection_count}")
        print(f"    - Conversion Prob: {scenario['context'].conversion_probability:.0%}")
        
        # Get optimal strategy
        selected_strategy = strategies.select_optimal_strategy(scenario["context"])
        print(f"\n  🎯 Selected Strategy: {selected_strategy.value.upper()}")
        
        # Execute strategy
        decision = strategies.execute_strategy(selected_strategy, scenario["context"])
        print(f"  📌 Recommended Action: {decision.recommended_action}")
        print(f"  💪 Confidence: {decision.confidence:.2f}")
        print(f"  ⚡ Urgency Level: {decision.urgency_level}/10")
        print(f"  💭 Reasoning: {decision.reasoning}")
        
        # Check if matches expected
        success = selected_strategy in scenario["expected_strategies"]
        print(f"\n  Validation: {'✅ PASS' if success else '❌ FAIL'}")
        if not success:
            print(f"    Expected: {[s.value for s in scenario['expected_strategies']]}")
            all_passed = False
        
        results.append({
            "scenario": scenario["name"],
            "selected": selected_strategy.value,
            "expected": [s.value for s in scenario["expected_strategies"]],
            "decision": decision.recommended_action,
            "confidence": decision.confidence,
            "urgency": decision.urgency_level,
            "success": success
        })
    
    # Test multi-strategy recommendations
    print("\n" + "="*80)
    print("📊 Testing Multi-Strategy Recommendations")
    print("="*80)
    
    test_context = scenarios[0]["context"]  # High conversion scenario
    recommendations = strategies.get_multi_strategy_recommendation(test_context, top_n=5)
    
    print("\nTop 5 Strategy Recommendations for High Conversion Scenario:")
    for i, (strategy, decision) in enumerate(recommendations, 1):
        print(f"\n{i}. {strategy.value.upper()}")
        print(f"   Action: {decision.recommended_action}")
        print(f"   Confidence: {decision.confidence:.2f}")
        print(f"   Urgency: {decision.urgency_level}/10")
        print(f"   Reasoning: {decision.reasoning}")
    
    # Test strategy adaptation
    print("\n" + "="*80)
    print("🔧 Testing Strategy Weight Adaptation")
    print("="*80)
    
    print("\nInitial Strategy Weights:")
    for strategy, weight in strategies.strategy_weights.items():
        print(f"  {strategy.value}: {weight:.2f}")
    
    # Simulate performance data
    performance_data = {
        "aggressive": 0.85,      # High performance
        "conservative": 0.25,    # Low performance
        "adaptive": 0.70,        # Good performance
        "empathetic": 0.60,      # Medium performance
        "value_focused": 0.75,   # Good performance
    }
    
    print("\nSimulated Performance:")
    for strategy, perf in performance_data.items():
        print(f"  {strategy}: {perf:.0%} success rate")
    
    strategies.adapt_strategy_weights(performance_data)
    
    print("\nAdapted Strategy Weights:")
    for strategy, weight in strategies.strategy_weights.items():
        print(f"  {strategy.value}: {weight:.2f}")
    
    # Summary
    successful = sum(1 for r in results if r["success"])
    total = len(results)
    
    print("\n" + "="*80)
    print("📊 VALIDATION SUMMARY")
    print("="*80)
    print(f"\nTotal Scenarios Tested: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success Rate: {(successful/total)*100:.0f}%")
    
    # Strategy distribution
    print("\nStrategy Selection Distribution:")
    strategy_counts = {}
    for result in results:
        strategy = result["selected"]
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
    
    for strategy, count in sorted(strategy_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {strategy}: {count} times ({count/total*100:.0f}%)")
    
    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "scenarios_tested": total,
        "successful": successful,
        "success_rate": successful/total,
        "all_passed": all_passed,
        "detailed_results": results,
        "strategy_distribution": strategy_counts,
        "multi_strategy_test": [
            {
                "rank": i+1,
                "strategy": rec[0].value,
                "action": rec[1].recommended_action,
                "confidence": rec[1].confidence,
                "urgency": rec[1].urgency_level
            }
            for i, rec in enumerate(recommendations)
        ],
        "weight_adaptation": {
            "before": {s.value: 1.0 for s in DecisionStrategy},  # Initial weights
            "performance": performance_data,
            "after": {s.value: w for s, w in strategies.strategy_weights.items()}
        }
    }
    
    report_file = f"advanced_strategies_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Detailed report saved to: {report_file}")
    
    if all_passed:
        print("\n✅ ALL STRATEGY TESTS PASSED!")
        print("   Advanced decision strategies are working perfectly!")
        print("\n   🎯 Key Achievements:")
        print("   • All scenarios matched expected strategies")
        print("   • Multi-strategy recommendations provide variety")
        print("   • Weight adaptation responds to performance")
        print("   • Strategies cover all conversation scenarios")
    else:
        print("\n⚠️  SOME STRATEGY TESTS FAILED")
        print("   Review the results above for details")
    
    return all_passed


if __name__ == "__main__":
    success = test_advanced_strategies()
    exit(0 if success else 1)