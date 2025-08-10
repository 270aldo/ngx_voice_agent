#!/usr/bin/env python3
"""
Test simplified orchestrator with mocked dependencies.
"""
import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.conversation.orchestrator import ConversationOrchestrator
from src.models.conversation import CustomerData, ConversationState

async def test_response_quality():
    """Test response quality and performance with mocked dependencies."""
    print("🚀 Testing Simplified Response Quality")
    print("=" * 60)
    
    # Mock the database methods
    with patch.object(ConversationOrchestrator, '_save_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_get_conversation_state', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_register_session', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_start_ml_conversation_tracking', new_callable=AsyncMock), \
         patch.object(ConversationOrchestrator, '_update_ml_conversation_metrics', new_callable=AsyncMock):
        
        orchestrator = ConversationOrchestrator()
        await orchestrator.initialize()
        
        # Create a mock conversation state
        state = ConversationState(
            conversation_id="test-123",
            customer_data={
                "id": "test_123",
                "name": "Carlos",
                "email": "carlos@test.com",
                "age": 35
            },
            messages=[],
            context={},
            program_type="PRIME"
        )
        
        # Mock _get_conversation_state to return our state
        orchestrator._get_conversation_state.return_value = state
        
        # Mock ML tracking to return empty config
        orchestrator._start_ml_conversation_tracking.return_value = {"experiments_assigned": []}
        
        # Test messages with various emotional states
        test_cases = [
            {
                "message": "Estoy agotado, trabajo 14 horas al día",
                "expected_emotion": "frustrated",
                "expected_price_objection": False
            },
            {
                "message": "¿Cuánto cuesta el programa?",
                "expected_emotion": "neutral",
                "expected_price_objection": True
            },
            {
                "message": "Me preocupa que sea muy caro y no tenga tiempo",
                "expected_emotion": "anxious",
                "expected_price_objection": True
            },
            {
                "message": "Estoy emocionado por empezar pero necesito garantías",
                "expected_emotion": "excited",
                "expected_price_objection": False
            }
        ]
        
        response_times = []
        
        for test in test_cases:
            print(f"\n💬 Testing: {test['message']}")
            print("-" * 40)
            
            # Time the response
            start_time = time.time()
            
            # Process message directly
            result = await orchestrator.process_message(
                "test-123",
                test["message"]
            )
            
            response_time = time.time() - start_time
            response_times.append(response_time)
            
            # Analyze results
            print(f"⏱️  Response time: {response_time:.2f}s")
            print(f"🤖 Response preview: {result['response'][:100]}...")
            
            # Check emotion detection
            detected_emotion = result['emotional_state']['primary_emotion']
            emotion_match = detected_emotion == test['expected_emotion']
            print(f"💭 Emotion detected: {detected_emotion} {'✅' if emotion_match else '❌'}")
            
            # Check for repetitive phrases
            repetitive_patterns = [
                "Tu cautela inicial es exactamente",
                "Comprendo que tu tiempo es extremadamente valioso",
                "Entiendo tu punto"
            ]
            
            found_repetitive = []
            for pattern in repetitive_patterns:
                if pattern in result['response']:
                    found_repetitive.append(pattern)
            
            if found_repetitive:
                print(f"⚠️  Repetitive phrases found: {found_repetitive}")
            else:
                print("✅ No repetitive phrases")
            
            # Check response length
            response_length = len(result['response'])
            print(f"📏 Response length: {response_length} chars")
            
            # Check for empathy indicators
            empathy_words = ["entiendo", "comprendo", "reconozco", "valoro", "aprecio"]
            has_empathy = any(word in result['response'].lower() for word in empathy_words)
            print(f"💚 Has empathy: {'✅' if has_empathy else '❌'}")
            
            # Check for questions
            has_question = "?" in result['response']
            print(f"❓ Has question: {'✅' if has_question else '❌'}")
        
        # Performance summary
        print("\n\n📊 PERFORMANCE SUMMARY")
        print("=" * 60)
        
        avg_time = sum(response_times) / len(response_times)
        print(f"Average response time: {avg_time:.2f}s")
        print(f"Min/Max: {min(response_times):.2f}s / {max(response_times):.2f}s")
        print(f"Target (<0.5s): {'✅ PASS' if avg_time < 0.5 else '❌ FAIL'}")
        
        if avg_time >= 0.5:
            print(f"\n⚠️  Performance gap: {(avg_time - 0.5):.2f}s above target")
            print(f"📈 Need {((avg_time / 0.5) - 1) * 100:.0f}% improvement")

if __name__ == "__main__":
    asyncio.run(test_response_quality())