#!/usr/bin/env python3
"""
Validación Rápida de Capacidades - NGX Voice Sales Agent

Prueba simplificada para verificar que las capacidades principales están funcionando.
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
from typing import Dict, List, Any

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")


class QuickCapabilityValidator:
    """Validador rápido de capacidades del agente."""
    
    def __init__(self):
        self.api_url = API_URL
        self.results = {}
    
    async def validate_basic_conversation(self) -> Dict[str, Any]:
        """
        Valida que el agente puede mantener una conversación básica.
        """
        print("\n📡 TEST 1: Conversación Básica")
        print("=" * 50)
        
        test_profile = {
            "name": "Carlos Mendez",
            "email": "carlos@techcorp.com",
            "age": 42,
            "occupation": "CEO",
            "company": "TechCorp",
            "interests": ["productivity", "leadership"],
            "pain_points": ["time management", "team performance"]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Iniciar conversación
                async with session.post(
                    f"{self.api_url}/conversations/start",
                    json={"customer_data": test_profile}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        conversation_id = data["conversation_id"]
                        print(f"✅ Conversación iniciada: {conversation_id}")
                        
                        # Enviar algunos mensajes
                        test_messages = [
                            "Hola, soy CEO de una empresa de tecnología",
                            "¿Cómo puede ayudarme NGX a mejorar mi productividad?",
                            "¿Qué incluye el programa PRIME?"
                        ]
                        
                        responses = []
                        for msg in test_messages:
                            async with session.post(
                                f"{self.api_url}/conversations/{conversation_id}/message",
                                json={"message": msg}
                            ) as msg_response:
                                if msg_response.status == 200:
                                    msg_data = await msg_response.json()
                                    response_text = msg_data.get("response", "")
                                    responses.append(response_text)
                                    print(f"\n🗣️ Usuario: {msg[:50]}...")
                                    print(f"🤖 Agente: {response_text[:100]}...")
                        
                        # Verificar calidad de respuestas
                        validation = {
                            "conversation_works": True,
                            "mentions_ngx": any("NGX" in r for r in responses),
                            "mentions_prime": any("PRIME" in r.upper() for r in responses),
                            "personalized": any("CEO" in r or "tecnología" in r for r in responses),
                            "total_responses": len(responses)
                        }
                        
                        return validation
                    else:
                        return {"conversation_works": False, "error": f"Status {response.status}"}
                        
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"conversation_works": False, "error": str(e)}
    
    async def validate_hie_mention(self) -> Dict[str, Any]:
        """
        Valida que el agente menciona los agentes HIE.
        """
        print("\n🤖 TEST 2: Mención de Agentes HIE")
        print("=" * 50)
        
        try:
            async with aiohttp.ClientSession() as session:
                # Iniciar conversación
                async with session.post(
                    f"{self.api_url}/conversations/start",
                    json={"customer_data": {"name": "Test HIE", "email": "test@hie.com", "age": 35}}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        conversation_id = data["conversation_id"]
                        
                        # Preguntar directamente sobre HIE
                        async with session.post(
                            f"{self.api_url}/conversations/{conversation_id}/message",
                            json={"message": "¿Qué es HIE y cómo funcionan los 11 agentes?"}
                        ) as msg_response:
                            if msg_response.status == 200:
                                msg_data = await msg_response.json()
                                response_text = msg_data.get("response", "")
                                
                                # Buscar menciones de agentes
                                agents = ["NEXUS", "BLAZE", "SAGE", "WAVE", "SPARK", 
                                         "NOVA", "LUNA", "STELLA", "CODE", "GUARDIAN", "NODE"]
                                
                                agents_mentioned = [agent for agent in agents if agent in response_text.upper()]
                                
                                validation = {
                                    "hie_explained": "HIE" in response_text or "sinergia" in response_text.lower(),
                                    "agents_mentioned": len(agents_mentioned),
                                    "agent_list": agents_mentioned,
                                    "impossible_to_clone": "imposible" in response_text.lower() and "clonar" in response_text.lower()
                                }
                                
                                print(f"✅ Agentes mencionados: {len(agents_mentioned)}/11")
                                if agents_mentioned:
                                    print(f"   Agentes: {', '.join(agents_mentioned)}")
                                
                                return validation
                            else:
                                return {"hie_explained": False, "error": "Message failed"}
                    else:
                        return {"hie_explained": False, "error": "Start failed"}
                        
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"hie_explained": False, "error": str(e)}
    
    async def validate_tier_detection(self) -> Dict[str, Any]:
        """
        Valida la detección de tier/arquetipo.
        """
        print("\n🎯 TEST 3: Detección de Tier")
        print("=" * 50)
        
        # Perfil de CEO que debería detectar PRIME
        ceo_profile = {
            "name": "Roberto Executive",
            "email": "roberto@fortune500.com",
            "age": 48,
            "occupation": "CEO",
            "company_size": "500+ employees",
            "interests": ["efficiency", "leadership"],
            "budget": "premium"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Iniciar conversación
                async with session.post(
                    f"{self.api_url}/conversations/start",
                    json={"customer_data": ceo_profile}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        conversation_id = data["conversation_id"]
                        
                        # Mensajes que deberían activar detección PRIME
                        messages = [
                            "Soy CEO y necesito maximizar mi productividad",
                            "Manejo un equipo de 500+ personas",
                            "¿Cuál es su programa más completo?"
                        ]
                        
                        tier_detected = False
                        archetype_detected = False
                        
                        for msg in messages:
                            async with session.post(
                                f"{self.api_url}/conversations/{conversation_id}/message",
                                json={"message": msg}
                            ) as msg_response:
                                if msg_response.status == 200:
                                    msg_data = await msg_response.json()
                                    response_text = msg_data.get("response", "")
                                    
                                    # Verificar si menciona PRIME
                                    if "PRIME" in response_text.upper():
                                        tier_detected = "PRIME"
                                    
                                    # Verificar si menciona características de optimizer
                                    if any(word in response_text.lower() for word in ["productividad", "rendimiento", "eficiencia"]):
                                        archetype_detected = "optimizer"
                        
                        validation = {
                            "tier_detection_works": bool(tier_detected),
                            "tier_detected": tier_detected,
                            "archetype_detected": archetype_detected,
                            "appropriate_for_ceo": tier_detected == "PRIME"
                        }
                        
                        print(f"🎯 Tier detectado: {tier_detected or 'Ninguno'}")
                        print(f"🧬 Arquetipo: {archetype_detected or 'No detectado'}")
                        
                        return validation
                    else:
                        return {"tier_detection_works": False, "error": "Start failed"}
                        
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"tier_detection_works": False, "error": str(e)}
    
    async def validate_empathy(self) -> Dict[str, Any]:
        """
        Valida respuesta empática.
        """
        print("\n💖 TEST 4: Empatía")
        print("=" * 50)
        
        # Perfil con necesidad de empatía
        stressed_profile = {
            "name": "Laura Stressed",
            "email": "laura@vp.com",
            "age": 42,
            "occupation": "VP Marketing",
            "emotional_state": "exhausted"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Iniciar conversación
                async with session.post(
                    f"{self.api_url}/conversations/start",
                    json={"customer_data": stressed_profile}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        conversation_id = data["conversation_id"]
                        
                        # Mensaje que requiere empatía
                        async with session.post(
                            f"{self.api_url}/conversations/{conversation_id}/message",
                            json={"message": "Estoy agotada, trabajo 80 horas a la semana y apenas veo a mi familia"}
                        ) as msg_response:
                            if msg_response.status == 200:
                                msg_data = await msg_response.json()
                                response_text = msg_data.get("response", "")
                                
                                # Buscar indicadores de empatía
                                empathy_words = ["entiendo", "comprendo", "difícil", "importante", 
                                               "familia", "equilibrio", "bienestar", "cuidar"]
                                
                                empathy_indicators = [word for word in empathy_words if word in response_text.lower()]
                                
                                validation = {
                                    "empathy_shown": len(empathy_indicators) > 0,
                                    "empathy_indicators": len(empathy_indicators),
                                    "empathy_words_found": empathy_indicators,
                                    "validates_feelings": any(word in response_text.lower() for word in ["entiendo", "comprendo", "difícil"])
                                }
                                
                                print(f"♥️ Indicadores de empatía: {len(empathy_indicators)}")
                                if empathy_indicators:
                                    print(f"   Palabras: {', '.join(empathy_indicators[:3])}...")
                                
                                return validation
                            else:
                                return {"empathy_shown": False, "error": "Message failed"}
                    else:
                        return {"empathy_shown": False, "error": "Start failed"}
                        
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"empathy_shown": False, "error": str(e)}
    
    async def validate_roi_mention(self) -> Dict[str, Any]:
        """
        Valida mención de ROI personalizado.
        """
        print("\n💰 TEST 5: ROI Personalizado")
        print("=" * 50)
        
        # Perfil de consultor con tarifa por hora
        consultant_profile = {
            "name": "Sarah Consultant",
            "email": "sarah@consulting.com",
            "age": 35,
            "occupation": "Senior Consultant",
            "hourly_rate": 150,
            "billable_hours": 40
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Iniciar conversación
                async with session.post(
                    f"{self.api_url}/conversations/start",
                    json={"customer_data": consultant_profile}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        conversation_id = data["conversation_id"]
                        
                        # Preguntar sobre ROI
                        async with session.post(
                            f"{self.api_url}/conversations/{conversation_id}/message",
                            json={"message": "Soy consultora y cobro $150/hora. ¿Cuál sería mi ROI con NGX?"}
                        ) as msg_response:
                            if msg_response.status == 200:
                                msg_data = await msg_response.json()
                                response_text = msg_data.get("response", "")
                                
                                # Buscar menciones de ROI
                                roi_indicators = {
                                    "mentions_roi": "ROI" in response_text.upper() or "retorno" in response_text.lower(),
                                    "mentions_hourly": "hora" in response_text.lower() or "hourly" in response_text.lower(),
                                    "mentions_numbers": any(char.isdigit() for char in response_text),
                                    "mentions_consultant": "consult" in response_text.lower()
                                }
                                
                                validation = {
                                    "roi_mentioned": roi_indicators["mentions_roi"],
                                    "personalized_calculation": roi_indicators["mentions_hourly"] and roi_indicators["mentions_numbers"],
                                    "profession_specific": roi_indicators["mentions_consultant"],
                                    "roi_indicators": sum(roi_indicators.values())
                                }
                                
                                print(f"💵 Indicadores ROI: {validation['roi_indicators']}/4")
                                
                                return validation
                            else:
                                return {"roi_mentioned": False, "error": "Message failed"}
                    else:
                        return {"roi_mentioned": False, "error": "Start failed"}
                        
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"roi_mentioned": False, "error": str(e)}
    
    async def run_all_validations(self) -> Dict[str, Any]:
        """
        Ejecuta todas las validaciones.
        """
        print("\n🚀 VALIDACIÓN RÁPIDA DE CAPACIDADES - NGX VOICE SALES AGENT")
        print("=" * 70)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"API URL: {self.api_url}")
        
        # Ejecutar validaciones
        results = {
            "basic_conversation": await self.validate_basic_conversation(),
            "hie_mention": await self.validate_hie_mention(),
            "tier_detection": await self.validate_tier_detection(),
            "empathy": await self.validate_empathy(),
            "roi_personalization": await self.validate_roi_mention()
        }
        
        # Calcular resumen
        summary = {
            "timestamp": datetime.now().isoformat(),
            "api_url": self.api_url,
            "validations": results,
            "capabilities_working": {
                "basic_conversation": results["basic_conversation"].get("conversation_works", False),
                "hie_integration": results["hie_mention"].get("hie_explained", False),
                "tier_detection": results["tier_detection"].get("tier_detection_works", False),
                "empathy": results["empathy"].get("empathy_shown", False),
                "roi_personalization": results["roi_personalization"].get("roi_mentioned", False)
            }
        }
        
        summary["total_capabilities"] = len(summary["capabilities_working"])
        summary["working_capabilities"] = sum(summary["capabilities_working"].values())
        summary["success_rate"] = (summary["working_capabilities"] / summary["total_capabilities"]) * 100
        
        # Mostrar resumen
        print("\n" + "="*70)
        print("📊 RESUMEN DE VALIDACIÓN")
        print("="*70)
        
        for capability, working in summary["capabilities_working"].items():
            status = "✅" if working else "❌"
            print(f"{status} {capability.replace('_', ' ').title()}")
        
        print(f"\nCapacidades funcionando: {summary['working_capabilities']}/{summary['total_capabilities']}")
        print(f"Tasa de éxito: {summary['success_rate']:.1f}%")
        
        # Guardar resultados
        results_file = f"tests/capabilities/results/quick_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n💾 Resultados guardados en: {results_file}")
        
        if summary['success_rate'] >= 80:
            print("\n✅ VALIDACIÓN EXITOSA - El agente está funcionando correctamente")
        else:
            print("\n⚠️  VALIDACIÓN PARCIAL - Algunas capacidades requieren revisión")
        
        return summary


async def main():
    """Función principal."""
    validator = QuickCapabilityValidator()
    summary = await validator.run_all_validations()
    
    # Retornar código de salida basado en éxito
    return 0 if summary['success_rate'] >= 80 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)