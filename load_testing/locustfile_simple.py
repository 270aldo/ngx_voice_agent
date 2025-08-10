"""
Simplified Load Testing Configuration for NGX Voice Sales Agent.
"""

from locust import HttpUser, task, between
import random
import json


class NGXUser(HttpUser):
    """Simulates a user interacting with the NGX Voice Sales Agent API."""
    
    wait_time = between(1, 3)
    
    @task(1)
    def health_check(self):
        """Test health endpoint."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(5)
    def root_endpoint(self):
        """Test root endpoint."""
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(10)
    def api_docs(self):
        """Test API documentation endpoint."""
        with self.client.get("/docs", catch_response=True, name="API Docs") as response:
            if response.status_code in [200, 307]:  # 307 is redirect to /docs/
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(20)
    def simulate_conversation_start(self):
        """Simulate starting a conversation (will fail but tests load)."""
        conversation_data = {
            "customer_data": {
                "name": f"Test User {random.randint(1, 1000)}",
                "email": f"test{random.randint(1000, 9999)}@example.com",
                "profession": random.choice(["personal_trainer", "gym_owner", "fitness_coach"])
            },
            "context": {
                "source": "load_test"
            }
        }
        
        with self.client.post(
            "/api/v1/conversations/start",
            json=conversation_data,
            catch_response=True,
            name="Start Conversation (Expected 404)"
        ) as response:
            # We expect this to fail since we're using the simplified API
            if response.status_code == 404:
                response.success()  # Expected failure
            elif response.status_code == 200:
                response.success()  # If it works, great!
            else:
                response.failure(f"Unexpected status code {response.status_code}")
    
    @task(30)
    def simulate_message_send(self):
        """Simulate sending a message (will fail but tests load)."""
        messages = [
            "¿Cuáles son los precios de NGX?",
            "¿Cómo funciona el sistema?",
            "¿Puedo ver una demo?",
            "¿Qué incluye el plan básico?",
            "¿Cuál es el ROI esperado?"
        ]
        
        message_data = {
            "conversation_id": f"test-{random.randint(1000, 9999)}",
            "message": random.choice(messages)
        }
        
        with self.client.post(
            f"/api/v1/conversations/{message_data['conversation_id']}/messages",
            json=message_data,
            catch_response=True,
            name="Send Message (Expected 404)"
        ) as response:
            # We expect this to fail since we're using the simplified API
            if response.status_code == 404:
                response.success()  # Expected failure
            elif response.status_code == 200:
                response.success()  # If it works, great!
            else:
                response.failure(f"Unexpected status code {response.status_code}")