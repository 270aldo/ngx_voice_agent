#!/usr/bin/env python3
"""
Test de Multi-Voice Adaptation - NGX Voice Sales Agent

Probar las 7 personalidades de voz:
- Alex Rivera (Motivacional)
- Maria Gutierrez (Empática)
- Robert Chen (Técnico)
- Isabella Rodriguez (Coach)
- Daniel Patel (Directo)
- Laura Mitchell (Educadora)
- Marcus Johnson (Estratega)
"""

import asyncio
import aiohttp
import json
import os
from typing import Dict, List, Any, Tuple
from datetime import datetime
import re

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")


class VoiceAdaptationTester:
    """Evalúa la adaptación de voz según contexto y cliente."""
    
    def __init__(self):
        self.api_url = API_URL
        self.voice_scenarios = self._create_voice_scenarios()
        
    def _create_voice_scenarios(self) -> List[Dict[str, Any]]:
        """
        Crea escenarios que deberían activar diferentes voces.
        """
        return [
            {
                "scenario": "motivational_athlete",
                "expected_voice": "Alex Rivera",
                "profile": {
                    "name": "Diego Martinez",
                    "occupation": "Professional Athlete",
                    "age": 28,
                    "personality": "competitive",
                    "needs": "peak performance"
                },
                "trigger_messages": [
                    "Necesito llevar mi rendimiento al siguiente nivel",
                    "Quiero ser el mejor en mi deporte",
                    "¿Cómo puedo superar mis límites actuales?"
                ],
                "expected_traits": ["energético", "motivacional", "retórico"]
            },
            {
                "scenario": "empathetic_burnout",
                "expected_voice": "Maria Gutierrez",
                "profile": {
                    "name": "Ana Silva",
                    "occupation": "Nurse Manager",
                    "age": 45,
                    "personality": "caring",
                    "emotional_state": "exhausted"
                },
                "trigger_messages": [
                    "Estoy agotada de cuidar a todos menos a mí misma",
                    "Siento que he perdido mi propósito",
                    "Necesito recuperar mi energía y pasión"
                ],
                "expected_traits": ["empático", "cálido", "comprensivo"]
            },
            {
                "scenario": "technical_engineer",
                "expected_voice": "Robert Chen",
                "profile": {
                    "name": "Kumar Patel",
                    "occupation": "Software Engineer",
                    "age": 32,
                    "personality": "analytical",
                    "communication_preference": "data-driven"
                },
                "trigger_messages": [
                    "¿Cuáles son las métricas específicas de mejora?",
                    "Necesito ver datos concretos del ROI",
                    "¿Cómo funciona exactamente la metodología HIE?"
                ],
                "expected_traits": ["preciso", "analítico", "detallado"]
            },
            {
                "scenario": "transformation_coach",
                "expected_voice": "Isabella Rodriguez",
                "profile": {
                    "name": "Carmen Lopez",
                    "occupation": "Life Coach",
                    "age": 38,
                    "personality": "growth-oriented",
                    "goals": "personal transformation"
                },
                "trigger_messages": [
                    "Quiero transformar mi vida completamente",
                    "Estoy lista para un cambio profundo",
                    "¿Cómo puedo ser la mejor versión de mí misma?"
                ],
                "expected_traits": ["inspirador", "coaching", "transformacional"]
            },
            {
                "scenario": "direct_ceo",
                "expected_voice": "Daniel Patel",
                "profile": {
                    "name": "Richard Thompson",
                    "occupation": "CEO",
                    "age": 52,
                    "personality": "decisive",
                    "communication_style": "direct"
                },
                "trigger_messages": [
                    "No tengo tiempo para rodeos, ¿cuál es el punto?",
                    "¿Cuánto cuesta y qué obtengo exactamente?",
                    "Necesito resultados rápidos y medibles"
                ],
                "expected_traits": ["directo", "eficiente", "ejecutivo"]
            },
            {
                "scenario": "educational_teacher",
                "expected_voice": "Laura Mitchell",
                "profile": {
                    "name": "Patricia Gonzalez",
                    "occupation": "University Professor",
                    "age": 48,
                    "personality": "curious",
                    "learning_style": "comprehensive"
                },
                "trigger_messages": [
                    "Me gustaría entender la ciencia detrás del programa",
                    "¿Qué investigaciones respaldan su metodología?",
                    "¿Cómo funciona el proceso de aprendizaje adaptativo?"
                ],
                "expected_traits": ["educativo", "informativo", "paciente"]
            },
            {
                "scenario": "strategic_consultant",
                "expected_voice": "Marcus Johnson",
                "profile": {
                    "name": "James Wilson",
                    "occupation": "Strategy Consultant",
                    "age": 41,
                    "personality": "strategic",
                    "focus": "long-term planning"
                },
                "trigger_messages": [
                    "¿Cómo se integra esto en mi estrategia a largo plazo?",
                    "Necesito entender el impacto estratégico",
                    "¿Cuál es la visión a 5 años de NGX?"
                ],
                "expected_traits": ["estratégico", "visionario", "planificador"]
            }
        ]
    
    async def test_voice_detection(self, scenario_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prueba la detección y adaptación de voz para un escenario.
        """
        scenario = scenario_data["scenario"]
        expected_voice = scenario_data["expected_voice"]
        profile = scenario_data["profile"]
        
        print(f"\n🎤 Testing Voice Adaptation: {scenario}")
        print(f"   Expected voice: {expected_voice}")
        print(f"   Profile: {profile['name']} - {profile['occupation']}")
        
        results = {
            "scenario": scenario,
            "expected_voice": expected_voice,
            "detected_voices": [],
            "voice_consistency": 0,
            "trait_matches": [],
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
                        
                        voice_detections = []
                        
                        # Enviar mensajes trigger
                        for i, message in enumerate(scenario_data["trigger_messages"]):
                            print(f"\n   Message {i+1}: \"{message[:50]}...\"")
                            
                            async with session.post(
                                f"{self.api_url}/conversations/{conversation_id}/message",
                                json={"message": message}
                            ) as msg_response:
                                if msg_response.status == 200:
                                    msg_data = await msg_response.json()
                                    agent_response = msg_data.get("response", "")
                                    
                                    # Detectar voz utilizada
                                    detected_voice = msg_data.get("voice_used", "Unknown")
                                    voice_detections.append(detected_voice)
                                    
                                    # Analizar características de la respuesta
                                    traits_found = self._analyze_voice_traits(
                                        agent_response,
                                        scenario_data["expected_traits"]
                                    )
                                    
                                    results["response_analysis"].append({
                                        "message_index": i,
                                        "voice_detected": detected_voice,
                                        "traits_found": traits_found,
                                        "response_length": len(agent_response)
                                    })
                                    
                                    # Imprimir voz detectada
                                    if detected_voice != "Unknown":
                                        print(f"   Voice detected: {detected_voice}")
                                        if detected_voice == expected_voice:
                                            print("   ✅ Correct voice!")
                                        else:
                                            print("   ⚠️  Different voice than expected")
                        
                        # Calcular consistencia de voz
                        results["detected_voices"] = list(set(voice_detections))
                        if voice_detections:
                            # Porcentaje de veces que usó la voz esperada
                            correct_voice_count = voice_detections.count(expected_voice)
                            results["voice_consistency"] = correct_voice_count / len(voice_detections)
                        
                        # Calcular match de traits
                        all_traits = []
                        for analysis in results["response_analysis"]:
                            all_traits.extend(analysis["traits_found"])
                        
                        unique_traits = list(set(all_traits))
                        expected_traits = scenario_data["expected_traits"]
                        trait_match_rate = len([t for t in unique_traits if any(exp in t for exp in expected_traits)]) / len(expected_traits)
                        
                        results["trait_matches"] = unique_traits
                        results["trait_match_rate"] = trait_match_rate
                        
                        # Verificar si la adaptación fue exitosa
                        results["adaptation_successful"] = (
                            results["voice_consistency"] >= 0.66 and  # 2/3 de las veces
                            trait_match_rate >= 0.5  # 50% de traits esperados
                        )
                        
                        print(f"\n   Voice consistency: {results['voice_consistency']:.0%}")
                        print(f"   Trait match rate: {trait_match_rate:.0%}")
                        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["error"] = str(e)
        
        return results
    
    def _analyze_voice_traits(self, response: str, expected_traits: List[str]) -> List[str]:
        """
        Analiza las características de voz en la respuesta.
        """
        traits_found = []
        response_lower = response.lower()
        
        # Patrones para cada tipo de trait
        trait_patterns = {
            "energético": ["!", "¡vamos", "puedes", "lograr", "increíble", "potencial"],
            "motivacional": ["tú puedes", "capaz", "alcanzar", "superar", "meta", "objetivo"],
            "empático": ["entiendo", "comprendo", "siento", "difícil", "juntos", "apoyar"],
            "cálido": ["querido", "importante", "valioso", "especial", "cuidar"],
            "analítico": ["%", "datos", "estadística", "métrica", "análisis", "resultado"],
            "preciso": ["específicamente", "exactamente", "detalle", "concreto"],
            "inspirador": ["transformar", "cambiar", "evolución", "mejor versión"],
            "directo": ["simple", "claro", "directo", "punto", "resultado"],
            "educativo": ["aprender", "entender", "explicar", "proceso", "cómo funciona"],
            "estratégico": ["plan", "estrategia", "largo plazo", "visión", "objetivo"]
        }
        
        # Buscar patrones
        for trait, patterns in trait_patterns.items():
            if any(pattern in response_lower for pattern in patterns):
                traits_found.append(trait)
        
        # Analizar estructura de respuesta
        if len(response) > 300:
            traits_found.append("detallado")
        if response.count("?") > 2:
            traits_found.append("inquisitivo")
        if response.count("!") > 2:
            traits_found.append("entusiasta")
        if re.search(r'\d+%|\$\d+', response):
            traits_found.append("cuantitativo")
        
        return traits_found
    
    async def test_voice_switching(self) -> Dict[str, Any]:
        """
        Prueba el cambio dinámico de voz dentro de una conversación.
        """
        print("\n🔁 TEST: Voice Switching Mid-Conversation")
        print("=" * 50)
        
        # Perfil que cambiará de necesidades durante la conversación
        dynamic_profile = {
            "name": "Sofia Chang",
            "occupation": "Entrepreneur",
            "age": 35,
            "personality": "adaptable"
        }
        
        # Mensajes que deberían provocar diferentes voces
        switching_messages = [
            ("Necesito motivación para seguir adelante", "Alex Rivera"),  # Motivacional
            ("Me siento abrumada y cansada", "Maria Gutierrez"),  # Empática
            ("Muéstrame los datos y métricas", "Robert Chen"),  # Técnico
            ("Quiero transformar mi empresa", "Isabella Rodriguez"),  # Coach
            ("Déjate de rodeos, ¿cuánto cuesta?", "Daniel Patel")  # Directo
        ]
        
        results = {
            "test_name": "voice_switching",
            "profile": dynamic_profile["name"],
            "voice_changes": [],
            "switching_success_rate": 0
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Iniciar conversación
                async with session.post(
                    f"{self.api_url}/conversations/start",
                    json={"customer_data": dynamic_profile}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        conversation_id = data["conversation_id"]
                        
                        successful_switches = 0
                        
                        for message, expected_voice in switching_messages:
                            async with session.post(
                                f"{self.api_url}/conversations/{conversation_id}/message",
                                json={"message": message}
                            ) as msg_response:
                                if msg_response.status == 200:
                                    msg_data = await msg_response.json()
                                    detected_voice = msg_data.get("voice_used", "Unknown")
                                    
                                    voice_change = {
                                        "message": message[:50] + "...",
                                        "expected": expected_voice,
                                        "detected": detected_voice,
                                        "matched": detected_voice == expected_voice
                                    }
                                    
                                    results["voice_changes"].append(voice_change)
                                    
                                    if voice_change["matched"]:
                                        successful_switches += 1
                        
                        # Calcular tasa de éxito
                        if results["voice_changes"]:
                            results["switching_success_rate"] = successful_switches / len(results["voice_changes"])
                        
                        print(f"\n   Voice switching results:")
                        for change in results["voice_changes"]:
                            status = "✅" if change["matched"] else "❌"
                            print(f"   {status} Expected: {change['expected']}, Got: {change['detected']}")
                        
                        print(f"\n   Success rate: {results['switching_success_rate']:.0%}")
                        
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Ejecuta todos los tests de adaptación de voz.
        """
        print("\n🎤 INICIANDO TESTS DE MULTI-VOICE ADAPTATION")
        print("=" * 70)
        
        all_results = {
            "test_suite": "Multi-Voice Adaptation",
            "timestamp": datetime.now().isoformat(),
            "voice_scenarios": [],
            "voice_switching_test": None
        }
        
        # Probar cada escenario de voz
        for scenario_data in self.voice_scenarios:
            result = await self.test_voice_detection(scenario_data)
            all_results["voice_scenarios"].append(result)
            
            # Pequeña pausa entre tests
            await asyncio.sleep(2)
        
        # Test de cambio de voz
        switching_result = await self.test_voice_switching()
        all_results["voice_switching_test"] = switching_result
        
        # Calcular métricas globales
        successful_scenarios = [s for s in all_results["voice_scenarios"] if "error" not in s]
        
        if successful_scenarios:
            # Tasa de adaptación exitosa
            adaptation_success_rate = len([s for s in successful_scenarios if s.get("adaptation_successful", False)]) / len(successful_scenarios)
            
            # Consistencia promedio de voz
            avg_consistency = sum(s["voice_consistency"] for s in successful_scenarios) / len(successful_scenarios)
            
            # Voces únicas detectadas
            all_voices = set()
            for scenario in successful_scenarios:
                all_voices.update(scenario["detected_voices"])
            
            all_results["global_metrics"] = {
                "total_scenarios": len(self.voice_scenarios),
                "successful_tests": len(successful_scenarios),
                "adaptation_success_rate": adaptation_success_rate,
                "avg_voice_consistency": avg_consistency,
                "unique_voices_detected": len(all_voices),
                "voice_list": list(all_voices),
                "switching_success_rate": switching_result.get("switching_success_rate", 0) if switching_result else 0
            }
        
        # Resumen
        print("\n📊 RESUMEN DE RESULTADOS")
        print("=" * 70)
        print(f"Escenarios probados: {len(self.voice_scenarios)}")
        
        if "global_metrics" in all_results:
            metrics = all_results["global_metrics"]
            print(f"Tests exitosos: {metrics['successful_tests']}")
            print(f"Tasa de adaptación exitosa: {metrics['adaptation_success_rate']:.0%}")
            print(f"Consistencia de voz promedio: {metrics['avg_voice_consistency']:.0%}")
            print(f"Voces únicas detectadas: {metrics['unique_voices_detected']}")
            
            if metrics['voice_list']:
                print("\nVoces detectadas:")
                for voice in metrics['voice_list']:
                    print(f"  - {voice}")
        
        # Guardar resultados
        results_file = f"tests/capabilities/results/voice_adaptation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Resultados guardados en: {results_file}")
        
        return all_results


async def main():
    """Función principal para ejecutar los tests."""
    tester = VoiceAdaptationTester()
    results = await tester.run_all_tests()
    
    # Determinar éxito
    if "global_metrics" in results:
        metrics = results["global_metrics"]
        success = (
            metrics["adaptation_success_rate"] >= 0.6 and  # 60% adaptación exitosa
            metrics["unique_voices_detected"] >= 4  # Al menos 4 voces diferentes
        )
    else:
        success = False
    
    if success:
        print("\n✅ MULTI-VOICE ADAPTATION: FUNCIONANDO CORRECTAMENTE")
        print(f"   Adaptación exitosa: {metrics['adaptation_success_rate']:.0%}")
        print(f"   Voces detectadas: {metrics['unique_voices_detected']}/7")
    else:
        print("\n❌ MULTI-VOICE ADAPTATION: REQUIERE REVISIÓN")
        if "global_metrics" in results:
            print(f"   Adaptación actual: {metrics['adaptation_success_rate']:.0%} (objetivo: 60%+)")
            print(f"   Voces detectadas: {metrics['unique_voices_detected']}/7 (objetivo: 4+)")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)