#!/usr/bin/env python3
"""
Test suite para validar la precisión del NGX ROI Calculator.

Objetivos:
1. Verificar cálculos de ROI para diferentes perfiles
2. Validar que los porcentajes sean realistas
3. Comprobar consistencia en las recomendaciones
4. Asegurar que no hay errores de cálculo
"""

import asyncio
import pytest
from typing import Dict, List, Any, Tuple
from datetime import datetime
import json
import sys
import os

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.ngx_roi_calculator import NGXROICalculator, ROIMetric, NGXROIResult


class TestROICalculatorAccuracy:
    """Suite de tests para validar precisión del ROI Calculator."""
    
    @pytest.fixture
    async def calculator(self):
        """Fixture para crear instancia del calculator."""
        return NGXROICalculator()
    
    # Test 1: Validar rangos de ROI por profesión
    @pytest.mark.asyncio
    async def test_roi_ranges_by_profession(self, calculator):
        """Verifica que los ROI estén en rangos realistas por profesión."""
        
        test_cases = [
            # (profession, age, expected_min_roi, expected_max_roi)
            ("ceo", 45, 200, 8000),  # CEOs can see very high ROI
            ("executive", 40, 150, 6000),
            ("consultant", 35, 100, 5000),
            ("entrepreneur", 30, 150, 7000),  # High variability
            ("manager", 35, 80, 4000),
            ("professional", 30, 50, 3000)
        ]
        
        results = []
        for profession, age, min_roi, max_roi in test_cases:
            user_context = {
                'profession': profession,
                'age': age,
                'budget_sensitivity': 'medium'
            }
            
            # Test all tiers
            for tier in ['essential', 'pro', 'elite']:
                roi_result = await calculator.calculate_ngx_roi(user_context, tier)
                
                # Validar rango
                assert min_roi <= roi_result.total_roi_percentage <= max_roi, \
                    f"{profession} - {tier}: ROI {roi_result.total_roi_percentage}% fuera de rango [{min_roi}, {max_roi}]"
                
                # Validar payback period
                assert 1 <= roi_result.payback_period_months <= 24, \
                    f"{profession} - {tier}: Payback period {roi_result.payback_period_months} meses no realista"
                
                results.append({
                    'profession': profession,
                    'tier': tier,
                    'roi': roi_result.total_roi_percentage,
                    'payback': roi_result.payback_period_months
                })
        
        # Verificar progresión lógica: elite > pro > essential
        for profession in set(tc[0] for tc in test_cases):
            prof_results = [r for r in results if r['profession'] == profession]
            essential_roi = next(r['roi'] for r in prof_results if r['tier'] == 'essential')
            pro_roi = next(r['roi'] for r in prof_results if r['tier'] == 'pro')
            elite_roi = next(r['roi'] for r in prof_results if r['tier'] == 'elite')
            
            assert elite_roi >= pro_roi >= essential_roi, \
                f"{profession}: ROI no progresa correctamente (E:{essential_roi}, P:{pro_roi}, El:{elite_roi})"
    
    # Test 2: Validar cálculos matemáticos
    @pytest.mark.asyncio
    async def test_calculation_accuracy(self, calculator):
        """Verifica que los cálculos matemáticos sean correctos."""
        
        user_context = {
            'profession': 'executive',
            'age': 40,
            'budget_sensitivity': 'low'
        }
        
        roi_result = await calculator.calculate_ngx_roi(user_context, 'pro')
        
        # Verificar que los cálculos sumen correctamente
        total_annual_benefit = sum(calc.annual_benefit for calc in roi_result.calculations)
        assert abs(total_annual_benefit - roi_result.annual_value) < 0.01, \
            "La suma de beneficios no coincide con el valor anual total"
        
        # Verificar cálculo de ROI
        expected_roi = ((roi_result.annual_value - roi_result.subscription_cost) / roi_result.subscription_cost) * 100
        assert abs(expected_roi - roi_result.total_roi_percentage) < 0.01, \
            f"ROI calculado incorrectamente: esperado {expected_roi:.2f}%, obtenido {roi_result.total_roi_percentage:.2f}%"
        
        # Verificar payback period
        if roi_result.annual_value > 0:
            expected_payback = (roi_result.subscription_cost / (roi_result.annual_value / 12))
            assert abs(expected_payback - roi_result.payback_period_months) < 0.01, \
                "Período de payback calculado incorrectamente"
        
        # Verificar que cada cálculo tenga sentido
        for calc in roi_result.calculations:
            assert calc.monthly_benefit * 12 == calc.annual_benefit, \
                f"Cálculo mensual/anual inconsistente para {calc.metric_type}"
            assert 0.5 <= calc.confidence_score <= 1.0, \
                f"Score de confianza fuera de rango para {calc.metric_type}"
    
    # Test 3: Validar recomendaciones
    @pytest.mark.asyncio
    async def test_recommendation_logic(self, calculator):
        """Verifica que las recomendaciones sean lógicas."""
        
        test_scenarios = [
            # CEO con presupuesto bajo -> debería recomendar algo de valor alto ROI
            {
                'context': {'profession': 'ceo', 'age': 50, 'budget_sensitivity': 'low'},
                'expected_tiers': ['elite', 'prime_program']
            },
            # Manager joven con presupuesto ajustado -> tier más básico
            {
                'context': {'profession': 'manager', 'age': 28, 'budget_sensitivity': 'high'},
                'expected_tiers': ['essential', 'pro']
            },
            # Executive de 55 años -> debería incluir longevity
            {
                'context': {'profession': 'executive', 'age': 55, 'budget_sensitivity': 'medium'},
                'expected_tiers': ['elite', 'longevity_program']
            }
        ]
        
        for scenario in test_scenarios:
            recommendation = await calculator.get_recommended_ngx_offering(scenario['context'])
            
            # Verificar que la recomendación esté en las esperadas
            assert recommendation['recommended_offering'] in scenario['expected_tiers'], \
                f"Recomendación inesperada para {scenario['context']}: {recommendation['recommended_offering']}"
            
            # Verificar que haya reasoning
            assert len(recommendation['recommendation_reasoning']) > 0, \
                "No se proporcionó reasoning para la recomendación"
    
    # Test 4: Validar hybrid coaching ROI
    @pytest.mark.asyncio
    async def test_hybrid_coaching_roi(self, calculator):
        """Verifica cálculos específicos de hybrid coaching."""
        
        # Test PRIME program para executive
        executive_context = {
            'profession': 'ceo',
            'age': 45,
            'budget_sensitivity': 'low'
        }
        
        prime_roi = await calculator.calculate_ngx_roi(executive_context, 'prime_program')
        
        # PRIME debe tener alto ROI para executives
        assert prime_roi.total_roi_percentage >= 200, \
            f"PRIME ROI muy bajo para CEO: {prime_roi.total_roi_percentage}%"
        
        # Verificar que incluya productivity gains
        productivity_calcs = [c for c in prime_roi.calculations 
                            if c.metric_type == ROIMetric.PRODUCTIVITY_GAINS]
        assert len(productivity_calcs) > 0, "PRIME debe incluir productivity gains"
        
        # Test LONGEVITY program para profesional mayor
        senior_context = {
            'profession': 'consultant',
            'age': 55,
            'budget_sensitivity': 'medium'
        }
        
        longevity_roi = await calculator.calculate_ngx_roi(senior_context, 'longevity_program')
        
        # Verificar que incluya health cost avoidance
        health_calcs = [c for c in longevity_roi.calculations 
                       if c.metric_type == ROIMetric.HEALTH_COST_AVOIDANCE]
        assert len(health_calcs) > 0, "LONGEVITY debe incluir health cost avoidance"
    
    # Test 5: Stress test con valores extremos
    @pytest.mark.asyncio
    async def test_edge_cases(self, calculator):
        """Prueba casos extremos para asegurar robustez."""
        
        edge_cases = [
            # Profesión no reconocida
            {'profession': 'astronaut', 'age': 35, 'budget_sensitivity': 'medium'},
            # Edad extrema
            {'profession': 'ceo', 'age': 25, 'budget_sensitivity': 'high'},
            {'profession': 'consultant', 'age': 70, 'budget_sensitivity': 'low'},
            # Combinaciones inusuales
            {'profession': 'entrepreneur', 'age': 65, 'budget_sensitivity': 'high'}
        ]
        
        for context in edge_cases:
            try:
                roi_result = await calculator.calculate_ngx_roi(context, 'pro')
                
                # Verificar que aún con casos extremos, los valores sean razonables
                assert 0 < roi_result.total_roi_percentage < 10000, \
                    f"ROI fuera de rango razonable: {roi_result.total_roi_percentage}%"
                assert 0 < roi_result.payback_period_months < 60, \
                    f"Payback period no realista: {roi_result.payback_period_months} meses"
                
            except Exception as e:
                pytest.fail(f"Calculator falló con caso extremo {context}: {str(e)}")
    
    # Test 6: Consistencia en múltiples llamadas
    @pytest.mark.asyncio
    async def test_consistency(self, calculator):
        """Verifica que los cálculos sean consistentes."""
        
        user_context = {
            'profession': 'consultant',
            'age': 40,
            'budget_sensitivity': 'medium'
        }
        
        # Hacer 5 llamadas idénticas
        results = []
        for _ in range(5):
            roi_result = await calculator.calculate_ngx_roi(user_context, 'elite')
            results.append(roi_result.total_roi_percentage)
        
        # Todos los resultados deben ser idénticos
        assert len(set(results)) == 1, \
            f"Resultados inconsistentes: {results}"
    
    # Test 7: Validar insights generados
    @pytest.mark.asyncio
    async def test_insights_quality(self, calculator):
        """Verifica que los insights sean relevantes y correctos."""
        
        contexts = [
            {'profession': 'ceo', 'age': 45, 'tier': 'elite'},
            {'profession': 'manager', 'age': 30, 'tier': 'essential'},
            {'profession': 'entrepreneur', 'age': 35, 'tier': 'pro'}
        ]
        
        for ctx in contexts:
            user_context = {
                'profession': ctx['profession'],
                'age': ctx['age'],
                'budget_sensitivity': 'medium'
            }
            
            roi_result = await calculator.calculate_ngx_roi(user_context, ctx['tier'])
            
            # Verificar que haya insights
            assert len(roi_result.key_insights) >= 3, \
                f"Pocos insights para {ctx['profession']}-{ctx['tier']}"
            
            # Verificar que los insights mencionen elementos clave
            insights_text = ' '.join(roi_result.key_insights).lower()
            assert 'roi' in insights_text, "Insights deben mencionar ROI"
            assert ctx['tier'] in insights_text, f"Insights deben mencionar el tier {ctx['tier']}"
            assert 'payback' in insights_text or 'months' in insights_text, \
                "Insights deben mencionar período de recuperación"


# Función para ejecutar los tests y generar reporte
async def run_roi_validation():
    """Ejecuta todos los tests de ROI y genera reporte."""
    
    print("\n" + "="*80)
    print("🧮 VALIDACIÓN DE PRECISIÓN - NGX ROI CALCULATOR")
    print("="*80)
    
    calculator = NGXROICalculator()
    test_suite = TestROICalculatorAccuracy()
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'tests_passed': 0,
        'tests_failed': 0,
        'test_details': [],
        'sample_calculations': []
    }
    
    # Test 1: Rangos por profesión
    print("\n📊 Test 1: Validando rangos de ROI por profesión...")
    try:
        await test_suite.test_roi_ranges_by_profession(calculator)
        print("✅ Rangos de ROI validados correctamente")
        results['tests_passed'] += 1
        results['test_details'].append({
            'test': 'roi_ranges_by_profession',
            'status': 'passed',
            'message': 'Todos los ROI están en rangos realistas'
        })
    except AssertionError as e:
        print(f"❌ Error en rangos: {str(e)}")
        results['tests_failed'] += 1
        results['test_details'].append({
            'test': 'roi_ranges_by_profession',
            'status': 'failed',
            'error': str(e)
        })
    
    # Test 2: Precisión matemática
    print("\n🔢 Test 2: Validando precisión de cálculos...")
    try:
        await test_suite.test_calculation_accuracy(calculator)
        print("✅ Cálculos matemáticos precisos")
        results['tests_passed'] += 1
        results['test_details'].append({
            'test': 'calculation_accuracy',
            'status': 'passed',
            'message': 'Todos los cálculos son matemáticamente correctos'
        })
    except AssertionError as e:
        print(f"❌ Error en cálculos: {str(e)}")
        results['tests_failed'] += 1
        results['test_details'].append({
            'test': 'calculation_accuracy',
            'status': 'failed',
            'error': str(e)
        })
    
    # Test 3: Lógica de recomendaciones
    print("\n🎯 Test 3: Validando lógica de recomendaciones...")
    try:
        await test_suite.test_recommendation_logic(calculator)
        print("✅ Recomendaciones lógicas y coherentes")
        results['tests_passed'] += 1
        results['test_details'].append({
            'test': 'recommendation_logic',
            'status': 'passed',
            'message': 'Las recomendaciones siguen lógica de negocio correcta'
        })
    except AssertionError as e:
        print(f"❌ Error en recomendaciones: {str(e)}")
        results['tests_failed'] += 1
        results['test_details'].append({
            'test': 'recommendation_logic',
            'status': 'failed',
            'error': str(e)
        })
    
    # Test 4: Hybrid Coaching
    print("\n🏋️ Test 4: Validando Hybrid Coaching ROI...")
    try:
        await test_suite.test_hybrid_coaching_roi(calculator)
        print("✅ Hybrid Coaching ROI validado")
        results['tests_passed'] += 1
        results['test_details'].append({
            'test': 'hybrid_coaching_roi',
            'status': 'passed',
            'message': 'PRIME y LONGEVITY calculan ROI correctamente'
        })
    except AssertionError as e:
        print(f"❌ Error en Hybrid Coaching: {str(e)}")
        results['tests_failed'] += 1
        results['test_details'].append({
            'test': 'hybrid_coaching_roi',
            'status': 'failed',
            'error': str(e)
        })
    
    # Test 5: Casos extremos
    print("\n🔥 Test 5: Probando casos extremos...")
    try:
        await test_suite.test_edge_cases(calculator)
        print("✅ Manejo robusto de casos extremos")
        results['tests_passed'] += 1
        results['test_details'].append({
            'test': 'edge_cases',
            'status': 'passed',
            'message': 'Calculator maneja correctamente casos inusuales'
        })
    except AssertionError as e:
        print(f"❌ Error en casos extremos: {str(e)}")
        results['tests_failed'] += 1
        results['test_details'].append({
            'test': 'edge_cases',
            'status': 'failed',
            'error': str(e)
        })
    
    # Test 6: Consistencia
    print("\n🔄 Test 6: Verificando consistencia...")
    try:
        await test_suite.test_consistency(calculator)
        print("✅ Cálculos consistentes")
        results['tests_passed'] += 1
        results['test_details'].append({
            'test': 'consistency',
            'status': 'passed',
            'message': 'Resultados idénticos para entradas idénticas'
        })
    except AssertionError as e:
        print(f"❌ Error en consistencia: {str(e)}")
        results['tests_failed'] += 1
        results['test_details'].append({
            'test': 'consistency',
            'status': 'failed',
            'error': str(e)
        })
    
    # Test 7: Calidad de insights
    print("\n💡 Test 7: Evaluando calidad de insights...")
    try:
        await test_suite.test_insights_quality(calculator)
        print("✅ Insights relevantes y completos")
        results['tests_passed'] += 1
        results['test_details'].append({
            'test': 'insights_quality',
            'status': 'passed',
            'message': 'Insights proporcionan valor y contexto adecuado'
        })
    except AssertionError as e:
        print(f"❌ Error en insights: {str(e)}")
        results['tests_failed'] += 1
        results['test_details'].append({
            'test': 'insights_quality',
            'status': 'failed',
            'error': str(e)
        })
    
    # Generar ejemplos de cálculos
    print("\n📈 Generando ejemplos de cálculos...")
    sample_profiles = [
        {'profession': 'ceo', 'age': 45, 'tier': 'elite'},
        {'profession': 'manager', 'age': 35, 'tier': 'pro'},
        {'profession': 'consultant', 'age': 40, 'tier': 'essential'}
    ]
    
    for profile in sample_profiles:
        user_context = {
            'profession': profile['profession'],
            'age': profile['age'],
            'budget_sensitivity': 'medium'
        }
        
        roi_result = await calculator.calculate_ngx_roi(user_context, profile['tier'])
        
        results['sample_calculations'].append({
            'profile': profile,
            'roi_percentage': roi_result.total_roi_percentage,
            'annual_value': roi_result.annual_value,
            'payback_months': roi_result.payback_period_months,
            'top_benefit': roi_result.calculations[0].calculation_basis if roi_result.calculations else "N/A"
        })
        
        print(f"\n{profile['profession'].upper()} - {profile['tier'].upper()}:")
        print(f"  ROI: {roi_result.total_roi_percentage:.0f}%")
        print(f"  Valor anual: ${roi_result.annual_value:,.0f}")
        print(f"  Payback: {roi_result.payback_period_months:.1f} meses")
    
    # Resumen final
    print("\n" + "="*80)
    print("📊 RESUMEN DE VALIDACIÓN")
    print("="*80)
    print(f"\n✅ Tests pasados: {results['tests_passed']}")
    print(f"❌ Tests fallidos: {results['tests_failed']}")
    print(f"📈 Tasa de éxito: {results['tests_passed']/(results['tests_passed']+results['tests_failed'])*100:.1f}%")
    
    # Guardar reporte
    report_filename = f"roi_calculator_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Reporte detallado guardado en: {report_filename}")
    
    # Evaluación final
    if results['tests_failed'] == 0:
        print("\n✅ ROI CALCULATOR VALIDADO - Listo para producción")
        print("   Todos los cálculos son precisos y las recomendaciones son lógicas")
    else:
        print("\n⚠️  ROI CALCULATOR REQUIERE AJUSTES")
        print("   Revisar los tests fallidos antes de usar en producción")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_roi_validation())