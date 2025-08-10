#!/usr/bin/env python3
"""
Test performance after simplification.
"""
import asyncio
import time
import requests
import json
from datetime import datetime

API_BASE_URL = "http://127.0.0.1:8000"

# Test scenarios
TEST_SCENARIOS = [
    {
        "name": "Cansancio extremo",
        "initial_message": "Estoy agotado, trabajo 14 horas al día en mi startup",
        "messages": [
            "¿Cómo me puede ayudar NGX con mi agotamiento?",
            "¿Cuánto cuesta el programa?",
            "Me preocupa no tener tiempo para otro compromiso más",
            "¿Hay garantías de que funcione?"
        ]
    },
    {
        "name": "Madre preocupada",
        "initial_message": "Soy madre de 3 hijos y necesito más energía",
        "messages": [
            "Me cuesta mucho levantarme por las mañanas",
            "¿Es muy caro? Tengo un presupuesto limitado",
            "¿Cómo sé que esto no es otra promesa vacía?",
            "¿Puedo probar antes de comprometerme?"
        ]
    }
]

def measure_response_time(func):
    """Decorator to measure response time."""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        return result, (end - start)
    return wrapper

@measure_response_time
def start_conversation(customer_data):
    """Start a conversation."""
    response = requests.post(
        f"{API_BASE_URL}/conversation/start",
        json=customer_data
    )
    return response

@measure_response_time
def send_message(conversation_id, message):
    """Send a message."""
    response = requests.post(
        f"{API_BASE_URL}/conversation/message",
        json={
            "conversation_id": conversation_id,
            "message": message
        }
    )
    return response

def analyze_response(response_text):
    """Analyze response for quality metrics."""
    metrics = {
        "length": len(response_text),
        "has_empathy": any(word in response_text.lower() for word in [
            "entiendo", "comprendo", "reconozco", "valoro", "aprecio"
        ]),
        "has_price_mention": any(word in response_text.lower() for word in [
            "precio", "costo", "inversión", "$"
        ]),
        "has_hie_mention": "hie" in response_text.lower() or "inteligencia híbrida" in response_text.lower(),
        "has_question": "?" in response_text,
        "repetitive_phrases": []
    }
    
    # Check for known repetitive phrases
    repetitive_patterns = [
        "Tu cautela inicial es exactamente",
        "Comprendo que tu tiempo es extremadamente valioso",
        "Entiendo tu punto"
    ]
    
    for pattern in repetitive_patterns:
        if pattern in response_text:
            metrics["repetitive_phrases"].append(pattern)
    
    return metrics

def main():
    print("🚀 Testing Simplified Performance")
    print("=" * 60)
    
    results = []
    
    for scenario in TEST_SCENARIOS:
        print(f"\n📋 Scenario: {scenario['name']}")
        print("-" * 40)
        
        scenario_results = {
            "name": scenario["name"],
            "response_times": [],
            "responses": [],
            "metrics": []
        }
        
        # Start conversation
        customer_data = {
            "name": "Test User",
            "email": f"test_{int(time.time())}@example.com",
            "initial_message": scenario["initial_message"]
        }
        
        start_response, start_time = start_conversation(customer_data)
        
        if start_response.status_code != 200:
            print(f"❌ Failed to start conversation: {start_response.text}")
            continue
        
        conversation_data = start_response.json()
        conversation_id = conversation_data["conversation_id"]
        
        print(f"✅ Started conversation: {conversation_id[:8]}...")
        print(f"⏱️  Start time: {start_time:.2f}s")
        
        scenario_results["response_times"].append(start_time)
        
        # Send messages
        for i, message in enumerate(scenario["messages"]):
            print(f"\n💬 Message {i+1}: {message}")
            
            msg_response, msg_time = send_message(conversation_id, message)
            
            if msg_response.status_code != 200:
                print(f"❌ Failed to send message: {msg_response.text}")
                continue
            
            response_data = msg_response.json()
            agent_response = response_data["response"]
            
            # Analyze response
            metrics = analyze_response(agent_response)
            
            print(f"🤖 Response: {agent_response[:100]}...")
            print(f"⏱️  Response time: {msg_time:.2f}s")
            print(f"📊 Metrics:")
            print(f"   - Length: {metrics['length']} chars")
            print(f"   - Has empathy: {'✅' if metrics['has_empathy'] else '❌'}")
            print(f"   - Has question: {'✅' if metrics['has_question'] else '❌'}")
            print(f"   - Repetitive phrases: {len(metrics['repetitive_phrases'])}")
            
            if metrics["repetitive_phrases"]:
                print(f"   ⚠️  Found repetitive: {metrics['repetitive_phrases']}")
            
            scenario_results["response_times"].append(msg_time)
            scenario_results["responses"].append(agent_response)
            scenario_results["metrics"].append(metrics)
        
        results.append(scenario_results)
    
    # Summary
    print("\n\n📊 PERFORMANCE SUMMARY")
    print("=" * 60)
    
    total_messages = 0
    total_time = 0
    repetitive_count = 0
    
    for scenario in results:
        times = scenario["response_times"]
        avg_time = sum(times) / len(times) if times else 0
        
        print(f"\n{scenario['name']}:")
        print(f"  Average response time: {avg_time:.2f}s")
        print(f"  Min/Max: {min(times):.2f}s / {max(times):.2f}s")
        
        # Count repetitive phrases
        for metrics in scenario["metrics"]:
            if metrics["repetitive_phrases"]:
                repetitive_count += len(metrics["repetitive_phrases"])
        
        total_messages += len(times)
        total_time += sum(times)
    
    overall_avg = total_time / total_messages if total_messages > 0 else 0
    
    print(f"\n🎯 OVERALL:")
    print(f"  Total messages: {total_messages}")
    print(f"  Average response time: {overall_avg:.2f}s")
    print(f"  Repetitive phrases found: {repetitive_count}")
    print(f"  Performance target: <0.5s {'✅ PASS' if overall_avg < 0.5 else '❌ FAIL'}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"tests/results/simplified_performance_{timestamp}.json", "w") as f:
        json.dump({
            "timestamp": timestamp,
            "results": results,
            "summary": {
                "total_messages": total_messages,
                "average_response_time": overall_avg,
                "repetitive_phrases_count": repetitive_count,
                "target_met": overall_avg < 0.5
            }
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: tests/results/simplified_performance_{timestamp}.json")

if __name__ == "__main__":
    main()