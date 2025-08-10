import requests
import json
import time

# Test básico para ver respuestas reales
api_url = "http://localhost:8000"

# 1. Iniciar conversación
print("=== INICIANDO CONVERSACIÓN ===")
start_response = requests.post(f"{api_url}/conversations/start", json={
    "customer_data": {
        "name": "Carlos CEO",
        "email": "carlos@tech.com",
        "age": 45,
        "occupation": "CEO"
    },
    "program_type": "PRIME"
})

if start_response.status_code == 200:
    data = start_response.json()
    print("DEBUG - Response structure:", list(data.keys()))
    conversation_id = data.get("conversation_id")
    print(f"✅ Conversación iniciada: {conversation_id}")
    if "response" in data:
        print(f"🤖 Saludo: {data['response'][:200]}...")
    elif "greeting" in data:
        print(f"🤖 Saludo: {data['greeting'][:200]}...")
    else:
        print("🤖 No greeting message found")
else:
    print(f"❌ Error: {start_response.status_code}")
    print(f"Details: {start_response.text}")
    exit(1)

# 2. Preguntar por HIE
print("\n=== TEST HIE ===")
msg1 = "¿Qué es HIE y cómo funciona con los agentes?"
print(f"👤 Usuario: {msg1}")

msg1_response = requests.post(
    f"{api_url}/conversations/{conversation_id}/message",
    json={"message": msg1}
)

if msg1_response.status_code == 200:
    resp_data = msg1_response.json()
    print("DEBUG - Message response structure:", list(resp_data.keys()))
    response = resp_data.get("response", resp_data.get("message", "No response found"))
    print(f"🤖 Agente: {response[:200]}...")
    # Contar menciones de agentes
    agents = ["NEXUS", "BLAZE", "SAGE", "WAVE", "SPARK", "NOVA", "LUNA", "STELLA", "CODE", "GUARDIAN", "NODE"]
    mentioned = [agent for agent in agents if agent in response]
    print(f"📊 Agentes mencionados: {mentioned} ({len(mentioned)}/11)")
else:
    print(f"❌ Error: {msg1_response.status_code}")

# 3. Preguntar por ROI
print("\n=== TEST ROI ===")
msg2 = "Soy CEO y cobro $300/hora. ¿Cuál sería mi ROI con NGX?"
print(f"👤 Usuario: {msg2}")

msg2_response = requests.post(
    f"{api_url}/conversations/{conversation_id}/message",
    json={"message": msg2}
)

if msg2_response.status_code == 200:
    response = msg2_response.json()["response"]
    print(f"🤖 Agente: {response[:200]}...")
    # Buscar indicadores ROI
    roi_keywords = ["ROI", "$", "horas", "productividad", "300", "CEO"]
    found_keywords = [kw for kw in roi_keywords if kw in response]
    print(f"📊 ROI Keywords: {found_keywords}")
else:
    print(f"❌ Error: {msg2_response.status_code}")

# 4. Test de empatía
print("\n=== TEST EMPATÍA ===")
msg3 = "Estoy agotado, trabajo 80 horas a la semana y siento que no puedo más"
print(f"👤 Usuario: {msg3}")

msg3_response = requests.post(
    f"{api_url}/conversations/{conversation_id}/message",
    json={"message": msg3}
)

if msg3_response.status_code == 200:
    response = msg3_response.json()["response"]
    print(f"🤖 Agente: {response[:200]}...")
    # Buscar indicadores de empatía
    empathy_keywords = ["entiendo", "comprendo", "difícil", "agotador", "reconozco", "valoro"]
    found_empathy = [kw for kw in empathy_keywords if kw.lower() in response.lower()]
    print(f"📊 Palabras empáticas: {found_empathy}")
else:
    print(f"❌ Error: {msg3_response.status_code}")