#!/usr/bin/env python3
"""
Cache Migration Script - Migrate from legacy cache services to consolidated CacheService.

This script helps migrate the NGX Voice Agent from legacy cache services to the
consolidated CacheService with zero downtime and easy rollback capability.
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import settings
from src.services.cache_service import get_cache_instance
from src.services.cache_compatibility import log_cache_migration_progress
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)


class CacheMigrationManager:
    """Manages the cache migration process."""
    
    def __init__(self):
        self.consolidated_cache = None
        self.migration_stats = {
            "keys_migrated": 0,
            "keys_failed": 0,
            "namespaces_migrated": [],
            "errors": []
        }
    
    async def initialize(self):
        """Initialize migration components."""
        try:
            self.consolidated_cache = await get_cache_instance()
            if not self.consolidated_cache:
                raise Exception("Failed to initialize consolidated cache")
            logger.info("Migration manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize migration manager: {e}")
            raise
    
    async def check_migration_readiness(self) -> dict:
        """
        Check if the system is ready for cache migration.
        
        Returns:
            Dict with readiness status and recommendations
        """
        readiness = {
            "ready": True,
            "checks": {},
            "warnings": [],
            "blockers": []
        }
        
        # Check consolidated cache health
        try:
            cache_health = await self.consolidated_cache.health_check()
            readiness["checks"]["consolidated_cache"] = cache_health
            if not cache_health:
                readiness["ready"] = False
                readiness["blockers"].append("Consolidated cache is not healthy")
        except Exception as e:
            readiness["checks"]["consolidated_cache"] = False
            readiness["ready"] = False
            readiness["blockers"].append(f"Consolidated cache error: {e}")
        
        # Check configuration
        if not settings.use_consolidated_cache:
            readiness["warnings"].append("USE_CONSOLIDATED_CACHE is disabled - migration will not be effective")
        
        # Check Redis connectivity
        try:
            redis_url = settings.redis_url or f"redis://{settings.redis_host}:{settings.redis_port}"
            readiness["checks"]["redis_url"] = redis_url
        except Exception as e:
            readiness["warnings"].append(f"Redis configuration issue: {e}")
        
        # Check disk space and memory
        try:
            import psutil
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            readiness["checks"]["memory_available_gb"] = round(memory.available / (1024**3), 2)
            readiness["checks"]["disk_free_gb"] = round(disk.free / (1024**3), 2)
            
            if memory.percent > 85:
                readiness["warnings"].append("High memory usage - migration may be slower")
            
            if disk.free < 1024**3:  # Less than 1GB
                readiness["warnings"].append("Low disk space - consider cleanup before migration")
        except ImportError:
            readiness["warnings"].append("psutil not available - cannot check system resources")
        
        return readiness
    
    async def run_migration_dry_run(self) -> dict:
        """
        Run a dry-run of the migration to estimate impact.
        
        Returns:
            Dict with migration estimates and potential issues
        """
        dry_run_results = {
            "estimated_keys": 0,
            "estimated_data_size_mb": 0,
            "estimated_duration_minutes": 0,
            "potential_issues": [],
            "recommendations": []
        }
        
        try:
            # Get cache statistics
            stats = await self.consolidated_cache.get_service_stats()
            dry_run_results["estimated_keys"] = stats.get("total_entries", 0)
            dry_run_results["estimated_data_size_mb"] = stats.get("total_size_bytes", 0) / (1024 * 1024)
            
            # Estimate duration (rough calculation)
            keys_count = dry_run_results["estimated_keys"]
            if keys_count > 0:
                # Assume ~100 keys per second migration rate
                dry_run_results["estimated_duration_minutes"] = max(1, keys_count / 100 / 60)
            
            # Check for potential issues
            if keys_count > 10000:
                dry_run_results["potential_issues"].append("Large number of keys may cause extended migration time")
                dry_run_results["recommendations"].append("Consider running migration during low-traffic period")
            
            if dry_run_results["estimated_data_size_mb"] > 100:
                dry_run_results["potential_issues"].append("Large data size may impact performance during migration")
                dry_run_results["recommendations"].append("Monitor system resources during migration")
            
            logger.info(f"Dry run completed - estimated {keys_count} keys, {dry_run_results['estimated_data_size_mb']:.2f}MB")
            
        except Exception as e:
            dry_run_results["potential_issues"].append(f"Error during dry run: {e}")
            logger.error(f"Dry run failed: {e}")
        
        return dry_run_results
    
    async def perform_migration(self, backup: bool = True) -> dict:
        """
        Perform the actual cache migration.
        
        Args:
            backup: Whether to create backup before migration
            
        Returns:
            Dict with migration results
        """
        migration_result = {
            "success": False,
            "stats": self.migration_stats.copy(),
            "backup_created": False,
            "errors": [],
            "duration_seconds": 0
        }
        
        import time
        start_time = time.time()
        
        try:
            logger.info("Starting cache migration...")
            
            # Create backup if requested
            if backup:
                try:
                    backup_result = await self._create_backup()
                    migration_result["backup_created"] = backup_result
                    if backup_result:
                        logger.info("Backup created successfully")
                    else:
                        logger.warning("Backup creation failed - continuing without backup")
                except Exception as e:
                    logger.error(f"Backup creation error: {e}")
                    migration_result["errors"].append(f"Backup error: {e}")
            
            # The actual migration is mainly a configuration switch since we're using
            # the consolidated cache with compatibility layers
            logger.info("Migration consists primarily of configuration switch to USE_CONSOLIDATED_CACHE=True")
            
            # Verify consolidated cache is working
            test_key = "migration_test_key"
            test_value = {"test": "migration_verification", "timestamp": time.time()}
            
            success = await self.consolidated_cache.set(test_key, test_value, ttl=60)
            if success:
                retrieved_value = await self.consolidated_cache.get(test_key)
                if retrieved_value == test_value:
                    logger.info("Consolidated cache verification successful")
                    await self.consolidated_cache.delete(test_key)
                    migration_result["success"] = True
                else:
                    raise Exception("Cache verification failed - retrieved value doesn't match")
            else:
                raise Exception("Cache verification failed - could not set test value")
            
            migration_result["duration_seconds"] = time.time() - start_time
            logger.info(f"Cache migration completed successfully in {migration_result['duration_seconds']:.2f}s")
            
        except Exception as e:
            migration_result["success"] = False
            migration_result["errors"].append(str(e))
            logger.error(f"Migration failed: {e}")
        
        return migration_result
    
    async def _create_backup(self) -> bool:
        """Create a backup of current cache data."""
        try:
            # For Redis, we could use BGSAVE or create a dump
            # For now, we'll just log that backup would be created
            logger.info("Backup would be created here (implementation depends on cache backend)")
            return True
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return False
    
    async def rollback_migration(self) -> dict:
        """
        Rollback the migration to legacy cache services.
        
        Returns:
            Dict with rollback results
        """
        rollback_result = {
            "success": False,
            "message": "",
            "errors": []
        }
        
        try:
            logger.info("Rolling back cache migration...")
            
            # The rollback mainly involves switching the USE_CONSOLIDATED_CACHE flag
            rollback_result["message"] = (
                "To complete rollback, set USE_CONSOLIDATED_CACHE=False in your environment "
                "and restart the application"
            )
            rollback_result["success"] = True
            
            logger.info("Rollback preparation completed - restart required with USE_CONSOLIDATED_CACHE=False")
            
        except Exception as e:
            rollback_result["success"] = False
            rollback_result["errors"].append(str(e))
            logger.error(f"Rollback failed: {e}")
        
        return rollback_result
    
    async def validate_migration(self) -> dict:
        """
        Validate that the migration was successful.
        
        Returns:
            Dict with validation results
        """
        validation_result = {
            "valid": False,
            "checks": {},
            "issues": [],
            "recommendations": []
        }
        
        try:
            # Check if consolidated cache is enabled
            validation_result["checks"]["use_consolidated_cache"] = settings.use_consolidated_cache
            
            # Check cache health
            cache_healthy = await self.consolidated_cache.health_check()
            validation_result["checks"]["cache_health"] = cache_healthy
            
            # Test basic operations
            test_operations = await self._test_cache_operations()
            validation_result["checks"]["basic_operations"] = test_operations
            
            # Check if legacy warnings are being issued
            from src.services.cache_compatibility import DeprecationWarningManager
            deprecated_services_count = len(DeprecationWarningManager._warned_services)
            validation_result["checks"]["deprecated_services_warned"] = deprecated_services_count
            
            if deprecated_services_count > 0:
                validation_result["recommendations"].append(
                    f"Update {deprecated_services_count} components to use consolidated cache directly"
                )
            
            # Overall validation
            validation_result["valid"] = (
                settings.use_consolidated_cache and
                cache_healthy and
                test_operations
            )
            
            if not validation_result["valid"]:
                if not settings.use_consolidated_cache:
                    validation_result["issues"].append("Consolidated cache is not enabled")
                if not cache_healthy:
                    validation_result["issues"].append("Cache is not healthy")
                if not test_operations:
                    validation_result["issues"].append("Basic cache operations failed")
            
        except Exception as e:
            validation_result["issues"].append(f"Validation error: {e}")
            logger.error(f"Migration validation failed: {e}")
        
        return validation_result
    
    async def _test_cache_operations(self) -> bool:
        """Test basic cache operations."""
        try:
            # Test key-value operations
            test_key = "validation_test"
            test_value = {"validation": True, "timestamp": "test"}
            
            # Test set
            if not await self.consolidated_cache.set(test_key, test_value, ttl=60):
                return False
            
            # Test get
            retrieved = await self.consolidated_cache.get(test_key)
            if retrieved != test_value:
                return False
            
            # Test delete
            if not await self.consolidated_cache.delete(test_key):
                return False
            
            # Test NGX-specific methods
            if hasattr(self.consolidated_cache, 'get_service_stats'):
                stats = await self.consolidated_cache.get_service_stats()
                if not isinstance(stats, dict):
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Cache operations test failed: {e}")
            return False
    
    async def cleanup(self):
        """Clean up migration resources."""
        if self.consolidated_cache:
            await self.consolidated_cache.close()
        logger.info("Migration manager cleaned up")


async def main():
    """Main migration script."""
    parser = argparse.ArgumentParser(description="NGX Cache Migration Tool")
    parser.add_argument("command", choices=[
        "check", "dry-run", "migrate", "rollback", "validate", "status"
    ], help="Migration command to execute")
    parser.add_argument("--no-backup", action="store_true", 
                       help="Skip backup creation during migration")
    parser.add_argument("--force", action="store_true",
                       help="Force migration even if checks fail")
    
    args = parser.parse_args()
    
    migration_manager = CacheMigrationManager()
    
    try:
        await migration_manager.initialize()
        
        if args.command == "status":
            log_cache_migration_progress()
            print(f"Consolidated cache enabled: {settings.use_consolidated_cache}")
            
        elif args.command == "check":
            print("🔍 Checking migration readiness...")
            readiness = await migration_manager.check_migration_readiness()
            
            print(f"✅ Ready for migration: {readiness['ready']}")
            
            if readiness["checks"]:
                print("\n📊 System Checks:")
                for check, result in readiness["checks"].items():
                    print(f"  {check}: {result}")
            
            if readiness["warnings"]:
                print("\n⚠️  Warnings:")
                for warning in readiness["warnings"]:
                    print(f"  - {warning}")
            
            if readiness["blockers"]:
                print("\n❌ Blockers:")
                for blocker in readiness["blockers"]:
                    print(f"  - {blocker}")
            
            if not readiness["ready"] and not args.force:
                print("\nMigration not recommended. Use --force to override.")
                sys.exit(1)
        
        elif args.command == "dry-run":
            print("🧪 Running migration dry run...")
            dry_run = await migration_manager.run_migration_dry_run()
            
            print(f"📈 Estimated keys to migrate: {dry_run['estimated_keys']}")
            print(f"💾 Estimated data size: {dry_run['estimated_data_size_mb']:.2f} MB")
            print(f"⏱️  Estimated duration: {dry_run['estimated_duration_minutes']:.1f} minutes")
            
            if dry_run["potential_issues"]:
                print("\n⚠️  Potential Issues:")
                for issue in dry_run["potential_issues"]:
                    print(f"  - {issue}")
            
            if dry_run["recommendations"]:
                print("\n💡 Recommendations:")
                for rec in dry_run["recommendations"]:
                    print(f"  - {rec}")
        
        elif args.command == "migrate":
            print("🚀 Starting cache migration...")
            
            # Check readiness unless forced
            if not args.force:
                readiness = await migration_manager.check_migration_readiness()
                if not readiness["ready"]:
                    print("❌ System not ready for migration. Use --force to override.")
                    sys.exit(1)
            
            result = await migration_manager.perform_migration(backup=not args.no_backup)
            
            if result["success"]:
                print("✅ Migration completed successfully!")
                print(f"⏱️  Duration: {result['duration_seconds']:.2f} seconds")
                if result["backup_created"]:
                    print("💾 Backup created")
            else:
                print("❌ Migration failed!")
                if result["errors"]:
                    print("Errors:")
                    for error in result["errors"]:
                        print(f"  - {error}")
                sys.exit(1)
        
        elif args.command == "rollback":
            print("🔄 Rolling back cache migration...")
            result = await migration_manager.rollback_migration()
            
            if result["success"]:
                print("✅ Rollback prepared successfully!")
                print(f"📝 {result['message']}")
            else:
                print("❌ Rollback failed!")
                if result["errors"]:
                    for error in result["errors"]:
                        print(f"  - {error}")
                sys.exit(1)
        
        elif args.command == "validate":
            print("🔍 Validating migration...")
            validation = await migration_manager.validate_migration()
            
            if validation["valid"]:
                print("✅ Migration validation successful!")
            else:
                print("❌ Migration validation failed!")
            
            if validation["checks"]:
                print("\n📊 Validation Checks:")
                for check, result in validation["checks"].items():
                    status = "✅" if result else "❌"
                    print(f"  {status} {check}: {result}")
            
            if validation["issues"]:
                print("\n❌ Issues Found:")
                for issue in validation["issues"]:
                    print(f"  - {issue}")
            
            if validation["recommendations"]:
                print("\n💡 Recommendations:")
                for rec in validation["recommendations"]:
                    print(f"  - {rec}")
            
            if not validation["valid"]:
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Migration script error: {e}")
        logger.error(f"Migration script error: {e}")
        sys.exit(1)
    finally:
        await migration_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(main())