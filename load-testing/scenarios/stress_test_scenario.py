"""
Stress Test Scenarios for NGX Voice Sales Agent.

This module implements various stress test scenarios to identify
system breaking points and performance bottlenecks.
"""

from locust import HttpUser, task, between, constant_pacing, LoadTestShape
from locust.env import Environment
import math
import random
from datetime import datetime, timedelta
from typing import Tuple, Optional

from ..locustfile import NGXVoiceSalesUser


class StressTestUser(NGXVoiceSalesUser):
    """
    Aggressive user behavior for stress testing.
    
    Simulates worst-case scenarios with rapid requests and
    complex conversation patterns.
    """
    
    # Minimal wait time for stress testing
    wait_time = between(0.5, 1.5)
    
    @task(weight=80)
    def rapid_fire_messages(self):
        """Send messages rapidly to stress the system."""
        # Send multiple messages in quick succession
        for _ in range(3):
            super().send_message()
    
    @task(weight=10)
    def concurrent_operations(self):
        """Perform multiple operations simultaneously."""
        # Tier detection + ROI calculation + Analytics
        self.schedule_task(self.check_tier_detection, first=True)
        self.schedule_task(self.calculate_roi, first=True)
        self.schedule_task(self.get_analytics, first=True)
    
    @task(weight=5)
    def complex_conversation(self):
        """Create conversations with complex requirements."""
        if not self.conversation_id:
            self._start_conversation()
        
        # Send a very long, complex message
        complex_message = f"""
        Hola, soy {self.customer_profile['name']} y tengo múltiples preguntas sobre su programa.
        Primero, trabajo como {self.customer_profile['occupation']} y tengo {self.customer_profile['age']} años.
        Mis objetivos son: {', '.join([self.customer_profile['goals']['primary']] + self.customer_profile['goals']['secondary'])}.
        
        Necesito saber:
        1. ¿Cuál es el precio exacto del programa {self.customer_profile['program_interest']}?
        2. ¿Qué incluye específicamente?
        3. ¿Cuánto tiempo dura?
        4. ¿Qué garantías ofrecen?
        5. ¿Puedo hablar con alguien que ya haya tomado el programa?
        
        Además, tengo algunas condiciones médicas que debo considerar y me gustaría saber si eso afecta el programa.
        También necesito opciones de financiamiento ya que mi presupuesto es limitado.
        
        Por favor, respóndeme de manera detallada a cada punto.
        """
        
        headers = self._get_headers()
        
        with self.client.post(
            f"/conversation/{self.conversation_id}/message",
            json={"message": complex_message},
            headers=headers,
            catch_response=True,
            name="/conversation/[id]/message-complex"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Complex message failed: {response.status_code}")
    
    @task(weight=5)
    def circuit_breaker_test(self):
        """Test circuit breaker behavior."""
        # Intentionally cause failures to test circuit breakers
        headers = self._get_headers()
        
        # Invalid conversation ID to trigger errors
        with self.client.post(
            "/conversation/invalid-id-12345/message",
            json={"message": "Test message"},
            headers=headers,
            catch_response=True,
            name="/conversation/invalid/message"
        ) as response:
            if response.status_code in [404, 500]:
                # Expected failures
                response.success()
            else:
                response.failure("Circuit breaker test unexpected response")


class SpikeLoadShape(LoadTestShape):
    """
    Spike load pattern to test sudden traffic increases.
    
    Simulates scenarios like marketing campaigns or viral content
    that cause sudden spikes in user traffic.
    """
    
    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 2},      # Warm-up
        {"duration": 120, "users": 50, "spawn_rate": 5},     # Normal load
        {"duration": 180, "users": 200, "spawn_rate": 50},   # Sudden spike!
        {"duration": 240, "users": 200, "spawn_rate": 0},    # Sustained high load
        {"duration": 300, "users": 50, "spawn_rate": 10},    # Recovery
        {"duration": 360, "users": 10, "spawn_rate": 2},     # Cool down
    ]
    
    def tick(self) -> Optional[Tuple[int, float]]:
        run_time = self.get_run_time()
        
        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]
        
        return None


class StepLoadShape(LoadTestShape):
    """
    Step load pattern for finding system limits.
    
    Gradually increases load to identify the exact point
    where performance starts degrading.
    """
    
    step_time = 60      # Time between steps (seconds)
    step_users = 20     # Users to add per step
    spawn_rate = 5      # Users per second spawn rate
    max_users = 200     # Maximum users to test
    
    def tick(self) -> Optional[Tuple[int, float]]:
        run_time = self.get_run_time()
        current_step = math.floor(run_time / self.step_time)
        target_users = min(current_step * self.step_users, self.max_users)
        
        if target_users < self.max_users or run_time < self.step_time * (self.max_users / self.step_users + 2):
            return target_users, self.spawn_rate
        
        return None


class RealisticLoadShape(LoadTestShape):
    """
    Realistic daily traffic pattern.
    
    Simulates a typical day with morning ramp-up,
    lunch spike, afternoon steady state, and evening decline.
    """
    
    def tick(self) -> Optional[Tuple[int, float]]:
        run_time = self.get_run_time()
        
        # Simulate 12-hour day compressed into test duration
        hour_in_day = (run_time % 720) / 60  # 720 seconds = 12 minutes = 12 hours
        
        # User count based on time of day
        if hour_in_day < 1:  # Early morning
            target_users = 10
        elif hour_in_day < 3:  # Morning ramp-up
            target_users = int(10 + (hour_in_day - 1) * 45)
        elif hour_in_day < 5:  # Morning peak
            target_users = 100
        elif hour_in_day < 6:  # Lunch spike
            target_users = 150
        elif hour_in_day < 9:  # Afternoon steady
            target_users = 80
        elif hour_in_day < 11:  # Evening decline
            target_users = int(80 - (hour_in_day - 9) * 35)
        else:  # Night
            target_users = 10
        
        return target_users, 5.0


class CacheStressUser(NGXVoiceSalesUser):
    """
    User behavior designed to stress test caching layers.
    
    Alternates between cache hits and misses to verify
    cache performance and fallback mechanisms.
    """
    
    wait_time = constant_pacing(1)  # Consistent pace for cache testing
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conversation_cache = []  # Store conversation IDs for reuse
    
    @task(weight=40)
    def cache_hit_scenario(self):
        """Generate requests that should hit cache."""
        # Reuse conversation IDs to trigger cache hits
        if self.conversation_cache:
            cached_id = random.choice(self.conversation_cache)
            headers = self._get_headers()
            
            # These should be cached
            with self.client.get(
                f"/conversation/{cached_id}/summary",
                headers=headers,
                catch_response=True,
                name="/conversation/[id]/summary-cached"
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Cache hit failed: {response.status_code}")
    
    @task(weight=40)
    def cache_miss_scenario(self):
        """Generate requests that should miss cache."""
        # Create new conversations for cache misses
        self._start_conversation()
        if self.conversation_id and self.conversation_id not in self.conversation_cache:
            self.conversation_cache.append(self.conversation_id)
            # Limit cache size to prevent memory issues
            if len(self.conversation_cache) > 100:
                self.conversation_cache.pop(0)
    
    @task(weight=20)
    def cache_invalidation_test(self):
        """Test cache invalidation scenarios."""
        if self.conversation_id:
            # Update conversation to invalidate cache
            headers = self._get_headers()
            
            with self.client.put(
                f"/conversation/{self.conversation_id}/update",
                json={"metadata": {"cache_test": str(datetime.now())}},
                headers=headers,
                catch_response=True,
                name="/conversation/[id]/update"
            ) as response:
                if response.status_code in [200, 204]:
                    response.success()
                else:
                    response.failure(f"Cache invalidation failed: {response.status_code}")


class CircuitBreakerTestUser(NGXVoiceSalesUser):
    """
    User behavior to specifically test circuit breaker functionality.
    
    Generates patterns of failures to verify circuit breaker
    opens, closes, and provides appropriate fallbacks.
    """
    
    wait_time = between(0.5, 1)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failure_mode = False
        self.failure_count = 0
    
    @task(weight=70)
    def normal_operation(self):
        """Normal requests when not in failure mode."""
        if not self.failure_mode:
            super().send_message()
    
    @task(weight=20)
    def trigger_failures(self):
        """Trigger failures to open circuit breakers."""
        if random.random() < 0.1:  # 10% chance to enter failure mode
            self.failure_mode = True
            self.failure_count = 0
        
        if self.failure_mode:
            headers = self._get_headers()
            
            # Simulate API timeout (longer than circuit breaker timeout)
            with self.client.post(
                "/conversation/timeout-test",
                json={"delay": 10000},  # 10 second delay
                headers=headers,
                timeout=1,  # 1 second timeout
                catch_response=True,
                name="/conversation/timeout-test"
            ) as response:
                self.failure_count += 1
                
                # After 5 failures, circuit should be open
                if self.failure_count >= 5:
                    if response.status_code == 503:  # Circuit open response
                        response.success()
                        self.failure_mode = False  # Exit failure mode
                    else:
                        response.failure("Circuit breaker didn't open")
                else:
                    response.failure("Intentional timeout failure")
    
    @task(weight=10)
    def test_fallback_responses(self):
        """Verify fallback responses work correctly."""
        headers = self._get_headers()
        
        # Request that should trigger fallback
        with self.client.post(
            "/conversation/force-fallback",
            json={"test_fallback": True},
            headers=headers,
            catch_response=True,
            name="/conversation/fallback-test"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "_fallback" in data:
                    response.success()
                else:
                    response.failure("No fallback indicator in response")
            else:
                response.failure(f"Fallback test failed: {response.status_code}")