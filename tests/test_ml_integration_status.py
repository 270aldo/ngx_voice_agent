#!/usr/bin/env python3
"""
Test específico para verificar el estado de la integración ML.
"""

import asyncio
import aiohttp
import json
from datetime import datetime


async def test_ml_integration():
    """Test the ML integration status."""
    
    print("\n🔍 VERIFICANDO INTEGRACIÓN ML - NGX Voice Sales Agent")
    print("=" * 60)
    
    api_url = "http://localhost:8000"
    
    # First check if server is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{api_url}/health") as response:
                if response.status == 200:
                    print("✅ Servidor está funcionando")
                else:
                    print(f"❌ Servidor respondió con status: {response.status}")
                    return
    except Exception as e:
        print(f"❌ No se puede conectar al servidor: {e}")
        print("   Asegúrate de que el servidor esté corriendo con: python run.py")
        return
    
    # Test conversation with ML features
    try:
        async with aiohttp.ClientSession() as session:
            # Start conversation
            print("\n📞 Iniciando conversación de prueba...")
            
            start_data = {
                "customer_data": {
                    "name": "ML Test User",
                    "email": "mltest@example.com",
                    "age": 35,
                    "occupation": "CEO"
                }
            }
            
            async with session.post(
                f"{api_url}/conversations/start",
                json=start_data
            ) as response:
                if response.status != 200:
                    print(f"❌ Error al iniciar conversación: {response.status}")
                    return
                    
                data = await response.json()
                conversation_id = data.get("conversation_id")
                print(f"✅ Conversación iniciada: {conversation_id}")
            
            # Send test messages that should trigger ML
            test_messages = [
                "Hola, soy CEO y busco optimizar mi productividad ejecutiva",
                "¿Cuánto cuesta el programa PRIME?",
                "Me preocupa no tener tiempo para comprometerme",
                "¿Qué ROI puedo esperar de su programa?"
            ]
            
            ml_features_detected = {
                "predictive_insights": False,
                "objection_prediction": False,
                "needs_detection": False,
                "conversion_probability": False,
                "roi_calculation": False
            }
            
            for i, message in enumerate(test_messages):
                print(f"\n📤 Mensaje {i+1}: {message}")
                
                async with session.post(
                    f"{api_url}/conversations/{conversation_id}/message",
                    json={"message": message}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = data.get("message", "")
                        
                        # Check for ML features in response
                        if "ml_insights" in data and data["ml_insights"]:
                            ml_features_detected["predictive_insights"] = True
                            print("   ✅ ML insights detectados")
                            
                            insights = data["ml_insights"]
                            if insights.get("objections_predicted"):
                                ml_features_detected["objection_prediction"] = True
                                objs = insights['objections_predicted'].get('objections', [])
                                if objs:
                                    print(f"   ✅ Objeciones predichas: {objs[0].get('type', 'unknown')}")
                            
                            if insights.get("needs_detected"):
                                ml_features_detected["needs_detection"] = True
                                needs = insights['needs_detected'].get('needs', [])
                                if needs:
                                    print(f"   ✅ Necesidades detectadas: {needs[0].get('type', 'unknown')}")
                                elif insights['needs_detected'].get('primary_need'):
                                    ml_features_detected["needs_detection"] = True
                                    print(f"   ✅ Necesidad primaria: {insights['needs_detected']['primary_need']}")
                            
                            if insights.get("conversion_probability", 0) > 0:
                                ml_features_detected["conversion_probability"] = True
                                print(f"   ✅ Probabilidad de conversión: {insights['conversion_probability']:.2%}")
                        
                        # Check response quality indicators
                        if any(word in response_text.lower() for word in ["roi", "retorno", "inversión"]):
                            ml_features_detected["roi_calculation"] = True
                            print("   ✅ ROI mencionado en respuesta")
                        
                        # Print part of response
                        print(f"   📥 Respuesta: {response_text[:100]}...")
                    else:
                        print(f"   ❌ Error en mensaje: {response.status}")
            
            # Get conversation details to check ML tracking
            async with session.get(
                f"{api_url}/conversations/{conversation_id}"
            ) as response:
                if response.status == 200:
                    conv_data = await response.json()
                    
                    # Check for ML metadata
                    if "ml_metadata" in conv_data:
                        print("\n✅ Metadata ML encontrada en conversación")
                        ml_features_detected["conversion_probability"] = True
    
    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE INTEGRACIÓN ML")
    print("=" * 60)
    
    working_features = sum(1 for v in ml_features_detected.values() if v)
    total_features = len(ml_features_detected)
    
    for feature, status in ml_features_detected.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {feature.replace('_', ' ').title()}")
    
    success_rate = (working_features / total_features) * 100
    print(f"\nCaracterísticas ML funcionando: {working_features}/{total_features}")
    print(f"Tasa de éxito: {success_rate:.1f}%")
    
    if success_rate > 80:
        print("\n🎉 INTEGRACIÓN ML FUNCIONANDO CORRECTAMENTE")
    elif success_rate > 50:
        print("\n⚠️  INTEGRACIÓN ML PARCIALMENTE FUNCIONAL")
    else:
        print("\n❌ INTEGRACIÓN ML REQUIERE ATENCIÓN")
    
    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "ml_features_detected": ml_features_detected,
        "success_rate": success_rate,
        "working_features": working_features,
        "total_features": total_features
    }
    
    with open("ml_integration_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Resultados guardados en: ml_integration_test_results.json")


if __name__ == "__main__":
    asyncio.run(test_ml_integration())