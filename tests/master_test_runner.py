#!/usr/bin/env python3
"""
NGX Voice Sales Agent - Master Test Runner
Ejecuta todos los tests de la suite completa
"""

import asyncio
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import argparse

class MasterTestRunner:
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()
        
    def log(self, message, level="INFO"):
        """Log messages con formato bonito"""
        symbols = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️",
            "RUNNING": "🔄"
        }
        print(f"{symbols.get(level, '•')} {message}")
    
    async def run_test_suite(self, name, script_path, skip=False):
        """Ejecuta una suite de tests"""
        if skip:
            self.log(f"Skipping {name} tests", "WARNING")
            self.results[name] = {"status": "skipped", "duration": 0}
            return
            
        self.log(f"Running {name} tests...", "RUNNING")
        start = datetime.now()
        
        try:
            # Ejecutar el script de test
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos máximo por suite
            )
            
            duration = (datetime.now() - start).total_seconds()
            
            if result.returncode == 0:
                self.log(f"{name} tests completed successfully", "SUCCESS")
                self.results[name] = {
                    "status": "passed",
                    "duration": duration,
                    "output": result.stdout[-1000:]  # Últimas 1000 caracteres
                }
            else:
                self.log(f"{name} tests failed", "ERROR")
                self.results[name] = {
                    "status": "failed",
                    "duration": duration,
                    "error": result.stderr[-1000:]
                }
                
        except subprocess.TimeoutExpired:
            self.log(f"{name} tests timed out", "ERROR")
            self.results[name] = {
                "status": "timeout",
                "duration": 300
            }
        except Exception as e:
            self.log(f"{name} tests error: {str(e)}", "ERROR")
            self.results[name] = {
                "status": "error",
                "duration": (datetime.now() - start).total_seconds(),
                "error": str(e)
            }
    
    async def run_all_tests(self, args):
        """Ejecuta todos los tests en secuencia"""
        print("🚀 NGX Voice Sales Agent - Master Test Suite")
        print("=" * 60)
        print(f"Started at: {self.start_time}")
        print("=" * 60)
        
        test_suites = [
            ("Quick Validation", "quick_validation_test.py", False),
            ("E2E Conversation", "e2e/full_conversation_test.py", args.skip_e2e),
            ("Performance", "performance/extreme_load_test.py", args.skip_load),
            ("Security", "security/penetration_test.py", args.skip_security),
            ("Chaos Engineering", "resilience/chaos_test.py", args.skip_chaos)
        ]
        
        for name, script, skip in test_suites:
            script_path = Path(__file__).parent / script
            if script_path.exists():
                await self.run_test_suite(name, script_path, skip)
            else:
                self.log(f"{name} test script not found at {script_path}", "WARNING")
                self.results[name] = {"status": "not_found"}
            
            # Pequeña pausa entre tests
            await asyncio.sleep(2)
        
        # Generar reporte final
        self.generate_report()
    
    def generate_report(self):
        """Genera reporte final de todos los tests"""
        total_duration = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print("📊 MASTER TEST SUITE SUMMARY")
        print("=" * 60)
        
        passed = 0
        failed = 0
        skipped = 0
        
        for name, result in self.results.items():
            status = result['status']
            duration = result.get('duration', 0)
            
            if status == 'passed':
                symbol = "✅"
                passed += 1
            elif status == 'failed':
                symbol = "❌"
                failed += 1
            elif status == 'skipped':
                symbol = "⏭️"
                skipped += 1
            else:
                symbol = "⚠️"
                
            print(f"{symbol} {name}: {status.upper()} ({duration:.2f}s)")
        
        print("\n" + "-" * 60)
        print(f"Total tests run: {len(self.results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")
        print(f"Total duration: {total_duration:.2f}s")
        
        # Guardar resultados
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"master_test_results_{timestamp}.json"
        
        report_data = {
            "timestamp": self.start_time.isoformat(),
            "total_duration": total_duration,
            "summary": {
                "total": len(self.results),
                "passed": passed,
                "failed": failed,
                "skipped": skipped
            },
            "results": self.results
        }
        
        with open(results_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {results_file}")
        
        # Return exit code
        return 1 if failed > 0 else 0

async def main():
    parser = argparse.ArgumentParser(description='NGX Voice Sales Agent - Master Test Runner')
    parser.add_argument('--skip-load', action='store_true', help='Skip load/performance tests')
    parser.add_argument('--skip-security', action='store_true', help='Skip security tests')
    parser.add_argument('--skip-chaos', action='store_true', help='Skip chaos engineering tests')
    parser.add_argument('--skip-e2e', action='store_true', help='Skip E2E tests')
    
    args = parser.parse_args()
    
    runner = MasterTestRunner()
    await runner.run_all_tests(args)

if __name__ == "__main__":
    asyncio.run(main())