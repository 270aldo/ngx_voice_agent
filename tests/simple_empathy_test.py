#!/usr/bin/env python3
"""
Test simple y rápido de empatía del agente NGX.
Evalúa específicamente la mejora en empatía con GPT-4o.
"""

import asyncio
import aiohttp
import json
import os
from openai import AsyncOpenAI
from datetime import datetime

# Configuration
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("❌ ERROR: OPENAI_API_KEY not found in environment")
    exit(1)


async def test_empathy():
    """Test específico de empatía con un solo escenario."""
    print("🧪 NGX Voice Sales Agent - Empathy Test")
    print("=" * 50)
    print(f"API URL: {API_URL}")
    print(f"Using GPT-4o for evaluation")
    print("=" * 50)
    
    openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    # Test scenario: Cliente ansioso con preocupaciones
    test_data = {
        "customer_data": {
            "name": "Ana García",
            "email": "ana@test.com",
            "age": 45,
            "occupation": "Empresaria",
            "goals": {"primary": "stress_management"},
            "lifestyle": {"stress_level": "high"}
        },
        "messages": [
            "Hola, estoy muy estresada con mi trabajo y no sé si esto funcionará",
            "Me preocupa el precio y el tiempo que requiere",
            "Ya he probado muchas cosas y nada me ha funcionado"
        ]
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            # Start conversation
            print("\n1️⃣ Starting conversation...")
            start_response = await session.post(
                f"{API_URL}/conversations/start",
                json={"customer_data": test_data["customer_data"]},
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            if start_response.status != 200:
                print(f"❌ Failed to start conversation: {start_response.status}")
                return
            
            start_data = await start_response.json()
            conversation_id = start_data["conversation_id"]
            print(f"✅ Conversation started: {conversation_id}")
            
            # Evaluate initial response
            print("\n2️⃣ Evaluating initial greeting...")
            initial_empathy = await evaluate_empathy(
                openai_client,
                "Hola",
                start_data["message"]
            )
            print(f"Initial empathy score: {initial_empathy:.1f}/10")
            
            # Test empathy with anxious messages
            all_scores = [initial_empathy]
            
            for i, message in enumerate(test_data["messages"]):
                print(f"\n3️⃣ Testing message {i+1}: '{message[:50]}...'")
                
                # Send message
                msg_response = await session.post(
                    f"{API_URL}/conversations/{conversation_id}/message",
                    json={"message": message},
                    timeout=aiohttp.ClientTimeout(total=30)
                )
                
                if msg_response.status != 200:
                    print(f"❌ Message failed: {msg_response.status}")
                    continue
                
                msg_data = await msg_response.json()
                agent_response = msg_data["message"]
                
                # Evaluate empathy
                empathy_score = await evaluate_empathy(
                    openai_client,
                    message,
                    agent_response
                )
                all_scores.append(empathy_score)
                
                print(f"Response preview: {agent_response[:100]}...")
                print(f"Empathy score: {empathy_score:.1f}/10")
                
                # Small delay
                await asyncio.sleep(1)
            
            # Final results
            avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
            print("\n" + "=" * 50)
            print("📊 EMPATHY TEST RESULTS")
            print("=" * 50)
            print(f"Average Empathy Score: {avg_score:.1f}/10")
            print(f"Individual Scores: {[f'{s:.1f}' for s in all_scores]}")
            
            if avg_score >= 9.0:
                print("✅ EXCELLENT: Empathy is at target level!")
            elif avg_score >= 7.0:
                print("⚠️  GOOD: Empathy is good but can improve")
            else:
                print("❌ NEEDS WORK: Empathy needs significant improvement")
                
        except Exception as e:
            print(f"\n❌ Test error: {str(e)}")
            import traceback
            traceback.print_exc()


async def evaluate_empathy(openai_client, user_message: str, agent_response: str) -> float:
    """Evaluate empathy score using GPT-4o."""
    prompt = f"""
    Evalúa el nivel de EMPATÍA en esta respuesta de un agente de ventas.
    
    Cliente dijo: "{user_message}"
    Agente respondió: "{agent_response}"
    
    Criterios de empatía (puntaje 1-10):
    - Validación emocional: ¿Reconoce y valida los sentimientos del cliente?
    - Comprensión genuina: ¿Muestra que realmente entiende la situación?
    - Calidez humana: ¿El tono es cálido y personal, no robótico?
    - Conexión personal: ¿Usa lenguaje que crea conexión (tú, contigo, etc.)?
    - Apoyo incondicional: ¿Transmite que está ahí para ayudar sin presionar?
    
    IMPORTANTE: Sé estricto. Solo da 10/10 si la empatía es EXCEPCIONAL.
    
    Responde SOLO con un número del 1 al 10.
    """
    
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un evaluador experto en empatía. Responde SOLO con un número del 1-10."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=10
        )
        
        score_text = response.choices[0].message.content.strip()
        # Extract number from response
        import re
        numbers = re.findall(r'\d+\.?\d*', score_text)
        if numbers:
            return float(numbers[0])
        else:
            return 0.0
            
    except Exception as e:
        print(f"Error evaluating empathy: {e}")
        return 0.0


if __name__ == "__main__":
    asyncio.run(test_empathy())