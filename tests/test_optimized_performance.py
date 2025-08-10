#!/usr/bin/env python3
"""
Test optimized performance with reduced prompts and caching.
"""
import asyncio
import time
from unittest.mock import AsyncMock, patch
from datetime import datetime
import json

from src.services.conversation.orchestrator import ConversationOrchestrator
from src.services.conversation.response_cache import response_cache
from src.services.conversation.cache_warmer import cache_warmer
from src.models.conversation import CustomerData, ConversationState


async def test_optimized_performance():
    """Test performance with all optimizations."""
    print("🚀 Testing Optimized Performance")
    print("=" * 60)
    
    # Clear cache first
    response_cache.clear()
    
    # Warm cache with common questions
    print("\n📦 Warming cache...")
    warm_stats = await cache_warmer.warm_cache()
    print(f"✅ Cache warmed: {warm_stats['success']} responses cached")
    
    # Mock database
    with patch.object(ConversationOrchestrator, '_save_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_get_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_register_session', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_start_ml_conversation_tracking', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_update_ml_conversation_metrics', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_calculate_personalized_roi', new_callable=AsyncMock):
        
        orchestrator = ConversationOrchestrator()
        await orchestrator.initialize()
        
        # Mock ROI
        orchestrator._calculate_personalized_roi.return_value = {
            "projected_roi_percentage": 500,
            "annual_value": 5000,
            "payback_period_months": 2.4
        }
        
        # Test scenarios
        test_cases = [
            {
                "name": "Common Questions (Cached)",
                "messages": [
                    "¿Cuánto cuesta el programa?",
                    "¿Cómo funciona NGX?",
                    "No tengo tiempo",
                    "¿Qué garantías hay?"
                ]
            },
            {
                "name": "Unique Questions (Not Cached)",
                "messages": [
                    "Trabajo en tecnología y duermo 4 horas",
                    "Mi esposa dice que estoy siempre irritable",
                    "Tengo 3 startups y no puedo más",
                    "¿NGX funciona para emprendedores?"
                ]
            }
        ]
        
        all_results = []
        
        for test_case in test_cases:
            print(f"\n\n📋 Testing: {test_case['name']}")
            print("-" * 50)
            
            # Create state
            state = ConversationState(
                conversation_id=f"test-{test_case['name'].lower().replace(' ', '-')}",
                customer_data={
                    "id": "test_123",
                    "name": "Carlos",
                    "email": "test@test.com",
                    "age": 35
                },
                messages=[],
                context={},
                program_type="PRIME",
                phase="exploration"
            )
            
            orchestrator._get_conversation_state.return_value = state
            orchestrator._start_ml_conversation_tracking.return_value = {"experiments_assigned": []}
            
            response_times = []
            responses = []
            
            for i, message in enumerate(test_case["messages"]):
                print(f"\n💬 {message}")
                
                # Time the response
                start_time = time.time()
                result = await orchestrator.process_message(state.conversation_id, message)
                response_time = time.time() - start_time
                
                response_times.append(response_time)
                responses.append(result["response"])
                
                # Display results
                print(f"⏱️  Time: {response_time:.3f}s")
                print(f"📏 Length: {len(result['response'])} chars")
                print(f"🤖 Preview: {result['response'][:80]}...")
                
                # Check if response meets length constraints
                if len(result['response']) > 1000:
                    print(f"⚠️  Response too long!")
            
            # Calculate stats
            avg_time = sum(response_times) / len(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            print(f"\n📊 {test_case['name']} Stats:")
            print(f"  Average: {avg_time:.3f}s")
            print(f"  Min/Max: {min_time:.3f}s / {max_time:.3f}s")
            print(f"  Target < 0.5s: {'✅ PASS' if avg_time < 0.5 else '❌ FAIL'}")
            
            all_results.append({
                "name": test_case["name"],
                "avg_time": avg_time,
                "min_time": min_time,
                "max_time": max_time,
                "response_times": response_times,
                "avg_response_length": sum(len(r) for r in responses) / len(responses)
            })
        
        # Overall summary
        print("\n\n🎯 OVERALL PERFORMANCE SUMMARY")
        print("=" * 60)
        
        overall_times = []
        for result in all_results:
            overall_times.extend(result["response_times"])
        
        overall_avg = sum(overall_times) / len(overall_times)
        
        print(f"Total messages tested: {len(overall_times)}")
        print(f"Overall average time: {overall_avg:.3f}s")
        print(f"Performance target (<0.5s): {'✅ PASS' if overall_avg < 0.5 else '❌ FAIL'}")
        
        # Cache effectiveness
        cache_stats = response_cache.stats()
        print(f"\n📦 Cache Stats:")
        print(f"  Total entries: {cache_stats['total_entries']}")
        print(f"  Active entries: {cache_stats['active_entries']}")
        print(f"  Cache size: {cache_stats['cache_size_bytes'] / 1024:.1f} KB")
        
        # Performance improvement
        if len(all_results) >= 2:
            cached_avg = all_results[0]["avg_time"]
            uncached_avg = all_results[1]["avg_time"]
            improvement = ((uncached_avg - cached_avg) / uncached_avg) * 100
            print(f"\n🚀 Cache Performance Boost: {improvement:.0f}%")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_data = {
            "timestamp": timestamp,
            "test_cases": all_results,
            "overall_metrics": {
                "avg_response_time": overall_avg,
                "total_messages": len(overall_times),
                "cache_stats": cache_stats,
                "target_met": overall_avg < 0.5
            }
        }
        
        with open(f"tests/results/optimized_performance_{timestamp}.json", "w") as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\n💾 Results saved to: tests/results/optimized_performance_{timestamp}.json")


if __name__ == "__main__":
    asyncio.run(test_optimized_performance())