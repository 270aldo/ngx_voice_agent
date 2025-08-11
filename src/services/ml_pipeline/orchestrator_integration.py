"""
Orchestrator Integration for ML Pipeline.

Integrates the ML Pipeline with the conversation orchestrator to:
- Capture predictions in real-time
- Store ML events
- Enable pattern recognition
- Support A/B testing
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.services.ml_pipeline.ml_pipeline_service import MLPipelineService
from src.services.conversation.ml_tracking import MLTrackingMixin

logger = logging.getLogger(__name__)


class MLPipelineIntegration:
    """
    Integrates ML Pipeline with the conversation orchestrator.
    """
    
    def __init__(self):
        """Initialize ML Pipeline integration."""
        self.pipeline = MLPipelineService()
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize the ML pipeline integration."""
        if self.initialized:
            return
        
        try:
            # Initialize pipeline components
            logger.info("Initializing ML Pipeline integration...")
            
            # Check pipeline health
            health = await self.pipeline.get_ml_pipeline_metrics()
            
            if health.get("pipeline_status") == "operational":
                self.initialized = True
                logger.info("ML Pipeline integration initialized successfully")
            else:
                logger.error(f"ML Pipeline not operational: {health}")
            
        except Exception as e:
            logger.error(f"Error initializing ML Pipeline: {e}")
    
    async def process_orchestrator_predictions(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any],
        existing_predictions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process predictions from the orchestrator.
        
        This method should be called by the orchestrator after making predictions.
        
        Args:
            conversation_id: Conversation ID
            messages: Conversation messages
            context: Conversation context
            existing_predictions: Predictions already made by orchestrator
            
        Returns:
            Enhanced predictions with ML pipeline tracking
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            # Process through ML pipeline
            result = await self.pipeline.process_conversation_predictions(
                conversation_id=conversation_id,
                messages=messages,
                context=context,
                predictions=existing_predictions
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing predictions: {e}")
            return {
                "predictions": existing_predictions or {},
                "error": str(e)
            }
    
    async def record_conversation_outcome(
        self,
        conversation_id: str,
        outcome: str,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Record conversation outcome for ML learning.
        
        Args:
            conversation_id: Conversation ID
            outcome: Conversation outcome
            metrics: Conversation metrics
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            await self.pipeline.record_conversation_outcome(
                conversation_id=conversation_id,
                outcome=outcome,
                metrics=metrics
            )
        except Exception as e:
            logger.error(f"Error recording outcome: {e}")
    
    async def get_ml_insights_for_conversation(
        self,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        Get ML insights for a specific conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            ML insights and predictions
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            # Get recent predictions
            events = await self.pipeline.event_tracker.get_event_stream(
                conversation_id=conversation_id,
                event_types=["predictions_computed"],
                limit=10
            )
            
            if not events:
                return {"insights": "No ML data available"}
            
            # Get latest predictions
            latest_event = events[0]
            predictions = latest_event.get("data", {}).get("predictions", {})
            
            # Generate insights
            insights = {
                "predictions": predictions,
                "confidence_scores": self._extract_confidence_scores(predictions),
                "recommended_actions": self._generate_recommendations(predictions),
                "ab_variants": predictions.get("ab_variants", {})
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting ML insights: {e}")
            return {"error": str(e)}
    
    def _extract_confidence_scores(
        self,
        predictions: Dict[str, Any]
    ) -> Dict[str, float]:
        """Extract confidence scores from predictions."""
        scores = {}
        
        if "objections" in predictions:
            scores["objection_confidence"] = predictions["objections"].get("confidence", 0)
        
        if "needs" in predictions:
            scores["needs_confidence"] = predictions["needs"].get("confidence", 0)
        
        if "conversion" in predictions:
            scores["conversion_probability"] = predictions["conversion"].get("probability", 0)
        
        return scores
    
    def _generate_recommendations(
        self,
        predictions: Dict[str, Any]
    ) -> List[str]:
        """Generate action recommendations based on predictions."""
        recommendations = []
        
        # Check objections
        if "objections" in predictions:
            objections = predictions["objections"].get("objections", [])
            if objections:
                top_objection = objections[0]
                recommendations.append(
                    f"Address {top_objection['type']} objection with: "
                    f"{top_objection['suggested_responses'][0] if top_objection.get('suggested_responses') else 'empathy'}"
                )
        
        # Check needs
        if "needs" in predictions:
            needs = predictions["needs"].get("needs", [])
            if needs:
                top_need = needs[0]
                recommendations.append(
                    f"Focus on {top_need['type']} need - "
                    f"{top_need['recommendations'][0] if top_need.get('recommendations') else 'provide information'}"
                )
        
        # Check conversion
        if "conversion" in predictions:
            conversion = predictions["conversion"]
            if conversion.get("probability", 0) > 0.7:
                recommendations.append("High conversion probability - proceed to close")
            elif conversion.get("probability", 0) < 0.3:
                recommendations.append("Low conversion probability - focus on building trust")
        
        return recommendations


# Enhanced MLTrackingMixin with Pipeline Integration
class EnhancedMLTrackingMixin(MLTrackingMixin):
    """
    Enhanced ML tracking that integrates with the ML Pipeline.
    """
    
    def __init__(self):
        """Initialize enhanced tracking."""
        super().__init__()
        self.ml_pipeline = MLPipelineIntegration()
    
    async def _process_ml_predictions(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any],
        predictions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process ML predictions through the pipeline.
        
        Args:
            conversation_id: Conversation ID
            messages: Conversation messages
            context: Conversation context
            predictions: Raw predictions
            
        Returns:
            Enhanced predictions
        """
        # Process through ML pipeline
        enhanced = await self.ml_pipeline.process_orchestrator_predictions(
            conversation_id=conversation_id,
            messages=messages,
            context=context,
            existing_predictions=predictions
        )
        
        return enhanced
    
    async def _record_ml_outcome(
        self,
        conversation_id: str,
        outcome: str,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Record outcome through ML pipeline.
        
        Args:
            conversation_id: Conversation ID
            outcome: Conversation outcome
            metrics: Performance metrics
        """
        # Add ML-specific metrics
        ml_metrics = {
            **metrics,
            "ml_tracking_enabled": True,
            "pipeline_version": "1.0",
            "timestamp": datetime.now().isoformat()
        }
        
        # Record through pipeline
        await self.ml_pipeline.record_conversation_outcome(
            conversation_id=conversation_id,
            outcome=outcome,
            metrics=ml_metrics
        )


def create_orchestrator_patch() -> Dict[str, Any]:
    """
    Create a patch for the orchestrator to integrate ML pipeline.
    
    Returns:
        Patch configuration
    """
    return {
        "mixin_class": EnhancedMLTrackingMixin,
        "methods_to_override": [
            "_process_ml_predictions",
            "_record_ml_outcome"
        ],
        "initialization": """
# Add to orchestrator __init__:
self.ml_pipeline_integration = MLPipelineIntegration()
await self.ml_pipeline_integration.initialize()
""",
        "prediction_integration": """
# Add after making predictions in orchestrator:
if self.ml_pipeline_integration:
    enhanced_predictions = await self.ml_pipeline_integration.process_orchestrator_predictions(
        conversation_id=state.conversation_id,
        messages=state.messages,
        context={
            "phase": state.phase,
            "customer_data": state.customer_data,
            "program_type": state.program_type
        },
        existing_predictions=predictions
    )
    predictions = enhanced_predictions.get("predictions", predictions)
""",
        "outcome_integration": """
# Add when recording conversation outcome:
if self.ml_pipeline_integration:
    await self.ml_pipeline_integration.record_conversation_outcome(
        conversation_id=conversation_id,
        outcome=outcome,
        metrics={
            "predictions": predictions,
            "duration_seconds": duration,
            "message_count": len(state.messages),
            "final_phase": state.phase,
            "ab_variants": getattr(state, "ab_variants", {})
        }
    )
"""
    }