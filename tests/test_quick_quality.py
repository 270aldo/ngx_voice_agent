#!/usr/bin/env python3
"""
Quick quality test to verify improvements.
"""
import asyncio
import aiohttp
import json

async def test_conversation_flow():
    API_URL = "http://127.0.0.1:8000"
    
    async with aiohttp.ClientSession() as session:
        # Start conversation
        customer_data = {
            "name": "Carlos",
            "email": "carlos@test.com",
            "age": 35,
            "occupation": "CTO"
        }
        
        print("🚀 Starting conversation test...")
        print("-" * 50)
        
        # Start conversation
        start_response = await session.post(
            f"{API_URL}/conversations/start",
            json={"customer_data": customer_data},
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        if start_response.status != 200:
            print(f"❌ Failed to start: {start_response.status}")
            return
            
        data = await start_response.json()
        conversation_id = data['conversation_id']
        print(f"✅ Started conversation: {conversation_id[:8]}...")
        print(f"🤖 Greeting: {data['message']}")
        print()
        
        # Test messages
        test_messages = [
            "Estoy agotado, trabajo 14 horas al día",
            "¿Cuánto cuesta el programa?",
            "Me preocupa que sea muy caro",
            "¿Qué garantías tienen?"
        ]
        
        for msg in test_messages:
            print(f"👤 User: {msg}")
            
            msg_response = await session.post(
                f"{API_URL}/conversations/{conversation_id}/message",
                json={"message": msg},
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            if msg_response.status != 200:
                error_text = await msg_response.text()
                print(f"❌ Error: {error_text}")
                continue
                
            msg_data = await msg_response.json()
            response = msg_data['message']
            
            print(f"🤖 Agent: {response[:200]}...")
            
            # Check for repetitive phrases
            if "Tu cautela inicial es exactamente" in response:
                print("⚠️  WARNING: Found repetitive phrase!")
            else:
                print("✅ No repetitive phrases detected")
            
            print("-" * 50)
            await asyncio.sleep(1)
        
        print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_conversation_flow())