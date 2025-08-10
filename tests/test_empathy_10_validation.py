#!/usr/bin/env python3
"""
Test de Validación de Empatía 10/10 - NGX Voice Sales Agent

Este test valida que las mejoras de empatía implementadas alcancen
un score de 10/10 en todas las categorías críticas.
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

# Añadir el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.ultra_empathy_greetings import get_greeting_engine, GreetingContext
from src.services.ultra_empathy_price_handler import get_price_handler, PriceObjectionContext
from src.services.advanced_empathy_engine import AdvancedEmpathyEngine
from src.services.emotional_intelligence_service import EmotionalProfile, EmotionalState
from src.services.intelligent_empathy_prompt_manager import IntelligentEmpathyPromptManager, EmotionalContext
from src.config.empathy_config import EmpathyConfig


class EmpathyValidator:
    """Validates empathy improvements achieve 10/10 scores."""
    
    def __init__(self):
        self.greeting_engine = get_greeting_engine()
        self.price_handler = get_price_handler()
        self.advanced_empathy = AdvancedEmpathyEngine()
        self.prompt_manager = IntelligentEmpathyPromptManager()
        self.test_results = []
        
    async def test_ultra_empathetic_greetings(self) -> Dict[str, Any]:
        """Test ultra-empathetic greeting generation."""
        print("\n🌟 TEST 1: Ultra-Empathetic Greetings")
        print("=" * 60)
        
        test_cases = [
            {
                "name": "Carlos",
                "age": 38,
                "initial_message": "Hola, soy CEO y estoy muy cansado últimamente",
                "expected_elements": ["cansado", "CEO", "Carlos", "?"]
            },
            {
                "name": "María",
                "age": 52,
                "initial_message": "Busco algo para mejorar mi energía y salud",
                "expected_elements": ["energía", "salud", "María", "?"]
            },
            {
                "name": "Roberto",
                "age": 45,
                "initial_message": "Me preocupa envejecer y perder vitalidad",
                "expected_elements": ["envejecer", "vitalidad", "Roberto", "?"]
            }
        ]
        
        results = []
        for case in test_cases:
            context = GreetingContext(
                customer_name=case["name"],
                age=case["age"],
                initial_message=case["initial_message"]
            )
            
            greeting = self.greeting_engine.generate_ultra_empathetic_greeting(context)
            
            # Validate greeting quality
            score = self._score_greeting(greeting, case)
            
            print(f"\n👤 Cliente: {case['name']}")
            print(f"📝 Mensaje: {case['initial_message']}")
            print(f"💬 Greeting: {greeting[:200]}...")
            print(f"⭐ Score: {score}/10")
            
            results.append({
                "case": case["name"],
                "greeting_preview": greeting[:150],
                "score": score,
                "has_name": case["name"] in greeting,
                "has_question": "?" in greeting,
                "addresses_concern": any(elem in greeting for elem in case["expected_elements"][:2]),
                "length": len(greeting),
                "micro_compliment": any(phrase in greeting for phrase in ["habla muy bien de", "admirable", "valoro mucho"])
            })
        
        avg_score = sum(r["score"] for r in results) / len(results)
        
        return {
            "test": "ultra_empathetic_greetings",
            "average_score": avg_score,
            "passed": avg_score >= 9.5,
            "results": results
        }
    
    async def test_price_objection_handling(self) -> Dict[str, Any]:
        """Test ultra-empathetic price objection responses."""
        print("\n💰 TEST 2: Price Objection Handling")
        print("=" * 60)
        
        test_cases = [
            {
                "name": "Ana",
                "objection": "¡$149 al mes! Es mucho dinero para mí",
                "tier": "pro",
                "emotion": "shock"
            },
            {
                "name": "Luis",
                "objection": "No sé si vale la pena el precio",
                "tier": "elite",
                "emotion": "doubt"
            },
            {
                "name": "Carmen",
                "objection": "Mi presupuesto es muy limitado ahora",
                "tier": "essential",
                "emotion": "concern"
            }
        ]
        
        results = []
        for case in test_cases:
            context = PriceObjectionContext(
                objection_text=case["objection"],
                customer_name=case["name"],
                detected_emotion=case["emotion"],
                tier_mentioned=case["tier"],
                conversation_phase="negotiation"
            )
            
            response_data = self.price_handler.generate_ultra_empathetic_response(context)
            response = response_data["response"]
            
            # Score response
            score = self._score_price_response(response, case, response_data)
            
            print(f"\n👤 Cliente: {case['name']}")
            print(f"💬 Objeción: {case['objection']}")
            print(f"🤝 Respuesta: {response[:200]}...")
            print(f"⭐ Score: {score}/10")
            print(f"🔧 Flexibilidad: {response_data.get('flexibility_option', 'N/A')}")
            
            results.append({
                "case": case["name"],
                "response_preview": response[:150],
                "score": score,
                "validates_concern": any(phrase in response for phrase in ["entiendo", "comprendo", "respeto"]),
                "offers_flexibility": response_data.get("flexibility_option") is not None,
                "reframes_value": "inversión" in response or "valor" in response,
                "empathy_score": response_data.get("empathy_score", 0)
            })
        
        avg_score = sum(r["score"] for r in results) / len(results)
        
        return {
            "test": "price_objection_handling",
            "average_score": avg_score,
            "passed": avg_score >= 9.5,
            "results": results
        }
    
    async def test_micro_signal_detection(self) -> Dict[str, Any]:
        """Test improved micro-signal detection."""
        print("\n🔍 TEST 3: Micro-Signal Detection")
        print("=" * 60)
        
        test_messages = [
            {
                "text": "Bueno... no sé si puedo pagar tanto. Estoy muy cansado y abrumado con todo.",
                "expected_signals": ["hesitation", "price_concern", "fatigue", "overwhelm"]
            },
            {
                "text": "Me encantaría mejorar pero tengo miedo al compromiso financiero. Ya he probado otras cosas.",
                "expected_signals": ["hope", "fear", "price_concern", "resistance"]
            },
            {
                "text": "Necesito esto urgentemente, no aguanto más el estrés, pero es mucho dinero.",
                "expected_signals": ["urgency", "frustration", "price_concern"]
            }
        ]
        
        results = []
        for test in test_messages:
            signals = await self.advanced_empathy._detect_micro_signals(test["text"])
            
            detected_types = [s.signal_type for s in signals]
            correct_detections = sum(1 for expected in test["expected_signals"] if expected in detected_types)
            
            print(f"\n📝 Mensaje: {test['text']}")
            print(f"🎯 Señales esperadas: {test['expected_signals']}")
            print(f"✅ Señales detectadas: {detected_types}")
            print(f"🔢 Precisión: {correct_detections}/{len(test['expected_signals'])}")
            
            # Check for combined signals
            combined_signals = [s for s in signals if s.signal_type in ["burnout_risk", "qualified_interest", "crisis_mode"]]
            if combined_signals:
                print(f"🔗 Señales combinadas: {[s.signal_type for s in combined_signals]}")
            
            accuracy = correct_detections / len(test["expected_signals"])
            
            results.append({
                "message_preview": test["text"][:80],
                "expected_count": len(test["expected_signals"]),
                "detected_count": len(signals),
                "correct_detections": correct_detections,
                "accuracy": accuracy,
                "has_combined_analysis": len(combined_signals) > 0,
                "confidence_avg": sum(s.confidence for s in signals) / len(signals) if signals else 0
            })
        
        avg_accuracy = sum(r["accuracy"] for r in results) / len(results)
        
        return {
            "test": "micro_signal_detection",
            "average_accuracy": avg_accuracy,
            "passed": avg_accuracy >= 0.85,
            "results": results
        }
    
    async def test_empathy_parameters(self) -> Dict[str, Any]:
        """Test GPT-4o parameter optimization."""
        print("\n⚙️ TEST 4: Empathy Parameter Optimization")
        print("=" * 60)
        
        contexts = ["greeting", "price_objection", "emotional_moment", "closing"]
        
        results = []
        for context in contexts:
            params = EmpathyConfig.get_context_params(context)
            addon = EmpathyConfig.get_system_prompt_addon(context)
            
            print(f"\n🎯 Context: {context}")
            print(f"🌡️ Temperature: {params.get('temperature', 'default')}")
            print(f"📏 Max Tokens: {params.get('max_tokens', 'default')}")
            print(f"✨ Special Instructions: {'Yes' if addon else 'No'}")
            
            # Validate parameters are optimized for empathy
            is_optimized = (
                params.get("temperature", 0) >= 0.88 and
                params.get("max_tokens", 0) >= 2500 and
                params.get("presence_penalty", 0) <= -0.2
            )
            
            results.append({
                "context": context,
                "temperature": params.get("temperature", 0),
                "is_warm": params.get("temperature", 0) >= 0.88,
                "allows_length": params.get("max_tokens", 0) >= 2500,
                "has_special_instructions": bool(addon),
                "optimized": is_optimized
            })
        
        optimization_rate = sum(1 for r in results if r["optimized"]) / len(results)
        
        return {
            "test": "empathy_parameters",
            "optimization_rate": optimization_rate,
            "passed": optimization_rate >= 0.9,
            "results": results
        }
    
    async def test_emotional_enhancement(self) -> Dict[str, Any]:
        """Test emotional response enhancement."""
        print("\n💗 TEST 5: Emotional Response Enhancement")
        print("=" * 60)
        
        test_cases = [
            {
                "base_response": "El precio de NGX Pro es $149 mensuales.",
                "emotional_context": EmotionalContext(
                    anxiety_level=0.8,
                    excitement_level=0.2,
                    confusion_level=0.6,
                    trust_level=0.4,
                    engagement_level=0.5,
                    decision_readiness=0.3,
                    primary_concern="price"
                ),
                "customer_profile": {"name": "Miguel", "age": 42}
            }
        ]
        
        results = []
        for case in test_cases:
            # Test original vs enhanced
            enhanced = await self.prompt_manager.enhance_response_with_empathy(
                case["base_response"],
                case["emotional_context"],
                case["customer_profile"],
                "negotiation"
            )
            
            # Measure empathy quality
            metrics = self.prompt_manager.measure_empathy_quality(enhanced)
            
            print(f"\n❌ Base: {case['base_response']}")
            print(f"✅ Enhanced: {enhanced[:200]}...")
            print(f"\n📊 Empathy Metrics:")
            print(f"   Overall: {metrics['overall_score']:.2f}")
            print(f"   Warmth: {metrics['warmth_score']:.2f}")
            print(f"   Validation: {metrics['validation_score']:.2f}")
            print(f"   Personalization: {metrics['personalization_score']:.2f}")
            
            results.append({
                "base_length": len(case["base_response"]),
                "enhanced_length": len(enhanced),
                "improvement_ratio": len(enhanced) / len(case["base_response"]),
                "overall_score": metrics['overall_score'],
                "all_metrics_high": all(v >= 0.7 for k, v in metrics.items() if k.endswith('_score'))
            })
        
        avg_score = sum(r["overall_score"] for r in results) / len(results)
        
        return {
            "test": "emotional_enhancement",
            "average_score": avg_score,
            "passed": avg_score >= 0.8,
            "results": results
        }
    
    def _score_greeting(self, greeting: str, case: Dict[str, Any]) -> float:
        """Score greeting quality out of 10."""
        score = 0
        
        # Name usage (2 points)
        name_count = greeting.count(case["name"])
        if name_count >= 1:
            score += 1
        if 2 <= name_count <= 3:  # Optimal range
            score += 1
            
        # Question presence (2 points)
        if "?" in greeting:
            score += 2
            
        # Addresses initial concern (2 points)
        if any(concern in greeting.lower() for concern in case["initial_message"].lower().split()):
            score += 2
            
        # Warmth indicators (2 points)
        warmth_phrases = ["gusto", "alegra", "privilegio", "honor", "encanta"]
        if any(phrase in greeting.lower() for phrase in warmth_phrases):
            score += 2
            
        # Length appropriate (1 point)
        if 200 <= len(greeting) <= 500:
            score += 1
            
        # Personal touch (1 point)
        if any(phrase in greeting for phrase in ["valoro mucho", "habla muy bien de ti", "admirable"]):
            score += 1
            
        return min(10, score)
    
    def _score_price_response(self, response: str, case: Dict[str, Any], response_data: Dict[str, Any]) -> float:
        """Score price objection response quality."""
        score = 0
        
        # Validation (3 points)
        validation_phrases = ["entiendo", "comprendo", "respeto", "valoro", "agradezco"]
        validation_count = sum(1 for phrase in validation_phrases if phrase in response.lower())
        score += min(3, validation_count)
        
        # Flexibility offered (2 points)
        if response_data.get("flexibility_option"):
            score += 2
            
        # Reframing value (2 points)
        if any(word in response for word in ["inversión", "valor", "recuperar", "retorno"]):
            score += 2
            
        # Personal approach (2 points)
        if case["name"] in response:
            score += 1
        if "?" in response:  # Has follow-up question
            score += 1
            
        # Never pushy (1 point)
        pushy_phrases = ["tienes que", "debes", "necesitas comprar"]
        if not any(phrase in response.lower() for phrase in pushy_phrases):
            score += 1
            
        return min(10, score)
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all empathy validation tests."""
        print("\n🚀 NGX VOICE AGENT - EMPATHY 10/10 VALIDATION")
        print("=" * 70)
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # Run all tests
        test_results = []
        
        tests = [
            self.test_ultra_empathetic_greetings,
            self.test_price_objection_handling,
            self.test_micro_signal_detection,
            self.test_empathy_parameters,
            self.test_emotional_enhancement
        ]
        
        for test_func in tests:
            try:
                result = await test_func()
                test_results.append(result)
            except Exception as e:
                print(f"\n❌ Error in {test_func.__name__}: {e}")
                import traceback
                traceback.print_exc()
                test_results.append({
                    "test": test_func.__name__,
                    "error": str(e),
                    "passed": False
                })
        
        # Calculate overall results
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r.get("passed", False))
        
        # Calculate weighted score
        scores = []
        weights = {
            "ultra_empathetic_greetings": 0.25,
            "price_objection_handling": 0.25,
            "micro_signal_detection": 0.20,
            "empathy_parameters": 0.15,
            "emotional_enhancement": 0.15
        }
        
        for result in test_results:
            test_name = result.get("test", "")
            weight = weights.get(test_name, 0.2)
            
            if "average_score" in result:
                scores.append(result["average_score"] * weight * 10)
            elif "average_accuracy" in result:
                scores.append(result["average_accuracy"] * weight * 10)
            elif "optimization_rate" in result:
                scores.append(result["optimization_rate"] * weight * 10)
        
        final_empathy_score = sum(scores) if scores else 0
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 FINAL EMPATHY VALIDATION RESULTS")
        print("=" * 70)
        
        for result in test_results:
            status = "✅ PASSED" if result.get("passed", False) else "❌ FAILED"
            print(f"{status} - {result.get('test', 'Unknown')}")
        
        print("\n" + "=" * 70)
        print(f"📈 Overall Empathy Score: {final_empathy_score:.1f}/10")
        print(f"✅ Tests Passed: {passed_tests}/{total_tests}")
        print("=" * 70)
        
        if final_empathy_score >= 9.5:
            print("\n🎉 ¡FELICITACIONES! Has alcanzado EMPATHY 10/10 🎉")
            print("El NGX Voice Agent ahora tiene empatía de clase mundial!")
        elif final_empathy_score >= 9.0:
            print("\n🌟 ¡Excelente! Empathy score de 9+/10")
            print("Solo pequeños ajustes necesarios para la perfección.")
        else:
            print(f"\n⚠️ Empathy score: {final_empathy_score:.1f}/10")
            print("Se requieren más mejoras para alcanzar el objetivo.")
        
        return {
            "final_score": final_empathy_score,
            "tests_passed": f"{passed_tests}/{total_tests}",
            "test_results": test_results,
            "timestamp": datetime.now().isoformat()
        }


async def main():
    """Run empathy validation tests."""
    validator = EmpathyValidator()
    results = await validator.run_all_tests()
    
    # Save results
    import json
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tests/results/empathy_10_validation_{timestamp}.json"
    
    os.makedirs("tests/results", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {filename}")


if __name__ == "__main__":
    asyncio.run(main())