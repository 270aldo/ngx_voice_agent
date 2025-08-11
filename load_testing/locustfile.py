"""
Load Testing Configuration for NGX Voice Sales Agent.

This file contains load testing scenarios using Locust to simulate
realistic user behavior and test system performance under load.
"""

import random
import json
from locust import HttpUser, task, between
from datetime import datetime


class NGXSalesAgentUser(HttpUser):
    """Simulates a user interacting with the NGX Voice Sales Agent API."""
    
    # Wait between 1 and 3 seconds between tasks
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize user session."""
        # In a real scenario, this would authenticate and get a token
        self.conversation_id = None
        self.user_id = f"test_user_{random.randint(1000, 9999)}"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "NGX-LoadTest/1.0"
        }
    
    @task(1)
    def health_check(self):
        """Perform health check - low weight as this is not a primary user action."""
        self.client.get("/health", name="Health Check")
    
    @task(10)
    def start_conversation(self):
        """Start a new sales conversation - primary user action."""
        conversation_data = {
            "user_id": self.user_id,
            "customer_data": {
                "name": f"Test Customer {random.randint(1, 1000)}",
                "email": f"test{random.randint(1000, 9999)}@loadtest.com",
                "phone": f"+1555{random.randint(1000000, 9999999)}",
                "profession": random.choice([
                    "personal_trainer",
                    "gym_owner",
                    "fitness_coach",
                    "nutritionist",
                    "physical_therapist"
                ]),
                "age_range": random.choice(["25-34", "35-44", "45-54", "55+"]),
                "business_type": random.choice(["freelance", "studio", "gym", "online"])
            },
            "context": {
                "source": "load_test",
                "campaign": "performance_test",
                "referrer": "direct"
            }
        }
        
        response = self.client.post(
            "/api/v1/conversations/start",
            json=conversation_data,
            headers=self.headers,
            name="Start Conversation"
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("data"):
                self.conversation_id = data["data"].get("conversation_id")
    
    @task(20)
    def send_message(self):
        """Send a message in an ongoing conversation - most frequent action."""
        if not self.conversation_id:
            # If no conversation exists, start one first
            self.start_conversation()
            return
        
        # Simulate realistic user messages
        messages = [
            "Cuéntame más sobre NGX",
            "¿Cuáles son los precios?",
            "¿Cómo funciona el sistema HIE?",
            "¿Qué incluye el plan AGENTS ACCESS?",
            "¿Puedo ver una demo?",
            "¿Cuál es el ROI esperado?",
            "¿Cómo se integra con mi negocio actual?",
            "¿Qué tipo de soporte ofrecen?",
            "No estoy seguro si es para mí",
            "¿Hay algún descuento disponible?",
            "¿Cuánto tiempo lleva la implementación?",
            "¿Qué resultados han visto otros clientes?"
        ]
        
        message_data = {
            "conversation_id": self.conversation_id,
            "message": random.choice(messages),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = self.client.post(
            f"/api/v1/conversations/{self.conversation_id}/messages",
            json=message_data,
            headers=self.headers,
            name="Send Message"
        )
        
        if response.status_code != 200:
            # Reset conversation if error
            self.conversation_id = None
    
    @task(5)
    def get_conversation_state(self):
        """Check conversation state - moderate frequency."""
        if not self.conversation_id:
            return
        
        self.client.get(
            f"/api/v1/conversations/{self.conversation_id}/state",
            headers=self.headers,
            name="Get Conversation State"
        )
    
    @task(3)
    def get_recommendations(self):
        """Get program recommendations - occasional action."""
        if not self.conversation_id:
            return
        
        self.client.get(
            f"/api/v1/conversations/{self.conversation_id}/recommendations",
            headers=self.headers,
            name="Get Recommendations"
        )
    
    @task(2)
    def calculate_roi(self):
        """Calculate ROI - less frequent but important."""
        roi_data = {
            "profession": random.choice(["personal_trainer", "gym_owner"]),
            "current_clients": random.randint(10, 100),
            "average_ticket": random.randint(50, 200),
            "work_hours_per_week": random.randint(20, 60)
        }
        
        self.client.post(
            "/api/v1/analytics/roi/calculate",
            json=roi_data,
            headers=self.headers,
            name="Calculate ROI"
        )
    
    @task(1)
    def end_conversation(self):
        """End conversation - infrequent action."""
        if not self.conversation_id:
            return
        
        self.client.post(
            f"/api/v1/conversations/{self.conversation_id}/end",
            headers=self.headers,
            name="End Conversation"
        )
        
        # Reset for next conversation
        self.conversation_id = None
    
    def on_stop(self):
        """Clean up when user stops."""
        if self.conversation_id:
            # Try to end any open conversation
            self.client.post(
                f"/api/v1/conversations/{self.conversation_id}/end",
                headers=self.headers,
                catch_response=True
            )


class NGXAdminUser(HttpUser):
    """Simulates admin users checking analytics and system status."""
    
    wait_time = between(5, 10)  # Admins check less frequently
    
    def on_start(self):
        """Initialize admin session."""
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer admin-test-token"  # In real scenario, would authenticate
        }
    
    @task(5)
    def check_analytics_dashboard(self):
        """Check main analytics dashboard."""
        self.client.get(
            "/api/v1/analytics/dashboard",
            headers=self.headers,
            name="Analytics Dashboard"
        )
    
    @task(3)
    def get_conversion_metrics(self):
        """Get conversion metrics."""
        params = {
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "group_by": "day"
        }
        
        self.client.get(
            "/api/v1/analytics/conversions",
            params=params,
            headers=self.headers,
            name="Conversion Metrics"
        )
    
    @task(2)
    def check_system_health(self):
        """Check detailed system health."""
        self.client.get(
            "/api/v1/metrics/health",
            headers=self.headers,
            name="System Health"
        )
    
    @task(1)
    def get_active_conversations(self):
        """Get list of active conversations."""
        self.client.get(
            "/api/v1/analytics/conversations/active",
            headers=self.headers,
            name="Active Conversations"
        )


# Scenario definitions for different load patterns
class StandardLoadTest(HttpUser):
    """Standard load test mixing regular users and admins."""
    tasks = {NGXSalesAgentUser: 95, NGXAdminUser: 5}  # 95% users, 5% admins
    wait_time = between(1, 5)


class PeakLoadTest(HttpUser):
    """Peak load test simulating high traffic periods."""
    tasks = {NGXSalesAgentUser: 98, NGXAdminUser: 2}  # More users during peak
    wait_time = between(0.5, 2)  # Faster interactions


class StressTest(HttpUser):
    """Stress test to find system limits."""
    tasks = {NGXSalesAgentUser: 100}  # Only users, no admins
    wait_time = between(0.1, 1)  # Very fast interactions