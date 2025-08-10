#!/usr/bin/env python3
"""
Script de load testing LITE para el DecisionEngineService optimizado.
Versión simplificada que se enfoca en probar el rendimiento del motor
sin dependencias de base de datos.
"""

import asyncio
import time
import json
import random
from datetime import datetime
from typing import List, Dict, Any
import logging
from dataclasses import dataclass
import numpy as np

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


@dataclass
class LoadTestResults:
    """Resultados del load test."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    latencies: List[float] = None
    start_time: float = 0
    end_time: float = 0
    
    def __post_init__(self):
        if self.latencies is None:
            self.latencies = []
    
    def add_request(self, latency: float, success: bool = True):
        """Registra una petición."""
        self.total_requests += 1
        self.latencies.append(latency)
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
    
    def get_percentiles(self) -> Dict[str, float]:
        """Calcula percentiles de latencia."""
        if not self.latencies:
            return {}
        
        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)
        
        return {
            "p50": sorted_latencies[int(n * 0.50)],
            "p90": sorted_latencies[int(n * 0.90)],
            "p95": sorted_latencies[int(n * 0.95)],
            "p99": sorted_latencies[int(n * 0.99)] if n > 99 else sorted_latencies[-1],
            "avg": np.mean(self.latencies),
            "min": min(self.latencies),
            "max": max(self.latencies)
        }
    
    def get_throughput(self) -> float:
        """Calcula throughput en requests/segundo."""
        duration = self.end_time - self.start_time
        return self.total_requests / duration if duration > 0 else 0


async def generate_test_conversation(length: int = 10) -> List[Dict[str, Any]]:
    """Genera una conversación de prueba realista."""
    templates = {
        "user_initial": [
            "Hola, necesito ayuda para gestionar mi gimnasio",
            "Estoy buscando una solución para mejorar mi negocio",
            "Quiero información sobre sus servicios",
            "Me interesa saber más sobre NGX"
        ],
        "user_inquiry": [
            "¿Cuánto cuesta el servicio?",
            "¿Qué incluye el plan básico?",
            "¿Cómo funciona la IA?",
            "¿Puedo integrarlo con mi sistema actual?"
        ],
        "user_objection": [
            "Me parece un poco caro",
            "Necesito pensarlo más",
            "No estoy seguro si lo necesito",
            "Ya tengo otro sistema"
        ],
        "assistant_response": [
            "Entiendo tu consulta. NGX puede ayudarte con eso.",
            "Excelente pregunta. Déjame explicarte los beneficios.",
            "Comprendo tu preocupación. Muchos clientes tenían dudas similares.",
            "Gracias por tu interés. Te puedo ofrecer más detalles."
        ]
    }
    
    messages = []
    for i in range(length):
        if i == 0:
            # Mensaje inicial
            messages.append({
                "role": "user",
                "content": random.choice(templates["user_initial"])
            })
        elif i % 2 == 0:
            # Mensaje del usuario
            msg_type = random.choice(["user_inquiry", "user_objection"])
            messages.append({
                "role": "user",
                "content": random.choice(templates[msg_type])
            })
        else:
            # Respuesta del asistente
            messages.append({
                "role": "assistant",
                "content": random.choice(templates["assistant_response"])
            })
    
    return messages


async def test_single_request(engine: OptimizedDecisionEngineService, 
                            conversation_id: str,
                            messages: List[Dict[str, Any]],
                            customer_profile: Dict[str, Any]) -> float:
    """Ejecuta una sola petición y devuelve la latencia."""
    start_time = time.perf_counter()
    
    try:
        result = await engine.optimize_conversation_flow(
            conversation_id=conversation_id,
            messages=messages,
            customer_profile=customer_profile
        )
        
        latency = (time.perf_counter() - start_time) * 1000  # ms
        return latency
        
    except Exception as e:
        logger.error(f"Error en petición: {e}")
        return -1  # Indicador de error


async def run_concurrent_load(engine: OptimizedDecisionEngineService,
                            num_users: int,
                            requests_per_user: int,
                            results: LoadTestResults) -> None:
    """Ejecuta carga concurrente con múltiples usuarios."""
    
    async def user_session(user_id: int):
        """Simula una sesión de usuario."""
        for req_num in range(requests_per_user):
            # Generar conversación única para cada petición
            conversation_id = f"load_test_user_{user_id}_req_{req_num}"
            messages = await generate_test_conversation(random.randint(5, 15))
            
            customer_profile = {
                "business_type": random.choice(["gym", "studio", "trainer"]),
                "size": random.choice(["small", "medium", "large"]),
                "current_clients": random.randint(50, 1000),
                "budget": random.choice(["low", "medium", "high"])
            }
            
            # Ejecutar petición
            latency = await test_single_request(
                engine, conversation_id, messages, customer_profile
            )
            
            if latency >= 0:
                results.add_request(latency, success=True)
            else:
                results.add_request(0, success=False)
            
            # Pequeña pausa entre peticiones
            await asyncio.sleep(random.uniform(0.1, 0.5))
    
    # Ejecutar todos los usuarios concurrentemente
    tasks = [user_session(i) for i in range(num_users)]
    await asyncio.gather(*tasks)


async def main():
    """Función principal del load test lite."""
    logger.info("=== LOAD TEST LITE - DecisionEngineService Optimizado ===")
    
    # Configuración del test
    test_configs = [
        {"users": 10, "requests": 10, "name": "Carga Ligera"},
        {"users": 25, "requests": 10, "name": "Carga Media"},
        {"users": 50, "requests": 10, "name": "Carga Alta"},
        {"users": 100, "requests": 5, "name": "Carga Máxima"}
    ]
    
    # Inicializar servicios
    logger.info("Inicializando servicios...")
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
        redis_client=None,
        enable_cache=True
    )
    
    # Pre-calentar cache
    logger.info("Pre-calentando cache...")
    await engine.warmup_cache()
    
    # Ejecutar pruebas
    all_results = []
    
    for config in test_configs:
        logger.info(f"\n🔄 Ejecutando: {config['name']} ({config['users']} usuarios, {config['requests']} requests c/u)")
        
        results = LoadTestResults()
        results.start_time = time.time()
        
        await run_concurrent_load(
            engine=engine,
            num_users=config['users'],
            requests_per_user=config['requests'],
            results=results
        )
        
        results.end_time = time.time()
        
        # Mostrar resultados
        percentiles = results.get_percentiles()
        throughput = results.get_throughput()
        
        logger.info(f"✅ Completado - Total: {results.total_requests} requests")
        logger.info(f"  Exitosos: {results.successful_requests}")
        logger.info(f"  Fallidos: {results.failed_requests}")
        logger.info(f"  Throughput: {throughput:.2f} req/s")
        
        if percentiles:
            logger.info(f"  Latencias:")
            logger.info(f"    P50: {percentiles['p50']:.2f}ms")
            logger.info(f"    P90: {percentiles['p90']:.2f}ms")
            logger.info(f"    P95: {percentiles['p95']:.2f}ms")
            logger.info(f"    P99: {percentiles['p99']:.2f}ms")
            logger.info(f"    Promedio: {percentiles['avg']:.2f}ms")
            
            # Verificar objetivo
            if percentiles['p95'] < 500:
                logger.info(f"  ✅ OBJETIVO CUMPLIDO: P95 < 500ms")
            else:
                logger.warning(f"  ❌ OBJETIVO NO CUMPLIDO: P95 = {percentiles['p95']:.2f}ms")
        
        all_results.append({
            "config": config,
            "results": results,
            "percentiles": percentiles
        })
    
    # Obtener métricas finales del motor
    if hasattr(engine, 'get_performance_metrics'):
        engine_metrics = await engine.get_performance_metrics()
        logger.info(f"\n📊 Métricas finales del motor:")
        logger.info(f"  Cache hit rate: {engine_metrics.get('cache', {}).get('hit_rate', 0):.2%}")
        logger.info(f"  L1 hit rate: {engine_metrics.get('cache', {}).get('l1_hit_rate', 0):.2%}")
    
    # Resumen final
    logger.info("\n" + "="*60)
    logger.info("📊 RESUMEN LOAD TEST LITE")
    logger.info("="*60)
    
    for i, result_data in enumerate(all_results):
        config = result_data['config']
        percentiles = result_data['percentiles']
        
        logger.info(f"\n{config['name']}:")
        if percentiles:
            logger.info(f"  P95: {percentiles['p95']:.2f}ms {'✅' if percentiles['p95'] < 500 else '❌'}")
            logger.info(f"  Throughput: {result_data['results'].get_throughput():.2f} req/s")
    
    # Guardar resultados
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"load_test_lite_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "results": [
                {
                    "config": r["config"],
                    "total_requests": r["results"].total_requests,
                    "successful_requests": r["results"].successful_requests,
                    "failed_requests": r["results"].failed_requests,
                    "throughput": r["results"].get_throughput(),
                    "percentiles": r["percentiles"]
                }
                for r in all_results
            ]
        }, f, indent=2)
    
    logger.info(f"\n💾 Resultados guardados en: {filename}")


if __name__ == "__main__":
    asyncio.run(main())