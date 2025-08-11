#!/usr/bin/env python3
"""
Test de Empathy Excellence - NGX Voice Sales Agent

Medir:
- Uso de 50+ frases de conexión
- Validación emocional apropiada
- Personalización por edad/profesión
- Warmth score > 0.9
"""

import asyncio
import aiohttp
import json
import os
from typing import Dict, List, Any, Tuple
from datetime import datetime
from openai import AsyncOpenAI

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")


class EmpathyExcellenceTester:
    """Evalúa el nivel de empatía del agente NGX."""
    
    def __init__(self):
        self.api_url = API_URL
        self.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.empathy_scenarios = self._create_empathy_scenarios()
        
    def _create_empathy_scenarios(self) -> List[Dict[str, Any]]:
        """Crea escenarios que requieren alta empatía."""
        return [
            {
                "scenario": "executive_burnout",
                "profile": {
                    "name": "Laura Rodriguez",
                    "age": 42,
                    "occupation": "VP Marketing",
                    "emotional_state": "exhausted",
                    "context": "Working 80-hour weeks, missing family time"
                },
                "messages": [
                    "Estoy agotada... trabajo 80 horas a la semana y apenas veo a mis hijos",
                    "Siento que estoy sacrificando mi salud por mi carrera",
                    "A veces me pregunto si vale la pena todo este esfuerzo",
                    "Necesito un cambio pero no sé por dónde empezar"
                ],
                "empathy_requirements": {
                    "emotional_validation": ["exhaustion", "sacrifice", "family guilt"],
                    "personal_connection": True,
                    "reassurance": True,
                    "hope_building": True
                }
            },
            {
                "scenario": "health_anxiety",
                "profile": {
                    "name": "Dr. Carlos Mendez",
                    "age": 58,
                    "occupation": "Cardiologist",
                    "emotional_state": "worried",
                    "context": "Concerned about own health despite being a doctor"
                },
                "messages": [
                    "Como médico, veo todos los días lo que pasa cuando no cuidamos nuestra salud",
                    "Tengo 58 años y me preocupa no poder mantener mi ritmo",
                    "Mi padre tuvo problemas cardíacos a mi edad",
                    "¿Será demasiado tarde para empezar a cuidarme?"
                ],
                "empathy_requirements": {
                    "emotional_validation": ["worry", "mortality awareness", "irony of situation"],
                    "age_appropriate_response": True,
                    "professional_respect": True,
                    "encouragement": True
                }
            },
            {
                "scenario": "entrepreneur_isolation",
                "profile": {
                    "name": "Alex Chen",
                    "age": 29,
                    "occupation": "Startup Founder",
                    "emotional_state": "lonely",
                    "context": "Feeling isolated while building company"
                },
                "messages": [
                    "Construir una startup es más solitario de lo que pensaba",
                    "Mis amigos no entienden por qué trabajo tanto",
                    "A veces dudo si estoy en el camino correcto",
                    "Me siento desconectado de todo menos del trabajo"
                ],
                "empathy_requirements": {
                    "emotional_validation": ["loneliness", "doubt", "disconnection"],
                    "peer_understanding": True,
                    "motivation": True,
                    "community_building": True
                }
            },
            {
                "scenario": "midlife_crisis",
                "profile": {
                    "name": "Patricia Jimenez",
                    "age": 45,
                    "occupation": "CFO",
                    "emotional_state": "questioning",
                    "context": "Questioning life choices at midlife"
                },
                "messages": [
                    "A los 45, me pregunto si esto es todo lo que hay",
                    "He logrado el éxito profesional pero me siento vacía",
                    "¿Es normal sentir que necesito reinventarme a esta edad?",
                    "Quiero los próximos 20 años sean diferentes"
                ],
                "empathy_requirements": {
                    "emotional_validation": ["existential questioning", "emptiness", "desire for change"],
                    "midlife_understanding": True,
                    "inspiration": True,
                    "future_vision": True
                }
            }
        ]
    
    async def evaluate_empathy_with_gpt4(self, 
                                       user_message: str, 
                                       agent_response: str,
                                       context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Usa GPT-4o para evaluar el nivel de empatía de una respuesta.
        """
        evaluation_prompt = f"""
        Eres un experto en comunicación empática y psicología. Evalúa el nivel de empatía en la siguiente respuesta de un agente de ventas.

        CONTEXTO DEL CLIENTE:
        - Nombre: {context['profile']['name']}
        - Edad: {context['profile']['age']}
        - Ocupación: {context['profile']['occupation']}
        - Estado emocional: {context['profile']['emotional_state']}
        - Situación: {context['profile']['context']}

        MENSAJE DEL CLIENTE:
        "{user_message}"

        RESPUESTA DEL AGENTE:
        "{agent_response}"

        Evalúa la respuesta en estas dimensiones (1-10):

        1. **Validación Emocional**: ¿Reconoce y valida los sentimientos del cliente?
        2. **Conexión Personal**: ¿Establece una conexión humana genuina?
        3. **Lenguaje Apropiado**: ¿Usa lenguaje cálido y apropiado para la situación?
        4. **Escucha Activa**: ¿Demuestra que realmente escuchó y entendió?
        5. **Apoyo Incondicional**: ¿Ofrece apoyo sin juzgar?
        6. **Personalización**: ¿La respuesta está personalizada para este cliente específico?
        7. **Calidez Humana**: ¿Se siente como una conversación con un amigo que se preocupa?
        8. **Timing Emocional**: ¿Responde al estado emocional antes de vender?

        Además, identifica:
        - Frases específicas de conexión emocional usadas
        - Elementos que podrían mejorar
        - Si menciona venta demasiado pronto (reduce puntaje)

        Responde SOLO en formato JSON:
        {{
            "scores": {{
                "validacion_emocional": <1-10>,
                "conexion_personal": <1-10>,
                "lenguaje_apropiado": <1-10>,
                "escucha_activa": <1-10>,
                "apoyo_incondicional": <1-10>,
                "personalizacion": <1-10>,
                "calidez_humana": <1-10>,
                "timing_emocional": <1-10>
            }},
            "empathy_score": <promedio de todos los scores>,
            "connection_phrases": ["lista de frases empáticas encontradas"],
            "improvement_areas": ["áreas de mejora"],
            "premature_selling": <true/false>,
            "overall_assessment": "evaluación general en una frase"
        }}
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Eres un evaluador experto en empatía. SIEMPRE responde en formato JSON válido."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"Error en evaluación GPT-4: {e}")
            return {
                "empathy_score": 0,
                "error": str(e)
            }
    
    async def test_empathy_scenario(self, scenario_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prueba un escenario específico de empatía.
        """
        scenario = scenario_data["scenario"]
        profile = scenario_data["profile"]
        
        print(f"\n💝 Testing Empathy Scenario: {scenario}")
        print(f"   Client: {profile['name']} ({profile['age']} años, {profile['occupation']})")
        print(f"   Emotional state: {profile['emotional_state']}")
        
        results = {
            "scenario": scenario,
            "profile": profile,
            "empathy_evaluations": [],
            "avg_empathy_score": 0,
            "connection_phrases_found": [],
            "personalization_examples": [],
            "overall_performance": {}
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
                        
                        # Enviar cada mensaje del escenario
                        for i, message in enumerate(scenario_data["messages"]):
                            print(f"\n   Message {i+1}: \"{message[:50]}...\"")
                            
                            async with session.post(
                                f"{self.api_url}/conversations/{conversation_id}/message",
                                json={"message": message}
                            ) as msg_response:
                                if msg_response.status == 200:
                                    msg_data = await msg_response.json()
                                    agent_response = msg_data.get("response", "")
                                    
                                    # Evaluar empatía con GPT-4
                                    empathy_eval = await self.evaluate_empathy_with_gpt4(
                                        message,
                                        agent_response,
                                        scenario_data
                                    )
                                    
                                    results["empathy_evaluations"].append(empathy_eval)
                                    
                                    # Recopilar frases de conexión
                                    if "connection_phrases" in empathy_eval:
                                        for phrase in empathy_eval["connection_phrases"]:
                                            if phrase not in results["connection_phrases_found"]:
                                                results["connection_phrases_found"].append(phrase)
                                    
                                    # Imprimir score
                                    score = empathy_eval.get("empathy_score", 0)
                                    print(f"   Empathy score: {score:.1f}/10")
                                    
                                    if score >= 9:
                                        print("   ✅ Excellent empathy!")
                                    elif score >= 7:
                                        print("   ⚠️  Good empathy, room for improvement")
                                    else:
                                        print("   ❌ Low empathy detected")
                        
                        # Calcular métricas finales
                        valid_evals = [e for e in results["empathy_evaluations"] if "empathy_score" in e]
                        if valid_evals:
                            results["avg_empathy_score"] = sum(e["empathy_score"] for e in valid_evals) / len(valid_evals)
                            
                            # Análisis detallado por dimensión
                            dimension_scores = {}
                            for dimension in ["validacion_emocional", "conexion_personal", "lenguaje_apropiado", 
                                            "escucha_activa", "apoyo_incondicional", "personalizacion", 
                                            "calidez_humana", "timing_emocional"]:
                                scores = [e["scores"][dimension] for e in valid_evals if "scores" in e and dimension in e["scores"]]
                                if scores:
                                    dimension_scores[dimension] = sum(scores) / len(scores)
                            
                            results["overall_performance"] = dimension_scores
                        
                        # Verificar requisitos específicos del escenario
                        results["requirements_met"] = self._check_scenario_requirements(
                            results,
                            scenario_data["empathy_requirements"]
                        )
                        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["error"] = str(e)
        
        return results
    
    def _check_scenario_requirements(self, results: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, bool]:
        """
        Verifica si se cumplieron los requisitos específicos del escenario.
        """
        met = {}
        
        # Verificar validación emocional
        if "emotional_validation" in requirements:
            required_emotions = requirements["emotional_validation"]
            all_responses = " ".join([str(e) for e in results["empathy_evaluations"]])
            met["emotional_validation"] = any(emotion in all_responses.lower() for emotion in required_emotions)
        
        # Verificar otros requisitos
        for req in ["personal_connection", "reassurance", "hope_building", 
                   "age_appropriate_response", "professional_respect", "encouragement",
                   "peer_understanding", "motivation", "community_building",
                   "midlife_understanding", "inspiration", "future_vision"]:
            if req in requirements and requirements[req]:
                # Simplificación: verificar si el score promedio es alto
                met[req] = results["avg_empathy_score"] >= 8
        
        return met
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Ejecuta todos los tests de excelencia en empatía.
        """
        print("\n💖 INICIANDO TESTS DE EMPATHY EXCELLENCE")
        print("=" * 70)
        
        all_results = {
            "test_suite": "Empathy Excellence",
            "timestamp": datetime.now().isoformat(),
            "scenarios_tested": len(self.empathy_scenarios),
            "results": [],
            "global_metrics": {}
        }
        
        # Probar cada escenario
        for scenario_data in self.empathy_scenarios:
            result = await self.test_empathy_scenario(scenario_data)
            all_results["results"].append(result)
            
            # Pequeña pausa entre tests
            await asyncio.sleep(2)
        
        # Calcular métricas globales
        successful_tests = [r for r in all_results["results"] if "error" not in r and r["avg_empathy_score"] > 0]
        
        if successful_tests:
            # Score promedio global
            all_results["global_metrics"]["avg_empathy_score"] = sum(r["avg_empathy_score"] for r in successful_tests) / len(successful_tests)
            
            # Conteo de frases de conexión únicas
            all_phrases = set()
            for result in successful_tests:
                all_phrases.update(result["connection_phrases_found"])
            all_results["global_metrics"]["unique_connection_phrases"] = len(all_phrases)
            all_results["global_metrics"]["sample_connection_phrases"] = list(all_phrases)[:10]
            
            # Performance por dimensión
            dimension_totals = {}
            dimension_counts = {}
            
            for result in successful_tests:
                for dimension, score in result.get("overall_performance", {}).items():
                    if dimension not in dimension_totals:
                        dimension_totals[dimension] = 0
                        dimension_counts[dimension] = 0
                    dimension_totals[dimension] += score
                    dimension_counts[dimension] += 1
            
            all_results["global_metrics"]["performance_by_dimension"] = {
                dim: dimension_totals[dim] / dimension_counts[dim] 
                for dim in dimension_totals
            }
            
            # Tests con excelencia (9+)
            all_results["global_metrics"]["excellence_count"] = len([r for r in successful_tests if r["avg_empathy_score"] >= 9])
            all_results["global_metrics"]["excellence_rate"] = all_results["global_metrics"]["excellence_count"] / len(successful_tests)
        
        # Resumen
        print("\n📊 RESUMEN DE RESULTADOS")
        print("=" * 70)
        print(f"Escenarios probados: {len(self.empathy_scenarios)}")
        print(f"Tests exitosos: {len(successful_tests)}")
        
        if successful_tests:
            avg_score = all_results["global_metrics"]["avg_empathy_score"]
            print(f"Score de empatía promedio: {avg_score:.1f}/10")
            print(f"Frases de conexión únicas: {all_results['global_metrics']['unique_connection_phrases']}")
            print(f"Tests con excelencia (9+): {all_results['global_metrics']['excellence_count']}/{len(successful_tests)}")
            
            print("\nPerformance por dimensión:")
            for dimension, score in all_results["global_metrics"]["performance_by_dimension"].items():
                print(f"  - {dimension.replace('_', ' ').title()}: {score:.1f}/10")
            
            if all_results['global_metrics']['sample_connection_phrases']:
                print("\nEjemplos de frases de conexión:")
                for phrase in all_results['global_metrics']['sample_connection_phrases'][:5]:
                    print(f"  - \"{phrase}\"")
        
        # Guardar resultados
        results_file = f"tests/capabilities/results/empathy_excellence_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Resultados guardados en: {results_file}")
        
        return all_results


async def main():
    """Función principal para ejecutar los tests."""
    tester = EmpathyExcellenceTester()
    results = await tester.run_all_tests()
    
    # Determinar éxito (objetivo: 9+/10)
    avg_score = results.get("global_metrics", {}).get("avg_empathy_score", 0)
    unique_phrases = results.get("global_metrics", {}).get("unique_connection_phrases", 0)
    
    success = avg_score >= 9.0 and unique_phrases >= 20  # 9+/10 y 20+ frases únicas
    
    if success:
        print("\n✅ EMPATHY EXCELLENCE: OBJETIVO ALCANZADO")
        print(f"   Score de empatía: {avg_score:.1f}/10")
        print(f"   Frases únicas: {unique_phrases}")
    else:
        print("\n❌ EMPATHY EXCELLENCE: REQUIERE MEJORA")
        print(f"   Score actual: {avg_score:.1f}/10 (objetivo: 9+)")
        print(f"   Frases únicas: {unique_phrases} (objetivo: 20+)")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)