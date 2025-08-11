"""
Load Testing for NGX Voice Sales Agent.

This module implements comprehensive load testing scenarios to validate
system performance with 100+ concurrent users.
"""

import json
import random
import time
from datetime import datetime
from typing import Dict, List, Any
import uuid

from locust import HttpUser, task, between, events
from locust.env import Environment
from faker import Faker

# Initialize Faker for realistic test data
fake = Faker(['es_ES', 'es_MX'])  # Spanish locales for NGX

# Test configuration
TEST_CONFIG = {
    "programs": ["PRIME", "LONGEVITY"],
    "tiers": ["AGENTS ACCESS", "Hybrid Coaching"],
    "age_ranges": {
        "PRIME": (25, 45),
        "LONGEVITY": (45, 70)
    },
    "occupations": [
        "Empresario", "Director de Marketing", "Médico", "Abogado",
        "Ingeniero", "Consultor", "Profesor", "Emprendedor"
    ],
    "goals": {
        "PRIME": [
            "Mejorar mi productividad diaria",
            "Tener más energía durante el día",
            "Optimizar mi rendimiento mental",
            "Reducir el estrés laboral"
        ],
        "LONGEVITY": [
            "Envejecer de forma saludable",
            "Prevenir enfermedades crónicas",
            "Mantener mi vitalidad",
            "Mejorar mi calidad de vida"
        ]
    }
}


class NGXVoiceSalesUser(HttpUser):
    """
    Simulates a user interacting with the NGX Voice Sales Agent.
    
    This user class represents different customer personas and their
    typical conversation flows through the sales process.
    """
    
    wait_time = between(2, 5)  # Realistic wait between messages
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conversation_id = None
        self.jwt_token = None
        self.customer_profile = None
        self.conversation_phase = "greeting"
        self.message_count = 0
        
    def on_start(self):
        """Initialize user session and authenticate."""
        # Generate customer profile
        self.customer_profile = self._generate_customer_profile()
        
        # Authenticate and get JWT token
        self._authenticate()
        
        # Start conversation
        self._start_conversation()
    
    def _generate_customer_profile(self) -> Dict[str, Any]:
        """Generate realistic customer profile."""
        program = random.choice(TEST_CONFIG["programs"])
        age_min, age_max = TEST_CONFIG["age_ranges"][program]
        
        return {
            "name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "age": random.randint(age_min, age_max),
            "occupation": random.choice(TEST_CONFIG["occupations"]),
            "program_interest": program,
            "goals": {
                "primary": random.choice(TEST_CONFIG["goals"][program]),
                "secondary": random.sample(TEST_CONFIG["goals"][program], 2)
            },
            "budget_range": random.choice(["low", "medium", "high"]),
            "urgency": random.choice(["immediate", "this_month", "exploring"])
        }
    
    def _authenticate(self):
        """Authenticate user and get JWT token."""
        with self.client.post(
            "/auth/login",
            json={
                "email": "test@ngx.com",
                "password": "test_password"
            },
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.jwt_token = data.get("access_token")
                response.success()
            else:
                response.failure(f"Authentication failed: {response.status_code}")
    
    def _start_conversation(self):
        """Start a new conversation."""
        headers = self._get_headers()
        
        with self.client.post(
            "/conversation/start",
            json={
                "customer_data": self.customer_profile,
                "program_type": self.customer_profile["program_interest"],
                "channel": "web",
                "metadata": {
                    "source": "load_test",
                    "test_id": str(uuid.uuid4())
                }
            },
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.conversation_id = data.get("conversation_id")
                response.success()
            else:
                response.failure(f"Failed to start conversation: {response.status_code}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.jwt_token}",
            "Content-Type": "application/json",
            "X-Request-ID": str(uuid.uuid4())
        }
    
    def _generate_user_message(self) -> str:
        """Generate realistic user message based on conversation phase."""
        messages_by_phase = {
            "greeting": [
                f"Hola, soy {self.customer_profile['name']} y estoy interesado en {self.customer_profile['program_interest']}",
                f"Buenos días, me gustaría información sobre sus programas",
                f"Hola, tengo {self.customer_profile['age']} años y busco mejorar mi salud"
            ],
            "exploration": [
                f"Mi objetivo principal es {self.customer_profile['goals']['primary']}",
                f"Trabajo como {self.customer_profile['occupation']} y necesito más energía",
                "¿Qué incluye exactamente el programa?",
                "¿Cuánto tiempo dura el programa completo?"
            ],
            "presentation": [
                "¿Cuáles son los beneficios específicos?",
                "¿Tienen casos de éxito de personas como yo?",
                "¿Cómo funciona el seguimiento?",
                "¿Qué tipo de resultados puedo esperar?"
            ],
            "objection_handling": [
                "¿Cuál es el precio del programa?",
                "Me parece un poco caro, ¿hay opciones de pago?",
                "¿Qué garantías ofrecen?",
                "Necesito pensarlo un poco más"
            ],
            "closing": [
                "Me interesa, ¿cuáles son los siguientes pasos?",
                "¿Puedo empezar esta semana?",
                "¿Cómo agendo mi primera sesión?",
                "Estoy listo para comenzar"
            ]
        }
        
        return random.choice(messages_by_phase.get(self.conversation_phase, messages_by_phase["greeting"]))
    
    def _update_conversation_phase(self, response_text: str):
        """Update conversation phase based on agent response."""
        phase_keywords = {
            "exploration": ["cuéntame más", "háblame de", "objetivos"],
            "presentation": ["nuestro programa", "beneficios", "incluye"],
            "objection_handling": ["precio", "inversión", "garantía"],
            "closing": ["próximos pasos", "agendar", "comenzar"]
        }
        
        current_index = list(phase_keywords.keys()).index(self.conversation_phase) if self.conversation_phase in phase_keywords else -1
        
        for phase, keywords in phase_keywords.items():
            phase_index = list(phase_keywords.keys()).index(phase)
            if phase_index > current_index and any(kw in response_text.lower() for kw in keywords):
                self.conversation_phase = phase
                break
    
    @task(weight=70)
    def send_message(self):
        """Main task: Send message in ongoing conversation."""
        if not self.conversation_id:
            self._start_conversation()
            return
        
        # Generate and send message
        user_message = self._generate_user_message()
        headers = self._get_headers()
        
        start_time = time.time()
        
        with self.client.post(
            f"/conversation/{self.conversation_id}/message",
            json={
                "message": user_message,
                "metadata": {
                    "phase": self.conversation_phase,
                    "message_number": self.message_count
                }
            },
            headers=headers,
            catch_response=True,
            name="/conversation/[id]/message"
        ) as response:
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            if response.status_code == 200:
                data = response.json()
                agent_response = data.get("response", "")
                
                # Validate response quality
                if len(agent_response) < 10:
                    response.failure("Response too short")
                elif response_time > 3000:  # 3 second threshold
                    response.failure(f"Response too slow: {response_time:.0f}ms")
                else:
                    response.success()
                    
                    # Update conversation phase
                    self._update_conversation_phase(agent_response)
                    self.message_count += 1
                    
                    # End conversation after realistic number of messages
                    if self.message_count > random.randint(8, 15):
                        self.conversation_id = None
                        self.message_count = 0
                        self.conversation_phase = "greeting"
            else:
                response.failure(f"Message failed: {response.status_code}")
    
    @task(weight=10)
    def check_tier_detection(self):
        """Secondary task: Check tier detection."""
        if not self.conversation_id:
            return
        
        headers = self._get_headers()
        
        with self.client.get(
            f"/conversation/{self.conversation_id}/tier",
            headers=headers,
            catch_response=True,
            name="/conversation/[id]/tier"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                detected_tier = data.get("tier")
                if detected_tier in TEST_CONFIG["tiers"]:
                    response.success()
                else:
                    response.failure(f"Invalid tier detected: {detected_tier}")
            else:
                response.failure(f"Tier detection failed: {response.status_code}")
    
    @task(weight=10)
    def calculate_roi(self):
        """Secondary task: Calculate ROI."""
        if not self.customer_profile:
            return
        
        headers = self._get_headers()
        
        with self.client.post(
            "/predictive/roi-projection",
            json={
                "customer_profile": {
                    "age": self.customer_profile["age"],
                    "occupation": self.customer_profile["occupation"],
                    "goals": self.customer_profile["goals"]
                },
                "program_type": self.customer_profile["program_interest"],
                "tier": random.choice(TEST_CONFIG["tiers"])
            },
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "roi_projection" in data and "confidence" in data:
                    response.success()
                else:
                    response.failure("Invalid ROI response format")
            else:
                response.failure(f"ROI calculation failed: {response.status_code}")
    
    @task(weight=5)
    def get_analytics(self):
        """Secondary task: Get conversation analytics."""
        if not self.conversation_id:
            return
        
        headers = self._get_headers()
        
        with self.client.get(
            f"/analytics/conversation/{self.conversation_id}",
            headers=headers,
            catch_response=True,
            name="/analytics/conversation/[id]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Analytics failed: {response.status_code}")
    
    @task(weight=5)
    def health_check(self):
        """Monitoring task: Check system health."""
        with self.client.get(
            "/health",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    response.success()
                else:
                    response.failure("System unhealthy")
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    def on_stop(self):
        """Clean up when user stops."""
        # End any ongoing conversation
        if self.conversation_id:
            headers = self._get_headers()
            self.client.post(
                f"/conversation/{self.conversation_id}/end",
                headers=headers
            )


# Event handlers for statistics collection
@events.init.add_listener
def on_locust_init(environment: Environment, **kwargs):
    """Initialize test environment."""
    print("=" * 80)
    print("NGX Voice Sales Agent - Load Testing")
    print(f"Target Host: {environment.host}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


@events.test_start.add_listener
def on_test_start(environment: Environment, **kwargs):
    """Log test start."""
    print(f"\nStarting load test with {environment.runner.target_user_count} users")
    print(f"Spawn rate: {environment.runner.spawn_rate} users/second")


@events.test_stop.add_listener
def on_test_stop(environment: Environment, **kwargs):
    """Generate summary report."""
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    
    stats = environment.runner.stats
    
    print(f"\nTotal Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Average Response Time: {stats.total.avg_response_time:.0f}ms")
    print(f"Requests/sec: {stats.total.current_rps:.2f}")
    
    if stats.total.num_requests > 0:
        failure_rate = (stats.total.num_failures / stats.total.num_requests) * 100
        print(f"Failure Rate: {failure_rate:.2f}%")
    
    print("\nResponse Time Percentiles:")
    print(f"  50%: {stats.total.get_response_time_percentile(0.5):.0f}ms")
    print(f"  90%: {stats.total.get_response_time_percentile(0.9):.0f}ms")
    print(f"  95%: {stats.total.get_response_time_percentile(0.95):.0f}ms")
    print(f"  99%: {stats.total.get_response_time_percentile(0.99):.0f}ms")