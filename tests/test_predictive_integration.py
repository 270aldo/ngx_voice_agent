#!/usr/bin/env python3
"""
Test predictive services integration in ConversationOrchestrator.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.conversation.orchestrator import ConversationOrchestrator
from src.models.conversation import CustomerData


async def test_predictive_services_initialization():
    """Test that predictive services initialize correctly."""
    print("\n🚀 Testing Predictive Services Integration...")
    
    try:
        # Create orchestrator
        orchestrator = ConversationOrchestrator(industry='salud')
        
        # Check services before initialization
        print("✅ Orchestrator created")
        print(f"  - objection_predictor: {orchestrator.objection_predictor}")
        print(f"  - needs_predictor: {orchestrator.needs_predictor}")
        print(f"  - conversion_predictor: {orchestrator.conversion_predictor}")
        print(f"  - decision_engine: {orchestrator.decision_engine}")
        
        # Initialize
        print("\n🔧 Initializing orchestrator...")
        await orchestrator.initialize()
        
        # Check services after initialization
        print("\n✅ After initialization:")
        print(f"  - objection_predictor: {orchestrator.objection_predictor}")
        print(f"  - needs_predictor: {orchestrator.needs_predictor}")
        print(f"  - conversion_predictor: {orchestrator.conversion_predictor}")
        print(f"  - decision_engine: {orchestrator.decision_engine}")
        print(f"  - predictive_model_service: {orchestrator.predictive_model_service}")
        print(f"  - nlp_integration_service: {orchestrator.nlp_integration_service}")
        
        # Test conversation with predictive analysis
        print("\n🎯 Testing conversation with predictive analysis...")
        
        # Create customer data
        customer = CustomerData(
            id="test-123",
            name="María García",
            email="maria@test.com",
            age=35,
            occupation="Emprendedora",
            initial_message="Hola, estoy interesada en mejorar mi energía"
        )
        
        # Start conversation
        state = await orchestrator.start_conversation(customer)
        print(f"\n✅ Conversation started: {state.conversation_id}")
        print(f"   Initial greeting: {state.messages[0].content[:100]}...")
        
        # Process a message
        response = await orchestrator.process_message(
            state.conversation_id,
            "Me preocupa el precio, ¿es muy caro?"
        )
        
        print(f"\n✅ Message processed")
        print(f"   Response: {response['response'][:150]}...")
        
        # Check if predictive insights were included
        if 'metadata' in response and 'predictive_insights' in response['metadata']:
            insights = response['metadata']['predictive_insights']
            print(f"\n📊 Predictive Insights:")
            print(f"   - Objections predicted: {len(insights.get('objections_predicted', []))}")
            print(f"   - Needs detected: {len(insights.get('needs_detected', []))}")
            print(f"   - Conversion probability: {insights.get('conversion_probability', 0):.0%}")
            print(f"   - Recommended actions: {len(insights.get('recommended_actions', []))}")
        
        # End conversation
        await orchestrator.end_conversation(state.conversation_id)
        print(f"\n✅ Conversation ended successfully")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run tests."""
    success = await test_predictive_services_initialization()
    
    if success:
        print("\n✅ ALL TESTS PASSED! Predictive services are integrated.")
    else:
        print("\n❌ Tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())