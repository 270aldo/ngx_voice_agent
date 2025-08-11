#!/usr/bin/env python3
"""
Enhanced Load Test for 200+ Users - NGX Voice Sales Agent
Tests system performance with progressive load stages from 200 to 500 users.
"""

import asyncio
import aiohttp
import time
import statistics
import json
import random
import psutil
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict


@dataclass
class TestMetrics:
    """Container for test metrics."""
    timestamp: str
    stage: str
    total_users: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    max_response_time_ms: float
    requests_per_second: float
    error_rate_percent: float
    cpu_usage_percent: float
    memory_usage_percent: float
    active_connections: int


class NGXLoadTester200Plus:
    """Advanced load tester for 200+ concurrent users."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.errors = []
        self.start_time = None
        self.metrics_history = []
        
    async def create_user_session(self, user_id: int, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Simulate a complete user session with multiple interactions."""
        results = {
            "user_id": user_id,
            "start_time": time.time(),
            "requests": [],
            "errors": []
        }
        
        try:
            # 1. Health check
            health_start = time.time()
            async with session.get(f"{self.base_url}/health") as resp:
                health_time = (time.time() - health_start) * 1000
                results["requests"].append({
                    "type": "health",
                    "status": resp.status,
                    "duration_ms": health_time
                })
            
            # 2. Start conversation
            conv_start = time.time()
            conversation_data = {
                "customer_data": {
                    "name": f"Usuario Prueba",
                    "email": f"test{user_id}@example.com",
                    "profession": random.choice([
                        "Fitness Coach", "Personal Trainer", "Gym Owner",
                        "Nutritionist", "Physical Therapist", "Wellness Coach"
                    ]),
                    "age": random.randint(25, 55),
                    "business_type": random.choice(["freelance", "studio", "gym", "online"]),
                    "current_clients": random.randint(10, 100),
                    "years_experience": random.randint(1, 20)
                }
            }
            
            async with session.post(
                f"{self.base_url}/conversations/start",
                json=conversation_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                conv_time = (time.time() - conv_start) * 1000
                if resp.status == 200:
                    data = await resp.json()
                    conversation_id = data.get("conversation_id")
                    results["conversation_id"] = conversation_id
                else:
                    conversation_id = None
                    
                results["requests"].append({
                    "type": "start_conversation",
                    "status": resp.status,
                    "duration_ms": conv_time
                })
            
            # 3. Send realistic message sequence
            if conversation_id:
                messages = self._generate_realistic_messages(user_id)
                
                for msg in messages:
                    msg_start = time.time()
                    try:
                        async with session.post(
                            f"{self.base_url}/conversations/{conversation_id}/message",
                            json={"message": msg["text"]},
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as resp:
                            msg_time = (time.time() - msg_start) * 1000
                            results["requests"].append({
                                "type": f"message_{msg['intent']}",
                                "status": resp.status,
                                "duration_ms": msg_time
                            })
                            
                            # Simulate thinking time between messages
                            await asyncio.sleep(random.uniform(0.5, 2.0))
                            
                    except Exception as e:
                        results["errors"].append({
                            "type": "message_error",
                            "error": str(e),
                            "message": msg["text"]
                        })
                
                # 4. Get recommendations
                rec_start = time.time()
                try:
                    async with session.get(
                        f"{self.base_url}/conversations/{conversation_id}"
                    ) as resp:
                        rec_time = (time.time() - rec_start) * 1000
                        results["requests"].append({
                            "type": "get_recommendations",
                            "status": resp.status,
                            "duration_ms": rec_time
                        })
                except Exception as e:
                    results["errors"].append({
                        "type": "recommendations_error",
                        "error": str(e)
                    })
                
                # 5. Calculate ROI
                roi_start = time.time()
                roi_data = {
                    "profession": conversation_data["customer_data"]["profession"],
                    "current_clients": conversation_data["customer_data"]["current_clients"],
                    "average_ticket": random.randint(50, 300),
                    "work_hours_per_week": random.randint(20, 60)
                }
                
                try:
                    async with session.post(
                        f"{self.base_url}/conversations/{conversation_id}/message",
                        json=roi_data
                    ) as resp:
                        roi_time = (time.time() - roi_start) * 1000
                        results["requests"].append({
                            "type": "calculate_roi",
                            "status": resp.status,
                            "duration_ms": roi_time
                        })
                except Exception as e:
                    results["errors"].append({
                        "type": "roi_error",
                        "error": str(e)
                    })
            
            results["end_time"] = time.time()
            results["total_duration_ms"] = (results["end_time"] - results["start_time"]) * 1000
            results["success"] = len(results["errors"]) == 0
            
        except Exception as e:
            results["errors"].append({
                "type": "session_error",
                "error": str(e)
            })
            results["success"] = False
            
        return results
    
    def _generate_realistic_messages(self, user_id: int) -> List[Dict[str, str]]:
        """Generate realistic conversation flow based on user personas."""
        persona = user_id % 5  # 5 different personas
        
        if persona == 0:  # Skeptical user
            return [
                {"intent": "greeting", "text": "Hola, he escuchado sobre NGX pero tengo dudas"},
                {"intent": "objection", "text": "¿No es muy caro para empezar?"},
                {"intent": "technical", "text": "¿Cómo exactamente funciona la IA?"},
                {"intent": "comparison", "text": "¿Qué diferencia hay con otros sistemas?"},
                {"intent": "roi", "text": "¿Puedes mostrarme números concretos de ROI?"}
            ]
        elif persona == 1:  # Eager buyer
            return [
                {"intent": "greeting", "text": "¡Hola! Estoy muy interesado en NGX"},
                {"intent": "features", "text": "¿Qué incluye el programa completo?"},
                {"intent": "pricing", "text": "¿Cuáles son los planes disponibles?"},
                {"intent": "timeline", "text": "¿Cuándo puedo empezar?"},
                {"intent": "payment", "text": "¿Qué formas de pago aceptan?"}
            ]
        elif persona == 2:  # Technical user
            return [
                {"intent": "greeting", "text": "Hola, soy dueño de un gimnasio"},
                {"intent": "integration", "text": "¿Cómo se integra con mis sistemas actuales?"},
                {"intent": "data", "text": "¿Qué tipo de datos y métricas proporciona?"},
                {"intent": "security", "text": "¿Cómo manejan la seguridad de los datos?"},
                {"intent": "scalability", "text": "¿Puede crecer con mi negocio?"}
            ]
        elif persona == 3:  # Price-conscious
            return [
                {"intent": "greeting", "text": "Buenos días, busco optimizar costos"},
                {"intent": "pricing", "text": "¿Cuál es el precio exacto?"},
                {"intent": "discount", "text": "¿Hay descuentos por pago anual?"},
                {"intent": "value", "text": "¿Qué valor adicional ofrece NGX?"},
                {"intent": "guarantee", "text": "¿Ofrecen garantía de satisfacción?"}
            ]
        else:  # Relationship builder
            return [
                {"intent": "greeting", "text": "Hola, me recomendaron NGX"},
                {"intent": "story", "text": "¿Puedes contarme casos de éxito?"},
                {"intent": "support", "text": "¿Qué tipo de soporte ofrecen?"},
                {"intent": "community", "text": "¿Hay una comunidad de usuarios?"},
                {"intent": "personal", "text": "¿Cómo me ayudaría específicamente a mí?"}
            ]
    
    async def run_load_stage(self, num_users: int, stage_name: str, duration_seconds: int = 60) -> TestMetrics:
        """Run a load test stage with specified number of users."""
        print(f"\n{'='*60}")
        print(f"🚀 Starting {stage_name}: {num_users} concurrent users")
        print(f"Duration: {duration_seconds} seconds")
        print(f"{'='*60}")
        
        stage_results = []
        stage_start = time.time()
        stage_end = stage_start + duration_seconds
        
        # Monitor system resources
        process = psutil.Process(os.getpid())
        initial_connections = len(process.net_connections())
        
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=num_users * 2)
        ) as session:
            batch_num = 0
            
            while time.time() < stage_end:
                batch_start = time.time()
                batch_num += 1
                
                # Create batch of users
                tasks = []
                for i in range(num_users):
                    user_id = (batch_num * num_users) + i
                    task = self.create_user_session(user_id, session)
                    tasks.append(task)
                
                # Execute batch concurrently
                print(f"\nBatch {batch_num}: Launching {num_users} users...")
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in batch_results:
                    if isinstance(result, dict):
                        stage_results.append(result)
                    else:
                        self.errors.append({
                            "batch": batch_num,
                            "error": str(result),
                            "timestamp": datetime.now().isoformat()
                        })
                
                # Progress update
                elapsed = time.time() - stage_start
                remaining = stage_end - time.time()
                successful = sum(1 for r in stage_results if r.get("success", False))
                
                print(f"Progress: {elapsed:.1f}s elapsed, {remaining:.1f}s remaining")
                print(f"Success rate: {successful}/{len(stage_results)} "
                      f"({successful/len(stage_results)*100:.1f}%)")
                
                # Maintain consistent load
                batch_duration = time.time() - batch_start
                if batch_duration < 2 and remaining > 2:
                    await asyncio.sleep(2 - batch_duration)
        
        # Calculate metrics
        metrics = self._calculate_metrics(
            stage_results, 
            stage_name, 
            num_users,
            process,
            initial_connections
        )
        
        self.metrics_history.append(metrics)
        self._print_stage_summary(metrics)
        
        return metrics
    
    def _calculate_metrics(self, results: List[Dict], stage_name: str, 
                          num_users: int, process, initial_connections: int) -> TestMetrics:
        """Calculate comprehensive metrics for a test stage."""
        # Extract all request timings
        all_timings = []
        successful_requests = 0
        failed_requests = 0
        
        for result in results:
            for request in result.get("requests", []):
                all_timings.append(request["duration_ms"])
                if request["status"] < 400:
                    successful_requests += 1
                else:
                    failed_requests += 1
            
            failed_requests += len(result.get("errors", []))
        
        total_requests = successful_requests + failed_requests
        
        # Calculate response time statistics
        if all_timings:
            avg_time = statistics.mean(all_timings)
            p50_time = statistics.median(all_timings)
            p95_time = statistics.quantiles(all_timings, n=20)[18] if len(all_timings) > 20 else max(all_timings)
            p99_time = statistics.quantiles(all_timings, n=100)[98] if len(all_timings) > 100 else max(all_timings)
            max_time = max(all_timings)
        else:
            avg_time = p50_time = p95_time = p99_time = max_time = 0
        
        # Calculate throughput
        total_duration = max(r.get("total_duration_ms", 0) for r in results) / 1000 if results else 1
        rps = total_requests / total_duration if total_duration > 0 else 0
        
        # System metrics
        cpu_percent = process.cpu_percent()
        memory_percent = process.memory_percent()
        current_connections = len(process.net_connections())
        active_connections = current_connections - initial_connections
        
        return TestMetrics(
            timestamp=datetime.now().isoformat(),
            stage=stage_name,
            total_users=num_users,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time_ms=avg_time,
            p50_response_time_ms=p50_time,
            p95_response_time_ms=p95_time,
            p99_response_time_ms=p99_time,
            max_response_time_ms=max_time,
            requests_per_second=rps,
            error_rate_percent=(failed_requests / total_requests * 100) if total_requests > 0 else 0,
            cpu_usage_percent=cpu_percent,
            memory_usage_percent=memory_percent,
            active_connections=active_connections
        )
    
    def _print_stage_summary(self, metrics: TestMetrics):
        """Print summary of stage results."""
        print(f"\n📊 {metrics.stage} Results:")
        print(f"{'='*60}")
        print(f"Total Requests: {metrics.total_requests}")
        print(f"Successful: {metrics.successful_requests} "
              f"({metrics.successful_requests/metrics.total_requests*100:.1f}%)")
        print(f"Failed: {metrics.failed_requests} "
              f"({metrics.error_rate_percent:.1f}%)")
        
        print(f"\n⏱️  Response Times:")
        print(f"  Average: {metrics.avg_response_time_ms:.2f} ms")
        print(f"  Median (p50): {metrics.p50_response_time_ms:.2f} ms")
        print(f"  p95: {metrics.p95_response_time_ms:.2f} ms")
        print(f"  p99: {metrics.p99_response_time_ms:.2f} ms")
        print(f"  Max: {metrics.max_response_time_ms:.2f} ms")
        
        print(f"\n🚀 Performance:")
        print(f"  Throughput: {metrics.requests_per_second:.2f} req/s")
        print(f"  CPU Usage: {metrics.cpu_usage_percent:.1f}%")
        print(f"  Memory Usage: {metrics.memory_usage_percent:.1f}%")
        print(f"  Active Connections: {metrics.active_connections}")
        
        # Performance verdict
        if metrics.error_rate_percent > 5:
            print(f"\n❌ High error rate detected!")
        elif metrics.p95_response_time_ms > 2000:
            print(f"\n⚠️  Response times exceeding targets")
        else:
            print(f"\n✅ Performance within acceptable limits")
    
    async def run_progressive_load_test(self):
        """Run progressive load test from 200 to 500 users."""
        self.start_time = time.time()
        
        print("🎯 NGX Voice Sales Agent - Progressive Load Test (200-500 users)")
        print("=" * 80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Check system is ready
        if not await self._check_system_ready():
            print("❌ System not ready for testing. Please ensure API is running.")
            return
        
        # Progressive load stages
        stages = [
            {"users": 200, "name": "Stage 1: Baseline Load", "duration": 120},
            {"users": 300, "name": "Stage 2: Moderate Stress", "duration": 120},
            {"users": 400, "name": "Stage 3: High Load", "duration": 90},
            {"users": 500, "name": "Stage 4: Extreme Load", "duration": 60}
        ]
        
        for stage in stages:
            metrics = await self.run_load_stage(
                num_users=stage["users"],
                stage_name=stage["name"],
                duration_seconds=stage["duration"]
            )
            
            # Check if we should continue
            if metrics.error_rate_percent > 20:
                print(f"\n🛑 Stopping test - error rate too high: {metrics.error_rate_percent:.1f}%")
                break
            
            # Cool down between stages
            if stage != stages[-1]:
                print(f"\n⏸️  Cooling down for 30 seconds...")
                await asyncio.sleep(30)
        
        # Generate final report
        self._generate_final_report()
    
    async def _check_system_ready(self) -> bool:
        """Check if system is ready for load testing."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as resp:
                    if resp.status == 200:
                        print("✅ API health check passed")
                        return True
                    else:
                        print(f"❌ API health check failed: {resp.status}")
                        return False
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            return False
    
    def _generate_final_report(self):
        """Generate comprehensive final report."""
        total_duration = time.time() - self.start_time
        
        print("\n" + "=" * 80)
        print("📊 PROGRESSIVE LOAD TEST - FINAL REPORT")
        print("=" * 80)
        print(f"Total Duration: {total_duration/60:.2f} minutes")
        print(f"Stages Completed: {len(self.metrics_history)}")
        
        # Summary table
        print("\n📈 Performance Summary by Stage:")
        print(f"{'Stage':<30} {'Users':<10} {'Error %':<10} {'Avg ms':<10} {'p95 ms':<10} {'RPS':<10}")
        print("-" * 80)
        
        for metrics in self.metrics_history:
            print(f"{metrics.stage:<30} {metrics.total_users:<10} "
                  f"{metrics.error_rate_percent:<10.1f} {metrics.avg_response_time_ms:<10.0f} "
                  f"{metrics.p95_response_time_ms:<10.0f} {metrics.requests_per_second:<10.1f}")
        
        # Identify performance limits
        print("\n🎯 Performance Analysis:")
        
        # Find breaking point
        breaking_point = None
        for metrics in self.metrics_history:
            if metrics.error_rate_percent > 5 or metrics.p95_response_time_ms > 2000:
                breaking_point = metrics.total_users
                break
        
        if breaking_point:
            print(f"  ⚠️  Performance degradation starts at: {breaking_point} users")
        else:
            print(f"  ✅ System handled all tested loads successfully")
        
        # Maximum successful load
        successful_stages = [m for m in self.metrics_history if m.error_rate_percent < 5]
        if successful_stages:
            max_successful = max(m.total_users for m in successful_stages)
            print(f"  ✅ Maximum successful concurrent users: {max_successful}")
        
        # Best performance metrics
        if self.metrics_history:
            best_rps = max(m.requests_per_second for m in self.metrics_history)
            best_response = min(m.avg_response_time_ms for m in self.metrics_history)
            print(f"  🚀 Peak throughput achieved: {best_rps:.1f} req/s")
            print(f"  ⚡ Best average response time: {best_response:.0f} ms")
        
        # Recommendations
        print("\n💡 Recommendations:")
        
        if breaking_point and breaking_point <= 300:
            print("  1. Optimize database queries and connection pooling")
            print("  2. Increase Redis cache coverage")
            print("  3. Consider horizontal scaling")
        elif breaking_point and breaking_point <= 400:
            print("  1. System performs well under moderate load")
            print("  2. Consider implementing auto-scaling for peak loads")
            print("  3. Monitor database connection limits")
        else:
            print("  1. Excellent performance across all tested loads")
            print("  2. System is ready for production deployment")
            print("  3. Continue monitoring for optimization opportunities")
        
        # Save detailed report
        self._save_detailed_report(total_duration)
    
    def _save_detailed_report(self, total_duration: float):
        """Save detailed test report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/performance/results/load_test_200_plus_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        report = {
            "test_name": "Progressive Load Test 200-500 Users",
            "timestamp": timestamp,
            "total_duration_minutes": total_duration / 60,
            "stages": [asdict(m) for m in self.metrics_history],
            "summary": {
                "stages_completed": len(self.metrics_history),
                "max_users_tested": max(m.total_users for m in self.metrics_history) if self.metrics_history else 0,
                "overall_success_rate": (
                    sum(m.successful_requests for m in self.metrics_history) / 
                    sum(m.total_requests for m in self.metrics_history) * 100
                ) if self.metrics_history else 0,
                "errors_encountered": len(self.errors)
            },
            "errors": self.errors[:50]  # First 50 errors
        }
        
        with open(filename, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {filename}")
        
        # Also create a summary CSV for easy analysis
        csv_filename = filename.replace(".json", ".csv")
        with open(csv_filename, "w") as f:
            f.write("Stage,Users,Total Requests,Success Rate,Error Rate,Avg Response,p95 Response,p99 Response,RPS\n")
            for m in self.metrics_history:
                f.write(f"{m.stage},{m.total_users},{m.total_requests},"
                       f"{100-m.error_rate_percent:.1f},{m.error_rate_percent:.1f},"
                       f"{m.avg_response_time_ms:.0f},{m.p95_response_time_ms:.0f},"
                       f"{m.p99_response_time_ms:.0f},{m.requests_per_second:.1f}\n")
        
        print(f"💾 Summary CSV saved to: {csv_filename}")


async def main():
    """Run the progressive load test."""
    tester = NGXLoadTester200Plus()
    await tester.run_progressive_load_test()


if __name__ == "__main__":
    print("🚀 NGX Voice Sales Agent - Enhanced Load Testing (200+ Users)")
    print("This test will progressively increase load from 200 to 500 users.")
    print("Ensure your system is ready and monitoring is active.")
    print("Press Ctrl+C to cancel...\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")