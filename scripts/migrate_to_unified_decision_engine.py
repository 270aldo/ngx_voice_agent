#!/usr/bin/env python3
"""
Migration script to update references from old decision engine services to the new unified service.
This script will help transition the codebase to use the UnifiedDecisionEngine.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Define the old imports and their replacements
OLD_IMPORTS = [
    (r'from \.\.services\.decision_engine_service import DecisionEngineService',
     'from ..services.unified_decision_engine import UnifiedDecisionEngine'),
    (r'from \.\.services\.optimized_decision_engine_service import OptimizedDecisionEngineService',
     'from ..services.unified_decision_engine import UnifiedDecisionEngine'),
    (r'from \.\.services\.enhanced_decision_engine_service import EnhancedDecisionEngineService',
     'from ..services.unified_decision_engine import UnifiedDecisionEngine'),
    (r'from src\.services\.decision_engine_service import DecisionEngineService',
     'from src.services.unified_decision_engine import UnifiedDecisionEngine'),
    (r'from src\.services\.optimized_decision_engine_service import OptimizedDecisionEngineService',
     'from src.services.unified_decision_engine import UnifiedDecisionEngine'),
    (r'from src\.services\.enhanced_decision_engine_service import EnhancedDecisionEngineService',
     'from src.services.unified_decision_engine import UnifiedDecisionEngine'),
]

# Define class instantiation replacements
CLASS_REPLACEMENTS = [
    (r'DecisionEngineService\s*\(', 'UnifiedDecisionEngine('),
    (r'OptimizedDecisionEngineService\s*\(', 'UnifiedDecisionEngine('),
    (r'EnhancedDecisionEngineService\s*\(', 'UnifiedDecisionEngine('),
]

# Configuration mapping for different modes
CONFIG_MAPPING = """
# Migration Guide for UnifiedDecisionEngine Configuration

## For DecisionEngineService users:
```python
# Old
engine = DecisionEngineService(
    conversion_predictor=conv_predictor,
    objection_predictor=obj_predictor,
    needs_predictor=needs_predictor
)

# New
from src.services.unified_decision_engine import UnifiedDecisionEngine, DecisionConfig, OptimizationMode

engine = UnifiedDecisionEngine(
    conversion_predictor=conv_predictor,
    objection_predictor=obj_predictor,
    needs_predictor=needs_predictor,
    config=DecisionConfig(
        optimization_mode=OptimizationMode.STANDARD
    )
)
```

## For OptimizedDecisionEngineService users:
```python
# Old
engine = OptimizedDecisionEngineService(
    enable_cache=True,
    cache_ttl=300
)

# New
engine = UnifiedDecisionEngine(
    config=DecisionConfig(
        optimization_mode=OptimizationMode.FAST,
        enable_cache=True,
        cache_ttl=300
    )
)
```

## For EnhancedDecisionEngineService users:
```python
# Old
engine = EnhancedDecisionEngineService(
    enable_advanced_features=True
)

# New
engine = UnifiedDecisionEngine(
    config=DecisionConfig(
        optimization_mode=OptimizationMode.ACCURATE,
        enable_advanced_strategies=True
    )
)
```
"""


def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in the directory."""
    return list(directory.rglob("*.py"))


def update_file(file_path: Path, dry_run: bool = True) -> List[str]:
    """Update a single file with new imports and class names."""
    changes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Update imports
        for old_import, new_import in OLD_IMPORTS:
            if re.search(old_import, content):
                content = re.sub(old_import, new_import, content)
                changes.append(f"Updated import: {old_import} -> {new_import}")
        
        # Update class instantiations
        for old_class, new_class in CLASS_REPLACEMENTS:
            if re.search(old_class, content):
                content = re.sub(old_class, new_class, content)
                changes.append(f"Updated class: {old_class} -> {new_class}")
        
        # Only write if changes were made
        if content != original_content and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
    except Exception as e:
        changes.append(f"ERROR: {str(e)}")
    
    return changes


def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate to UnifiedDecisionEngine"
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path("src"),
        help="Directory to search for Python files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes"
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Show configuration migration guide"
    )
    
    args = parser.parse_args()
    
    if args.show_config:
        print(CONFIG_MAPPING)
        return
    
    print(f"{'DRY RUN' if args.dry_run else 'MIGRATION'} MODE")
    print(f"Searching for Python files in: {args.directory}")
    print("-" * 80)
    
    files = find_python_files(args.directory)
    total_changes = 0
    
    for file_path in files:
        # Skip migration script itself
        if file_path.name == "migrate_to_unified_decision_engine.py":
            continue
        
        # Skip the old service files
        if file_path.name in [
            "decision_engine_service.py",
            "optimized_decision_engine_service.py",
            "enhanced_decision_engine_service.py"
        ]:
            continue
        
        changes = update_file(file_path, dry_run=args.dry_run)
        
        if changes:
            print(f"\n{file_path}:")
            for change in changes:
                print(f"  - {change}")
            total_changes += len(changes)
    
    print("\n" + "-" * 80)
    print(f"Total changes: {total_changes}")
    
    if args.dry_run:
        print("\nThis was a dry run. No files were modified.")
        print("Run without --dry-run to apply changes.")
    else:
        print("\nMigration complete!")
        print("\nNext steps:")
        print("1. Review the changes")
        print("2. Update any custom configurations (run with --show-config)")
        print("3. Run tests to ensure everything works")
        print("4. Delete old service files when ready")


if __name__ == "__main__":
    main()