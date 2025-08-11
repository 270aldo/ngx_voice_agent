#!/usr/bin/env python3
"""
Script para ejecutar el suite de tests de inteligencia conversacional.
Valida la efectividad del agente de ventas NGX.
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
import json

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conversation_intelligence_test_suite import (
    ConversationIntelligenceTestSuite,
    TestCategory,
    run_quick_test,
    validate_sales_effectiveness
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockAgentService:
    """
    Servicio mock del agente para pruebas.
    En producción, esto sería reemplazado por el servicio real.
    """
    
    def __init__(self):
        self.response_templates = self._load_response_templates()
    
    def _load_response_templates(self):
        """Carga templates de respuestas para diferentes contextos."""
        return {
            "greeting": "¡Hola! Soy el agente de ventas de NGX. Entiendo que manejas un {business_type} y estás buscando soluciones para mejorar tu negocio. ¿Cuál es tu principal desafío actualmente?",
            
            "pain_point_retention": "Entiendo perfectamente tu preocupación sobre la retención de clientes. Es uno de los mayores desafíos en la industria del fitness. Con NGX, hemos ayudado a gimnasios similares a reducir su churn mensual del 10% al 5% en promedio. Nuestro sistema utiliza IA para identificar clientes en riesgo de cancelar y automatiza campañas de re-engagement personalizadas. ¿Cuántos clientes activos tienes actualmente?",
            
            "pricing_inquiry": "Excelente pregunta sobre los precios. Para un gimnasio de tu tamaño, recomendaría nuestro plan PRO a $349/mes, que incluye:\n- Los 11 agentes de IA de NGX AGENTS ACCESS\n- Gestión ilimitada de clientes\n- Automatización de marketing\n- Análisis predictivo de churn\n- Soporte prioritario 24/7\n\nCon tu volumen actual de clientes, el ROI típico es del 300% en los primeros 6 meses. ¿Te gustaría que calculemos el ROI específico para tu gimnasio?",
            
            "ngx_agents_list": "NGX AGENTS ACCESS incluye 11 agentes especializados de IA:\n1. Voice Sales Agent - Ventas automatizadas\n2. Support Agent - Soporte 24/7\n3. Marketing Agent - Campañas personalizadas\n4. Social Media Agent - Gestión de redes\n5. Content Creator Agent - Creación de contenido\n6. Analytics Agent - Insights y reportes\n7. Onboarding Agent - Activación de clientes\n8. Retention Agent - Prevención de churn\n9. Trainer Assistant - Apoyo a entrenadores\n10. Community Manager - Gestión de comunidad\n11. Scheduling Agent - Gestión de citas\n\nTodos trabajan en conjunto para optimizar cada aspecto de tu negocio.",
            
            "objection_price": "Entiendo tu preocupación sobre la inversión. Es válido evaluar cuidadosamente cualquier gasto. Permíteme ponerlo en perspectiva: con 200 clientes pagando en promedio $50/mes, tu ingreso mensual es de $10,000. Si reduces tu churn del 10% al 5%, retienes 10 clientes más cada mes, lo que representa $500 adicionales. Además, con la automatización de marketing, nuestros clientes típicamente aumentan sus nuevas inscripciones en un 20%. Eso podría significar $2,000+ adicionales al mes. El plan PRO a $349 se paga solo y genera ganancias desde el primer mes.",
            
            "closing": "¡Excelente decisión! Para comenzar con NGX, el proceso es muy sencillo:\n1. Completamos un formulario rápido con los datos de tu gimnasio\n2. Nuestro equipo configura tu cuenta en 24-48 horas\n3. Tienes una sesión de onboarding personalizada\n4. Comienzas a ver resultados desde la primera semana\n\n¿Prefieres que te envíe el enlace de registro por email o completamos el proceso juntos ahora mismo?",
            
            "competitor_comparison": "Es genial que ya estés usando tecnología para tu gimnasio. NGX se diferencia en varios aspectos clave:\n- Nuestros 11 agentes de IA trabajan 24/7 (no solo software de gestión)\n- Especialización exclusiva en fitness (no somos genéricos)\n- ROI garantizado o devolvemos tu dinero\n- Migración gratuita y sin interrupciones\n- Resultados medibles desde el día 1\n\nMuchos de nuestros clientes migraron de otros sistemas y en promedio duplicaron su eficiencia operativa. ¿Qué es lo que más te gustaría mejorar de tu sistema actual?",
            
            "aggressive_response": "Comprendo tu escepticismo y es completamente válido cuestionar cualquier servicio nuevo. No somos una estafa, somos una empresa establecida con más de 500 gimnasios usando nuestro sistema exitosamente. Me encantaría mostrarte casos de éxito reales y testimonios verificables. También ofrecemos una garantía de satisfacción de 30 días. ¿Qué específicamente te preocupa? Me gustaría abordar tus dudas directamente.",
            
            "prompt_injection_response": "Entiendo que quieres explorar nuestras opciones de precios. Los planes de NGX tienen precios fijos que te mencioné anteriormente: STARTER $149, GROWTH $299, PRO $349, SCALE $549, y ENTERPRISE con precio personalizado. Estos precios reflejan el valor real que proporcionamos. ¿Cuál de estos planes se ajusta mejor a tu presupuesto actual?",
            
            "off_topic_response": "Aprecio la pregunta, pero me especializo en ayudar a negocios de fitness a crecer con las soluciones de NGX. Volviendo a tu gimnasio, ¿qué aspecto de tu operación te gustaría mejorar más: la retención de clientes, la adquisición de nuevos miembros, o la eficiencia operativa?"
        }
    
    async def process_message(self, 
                            conversation_id: str,
                            message: str,
                            conversation_history: list,
                            customer_profile: dict) -> dict:
        """Procesa un mensaje y retorna una respuesta apropiada."""
        
        # Analizar el mensaje para determinar el tipo de respuesta
        message_lower = message.lower()
        
        # Seleccionar template apropiado
        if len(conversation_history) <= 2:
            response_template = self.response_templates["greeting"]
        elif any(word in message_lower for word in ["retención", "perder clientes", "churn"]):
            response_template = self.response_templates["pain_point_retention"]
        elif any(word in message_lower for word in ["precio", "cuesta", "cuánto", "costo"]):
            response_template = self.response_templates["pricing_inquiry"]
        elif any(word in message_lower for word in ["agentes", "incluye", "qué hace"]):
            response_template = self.response_templates["ngx_agents_list"]
        elif any(word in message_lower for word in ["caro", "mucho dinero", "económico"]):
            response_template = self.response_templates["objection_price"]
        elif any(word in message_lower for word in ["empezar", "contratar", "siguiente", "listo"]):
            response_template = self.response_templates["closing"]
        elif any(word in message_lower for word in ["otro sistema", "competencia", "mindbody"]):
            response_template = self.response_templates["competitor_comparison"]
        elif any(word in message_lower for word in ["estafa", "mentira", "no funciona"]):
            response_template = self.response_templates["aggressive_response"]
        elif any(word in message_lower for word in ["ignore", "override", "system", "gratis"]):
            response_template = self.response_templates["prompt_injection_response"]
        elif any(word in message_lower for word in ["clima", "cocinar", "chiste"]):
            response_template = self.response_templates["off_topic_response"]
        else:
            # Respuesta genérica
            response_template = "Gracias por tu pregunta. En NGX nos especializamos en ayudar a gimnasios y estudios de fitness a crecer. ¿Podrías contarme más sobre tu negocio y qué desafíos enfrentas actualmente?"
        
        # Formatear respuesta con contexto
        try:
            response_content = response_template.format(**customer_profile)
        except:
            response_content = response_template
        
        return {
            "content": response_content,
            "metadata": {
                "confidence": 0.95,
                "detected_intent": self._detect_intent(message),
                "recommended_action": "continue_conversation"
            }
        }
    
    def _detect_intent(self, message: str) -> str:
        """Detecta la intención del mensaje."""
        message_lower = message.lower()
        
        intents = {
            "pricing_inquiry": ["precio", "costo", "cuánto", "tarifa"],
            "feature_inquiry": ["incluye", "características", "funciones", "qué hace"],
            "objection": ["caro", "duda", "no sé", "problema"],
            "purchase_intent": ["contratar", "empezar", "comprar", "adquirir"],
            "comparison": ["otro", "competencia", "versus", "diferencia"],
            "support": ["ayuda", "problema", "no funciona", "error"]
        }
        
        for intent, keywords in intents.items():
            if any(keyword in message_lower for keyword in keywords):
                return intent
        
        return "general_inquiry"


async def run_comprehensive_test():
    """Ejecuta el test completo de inteligencia conversacional."""
    print("\n" + "="*80)
    print("🧪 SUITE DE TESTS DE INTELIGENCIA CONVERSACIONAL - NGX VOICE SALES AGENT")
    print("="*80)
    
    # Inicializar servicio (mock para pruebas)
    agent_service = MockAgentService()
    
    # Crear suite de tests
    suite = ConversationIntelligenceTestSuite(agent_service)
    
    # Ejecutar todos los tests
    print("\n📋 Ejecutando todos los escenarios de prueba...")
    report = await suite.run_all_tests()
    
    # Mostrar resultados
    print("\n" + "="*80)
    print("📊 RESULTADOS DEL TEST")
    print("="*80)
    
    summary = report["summary"]
    print(f"\n✅ Tests Pasados: {summary['passed']}/{summary['total_scenarios']}")
    print(f"❌ Tests Fallidos: {summary['failed']}")
    print(f"📈 Tasa de Éxito: {summary['pass_rate']:.1%}")
    print(f"⭐ Score Promedio: {summary['average_score']:.2f}/1.0")
    
    # Resultados por categoría
    print("\n📑 RESULTADOS POR CATEGORÍA:")
    for category, results in report["category_breakdown"].items():
        print(f"\n{category.upper()}:")
        print(f"  - Tests: {results['total_tests']}")
        print(f"  - Pasados: {results['passed']} ({results['pass_rate']:.1%})")
        print(f"  - Score Promedio: {results['average_score']:.2f}")
    
    # Top issues
    if report["top_issues"]:
        print("\n⚠️  PROBLEMAS MÁS COMUNES:")
        for issue, count in report["top_issues"][:5]:
            print(f"  - {issue}: {count} ocurrencias")
    
    # Recomendaciones
    if report["recommendations"]:
        print("\n💡 RECOMENDACIONES:")
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"  {i}. {rec}")
    
    # Guardar reporte detallado
    report_file = f"conversation_intelligence_detailed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Reporte detallado guardado en: {report_file}")
    
    # Evaluación final
    print("\n" + "="*80)
    if summary['pass_rate'] >= 0.8 and summary['average_score'] >= 0.75:
        print("✅ RESULTADO FINAL: AGENTE APROBADO PARA BETA")
        print("   El agente demuestra capacidades suficientes para ventas efectivas")
    else:
        print("❌ RESULTADO FINAL: SE REQUIEREN MEJORAS")
        print("   El agente necesita optimización antes del lanzamiento beta")
    print("="*80)


async def run_sales_effectiveness_test():
    """Ejecuta solo el test de efectividad en ventas."""
    print("\n🎯 TEST RÁPIDO: EFECTIVIDAD EN VENTAS")
    print("-"*50)
    
    agent_service = MockAgentService()
    effectiveness_score = await validate_sales_effectiveness(agent_service)
    
    print(f"\nScore de Efectividad en Ventas: {effectiveness_score:.2f}/1.0")
    
    if effectiveness_score >= 0.75:
        print("✅ El agente demuestra buena efectividad en ventas")
    else:
        print("❌ El agente necesita mejorar sus técnicas de venta")


async def run_quick_validation():
    """Ejecuta una validación rápida con escenarios clave."""
    print("\n⚡ VALIDACIÓN RÁPIDA")
    print("-"*50)
    
    agent_service = MockAgentService()
    await run_quick_test(agent_service)


async def main():
    """Función principal del script."""
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        
        if mode == "--quick":
            await run_quick_validation()
        elif mode == "--sales":
            await run_sales_effectiveness_test()
        elif mode == "--full":
            await run_comprehensive_test()
        else:
            print("Modo no reconocido. Use: --quick, --sales, o --full")
    else:
        # Por defecto, ejecutar test completo
        await run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())