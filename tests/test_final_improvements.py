#!/usr/bin/env python3
"""
Final test to verify all improvements:
1. No repetitive phrases
2. Better performance with caching
3. High empathy scores
"""
import asyncio
import time
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

from src.services.conversation.orchestrator import ConversationOrchestrator
from src.services.conversation.response_cache import response_cache
from src.models.conversation import CustomerData, ConversationState

# Simulated GPT-4 quality evaluator
def evaluate_response_quality(response: str, context: str) -> dict:
    """Simulate GPT-4 quality evaluation."""
    quality_metrics = {
        "empathy_score": 0,
        "personalization_score": 0,
        "clarity_score": 0,
        "sales_effectiveness": 0,
        "overall_score": 0,
        "issues": []
    }
    
    # Check for empathy indicators
    empathy_words = ["entiendo", "comprendo", "reconozco", "valoro", "aprecio", "respeto"]
    empathy_count = sum(1 for word in empathy_words if word in response.lower())
    quality_metrics["empathy_score"] = min(10, 7 + empathy_count)
    
    # Check for personalization
    if "carlos" in response.lower() or "tu" in response.lower():
        quality_metrics["personalization_score"] = 8
    else:
        quality_metrics["personalization_score"] = 5
    
    # Check clarity
    if len(response) > 100 and len(response) < 500 and "?" in response:
        quality_metrics["clarity_score"] = 9
    else:
        quality_metrics["clarity_score"] = 7
    
    # Check sales effectiveness
    if any(word in response.lower() for word in ["ngx", "programa", "beneficio", "valor"]):
        quality_metrics["sales_effectiveness"] = 8
    else:
        quality_metrics["sales_effectiveness"] = 6
    
    # Check for known issues
    repetitive_patterns = [
        "Tu cautela inicial es exactamente",
        "Comprendo que tu tiempo es extremadamente valioso",
        "Entiendo tu punto"
    ]
    
    for pattern in repetitive_patterns:
        if pattern in response:
            quality_metrics["issues"].append(f"Repetitive phrase: {pattern}")
    
    # Calculate overall score
    quality_metrics["overall_score"] = round(
        (quality_metrics["empathy_score"] + 
         quality_metrics["personalization_score"] + 
         quality_metrics["clarity_score"] + 
         quality_metrics["sales_effectiveness"]) / 4, 1
    )
    
    return quality_metrics

async def test_final_improvements():
    """Test all improvements together."""
    print("🚀 FINAL SYSTEM TEST - NGX Voice Sales Agent")
    print("=" * 60)
    
    # Clear cache for fresh test
    response_cache.clear()
    
    # Mock database methods
    with patch.object(ConversationOrchestrator, '_save_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_get_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_register_session', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_start_ml_conversation_tracking', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_update_ml_conversation_metrics', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_calculate_personalized_roi', new_callable=AsyncMock):
        
        orchestrator = ConversationOrchestrator()
        await orchestrator.initialize()
        
        # Mock ROI calculation
        orchestrator._calculate_personalized_roi.return_value = {
            "projected_roi_percentage": 500,
            "annual_value": 5000,
            "payback_period_months": 2.4
        }
        
        # Test scenarios
        test_scenarios = [
            {
                "name": "Exhausted Professional",
                "messages": [
                    "Estoy agotado, trabajo 14 horas al día",
                    "¿Cómo puede ayudarme NGX?",
                    "¿Cuánto cuesta el programa?",
                    "Me preocupa no tener tiempo"
                ]
            },
            {
                "name": "Skeptical Mother",
                "messages": [
                    "Soy madre de 3 hijos y estoy siempre cansada",
                    "He probado muchas cosas que no funcionan",
                    "¿Qué hace diferente a NGX?",
                    "¿Hay alguna garantía?"
                ]
            }
        ]
        
        all_results = []
        
        for scenario in test_scenarios:
            print(f"\n\n📋 SCENARIO: {scenario['name']}")
            print("-" * 60)
            
            # Create fresh state for each scenario
            state = ConversationState(
                conversation_id=f"test-{scenario['name'].lower().replace(' ', '-')}",
                customer_data={
                    "id": "test_123",
                    "name": "Carlos" if "Professional" in scenario['name'] else "María",
                    "email": "test@test.com",
                    "age": 35
                },
                messages=[],
                context={},
                program_type="PRIME",
                phase="greeting"
            )
            
            orchestrator._get_conversation_state.return_value = state
            orchestrator._start_ml_conversation_tracking.return_value = {"experiments_assigned": []}
            
            scenario_results = {
                "name": scenario["name"],
                "conversations": [],
                "metrics": {
                    "avg_response_time": 0,
                    "avg_quality_score": 0,
                    "total_issues": 0,
                    "cache_hits": 0
                }
            }
            
            response_times = []
            quality_scores = []
            
            for i, message in enumerate(scenario["messages"]):
                print(f"\n💬 Message {i+1}: {message}")
                
                # Measure response time
                start_time = time.time()
                result = await orchestrator.process_message(state.conversation_id, message)
                response_time = time.time() - start_time
                response_times.append(response_time)
                
                # Evaluate quality
                quality = evaluate_response_quality(result["response"], message)
                quality_scores.append(quality["overall_score"])
                
                # Display results
                print(f"⏱️  Response time: {response_time:.2f}s")
                print(f"🤖 Response: {result['response'][:100]}...")
                print(f"📊 Quality Score: {quality['overall_score']}/10")
                
                if quality["issues"]:
                    print(f"⚠️  Issues: {quality['issues']}")
                    scenario_results["metrics"]["total_issues"] += len(quality["issues"])
                else:
                    print("✅ No issues detected")
                
                # Store conversation
                scenario_results["conversations"].append({
                    "message": message,
                    "response": result["response"],
                    "response_time": response_time,
                    "quality": quality
                })
            
            # Calculate scenario metrics
            scenario_results["metrics"]["avg_response_time"] = sum(response_times) / len(response_times)
            scenario_results["metrics"]["avg_quality_score"] = sum(quality_scores) / len(quality_scores)
            
            all_results.append(scenario_results)
        
        # Test cache effectiveness
        print("\n\n🔄 CACHE EFFECTIVENESS TEST")
        print("-" * 60)
        
        # Send same messages again
        cache_times = []
        for message in ["¿Cuánto cuesta el programa?", "Estoy agotado, trabajo 14 horas al día"]:
            start_time = time.time()
            result = await orchestrator.process_message("test-cache", message)
            cache_time = time.time() - start_time
            cache_times.append(cache_time)
            print(f"💬 {message[:30]}... - ⏱️ {cache_time:.2f}s")
        
        # Summary
        print("\n\n📊 FINAL PERFORMANCE SUMMARY")
        print("=" * 60)
        
        total_times = []
        total_scores = []
        total_issues = 0
        
        for scenario in all_results:
            print(f"\n{scenario['name']}:")
            print(f"  Average response time: {scenario['metrics']['avg_response_time']:.2f}s")
            print(f"  Average quality score: {scenario['metrics']['avg_quality_score']:.1f}/10")
            print(f"  Issues found: {scenario['metrics']['total_issues']}")
            
            total_times.extend([conv["response_time"] for conv in scenario["conversations"]])
            total_scores.extend([conv["quality"]["overall_score"] for conv in scenario["conversations"]])
            total_issues += scenario["metrics"]["total_issues"]
        
        overall_avg_time = sum(total_times) / len(total_times)
        overall_avg_score = sum(total_scores) / len(total_scores)
        
        print(f"\n🎯 OVERALL METRICS:")
        print(f"  Average response time: {overall_avg_time:.2f}s")
        print(f"  Average quality score: {overall_avg_score:.1f}/10")
        print(f"  Total issues: {total_issues}")
        print(f"  Cache performance: {sum(cache_times)/len(cache_times):.2f}s avg")
        
        # Success criteria
        print(f"\n✅ SUCCESS CRITERIA:")
        print(f"  Response time < 0.5s: {'✅ PASS' if overall_avg_time < 0.5 else '❌ FAIL'}")
        print(f"  Quality score >= 9/10: {'✅ PASS' if overall_avg_score >= 9 else '❌ FAIL'}")
        print(f"  Zero repetitive phrases: {'✅ PASS' if total_issues == 0 else '❌ FAIL'}")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"tests/results/final_test_{timestamp}.json", "w") as f:
            json.dump({
                "timestamp": timestamp,
                "scenarios": all_results,
                "overall_metrics": {
                    "avg_response_time": overall_avg_time,
                    "avg_quality_score": overall_avg_score,
                    "total_issues": total_issues,
                    "cache_effectiveness": sum(cache_times)/len(cache_times)
                },
                "success_criteria": {
                    "performance_target_met": overall_avg_time < 0.5,
                    "quality_target_met": overall_avg_score >= 9,
                    "no_repetitive_phrases": total_issues == 0
                }
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: tests/results/final_test_{timestamp}.json")

if __name__ == "__main__":
    asyncio.run(test_final_improvements())