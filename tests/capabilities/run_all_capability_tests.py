#!/usr/bin/env python3
"""
Run All Capability Tests - NGX Voice Sales Agent

Ejecuta todos los tests de capacidades únicas y genera reporte consolidado.
"""

import asyncio
import subprocess
import json
import os
from datetime import datetime
from typing import Dict, List, Any
import sys


class CapabilityTestRunner:
    """Ejecuta todos los tests de capacidades y consolida resultados."""
    
    def __init__(self):
        self.test_files = [
            "test_ml_adaptive_evolution.py",
            "test_archetype_detection.py",
            "test_roi_personalization.py",
            "test_empathy_excellence.py",
            "test_ab_testing_bandit.py",
            "test_voice_adaptation.py",
            "test_hie_agents_mention.py"
        ]
        self.results = {}
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
    
    async def run_test(self, test_file: str) -> Dict[str, Any]:
        """
        Ejecuta un test individual y captura resultados.
        """
        print(f"\n{'='*70}")
        print(f"🚀 Ejecutando: {test_file}")
        print(f"{'='*70}")
        
        result = {
            "test_file": test_file,
            "start_time": datetime.now().isoformat(),
            "success": False,
            "output": "",
            "error": "",
            "exit_code": -1
        }
        
        try:
            # Ejecutar test
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                os.path.join(self.test_dir, test_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.test_dir
            )
            
            stdout, stderr = await process.communicate()
            
            result["exit_code"] = process.returncode
            result["success"] = process.returncode == 0
            result["output"] = stdout.decode('utf-8', errors='replace')
            result["error"] = stderr.decode('utf-8', errors='replace')
            result["end_time"] = datetime.now().isoformat()
            
            # Buscar archivo de resultados JSON
            results_pattern = test_file.replace('.py', '_*.json')
            results_dir = os.path.join(self.test_dir, 'results')
            
            if os.path.exists(results_dir):
                # Buscar el archivo más reciente
                import glob
                json_files = glob.glob(os.path.join(results_dir, results_pattern))
                if json_files:
                    latest_json = max(json_files, key=os.path.getctime)
                    with open(latest_json, 'r') as f:
                        result["detailed_results"] = json.load(f)
            
            if result["success"]:
                print(f"✅ {test_file}: EXITOSO")
            else:
                print(f"❌ {test_file}: FALLO (exit code: {result['exit_code']})")
                if result["error"]:
                    print(f"   Error: {result['error'][:200]}...")
            
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
            print(f"❌ {test_file}: ERROR - {e}")
        
        return result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Ejecuta todos los tests de capacidades.
        """
        print("\n🚀 INICIANDO SUITE COMPLETA DE TESTS DE CAPACIDADES")
        print(f"   Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Tests a ejecutar: {len(self.test_files)}")
        
        start_time = datetime.now()
        
        # Ejecutar tests secuencialmente para evitar conflictos
        for test_file in self.test_files:
            result = await self.run_test(test_file)
            self.results[test_file] = result
            
            # Pausa entre tests
            await asyncio.sleep(3)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Generar resumen
        summary = self._generate_summary(duration)
        
        # Guardar reporte completo
        report_file = self._save_report(summary)
        
        # Mostrar resumen en consola
        self._print_summary(summary)
        
        return summary
    
    def _generate_summary(self, duration: float) -> Dict[str, Any]:
        """
        Genera resumen de todos los tests.
        """
        successful_tests = [name for name, result in self.results.items() if result["success"]]
        failed_tests = [name for name, result in self.results.items() if not result["success"]]
        
        summary = {
            "test_suite": "NGX Voice Sales Agent - Capability Tests",
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "total_tests": len(self.test_files),
            "successful_tests": len(successful_tests),
            "failed_tests": len(failed_tests),
            "success_rate": len(successful_tests) / len(self.test_files) * 100,
            "test_results": self.results,
            "capability_status": {}
        }
        
        # Analizar capacidades específicas
        capabilities = {
            "ml_adaptive_learning": "test_ml_adaptive_evolution.py" in successful_tests,
            "archetype_detection": "test_archetype_detection.py" in successful_tests,
            "roi_personalization": "test_roi_personalization.py" in successful_tests,
            "empathy_excellence": "test_empathy_excellence.py" in successful_tests,
            "ab_testing": "test_ab_testing_bandit.py" in successful_tests,
            "voice_adaptation": "test_voice_adaptation.py" in successful_tests,
            "hie_integration": "test_hie_agents_mention.py" in successful_tests
        }
        
        summary["capability_status"] = capabilities
        summary["all_capabilities_working"] = all(capabilities.values())
        
        return summary
    
    def _save_report(self, summary: Dict[str, Any]) -> str:
        """
        Guarda reporte completo en archivo.
        """
        results_dir = os.path.join(self.test_dir, 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        report_file = os.path.join(
            results_dir,
            f"capability_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(report_file, 'w') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # También crear reporte en markdown
        md_file = report_file.replace('.json', '.md')
        self._create_markdown_report(summary, md_file)
        
        return report_file
    
    def _create_markdown_report(self, summary: Dict[str, Any], md_file: str):
        """
        Crea reporte en formato Markdown.
        """
        with open(md_file, 'w') as f:
            f.write("# NGX Voice Sales Agent - Capability Test Report\n\n")
            f.write(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Duración total:** {summary['duration_seconds']:.1f} segundos\n\n")
            
            f.write("## Resumen Ejecutivo\n\n")
            f.write(f"- **Tests totales:** {summary['total_tests']}\n")
            f.write(f"- **Exitosos:** {summary['successful_tests']} ✅\n")
            f.write(f"- **Fallidos:** {summary['failed_tests']} ❌\n")
            f.write(f"- **Tasa de éxito:** {summary['success_rate']:.1f}%\n\n")
            
            f.write("## Estado de Capacidades\n\n")
            f.write("| Capacidad | Estado | Descripción |\n")
            f.write("|-----------|--------|-------------|\n")
            
            capability_descriptions = {
                "ml_adaptive_learning": "Aprendizaje adaptativo con auto-deployment",
                "archetype_detection": "Detección de 5 arquetipos de cliente",
                "roi_personalization": "Cálculos ROI personalizados por profesión",
                "empathy_excellence": "Empatía de nivel 9+/10 con GPT-4o",
                "ab_testing": "A/B testing con Multi-Armed Bandit",
                "voice_adaptation": "7 personalidades de voz adaptativas",
                "hie_integration": "Integración de 11 agentes HIE"
            }
            
            for cap, status in summary["capability_status"].items():
                emoji = "✅" if status else "❌"
                desc = capability_descriptions.get(cap, "")
                f.write(f"| {cap.replace('_', ' ').title()} | {emoji} | {desc} |\n")
            
            f.write("\n## Detalles de Tests\n\n")
            
            for test_name, result in summary["test_results"].items():
                emoji = "✅" if result["success"] else "❌"
                f.write(f"### {emoji} {test_name}\n\n")
                f.write(f"- **Exit code:** {result['exit_code']}\n")
                
                if result.get("detailed_results"):
                    # Extraer métricas clave de resultados detallados
                    details = result["detailed_results"]
                    if "global_metrics" in details:
                        f.write("- **Métricas clave:**\n")
                        for key, value in details["global_metrics"].items():
                            if isinstance(value, (int, float)):
                                f.write(f"  - {key}: {value}\n")
                
                if result["error"]:
                    f.write(f"- **Error:** {result['error'][:200]}...\n")
                
                f.write("\n")
            
            if summary["all_capabilities_working"]:
                f.write("## 🎆 Conclusión\n\n")
                f.write("✅ **TODAS LAS CAPACIDADES ESTÁN FUNCIONANDO CORRECTAMENTE**\n\n")
                f.write("El agente NGX Voice Sales está listo para producción con todas sus características únicas operativas.\n")
            else:
                f.write("## ⚠️ Conclusión\n\n")
                f.write("Algunas capacidades requieren revisión antes de producción.\n")
    
    def _print_summary(self, summary: Dict[str, Any]):
        """
        Imprime resumen en consola.
        """
        print("\n" + "="*70)
        print("📊 RESUMEN DE RESULTADOS")
        print("="*70)
        
        print(f"\nTests totales: {summary['total_tests']}")
        print(f"Exitosos: {summary['successful_tests']} ✅")
        print(f"Fallidos: {summary['failed_tests']} ❌")
        print(f"Tasa de éxito: {summary['success_rate']:.1f}%")
        print(f"Duración total: {summary['duration_seconds']:.1f} segundos")
        
        print("\n🎯 ESTADO DE CAPACIDADES:")
        print("-" * 50)
        
        for capability, status in summary["capability_status"].items():
            emoji = "✅" if status else "❌"
            print(f"{emoji} {capability.replace('_', ' ').title()}")
        
        print("\n" + "="*70)
        
        if summary["all_capabilities_working"]:
            print("✅ TODAS LAS CAPACIDADES FUNCIONANDO - AGENTE LISTO PARA PRODUCCIÓN")
        else:
            print("⚠️  ALGUNAS CAPACIDADES REQUIEREN REVISIÓN")
        
        print("="*70)


async def main():
    """Función principal."""
    runner = CapabilityTestRunner()
    summary = await runner.run_all_tests()
    
    # Retornar código de salida basado en éxito
    return 0 if summary["all_capabilities_working"] else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)