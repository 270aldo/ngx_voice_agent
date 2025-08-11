#!/usr/bin/env python3
"""
Test de Calidad de Conversación REAL - NGX Voice Sales Agent

Este test evalúa la calidad real del agente después de las mejoras:
- Empatía mejorada (objetivo: 10/10)
- Performance optimizado (objetivo: <0.5s)
- 0 errores por mensaje
- Conversión efectiva
"""

import asyncio
import aiohttp
import json
import os
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple
from openai import AsyncOpenAI

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is required for quality evaluation")


class RealConversationQualityTest:
    """Test real de calidad de conversación con API funcionando."""
    
    def __init__(self):
        self.api_url = API_URL
        self.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.test_results = {
            "conversations": [],
            "overall_metrics": {},
            "empathy_scores": [],
            "response_times": [],
            "errors": [],
            "conversion_signals": []
        }
    
    async def evaluate_response_quality(self, 
                                      user_message: str, 
                                      agent_response: str,
                                      conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Evalúa la calidad de respuesta usando GPT-4.
        """
        evaluation_prompt = f"""
        Eres un evaluador experto en ventas consultivas, empatía y experiencia del cliente.
        
        Evalúa la siguiente respuesta del agente de ventas NGX con MÁXIMA EXIGENCIA.
        
        Historial de conversación:
        {json.dumps(conversation_history[-3:], indent=2) if conversation_history else "Primera interacción"}
        
        Usuario dijo: "{user_message}"
        
        Agente respondió: "{agent_response}"
        
        Evalúa en escala 1-10 (sé MUY crítico, 10 es perfección absoluta):
        
        1. **Empatía**: ¿Muestra comprensión genuina y conexión emocional real?
        2. **Personalización**: ¿La respuesta está adaptada específicamente a este usuario?
        3. **Claridad**: ¿Es fácil de entender sin jerga innecesaria?
        4. **Persuasión**: ¿Guía efectivamente hacia la venta sin ser agresivo?
        5. **Conocimiento**: ¿Demuestra expertise sin inventar información?
        6. **Engagement**: ¿Invita a continuar la conversación de forma natural?
        7. **Autenticidad**: ¿Suena como un humano real, no un robot?
        
        Además identifica:
        - Señales de conversión (si el cliente muestra interés en comprar)
        - Errores o inconsistencias
        - Oportunidades perdidas
        
        Responde SOLO en formato JSON:
        {{
            "scores": {{
                "empathy": <1-10>,
                "personalization": <1-10>,
                "clarity": <1-10>,
                "persuasion": <1-10>,
                "knowledge": <1-10>,
                "engagement": <1-10>,
                "authenticity": <1-10>
            }},
            "average_score": <promedio>,
            "conversion_signals": ["lista de señales positivas"],
            "errors": ["lista de errores"],
            "missed_opportunities": ["oportunidades no aprovechadas"],
            "best_aspect": "lo mejor de la respuesta",
            "worst_aspect": "lo peor de la respuesta"
        }}
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Eres un evaluador crítico. Sé exigente. Un 10 es excepcional, un 7 es bueno, un 5 es mediocre."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"Error evaluating: {e}")
            return {
                "scores": {k: 0 for k in ["empathy", "personalization", "clarity", "persuasion", "knowledge", "engagement", "authenticity"]},
                "average_score": 0,
                "error": str(e)
            }
    
    async def run_test_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta un escenario completo de conversación.
        """
        print(f"\n🎯 Testing Scenario: {scenario['name']}")
        print("-" * 60)
        
        results = {
            "scenario": scenario['name'],
            "conversation_id": None,
            "messages": [],
            "evaluations": [],
            "metrics": {
                "avg_response_time": 0,
                "avg_quality_score": 0,
                "empathy_score": 0,
                "conversion_probability": 0,
                "errors_count": 0
            }
        }
        
        conversation_history = []
        response_times = []
        
        async with aiohttp.ClientSession() as session:
            # Start conversation
            print("📞 Starting conversation...")
            start_time = time.time()
            
            try:
                response = await session.post(
                    f"{self.api_url}/conversations/start",
                    json={"customer_data": scenario["customer_data"]},
                    timeout=aiohttp.ClientTimeout(total=30)
                )
                
                response_time = time.time() - start_time
                response_times.append(response_time)
                
                if response.status != 200:
                    results["metrics"]["errors_count"] += 1
                    error_text = await response.text()
                    print(f"❌ Failed to start: {response.status} - {error_text}")
                    return results
                
                data = await response.json()
                conversation_id = data["conversation_id"]
                initial_message = data["message"]
                
                results["conversation_id"] = conversation_id
                print(f"✅ Started (ID: {conversation_id[:8]}...) in {response_time:.2f}s")
                print(f"🤖 Agent: {initial_message[:100]}...")
                
                # Evaluate initial greeting
                eval_result = await self.evaluate_response_quality(
                    "Hola",
                    initial_message,
                    []
                )
                results["evaluations"].append(eval_result)
                
                # Send test messages
                for i, user_message in enumerate(scenario["messages"]):
                    print(f"\n👤 User: {user_message}")
                    
                    start_time = time.time()
                    msg_response = await session.post(
                        f"{self.api_url}/conversations/{conversation_id}/message",
                        json={"message": user_message},
                        timeout=aiohttp.ClientTimeout(total=30)
                    )
                    response_time = time.time() - start_time
                    response_times.append(response_time)
                    
                    if msg_response.status != 200:
                        results["metrics"]["errors_count"] += 1
                        error_text = await msg_response.text()
                        print(f"❌ Message failed: {error_text}")
                        continue
                    
                    msg_data = await msg_response.json()
                    agent_response = msg_data["message"]
                    
                    print(f"🤖 Agent: {agent_response[:150]}...")
                    print(f"⚡ Response time: {response_time:.2f}s")
                    
                    # Add to history
                    conversation_history.append({"role": "user", "content": user_message})
                    conversation_history.append({"role": "assistant", "content": agent_response})
                    
                    results["messages"].append({
                        "user": user_message,
                        "agent": agent_response,
                        "response_time": response_time
                    })
                    
                    # Evaluate response
                    eval_result = await self.evaluate_response_quality(
                        user_message,
                        agent_response,
                        conversation_history
                    )
                    results["evaluations"].append(eval_result)
                    
                    # Print evaluation summary
                    if "scores" in eval_result:
                        scores = eval_result["scores"]
                        print(f"📊 Quality Scores:")
                        print(f"   Empatía: {scores.get('empathy', 0)}/10")
                        print(f"   Personalización: {scores.get('personalization', 0)}/10")
                        print(f"   Average: {eval_result.get('average_score', 0)}/10")
                    
                    # Small delay
                    await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Error in scenario: {e}")
                results["metrics"]["errors_count"] += 1
                self.test_results["errors"].append(str(e))
        
        # Calculate metrics
        if response_times:
            results["metrics"]["avg_response_time"] = sum(response_times) / len(response_times)
        
        if results["evaluations"]:
            all_scores = []
            empathy_scores = []
            
            for eval in results["evaluations"]:
                if "average_score" in eval:
                    all_scores.append(eval["average_score"])
                if "scores" in eval and "empathy" in eval["scores"]:
                    empathy_scores.append(eval["scores"]["empathy"])
            
            if all_scores:
                results["metrics"]["avg_quality_score"] = sum(all_scores) / len(all_scores)
            if empathy_scores:
                results["metrics"]["empathy_score"] = sum(empathy_scores) / len(empathy_scores)
        
        # Check for conversion signals
        conversion_signals = []
        for eval in results["evaluations"]:
            if "conversion_signals" in eval:
                conversion_signals.extend(eval["conversion_signals"])
        
        results["metrics"]["conversion_probability"] = min(len(conversion_signals) * 20, 100)
        
        return results
    
    async def run_comprehensive_test(self):
        """
        Ejecuta suite completa de tests de calidad.
        """
        print("🚀 NGX Voice Sales Agent - Comprehensive Quality Test")
        print("=" * 80)
        print(f"API URL: {self.api_url}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Objective: Empathy 10/10, Response <0.5s, 0 errors")
        print("=" * 80)
        
        # Define test scenarios
        test_scenarios = [
            {
                "name": "🎯 Ejecutivo Estresado (35 años)",
                "customer_data": {
                    "name": "Carlos Mendoza",
                    "email": "carlos@techcorp.com",
                    "age": 35,
                    "occupation": "CTO",
                    "goals": {"primary": "performance", "timeline": "immediate"}
                },
                "messages": [
                    "Hola, soy CTO de una startup y estoy quemado, trabajo 14 horas al día",
                    "No tengo tiempo para nada, ¿cómo me puede ayudar NGX?",
                    "¿Cuánto cuesta y cuánto tiempo requiere?",
                    "Me preocupa que sea otra cosa más que agregar a mi agenda",
                    "¿Qué garantías tienen de que funciona?"
                ]
            },
            {
                "name": "💪 Entrenadora Escéptica (42 años)",
                "customer_data": {
                    "name": "María González",
                    "email": "maria@fitlife.com",
                    "age": 42,
                    "occupation": "Personal Trainer",
                    "goals": {"primary": "grow_business", "timeline": "6_months"}
                },
                "messages": [
                    "Soy entrenadora personal con 15 años de experiencia",
                    "He visto muchos programas que prometen milagros, ¿qué tiene NGX de diferente?",
                    "¿Esto es solo marketing o hay ciencia real detrás?",
                    "El precio me parece alto, ¿vale la pena la inversión?",
                    "¿Puedo probarlo antes de comprometerme?"
                ]
            },
            {
                "name": "🏥 Doctor Analítico (52 años)",
                "customer_data": {
                    "name": "Dr. Roberto Silva",
                    "email": "dr.silva@hospital.com",
                    "age": 52,
                    "occupation": "Cardiologist",
                    "goals": {"primary": "longevity", "timeline": "1_year"}
                },
                "messages": [
                    "Soy cardiólogo y me interesa el enfoque preventivo",
                    "¿Qué evidencia científica respalda su metodología HIE?",
                    "¿Cómo se integra con mi conocimiento médico existente?",
                    "Necesito detalles específicos sobre los 11 agentes que mencionan",
                    "¿Tienen casos de éxito documentados en profesionales de la salud?"
                ]
            }
        ]
        
        # Run all scenarios
        for scenario in test_scenarios:
            result = await self.run_test_scenario(scenario)
            self.test_results["conversations"].append(result)
            
            # Collect metrics
            self.test_results["empathy_scores"].append(result["metrics"]["empathy_score"])
            self.test_results["response_times"].extend([m["response_time"] for m in result["messages"]])
            
            if result["metrics"]["conversion_probability"] > 50:
                self.test_results["conversion_signals"].append(scenario["name"])
            
            # Brief pause between scenarios
            await asyncio.sleep(2)
        
        # Generate final report
        self._generate_comprehensive_report()
    
    def _generate_comprehensive_report(self):
        """
        Genera reporte detallado de calidad.
        """
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE QUALITY REPORT")
        print("=" * 80)
        
        # Overall Quality Metrics
        all_quality_scores = []
        for conv in self.test_results["conversations"]:
            if conv["metrics"]["avg_quality_score"] > 0:
                all_quality_scores.append(conv["metrics"]["avg_quality_score"])
        
        avg_quality = sum(all_quality_scores) / len(all_quality_scores) if all_quality_scores else 0
        
        print(f"\n🎯 OVERALL QUALITY SCORE: {avg_quality:.1f}/10")
        if avg_quality >= 9.0:
            print("   ✅ EXCEEDS TARGET (9+/10)")
        else:
            print(f"   ❌ BELOW TARGET (target: 9+/10)")
        
        # Empathy Score
        avg_empathy = sum(self.test_results["empathy_scores"]) / len(self.test_results["empathy_scores"]) if self.test_results["empathy_scores"] else 0
        print(f"\n💝 EMPATHY SCORE: {avg_empathy:.1f}/10")
        if avg_empathy >= 9.5:
            print("   ✅ EXCELLENT EMPATHY!")
        else:
            print(f"   ❌ NEEDS IMPROVEMENT (target: 10/10)")
        
        # Response Time
        avg_response_time = sum(self.test_results["response_times"]) / len(self.test_results["response_times"]) if self.test_results["response_times"] else 0
        print(f"\n⚡ AVERAGE RESPONSE TIME: {avg_response_time:.2f}s")
        if avg_response_time < 0.5:
            print("   ✅ MEETS PERFORMANCE TARGET!")
        else:
            print(f"   ❌ TOO SLOW (target: <0.5s)")
        
        # Error Rate
        total_errors = sum(conv["metrics"]["errors_count"] for conv in self.test_results["conversations"])
        total_messages = sum(len(conv["messages"]) for conv in self.test_results["conversations"])
        error_rate = (total_errors / total_messages * 100) if total_messages > 0 else 0
        
        print(f"\n🐛 ERROR RATE: {error_rate:.1f}%")
        if error_rate == 0:
            print("   ✅ ZERO ERRORS - PERFECT!")
        else:
            print(f"   ❌ ERRORS DETECTED ({total_errors} errors)")
        
        # Conversion Signals
        conversion_rate = len(self.test_results["conversion_signals"]) / len(self.test_results["conversations"]) * 100
        print(f"\n💰 CONVERSION SIGNALS: {conversion_rate:.0f}%")
        print(f"   Interested prospects: {self.test_results['conversion_signals']}")
        
        # Detailed Breakdown by Scenario
        print("\n📋 DETAILED RESULTS BY SCENARIO:")
        for conv in self.test_results["conversations"]:
            print(f"\n   {conv['scenario']}:")
            print(f"   - Quality Score: {conv['metrics']['avg_quality_score']:.1f}/10")
            print(f"   - Empathy Score: {conv['metrics']['empathy_score']:.1f}/10")
            print(f"   - Avg Response Time: {conv['metrics']['avg_response_time']:.2f}s")
            print(f"   - Errors: {conv['metrics']['errors_count']}")
            print(f"   - Conversion Probability: {conv['metrics']['conversion_probability']}%")
        
        # Best and Worst Aspects
        print("\n🌟 QUALITATIVE ANALYSIS:")
        best_aspects = []
        worst_aspects = []
        
        for conv in self.test_results["conversations"]:
            for eval in conv["evaluations"]:
                if "best_aspect" in eval:
                    best_aspects.append(eval["best_aspect"])
                if "worst_aspect" in eval:
                    worst_aspects.append(eval["worst_aspect"])
        
        if best_aspects:
            print("\n✅ Best Aspects:")
            for aspect in list(set(best_aspects))[:5]:
                print(f"   - {aspect}")
        
        if worst_aspects:
            print("\n❌ Areas for Improvement:")
            for aspect in list(set(worst_aspects))[:5]:
                print(f"   - {aspect}")
        
        # Final Verdict
        print("\n" + "=" * 80)
        print("🏁 FINAL VERDICT:")
        
        ready_criteria = {
            "Quality >= 9.0": avg_quality >= 9.0,
            "Empathy >= 9.5": avg_empathy >= 9.5,
            "Response < 0.5s": avg_response_time < 0.5,
            "Zero Errors": error_rate == 0,
            "Conversion > 15%": conversion_rate > 15
        }
        
        ready_count = sum(ready_criteria.values())
        
        for criterion, passed in ready_criteria.items():
            print(f"   {'✅' if passed else '❌'} {criterion}")
        
        print(f"\n   Score: {ready_count}/5 criteria met")
        
        if ready_count >= 4:
            print("\n   🎉 SYSTEM IS READY FOR BETA!")
        else:
            print("\n   ⚠️  SYSTEM NEEDS MORE WORK")
        
        print("=" * 80)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/results/quality_test_{timestamp}.json"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "summary": {
                    "avg_quality": avg_quality,
                    "avg_empathy": avg_empathy,
                    "avg_response_time": avg_response_time,
                    "error_rate": error_rate,
                    "conversion_rate": conversion_rate,
                    "ready_for_beta": ready_count >= 4
                },
                "detailed_results": self.test_results
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {filename}")


async def main():
    """Run comprehensive quality test."""
    tester = RealConversationQualityTest()
    
    try:
        await tester.run_comprehensive_test()
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🔍 Starting Comprehensive Quality Test...")
    print("This will test multiple conversation scenarios.")
    print("Estimated time: 5-10 minutes\n")
    
    asyncio.run(main())