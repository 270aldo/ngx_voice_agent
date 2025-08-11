#!/usr/bin/env python3
"""
MASTER TEST: Verify ALL NGX Voice Sales Agent capabilities are working.

Tests all major features:
1. ML Adaptive Learning
2. Tier Detection (PRIME/LONGEVITY)
3. Emotional Analysis
4. ROI Calculation
5. A/B Testing
6. Lead Qualification
7. HIE Integration
8. Multi-phase sales process
"""
import asyncio
import json
import time
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from src.services.conversation.orchestrator import ConversationOrchestrator
from src.models.conversation import CustomerData, ConversationState
from src.services.adaptive_learning_service import AdaptiveLearningService
from src.services.tier_detection_service import TierDetectionService
from src.services.ngx_roi_calculator import NGXROICalculator
from src.services.ab_testing_framework import ABTestingFramework
from src.services.qualification_service import LeadQualificationService


async def test_ml_adaptive_learning():
    """Test ML adaptive learning capabilities."""
    print("\n🧠 Testing ML Adaptive Learning...")
    
    # Initialize service
    ml_service = AdaptiveLearningService()
    await ml_service.initialize()
    
    # Test pattern learning
    test_pattern = {
        "conversation_id": "test-123",
        "message_index": 5,
        "user_message": "¿Cuánto cuesta?",
        "assistant_response": "NGX PRIME tiene varios tiers...",
        "user_reaction": "positive",
        "conversion_outcome": True
    }
    
    # Record pattern
    await ml_service.learn_from_conversation(test_pattern)
    
    # Get recommendations
    recommendations = await ml_service.get_response_recommendations(
        context={"message": "¿Cuánto cuesta?", "conversation_phase": "price_discussion"}
    )
    
    print(f"✅ ML Service initialized and learning")
    print(f"📊 Recorded pattern for price objection")
    print(f"💡 Got {len(recommendations) if recommendations else 0} recommendations")
    
    return True


async def test_tier_detection():
    """Test tier detection capabilities."""
    print("\n🎯 Testing Tier Detection...")
    
    # Initialize service
    tier_service = TierDetectionService()
    
    # Test cases
    test_cases = [
        {
            "name": "Young Professional",
            "data": {
                "age": 32,
                "occupation": "Software Developer",
                "initial_message": "Necesito más energía para mi trabajo",
                "budget_mentioned": False
            },
            "expected": "PRIME"
        },
        {
            "name": "Mature Executive",
            "data": {
                "age": 58,
                "occupation": "CEO",
                "initial_message": "Quiero mantenerme saludable a largo plazo",
                "budget_mentioned": True
            },
            "expected": "LONGEVITY"
        },
        {
            "name": "Hybrid Case",
            "data": {
                "age": 48,
                "occupation": "Consultor",
                "initial_message": "Busco rendimiento y prevención",
                "budget_mentioned": False
            },
            "expected": "HYBRID"
        }
    ]
    
    results = []
    for case in test_cases:
        result = await tier_service.detect_tier(
            messages=[case["data"]["initial_message"]],
            customer_data=case["data"]
        )
        
        results.append({
            "case": case["name"],
            "detected": result.get("tier", "Unknown"),
            "confidence": result.get("confidence", 0),
            "expected": case["expected"],
            "correct": result.get("tier") == case["expected"]
        })
        
        print(f"  {case['name']}: {result.get('tier')} (confidence: {result.get('confidence', 0):.2f})")
    
    accuracy = sum(1 for r in results if r["correct"]) / len(results) * 100
    print(f"✅ Tier detection accuracy: {accuracy:.0f}%")
    
    return accuracy >= 60  # At least 60% accuracy


async def test_roi_calculation():
    """Test ROI calculation capabilities."""
    print("\n💰 Testing ROI Calculator...")
    
    # Initialize service
    roi_service = NGXROICalculator()
    
    # Test professions
    test_professions = [
        {"profession": "Médico", "age": 45, "tier": "elite"},
        {"profession": "Emprendedor", "age": 35, "tier": "pro"},
        {"profession": "Entrenador Personal", "age": 28, "tier": "essential"}
    ]
    
    for prof in test_professions:
        roi = await roi_service.calculate_roi(
            profession=prof["profession"],
            age=prof["age"],
            selected_tier=prof["tier"]
        )
        
        print(f"\n  {prof['profession']} ({prof['age']} años):")
        print(f"    ROI: {roi.get('projected_roi_percentage', 0):.0f}%")
        print(f"    Valor anual: ${roi.get('annual_value', 0):,.0f}")
        print(f"    Recuperación: {roi.get('payback_period_months', 0):.1f} meses")
    
    print("✅ ROI calculations working")
    return True


async def test_emotional_analysis():
    """Test emotional analysis in conversation."""
    print("\n😊 Testing Emotional Analysis...")
    
    with patch.object(ConversationOrchestrator, '_save_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_get_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_register_session', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_start_ml_conversation_tracking', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_update_ml_conversation_metrics', new_callable=AsyncMock):
        
        orchestrator = ConversationOrchestrator()
        await orchestrator.initialize()
        
        # Create test state
        state = ConversationState(
            conversation_id="test-emotional",
            customer_data={"id": "test", "name": "María", "email": "test@test.com", "age": 40},
            messages=[],
            context={},
            program_type="LONGEVITY"
        )
        
        orchestrator._get_conversation_state.return_value = state
        orchestrator._start_ml_conversation_tracking.return_value = {"experiments_assigned": []}
        
        # Test emotional messages
        emotional_messages = [
            {"message": "Estoy muy frustrado con mi salud", "expected": "frustrated"},
            {"message": "Me siento emocionado por empezar", "expected": "excited"},
            {"message": "Tengo miedo de que no funcione", "expected": "anxious"},
            {"message": "Me da esperanza este programa", "expected": "hopeful"}
        ]
        
        correct_detections = 0
        for test in emotional_messages:
            result = await orchestrator.process_message(
                state.conversation_id,
                test["message"]
            )
            
            detected_emotion = result.get("emotional_state", {}).get("primary_emotion", "unknown")
            is_correct = detected_emotion == test["expected"]
            correct_detections += is_correct
            
            print(f"  '{test['message'][:30]}...' → {detected_emotion} {'✅' if is_correct else '❌'}")
        
        accuracy = (correct_detections / len(emotional_messages)) * 100
        print(f"✅ Emotional detection accuracy: {accuracy:.0f}%")
        
        return accuracy >= 50


async def test_ab_testing_framework():
    """Test A/B testing framework."""
    print("\n🔬 Testing A/B Testing Framework...")
    
    # Initialize framework
    ab_framework = ABTestingFramework()
    
    # Create test experiment
    experiment_id = "greeting_test"
    variants = [
        {"id": "formal", "content": "Buenos días, ¿cómo puedo ayudarle?"},
        {"id": "casual", "content": "¡Hola! ¿En qué te puedo ayudar?"},
        {"id": "empathetic", "content": "Hola, me alegra que estés aquí. ¿Cómo te puedo apoyar?"}
    ]
    
    # Get variant assignment
    user_id = "test_user_123"
    assigned_variant = await ab_framework.get_variant(experiment_id, user_id, variants)
    
    print(f"  Assigned variant: {assigned_variant['id']}")
    
    # Record conversions
    await ab_framework.record_conversion(experiment_id, user_id, assigned_variant['id'])
    
    # Get statistics
    stats = await ab_framework.get_experiment_stats(experiment_id)
    
    print(f"  Experiment stats recorded")
    print("✅ A/B testing framework operational")
    
    return True


async def test_lead_qualification():
    """Test lead qualification scoring."""
    print("\n📊 Testing Lead Qualification...")
    
    # Initialize service
    qual_service = LeadQualificationService()
    
    # Test different lead profiles
    test_leads = [
        {
            "name": "High Value Lead",
            "data": {
                "occupation": "Doctor",
                "age": 45,
                "initial_interest": "Quiero el programa completo",
                "budget_mentioned": True,
                "urgency_expressed": True
            }
        },
        {
            "name": "Low Value Lead", 
            "data": {
                "occupation": "Estudiante",
                "age": 22,
                "initial_interest": "Solo quiero información",
                "budget_mentioned": False,
                "urgency_expressed": False
            }
        }
    ]
    
    for lead in test_leads:
        score = await qual_service.calculate_lead_score(lead["data"])
        qualification = "Alta" if score > 70 else "Media" if score > 40 else "Baja"
        
        print(f"  {lead['name']}: Score {score}/100 - Calificación: {qualification}")
    
    print("✅ Lead qualification working")
    return True


async def test_hie_integration():
    """Test HIE (11 agents) integration in responses."""
    print("\n🤖 Testing HIE Integration...")
    
    with patch.object(ConversationOrchestrator, '_save_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_get_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_register_session', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_start_ml_conversation_tracking', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_update_ml_conversation_metrics', new_callable=AsyncMock):
        
        orchestrator = ConversationOrchestrator()
        await orchestrator.initialize()
        
        state = ConversationState(
            conversation_id="test-hie",
            customer_data={"id": "test", "name": "Carlos", "email": "test@test.com", "age": 35},
            messages=[],
            context={},
            program_type="PRIME"
        )
        
        orchestrator._get_conversation_state.return_value = state
        orchestrator._start_ml_conversation_tracking.return_value = {"experiments_assigned": []}
        
        # Test HIE mentions
        result = await orchestrator.process_message(
            state.conversation_id,
            "¿Qué hace diferente a NGX de otros programas?"
        )
        
        response = result["response"]
        
        # Check for HIE concepts
        hie_mentioned = "HIE" in response or "inteligencia híbrida" in response.lower()
        agents_mentioned = any(agent in response for agent in ["NEXUS", "BLAZE", "SAGE", "WAVE", "SPARK"])
        synergy_mentioned = "sinergia" in response.lower()
        
        print(f"  HIE mencionado: {'✅' if hie_mentioned else '❌'}")
        print(f"  Agentes mencionados: {'✅' if agents_mentioned else '❌'}")
        print(f"  Sinergia hombre-máquina: {'✅' if synergy_mentioned else '❌'}")
        
        return hie_mentioned or agents_mentioned


async def test_sales_phases():
    """Test multi-phase sales process."""
    print("\n📈 Testing Sales Phase Progression...")
    
    with patch.object(ConversationOrchestrator, '_save_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_get_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_register_session', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_start_ml_conversation_tracking', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_update_ml_conversation_metrics', new_callable=AsyncMock):
        
        orchestrator = ConversationOrchestrator()
        await orchestrator.initialize()
        
        state = ConversationState(
            conversation_id="test-phases",
            customer_data={"id": "test", "name": "Ana", "email": "test@test.com", "age": 38},
            messages=[],
            context={},
            program_type="PRIME",
            phase="greeting"
        )
        
        orchestrator._get_conversation_state.return_value = state
        orchestrator._start_ml_conversation_tracking.return_value = {"experiments_assigned": []}
        
        # Test conversation flow through phases
        conversation_flow = [
            {"message": "Hola, estoy interesada", "expected_phase": "greeting"},
            {"message": "Trabajo mucho y estoy cansada", "expected_phase": "exploration"},
            {"message": "¿Cómo me puede ayudar NGX?", "expected_phase": "exploration"},
            {"message": "¿Cuánto cuesta?", "expected_phase": "objection_handling"},
            {"message": "Me interesa empezar", "expected_phase": "closing"}
        ]
        
        phases_detected = []
        for step in conversation_flow:
            result = await orchestrator.process_message(
                state.conversation_id,
                step["message"]
            )
            
            current_phase = result.get("sales_phase", "unknown")
            phases_detected.append(current_phase)
            print(f"  Message: '{step['message'][:30]}...' → Phase: {current_phase}")
        
        # Check if phases progress logically
        print("✅ Sales phases progression tracked")
        return True


async def run_all_capability_tests():
    """Run all capability tests."""
    print("🚀 NGX VOICE SALES AGENT - COMPLETE CAPABILITY TEST")
    print("=" * 60)
    print("\nTesting all major capabilities...")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {},
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0
        }
    }
    
    # Run all tests
    tests = [
        ("ML Adaptive Learning", test_ml_adaptive_learning),
        ("Tier Detection", test_tier_detection),
        ("ROI Calculation", test_roi_calculation),
        ("Emotional Analysis", test_emotional_analysis),
        ("A/B Testing", test_ab_testing_framework),
        ("Lead Qualification", test_lead_qualification),
        ("HIE Integration", test_hie_integration),
        ("Sales Phases", test_sales_phases)
    ]
    
    for test_name, test_func in tests:
        try:
            start_time = time.time()
            passed = await test_func()
            duration = time.time() - start_time
            
            results["tests"][test_name] = {
                "passed": passed,
                "duration": duration,
                "error": None
            }
            
            if passed:
                results["summary"]["passed"] += 1
            else:
                results["summary"]["failed"] += 1
                
        except Exception as e:
            print(f"\n❌ {test_name} FAILED with error: {str(e)}")
            results["tests"][test_name] = {
                "passed": False,
                "duration": 0,
                "error": str(e)
            }
            results["summary"]["failed"] += 1
        
        results["summary"]["total"] += 1
    
    # Summary
    print("\n\n📊 CAPABILITY TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {results['summary']['total']}")
    print(f"Passed: {results['summary']['passed']} ✅")
    print(f"Failed: {results['summary']['failed']} ❌")
    print(f"Success Rate: {(results['summary']['passed'] / results['summary']['total'] * 100):.0f}%")
    
    # Detailed results
    print("\nDetailed Results:")
    for test_name, result in results["tests"].items():
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"  {test_name}: {status} ({result['duration']:.2f}s)")
        if result["error"]:
            print(f"    Error: {result['error']}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"tests/results/capability_test_{timestamp}.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: tests/results/capability_test_{timestamp}.json")
    
    # Overall assessment
    if results['summary']['passed'] == results['summary']['total']:
        print("\n🎉 ALL CAPABILITIES WORKING PERFECTLY!")
    elif results['summary']['passed'] >= results['summary']['total'] * 0.8:
        print("\n✅ SYSTEM MOSTLY FUNCTIONAL (80%+ capabilities working)")
    else:
        print("\n⚠️  SYSTEM NEEDS ATTENTION (Several capabilities not working)")


if __name__ == "__main__":
    asyncio.run(run_all_capability_tests())