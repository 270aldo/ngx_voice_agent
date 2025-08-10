#!/usr/bin/env python3
"""
Automated test suite for NGX Voice Sales Agent CI/CD pipeline.
Runs all advanced tests and generates a comprehensive report.
"""

import asyncio
import subprocess
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Tuple
import argparse

class TestSuite:
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0
            },
            "duration": 0
        }
        
    async def check_api_health(self) -> bool:
        """Check if API is running and healthy."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/health") as response:
                    return response.status == 200
        except:
            return False
    
    def run_test(self, test_name: str, command: List[str], timeout: int = 300) -> Dict[str, Any]:
        """Run a single test and capture results."""
        print(f"\n{'='*60}")
        print(f"🧪 Running: {test_name}")
        print(f"{'='*60}")
        
        start_time = datetime.now()
        
        try:
            # Run test with timeout
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # Parse output for test results
            success = result.returncode == 0
            output_lines = result.stdout.split('\n')
            
            # Extract key metrics from output
            metrics = self.extract_metrics(output_lines)
            
            test_result = {
                "name": test_name,
                "status": "passed" if success else "failed",
                "duration": duration,
                "exit_code": result.returncode,
                "metrics": metrics,
                "errors": result.stderr.split('\n')[:10] if result.stderr else []
            }
            
            # Print summary
            print(f"\n✅ Test completed in {duration:.1f}s")
            if metrics:
                print(f"📊 Key metrics:")
                for key, value in metrics.items():
                    print(f"   - {key}: {value}")
            
        except subprocess.TimeoutExpired:
            test_result = {
                "name": test_name,
                "status": "timeout",
                "duration": timeout,
                "error": f"Test timed out after {timeout}s"
            }
            print(f"\n⏱️  Test timed out after {timeout}s")
            
        except Exception as e:
            test_result = {
                "name": test_name,
                "status": "error",
                "error": str(e)
            }
            print(f"\n❌ Test error: {e}")
        
        return test_result
    
    def extract_metrics(self, output_lines: List[str]) -> Dict[str, Any]:
        """Extract key metrics from test output."""
        metrics = {}
        
        for line in output_lines:
            # Success rate
            if "success rate:" in line.lower() or "% success" in line:
                try:
                    import re
                    match = re.search(r'(\d+\.?\d*)%', line)
                    if match:
                        metrics["success_rate"] = float(match.group(1))
                except:
                    pass
            
            # Throughput
            if "req/s" in line or "requests/second" in line.lower():
                try:
                    import re
                    match = re.search(r'(\d+\.?\d*)\s*req/s', line, re.IGNORECASE)
                    if match:
                        metrics["throughput"] = float(match.group(1))
                except:
                    pass
            
            # Response time
            if "average response" in line.lower() or "avg response" in line.lower():
                try:
                    import re
                    match = re.search(r'(\d+\.?\d*)\s*ms', line)
                    if match:
                        metrics["avg_response_ms"] = float(match.group(1))
                except:
                    pass
            
            # Memory usage
            if "memory" in line.lower() and "mb" in line.lower():
                try:
                    import re
                    match = re.search(r'(\d+\.?\d*)\s*MB', line, re.IGNORECASE)
                    if match:
                        metrics["memory_mb"] = float(match.group(1))
                except:
                    pass
        
        return metrics
    
    async def run_all_tests(self, test_filter: str = None):
        """Run all tests in the suite."""
        start_time = datetime.now()
        
        # Check API health first
        print("🏥 Checking API health...")
        if not await self.check_api_health():
            print("❌ API is not healthy! Please start the API server first.")
            sys.exit(1)
        print("✅ API is healthy\n")
        
        # Define test suite
        tests = [
            {
                "name": "Unit Tests",
                "command": ["pytest", "tests/unit/", "-v", "--tb=short"],
                "timeout": 300,
                "category": "unit"
            },
            {
                "name": "Integration Tests",
                "command": ["pytest", "tests/integration/", "-v", "--tb=short"],
                "timeout": 300,
                "category": "integration"
            },
            {
                "name": "Load Test (200 users)",
                "command": ["python", "tests/performance/final_load_test.py"],
                "timeout": 120,
                "category": "performance"
            },
            {
                "name": "Circuit Breaker Tests",
                "command": ["python", "tests/resilience/test_circuit_breakers.py"],
                "timeout": 180,
                "category": "resilience"
            },
            {
                "name": "Security Tests",
                "command": ["python", "tests/security/penetration_test.py"],
                "timeout": 300,
                "category": "security"
            },
            {
                "name": "Endurance Test (10 min)",
                "command": ["python", "tests/performance/endurance_test.py", "--hours", "0.167"],
                "timeout": 700,
                "category": "endurance"
            },
            {
                "name": "Stress Test (1000+ users)",
                "command": ["python", "tests/performance/stress_test_1000.py"],
                "timeout": 600,
                "category": "stress"
            }
        ]
        
        # Filter tests if requested
        if test_filter:
            tests = [t for t in tests if test_filter.lower() in t["category"].lower() or test_filter.lower() in t["name"].lower()]
        
        # Run each test
        for test in tests:
            result = self.run_test(test["name"], test["command"], test["timeout"])
            self.results["tests"][test["name"]] = result
            
            # Update summary
            self.results["summary"]["total"] += 1
            if result["status"] == "passed":
                self.results["summary"]["passed"] += 1
            elif result["status"] == "failed":
                self.results["summary"]["failed"] += 1
            elif result["status"] == "timeout":
                self.results["summary"]["failed"] += 1
            else:
                self.results["summary"]["skipped"] += 1
        
        # Calculate duration
        self.results["duration"] = (datetime.now() - start_time).total_seconds()
    
    def generate_report(self):
        """Generate test report."""
        print(f"\n{'='*60}")
        print("📊 TEST SUITE SUMMARY")
        print(f"{'='*60}")
        
        # Overall summary
        total = self.results["summary"]["total"]
        passed = self.results["summary"]["passed"]
        failed = self.results["summary"]["failed"]
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Pass Rate: {pass_rate:.1f}%")
        print(f"⏱️  Duration: {self.results['duration']:.1f}s")
        
        # Individual test results
        print(f"\n{'Test Name':<30} {'Status':<10} {'Duration':<10} {'Key Metric'}")
        print("-" * 70)
        
        for test_name, result in self.results["tests"].items():
            status_emoji = "✅" if result["status"] == "passed" else "❌"
            duration = f"{result.get('duration', 0):.1f}s"
            
            # Get key metric
            key_metric = ""
            if result.get("metrics"):
                if "success_rate" in result["metrics"]:
                    key_metric = f"{result['metrics']['success_rate']:.1f}% success"
                elif "throughput" in result["metrics"]:
                    key_metric = f"{result['metrics']['throughput']:.1f} req/s"
            
            print(f"{test_name:<30} {status_emoji} {result['status']:<8} {duration:<10} {key_metric}")
        
        # Failed test details
        if failed > 0:
            print(f"\n{'='*60}")
            print("❌ FAILED TEST DETAILS")
            print(f"{'='*60}")
            
            for test_name, result in self.results["tests"].items():
                if result["status"] != "passed":
                    print(f"\n{test_name}:")
                    if result.get("error"):
                        print(f"  Error: {result['error']}")
                    if result.get("errors"):
                        print(f"  Stderr: {result['errors'][0]}")
        
        # Recommendations
        print(f"\n{'='*60}")
        print("💡 RECOMMENDATIONS")
        print(f"{'='*60}")
        
        if pass_rate < 100:
            print("- Fix failing tests before deployment")
        
        # Check performance metrics
        perf_tests = [r for r in self.results["tests"].values() if r.get("metrics", {}).get("success_rate")]
        if perf_tests:
            avg_success = sum(r["metrics"]["success_rate"] for r in perf_tests) / len(perf_tests)
            if avg_success < 95:
                print(f"- Performance tests show {avg_success:.1f}% success rate. Consider optimization.")
        
        # Save detailed report
        os.makedirs("results", exist_ok=True)
        report_file = f"results/test_suite_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {report_file}")
        
        # Return exit code
        return 0 if failed == 0 else 1
    
    def generate_junit_xml(self):
        """Generate JUnit XML report for CI/CD integration."""
        try:
            import xml.etree.ElementTree as ET
            
            # Create test suite element
            testsuite = ET.Element("testsuite")
            testsuite.set("name", "NGX Voice Sales Agent Test Suite")
            testsuite.set("tests", str(self.results["summary"]["total"]))
            testsuite.set("failures", str(self.results["summary"]["failed"]))
            testsuite.set("time", str(self.results["duration"]))
            testsuite.set("timestamp", self.results["timestamp"])
            
            # Add test cases
            for test_name, result in self.results["tests"].items():
                testcase = ET.SubElement(testsuite, "testcase")
                testcase.set("name", test_name)
                testcase.set("time", str(result.get("duration", 0)))
                
                if result["status"] != "passed":
                    failure = ET.SubElement(testcase, "failure")
                    failure.set("type", result["status"])
                    failure.text = result.get("error", "Test failed")
            
            # Write XML
            tree = ET.ElementTree(testsuite)
            xml_file = f"results/junit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
            tree.write(xml_file, encoding="utf-8", xml_declaration=True)
            
            print(f"📄 JUnit XML report saved to: {xml_file}")
            
        except Exception as e:
            print(f"⚠️  Could not generate JUnit XML: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Run NGX test suite")
    parser.add_argument("--filter", help="Filter tests by category or name")
    parser.add_argument("--junit", action="store_true", help="Generate JUnit XML report")
    parser.add_argument("--url", default="http://localhost:8000", help="API URL")
    args = parser.parse_args()
    
    # Run test suite
    suite = TestSuite(api_url=args.url)
    await suite.run_all_tests(test_filter=args.filter)
    
    # Generate reports
    exit_code = suite.generate_report()
    
    if args.junit:
        suite.generate_junit_xml()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())