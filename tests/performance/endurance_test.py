#!/usr/bin/env python3
"""
Endurance test for NGX Voice Sales Agent - 2 hour memory leak detection.
"""

import asyncio
import aiohttp
import time
import psutil
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import statistics
import gc

class EnduranceTest:
    def __init__(self, api_url: str = "http://localhost:8000", duration_hours: float = 2.0):
        self.api_url = api_url
        self.duration_seconds = int(duration_hours * 3600)
        self.metrics = {
            "memory_samples": [],
            "cpu_samples": [],
            "response_times": [],
            "errors": [],
            "requests_count": 0,
            "start_time": None,
            "end_time": None
        }
        self.process = psutil.Process()
        self.sample_interval = 30  # seconds
        self.last_sample_time = 0
        
    async def create_test_user(self) -> Dict[str, Any]:
        """Create test user data."""
        return {
            "nombre": f"TestUser_{int(time.time() * 1000) % 100000}",
            "edad": 35,
            "profesion": "Entrenador Personal",
            "experiencia_fitness": "intermedio",
            "objetivos": ["perder_peso", "ganar_musculo"],
            "presupuesto": "medio",
            "compromiso_tiempo": "3-4 días/semana",
            "preferencias": {
                "prefiere_online": True,
                "horario_preferido": "mañana",
                "experiencia_apps": True
            }
        }
    
    def collect_system_metrics(self):
        """Collect current system metrics."""
        current_time = time.time()
        
        # Collect every sample_interval seconds
        if current_time - self.last_sample_time >= self.sample_interval:
            # Memory metrics
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            
            # CPU metrics
            cpu_percent = self.process.cpu_percent(interval=0.1)
            
            self.metrics["memory_samples"].append({
                "timestamp": datetime.now().isoformat(),
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": memory_percent
            })
            
            self.metrics["cpu_samples"].append({
                "timestamp": datetime.now().isoformat(),
                "percent": cpu_percent
            })
            
            self.last_sample_time = current_time
            
            # Force garbage collection periodically
            gc.collect()
    
    async def make_conversation_request(self, session: aiohttp.ClientSession):
        """Make a single conversation request."""
        start_time = time.time()
        
        try:
            user_data = await self.create_test_user()
            
            # Start conversation
            async with session.post(
                f"{self.api_url}/api/v1/conversation",
                json={
                    "message": "Hola, estoy interesado en mejorar mi condición física",
                    "user_id": user_data["nombre"],
                    "session_id": f"endurance_test_{int(time.time() * 1000)}",
                    "customer_data": user_data,
                    "context": {
                        "test_type": "endurance",
                        "timestamp": datetime.now().isoformat()
                    }
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_time = time.time() - start_time
                self.metrics["response_times"].append(response_time)
                self.metrics["requests_count"] += 1
                
                if response.status != 200:
                    self.metrics["errors"].append({
                        "timestamp": datetime.now().isoformat(),
                        "status": response.status,
                        "message": await response.text()
                    })
                
                return await response.json()
                
        except Exception as e:
            self.metrics["errors"].append({
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "type": type(e).__name__
            })
            self.metrics["requests_count"] += 1
    
    async def continuous_load(self):
        """Generate continuous load for the duration."""
        async with aiohttp.ClientSession() as session:
            while time.time() - self.metrics["start_time"] < self.duration_seconds:
                # Collect system metrics
                self.collect_system_metrics()
                
                # Make requests (10 concurrent)
                tasks = []
                for _ in range(10):
                    tasks.append(self.make_conversation_request(session))
                
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Small delay between batches
                await asyncio.sleep(1)
                
                # Print progress every minute
                elapsed = time.time() - self.metrics["start_time"]
                if int(elapsed) % 60 == 0:
                    self.print_progress(elapsed)
    
    def print_progress(self, elapsed_seconds: float):
        """Print current progress."""
        elapsed_minutes = elapsed_seconds / 60
        total_minutes = self.duration_seconds / 60
        progress = (elapsed_seconds / self.duration_seconds) * 100
        
        print(f"\n⏱️  Progress: {elapsed_minutes:.1f}/{total_minutes:.0f} minutes ({progress:.1f}%)")
        print(f"📊 Requests: {self.metrics['requests_count']:,}")
        print(f"❌ Errors: {len(self.metrics['errors'])}")
        
        if self.metrics["memory_samples"]:
            latest_memory = self.metrics["memory_samples"][-1]
            print(f"💾 Memory: {latest_memory['rss_mb']:.1f} MB ({latest_memory['percent']:.1f}%)")
        
        if self.metrics["cpu_samples"]:
            latest_cpu = self.metrics["cpu_samples"][-1]
            print(f"🖥️  CPU: {latest_cpu['percent']:.1f}%")
    
    def analyze_results(self) -> Dict[str, Any]:
        """Analyze test results for memory leaks and performance issues."""
        analysis = {
            "duration": {
                "hours": self.duration_seconds / 3600,
                "start": self.metrics["start_time"],
                "end": self.metrics["end_time"]
            },
            "requests": {
                "total": self.metrics["requests_count"],
                "errors": len(self.metrics["errors"]),
                "success_rate": (1 - len(self.metrics["errors"]) / max(1, self.metrics["requests_count"])) * 100
            },
            "performance": {},
            "memory": {},
            "cpu": {},
            "issues": []
        }
        
        # Response time analysis
        if self.metrics["response_times"]:
            analysis["performance"] = {
                "avg_response_time": statistics.mean(self.metrics["response_times"]),
                "p95_response_time": statistics.quantiles(self.metrics["response_times"], n=20)[18],
                "p99_response_time": statistics.quantiles(self.metrics["response_times"], n=100)[98],
                "max_response_time": max(self.metrics["response_times"])
            }
        
        # Memory analysis
        if self.metrics["memory_samples"]:
            memory_values = [s["rss_mb"] for s in self.metrics["memory_samples"]]
            initial_memory = memory_values[0]
            final_memory = memory_values[-1]
            memory_growth = final_memory - initial_memory
            memory_growth_percent = (memory_growth / initial_memory) * 100
            
            analysis["memory"] = {
                "initial_mb": initial_memory,
                "final_mb": final_memory,
                "growth_mb": memory_growth,
                "growth_percent": memory_growth_percent,
                "max_mb": max(memory_values),
                "avg_mb": statistics.mean(memory_values)
            }
            
            # Check for memory leak
            if memory_growth_percent > 20:
                analysis["issues"].append({
                    "type": "potential_memory_leak",
                    "severity": "high" if memory_growth_percent > 50 else "medium",
                    "description": f"Memory grew by {memory_growth_percent:.1f}% during test"
                })
        
        # CPU analysis
        if self.metrics["cpu_samples"]:
            cpu_values = [s["percent"] for s in self.metrics["cpu_samples"]]
            analysis["cpu"] = {
                "avg_percent": statistics.mean(cpu_values),
                "max_percent": max(cpu_values),
                "min_percent": min(cpu_values)
            }
            
            # Check for high CPU
            if analysis["cpu"]["avg_percent"] > 80:
                analysis["issues"].append({
                    "type": "high_cpu_usage",
                    "severity": "medium",
                    "description": f"Average CPU usage was {analysis['cpu']['avg_percent']:.1f}%"
                })
        
        return analysis
    
    async def run(self):
        """Run the endurance test."""
        print(f"""
============================================================
🏃 NGX Voice Sales Agent - Endurance Test
Duration: {self.duration_seconds / 3600:.1f} hours
Target: Detect memory leaks and performance degradation
============================================================
        """)
        
        # Check API health
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/health") as response:
                    if response.status == 200:
                        print("✅ API is healthy\n")
                    else:
                        print("❌ API health check failed")
                        return
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            return
        
        # Start test
        self.metrics["start_time"] = time.time()
        print(f"🚀 Starting endurance test at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("This will run continuously for the specified duration...")
        print("Press Ctrl+C to stop early\n")
        
        try:
            await self.continuous_load()
        except KeyboardInterrupt:
            print("\n⚠️  Test interrupted by user")
        finally:
            self.metrics["end_time"] = time.time()
        
        # Analyze results
        print("\n🔍 Analyzing results...")
        analysis = self.analyze_results()
        
        # Print summary
        print(f"""
============================================================
📊 ENDURANCE TEST RESULTS
============================================================
Duration: {analysis['duration']['hours']:.1f} hours
Total Requests: {analysis['requests']['total']:,}
Success Rate: {analysis['requests']['success_rate']:.1f}%

⏱️  Performance:
  Average Response: {analysis['performance'].get('avg_response_time', 0):.2f}s
  P95 Response: {analysis['performance'].get('p95_response_time', 0):.2f}s
  P99 Response: {analysis['performance'].get('p99_response_time', 0):.2f}s

💾 Memory Analysis:
  Initial: {analysis['memory'].get('initial_mb', 0):.1f} MB
  Final: {analysis['memory'].get('final_mb', 0):.1f} MB
  Growth: {analysis['memory'].get('growth_mb', 0):.1f} MB ({analysis['memory'].get('growth_percent', 0):.1f}%)
  
🖥️  CPU Analysis:
  Average: {analysis['cpu'].get('avg_percent', 0):.1f}%
  Maximum: {analysis['cpu'].get('max_percent', 0):.1f}%
        """)
        
        # Report issues
        if analysis["issues"]:
            print("\n⚠️  ISSUES DETECTED:")
            for issue in analysis["issues"]:
                print(f"  - [{issue['severity'].upper()}] {issue['type']}: {issue['description']}")
        else:
            print("\n✅ No significant issues detected!")
        
        # Save detailed report
        report_file = f"results/endurance_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs("results", exist_ok=True)
        
        with open(report_file, "w") as f:
            json.dump({
                "analysis": analysis,
                "metrics": {
                    "memory_samples": self.metrics["memory_samples"],
                    "cpu_samples": self.metrics["cpu_samples"],
                    "errors": self.metrics["errors"][-100:],  # Last 100 errors
                    "response_time_stats": {
                        "samples": len(self.metrics["response_times"]),
                        "avg": statistics.mean(self.metrics["response_times"]) if self.metrics["response_times"] else 0,
                        "min": min(self.metrics["response_times"]) if self.metrics["response_times"] else 0,
                        "max": max(self.metrics["response_times"]) if self.metrics["response_times"] else 0
                    }
                }
            }, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {report_file}")


async def main():
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description="Run endurance test")
    parser.add_argument("--hours", type=float, default=2.0, help="Test duration in hours")
    parser.add_argument("--url", default="http://localhost:8000", help="API URL")
    args = parser.parse_args()
    
    # Run test
    test = EnduranceTest(api_url=args.url, duration_hours=args.hours)
    await test.run()


if __name__ == "__main__":
    asyncio.run(main())