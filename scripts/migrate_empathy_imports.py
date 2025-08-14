#!/usr/bin/env python3
"""
Empathy Services Migration Script for NGX Voice Sales Agent.

This script helps migrate from legacy empathy services to the consolidated
service by updating imports and adding feature flag support.

Usage:
    python scripts/migrate_empathy_imports.py --mode check
    python scripts/migrate_empathy_imports.py --mode migrate
    python scripts/migrate_empathy_imports.py --mode revert
"""

import os
import re
import sys
import argparse
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Color codes for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class EmpathyMigrationTool:
    """Tool for migrating from legacy empathy services to consolidated service."""
    
    def __init__(self):
        self.project_root = project_root
        self.src_dir = self.project_root / "src"
        self.backup_dir = self.project_root / "migration_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Legacy service mappings
        self.legacy_imports = {
            "src.services.advanced_empathy_engine": {
                "replacement": "src.services.empathy_compatibility",
                "classes": ["AdvancedEmpathyEngine"],
                "functions": ["get_advanced_empathy_engine"]
            },
            "src.services.emotional_intelligence_service": {
                "replacement": "src.services.empathy_compatibility", 
                "classes": ["EmotionalIntelligenceService"],
                "functions": ["get_emotional_intelligence_service"]
            },
            "src.services.empathy_engine_service": {
                "replacement": "src.services.empathy_compatibility",
                "classes": ["EmpathyEngineService"],
                "functions": ["get_empathy_engine_service"]
            },
            "src.services.ultra_empathy_greetings": {
                "replacement": "src.services.empathy_compatibility",
                "classes": ["UltraEmpathyGreetingEngine"],
                "functions": ["get_ultra_empathy_greeting_engine"]
            },
            "src.services.ultra_empathy_price_handler": {
                "replacement": "src.services.empathy_compatibility",
                "classes": ["UltraEmpathyPriceHandler"],
                "functions": ["get_ultra_empathy_price_handler"]
            },
            "src.services.advanced_sentiment_service": {
                "replacement": "src.services.empathy_compatibility",
                "classes": ["AdvancedSentimentService"],
                "functions": ["get_advanced_sentiment_service"]
            },
            "src.services.sentiment_alert_service": {
                "replacement": "src.services.empathy_compatibility",
                "classes": ["SentimentAlertService"],
                "functions": ["get_sentiment_alert_service"]
            },
            "src.services.adaptive_personality_service": {
                "replacement": "src.services.empathy_compatibility",
                "classes": ["AdaptivePersonalityService"],
                "functions": ["get_adaptive_personality_service"]
            }
        }
        
        # Files to process (patterns)
        self.file_patterns = [
            "**/*.py"
        ]
        
        # Files to exclude
        self.exclude_patterns = [
            "**/empathy_compatibility.py",
            "**/consolidated_empathy_intelligence_service.py",
            "**/empathy_feature_flags.py",
            "**/test_empathy_consolidation.py",
            "**/migrate_empathy_imports.py",
            "**/migration_backups/**"
        ]
        
        self.migration_log = []
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message with color coding."""
        colors = {
            "INFO": Colors.CYAN,
            "SUCCESS": Colors.GREEN,
            "WARNING": Colors.YELLOW,
            "ERROR": Colors.RED,
            "MIGRATION": Colors.MAGENTA
        }
        
        color = colors.get(level, Colors.WHITE)
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"{color}[{timestamp}] {level}: {message}{Colors.END}"
        print(formatted_message)
        
        self.migration_log.append({
            "timestamp": timestamp,
            "level": level,
            "message": message
        })
    
    def find_python_files(self) -> List[Path]:
        """Find all Python files to process."""
        files = []
        
        for pattern in self.file_patterns:
            for file_path in self.src_dir.rglob(pattern):
                # Check if file should be excluded
                excluded = False
                for exclude_pattern in self.exclude_patterns:
                    if file_path.match(exclude_pattern):
                        excluded = True
                        break
                
                if not excluded and file_path.is_file():
                    files.append(file_path)
        
        return sorted(files)
    
    def analyze_file(self, file_path: Path) -> Dict[str, any]:
        """Analyze a file for legacy empathy imports."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            analysis = {
                "file_path": file_path,
                "legacy_imports": [],
                "needs_migration": False,
                "migration_complexity": "low",
                "estimated_changes": 0
            }
            
            # Find legacy imports
            for legacy_import, config in self.legacy_imports.items():
                # Check for various import patterns
                import_patterns = [
                    rf"from {re.escape(legacy_import)} import",
                    rf"import {re.escape(legacy_import)}",
                    rf"from {re.escape(legacy_import)}\\.",
                ]
                
                for pattern in import_patterns:
                    if re.search(pattern, content):
                        analysis["legacy_imports"].append({
                            "import": legacy_import,
                            "pattern": pattern,
                            "config": config
                        })
                        analysis["needs_migration"] = True
                        analysis["estimated_changes"] += 1
            
            # Assess complexity
            if len(analysis["legacy_imports"]) > 3:
                analysis["migration_complexity"] = "high"
            elif len(analysis["legacy_imports"]) > 1:
                analysis["migration_complexity"] = "medium"
            
            return analysis
            
        except Exception as e:
            self.log(f"Error analyzing {file_path}: {e}", "ERROR")
            return {
                "file_path": file_path,
                "error": str(e),
                "needs_migration": False
            }
    
    def check_migration_status(self) -> Dict[str, any]:
        """Check current migration status."""
        self.log("Checking migration status...", "INFO")
        
        files = self.find_python_files()
        self.log(f"Found {len(files)} Python files to analyze", "INFO")
        
        status = {
            "total_files": len(files),
            "files_needing_migration": 0,
            "total_legacy_imports": 0,
            "complexity_breakdown": {"low": 0, "medium": 0, "high": 0},
            "files_by_complexity": {"low": [], "medium": [], "high": []},
            "migration_recommendations": []
        }
        
        for file_path in files:
            analysis = self.analyze_file(file_path)
            
            if analysis.get("needs_migration", False):
                status["files_needing_migration"] += 1
                status["total_legacy_imports"] += len(analysis.get("legacy_imports", []))
                
                complexity = analysis.get("migration_complexity", "low")
                status["complexity_breakdown"][complexity] += 1
                status["files_by_complexity"][complexity].append(file_path)
        
        # Generate recommendations
        if status["files_needing_migration"] == 0:
            status["migration_recommendations"].append("✅ No migration needed - all files are up to date!")
        else:
            status["migration_recommendations"].extend([
                f"📁 {status['files_needing_migration']} files need migration",
                f"📦 {status['total_legacy_imports']} legacy imports found",
                f"🔧 Start with {status['complexity_breakdown']['low']} low-complexity files",
                f"⚡ Test consolidated service with feature flags first",
                f"🔄 Migrate in batches to minimize risk"
            ])
        
        return status
    
    def create_backup(self, file_path: Path):
        """Create backup of a file before migration."""
        try:
            # Ensure backup directory exists
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Create relative path structure in backup
            relative_path = file_path.relative_to(self.project_root)
            backup_path = self.backup_dir / relative_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file to backup
            shutil.copy2(file_path, backup_path)
            
            self.log(f"Backed up {relative_path}", "INFO")
            return True
            
        except Exception as e:
            self.log(f"Error backing up {file_path}: {e}", "ERROR")
            return False
    
    def migrate_file(self, file_path: Path, analysis: Dict[str, any]) -> bool:
        """Migrate a single file."""
        try:
            # Create backup first
            if not self.create_backup(file_path):
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            changes_made = 0
            
            # Process each legacy import
            for legacy_info in analysis.get("legacy_imports", []):\n                legacy_import = legacy_info["import"]\n                config = legacy_info["config"]\n                replacement = config["replacement"]\n                \n                # Replace import statements\n                import_replacements = [\n                    (rf"from {re.escape(legacy_import)} import", f"from {replacement} import"),\n                    (rf"import {re.escape(legacy_import)}", f"import {replacement}"),\n                ]\n                \n                for old_pattern, new_pattern in import_replacements:\n                    if re.search(old_pattern, content):\n                        content = re.sub(old_pattern, new_pattern, content)\n                        changes_made += 1\n            \n            # Add feature flag import if not present and needed\n            if changes_made > 0 and "empathy_feature_flags" not in content:\n                # Find a good place to add the import\n                import_section_match = re.search(r"(from src\\.[\\w\\.]+|import \\w+).*?\\n", content)\n                if import_section_match:\n                    insert_pos = import_section_match.end()\n                    feature_flag_import = "from src.config.empathy_feature_flags import use_consolidated_service, is_feature_enabled\\n"\n                    content = content[:insert_pos] + feature_flag_import + content[insert_pos:]\n                    changes_made += 1\n            \n            # Write modified content\n            if changes_made > 0:\n                with open(file_path, 'w', encoding='utf-8') as f:\n                    f.write(content)\n                \n                relative_path = file_path.relative_to(self.project_root)\n                self.log(f"Migrated {relative_path} ({changes_made} changes)", "MIGRATION")\n                return True\n            else:\n                self.log(f"No changes needed for {file_path.relative_to(self.project_root)}", "INFO")\n                return True\n                \n        except Exception as e:\n            self.log(f"Error migrating {file_path}: {e}", "ERROR")\n            return False\n    \n    def run_migration(self, dry_run: bool = False) -> Dict[str, any]:\n        """Run the migration process."""\n        self.log(f"Starting migration (dry_run={dry_run})...", "INFO")\n        \n        files = self.find_python_files()\n        migration_results = {\n            "total_files_processed": 0,\n            "files_migrated": 0,\n            "files_failed": 0,\n            "total_changes": 0,\n            "errors": []\n        }\n        \n        for file_path in files:\n            analysis = self.analyze_file(file_path)\n            migration_results["total_files_processed"] += 1\n            \n            if analysis.get("needs_migration", False):\n                if dry_run:\n                    relative_path = file_path.relative_to(self.project_root)\n                    self.log(f"Would migrate {relative_path} ({len(analysis['legacy_imports'])} imports)", "INFO")\n                    migration_results["files_migrated"] += 1\n                    migration_results["total_changes"] += analysis.get("estimated_changes", 0)\n                else:\n                    if self.migrate_file(file_path, analysis):\n                        migration_results["files_migrated"] += 1\n                        migration_results["total_changes"] += analysis.get("estimated_changes", 0)\n                    else:\n                        migration_results["files_failed"] += 1\n                        migration_results["errors"].append(str(file_path))\n        \n        return migration_results\n    \n    def revert_migration(self) -> bool:\n        """Revert migration using backups."""\n        self.log("Starting migration revert...", "INFO")\n        \n        if not self.backup_dir.exists():\n            available_backups = [d for d in (self.project_root / "migration_backups").glob("*") if d.is_dir()]\n            if not available_backups:\n                self.log("No backups found for revert", "ERROR")\n                return False\n            \n            # Use most recent backup\n            self.backup_dir = max(available_backups, key=lambda x: x.name)\n            self.log(f"Using backup from {self.backup_dir.name}", "INFO")\n        \n        try:\n            # Restore files from backup\n            reverted_count = 0\n            \n            for backup_file in self.backup_dir.rglob("*.py"):\n                # Calculate original file path\n                relative_path = backup_file.relative_to(self.backup_dir)\n                original_file = self.project_root / relative_path\n                \n                if original_file.exists():\n                    shutil.copy2(backup_file, original_file)\n                    reverted_count += 1\n                    self.log(f"Reverted {relative_path}", "SUCCESS")\n            \n            self.log(f"Successfully reverted {reverted_count} files", "SUCCESS")\n            return True\n            \n        except Exception as e:\n            self.log(f"Error during revert: {e}", "ERROR")\n            return False\n    \n    def generate_migration_report(self, status: Dict[str, any]) -> str:\n        """Generate a detailed migration report."""\n        report = f\"\"\"\n{Colors.BOLD}{'='*60}\nNGX Empathy Services Migration Report\n{'='*60}{Colors.END}\n\n{Colors.CYAN}📊 MIGRATION OVERVIEW{Colors.END}\n{Colors.WHITE}Total Files Analyzed:{Colors.END} {status['total_files']}\n{Colors.YELLOW}Files Needing Migration:{Colors.END} {status['files_needing_migration']}\n{Colors.MAGENTA}Total Legacy Imports:{Colors.END} {status['total_legacy_imports']}\n\n{Colors.CYAN}🔧 COMPLEXITY BREAKDOWN{Colors.END}\n{Colors.GREEN}Low Complexity:{Colors.END} {status['complexity_breakdown']['low']} files\n{Colors.YELLOW}Medium Complexity:{Colors.END} {status['complexity_breakdown']['medium']} files\n{Colors.RED}High Complexity:{Colors.END} {status['complexity_breakdown']['high']} files\n\n{Colors.CYAN}📝 RECOMMENDATIONS{Colors.END}\n\"\"\"\n        \n        for i, rec in enumerate(status['migration_recommendations'], 1):\n            report += f\"{i}. {rec}\\n\"\n        \n        if status['files_by_complexity']['low']:\n            report += f\"\\n{Colors.CYAN}🚀 SUGGESTED MIGRATION ORDER (Low Complexity First){Colors.END}\\n\"\n            for i, file_path in enumerate(status['files_by_complexity']['low'][:5], 1):\n                relative_path = file_path.relative_to(self.project_root)\n                report += f\"{i}. {relative_path}\\n\"\n            \n            if len(status['files_by_complexity']['low']) > 5:\n                report += f\"... and {len(status['files_by_complexity']['low']) - 5} more low-complexity files\\n\"\n        \n        report += f\"\\n{Colors.CYAN}💡 NEXT STEPS{Colors.END}\\n\"\n        report += \"1. Review this report and plan your migration strategy\\n\"\n        report += \"2. Test consolidated service in development environment\\n\"\n        report += \"3. Run migration in dry-run mode first: --mode migrate --dry-run\\n\"\n        report += \"4. Execute migration on low-complexity files first\\n\"\n        report += \"5. Test thoroughly after each batch\\n\"\n        report += \"6. Monitor feature flags and performance metrics\\n\"\n        \n        return report\n    \n    def save_migration_log(self):\n        """Save migration log to file."""\n        try:\n            log_dir = self.project_root / \"logs\"\n            log_dir.mkdir(exist_ok=True)\n            \n            log_file = log_dir / f\"empathy_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log\"\n            \n            with open(log_file, 'w', encoding='utf-8') as f:\n                f.write(\"NGX Empathy Services Migration Log\\n\")\n                f.write(f\"Generated: {datetime.now().isoformat()}\\n\\n\")\n                \n                for entry in self.migration_log:\n                    f.write(f\"[{entry['timestamp']}] {entry['level']}: {entry['message']}\\n\")\n            \n            self.log(f\"Migration log saved to {log_file}\", \"SUCCESS\")\n            \n        except Exception as e:\n            self.log(f\"Error saving migration log: {e}\", \"ERROR\")\n\n\ndef main():\n    \"\"\"Main entry point.\"\"\"\n    parser = argparse.ArgumentParser(\n        description=\"NGX Empathy Services Migration Tool\",\n        formatter_class=argparse.RawDescriptionHelpFormatter,\n        epilog=\"\"\"\nExamples:\n    # Check current migration status\n    python scripts/migrate_empathy_imports.py --mode check\n    \n    # Run migration in dry-run mode (safe)\n    python scripts/migrate_empathy_imports.py --mode migrate --dry-run\n    \n    # Execute actual migration\n    python scripts/migrate_empathy_imports.py --mode migrate\n    \n    # Revert migration using backups\n    python scripts/migrate_empathy_imports.py --mode revert\n        \"\"\"\n    )\n    \n    parser.add_argument(\n        \"--mode\",\n        choices=[\"check\", \"migrate\", \"revert\"],\n        required=True,\n        help=\"Migration mode to run\"\n    )\n    \n    parser.add_argument(\n        \"--dry-run\",\n        action=\"store_true\",\n        help=\"Run in dry-run mode (no actual changes)\"\n    )\n    \n    parser.add_argument(\n        \"--verbose\",\n        action=\"store_true\",\n        help=\"Enable verbose logging\"\n    )\n    \n    args = parser.parse_args()\n    \n    # Create migration tool\n    tool = EmpathyMigrationTool()\n    \n    # Print header\n    print(f\"{Colors.BOLD}{Colors.CYAN}{'='*60}\")\n    print(\"NGX Empathy Services Migration Tool\")\n    print(f\"{'='*60}{Colors.END}\\n\")\n    \n    try:\n        if args.mode == \"check\":\n            status = tool.check_migration_status()\n            report = tool.generate_migration_report(status)\n            print(report)\n            \n        elif args.mode == \"migrate\":\n            if args.dry_run:\n                tool.log(\"Running migration in DRY-RUN mode - no changes will be made\", \"WARNING\")\n            \n            results = tool.run_migration(dry_run=args.dry_run)\n            \n            tool.log(f\"Migration completed!\", \"SUCCESS\")\n            tool.log(f\"Files processed: {results['total_files_processed']}\", \"INFO\")\n            tool.log(f\"Files migrated: {results['files_migrated']}\", \"SUCCESS\")\n            tool.log(f\"Total changes: {results['total_changes']}\", \"INFO\")\n            \n            if results['files_failed'] > 0:\n                tool.log(f\"Files failed: {results['files_failed']}\", \"ERROR\")\n                for error_file in results['errors']:\n                    tool.log(f\"Failed: {error_file}\", \"ERROR\")\n            \n            if not args.dry_run:\n                tool.log(f\"Backups created in: {tool.backup_dir}\", \"INFO\")\n                \n        elif args.mode == \"revert\":\n            if tool.revert_migration():\n                tool.log(\"Migration reverted successfully\", \"SUCCESS\")\n            else:\n                tool.log(\"Migration revert failed\", \"ERROR\")\n                return 1\n        \n        # Save log\n        tool.save_migration_log()\n        \n        return 0\n        \n    except KeyboardInterrupt:\n        tool.log(\"Migration interrupted by user\", \"WARNING\")\n        return 1\n    except Exception as e:\n        tool.log(f\"Unexpected error: {e}\", \"ERROR\")\n        return 1\n\n\nif __name__ == \"__main__\":\n    sys.exit(main())"