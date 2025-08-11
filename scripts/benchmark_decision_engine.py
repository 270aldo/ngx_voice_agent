#!/usr/bin/env python3
"""
Script de benchmark para comparar el DecisionEngineService original
vs la versión optimizada.
"""

import asyncio
import time
import json
import statistics
from datetime import datetime
from typing import List, Dict, Any
import logging
from concurrent.futures import ThreadPoolExecutor
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
from src.services.decision_engine_service import DecisionEngineService
from src.services.optimized_decision_engine_service import OptimizedDecisionEngineService
from src.services.predictive_model_service import PredictiveModelService
from src.services.nlp_integration_service import NLPIntegrationService
from src.services.objection_prediction_service import ObjectionPredictionService
from src.services.needs_prediction_service import NeedsPredictionService
from src.services.conversion_prediction_service import ConversionPredictionService


class BenchmarkRunner:
    """Runner para ejecutar benchmarks comparativos."""
    
    def __init__(self):
        self.results = {
            "original": {
                "latencies": [],
                "errors": 0,
                "timeouts": 0
            },
            "optimized": {
                "latencies": [],
                "errors": 0,
                "timeouts": 0,
                "cache_hits": 0,
                "cache_misses": 0
            }
        }
    
    async def create_test_conversation(self, num_messages: int) -> List[Dict[str, Any]]:
        """Crea una conversación de prueba con el número especificado de mensajes."""
        messages = []
        
        # Plantillas de mensajes para simular conversación realista
        user_templates = [
            "Estoy buscando una solución para gestionar mi gimnasio",
            "¿Cuánto cuesta el servicio?",
            "¿Qué incluye exactamente?",
            "Necesito pensarlo un poco más",
            "¿Hay algún descuento disponible?",
            "¿Cómo funciona la implementación?",
            "¿Qué soporte ofrecen?",
            "¿Puedo ver una demo primero?",
            "¿Qué diferencia tienen con la competencia?",
            "Estoy listo para empezar"
        ]
        
        assistant_templates = [
            "¡Excelente! NGX tiene soluciones específicas para gimnasios. ¿Cuál es tu principal desafío?",
            "Ofrecemos varios planes. Para un gimnasio, el plan PRO a $349/mes sería ideal",
            "Incluye gestión de clientes, automatización de marketing, análisis con IA y más",
            "Entiendo. ¿Hay algo específico que te preocupe o sobre lo que necesites más información?",
            "Sí, tenemos un 20% de descuento para los primeros 3 meses",
            "La implementación es muy sencilla, toma solo 24-48 horas",
            "Ofrecemos soporte 24/7 y un gerente de éxito dedicado",
            "Por supuesto, puedo agendar una demo personalizada para mañana",
            "NGX se diferencia por su IA especializada en fitness y ROI garantizado",
            "¡Perfecto! Te voy a enviar el enlace para comenzar"
        ]
        
        for i in range(num_messages // 2):
            # Mensaje del usuario
            messages.append({
                "role": "user",
                "content": user_templates[i % len(user_templates)],
                "timestamp": datetime.now().isoformat()
            })
            
            # Respuesta del asistente
            messages.append({
                "role": "assistant",
                "content": assistant_templates[i % len(assistant_templates)],
                "timestamp": datetime.now().isoformat()
            })
        
        return messages
    
    async def run_single_test(self, 
                            engine: DecisionEngineService,
                            conversation_id: str,
                            messages: List[Dict[str, Any]],
                            engine_type: str) -> float:
        """Ejecuta una prueba individual y retorna la latencia."""
        start_time = time.perf_counter()
        
        try:
            result = await asyncio.wait_for(
                engine.optimize_conversation_flow(
                    conversation_id=conversation_id,
                    messages=messages,
                    customer_profile={
                        "business_type": "gym",
                        "size": "medium",
                        "current_clients": 500,
                        "monthly_churn": 0.1
                    }
                ),
                timeout=5.0  # 5 segundos timeout
            )
            
            latency = (time.perf_counter() - start_time) * 1000  # ms
            self.results[engine_type]["latencies"].append(latency)
            
            # Para la versión optimizada, trackear cache hits
            if engine_type == "optimized" and hasattr(engine, 'monitor'):
                if engine.monitor.metrics["cache_hits"] > 0:
                    self.results["optimized"]["cache_hits"] += 1
                else:
                    self.results["optimized"]["cache_misses"] += 1
            
            return latency
            
        except asyncio.TimeoutError:
            self.results[engine_type]["timeouts"] += 1
            return 5000.0  # Penalización de 5 segundos
        except Exception as e:
            logger.error(f"Error en {engine_type}: {e}")
            self.results[engine_type]["errors"] += 1
            return 5000.0
    
    async def run_concurrent_tests(self,
                                 engine: DecisionEngineService,
                                 engine_type: str,
                                 num_concurrent: int,
                                 messages_per_conversation: int,
                                 total_requests: int) -> None:
        """Ejecuta pruebas concurrentes."""
        logger.info(f"\nEjecutando {total_requests} requests con {num_concurrent} concurrentes para {engine_type}")
        
        # Pre-crear conversaciones para reutilizar
        conversations = []
        for i in range(min(10, total_requests)):  # Cache 10 conversaciones diferentes
            messages = await self.create_test_conversation(messages_per_conversation)
            conversations.append(messages)
        
        # Crear semáforo para limitar concurrencia
        semaphore = asyncio.Semaphore(num_concurrent)
        
        async def limited_test(index: int):
            async with semaphore:
                conversation_id = f"bench_{engine_type}_{index}"
                messages = conversations[index % len(conversations)]
                return await self.run_single_test(engine, conversation_id, messages, engine_type)
        
        # Ejecutar todas las pruebas
        tasks = [limited_test(i) for i in range(total_requests)]
        
        start_time = time.time()
        latencies = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Calcular throughput
        successful_requests = total_requests - self.results[engine_type]["errors"] - self.results[engine_type]["timeouts"]
        throughput = successful_requests / total_time if total_time > 0 else 0
        
        logger.info(f"{engine_type} - Completado en {total_time:.2f}s, Throughput: {throughput:.2f} req/s")
    
    def calculate_statistics(self, latencies: List[float]) -> Dict[str, float]:
        """Calcula estadísticas de latencia."""
        if not latencies:
            return {
                "p50": 0, "p90": 0, "p95": 0, "p99": 0,
                "avg": 0, "min": 0, "max": 0, "std": 0
            }
        
        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)
        
        return {
            "p50": sorted_latencies[int(n * 0.50)],
            "p90": sorted_latencies[int(n * 0.90)],
            "p95": sorted_latencies[int(n * 0.95)],
            "p99": sorted_latencies[int(n * 0.99)] if n > 99 else sorted_latencies[-1],
            "avg": statistics.mean(latencies),
            "min": min(latencies),
            "max": max(latencies),
            "std": statistics.stdev(latencies) if n > 1 else 0
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """Genera reporte comparativo."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "comparison": {}
        }
        
        for engine_type in ["original", "optimized"]:
            latencies = self.results[engine_type]["latencies"]
            stats = self.calculate_statistics(latencies)
            
            report["comparison"][engine_type] = {
                "statistics": stats,
                "total_requests": len(latencies) + self.results[engine_type]["errors"] + self.results[engine_type]["timeouts"],
                "successful_requests": len(latencies),
                "errors": self.results[engine_type]["errors"],
                "timeouts": self.results[engine_type]["timeouts"],
                "error_rate": self.results[engine_type]["errors"] / max(1, len(latencies) + self.results[engine_type]["errors"])
            }
        
        # Agregar métricas específicas de optimización
        if self.results["optimized"]["cache_hits"] + self.results["optimized"]["cache_misses"] > 0:
            report["comparison"]["optimized"]["cache_hit_rate"] = (
                self.results["optimized"]["cache_hits"] / 
                (self.results["optimized"]["cache_hits"] + self.results["optimized"]["cache_misses"])
            )
        
        # Calcular mejoras
        if (report["comparison"]["original"]["statistics"]["p95"] > 0 and
            report["comparison"]["optimized"]["statistics"]["p95"] > 0):
            
            improvement = {
                "p95_improvement": (
                    (report["comparison"]["original"]["statistics"]["p95"] - 
                     report["comparison"]["optimized"]["statistics"]["p95"]) / 
                    report["comparison"]["original"]["statistics"]["p95"] * 100
                ),
                "avg_improvement": (
                    (report["comparison"]["original"]["statistics"]["avg"] - 
                     report["comparison"]["optimized"]["statistics"]["avg"]) / 
                    report["comparison"]["original"]["statistics"]["avg"] * 100
                )
            }
            report["improvement"] = improvement
        
        return report


async def run_benchmark():
    """Ejecuta el benchmark completo."""
    logger.info("Inicializando servicios para benchmark...")
    
    # Inicializar servicios compartidos
    supabase = ResilientSupabaseClient()
    predictive_model_service = PredictiveModelService(supabase)
    nlp_service = NLPIntegrationService()
    
    # Inicializar servicios de predicción
    objection_service = ObjectionPredictionService(
        supabase_client=supabase,
        predictive_model_service=predictive_model_service,
        nlp_integration_service=nlp_service
    )
    
    needs_service = NeedsPredictionService(
        supabase_client=supabase,
        predictive_model_service=predictive_model_service,
        nlp_integration_service=nlp_service
    )
    
    conversion_service = ConversionPredictionService(
        supabase_client=supabase,
        predictive_model_service=predictive_model_service,
        nlp_integration_service=nlp_service
    )
    
    # Crear motores original y optimizado
    original_engine = DecisionEngineService(
        supabase=supabase,
        predictive_model_service=predictive_model_service,
        nlp_integration_service=nlp_service,
        objection_prediction_service=objection_service,
        needs_prediction_service=needs_service,
        conversion_prediction_service=conversion_service
    )
    
    optimized_engine = OptimizedDecisionEngineService(
        supabase=supabase,
        predictive_model_service=predictive_model_service,
        nlp_integration_service=nlp_service,
        objection_prediction_service=objection_service,
        needs_prediction_service=needs_service,
        conversion_prediction_service=conversion_service,
        redis_client=None,  # Por ahora sin Redis
        enable_cache=True
    )
    
    # Pre-calentar cache de la versión optimizada
    logger.info("Pre-calentando cache...")
    await optimized_engine.warmup_cache()
    
    # Configuración de pruebas
    test_configs = [
        {"concurrent": 1, "messages": 10, "total": 50, "name": "Single Thread - Small"},
        {"concurrent": 5, "messages": 20, "total": 100, "name": "5 Concurrent - Medium"},
        {"concurrent": 10, "messages": 30, "total": 100, "name": "10 Concurrent - Large"},
        {"concurrent": 20, "messages": 20, "total": 200, "name": "20 Concurrent - Stress"}
    ]
    
    runner = BenchmarkRunner()
    
    # Ejecutar pruebas para cada configuración
    for config in test_configs:
        logger.info(f"\n{'='*80}")
        logger.info(f"Ejecutando: {config['name']}")
        logger.info(f"Configuración: {config['concurrent']} concurrentes, {config['messages']} mensajes/conversación")
        logger.info(f"{'='*80}")
        
        # Reset resultados para esta configuración
        runner.results = {
            "original": {"latencies": [], "errors": 0, "timeouts": 0},
            "optimized": {"latencies": [], "errors": 0, "timeouts": 0, "cache_hits": 0, "cache_misses": 0}
        }
        
        # Prueba motor original
        await runner.run_concurrent_tests(
            original_engine,
            "original",
            config["concurrent"],
            config["messages"],
            config["total"]
        )
        
        # Pequeña pausa
        await asyncio.sleep(2)
        
        # Prueba motor optimizado
        await runner.run_concurrent_tests(
            optimized_engine,
            "optimized",
            config["concurrent"],
            config["messages"],
            config["total"]
        )
        
        # Generar y mostrar reporte para esta configuración
        report = runner.generate_report()
        
        print(f"\n📊 RESULTADOS - {config['name']}")
        print("="*60)
        
        # Comparar resultados
        for engine_type in ["original", "optimized"]:
            stats = report["comparison"][engine_type]["statistics"]
            print(f"\n{engine_type.upper()}:")
            print(f"  P50: {stats['p50']:.2f}ms")
            print(f"  P90: {stats['p90']:.2f}ms")
            print(f"  P95: {stats['p95']:.2f}ms")
            print(f"  P99: {stats['p99']:.2f}ms")
            print(f"  Promedio: {stats['avg']:.2f}ms ± {stats['std']:.2f}ms")
            print(f"  Errores: {report['comparison'][engine_type]['errors']}")
            print(f"  Timeouts: {report['comparison'][engine_type]['timeouts']}")
            
            if engine_type == "optimized" and "cache_hit_rate" in report["comparison"]["optimized"]:
                print(f"  Cache Hit Rate: {report['comparison']['optimized']['cache_hit_rate']:.2%}")
        
        # Mostrar mejoras
        if "improvement" in report:
            print(f"\n🚀 MEJORAS:")
            print(f"  P95 Latencia: {report['improvement']['p95_improvement']:.1f}% mejor")
            print(f"  Promedio: {report['improvement']['avg_improvement']:.1f}% mejor")
        
        # Guardar reporte detallado
        report_filename = f"benchmark_{config['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Reporte guardado en: {report_filename}")
    
    # Obtener métricas finales del motor optimizado
    if hasattr(optimized_engine, 'get_performance_metrics'):
        final_metrics = await optimized_engine.get_performance_metrics()
        print("\n📈 MÉTRICAS FINALES DEL MOTOR OPTIMIZADO:")
        print(json.dumps(final_metrics, indent=2))
    
    print("\n✅ Benchmark completado!")


if __name__ == "__main__":
    asyncio.run(run_benchmark())