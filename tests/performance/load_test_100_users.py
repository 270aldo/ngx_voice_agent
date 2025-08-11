#!/usr/bin/env python3
"""
Load Test con 100 usuarios - Versión optimizada para resultados rápidos
"""

import asyncio
import aiohttp
import time
from datetime import datetime
import json
import statistics

async def test_100_users():
    """Test de carga con 100 usuarios concurrentes"""
    print("🚀 NGX Voice Sales Agent - LOAD TEST (100 USERS)")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    num_users = 100
    requests_per_user = 10
    
    print(f"\n📊 Test Configuration:")
    print(f"  - Concurrent users: {num_users}")
    print(f"  - Requests per user: {requests_per_user}")
    print(f"  - Total requests: {num_users * requests_per_user}")
    
    async def user_session(user_id):
        """Simula una sesión completa de usuario"""
        results = []
        async with aiohttp.ClientSession() as session:
            for i in range(requests_per_user):
                try:
                    start = time.time()
                    
                    # Ciclo de conversación realista
                    # 1. Health check
                    async with session.get(f"{base_url}/health") as resp:
                        health_time = time.time() - start
                    
                    # 2. Start conversation
                    conv_start = time.time()
                    async with session.post(
                        f"{base_url}/api/v1/conversations/start",
                        json={
                            "customer_data": {
                                "name": f"Test User {user_id}",
                                "email": f"user{user_id}@test.com",
                                "profession": ["Fitness Coach", "Doctor", "Nutritionist", "Business Owner"][user_id % 4]
                            }
                        }
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            conversation_id = data.get("conversation_id")
                            conv_time = time.time() - conv_start
                        else:
                            conversation_id = None
                            conv_time = 0
                    
                    # 3. Send messages if conversation started
                    msg_times = []
                    if conversation_id:
                        messages = [
                            "Hola, quiero saber sobre NGX",
                            "¿Cuáles son los precios?",
                            "¿Cómo funciona la IA?"
                        ]
                        
                        for msg in messages:
                            msg_start = time.time()
                            try:
                                async with session.post(
                                    f"{base_url}/api/v1/conversations/{conversation_id}/message",
                                    json={"message": msg}
                                ) as resp:
                                    await resp.json()
                                    msg_times.append(time.time() - msg_start)
                            except:
                                msg_times.append(0)
                            
                            # Small delay between messages
                            await asyncio.sleep(0.05)
                    
                    total_time = time.time() - start
                    results.append({
                        "user": user_id,
                        "request": i,
                        "success": conversation_id is not None,
                        "total_time": total_time,
                        "health_time": health_time,
                        "conv_time": conv_time,
                        "msg_times": msg_times
                    })
                    
                except Exception as e:
                    results.append({
                        "user": user_id,
                        "request": i,
                        "success": False,
                        "error": str(e),
                        "total_time": time.time() - start
                    })
                
                # Delay between conversation cycles
                await asyncio.sleep(0.1)
        
        return results
    
    # Launch all users with slight staggering
    print(f"\n🔄 Launching {num_users} concurrent users...")
    print("  (Staggered start over 5 seconds)")
    
    start_time = time.time()
    tasks = []
    
    for i in range(num_users):
        tasks.append(user_session(i))
        # Stagger user starts
        if i < num_users - 1:
            await asyncio.sleep(0.05)
    
    # Wait for all users to complete
    print("\n⏳ Waiting for all users to complete...")
    all_results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    
    # Analyze results
    all_requests = []
    for user_results in all_results:
        all_requests.extend(user_results)
    
    successful = [r for r in all_requests if r.get("success")]
    failed = [r for r in all_requests if not r.get("success")]
    
    # Calculate detailed metrics
    if successful:
        total_times = [r["total_time"] for r in successful]
        conv_times = [r["conv_time"] for r in successful if r.get("conv_time")]
        all_msg_times = []
        for r in successful:
            if r.get("msg_times"):
                all_msg_times.extend([t for t in r["msg_times"] if t > 0])
        
        metrics = {
            "avg_total_time": statistics.mean(total_times),
            "median_total_time": statistics.median(total_times),
            "p95_total_time": sorted(total_times)[int(len(total_times) * 0.95)] if len(total_times) > 20 else max(total_times),
            "p99_total_time": sorted(total_times)[int(len(total_times) * 0.99)] if len(total_times) > 100 else max(total_times),
            "avg_conv_start": statistics.mean(conv_times) if conv_times else 0,
            "avg_msg_time": statistics.mean(all_msg_times) if all_msg_times else 0
        }
    else:
        metrics = {}
    
    # Print results
    print("\n" + "=" * 60)
    print("📊 LOAD TEST RESULTS (100 USERS)")
    print("=" * 60)
    print(f"Total users: {num_users}")
    print(f"Requests per user: {requests_per_user}")
    print(f"Total requests: {len(all_requests)}")
    print(f"Successful: {len(successful)} ({len(successful)/len(all_requests)*100:.1f}%)")
    print(f"Failed: {len(failed)} ({len(failed)/len(all_requests)*100:.1f}%)")
    
    if metrics:
        print(f"\n⏱️  Performance Metrics:")
        print(f"  Average total time: {metrics['avg_total_time']:.3f}s")
        print(f"  Median total time: {metrics['median_total_time']:.3f}s")
        print(f"  95th percentile: {metrics['p95_total_time']:.3f}s")
        print(f"  99th percentile: {metrics['p99_total_time']:.3f}s")
        print(f"  Avg conversation start: {metrics['avg_conv_start']:.3f}s")
        print(f"  Avg message response: {metrics['avg_msg_time']:.3f}s")
    
    print(f"\n🚀 Throughput:")
    print(f"  Total test duration: {total_time:.2f}s")
    print(f"  Requests per second: {len(all_requests)/total_time:.2f}")
    print(f"  Conversations per second: {len(successful)/total_time:.2f}")
    
    # Save detailed results
    results_dir = "tests/performance/results"
    import os
    os.makedirs(results_dir, exist_ok=True)
    
    results_file = f"{results_dir}/load_test_100_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "test_type": "load_test_100",
            "timestamp": datetime.now().isoformat(),
            "config": {
                "users": num_users,
                "requests_per_user": requests_per_user
            },
            "summary": {
                "total_requests": len(all_requests),
                "successful": len(successful),
                "failed": len(failed),
                "success_rate": len(successful)/len(all_requests) if all_requests else 0,
                "total_duration": total_time,
                "rps": len(all_requests)/total_time if total_time > 0 else 0
            },
            "metrics": metrics
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    
    # Performance verdict
    success_rate = len(successful)/len(all_requests) if all_requests else 0
    avg_time = metrics.get('avg_total_time', float('inf'))
    
    print("\n" + "=" * 60)
    if success_rate < 0.95:
        print("❌ PERFORMANCE TEST FAILED - Success rate < 95%")
    elif avg_time > 3.0:
        print("⚠️  PERFORMANCE WARNING - Average response time > 3s")
    else:
        print("✅ PERFORMANCE TEST PASSED!")
        print("   System successfully handled 100 concurrent users")

if __name__ == "__main__":
    asyncio.run(test_100_users())