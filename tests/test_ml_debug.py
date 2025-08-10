#!/usr/bin/env python3
"""
Debug test para verificar qué está retornando el sistema ML.
"""

import asyncio
import aiohttp
import json
from pprint import pprint


async def test_ml_debug():
    """Debug ML integration."""
    
    print("\n🔍 DEBUG ML - NGX Voice Sales Agent")
    print("=" * 60)
    
    api_url = "http://localhost:8000"
    
    try:
        async with aiohttp.ClientSession() as session:
            # Start conversation
            start_data = {
                "customer_data": {
                    "name": "Debug User",
                    "email": "debug@test.com",
                    "age": 40,
                    "occupation": "CEO"
                }
            }
            
            async with session.post(
                f"{api_url}/conversations/start",
                json=start_data
            ) as response:
                data = await response.json()
                conversation_id = data.get("conversation_id")
                print(f"Conversation ID: {conversation_id}")
            
            # Send a message that should trigger ML
            message = "Estoy preocupado por el precio y el tiempo de compromiso"
            
            async with session.post(
                f"{api_url}/conversations/{conversation_id}/message",
                json={"message": message}
            ) as response:
                data = await response.json()
                
                print("\n📊 RESPUESTA COMPLETA DEL API:")
                print("-" * 40)
                pprint(data)
                
                if "ml_insights" in data:
                    print("\n🧠 ML INSIGHTS RECIBIDOS:")
                    print("-" * 40)
                    pprint(data["ml_insights"])
                else:
                    print("\n❌ No se encontraron ML insights en la respuesta")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ml_debug())