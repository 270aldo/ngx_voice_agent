"""
Empathy Feature Flags Configuration for NGX Voice Sales Agent.

This module manages feature flags for the empathy services consolidation,
allowing for controlled rollout and A/B testing of the new consolidated service.

Features:
- Gradual rollout control
- A/B testing configuration
- Performance monitoring flags
- Emergency rollback capabilities
- Environment-specific settings
"""

import os
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RolloutStage(str, Enum):
    """Rollout stages for empathy consolidation."""
    DISABLED = "disabled"           # Legacy services only
    TESTING = "testing"            # Internal testing only
    CANARY = "canary"              # 5% of traffic
    BETA = "beta"                  # 25% of traffic
    GRADUAL = "gradual"            # 50% of traffic
    FULL = "full"                  # 100% of traffic
    FORCE_LEGACY = "force_legacy"  # Force legacy for debugging


class EmpathyFeature(str, Enum):
    """Individual empathy features that can be toggled."""
    CONSOLIDATED_SERVICE = "consolidated_service"
    ADVANCED_SENTIMENT = "advanced_sentiment"
    PERSONALITY_DETECTION = "personality_detection"
    PATTERN_RECOGNITION = "pattern_recognition"
    ULTRA_EMPATHY_GREETINGS = "ultra_empathy_greetings"
    PRICE_OBJECTION_HANDLER = "price_objection_handler"
    SENTIMENT_ALERTS = "sentiment_alerts"
    EMPATHY_CACHING = "empathy_caching"
    LEARNING_SYSTEM = "learning_system"
    CULTURAL_ADAPTATION = "cultural_adaptation"


@dataclass
class FeatureFlagConfig:
    """Configuration for a single feature flag."""
    enabled: bool = False
    rollout_percentage: float = 0.0  # 0-100
    environments: List[str] = field(default_factory=lambda: ["development"])
    user_groups: List[str] = field(default_factory=list)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    emergency_disable: bool = False
    description: str = ""


@dataclass
class EmpathyMetrics:
    """Metrics tracking for empathy features."""
    response_time_ms: float = 0.0
    empathy_score: float = 0.0
    error_rate: float = 0.0
    user_satisfaction: float = 0.0
    conversion_rate: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


class EmpathyFeatureFlags:
    """
    Feature flags manager for empathy services consolidation.
    
    Features:
    - Environment-aware configuration
    - Gradual rollout support
    - A/B testing capabilities
    - Performance monitoring
    - Emergency controls
    """
    
    def __init__(self):
        """Initialize feature flags with default configuration."""
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.rollout_stage = RolloutStage(os.getenv("EMPATHY_ROLLOUT_STAGE", "testing"))
        
        # Initialize feature flags
        self.flags = self._initialize_feature_flags()
        
        # Performance tracking
        self.metrics = {}
        self.a_b_test_groups = {}
        
        # Load configuration from environment
        self._load_environment_config()
        
        logger.info(f"EmpathyFeatureFlags initialized for {self.environment} environment")
        logger.info(f"Current rollout stage: {self.rollout_stage}")
    
    def _initialize_feature_flags(self) -> Dict[EmpathyFeature, FeatureFlagConfig]:
        """Initialize feature flags with default configurations."""
        return {
            EmpathyFeature.CONSOLIDATED_SERVICE: FeatureFlagConfig(
                enabled=True,
                rollout_percentage=100.0 if self.rollout_stage == RolloutStage.FULL else 0.0,
                environments=["development", "testing", "staging", "production"],
                description="Main consolidated empathy service"
            ),
            
            EmpathyFeature.ADVANCED_SENTIMENT: FeatureFlagConfig(
                enabled=True,
                rollout_percentage=90.0,
                environments=["development", "testing", "staging", "production"],
                dependencies=["consolidated_service"],
                description="Advanced sentiment analysis with emotion detection"
            ),
            
            EmpathyFeature.PERSONALITY_DETECTION: FeatureFlagConfig(
                enabled=True,
                rollout_percentage=75.0,
                environments=["development", "testing", "staging"],
                dependencies=["consolidated_service"],
                description="Communication style and personality detection"
            ),
            
            EmpathyFeature.PATTERN_RECOGNITION: FeatureFlagConfig(
                enabled=True,
                rollout_percentage=80.0,
                environments=["development", "testing", "staging"],
                dependencies=["consolidated_service"],
                description="Conversation pattern recognition and analysis"
            ),
            
            EmpathyFeature.ULTRA_EMPATHY_GREETINGS: FeatureFlagConfig(
                enabled=True,
                rollout_percentage=100.0,
                environments=["development", "testing", "staging", "production"],
                dependencies=["consolidated_service"],
                description="Ultra-empathetic greeting generation"
            ),
            
            EmpathyFeature.PRICE_OBJECTION_HANDLER: FeatureFlagConfig(
                enabled=True,
                rollout_percentage=100.0,
                environments=["development", "testing", "staging", "production"],
                dependencies=["consolidated_service"],
                description="Empathetic price objection handling"
            ),
            
            EmpathyFeature.SENTIMENT_ALERTS: FeatureFlagConfig(
                enabled=True,
                rollout_percentage=85.0,
                environments=["development", "testing", "staging", "production"],
                dependencies=["consolidated_service", "advanced_sentiment"],
                description="Real-time sentiment monitoring and alerts"
            ),
            
            EmpathyFeature.EMPATHY_CACHING: FeatureFlagConfig(
                enabled=True,
                rollout_percentage=100.0,
                environments=["staging", "production"],
                dependencies=["consolidated_service"],
                description="Empathy response caching for performance"
            ),
            
            EmpathyFeature.LEARNING_SYSTEM: FeatureFlagConfig(
                enabled=False,  # Experimental
                rollout_percentage=10.0,
                environments=["development", "testing"],
                dependencies=["consolidated_service"],
                description="Empathy learning and adaptation system"
            ),
            
            EmpathyFeature.CULTURAL_ADAPTATION: FeatureFlagConfig(
                enabled=True,
                rollout_percentage=70.0,
                environments=["development", "testing", "staging"],
                dependencies=["consolidated_service"],
                description="Cultural context adaptation for empathy"
            )
        }
    
    def _load_environment_config(self):
        """Load configuration from environment variables."""
        # Override rollout percentages from environment
        for feature in EmpathyFeature:
            env_var = f"EMPATHY_{feature.value.upper()}_ROLLOUT"
            if env_var in os.environ:
                try:
                    percentage = float(os.environ[env_var])
                    self.flags[feature].rollout_percentage = min(100.0, max(0.0, percentage))
                    logger.info(f"Set {feature.value} rollout to {percentage}% from environment")
                except ValueError:
                    logger.warning(f"Invalid rollout percentage for {feature.value}: {os.environ[env_var]}")
        
        # Emergency disable flags
        if os.getenv("EMPATHY_EMERGENCY_DISABLE", "false").lower() == "true":
            for flag in self.flags.values():
                flag.emergency_disable = True
            logger.warning("EMERGENCY DISABLE activated for all empathy features")
    
    def is_enabled(self, feature: EmpathyFeature, user_id: Optional[str] = None) -> bool:
        """
        Check if a feature is enabled for the current environment and user.
        
        Args:
            feature: Feature to check
            user_id: Optional user ID for user-specific flags
            
        Returns:
            True if feature is enabled, False otherwise
        """
        config = self.flags.get(feature)
        if not config:
            return False
        
        # Emergency disable check
        if config.emergency_disable:
            logger.warning(f"Feature {feature.value} emergency disabled")
            return False
        
        # Environment check
        if self.environment not in config.environments:
            return False
        
        # Base enabled check
        if not config.enabled:
            return False
        
        # Dependency check
        for dep in config.dependencies:
            dep_feature = EmpathyFeature(dep)
            if not self.is_enabled(dep_feature, user_id):
                logger.debug(f"Feature {feature.value} disabled due to dependency {dep}")
                return False
        
        # Date range check
        now = datetime.now()
        if config.start_date and now < config.start_date:
            return False
        if config.end_date and now > config.end_date:
            return False
        
        # Rollout percentage check
        if config.rollout_percentage >= 100.0:
            return True
        
        # User-based rollout
        if user_id:
            # Consistent hash-based rollout
            hash_value = hash(f"{feature.value}:{user_id}") % 100
            return hash_value < config.rollout_percentage
        
        # Environment-based rollout
        if self.environment == "production":
            # More conservative rollout in production
            return config.rollout_percentage >= 95.0
        else:
            # Aggressive rollout in non-production
            return config.rollout_percentage >= 50.0
    
    def should_use_consolidated_service(self, user_id: Optional[str] = None) -> bool:
        """
        Determine if consolidated service should be used instead of legacy services.
        
        Args:
            user_id: Optional user ID for consistent routing
            
        Returns:
            True if consolidated service should be used
        """
        # Check overall rollout stage
        if self.rollout_stage == RolloutStage.DISABLED:
            return False
        elif self.rollout_stage == RolloutStage.FORCE_LEGACY:
            return False
        elif self.rollout_stage == RolloutStage.FULL:
            return self.is_enabled(EmpathyFeature.CONSOLIDATED_SERVICE, user_id)
        
        # Progressive rollout based on stage
        rollout_percentages = {
            RolloutStage.TESTING: 0.0,      # Internal only
            RolloutStage.CANARY: 5.0,       # 5% of users
            RolloutStage.BETA: 25.0,        # 25% of users
            RolloutStage.GRADUAL: 50.0,     # 50% of users
            RolloutStage.FULL: 100.0        # All users
        }
        
        target_percentage = rollout_percentages.get(self.rollout_stage, 0.0)
        
        # Consistent user routing
        if user_id:
            hash_value = hash(f"consolidated_service:{user_id}") % 100
            return hash_value < target_percentage
        
        # Environment-based routing
        return target_percentage >= 50.0 if self.environment != "production" else target_percentage >= 90.0
    
    def get_feature_config(self, feature: EmpathyFeature) -> Optional[FeatureFlagConfig]:
        """Get configuration for a specific feature."""
        return self.flags.get(feature)
    
    def update_feature_flag(
        self, 
        feature: EmpathyFeature, 
        enabled: Optional[bool] = None,
        rollout_percentage: Optional[float] = None,
        emergency_disable: Optional[bool] = None
    ):
        """
        Update feature flag configuration.
        
        Args:
            feature: Feature to update
            enabled: Enable/disable the feature
            rollout_percentage: New rollout percentage (0-100)
            emergency_disable: Emergency disable flag
        """
        config = self.flags.get(feature)
        if not config:
            logger.error(f"Feature {feature.value} not found")
            return
        
        if enabled is not None:
            config.enabled = enabled
            logger.info(f"Feature {feature.value} enabled set to {enabled}")
        
        if rollout_percentage is not None:
            config.rollout_percentage = min(100.0, max(0.0, rollout_percentage))
            logger.info(f"Feature {feature.value} rollout set to {config.rollout_percentage}%")
        
        if emergency_disable is not None:
            config.emergency_disable = emergency_disable
            logger.warning(f"Feature {feature.value} emergency disable set to {emergency_disable}")
    
    def emergency_disable_all(self):
        """Emergency disable all empathy features."""
        for config in self.flags.values():
            config.emergency_disable = True
        logger.critical("EMERGENCY: All empathy features disabled")
    
    def track_performance(self, feature: EmpathyFeature, metrics: EmpathyMetrics):
        """
        Track performance metrics for a feature.
        
        Args:
            feature: Feature being tracked
            metrics: Performance metrics
        """
        self.metrics[feature] = metrics
        
        # Auto-disable if performance is poor
        if metrics.error_rate > 10.0:  # 10% error rate
            logger.warning(f"High error rate detected for {feature.value}: {metrics.error_rate}%")
            self.update_feature_flag(feature, emergency_disable=True)
        
        if metrics.response_time_ms > 5000:  # 5 second response time
            logger.warning(f"High response time detected for {feature.value}: {metrics.response_time_ms}ms")
    
    def setup_a_b_test(
        self, 
        test_name: str, 
        feature: EmpathyFeature, 
        control_percentage: float = 50.0,
        variant_percentage: float = 50.0
    ):
        """
        Setup A/B test for a feature.
        
        Args:
            test_name: Name of the A/B test
            feature: Feature being tested
            control_percentage: Percentage for control group
            variant_percentage: Percentage for variant group
        """
        self.a_b_test_groups[test_name] = {
            "feature": feature,
            "control_percentage": control_percentage,
            "variant_percentage": variant_percentage,
            "start_time": datetime.now(),
            "metrics": {"control": {}, "variant": {}}
        }
        
        logger.info(f"A/B test '{test_name}' setup for {feature.value}")
    
    def get_a_b_test_group(self, test_name: str, user_id: str) -> str:
        """
        Get A/B test group for a user.
        
        Args:
            test_name: Name of the A/B test
            user_id: User identifier
            
        Returns:
            'control' or 'variant'
        """
        test_config = self.a_b_test_groups.get(test_name)
        if not test_config:
            return "control"
        
        hash_value = hash(f"{test_name}:{user_id}") % 100
        if hash_value < test_config["control_percentage"]:
            return "control"
        else:
            return "variant"
    
    def get_feature_status_report(self) -> Dict[str, Any]:
        """Get comprehensive status report of all features."""
        report = {
            "environment": self.environment,
            "rollout_stage": self.rollout_stage.value,
            "timestamp": datetime.now().isoformat(),
            "features": {},
            "metrics": {},
            "a_b_tests": len(self.a_b_test_groups)
        }
        
        for feature, config in self.flags.items():
            report["features"][feature.value] = {
                "enabled": config.enabled,
                "rollout_percentage": config.rollout_percentage,
                "environments": config.environments,
                "dependencies": config.dependencies,
                "emergency_disable": config.emergency_disable,
                "description": config.description
            }
        
        for feature, metrics in self.metrics.items():
            report["metrics"][feature.value] = {
                "response_time_ms": metrics.response_time_ms,
                "empathy_score": metrics.empathy_score,
                "error_rate": metrics.error_rate,
                "user_satisfaction": metrics.user_satisfaction,
                "last_updated": metrics.last_updated.isoformat()
            }
        
        return report
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export current configuration for backup or replication."""
        return {
            "environment": self.environment,
            "rollout_stage": self.rollout_stage.value,
            "flags": {
                feature.value: {
                    "enabled": config.enabled,
                    "rollout_percentage": config.rollout_percentage,
                    "environments": config.environments,
                    "user_groups": config.user_groups,
                    "dependencies": config.dependencies,
                    "emergency_disable": config.emergency_disable,
                    "description": config.description
                }
                for feature, config in self.flags.items()
            },
            "export_timestamp": datetime.now().isoformat()
        }


# Global feature flags instance
_empathy_flags = None

def get_empathy_flags() -> EmpathyFeatureFlags:
    """Get global empathy feature flags instance."""
    global _empathy_flags
    if _empathy_flags is None:
        _empathy_flags = EmpathyFeatureFlags()
    return _empathy_flags

# Convenience functions for common checks
def use_consolidated_service(user_id: Optional[str] = None) -> bool:
    """Check if consolidated service should be used."""
    return get_empathy_flags().should_use_consolidated_service(user_id)

def is_feature_enabled(feature: EmpathyFeature, user_id: Optional[str] = None) -> bool:
    """Check if a specific feature is enabled."""
    return get_empathy_flags().is_enabled(feature, user_id)

def track_empathy_performance(feature: EmpathyFeature, metrics: EmpathyMetrics):
    """Track performance metrics for empathy feature."""
    get_empathy_flags().track_performance(feature, metrics)