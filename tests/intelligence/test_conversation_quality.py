#!/usr/bin/env python3
"""
Test de Calidad de Conversación - NGX Voice Sales Agent

Evalúa la calidad de las respuestas del agente usando GPT-4 como evaluador.
Verifica:
- Calidad general de respuestas
- Conocimiento correcto de productos
- Técnicas de venta apropiadas
- Coherencia con brand voice de NGX
"""

import asyncio
import aiohttp
import json
import os
from typing import Dict, List, Any, Tuple
from datetime import datetime
import statistics
from openai import AsyncOpenAI

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")


class ConversationQualityTester:
    """Evalúa la calidad de las conversaciones del agente NGX."""
    
    def __init__(self):
        self.api_url = API_URL
        self.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.test_results = []
        
    async def evaluate_response_quality(self, 
                                      user_message: str, 
                                      agent_response: str,
                                      context: str = "") -> Dict[str, Any]:
        """
        Usa GPT-4 para evaluar la calidad de una respuesta del agente.
        
        Returns:
            Dict con scores de 1-10 en diferentes categorías
        """
        evaluation_prompt = f"""
        Eres un evaluador experto en ventas consultivas y coaching de salud.
        
        Evalúa la siguiente respuesta de un agente de ventas de NGX (empresa de optimización humana).
        
        Contexto de la conversación: {context}
        
        Usuario dijo: "{user_message}"
        
        Agente respondió: "{agent_response}"
        
        Evalúa la respuesta en estas categorías (1-10):
        
        1. **Calidad General**: ¿Es una respuesta profesional y bien estructurada?
        2. **Conocimiento de Producto**: ¿Demuestra conocimiento correcto de NGX sin inventar?
        3. **Técnica de Venta**: ¿Usa técnicas consultivas apropiadas sin ser agresivo?
        4. **Empatía**: ¿Muestra comprensión genuina de las necesidades del cliente?
        5. **Claridad**: ¿Es clara y fácil de entender?
        6. **Acción**: ¿Guía al cliente hacia el siguiente paso?
        7. **Brand Voice**: ¿Mantiene el tono profesional pero cálido de NGX?
        
        Además, identifica:
        - Errores factuales (si los hay)
        - Oportunidades perdidas
        - Aspectos destacables
        
        Responde en formato JSON:
        {{
            "scores": {{
                "calidad_general": <1-10>,
                "conocimiento_producto": <1-10>,
                "tecnica_venta": <1-10>,
                "empatia": <1-10>,
                "claridad": <1-10>,
                "accion": <1-10>,
                "brand_voice": <1-10>
            }},
            "promedio": <promedio de todos los scores>,
            "errores_factuales": ["lista de errores si los hay"],
            "oportunidades_perdidas": ["lista de oportunidades"],
            "aspectos_destacables": ["aspectos positivos"],
            "recomendacion": "breve recomendación para mejorar"
        }}
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Eres un evaluador experto en ventas consultivas. SIEMPRE responde en formato JSON válido."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                temperature=0.3
            )
            
            evaluation = json.loads(response.choices[0].message.content)
            return evaluation
            
        except Exception as e:
            print(f"Error evaluating with GPT-4: {e}")
            return {
                "scores": {k: 0 for k in ["calidad_general", "conocimiento_producto", 
                          "tecnica_venta", "empatia", "claridad", "accion", "brand_voice"]},
                "promedio": 0,
                "error": str(e)
            }
    
    async def run_conversation_test(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una conversación completa y evalúa cada respuesta.
        
        Args:
            scenario: Dict con customer_data y messages a enviar
            
        Returns:
            Dict con resultados de la conversación y evaluaciones
        """
        results = {
            "scenario_name": scenario["name"],
            "conversation_id": None,
            "messages": [],
            "evaluations": [],
            "average_score": 0,
            "errors": []
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                # Start conversation
                start_response = await session.post(
                    f"{self.api_url}/conversations/start",
                    json={"customer_data": scenario["customer_data"]},
                    timeout=aiohttp.ClientTimeout(total=30)
                )
                
                if start_response.status != 200:
                    results["errors"].append(f"Failed to start conversation: {start_response.status}")
                    return results
                
                start_data = await start_response.json()
                conversation_id = start_data["conversation_id"]
                results["conversation_id"] = conversation_id
                
                # Evaluate initial greeting
                initial_evaluation = await self.evaluate_response_quality(
                    "Hola, me interesa NGX",
                    start_data["message"],
                    "Inicio de conversación"
                )
                results["evaluations"].append(initial_evaluation)
                
                # Send test messages
                context = "Conversación en progreso"
                for i, message in enumerate(scenario["messages"]):
                    # Send message
                    msg_response = await session.post(
                        f"{self.api_url}/conversations/{conversation_id}/message",
                        json={"message": message},
                        timeout=aiohttp.ClientTimeout(total=30)
                    )
                    
                    if msg_response.status != 200:
                        results["errors"].append(f"Message {i} failed: {msg_response.status}")
                        continue
                    
                    msg_data = await msg_response.json()
                    agent_response = msg_data["message"]
                    
                    results["messages"].append({
                        "user": message,
                        "agent": agent_response
                    })
                    
                    # Evaluate response
                    evaluation = await self.evaluate_response_quality(
                        message,
                        agent_response,
                        context
                    )
                    results["evaluations"].append(evaluation)
                    
                    # Update context
                    context = f"Usuario preguntó sobre: {message[:50]}..."
                    
                    # Small delay between messages
                    await asyncio.sleep(1)
                
                # Calculate average score
                all_scores = []
                for eval in results["evaluations"]:
                    if "promedio" in eval and eval["promedio"] > 0:
                        all_scores.append(eval["promedio"])
                
                if all_scores:
                    results["average_score"] = statistics.mean(all_scores)
                
            except Exception as e:
                results["errors"].append(f"Test error: {str(e)}")
        
        return results
    
    async def run_quality_test_suite(self):
        """Ejecuta una suite completa de tests de calidad."""
        print("🧪 NGX Voice Sales Agent - Conversation Quality Test Suite")
        print("=" * 60)
        
        # Define test scenarios
        test_scenarios = [
            {
                "name": "Cliente Ideal - Ejecutivo 35 años",
                "customer_data": {
                    "name": "Carlos Mendoza",
                    "email": "carlos@empresa.com",
                    "age": 35,
                    "occupation": "CEO Startup",
                    "goals": {"primary": "performance", "timeline": "3_months"},
                    "fitness_metrics": {"activity_level": "moderate"},
                    "lifestyle": {"work_hours": "long", "stress_level": "high"}
                },
                "messages": [
                    "Hola, soy CEO de una startup y busco optimizar mi rendimiento",
                    "¿Qué incluye exactamente el programa PRIME?",
                    "¿Cuánto cuesta y qué resultados puedo esperar?",
                    "Suena interesante, ¿cómo funciona el HIE que mencionas?",
                    "Me preocupa el tiempo, trabajo 12 horas al día"
                ]
            },
            {
                "name": "Cliente Escéptico - Presupuesto Limitado",
                "customer_data": {
                    "name": "Maria Lopez",
                    "email": "maria@gmail.com",
                    "age": 42,
                    "occupation": "Personal Trainer",
                    "goals": {"primary": "grow_business", "timeline": "6_months"},
                    "fitness_metrics": {"activity_level": "very_active"},
                    "lifestyle": {"work_hours": "flexible", "stress_level": "moderate"}
                },
                "messages": [
                    "Hola, soy entrenadora personal y vi su publicidad",
                    "¿Esto es solo otro programa de fitness más?",
                    "Ya he probado muchas cosas, ¿qué tiene de diferente?",
                    "El precio me parece alto para lo que ofrecen",
                    "¿Tienen alguna garantía o periodo de prueba?"
                ]
            },
            {
                "name": "Cliente Técnico - Muchas Preguntas",
                "customer_data": {
                    "name": "Roberto Silva",
                    "email": "roberto@tech.com",
                    "age": 28,
                    "occupation": "Software Engineer",
                    "goals": {"primary": "muscle_gain", "timeline": "1_year"},
                    "fitness_metrics": {"activity_level": "sedentary"},
                    "lifestyle": {"work_hours": "standard", "stress_level": "low"}
                },
                "messages": [
                    "Hola, soy ingeniero y me gusta entender cómo funcionan las cosas",
                    "¿Qué tecnología usan en su sistema HIE?",
                    "¿Cómo miden los resultados que prometen?",
                    "¿Los 11 agentes son IA o personas reales?",
                    "¿Puedo integrar esto con mi Apple Watch?"
                ]
            }
        ]
        
        # Run tests
        all_results = []
        for i, scenario in enumerate(test_scenarios):
            print(f"\n📋 Testing {i+1}/{len(test_scenarios)}: {scenario['name']}")
            print("-" * 40)
            
            result = await self.run_conversation_test(scenario)
            all_results.append(result)
            
            # Print summary
            print(f"Average Score: {result['average_score']:.1f}/10")
            print(f"Messages Evaluated: {len(result['evaluations'])}")
            if result['errors']:
                print(f"Errors: {len(result['errors'])}")
            
            # Print detailed scores for each response
            for i, eval in enumerate(result['evaluations']):
                if "scores" in eval:
                    scores = eval["scores"]
                    print(f"\nResponse {i+1} Scores:")
                    for category, score in scores.items():
                        print(f"  {category}: {score}/10")
                    if eval.get("errores_factuales"):
                        print(f"  ⚠️ Errores: {', '.join(eval['errores_factuales'])}")
        
        # Generate summary report
        self._generate_quality_report(all_results)
        
    def _generate_quality_report(self, results: List[Dict[str, Any]]):
        """Genera un reporte de calidad consolidado."""
        print("\n" + "=" * 60)
        print("📊 CONVERSATION QUALITY TEST REPORT")
        print("=" * 60)
        
        # Overall metrics
        all_scores = []
        category_scores = {
            "calidad_general": [],
            "conocimiento_producto": [],
            "tecnica_venta": [],
            "empatia": [],
            "claridad": [],
            "accion": [],
            "brand_voice": []
        }
        
        total_errors = []
        
        for result in results:
            if result["average_score"] > 0:
                all_scores.append(result["average_score"])
            
            for eval in result["evaluations"]:
                if "scores" in eval:
                    for category, score in eval["scores"].items():
                        if category in category_scores:
                            category_scores[category].append(score)
                
                if eval.get("errores_factuales"):
                    total_errors.extend(eval["errores_factuales"])
        
        # Print overall results
        if all_scores:
            print(f"\n🎯 Overall Average Score: {statistics.mean(all_scores):.1f}/10")
        
        print("\n📈 Category Averages:")
        for category, scores in category_scores.items():
            if scores:
                avg = statistics.mean(scores)
                status = "✅" if avg >= 7 else "⚠️" if avg >= 5 else "❌"
                print(f"{status} {category}: {avg:.1f}/10")
        
        if total_errors:
            print(f"\n❌ Total Factual Errors Found: {len(total_errors)}")
            for error in set(total_errors):
                print(f"  - {error}")
        
        # Determine pass/fail
        overall_avg = statistics.mean(all_scores) if all_scores else 0
        knowledge_avg = statistics.mean(category_scores["conocimiento_producto"]) if category_scores["conocimiento_producto"] else 0
        
        print("\n" + "=" * 60)
        if overall_avg >= 7 and knowledge_avg >= 8 and len(total_errors) == 0:
            print("✅ QUALITY TEST PASSED")
        else:
            print("❌ QUALITY TEST FAILED")
            if overall_avg < 7:
                print(f"  - Overall score below 7: {overall_avg:.1f}")
            if knowledge_avg < 8:
                print(f"  - Product knowledge below 8: {knowledge_avg:.1f}")
            if total_errors:
                print(f"  - Factual errors found: {len(total_errors)}")
        print("=" * 60)
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/intelligence/results/quality_test_{timestamp}.json"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump({
                "test_name": "Conversation Quality Test",
                "timestamp": timestamp,
                "scenarios_tested": len(results),
                "overall_average": overall_avg,
                "category_averages": {k: statistics.mean(v) if v else 0 for k, v in category_scores.items()},
                "factual_errors": list(set(total_errors)),
                "detailed_results": results
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {filename}")


async def main():
    """Run the conversation quality test suite."""
    tester = ConversationQualityTester()
    
    try:
        await tester.run_quality_test_suite()
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())