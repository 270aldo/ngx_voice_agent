#!/usr/bin/env python3
"""
Rate-limit aware load test for NGX Voice Sales Agent.
Respects API rate limits while testing performance.
"""

import asyncio
import aiohttp
import time
import json
import random
from datetime import datetime
from typing import Dict, List
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class RateLimitAwareLoadTest:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.results = []
        # Rate limit: 100 requests per minute = ~1.67 requests per second
        self.max_rps = 1.5  # Stay under limit
        self.semaphore = asyncio.Semaphore(10)  # Max 10 concurrent requests
        
    async def simulate_user(self, session, user_id, stats):
        """Simulate a single user with rate limiting."""
        async with self.semaphore:  # Limit concurrent requests
            try:
                # Generate user data
                user_data = {
                    "customer_data": {
                        "name": f"Test User {user_id}",
                        "email": f"user{user_id}@test.com",
                        "phone": f"+1555{user_id:06d}",
                        "initial_message": self._get_initial_message(user_id)
                    }
                }
                
                start_time = time.time()
                async with session.post(
                    f"{self.base_url}/conversations/start",
                    json=user_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    duration = (time.time() - start_time) * 1000
                    
                    stats["total_requests"] += 1
                    if response.status == 200:
                        stats["successful_requests"] += 1
                        stats["response_times"].append(duration)
                    elif response.status == 429:
                        stats["rate_limited"] += 1
                    else:
                        stats["failed_requests"] += 1
                        
                    return {
                        "user_id": user_id,
                        "status": response.status,
                        "duration_ms": duration,
                        "timestamp": datetime.now().isoformat()
                    }
                    
            except asyncio.TimeoutError:
                stats["timeout_errors"] += 1
                return {"user_id": user_id, "error": "timeout"}
            except Exception as e:
                stats["other_errors"] += 1
                return {"user_id": user_id, "error": str(e)}
    
    def _get_initial_message(self, user_id):
        """Get varied initial messages."""
        messages = [
            "Hola, quiero saber más sobre NGX",
            "¿Cómo puede ayudarme NGX con mi negocio?",
            "Estoy interesado en el programa PRIME",
            "Necesito información sobre LONGEVITY",
            "¿Cuál es el precio de NGX?"
        ]
        return messages[user_id % len(messages)]
    
    async def run_test(self, num_users: int, duration_seconds: int = 60):
        """Run load test with rate limiting."""
        print(f"\n{'='*60}")
        print(f"🚀 Rate-Limited Load Test: {num_users} users over {duration_seconds}s")
        print(f"Max RPS: {self.max_rps}")
        print(f"{'='*60}\n")
        
        stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "rate_limited": 0,
            "timeout_errors": 0,
            "other_errors": 0,
            "response_times": []
        }
        
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            tasks = []
            
            # Spread users over time to respect rate limit
            delay_between_users = 1.0 / self.max_rps
            
            for i in range(num_users):
                # Create task
                task = self.simulate_user(session, i, stats)
                tasks.append(task)
                
                # Rate limiting delay
                await asyncio.sleep(delay_between_users)
                
                # Progress update
                if i % 10 == 0:
                    elapsed = time.time() - start_time
                    print(f"Progress: {i}/{num_users} users started ({elapsed:.1f}s)")
                
                # Stop if duration exceeded
                if time.time() - start_time > duration_seconds:
                    print(f"Duration limit reached, stopping at {i} users")
                    break
            
            # Wait for all tasks to complete
            print("\nWaiting for all requests to complete...")
            results = await asyncio.gather(*tasks)
            
            # Calculate statistics
            total_time = time.time() - start_time
            if stats["response_times"]:
                avg_response = sum(stats["response_times"]) / len(stats["response_times"])
                p95_response = sorted(stats["response_times"])[int(len(stats["response_times"]) * 0.95)]
                p99_response = sorted(stats["response_times"])[int(len(stats["response_times"]) * 0.99)]
            else:
                avg_response = p95_response = p99_response = 0
            
            # Print results
            print(f"\n{'='*60}")
            print("📊 Test Results")
            print(f"{'='*60}")
            print(f"Total Duration: {total_time:.2f}s")
            print(f"Total Requests: {stats['total_requests']}")
            print(f"Successful: {stats['successful_requests']} ({stats['successful_requests']/max(1,stats['total_requests'])*100:.1f}%)")
            print(f"Failed: {stats['failed_requests']}")
            print(f"Rate Limited (429): {stats['rate_limited']}")
            print(f"Timeouts: {stats['timeout_errors']}")
            print(f"Other Errors: {stats['other_errors']}")
            print(f"\nResponse Times:")
            print(f"  Average: {avg_response:.2f}ms")
            print(f"  P95: {p95_response:.2f}ms")
            print(f"  P99: {p99_response:.2f}ms")
            print(f"  RPS: {stats['total_requests']/total_time:.2f}")
            
            # Save results
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            with open(f'results/rate_aware_test_{timestamp}.json', 'w') as f:
                json.dump({
                    "test_config": {
                        "num_users": num_users,
                        "duration_seconds": duration_seconds,
                        "max_rps": self.max_rps
                    },
                    "results": stats,
                    "timestamp": timestamp
                }, f, indent=2)

if __name__ == "__main__":
    test = RateLimitAwareLoadTest()
    
    # Run progressive tests
    asyncio.run(test.run_test(num_users=50, duration_seconds=60))
    
    print("\n⏳ Waiting 30 seconds before next test...")
    time.sleep(30)
    
    asyncio.run(test.run_test(num_users=100, duration_seconds=120))