#!/usr/bin/env python3
"""
Test de HIE Agents Mention - NGX Voice Sales Agent

Verificar que menciona correctamente los 11 agentes HIE:
- NEXUS (Coordinador)
- BLAZE (Marketing)
- SAGE (Estrategia)
- WAVE (Comunicación)
- SPARK (Creatividad)
- NOVA (Innovación)
- LUNA (Análisis emocional)
- STELLA (Motivación)
- CODE (Técnico)
- GUARDIAN (Protección)
- NODE (Red)
"""

import asyncio
import aiohttp
import json
import os
from typing import Dict, List, Any, Set
from datetime import datetime
import re

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")


class HIEAgentsMentionTester:
    """Evalúa las menciones de los agentes HIE en conversaciones."""
    
    def __init__(self):
        self.api_url = API_URL
        self.hie_agents = {
            "NEXUS": {
                "role": "Coordinador General",
                "triggers": ["coordinación", "integración", "visión general", "orquestar"]
            },
            "BLAZE": {
                "role": "Marketing y Comunicación",
                "triggers": ["marketing", "branding", "posicionamiento", "mensaje de marca"]
            },
            "SAGE": {
                "role": "Estrategia y Planificación",
                "triggers": ["estrategia", "planificación", "roadmap", "objetivos a largo plazo"]
            },
            "WAVE": {
                "role": "Comunicación y Mensajería",
                "triggers": ["comunicación", "mensajes", "copywriting", "narrativa"]
            },
            "SPARK": {
                "role": "Creatividad e Innovación",
                "triggers": ["creatividad", "ideas innovadoras", "brainstorming", "pensar diferente"]
            },
            "NOVA": {
                "role": "Innovación Tecnológica",
                "triggers": ["tecnología", "innovación", "automatización", "IA avanzada"]
            },
            "LUNA": {
                "role": "Análisis Emocional",
                "triggers": ["emociones", "sentimientos", "empatía", "conexión emocional"]
            },
            "STELLA": {
                "role": "Motivación y Coaching",
                "triggers": ["motivación", "coaching", "inspiración", "superar obstáculos"]
            },
            "CODE": {
                "role": "Desarrollo Técnico",
                "triggers": ["programación", "desarrollo", "código", "implementación técnica"]
            },
            "GUARDIAN": {
                "role": "Seguridad y Protección",
                "triggers": ["seguridad", "protección", "privacidad", "datos seguros"]
            },
            "NODE": {
                "role": "Conexiones y Networking",
                "triggers": ["networking", "conexiones", "red de contactos", "colaboración"]
            }
        }
        self.test_scenarios = self._create_test_scenarios()
    
    def _create_test_scenarios(self) -> List[Dict[str, Any]]:
        """
        Crea escenarios que deberían provocar menciones de agentes específicos.
        """
        return [
            {
                "scenario": "marketing_strategy",
                "profile": {
                    "name": "Carlos Marketing",
                    "occupation": "CMO",
                    "age": 42,
                    "needs": "estrategia de marketing"
                },
                "messages": [
                    "Necesito ayuda con mi estrategia de marketing",
                    "¿Cómo puede NGX ayudarme con el branding de mi empresa?",
                    "Quiero crear una campaña innovadora que conecte emocionalmente"
                ],
                "expected_agents": ["BLAZE", "SAGE", "WAVE", "SPARK", "LUNA"]
            },
            {
                "scenario": "technical_automation",
                "profile": {
                    "name": "Ana Tech",
                    "occupation": "CTO",
                    "age": 38,
                    "needs": "automatización y desarrollo"
                },
                "messages": [
                    "Necesito automatizar procesos en mi empresa",
                    "¿Cómo funciona la tecnología de IA de NGX?",
                    "Me preocupa la seguridad de los datos"
                ],
                "expected_agents": ["CODE", "NOVA", "GUARDIAN", "NEXUS"]
            },
            {
                "scenario": "personal_transformation",
                "profile": {
                    "name": "Laura Growth",
                    "occupation": "Life Coach",
                    "age": 35,
                    "needs": "transformación personal"
                },
                "messages": [
                    "Quiero transformar mi vida y superar mis límites",
                    "Necesito motivación constante y apoyo emocional",
                    "¿Cómo puedo conectar mejor con mis clientes?"
                ],
                "expected_agents": ["STELLA", "LUNA", "NODE", "WAVE"]
            },
            {
                "scenario": "comprehensive_solution",
                "profile": {
                    "name": "Roberto Enterprise",
                    "occupation": "CEO Fortune 500",
                    "age": 52,
                    "needs": "solución integral"
                },
                "messages": [
                    "Necesito una solución completa para mi organización",
                    "¿Cómo se integran todos estos agentes?",
                    "Quiero ver el roadmap completo y la visión a largo plazo"
                ],
                "expected_agents": ["NEXUS", "SAGE", "All agents"]
            }
        ]
    
    async def test_agent_mentions(self, scenario_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prueba las menciones de agentes HIE en un escenario.
        """
        scenario = scenario_data["scenario"]
        profile = scenario_data["profile"]
        expected_agents = scenario_data["expected_agents"]
        
        print(f"\n🤖 Testing HIE Agents Mention: {scenario}")
        print(f"   Profile: {profile['name']} - {profile['occupation']}")
        print(f"   Expected agents: {', '.join(expected_agents)}")
        
        results = {
            "scenario": scenario,
            "profile_name": profile["name"],
            "expected_agents": expected_agents,
            "agents_mentioned": set(),
            "agent_descriptions": {},
            "context_appropriate": {},
            "response_analysis": []
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Iniciar conversación
                async with session.post(
                    f"{self.api_url}/conversations/start",
                    json={"customer_data": profile}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        conversation_id = data["conversation_id"]
                        
                        # Enviar mensajes del escenario
                        for i, message in enumerate(scenario_data["messages"]):
                            print(f"\n   Message {i+1}: \"{message[:50]}...\"")
                            
                            async with session.post(
                                f"{self.api_url}/conversations/{conversation_id}/message",
                                json={"message": message}
                            ) as msg_response:
                                if msg_response.status == 200:
                                    msg_data = await msg_response.json()
                                    agent_response = msg_data.get("response", "")
                                    
                                    # Analizar menciones de agentes
                                    mentions = self._analyze_agent_mentions(agent_response)
                                    results["agents_mentioned"].update(mentions["agents"])
                                    
                                    # Guardar descripciones encontradas
                                    for agent, descriptions in mentions["descriptions"].items():
                                        if agent not in results["agent_descriptions"]:
                                            results["agent_descriptions"][agent] = []
                                        results["agent_descriptions"][agent].extend(descriptions)
                                    
                                    # Verificar contexto apropiado
                                    context_check = self._check_context_appropriateness(
                                        message,
                                        agent_response,
                                        mentions["agents"]
                                    )
                                    
                                    results["response_analysis"].append({
                                        "message_index": i,
                                        "agents_found": list(mentions["agents"]),
                                        "context_appropriate": context_check,
                                        "hie_explanation_quality": mentions["hie_quality"]
                                    })
                                    
                                    # Imprimir agentes encontrados
                                    if mentions["agents"]:
                                        print(f"   Agents mentioned: {', '.join(mentions['agents'])}")
                                        for agent in mentions["agents"]:
                                            if agent in expected_agents or "All agents" in expected_agents:
                                                print(f"   ✅ {agent} - Expected!")
                                            else:
                                                print(f"   ⚠️  {agent} - Not expected but relevant")
                        
                        # Calcular métricas
                        results["agents_mentioned"] = list(results["agents_mentioned"])
                        
                        # Verificar cobertura de agentes esperados
                        if "All agents" in expected_agents:
                            results["expected_coverage"] = len(results["agents_mentioned"]) / len(self.hie_agents)
                        else:
                            covered = len([a for a in expected_agents if a in results["agents_mentioned"]])
                            results["expected_coverage"] = covered / len(expected_agents) if expected_agents else 0
                        
                        # Verificar calidad de explicación HIE
                        hie_quality_scores = [r["hie_explanation_quality"] for r in results["response_analysis"]]
                        results["avg_hie_quality"] = sum(hie_quality_scores) / len(hie_quality_scores) if hie_quality_scores else 0
                        
                        print(f"\n   Coverage of expected agents: {results['expected_coverage']:.0%}")
                        print(f"   HIE explanation quality: {results['avg_hie_quality']:.0%}")
                        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["error"] = str(e)
        
        return results
    
    def _analyze_agent_mentions(self, response: str) -> Dict[str, Any]:
        """
        Analiza las menciones de agentes HIE en una respuesta.
        """
        mentions = {
            "agents": set(),
            "descriptions": {},
            "hie_quality": 0
        }
        
        response_upper = response.upper()
        
        # Buscar menciones de cada agente
        for agent_name in self.hie_agents.keys():
            if agent_name in response_upper:
                mentions["agents"].add(agent_name)
                
                # Buscar descripciones del agente
                pattern = rf"{agent_name}[^.]*\."
                descriptions = re.findall(pattern, response, re.IGNORECASE)
                if descriptions:
                    mentions["descriptions"][agent_name] = descriptions
        
        # Evaluar calidad de explicación HIE
        quality_indicators = 0
        quality_checks = [
            ("sinergia" in response.lower(), 2),  # Menciona sinergia
            ("hombre-máquina" in response.lower(), 2),  # Concepto clave
            ("imposible de clonar" in response.lower(), 2),  # Diferenciador
            ("colaboración" in response.lower(), 1),
            ("inteligencia híbrida" in response.lower(), 1),
            (len(mentions["agents"]) >= 3, 1),  # Menciona múltiples agentes
            ("trabajan juntos" in response.lower(), 1)
        ]
        
        for check, weight in quality_checks:
            if check:
                quality_indicators += weight
        
        mentions["hie_quality"] = min(quality_indicators / 10, 1.0)  # Normalizar a 0-1
        
        return mentions
    
    def _check_context_appropriateness(self, user_message: str, response: str, agents_mentioned: Set[str]) -> float:
        """
        Verifica si los agentes mencionados son apropiados para el contexto.
        """
        if not agents_mentioned:
            return 0.0
        
        user_message_lower = user_message.lower()
        appropriate_count = 0
        
        for agent in agents_mentioned:
            agent_info = self.hie_agents[agent]
            # Verificar si algún trigger del agente está en el mensaje del usuario
            if any(trigger in user_message_lower for trigger in agent_info["triggers"]):
                appropriate_count += 1
        
        return appropriate_count / len(agents_mentioned) if agents_mentioned else 0
    
    async def test_hie_differentiation(self) -> Dict[str, Any]:
        """
        Prueba cómo se presenta HIE como diferenciador único.
        """
        print("\n🎆 TEST: HIE Differentiation Messaging")
        print("=" * 50)
        
        differentiation_messages = [
            "¿Qué hace diferente a NGX de otros servicios?",
            "¿Por qué debería elegir NGX sobre la competencia?",
            "¿Cuál es su propuesta de valor única?"
        ]
        
        profile = {
            "name": "Evaluator Test",
            "occupation": "Business Analyst",
            "age": 40
        }
        
        results = {
            "test_name": "hie_differentiation",
            "differentiation_quality": [],
            "key_messages_found": []
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Iniciar conversación
                async with session.post(
                    f"{self.api_url}/conversations/start",
                    json={"customer_data": profile}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        conversation_id = data["conversation_id"]
                        
                        for message in differentiation_messages:
                            async with session.post(
                                f"{self.api_url}/conversations/{conversation_id}/message",
                                json={"message": message}
                            ) as msg_response:
                                if msg_response.status == 200:
                                    msg_data = await msg_response.json()
                                    agent_response = msg_data.get("response", "")
                                    
                                    # Analizar calidad de diferenciación
                                    quality = self._analyze_differentiation_quality(agent_response)
                                    results["differentiation_quality"].append(quality)
                                    for msg in quality["key_messages"]:
                                        if msg not in results["key_messages_found"]:
                                            results["key_messages_found"].append(msg)
                        
                        # Calcular métricas finales
                        if results["differentiation_quality"]:
                            avg_quality = sum(q["score"] for q in results["differentiation_quality"]) / len(results["differentiation_quality"])
                            results["avg_differentiation_score"] = avg_quality
                            results["strong_differentiation"] = avg_quality >= 0.7
                        
                        print(f"\n   Differentiation quality: {results.get('avg_differentiation_score', 0):.0%}")
                        print(f"   Key messages found: {len(results['key_messages_found'])}")
                        
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    def _analyze_differentiation_quality(self, response: str) -> Dict[str, Any]:
        """
        Analiza la calidad del mensaje de diferenciación HIE.
        """
        response_lower = response.lower()
        
        key_differentiators = {
            "sinergia_hombre_maquina": "sinergia" in response_lower and "máquina" in response_lower,
            "imposible_clonar": "imposible" in response_lower and "clonar" in response_lower,
            "11_agentes": "11 agentes" in response_lower or "once agentes" in response_lower,
            "colaboracion_unica": "colaboración única" in response_lower,
            "inteligencia_hibrida": "inteligencia híbrida" in response_lower,
            "epic_onboarding": "epic onboarding" in response_lower,
            "nexus_coordinator": "nexus" in response_lower and "coordina" in response_lower
        }
        
        key_messages = [key for key, found in key_differentiators.items() if found]
        score = len(key_messages) / len(key_differentiators)
        
        return {
            "score": score,
            "key_messages": key_messages,
            "differentiators_found": key_differentiators
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Ejecuta todos los tests de menciones HIE.
        """
        print("\n🤖 INICIANDO TESTS DE HIE AGENTS MENTION")
        print("=" * 70)
        
        all_results = {
            "test_suite": "HIE Agents Mention",
            "timestamp": datetime.now().isoformat(),
            "scenario_results": [],
            "differentiation_test": None
        }
        
        # Probar cada escenario
        for scenario_data in self.test_scenarios:
            result = await self.test_agent_mentions(scenario_data)
            all_results["scenario_results"].append(result)
            
            # Pequeña pausa entre tests
            await asyncio.sleep(2)
        
        # Test de diferenciación
        diff_result = await self.test_hie_differentiation()
        all_results["differentiation_test"] = diff_result
        
        # Calcular métricas globales
        successful_tests = [r for r in all_results["scenario_results"] if "error" not in r]
        
        if successful_tests:
            # Agentes únicos mencionados en total
            all_agents_mentioned = set()
            for result in successful_tests:
                all_agents_mentioned.update(result["agents_mentioned"])
            
            # Cobertura promedio de agentes esperados
            avg_coverage = sum(r["expected_coverage"] for r in successful_tests) / len(successful_tests)
            
            # Calidad promedio de explicación HIE
            avg_hie_quality = sum(r["avg_hie_quality"] for r in successful_tests) / len(successful_tests)
            
            all_results["global_metrics"] = {
                "total_scenarios": len(self.test_scenarios),
                "successful_tests": len(successful_tests),
                "unique_agents_mentioned": len(all_agents_mentioned),
                "agent_coverage_percentage": len(all_agents_mentioned) / len(self.hie_agents),
                "avg_expected_coverage": avg_coverage,
                "avg_hie_explanation_quality": avg_hie_quality,
                "agents_mentioned_list": sorted(list(all_agents_mentioned)),
                "strong_differentiation": diff_result.get("strong_differentiation", False)
            }
        
        # Resumen
        print("\n📊 RESUMEN DE RESULTADOS")
        print("=" * 70)
        print(f"Escenarios probados: {len(self.test_scenarios)}")
        
        if "global_metrics" in all_results:
            metrics = all_results["global_metrics"]
            print(f"Tests exitosos: {metrics['successful_tests']}")
            print(f"Agentes únicos mencionados: {metrics['unique_agents_mentioned']}/{len(self.hie_agents)}")
            print(f"Cobertura de agentes: {metrics['agent_coverage_percentage']:.0%}")
            print(f"Cobertura esperada promedio: {metrics['avg_expected_coverage']:.0%}")
            print(f"Calidad de explicación HIE: {metrics['avg_hie_explanation_quality']:.0%}")
            
            print("\nAgentes mencionados:")
            for agent in metrics['agents_mentioned_list']:
                print(f"  - {agent}: {self.hie_agents[agent]['role']}")
            
            if metrics["strong_differentiation"]:
                print("\n✅ Diferenciación HIE comunicada efectivamente")
            else:
                print("\n⚠️  Diferenciación HIE necesita mejora")
        
        # Guardar resultados
        results_file = f"tests/capabilities/results/hie_agents_mention_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Resultados guardados en: {results_file}")
        
        return all_results


async def main():
    """Función principal para ejecutar los tests."""
    tester = HIEAgentsMentionTester()
    results = await tester.run_all_tests()
    
    # Determinar éxito
    if "global_metrics" in results:
        metrics = results["global_metrics"]
        success = (
            metrics["unique_agents_mentioned"] >= 7 and  # Al menos 7 de 11 agentes
            metrics["avg_expected_coverage"] >= 0.7 and  # 70% cobertura esperada
            metrics["avg_hie_explanation_quality"] >= 0.6  # 60% calidad HIE
        )
    else:
        success = False
    
    if success:
        print("\n✅ HIE AGENTS MENTION: FUNCIONANDO CORRECTAMENTE")
        print(f"   Agentes mencionados: {metrics['unique_agents_mentioned']}/11")
        print(f"   Cobertura esperada: {metrics['avg_expected_coverage']:.0%}")
        print(f"   Calidad HIE: {metrics['avg_hie_explanation_quality']:.0%}")
    else:
        print("\n❌ HIE AGENTS MENTION: REQUIERE REVISIÓN")
        if "global_metrics" in results:
            print(f"   Agentes mencionados: {metrics['unique_agents_mentioned']}/11 (objetivo: 7+)")
            print(f"   Cobertura esperada: {metrics['avg_expected_coverage']:.0%} (objetivo: 70%+)")
            print(f"   Calidad HIE: {metrics['avg_hie_explanation_quality']:.0%} (objetivo: 60%+)")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)