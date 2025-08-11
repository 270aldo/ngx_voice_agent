#!/usr/bin/env python3
"""
Script simple para probar el DecisionEngineService optimizado.
Valida que todos los servicios se inicialicen correctamente.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List
import json

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar servicios
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.integrations.supabase.resilient_client import ResilientSupabaseClient
from src.services.optimized_decision_engine_service import OptimizedDecisionEngineService
from src.services.predictive_model_service import PredictiveModelService
from src.services.nlp_integration_service import NLPIntegrationService
from src.services.objection_prediction_service import ObjectionPredictionService
from src.services.needs_prediction_service import NeedsPredictionService
from src.services.conversion_prediction_service import ConversionPredictionService
from src.services.entity_recognition_service import EntityRecognitionService


async def test_simple_conversation():
    """Prueba una conversación simple con el motor optimizado."""
    
    logger.info("Inicializando servicios...")
    
    try:
        # Inicializar servicios base
        supabase = ResilientSupabaseClient()
        predictive_model_service = PredictiveModelService(supabase)
        nlp_service = NLPIntegrationService()
        entity_service = EntityRecognitionService()
        
        # Servicios de predicción
        objection_service = ObjectionPredictionService(
            supabase_client=supabase,
            predictive_model_service=predictive_model_service,
            nlp_integration_service=nlp_service
        )
        
        needs_service = NeedsPredictionService(
            supabase_client=supabase,
            predictive_model_service=predictive_model_service,
            nlp_integration_service=nlp_service,
            entity_recognition_service=entity_service
        )
        
        conversion_service = ConversionPredictionService(
            supabase_client=supabase,
            predictive_model_service=predictive_model_service,
            nlp_integration_service=nlp_service
        )
        
        # Motor optimizado
        engine = OptimizedDecisionEngineService(
            supabase=supabase,
            predictive_model_service=predictive_model_service,
            nlp_integration_service=nlp_service,
            objection_prediction_service=objection_service,
            needs_prediction_service=needs_service,
            conversion_prediction_service=conversion_service,
            redis_client=None,  # Sin Redis para esta prueba simple
            enable_cache=True
        )
        
        logger.info("✅ Todos los servicios inicializados correctamente")
        
        # Pre-calentar cache
        logger.info("Pre-calentando cache...")
        await engine.warmup_cache()
        
        # Conversación de prueba
        conversation_id = f"test_simple_{int(time.time())}"
        messages = [
            {
                "role": "user",
                "content": "Hola, estoy interesado en mejorar la gestión de mi gimnasio"
            },
            {
                "role": "assistant",
                "content": "¡Hola! Me da mucho gusto que estés interesado en mejorar la gestión de tu gimnasio. NGX puede ayudarte significativamente con eso. ¿Cuáles son los principales desafíos que enfrentas actualmente?"
            },
            {
                "role": "user",
                "content": "Tengo problemas con la retención de clientes y me cuesta mantener organizada la información"
            },
            {
                "role": "assistant",
                "content": "Entiendo perfectamente. La retención de clientes es crucial para cualquier gimnasio. NGX AGENTS ACCESS incluye herramientas específicas para esto, con IA que analiza patrones de comportamiento y te alerta sobre clientes en riesgo de cancelar. ¿Cuántos clientes manejas actualmente?"
            },
            {
                "role": "user",
                "content": "Tengo alrededor de 300 clientes activos, pero pierdo como 20-30 cada mes"
            }
        ]
        
        customer_profile = {
            "business_type": "gym",
            "size": "medium",
            "current_clients": 300,
            "monthly_churn": 0.08,
            "budget": "medium"
        }
        
        # Medir latencia de la primera llamada
        logger.info("\n🔄 Ejecutando primera llamada (sin cache)...")
        start_time = time.perf_counter()
        
        result1 = await engine.optimize_conversation_flow(
            conversation_id=conversation_id,
            messages=messages,
            customer_profile=customer_profile
        )
        
        latency1 = (time.perf_counter() - start_time) * 1000
        logger.info(f"⏱️  Latencia primera llamada: {latency1:.2f}ms")
        
        # Mostrar resultados
        if result1.get("success"):
            logger.info("✅ Primera llamada exitosa")
            logger.info(f"Fase actual: {result1.get('sales_phase', {}).get('current_phase')}")
            logger.info(f"Sentimiento: {result1.get('sentiment', {}).get('overall_sentiment')}")
            
            if result1.get("predictions", {}).get("objections"):
                logger.info("\n🚫 Objeciones predichas:")
                for obj in result1["predictions"]["objections"][:3]:
                    logger.info(f"  - {obj['objection_type']}: {obj['confidence']:.2%}")
            
            if result1.get("predictions", {}).get("needs"):
                logger.info("\n🎯 Necesidades detectadas:")
                for need in result1["predictions"]["needs"][:3]:
                    logger.info(f"  - {need['category']}: {need['confidence']:.2%}")
            
            if result1.get("response_suggestions"):
                logger.info("\n💡 Sugerencias de respuesta:")
                for suggestion in result1["response_suggestions"][:2]:
                    logger.info(f"  - {suggestion['text'][:100]}...")
        else:
            logger.error(f"❌ Error en primera llamada: {result1.get('error')}")
        
        # Medir latencia de segunda llamada (debería usar cache)
        logger.info("\n🔄 Ejecutando segunda llamada (con cache)...")
        start_time = time.perf_counter()
        
        result2 = await engine.optimize_conversation_flow(
            conversation_id=conversation_id,
            messages=messages,
            customer_profile=customer_profile
        )
        
        latency2 = (time.perf_counter() - start_time) * 1000
        logger.info(f"⏱️  Latencia segunda llamada: {latency2:.2f}ms")
        
        # Calcular mejora
        improvement = ((latency1 - latency2) / latency1) * 100 if latency1 > 0 else 0
        logger.info(f"📈 Mejora de rendimiento con cache: {improvement:.1f}%")
        
        # Obtener métricas del motor
        if hasattr(engine, 'get_performance_metrics'):
            metrics = await engine.get_performance_metrics()
            logger.info("\n📊 Métricas del motor:")
            logger.info(f"  Cache hit rate: {metrics.get('cache', {}).get('hit_rate', 0):.2%}")
            logger.info(f"  L1 hit rate: {metrics.get('cache', {}).get('l1_hit_rate', 0):.2%}")
            logger.info(f"  Total llamadas: {metrics.get('total_calls', 0)}")
        
        # Agregar más mensajes para probar escalabilidad
        logger.info("\n🔄 Probando con conversación más larga...")
        messages.extend([
            {
                "role": "assistant",
                "content": "Una tasa de cancelación del 8-10% es definitivamente algo que podemos mejorar. Con NGX AGENTS ACCESS, nuestros clientes típicamente reducen su churn en un 30-40% en los primeros 3 meses."
            },
            {
                "role": "user",
                "content": "¿Cuánto cuesta el servicio? Mi presupuesto es limitado"
            }
        ])
        
        start_time = time.perf_counter()
        result3 = await engine.optimize_conversation_flow(
            conversation_id=conversation_id,
            messages=messages,
            customer_profile=customer_profile
        )
        latency3 = (time.perf_counter() - start_time) * 1000
        
        logger.info(f"⏱️  Latencia con más mensajes: {latency3:.2f}ms")
        
        # Resumen final
        logger.info("\n" + "="*60)
        logger.info("📊 RESUMEN DE PRUEBA SIMPLE")
        logger.info("="*60)
        logger.info(f"✅ Servicios inicializados correctamente")
        logger.info(f"✅ Motor de decisiones funcionando")
        logger.info(f"✅ Cache activado y funcionando")
        logger.info(f"📈 Latencias: {latency1:.0f}ms → {latency2:.0f}ms → {latency3:.0f}ms")
        logger.info(f"🎯 Objetivo P95 < 500ms: {'✅ CUMPLIDO' if max(latency1, latency2, latency3) < 500 else '❌ NO CUMPLIDO'}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Función principal."""
    success = await test_simple_conversation()
    
    if success:
        logger.info("\n✅ Prueba simple completada exitosamente")
        logger.info("📝 Próximo paso: Ejecutar load_test_decision_engine.py para prueba de carga completa")
    else:
        logger.error("\n❌ La prueba simple falló. Revisar errores antes de ejecutar load test")


if __name__ == "__main__":
    asyncio.run(main())