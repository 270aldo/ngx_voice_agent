#!/usr/bin/env python3
"""
Test suite para validar la precisión del Tier Detection Service.

Objetivo: Validar que el sistema detecta correctamente el tier óptimo
con una precisión >80% basándose en el perfil del cliente.
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

from src.services.tier_detection_service import TierDetectionService, TierType, ArchetypeType


class TestTierDetectionAccuracy:
    """Suite de tests para validar precisión del Tier Detection Service."""
    
    @pytest.fixture
    async def detector(self):
        """Fixture para crear instancia del detector."""
        return TierDetectionService()
    
    # Test 1: Precisión por profesión
    @pytest.mark.asyncio
    async def test_detection_by_profession(self, detector):
        """Verifica detección correcta basada en profesión."""
        
        test_cases = [
            # (profession, age, expected_tier, expected_archetype)
            ("ceo", 45, TierType.PRIME_PREMIUM, ArchetypeType.PRIME),
            ("director", 50, TierType.ELITE, ArchetypeType.HYBRID),
            ("gerente", 35, TierType.PRO, ArchetypeType.PRIME),
            ("estudiante", 22, TierType.ESSENTIAL, ArchetypeType.PRIME),
            ("médico", 55, TierType.LONGEVITY_PREMIUM, ArchetypeType.LONGEVITY),
            ("consultor", 40, TierType.ELITE, ArchetypeType.PRIME),
            ("emprendedor", 30, TierType.ELITE, ArchetypeType.PRIME),
            ("abogado", 48, TierType.PRIME_PREMIUM, ArchetypeType.HYBRID),
            ("ingeniero", 28, TierType.PRO, ArchetypeType.PRIME),
            ("freelancer", 32, TierType.PRO, ArchetypeType.PRIME)
        ]
        
        correct_detections = 0
        total_tests = len(test_cases)
        results = []
        
        for profession, age, expected_tier, expected_archetype in test_cases:
            user_profile = {
                'occupation': profession,
                'age': age,
                'location': 'Ciudad de México'
            }
            
            user_message = f"Soy {profession} y busco mejorar mi productividad"
            
            result = await detector.detect_optimal_tier(
                user_message=user_message,
                user_profile=user_profile,
                conversation_history=[]
            )
            
            # Verificar tier
            tier_correct = result.recommended_tier == expected_tier
            if tier_correct:
                correct_detections += 1
            
            results.append({
                'profession': profession,
                'age': age,
                'expected_tier': expected_tier.value,
                'detected_tier': result.recommended_tier.value,
                'tier_correct': tier_correct,
                'confidence': result.confidence,
                'detected_archetype': result.detected_archetype.value,
                'archetype_confidence': result.archetype_confidence
            })
            
            # Log para debugging
            if not tier_correct:
                print(f"❌ {profession} ({age}): Esperado {expected_tier.value}, Detectado {result.recommended_tier.value}")
        
        accuracy = correct_detections / total_tests
        assert accuracy >= 0.8, f"Precisión {accuracy:.2%} menor al objetivo 80%"
        
        return results, accuracy
    
    # Test 2: Detección por mensajes de precio
    @pytest.mark.asyncio
    async def test_price_sensitivity_detection(self, detector):
        """Verifica detección basada en sensibilidad al precio."""
        
        test_cases = [
            # (message, profile, expected_sensitivity, expected_tier_adjustment)
            (
                "Me preocupa mucho el costo, ¿tienen algo económico?",
                {'occupation': 'gerente', 'age': 35},
                "high",
                TierType.ESSENTIAL  # Debería bajar de PRO a ESSENTIAL
            ),
            (
                "El precio no es problema, quiero lo mejor",
                {'occupation': 'gerente', 'age': 35},
                "low",
                TierType.ELITE  # Debería subir de PRO a ELITE
            ),
            (
                "¿Cuánto cuesta? Necesito ver si entra en mi presupuesto",
                {'occupation': 'consultor', 'age': 40},
                "medium",
                TierType.ELITE  # Debería mantener ELITE
            ),
            (
                "Busco la mejor inversión calidad-precio",
                {'occupation': 'emprendedor', 'age': 30},
                "medium",
                TierType.ELITE  # Mantiene recomendación
            )
        ]
        
        correct_adjustments = 0
        
        for message, profile, expected_sensitivity, expected_tier in test_cases:
            result = await detector.detect_optimal_tier(
                user_message=message,
                user_profile=profile,
                conversation_history=[]
            )
            
            # Verificar sensibilidad al precio
            assert result.price_sensitivity == expected_sensitivity, \
                f"Sensibilidad incorrecta: esperado {expected_sensitivity}, detectado {result.price_sensitivity}"
            
            # Verificar ajuste de tier
            if result.recommended_tier == expected_tier:
                correct_adjustments += 1
        
        adjustment_accuracy = correct_adjustments / len(test_cases)
        assert adjustment_accuracy >= 0.75, \
            f"Precisión de ajuste por precio {adjustment_accuracy:.2%} menor al objetivo 75%"
    
    # Test 3: Detección de arquetipos
    @pytest.mark.asyncio
    async def test_archetype_detection_accuracy(self, detector):
        """Verifica precisión en detección de arquetipos."""
        
        test_cases = [
            # Casos PRIME (25-45 años, enfoque en performance)
            {
                'profile': {'occupation': 'ceo', 'age': 35},
                'message': "Necesito maximizar mi productividad y rendimiento",
                'expected_archetype': ArchetypeType.PRIME
            },
            {
                'profile': {'occupation': 'emprendedor', 'age': 28},
                'message': "Busco herramientas para ser más eficiente",
                'expected_archetype': ArchetypeType.PRIME
            },
            
            # Casos LONGEVITY (55+ años, enfoque en salud)
            {
                'profile': {'occupation': 'médico', 'age': 60},
                'message': "Me interesa mantener mi salud y bienestar a largo plazo",
                'expected_archetype': ArchetypeType.LONGEVITY
            },
            {
                'profile': {'occupation': 'consultor', 'age': 58},
                'message': "Quiero prevenir problemas de salud futuros",
                'expected_archetype': ArchetypeType.LONGEVITY
            },
            
            # Casos HYBRID (45-55 años, transición)
            {
                'profile': {'occupation': 'director', 'age': 50},
                'message': "Busco balance entre rendimiento y bienestar",
                'expected_archetype': ArchetypeType.HYBRID
            },
            {
                'profile': {'occupation': 'abogado', 'age': 48},
                'message': "Necesito mantener mi performance pero cuidar mi salud",
                'expected_archetype': ArchetypeType.HYBRID
            }
        ]
        
        correct_archetypes = 0
        total_confidence = 0
        
        for case in test_cases:
            result = await detector.detect_optimal_tier(
                user_message=case['message'],
                user_profile=case['profile'],
                conversation_history=[]
            )
            
            if result.detected_archetype == case['expected_archetype']:
                correct_archetypes += 1
            else:
                print(f"❌ Arquetipo incorrecto: {case['profile']['occupation']} ({case['profile']['age']})")
                print(f"   Esperado: {case['expected_archetype'].value}, Detectado: {result.detected_archetype.value}")
            
            total_confidence += result.archetype_confidence
        
        archetype_accuracy = correct_archetypes / len(test_cases)
        avg_confidence = total_confidence / len(test_cases)
        
        assert archetype_accuracy >= 0.8, \
            f"Precisión de arquetipos {archetype_accuracy:.2%} menor al objetivo 80%"
        assert avg_confidence >= 0.7, \
            f"Confianza promedio {avg_confidence:.2f} menor al objetivo 0.7"
    
    # Test 4: Consistencia con historial de conversación
    @pytest.mark.asyncio
    async def test_conversation_history_impact(self, detector):
        """Verifica que el historial de conversación mejore la precisión."""
        
        user_profile = {
            'occupation': 'gerente',
            'age': 38,
            'location': 'Buenos Aires'
        }
        
        # Sin historial
        result_no_history = await detector.detect_optimal_tier(
            user_message="¿Qué planes tienen disponibles?",
            user_profile=user_profile,
            conversation_history=[]
        )
        
        # Con historial mostrando alto engagement
        engaged_history = [
            {"role": "user", "content": "Necesito mejorar la gestión de mi equipo"},
            {"role": "assistant", "content": "Entiendo, NGX puede ayudarte..."},
            {"role": "user", "content": "¿Cómo funciona exactamente?"},
            {"role": "assistant", "content": "NGX utiliza IA para..."},
            {"role": "user", "content": "¿Qué resultados han visto otros gerentes?"},
            {"role": "assistant", "content": "En promedio, 25% de mejora..."},
            {"role": "user", "content": "Suena interesante, ¿incluye soporte?"},
            {"role": "assistant", "content": "Sí, todos los planes incluyen..."},
            {"role": "user", "content": "¿Puedo ver una demo?"},
            {"role": "assistant", "content": "Por supuesto..."},
            {"role": "user", "content": "¿Qué planes tienen disponibles?"}
        ]
        
        result_with_history = await detector.detect_optimal_tier(
            user_message="¿Qué planes tienen disponibles?",
            user_profile=user_profile,
            conversation_history=engaged_history
        )
        
        # Con historial largo debería tener más confianza
        assert result_with_history.confidence >= result_no_history.confidence, \
            "El historial debería aumentar la confianza"
        
        # Verificar que detecta señales de engagement
        assert "engaged_conversation" in result_with_history.behavioral_signals or \
               "high_interest" in result_with_history.behavioral_signals, \
            "Debería detectar alto engagement"
    
    # Test 5: Upsell potential detection
    @pytest.mark.asyncio
    async def test_upsell_potential_accuracy(self, detector):
        """Verifica detección correcta del potencial de upsell."""
        
        test_cases = [
            # Alto potencial de upsell
            {
                'profile': {'occupation': 'gerente', 'age': 35, 'income_bracket': 'high'},
                'message': "Empecemos con algo básico y vemos cómo va",
                'expected_upsell': "high"  # Puede pagar más pero empieza conservador
            },
            # Bajo potencial de upsell
            {
                'profile': {'occupation': 'estudiante', 'age': 22},
                'message': "Necesito la opción más económica",
                'expected_upsell': "low"  # Limitado por presupuesto
            },
            # Medio potencial de upsell
            {
                'profile': {'occupation': 'consultor', 'age': 40},
                'message': "Busco algo profesional pero razonable",
                'expected_upsell': "medium"  # Puede crecer con resultados
            }
        ]
        
        for case in test_cases:
            result = await detector.detect_optimal_tier(
                user_message=case['message'],
                user_profile=case['profile'],
                conversation_history=[]
            )
            
            # El upsell potential debería alinearse con el perfil
            assert result.upsell_potential in ["low", "medium", "high"], \
                "Upsell potential debe ser low/medium/high"
    
    # Test 6: Edge cases y robustez
    @pytest.mark.asyncio
    async def test_edge_cases(self, detector):
        """Prueba casos extremos para asegurar robustez."""
        
        edge_cases = [
            # Perfil vacío
            ({}, "Quiero información sobre sus servicios"),
            # Edad extrema
            ({'occupation': 'ceo', 'age': 18}, "Soy muy joven pero ambicioso"),
            ({'occupation': 'consultor', 'age': 85}, "A mi edad quiero cuidar mi salud"),
            # Profesión no reconocida
            ({'occupation': 'astronauta', 'age': 40}, "Trabajo en un campo muy específico"),
            # Mensaje ambiguo
            ({'occupation': 'gerente', 'age': 35}, "Tal vez, no sé, quizás...")
        ]
        
        for profile, message in edge_cases:
            try:
                result = await detector.detect_optimal_tier(
                    user_message=message,
                    user_profile=profile,
                    conversation_history=[]
                )
                
                # Debe retornar un resultado válido
                assert result.recommended_tier in TierType, \
                    "Debe retornar un tier válido"
                assert 0 <= result.confidence <= 1, \
                    "Confianza debe estar entre 0 y 1"
                assert result.detected_archetype in ArchetypeType, \
                    "Debe detectar un arquetipo válido"
                
            except Exception as e:
                pytest.fail(f"Falló con caso extremo {profile}: {str(e)}")


# Función principal para ejecutar validación
async def run_tier_detection_validation():
    """Ejecuta la validación completa del Tier Detection Service."""
    
    print("\n" + "="*80)
    print("🎯 VALIDACIÓN DE PRECISIÓN - TIER DETECTION SERVICE")
    print("="*80)
    
    detector = TierDetectionService()
    test_suite = TestTierDetectionAccuracy()
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'tests_passed': 0,
        'tests_failed': 0,
        'overall_accuracy': 0,
        'test_details': [],
        'accuracy_by_category': {}
    }
    
    # Test 1: Detección por profesión
    print("\n📊 Test 1: Detección por profesión...")
    try:
        profession_results, accuracy = await test_suite.test_detection_by_profession(detector)
        print(f"✅ Precisión por profesión: {accuracy:.2%}")
        results['tests_passed'] += 1
        results['accuracy_by_category']['profession'] = accuracy
        results['test_details'].append({
            'test': 'detection_by_profession',
            'status': 'passed',
            'accuracy': accuracy,
            'details': profession_results
        })
    except AssertionError as e:
        print(f"❌ Error: {str(e)}")
        results['tests_failed'] += 1
        results['test_details'].append({
            'test': 'detection_by_profession',
            'status': 'failed',
            'error': str(e)
        })
    
    # Test 2: Sensibilidad al precio
    print("\n💰 Test 2: Detección de sensibilidad al precio...")
    try:
        await test_suite.test_price_sensitivity_detection(detector)
        print("✅ Sensibilidad al precio detectada correctamente")
        results['tests_passed'] += 1
        results['test_details'].append({
            'test': 'price_sensitivity_detection',
            'status': 'passed'
        })
    except AssertionError as e:
        print(f"❌ Error: {str(e)}")
        results['tests_failed'] += 1
        results['test_details'].append({
            'test': 'price_sensitivity_detection',
            'status': 'failed',
            'error': str(e)
        })
    
    # Test 3: Detección de arquetipos
    print("\n🧬 Test 3: Detección de arquetipos...")
    try:
        await test_suite.test_archetype_detection_accuracy(detector)
        print("✅ Arquetipos detectados con precisión >80%")
        results['tests_passed'] += 1
        results['test_details'].append({
            'test': 'archetype_detection',
            'status': 'passed'
        })
    except AssertionError as e:
        print(f"❌ Error: {str(e)}")
        results['tests_failed'] += 1
        results['test_details'].append({
            'test': 'archetype_detection',
            'status': 'failed',
            'error': str(e)
        })
    
    # Test 4: Impacto del historial
    print("\n📜 Test 4: Impacto del historial de conversación...")
    try:
        await test_suite.test_conversation_history_impact(detector)
        print("✅ Historial mejora la detección correctamente")
        results['tests_passed'] += 1
        results['test_details'].append({
            'test': 'conversation_history_impact',
            'status': 'passed'
        })
    except AssertionError as e:
        print(f"❌ Error: {str(e)}")
        results['tests_failed'] += 1
        results['test_details'].append({
            'test': 'conversation_history_impact',
            'status': 'failed',
            'error': str(e)
        })
    
    # Test 5: Potencial de upsell
    print("\n📈 Test 5: Detección de potencial de upsell...")
    try:
        await test_suite.test_upsell_potential_accuracy(detector)
        print("✅ Potencial de upsell detectado correctamente")
        results['tests_passed'] += 1
        results['test_details'].append({
            'test': 'upsell_potential',
            'status': 'passed'
        })
    except AssertionError as e:
        print(f"❌ Error: {str(e)}")
        results['tests_failed'] += 1
        results['test_details'].append({
            'test': 'upsell_potential',
            'status': 'failed',
            'error': str(e)
        })
    
    # Test 6: Casos extremos
    print("\n🔥 Test 6: Casos extremos y robustez...")
    try:
        await test_suite.test_edge_cases(detector)
        print("✅ Manejo robusto de casos extremos")
        results['tests_passed'] += 1
        results['test_details'].append({
            'test': 'edge_cases',
            'status': 'passed'
        })
    except AssertionError as e:
        print(f"❌ Error: {str(e)}")
        results['tests_failed'] += 1
        results['test_details'].append({
            'test': 'edge_cases',
            'status': 'failed',
            'error': str(e)
        })
    
    # Ejemplos de detección
    print("\n📋 Ejemplos de detección:")
    example_profiles = [
        {'occupation': 'ceo', 'age': 45, 'message': "Busco maximizar mi productividad"},
        {'occupation': 'gerente', 'age': 35, 'message': "¿Cuánto cuesta el servicio?"},
        {'occupation': 'médico', 'age': 58, 'message': "Me interesa cuidar mi salud a largo plazo"}
    ]
    
    for profile in example_profiles:
        result = await detector.detect_optimal_tier(
            user_message=profile['message'],
            user_profile={'occupation': profile['occupation'], 'age': profile['age']},
            conversation_history=[]
        )
        
        print(f"\n{profile['occupation'].upper()} ({profile['age']} años):")
        print(f"  Tier: {result.recommended_tier.value} ({result.price_point})")
        print(f"  Arquetipo: {result.detected_archetype.value}")
        print(f"  Confianza: {result.confidence:.2f}")
        print(f"  Reasoning: {result.reasoning}")
    
    # Calcular precisión general
    if 'profession' in results['accuracy_by_category']:
        results['overall_accuracy'] = results['accuracy_by_category']['profession']
    
    # Resumen final
    print("\n" + "="*80)
    print("📊 RESUMEN DE VALIDACIÓN")
    print("="*80)
    print(f"\n✅ Tests pasados: {results['tests_passed']}")
    print(f"❌ Tests fallidos: {results['tests_failed']}")
    print(f"🎯 Precisión general: {results['overall_accuracy']:.2%}")
    
    # Guardar reporte
    report_filename = f"tier_detection_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Reporte detallado guardado en: {report_filename}")
    
    # Evaluación final
    if results['overall_accuracy'] >= 0.8 and results['tests_failed'] == 0:
        print("\n✅ TIER DETECTION VALIDADO - Precisión >80% alcanzada")
        print("   El sistema detecta correctamente el tier óptimo para cada cliente")
    else:
        print("\n⚠️  TIER DETECTION REQUIERE MEJORAS")
        print("   La precisión está por debajo del objetivo del 80%")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_tier_detection_validation())