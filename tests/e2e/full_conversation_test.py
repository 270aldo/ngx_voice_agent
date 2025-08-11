#!/usr/bin/env python3
"""
End-to-End Full Conversation Test for NGX Voice Sales Agent.
Simulates real customer conversations with various personalities and scenarios.
"""

import asyncio
import aiohttp
import time
import json
import random
from datetime import datetime
from typing import Dict, List, Any


class ConversationPersonality:
    """Different customer personalities for testing."""
    
    ENTHUSIASTIC = {
        "name": "Enthusiastic Entrepreneur",
        "messages": [
            "¡Hola! Estoy super emocionado por conocer NGX",
            "¡Wow! Eso suena increíble, cuéntame más sobre el HIE",
            "Me encanta la idea de optimizar mi tiempo, ¿qué incluye exactamente?",
            "¡Excelente! ¿Cuál es el precio? Estoy listo para empezar",
            "¡Perfecto! ¿Cómo puedo inscribirme ahora mismo?"
        ],
        "expected_outcome": "high_conversion"
    }
    
    SKEPTICAL = {
        "name": "Skeptical Business Owner",
        "messages": [
            "Hola, he visto muchos programas similares... ¿qué tiene de especial NGX?",
            "Eso suena bien en teoría, pero ¿tienen casos de éxito reales?",
            "¿Y cómo sé que esto no es otro curso más que promete y no cumple?",
            "El precio me parece alto, ¿realmente vale la pena la inversión?",
            "Necesito pensarlo más, ¿pueden enviarme más información?"
        ],
        "expected_outcome": "medium_conversion"
    }
    
    INDECISIVE = {
        "name": "Indecisive Fitness Coach",
        "messages": [
            "Hola, no estoy seguro si esto es para mí",
            "Mmm, suena interesante pero también complicado",
            "¿Y si no tengo tiempo? Mi agenda está muy llena",
            "No sé... tal vez... ¿qué opinas tú?",
            "Creo que necesito consultarlo con mi socio primero"
        ],
        "expected_outcome": "low_conversion"
    }
    
    PRICE_SENSITIVE = {
        "name": "Price-Sensitive Trainer",
        "messages": [
            "Hola, ¿cuánto cuesta el programa?",
            "Uf, es bastante caro... ¿hay opciones de pago?",
            "¿No tienen algo más económico? Mi presupuesto es limitado",
            "¿Qué garantías ofrecen? No puedo arriesgar tanto dinero",
            "¿Hay descuentos o promociones disponibles?"
        ],
        "expected_outcome": "objection_handling"
    }
    
    TECHNICAL = {
        "name": "Technical Nutritionist",
        "messages": [
            "Hola, ¿pueden explicarme la metodología científica detrás del HIE?",
            "¿Qué algoritmos de ML utilizan para la personalización?",
            "¿Cómo miden exactamente el ROI? Necesito métricas específicas",
            "¿Qué estudios respaldan su enfoque de productividad?",
            "¿Puedo ver un demo técnico antes de decidir?"
        ],
        "expected_outcome": "technical_conversation"
    }


class E2EConversationTester:
    """End-to-end conversation testing."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        
    async def run_conversation(self, session: aiohttp.ClientSession, 
                             personality: Dict[str, Any], 
                             test_id: int) -> Dict[str, Any]:
        """Run a complete conversation with given personality."""
        print(f"\n🎭 Testing: {personality['name']} (Test #{test_id})")
        print("-" * 50)
        
        conversation_id = None
        conversation_log = []
        metrics = {
            "start_time": time.time(),
            "personality": personality["name"],
            "test_id": test_id,
            "messages_sent": 0,
            "responses_received": 0,
            "errors": []
        }
        
        try:
            # Start conversation
            customer_data = {
                "id": f"e2e-test-{test_id}",
                "name": personality["name"],
                "email": f"test{test_id}@ngx.com",
                "age": random.randint(28, 45),
                "profession": random.choice([
                    "Entrepreneur", "Business Owner", "Fitness Coach",
                    "Personal Trainer", "Nutritionist"
                ])
            }
            
            print(f"Starting conversation as {customer_data['profession']}...")
            
            async with session.post(
                f"{self.base_url}/conversations/start",
                json={"customer_data": customer_data},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                result = await response.json()
                conversation_id = result.get("conversation_id")
                initial_message = result.get("message", "")
                
                conversation_log.append({
                    "role": "assistant",
                    "content": initial_message,
                    "timestamp": time.time()
                })
                
                print(f"NGX Agent: {initial_message[:100]}...")
            
            # Send personality-specific messages
            for i, message in enumerate(personality["messages"]):
                await asyncio.sleep(random.uniform(2, 4))  # Simulate thinking time
                
                print(f"\nCustomer: {message}")
                metrics["messages_sent"] += 1
                
                conversation_log.append({
                    "role": "user",
                    "content": message,
                    "timestamp": time.time()
                })
                
                # Send message
                async with session.post(
                    f"{self.base_url}/conversations/{conversation_id}/message",
                    json={"message": message},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    result = await response.json()
                    agent_response = result.get("response", "")
                    
                    conversation_log.append({
                        "role": "assistant",
                        "content": agent_response,
                        "timestamp": time.time()
                    })
                    
                    metrics["responses_received"] += 1
                    print(f"NGX Agent: {agent_response[:100]}...")
                    
                    # Analyze response
                    self._analyze_response(agent_response, metrics)
            
            # End conversation
            async with session.post(
                f"{self.base_url}/conversations/{conversation_id}/end",
                json={"reason": "test_completed"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                end_result = await response.json()
                metrics["conversion_achieved"] = end_result.get("conversion_achieved", False)
                metrics["final_tier"] = end_result.get("tier_detected", "Unknown")
            
        except Exception as e:
            metrics["errors"].append(str(e))
            print(f"❌ Error: {str(e)}")
        
        # Calculate final metrics
        metrics["end_time"] = time.time()
        metrics["duration"] = metrics["end_time"] - metrics["start_time"]
        metrics["conversation_id"] = conversation_id
        metrics["conversation_log"] = conversation_log
        metrics["expected_outcome"] = personality["expected_outcome"]
        metrics["success"] = len(metrics["errors"]) == 0
        
        return metrics
    
    def _analyze_response(self, response: str, metrics: Dict):
        """Analyze agent response for quality markers."""
        response_lower = response.lower()
        
        # Check for HIE mentions
        if "hie" in response_lower or "human intelligence ecosystem" in response_lower:
            metrics.setdefault("hie_mentions", 0)
            metrics["hie_mentions"] += 1
        
        # Check for agent mentions
        agent_names = ["nexus", "blaze", "sage", "wave", "spark", "nova", 
                      "luna", "stella", "code", "guardian", "node"]
        for agent in agent_names:
            if agent in response_lower:
                metrics.setdefault("agent_mentions", [])
                metrics["agent_mentions"].append(agent)
        
        # Check for pricing mentions
        if "$" in response or "precio" in response_lower or "price" in response_lower:
            metrics.setdefault("pricing_mentioned", True)
        
        # Check for urgency/scarcity
        urgency_words = ["ahora", "hoy", "limitado", "especial", "descuento", "bonus"]
        if any(word in response_lower for word in urgency_words):
            metrics.setdefault("urgency_used", True)
        
        # Check for empathy/personalization
        empathy_words = ["entiendo", "comprendo", "tu caso", "tu situación", "específicamente"]
        if any(word in response_lower for word in empathy_words):
            metrics.setdefault("empathy_shown", True)
    
    async def test_all_personalities(self):
        """Test all personality types."""
        personalities = [
            ConversationPersonality.ENTHUSIASTIC,
            ConversationPersonality.SKEPTICAL,
            ConversationPersonality.INDECISIVE,
            ConversationPersonality.PRICE_SENSITIVE,
            ConversationPersonality.TECHNICAL
        ]
        
        all_results = []
        
        async with aiohttp.ClientSession() as session:
            for i, personality in enumerate(personalities):
                result = await self.run_conversation(session, personality, i + 1)
                all_results.append(result)
                await asyncio.sleep(5)  # Cool down between tests
        
        self._print_summary(all_results)
        return all_results
    
    async def test_multilingual_conversation(self):
        """Test conversation in multiple languages."""
        print("\n🌍 MULTILINGUAL TEST")
        print("=" * 60)
        
        languages = [
            {
                "name": "Spanish Native",
                "messages": [
                    "Hola, ¿qué tal? Me interesa conocer sobre NGX",
                    "¿Cuáles son los beneficios principales?",
                    "¿Tienen testimonios en español?"
                ]
            },
            {
                "name": "English Speaker",
                "messages": [
                    "Hi there! I'd like to learn about NGX",
                    "What are the main benefits?",
                    "Do you have success stories?"
                ]
            },
            {
                "name": "Spanglish User",
                "messages": [
                    "Hey! Estoy interested en el programa",
                    "So, cuánto time necesito to dedicate?",
                    "Sounds good pero need más info about el pricing"
                ]
            }
        ]
        
        results = []
        async with aiohttp.ClientSession() as session:
            for i, lang_test in enumerate(languages):
                result = await self.run_conversation(session, {
                    "name": lang_test["name"],
                    "messages": lang_test["messages"],
                    "expected_outcome": "language_adaptation"
                }, 100 + i)
                results.append(result)
        
        return results
    
    def _print_summary(self, results: List[Dict]):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 E2E CONVERSATION TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(results)
        successful = sum(1 for r in results if r["success"])
        conversions = sum(1 for r in results if r.get("conversion_achieved", False))
        
        print(f"\nTests Run: {total_tests}")
        print(f"Successful: {successful} ({successful/total_tests*100:.1f}%)")
        print(f"Conversions: {conversions} ({conversions/total_tests*100:.1f}%)")
        
        print("\nPer Personality Results:")
        for result in results:
            print(f"\n{result['personality']}:")
            print(f"  Duration: {result['duration']:.2f}s")
            print(f"  Messages: {result['messages_sent']} sent, "
                  f"{result['responses_received']} received")
            print(f"  Conversion: {'✅' if result.get('conversion_achieved') else '❌'}")
            print(f"  Final Tier: {result.get('final_tier', 'Unknown')}")
            
            if result.get("hie_mentions"):
                print(f"  HIE Mentions: {result['hie_mentions']}")
            if result.get("agent_mentions"):
                print(f"  Agents Mentioned: {', '.join(set(result['agent_mentions']))}")
            if result.get("empathy_shown"):
                print(f"  Empathy: ✅")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/e2e/results/conversation_test_{timestamp}.json"
        
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, "w") as f:
            json.dump({
                "test_type": "e2e_conversation",
                "timestamp": timestamp,
                "summary": {
                    "total_tests": total_tests,
                    "successful": successful,
                    "conversions": conversions,
                    "conversion_rate": conversions/total_tests*100 if total_tests > 0 else 0
                },
                "detailed_results": results
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {filename}")


async def main():
    """Run all E2E conversation tests."""
    print("🎭 NGX Voice Sales Agent - E2E CONVERSATION TESTS")
    print("=" * 60)
    
    tester = E2EConversationTester()
    
    # Test all personalities
    personality_results = await tester.test_all_personalities()
    
    # Test multilingual
    multilingual_results = await tester.test_multilingual_conversation()
    
    print("\n✅ All E2E tests completed!")


if __name__ == "__main__":
    asyncio.run(main())