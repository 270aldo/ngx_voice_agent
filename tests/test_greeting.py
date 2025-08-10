import asyncio
import aiohttp
import json

async def test_greeting():
    API_URL = "http://127.0.0.1:8000"
    
    async with aiohttp.ClientSession() as session:
        # Start conversation
        customer_data = {
            "name": "María",
            "email": "maria@test.com",
            "phone": "+52123456789",
            "age": 35,
            "initial_message": "Hola, quiero información"
        }
        
        start_response = await session.post(
            f"{API_URL}/conversations/start",
            json={"customer_data": customer_data},
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        if start_response.status == 200:
            data = await start_response.json()
            print(f"✅ Conversation ID: {data['conversation_id']}")
            print(f"\n📝 GREETING:")
            print("-" * 50)
            print(data['message'])
            print("-" * 50)
        else:
            print(f"❌ Failed to start: {start_response.status}")
            print(await start_response.text())

if __name__ == "__main__":
    asyncio.run(test_greeting())