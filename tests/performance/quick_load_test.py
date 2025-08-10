#!/usr/bin/env python3
"""
Quick Load Test - Versión simplificada para verificación rápida
"""

import asyncio
import aiohttp
import time
from datetime import datetime
import json

async def quick_load_test():
    """Test de carga rápido con 50 usuarios"""
    print("🚀 NGX Voice Sales Agent - QUICK LOAD TEST")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")
    print("Testing with 50 concurrent users...")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    num_users = 50
    requests_per_user = 5
    
    async def user_session(user_id):
        """Simula una sesión de usuario"""
        results = []
        async with aiohttp.ClientSession() as session:
            for i in range(requests_per_user):
                try:
                    start = time.time()
                    
                    # 1. Health check
                    async with session.get(f"{base_url}/health") as resp:
                        await resp.json()
                    
                    # 2. Start conversation
                    async with session.post(
                        f"{base_url}/conversations/start",
                        json={
                            "customer_data": {
                                "name": f"Test User {user_id}",
                                "email": f"user{user_id}@test.com",
                                "profession": "Fitness Coach"
                            }
                        }
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            conversation_id = data.get("conversation_id")
                        else:
                            conversation_id = None
                    
                    # 3. Send message if conversation started
                    if conversation_id:
                        async with session.post(
                            f"{base_url}/conversations/{conversation_id}/message",
                            json={"message": "Hola, quiero saber sobre NGX"}
                        ) as resp:
                            await resp.json()
                    
                    elapsed = time.time() - start
                    results.append({
                        "user": user_id,
                        "request": i,
                        "success": True,
                        "duration": elapsed
                    })
                    
                except Exception as e:
                    results.append({
                        "user": user_id,
                        "request": i,
                        "success": False,
                        "error": str(e)
                    })
                
                # Small delay between requests
                await asyncio.sleep(0.1)
        
        return results
    
    # Launch all users concurrently
    print(f"\n🔄 Launching {num_users} concurrent users...")
    start_time = time.time()
    
    tasks = [user_session(i) for i in range(num_users)]
    all_results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    
    # Analyze results
    all_requests = []
    for user_results in all_results:
        all_requests.extend(user_results)
    
    successful = [r for r in all_requests if r["success"]]
    failed = [r for r in all_requests if not r["success"]]
    
    if successful:
        avg_duration = sum(r["duration"] for r in successful) / len(successful)
        max_duration = max(r["duration"] for r in successful)
        min_duration = min(r["duration"] for r in successful)
    else:
        avg_duration = max_duration = min_duration = 0
    
    # Print results
    print("\n" + "=" * 60)
    print("📊 QUICK LOAD TEST RESULTS")
    print("=" * 60)
    print(f"Total users: {num_users}")
    print(f"Requests per user: {requests_per_user}")
    print(f"Total requests: {len(all_requests)}")
    print(f"Successful: {len(successful)} ({len(successful)/len(all_requests)*100:.1f}%)")
    print(f"Failed: {len(failed)} ({len(failed)/len(all_requests)*100:.1f}%)")
    print(f"\nPerformance Metrics:")
    print(f"  - Average response time: {avg_duration:.3f}s")
    print(f"  - Min response time: {min_duration:.3f}s")
    print(f"  - Max response time: {max_duration:.3f}s")
    print(f"  - Total test duration: {total_time:.2f}s")
    print(f"  - Requests per second: {len(all_requests)/total_time:.2f}")
    
    # Save results
    results_file = f"tests/performance/results/quick_load_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "test_type": "quick_load",
            "timestamp": datetime.now().isoformat(),
            "config": {
                "users": num_users,
                "requests_per_user": requests_per_user
            },
            "results": {
                "total_requests": len(all_requests),
                "successful": len(successful),
                "failed": len(failed),
                "avg_response_time": avg_duration,
                "min_response_time": min_duration,
                "max_response_time": max_duration,
                "total_duration": total_time,
                "rps": len(all_requests)/total_time
            }
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    # Verdict
    if len(failed) / len(all_requests) > 0.1:  # More than 10% failed
        print("\n❌ PERFORMANCE TEST FAILED - Too many errors")
    elif avg_duration > 2.0:  # Average response > 2 seconds
        print("\n⚠️  PERFORMANCE TEST WARNING - Response times too high")
    else:
        print("\n✅ PERFORMANCE TEST PASSED")

if __name__ == "__main__":
    asyncio.run(quick_load_test())