"""
Load Testing Suite for NGX Voice Sales Agent

Simulates 1000+ concurrent users to validate performance under stress.
Target: <500ms response time for 95% of requests with cache system.
"""

import asyncio
import time
import random
import statistics
from typing import List, Dict, Any, Tuple
from datetime import datetime
import aiohttp
import json
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class LoadTestResult:
    """Result of a single request."""
    user_id: int
    request_id: int
    start_time: float
    end_time: float
    response_time_ms: float
    status_code: int
    cache_level: str
    error: str = None
    
    @property
    def success(self) -> bool:
        return self.status_code == 200 and self.error is None


class LoadTestRunner:
    """Orchestrates load testing with concurrent users."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[LoadTestResult] = []
        self.conversation_endpoint = f"{base_url}/api/v1/conversation/message"
        self.health_endpoint = f"{base_url}/health"
        
        # Realistic conversation scenarios
        self.conversation_scenarios = [
            # Pricing inquiries (should hit instant cache)
            [
                "Hola, cuanto cuesta NGX?",
                "Es muy caro para mi",
                "Hay algun descuento disponible?",
                "Ok, dejame pensarlo"
            ],
            # Feature questions (should hit pre-computed cache)
            [
                "Que es NGX exactamente?",
                "Como funciona el sistema?",
                "Que incluye el programa?",
                "Cuales son los beneficios?"
            ],
            # Objection handling
            [
                "No tengo tiempo para esto",
                "Ya tengo un sistema similar",
                "No creo que funcione para mi",
                "Necesito ver resultados primero"
            ],
            # High-intent conversation
            [
                "Estoy interesado en mejorar mi productividad",
                "Cuanto tiempo toma ver resultados?",
                "Como me inscribo?",
                "Puedo empezar hoy mismo?"
            ],
            # Technical questions
            [
                "Es compatible con mi telefono?",
                "Necesito internet todo el tiempo?",
                "Puedo cancelar cuando quiera?",
                "Hay garantia de devolucion?"
            ]
        ]
    
    async def check_health(self) -> bool:
        """Check if the service is healthy before testing."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.health_endpoint) as response:
                    return response.status == 200
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
    
    async def simulate_user_conversation(
        self, 
        user_id: int, 
        session: aiohttp.ClientSession
    ) -> List[LoadTestResult]:
        """Simulate a complete user conversation."""
        results = []
        
        # Select random scenario
        scenario = random.choice(self.conversation_scenarios)
        conversation_id = f"load_test_{user_id}_{int(time.time())}"
        
        # Add some randomness to message timing
        for request_id, message in enumerate(scenario):
            # Random delay between messages (0.5-2 seconds)
            if request_id > 0:
                await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # Prepare request
            payload = {
                "conversation_id": conversation_id,
                "message": message,
                "customer_data": {
                    "id": f"test_user_{user_id}",
                    "name": f"Test User {user_id}",
                    "email": f"user{user_id}@test.com",
                    "initial_message": message if request_id == 0 else None
                },
                "platform_context": {
                    "source": "load_test",
                    "device_type": random.choice(["mobile", "desktop"]),
                    "test_mode": True
                }
            }
            
            # Make request
            start_time = time.time()
            result = LoadTestResult(
                user_id=user_id,
                request_id=request_id,
                start_time=start_time,
                end_time=0,
                response_time_ms=0,
                status_code=0,
                cache_level="unknown"
            )
            
            try:
                async with session.post(
                    self.conversation_endpoint,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    end_time = time.time()
                    response_data = await response.json()
                    
                    result.end_time = end_time
                    result.response_time_ms = (end_time - start_time) * 1000
                    result.status_code = response.status
                    
                    # Extract cache level from response
                    cache_metadata = response_data.get("_cache_metadata", {})
                    result.cache_level = cache_metadata.get("cache_level", "computed")
                    
            except asyncio.TimeoutError:
                result.error = "Timeout after 5 seconds"
                result.end_time = time.time()
                result.response_time_ms = 5000
            except Exception as e:
                result.error = str(e)
                result.end_time = time.time()
                result.response_time_ms = (result.end_time - result.start_time) * 1000
            
            results.append(result)
        
        return results
    
    async def run_load_test(
        self, 
        num_users: int = 1000,
        ramp_up_seconds: int = 30
    ) -> Dict[str, Any]:
        """Run the load test with specified number of users."""
        print(f"Starting load test with {num_users} users...")
        print(f"Ramp-up period: {ramp_up_seconds} seconds")
        
        # Check health first
        if not await self.check_health():
            return {"error": "Service health check failed"}
        
        # Calculate delay between user starts
        delay_between_users = ramp_up_seconds / num_users
        
        # Create session with connection pooling
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=100)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Start users with ramp-up
            tasks = []
            for user_id in range(num_users):
                # Start user conversation
                task = asyncio.create_task(
                    self.simulate_user_conversation(user_id, session)
                )
                tasks.append(task)
                
                # Ramp-up delay
                if user_id < num_users - 1:
                    await asyncio.sleep(delay_between_users)
                
                # Progress update
                if (user_id + 1) % 100 == 0:
                    print(f"Started {user_id + 1} users...")
            
            # Wait for all conversations to complete
            print("All users started. Waiting for conversations to complete...")
            all_results = await asyncio.gather(*tasks)
            
            # Flatten results
            for user_results in all_results:
                self.results.extend(user_results)
        
        return self.analyze_results()
    
    def analyze_results(self) -> Dict[str, Any]:
        """Analyze load test results."""
        if not self.results:
            return {"error": "No results to analyze"}
        
        # Basic metrics
        total_requests = len(self.results)
        successful_requests = [r for r in self.results if r.success]
        failed_requests = [r for r in self.results if not r.success]
        
        success_rate = len(successful_requests) / total_requests * 100
        
        # Response time analysis (only for successful requests)
        if successful_requests:
            response_times = [r.response_time_ms for r in successful_requests]
            response_times.sort()
            
            metrics = {
                "min": response_times[0],
                "max": response_times[-1],
                "mean": statistics.mean(response_times),
                "median": statistics.median(response_times),
                "p95": response_times[int(len(response_times) * 0.95)],
                "p99": response_times[int(len(response_times) * 0.99)]
            }
        else:
            metrics = {}
        
        # Cache performance
        cache_distribution = defaultdict(int)
        cache_response_times = defaultdict(list)
        
        for result in successful_requests:
            cache_distribution[result.cache_level] += 1
            cache_response_times[result.cache_level].append(result.response_time_ms)
        
        # Calculate cache metrics
        cache_metrics = {}
        for cache_level, times in cache_response_times.items():
            if times:
                cache_metrics[cache_level] = {
                    "count": len(times),
                    "avg_ms": statistics.mean(times),
                    "percentage": len(times) / len(successful_requests) * 100
                }
        
        # Error analysis
        error_types = defaultdict(int)
        for result in failed_requests:
            error_types[result.error or "Unknown"] += 1
        
        # Time-based analysis (requests per second)
        if self.results:
            start_time = min(r.start_time for r in self.results)
            end_time = max(r.end_time for r in self.results)
            duration_seconds = end_time - start_time
            rps = total_requests / duration_seconds
        else:
            duration_seconds = 0
            rps = 0
        
        # Final report
        report = {
            "summary": {
                "total_requests": total_requests,
                "successful_requests": len(successful_requests),
                "failed_requests": len(failed_requests),
                "success_rate": f"{success_rate:.2f}%",
                "duration_seconds": f"{duration_seconds:.2f}",
                "requests_per_second": f"{rps:.2f}"
            },
            "response_times_ms": metrics,
            "cache_performance": cache_metrics,
            "errors": dict(error_types),
            "sla_compliance": {
                "target_p95_ms": 500,
                "actual_p95_ms": metrics.get("p95", 0),
                "compliant": metrics.get("p95", float('inf')) <= 500
            }
        }
        
        return report
    
    def print_report(self, report: Dict[str, Any]):
        """Print a formatted report of the results."""
        print("\n" + "="*60)
        print("LOAD TEST REPORT")
        print("="*60)
        
        # Summary
        print("\n📊 SUMMARY:")
        for key, value in report["summary"].items():
            print(f"  {key}: {value}")
        
        # Response times
        print("\n⏱️  RESPONSE TIMES (ms):")
        for key, value in report["response_times_ms"].items():
            print(f"  {key}: {value:.2f}")
        
        # Cache performance
        print("\n💾 CACHE PERFORMANCE:")
        for cache_level, metrics in report["cache_performance"].items():
            print(f"  {cache_level}:")
            print(f"    - Requests: {metrics['count']} ({metrics['percentage']:.1f}%)")
            print(f"    - Avg time: {metrics['avg_ms']:.2f}ms")
        
        # Errors
        if report["errors"]:
            print("\n❌ ERRORS:")
            for error_type, count in report["errors"].items():
                print(f"  {error_type}: {count}")
        
        # SLA Compliance
        print("\n✅ SLA COMPLIANCE:")
        sla = report["sla_compliance"]
        status = "PASS ✅" if sla["compliant"] else "FAIL ❌"
        print(f"  Target P95: {sla['target_p95_ms']}ms")
        print(f"  Actual P95: {sla['actual_p95_ms']:.2f}ms")
        print(f"  Status: {status}")
        
        print("\n" + "="*60)


async def main():
    """Run the load test."""
    runner = LoadTestRunner()
    
    # Test configurations
    test_configs = [
        {"name": "Warmup", "users": 10, "ramp_up": 5},
        {"name": "Standard Load", "users": 100, "ramp_up": 10},
        {"name": "High Load", "users": 500, "ramp_up": 30},
        {"name": "Stress Test", "users": 1000, "ramp_up": 60}
    ]
    
    for config in test_configs:
        print(f"\n🚀 Running {config['name']} test...")
        report = await runner.run_load_test(
            num_users=config["users"],
            ramp_up_seconds=config["ramp_up"]
        )
        runner.print_report(report)
        
        # Reset results for next test
        runner.results = []
        
        # Cool down period between tests
        if config != test_configs[-1]:
            print("\n⏳ Cooling down for 10 seconds...")
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())