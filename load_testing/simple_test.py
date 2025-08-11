#!/usr/bin/env python3
"""
Simple load test script for NGX Voice Sales Agent.
Tests basic endpoints with concurrent requests.
"""

import asyncio
import aiohttp
import time
import statistics
from datetime import datetime


async def fetch(session, url, name="Request"):
    """Make an HTTP request and measure response time."""
    start = time.time()
    try:
        async with session.get(url) as response:
            await response.text()
            elapsed = time.time() - start
            return {
                "name": name,
                "status": response.status,
                "time": elapsed * 1000,  # Convert to ms
                "success": response.status == 200
            }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "name": name,
            "status": 0,
            "time": elapsed * 1000,
            "success": False,
            "error": str(e)
        }


async def run_load_test(base_url, num_users, duration_seconds):
    """Run load test with specified number of concurrent users."""
    print(f"\n🚀 Starting load test...")
    print(f"URL: {base_url}")
    print(f"Users: {num_users}")
    print(f"Duration: {duration_seconds}s")
    print("-" * 50)
    
    results = []
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        while time.time() - start_time < duration_seconds:
            # Create tasks for concurrent requests
            tasks = []
            
            # Mix of different endpoints
            for i in range(num_users):
                if i % 5 == 0:
                    task = fetch(session, f"{base_url}/health", "Health Check")
                elif i % 3 == 0:
                    task = fetch(session, f"{base_url}/", "Root Endpoint")
                else:
                    task = fetch(session, f"{base_url}/docs", "API Docs")
                
                tasks.append(task)
            
            # Execute all requests concurrently
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            # Small delay between batches
            await asyncio.sleep(0.5)
    
    # Calculate statistics
    print("\n📊 Test Results:")
    print("-" * 50)
    
    total_requests = len(results)
    successful_requests = sum(1 for r in results if r["success"])
    failed_requests = total_requests - successful_requests
    
    response_times = [r["time"] for r in results if r["success"]]
    
    if response_times:
        avg_time = statistics.mean(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        p50 = statistics.median(response_times)
        p95 = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max_time
        p99 = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else max_time
    else:
        avg_time = min_time = max_time = p50 = p95 = p99 = 0
    
    duration = time.time() - start_time
    rps = total_requests / duration
    
    print(f"Total Requests: {total_requests}")
    print(f"Successful: {successful_requests} ({successful_requests/total_requests*100:.1f}%)")
    print(f"Failed: {failed_requests} ({failed_requests/total_requests*100:.1f}%)")
    print(f"Requests/sec: {rps:.2f}")
    print(f"\nResponse Times (ms):")
    print(f"  Average: {avg_time:.2f}")
    print(f"  Min: {min_time:.2f}")
    print(f"  Max: {max_time:.2f}")
    print(f"  Median (p50): {p50:.2f}")
    print(f"  p95: {p95:.2f}")
    print(f"  p99: {p99:.2f}")
    
    # Check if we meet the requirements
    print(f"\n✅ Performance Check:")
    if p95 < 1000:
        print("  ✓ p95 < 1s: PASS")
    else:
        print("  ✗ p95 < 1s: FAIL")
    
    if failed_requests / total_requests < 0.01:
        print("  ✓ Error rate < 1%: PASS")
    else:
        print("  ✗ Error rate < 1%: FAIL")
    
    if rps > 50:
        print("  ✓ Throughput > 50 RPS: PASS")
    else:
        print("  ✗ Throughput > 50 RPS: FAIL")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"results/simple_test_{num_users}users_{timestamp}.txt"
    
    with open(filename, "w") as f:
        f.write(f"Load Test Results\n")
        f.write(f"================\n")
        f.write(f"Timestamp: {datetime.now()}\n")
        f.write(f"URL: {base_url}\n")
        f.write(f"Users: {num_users}\n")
        f.write(f"Duration: {duration:.1f}s\n")
        f.write(f"\nResults:\n")
        f.write(f"Total Requests: {total_requests}\n")
        f.write(f"Successful: {successful_requests}\n")
        f.write(f"Failed: {failed_requests}\n")
        f.write(f"RPS: {rps:.2f}\n")
        f.write(f"\nResponse Times:\n")
        f.write(f"Average: {avg_time:.2f}ms\n")
        f.write(f"p50: {p50:.2f}ms\n")
        f.write(f"p95: {p95:.2f}ms\n")
        f.write(f"p99: {p99:.2f}ms\n")
    
    print(f"\n📄 Results saved to: {filename}")


async def main():
    """Run different load test scenarios."""
    base_url = "http://localhost:8000"
    
    # Ensure results directory exists
    import os
    os.makedirs("results", exist_ok=True)
    
    print("NGX Voice Sales Agent - Simple Load Test")
    print("=" * 50)
    
    # Scenario 1: Quick test (20 users, 10 seconds)
    print("\n🔄 Scenario 1: Quick Test")
    await run_load_test(base_url, 20, 10)
    
    await asyncio.sleep(5)  # Cool down
    
    # Scenario 2: Standard load (50 users, 30 seconds)
    print("\n🔄 Scenario 2: Standard Load")
    await run_load_test(base_url, 50, 30)
    
    await asyncio.sleep(5)  # Cool down
    
    # Scenario 3: Target load (100 users, 60 seconds)
    print("\n🔄 Scenario 3: Target Load (100 users)")
    await run_load_test(base_url, 100, 60)
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())