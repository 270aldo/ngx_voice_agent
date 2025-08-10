#!/usr/bin/env python3
"""
Test manual de la API para verificar funcionamiento.
"""

import requests
import json
from datetime import datetime

# API base URL
API_URL = "http://localhost:8000"

print("\n🚀 TEST MANUAL DE API - NGX VOICE SALES AGENT")
print("=" * 50)
print(f"Timestamp: {datetime.now()}")
print(f"API URL: {API_URL}")

# Test 1: Health check
print("\n1️⃣ Health Check...")
try:
    response = requests.get(f"{API_URL}/health")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   Error: {e}")

# Test 2: Start conversation
print("\n2️⃣ Starting conversation...")
customer_data = {
    "name": "Carlos Test",
    "email": "carlos@test.com",
    "age": 42,
    "occupation": "CEO",
    "company": "TestCorp"
}

try:
    response = requests.post(
        f"{API_URL}/conversations/start",
        json={"customer_data": customer_data}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        conversation_id = data.get("conversation_id")
        print(f"   Conversation ID: {conversation_id}")
        print(f"   Response: {json.dumps(data, indent=2)}")
        
        # Test 3: Send message
        if conversation_id:
            print("\n3️⃣ Sending message...")
            message_data = {
                "message": "Hola, soy CEO de una empresa de tecnología y necesito ayuda para mejorar mi productividad"
            }
            
            response = requests.post(
                f"{API_URL}/conversations/{conversation_id}/message",
                json=message_data
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
            
            # Test 4: Ask about HIE
            print("\n4️⃣ Asking about HIE...")
            hie_message = {
                "message": "¿Qué es HIE y cómo funcionan los 11 agentes?"
            }
            
            response = requests.post(
                f"{API_URL}/conversations/{conversation_id}/message",
                json=hie_message
            )
            print(f"   Status: {response.status_code}")
            data = response.json()
            if "response" in data:
                agent_response = data["response"]
                print(f"\n   Agent response preview: {agent_response[:200]}...")
                
                # Check for HIE agents
                agents = ["NEXUS", "BLAZE", "SAGE", "WAVE", "SPARK", 
                         "NOVA", "LUNA", "STELLA", "CODE", "GUARDIAN", "NODE"]
                agents_found = [a for a in agents if a in agent_response.upper()]
                print(f"\n   HIE Agents mentioned: {len(agents_found)}/11")
                if agents_found:
                    print(f"   Agents: {', '.join(agents_found)}")
            
            # Test 5: Ask about PRIME
            print("\n5️⃣ Asking about PRIME program...")
            prime_message = {
                "message": "¿Qué incluye el programa PRIME y cuál es el precio?"
            }
            
            response = requests.post(
                f"{API_URL}/conversations/{conversation_id}/message",
                json=prime_message
            )
            print(f"   Status: {response.status_code}")
            data = response.json()
            if "response" in data:
                agent_response = data["response"]
                print(f"\n   Agent response preview: {agent_response[:200]}...")
                
                # Check for PRIME mention
                if "PRIME" in agent_response.upper():
                    print("   ✅ PRIME program mentioned!")
                if "$" in agent_response or "precio" in agent_response.lower():
                    print("   ✅ Pricing mentioned!")
    else:
        print(f"   Error: {response.text}")
        
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 50)
print("🏁 Test completed!")