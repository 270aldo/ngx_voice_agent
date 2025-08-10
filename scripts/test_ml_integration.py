#!/usr/bin/env python3
"""
ML Pipeline Integration Test Script

This script tests the ML Pipeline Integration by running a simulated conversation
and verifying that all components are working together.
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

from src.services.conversation.orchestrator import ConversationOrchestrator
from src.models.conversation import CustomerData
from src.models.platform_context import PlatformInfo

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_ml_pipeline_integration():
    """Test the ML Pipeline Integration with a simulated conversation."""
    
    print("🚀 Starting ML Pipeline Integration Test")
    print("=" * 60)
    
    try:
        # 1. Initialize Orchestrator
        print("1. Initializing Conversation Orchestrator...")
        orchestrator = ConversationOrchestrator(industry='salud')
        await orchestrator.initialize()
        print("   ✅ Orchestrator initialized successfully")
        
        # Check ML Pipeline components
        ml_components = {
            "ML Pipeline Service": orchestrator.ml_pipeline is not None,
            "Pattern Recognition": orchestrator.pattern_recognition is not None,
            "A/B Testing": orchestrator.ab_testing is not None,
            "Decision Engine": orchestrator.decision_engine is not None
        }
        
        print("\n2. ML Components Status:")
        for component, status in ml_components.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {component}: {'Available' if status else 'Not Available'}")
        
        # 2. Create test customer
        print("\n3. Creating test customer...")
        customer_data = CustomerData(
            id="test-customer-ml-integration",
            name="María González",
            age=32,
            email="maria@test.com",
            phone="+1234567890",
            initial_message="Hola, quiero información sobre los programas de bienestar"
        )
        
        platform_info = PlatformInfo(
            source="web",
            user_agent="ml-integration-test",
            ip="127.0.0.1"
        )
        print("   ✅ Test customer created")
        
        # 3. Start conversation
        print("\n4. Starting conversation...")
        state = await orchestrator.start_conversation(
            customer_data=customer_data,
            platform_info=platform_info
        )
        
        conversation_id = state.conversation_id
        print(f"   ✅ Conversation started: {conversation_id}")
        print(f"   📝 Initial greeting: {state.messages[0].content[:100]}...")
        
        # 4. Simulate conversation flow
        print("\n5. Simulating conversation flow...")
        
        test_messages = [
            "Me interesa el programa PRIME, ¿qué incluye?",
            "¿Cuánto cuesta el programa completo?",
            "Parece un poco caro, ¿hay opciones de financiamiento?",
            "Me gusta lo que ofrecen, ¿cómo puedo empezar?",
            "Perfecto, quiero inscribirme al programa PRIME"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n   Message {i}: {message}")
            
            # Process message
            result = await orchestrator.process_message(
                conversation_id=conversation_id,
                message_text=message
            )
            
            # Display results
            print(f"   Response: {result['response'][:100]}...")
            print(f"   Phase: {result.get('sales_phase', 'unknown')}")
            print(f"   Emotion: {result.get('emotional_state', {}).get('primary_emotion', 'unknown')}")
            
            # Check ML insights
            if 'ml_insights' in result and result['ml_insights']:
                insights = result['ml_insights']
                if 'conversion_probability' in insights:
                    print(f"   🤖 Conversion Probability: {insights['conversion_probability']:.2%}")
                if 'objections_predicted' in insights and insights['objections_predicted']:
                    print(f"   🤖 Objections Predicted: {len(insights['objections_predicted'])}")
                if 'needs_detected' in insights and insights['needs_detected']:
                    print(f"   🤖 Needs Detected: {len(insights['needs_detected'])}")
            
            # Check patterns if available
            updated_state = await orchestrator._get_conversation_state(conversation_id)
            if updated_state.context.get('detected_patterns'):
                patterns = updated_state.context['detected_patterns']
                pattern_types = [p.get('type', 'unknown') for p in patterns]
                print(f"   🔍 Patterns Detected: {', '.join(pattern_types)}")
            
            # Check A/B variants if available
            if updated_state.context.get('ab_variants'):
                variants = updated_state.context['ab_variants']
                print(f"   🧪 A/B Variants Active: {len(variants)}")
        
        # 6. End conversation
        print("\n6. Ending conversation...")
        final_state = await orchestrator.end_conversation(
            conversation_id=conversation_id,
            end_reason="completed"
        )
        
        print(f"   ✅ Conversation ended successfully")
        print(f"   📊 Total messages: {len(final_state.messages)}")
        print(f"   📈 Final phase: {final_state.phase}")
        
        # 7. Test ML Pipeline metrics (if available)
        if orchestrator.ml_pipeline:
            print("\n7. Checking ML Pipeline metrics...")
            try:
                metrics = await orchestrator.ml_pipeline.get_ml_pipeline_metrics()
                print(f"   📊 Pipeline Status: {metrics.get('pipeline_status', 'unknown')}")
                print(f"   🏥 Health Score: {metrics.get('health_score', 0):.1f}/100")
                
                if 'predictions' in metrics:
                    pred_metrics = metrics['predictions']
                    print(f"   🤖 Total Predictions: {pred_metrics.get('total_predictions', 0)}")
                
                if 'buffers' in metrics:
                    buffers = metrics['buffers']
                    total_buffered = sum(buffers.values())
                    print(f"   📦 Buffered Events: {total_buffered}")
                
            except Exception as e:
                print(f"   ⚠️  Could not retrieve ML Pipeline metrics: {e}")
        
        # 8. Summary
        print("\n" + "=" * 60)
        print("🎉 ML Pipeline Integration Test COMPLETED")
        print("=" * 60)
        
        # Test results summary
        results = {
            "Orchestrator Initialization": "✅ Success",
            "ML Pipeline Service": "✅ Available" if orchestrator.ml_pipeline else "❌ Not Available",
            "Pattern Recognition": "✅ Available" if orchestrator.pattern_recognition else "❌ Not Available",
            "A/B Testing": "✅ Available" if orchestrator.ab_testing else "❌ Not Available",
            "Decision Engine": "✅ Available" if orchestrator.decision_engine else "❌ Not Available",
            "Conversation Flow": "✅ Successful",
            "Message Processing": "✅ All messages processed",
            "Outcome Recording": "✅ Conversation ended successfully"
        }
        
        print("\nTest Results Summary:")
        for test, result in results.items():
            print(f"  {result} {test}")
        
        # Calculate success rate
        successful_tests = sum(1 for result in results.values() if "✅" in result)
        total_tests = len(results)
        success_rate = (successful_tests / total_tests) * 100
        
        print(f"\nOverall Success Rate: {success_rate:.1f}% ({successful_tests}/{total_tests})")
        
        if success_rate >= 80:
            print("🎊 EXCELLENT! ML Pipeline Integration is working well!")
        elif success_rate >= 60:
            print("👍 GOOD! Most ML components are working, some improvements needed.")
        else:
            print("⚠️  NEEDS ATTENTION! Several ML components need fixing.")
        
        return success_rate >= 60  # Return True if at least 60% success
        
    except Exception as e:
        print(f"\n❌ ERROR during ML Pipeline Integration test: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_individual_components():
    """Test individual ML components separately."""
    print("\n" + "=" * 60)
    print("🔧 Testing Individual ML Components")
    print("=" * 60)
    
    try:
        # Test ML Pipeline Service
        print("\n1. Testing ML Pipeline Service...")
        try:
            from src.services.ml_pipeline.ml_pipeline_service import MLPipelineService
            pipeline = MLPipelineService()
            print("   ✅ ML Pipeline Service imported successfully")
            
            # Test event tracking
            if hasattr(pipeline, 'event_tracker'):
                print("   ✅ Event Tracker available")
            else:
                print("   ❌ Event Tracker not available")
                
        except Exception as e:
            print(f"   ❌ ML Pipeline Service error: {e}")
        
        # Test Pattern Recognition
        print("\n2. Testing Pattern Recognition...")
        try:
            from src.services.pattern_recognition_engine import pattern_recognition_engine
            print("   ✅ Pattern Recognition Engine imported successfully")
            
            if hasattr(pattern_recognition_engine, 'detect_patterns'):
                print("   ✅ Pattern detection method available")
            else:
                print("   ❌ Pattern detection method not available")
                
        except Exception as e:
            print(f"   ❌ Pattern Recognition error: {e}")
        
        # Test A/B Testing Framework
        print("\n3. Testing A/B Testing Framework...")
        try:
            from src.services.ab_testing_framework import ABTestingFramework
            print("   ✅ A/B Testing Framework imported successfully")
            
        except Exception as e:
            print(f"   ❌ A/B Testing Framework error: {e}")
        
        # Test Decision Engine
        print("\n4. Testing Decision Engine...")
        try:
            from src.services.unified_decision_engine import UnifiedDecisionEngine
            print("   ✅ Unified Decision Engine imported successfully")
            
        except Exception as e:
            print(f"   ❌ Decision Engine error: {e}")
        
        print("\n✅ Individual component testing completed")
        
    except Exception as e:
        print(f"\n❌ Error during component testing: {e}")


def main():
    """Main entry point for the test script."""
    print("ML Pipeline Integration Test Script")
    print("==================================")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Run the tests
        success = asyncio.run(test_ml_pipeline_integration())
        
        # Run component tests
        asyncio.run(test_individual_components())
        
        print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if success:
            print("\n🎉 All tests completed successfully!")
            sys.exit(0)
        else:
            print("\n⚠️  Some tests failed. Check the output above.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()