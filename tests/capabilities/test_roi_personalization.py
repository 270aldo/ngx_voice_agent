#!/usr/bin/env python3
"""
Test de ROI Personalization - NGX Voice Sales Agent

Casos de prueba por profesión:
- CEO: Validar 25% productividad = $X valor
- Consultant: ROI basado en hourly rate
- Entrepreneur: Cálculo de upside potential
"""

import asyncio
import aiohttp
import json
import os
from typing import Dict, List, Any, Tuple
from datetime import datetime

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")


class ROIPersonalizationTester:
    """Evalúa la personalización de cálculos ROI del agente."""
    
    def __init__(self):
        self.api_url = API_URL
        self.test_scenarios = self._create_test_scenarios()
        
    def _create_test_scenarios(self) -> List[Dict[str, Any]]:
        """Crea escenarios de prueba con ROI esperado."""
        return [
            {
                "profile": {
                    "name": "Michael Thompson",
                    "email": "mthompson@fortune500.com",
                    "occupation": "CEO",
                    "industry": "finance",
                    "company_size": "1000+ employees",
                    "age": 48,
                    "annual_salary": 500000,
                    "work_hours_per_week": 70
                },
                "scenario": "CEO_productivity",
                "messages": [
                    "Soy CEO de una empresa Fortune 500",
                    "Trabajo 70 horas a la semana y siento que no rindo al máximo",
                    "¿Cuál sería el ROI específico para alguien en mi posición?",
                    "Mi compensación anual es de $500,000"
                ],
                "expected_roi": {
                    "productivity_gain_percentage": 25,
                    "annual_value_range": [125000, 150000],  # 25% de $500K
                    "hourly_value": 137,  # $500K / 3640 horas
                    "time_savings_hours": 14,  # 3 horas/día productivas
                    "stress_reduction_value": 15000
                },
                "validation_points": [
                    "productivity_calculation",
                    "executive_specific_metrics",
                    "time_value_analysis",
                    "stress_cost_consideration"
                ]
            },
            {
                "profile": {
                    "name": "Sarah Chen",
                    "email": "schen@consultingfirm.com",
                    "occupation": "Senior Consultant",
                    "industry": "consulting",
                    "age": 35,
                    "hourly_rate": 150,
                    "billable_hours_per_week": 50,
                    "utilization_rate": 0.85
                },
                "scenario": "consultant_billable_hours",
                "messages": [
                    "Soy consultora senior con rate de $150/hora",
                    "Actualmente facturo 50 horas semanales pero mi energía baja después del almuerzo",
                    "¿Cómo NGX puede ayudarme a mantener mi performance todo el día?",
                    "¿Cuál sería mi ROI considerando mi tarifa horaria?"
                ],
                "expected_roi": {
                    "billable_hours_increase": 10,  # 10-15% más horas productivas
                    "weekly_revenue_increase": 1500,  # 10 horas x $150
                    "annual_revenue_increase": 78000,  # 52 semanas
                    "energy_optimization_value": 8000,
                    "focus_improvement_percentage": 20
                },
                "validation_points": [
                    "hourly_rate_calculation",
                    "billable_hours_optimization",
                    "consultant_specific_metrics",
                    "afternoon_energy_solution"
                ]
            },
            {
                "profile": {
                    "name": "David Martinez",
                    "email": "dmartinez@techstartup.io",
                    "occupation": "Startup Founder",
                    "industry": "technology",
                    "age": 32,
                    "company_stage": "Series A",
                    "current_revenue": 2000000,
                    "growth_target": 5000000,
                    "work_hours_per_week": 80
                },
                "scenario": "entrepreneur_growth_potential",
                "messages": [
                    "Soy founder de una startup en Series A",
                    "Trabajo 80 horas semanales y necesito escalar de $2M a $5M en revenue",
                    "Mi energía y focus son críticos para el crecimiento",
                    "¿Qué ROI puedo esperar como emprendedor?"
                ],
                "expected_roi": {
                    "decision_making_improvement": 40,  # % faster decisions
                    "growth_acceleration_factor": 1.3,  # 30% faster growth
                    "opportunity_cost_avoided": 100000,  # bad decisions avoided
                    "energy_sustainability_value": 10000,
                    "burnout_prevention_value": 50000,
                    "upside_potential_multiplier": 2.5
                },
                "validation_points": [
                    "entrepreneur_specific_metrics",
                    "growth_acceleration_focus",
                    "decision_quality_improvement",
                    "burnout_prevention_emphasis"
                ]
            },
            {
                "profile": {
                    "name": "Dr. Jennifer Williams",
                    "email": "jwilliams@medicalpractice.com",
                    "occupation": "Médico Especialista",
                    "industry": "healthcare",
                    "age": 45,
                    "patients_per_day": 25,
                    "average_consultation_value": 200,
                    "work_days_per_week": 5
                },
                "scenario": "healthcare_longevity_focus",
                "messages": [
                    "Soy médica especialista y veo 25 pacientes al día",
                    "Me preocupa mantener mi capacidad de atención por los próximos 20 años",
                    "¿Cuál es el ROI del programa LONGEVITY para alguien en medicina?",
                    "Necesito mantener mi agudeza mental y energía"
                ],
                "expected_roi": {
                    "career_extension_years": 5,  # 5 años más de práctica
                    "lifetime_earnings_increase": 1300000,  # 5 años x $260K
                    "cognitive_performance_retention": 95,  # % capacidad mantenida
                    "health_cost_avoidance": 30000,
                    "quality_of_life_value": 25000
                },
                "validation_points": [
                    "longevity_program_focus",
                    "career_extension_calculation",
                    "cognitive_preservation_emphasis",
                    "healthcare_professional_specific"
                ]
            }
        ]
    
    async def test_roi_calculation(self, scenario_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prueba el cálculo de ROI para un escenario específico.
        """
        profile = scenario_data["profile"]
        scenario = scenario_data["scenario"]
        
        print(f"\n💰 Testing ROI: {scenario}")
        print(f"   Profile: {profile['name']} - {profile['occupation']}")
        
        results = {
            "scenario": scenario,
            "profile_name": profile["name"],
            "occupation": profile["occupation"],
            "roi_calculations_found": {},
            "expected_vs_actual": {},
            "validation_scores": {},
            "response_quality": [],
            "overall_accuracy": 0
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
                        for message in scenario_data["messages"]:
                            async with session.post(
                                f"{self.api_url}/conversations/{conversation_id}/message",
                                json={"message": message}
                            ) as msg_response:
                                if msg_response.status == 200:
                                    msg_data = await msg_response.json()
                                    response_text = msg_data.get("response", "")
                                    
                                    # Analizar respuesta para ROI
                                    roi_analysis = self._analyze_roi_response(
                                        response_text,
                                        scenario_data["expected_roi"],
                                        scenario_data["validation_points"]
                                    )
                                    results["response_quality"].append(roi_analysis)
                                    
                                    # Capturar cálculos ROI si están disponibles
                                    if "roi_calculation" in msg_data:
                                        results["roi_calculations_found"].update(msg_data["roi_calculation"])
                        
                        # Obtener análisis ROI final
                        async with session.post(
                            f"{self.api_url}/analytics/roi-analysis",
                            json={
                                "conversation_id": conversation_id,
                                "customer_profile": profile
                            }
                        ) as roi_response:
                            if roi_response.status == 200:
                                roi_data = await roi_response.json()
                                results["roi_calculations_found"] = roi_data.get("roi_calculations", {})
                        
                        # Validar contra valores esperados
                        results["validation_scores"] = self._validate_roi_calculations(
                            results["roi_calculations_found"],
                            scenario_data["expected_roi"],
                            scenario_data["validation_points"]
                        )
                        
                        # Calcular precisión general
                        results["overall_accuracy"] = self._calculate_overall_accuracy(results)
                        
                        # Imprimir resultados
                        print(f"   ROI Accuracy: {results['overall_accuracy']:.0%}")
                        
                        if results["overall_accuracy"] >= 0.8:
                            print("   ✅ ROI calculation accurate!")
                        else:
                            print("   ⚠️  ROI calculation needs improvement")
                        
                        # Mostrar métricas clave encontradas
                        if results["roi_calculations_found"]:
                            print("   Key ROI metrics found:")
                            for key, value in list(results["roi_calculations_found"].items())[:3]:
                                print(f"     - {key}: {value}")
                        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["error"] = str(e)
        
        return results
    
    def _analyze_roi_response(self, response: str, expected_roi: Dict[str, Any], validation_points: List[str]) -> Dict[str, Any]:
        """
        Analiza la respuesta para encontrar elementos de ROI.
        """
        analysis = {
            "roi_elements_found": [],
            "specific_numbers_mentioned": [],
            "validation_points_addressed": {},
            "personalization_level": 0
        }
        
        response_lower = response.lower()
        
        # Buscar elementos ROI específicos
        roi_keywords = {
            "productivity": ["productividad", "rendimiento", "performance"],
            "time_savings": ["horas", "tiempo", "ahorro de tiempo"],
            "revenue": ["ingresos", "facturación", "revenue"],
            "value": ["valor", "beneficio", "retorno"],
            "percentage": ["%", "por ciento", "porcentaje"]
        }
        
        for category, keywords in roi_keywords.items():
            if any(keyword in response_lower for keyword in keywords):
                analysis["roi_elements_found"].append(category)
        
        # Extraer números mencionados
        import re
        numbers = re.findall(r'\$?[\d,]+(?:\.\d{2})?%?', response)
        analysis["specific_numbers_mentioned"] = numbers
        
        # Verificar puntos de validación
        for point in validation_points:
            if point == "productivity_calculation" and "productividad" in response_lower:
                analysis["validation_points_addressed"][point] = True
            elif point == "hourly_rate_calculation" and ("hora" in response_lower or "hourly" in response_lower):
                analysis["validation_points_addressed"][point] = True
            elif point == "executive_specific_metrics" and any(word in response_lower for word in ["ejecutivo", "ceo", "liderazgo"]):
                analysis["validation_points_addressed"][point] = True
            elif point == "entrepreneur_specific_metrics" and any(word in response_lower for word in ["emprendedor", "startup", "crecimiento"]):
                analysis["validation_points_addressed"][point] = True
            elif point == "longevity_program_focus" and "longevity" in response_lower:
                analysis["validation_points_addressed"][point] = True
            else:
                analysis["validation_points_addressed"][point] = False
        
        # Calcular nivel de personalización
        personalization_indicators = 0
        if any(str(value) in response for key, value in expected_roi.items() if isinstance(value, (int, float))):
            personalization_indicators += 2
        if len(analysis["specific_numbers_mentioned"]) > 2:
            personalization_indicators += 1
        if sum(analysis["validation_points_addressed"].values()) > len(validation_points) / 2:
            personalization_indicators += 1
        
        analysis["personalization_level"] = min(personalization_indicators / 4, 1.0)
        
        return analysis
    
    def _validate_roi_calculations(self, found: Dict[str, Any], expected: Dict[str, Any], validation_points: List[str]) -> Dict[str, float]:
        """
        Valida los cálculos ROI encontrados contra los esperados.
        """
        scores = {}
        
        for key, expected_value in expected.items():
            score = 0
            
            if key in found:
                found_value = found[key]
                
                # Manejar rangos
                if isinstance(expected_value, list) and len(expected_value) == 2:
                    if isinstance(found_value, (int, float)):
                        if expected_value[0] <= found_value <= expected_value[1]:
                            score = 1.0
                        else:
                            # Partial credit si está cerca
                            distance = min(abs(found_value - expected_value[0]), abs(found_value - expected_value[1]))
                            range_size = expected_value[1] - expected_value[0]
                            score = max(0, 1 - (distance / range_size))
                
                # Valores exactos con tolerancia
                elif isinstance(expected_value, (int, float)) and isinstance(found_value, (int, float)):
                    tolerance = 0.2  # 20% tolerance
                    if abs(found_value - expected_value) / expected_value <= tolerance:
                        score = 1.0
                    else:
                        score = max(0, 1 - abs(found_value - expected_value) / expected_value)
                
                # Comparación directa
                elif found_value == expected_value:
                    score = 1.0
            
            scores[key] = score
        
        # Bonus por abordar puntos de validación
        validation_score = sum(1 for point in validation_points if point in str(found)) / len(validation_points)
        scores["validation_points"] = validation_score
        
        return scores
    
    def _calculate_overall_accuracy(self, results: Dict[str, Any]) -> float:
        """
        Calcula la precisión general del cálculo ROI.
        """
        if not results["validation_scores"]:
            return 0.0
        
        # Promedio ponderado de scores
        weights = {
            "validation_points": 0.3,
            "default": 0.7 / (len(results["validation_scores"]) - 1) if len(results["validation_scores"]) > 1 else 0.7
        }
        
        total_score = 0
        for key, score in results["validation_scores"].items():
            weight = weights.get(key, weights["default"])
            total_score += score * weight
        
        # Bonus por calidad de respuesta
        if results["response_quality"]:
            avg_personalization = sum(r["personalization_level"] for r in results["response_quality"]) / len(results["response_quality"])
            total_score = total_score * 0.8 + avg_personalization * 0.2
        
        return min(total_score, 1.0)
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Ejecuta todos los tests de personalización ROI.
        """
        print("\n💎 INICIANDO TESTS DE ROI PERSONALIZATION")
        print("=" * 70)
        
        all_results = {
            "test_suite": "ROI Personalization",
            "timestamp": datetime.now().isoformat(),
            "scenarios_tested": len(self.test_scenarios),
            "results": []
        }
        
        # Probar cada escenario
        for scenario_data in self.test_scenarios:
            result = await self.test_roi_calculation(scenario_data)
            all_results["results"].append(result)
            
            # Pequeña pausa entre tests
            await asyncio.sleep(2)
        
        # Calcular métricas globales
        successful_tests = [r for r in all_results["results"] if "error" not in r]
        
        if successful_tests:
            all_results["overall_accuracy"] = sum(r["overall_accuracy"] for r in successful_tests) / len(successful_tests)
            all_results["high_accuracy_count"] = len([r for r in successful_tests if r["overall_accuracy"] >= 0.8])
            
            # Accuracy por tipo de profesión
            all_results["accuracy_by_occupation"] = {}
            for result in successful_tests:
                occupation = result["occupation"]
                if occupation not in all_results["accuracy_by_occupation"]:
                    all_results["accuracy_by_occupation"][occupation] = []
                all_results["accuracy_by_occupation"][occupation].append(result["overall_accuracy"])
            
            # Promediar por ocupación
            for occupation, accuracies in all_results["accuracy_by_occupation"].items():
                all_results["accuracy_by_occupation"][occupation] = sum(accuracies) / len(accuracies)
        
        # Resumen
        print("\n📊 RESUMEN DE RESULTADOS")
        print("=" * 70)
        print(f"Escenarios probados: {len(self.test_scenarios)}")
        print(f"Tests exitosos: {len(successful_tests)}")
        
        if successful_tests:
            print(f"Accuracy promedio: {all_results['overall_accuracy']:.0%}")
            print(f"Tests con alta precisión (>80%): {all_results['high_accuracy_count']}/{len(successful_tests)}")
            
            print("\nAccuracy por ocupación:")
            for occupation, accuracy in all_results["accuracy_by_occupation"].items():
                print(f"  - {occupation}: {accuracy:.0%}")
        
        # Guardar resultados
        results_file = f"tests/capabilities/results/roi_personalization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Resultados guardados en: {results_file}")
        
        return all_results


async def main():
    """Función principal para ejecutar los tests."""
    tester = ROIPersonalizationTester()
    results = await tester.run_all_tests()
    
    # Determinar éxito
    success = results.get("overall_accuracy", 0) >= 0.75  # 75% o más es éxito
    
    if success:
        print("\n✅ ROI PERSONALIZATION: FUNCIONANDO CORRECTAMENTE")
        print(f"   Precisión: {results.get('overall_accuracy', 0):.0%}")
    else:
        print("\n❌ ROI PERSONALIZATION: REQUIERE REVISIÓN")
        print(f"   Precisión actual: {results.get('overall_accuracy', 0):.0%} (objetivo: 75%+)")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)