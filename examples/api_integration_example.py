#!/usr/bin/env python3
"""
NGX Voice Sales Agent API Integration Example

This example demonstrates how to integrate with the NGX Voice Sales Agent API
to create a complete sales conversation flow.
"""

import aiohttp
import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime


class NGXSalesClient:
    """Client for interacting with NGX Voice Sales Agent API."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = None
        self.token = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers
    
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate and get JWT token."""
        async with self.session.post(
            f'{self.base_url}/auth/login',
            json={'username': username, 'password': password},
            headers=self._get_headers()
        ) as resp:
            data = await resp.json()
            if resp.status == 200:
                self.token = data['access_token']
                print(f"✅ Logged in successfully")
                return data
            else:
                raise Exception(f"Login failed: {data}")
    
    async def start_conversation(self, customer_info: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new sales conversation."""
        async with self.session.post(
            f'{self.base_url}/conversation/start',
            json={'customer_info': customer_info},
            headers=self._get_headers()
        ) as resp:
            data = await resp.json()
            if resp.status == 200:
                print(f"✅ Conversation started: {data['conversation_id']}")
                return data
            else:
                raise Exception(f"Failed to start conversation: {data}")
    
    async def send_message(self, conversation_id: str, message: str) -> Dict[str, Any]:
        """Send a message in the conversation."""
        async with self.session.post(
            f'{self.base_url}/conversation/{conversation_id}/message',
            json={'message': message},
            headers=self._get_headers()
        ) as resp:
            data = await resp.json()
            if resp.status == 200:
                return data
            else:
                raise Exception(f"Failed to send message: {data}")
    
    async def get_predictions(self, conversation_id: str, messages: list) -> Dict[str, Any]:
        """Get ML predictions for the conversation."""
        predictions = {}
        
        # Get objection predictions
        async with self.session.post(
            f'{self.base_url}/predictive/objection/predict',
            json={'conversation_id': conversation_id, 'messages': messages},
            headers=self._get_headers()
        ) as resp:
            if resp.status == 200:
                predictions['objections'] = await resp.json()
        
        # Get needs predictions
        async with self.session.post(
            f'{self.base_url}/predictive/needs/predict',
            json={'conversation_id': conversation_id, 'messages': messages},
            headers=self._get_headers()
        ) as resp:
            if resp.status == 200:
                predictions['needs'] = await resp.json()
        
        # Get conversion prediction
        async with self.session.post(
            f'{self.base_url}/predictive/conversion/predict',
            json={'conversation_id': conversation_id, 'messages': messages},
            headers=self._get_headers()
        ) as resp:
            if resp.status == 200:
                predictions['conversion'] = await resp.json()
        
        return predictions
    
    async def get_analytics(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation analytics."""
        async with self.session.get(
            f'{self.base_url}/analytics/conversation/{conversation_id}',
            headers=self._get_headers()
        ) as resp:
            data = await resp.json()
            if resp.status == 200:
                return data
            else:
                raise Exception(f"Failed to get analytics: {data}")
    
    async def end_conversation(self, conversation_id: str, outcome: str) -> Dict[str, Any]:
        """End the conversation with an outcome."""
        async with self.session.post(
            f'{self.base_url}/conversation/{conversation_id}/end',
            json={'outcome': outcome},
            headers=self._get_headers()
        ) as resp:
            data = await resp.json()
            if resp.status == 200:
                print(f"✅ Conversation ended: {outcome}")
                return data
            else:
                raise Exception(f"Failed to end conversation: {data}")


async def simulate_sales_conversation():
    """Simulate a complete sales conversation flow."""
    
    # Configuration
    BASE_URL = "http://localhost:8000/v1"  # Change to production URL
    USERNAME = "demo@ngx.com"
    PASSWORD = "DemoPass123!"
    
    async with NGXSalesClient(BASE_URL) as client:
        print("🚀 NGX Voice Sales Agent - API Integration Example")
        print("="*60)
        
        try:
            # Step 1: Authenticate
            print("\n1️⃣ Authenticating...")
            await client.login(USERNAME, PASSWORD)
            
            # Step 2: Start conversation
            print("\n2️⃣ Starting conversation...")
            customer_info = {
                "name": "Carlos Mendoza",
                "email": "carlos@elitegym.com",
                "phone": "+521234567890",
                "business_type": "gym",
                "business_size": "medium",
                "location": "Ciudad de México"
            }
            
            conversation = await client.start_conversation(customer_info)
            conv_id = conversation['conversation_id']
            
            # Step 3: Simulate conversation flow
            print("\n3️⃣ Simulating conversation...")
            
            # Customer messages to simulate
            customer_messages = [
                "Hola, estoy buscando mejorar la retención de clientes en mi gimnasio",
                "¿Cómo funciona exactamente su sistema?",
                "¿Qué resultados han visto otros gimnasios?",
                "Me preocupa el costo, ¿cuánto es la inversión?",
                "¿Incluye soporte técnico?",
                "¿Puedo ver una demostración primero?",
                "Suena interesante, ¿cuáles son los próximos pasos?"
            ]
            
            messages = []
            
            for i, customer_msg in enumerate(customer_messages):
                print(f"\n💬 Cliente: {customer_msg}")
                
                # Send message
                response = await client.send_message(conv_id, customer_msg)
                
                # Add to message history
                messages.append({"role": "customer", "content": customer_msg})
                messages.append({"role": "agent", "content": response['message']})
                
                print(f"🤖 Agente: {response['message']}")
                
                # Show metadata
                if 'metadata' in response:
                    meta = response['metadata']
                    print(f"   📊 Sentimiento: {meta.get('sentiment', 'N/A')}")
                    print(f"   🎯 Intent: {meta.get('detected_intent', 'N/A')}")
                    print(f"   💪 Confianza: {meta.get('confidence', 0):.2f}")
                
                # Get predictions every 3 messages
                if (i + 1) % 3 == 0:
                    print("\n🔮 Obteniendo predicciones ML...")
                    predictions = await client.get_predictions(conv_id, messages)
                    
                    if 'conversion' in predictions:
                        conv_prob = predictions['conversion']['probability']
                        print(f"   📈 Probabilidad de conversión: {conv_prob:.2%}")
                    
                    if 'objections' in predictions:
                        objections = predictions['objections']['objections']
                        if objections:
                            print(f"   ⚠️  Objeciones predichas:")
                            for obj in objections[:2]:
                                print(f"      - {obj['type']}: {obj['probability']:.2%}")
                    
                    if 'needs' in predictions:
                        needs = predictions['needs']['needs']
                        if needs:
                            print(f"   🎯 Necesidades detectadas:")
                            for need in needs[:2]:
                                print(f"      - {need['category']}: {need['description']}")
                
                # Small delay to simulate natural conversation
                await asyncio.sleep(1)
            
            # Step 4: Get final analytics
            print("\n4️⃣ Obteniendo análisis final...")
            analytics = await client.get_analytics(conv_id)
            
            print("\n📊 Análisis de la Conversación:")
            print(f"   ⏱️  Duración: {analytics.get('duration_seconds', 0)} segundos")
            print(f"   💬 Mensajes: {analytics.get('message_count', 0)}")
            print(f"   🎯 Engagement: {analytics.get('customer_engagement_score', 0):.2f}")
            print(f"   🛡️  Objeciones manejadas: {analytics.get('objections_handled', 0)}")
            print(f"   📈 Probabilidad final: {analytics.get('conversion_probability', 0):.2%}")
            
            if 'roi_projection' in analytics:
                roi = analytics['roi_projection']
                print(f"\n💰 Proyección ROI:")
                print(f"   📊 ROI: {roi.get('percentage', 0):.1f}%")
                print(f"   💵 Valor anual: ${roi.get('annual_value', 0):,.2f}")
                print(f"   ⏱️  Payback: {roi.get('payback_months', 0):.1f} meses")
            
            # Step 5: End conversation
            print("\n5️⃣ Finalizando conversación...")
            outcome = "converted" if analytics.get('conversion_probability', 0) > 0.7 else "follow_up_required"
            await client.end_conversation(conv_id, outcome)
            
            print("\n✅ Ejemplo completado exitosamente!")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()


async def test_error_handling():
    """Test API error handling."""
    print("\n🧪 Testing Error Handling")
    print("="*60)
    
    async with NGXSalesClient("http://localhost:8000/v1") as client:
        # Test 1: Invalid credentials
        print("\n❌ Test 1: Invalid credentials")
        try:
            await client.login("invalid@user.com", "wrongpass")
        except Exception as e:
            print(f"   Expected error: {e}")
        
        # Test 2: Unauthorized request
        print("\n❌ Test 2: Unauthorized request")
        try:
            await client.start_conversation({"name": "Test"})
        except Exception as e:
            print(f"   Expected error: {e}")
        
        # Test 3: Invalid conversation ID
        print("\n❌ Test 3: Invalid conversation ID")
        client.token = "fake_token"  # Simulate auth
        try:
            await client.send_message("invalid-id", "Hello")
        except Exception as e:
            print(f"   Expected error: {e}")


if __name__ == "__main__":
    print("🚀 NGX Voice Sales Agent API Integration Examples\n")
    print("1. Simulate complete sales conversation")
    print("2. Test error handling")
    print("3. Exit")
    
    choice = input("\nSelect option (1-3): ")
    
    if choice == "1":
        asyncio.run(simulate_sales_conversation())
    elif choice == "2":
        asyncio.run(test_error_handling())
    else:
        print("Goodbye!")