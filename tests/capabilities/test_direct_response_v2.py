import requests
import json
import time

# Test mejorado para ver respuestas reales
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
    conversation_id = data.get("conversation_id")
    print(f"✅ Conversación iniciada: {conversation_id}")
    greeting = data.get("message", data.get("response", "No greeting"))
    print(f"🤖 Saludo: {greeting[:300]}...")
else:
    print(f"❌ Error: {start_response.status_code}")
    print(f"Details: {start_response.text}")
    exit(1)

# Helper function to send message
def send_message(conv_id, message):
    resp = requests.post(
        f"{api_url}/conversations/{conv_id}/message",
        json={"message": message}
    )
    if resp.status_code == 200:
        data = resp.json()
        return data.get("message", data.get("response", "No response"))
    else:
        return f"Error: {resp.status_code}"

# 2. Preguntar por HIE
print("\n=== TEST HIE ===")
msg1 = "¿Qué es HIE y cómo funciona con los agentes?"
print(f"👤 Usuario: {msg1}")
response = send_message(conversation_id, msg1)
print(f"🤖 Agente: {response[:400]}...")
# Contar menciones de agentes
agents = ["NEXUS", "BLAZE", "SAGE", "WAVE", "SPARK", "NOVA", "LUNA", "STELLA", "CODE", "GUARDIAN", "NODE"]
mentioned = [agent for agent in agents if agent in response]
print(f"📊 Agentes mencionados: {mentioned} ({len(mentioned)}/11)")

# 3. Preguntar por ROI
print("\n=== TEST ROI ===")
msg2 = "Soy CEO y cobro $300/hora. ¿Cuál sería mi ROI con NGX?"
print(f"👤 Usuario: {msg2}")
response = send_message(conversation_id, msg2)
print(f"🤖 Agente: {response[:400]}...")
# Buscar indicadores ROI
roi_keywords = ["ROI", "$", "hora", "productividad", "300", "CEO", "%", "retorno"]
found_keywords = [kw for kw in roi_keywords if kw in response]
print(f"📊 ROI Keywords: {found_keywords}")

# 4. Test de empatía
print("\n=== TEST EMPATÍA ===")
msg3 = "Estoy agotado, trabajo 80 horas a la semana y siento que no puedo más"
print(f"👤 Usuario: {msg3}")
response = send_message(conversation_id, msg3)
print(f"🤖 Agente: {response[:400]}...")
# Buscar indicadores de empatía
empathy_keywords = ["entiendo", "comprendo", "difícil", "agotador", "reconozco", "valoro", "desgastante", "siento"]
found_empathy = [kw for kw in empathy_keywords if kw.lower() in response.lower()]
print(f"📊 Palabras empáticas: {found_empathy}")

# 5. Test de detección de tier
print("\n=== TEST TIER DETECTION ===")
msg4 = "¿Cuánto cuesta el programa? Necesito algo premium con soporte personalizado"
print(f"👤 Usuario: {msg4}")
response = send_message(conversation_id, msg4)
print(f"🤖 Agente: {response[:400]}...")
# Buscar indicadores de tier
tier_keywords = ["VIP", "Premium", "Enterprise", "personalizado", "dedicado", "$7,500", "$2,500", "$997"]
found_tier = [kw for kw in tier_keywords if kw in response]
print(f"📊 Tier indicators: {found_tier}")

# 6. Test ML Adaptive
print("\n=== TEST ML ADAPTIVE ===")
msg5 = "Me interesa pero necesito resultados garantizados y métricas claras"
print(f"👤 Usuario: {msg5}")
response = send_message(conversation_id, msg5)
print(f"🤖 Agente: {response[:400]}...")
# Buscar indicadores ML/métricas
ml_keywords = ["métrica", "KPI", "resultado", "garantía", "medible", "seguimiento", "progreso"]
found_ml = [kw for kw in ml_keywords if kw.lower() in response.lower()]
print(f"📊 ML/Metrics keywords: {found_ml}")

print("\n=== RESUMEN ===")
print(f"✅ HIE Agents: {len(mentioned)}/11 mencionados")
print(f"✅ ROI Keywords: {len(found_keywords)} encontrados")
print(f"✅ Empathy Words: {len(found_empathy)} encontrados") 
print(f"✅ Tier Detection: {len(found_tier)} indicadores")
print(f"✅ ML/Metrics: {len(found_ml)} keywords")