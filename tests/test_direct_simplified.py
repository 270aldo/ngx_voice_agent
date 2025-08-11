#!/usr/bin/env python3
"""
Direct test of simplified orchestrator without API.
"""
import asyncio
import time
from datetime import datetime
from src.services.conversation.orchestrator import ConversationOrchestrator
from src.models.conversation import CustomerData

async def test_simplified_flow():
    """Test the simplified conversation flow directly."""
    print("🚀 Testing Simplified Orchestrator Flow")
    print("=" * 60)
    
    orchestrator = ConversationOrchestrator()
    await orchestrator.initialize()
    
    # Test customer
    customer = CustomerData(
        id="test_123",
        name="Carlos",
        email="carlos@test.com",
        age=35,
        initial_message="Estoy agotado, trabajo 14 horas al día"
    )
    
    # Start conversation
    print("\n1️⃣ Starting conversation...")
    start_time = time.time()
    
    state = await orchestrator.start_conversation(customer)
    
    start_duration = time.time() - start_time
    print(f"✅ Conversation started in {start_duration:.2f}s")
    print(f"🤖 Greeting: {state.messages[-1].content[:150]}...")
    
    # Test messages
    test_messages = [
        "¿Cómo me puede ayudar NGX?",
        "¿Cuánto cuesta el programa?",
        "Me preocupa que sea muy caro",
        "¿Qué garantías tienen?"
    ]
    
    response_times = []
    
    for i, message in enumerate(test_messages):
        print(f"\n{i+2}️⃣ Message: {message}")
        
        msg_start = time.time()
        result = await orchestrator.process_message(
            state.conversation_id,
            message
        )
        msg_duration = time.time() - msg_start
        response_times.append(msg_duration)
        
        print(f"⏱️  Response time: {msg_duration:.2f}s")
        print(f"🤖 Response: {result['response'][:150]}...")
        
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
            print(f"⚠️  Found repetitive phrases: {found_repetitive}")
        else:
            print("✅ No repetitive phrases detected")
        
        # Check emotional state
        print(f"💭 Emotional state: {result.get('emotional_state', {}).get('primary_emotion', 'unknown')}")
        print(f"📊 Sales phase: {result.get('sales_phase', 'unknown')}")
    
    # Summary
    print("\n\n📊 PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Total messages: {len(test_messages) + 1}")
    print(f"Average response time: {sum(response_times) / len(response_times):.2f}s")
    print(f"Min/Max: {min(response_times):.2f}s / {max(response_times):.2f}s")
    
    avg_time = sum(response_times) / len(response_times)
    print(f"\n🎯 Performance target (<0.5s): {'✅ PASS' if avg_time < 0.5 else '❌ FAIL'}")
    
    if avg_time >= 0.5:
        print(f"⚠️  Current average ({avg_time:.2f}s) is {(avg_time/0.5 - 1)*100:.0f}% above target")

if __name__ == "__main__":
    asyncio.run(test_simplified_flow())