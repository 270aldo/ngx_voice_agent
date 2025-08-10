#!/usr/bin/env python3
"""
Test de Archetype Detection - NGX Voice Sales Agent

Probar con 5 perfiles diferentes:
- CEO (Optimizer → PRIME Premium)
- Doctor de 55 años (Architect → LONGEVITY Premium)
- Startup founder (Explorer → PRO)
- Manager cauteloso (Pragmatist → ESSENTIAL)
- Abogado exitoso (Maximizer → ELITE)
"""

import asyncio
import aiohttp
import json
import os
from typing import Dict, List, Any
from datetime import datetime

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")


class ArchetypeDetectionTester:
    """Evalúa la detección de arquetipos y tier assignment del agente."""
    
    def __init__(self):
        self.api_url = API_URL
        self.test_profiles = self._create_test_profiles()
        
    def _create_test_profiles(self) -> List[Dict[str, Any]]:
        """Crea los 5 perfiles de prueba con resultados esperados."""
        return [
            {
                "profile": {
                    "name": "Roberto Chen",
                    "email": "rchen@techcorp.com",
                    "age": 42,
                    "occupation": "CEO",
                    "industry": "technology",
                    "company_size": "500+ employees",
                    "interests": ["efficiency", "leadership", "innovation"],
                    "pain_points": ["time management", "decision fatigue", "team performance"],
                    "communication_style": "direct"
                },
                "expected": {
                    "archetype": "optimizer",
                    "tier": "PRIME Premium",
                    "reasoning": "Executive focused on performance and efficiency"
                },
                "test_messages": [
                    "Necesito maximizar mi productividad como CEO",
                    "Manejo un equipo de 500 personas y necesito estar al 100%",
                    "¿Cómo puede NGX ayudarme a tomar mejores decisiones más rápido?"
                ]
            },
            {
                "profile": {
                    "name": "Dr. Patricia Mendez",
                    "email": "pmendez@healthcenter.com",
                    "age": 55,
                    "occupation": "Médico Jefe",
                    "industry": "healthcare",
                    "interests": ["longevidad", "salud preventiva", "bienestar"],
                    "pain_points": ["envejecimiento", "energía", "balance vida-trabajo"],
                    "communication_style": "analytical"
                },
                "expected": {
                    "archetype": "architect",
                    "tier": "LONGEVITY Premium",
                    "reasoning": "Healthcare professional focused on longevity"
                },
                "test_messages": [
                    "Como médico, me preocupa mi propio envejecimiento",
                    "Quiero mantener mi vitalidad por los próximos 20 años",
                    "¿Qué evidencia científica respalda el programa de longevidad?"
                ]
            },
            {
                "profile": {
                    "name": "Alex Rivera",
                    "email": "alex@startuphub.io",
                    "age": 28,
                    "occupation": "Startup Founder",
                    "industry": "fintech",
                    "interests": ["innovación", "crecimiento rápido", "tecnología"],
                    "pain_points": ["burnout", "foco", "energía sostenible"],
                    "communication_style": "enthusiastic"
                },
                "expected": {
                    "archetype": "explorer",
                    "tier": "PRO",
                    "reasoning": "Young entrepreneur, early adopter mindset"
                },
                "test_messages": [
                    "Estoy construyendo mi startup y necesito energía constante",
                    "Me interesa probar tecnología cutting-edge para optimización personal",
                    "¿Tienen algún programa beta o early access?"
                ]
            },
            {
                "profile": {
                    "name": "Carlos Jimenez",
                    "email": "cjimenez@corporation.com",
                    "age": 38,
                    "occupation": "Manager de Operaciones",
                    "industry": "manufacturing",
                    "interests": ["mejora gradual", "resultados probados", "costo-beneficio"],
                    "pain_points": ["estrés", "productividad del equipo", "presupuesto"],
                    "communication_style": "cautious"
                },
                "expected": {
                    "archetype": "pragmatist",
                    "tier": "ESSENTIAL",
                    "reasoning": "Cost-conscious manager seeking proven solutions"
                },
                "test_messages": [
                    "Necesito algo que funcione pero que no sea muy caro",
                    "¿Cuál es la opción más básica que tienen?",
                    "Prefiero empezar con algo pequeño y ver resultados antes de invertir más"
                ]
            },
            {
                "profile": {
                    "name": "Isabella Dominguez",
                    "email": "idominguez@lawfirm.com",
                    "age": 45,
                    "occupation": "Socia Senior - Abogada",
                    "industry": "legal",
                    "interests": ["excelencia", "status", "exclusividad"],
                    "pain_points": ["mantener ventaja competitiva", "imagen profesional", "networking"],
                    "communication_style": "sophisticated"
                },
                "expected": {
                    "archetype": "maximizer",
                    "tier": "ELITE",
                    "reasoning": "High-achiever seeking premium/exclusive solutions"
                },
                "test_messages": [
                    "Busco lo mejor de lo mejor en optimización personal",
                    "El precio no es problema si los resultados son excepcionales",
                    "¿Qué beneficios exclusivos tienen para profesionales de alto nivel?"
                ]
            }
        ]
    
    async def test_archetype_detection(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prueba la detección de arquetipo para un perfil específico.
        """
        profile = profile_data["profile"]
        expected = profile_data["expected"]
        
        print(f"\n🎯 Testing: {profile['name']} - {profile['occupation']}")
        print(f"   Expected: {expected['archetype']} → {expected['tier']}")
        
        results = {
            "profile_name": profile["name"],
            "occupation": profile["occupation"],
            "expected_archetype": expected["archetype"],
            "expected_tier": expected["tier"],
            "detected_archetype": None,
            "detected_tier": None,
            "confidence_scores": {},
            "detection_accuracy": 0,
            "response_quality": []
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
                        
                        # Enviar mensajes de prueba
                        for i, message in enumerate(profile_data["test_messages"]):
                            async with session.post(
                                f"{self.api_url}/conversations/{conversation_id}/message",
                                json={"message": message}
                            ) as msg_response:
                                if msg_response.status == 200:
                                    msg_data = await msg_response.json()
                                    
                                    # Evaluar respuesta
                                    response_analysis = self._analyze_response(
                                        msg_data.get("response", ""),
                                        expected
                                    )
                                    results["response_quality"].append(response_analysis)
                                    
                                    # Capturar detección de tier si está disponible
                                    if "tier_detection" in msg_data:
                                        results["detected_tier"] = msg_data["tier_detection"].get("tier")
                                        results["confidence_scores"]["tier"] = msg_data["tier_detection"].get("confidence", 0)
                                    
                                    if "archetype_detection" in msg_data:
                                        results["detected_archetype"] = msg_data["archetype_detection"].get("archetype")
                                        results["confidence_scores"]["archetype"] = msg_data["archetype_detection"].get("confidence", 0)
                        
                        # Obtener análisis final de la conversación
                        async with session.get(
                            f"{self.api_url}/conversations/{conversation_id}/analysis"
                        ) as analysis_response:
                            if analysis_response.status == 200:
                                analysis = await analysis_response.json()
                                
                                # Extraer detecciones finales
                                if "customer_profile" in analysis:
                                    customer_profile = analysis["customer_profile"]
                                    results["detected_archetype"] = customer_profile.get("archetype", results["detected_archetype"])
                                    results["detected_tier"] = customer_profile.get("recommended_tier", results["detected_tier"])
                                    
                                    if "confidence_scores" in customer_profile:
                                        results["confidence_scores"].update(customer_profile["confidence_scores"])
                        
                        # Calcular accuracy
                        results["detection_accuracy"] = self._calculate_accuracy(results, expected)
                        
                        # Imprimir resultados
                        print(f"   Detected: {results['detected_archetype']} → {results['detected_tier']}")
                        print(f"   Accuracy: {results['detection_accuracy']:.0%}")
                        
                        if results["detection_accuracy"] == 1.0:
                            print("   ✅ Perfect match!")
                        else:
                            print("   ⚠️  Mismatch detected")
                        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["error"] = str(e)
        
        return results
    
    def _analyze_response(self, response: str, expected: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza la calidad de la respuesta en relación al arquetipo esperado.
        """
        analysis = {
            "mentions_expected_program": False,
            "appropriate_language": False,
            "tier_mentioned": None,
            "archetype_signals": []
        }
        
        response_lower = response.lower()
        
        # Verificar mención del programa esperado
        if expected["archetype"] == "optimizer" and "prime" in response_lower:
            analysis["mentions_expected_program"] = True
        elif expected["archetype"] == "architect" and "longevity" in response_lower:
            analysis["mentions_expected_program"] = True
        elif expected["archetype"] == "explorer" and ("pro" in response_lower or "beta" in response_lower):
            analysis["mentions_expected_program"] = True
        elif expected["archetype"] == "pragmatist" and "essential" in response_lower:
            analysis["mentions_expected_program"] = True
        elif expected["archetype"] == "maximizer" and "elite" in response_lower:
            analysis["mentions_expected_program"] = True
        
        # Verificar lenguaje apropiado
        if expected["archetype"] == "optimizer":
            if any(word in response_lower for word in ["productividad", "rendimiento", "eficiencia", "roi"]):
                analysis["appropriate_language"] = True
                analysis["archetype_signals"].append("performance_language")
        
        elif expected["archetype"] == "architect":
            if any(word in response_lower for word in ["longevidad", "vitalidad", "prevención", "largo plazo"]):
                analysis["appropriate_language"] = True
                analysis["archetype_signals"].append("longevity_language")
        
        elif expected["archetype"] == "explorer":
            if any(word in response_lower for word in ["innovación", "cutting-edge", "beta", "early access"]):
                analysis["appropriate_language"] = True
                analysis["archetype_signals"].append("innovation_language")
        
        elif expected["archetype"] == "pragmatist":
            if any(word in response_lower for word in ["básico", "empezar", "gradual", "resultados probados"]):
                analysis["appropriate_language"] = True
                analysis["archetype_signals"].append("practical_language")
        
        elif expected["archetype"] == "maximizer":
            if any(word in response_lower for word in ["premium", "exclusivo", "élite", "excepcional"]):
                analysis["appropriate_language"] = True
                analysis["archetype_signals"].append("premium_language")
        
        # Detectar tier mencionado
        if "$3,997" in response or "3997" in response:
            analysis["tier_mentioned"] = "Premium"
        elif "$199" in response:
            analysis["tier_mentioned"] = "Elite"
        elif "$149" in response:
            analysis["tier_mentioned"] = "Pro"
        elif "$79" in response:
            analysis["tier_mentioned"] = "Essential"
        
        return analysis
    
    def _calculate_accuracy(self, results: Dict[str, Any], expected: Dict[str, Any]) -> float:
        """
        Calcula la precisión de la detección.
        """
        score = 0
        total = 2  # Archetype + Tier
        
        # Comparar archetype
        if results["detected_archetype"] and results["detected_archetype"].lower() == expected["archetype"].lower():
            score += 1
        
        # Comparar tier (flexible con mayúsculas/minúsculas)
        if results["detected_tier"]:
            detected_tier_normalized = results["detected_tier"].upper().replace("_", " ")
            expected_tier_normalized = expected["tier"].upper()
            
            if detected_tier_normalized == expected_tier_normalized:
                score += 1
            elif detected_tier_normalized in expected_tier_normalized or expected_tier_normalized in detected_tier_normalized:
                score += 0.5  # Partial match
        
        return score / total
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Ejecuta todos los tests de detección de arquetipos.
        """
        print("\n🧬 INICIANDO TESTS DE ARCHETYPE DETECTION")
        print("=" * 70)
        
        all_results = {
            "test_suite": "Archetype Detection",
            "timestamp": datetime.now().isoformat(),
            "profiles_tested": len(self.test_profiles),
            "results": []
        }
        
        # Probar cada perfil
        for profile_data in self.test_profiles:
            result = await self.test_archetype_detection(profile_data)
            all_results["results"].append(result)
            
            # Pequeña pausa entre tests
            await asyncio.sleep(2)
        
        # Calcular métricas globales
        successful_detections = [r for r in all_results["results"] if "error" not in r]
        
        if successful_detections:
            all_results["overall_accuracy"] = sum(r["detection_accuracy"] for r in successful_detections) / len(successful_detections)
            all_results["perfect_matches"] = len([r for r in successful_detections if r["detection_accuracy"] == 1.0])
            
            # Accuracy por tipo
            all_results["accuracy_by_archetype"] = {}
            for archetype in ["optimizer", "architect", "explorer", "pragmatist", "maximizer"]:
                archetype_results = [r for r in successful_detections if r["expected_archetype"] == archetype]
                if archetype_results:
                    all_results["accuracy_by_archetype"][archetype] = sum(r["detection_accuracy"] for r in archetype_results) / len(archetype_results)
        
        # Resumen
        print("\n📊 RESUMEN DE RESULTADOS")
        print("=" * 70)
        print(f"Perfiles probados: {len(self.test_profiles)}")
        print(f"Detecciones exitosas: {len(successful_detections)}")
        
        if successful_detections:
            print(f"Accuracy promedio: {all_results['overall_accuracy']:.0%}")
            print(f"Matches perfectos: {all_results['perfect_matches']}/{len(self.test_profiles)}")
            
            print("\nAccuracy por arquetipo:")
            for archetype, accuracy in all_results["accuracy_by_archetype"].items():
                print(f"  - {archetype.capitalize()}: {accuracy:.0%}")
        
        # Guardar resultados
        results_file = f"tests/capabilities/results/archetype_detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Resultados guardados en: {results_file}")
        
        return all_results


async def main():
    """Función principal para ejecutar los tests."""
    tester = ArchetypeDetectionTester()
    results = await tester.run_all_tests()
    
    # Determinar éxito
    success = results.get("overall_accuracy", 0) >= 0.8  # 80% o más es éxito
    
    if success:
        print("\n✅ ARCHETYPE DETECTION: FUNCIONANDO CORRECTAMENTE")
        print(f"   Precisión: {results.get('overall_accuracy', 0):.0%}")
    else:
        print("\n❌ ARCHETYPE DETECTION: REQUIERE REVISIÓN")
        print(f"   Precisión actual: {results.get('overall_accuracy', 0):.0%} (objetivo: 80%+)")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)