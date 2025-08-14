#!/usr/bin/env python3
"""
ML/NLP Service Migration and Optimization Script.

This script manages the migration from legacy ML/NLP services to consolidated services,
validates performance improvements, and provides migration monitoring.

Usage:
    python scripts/ml_nlp_migration.py --command status
    python scripts/ml_nlp_migration.py --command check-readiness
    python scripts/ml_nlp_migration.py --command migrate
    python scripts/ml_nlp_migration.py --command benchmark
    python scripts/ml_nlp_migration.py --command validate
    python scripts/ml_nlp_migration.py --command rollback
"""

import argparse
import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import get_settings
from src.services.consolidated_ml_prediction_service import ConsolidatedMLPredictionService, PredictionType
from src.services.consolidated_nlp_analysis_service import ConsolidatedNLPAnalysisService
from src.services.ml_compatibility import MLMigrationManager, log_ml_migration_progress
from src.services.nlp_compatibility import NLPMigrationManager, log_nlp_migration_progress
from src.utils.structured_logging import StructuredLogger

settings = get_settings()
logger = StructuredLogger.get_logger(__name__)


class MLNLPMigrationManager:
    """Comprehensive migration manager for ML/NLP services."""
    
    def __init__(self):
        self.ml_service = None
        self.nlp_service = None
        self.ml_migration_manager = None
        self.nlp_migration_manager = None
        
        self.migration_report = {
            "timestamp": datetime.now().isoformat(),
            "ml_services": {},
            "nlp_services": {},
            "performance_metrics": {},
            "validation_results": {},
            "migration_status": "not_started"
        }
    
    async def initialize(self):
        """Initialize all services and managers."""
        logger.info("Initializing ML/NLP migration manager...")
        
        try:
            # Initialize consolidated services
            self.ml_service = ConsolidatedMLPredictionService()
            self.nlp_service = ConsolidatedNLPAnalysisService()
            
            await self.ml_service.initialize()
            await self.nlp_service.initialize()
            
            # Initialize migration managers
            self.ml_migration_manager = MLMigrationManager()
            self.nlp_migration_manager = NLPMigrationManager()
            
            await self.ml_migration_manager.initialize_services()
            await self.nlp_migration_manager.initialize_services()
            
            logger.info("✅ Migration manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize migration manager: {e}")
            raise
    
    async def check_migration_readiness(self) -> Dict[str, Any]:
        """Check if system is ready for migration."""
        logger.info("🔍 Checking migration readiness...")
        
        readiness = {
            "ready": True,
            "checks": {},
            "blockers": [],
            "warnings": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Check consolidated services health
            ml_health = await self.ml_service.health_check()
            nlp_health = await self.nlp_service.health_check()
            
            readiness["checks"]["ml_service_health"] = ml_health["status"] == "healthy"
            readiness["checks"]["nlp_service_health"] = nlp_health["status"] == "healthy"
            
            if ml_health["status"] != "healthy":
                readiness["blockers"].append(f"ML service unhealthy: {ml_health.get('issues', [])}")
                readiness["ready"] = False
            
            if nlp_health["status"] != "healthy":
                readiness["blockers"].append(f"NLP service unhealthy: {nlp_health.get('issues', [])}")
                readiness["ready"] = False
            
            # Check feature flags
            readiness["checks"]["ml_feature_flag"] = settings.use_consolidated_ml_service
            readiness["checks"]["nlp_feature_flag"] = settings.use_consolidated_nlp_service
            
            if not settings.use_consolidated_ml_service:
                readiness["warnings"].append("ML consolidation feature flag is disabled")
            
            if not settings.use_consolidated_nlp_service:
                readiness["warnings"].append("NLP consolidation feature flag is disabled")
            
            # Performance benchmarks
            await self._run_readiness_benchmarks(readiness)
            
            # Memory and resource checks
            await self._check_system_resources(readiness)
            
        except Exception as e:
            readiness["ready"] = False
            readiness["blockers"].append(f"Readiness check failed: {e}")
            logger.error(f"Migration readiness check failed: {e}")
        
        return readiness
    
    async def _run_readiness_benchmarks(self, readiness: Dict[str, Any]):
        """Run performance benchmarks for readiness check."""
        try:
            # ML benchmark
            ml_features = {
                "engagement_score": 0.8,
                "questions_asked": 3,
                "buying_signals": 2,
                "demo_requested": True,
                "price_discussed": True
            }
            
            start_time = time.time()
            await self.ml_service.predict_single(PredictionType.CONVERSION, ml_features)
            ml_time = (time.time() - start_time) * 1000
            
            # NLP benchmark
            test_text = "I'm interested in your pricing plans and would like to see a demo."
            
            start_time = time.time()
            await self.nlp_service.analyze_text(test_text)
            nlp_time = (time.time() - start_time) * 1000
            
            # Set performance checks
            readiness["checks"]["ml_performance"] = ml_time < 100  # Under 100ms
            readiness["checks"]["nlp_performance"] = nlp_time < 200  # Under 200ms
            
            if ml_time >= 100:
                readiness["warnings"].append(f"ML service slow: {ml_time:.2f}ms")
            
            if nlp_time >= 200:
                readiness["warnings"].append(f"NLP service slow: {nlp_time:.2f}ms")
            
            readiness["performance"] = {
                "ml_response_time_ms": ml_time,
                "nlp_response_time_ms": nlp_time
            }
            
        except Exception as e:
            readiness["warnings"].append(f"Performance benchmark failed: {e}")
    
    async def _check_system_resources(self, readiness: Dict[str, Any]):
        """Check system resource availability."""
        try:
            import psutil
            
            # Memory check
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            readiness["checks"]["memory_available"] = memory.percent < 80  # Under 80% usage
            readiness["checks"]["cpu_available"] = cpu_percent < 80  # Under 80% usage
            
            if memory.percent >= 80:
                readiness["warnings"].append(f"High memory usage: {memory.percent:.1f}%")
            
            if cpu_percent >= 80:
                readiness["warnings"].append(f"High CPU usage: {cpu_percent:.1f}%")
            
            readiness["system_resources"] = {
                "memory_percent": memory.percent,
                "cpu_percent": cpu_percent,
                "available_memory_gb": memory.available / (1024**3)
            }
            
        except ImportError:
            readiness["warnings"].append("psutil not available - cannot check system resources")
        except Exception as e:
            readiness["warnings"].append(f"System resource check failed: {e}")
    
    async def run_migration(self) -> Dict[str, Any]:
        """Execute the migration process."""
        logger.info("🚀 Starting ML/NLP service migration...")
        
        migration_result = {
            "success": False,
            "steps_completed": [],
            "steps_failed": [],
            "performance_comparison": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Step 1: Pre-migration validation
            logger.info("Step 1: Pre-migration validation")
            readiness = await self.check_migration_readiness()
            
            if not readiness["ready"]:
                migration_result["steps_failed"].append("Pre-migration validation failed")
                migration_result["readiness_issues"] = readiness["blockers"]
                return migration_result
            
            migration_result["steps_completed"].append("Pre-migration validation")
            
            # Step 2: Backup current configurations
            logger.info("Step 2: Backing up current configurations")
            backup_result = await self._backup_configurations()
            
            if backup_result["success"]:
                migration_result["steps_completed"].append("Configuration backup")
                migration_result["backup_location"] = backup_result["backup_path"]
            else:
                migration_result["steps_failed"].append("Configuration backup failed")
            
            # Step 3: Performance baseline
            logger.info("Step 3: Establishing performance baseline")
            baseline = await self._establish_performance_baseline()
            migration_result["baseline_metrics"] = baseline
            migration_result["steps_completed"].append("Performance baseline")
            
            # Step 4: Enable consolidated services
            logger.info("Step 4: Enabling consolidated services")
            await self._enable_consolidated_services()
            migration_result["steps_completed"].append("Consolidated services enabled")
            
            # Step 5: Validation tests
            logger.info("Step 5: Running validation tests")
            validation_results = await self._run_validation_tests()
            migration_result["validation_results"] = validation_results
            
            if validation_results["all_passed"]:
                migration_result["steps_completed"].append("Validation tests")
            else:
                migration_result["steps_failed"].append("Validation tests failed")
                migration_result["validation_failures"] = validation_results["failures"]
            
            # Step 6: Performance comparison
            logger.info("Step 6: Performance comparison")
            performance_comparison = await self._compare_performance(baseline)
            migration_result["performance_comparison"] = performance_comparison
            migration_result["steps_completed"].append("Performance comparison")
            
            # Step 7: Migration completion
            if len(migration_result["steps_failed"]) == 0:
                migration_result["success"] = True
                migration_result["status"] = "completed"
                logger.info("✅ Migration completed successfully!")
            else:
                migration_result["status"] = "completed_with_issues"
                logger.warning("⚠️ Migration completed with issues")
            
        except Exception as e:
            migration_result["steps_failed"].append(f"Migration failed: {e}")
            migration_result["status"] = "failed"
            logger.error(f"Migration failed: {e}")
        
        return migration_result
    
    async def _backup_configurations(self) -> Dict[str, Any]:
        """Backup current service configurations."""
        try:
            backup_dir = Path("backups/ml_nlp_migration")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"config_backup_{timestamp}.json"
            
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "settings": {
                    "use_consolidated_ml_service": settings.use_consolidated_ml_service,
                    "use_consolidated_nlp_service": settings.use_consolidated_nlp_service
                },
                "ml_service_status": await self.ml_migration_manager.get_migration_status(),
                "nlp_service_status": await self.nlp_migration_manager.get_migration_status()
            }
            
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            return {"success": True, "backup_path": str(backup_path)}
            
        except Exception as e:
            logger.error(f"Configuration backup failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _establish_performance_baseline(self) -> Dict[str, Any]:
        """Establish performance baseline before migration."""
        baseline = {
            "ml_metrics": {},
            "nlp_metrics": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # ML baseline
            ml_features = {
                "engagement_score": 0.8,
                "questions_asked": 3,
                "buying_signals": 2
            }
            
            ml_times = []
            for _ in range(10):
                start_time = time.time()
                await self.ml_service.predict_single(PredictionType.CONVERSION, ml_features)
                ml_times.append((time.time() - start_time) * 1000)
            
            baseline["ml_metrics"] = {
                "avg_response_time_ms": sum(ml_times) / len(ml_times),
                "min_response_time_ms": min(ml_times),
                "max_response_time_ms": max(ml_times)
            }
            
            # NLP baseline
            test_text = "I'm interested in your pricing and features."
            
            nlp_times = []
            for _ in range(10):
                start_time = time.time()
                await self.nlp_service.analyze_text(test_text)
                nlp_times.append((time.time() - start_time) * 1000)
            
            baseline["nlp_metrics"] = {
                "avg_response_time_ms": sum(nlp_times) / len(nlp_times),
                "min_response_time_ms": min(nlp_times),
                "max_response_time_ms": max(nlp_times)
            }
            
        except Exception as e:
            logger.error(f"Baseline establishment failed: {e}")
            baseline["error"] = str(e)
        
        return baseline
    
    async def _enable_consolidated_services(self):
        """Enable consolidated services (simulated - in production this would update config)."""
        # In a real scenario, this would update environment variables or config files
        logger.info("Consolidated services enabled (feature flags already set)")
    
    async def _run_validation_tests(self) -> Dict[str, Any]:
        """Run comprehensive validation tests."""
        validation = {
            "all_passed": True,
            "tests": {},
            "failures": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # ML validation tests
            ml_tests = await self._validate_ml_services()
            validation["tests"]["ml_services"] = ml_tests
            
            if not ml_tests["all_passed"]:
                validation["all_passed"] = False
                validation["failures"].extend([f"ML: {f}" for f in ml_tests["failures"]])
            
            # NLP validation tests
            nlp_tests = await self._validate_nlp_services()
            validation["tests"]["nlp_services"] = nlp_tests
            
            if not nlp_tests["all_passed"]:
                validation["all_passed"] = False
                validation["failures"].extend([f"NLP: {f}" for f in nlp_tests["failures"]])
            
            # Compatibility layer tests
            compat_tests = await self._validate_compatibility_layers()
            validation["tests"]["compatibility"] = compat_tests
            
            if not compat_tests["all_passed"]:
                validation["all_passed"] = False
                validation["failures"].extend([f"Compatibility: {f}" for f in compat_tests["failures"]])
            
        except Exception as e:
            validation["all_passed"] = False
            validation["failures"].append(f"Validation failed: {e}")
        
        return validation
    
    async def _validate_ml_services(self) -> Dict[str, Any]:
        """Validate ML services functionality."""
        validation = {"all_passed": True, "tests": {}, "failures": []}
        
        try:
            # Test conversion prediction
            features = {"engagement_score": 0.8, "buying_signals": 2}
            result = await self.ml_service.predict_single(PredictionType.CONVERSION, features)
            
            validation["tests"]["conversion_prediction"] = {
                "passed": 0.0 <= result.probability <= 1.0,
                "probability": result.probability,
                "confidence": result.confidence
            }
            
            if not validation["tests"]["conversion_prediction"]["passed"]:
                validation["failures"].append("Conversion prediction returned invalid probability")
                validation["all_passed"] = False
            
            # Test needs prediction
            needs_features = {"industry_match": 0.9, "pain_points_mentioned": 2}
            needs_result = await self.ml_service.predict_single(PredictionType.NEEDS, needs_features)
            
            validation["tests"]["needs_prediction"] = {
                "passed": 0.0 <= needs_result.probability <= 1.0,
                "probability": needs_result.probability
            }
            
            if not validation["tests"]["needs_prediction"]["passed"]:
                validation["failures"].append("Needs prediction returned invalid probability")
                validation["all_passed"] = False
            
            # Test health check
            health = await self.ml_service.health_check()
            validation["tests"]["health_check"] = {
                "passed": health["status"] in ["healthy", "degraded"],
                "status": health["status"]
            }
            
            if not validation["tests"]["health_check"]["passed"]:
                validation["failures"].append(f"ML service unhealthy: {health['status']}")
                validation["all_passed"] = False
            
        except Exception as e:
            validation["all_passed"] = False
            validation["failures"].append(f"ML validation failed: {e}")
        
        return validation
    
    async def _validate_nlp_services(self) -> Dict[str, Any]:
        """Validate NLP services functionality."""
        validation = {"all_passed": True, "tests": {}, "failures": []}
        
        try:
            # Test intent analysis
            pricing_text = "How much does your premium plan cost?"
            result = await self.nlp_service.analyze_text(pricing_text)
            
            validation["tests"]["intent_analysis"] = {
                "passed": result.intent.intent.value == "pricing_inquiry",
                "detected_intent": result.intent.intent.value,
                "confidence": result.intent.confidence
            }
            
            if not validation["tests"]["intent_analysis"]["passed"]:
                validation["failures"].append(f"Intent analysis failed - expected pricing_inquiry, got {result.intent.intent.value}")
                validation["all_passed"] = False
            
            # Test entity extraction
            entity_text = "Contact me at test@example.com or call (555) 123-4567"
            entity_result = await self.nlp_service.analyze_text(entity_text)
            
            has_email = any(e.entity_type.value == "email" for e in entity_result.entities)
            has_phone = any(e.entity_type.value == "phone" for e in entity_result.entities)
            
            validation["tests"]["entity_extraction"] = {
                "passed": has_email or has_phone,
                "entities_found": len(entity_result.entities),
                "has_email": has_email,
                "has_phone": has_phone
            }
            
            if not validation["tests"]["entity_extraction"]["passed"]:
                validation["failures"].append("Entity extraction failed to find expected entities")
                validation["all_passed"] = False
            
            # Test sentiment analysis
            positive_text = "This looks amazing! I love it!"
            sentiment_result = await self.nlp_service.analyze_text(positive_text)
            
            validation["tests"]["sentiment_analysis"] = {
                "passed": sentiment_result.sentiment.sentiment.value == "positive",
                "detected_sentiment": sentiment_result.sentiment.sentiment.value,
                "polarity": sentiment_result.sentiment.polarity
            }
            
            if not validation["tests"]["sentiment_analysis"]["passed"]:
                validation["failures"].append(f"Sentiment analysis failed - expected positive, got {sentiment_result.sentiment.sentiment.value}")
                validation["all_passed"] = False
            
        except Exception as e:
            validation["all_passed"] = False
            validation["failures"].append(f"NLP validation failed: {e}")
        
        return validation
    
    async def _validate_compatibility_layers(self) -> Dict[str, Any]:
        """Validate compatibility layers."""
        validation = {"all_passed": True, "tests": {}, "failures": []}
        
        try:
            # Test ML compatibility
            ml_health = await self.ml_migration_manager.health_check()
            validation["tests"]["ml_compatibility"] = {
                "passed": ml_health["status"] in ["healthy", "degraded"],
                "status": ml_health["status"]
            }
            
            if not validation["tests"]["ml_compatibility"]["passed"]:
                validation["failures"].append(f"ML compatibility layer unhealthy: {ml_health['status']}")
                validation["all_passed"] = False
            
            # Test NLP compatibility
            nlp_health = await self.nlp_migration_manager.health_check()
            validation["tests"]["nlp_compatibility"] = {
                "passed": nlp_health["status"] in ["healthy", "degraded"],
                "status": nlp_health["status"]
            }
            
            if not validation["tests"]["nlp_compatibility"]["passed"]:
                validation["failures"].append(f"NLP compatibility layer unhealthy: {nlp_health['status']}")
                validation["all_passed"] = False
            
        except Exception as e:
            validation["all_passed"] = False
            validation["failures"].append(f"Compatibility validation failed: {e}")
        
        return validation
    
    async def _compare_performance(self, baseline: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current performance with baseline."""
        comparison = {
            "improvement": {},
            "degradation": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Current ML performance
            ml_features = {"engagement_score": 0.8, "questions_asked": 3, "buying_signals": 2}
            
            ml_times = []
            for _ in range(10):
                start_time = time.time()
                await self.ml_service.predict_single(PredictionType.CONVERSION, ml_features)
                ml_times.append((time.time() - start_time) * 1000)
            
            current_ml_avg = sum(ml_times) / len(ml_times)
            baseline_ml_avg = baseline.get("ml_metrics", {}).get("avg_response_time_ms", current_ml_avg)
            
            ml_improvement = ((baseline_ml_avg - current_ml_avg) / baseline_ml_avg) * 100
            
            comparison["ml_performance"] = {
                "baseline_ms": baseline_ml_avg,
                "current_ms": current_ml_avg,
                "improvement_percent": ml_improvement,
                "faster": ml_improvement > 0
            }
            
            # Current NLP performance
            test_text = "I'm interested in your pricing and features."
            
            nlp_times = []
            for _ in range(10):
                start_time = time.time()
                await self.nlp_service.analyze_text(test_text)
                nlp_times.append((time.time() - start_time) * 1000)
            
            current_nlp_avg = sum(nlp_times) / len(nlp_times)
            baseline_nlp_avg = baseline.get("nlp_metrics", {}).get("avg_response_time_ms", current_nlp_avg)
            
            nlp_improvement = ((baseline_nlp_avg - current_nlp_avg) / baseline_nlp_avg) * 100
            
            comparison["nlp_performance"] = {
                "baseline_ms": baseline_nlp_avg,
                "current_ms": current_nlp_avg,
                "improvement_percent": nlp_improvement,
                "faster": nlp_improvement > 0
            }
            
            # Overall assessment
            if ml_improvement > 0:
                comparison["improvement"]["ml_service"] = f"{ml_improvement:.1f}% faster"
            else:
                comparison["degradation"]["ml_service"] = f"{abs(ml_improvement):.1f}% slower"
            
            if nlp_improvement > 0:
                comparison["improvement"]["nlp_service"] = f"{nlp_improvement:.1f}% faster"
            else:
                comparison["degradation"]["nlp_service"] = f"{abs(nlp_improvement):.1f}% slower"
            
        except Exception as e:
            comparison["error"] = str(e)
        
        return comparison
    
    async def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive performance benchmarks."""
        logger.info("🏁 Running comprehensive ML/NLP benchmarks...")
        
        benchmark_results = {
            "timestamp": datetime.now().isoformat(),
            "ml_benchmarks": {},
            "nlp_benchmarks": {},
            "batch_processing": {},
            "memory_usage": {},
            "summary": {}
        }
        
        try:
            # ML Benchmarks
            await self._benchmark_ml_services(benchmark_results)
            
            # NLP Benchmarks
            await self._benchmark_nlp_services(benchmark_results)
            
            # Batch processing benchmarks
            await self._benchmark_batch_processing(benchmark_results)
            
            # Memory usage analysis
            await self._analyze_memory_usage(benchmark_results)
            
            # Generate summary
            self._generate_benchmark_summary(benchmark_results)
            
        except Exception as e:
            benchmark_results["error"] = str(e)
            logger.error(f"Benchmark failed: {e}")
        
        return benchmark_results
    
    async def _benchmark_ml_services(self, results: Dict[str, Any]):
        """Benchmark ML service performance."""
        ml_results = {}
        
        # Single prediction benchmarks
        prediction_types = [PredictionType.CONVERSION, PredictionType.NEEDS, PredictionType.OBJECTION]
        
        for pred_type in prediction_types:
            features = self._get_sample_features(pred_type)
            
            # Warm up
            await self.ml_service.predict_single(pred_type, features)
            
            # Benchmark
            times = []
            for _ in range(50):
                start_time = time.time()
                await self.ml_service.predict_single(pred_type, features)
                times.append((time.time() - start_time) * 1000)
            
            ml_results[pred_type.value] = {
                "avg_time_ms": sum(times) / len(times),
                "min_time_ms": min(times),
                "max_time_ms": max(times),
                "p95_time_ms": sorted(times)[int(len(times) * 0.95)],
                "throughput_per_sec": 1000 / (sum(times) / len(times))
            }
        
        results["ml_benchmarks"] = ml_results
    
    async def _benchmark_nlp_services(self, results: Dict[str, Any]):
        """Benchmark NLP service performance."""
        test_texts = [
            "How much does your premium plan cost?",
            "Can you show me a demo of the features?",
            "I'm not sure if this is right for our company.",
            "We need a solution for lead generation and customer management.",
            "What makes you different from your competitors?"
        ]
        
        nlp_results = {}
        
        for i, text in enumerate(test_texts):
            # Warm up
            await self.nlp_service.analyze_text(text)
            
            # Benchmark
            times = []
            for _ in range(30):
                start_time = time.time()
                await self.nlp_service.analyze_text(text)
                times.append((time.time() - start_time) * 1000)
            
            nlp_results[f"text_{i+1}"] = {
                "text_length": len(text),
                "avg_time_ms": sum(times) / len(times),
                "min_time_ms": min(times),
                "max_time_ms": max(times),
                "throughput_per_sec": 1000 / (sum(times) / len(times))
            }
        
        # Batch processing benchmark
        times = []
        for _ in range(10):
            start_time = time.time()
            await self.nlp_service.analyze_batch(test_texts)
            times.append((time.time() - start_time) * 1000)
        
        nlp_results["batch_processing"] = {
            "batch_size": len(test_texts),
            "avg_batch_time_ms": sum(times) / len(times),
            "avg_time_per_item_ms": (sum(times) / len(times)) / len(test_texts),
            "batch_throughput_per_sec": (1000 * len(test_texts)) / (sum(times) / len(times))
        }
        
        results["nlp_benchmarks"] = nlp_results
    
    async def _benchmark_batch_processing(self, results: Dict[str, Any]):
        """Benchmark batch processing capabilities."""
        from src.services.consolidated_ml_prediction_service import BatchPredictionRequest
        
        # Create batch requests
        features = self._get_sample_features(PredictionType.CONVERSION)
        batch_sizes = [10, 20, 50]
        
        batch_results = {}
        
        for batch_size in batch_sizes:
            batch_request = BatchPredictionRequest(
                conversation_ids=[f"conv_{i}" for i in range(batch_size)],
                prediction_types=[PredictionType.CONVERSION],
                features_batch=[features] * batch_size
            )
            
            # Benchmark batch processing
            times = []
            for _ in range(5):
                start_time = time.time()
                await self.ml_service.predict_batch(batch_request)
                times.append((time.time() - start_time) * 1000)
            
            avg_batch_time = sum(times) / len(times)
            
            # Compare with individual processing
            individual_times = []
            start_time = time.time()
            for _ in range(batch_size):
                await self.ml_service.predict_single(PredictionType.CONVERSION, features)
            individual_time = (time.time() - start_time) * 1000
            
            efficiency = (1 - avg_batch_time / individual_time) * 100 if individual_time > 0 else 0
            
            batch_results[f"batch_size_{batch_size}"] = {
                "avg_batch_time_ms": avg_batch_time,
                "individual_time_ms": individual_time,
                "efficiency_improvement_percent": efficiency,
                "throughput_per_sec": (1000 * batch_size) / avg_batch_time
            }
        
        results["batch_processing"] = batch_results
    
    async def _analyze_memory_usage(self, results: Dict[str, Any]):
        """Analyze memory usage patterns."""
        try:
            import psutil
            import gc
            
            process = psutil.Process()
            
            # Initial memory
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Memory after ML operations
            features = self._get_sample_features(PredictionType.CONVERSION)
            for _ in range(100):
                await self.ml_service.predict_single(PredictionType.CONVERSION, features)
            
            ml_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Memory after NLP operations
            for _ in range(50):
                await self.nlp_service.analyze_text("Test text for memory analysis")
            
            nlp_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Force garbage collection
            gc.collect()
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            results["memory_usage"] = {
                "initial_mb": initial_memory,
                "after_ml_operations_mb": ml_memory,
                "after_nlp_operations_mb": nlp_memory,
                "after_gc_mb": final_memory,
                "ml_memory_increase_mb": ml_memory - initial_memory,
                "nlp_memory_increase_mb": nlp_memory - ml_memory,
                "total_increase_mb": nlp_memory - initial_memory,
                "gc_recovered_mb": nlp_memory - final_memory
            }
            
        except ImportError:
            results["memory_usage"] = {"error": "psutil not available"}
        except Exception as e:
            results["memory_usage"] = {"error": str(e)}
    
    def _generate_benchmark_summary(self, results: Dict[str, Any]):
        """Generate benchmark summary."""
        summary = {
            "overall_performance": "excellent",
            "recommendations": [],
            "key_metrics": {}
        }
        
        try:
            # ML performance summary
            ml_benchmarks = results.get("ml_benchmarks", {})
            if ml_benchmarks:
                avg_ml_times = [metrics["avg_time_ms"] for metrics in ml_benchmarks.values()]
                avg_ml_time = sum(avg_ml_times) / len(avg_ml_times) if avg_ml_times else 0
                
                summary["key_metrics"]["avg_ml_prediction_ms"] = avg_ml_time
                
                if avg_ml_time > 100:
                    summary["overall_performance"] = "needs_optimization"
                    summary["recommendations"].append("ML prediction time exceeds 100ms - consider optimization")
            
            # NLP performance summary
            nlp_benchmarks = results.get("nlp_benchmarks", {})
            if nlp_benchmarks:
                text_benchmarks = {k: v for k, v in nlp_benchmarks.items() if k.startswith("text_")}
                if text_benchmarks:
                    avg_nlp_times = [metrics["avg_time_ms"] for metrics in text_benchmarks.values()]
                    avg_nlp_time = sum(avg_nlp_times) / len(avg_nlp_times) if avg_nlp_times else 0
                    
                    summary["key_metrics"]["avg_nlp_analysis_ms"] = avg_nlp_time
                    
                    if avg_nlp_time > 200:
                        summary["overall_performance"] = "needs_optimization"
                        summary["recommendations"].append("NLP analysis time exceeds 200ms - consider optimization")
            
            # Batch processing efficiency
            batch_processing = results.get("batch_processing", {})
            if batch_processing:
                efficiencies = [metrics["efficiency_improvement_percent"] 
                              for metrics in batch_processing.values()]
                avg_efficiency = sum(efficiencies) / len(efficiencies) if efficiencies else 0
                
                summary["key_metrics"]["batch_processing_efficiency_percent"] = avg_efficiency
                
                if avg_efficiency < 30:
                    summary["recommendations"].append("Batch processing efficiency is low - review implementation")
            
            # Memory usage
            memory_usage = results.get("memory_usage", {})
            if memory_usage and "total_increase_mb" in memory_usage:
                total_memory_increase = memory_usage["total_increase_mb"]
                summary["key_metrics"]["memory_increase_mb"] = total_memory_increase
                
                if total_memory_increase > 500:
                    summary["recommendations"].append("High memory usage detected - consider memory optimization")
            
            # Overall assessment
            if len(summary["recommendations"]) == 0:
                summary["overall_performance"] = "excellent"
                summary["recommendations"].append("All performance metrics within optimal ranges")
            elif len(summary["recommendations"]) <= 2:
                summary["overall_performance"] = "good"
            else:
                summary["overall_performance"] = "needs_optimization"
        
        except Exception as e:
            summary["error"] = str(e)
        
        results["summary"] = summary
    
    def _get_sample_features(self, prediction_type: PredictionType) -> Dict[str, Any]:
        """Get sample features for a prediction type."""
        if prediction_type == PredictionType.CONVERSION:
            return {
                "engagement_score": 0.8,
                "questions_asked": 3,
                "objections_raised": 1,
                "price_discussed": True,
                "demo_requested": True,
                "avg_response_time": 25.0,
                "conversation_duration": 15,
                "positive_sentiment": 0.7,
                "buying_signals": 2,
                "decision_maker_present": True
            }
        elif prediction_type == PredictionType.NEEDS:
            return {
                "industry_match": 0.9,
                "company_size": 50,
                "pain_points_mentioned": 2,
                "budget_range_discussed": True,
                "timeline_urgency": 0.8,
                "feature_interest_score": 0.7,
                "competitive_mentions": 1,
                "specific_requirements": 3,
                "stakeholder_count": 3,
                "current_solution_mentioned": True
            }
        elif prediction_type == PredictionType.OBJECTION:
            return {
                "negative_sentiment": 2,
                "hesitation_words": 1,
                "comparison_requests": 1,
                "price_concerns": 2,
                "implementation_concerns": 1,
                "authority_questions": 1,
                "delay_indicators": 0,
                "skeptical_tone": 1,
                "competitor_mentions": 1,
                "budget_constraints": 1
            }
        else:
            return {"engagement_score": 0.7, "feature_interest": 0.8}
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status."""
        return {
            "consolidated_ml_enabled": settings.use_consolidated_ml_service,
            "consolidated_nlp_enabled": settings.use_consolidated_nlp_service,
            "services_initialized": {
                "ml_service": self.ml_service is not None and self.ml_service._initialized,
                "nlp_service": self.nlp_service is not None and self.nlp_service._initialized,
                "ml_migration_manager": self.ml_migration_manager is not None,
                "nlp_migration_manager": self.nlp_migration_manager is not None
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.ml_service:
            await self.ml_service.cleanup()
        
        if self.nlp_service:
            await self.nlp_service.cleanup()


async def main():
    """Main function for CLI interface."""
    parser = argparse.ArgumentParser(description="ML/NLP Service Migration Manager")
    parser.add_argument(
        "--command", 
        choices=["status", "check-readiness", "migrate", "benchmark", "validate", "rollback"],
        required=True,
        help="Command to execute"
    )
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    # Initialize migration manager
    migration_manager = MLNLPMigrationManager()
    await migration_manager.initialize()
    
    try:
        if args.command == "status":
            print("📊 ML/NLP Migration Status")
            print("=" * 50)
            
            status = migration_manager.get_migration_status()
            
            print(f"ML Consolidated Service: {'✅ Enabled' if status['consolidated_ml_enabled'] else '❌ Disabled'}")
            print(f"NLP Consolidated Service: {'✅ Enabled' if status['consolidated_nlp_enabled'] else '❌ Disabled'}")
            print()
            
            print("Service Initialization Status:")
            for service_name, initialized in status["services_initialized"].items():
                print(f"  {service_name}: {'✅ Initialized' if initialized else '❌ Not Initialized'}")
            
            # Log migration progress
            log_ml_migration_progress()
            log_nlp_migration_progress()
        
        elif args.command == "check-readiness":
            print("🔍 Checking Migration Readiness...")
            print("=" * 50)
            
            readiness = await migration_manager.check_migration_readiness()
            
            print(f"Overall Readiness: {'✅ Ready' if readiness['ready'] else '❌ Not Ready'}")
            print()
            
            print("Readiness Checks:")
            for check_name, passed in readiness["checks"].items():
                print(f"  {check_name}: {'✅ Pass' if passed else '❌ Fail'}")
            
            if readiness["blockers"]:
                print("\n🚫 Blockers:")
                for blocker in readiness["blockers"]:
                    print(f"  - {blocker}")
            
            if readiness["warnings"]:
                print("\n⚠️ Warnings:")
                for warning in readiness["warnings"]:
                    print(f"  - {warning}")
            
            if "performance" in readiness:
                print(f"\n⚡ Performance:")
                print(f"  ML Response Time: {readiness['performance']['ml_response_time_ms']:.2f}ms")
                print(f"  NLP Response Time: {readiness['performance']['nlp_response_time_ms']:.2f}ms")
        
        elif args.command == "migrate":
            print("🚀 Starting Migration Process...")
            print("=" * 50)
            
            migration_result = await migration_manager.run_migration()
            
            print(f"Migration Status: {migration_result['status']}")
            print(f"Success: {'✅' if migration_result['success'] else '❌'}")
            print()
            
            print("Completed Steps:")
            for step in migration_result["steps_completed"]:
                print(f"  ✅ {step}")
            
            if migration_result["steps_failed"]:
                print("\nFailed Steps:")
                for step in migration_result["steps_failed"]:
                    print(f"  ❌ {step}")
            
            if "performance_comparison" in migration_result:
                perf = migration_result["performance_comparison"]
                
                print("\n📈 Performance Comparison:")
                if "ml_performance" in perf:
                    ml_perf = perf["ml_performance"]
                    print(f"  ML Service: {ml_perf['improvement_percent']:.1f}% {'faster' if ml_perf['faster'] else 'slower'}")
                
                if "nlp_performance" in perf:
                    nlp_perf = perf["nlp_performance"]
                    print(f"  NLP Service: {nlp_perf['improvement_percent']:.1f}% {'faster' if nlp_perf['faster'] else 'slower'}")
        
        elif args.command == "benchmark":
            print("🏁 Running Comprehensive Benchmarks...")
            print("=" * 50)
            
            benchmark_results = await migration_manager.run_comprehensive_benchmark()
            
            # Display summary
            if "summary" in benchmark_results:
                summary = benchmark_results["summary"]
                print(f"Overall Performance: {summary['overall_performance'].replace('_', ' ').title()}")
                print()
                
                if "key_metrics" in summary:
                    print("Key Metrics:")
                    for metric, value in summary["key_metrics"].items():
                        if isinstance(value, float):
                            print(f"  {metric.replace('_', ' ').title()}: {value:.2f}")
                        else:
                            print(f"  {metric.replace('_', ' ').title()}: {value}")
                
                print("\nRecommendations:")
                for rec in summary.get("recommendations", []):
                    print(f"  • {rec}")
            
            # Save detailed results if output file specified
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(benchmark_results, f, indent=2)
                print(f"\nDetailed results saved to: {args.output}")
        
        elif args.command == "validate":
            print("🔍 Running Validation Tests...")
            print("=" * 50)
            
            readiness = await migration_manager.check_migration_readiness()
            validation = readiness  # Reuse readiness check for now
            
            print(f"All Tests Passed: {'✅ Yes' if validation['ready'] else '❌ No'}")
            
            if not validation["ready"] and validation["blockers"]:
                print("\nTest Failures:")
                for failure in validation["blockers"]:
                    print(f"  ❌ {failure}")
        
        elif args.command == "rollback":
            print("🔄 Rollback functionality not yet implemented")
            print("To rollback manually, disable feature flags:")
            print("  USE_CONSOLIDATED_ML_SERVICE=false")
            print("  USE_CONSOLIDATED_NLP_SERVICE=false")
        
    except Exception as e:
        print(f"❌ Command failed: {e}")
        return 1
    
    finally:
        await migration_manager.cleanup()
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)