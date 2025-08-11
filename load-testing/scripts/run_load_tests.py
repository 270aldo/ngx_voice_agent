#!/usr/bin/env python3
"""
Script to run comprehensive load tests for NGX Voice Sales Agent.

This script orchestrates different load test scenarios and collects
performance metrics for analysis.
"""

import os
import sys
import subprocess
import time
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LoadTestRunner:
    """Orchestrates load test execution and metrics collection."""
    
    def __init__(self, host: str = "http://localhost:8000", output_dir: str = "results"):
        self.host = host
        self.output_dir = output_dir
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_path = os.path.join(output_dir, self.timestamp)
        
        # Create results directory
        os.makedirs(self.results_path, exist_ok=True)
        
        # Test scenarios
        self.scenarios = {
            "baseline": {
                "users": 10,
                "spawn_rate": 2,
                "run_time": "2m",
                "description": "Baseline test with light load"
            },
            "normal": {
                "users": 50,
                "spawn_rate": 5,
                "run_time": "5m",
                "description": "Normal expected load"
            },
            "peak": {
                "users": 100,
                "spawn_rate": 10,
                "run_time": "5m",
                "description": "Peak hour simulation"
            },
            "stress": {
                "users": 200,
                "spawn_rate": 20,
                "run_time": "5m",
                "description": "Stress test beyond expected capacity"
            },
            "spike": {
                "class": "SpikeLoadShape",
                "run_time": "6m",
                "description": "Sudden spike in traffic"
            },
            "step": {
                "class": "StepLoadShape",
                "run_time": "10m",
                "description": "Gradual increase to find limits"
            },
            "realistic": {
                "class": "RealisticLoadShape",
                "run_time": "12m",
                "description": "Daily traffic pattern simulation"
            }
        }
    
    def check_system_health(self) -> bool:
        """Check if the system is healthy before testing."""
        try:
            response = requests.get(f"{self.host}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "healthy"
        except Exception as e:
            print(f"Health check failed: {e}")
        return False
    
    def collect_baseline_metrics(self) -> Dict[str, Any]:
        """Collect baseline system metrics."""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu_usage": self._get_cpu_usage(),
            "memory_usage": self._get_memory_usage(),
            "active_connections": self._get_active_connections(),
            "cache_stats": self._get_cache_stats(),
            "circuit_breaker_status": self._get_circuit_breaker_status()
        }
        return metrics
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage."""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except ImportError:
            return 0.0
    
    def _get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                "total": mem.total,
                "used": mem.used,
                "percent": mem.percent
            }
        except ImportError:
            return {"total": 0, "used": 0, "percent": 0}
    
    def _get_active_connections(self) -> int:
        """Get number of active connections."""
        try:
            response = requests.get(f"{self.host}/metrics/connections", timeout=2)
            if response.status_code == 200:
                return response.json().get("active_connections", 0)
        except:
            pass
        return 0
    
    def _get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            response = requests.get(f"{self.host}/cache/stats", timeout=2)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return {"hit_rate": 0, "total_keys": 0}
    
    def _get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        try:
            response = requests.get(f"{self.host}/metrics/circuit-breakers", timeout=2)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return {"healthy": True, "open_circuits": []}
    
    def run_scenario(self, scenario_name: str, scenario_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single load test scenario."""
        print(f"\n{'='*60}")
        print(f"Running scenario: {scenario_name}")
        print(f"Description: {scenario_config['description']}")
        print(f"{'='*60}")
        
        # Build locust command
        cmd = [
            "locust",
            "-f", "locustfile.py",
            "--host", self.host,
            "--headless",
            "--run-time", scenario_config.get("run_time", "5m"),
            "--html", os.path.join(self.results_path, f"{scenario_name}_report.html"),
            "--csv", os.path.join(self.results_path, f"{scenario_name}_stats"),
            "--logfile", os.path.join(self.results_path, f"{scenario_name}_log.txt")
        ]
        
        # Add user count or load shape
        if "class" in scenario_config:
            # Custom load shape
            cmd.extend([
                "-f", f"scenarios/stress_test_scenario.py",
                "--class-picker",
                f"--locustfile", f"scenarios/stress_test_scenario.py:{scenario_config['class']}"
            ])
        else:
            # Fixed user count
            cmd.extend([
                "--users", str(scenario_config["users"]),
                "--spawn-rate", str(scenario_config["spawn_rate"])
            ])
        
        # Collect metrics before test
        pre_metrics = self.collect_baseline_metrics()
        
        # Run the test
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = time.time() - start_time
        
        # Collect metrics after test
        post_metrics = self.collect_baseline_metrics()
        
        # Parse results
        stats_file = os.path.join(self.results_path, f"{scenario_name}_stats_stats.csv")
        stats_data = None
        if os.path.exists(stats_file):
            stats_data = pd.read_csv(stats_file)
        
        return {
            "scenario": scenario_name,
            "config": scenario_config,
            "duration": duration,
            "pre_metrics": pre_metrics,
            "post_metrics": post_metrics,
            "stats": stats_data.to_dict() if stats_data is not None else None,
            "exit_code": result.returncode,
            "errors": result.stderr if result.returncode != 0 else None
        }
    
    def analyze_results(self, results: List[Dict[str, Any]]):
        """Analyze and visualize test results."""
        print(f"\n{'='*60}")
        print("Test Results Analysis")
        print(f"{'='*60}")
        
        # Create summary report
        summary = {
            "test_run": self.timestamp,
            "host": self.host,
            "scenarios_run": len(results),
            "total_duration": sum(r["duration"] for r in results),
            "results": []
        }
        
        for result in results:
            scenario_summary = {
                "scenario": result["scenario"],
                "description": result["config"]["description"],
                "duration": result["duration"],
                "success": result["exit_code"] == 0
            }
            
            if result["stats"]:
                stats_df = pd.DataFrame(result["stats"])
                if not stats_df.empty and "Type" in stats_df.columns:
                    aggregated = stats_df[stats_df["Type"] == "Aggregated"]
                    if not aggregated.empty:
                        row = aggregated.iloc[0]
                        scenario_summary.update({
                            "total_requests": row.get("Request Count", 0),
                            "failure_rate": row.get("Failure Count", 0) / max(row.get("Request Count", 1), 1) * 100,
                            "avg_response_time": row.get("Average Response Time", 0),
                            "p95_response_time": row.get("95%", 0),
                            "p99_response_time": row.get("99%", 0),
                            "requests_per_second": row.get("Requests/s", 0)
                        })
            
            summary["results"].append(scenario_summary)
        
        # Save summary
        with open(os.path.join(self.results_path, "summary.json"), "w") as f:
            json.dump(summary, f, indent=2)
        
        # Create visualizations
        self._create_visualizations(summary)
        
        # Print summary
        self._print_summary(summary)
        
        return summary
    
    def _create_visualizations(self, summary: Dict[str, Any]):
        """Create visualization charts."""
        results_df = pd.DataFrame(summary["results"])
        
        if results_df.empty:
            return
        
        # Set up the plot style
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'Load Test Results - {self.timestamp}', fontsize=16)
        
        # 1. Response times by scenario
        if "avg_response_time" in results_df.columns:
            ax = axes[0, 0]
            scenarios = results_df["scenario"]
            x_pos = range(len(scenarios))
            
            ax.bar(x_pos, results_df["avg_response_time"], label="Average", alpha=0.7)
            if "p95_response_time" in results_df.columns:
                ax.bar(x_pos, results_df["p95_response_time"], label="P95", alpha=0.5)
            if "p99_response_time" in results_df.columns:
                ax.bar(x_pos, results_df["p99_response_time"], label="P99", alpha=0.3)
            
            ax.set_xlabel("Scenario")
            ax.set_ylabel("Response Time (ms)")
            ax.set_title("Response Times by Scenario")
            ax.set_xticks(x_pos)
            ax.set_xticklabels(scenarios, rotation=45)
            ax.legend()
        
        # 2. Failure rates
        if "failure_rate" in results_df.columns:
            ax = axes[0, 1]
            ax.bar(range(len(results_df)), results_df["failure_rate"], color='red', alpha=0.7)
            ax.set_xlabel("Scenario")
            ax.set_ylabel("Failure Rate (%)")
            ax.set_title("Failure Rates by Scenario")
            ax.set_xticks(range(len(results_df)))
            ax.set_xticklabels(results_df["scenario"], rotation=45)
            ax.axhline(y=1, color='g', linestyle='--', label='1% Target')
            ax.legend()
        
        # 3. Throughput
        if "requests_per_second" in results_df.columns:
            ax = axes[1, 0]
            ax.plot(range(len(results_df)), results_df["requests_per_second"], 'o-', markersize=10)
            ax.set_xlabel("Scenario")
            ax.set_ylabel("Requests/Second")
            ax.set_title("Throughput by Scenario")
            ax.set_xticks(range(len(results_df)))
            ax.set_xticklabels(results_df["scenario"], rotation=45)
            ax.grid(True, alpha=0.3)
        
        # 4. Success vs Failure pie chart
        if "success" in results_df.columns:
            ax = axes[1, 1]
            success_count = results_df["success"].sum()
            failure_count = len(results_df) - success_count
            
            if success_count > 0 or failure_count > 0:
                ax.pie([success_count, failure_count], 
                      labels=['Successful', 'Failed'],
                      colors=['green', 'red'],
                      autopct='%1.1f%%',
                      startangle=90)
                ax.set_title("Scenario Success Rate")
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.results_path, "results_visualization.png"), dpi=300)
        plt.close()
    
    def _print_summary(self, summary: Dict[str, Any]):
        """Print summary to console."""
        print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total duration: {summary['total_duration']:.1f} seconds")
        print(f"\nScenario Results:")
        print(f"{'Scenario':<15} {'Status':<10} {'Requests':<10} {'Fail %':<8} {'Avg RT':<10} {'RPS':<8}")
        print("-" * 70)
        
        for result in summary["results"]:
            status = "✓ Pass" if result["success"] else "✗ Fail"
            requests = result.get("total_requests", "N/A")
            fail_rate = f"{result.get('failure_rate', 0):.1f}%" if "failure_rate" in result else "N/A"
            avg_rt = f"{result.get('avg_response_time', 0):.0f}ms" if "avg_response_time" in result else "N/A"
            rps = f"{result.get('requests_per_second', 0):.1f}" if "requests_per_second" in result else "N/A"
            
            print(f"{result['scenario']:<15} {status:<10} {str(requests):<10} {fail_rate:<8} {avg_rt:<10} {rps:<8}")
        
        print(f"\nResults saved to: {self.results_path}")
    
    def run_all_tests(self, scenarios: List[str] = None):
        """Run all or specified test scenarios."""
        # Check system health
        if not self.check_system_health():
            print("System health check failed. Aborting tests.")
            return None
        
        # Select scenarios to run
        scenarios_to_run = scenarios if scenarios else list(self.scenarios.keys())
        
        # Run each scenario
        results = []
        for scenario_name in scenarios_to_run:
            if scenario_name in self.scenarios:
                result = self.run_scenario(scenario_name, self.scenarios[scenario_name])
                results.append(result)
                
                # Wait between scenarios
                print(f"\nWaiting 30 seconds before next scenario...")
                time.sleep(30)
        
        # Analyze all results
        return self.analyze_results(results)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run load tests for NGX Voice Sales Agent")
    parser.add_argument("--host", default="http://localhost:8000", help="Target host URL")
    parser.add_argument("--output", default="results", help="Output directory for results")
    parser.add_argument("--scenarios", nargs="+", help="Specific scenarios to run")
    
    args = parser.parse_args()
    
    # Create runner
    runner = LoadTestRunner(host=args.host, output_dir=args.output)
    
    # Run tests
    runner.run_all_tests(scenarios=args.scenarios)


if __name__ == "__main__":
    main()