#!/usr/bin/env python3
"""
Test de A/B Testing Automático - NGX Voice Sales Agent

Verificar:
- Multi-Armed Bandit activo
- Thompson Sampling funcionando
- Experimentos concurrentes
- Auto-optimización de prompts
"""

import asyncio
import aiohttp
import json
import os
from typing import Dict, List, Any, Tuple
from datetime import datetime
import random
import statistics

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")


class ABTestingBanditTester:
    """Evalúa el sistema de A/B testing con Multi-Armed Bandit."""
    
    def __init__(self):
        self.api_url = API_URL
        self.experiment_results = {}
        
    async def test_multi_armed_bandit(self) -> Dict[str, Any]:
        """
        Verifica que el Multi-Armed Bandit está optimizando variantes.
        """
        print("\n🎰 TEST 1: Multi-Armed Bandit Active")
        print("=" * 50)
        
        try:
            async with aiohttp.ClientSession() as session:
                # Obtener experimentos activos de A/B testing
                async with session.get(
                    f"{self.api_url}/ab-experiments"
                ) as response:
                    if response.status == 200:
                        experiments = await response.json()
                        print(f"📊 Experimentos A/B activos: {len(experiments)}")
                        
                        bandit_results = []
                        
                        for exp in experiments:
                            exp_type = exp.get("experiment_type", "")
                            if "bandit" in exp_type.lower() or "thompson" in exp_type.lower():
                                print(f"\n🎯 Experimento Bandit: {exp.get('name', 'Unknown')}")
                                print(f"   Variantes: {exp.get('variant_count', 0)}")
                                
                                # Verificar distribución de Thompson Sampling
                                if "variant_performance" in exp:
                                    performances = exp["variant_performance"]
                                    print(f"   Performance por variante:")
                                    
                                    for variant, perf in performances.items():
                                        print(f"     - {variant}: {perf.get('success_rate', 0):.2%} "
                                              f"({perf.get('samples', 0)} muestras)")
                                    
                                    # Verificar que está explorando y explotando
                                    sample_counts = [p.get("samples", 0) for p in performances.values()]
                                    if sample_counts:
                                        exploration_ratio = min(sample_counts) / max(sample_counts)
                                        
                                        bandit_results.append({
                                            "experiment_id": exp.get("id"),
                                            "name": exp.get("name"),
                                            "is_exploring": exploration_ratio > 0.1,
                                            "is_exploiting": max(sample_counts) > sum(sample_counts) * 0.4,
                                            "variant_count": exp.get("variant_count", 0),
                                            "total_samples": sum(sample_counts)
                                        })
                        
                        return {
                            "test_name": "multi_armed_bandit",
                            "total_experiments": len(experiments),
                            "bandit_experiments": len(bandit_results),
                            "active_bandits": len([b for b in bandit_results if b["is_exploring"] and b["is_exploiting"]]),
                            "results": bandit_results
                        }
                    else:
                        return {
                            "test_name": "multi_armed_bandit",
                            "error": f"API returned status {response.status}"
                        }
                        
        except Exception as e:
            return {
                "test_name": "multi_armed_bandit",
                "error": str(e)
            }
    
    async def test_concurrent_experiments(self) -> Dict[str, Any]:
        """
        Verifica múltiples experimentos ejecutándose simultáneamente.
        """
        print("\n🔬 TEST 2: Experimentos Concurrentes")
        print("=" * 50)
        
        # Simular múltiples conversaciones para generar datos de experimentos
        test_profiles = [
            {"name": "Test User 1", "occupation": "CEO", "age": 45},
            {"name": "Test User 2", "occupation": "Doctor", "age": 50},
            {"name": "Test User 3", "occupation": "Entrepreneur", "age": 35},
            {"name": "Test User 4", "occupation": "Manager", "age": 40},
            {"name": "Test User 5", "occupation": "Consultant", "age": 38}
        ]
        
        experiment_variants = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                # Ejecutar 5 conversaciones en paralelo
                tasks = []
                for profile in test_profiles:
                    task = self._run_experiment_conversation(session, profile)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Analizar variantes usadas
                for i, result in enumerate(results):
                    if isinstance(result, dict) and "experiment_variants" in result:
                        for exp_name, variant in result["experiment_variants"].items():
                            if exp_name not in experiment_variants:
                                experiment_variants[exp_name] = set()
                            experiment_variants[exp_name].add(variant)
                
                # Verificar concurrencia
                concurrent_experiments = len(experiment_variants)
                avg_variants_per_experiment = statistics.mean(
                    [len(variants) for variants in experiment_variants.values()]
                ) if experiment_variants else 0
                
                print(f"\n📊 Resultados de concurrencia:")
                print(f"   Experimentos únicos detectados: {concurrent_experiments}")
                print(f"   Promedio de variantes por experimento: {avg_variants_per_experiment:.1f}")
                
                for exp_name, variants in experiment_variants.items():
                    print(f"   - {exp_name}: {len(variants)} variantes")
                
                return {
                    "test_name": "concurrent_experiments",
                    "conversations_run": len(test_profiles),
                    "successful_conversations": len([r for r in results if isinstance(r, dict) and "error" not in r]),
                    "concurrent_experiments": concurrent_experiments,
                    "avg_variants_per_experiment": avg_variants_per_experiment,
                    "experiment_details": {k: list(v) for k, v in experiment_variants.items()}
                }
                
        except Exception as e:
            return {
                "test_name": "concurrent_experiments",
                "error": str(e)
            }
    
    async def test_prompt_optimization(self) -> Dict[str, Any]:
        """
        Verifica la optimización automática de prompts.
        """
        print("\n🧬 TEST 3: Auto-optimización de Prompts")
        print("=" * 50)
        
        try:
            async with aiohttp.ClientSession() as session:
                # Obtener historial de optimizaciones de prompts
                async with session.get(
                    f"{self.api_url}/prompt-optimizations"
                ) as response:
                    if response.status == 200:
                        optimizations = await response.json()
                        print(f"📝 Optimizaciones de prompts encontradas: {len(optimizations)}")
                        
                        optimization_metrics = []
                        
                        for opt in optimizations[:5]:  # Analizar últimas 5
                            print(f"\n🔍 Optimización: {opt.get('prompt_type', 'Unknown')}")
                            print(f"   Timestamp: {opt.get('created_at', 'Unknown')}")
                            
                            if "performance_metrics" in opt:
                                metrics = opt["performance_metrics"]
                                improvement = metrics.get("improvement_percentage", 0)
                                confidence = metrics.get("confidence_score", 0)
                                generation = metrics.get("generation", 0)
                                
                                print(f"   Mejora: {improvement:.1f}%")
                                print(f"   Confianza: {confidence:.2%}")
                                print(f"   Generación: {generation}")
                                
                                optimization_metrics.append({
                                    "prompt_type": opt.get('prompt_type'),
                                    "improvement": improvement,
                                    "confidence": confidence,
                                    "generation": generation,
                                    "is_improving": improvement > 0
                                })
                        
                        # Análisis global
                        if optimization_metrics:
                            avg_improvement = statistics.mean([m["improvement"] for m in optimization_metrics])
                            improving_prompts = len([m for m in optimization_metrics if m["is_improving"]])
                            
                            return {
                                "test_name": "prompt_optimization",
                                "total_optimizations": len(optimizations),
                                "analyzed_optimizations": len(optimization_metrics),
                                "avg_improvement_percentage": avg_improvement,
                                "improving_prompts": improving_prompts,
                                "optimization_active": avg_improvement > 0,
                                "details": optimization_metrics
                            }
                        else:
                            return {
                                "test_name": "prompt_optimization",
                                "status": "no_optimizations_found",
                                "optimization_active": False
                            }
                    else:
                        # Si no hay endpoint, verificar en experimentos generales
                        return await self._check_prompt_experiments(session)
                        
        except Exception as e:
            # Si falla, intentar verificar de otra forma
            try:
                async with aiohttp.ClientSession() as session:
                    return await self._check_prompt_experiments(session)
            except:
                return {
                    "test_name": "prompt_optimization",
                    "error": str(e)
                }
    
    async def _run_experiment_conversation(self, session: aiohttp.ClientSession, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una conversación para detectar experimentos activos.
        """
        try:
            # Iniciar conversación
            async with session.post(
                f"{self.api_url}/conversations/start",
                json={"customer_data": profile}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    conversation_id = data["conversation_id"]
                    
                    # Enviar algunos mensajes
                    messages = [
                        "Hola, necesito información sobre sus programas",
                        "¿Cuál es la diferencia entre los diferentes niveles?",
                        "¿Qué resultados puedo esperar?"
                    ]
                    
                    experiment_variants = {}
                    
                    for msg in messages:
                        async with session.post(
                            f"{self.api_url}/conversations/{conversation_id}/message",
                            json={"message": msg}
                        ) as msg_response:
                            if msg_response.status == 200:
                                msg_data = await msg_response.json()
                                
                                # Capturar información de experimentos
                                if "active_experiments" in msg_data:
                                    for exp in msg_data["active_experiments"]:
                                        exp_name = exp.get("name", "unknown")
                                        variant = exp.get("variant", "control")
                                        experiment_variants[exp_name] = variant
                    
                    return {
                        "profile": profile["name"],
                        "conversation_id": conversation_id,
                        "experiment_variants": experiment_variants,
                        "experiments_count": len(experiment_variants)
                    }
                else:
                    return {"error": f"Status {response.status}"}
                    
        except Exception as e:
            return {"error": str(e)}
    
    async def _check_prompt_experiments(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """
        Verifica experimentos de prompts de forma alternativa.
        """
        try:
            async with session.get(
                f"{self.api_url}/experiments/active"
            ) as response:
                if response.status == 200:
                    experiments = await response.json()
                    
                    prompt_experiments = [
                        exp for exp in experiments 
                        if "prompt" in exp.get("experiment_type", "").lower()
                    ]
                    
                    if prompt_experiments:
                        return {
                            "test_name": "prompt_optimization",
                            "prompt_experiments_found": len(prompt_experiments),
                            "optimization_active": True,
                            "method": "alternative_check"
                        }
                    else:
                        return {
                            "test_name": "prompt_optimization",
                            "optimization_active": False,
                            "method": "alternative_check"
                        }
        except:
            return {
                "test_name": "prompt_optimization",
                "optimization_active": False,
                "error": "Could not verify prompt optimization"
            }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Ejecuta todos los tests de A/B testing automático.
        """
        print("\n🎲 INICIANDO TESTS DE A/B TESTING AUTOMÁTICO")
        print("=" * 70)
        
        all_results = {
            "test_suite": "A/B Testing Multi-Armed Bandit",
            "timestamp": datetime.now().isoformat(),
            "tests": []
        }
        
        # Test 1: Multi-Armed Bandit
        bandit_test = await self.test_multi_armed_bandit()
        all_results["tests"].append(bandit_test)
        
        # Test 2: Experimentos concurrentes
        concurrent_test = await self.test_concurrent_experiments()
        all_results["tests"].append(concurrent_test)
        
        # Test 3: Optimización de prompts
        prompt_test = await self.test_prompt_optimization()
        all_results["tests"].append(prompt_test)
        
        # Calcular métricas globales
        successful_tests = [t for t in all_results["tests"] if "error" not in t]
        
        all_results["summary"] = {
            "total_tests": len(all_results["tests"]),
            "successful_tests": len(successful_tests),
            "bandit_active": any(t.get("active_bandits", 0) > 0 for t in successful_tests),
            "concurrent_experiments_detected": any(t.get("concurrent_experiments", 0) > 1 for t in successful_tests),
            "prompt_optimization_active": any(t.get("optimization_active", False) for t in successful_tests)
        }
        
        # Resumen
        print("\n📊 RESUMEN DE RESULTADOS")
        print("=" * 70)
        
        if all_results["summary"]["bandit_active"]:
            print("✅ Multi-Armed Bandit activo y optimizando")
        else:
            print("⚠️  Multi-Armed Bandit no detectado")
        
        if all_results["summary"]["concurrent_experiments_detected"]:
            print("✅ Múltiples experimentos ejecutándose concurrentemente")
        else:
            print("⚠️  No se detectaron experimentos concurrentes")
        
        if all_results["summary"]["prompt_optimization_active"]:
            print("✅ Optimización automática de prompts activa")
        else:
            print("⚠️  Optimización de prompts no detectada")
        
        # Guardar resultados
        results_file = f"tests/capabilities/results/ab_testing_bandit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Resultados guardados en: {results_file}")
        
        return all_results


async def main():
    """Función principal para ejecutar los tests."""
    tester = ABTestingBanditTester()
    results = await tester.run_all_tests()
    
    # Determinar éxito
    summary = results.get("summary", {})
    features_active = sum([
        summary.get("bandit_active", False),
        summary.get("concurrent_experiments_detected", False),
        summary.get("prompt_optimization_active", False)
    ])
    
    success = features_active >= 2  # Al menos 2 de 3 características activas
    
    if success:
        print("\n✅ A/B TESTING AUTOMÁTICO: FUNCIONANDO")
        print(f"   Características activas: {features_active}/3")
    else:
        print("\n❌ A/B TESTING AUTOMÁTICO: REQUIERE REVISIÓN")
        print(f"   Características activas: {features_active}/3 (mínimo: 2)")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)