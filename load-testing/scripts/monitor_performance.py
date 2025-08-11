#!/usr/bin/env python3
"""
Real-time performance monitoring during load tests.

This script monitors system metrics and displays them in real-time
while load tests are running.
"""

import os
import sys
import time
import json
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any, List
import threading
from collections import deque
import statistics

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available. System metrics will be limited.")


class PerformanceMonitor:
    """Real-time performance monitoring for load tests."""
    
    def __init__(self, host: str = "http://localhost:8000", interval: int = 1):
        self.host = host
        self.interval = interval
        self.running = False
        self.metrics_history = {
            "timestamp": deque(maxlen=300),  # 5 minutes of history
            "response_time": deque(maxlen=300),
            "error_rate": deque(maxlen=300),
            "requests_per_second": deque(maxlen=300),
            "cpu_usage": deque(maxlen=300),
            "memory_usage": deque(maxlen=300),
            "active_connections": deque(maxlen=300),
            "cache_hit_rate": deque(maxlen=300),
            "open_circuits": deque(maxlen=300)
        }
        self.alerts = []
        
        # Thresholds for alerts
        self.thresholds = {
            "response_time": 1000,      # ms
            "error_rate": 5,            # %
            "cpu_usage": 80,            # %
            "memory_usage": 85,         # %
            "open_circuits": 1          # count
        }
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics."""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "response_time": 0,
            "error_rate": 0,
            "requests_per_second": 0,
            "cpu_usage": 0,
            "memory_usage": 0,
            "active_connections": 0,
            "cache_hit_rate": 0,
            "open_circuits": 0
        }
        
        # Collect system metrics
        if PSUTIL_AVAILABLE:
            metrics["cpu_usage"] = psutil.cpu_percent(interval=0.1)
            metrics["memory_usage"] = psutil.virtual_memory().percent
        
        # Collect application metrics
        async with aiohttp.ClientSession() as session:
            # Get general metrics
            try:
                async with session.get(f"{self.host}/metrics", timeout=2) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        metrics["response_time"] = data.get("avg_response_time", 0)
                        metrics["error_rate"] = data.get("error_rate", 0)
                        metrics["requests_per_second"] = data.get("requests_per_second", 0)
                        metrics["active_connections"] = data.get("active_connections", 0)
            except Exception as e:
                pass
            
            # Get cache stats
            try:
                async with session.get(f"{self.host}/cache/stats", timeout=2) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        metrics["cache_hit_rate"] = data.get("hit_rate", 0) * 100
            except:
                pass
            
            # Get circuit breaker status
            try:
                async with session.get(f"{self.host}/metrics/circuit-breakers", timeout=2) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        metrics["open_circuits"] = len(data.get("open_circuits", []))
            except:
                pass
        
        return metrics
    
    def check_alerts(self, metrics: Dict[str, Any]):
        """Check if any metrics exceed thresholds."""
        alerts = []
        
        for metric, threshold in self.thresholds.items():
            if metric in metrics and metrics[metric] > threshold:
                alert = {
                    "timestamp": metrics["timestamp"],
                    "metric": metric,
                    "value": metrics[metric],
                    "threshold": threshold,
                    "severity": self._get_severity(metric, metrics[metric], threshold)
                }
                alerts.append(alert)
                self.alerts.append(alert)
        
        return alerts
    
    def _get_severity(self, metric: str, value: float, threshold: float) -> str:
        """Determine alert severity."""
        ratio = value / threshold
        if ratio > 2:
            return "CRITICAL"
        elif ratio > 1.5:
            return "HIGH"
        elif ratio > 1.2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def update_history(self, metrics: Dict[str, Any]):
        """Update metrics history."""
        for key, value in metrics.items():
            if key in self.metrics_history:
                self.metrics_history[key].append(value)
    
    def get_summary_stats(self) -> Dict[str, Dict[str, float]]:
        """Get summary statistics for recent metrics."""
        summary = {}
        
        for metric, values in self.metrics_history.items():
            if metric == "timestamp" or not values:
                continue
            
            # Convert to list and filter numeric values
            numeric_values = [v for v in values if isinstance(v, (int, float))]
            
            if numeric_values:
                summary[metric] = {
                    "current": numeric_values[-1] if numeric_values else 0,
                    "avg": statistics.mean(numeric_values),
                    "min": min(numeric_values),
                    "max": max(numeric_values),
                    "p95": statistics.quantiles(numeric_values, n=20)[18] if len(numeric_values) > 20 else max(numeric_values)
                }
        
        return summary
    
    def display_dashboard(self):
        """Display real-time dashboard."""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("=" * 80)
        print(f"NGX Voice Sales Agent - Performance Monitor")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Get latest metrics
        summary = self.get_summary_stats()
        
        # Display metrics table
        print(f"\n{'Metric':<25} {'Current':>10} {'Average':>10} {'Min':>10} {'Max':>10} {'P95':>10}")
        print("-" * 80)
        
        for metric, stats in summary.items():
            # Format based on metric type
            if metric in ["response_time"]:
                format_str = "{:>10.0f}ms"
            elif metric in ["error_rate", "cpu_usage", "memory_usage", "cache_hit_rate"]:
                format_str = "{:>10.1f}%"
            elif metric in ["requests_per_second"]:
                format_str = "{:>10.1f}/s"
            else:
                format_str = "{:>10.0f}"
            
            print(f"{metric.replace('_', ' ').title():<25} "
                  f"{format_str.format(stats['current'])[:-2]:>10} "
                  f"{format_str.format(stats['avg'])[:-2]:>10} "
                  f"{format_str.format(stats['min'])[:-2]:>10} "
                  f"{format_str.format(stats['max'])[:-2]:>10} "
                  f"{format_str.format(stats['p95'])[:-2]:>10}")
        
        # Display recent alerts
        if self.alerts:
            print(f"\n{'='*80}")
            print("Recent Alerts (Last 5):")
            print(f"{'Time':<20} {'Metric':<20} {'Value':<15} {'Threshold':<15} {'Severity':<10}")
            print("-" * 80)
            
            for alert in self.alerts[-5:]:
                timestamp = datetime.fromisoformat(alert["timestamp"]).strftime("%H:%M:%S")
                print(f"{timestamp:<20} "
                      f"{alert['metric']:<20} "
                      f"{alert['value']:<15.1f} "
                      f"{alert['threshold']:<15.1f} "
                      f"{alert['severity']:<10}")
        
        # Display circuit breaker status
        open_circuits = summary.get("open_circuits", {}).get("current", 0)
        if open_circuits > 0:
            print(f"\n⚠️  WARNING: {int(open_circuits)} circuit breaker(s) OPEN!")
        
        print(f"\n{'='*80}")
        print("Press Ctrl+C to stop monitoring")
    
    async def monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Collect metrics
                metrics = await self.collect_metrics()
                
                # Update history
                self.update_history(metrics)
                
                # Check alerts
                alerts = self.check_alerts(metrics)
                
                # Display dashboard
                self.display_dashboard()
                
                # Wait for next interval
                await asyncio.sleep(self.interval)
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.interval)
    
    def start(self):
        """Start monitoring."""
        self.running = True
        try:
            asyncio.run(self.monitor_loop())
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")
            self.stop()
    
    def stop(self):
        """Stop monitoring."""
        self.running = False
        
        # Save final report
        self.save_report()
    
    def save_report(self):
        """Save monitoring report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"monitoring_report_{timestamp}.json"
        
        report = {
            "start_time": self.metrics_history["timestamp"][0] if self.metrics_history["timestamp"] else None,
            "end_time": self.metrics_history["timestamp"][-1] if self.metrics_history["timestamp"] else None,
            "summary_statistics": self.get_summary_stats(),
            "alerts": self.alerts,
            "thresholds": self.thresholds
        }
        
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\nMonitoring report saved to: {report_file}")


class LoadTestMonitor(PerformanceMonitor):
    """Extended monitor specifically for load testing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Additional metrics for load testing
        self.metrics_history.update({
            "concurrent_users": deque(maxlen=300),
            "total_requests": deque(maxlen=300),
            "total_failures": deque(maxlen=300),
            "median_response_time": deque(maxlen=300),
            "p95_response_time": deque(maxlen=300),
            "p99_response_time": deque(maxlen=300)
        })
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect metrics including Locust-specific data."""
        metrics = await super().collect_metrics()
        
        # Try to get Locust stats
        async with aiohttp.ClientSession() as session:
            try:
                # Locust stats endpoint (if running with web UI)
                async with session.get("http://localhost:8089/stats/requests", timeout=2) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "stats" in data and data["stats"]:
                            # Aggregate stats
                            total_stats = next((s for s in data["stats"] if s["name"] == "Aggregated"), None)
                            if total_stats:
                                metrics["concurrent_users"] = data.get("user_count", 0)
                                metrics["total_requests"] = total_stats.get("num_requests", 0)
                                metrics["total_failures"] = total_stats.get("num_failures", 0)
                                metrics["median_response_time"] = total_stats.get("median_response_time", 0)
                                metrics["p95_response_time"] = total_stats.get("ninetieth_percentile_response_time", 0)
                                # Note: Locust might use different field names
            except:
                # Locust web UI might not be available in headless mode
                pass
        
        return metrics


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor performance during load tests")
    parser.add_argument("--host", default="http://localhost:8000", help="Target host URL")
    parser.add_argument("--interval", type=int, default=1, help="Update interval in seconds")
    parser.add_argument("--load-test", action="store_true", help="Enable load test specific monitoring")
    
    args = parser.parse_args()
    
    # Create appropriate monitor
    if args.load_test:
        monitor = LoadTestMonitor(host=args.host, interval=args.interval)
    else:
        monitor = PerformanceMonitor(host=args.host, interval=args.interval)
    
    # Start monitoring
    monitor.start()


if __name__ == "__main__":
    main()