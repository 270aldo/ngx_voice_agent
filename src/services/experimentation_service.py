"""
Experimentation Service - Consolidated A/B testing and optimization functionality.

This service consolidates functionality from:
- ab_testing_framework.py
- ab_testing_manager.py
- prompt_optimizer_service.py

Provides:
- A/B testing framework with multi-armed bandit algorithms
- Experiment management and statistical analysis
- Prompt optimization and testing
- Conversion rate optimization
- Automated winner selection and deployment
- Statistical significance testing
"""

import logging
import asyncio
import json
import math
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import random
from collections import defaultdict

from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)


class ExperimentStatus(str, Enum):
    """Experiment status types."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class VariantType(str, Enum):
    """Types of variants that can be tested."""
    GREETING = "greeting"
    EMPATHY_RESPONSE = "empathy_response"
    PRICING_PRESENTATION = "pricing_presentation"
    CLOSING_TECHNIQUE = "closing_technique"
    OBJECTION_HANDLING = "objection_handling"
    DEMO_INVITATION = "demo_invitation"
    FOLLOW_UP = "follow_up"
    PROMPT_TEMPLATE = "prompt_template"


class OptimizationGoal(str, Enum):
    """Optimization goals for experiments."""
    CONVERSION_RATE = "conversion_rate"
    ENGAGEMENT_RATE = "engagement_rate"
    RESPONSE_TIME = "response_time"
    CUSTOMER_SATISFACTION = "customer_satisfaction"
    DEMO_BOOKING_RATE = "demo_booking_rate"
    OBJECTION_RESOLUTION = "objection_resolution"


@dataclass
class Variant:
    """Experiment variant configuration."""
    id: str
    name: str
    content: str
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentResult:
    """Results for a single variant."""
    variant_id: str
    impressions: int = 0
    conversions: int = 0
    total_value: float = 0.0
    conversion_rate: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    statistical_significance: float = 0.0


@dataclass 
class Experiment:
    """A/B test experiment configuration."""
    id: str
    name: str
    description: str
    variant_type: VariantType
    optimization_goal: OptimizationGoal
    variants: List[Variant]
    traffic_allocation: float = 1.0
    min_sample_size: int = 100
    max_duration_days: int = 30
    significance_threshold: float = 0.95
    status: ExperimentStatus = ExperimentStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    winner_variant_id: Optional[str] = None
    results: List[ExperimentResult] = field(default_factory=list)


@dataclass
class BanditArm:
    """Multi-armed bandit arm for dynamic optimization."""
    variant_id: str
    rewards: List[float] = field(default_factory=list)
    pulls: int = 0
    total_reward: float = 0.0
    average_reward: float = 0.0
    confidence_bound: float = 0.0


class ExperimentationService:
    """
    Unified experimentation service for A/B testing and optimization.
    
    Features:
    - Multi-armed bandit algorithms for dynamic optimization
    - Classical A/B testing with statistical significance
    - Prompt optimization and testing
    - Conversion rate optimization
    - Automated experiment management
    - Real-time performance monitoring
    """
    
    def __init__(self):
        """Initialize experimentation service."""
        self.experiments: Dict[str, Experiment] = {}
        self.active_experiments: Dict[VariantType, str] = {}  # variant_type -> experiment_id
        self.bandit_arms: Dict[str, List[BanditArm]] = {}  # experiment_id -> arms
        self.experiment_data: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Configuration
        self.epsilon = 0.1  # Exploration rate for epsilon-greedy
        self.confidence_level = 0.95
        self.min_confidence_interval = 0.8
        
        # Pre-defined experiment templates
        self.experiment_templates = self._initialize_experiment_templates()
        
        logger.info("ExperimentationService initialized")
    
    def _initialize_experiment_templates(self) -> Dict[VariantType, Dict[str, Any]]:
        """Initialize experiment templates for common scenarios."""
        return {
            VariantType.GREETING: {
                "name": "Greeting Optimization",
                "description": "Test different greeting approaches",
                "variants": [
                    {"id": "formal", "name": "Formal Greeting", "content": "Buenos días, soy el asistente de NGX. ¿En qué puedo ayudarle?"},
                    {"id": "casual", "name": "Casual Greeting", "content": "¡Hola! Soy tu asistente NGX. ¿Cómo te puedo ayudar hoy?"},
                    {"id": "enthusiastic", "name": "Enthusiastic Greeting", "content": "¡Hola! ¡Qué gusto conectar contigo! Soy tu asistente NGX y estoy súper emocionado de ayudarte."}
                ],
                "goal": OptimizationGoal.ENGAGEMENT_RATE,
                "min_sample_size": 50
            },
            VariantType.PRICING_PRESENTATION: {
                "name": "Pricing Approach Test",
                "description": "Test different ways to present pricing",
                "variants": [
                    {"id": "value_first", "name": "Value-First", "content": "Primero déjame mostrarte el increíble valor que obtienes..."},
                    {"id": "price_anchor", "name": "Price Anchoring", "content": "Nuestro plan premium cuesta $2,000, pero tenemos opciones más accesibles..."},
                    {"id": "roi_focus", "name": "ROI Focus", "content": "Con NGX verás un retorno de inversión del 400-800%..."}
                ],
                "goal": OptimizationGoal.CONVERSION_RATE,
                "min_sample_size": 100
            },
            VariantType.OBJECTION_HANDLING: {
                "name": "Objection Handling Optimization",
                "description": "Test different objection handling techniques",
                "variants": [
                    {"id": "empathetic", "name": "Empathetic Response", "content": "Entiendo perfectamente tu preocupación..."},
                    {"id": "logical", "name": "Logical Response", "content": "Déjame explicarte por qué esto no debería preocuparte..."},
                    {"id": "social_proof", "name": "Social Proof", "content": "Otros clientes tenían la misma preocupación y ahora están..."}
                ],
                "goal": OptimizationGoal.OBJECTION_RESOLUTION,
                "min_sample_size": 75
            }
        }
    
    async def create_experiment(
        self,
        name: str,
        description: str,
        variant_type: VariantType,
        variants: List[Dict[str, Any]],
        optimization_goal: OptimizationGoal = OptimizationGoal.CONVERSION_RATE,
        traffic_allocation: float = 1.0,
        min_sample_size: int = 100
    ) -> str:
        """
        Create a new A/B test experiment.
        
        Args:
            name: Experiment name
            description: Experiment description
            variant_type: Type of variants being tested
            variants: List of variant configurations
            optimization_goal: What metric to optimize for
            traffic_allocation: Percentage of traffic to include (0.0-1.0)
            min_sample_size: Minimum samples needed per variant
            
        Returns:
            Experiment ID
        """
        experiment_id = f"exp_{variant_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create variant objects
        variant_objects = []
        for i, variant_data in enumerate(variants):
            variant = Variant(
                id=variant_data.get("id", f"variant_{i}"),
                name=variant_data.get("name", f"Variant {i+1}"),
                content=variant_data["content"],
                weight=variant_data.get("weight", 1.0),
                metadata=variant_data.get("metadata", {})
            )
            variant_objects.append(variant)
        
        # Create experiment
        experiment = Experiment(
            id=experiment_id,
            name=name,
            description=description,
            variant_type=variant_type,
            optimization_goal=optimization_goal,
            variants=variant_objects,
            traffic_allocation=traffic_allocation,
            min_sample_size=min_sample_size
        )
        
        self.experiments[experiment_id] = experiment
        
        # Initialize bandit arms
        self.bandit_arms[experiment_id] = [
            BanditArm(variant_id=variant.id)
            for variant in variant_objects
        ]
        
        logger.info(f"Created experiment: {experiment_id} with {len(variants)} variants")
        return experiment_id
    
    async def create_experiment_from_template(
        self,
        variant_type: VariantType,
        custom_variants: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Create experiment from predefined template.
        
        Args:
            variant_type: Type of experiment template to use
            custom_variants: Optional custom variants to override template
            
        Returns:
            Experiment ID
        """
        template = self.experiment_templates.get(variant_type)
        if not template:
            raise ValueError(f"No template found for variant type: {variant_type}")
        
        variants = custom_variants or template["variants"]
        
        return await self.create_experiment(
            name=template["name"],
            description=template["description"],
            variant_type=variant_type,
            variants=variants,
            optimization_goal=template["goal"],
            min_sample_size=template["min_sample_size"]
        )
    
    async def start_experiment(self, experiment_id: str) -> bool:
        """
        Start running an experiment.
        
        Args:
            experiment_id: ID of experiment to start
            
        Returns:
            Success status
        """
        if experiment_id not in self.experiments:
            logger.error(f"Experiment not found: {experiment_id}")
            return False
        
        experiment = self.experiments[experiment_id]
        
        if experiment.status != ExperimentStatus.DRAFT:
            logger.error(f"Cannot start experiment in status: {experiment.status}")
            return False
        
        # Check if there's already an active experiment for this variant type
        if experiment.variant_type in self.active_experiments:
            current_experiment_id = self.active_experiments[experiment.variant_type]
            logger.warning(f"Stopping current experiment {current_experiment_id} to start new one")
            await self.stop_experiment(current_experiment_id)
        
        # Start the experiment
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.now()
        self.active_experiments[experiment.variant_type] = experiment_id
        
        # Initialize results
        experiment.results = [
            ExperimentResult(variant_id=variant.id)
            for variant in experiment.variants
        ]
        
        logger.info(f"Started experiment: {experiment_id}")
        return True
    
    async def get_variant(
        self,
        variant_type: VariantType,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get variant for active experiment using multi-armed bandit.
        
        Args:
            variant_type: Type of variant requested
            context: Additional context for variant selection
            
        Returns:
            Selected variant data or None if no active experiment
        """
        experiment_id = self.active_experiments.get(variant_type)
        if not experiment_id:
            return None
        
        experiment = self.experiments[experiment_id]
        if experiment.status != ExperimentStatus.RUNNING:
            return None
        
        # Check traffic allocation
        if random.random() > experiment.traffic_allocation:
            return None
        
        # Select variant using Upper Confidence Bound (UCB) algorithm
        selected_variant_id = self._select_variant_ucb(experiment_id)
        
        # Find the variant
        selected_variant = next(
            (v for v in experiment.variants if v.id == selected_variant_id),
            None
        )
        
        if selected_variant:
            # Record impression
            await self._record_impression(experiment_id, selected_variant_id)
            
            return {
                "experiment_id": experiment_id,
                "variant_id": selected_variant_id,
                "variant_name": selected_variant.name,
                "content": selected_variant.content,
                "metadata": selected_variant.metadata
            }
        
        return None
    
    def _select_variant_ucb(self, experiment_id: str) -> str:
        """Select variant using Upper Confidence Bound algorithm."""
        arms = self.bandit_arms[experiment_id]
        total_pulls = sum(arm.pulls for arm in arms)
        
        if total_pulls == 0:
            # Random selection for first pull
            return random.choice(arms).variant_id
        
        # Calculate UCB for each arm
        best_arm = None
        best_ucb = -float('inf')
        
        for arm in arms:
            if arm.pulls == 0:
                # Always try unexplored arms first
                return arm.variant_id
            
            # UCB formula: average_reward + sqrt(2 * ln(total_pulls) / arm_pulls)
            confidence_bound = math.sqrt(2 * math.log(total_pulls) / arm.pulls)
            ucb = arm.average_reward + confidence_bound
            
            if ucb > best_ucb:
                best_ucb = ucb
                best_arm = arm
        
        return best_arm.variant_id if best_arm else arms[0].variant_id
    
    async def _record_impression(self, experiment_id: str, variant_id: str) -> None:
        """Record an impression for a variant."""
        # Update experiment results
        experiment = self.experiments[experiment_id]
        result = next((r for r in experiment.results if r.variant_id == variant_id), None)
        if result:
            result.impressions += 1
        
        # Update bandit arm
        arm = next((a for a in self.bandit_arms[experiment_id] if a.variant_id == variant_id), None)
        if arm:
            arm.pulls += 1
    
    async def record_conversion(
        self,
        experiment_id: str,
        variant_id: str,
        conversion_value: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Record a conversion for a variant.
        
        Args:
            experiment_id: Experiment ID
            variant_id: Variant that led to conversion
            conversion_value: Value of the conversion (1.0 for binary conversion)
            metadata: Additional conversion metadata
            
        Returns:
            Success status
        """
        if experiment_id not in self.experiments:
            logger.error(f"Experiment not found: {experiment_id}")
            return False
        
        experiment = self.experiments[experiment_id]
        if experiment.status != ExperimentStatus.RUNNING:
            logger.warning(f"Recording conversion for non-running experiment: {experiment_id}")
        
        # Update experiment results
        result = next((r for r in experiment.results if r.variant_id == variant_id), None)
        if result:
            result.conversions += 1
            result.total_value += conversion_value
            if result.impressions > 0:
                result.conversion_rate = result.conversions / result.impressions
        
        # Update bandit arm
        arm = next((a for a in self.bandit_arms[experiment_id] if a.variant_id == variant_id), None)
        if arm:
            arm.rewards.append(conversion_value)
            arm.total_reward += conversion_value
            if arm.pulls > 0:
                arm.average_reward = arm.total_reward / arm.pulls
        
        # Check if experiment should be completed
        await self._check_experiment_completion(experiment_id)
        
        logger.info(f"Recorded conversion for experiment {experiment_id}, variant {variant_id}")
        return True
    
    async def _check_experiment_completion(self, experiment_id: str) -> None:
        """Check if experiment meets completion criteria."""
        experiment = self.experiments[experiment_id]
        
        if experiment.status != ExperimentStatus.RUNNING:
            return
        
        # Check minimum sample size
        min_samples_met = all(
            result.impressions >= experiment.min_sample_size
            for result in experiment.results
        )
        
        if not min_samples_met:
            return
        
        # Check statistical significance
        if len(experiment.results) >= 2:
            statistical_significance = self._calculate_statistical_significance(experiment.results)
            
            if statistical_significance >= experiment.significance_threshold:
                await self._complete_experiment(experiment_id, "statistical_significance")
                return
        
        # Check maximum duration
        if experiment.started_at:
            duration = datetime.now() - experiment.started_at
            if duration.days >= experiment.max_duration_days:
                await self._complete_experiment(experiment_id, "max_duration_reached")
    
    def _calculate_statistical_significance(self, results: List[ExperimentResult]) -> float:
        """Calculate statistical significance using z-test."""
        if len(results) < 2:
            return 0.0
        
        # Get the two best performing variants
        sorted_results = sorted(results, key=lambda r: r.conversion_rate, reverse=True)
        best_result = sorted_results[0]
        second_result = sorted_results[1]
        
        # Calculate z-score for difference in conversion rates
        p1 = best_result.conversion_rate
        p2 = second_result.conversion_rate
        n1 = best_result.impressions
        n2 = second_result.impressions
        
        if n1 == 0 or n2 == 0 or p1 == p2:
            return 0.0
        
        # Pooled proportion
        p_pool = (best_result.conversions + second_result.conversions) / (n1 + n2)
        
        # Standard error
        se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
        
        if se == 0:
            return 0.0
        
        # Z-score
        z = abs(p1 - p2) / se
        
        # Convert z-score to confidence level (approximate)
        confidence = min(0.999, max(0.0, (z - 1.96) / 1.96 * 0.45 + 0.55))
        
        return confidence
    
    async def _complete_experiment(self, experiment_id: str, reason: str) -> None:
        """Complete an experiment and select winner."""
        experiment = self.experiments[experiment_id]
        
        # Find winner (highest conversion rate)
        if experiment.results:
            winner = max(experiment.results, key=lambda r: r.conversion_rate)
            experiment.winner_variant_id = winner.variant_id
        
        # Update experiment status
        experiment.status = ExperimentStatus.COMPLETED
        experiment.completed_at = datetime.now()
        
        # Remove from active experiments
        if experiment.variant_type in self.active_experiments:
            del self.active_experiments[experiment.variant_type]
        
        logger.info(f"Completed experiment {experiment_id}: winner={experiment.winner_variant_id}, reason={reason}")
    
    async def stop_experiment(self, experiment_id: str) -> bool:
        """
        Manually stop an experiment.
        
        Args:
            experiment_id: Experiment ID to stop
            
        Returns:
            Success status
        """
        if experiment_id not in self.experiments:
            return False
        
        experiment = self.experiments[experiment_id]
        
        if experiment.status == ExperimentStatus.RUNNING:
            experiment.status = ExperimentStatus.PAUSED
            
            # Remove from active experiments
            if experiment.variant_type in self.active_experiments:
                del self.active_experiments[experiment.variant_type]
            
            logger.info(f"Stopped experiment: {experiment_id}")
            return True
        
        return False
    
    async def get_experiment_results(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed results for an experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Experiment results or None if not found
        """
        if experiment_id not in self.experiments:
            return None
        
        experiment = self.experiments[experiment_id]
        
        # Calculate additional metrics
        total_impressions = sum(result.impressions for result in experiment.results)
        total_conversions = sum(result.conversions for result in experiment.results)
        overall_conversion_rate = total_conversions / total_impressions if total_impressions > 0 else 0.0
        
        # Calculate statistical significance
        statistical_significance = self._calculate_statistical_significance(experiment.results)
        
        return {
            "experiment": {
                "id": experiment.id,
                "name": experiment.name,
                "description": experiment.description,
                "variant_type": experiment.variant_type.value,
                "optimization_goal": experiment.optimization_goal.value,
                "status": experiment.status.value,
                "created_at": experiment.created_at.isoformat(),
                "started_at": experiment.started_at.isoformat() if experiment.started_at else None,
                "completed_at": experiment.completed_at.isoformat() if experiment.completed_at else None,
                "winner_variant_id": experiment.winner_variant_id
            },
            "overall_metrics": {
                "total_impressions": total_impressions,
                "total_conversions": total_conversions,
                "overall_conversion_rate": overall_conversion_rate,
                "statistical_significance": statistical_significance
            },
            "variant_results": [
                {
                    "variant_id": result.variant_id,
                    "variant_name": next(
                        (v.name for v in experiment.variants if v.id == result.variant_id),
                        result.variant_id
                    ),
                    "impressions": result.impressions,
                    "conversions": result.conversions,
                    "conversion_rate": result.conversion_rate,
                    "total_value": result.total_value,
                    "avg_value": result.total_value / result.conversions if result.conversions > 0 else 0.0
                }
                for result in experiment.results
            ],
            "bandit_performance": [
                {
                    "variant_id": arm.variant_id,
                    "pulls": arm.pulls,
                    "average_reward": arm.average_reward,
                    "total_reward": arm.total_reward
                }
                for arm in self.bandit_arms.get(experiment_id, [])
            ]
        }
    
    async def get_active_experiments(self) -> Dict[str, Any]:
        """Get all currently active experiments."""
        active = {}
        
        for variant_type, experiment_id in self.active_experiments.items():
            experiment = self.experiments[experiment_id]
            active[variant_type.value] = {
                "experiment_id": experiment_id,
                "name": experiment.name,
                "started_at": experiment.started_at.isoformat() if experiment.started_at else None,
                "variant_count": len(experiment.variants),
                "total_impressions": sum(result.impressions for result in experiment.results),
                "total_conversions": sum(result.conversions for result in experiment.results)
            }
        
        return active
    
    async def optimize_prompts(
        self,
        base_prompt: str,
        optimization_goal: OptimizationGoal,
        variations: List[str],
        min_samples: int = 50
    ) -> str:
        """
        Optimize prompts using A/B testing.
        
        Args:
            base_prompt: Base prompt template
            optimization_goal: What to optimize for
            variations: List of prompt variations to test
            min_samples: Minimum samples per variant
            
        Returns:
            Experiment ID for tracking
        """
        variants = [
            {"id": f"prompt_{i}", "name": f"Prompt Variation {i+1}", "content": variation}
            for i, variation in enumerate([base_prompt] + variations)
        ]
        
        return await self.create_experiment(
            name="Prompt Optimization",
            description="Testing different prompt variations for optimization",
            variant_type=VariantType.PROMPT_TEMPLATE,
            variants=variants,
            optimization_goal=optimization_goal,
            min_sample_size=min_samples
        )
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        total_experiments = len(self.experiments)
        active_count = len(self.active_experiments)
        completed_count = sum(1 for exp in self.experiments.values() if exp.status == ExperimentStatus.COMPLETED)
        
        # Calculate total impressions and conversions across all experiments
        total_impressions = sum(
            sum(result.impressions for result in exp.results)
            for exp in self.experiments.values()
        )
        
        total_conversions = sum(
            sum(result.conversions for result in exp.results)
            for exp in self.experiments.values()
        )
        
        return {
            "total_experiments": total_experiments,
            "active_experiments": active_count,
            "completed_experiments": completed_count,
            "total_impressions": total_impressions,
            "total_conversions": total_conversions,
            "overall_conversion_rate": total_conversions / total_impressions if total_impressions > 0 else 0.0,
            "experiment_templates": len(self.experiment_templates),
            "supported_variant_types": [vt.value for vt in VariantType],
            "supported_optimization_goals": [og.value for og in OptimizationGoal]
        }