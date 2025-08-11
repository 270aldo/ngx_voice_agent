#!/usr/bin/env python3
"""
Extreme Performance Tests for NGX Voice Sales Agent.
Tests the system under extreme conditions to find breaking points.
"""

import asyncio
import aiohttp
import time
import statistics
import json
import random
from datetime import datetime
from typing import List, Dict, Any


class ExtremeLoadTester:
    """Extreme load testing scenarios for NGX Voice Agent."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.errors = []
        
    async def make_conversation_request(self, session: aiohttp.ClientSession, user_id: int):
        """Simulate a full conversation flow."""
        conversation_id = None
        
        try:
            # Start conversation
            start_data = {
                "customer_data": {
                    "id": f"extreme-test-user-{user_id}",
                    "name": f"Extreme Tester {user_id}",
                    "email": f"extreme{user_id}@test.com",
                    "age": random.randint(25, 55),
                    "profession": random.choice([
                        "Entrepreneur", "Fitness Coach", "Business Owner",
                        "Personal Trainer", "Nutritionist"
                    ])
                },
                "program_type": random.choice(["PRIME", "LONGEVITY", None])
            }
            
            start_time = time.time()
            async with session.post(
                f"{self.base_url}/conversations/start",
                json=start_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                result = await response.json()
                conversation_id = result.get("conversation_id")
                
            # Send multiple messages
            messages = [
                "Hola, ¿qué incluye el programa?",
                "¿Cuál es el precio?",
                "¿Qué ROI puedo esperar?",
                "Tengo dudas sobre el tiempo de compromiso",
                "¿Cómo funciona el HIE?"
            ]
            
            for msg in messages:
                if conversation_id:
                    async with session.post(
                        f"{self.base_url}/conversations/{conversation_id}/message",
                        json={"message": msg},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        await response.json()
                        
            elapsed = time.time() - start_time
            return {
                "user_id": user_id,
                "success": True,
                "duration": elapsed * 1000,
                "conversation_id": conversation_id
            }
            
        except Exception as e:
            self.errors.append({
                "user_id": user_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return {
                "user_id": user_id,
                "success": False,
                "error": str(e)
            }
    
    async def stress_test(self, target_users: int = 200, ramp_up_time: int = 30):
        """Stress test: Gradually increase load to target users."""
        print(f"\n🔥 STRESS TEST: Ramping up to {target_users} users")
        print(f"Ramp up time: {ramp_up_time} seconds")
        print("=" * 60)
        
        results = []
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            # Calculate users to add per second
            users_per_second = target_users / ramp_up_time
            current_users = 0
            
            while current_users < target_users:
                batch_start = time.time()
                
                # Add users for this second
                users_to_add = min(
                    int(users_per_second),
                    target_users - current_users
                )
                
                tasks = []
                for i in range(users_to_add):
                    user_id = current_users + i
                    task = self.make_conversation_request(session, user_id)
                    tasks.append(task)
                
                # Execute batch
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                results.extend([r for r in batch_results if isinstance(r, dict)])
                
                current_users += users_to_add
                
                # Progress update
                print(f"Active users: {current_users}/{target_users} "
                      f"({current_users/target_users*100:.1f}%)")
                
                # Wait for next second
                elapsed = time.time() - batch_start
                if elapsed < 1:
                    await asyncio.sleep(1 - elapsed)
        
        self._print_results("Stress Test", results)
        return results
    
    async def spike_test(self, spike_users: int = 150, spike_time: int = 10):
        """Spike test: Sudden burst of users."""
        print(f"\n⚡ SPIKE TEST: {spike_users} users in {spike_time} seconds")
        print("=" * 60)
        
        results = []
        
        async with aiohttp.ClientSession() as session:
            # Create all tasks at once
            tasks = []
            for i in range(spike_users):
                task = self.make_conversation_request(session, i)
                tasks.append(task)
            
            # Execute all at once with small delays
            print("Releasing the spike! 💥")
            start_time = time.time()
            
            # Split into smaller batches to avoid overwhelming
            batch_size = spike_users // spike_time
            for i in range(0, spike_users, batch_size):
                batch = tasks[i:i+batch_size]
                batch_results = await asyncio.gather(*batch, return_exceptions=True)
                results.extend([r for r in batch_results if isinstance(r, dict)])
                
                if i + batch_size < spike_users:
                    await asyncio.sleep(1)
            
            duration = time.time() - start_time
            print(f"Spike completed in {duration:.2f} seconds")
        
        self._print_results("Spike Test", results)
        return results
    
    async def endurance_test(self, users: int = 50, duration_minutes: int = 5):
        """Endurance test: Sustained load over time."""
        print(f"\n⏱️  ENDURANCE TEST: {users} users for {duration_minutes} minutes")
        print("=" * 60)
        
        results = []
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        async with aiohttp.ClientSession() as session:
            iteration = 0
            
            while time.time() < end_time:
                iteration += 1
                batch_start = time.time()
                
                # Create batch of requests
                tasks = []
                for i in range(users):
                    user_id = (iteration * users) + i
                    task = self.make_conversation_request(session, user_id)
                    tasks.append(task)
                
                # Execute batch
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                results.extend([r for r in batch_results if isinstance(r, dict)])
                
                # Progress update
                elapsed = time.time() - start_time
                remaining = end_time - time.time()
                print(f"Iteration {iteration}: "
                      f"Elapsed: {elapsed/60:.1f}min, "
                      f"Remaining: {remaining/60:.1f}min")
                
                # Maintain consistent load
                batch_duration = time.time() - batch_start
                if batch_duration < 2:
                    await asyncio.sleep(2 - batch_duration)
        
        self._print_results("Endurance Test", results)
        return results
    
    async def breakpoint_test(self, start_users: int = 50, increment: int = 25,
                            max_users: int = 500):
        """Breakpoint test: Find system limits."""
        print(f"\n💥 BREAKPOINT TEST: Finding system limits")
        print(f"Starting with {start_users} users, increment by {increment}")
        print("=" * 60)
        
        current_users = start_users
        all_results = []
        
        async with aiohttp.ClientSession() as session:
            while current_users <= max_users:
                print(f"\nTesting with {current_users} concurrent users...")
                
                # Run test batch
                tasks = []
                for i in range(current_users):
                    task = self.make_conversation_request(session, i)
                    tasks.append(task)
                
                start_time = time.time()
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                results = [r for r in batch_results if isinstance(r, dict)]
                duration = time.time() - start_time
                
                # Calculate success rate
                successful = sum(1 for r in results if r.get("success", False))
                success_rate = successful / len(results) * 100 if results else 0
                
                # Calculate response times
                response_times = [r["duration"] for r in results if "duration" in r]
                avg_response = statistics.mean(response_times) if response_times else 0
                
                print(f"Results: Success rate: {success_rate:.1f}%, "
                      f"Avg response: {avg_response:.0f}ms")
                
                all_results.extend(results)
                
                # Check if system is breaking
                if success_rate < 95 or avg_response > 2000:
                    print(f"\n⚠️  System showing stress at {current_users} users!")
                    print(f"Success rate: {success_rate:.1f}%")
                    print(f"Average response time: {avg_response:.0f}ms")
                    
                    if success_rate < 80:
                        print(f"\n🔴 BREAKPOINT FOUND: System fails at {current_users} users")
                        break
                
                current_users += increment
                await asyncio.sleep(5)  # Cool down between tests
        
        return all_results
    
    def _print_results(self, test_name: str, results: List[Dict]):
        """Print detailed test results."""
        print(f"\n📊 {test_name} Results:")
        print("-" * 60)
        
        total = len(results)
        successful = sum(1 for r in results if r.get("success", False))
        failed = total - successful
        
        response_times = [r["duration"] for r in results if "duration" in r]
        
        if response_times:
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            p50 = statistics.median(response_times)
            p95 = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max_time
            p99 = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else max_time
        else:
            avg_time = min_time = max_time = p50 = p95 = p99 = 0
        
        print(f"Total Requests: {total}")
        print(f"Successful: {successful} ({successful/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")
        
        print(f"\nResponse Times (ms):")
        print(f"  Average: {avg_time:.2f}")
        print(f"  Min: {min_time:.2f}")
        print(f"  Max: {max_time:.2f}")
        print(f"  Median (p50): {p50:.2f}")
        print(f"  p95: {p95:.2f}")
        print(f"  p99: {p99:.2f}")
        
        if self.errors:
            print(f"\n⚠️  Errors encountered: {len(self.errors)}")
            for i, error in enumerate(self.errors[:5]):  # Show first 5 errors
                print(f"  {i+1}. User {error['user_id']}: {error['error']}")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/performance/results/{test_name.lower().replace(' ', '_')}_{timestamp}.json"
        
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, "w") as f:
            json.dump({
                "test_name": test_name,
                "timestamp": timestamp,
                "summary": {
                    "total_requests": total,
                    "successful": successful,
                    "failed": failed,
                    "success_rate": successful/total*100 if total > 0 else 0,
                    "avg_response_time": avg_time,
                    "p95_response_time": p95,
                    "p99_response_time": p99
                },
                "results": results,
                "errors": self.errors
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")


async def main():
    """Run all extreme performance tests."""
    print("🚀 NGX Voice Sales Agent - EXTREME PERFORMANCE TESTS")
    print("=" * 60)
    
    tester = ExtremeLoadTester()
    
    # 1. Stress Test
    await tester.stress_test(target_users=200, ramp_up_time=30)
    await asyncio.sleep(10)  # Cool down
    
    # 2. Spike Test
    await tester.spike_test(spike_users=150, spike_time=10)
    await asyncio.sleep(10)  # Cool down
    
    # 3. Endurance Test (reduced for demo)
    await tester.endurance_test(users=50, duration_minutes=5)
    await asyncio.sleep(10)  # Cool down
    
    # 4. Breakpoint Test
    await tester.breakpoint_test(start_users=50, increment=50, max_users=300)
    
    print("\n✅ All extreme tests completed!")
    print("Check the results folder for detailed reports.")


if __name__ == "__main__":
    asyncio.run(main())