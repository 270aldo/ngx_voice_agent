#!/usr/bin/env python3
"""
Simplified Load Test for Testing Infrastructure
Tests the load testing framework even with minimal API endpoints.
"""

import asyncio
import aiohttp
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Any


class SimplifiedLoadTester:
    """Load tester that works with minimal API endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        
    async def simulate_user_activity(self, user_id: int, session: aiohttp.ClientSession) -> Dict:
        """Simulate user activity with available endpoints."""
        results = {
            "user_id": user_id,
            "requests": [],
            "start_time": time.time()
        }
        
        # Test 1: Health check
        try:
            start = time.time()
            async with session.get(f"{self.base_url}/health") as resp:
                duration = (time.time() - start) * 1000
                results["requests"].append({
                    "endpoint": "/health",
                    "status": resp.status,
                    "duration_ms": duration
                })
        except Exception as e:
            results["requests"].append({
                "endpoint": "/health",
                "error": str(e)
            })
        
        # Test 2: Try conversation endpoint (may fail)
        try:
            start = time.time()
            data = {
                "customer_data": {
                    "name": f"Load Test User {user_id}",
                    "email": f"user{user_id}@loadtest.com",
                    "profession": "Personal Trainer"
                }
            }
            async with session.post(
                f"{self.base_url}/api/v1/conversations/start",
                json=data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                duration = (time.time() - start) * 1000
                results["requests"].append({
                    "endpoint": "/api/v1/conversations/start",
                    "status": resp.status,
                    "duration_ms": duration
                })
        except Exception as e:
            results["requests"].append({
                "endpoint": "/api/v1/conversations/start",
                "error": str(e)
            })
        
        # Test 3: Multiple health checks to simulate load
        for i in range(5):
            try:
                start = time.time()
                async with session.get(
                    f"{self.base_url}/health",
                    headers={"X-User-ID": str(user_id), "X-Request-ID": f"{user_id}-{i}"}
                ) as resp:
                    duration = (time.time() - start) * 1000
                    results["requests"].append({
                        "endpoint": f"/health-{i}",
                        "status": resp.status,
                        "duration_ms": duration
                    })
                    await asyncio.sleep(0.1)  # Small delay between requests
            except Exception as e:
                results["requests"].append({
                    "endpoint": f"/health-{i}",
                    "error": str(e)
                })
        
        results["end_time"] = time.time()
        results["total_duration_ms"] = (results["end_time"] - results["start_time"]) * 1000
        return results
    
    async def run_load_test(self, num_users: int, test_name: str) -> Dict:
        """Run load test with specified number of users."""
        print(f"\n{'='*60}")
        print(f"🧪 {test_name}")
        print(f"Users: {num_users}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        # Create connector with higher limits
        connector = aiohttp.TCPConnector(limit=num_users * 2, limit_per_host=num_users)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            # Launch all users concurrently
            tasks = []
            for i in range(num_users):
                task = self.simulate_user_activity(i, session)
                tasks.append(task)
            
            print(f"Launching {num_users} concurrent users...")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
        # Process results
        successful_results = []
        errors = []
        
        for result in results:
            if isinstance(result, dict):
                successful_results.append(result)
            else:
                errors.append(str(result))
        
        total_duration = time.time() - start_time
        
        # Calculate metrics
        all_requests = []
        for user_result in successful_results:
            for req in user_result.get("requests", []):
                if "duration_ms" in req and req.get("status", 500) < 400:
                    all_requests.append(req["duration_ms"])
        
        if all_requests:
            avg_response = sum(all_requests) / len(all_requests)
            min_response = min(all_requests)
            max_response = max(all_requests)
        else:
            avg_response = min_response = max_response = 0
        
        # Print results
        print(f"\n📊 Results:")
        print(f"Total duration: {total_duration:.2f}s")
        print(f"Successful users: {len(successful_results)}/{num_users}")
        print(f"Total requests: {len(all_requests)}")
        print(f"Average response time: {avg_response:.2f}ms")
        print(f"Min response time: {min_response:.2f}ms")
        print(f"Max response time: {max_response:.2f}ms")
        print(f"Requests per second: {len(all_requests)/total_duration:.2f}")
        
        if errors:
            print(f"\n⚠️  Errors encountered: {len(errors)}")
            for i, error in enumerate(errors[:3]):
                print(f"  {i+1}. {error}")
        
        return {
            "test_name": test_name,
            "num_users": num_users,
            "duration_seconds": total_duration,
            "successful_users": len(successful_results),
            "total_requests": len(all_requests),
            "avg_response_ms": avg_response,
            "requests_per_second": len(all_requests)/total_duration if total_duration > 0 else 0,
            "errors": len(errors)
        }


async def main():
    """Run progressive load tests."""
    print("🚀 NGX Voice Sales Agent - Simplified Load Testing")
    print("Testing load capacity with available endpoints")
    print("=" * 80)
    
    tester = SimplifiedLoadTester()
    
    # Progressive load stages
    stages = [
        (50, "Stage 1: Light Load"),
        (100, "Stage 2: Moderate Load"),
        (200, "Stage 3: Target Load"),
        (300, "Stage 4: Heavy Load"),
        (500, "Stage 5: Stress Test")
    ]
    
    all_results = []
    
    for num_users, stage_name in stages:
        result = await tester.run_load_test(num_users, stage_name)
        all_results.append(result)
        
        # Check if we should continue
        if result["errors"] > num_users * 0.5:  # More than 50% errors
            print(f"\n🛑 Stopping test due to high error rate")
            break
        
        # Cool down between stages
        if num_users < 500:
            print(f"\n⏸️  Cooling down for 10 seconds...")
            await asyncio.sleep(10)
    
    # Final report
    print("\n" + "="*80)
    print("📊 FINAL REPORT - Simplified Load Test")
    print("="*80)
    
    print(f"\n{'Stage':<20} {'Users':<10} {'RPS':<10} {'Avg MS':<10} {'Errors':<10}")
    print("-"*60)
    
    for result in all_results:
        print(f"{result['test_name']:<20} {result['num_users']:<10} "
              f"{result['requests_per_second']:<10.1f} "
              f"{result['avg_response_ms']:<10.1f} "
              f"{result['errors']:<10}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tests/performance/results/simplified_load_test_{timestamp}.json"
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, "w") as f:
        json.dump({
            "test_type": "simplified_load_test",
            "timestamp": timestamp,
            "stages": all_results
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {filename}")
    
    # Determine if API can handle real load
    if all_results and all_results[-1]["requests_per_second"] > 100:
        print("\n✅ System demonstrates good throughput capacity")
        print("   Ready for full conversation load testing when API is complete")
    else:
        print("\n⚠️  Limited throughput detected")
        print("   This may be due to simplified API endpoints")


if __name__ == "__main__":
    asyncio.run(main())