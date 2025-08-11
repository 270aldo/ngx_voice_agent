"""
Load Test Configuration and Setup Verification

Ensures the environment is ready for load testing.
"""

import os
import sys
import asyncio
import aiohttp
from typing import Dict, Any, Tuple
import psutil
import platform


class LoadTestConfig:
    """Configuration and verification for load tests."""
    
    # Performance targets
    TARGETS = {
        "response_time_p95_ms": 500,
        "success_rate_percent": 99,
        "cache_hit_rate_percent": 60,
        "requests_per_second": 100
    }
    
    # System requirements
    MIN_REQUIREMENTS = {
        "memory_gb": 4,
        "cpu_cores": 2,
        "free_disk_gb": 2
    }
    
    # Test endpoints
    ENDPOINTS = {
        "health": "/health",
        "conversation": "/api/v1/conversation/message",
        "metrics": "/api/v1/metrics"
    }
    
    @staticmethod
    def check_system_resources() -> Tuple[bool, Dict[str, Any]]:
        """Check if system has enough resources for load testing."""
        # Get system info
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_count = psutil.cpu_count()
        
        resources = {
            "memory_gb": memory.total / (1024**3),
            "memory_available_gb": memory.available / (1024**3),
            "memory_percent": memory.percent,
            "cpu_cores": cpu_count,
            "cpu_percent": psutil.cpu_percent(interval=1),
            "disk_free_gb": disk.free / (1024**3),
            "disk_percent": disk.percent,
            "platform": platform.platform()
        }
        
        # Check minimums
        meets_requirements = (
            resources["memory_available_gb"] >= LoadTestConfig.MIN_REQUIREMENTS["memory_gb"] and
            resources["cpu_cores"] >= LoadTestConfig.MIN_REQUIREMENTS["cpu_cores"] and
            resources["disk_free_gb"] >= LoadTestConfig.MIN_REQUIREMENTS["free_disk_gb"]
        )
        
        return meets_requirements, resources
    
    @staticmethod
    async def verify_service_health(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
        """Verify all required services are healthy."""
        results = {}
        
        async with aiohttp.ClientSession() as session:
            # Check health endpoint
            try:
                async with session.get(f"{base_url}{LoadTestConfig.ENDPOINTS['health']}") as resp:
                    results["health"] = {
                        "status": resp.status,
                        "healthy": resp.status == 200,
                        "data": await resp.json() if resp.status == 200 else None
                    }
            except Exception as e:
                results["health"] = {
                    "status": 0,
                    "healthy": False,
                    "error": str(e)
                }
            
            # Check conversation endpoint (OPTIONS)
            try:
                async with session.options(f"{base_url}{LoadTestConfig.ENDPOINTS['conversation']}") as resp:
                    results["conversation"] = {
                        "status": resp.status,
                        "available": resp.status in [200, 204],
                    }
            except Exception as e:
                results["conversation"] = {
                    "status": 0,
                    "available": False,
                    "error": str(e)
                }
        
        # Overall health
        results["all_healthy"] = (
            results.get("health", {}).get("healthy", False) and
            results.get("conversation", {}).get("available", False)
        )
        
        return results
    
    @staticmethod
    def generate_load_test_scenarios() -> Dict[str, Any]:
        """Generate different load test scenarios."""
        return {
            "smoke_test": {
                "name": "Smoke Test",
                "description": "Quick validation test",
                "users": 5,
                "ramp_up": 2,
                "duration": 30
            },
            "load_test": {
                "name": "Standard Load Test", 
                "description": "Normal expected load",
                "users": 100,
                "ramp_up": 30,
                "duration": 300
            },
            "stress_test": {
                "name": "Stress Test",
                "description": "Above normal load",
                "users": 500,
                "ramp_up": 60,
                "duration": 600
            },
            "spike_test": {
                "name": "Spike Test",
                "description": "Sudden traffic spike",
                "users": 1000,
                "ramp_up": 10,
                "duration": 300
            },
            "endurance_test": {
                "name": "Endurance Test",
                "description": "Sustained load over time",
                "users": 200,
                "ramp_up": 60,
                "duration": 3600
            }
        }
    
    @staticmethod
    async def pre_test_checklist() -> Tuple[bool, Dict[str, Any]]:
        """Run pre-test checklist."""
        checklist = {
            "timestamp": asyncio.get_event_loop().time(),
            "checks": {}
        }
        
        # 1. Check system resources
        resources_ok, resources = LoadTestConfig.check_system_resources()
        checklist["checks"]["system_resources"] = {
            "passed": resources_ok,
            "details": resources
        }
        
        # 2. Check service health
        service_health = await LoadTestConfig.verify_service_health()
        checklist["checks"]["service_health"] = {
            "passed": service_health["all_healthy"],
            "details": service_health
        }
        
        # 3. Check environment variables
        required_env = ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY"]
        env_check = all(os.getenv(var) for var in required_env)
        checklist["checks"]["environment"] = {
            "passed": env_check,
            "missing": [var for var in required_env if not os.getenv(var)]
        }
        
        # Overall status
        all_passed = all(
            check["passed"] for check in checklist["checks"].values()
        )
        
        return all_passed, checklist
    
    @staticmethod
    def print_pre_test_report(checklist: Dict[str, Any]):
        """Print formatted pre-test checklist report."""
        print("\n" + "="*60)
        print("PRE-LOAD TEST CHECKLIST")
        print("="*60)
        
        for check_name, check_data in checklist["checks"].items():
            status = "✅ PASS" if check_data["passed"] else "❌ FAIL"
            print(f"\n{check_name.upper()}: {status}")
            
            if check_name == "system_resources":
                details = check_data["details"]
                print(f"  - CPU Cores: {details['cpu_cores']}")
                print(f"  - CPU Usage: {details['cpu_percent']:.1f}%")
                print(f"  - Memory Available: {details['memory_available_gb']:.1f} GB")
                print(f"  - Disk Free: {details['disk_free_gb']:.1f} GB")
            
            elif check_name == "service_health":
                for service, health in check_data["details"].items():
                    if service != "all_healthy":
                        status = "✅" if health.get("healthy") or health.get("available") else "❌"
                        print(f"  - {service}: {status}")
            
            elif check_name == "environment":
                if check_data.get("missing"):
                    print(f"  - Missing: {', '.join(check_data['missing'])}")
        
        print("\n" + "="*60)


async def main():
    """Run pre-test verification."""
    print("🔍 Running pre-load test verification...")
    
    passed, checklist = await LoadTestConfig.pre_test_checklist()
    LoadTestConfig.print_pre_test_report(checklist)
    
    if passed:
        print("\n✅ All checks passed! Ready for load testing.")
        print("\nAvailable test scenarios:")
        for scenario_id, scenario in LoadTestConfig.generate_load_test_scenarios().items():
            print(f"  - {scenario_id}: {scenario['name']} ({scenario['users']} users)")
    else:
        print("\n❌ Some checks failed. Please fix issues before running load tests.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())