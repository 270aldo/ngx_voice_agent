#!/usr/bin/env python3
"""
Test de Conocimiento de Productos - NGX Voice Sales Agent

Verifica que el agente tenga conocimiento correcto sobre:
- Precios exactos de PRIME y LONGEVITY
- Diferencias entre programas
- Los 11 agentes HIE
- No inventar características
"""

import asyncio
import aiohttp
import json
import os
from typing import Dict, List, Any
from datetime import datetime
import re


API_URL = os.getenv("API_URL", "http://localhost:8000")


class ProductKnowledgeTester:
    """Evalúa el conocimiento de productos del agente NGX."""
    
    def __init__(self):
        self.api_url = API_URL
        self.test_results = []
        
        # Ground truth - información correcta de productos
        self.correct_info = {
            "prime_prices": {
                "Essential": 79,
                "Pro": 149,
                "Elite": 199,
                "Premium": 3997
            },
            "longevity_prices": {
                "Foundation": 89,
                "Advanced": 169,
                "Premium": 249,
                "Platinum": 4997
            },
            "hie_agents": [
                "NEXUS", "BLAZE", "SAGE", "WAVE", "SPARK", 
                "NOVA", "LUNA", "STELLA", "CODE", "GUARDIAN", "NODE"
            ],
            "prime_age": "25-50",
            "longevity_age": "50+",
            "key_differentiators": [
                "HIE", "Hybrid Intelligence Engine", 
                "sinergia hombre-máquina", "11 agentes"
            ]
        }
    
    def verify_price_accuracy(self, response: str, program: str) -> Dict[str, Any]:
        """Verifica que los precios mencionados sean correctos."""
        result = {
            "prices_mentioned": [],
            "incorrect_prices": [],
            "missing_tiers": [],
            "accuracy": 0
        }
        
        # Extract prices from response
        price_pattern = r'\$?(\d{2,4})\s*(?:USD|usd|dólares)?'
        found_prices = re.findall(price_pattern, response)
        found_prices = [int(p) for p in found_prices]
        result["prices_mentioned"] = found_prices
        
        # Check accuracy
        if program.upper() == "PRIME":
            correct_prices = list(self.correct_info["prime_prices"].values())
        else:
            correct_prices = list(self.correct_info["longevity_prices"].values())
        
        for price in found_prices:
            if price not in correct_prices and price < 1000:  # Ignore year prices
                result["incorrect_prices"].append(price)
        
        # Check if key tiers are mentioned
        if program.upper() == "PRIME":
            if 79 not in found_prices:
                result["missing_tiers"].append("Essential ($79)")
            if 149 not in found_prices:
                result["missing_tiers"].append("Pro ($149)")
        
        # Calculate accuracy
        if found_prices:
            correct_count = sum(1 for p in found_prices if p in correct_prices)
            result["accuracy"] = correct_count / len(found_prices) * 100
        
        return result
    
    def verify_hie_agents(self, response: str) -> Dict[str, Any]:
        """Verifica que los agentes HIE mencionados sean correctos."""
        result = {
            "agents_mentioned": [],
            "incorrect_agents": [],
            "count_accurate": True
        }
        
        # Find agent mentions
        for agent in self.correct_info["hie_agents"]:
            if agent in response.upper():
                result["agents_mentioned"].append(agent)
        
        # Check for made-up agents
        fake_agent_pattern = r'(?:agente|agent)\s+([A-Z]{3,})'
        potential_agents = re.findall(fake_agent_pattern, response.upper())
        
        for agent in potential_agents:
            if agent not in self.correct_info["hie_agents"] and len(agent) <= 8:
                result["incorrect_agents"].append(agent)
        
        # Verify count if mentioned
        if "11 agentes" in response or "once agentes" in response:
            result["count_accurate"] = True
        elif re.search(r'\d+\s*agentes', response):
            result["count_accurate"] = False
        
        return result
    
    def check_hallucinations(self, response: str) -> List[str]:
        """Detecta posibles alucinaciones o información inventada."""
        hallucinations = []
        
        # Common hallucination patterns
        suspicious_patterns = [
            (r'garantía\s+de\s+\d+\s*días', "Garantías específicas no definidas"),
            (r'aprobado\s+por\s+(?:FDA|OMS)', "Aprobaciones regulatorias no confirmadas"),
            (r'\d+%\s+de\s+descuento', "Descuentos no autorizados"),
            (r'gratis\s+por\s+\d+\s*(?:días|meses)', "Períodos gratuitos no definidos"),
            (r'certificado\s+(?:médico|profesional)', "Certificaciones no confirmadas"),
            (r'reembolso\s+(?:total|completo)', "Políticas de reembolso no definidas")
        ]
        
        for pattern, description in suspicious_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                hallucinations.append(description)
        
        return hallucinations
    
    async def test_product_knowledge_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta un escenario de test de conocimiento de productos."""
        results = {
            "scenario": scenario["name"],
            "questions": [],
            "overall_accuracy": 0,
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
                
                # Test each question
                for question_data in scenario["questions"]:
                    question = question_data["question"]
                    test_type = question_data["type"]
                    
                    # Send question
                    msg_response = await session.post(
                        f"{self.api_url}/conversations/{conversation_id}/message",
                        json={"message": question},
                        timeout=aiohttp.ClientTimeout(total=30)
                    )
                    
                    if msg_response.status != 200:
                        results["errors"].append(f"Failed to send message: {msg_response.status}")
                        continue
                    
                    msg_data = await msg_response.json()
                    response = msg_data["message"]
                    
                    # Evaluate response based on type
                    question_result = {
                        "question": question,
                        "response": response,
                        "type": test_type,
                        "evaluation": {}
                    }
                    
                    if test_type == "price_check":
                        question_result["evaluation"] = self.verify_price_accuracy(
                            response, 
                            question_data.get("program", "PRIME")
                        )
                    elif test_type == "hie_check":
                        question_result["evaluation"] = self.verify_hie_agents(response)
                    elif test_type == "hallucination_check":
                        hallucinations = self.check_hallucinations(response)
                        question_result["evaluation"] = {
                            "hallucinations": hallucinations,
                            "passed": len(hallucinations) == 0
                        }
                    
                    results["questions"].append(question_result)
                    
                    await asyncio.sleep(1)  # Rate limiting
                
                # Calculate overall accuracy
                total_tests = len(results["questions"])
                passed_tests = 0
                
                for q in results["questions"]:
                    if q["type"] == "price_check" and q["evaluation"].get("accuracy", 0) == 100:
                        passed_tests += 1
                    elif q["type"] == "hie_check" and not q["evaluation"].get("incorrect_agents"):
                        passed_tests += 1
                    elif q["type"] == "hallucination_check" and q["evaluation"].get("passed"):
                        passed_tests += 1
                
                results["overall_accuracy"] = (passed_tests / total_tests * 100) if total_tests > 0 else 0
                
            except Exception as e:
                results["errors"].append(f"Test error: {str(e)}")
        
        return results
    
    async def run_product_knowledge_tests(self):
        """Ejecuta la suite completa de tests de conocimiento de productos."""
        print("🧪 NGX Voice Sales Agent - Product Knowledge Test Suite")
        print("=" * 60)
        
        test_scenarios = [
            {
                "name": "Price Accuracy Test - PRIME",
                "customer_data": {
                    "name": "Ana Martinez",
                    "email": "ana@test.com",
                    "age": 35,
                    "occupation": "Marketing Manager"
                },
                "questions": [
                    {
                        "question": "¿Cuáles son los precios exactos de PRIME?",
                        "type": "price_check",
                        "program": "PRIME"
                    },
                    {
                        "question": "¿Cuál es la opción más económica de PRIME?",
                        "type": "price_check",
                        "program": "PRIME"
                    },
                    {
                        "question": "¿Hay algún plan entre $100 y $200?",
                        "type": "price_check",
                        "program": "PRIME"
                    }
                ]
            },
            {
                "name": "HIE Agents Knowledge Test",
                "customer_data": {
                    "name": "Luis Gonzalez",
                    "email": "luis@test.com",
                    "age": 40,
                    "occupation": "Business Owner"
                },
                "questions": [
                    {
                        "question": "¿Qué es exactamente el HIE que mencionas?",
                        "type": "hie_check"
                    },
                    {
                        "question": "¿Cuántos agentes tiene el sistema y cómo se llaman?",
                        "type": "hie_check"
                    },
                    {
                        "question": "¿Cuál agente me ayudaría con nutrición?",
                        "type": "hie_check"
                    }
                ]
            },
            {
                "name": "Hallucination Detection Test",
                "customer_data": {
                    "name": "Carmen Ruiz",
                    "email": "carmen@test.com",
                    "age": 45,
                    "occupation": "Doctor"
                },
                "questions": [
                    {
                        "question": "¿Tienen garantía de devolución?",
                        "type": "hallucination_check"
                    },
                    {
                        "question": "¿Está aprobado por alguna institución médica?",
                        "type": "hallucination_check"
                    },
                    {
                        "question": "¿Ofrecen algún descuento o promoción?",
                        "type": "hallucination_check"
                    }
                ]
            },
            {
                "name": "Program Differentiation Test",
                "customer_data": {
                    "name": "Roberto Diaz",
                    "email": "roberto@test.com",
                    "age": 55,
                    "occupation": "CEO"
                },
                "questions": [
                    {
                        "question": "Tengo 55 años, ¿qué programa me recomiendas y por qué?",
                        "type": "hallucination_check"
                    },
                    {
                        "question": "¿Cuál es la diferencia entre PRIME y LONGEVITY?",
                        "type": "hallucination_check"
                    },
                    {
                        "question": "¿Los precios son los mismos para ambos programas?",
                        "type": "price_check",
                        "program": "LONGEVITY"
                    }
                ]
            }
        ]
        
        all_results = []
        
        for scenario in test_scenarios:
            print(f"\n📋 Testing: {scenario['name']}")
            print("-" * 40)
            
            result = await self.test_product_knowledge_scenario(scenario)
            all_results.append(result)
            
            print(f"Overall Accuracy: {result['overall_accuracy']:.1f}%")
            
            # Print details for each question
            for q_result in result["questions"]:
                print(f"\n❓ {q_result['question']}")
                
                if q_result["type"] == "price_check":
                    eval = q_result["evaluation"]
                    print(f"   Prices mentioned: {eval['prices_mentioned']}")
                    if eval["incorrect_prices"]:
                        print(f"   ❌ Incorrect prices: {eval['incorrect_prices']}")
                    if eval["missing_tiers"]:
                        print(f"   ⚠️ Missing tiers: {', '.join(eval['missing_tiers'])}")
                    print(f"   Accuracy: {eval['accuracy']:.0f}%")
                    
                elif q_result["type"] == "hie_check":
                    eval = q_result["evaluation"]
                    print(f"   Agents mentioned: {', '.join(eval['agents_mentioned'])}")
                    if eval["incorrect_agents"]:
                        print(f"   ❌ Incorrect agents: {', '.join(eval['incorrect_agents'])}")
                    
                elif q_result["type"] == "hallucination_check":
                    eval = q_result["evaluation"]
                    if eval["hallucinations"]:
                        print(f"   ❌ Hallucinations detected: {', '.join(eval['hallucinations'])}")
                    else:
                        print(f"   ✅ No hallucinations detected")
        
        self._generate_knowledge_report(all_results)
    
    def _generate_knowledge_report(self, results: List[Dict[str, Any]]):
        """Genera reporte consolidado de conocimiento de productos."""
        print("\n" + "=" * 60)
        print("📊 PRODUCT KNOWLEDGE TEST REPORT")
        print("=" * 60)
        
        # Aggregate metrics
        total_questions = sum(len(r["questions"]) for r in results)
        total_passed = 0
        price_errors = []
        agent_errors = []
        hallucinations = []
        
        for result in results:
            for q in result["questions"]:
                if q["type"] == "price_check":
                    if q["evaluation"]["incorrect_prices"]:
                        price_errors.extend(q["evaluation"]["incorrect_prices"])
                    if q["evaluation"]["accuracy"] == 100:
                        total_passed += 1
                elif q["type"] == "hie_check":
                    if q["evaluation"]["incorrect_agents"]:
                        agent_errors.extend(q["evaluation"]["incorrect_agents"])
                    elif not q["evaluation"]["incorrect_agents"]:
                        total_passed += 1
                elif q["type"] == "hallucination_check":
                    if q["evaluation"]["hallucinations"]:
                        hallucinations.extend(q["evaluation"]["hallucinations"])
                    elif q["evaluation"]["passed"]:
                        total_passed += 1
        
        overall_accuracy = (total_passed / total_questions * 100) if total_questions > 0 else 0
        
        print(f"\n🎯 Overall Accuracy: {overall_accuracy:.1f}%")
        print(f"Questions Tested: {total_questions}")
        print(f"Questions Passed: {total_passed}")
        
        if price_errors:
            print(f"\n❌ Price Errors: {len(price_errors)}")
            for error in set(price_errors):
                print(f"  - Incorrect price: ${error}")
        
        if agent_errors:
            print(f"\n❌ Agent Errors: {len(agent_errors)}")
            for error in set(agent_errors):
                print(f"  - Incorrect agent: {error}")
        
        if hallucinations:
            print(f"\n❌ Hallucinations: {len(hallucinations)}")
            for h in set(hallucinations):
                print(f"  - {h}")
        
        # Pass/Fail determination
        print("\n" + "=" * 60)
        if overall_accuracy >= 90 and not hallucinations:
            print("✅ PRODUCT KNOWLEDGE TEST PASSED")
        else:
            print("❌ PRODUCT KNOWLEDGE TEST FAILED")
            if overall_accuracy < 90:
                print(f"  - Accuracy below 90%: {overall_accuracy:.1f}%")
            if hallucinations:
                print(f"  - Hallucinations detected: {len(set(hallucinations))}")
        print("=" * 60)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/intelligence/results/product_knowledge_{timestamp}.json"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump({
                "test_name": "Product Knowledge Test",
                "timestamp": timestamp,
                "overall_accuracy": overall_accuracy,
                "total_questions": total_questions,
                "price_errors": list(set(price_errors)),
                "agent_errors": list(set(agent_errors)),
                "hallucinations": list(set(hallucinations)),
                "detailed_results": results
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {filename}")


async def main():
    """Run the product knowledge test suite."""
    tester = ProductKnowledgeTester()
    
    try:
        await tester.run_product_knowledge_tests()
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())