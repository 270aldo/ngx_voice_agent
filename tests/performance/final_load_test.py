#!/usr/bin/env python3
"""
Final load test for NGX Voice Sales Agent - Testing real performance.
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime
import random
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class FinalLoadTest:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.results = []
        
    async def test_single_user(self, session, user_id):
        """Test a single user conversation."""
        try:
            # Generate valid user data
            names = ["Juan Perez", "Maria Garcia", "Carlos Lopez", "Ana Martinez", "Pedro Rodriguez"]
            
            user_data = {
                "customer_data": {
                    "name": random.choice(names),
                    "email": f"user{user_id}@gmail.com",
                    "phone": f"+52155{random.randint(10000000, 99999999)}",
                    "age": random.randint(25, 55),
                    "initial_message": "Hola, quiero información sobre NGX"
                }
            }
            
            start_time = time.time()
            
            async with session.post(
                f"{self.base_url}/conversations/start",
                json=user_data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                duration = (time.time() - start_time) * 1000
                result = {
                    "user_id": user_id,
                    "status": response.status,
                    "duration_ms": duration,
                    "success": response.status == 200
                }
                
                if response.status == 200:
                    data = await response.json()
                    result["conversation_id"] = data.get("conversation_id")
                else:
                    result["error"] = await response.text()
                    
                return result
                
        except asyncio.TimeoutError:
            return {
                "user_id": user_id,
                "status": 0,
                "error": "timeout",
                "success": False
            }
        except Exception as e:
            return {
                "user_id": user_id,
                "status": 0,
                "error": str(e),
                "success": False
            }
    
    async def run_test(self, num_users: int, concurrent_limit: int = 50):
        """Run load test with specified number of users."""
        print(f"\n{'='*60}")
        print(f"🚀 NGX Voice Sales Agent - Final Load Test")
        print(f"Users: {num_users}, Concurrent Limit: {concurrent_limit}")
        print(f"{'='*60}\n")
        
        # Check API health first
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as resp:
                    if resp.status != 200:
                        print("❌ API health check failed!")
                        return
                    print("✅ API is healthy\n")
        except:
            print("❌ Cannot connect to API!")
            return
        
        # Run test
        start_time = time.time()
        semaphore = asyncio.Semaphore(concurrent_limit)
        
        async def limited_test(user_id):
            async with semaphore:
                return await self.test_single_user(session, user_id)
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            # Launch users in batches
            batch_size = 100
            for i in range(0, num_users, batch_size):
                batch_end = min(i + batch_size, num_users)
                batch_tasks = [limited_test(j) for j in range(i, batch_end)]
                
                print(f"Launching batch {i//batch_size + 1}: users {i}-{batch_end}")
                batch_results = await asyncio.gather(*batch_tasks)
                self.results.extend(batch_results)
                
                # Progress update
                successful = sum(1 for r in self.results if r.get("success", False))
                print(f"Progress: {len(self.results)}/{num_users} users")
                print(f"Success rate: {successful}/{len(self.results)} ({successful/len(self.results)*100:.1f}%)\n")
                
                # Small delay between batches
                if batch_end < num_users:
                    await asyncio.sleep(0.5)
        
        # Calculate final statistics
        total_time = time.time() - start_time
        successful_results = [r for r in self.results if r.get("success", False)]
        failed_results = [r for r in self.results if not r.get("success", False)]
        
        if successful_results:
            durations = [r["duration_ms"] for r in successful_results]
            avg_duration = sum(durations) / len(durations)
            sorted_durations = sorted(durations)
            p95 = sorted_durations[int(len(sorted_durations) * 0.95)]
            p99 = sorted_durations[int(len(sorted_durations) * 0.99)]
        else:
            avg_duration = p95 = p99 = 0
        
        # Print results
        print(f"\n{'='*60}")
        print(f"📊 FINAL TEST RESULTS")
        print(f"{'='*60}")
        print(f"Total Duration: {total_time:.2f}s")
        print(f"Total Users: {num_users}")
        print(f"Successful: {len(successful_results)} ({len(successful_results)/num_users*100:.1f}%)")
        print(f"Failed: {len(failed_results)} ({len(failed_results)/num_users*100:.1f}%)")
        
        if successful_results:
            print(f"\n⏱️  Response Times (successful requests):")
            print(f"  Average: {avg_duration:.2f}ms")
            print(f"  P95: {p95:.2f}ms")
            print(f"  P99: {p99:.2f}ms")
            print(f"  Throughput: {len(successful_results)/total_time:.2f} req/s")
        
        # Analyze errors
        if failed_results:
            print(f"\n❌ Error Analysis:")
            error_types = {}
            for r in failed_results:
                error = r.get("error", "unknown")
                if "429" in str(error):
                    error = "rate_limit"
                elif "timeout" in error:
                    error = "timeout"
                elif "validation" in str(error).lower():
                    error = "validation"
                    
                error_types[error] = error_types.get(error, 0) + 1
            
            for error, count in error_types.items():
                print(f"  {error}: {count}")
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report = {
            "test_name": "NGX Final Load Test",
            "timestamp": timestamp,
            "config": {
                "num_users": num_users,
                "concurrent_limit": concurrent_limit
            },
            "results": {
                "total_duration_s": total_time,
                "total_users": num_users,
                "successful": len(successful_results),
                "failed": len(failed_results),
                "success_rate": len(successful_results)/num_users*100,
                "avg_response_ms": avg_duration,
                "p95_response_ms": p95,
                "p99_response_ms": p99,
                "throughput_rps": len(successful_results)/total_time if total_time > 0 else 0
            }
        }
        
        os.makedirs("results", exist_ok=True)
        with open(f"results/final_load_test_{timestamp}.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Report saved to: results/final_load_test_{timestamp}.json")

if __name__ == "__main__":
    test = FinalLoadTest()
    
    # Progressive test
    print("Starting progressive load test...")
    
    # Test 1: 200 users
    asyncio.run(test.run_test(num_users=200, concurrent_limit=50))
    
    print("\n⏳ Waiting 10 seconds before next test...")
    time.sleep(10)
    
    # Test 2: 500 users
    asyncio.run(test.run_test(num_users=500, concurrent_limit=100))