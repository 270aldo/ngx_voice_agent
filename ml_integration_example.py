"""
ML Integration Example for NGX Voice Sales Agent.

This example shows how to use the ML-enhanced predictive services
in your application.
"""

import asyncio
from typing import List, Dict, Any

# Import the services
from src.services.training import MLPredictionService
from src.services.ml_enhanced_predictive_service import MLEnhancedPredictiveService

# For this example, we'll create mock versions of the existing services
class MockObjectionService:
    async def predict_objections(self, *args, **kwargs):
        return {"objections": [], "confidence": 0}
    
    async def record_actual_objection(self, *args, **kwargs):
        return {}

class MockNeedsService:
    async def predict_needs(self, *args, **kwargs):
        return {"needs": [], "confidence": 0}
    
    async def _get_response_templates(self, need_type):
        return ["Template response"]
    
    async def record_identified_need(self, *args, **kwargs):
        return {}

class MockConversionService:
    async def predict_conversion_probability(self, *args, **kwargs):
        return {"probability": 0.5, "conversion_level": "medium"}
    
    class predictive_model_service:
        @staticmethod
        async def store_prediction(*args, **kwargs):
            return {}

async def example_ml_predictions():
    """Example of using ML predictions directly."""
    print("\n" + "="*50)
    print("DIRECT ML PREDICTION EXAMPLE")
    print("="*50)
    
    # Initialize ML prediction service
    ml_service = MLPredictionService()
    
    # Example conversation
    conversation = [
        {"role": "assistant", "content": "¡Hola! Soy tu asistente de NGX. ¿En qué puedo ayudarte hoy?"},
        {"role": "user", "content": "Hola, tengo un gimnasio y pierdo muchos clientes por no responder rápido"},
        {"role": "assistant", "content": "Entiendo perfectamente. NGX AGENTS ACCESS puede responder 24/7 instantáneamente. Nunca perderás otro lead."},
        {"role": "user", "content": "Suena bien, pero $2,700 al mes es mucho para mi gimnasio pequeño"}
    ]
    
    # Get predictions
    print("\n1. Objection Prediction:")
    objections = await ml_service.predict_objections(conversation)
    if objections.get("primary_objection"):
        print(f"   Primary: {objections['primary_objection']} ({objections['confidence']:.1%})")
        if objections.get("objections"):
            print(f"   Suggested Response: {objections['objections'][0]['suggested_responses'][0][:100]}...")
    
    print("\n2. Needs Analysis:")
    needs = await ml_service.predict_needs(conversation)
    if needs.get("primary_need"):
        print(f"   Primary Need: {needs['primary_need']} ({needs['confidence']:.1%})")
        if needs.get("next_questions"):
            print(f"   Next Question: {needs['next_questions'][0]}")
    
    print("\n3. Conversion Prediction:")
    conversion = await ml_service.predict_conversion(conversation)
    print(f"   Probability: {conversion['probability']:.1%}")
    print(f"   Level: {conversion['conversion_level']}")
    print(f"   Next Action: {conversion['next_action']}")

async def example_enhanced_service():
    """Example of using the enhanced service with ML + rule-based fallback."""
    print("\n" + "="*50)
    print("ML ENHANCED SERVICE EXAMPLE")
    print("="*50)
    
    # Create mock services
    objection_service = MockObjectionService()
    needs_service = MockNeedsService()
    conversion_service = MockConversionService()
    
    # Initialize enhanced service
    enhanced_service = MLEnhancedPredictiveService(
        objection_service=objection_service,
        needs_service=needs_service,
        conversion_service=conversion_service
    )
    
    # Example conversation
    conversation = [
        {"role": "assistant", "content": "¡Hola! ¿Cómo puedo ayudarte con tu negocio fitness?"},
        {"role": "user", "content": "Tengo un box de CrossFit y necesito automatizar mi proceso de ventas"},
        {"role": "assistant", "content": "NGX es perfecto para boxes de CrossFit. Automatizamos todo el proceso de ventas con 11 agentes especializados."},
        {"role": "user", "content": "Me interesa mucho. ¿Cómo empezamos? Necesito esto funcionando lo antes posible."}
    ]
    
    # Get unified insights
    print("\nGetting Unified Insights...")
    insights = await enhanced_service.get_unified_insights(
        conversation_id="example-123",
        messages=conversation
    )
    
    print(f"\nConversation Phase: {insights['conversation_phase']}")
    print(f"Primary Focus: {insights['primary_focus']}")
    print(f"Recommended Action: {insights['recommended_action']}")
    print(f"Overall Confidence: {insights['confidence_score']:.1%}")
    print(f"ML Models Active: {insights['ml_models_active']}")

async def example_real_time_analysis():
    """Example of real-time conversation analysis."""
    print("\n" + "="*50)
    print("REAL-TIME CONVERSATION ANALYSIS")
    print("="*50)
    
    ml_service = MLPredictionService()
    
    # Simulate a conversation flow
    conversation_flow = [
        ("assistant", "¡Hola! Soy tu asistente de NGX. ¿En qué puedo ayudarte hoy?"),
        ("user", "Hola, vi su publicidad. Tengo un estudio de pilates pequeño"),
        ("assistant", "¡Qué gusto! NGX es ideal para estudios de pilates. ¿Cuál es tu mayor reto actualmente?"),
        ("user", "No tengo tiempo para responder a todos los mensajes de WhatsApp de mis clientes"),
        ("assistant", "Lo entiendo perfectamente. NGX puede responder automáticamente 24/7. ¿Cuántos mensajes recibes al día?"),
        ("user", "Unos 30-40 mensajes. Me interesa, pero no sé si puedo pagarlo"),
    ]
    
    conversation = []
    
    print("\nAnalyzing conversation in real-time:")
    print("-" * 40)
    
    for role, content in conversation_flow:
        conversation.append({"role": role, "content": content})
        
        if role == "user":
            # Analyze after each user message
            print(f"\nUser: {content}")
            
            # Quick analysis
            conversion = await ml_service.predict_conversion(conversation)
            print(f"→ Conversion: {conversion['probability']:.0%} ({conversion['conversion_level']})")
            
            # Check for immediate concerns
            if "precio" in content.lower() or "pagar" in content.lower():
                objections = await ml_service.predict_objections(conversation)
                if objections.get("primary_objection"):
                    print(f"→ Objection: {objections['primary_objection']}")
                    print(f"→ Response: Handle price concern with ROI focus")

def main():
    """Run all examples."""
    print("\n🚀 NGX ML INTEGRATION EXAMPLES")
    print("Demonstrating ML-powered predictive services")
    
    # Run examples
    asyncio.run(example_ml_predictions())
    asyncio.run(example_enhanced_service())
    asyncio.run(example_real_time_analysis())
    
    print("\n\n✅ Examples completed!")
    print("\nTo use in production:")
    print("1. Run 'python initialize_ml_models.py' to train models")
    print("2. Import MLPredictionService or MLEnhancedPredictiveService")
    print("3. Use the prediction methods as shown above")

if __name__ == "__main__":
    main()