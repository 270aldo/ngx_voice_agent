#!/usr/bin/env python3
"""
Stress test for NGX Voice Sales Agent - 1000+ concurrent users.
Tests system limits and breaking points.
"""

import asyncio
import aiohttp
import time
import psutil
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Tuple
import statistics
import resource

class StressTest:
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.results = {
            "stages": [],
            "errors": [],
            "breaking_point": None,
            "max_successful_users": 0,
            "system_metrics": []
        }
        
    async def create_test_user(self, user_id: int) -> Dict[str, Any]:
        """Create test user data with variations."""
        professions = ["Entrenador Personal", "Nutricionista", "Coach de Vida", "Fisioterapeuta", "Instructor de Yoga"]
        objectives = [
            ["perder_peso", "ganar_musculo"],
            ["mejorar_salud", "reducir_estres"],
            ["ganar_fuerza", "mejorar_resistencia"],
            ["tonificar", "flexibilidad"]
        ]
        
        return {
            "name": f"StressUser_{user_id}",
            "email": f"stress_user_{user_id}@test.com",
            "age": 25 + (user_id % 40),
            "profesion": professions[user_id % len(professions)],
            "experiencia_fitness": ["principiante", "intermedio", "avanzado"][user_id % 3],
            "objetivos": objectives[user_id % len(objectives)],
            "presupuesto": ["bajo", "medio", "alto"][user_id % 3],
            "compromiso_tiempo": f"{3 + (user_id % 4)} días/semana",
            "preferencias": {
                "prefiere_online": user_id % 2 == 0,
                "horario_preferido": ["mañana", "tarde", "noche"][user_id % 3],
                "experiencia_apps": True
            }
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system resource usage."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()
        
        # Get process-specific metrics
        try:
            # Find API process
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'uvicorn' in str(proc.info.get('cmdline', [])):
                    api_process = psutil.Process(proc.info['pid'])
                    api_memory = api_process.memory_info().rss / 1024 / 1024  # MB
                    api_cpu = api_process.cpu_percent(interval=0.1)
                    break
            else:
                api_memory = 0
                api_cpu = 0
        except:
            api_memory = 0
            api_cpu = 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_read_mb": disk_io.read_bytes / (1024**2),
                "disk_write_mb": disk_io.write_bytes / (1024**2),
                "network_sent_mb": net_io.bytes_sent / (1024**2),
                "network_recv_mb": net_io.bytes_recv / (1024**2)
            },
            "api_process": {
                "memory_mb": api_memory,
                "cpu_percent": api_cpu
            }
        }
    
    async def make_request(self, session: aiohttp.ClientSession, user_id: int) -> Tuple[bool, float, str]:
        """Make a single request and return success, response time, and error if any."""
        start_time = time.time()
        
        try:
            user_data = await self.create_test_user(user_id)
            
            async with session.post(
                f"{self.api_url}/conversations/start",
                json={
                    "message": f"Hola, soy {user_data['name']} y quiero mejorar mi salud",
                    "customer_data": user_data
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    return True, response_time, ""
                else:
                    error_text = await response.text()
                    return False, response_time, f"Status {response.status}: {error_text[:100]}"
                    
        except asyncio.TimeoutError:
            return False, time.time() - start_time, "Timeout"
        except Exception as e:
            return False, time.time() - start_time, str(e)[:100]
    
    async def run_stage(self, concurrent_users: int, duration_seconds: int = 30) -> Dict[str, Any]:
        """Run a single stage with specified concurrent users."""
        print(f"\n🚀 Stage: {concurrent_users} concurrent users for {duration_seconds}s")
        
        stage_start = time.time()
        successful_requests = 0
        failed_requests = 0
        response_times = []
        errors = []
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(concurrent_users)
        
        async def limited_request(session: aiohttp.ClientSession, user_id: int):
            async with semaphore:
                return await self.make_request(session, user_id)
        
        # Create connector with proper limits
        connector = aiohttp.TCPConnector(
            limit=concurrent_users,
            limit_per_host=concurrent_users,
            force_close=True
        )
        
        async with aiohttp.ClientSession(connector=connector) as session:
            user_counter = 0
            tasks = []
            
            # Collect initial system metrics
            initial_metrics = self.get_system_metrics()
            
            while time.time() - stage_start < duration_seconds:
                # Launch batch of requests
                batch_tasks = []
                for _ in range(min(100, concurrent_users)):  # Launch in batches
                    task = asyncio.create_task(limited_request(session, user_counter))
                    batch_tasks.append(task)
                    user_counter += 1
                
                # Wait for batch to complete
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Process results
                for result in batch_results:
                    if isinstance(result, tuple):
                        success, response_time, error = result
                        if success:
                            successful_requests += 1
                            response_times.append(response_time)
                        else:
                            failed_requests += 1
                            if error and len(errors) < 100:  # Limit error collection
                                errors.append(error)
                    else:
                        failed_requests += 1
                        if len(errors) < 100:
                            errors.append(str(result))
                
                # Small delay between batches
                await asyncio.sleep(0.1)
                
                # Print progress
                if int(time.time() - stage_start) % 5 == 0:
                    success_rate = successful_requests / max(1, successful_requests + failed_requests) * 100
                    print(f"  Progress: {successful_requests + failed_requests} requests, {success_rate:.1f}% success")
        
        # Collect final system metrics
        final_metrics = self.get_system_metrics()
        
        # Calculate statistics
        total_requests = successful_requests + failed_requests
        success_rate = successful_requests / max(1, total_requests) * 100
        
        stage_result = {
            "concurrent_users": concurrent_users,
            "duration": time.time() - stage_start,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": success_rate,
            "response_times": {
                "avg": statistics.mean(response_times) if response_times else 0,
                "p50": statistics.median(response_times) if response_times else 0,
                "p95": statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else 0,
                "p99": statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else 0,
                "max": max(response_times) if response_times else 0
            },
            "throughput": total_requests / (time.time() - stage_start),
            "errors": errors[:10],  # Sample of errors
            "system_metrics": {
                "initial": initial_metrics,
                "final": final_metrics,
                "cpu_increase": final_metrics["system"]["cpu_percent"] - initial_metrics["system"]["cpu_percent"],
                "memory_increase": final_metrics["system"]["memory_percent"] - initial_metrics["system"]["memory_percent"]
            }
        }
        
        # Print stage summary
        print(f"\n  📊 Stage Results:")
        print(f"     Success Rate: {success_rate:.1f}%")
        print(f"     Throughput: {stage_result['throughput']:.1f} req/s")
        print(f"     Avg Response: {stage_result['response_times']['avg']:.2f}s")
        print(f"     P95 Response: {stage_result['response_times']['p95']:.2f}s")
        print(f"     CPU Usage: {final_metrics['system']['cpu_percent']:.1f}%")
        print(f"     Memory Usage: {final_metrics['system']['memory_percent']:.1f}%")
        
        return stage_result
    
    async def find_breaking_point(self):
        """Progressively increase load until system breaks."""
        stages = [
            (100, 20),    # warmup
            (200, 30),    # baseline
            (500, 30),    # moderate load
            (750, 30),    # high load
            (1000, 30),   # stress load
            (1250, 30),   # extreme load
            (1500, 30),   # breaking point?
            (2000, 20),   # system limit?
        ]
        
        for concurrent_users, duration in stages:
            print(f"\n{'='*60}")
            print(f"Testing with {concurrent_users} concurrent users...")
            
            stage_result = await self.run_stage(concurrent_users, duration)
            self.results["stages"].append(stage_result)
            
            # Check if we've hit breaking point
            if stage_result["success_rate"] < 50:
                self.results["breaking_point"] = concurrent_users
                print(f"\n⚠️  Breaking point detected at {concurrent_users} users!")
                print(f"   Success rate dropped to {stage_result['success_rate']:.1f}%")
                break
            
            if stage_result["success_rate"] >= 95:
                self.results["max_successful_users"] = concurrent_users
            
            # Check system resources
            if stage_result["system_metrics"]["final"]["system"]["cpu_percent"] > 90:
                print("\n⚠️  CPU usage critical! Stopping test.")
                break
            
            if stage_result["system_metrics"]["final"]["system"]["memory_percent"] > 90:
                print("\n⚠️  Memory usage critical! Stopping test.")
                break
            
            # Cool down between stages
            print("\n⏳ Cooling down for 10 seconds...")
            await asyncio.sleep(10)
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive stress test report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_stages": len(self.results["stages"]),
                "max_successful_users": self.results["max_successful_users"],
                "breaking_point": self.results["breaking_point"],
                "max_throughput": 0,
                "optimal_concurrent_users": 0
            },
            "stages": self.results["stages"],
            "recommendations": []
        }
        
        # Find max throughput and optimal users
        max_throughput = 0
        optimal_users = 0
        
        for stage in self.results["stages"]:
            if stage["success_rate"] >= 95 and stage["throughput"] > max_throughput:
                max_throughput = stage["throughput"]
                optimal_users = stage["concurrent_users"]
        
        report["summary"]["max_throughput"] = max_throughput
        report["summary"]["optimal_concurrent_users"] = optimal_users
        
        # Generate recommendations
        if self.results["breaking_point"]:
            report["recommendations"].append(
                f"System breaks at {self.results['breaking_point']} concurrent users. "
                f"Consider scaling infrastructure for higher loads."
            )
        
        if optimal_users < 500:
            report["recommendations"].append(
                "System struggles with moderate loads. Review connection pooling and async handling."
            )
        
        # Check for performance degradation
        if self.results["stages"]:
            first_stage = self.results["stages"][0]
            last_stage = self.results["stages"][-1]
            
            if last_stage["response_times"]["avg"] > first_stage["response_times"]["avg"] * 3:
                report["recommendations"].append(
                    "Significant performance degradation under load. Check for bottlenecks."
                )
        
        return report
    
    async def run(self):
        """Run the complete stress test."""
        print("""
============================================================
💪 NGX Voice Sales Agent - Stress Test (1000+ Users)
Finding system limits and breaking points
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
        
        # Increase system limits
        try:
            resource.setrlimit(resource.RLIMIT_NOFILE, (4096, 4096))
        except:
            print("⚠️  Could not increase file descriptor limit")
        
        print("🔍 Starting progressive load test...\n")
        
        # Run stress test
        await self.find_breaking_point()
        
        # Generate report
        report = self.generate_report()
        
        # Print final summary
        print(f"""
============================================================
📊 STRESS TEST FINAL RESULTS
============================================================
Stages Completed: {report['summary']['total_stages']}
Max Successful Users: {report['summary']['max_successful_users']}
Breaking Point: {report['summary']['breaking_point'] or 'Not reached'}
Max Throughput: {report['summary']['max_throughput']:.1f} req/s
Optimal Concurrent Users: {report['summary']['optimal_concurrent_users']}

📈 Performance Progression:
""")
        
        for stage in report['stages']:
            bar_length = int(stage['success_rate'] / 2)
            bar = '█' * bar_length + '░' * (50 - bar_length)
            print(f"{stage['concurrent_users']:4d} users: [{bar}] {stage['success_rate']:.1f}%")
        
        if report['recommendations']:
            print("\n💡 Recommendations:")
            for rec in report['recommendations']:
                print(f"  - {rec}")
        
        # Save report
        os.makedirs("results", exist_ok=True)
        report_file = f"results/stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {report_file}")


async def main():
    test = StressTest()
    await test.run()


if __name__ == "__main__":
    asyncio.run(main())