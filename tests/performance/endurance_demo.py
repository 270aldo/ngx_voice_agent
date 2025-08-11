#!/usr/bin/env python3
"""
30-Minute Endurance Demo for NGX Voice Sales Agent
Demonstrates system stability under sustained load.
"""

import asyncio
import aiohttp
import time
import psutil
import json
import os
from datetime import datetime
from typing import List, Dict, Any


class EnduranceDemoRunner:
    """Runs a 30-minute endurance test with 200 users."""
    
    def __init__(self, base_url: str = "http://localhost:8000", duration_minutes: int = 30):
        self.base_url = base_url
        self.duration_minutes = duration_minutes
        self.target_users = 200
        self.metrics_history = []
        self.start_time = None
        self.process = psutil.Process()
        
    async def user_session(self, user_id: int, batch: int, session: aiohttp.ClientSession) -> Dict:
        """Simulate continuous user activity."""
        results = {
            "user_id": f"endurance_{batch}_{user_id}",
            "requests": [],
            "start_time": time.time()
        }
        
        # Simulate various API calls
        endpoints = [
            ("GET", "/health", None),
            ("GET", "/health", None),  # Multiple health checks
            ("GET", "/health", None),
            ("POST", "/api/v1/conversations/start", {
                "customer_data": {
                    "name": f"Endurance User {user_id}",
                    "email": f"endurance{user_id}@test.com"
                }
            }),
            ("GET", "/metrics", None),
        ]
        
        for method, endpoint, data in endpoints:
            try:
                start = time.time()
                
                if method == "GET":
                    async with session.get(
                        f"{self.base_url}{endpoint}",
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        duration = (time.time() - start) * 1000
                        results["requests"].append({
                            "endpoint": endpoint,
                            "method": method,
                            "status": resp.status,
                            "duration_ms": duration
                        })
                else:  # POST
                    async with session.post(
                        f"{self.base_url}{endpoint}",
                        json=data,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        duration = (time.time() - start) * 1000
                        results["requests"].append({
                            "endpoint": endpoint,
                            "method": method,
                            "status": resp.status,
                            "duration_ms": duration
                        })
                
                # Small delay between requests
                await asyncio.sleep(0.2)
                
            except Exception as e:
                results["requests"].append({
                    "endpoint": endpoint,
                    "method": method,
                    "error": str(e)
                })
        
        results["end_time"] = time.time()
        return results
    
    async def run_batch(self, batch_num: int) -> Dict:
        """Run a single batch of users."""
        batch_start = time.time()
        
        connector = aiohttp.TCPConnector(limit=self.target_users)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for i in range(self.target_users):
                task = self.user_session(i, batch_num, session)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_requests = 0
        failed_requests = 0
        response_times = []
        
        for result in results:
            if isinstance(result, dict):
                for req in result.get("requests", []):
                    if "duration_ms" in req and req.get("status", 500) < 400:
                        successful_requests += 1
                        response_times.append(req["duration_ms"])
                    else:
                        failed_requests += 1
            else:
                failed_requests += 1
        
        batch_duration = time.time() - batch_start
        
        return {
            "batch_num": batch_num,
            "duration": batch_duration,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "response_times": response_times
        }
    
    def collect_system_metrics(self, batch_result: Dict, elapsed_minutes: float) -> Dict:
        """Collect system metrics."""
        response_times = batch_result.get("response_times", [])
        
        return {
            "timestamp": datetime.now().isoformat(),
            "elapsed_minutes": elapsed_minutes,
            "batch_num": batch_result["batch_num"],
            "cpu_percent": self.process.cpu_percent(interval=0.1),
            "memory_mb": self.process.memory_info().rss / 1024 / 1024,
            "successful_requests": batch_result["successful_requests"],
            "failed_requests": batch_result["failed_requests"],
            "avg_response_ms": sum(response_times) / len(response_times) if response_times else 0,
            "min_response_ms": min(response_times) if response_times else 0,
            "max_response_ms": max(response_times) if response_times else 0,
            "throughput_rps": (batch_result["successful_requests"] + batch_result["failed_requests"]) / batch_result["duration"]
        }
    
    async def run_endurance_test(self):
        """Run the full endurance test."""
        self.start_time = time.time()
        end_time = self.start_time + (self.duration_minutes * 60)
        
        print(f"🏃 NGX Voice Sales Agent - {self.duration_minutes}-Minute Endurance Demo")
        print(f"{'='*80}")
        print(f"Target Users: {self.target_users}")
        print(f"Duration: {self.duration_minutes} minutes")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        batch_num = 0
        checkpoint_interval = 5  # Every 5 minutes
        next_checkpoint = checkpoint_interval
        
        while time.time() < end_time:
            batch_num += 1
            elapsed_minutes = (time.time() - self.start_time) / 60
            
            print(f"Batch {batch_num} - Elapsed: {elapsed_minutes:.1f} minutes", end="", flush=True)
            
            # Run batch
            batch_result = await self.run_batch(batch_num)
            
            # Collect metrics
            metrics = self.collect_system_metrics(batch_result, elapsed_minutes)
            self.metrics_history.append(metrics)
            
            # Quick status
            print(f" | Response: {metrics['avg_response_ms']:.0f}ms | "
                  f"Success: {metrics['successful_requests']} | "
                  f"Failed: {metrics['failed_requests']} | "
                  f"CPU: {metrics['cpu_percent']:.1f}% | "
                  f"Memory: {metrics['memory_mb']:.0f}MB")
            
            # Checkpoint
            if elapsed_minutes >= next_checkpoint:
                self._print_checkpoint(elapsed_minutes)
                next_checkpoint += checkpoint_interval
            
            # Maintain 1 batch per minute
            batch_duration = time.time() - (self.start_time + (batch_num - 1) * 60)
            if batch_duration < 60:
                await asyncio.sleep(60 - batch_duration)
        
        # Final report
        self._generate_final_report()
    
    def _print_checkpoint(self, elapsed_minutes: float):
        """Print checkpoint summary."""
        print(f"\n{'='*60}")
        print(f"📊 Checkpoint at {elapsed_minutes:.0f} minutes")
        print(f"{'='*60}")
        
        # Last 5 batches
        recent_metrics = self.metrics_history[-5:]
        
        avg_response = sum(m["avg_response_ms"] for m in recent_metrics) / len(recent_metrics)
        avg_throughput = sum(m["throughput_rps"] for m in recent_metrics) / len(recent_metrics)
        total_failures = sum(m["failed_requests"] for m in recent_metrics)
        
        print(f"Average Response Time: {avg_response:.1f} ms")
        print(f"Average Throughput: {avg_throughput:.1f} req/s")
        print(f"Recent Failures: {total_failures}")
        
        # Check for degradation
        if len(self.metrics_history) > 10:
            initial_response = sum(m["avg_response_ms"] for m in self.metrics_history[:5]) / 5
            response_increase = (avg_response - initial_response) / initial_response * 100
            
            if response_increase > 50:
                print(f"⚠️  Response time increased by {response_increase:.1f}%")
            else:
                print(f"✅ Performance stable (change: {response_increase:+.1f}%)")
        
        print(f"{'='*60}\n")
    
    def _generate_final_report(self):
        """Generate final endurance test report."""
        duration_minutes = (time.time() - self.start_time) / 60
        
        print(f"\n{'='*80}")
        print(f"📊 ENDURANCE TEST - FINAL REPORT")
        print(f"{'='*80}")
        print(f"Test Duration: {duration_minutes:.1f} minutes")
        print(f"Total Batches: {len(self.metrics_history)}")
        
        # Performance comparison
        if len(self.metrics_history) >= 2:
            # First 5 vs Last 5 batches
            first_5 = self.metrics_history[:5]
            last_5 = self.metrics_history[-5:]
            
            metrics_comparison = [
                ("Response Time", "avg_response_ms", "ms"),
                ("Throughput", "throughput_rps", "req/s"),
                ("CPU Usage", "cpu_percent", "%"),
                ("Memory Usage", "memory_mb", "MB")
            ]
            
            print(f"\n{'Metric':<20} {'Start':<15} {'End':<15} {'Change':<15}")
            print("-" * 65)
            
            for metric_name, field, unit in metrics_comparison:
                start_val = sum(m[field] for m in first_5) / len(first_5)
                end_val = sum(m[field] for m in last_5) / len(last_5)
                change = end_val - start_val
                change_pct = (change / start_val * 100) if start_val > 0 else 0
                
                print(f"{metric_name:<20} {start_val:<15.1f} {end_val:<15.1f} "
                      f"{change:+.1f} {unit} ({change_pct:+.1f}%)")
        
        # Overall statistics
        total_successful = sum(m["successful_requests"] for m in self.metrics_history)
        total_failed = sum(m["failed_requests"] for m in self.metrics_history)
        success_rate = total_successful / (total_successful + total_failed) * 100
        
        print(f"\nTotal Requests: {total_successful + total_failed:,}")
        print(f"Success Rate: {success_rate:.2f}%")
        
        # Stability verdict
        print(f"\n🎯 STABILITY VERDICT:")
        
        response_degradation = 0
        if len(self.metrics_history) >= 2:
            initial_response = self.metrics_history[0]["avg_response_ms"]
            final_response = self.metrics_history[-1]["avg_response_ms"]
            response_degradation = (final_response - initial_response) / initial_response * 100
        
        if success_rate >= 99 and response_degradation < 20:
            print("✅ EXCELLENT - System showed exceptional stability")
        elif success_rate >= 95 and response_degradation < 50:
            print("✅ GOOD - System remained stable under load")
        else:
            print("⚠️  CONCERNS - Some degradation detected")
        
        # Save results
        self._save_results(duration_minutes)
    
    def _save_results(self, duration_minutes: float):
        """Save test results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/performance/results/endurance_demo_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        report = {
            "test_type": "endurance_demo",
            "timestamp": timestamp,
            "duration_minutes": duration_minutes,
            "target_users": self.target_users,
            "metrics_history": self.metrics_history
        }
        
        with open(filename, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")
        
        # Also create CSV for graphing
        csv_filename = filename.replace(".json", ".csv")
        with open(csv_filename, "w") as f:
            f.write("elapsed_minutes,avg_response_ms,throughput_rps,cpu_percent,memory_mb\n")
            for m in self.metrics_history:
                f.write(f"{m['elapsed_minutes']:.1f},{m['avg_response_ms']:.1f},"
                       f"{m['throughput_rps']:.1f},{m['cpu_percent']:.1f},"
                       f"{m['memory_mb']:.1f}\n")
        
        print(f"💾 CSV saved to: {csv_filename}")


async def main():
    """Run endurance demo test."""
    runner = EnduranceDemoRunner(duration_minutes=30)
    
    try:
        await runner.run_endurance_test()
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        runner._generate_final_report()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())