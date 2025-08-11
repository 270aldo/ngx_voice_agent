#!/usr/bin/env python3
"""
Circuit breaker resilience tests for NGX Voice Sales Agent.
Tests system behavior under simulated failures of external services.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import os

class CircuitBreakerTest:
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.results = {
            "openai_tests": [],
            "elevenlabs_tests": [],
            "redis_tests": [],
            "database_tests": []
        }
        
    async def create_test_payload(self) -> Dict[str, Any]:
        """Create test conversation payload."""
        return {
            "message": "Hola, quiero mejorar mi salud y fitness",
            "user_id": f"circuit_test_{int(time.time())}",
            "session_id": f"session_{int(time.time())}",
            "customer_data": {
                "nombre": "TestUser",
                "edad": 30,
                "profesion": "Developer",
                "experiencia_fitness": "principiante",
                "objetivos": ["perder_peso"],
                "presupuesto": "bajo"
            }
        }
    
    async def test_openai_failure(self):
        """Test circuit breaker behavior when OpenAI fails."""
        print("\n🧪 Testing OpenAI Circuit Breaker...")
        
        test_scenarios = [
            {
                "name": "Normal Operation",
                "simulate_failure": False,
                "expected_behavior": "success"
            },
            {
                "name": "Service Timeout",
                "simulate_failure": True,
                "failure_type": "timeout",
                "expected_behavior": "fallback_response"
            },
            {
                "name": "API Error",
                "simulate_failure": True,
                "failure_type": "api_error",
                "expected_behavior": "cached_response_or_fallback"
            },
            {
                "name": "Circuit Open",
                "simulate_failure": True,
                "failure_type": "multiple_failures",
                "expected_behavior": "immediate_fallback"
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n  📌 Scenario: {scenario['name']}")
            
            # Prepare headers for failure simulation
            headers = {}
            if scenario.get("simulate_failure"):
                headers["X-Test-Simulate-Failure"] = scenario["failure_type"]
                headers["X-Test-Service"] = "openai"
            
            start_time = time.time()
            
            try:
                async with aiohttp.ClientSession() as session:
                    payload = await self.create_test_payload()
                    
                    # Make multiple requests to trigger circuit breaker
                    responses = []
                    for i in range(6):  # More than failure threshold
                        async with session.post(
                            f"{self.api_url}/api/v1/conversation",
                            json=payload,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            response_data = {
                                "status": response.status,
                                "time": time.time() - start_time,
                                "headers": dict(response.headers),
                                "body": await response.json() if response.status == 200 else await response.text()
                            }
                            responses.append(response_data)
                            
                            # Small delay between requests
                            await asyncio.sleep(0.5)
                    
                    # Analyze results
                    result = {
                        "scenario": scenario["name"],
                        "responses": responses,
                        "circuit_opened": any(r.get("headers", {}).get("X-Circuit-Breaker-Status") == "OPEN" for r in responses),
                        "fallback_used": any("fallback" in str(r.get("body", "")).lower() for r in responses),
                        "all_successful": all(r["status"] == 200 for r in responses)
                    }
                    
                    self.results["openai_tests"].append(result)
                    
                    # Print summary
                    if result["circuit_opened"]:
                        print(f"    ✅ Circuit breaker opened after failures")
                    if result["fallback_used"]:
                        print(f"    ✅ Fallback responses provided")
                    if result["all_successful"]:
                        print(f"    ✅ All requests handled gracefully")
                    
            except Exception as e:
                print(f"    ❌ Test failed: {e}")
                self.results["openai_tests"].append({
                    "scenario": scenario["name"],
                    "error": str(e)
                })
    
    async def test_elevenlabs_failure(self):
        """Test circuit breaker behavior when ElevenLabs fails."""
        print("\n🧪 Testing ElevenLabs Circuit Breaker...")
        
        # Test voice synthesis endpoint
        test_cases = [
            {
                "name": "Voice Synthesis - Normal",
                "endpoint": "/api/v1/voice/synthesize",
                "payload": {"text": "Hola, bienvenido a NGX"},
                "simulate_failure": False
            },
            {
                "name": "Voice Synthesis - Service Down",
                "endpoint": "/api/v1/voice/synthesize",
                "payload": {"text": "Test message"},
                "simulate_failure": True,
                "failure_type": "service_unavailable"
            }
        ]
        
        for test in test_cases:
            print(f"\n  📌 Test: {test['name']}")
            
            headers = {}
            if test.get("simulate_failure"):
                headers["X-Test-Simulate-Failure"] = test["failure_type"]
                headers["X-Test-Service"] = "elevenlabs"
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.api_url}{test['endpoint']}",
                        json=test["payload"],
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        result = {
                            "test": test["name"],
                            "status": response.status,
                            "headers": dict(response.headers),
                            "fallback_audio": response.headers.get("X-Fallback-Audio") == "true"
                        }
                        
                        self.results["elevenlabs_tests"].append(result)
                        
                        if response.status == 200:
                            if result["fallback_audio"]:
                                print(f"    ✅ Fallback audio provided")
                            else:
                                print(f"    ✅ Normal audio synthesis")
                        else:
                            print(f"    ❌ Request failed: {response.status}")
                            
            except Exception as e:
                print(f"    ❌ Test error: {e}")
                self.results["elevenlabs_tests"].append({
                    "test": test["name"],
                    "error": str(e)
                })
    
    async def test_redis_failure(self):
        """Test system behavior when Redis cache fails."""
        print("\n🧪 Testing Redis Failure Resilience...")
        
        # Test cache-dependent operations
        test_operations = [
            {
                "name": "Conversation with Cache Down",
                "endpoint": "/api/v1/conversation",
                "method": "POST",
                "description": "Should fall back to database"
            },
            {
                "name": "Analytics with Cache Down",
                "endpoint": "/api/v1/analytics/conversation/test_id",
                "method": "GET",
                "description": "Should compute from database"
            }
        ]
        
        for op in test_operations:
            print(f"\n  📌 Operation: {op['name']}")
            print(f"     Expected: {op['description']}")
            
            headers = {
                "X-Test-Simulate-Failure": "connection_error",
                "X-Test-Service": "redis"
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    if op["method"] == "POST":
                        payload = await self.create_test_payload()
                        async with session.post(
                            f"{self.api_url}{op['endpoint']}",
                            json=payload,
                            headers=headers
                        ) as response:
                            status = response.status
                            cache_status = response.headers.get("X-Cache-Status", "unknown")
                    else:
                        async with session.get(
                            f"{self.api_url}{op['endpoint']}",
                            headers=headers
                        ) as response:
                            status = response.status
                            cache_status = response.headers.get("X-Cache-Status", "unknown")
                    
                    result = {
                        "operation": op["name"],
                        "status": status,
                        "cache_status": cache_status,
                        "success": status in [200, 404]  # 404 is ok for missing analytics
                    }
                    
                    self.results["redis_tests"].append(result)
                    
                    if result["success"]:
                        print(f"    ✅ Operation succeeded without cache")
                        if cache_status == "bypass":
                            print(f"    ✅ Cache properly bypassed")
                    else:
                        print(f"    ❌ Operation failed: {status}")
                        
            except Exception as e:
                print(f"    ❌ Test error: {e}")
                self.results["redis_tests"].append({
                    "operation": op["name"],
                    "error": str(e)
                })
    
    async def test_cascade_failures(self):
        """Test system behavior under multiple simultaneous failures."""
        print("\n🧪 Testing Cascade Failure Scenarios...")
        
        scenarios = [
            {
                "name": "OpenAI + Redis Down",
                "failures": ["openai", "redis"],
                "expected": "Fallback responses without caching"
            },
            {
                "name": "All External Services Down",
                "failures": ["openai", "elevenlabs", "redis"],
                "expected": "Graceful degradation with basic responses"
            }
        ]
        
        for scenario in scenarios:
            print(f"\n  📌 Scenario: {scenario['name']}")
            print(f"     Expected: {scenario['expected']}")
            
            headers = {
                "X-Test-Simulate-Failure": "multiple",
                "X-Test-Failed-Services": ",".join(scenario["failures"])
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    payload = await self.create_test_payload()
                    
                    async with session.post(
                        f"{self.api_url}/api/v1/conversation",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as response:
                        result = {
                            "scenario": scenario["name"],
                            "status": response.status,
                            "degraded_mode": response.headers.get("X-Degraded-Mode") == "true",
                            "services_available": response.headers.get("X-Services-Available", "")
                        }
                        
                        if response.status == 200:
                            body = await response.json()
                            result["response_type"] = body.get("metadata", {}).get("response_type", "unknown")
                        
                        self.results["database_tests"].append(result)
                        
                        if result["status"] == 200:
                            print(f"    ✅ System remained operational")
                            if result["degraded_mode"]:
                                print(f"    ✅ Degraded mode activated")
                            print(f"    📊 Available services: {result['services_available']}")
                        else:
                            print(f"    ❌ System failed: {result['status']}")
                            
            except Exception as e:
                print(f"    ❌ Test error: {e}")
                self.results["database_tests"].append({
                    "scenario": scenario["name"],
                    "error": str(e)
                })
    
    async def test_recovery(self):
        """Test circuit breaker recovery after failures."""
        print("\n🧪 Testing Circuit Breaker Recovery...")
        
        # Simulate failure then recovery
        headers_fail = {
            "X-Test-Simulate-Failure": "api_error",
            "X-Test-Service": "openai"
        }
        
        print("\n  📌 Phase 1: Triggering failures...")
        
        async with aiohttp.ClientSession() as session:
            # Trigger failures
            for i in range(6):
                try:
                    payload = await self.create_test_payload()
                    async with session.post(
                        f"{self.api_url}/api/v1/conversation",
                        json=payload,
                        headers=headers_fail,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        print(f"    Request {i+1}: {response.status}")
                except:
                    print(f"    Request {i+1}: Failed")
                
                await asyncio.sleep(0.5)
            
            print("\n  📌 Phase 2: Waiting for recovery timeout...")
            await asyncio.sleep(5)  # Wait for partial recovery
            
            print("\n  📌 Phase 3: Testing recovery...")
            
            # Test without failure simulation
            recovery_results = []
            for i in range(3):
                try:
                    payload = await self.create_test_payload()
                    async with session.post(
                        f"{self.api_url}/api/v1/conversation",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        circuit_status = response.headers.get("X-Circuit-Breaker-Status", "UNKNOWN")
                        recovery_results.append({
                            "attempt": i+1,
                            "status": response.status,
                            "circuit_status": circuit_status
                        })
                        print(f"    Recovery attempt {i+1}: {response.status} (Circuit: {circuit_status})")
                except Exception as e:
                    print(f"    Recovery attempt {i+1}: Failed - {e}")
                
                await asyncio.sleep(2)
            
            # Check if recovery successful
            if any(r["status"] == 200 and r["circuit_status"] != "OPEN" for r in recovery_results):
                print("\n    ✅ Circuit breaker recovered successfully!")
            else:
                print("\n    ❌ Circuit breaker recovery failed")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": sum(len(v) for v in self.results.values()),
                "services_tested": list(self.results.keys()),
                "resilience_score": 0
            },
            "detailed_results": self.results,
            "recommendations": []
        }
        
        # Calculate resilience score
        total_tests = 0
        successful_tests = 0
        
        for service, tests in self.results.items():
            for test in tests:
                total_tests += 1
                if isinstance(test, dict) and not test.get("error"):
                    if test.get("status") == 200 or test.get("success") or test.get("all_successful"):
                        successful_tests += 1
        
        report["summary"]["resilience_score"] = (successful_tests / max(1, total_tests)) * 100
        
        # Add recommendations
        if report["summary"]["resilience_score"] < 80:
            report["recommendations"].append("Consider improving fallback mechanisms")
        
        if any("error" in str(test) for tests in self.results.values() for test in tests):
            report["recommendations"].append("Review error handling in circuit breakers")
        
        return report
    
    async def run(self):
        """Run all circuit breaker tests."""
        print("""
============================================================
🔌 NGX Voice Sales Agent - Circuit Breaker Tests
Testing resilience under external service failures
============================================================
        """)
        
        # Check API health first
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/health") as response:
                    if response.status != 200:
                        print("❌ API is not healthy!")
                        return
                    print("✅ API is healthy\n")
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            return
        
        # Run all tests
        await self.test_openai_failure()
        await self.test_elevenlabs_failure()
        await self.test_redis_failure()
        await self.test_cascade_failures()
        await self.test_recovery()
        
        # Generate report
        report = self.generate_report()
        
        print(f"""
============================================================
📊 CIRCUIT BREAKER TEST RESULTS
============================================================
Total Tests: {report['summary']['total_tests']}
Resilience Score: {report['summary']['resilience_score']:.1f}%

Services Tested:
""")
        for service in report['summary']['services_tested']:
            test_count = len(report['detailed_results'][service])
            print(f"  - {service}: {test_count} tests")
        
        if report['recommendations']:
            print("\n💡 Recommendations:")
            for rec in report['recommendations']:
                print(f"  - {rec}")
        
        # Save detailed report
        os.makedirs("results", exist_ok=True)
        report_file = f"results/circuit_breaker_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {report_file}")
        
        if report['summary']['resilience_score'] >= 90:
            print("\n🎉 Excellent resilience! System handles failures gracefully.")
        elif report['summary']['resilience_score'] >= 70:
            print("\n✅ Good resilience with minor improvements needed.")
        else:
            print("\n⚠️  Resilience needs improvement.")


async def main():
    test = CircuitBreakerTest()
    await test.run()


if __name__ == "__main__":
    asyncio.run(main())