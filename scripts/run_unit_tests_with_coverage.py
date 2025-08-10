#!/usr/bin/env python3
"""
Script to run unit tests with coverage reporting.
Helps track progress towards 80% test coverage goal.
"""

import subprocess
import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_coverage_tests():
    """Run unit tests with coverage measurement."""
    print("=" * 80)
    print("Running Unit Tests with Coverage Analysis")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Change to project root
    os.chdir(project_root)
    
    # Coverage configuration
    coverage_config = """
[run]
source = src
omit = 
    */tests/*
    */test_*
    */__pycache__/*
    */migrations/*
    */scripts/*
    */archived/*

[report]
precision = 2
show_missing = True
skip_covered = False

[html]
directory = htmlcov

[json]
output = coverage.json
"""
    
    # Write coverage config
    with open(".coveragerc", "w") as f:
        f.write(coverage_config)
    
    try:
        # Step 1: Clean previous coverage data
        print("Step 1: Cleaning previous coverage data...")
        subprocess.run(["coverage", "erase"], check=True)
        print("✓ Cleaned")
        print()
        
        # Step 2: Run tests with coverage
        print("Step 2: Running unit tests with coverage...")
        result = subprocess.run(
            [
                "coverage", "run", "-m", "pytest",
                "tests/unit",
                "-v",
                "--tb=short",
                "--no-header"
            ],
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode != 0:
            print(f"⚠️  Some tests failed (exit code: {result.returncode})")
        else:
            print("✓ All tests passed!")
        print()
        
        # Step 3: Generate coverage report
        print("Step 3: Generating coverage report...")
        
        # Text report
        print("\nCoverage Summary:")
        print("-" * 80)
        subprocess.run(["coverage", "report", "--skip-empty"], check=False)
        
        # JSON report for parsing
        subprocess.run(["coverage", "json", "-q"], check=False)
        
        # HTML report
        subprocess.run(["coverage", "html", "-q"], check=False)
        print(f"\n✓ HTML report generated at: {project_root}/htmlcov/index.html")
        
        # Step 4: Analyze coverage
        print("\nStep 4: Analyzing coverage results...")
        analyze_coverage()
        
        # Step 5: Generate recommendations
        print("\nStep 5: Coverage recommendations...")
        generate_recommendations()
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running tests: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
    
    print("\n" + "=" * 80)
    print("Coverage analysis complete!")
    print("=" * 80)
    
    return 0


def analyze_coverage():
    """Analyze coverage results from JSON report."""
    try:
        with open("coverage.json", "r") as f:
            coverage_data = json.load(f)
        
        total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
        
        print(f"\n📊 Overall Coverage: {total_coverage:.2f}%")
        print(f"📎 Target Coverage: 80%")
        
        if total_coverage >= 80:
            print("✅ Target achieved!")
        else:
            gap = 80 - total_coverage
            print(f"📈 Gap to target: {gap:.2f}%")
        
        # Find least covered modules
        files = coverage_data.get("files", {})
        
        # Sort by coverage percentage
        sorted_files = sorted(
            [(f, data.get("summary", {}).get("percent_covered", 0)) 
             for f, data in files.items()],
            key=lambda x: x[1]
        )
        
        print("\n🔍 Least covered modules:")
        for file_path, coverage in sorted_files[:10]:
            if coverage < 50:  # Show files with less than 50% coverage
                module = file_path.replace(str(project_root) + "/", "")
                print(f"   - {module}: {coverage:.1f}%")
        
    except FileNotFoundError:
        print("⚠️  Coverage JSON report not found")
    except Exception as e:
        print(f"⚠️  Error analyzing coverage: {e}")


def generate_recommendations():
    """Generate recommendations for improving test coverage."""
    print("\n📋 Recommendations to reach 80% coverage:\n")
    
    recommendations = [
        "1. **Focus on untested services**: Start with services that have 0% coverage",
        "2. **Test critical paths**: Ensure main conversation flow is well tested",
        "3. **Add integration tests**: Test service interactions",
        "4. **Mock external dependencies**: Use mocks for OpenAI, Supabase, etc.",
        "5. **Test error handling**: Add tests for exception cases",
        "6. **Test edge cases**: Empty inputs, None values, timeouts",
        "7. **Test configuration variations**: Different OptimizationModes, settings",
        "8. **Add parametrized tests**: Use pytest.mark.parametrize for similar tests"
    ]
    
    for rec in recommendations:
        print(f"   {rec}")
    
    print("\n🎯 Priority areas for testing:")
    priority_areas = [
        "- Conversation orchestrator pipelines",
        "- ML prediction services",
        "- Cache layer implementations", 
        "- Error handling and sanitization",
        "- API endpoint handlers",
        "- Authentication and security",
        "- Database repository layer"
    ]
    
    for area in priority_areas:
        print(f"   {area}")


def main():
    """Main execution."""
    # Check if coverage is installed
    try:
        subprocess.run(["coverage", "--version"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("❌ Coverage not installed. Please run: pip install coverage pytest")
        return 1
    
    return run_coverage_tests()


if __name__ == "__main__":
    sys.exit(main())