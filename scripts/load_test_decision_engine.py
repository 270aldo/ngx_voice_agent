#!/usr/bin/env python3
"""
Script de load testing para el DecisionEngineService optimizado.
Simula carga realista con múltiples usuarios concurrentes.
"""

import asyncio
import time
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import logging
from dataclasses import dataclass
import aiohttp
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
class LoadTestConfig:
    """Configuración para el load test."""
    initial_users: int = 10
    max_users: int = 100
    ramp_up_time: int = 60  # segundos
    test_duration: int = 300  # segundos
    messages_per_conversation: Tuple[int, int] = (5, 50)  # min, max
    think_time: Tuple[float, float] = (0.5, 2.0)  # segundos entre requests
    spike_enabled: bool = True
    spike_users: int = 200
    spike_duration: int = 30


class VirtualUser:
    """Simula un usuario virtual interactuando con el sistema."""
    
    def __init__(self, user_id: int, engine: OptimizedDecisionEngineService, config: LoadTestConfig):
        self.user_id = user_id
        self.engine = engine
        self.config = config
        self.conversation_id = f"load_test_user_{user_id}_{int(time.time())}"
        self.messages = []
        self.metrics = {
            "requests": 0,
            "successes": 0,
            "errors": 0,
            "latencies": []
        }
        
        # Perfil de usuario aleatorio
        self.profile = self._generate_user_profile()
    
    def _generate_user_profile(self) -> Dict[str, Any]:
        """Genera un perfil de usuario aleatorio."""
        business_types = ["gym", "studio", "trainer", "wellness_center"]
        sizes = ["small", "medium", "large"]
        
        return {
            "business_type": random.choice(business_types),
            "size": random.choice(sizes),
            "current_clients": random.randint(50, 1000),
            "monthly_churn": random.uniform(0.05, 0.20),
            "budget": random.choice(["low", "medium", "high"]),
            "urgency": random.choice(["immediate", "this_quarter", "exploring"])
        }
    
    async def generate_message(self) -> Dict[str, Any]:
        """Genera un mensaje realista basado en el contexto."""
        message_templates = {
            "initial": [
                "Hola, necesito ayuda para gestionar mi {business_type}",
                "Estoy buscando una solución para mejorar la retención de clientes",
                "¿Qué pueden ofrecer para un {business_type} {size}?",
                "Tengo {current_clients} clientes y necesito crecer"
            ],
            "price_inquiry": [
                "¿Cuánto cuesta el servicio?",
                "¿Qué planes tienen disponibles?",
                "Mi presupuesto es {budget}, ¿qué me recomiendan?",
                "¿Hay descuentos por pago anual?"
            ],
            "feature_inquiry": [
                "¿Incluye automatización de marketing?",
                "¿Cómo funciona la IA para retención?",
                "¿Puedo integrar con mi sistema actual?",
                "¿Qué reportes puedo obtener?"
            ],
            "objection": [
                "Me parece un poco caro",
                "Necesito pensarlo más",
                "¿Qué garantías ofrecen?",
                "Ya tengo otro sistema"
            ],
            "closing": [
                "Estoy listo para empezar",
                "¿Cómo es el proceso de onboarding?",
                "Quiero contratar el plan {size}",
                "Envíame el contrato"
            ]
        }
        
        # Determinar tipo de mensaje basado en el progreso
        num_messages = len(self.messages)
        if num_messages == 0:
            msg_type = "initial"
        elif num_messages < 3:
            msg_type = random.choice(["price_inquiry", "feature_inquiry"])
        elif num_messages < 6:
            msg_type = random.choice(["feature_inquiry", "objection"])
        else:
            msg_type = random.choice(["objection", "closing"])
        
        # Seleccionar y formatear template
        template = random.choice(message_templates[msg_type])
        content = template.format(**self.profile, current_clients=self.profile["current_clients"])
        
        return {
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
    
    async def simulate_conversation(self) -> None:
        """Simula una conversación completa."""
        # Determinar número de mensajes para esta conversación
        num_messages = random.randint(*self.config.messages_per_conversation)
        
        logger.debug(f"Usuario {self.user_id} iniciando conversación con {num_messages} mensajes")
        
        for i in range(num_messages):
            # Generar mensaje del usuario
            user_message = await self.generate_message()
            self.messages.append(user_message)
            
            # Simular respuesta del asistente (no la generamos, solo la agregamos)
            assistant_message = {
                "role": "assistant",
                "content": "Respuesta simulada del asistente",
                "timestamp": datetime.now().isoformat()
            }
            self.messages.append(assistant_message)
            
            # Hacer request al motor de decisiones
            start_time = time.perf_counter()
            self.metrics["requests"] += 1
            
            try:
                result = await asyncio.wait_for(
                    self.engine.optimize_conversation_flow(
                        conversation_id=self.conversation_id,
                        messages=self.messages,
                        customer_profile=self.profile
                    ),
                    timeout=10.0
                )
                
                latency = (time.perf_counter() - start_time) * 1000
                self.metrics["latencies"].append(latency)
                self.metrics["successes"] += 1
                
                # Log si la latencia es alta
                if latency > 1000:
                    logger.warning(f"Usuario {self.user_id}: Latencia alta {latency:.2f}ms")
                
            except asyncio.TimeoutError:
                self.metrics["errors"] += 1
                logger.error(f"Usuario {self.user_id}: Timeout en request")
            except Exception as e:
                self.metrics["errors"] += 1
                logger.error(f"Usuario {self.user_id}: Error {e}")
            
            # Think time entre mensajes
            think_time = random.uniform(*self.config.think_time)
            await asyncio.sleep(think_time)
    
    async def run(self) -> Dict[str, Any]:
        """Ejecuta la simulación del usuario."""
        await self.simulate_conversation()
        return self.metrics


class LoadTestRunner:
    """Ejecutor principal del load test."""
    
    def __init__(self, engine: OptimizedDecisionEngineService, config: LoadTestConfig):
        self.engine = engine
        self.config = config
        self.metrics = {
            "total_requests": 0,
            "total_successes": 0,
            "total_errors": 0,
            "all_latencies": [],
            "timeline": []
        }
        self.active_users = 0
        self.start_time = None
    
    async def ramp_up_users(self) -> List[asyncio.Task]:
        """Incrementa gradualmente el número de usuarios."""
        tasks = []
        users_per_second = (self.config.max_users - self.config.initial_users) / self.config.ramp_up_time
        
        logger.info(f"Iniciando ramp-up: {self.config.initial_users} → {self.config.max_users} usuarios en {self.config.ramp_up_time}s")
        
        # Iniciar usuarios iniciales
        for i in range(self.config.initial_users):
            user = VirtualUser(i, self.engine, self.config)
            task = asyncio.create_task(self._run_user(user))
            tasks.append(task)
            self.active_users += 1
        
        # Ramp-up gradual
        current_users = self.config.initial_users
        ramp_up_start = time.time()
        
        while current_users < self.config.max_users:
            await asyncio.sleep(1)  # Esperar 1 segundo
            
            # Calcular cuántos usuarios agregar
            elapsed = time.time() - ramp_up_start
            target_users = min(
                self.config.initial_users + int(elapsed * users_per_second),
                self.config.max_users
            )
            
            # Agregar nuevos usuarios
            while current_users < target_users:
                user = VirtualUser(current_users, self.engine, self.config)
                task = asyncio.create_task(self._run_user(user))
                tasks.append(task)
                current_users += 1
                self.active_users += 1
            
            # Log progreso
            if current_users % 10 == 0:
                logger.info(f"Usuarios activos: {self.active_users}")
        
        return tasks
    
    async def _run_user(self, user: VirtualUser) -> None:
        """Ejecuta un usuario virtual hasta que termine el test."""
        user_start = time.time()
        
        while time.time() - self.start_time < self.config.test_duration:
            try:
                metrics = await user.run()
                self._update_metrics(metrics)
            except Exception as e:
                logger.error(f"Error en usuario {user.user_id}: {e}")
            
            # Pequeña pausa antes de iniciar nueva conversación
            await asyncio.sleep(random.uniform(2, 5))
        
        self.active_users -= 1
        logger.debug(f"Usuario {user.user_id} finalizado después de {time.time() - user_start:.2f}s")
    
    def _update_metrics(self, user_metrics: Dict[str, Any]) -> None:
        """Actualiza métricas globales con las de un usuario."""
        self.metrics["total_requests"] += user_metrics["requests"]
        self.metrics["total_successes"] += user_metrics["successes"]
        self.metrics["total_errors"] += user_metrics["errors"]
        self.metrics["all_latencies"].extend(user_metrics["latencies"])
        
        # Registrar punto en timeline
        self.metrics["timeline"].append({
            "timestamp": time.time() - self.start_time,
            "active_users": self.active_users,
            "requests_per_second": user_metrics["requests"],
            "avg_latency": np.mean(user_metrics["latencies"]) if user_metrics["latencies"] else 0,
            "error_rate": user_metrics["errors"] / max(1, user_metrics["requests"])
        })
    
    async def simulate_spike(self) -> None:
        """Simula un spike de tráfico."""
        if not self.config.spike_enabled:
            return
        
        logger.warning(f"⚡ INICIANDO SPIKE: {self.config.spike_users} usuarios adicionales!")
        
        spike_tasks = []
        for i in range(self.config.spike_users):
            user = VirtualUser(1000 + i, self.engine, self.config)
            task = asyncio.create_task(self._run_spike_user(user))
            spike_tasks.append(task)
            self.active_users += 1
        
        # Esperar duración del spike
        await asyncio.sleep(self.config.spike_duration)
        
        # Cancelar tareas del spike
        for task in spike_tasks:
            task.cancel()
        
        self.active_users -= len(spike_tasks)
        logger.info("Spike finalizado")
    
    async def _run_spike_user(self, user: VirtualUser) -> None:
        """Ejecuta un usuario del spike (más agresivo)."""
        try:
            while True:
                metrics = await user.run()
                self._update_metrics(metrics)
                # Spike users tienen menos think time
                await asyncio.sleep(random.uniform(0.1, 0.5))
        except asyncio.CancelledError:
            pass
    
    async def run(self) -> Dict[str, Any]:
        """Ejecuta el load test completo."""
        self.start_time = time.time()
        
        logger.info("🚀 Iniciando Load Test")
        logger.info(f"Configuración: {self.config}")
        
        # Fase 1: Ramp-up
        user_tasks = await self.ramp_up_users()
        
        # Fase 2: Carga sostenida
        logger.info(f"Carga estable con {self.active_users} usuarios")
        
        # Programar spike si está habilitado
        if self.config.spike_enabled:
            spike_time = self.config.test_duration * 0.6  # Spike al 60% del test
            asyncio.create_task(self._schedule_spike(spike_time))
        
        # Esperar a que termine el test
        remaining_time = self.config.test_duration - (time.time() - self.start_time)
        if remaining_time > 0:
            await asyncio.sleep(remaining_time)
        
        # Cancelar tareas restantes
        logger.info("Finalizando test...")
        for task in user_tasks:
            if not task.done():
                task.cancel()
        
        # Esperar a que todas las tareas terminen
        await asyncio.gather(*user_tasks, return_exceptions=True)
        
        # Generar reporte final
        return self._generate_report()
    
    async def _schedule_spike(self, delay: float) -> None:
        """Programa un spike después del delay especificado."""
        await asyncio.sleep(delay)
        await self.simulate_spike()
    
    def _generate_report(self) -> Dict[str, Any]:
        """Genera reporte del load test."""
        # Calcular estadísticas
        latencies = self.metrics["all_latencies"]
        if latencies:
            latencies_sorted = sorted(latencies)
            n = len(latencies_sorted)
            
            latency_stats = {
                "p50": latencies_sorted[int(n * 0.50)],
                "p90": latencies_sorted[int(n * 0.90)],
                "p95": latencies_sorted[int(n * 0.95)],
                "p99": latencies_sorted[int(n * 0.99)] if n > 99 else latencies_sorted[-1],
                "avg": np.mean(latencies),
                "min": min(latencies),
                "max": max(latencies),
                "std": np.std(latencies)
            }
        else:
            latency_stats = {}
        
        # Calcular throughput
        test_duration = time.time() - self.start_time
        throughput = self.metrics["total_requests"] / test_duration
        
        report = {
            "test_config": {
                "initial_users": self.config.initial_users,
                "max_users": self.config.max_users,
                "test_duration": test_duration,
                "spike_enabled": self.config.spike_enabled
            },
            "summary": {
                "total_requests": self.metrics["total_requests"],
                "total_successes": self.metrics["total_successes"],
                "total_errors": self.metrics["total_errors"],
                "error_rate": self.metrics["total_errors"] / max(1, self.metrics["total_requests"]),
                "throughput_rps": throughput,
                "avg_latency_ms": latency_stats.get("avg", 0)
            },
            "latency_percentiles": latency_stats,
            "timeline": self.metrics["timeline"][-100:]  # Últimos 100 puntos
        }
        
        return report


async def main():
    """Función principal del load test."""
    logger.info("Inicializando servicios...")
    
    # Configuración del test
    config = LoadTestConfig(
        initial_users=10,
        max_users=100,
        ramp_up_time=60,
        test_duration=300,  # 5 minutos
        messages_per_conversation=(5, 30),
        think_time=(0.5, 2.0),
        spike_enabled=True,
        spike_users=200,
        spike_duration=30
    )
    
    # Inicializar servicios
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
    
    # Ejecutar load test
    runner = LoadTestRunner(engine, config)
    report = await runner.run()
    
    # Mostrar resultados
    print("\n" + "="*80)
    print("📊 RESULTADOS DEL LOAD TEST")
    print("="*80)
    
    print(f"\n🎯 RESUMEN:")
    print(f"  Total Requests: {report['summary']['total_requests']:,}")
    print(f"  Exitosos: {report['summary']['total_successes']:,}")
    print(f"  Errores: {report['summary']['total_errors']:,}")
    print(f"  Tasa de Error: {report['summary']['error_rate']:.2%}")
    print(f"  Throughput: {report['summary']['throughput_rps']:.2f} req/s")
    
    if report["latency_percentiles"]:
        print(f"\n⏱️  LATENCIAS:")
        print(f"  P50: {report['latency_percentiles']['p50']:.2f}ms")
        print(f"  P90: {report['latency_percentiles']['p90']:.2f}ms")
        print(f"  P95: {report['latency_percentiles']['p95']:.2f}ms")
        print(f"  P99: {report['latency_percentiles']['p99']:.2f}ms")
        print(f"  Promedio: {report['latency_percentiles']['avg']:.2f}ms")
        
        # Verificar objetivo P95 < 500ms
        if report['latency_percentiles']['p95'] < 500:
            print(f"\n✅ OBJETIVO CUMPLIDO: P95 < 500ms")
        else:
            print(f"\n❌ OBJETIVO NO CUMPLIDO: P95 = {report['latency_percentiles']['p95']:.2f}ms > 500ms")
    
    # Obtener métricas del motor
    if hasattr(engine, 'get_performance_metrics'):
        engine_metrics = await engine.get_performance_metrics()
        if "cache" in engine_metrics:
            print(f"\n💾 CACHE:")
            print(f"  Hit Rate: {engine_metrics['cache']['hit_rate']:.2%}")
            print(f"  L1 Hit Rate: {engine_metrics['cache']['l1_hit_rate']:.2%}")
    
    # Guardar reporte completo
    report_filename = f"load_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Reporte completo guardado en: {report_filename}")
    
    # Análisis de la línea de tiempo
    if report["timeline"]:
        print(f"\n📈 ANÁLISIS TEMPORAL:")
        # Encontrar momento de mayor carga
        max_users_point = max(report["timeline"], key=lambda x: x["active_users"])
        print(f"  Máximo usuarios concurrentes: {max_users_point['active_users']}")
        
        # Encontrar momento de mayor latencia
        max_latency_point = max(report["timeline"], key=lambda x: x["avg_latency"])
        print(f"  Máxima latencia promedio: {max_latency_point['avg_latency']:.2f}ms")
        
        # Detectar degradación
        early_latency = np.mean([p["avg_latency"] for p in report["timeline"][:10] if p["avg_latency"] > 0])
        late_latency = np.mean([p["avg_latency"] for p in report["timeline"][-10:] if p["avg_latency"] > 0])
        
        if early_latency > 0 and late_latency > 0:
            degradation = (late_latency - early_latency) / early_latency * 100
            print(f"  Degradación de latencia: {degradation:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())