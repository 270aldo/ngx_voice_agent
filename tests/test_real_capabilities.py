#!/usr/bin/env python3
"""
Test REAL integrated capabilities in the orchestrator.
Focus on what's actually connected and working.
"""
import asyncio
import json
import time
from datetime import datetime
from unittest.mock import AsyncMock, patch

from src.services.conversation.orchestrator import ConversationOrchestrator
from src.models.conversation import CustomerData, ConversationState


async def test_conversation_flow():
    """Test a complete sales conversation flow."""
    print("\n💬 Testing Complete Conversation Flow...")
    
    with patch.object(ConversationOrchestrator, '_save_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_register_session', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_start_ml_conversation_tracking', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_update_ml_conversation_metrics', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_calculate_personalized_roi', new_callable=AsyncMock):
        
        orchestrator = ConversationOrchestrator()
        await orchestrator.initialize()
        
        # Mock ROI calculation
        orchestrator._calculate_personalized_roi.return_value = {
            "projected_roi_percentage": 500,
            "annual_value": 50000,
            "payback_period_months": 2.4,
            "key_insights": [
                "Incremento del 35% en productividad laboral",
                "Reducción del 60% en días de enfermedad",
                "Mejora del 45% en calidad del sueño"
            ]
        }
        
        # Start conversation
        customer = CustomerData(
            id="test_001",
            name="Roberto",
            email="roberto@test.com",
            age=42,
            initial_message="Hola, soy ejecutivo y estoy agotado"
        )
        
        print("\n1️⃣ Starting conversation...")
        state = await orchestrator.start_conversation(customer, program_type="PRIME")
        print(f"✅ Conversation started: {state.conversation_id}")
        print(f"📝 Greeting: {state.messages[-1].content[:100]}...")
        
        # Simulate conversation
        test_messages = [
            {
                "user": "Trabajo 60 horas a la semana y no tengo energía",
                "check": ["empatía", "comprensión"]
            },
            {
                "user": "¿Qué hace diferente a NGX?",
                "check": ["HIE", "agentes", "sinergia"]
            },
            {
                "user": "¿Cuánto cuesta el programa?",
                "check": ["precio", "tier", "valor"]
            },
            {
                "user": "Me preocupa no tener tiempo para otro compromiso",
                "check": ["tiempo", "flexible", "adapta"]
            },
            {
                "user": "¿Qué ROI puedo esperar?",
                "check": ["500%", "productividad", "retorno"]
            }
        ]
        
        results = []
        for i, test in enumerate(test_messages):
            print(f"\n{i+2}️⃣ User: {test['user']}")
            
            result = await orchestrator.process_message(
                state.conversation_id,
                test["user"]
            )
            
            response = result["response"]
            print(f"🤖 Agent: {response[:100]}...")
            
            # Check for expected elements
            checks_passed = []
            for check_word in test["check"]:
                if check_word.lower() in response.lower():
                    checks_passed.append(check_word)
            
            print(f"✅ Found: {', '.join(checks_passed) if checks_passed else 'None'}")
            
            results.append({
                "message": test["user"],
                "response_length": len(response),
                "checks_passed": len(checks_passed),
                "checks_total": len(test["check"]),
                "emotional_state": result.get("emotional_state", {}).get("primary_emotion"),
                "sales_phase": result.get("sales_phase")
            })
        
        return results


async def test_tier_detection_flow():
    """Test tier detection through conversation."""
    print("\n🎯 Testing Tier Detection in Conversation...")
    
    with patch.object(ConversationOrchestrator, '_save_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_get_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_register_session', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_start_ml_conversation_tracking', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_update_ml_conversation_metrics', new_callable=AsyncMock):
        
        orchestrator = ConversationOrchestrator()
        await orchestrator.initialize()
        
        # Test different customer profiles
        test_profiles = [
            {
                "name": "Budget Conscious",
                "messages": [
                    "Hola, busco algo económico",
                    "No tengo mucho presupuesto",
                    "¿Cuál es la opción más barata?"
                ],
                "expected_tier": "essential"
            },
            {
                "name": "High Value",
                "messages": [
                    "Soy CEO de una empresa",
                    "Quiero el programa más completo",
                    "El precio no es problema si funciona"
                ],
                "expected_tier": "premium"
            }
        ]
        
        results = []
        for profile in test_profiles:
            print(f"\n📋 Profile: {profile['name']}")
            
            state = ConversationState(
                conversation_id=f"test-tier-{profile['name']}",
                customer_data={"id": "test", "name": "Test", "email": "test@test.com", "age": 40},
                messages=[],
                context={},
                program_type="PRIME"
            )
            
            orchestrator._get_conversation_state.return_value = state
            orchestrator._start_ml_conversation_tracking.return_value = {"experiments_assigned": []}
            
            # Send messages
            for msg in profile["messages"]:
                result = await orchestrator.process_message(state.conversation_id, msg)
                print(f"  💬 '{msg}' → Phase: {result.get('sales_phase', 'unknown')}")
            
            # Check final tier detection
            detected_tier = state.context.get("tier_detected", "unknown")
            print(f"  🎯 Detected tier: {detected_tier}")
            
            results.append({
                "profile": profile["name"],
                "detected_tier": detected_tier,
                "expected": profile["expected_tier"]
            })
        
        return results


async def test_ml_tracking():
    """Test ML tracking integration."""
    print("\n📊 Testing ML Tracking Integration...")
    
    with patch.object(ConversationOrchestrator, '_save_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_get_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_register_session', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_start_ml_conversation_tracking', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_update_ml_conversation_metrics', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_record_conversation_outcome_for_ml', new_callable=AsyncMock):
        
        orchestrator = ConversationOrchestrator()
        await orchestrator.initialize()
        
        # Track ML calls
        ml_tracking_calls = []
        ml_metrics_calls = []
        ml_outcome_calls = []
        
        orchestrator._start_ml_conversation_tracking.side_effect = lambda *args, **kwargs: {
            "experiments_assigned": ["greeting_v2", "empathy_ultra"],
            "tracking_id": "ml_123"
        }
        
        orchestrator._update_ml_conversation_metrics.side_effect = lambda conv_id, metrics: ml_metrics_calls.append(metrics)
        orchestrator._record_conversation_outcome_for_ml.side_effect = lambda *args, **kwargs: ml_outcome_calls.append(args)
        
        # Create conversation
        state = ConversationState(
            conversation_id="test-ml",
            customer_data={"id": "test", "name": "ML Test", "email": "test@test.com", "age": 35},
            messages=[],
            context={},
            program_type="PRIME",
            ml_tracking_enabled=True
        )
        
        orchestrator._get_conversation_state.return_value = state
        
        # Process messages
        messages = [
            "Estoy cansado",
            "¿Cuánto cuesta?",
            "Me interesa"
        ]
        
        for msg in messages:
            await orchestrator.process_message(state.conversation_id, msg)
        
        # End conversation
        await orchestrator.end_conversation(state.conversation_id, "completed")
        
        print(f"  📊 ML metrics tracked: {len(ml_metrics_calls)} times")
        print(f"  🧪 Experiments assigned: {state.experiment_assignments}")
        print(f"  📈 Metrics captured: {list(ml_metrics_calls[0].keys()) if ml_metrics_calls else 'None'}")
        print(f"  🎯 Outcome recorded: {'Yes' if ml_outcome_calls else 'No'}")
        
        return {
            "ml_tracking_active": len(ml_metrics_calls) > 0,
            "experiments_assigned": len(state.experiment_assignments) > 0,
            "outcome_tracking": len(ml_outcome_calls) > 0
        }


async def test_empathy_system():
    """Test empathy system responses."""
    print("\n💚 Testing Empathy System...")
    
    with patch.object(ConversationOrchestrator, '_save_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_get_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_register_session', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_start_ml_conversation_tracking', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_update_ml_conversation_metrics', new_callable=AsyncMock):
        
        orchestrator = ConversationOrchestrator()
        await orchestrator.initialize()
        
        state = ConversationState(
            conversation_id="test-empathy",
            customer_data={"id": "test", "name": "María", "email": "test@test.com", "age": 45},
            messages=[],
            context={},
            program_type="LONGEVITY"
        )
        
        orchestrator._get_conversation_state.return_value = state
        orchestrator._start_ml_conversation_tracking.return_value = {"experiments_assigned": []}
        
        # Test empathy triggers
        empathy_tests = [
            {
                "message": "Mi esposo murió hace 6 meses y no tengo energía",
                "check_words": ["siento", "comprendo", "difícil", "apoyo"],
                "min_length": 200
            },
            {
                "message": "Tengo miedo de envejecer sola",
                "check_words": ["entiendo", "natural", "acompañ", "apoyo"],
                "min_length": 150
            },
            {
                "message": "Los doctores no me hacen caso",
                "check_words": ["frustrante", "escuch", "importa", "valor"],
                "min_length": 150
            }
        ]
        
        results = []
        for test in empathy_tests:
            result = await orchestrator.process_message(state.conversation_id, test["message"])
            response = result["response"]
            
            # Check empathy indicators
            empathy_found = []
            for word in test["check_words"]:
                if word.lower() in response.lower():
                    empathy_found.append(word)
            
            print(f"\n  💬 '{test['message'][:40]}...'")
            print(f"  📏 Response length: {len(response)} chars")
            print(f"  💚 Empathy words found: {empathy_found}")
            print(f"  😊 Emotion detected: {result.get('emotional_state', {}).get('primary_emotion', 'unknown')}")
            
            results.append({
                "message": test["message"],
                "empathy_score": len(empathy_found) / len(test["check_words"]),
                "length_ok": len(response) >= test["min_length"],
                "emotion": result.get("emotional_state", {}).get("primary_emotion")
            })
        
        avg_empathy = sum(r["empathy_score"] for r in results) / len(results)
        print(f"\n  💚 Average empathy score: {avg_empathy:.0%}")
        
        return results


async def run_integrated_tests():
    """Run all integrated capability tests."""
    print("🚀 NGX VOICE SALES AGENT - INTEGRATED CAPABILITIES TEST")
    print("=" * 60)
    print("Testing what's ACTUALLY working in the system...")
    
    all_results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {}
    }
    
    # Test 1: Complete conversation flow
    print("\n" + "="*60)
    try:
        conv_results = await test_conversation_flow()
        all_results["tests"]["conversation_flow"] = {
            "passed": all(r["checks_passed"] > 0 for r in conv_results),
            "details": conv_results
        }
    except Exception as e:
        print(f"❌ Conversation flow test failed: {e}")
        all_results["tests"]["conversation_flow"] = {"passed": False, "error": str(e)}
    
    # Test 2: Tier detection
    print("\n" + "="*60)
    try:
        tier_results = await test_tier_detection_flow()
        all_results["tests"]["tier_detection"] = {
            "passed": any(r["detected_tier"] != "unknown" for r in tier_results),
            "details": tier_results
        }
    except Exception as e:
        print(f"❌ Tier detection test failed: {e}")
        all_results["tests"]["tier_detection"] = {"passed": False, "error": str(e)}
    
    # Test 3: ML tracking
    print("\n" + "="*60)
    try:
        ml_results = await test_ml_tracking()
        all_results["tests"]["ml_tracking"] = {
            "passed": ml_results["ml_tracking_active"],
            "details": ml_results
        }
    except Exception as e:
        print(f"❌ ML tracking test failed: {e}")
        all_results["tests"]["ml_tracking"] = {"passed": False, "error": str(e)}
    
    # Test 4: Empathy system
    print("\n" + "="*60)
    try:
        empathy_results = await test_empathy_system()
        avg_empathy = sum(r["empathy_score"] for r in empathy_results) / len(empathy_results)
        all_results["tests"]["empathy_system"] = {
            "passed": avg_empathy >= 0.5,
            "avg_score": avg_empathy,
            "details": empathy_results
        }
    except Exception as e:
        print(f"❌ Empathy test failed: {e}")
        all_results["tests"]["empathy_system"] = {"passed": False, "error": str(e)}
    
    # Summary
    print("\n\n📊 INTEGRATED CAPABILITIES SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for t in all_results["tests"].values() if t.get("passed", False))
    total = len(all_results["tests"])
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {total - passed} ❌")
    print(f"Success Rate: {(passed / total * 100):.0f}%")
    
    print("\nDetailed Results:")
    for test_name, result in all_results["tests"].items():
        status = "✅ PASS" if result.get("passed") else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if "error" in result:
            print(f"    Error: {result['error']}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"tests/results/integrated_test_{timestamp}.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n💾 Results saved to: tests/results/integrated_test_{timestamp}.json")
    
    # Assessment
    if passed == total:
        print("\n🎉 ALL INTEGRATED CAPABILITIES WORKING!")
    elif passed >= total * 0.7:
        print("\n✅ CORE SYSTEM FUNCTIONAL (70%+ working)")
    else:
        print("\n⚠️  SYSTEM HAS ISSUES (Multiple capabilities failing)")


if __name__ == "__main__":
    asyncio.run(run_integrated_tests())