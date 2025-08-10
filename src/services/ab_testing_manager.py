"""
A/B Testing Manager - Production-ready A/B testing management system.

This service manages active A/B testing experiments for the NGX Voice Sales Agent,
including experiment creation, variant assignment, outcome tracking, and automatic
optimization using Multi-Armed Bandit algorithms.

Key features:
- Experiment lifecycle management
- Dynamic variant assignment with Multi-Armed Bandit
- Real-time performance tracking
- Automatic winner deployment
- Statistical significance analysis
- Integration with conversation orchestrator
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import uuid
import json
from enum import Enum
from dataclasses import dataclass, field

from src.services.ab_testing_framework import ABTestingFramework
from src.models.learning_models import (
    ExperimentType, ExperimentVariant, MLExperiment,
    ExperimentStatus, ConversationOutcomeRecord
)
from src.integrations.supabase.resilient_client import resilient_supabase_client as supabase_client
from src.utils.async_task_manager import AsyncTaskManager, get_task_registry

logger = logging.getLogger(__name__)


class ExperimentCategory(Enum):
    """Categories of experiments we run."""
    GREETING = "greeting"
    PRICE_OBJECTION = "price_objection"
    CLOSING_TECHNIQUE = "closing_technique"
    EMPATHY_RESPONSE = "empathy_response"
    VALUE_PROPOSITION = "value_proposition"
    FEATURE_PRESENTATION = "feature_presentation"


@dataclass
class ExperimentConfig:
    """Configuration for an experiment."""
    name: str
    category: ExperimentCategory
    description: str
    hypothesis: str
    variants: List[Dict[str, Any]]
    target_metric: str = "conversion_rate"
    minimum_sample_size: int = 100
    confidence_level: float = 0.95
    auto_deploy: bool = True
    targeting_criteria: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VariantContent:
    """Content for a specific variant."""
    variant_id: str
    content: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ABTestingManager:
    """
    Production-ready A/B Testing Manager for NGX Voice Sales Agent.
    
    Manages the complete lifecycle of A/B testing experiments including:
    - Creating and configuring experiments
    - Assigning variants to conversations
    - Tracking performance and outcomes
    - Statistical analysis and winner determination
    - Automatic deployment of winning variants
    """
    
    def __init__(self):
        """Initialize the A/B Testing Manager."""
        self.ab_framework = ABTestingFramework()
        self.supabase = supabase_client
        
        # Cache for active experiments by category
        self.experiments_by_category: Dict[ExperimentCategory, List[MLExperiment]] = {
            category: [] for category in ExperimentCategory
        }
        
        # Variant assignment tracking
        self.conversation_assignments: Dict[str, Dict[str, str]] = {}
        
        # Default experiment configurations
        self.default_experiments = self._get_default_experiments()
        
        # Task manager for background tasks
        self.task_manager: Optional[AsyncTaskManager] = None
        
        # Initialize background tasks (deferred until first use)
        self._initialized = False
        
        logger.info("ABTestingManager initialized")
    
    async def _ensure_initialized(self):
        """Ensure async components are initialized."""
        if not self._initialized:
            await self._initialize_async()
            
    async def _initialize_async(self):
        """Async initialization including task manager setup."""
        try:
            # Get task manager from registry
            registry = get_task_registry()
            self.task_manager = await registry.register_service("ab_testing_manager")
            
            # Start background tasks with proper management
            await self._start_background_tasks()
            
            self._initialized = True
            logger.info("ABTestingManager async initialization complete")
        except Exception as e:
            logger.error(f"Failed to initialize ABTestingManager async: {e}")
            # Set as initialized anyway to prevent repeated attempts
            self._initialized = True
    
    async def _start_background_tasks(self):
        """Start background processing tasks with proper management."""
        if not self.task_manager:
            logger.error("Task manager not initialized")
            return
        
        await self.task_manager.create_task(
            self._sync_active_experiments(),
            name="sync_experiments"
        )
        await self.task_manager.create_task(
            self._monitor_experiment_performance(),
            name="monitor_performance"
        )
        await self.task_manager.create_task(
            self._auto_create_experiments(),
            name="auto_create_experiments"
        )
    
    def _get_default_experiments(self) -> List[ExperimentConfig]:
        """Get default experiment configurations."""
        return [
            # Greeting experiments
            ExperimentConfig(
                name="ultra_empathy_greeting_variants",
                category=ExperimentCategory.GREETING,
                description="Test different ultra-empathetic greeting approaches",
                hypothesis="More personalized and empathetic greetings will increase engagement by 20%",
                variants=[
                    {
                        "name": "consultive_professional",
                        "type": "greeting",
                        "content": "consultive",
                        "parameters": {
                            "style": "professional",
                            "empathy_level": "high",
                            "personalization": "medium"
                        }
                    },
                    {
                        "name": "warm_personal",
                        "type": "greeting",
                        "content": "warm",
                        "parameters": {
                            "style": "personal",
                            "empathy_level": "very_high",
                            "personalization": "high"
                        }
                    },
                    {
                        "name": "motivational_inspiring",
                        "type": "greeting",
                        "content": "motivational",
                        "parameters": {
                            "style": "inspiring",
                            "empathy_level": "high",
                            "personalization": "medium",
                            "energy": "high"
                        }
                    }
                ],
                target_metric="engagement_score",
                minimum_sample_size=150
            ),
            
            # Price objection handling experiments
            ExperimentConfig(
                name="price_objection_handling_strategies",
                category=ExperimentCategory.PRICE_OBJECTION,
                description="Test different approaches to handle price objections",
                hypothesis="Value-focused responses will convert 30% better than discount-focused ones",
                variants=[
                    {
                        "name": "value_roi_focus",
                        "type": "price_response",
                        "content": "roi_focused",
                        "parameters": {
                            "approach": "value_demonstration",
                            "roi_calculation": True,
                            "comparison": "competitor"
                        }
                    },
                    {
                        "name": "payment_flexibility",
                        "type": "price_response",
                        "content": "payment_options",
                        "parameters": {
                            "approach": "flexibility",
                            "payment_plans": True,
                            "discount_mention": "subtle"
                        }
                    },
                    {
                        "name": "testimonial_proof",
                        "type": "price_response",
                        "content": "social_proof",
                        "parameters": {
                            "approach": "testimonials",
                            "success_stories": True,
                            "roi_examples": True
                        }
                    }
                ],
                target_metric="conversion_rate",
                minimum_sample_size=200,
                targeting_criteria={
                    "phases": ["pricing_discussion", "objection_handling"]
                }
            ),
            
            # Closing technique experiments
            ExperimentConfig(
                name="closing_technique_optimization",
                category=ExperimentCategory.CLOSING_TECHNIQUE,
                description="Test different closing techniques for higher conversion",
                hypothesis="Assumptive close with urgency will increase conversions by 25%",
                variants=[
                    {
                        "name": "assumptive_close",
                        "type": "closing",
                        "content": "assumptive",
                        "parameters": {
                            "style": "confident",
                            "urgency": "medium",
                            "next_steps": "clear"
                        }
                    },
                    {
                        "name": "consultive_choice",
                        "type": "closing",
                        "content": "choice_close",
                        "parameters": {
                            "style": "consultive",
                            "options": "multiple",
                            "recommendation": "personalized"
                        }
                    },
                    {
                        "name": "urgency_scarcity",
                        "type": "closing",
                        "content": "urgency",
                        "parameters": {
                            "style": "urgent",
                            "scarcity": "time_limited",
                            "bonus": "exclusive"
                        }
                    }
                ],
                target_metric="conversion_rate",
                minimum_sample_size=250,
                targeting_criteria={
                    "phases": ["closing", "commitment"]
                }
            ),
            
            # Empathy response experiments
            ExperimentConfig(
                name="empathy_response_variations",
                category=ExperimentCategory.EMPATHY_RESPONSE,
                description="Test different empathetic response styles",
                hypothesis="Mirroring emotional tone will increase satisfaction scores by 15%",
                variants=[
                    {
                        "name": "emotional_mirroring",
                        "type": "empathy",
                        "content": "mirroring",
                        "parameters": {
                            "style": "reflective",
                            "intensity": "matched",
                            "validation": "high"
                        }
                    },
                    {
                        "name": "supportive_encouraging",
                        "type": "empathy",
                        "content": "supportive",
                        "parameters": {
                            "style": "encouraging",
                            "intensity": "warm",
                            "validation": "moderate"
                        }
                    },
                    {
                        "name": "solution_focused",
                        "type": "empathy",
                        "content": "solution_oriented",
                        "parameters": {
                            "style": "practical",
                            "intensity": "balanced",
                            "action_oriented": True
                        }
                    }
                ],
                target_metric="satisfaction_score",
                minimum_sample_size=200
            )
        ]
    
    async def initialize(self) -> None:
        """Initialize the A/B Testing Manager and create default experiments."""
        # Ensure async components are initialized
        await self._ensure_initialized()
        
        try:
            # Load active experiments
            await self._sync_active_experiments()
            
            # Create default experiments if none exist
            await self._ensure_default_experiments()
            
            logger.info("ABTestingManager initialization complete")
            
        except Exception as e:
            logger.error(f"Error initializing ABTestingManager: {e}")
            raise
    
    async def _sync_active_experiments(self) -> None:
        """Sync active experiments from the framework."""
        while True:
            try:
                # Get active experiments from framework
                active_experiments = await self.ab_framework.get_active_experiments()
                
                # Clear current cache
                for category in ExperimentCategory:
                    self.experiments_by_category[category] = []
                
                # Categorize experiments
                for experiment in active_experiments:
                    # Determine category from experiment name or metadata
                    category = self._determine_experiment_category(experiment)
                    if category:
                        self.experiments_by_category[category].append(experiment)
                
                logger.debug(f"Synced {len(active_experiments)} active experiments")
                
                # Wait before next sync
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Error syncing experiments: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute on error
    
    def _determine_experiment_category(self, experiment: MLExperiment) -> Optional[ExperimentCategory]:
        """Determine the category of an experiment."""
        name_lower = experiment.experiment_name.lower()
        
        if "greeting" in name_lower:
            return ExperimentCategory.GREETING
        elif "price" in name_lower or "objection" in name_lower:
            return ExperimentCategory.PRICE_OBJECTION
        elif "closing" in name_lower or "close" in name_lower:
            return ExperimentCategory.CLOSING_TECHNIQUE
        elif "empathy" in name_lower or "emotional" in name_lower:
            return ExperimentCategory.EMPATHY_RESPONSE
        elif "value" in name_lower or "proposition" in name_lower:
            return ExperimentCategory.VALUE_PROPOSITION
        elif "feature" in name_lower:
            return ExperimentCategory.FEATURE_PRESENTATION
        
        return None
    
    async def _ensure_default_experiments(self) -> None:
        """Ensure default experiments are created and running."""
        try:
            for config in self.default_experiments:
                # Check if experiment already exists
                existing = await self._find_experiment_by_name(config.name)
                
                if not existing:
                    # Create new experiment
                    experiment = await self.ab_framework.create_experiment(
                        experiment_name=config.name,
                        experiment_type=ExperimentType.STRATEGY_TEST,
                        description=config.description,
                        hypothesis=config.hypothesis,
                        variants=config.variants,
                        target_metric=config.target_metric,
                        minimum_sample_size=config.minimum_sample_size,
                        auto_deploy=config.auto_deploy
                    )
                    
                    if experiment:
                        # Start the experiment
                        await self.ab_framework.start_experiment(experiment.experiment_id)
                        logger.info(f"Created and started default experiment: {config.name}")
                
                elif existing.status == ExperimentStatus.PLANNING:
                    # Start planned experiment
                    await self.ab_framework.start_experiment(existing.experiment_id)
                    logger.info(f"Started existing experiment: {config.name}")
                    
        except Exception as e:
            logger.error(f"Error ensuring default experiments: {e}")
    
    async def _find_experiment_by_name(self, name: str) -> Optional[MLExperiment]:
        """Find an experiment by name."""
        try:
            result = await supabase_client.select(
                table="ml_experiments",
                columns="*",
                filters={"experiment_name": name}
            )
            
            # Handle both list and object responses
            data = result if isinstance(result, list) else (result.data if hasattr(result, 'data') else [])
            
            if data and len(data) > 0:
                # Convert to MLExperiment (simplified)
                exp_data = data[0]
                return MLExperiment(
                    experiment_id=exp_data["experiment_id"],
                    experiment_name=exp_data["experiment_name"],
                    experiment_type=ExperimentType(exp_data["experiment_type"]),
                    description=exp_data["description"],
                    hypothesis=exp_data["hypothesis"],
                    variants=[],  # Would need to parse properly
                    target_metric=exp_data["target_metric"],
                    status=ExperimentStatus(exp_data["status"])
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding experiment by name: {e}")
            return None
    
    async def get_variant_for_conversation(
        self,
        conversation_id: str,
        category: ExperimentCategory,
        context: Dict[str, Any]
    ) -> Optional[VariantContent]:
        """
        Get the appropriate variant for a conversation based on category and context.
        
        Args:
            conversation_id: Unique conversation identifier
            category: Category of experiment to get variant for
            context: Conversation context for targeting
            
        Returns:
            VariantContent with the selected variant or None
        """
        # Ensure async components are initialized
        await self._ensure_initialized()
        
        try:
            # Get active experiments for this category
            experiments = self.experiments_by_category.get(category, [])
            
            if not experiments:
                return None
            
            # Find the most relevant experiment based on targeting criteria
            relevant_experiment = self._find_relevant_experiment(experiments, context)
            
            if not relevant_experiment:
                return None
            
            # Get variant assignment from framework
            variant = await self.ab_framework.select_variant(
                experiment_id=relevant_experiment.experiment_id,
                context=context
            )
            
            if variant:
                # Track assignment
                if conversation_id not in self.conversation_assignments:
                    self.conversation_assignments[conversation_id] = {}
                
                self.conversation_assignments[conversation_id][category.value] = {
                    "experiment_id": relevant_experiment.experiment_id,
                    "variant_id": variant.variant_id,
                    "assigned_at": datetime.now().isoformat()
                }
                
                # Return variant content
                return VariantContent(
                    variant_id=variant.variant_id,
                    content=variant.variant_content,
                    parameters=variant.variant_content.get("parameters", {}) if isinstance(variant.variant_content, dict) else {},
                    metadata={
                        "experiment_name": relevant_experiment.experiment_name,
                        "variant_name": variant.variant_name
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting variant for conversation: {e}")
            return None
    
    def _find_relevant_experiment(
        self,
        experiments: List[MLExperiment],
        context: Dict[str, Any]
    ) -> Optional[MLExperiment]:
        """
        Find the most relevant experiment based on context and targeting criteria.
        """
        # For now, return the first running experiment
        # In production, this would check targeting criteria
        for experiment in experiments:
            if experiment.status == ExperimentStatus.RUNNING:
                return experiment
        
        return None
    
    async def record_outcome(
        self,
        conversation_id: str,
        outcome: str,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Record the outcome of a conversation for all assigned experiments.
        
        Args:
            conversation_id: Conversation identifier
            outcome: Outcome type (converted, abandoned, etc.)
            metrics: Performance metrics
        """
        # Ensure async components are initialized
        await self._ensure_initialized()
        
        try:
            if conversation_id not in self.conversation_assignments:
                return
            
            assignments = self.conversation_assignments[conversation_id]
            
            # Create outcome record
            outcome_record = ConversationOutcomeRecord(
                conversation_id=conversation_id,
                outcome=outcome,
                metrics=metrics,
                experiment_assignments=[
                    assignment["experiment_id"] 
                    for assignment in assignments.values()
                ]
            )
            
            # Record outcome for each experiment
            for category_name, assignment in assignments.items():
                experiment_id = assignment["experiment_id"]
                variant_id = assignment["variant_id"]
                
                # Calculate success based on outcome and category
                success = self._calculate_success(outcome, metrics, ExperimentCategory(category_name))
                
                # Record conversion in framework
                await self.ab_framework.record_conversion(
                    experiment_id=experiment_id,
                    variant_id=variant_id,
                    success=success,
                    value=metrics.get("conversion_value", 0)
                )
            
            # Clean up assignment tracking
            del self.conversation_assignments[conversation_id]
            
            logger.debug(f"Recorded outcomes for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error recording outcome: {e}")
    
    def _calculate_success(
        self,
        outcome: str,
        metrics: Dict[str, Any],
        category: ExperimentCategory
    ) -> bool:
        """
        Calculate if the outcome represents success for a specific experiment category.
        """
        # Base success on outcome
        if outcome in ["completed", "converted", "qualified"]:
            return True
        
        # Category-specific success criteria
        if category == ExperimentCategory.GREETING:
            # Success if high engagement
            return metrics.get("engagement_score", 0) >= 7
        
        elif category == ExperimentCategory.EMPATHY_RESPONSE:
            # Success if high satisfaction
            return metrics.get("satisfaction_score", 0) >= 8
        
        elif category == ExperimentCategory.PRICE_OBJECTION:
            # Success if overcame price objection
            return metrics.get("price_objection_overcome", False)
        
        return False
    
    async def get_experiment_results(
        self,
        category: Optional[ExperimentCategory] = None
    ) -> Dict[str, Any]:
        """
        Get current results for experiments.
        
        Args:
            category: Optional category to filter by
            
        Returns:
            Dictionary with experiment results and statistics
        """
        try:
            results = {
                "experiments": [],
                "summary": {
                    "total_active": 0,
                    "total_conversions": 0,
                    "winners_found": 0
                }
            }
            
            # Get experiments to analyze
            if category:
                experiments = self.experiments_by_category.get(category, [])
            else:
                experiments = []
                for exp_list in self.experiments_by_category.values():
                    experiments.extend(exp_list)
            
            # Get results for each experiment
            for experiment in experiments:
                if experiment.status == ExperimentStatus.RUNNING:
                    exp_results = await self.ab_framework.get_experiment_stats(
                        experiment.experiment_id
                    )
                    
                    if exp_results and "error" not in exp_results:
                        results["experiments"].append({
                            "name": experiment.experiment_name,
                            "category": self._determine_experiment_category(experiment).value,
                            "status": experiment.status.value,
                            "results": exp_results
                        })
                        
                        results["summary"]["total_active"] += 1
                        results["summary"]["total_conversions"] += exp_results.get(
                            "total_conversions", 0
                        )
                        
                        # Check if winner found
                        if experiment.winning_variant_id:
                            results["summary"]["winners_found"] += 1
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting experiment results: {e}")
            return {"error": str(e)}
    
    async def _monitor_experiment_performance(self) -> None:
        """Monitor experiment performance and log insights."""
        while True:
            try:
                await asyncio.sleep(3600)  # Every hour
                
                # Get results for all experiments
                results = await self.get_experiment_results()
                
                if "error" not in results:
                    # Log summary
                    summary = results["summary"]
                    logger.info(
                        f"A/B Testing Performance - "
                        f"Active: {summary['total_active']}, "
                        f"Conversions: {summary['total_conversions']}, "
                        f"Winners: {summary['winners_found']}"
                    )
                    
                    # Check for experiments ready to conclude
                    for exp_data in results["experiments"]:
                        exp_results = exp_data["results"]
                        if exp_results.get("total_assignments", 0) >= exp_results.get("minimum_sample_size", 100):
                            logger.info(
                                f"Experiment '{exp_data['name']}' has reached minimum sample size"
                            )
                
            except Exception as e:
                logger.error(f"Error monitoring experiments: {e}")
    
    async def _auto_create_experiments(self) -> None:
        """Automatically create new experiments based on performance data."""
        while True:
            try:
                await asyncio.sleep(86400)  # Daily
                
                # This is where we would analyze performance data and create new experiments
                # For now, just ensure default experiments exist
                await self._ensure_default_experiments()
                
                logger.info("Completed daily experiment creation check")
                
            except Exception as e:
                logger.error(f"Error in auto-create experiments: {e}")
    
    async def create_custom_experiment(
        self,
        config: ExperimentConfig
    ) -> Optional[str]:
        """
        Create a custom experiment from configuration.
        
        Args:
            config: Experiment configuration
            
        Returns:
            Experiment ID if successful, None otherwise
        """
        try:
            experiment = await self.ab_framework.create_experiment(
                experiment_name=config.name,
                experiment_type=ExperimentType.STRATEGY_TEST,
                description=config.description,
                hypothesis=config.hypothesis,
                variants=config.variants,
                target_metric=config.target_metric,
                minimum_sample_size=config.minimum_sample_size,
                auto_deploy=config.auto_deploy
            )
            
            if experiment:
                # Start the experiment
                await self.ab_framework.start_experiment(experiment.experiment_id)
                
                # Force sync to update cache
                await self._sync_active_experiments()
                
                logger.info(f"Created custom experiment: {config.name}")
                return experiment.experiment_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating custom experiment: {e}")
            return None
    
    def get_active_experiment_summary(self) -> Dict[str, List[str]]:
        """
        Get a summary of active experiments by category.
        
        Returns:
            Dictionary mapping categories to experiment names
        """
        summary = {}
        
        for category, experiments in self.experiments_by_category.items():
            summary[category.value] = [
                exp.experiment_name for exp in experiments
                if exp.status == ExperimentStatus.RUNNING
            ]
        
        return summary
    
    async def cleanup(self):
        """
        Cleanup resources and stop background tasks.
        
        This should be called when shutting down the service.
        """
        logger.info("Cleaning up ABTestingManager")
        
        try:
            # Unregister from task registry
            if self.task_manager:
                registry = get_task_registry()
                await registry.unregister_service("ab_testing_manager")
                self.task_manager = None
            
            logger.info("ABTestingManager cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during ABTestingManager cleanup: {e}")