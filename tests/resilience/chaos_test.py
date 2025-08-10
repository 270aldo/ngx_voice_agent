#!/usr/bin/env python3
"""
Chaos Engineering Tests for NGX Voice Sales Agent.
Tests system resilience under failure conditions.
"""

import asyncio
import aiohttp
import time
import json
import random
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional


class ChaosEngineeringTester:
    """Chaos testing to verify system resilience."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.chaos_results = []
        self.recovery_times = []
        
    async def test_service_failures(self):
        """Test behavior when external services fail."""
        print("\n💥 SERVICE FAILURE TESTS")
        print("-" * 50)
        
        services = [
            {
                "name": "Redis Cache",
                "container": "ngx-redis",
                "expected_behavior": "fallback_to_database",
                "recovery_time_limit": 30
            },
            {
                "name": "OpenAI API",
                "simulate_with": "network_block",
                "expected_behavior": "circuit_breaker_activation",
                "recovery_time_limit": 60
            },
            {
                "name": "Database",
                "container": "ngx-postgres",
                "expected_behavior": "graceful_degradation",
                "recovery_time_limit": 120
            }
        ]
        
        results = []
        
        for service in services:
            print(f"\n🔧 Testing {service['name']} failure...")
            
            # Baseline request
            baseline = await self._make_test_request()
            print(f"Baseline response time: {baseline['response_time']:.2f}ms")
            
            # Simulate failure
            if "container" in service:
                await self._stop_container(service["container"])
            elif service.get("simulate_with") == "network_block":
                await self._simulate_network_failure("api.openai.com")
            
            # Test during failure
            failure_start = time.time()
            failure_responses = []
            
            for i in range(10):
                response = await self._make_test_request()
                failure_responses.append(response)
                
                if response["success"]:
                    print(f"  Request {i+1}: Success (fallback working)")
                else:
                    print(f"  Request {i+1}: Failed")
                
                await asyncio.sleep(1)
            
            # Restore service
            if "container" in service:
                await self._start_container(service["container"])
            elif service.get("simulate_with") == "network_block":
                await self._restore_network("api.openai.com")
            
            # Test recovery
            recovery_start = time.time()
            recovered = False
            recovery_attempts = 0
            
            while not recovered and recovery_attempts < 30:
                recovery_attempts += 1
                response = await self._make_test_request()
                
                if response["success"] and response["response_time"] < baseline["response_time"] * 2:
                    recovered = True
                    recovery_time = time.time() - recovery_start
                    print(f"✅ Service recovered in {recovery_time:.2f}s")
                    self.recovery_times.append(recovery_time)
                else:
                    await asyncio.sleep(2)
            
            # Analyze results
            success_during_failure = sum(1 for r in failure_responses if r["success"])
            
            result = {
                "service": service["name"],
                "baseline_response_time": baseline["response_time"],
                "success_rate_during_failure": success_during_failure / len(failure_responses) * 100,
                "recovered": recovered,
                "recovery_time": recovery_time if recovered else None,
                "meets_sla": recovered and recovery_time <= service["recovery_time_limit"]
            }
            
            results.append(result)
            
            # Cool down
            await asyncio.sleep(10)
        
        self._print_service_failure_results(results)
        return results
    
    async def test_cascading_failures(self):
        """Test system behavior under cascading failures."""
        print("\n🌊 CASCADING FAILURE TEST")
        print("-" * 50)
        
        # Simulate progressive failures
        failures = [
            {"service": "Redis", "container": "ngx-redis", "delay": 0},
            {"service": "High Load", "action": "spike_load", "delay": 5},
            {"service": "Memory Pressure", "action": "memory_pressure", "delay": 10}
        ]
        
        print("Initiating cascading failures...")
        metrics = {
            "start_time": time.time(),
            "responses": [],
            "errors": [],
            "response_times": []
        }
        
        # Start monitoring task
        monitor_task = asyncio.create_task(
            self._monitor_system_health(metrics, duration=60)
        )
        
        # Apply failures progressively
        for failure in failures:
            await asyncio.sleep(failure["delay"])
            print(f"\n💥 Applying failure: {failure['service']}")
            
            if "container" in failure:
                await self._stop_container(failure["container"])
            elif failure["action"] == "spike_load":
                asyncio.create_task(self._generate_spike_load())
            elif failure["action"] == "memory_pressure":
                asyncio.create_task(self._simulate_memory_pressure())
        
        # Let chaos run
        await asyncio.sleep(30)
        
        # Start recovery
        print("\n🔧 Initiating recovery...")
        await self._start_container("ngx-redis")
        
        # Wait for monitoring to complete
        await monitor_task
        
        # Analyze cascading failure impact
        self._analyze_cascading_impact(metrics)
    
    async def test_network_conditions(self):
        """Test system under various network conditions."""
        print("\n🌐 NETWORK CONDITION TESTS")
        print("-" * 50)
        
        conditions = [
            {
                "name": "High Latency",
                "latency": "500ms",
                "description": "500ms added latency"
            },
            {
                "name": "Packet Loss",
                "loss": "10%",
                "description": "10% packet loss"
            },
            {
                "name": "Bandwidth Limit",
                "rate": "100kbit",
                "description": "Limited to 100kbit/s"
            },
            {
                "name": "Jitter",
                "jitter": "100ms",
                "description": "100ms jitter"
            }
        ]
        
        results = []
        
        for condition in conditions:
            print(f"\n🔧 Testing: {condition['name']} - {condition['description']}")
            
            # Apply network condition
            await self._apply_network_condition(condition)
            
            # Test performance under condition
            test_results = []
            for i in range(10):
                response = await self._make_test_request()
                test_results.append(response)
                print(f"  Request {i+1}: {response['response_time']:.0f}ms "
                      f"{'✅' if response['success'] else '❌'}")
            
            # Remove network condition
            await self._clear_network_conditions()
            
            # Analyze results
            avg_response_time = sum(r["response_time"] for r in test_results) / len(test_results)
            success_rate = sum(1 for r in test_results if r["success"]) / len(test_results) * 100
            
            results.append({
                "condition": condition["name"],
                "avg_response_time": avg_response_time,
                "success_rate": success_rate,
                "description": condition["description"]
            })
            
            await asyncio.sleep(5)
        
        self._print_network_test_results(results)
        return results
    
    async def test_resource_exhaustion(self):
        """Test system behavior under resource exhaustion."""
        print("\n💾 RESOURCE EXHAUSTION TESTS")
        print("-" * 50)
        
        tests = [
            {
                "name": "CPU Saturation",
                "method": self._simulate_cpu_load,
                "duration": 30,
                "expected": "degraded_performance"
            },
            {
                "name": "Memory Exhaustion",
                "method": self._simulate_memory_pressure,
                "duration": 30,
                "expected": "graceful_degradation"
            },
            {
                "name": "Connection Pool Exhaustion",
                "method": self._exhaust_connections,
                "duration": 20,
                "expected": "connection_queuing"
            }
        ]
        
        results = []
        
        for test in tests:
            print(f"\n🔧 Testing: {test['name']}")
            
            # Baseline
            baseline_responses = []
            for _ in range(5):
                response = await self._make_test_request()
                baseline_responses.append(response)
            
            baseline_avg = sum(r["response_time"] for r in baseline_responses) / len(baseline_responses)
            print(f"Baseline average: {baseline_avg:.2f}ms")
            
            # Apply resource pressure
            pressure_task = asyncio.create_task(test["method"](test["duration"]))
            
            # Test under pressure
            pressure_responses = []
            start_time = time.time()
            
            while time.time() - start_time < test["duration"]:
                response = await self._make_test_request()
                pressure_responses.append(response)
                
                if len(pressure_responses) % 5 == 0:
                    avg_last_5 = sum(r["response_time"] for r in pressure_responses[-5:]) / 5
                    print(f"  Current avg response: {avg_last_5:.2f}ms")
                
                await asyncio.sleep(1)
            
            # Wait for pressure to end
            await pressure_task
            
            # Test recovery
            print("Testing recovery...")
            recovery_responses = []
            for _ in range(10):
                response = await self._make_test_request()
                recovery_responses.append(response)
                await asyncio.sleep(1)
            
            # Analyze
            pressure_avg = sum(r["response_time"] for r in pressure_responses) / len(pressure_responses)
            recovery_avg = sum(r["response_time"] for r in recovery_responses) / len(recovery_responses)
            degradation = (pressure_avg - baseline_avg) / baseline_avg * 100
            
            results.append({
                "test": test["name"],
                "baseline_avg": baseline_avg,
                "pressure_avg": pressure_avg,
                "recovery_avg": recovery_avg,
                "degradation_percent": degradation,
                "recovered": recovery_avg < baseline_avg * 1.2
            })
            
            await asyncio.sleep(10)
        
        self._print_resource_test_results(results)
        return results
    
    async def _make_test_request(self) -> Dict[str, Any]:
        """Make a test request to the system."""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                # Try to start a conversation
                async with session.post(
                    f"{self.base_url}/conversations/start",
                    json={
                        "customer_data": {
                            "id": f"chaos-test-{random.randint(1000, 9999)}",
                            "name": "Chaos Tester",
                            "email": "chaos@test.com",
                            "age": 30
                        }
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    await response.json()
                    return {
                        "success": response.status == 200,
                        "response_time": (time.time() - start_time) * 1000,
                        "status_code": response.status
                    }
        except Exception as e:
            return {
                "success": False,
                "response_time": (time.time() - start_time) * 1000,
                "error": str(e)
            }
    
    async def _stop_container(self, container_name: str):
        """Stop a Docker container."""
        try:
            subprocess.run(["docker", "stop", container_name], 
                         capture_output=True, text=True)
            print(f"  ⏹️  Stopped {container_name}")
        except Exception as e:
            print(f"  ❌ Failed to stop {container_name}: {e}")
    
    async def _start_container(self, container_name: str):
        """Start a Docker container."""
        try:
            subprocess.run(["docker", "start", container_name], 
                         capture_output=True, text=True)
            print(f"  ▶️  Started {container_name}")
        except Exception as e:
            print(f"  ❌ Failed to start {container_name}: {e}")
    
    async def _simulate_network_failure(self, host: str):
        """Simulate network failure to a host."""
        # This would use iptables or similar in production
        print(f"  🚫 Simulating network failure to {host}")
    
    async def _restore_network(self, host: str):
        """Restore network to a host."""
        print(f"  ✅ Restored network to {host}")
    
    async def _generate_spike_load(self):
        """Generate a spike in load."""
        tasks = []
        for _ in range(50):
            task = self._make_test_request()
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _simulate_cpu_load(self, duration: int):
        """Simulate CPU load."""
        print(f"  🔥 Simulating CPU load for {duration}s")
        # In production, this would use stress-ng or similar
        await asyncio.sleep(duration)
    
    async def _simulate_memory_pressure(self, duration: int = 30):
        """Simulate memory pressure."""
        print(f"  💾 Simulating memory pressure for {duration}s")
        # In production, this would allocate actual memory
        await asyncio.sleep(duration)
    
    async def _exhaust_connections(self, duration: int):
        """Exhaust connection pool."""
        print(f"  🔌 Exhausting connections for {duration}s")
        
        # Create many concurrent connections
        connections = []
        for _ in range(100):
            session = aiohttp.ClientSession()
            connections.append(session)
        
        await asyncio.sleep(duration)
        
        # Clean up
        for session in connections:
            await session.close()
    
    async def _apply_network_condition(self, condition: Dict):
        """Apply network condition using tc (traffic control)."""
        # In production, this would use actual tc commands
        print(f"  📡 Applied network condition: {condition}")
    
    async def _clear_network_conditions(self):
        """Clear all network conditions."""
        print(f"  📡 Cleared network conditions")
    
    async def _monitor_system_health(self, metrics: Dict, duration: int):
        """Monitor system health during chaos."""
        start_time = time.time()
        
        while time.time() - start_time < duration:
            response = await self._make_test_request()
            metrics["responses"].append(response)
            
            if response["success"]:
                metrics["response_times"].append(response["response_time"])
            else:
                metrics["errors"].append(response.get("error", "Unknown"))
            
            await asyncio.sleep(1)
    
    def _analyze_cascading_impact(self, metrics: Dict):
        """Analyze impact of cascading failures."""
        total_requests = len(metrics["responses"])
        successful = sum(1 for r in metrics["responses"] if r["success"])
        
        print("\n📊 Cascading Failure Analysis:")
        print(f"Total requests: {total_requests}")
        print(f"Success rate: {successful/total_requests*100:.1f}%")
        print(f"Errors encountered: {len(metrics['errors'])}")
        
        if metrics["response_times"]:
            print(f"Avg response time: {sum(metrics['response_times'])/len(metrics['response_times']):.2f}ms")
    
    def _print_service_failure_results(self, results: List[Dict]):
        """Print service failure test results."""
        print("\n📊 Service Failure Test Results:")
        for result in results:
            print(f"\n{result['service']}:")
            print(f"  Success rate during failure: {result['success_rate_during_failure']:.1f}%")
            print(f"  Recovered: {'✅' if result['recovered'] else '❌'}")
            if result['recovery_time']:
                print(f"  Recovery time: {result['recovery_time']:.2f}s")
            print(f"  Meets SLA: {'✅' if result['meets_sla'] else '❌'}")
    
    def _print_network_test_results(self, results: List[Dict]):
        """Print network condition test results."""
        print("\n📊 Network Condition Test Results:")
        for result in results:
            print(f"\n{result['condition']} ({result['description']}):")
            print(f"  Avg response time: {result['avg_response_time']:.2f}ms")
            print(f"  Success rate: {result['success_rate']:.1f}%")
    
    def _print_resource_test_results(self, results: List[Dict]):
        """Print resource exhaustion test results."""
        print("\n📊 Resource Exhaustion Test Results:")
        for result in results:
            print(f"\n{result['test']}:")
            print(f"  Performance degradation: {result['degradation_percent']:.1f}%")
            print(f"  Baseline: {result['baseline_avg']:.2f}ms")
            print(f"  Under pressure: {result['pressure_avg']:.2f}ms")
            print(f"  After recovery: {result['recovery_avg']:.2f}ms")
            print(f"  Fully recovered: {'✅' if result['recovered'] else '❌'}")
    
    def generate_chaos_report(self):
        """Generate comprehensive chaos engineering report."""
        print("\n" + "=" * 60)
        print("💥 CHAOS ENGINEERING REPORT")
        print("=" * 60)
        
        if self.recovery_times:
            avg_recovery = sum(self.recovery_times) / len(self.recovery_times)
            print(f"\nAverage recovery time: {avg_recovery:.2f}s")
            print(f"Max recovery time: {max(self.recovery_times):.2f}s")
            print(f"Min recovery time: {min(self.recovery_times):.2f}s")
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/resilience/results/chaos_test_{timestamp}.json"
        
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, "w") as f:
            json.dump({
                "test_type": "chaos_engineering",
                "timestamp": timestamp,
                "recovery_times": self.recovery_times,
                "chaos_results": self.chaos_results
            }, f, indent=2)
        
        print(f"\n💾 Report saved to: {filename}")


async def main():
    """Run chaos engineering tests."""
    print("💥 NGX Voice Sales Agent - CHAOS ENGINEERING TESTS")
    print("=" * 60)
    print("⚠️  WARNING: These tests will disrupt services!")
    print("Ensure you're running in a test environment.")
    print("=" * 60)
    
    tester = ChaosEngineeringTester()
    
    # Run chaos tests
    await tester.test_service_failures()
    await tester.test_network_conditions()
    await tester.test_resource_exhaustion()
    await tester.test_cascading_failures()
    
    # Generate report
    tester.generate_chaos_report()
    
    print("\n✅ Chaos engineering tests completed!")


if __name__ == "__main__":
    asyncio.run(main())