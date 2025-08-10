#!/usr/bin/env python3
"""
Generate comprehensive load test report.

This script analyzes load test results and generates a detailed
report with recommendations.
"""

import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path
import numpy as np


class LoadTestReportGenerator:
    """Generate comprehensive load test reports."""
    
    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        self.report_data = {
            "generated_at": datetime.now().isoformat(),
            "test_results": {},
            "performance_metrics": {},
            "recommendations": [],
            "conclusions": []
        }
    
    def load_test_results(self) -> Dict[str, Any]:
        """Load all test results from directory."""
        results = {}
        
        # Load summary if exists
        summary_file = self.results_dir / "summary.json"
        if summary_file.exists():
            with open(summary_file) as f:
                results["summary"] = json.load(f)
        
        # Load individual scenario results
        for csv_file in self.results_dir.glob("*_stats_stats.csv"):
            scenario_name = csv_file.stem.replace("_stats_stats", "")
            try:
                df = pd.read_csv(csv_file)
                results[scenario_name] = df
            except Exception as e:
                print(f"Error loading {csv_file}: {e}")
        
        return results
    
    def analyze_performance(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance metrics across all scenarios."""
        analysis = {
            "response_times": {},
            "throughput": {},
            "error_rates": {},
            "scalability": {},
            "bottlenecks": []
        }
        
        # Analyze each scenario
        for scenario_name, data in results.items():
            if scenario_name == "summary" or not isinstance(data, pd.DataFrame):
                continue
            
            # Get aggregated stats
            aggregated = data[data["Type"] == "Aggregated"] if "Type" in data.columns else data
            
            if not aggregated.empty:
                stats = aggregated.iloc[0]
                
                # Response time analysis
                analysis["response_times"][scenario_name] = {
                    "average": stats.get("Average Response Time", 0),
                    "median": stats.get("Median Response Time", 0),
                    "p95": stats.get("95%", 0),
                    "p99": stats.get("99%", 0),
                    "max": stats.get("Max Response Time", 0)
                }
                
                # Throughput analysis
                analysis["throughput"][scenario_name] = {
                    "requests_per_second": stats.get("Requests/s", 0),
                    "total_requests": stats.get("Request Count", 0)
                }
                
                # Error rate analysis
                total_requests = stats.get("Request Count", 1)
                failures = stats.get("Failure Count", 0)
                analysis["error_rates"][scenario_name] = {
                    "failure_count": failures,
                    "failure_rate": (failures / total_requests * 100) if total_requests > 0 else 0
                }
        
        # Scalability analysis
        analysis["scalability"] = self._analyze_scalability(analysis)
        
        # Identify bottlenecks
        analysis["bottlenecks"] = self._identify_bottlenecks(analysis)
        
        return analysis
    
    def _analyze_scalability(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze system scalability based on load progression."""
        scalability = {
            "linear": True,
            "breaking_point": None,
            "efficiency": {}
        }
        
        # Compare performance at different load levels
        scenarios = ["baseline", "normal", "peak", "stress"]
        response_times = []
        throughputs = []
        
        for scenario in scenarios:
            if scenario in analysis["response_times"]:
                response_times.append(analysis["response_times"][scenario]["average"])
                throughputs.append(analysis["throughput"][scenario]["requests_per_second"])
        
        if len(response_times) >= 2:
            # Check if response time increases linearly
            response_increase = [(response_times[i] - response_times[0]) / response_times[0] * 100 
                               for i in range(1, len(response_times))]
            
            # If response time increases more than 200% it's not linear
            if any(increase > 200 for increase in response_increase):
                scalability["linear"] = False
                
                # Find breaking point
                for i, increase in enumerate(response_increase):
                    if increase > 200:
                        scalability["breaking_point"] = scenarios[i + 1]
                        break
        
        return scalability
    
    def _identify_bottlenecks(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks."""
        bottlenecks = []
        
        # Check for high response times
        for scenario, times in analysis["response_times"].items():
            if times["p95"] > 1000:  # 1 second
                bottlenecks.append({
                    "type": "high_response_time",
                    "scenario": scenario,
                    "severity": "HIGH" if times["p95"] > 3000 else "MEDIUM",
                    "details": f"P95 response time: {times['p95']:.0f}ms"
                })
        
        # Check for high error rates
        for scenario, errors in analysis["error_rates"].items():
            if errors["failure_rate"] > 1:
                bottlenecks.append({
                    "type": "high_error_rate",
                    "scenario": scenario,
                    "severity": "CRITICAL" if errors["failure_rate"] > 5 else "HIGH",
                    "details": f"Error rate: {errors['failure_rate']:.1f}%"
                })
        
        # Check for throughput plateau
        throughput_values = [t["requests_per_second"] for t in analysis["throughput"].values()]
        if len(throughput_values) >= 3:
            # If throughput doesn't increase with load, we hit a limit
            if max(throughput_values) < throughput_values[0] * 2:
                bottlenecks.append({
                    "type": "throughput_limit",
                    "scenario": "system",
                    "severity": "MEDIUM",
                    "details": f"Maximum throughput: {max(throughput_values):.1f} req/s"
                })
        
        return bottlenecks
    
    def generate_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        # Response time recommendations
        high_response_scenarios = [
            s for s, t in analysis["response_times"].items() 
            if t["p95"] > 1000
        ]
        if high_response_scenarios:
            recommendations.append({
                "category": "Performance",
                "priority": "HIGH",
                "issue": "High response times detected",
                "recommendation": "Optimize database queries and implement query result caching",
                "affected_scenarios": high_response_scenarios,
                "expected_improvement": "50-70% reduction in response time"
            })
        
        # Error rate recommendations
        high_error_scenarios = [
            s for s, e in analysis["error_rates"].items() 
            if e["failure_rate"] > 1
        ]
        if high_error_scenarios:
            recommendations.append({
                "category": "Reliability",
                "priority": "CRITICAL",
                "issue": "High error rates under load",
                "recommendation": "Review error logs, increase timeout values, and ensure circuit breakers are properly configured",
                "affected_scenarios": high_error_scenarios,
                "expected_improvement": "Error rate below 1%"
            })
        
        # Scalability recommendations
        if not analysis["scalability"]["linear"]:
            recommendations.append({
                "category": "Scalability",
                "priority": "HIGH",
                "issue": f"Non-linear scalability, breaking point at {analysis['scalability']['breaking_point']}",
                "recommendation": "Implement horizontal scaling, optimize resource-intensive operations",
                "affected_scenarios": ["system-wide"],
                "expected_improvement": "Linear scalability up to 200+ concurrent users"
            })
        
        # Cache recommendations
        if any(b["type"] == "throughput_limit" for b in analysis["bottlenecks"]):
            recommendations.append({
                "category": "Caching",
                "priority": "MEDIUM",
                "issue": "Throughput limitations detected",
                "recommendation": "Increase Redis cache TTL for frequently accessed data, implement cache warming",
                "affected_scenarios": ["high-load scenarios"],
                "expected_improvement": "20-30% increase in throughput"
            })
        
        # Circuit breaker recommendations
        recommendations.append({
            "category": "Resilience",
            "priority": "MEDIUM",
            "issue": "External API dependencies",
            "recommendation": "Verify circuit breaker thresholds are appropriate for load conditions",
            "affected_scenarios": ["all"],
            "expected_improvement": "Better graceful degradation under failure"
        })
        
        return recommendations
    
    def generate_visualizations(self, analysis: Dict[str, Any]):
        """Generate visualization charts for the report."""
        plt.style.use('seaborn-v0_8-whitegrid')
        
        # Create figure with subplots
        fig = plt.figure(figsize=(16, 12))
        
        # 1. Response time comparison
        ax1 = plt.subplot(2, 3, 1)
        scenarios = list(analysis["response_times"].keys())
        metrics = ["average", "p95", "p99"]
        data = []
        
        for metric in metrics:
            values = [analysis["response_times"][s].get(metric, 0) for s in scenarios]
            data.append(values)
        
        x = np.arange(len(scenarios))
        width = 0.25
        
        for i, (metric, values) in enumerate(zip(metrics, data)):
            ax1.bar(x + i * width, values, width, label=metric.upper())
        
        ax1.set_xlabel('Scenario')
        ax1.set_ylabel('Response Time (ms)')
        ax1.set_title('Response Time by Scenario')
        ax1.set_xticks(x + width)
        ax1.set_xticklabels(scenarios, rotation=45)
        ax1.legend()
        
        # 2. Throughput progression
        ax2 = plt.subplot(2, 3, 2)
        throughput_data = [(s, d["requests_per_second"]) 
                          for s, d in analysis["throughput"].items()]
        throughput_data.sort(key=lambda x: x[1])
        
        scenarios, values = zip(*throughput_data)
        ax2.plot(range(len(scenarios)), values, 'o-', markersize=10, linewidth=2)
        ax2.set_xlabel('Scenario')
        ax2.set_ylabel('Requests/Second')
        ax2.set_title('Throughput Progression')
        ax2.set_xticks(range(len(scenarios)))
        ax2.set_xticklabels(scenarios, rotation=45)
        ax2.grid(True, alpha=0.3)
        
        # 3. Error rates
        ax3 = plt.subplot(2, 3, 3)
        error_scenarios = []
        error_rates = []
        
        for scenario, data in analysis["error_rates"].items():
            if data["failure_rate"] > 0:
                error_scenarios.append(scenario)
                error_rates.append(data["failure_rate"])
        
        if error_scenarios:
            colors = ['red' if rate > 5 else 'orange' if rate > 1 else 'yellow' 
                     for rate in error_rates]
            ax3.bar(range(len(error_scenarios)), error_rates, color=colors)
            ax3.set_xlabel('Scenario')
            ax3.set_ylabel('Error Rate (%)')
            ax3.set_title('Error Rates by Scenario')
            ax3.set_xticks(range(len(error_scenarios)))
            ax3.set_xticklabels(error_scenarios, rotation=45)
            ax3.axhline(y=1, color='g', linestyle='--', alpha=0.7, label='1% Target')
            ax3.legend()
        else:
            ax3.text(0.5, 0.5, 'No Errors Detected', ha='center', va='center', 
                    transform=ax3.transAxes, fontsize=16, color='green')
            ax3.set_title('Error Rates')
        
        # 4. Performance heatmap
        ax4 = plt.subplot(2, 3, 4)
        heatmap_data = []
        heatmap_labels = []
        
        for scenario in scenarios[:4]:  # Limit to main scenarios
            if scenario in analysis["response_times"]:
                row = [
                    analysis["response_times"][scenario]["average"],
                    analysis["response_times"][scenario]["p95"],
                    analysis["error_rates"][scenario]["failure_rate"] * 100,  # Scale for visibility
                    analysis["throughput"][scenario]["requests_per_second"]
                ]
                heatmap_data.append(row)
                heatmap_labels.append(scenario)
        
        if heatmap_data:
            im = ax4.imshow(heatmap_data, cmap='RdYlGn_r', aspect='auto')
            ax4.set_xticks(range(4))
            ax4.set_xticklabels(['Avg RT', 'P95 RT', 'Error %', 'RPS'], rotation=45)
            ax4.set_yticks(range(len(heatmap_labels)))
            ax4.set_yticklabels(heatmap_labels)
            ax4.set_title('Performance Heatmap')
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=ax4)
            cbar.set_label('Relative Performance')
        
        # 5. Bottleneck summary
        ax5 = plt.subplot(2, 3, 5)
        bottleneck_types = {}
        for bottleneck in analysis["bottlenecks"]:
            bt = bottleneck["type"]
            bottleneck_types[bt] = bottleneck_types.get(bt, 0) + 1
        
        if bottleneck_types:
            ax5.pie(bottleneck_types.values(), labels=bottleneck_types.keys(), 
                   autopct='%1.0f%%', startangle=90)
            ax5.set_title('Bottleneck Distribution')
        else:
            ax5.text(0.5, 0.5, 'No Bottlenecks Detected', ha='center', va='center', 
                    transform=ax5.transAxes, fontsize=16, color='green')
            ax5.set_title('Bottlenecks')
        
        # 6. Recommendations priority
        ax6 = plt.subplot(2, 3, 6)
        rec_priorities = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for rec in self.report_data.get("recommendations", []):
            priority = rec.get("priority", "MEDIUM")
            rec_priorities[priority] += 1
        
        colors_map = {"CRITICAL": "red", "HIGH": "orange", "MEDIUM": "yellow", "LOW": "green"}
        priorities = list(rec_priorities.keys())
        counts = list(rec_priorities.values())
        colors = [colors_map[p] for p in priorities]
        
        ax6.bar(range(len(priorities)), counts, color=colors)
        ax6.set_xlabel('Priority')
        ax6.set_ylabel('Count')
        ax6.set_title('Recommendations by Priority')
        ax6.set_xticks(range(len(priorities)))
        ax6.set_xticklabels(priorities)
        
        plt.tight_layout()
        
        # Save figure
        output_path = self.results_dir / "load_test_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def generate_html_report(self, analysis: Dict[str, Any], recommendations: List[Dict[str, Any]]):
        """Generate HTML report."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>NGX Voice Sales Agent - Load Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        .summary {{ background: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; }}
        .metric-label {{ color: #666; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .recommendation {{ border-left: 4px solid #ff9800; padding: 10px; margin: 10px 0; background: #fff3e0; }}
        .critical {{ border-left-color: #f44336; background: #ffebee; }}
        .high {{ border-left-color: #ff9800; background: #fff3e0; }}
        .medium {{ border-left-color: #ffc107; background: #fffde7; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
        .warning {{ color: orange; }}
    </style>
</head>
<body>
    <h1>Load Test Report - NGX Voice Sales Agent</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="summary">
        <h2>Executive Summary</h2>
        <div class="metric">
            <div class="metric-value">{len(analysis['response_times'])}</div>
            <div class="metric-label">Scenarios Tested</div>
        </div>
        <div class="metric">
            <div class="metric-value">{sum(t['total_requests'] for t in analysis['throughput'].values()):,}</div>
            <div class="metric-label">Total Requests</div>
        </div>
        <div class="metric">
            <div class="metric-value">{max(t['requests_per_second'] for t in analysis['throughput'].values()):.1f}</div>
            <div class="metric-label">Peak RPS</div>
        </div>
        <div class="metric">
            <div class="metric-value">{len(analysis['bottlenecks'])}</div>
            <div class="metric-label">Bottlenecks Found</div>
        </div>
    </div>
    
    <h2>Performance Results</h2>
    <table>
        <tr>
            <th>Scenario</th>
            <th>Avg Response Time</th>
            <th>P95 Response Time</th>
            <th>Requests/Second</th>
            <th>Error Rate</th>
            <th>Status</th>
        </tr>
"""
        
        # Add scenario results
        for scenario in analysis["response_times"]:
            avg_rt = analysis["response_times"][scenario]["average"]
            p95_rt = analysis["response_times"][scenario]["p95"]
            rps = analysis["throughput"][scenario]["requests_per_second"]
            error_rate = analysis["error_rates"][scenario]["failure_rate"]
            
            # Determine status
            if error_rate > 5 or p95_rt > 3000:
                status = '<span class="fail">❌ FAIL</span>'
            elif error_rate > 1 or p95_rt > 1000:
                status = '<span class="warning">⚠️ WARNING</span>'
            else:
                status = '<span class="pass">✅ PASS</span>'
            
            html_content += f"""
        <tr>
            <td>{scenario}</td>
            <td>{avg_rt:.0f}ms</td>
            <td>{p95_rt:.0f}ms</td>
            <td>{rps:.1f}</td>
            <td>{error_rate:.1f}%</td>
            <td>{status}</td>
        </tr>
"""
        
        html_content += """
    </table>
    
    <h2>Recommendations</h2>
"""
        
        # Add recommendations
        for rec in recommendations:
            priority_class = rec['priority'].lower()
            html_content += f"""
    <div class="recommendation {priority_class}">
        <h3>{rec['category']} - {rec['priority']} Priority</h3>
        <p><strong>Issue:</strong> {rec['issue']}</p>
        <p><strong>Recommendation:</strong> {rec['recommendation']}</p>
        <p><strong>Expected Improvement:</strong> {rec['expected_improvement']}</p>
    </div>
"""
        
        # Add visualization
        html_content += """
    <h2>Performance Visualizations</h2>
    <img src="load_test_analysis.png" alt="Performance Analysis" style="max-width: 100%;">
    
    <h2>Conclusions</h2>
    <ul>
"""
        
        # Add conclusions
        conclusions = [
            f"System can handle up to {max(t['requests_per_second'] for t in analysis['throughput'].values()):.0f} requests per second",
            f"{'Linear' if analysis['scalability']['linear'] else 'Non-linear'} scalability observed",
        ]
        
        if analysis['scalability']['breaking_point']:
            conclusions.append(f"Performance degradation starts at '{analysis['scalability']['breaking_point']}' load level")
        
        if not analysis['bottlenecks']:
            conclusions.append("No critical bottlenecks identified")
        else:
            conclusions.append(f"{len(analysis['bottlenecks'])} bottlenecks require attention")
        
        for conclusion in conclusions:
            html_content += f"        <li>{conclusion}</li>\n"
        
        html_content += """
    </ul>
</body>
</html>
"""
        
        # Save HTML report
        report_path = self.results_dir / "load_test_report.html"
        with open(report_path, "w") as f:
            f.write(html_content)
        
        return str(report_path)
    
    def generate_report(self):
        """Generate complete load test report."""
        print("Generating load test report...")
        
        # Load results
        results = self.load_test_results()
        
        if not results:
            print("No test results found!")
            return None
        
        # Analyze performance
        analysis = self.analyze_performance(results)
        
        # Generate recommendations
        recommendations = self.generate_recommendations(analysis)
        
        # Store in report data
        self.report_data["test_results"] = {k: v.to_dict() if hasattr(v, 'to_dict') else v 
                                           for k, v in results.items()}
        self.report_data["performance_metrics"] = analysis
        self.report_data["recommendations"] = recommendations
        
        # Generate visualizations
        viz_path = self.generate_visualizations(analysis)
        print(f"Visualizations saved to: {viz_path}")
        
        # Generate HTML report
        html_path = self.generate_html_report(analysis, recommendations)
        print(f"HTML report saved to: {html_path}")
        
        # Save JSON report
        json_path = self.results_dir / "load_test_report.json"
        with open(json_path, "w") as f:
            json.dump(self.report_data, f, indent=2, default=str)
        print(f"JSON report saved to: {json_path}")
        
        return {
            "html": html_path,
            "json": json_path,
            "visualizations": viz_path
        }


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate load test report")
    parser.add_argument("results_dir", help="Directory containing test results")
    
    args = parser.parse_args()
    
    # Generate report
    generator = LoadTestReportGenerator(args.results_dir)
    report_paths = generator.generate_report()
    
    if report_paths:
        print(f"\nReport generation complete!")
        print(f"View the HTML report: {report_paths['html']}")


if __name__ == "__main__":
    main()