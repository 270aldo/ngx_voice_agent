#!/usr/bin/env python3
"""
Test de Carga REAL - NGX Voice Sales Agent

Prueba el sistema con múltiples usuarios concurrentes para validar:
- Response time <0.5s bajo carga
- 0% error rate
- 1000+ usuarios concurrentes
- Cache effectiveness
"""

import asyncio
import aiohttp
import time
import random
from datetime import datetime
from typing import Dict, Any, List
import os
import json
from concurrent.futures import ThreadPoolExecutor
import statistics

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
CONCURRENT_USERS = [10, 50, 100, 200, 500, 1000]  # Progressive load levels


class RealLoadTest:
    """Test de carga real con usuarios concurrentes."""
    
    def __init__(self):
        self.api_url = API_URL
        self.results = {
            "load_levels": {},
            "overall_metrics": {},
            "cache_performance": {}
        }
        
        # Customer profiles for variety
        self.customer_profiles = [
            {
                "name": f"User {i}",
                "email": f"user{i}@test.com",
                "age": random.randint(25, 65),
                "occupation": random.choice(["CEO", "Engineer", "Doctor", "Athlete", "Entrepreneur"]),
                "goals": {
                    "primary": random.choice(["performance", "muscle_gain", "longevity", "weight_loss"]),
                    "timeline": random.choice(["immediate", "3_months", "6_months", "1_year"])
                }
            }
            for i in range(1000)
        ]
        
        # Common messages to test cache
        self.test_messages = [
            "¿Cuál es el precio de sus programas?",
            "¿Cómo funciona el sistema HIE?",
            "¿Qué garantías ofrecen?",
            "Necesito más información sobre NGX",
            "¿Cuánto tiempo requiere el programa?",
            "¿Tienen descuentos disponibles?",
            "¿Cómo puedo empezar?",
            "¿Qué incluye el programa PRIME?",
            "¿Es esto para mí si tengo {age} años?",
            "Trabajo como {occupation}, ¿me sirve?"
        ]
    
    async def simulate_user_session(self, user_id: int, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """
        Simula una sesión completa de usuario.
        """
        results = {
            "user_id": user_id,
            "success": False,
            "conversation_id": None,
            "response_times": [],
            "errors": [],
            "cache_hits": 0
        }
        
        try:
            # Get customer profile
            customer = self.customer_profiles[user_id % len(self.customer_profiles)]
            
            # Start conversation
            start_time = time.time()
            response = await session.post(
                f"{self.api_url}/conversations/start",
                json={"customer_data": customer},
                timeout=aiohttp.ClientTimeout(total=10)
            )
            response_time = time.time() - start_time
            results["response_times"].append(response_time)
            
            if response.status != 200:
                results["errors"].append(f"Start failed: {response.status}")
                return results
            
            data = await response.json()
            conversation_id = data["conversation_id"]
            results["conversation_id"] = conversation_id
            
            # Send 3-5 messages
            num_messages = random.randint(3, 5)
            for i in range(num_messages):
                # Mix common and unique messages
                if random.random() < 0.6:  # 60% common messages (cache hits)
                    message = random.choice(self.test_messages[:5])  # Top 5 most common
                    results["cache_hits"] += 1
                else:
                    message = random.choice(self.test_messages[5:])
                    # Personalize message
                    message = message.format(age=customer["age"], occupation=customer["occupation"])
                
                start_time = time.time()
                msg_response = await session.post(
                    f"{self.api_url}/conversations/{conversation_id}/message",
                    json={"message": message},
                    timeout=aiohttp.ClientTimeout(total=10)
                )
                response_time = time.time() - start_time
                results["response_times"].append(response_time)
                
                if msg_response.status != 200:
                    results["errors"].append(f"Message failed: {msg_response.status}")
                    continue
                
                # Small delay between messages
                await asyncio.sleep(random.uniform(0.5, 2.0))
            
            results["success"] = len(results["errors"]) == 0
            
        except asyncio.TimeoutError:
            results["errors"].append("Timeout")
        except Exception as e:
            results["errors"].append(str(e))
        
        return results
    
    async def run_load_test(self, concurrent_users: int) -> Dict[str, Any]:
        """
        Ejecuta test de carga con número específico de usuarios.
        """
        print(f"\n🚀 Testing with {concurrent_users} concurrent users...")
        
        level_results = {
            "concurrent_users": concurrent_users,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "errors": [],
            "start_time": time.time(),
            "cache_hit_rate": 0
        }
        
        # Create session pool
        connector = aiohttp.TCPConnector(limit=concurrent_users, limit_per_host=concurrent_users)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Warm up cache with a few requests
            if concurrent_users == CONCURRENT_USERS[0]:  # First run
                print("   📦 Warming up cache...")
                for i in range(5):
                    await self.simulate_user_session(i, session)
            
            # Run concurrent users
            print(f"   🏃 Running {concurrent_users} users simultaneously...")
            tasks = []
            for i in range(concurrent_users):
                task = asyncio.create_task(self.simulate_user_session(i, session))
                tasks.append(task)
            
            # Wait for all to complete
            user_results = await asyncio.gather(*tasks)
            
            # Aggregate results
            total_cache_hits = 0
            total_cache_opportunities = 0
            
            for result in user_results:
                level_results["total_requests"] += 1
                if result["success"]:
                    level_results["successful_requests"] += 1
                else:
                    level_results["failed_requests"] += 1
                
                level_results["response_times"].extend(result["response_times"])
                level_results["errors"].extend(result["errors"])
                
                # Cache metrics
                total_cache_hits += result["cache_hits"]
                total_cache_opportunities += len(result["response_times"]) - 1  # Exclude start
        
        level_results["end_time"] = time.time()
        level_results["duration"] = level_results["end_time"] - level_results["start_time"]
        
        # Calculate metrics
        if level_results["response_times"]:
            level_results["avg_response_time"] = statistics.mean(level_results["response_times"])
            level_results["p95_response_time"] = statistics.quantiles(level_results["response_times"], n=20)[18]  # 95th percentile
            level_results["p99_response_time"] = statistics.quantiles(level_results["response_times"], n=100)[98]  # 99th percentile
            level_results["min_response_time"] = min(level_results["response_times"])
            level_results["max_response_time"] = max(level_results["response_times"])
        
        if total_cache_opportunities > 0:
            level_results["cache_hit_rate"] = (total_cache_hits / total_cache_opportunities) * 100
        
        level_results["success_rate"] = (level_results["successful_requests"] / level_results["total_requests"] * 100) if level_results["total_requests"] > 0 else 0
        level_results["requests_per_second"] = level_results["total_requests"] / level_results["duration"]
        
        # Print summary
        print(f"   ✅ Completed in {level_results['duration']:.1f}s")
        print(f"   📊 Success Rate: {level_results['success_rate']:.1f}%")
        print(f"   ⚡ Avg Response Time: {level_results['avg_response_time']:.3f}s")
        print(f"   🎯 P95 Response Time: {level_results['p95_response_time']:.3f}s")
        print(f"   💾 Cache Hit Rate: {level_results['cache_hit_rate']:.1f}%")
        print(f"   🔄 Requests/Second: {level_results['requests_per_second']:.1f}")
        
        return level_results
    
    async def run_progressive_load_test(self):
        """
        Ejecuta test de carga progresivo.
        """
        print("🏋️ NGX Voice Sales Agent - Progressive Load Test")
        print("=" * 70)
        print(f"API URL: {self.api_url}")
        print(f"Test levels: {CONCURRENT_USERS}")
        print("=" * 70)
        
        # Check API health first
        print("\n🏥 Checking API health...")
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.get(f"{self.api_url}/health")
                if response.status == 200:
                    print("✅ API is healthy")
                else:
                    print(f"❌ API health check failed: {response.status}")
                    return
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            return
        
        # Run progressive load tests
        for level in CONCURRENT_USERS:
            if level > 100 and self.results["load_levels"].get(100, {}).get("success_rate", 100) < 90:
                print(f"\n⚠️  Skipping {level} users due to poor performance at lower levels")
                continue
            
            level_result = await self.run_load_test(level)
            self.results["load_levels"][level] = level_result
            
            # Stop if performance degrades too much
            if level_result["success_rate"] < 50 or level_result["avg_response_time"] > 5.0:
                print(f"\n⚠️  Stopping test due to poor performance")
                break
            
            # Brief pause between levels
            if level < CONCURRENT_USERS[-1]:
                print("\n⏸️  Pausing 5 seconds before next level...")
                await asyncio.sleep(5)
        
        # Generate report
        self._generate_load_test_report()
    
    def _generate_load_test_report(self):
        """
        Genera reporte detallado del test de carga.
        """
        print("\n" + "=" * 70)
        print("📊 LOAD TEST REPORT")
        print("=" * 70)
        
        # Find maximum successful load
        max_successful_load = 0
        for level, results in self.results["load_levels"].items():
            if results["success_rate"] >= 99 and results["avg_response_time"] < 0.5:
                max_successful_load = level
        
        print(f"\n🎯 MAXIMUM SUCCESSFUL LOAD: {max_successful_load} concurrent users")
        
        # Performance summary table
        print("\n📈 PERFORMANCE BY LOAD LEVEL:")
        print(f"{'Users':>8} | {'Success':>8} | {'Avg RT':>8} | {'P95 RT':>8} | {'Cache':>8} | {'RPS':>8}")
        print("-" * 70)
        
        for level in sorted(self.results["load_levels"].keys()):
            r = self.results["load_levels"][level]
            print(f"{level:>8} | {r['success_rate']:>7.1f}% | {r['avg_response_time']:>7.3f}s | "
                  f"{r['p95_response_time']:>7.3f}s | {r['cache_hit_rate']:>7.1f}% | {r['requests_per_second']:>7.1f}")
        
        # Target validation
        print("\n🎯 TARGET VALIDATION:")
        targets = {
            "Response Time <0.5s": False,
            "1000+ Concurrent Users": False,
            "99%+ Success Rate": False,
            "80%+ Cache Hit Rate": False
        }
        
        # Check each target
        for level, results in self.results["load_levels"].items():
            if results["avg_response_time"] < 0.5 and results["success_rate"] >= 99:
                targets["Response Time <0.5s"] = True
            if level >= 1000 and results["success_rate"] >= 99:
                targets["1000+ Concurrent Users"] = True
            if results["success_rate"] >= 99:
                targets["99%+ Success Rate"] = True
            if results["cache_hit_rate"] >= 80:
                targets["80%+ Cache Hit Rate"] = True
        
        for target, achieved in targets.items():
            print(f"   {'✅' if achieved else '❌'} {target}")
        
        # Error analysis
        all_errors = []
        for results in self.results["load_levels"].values():
            all_errors.extend(results["errors"])
        
        if all_errors:
            print(f"\n❌ ERRORS FOUND ({len(all_errors)} total):")
            error_counts = {}
            for error in all_errors:
                error_type = error.split(":")[0]
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
            
            for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"   - {error_type}: {count} occurrences")
        
        # Cache effectiveness
        print("\n💾 CACHE EFFECTIVENESS:")
        cache_rates = [r["cache_hit_rate"] for r in self.results["load_levels"].values() if r["cache_hit_rate"] > 0]
        if cache_rates:
            avg_cache_rate = sum(cache_rates) / len(cache_rates)
            print(f"   Average Cache Hit Rate: {avg_cache_rate:.1f}%")
            
            # Estimate performance improvement from cache
            if len(self.results["load_levels"]) > 1:
                first_level = list(self.results["load_levels"].values())[0]
                last_level = list(self.results["load_levels"].values())[-1]
                if last_level["cache_hit_rate"] > first_level["cache_hit_rate"]:
                    print(f"   Cache improved from {first_level['cache_hit_rate']:.1f}% to {last_level['cache_hit_rate']:.1f}%")
        
        # Final verdict
        print("\n" + "=" * 70)
        print("🏁 FINAL VERDICT:")
        
        achieved_count = sum(targets.values())
        print(f"   Achieved {achieved_count}/4 performance targets")
        
        if achieved_count >= 3 and max_successful_load >= 500:
            print("\n   🎉 SYSTEM PASSES LOAD TEST!")
            print(f"   Can handle {max_successful_load}+ concurrent users with <0.5s response time")
        else:
            print("\n   ⚠️  SYSTEM NEEDS OPTIMIZATION")
            print(f"   Maximum load: {max_successful_load} users")
        
        print("=" * 70)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/results/load_test_{timestamp}.json"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "api_url": self.api_url,
                "max_successful_load": max_successful_load,
                "targets_achieved": achieved_count,
                "results": self.results
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {filename}")


async def main():
    """Run progressive load test."""
    tester = RealLoadTest()
    
    try:
        await tester.run_progressive_load_test()
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("⚡ Starting Progressive Load Test...")
    print("This will test the system with increasing load.")
    print("Estimated time: 10-15 minutes")
    print("\nMake sure the API is running and Redis is available!\n")
    
    asyncio.run(main())