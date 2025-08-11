#!/usr/bin/env python3
"""
Script de profiling para el DecisionEngineService.

Este script mide el rendimiento actual del servicio para establecer
una línea base antes de implementar optimizaciones.
"""

import asyncio
import time
import json
import statistics
from datetime import datetime
from typing import List, Dict, Any, Tuple
import logging
import cProfile
import pstats
import io
from contextlib import contextmanager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar servicios necesarios
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.integrations.supabase.resilient_client import ResilientSupabaseClient
from src.services.decision_engine_service import DecisionEngineService
from src.services.predictive_model_service import PredictiveModelService
from src.services.nlp_integration_service import NLPIntegrationService
from src.services.objection_prediction_service import ObjectionPredictionService
from src.services.needs_prediction_service import NeedsPredictionService
from src.services.conversion_prediction_service import ConversionPredictionService


class PerformanceProfiler:
    """Clase para perfilar el rendimiento del DecisionEngineService."""
    
    def __init__(self):
        self.metrics = {
            "latencies": [],
            "memory_usage": [],
            "cpu_times": [],
            "db_queries": [],
            "cache_hits": 0,
            "cache_misses": 0
        }
        
    @contextmanager
    def measure_time(self, operation_name: str):
        """Context manager para medir tiempo de ejecución."""
        start_time = time.perf_counter()
        start_cpu = time.process_time()
        
        logger.info(f"Iniciando operación: {operation_name}")
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            end_cpu = time.process_time()
            
            elapsed_time = (end_time - start_time) * 1000  # Convertir a ms
            cpu_time = (end_cpu - start_cpu) * 1000
            
            self.metrics["latencies"].append({
                "operation": operation_name,
                "elapsed_ms": elapsed_time,
                "cpu_ms": cpu_time,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"Operación {operation_name} completada en {elapsed_time:.2f}ms (CPU: {cpu_time:.2f}ms)")
    
    def calculate_percentiles(self, values: List[float]) -> Dict[str, float]:
        """Calcula percentiles de una lista de valores."""
        if not values:
            return {"p50": 0, "p90": 0, "p95": 0, "p99": 0}
            
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return {
            "p50": sorted_values[int(n * 0.50)],
            "p90": sorted_values[int(n * 0.90)],
            "p95": sorted_values[int(n * 0.95)],
            "p99": sorted_values[int(n * 0.99)] if n > 99 else sorted_values[-1],
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
            "std": statistics.stdev(values) if n > 1 else 0
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """Genera un reporte de rendimiento."""
        latencies = [m["elapsed_ms"] for m in self.metrics["latencies"]]
        cpu_times = [m["cpu_ms"] for m in self.metrics["latencies"]]
        
        report = {
            "summary": {
                "total_operations": len(self.metrics["latencies"]),
                "cache_hit_rate": self.metrics["cache_hits"] / max(1, self.metrics["cache_hits"] + self.metrics["cache_misses"]),
                "timestamp": datetime.now().isoformat()
            },
            "latency_stats": self.calculate_percentiles(latencies),
            "cpu_stats": self.calculate_percentiles(cpu_times),
            "operations_breakdown": self._get_operations_breakdown()
        }
        
        return report
    
    def _get_operations_breakdown(self) -> Dict[str, Any]:
        """Obtiene desglose de operaciones por tipo."""
        breakdown = {}
        
        for metric in self.metrics["latencies"]:
            op_name = metric["operation"]
            if op_name not in breakdown:
                breakdown[op_name] = {
                    "count": 0,
                    "total_ms": 0,
                    "latencies": []
                }
            
            breakdown[op_name]["count"] += 1
            breakdown[op_name]["total_ms"] += metric["elapsed_ms"]
            breakdown[op_name]["latencies"].append(metric["elapsed_ms"])
        
        # Calcular estadísticas para cada operación
        for op_name, data in breakdown.items():
            data["avg_ms"] = data["total_ms"] / data["count"]
            data["percentiles"] = self.calculate_percentiles(data["latencies"])
            del data["latencies"]  # Eliminar lista cruda para el reporte
        
        return breakdown


async def create_test_messages(count: int = 10) -> List[Dict[str, Any]]:
    """Crea mensajes de prueba para simular una conversación."""
    messages = []
    
    # Mensaje inicial del cliente
    messages.append({
        "role": "user",
        "content": "Hola, estoy interesado en mejorar la gestión de mi gimnasio",
        "timestamp": datetime.now().isoformat()
    })
    
    # Respuesta del agente
    messages.append({
        "role": "assistant", 
        "content": "¡Hola! Me alegra mucho que estés interesado en mejorar la gestión de tu gimnasio. NGX tiene soluciones específicas para optimizar las operaciones de gimnasios. ¿Cuál es tu principal desafío actualmente?",
        "timestamp": datetime.now().isoformat()
    })
    
    # Más intercambios
    test_exchanges = [
        ("user", "Mi principal problema es la retención de clientes"),
        ("assistant", "Entiendo perfectamente. La retención de clientes es crucial. NGX AGENTS ACCESS incluye herramientas específicas para mejorar la retención. ¿Cuántos clientes tienes actualmente?"),
        ("user", "Tenemos unos 500 clientes activos, pero perdemos un 10% cada mes"),
        ("assistant", "Un 10% de churn mensual es significativo. Con NGX podemos reducir eso a menos del 5%. Nuestro sistema de AI personaliza la experiencia de cada cliente. ¿Has considerado implementar programas de fidelización automatizados?"),
        ("user", "No estoy seguro del costo, ¿cuánto sería la inversión?"),
        ("assistant", "Entiendo tu preocupación sobre la inversión. NGX ofrece diferentes planes. Para un gimnasio con 500 clientes, el plan PRO a $349/mes sería ideal. El ROI típico es del 300% en los primeros 6 meses.")
    ]
    
    for role, content in test_exchanges[:min(count-2, len(test_exchanges))]:
        messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    return messages


async def profile_decision_engine():
    """Perfila el rendimiento del DecisionEngineService."""
    profiler = PerformanceProfiler()
    
    logger.info("Inicializando servicios...")
    
    # Inicializar Supabase
    supabase = ResilientSupabaseClient()
    
    # Inicializar servicios dependientes
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
    
    # Inicializar DecisionEngineService
    decision_engine = DecisionEngineService(
        supabase=supabase,
        predictive_model_service=predictive_model_service,
        nlp_integration_service=nlp_service,
        objection_prediction_service=objection_service,
        needs_prediction_service=needs_service,
        conversion_prediction_service=conversion_service
    )
    
    logger.info("Servicios inicializados. Comenzando pruebas de rendimiento...")
    
    # Ejecutar pruebas con diferentes tamaños de conversación
    conversation_sizes = [5, 10, 20, 50]
    iterations_per_size = 10
    
    for size in conversation_sizes:
        logger.info(f"\n=== Probando con {size} mensajes ===")
        messages = await create_test_messages(size)
        
        for i in range(iterations_per_size):
            conversation_id = f"test_conv_{size}_{i}"
            
            # Test 1: optimize_conversation_flow
            with profiler.measure_time(f"optimize_flow_{size}_msgs"):
                result = await decision_engine.optimize_conversation_flow(
                    conversation_id=conversation_id,
                    messages=messages,
                    customer_profile={
                        "business_type": "gym",
                        "size": "medium",
                        "current_clients": 500
                    }
                )
            
            # Test 2: adapt_strategy_realtime
            with profiler.measure_time(f"adapt_strategy_{size}_msgs"):
                feedback = {
                    "type": "objection",
                    "value": 0.8,
                    "details": {"objection_type": "price"}
                }
                
                adapted = await decision_engine.adapt_strategy_realtime(
                    conversation_id=conversation_id,
                    messages=messages,
                    feedback=feedback
                )
            
            # Test 3: prioritize_objectives
            with profiler.measure_time(f"prioritize_objectives_{size}_msgs"):
                objectives = await decision_engine.prioritize_objectives(
                    conversation_id=conversation_id,
                    messages=messages
                )
            
            # Pequeña pausa para evitar sobrecarga
            await asyncio.sleep(0.1)
    
    # Generar reporte
    report = profiler.generate_report()
    
    # Guardar reporte
    report_filename = f"decision_engine_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Imprimir resumen
    print("\n" + "="*80)
    print("RESUMEN DE RENDIMIENTO - DecisionEngineService")
    print("="*80)
    print(f"\nTotal de operaciones: {report['summary']['total_operations']}")
    print(f"Tasa de aciertos de caché: {report['summary']['cache_hit_rate']:.2%}")
    
    print("\n--- Estadísticas de Latencia (ms) ---")
    latency_stats = report['latency_stats']
    print(f"P50: {latency_stats['p50']:.2f}ms")
    print(f"P90: {latency_stats['p90']:.2f}ms")
    print(f"P95: {latency_stats['p95']:.2f}ms")
    print(f"P99: {latency_stats['p99']:.2f}ms")
    print(f"Promedio: {latency_stats['avg']:.2f}ms ± {latency_stats['std']:.2f}ms")
    
    print("\n--- Desglose por Operación ---")
    for op_name, data in report['operations_breakdown'].items():
        print(f"\n{op_name}:")
        print(f"  - Llamadas: {data['count']}")
        print(f"  - Promedio: {data['avg_ms']:.2f}ms")
        print(f"  - P95: {data['percentiles']['p95']:.2f}ms")
    
    print(f"\n✅ Reporte guardado en: {report_filename}")
    
    # Análisis de cuellos de botella
    print("\n" + "="*80)
    print("ANÁLISIS DE CUELLOS DE BOTELLA")
    print("="*80)
    
    # Identificar operaciones más lentas
    slowest_ops = sorted(
        report['operations_breakdown'].items(),
        key=lambda x: x[1]['percentiles']['p95'],
        reverse=True
    )[:3]
    
    print("\nOperaciones más lentas (P95):")
    for op_name, data in slowest_ops:
        print(f"  - {op_name}: {data['percentiles']['p95']:.2f}ms")
    
    # Recomendaciones basadas en métricas
    print("\n🎯 RECOMENDACIONES:")
    
    if latency_stats['p95'] > 500:
        print("❌ P95 latency > 500ms - Se requiere optimización urgente")
        print("   - Implementar caché L1/L2")
        print("   - Paralelizar llamadas a servicios")
        print("   - Optimizar consultas a base de datos")
    else:
        print("✅ P95 latency < 500ms - Rendimiento aceptable")
    
    if report['summary']['cache_hit_rate'] < 0.1:
        print("❌ Tasa de caché muy baja - Implementar sistema de caché")
    
    # Análisis de escalabilidad
    print("\n📊 ANÁLISIS DE ESCALABILIDAD:")
    
    # Calcular degradación de rendimiento por tamaño de conversación
    size_performance = {}
    for op_name, data in report['operations_breakdown'].items():
        parts = op_name.split('_')
        if len(parts) >= 3 and parts[-1] == 'msgs':
            size = int(parts[-2])
            op_type = '_'.join(parts[:-2])
            
            if op_type not in size_performance:
                size_performance[op_type] = {}
            
            size_performance[op_type][size] = data['avg_ms']
    
    for op_type, sizes in size_performance.items():
        if len(sizes) > 1:
            sorted_sizes = sorted(sizes.items())
            first_size, first_time = sorted_sizes[0]
            last_size, last_time = sorted_sizes[-1]
            
            degradation = (last_time - first_time) / first_time * 100
            
            print(f"\n{op_type}:")
            print(f"  - {first_size} msgs: {first_time:.2f}ms")
            print(f"  - {last_size} msgs: {last_time:.2f}ms")
            print(f"  - Degradación: {degradation:.1f}%")
            
            if degradation > 100:
                print("  ⚠️  Degradación significativa con el tamaño")


async def run_cpu_profile():
    """Ejecuta profiling detallado de CPU."""
    logger.info("Ejecutando profiling de CPU...")
    
    pr = cProfile.Profile()
    pr.enable()
    
    # Ejecutar operaciones de prueba
    await profile_decision_engine()
    
    pr.disable()
    
    # Generar estadísticas
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(20)  # Top 20 funciones
    
    # Guardar resultados
    cpu_profile_filename = f"cpu_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(cpu_profile_filename, 'w') as f:
        f.write(s.getvalue())
    
    print(f"\n📊 Perfil de CPU guardado en: {cpu_profile_filename}")


if __name__ == "__main__":
    # Ejecutar profiling principal
    asyncio.run(profile_decision_engine())
    
    # Opcionalmente, ejecutar profiling de CPU
    # asyncio.run(run_cpu_profile())