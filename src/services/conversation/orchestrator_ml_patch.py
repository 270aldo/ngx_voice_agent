"""
ML Pipeline Integration Patch for Orchestrator

This module provides the integration between the orchestrator and ML pipeline.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.services.ml_pipeline import MLPipelineService
from src.services.ml_pipeline.orchestrator_integration import MLPipelineIntegration

logger = logging.getLogger(__name__)


class MLPipelineOrchestratorPatch:
    """
    Patches the orchestrator to integrate ML Pipeline functionality.
    """
    
    @staticmethod
    def apply_patch(orchestrator_class):
        """
        Apply ML Pipeline integration to orchestrator class.
        
        Args:
            orchestrator_class: The orchestrator class to patch
        """
        # Store original methods
        original_init = orchestrator_class.__init__
        original_process_message = orchestrator_class.process_message
        
        # Create new __init__ that includes ML pipeline
        def new_init(self, *args, **kwargs):
            # Call original init
            original_init(self, *args, **kwargs)
            
            # Add ML pipeline integration
            self.ml_pipeline_integration = MLPipelineIntegration()
            self._ml_pipeline_initialized = False
            
            logger.info("ML Pipeline integration added to orchestrator")
        
        # Create enhanced process_message
        async def new_process_message(self, state: 'ConversationState', message_text: str) -> Tuple[str, Optional[Any]]:
            # Initialize ML pipeline if needed
            if not self._ml_pipeline_initialized:
                await self.ml_pipeline_integration.initialize()
                self._ml_pipeline_initialized = True
            
            # Call original process_message
            response, voice_data = await original_process_message(self, state, message_text)
            
            # Capture ML predictions if any were made
            if hasattr(self, '_last_predictions') and self._last_predictions:
                try:
                    # Process predictions through ML pipeline
                    enhanced = await self.ml_pipeline_integration.process_orchestrator_predictions(
                        conversation_id=state.conversation_id,
                        messages=[m.dict() for m in state.messages],
                        context={
                            "phase": state.phase,
                            "customer_data": state.customer_data,
                            "program_type": state.program_type,
                            "emotional_state": getattr(state, 'emotional_state', 'neutral'),
                            "tier_info": getattr(state, 'tier_info', {})
                        },
                        existing_predictions=self._last_predictions
                    )
                    
                    # Store enhanced predictions back
                    self._last_predictions = enhanced.get("predictions", self._last_predictions)
                    
                    # Add A/B variants to state if any
                    if "ab_variants" in enhanced:
                        state.ab_variants = enhanced["ab_variants"]
                    
                except Exception as e:
                    logger.error(f"Error processing ML predictions: {e}")
            
            return response, voice_data
        
        # Apply patches
        orchestrator_class.__init__ = new_init
        orchestrator_class.process_message = new_process_message
        
        # Add helper methods
        orchestrator_class._capture_ml_predictions = _capture_ml_predictions
        orchestrator_class._record_ml_outcome = _record_ml_outcome
        orchestrator_class.get_ml_insights = get_ml_insights
        
        logger.info("ML Pipeline patch applied successfully")
        return orchestrator_class


# Helper methods to add to orchestrator

async def _capture_ml_predictions(self, predictions: Dict[str, Any]) -> None:
    """
    Capture ML predictions for pipeline processing.
    
    Args:
        predictions: Dictionary of predictions from various services
    """
    self._last_predictions = predictions


async def _record_ml_outcome(
    self,
    conversation_id: str,
    outcome: str,
    metrics: Dict[str, Any]
) -> None:
    """
    Record conversation outcome to ML pipeline.
    
    Args:
        conversation_id: Conversation ID
        outcome: Conversation outcome
        metrics: Performance metrics
    """
    if hasattr(self, 'ml_pipeline_integration') and self._ml_pipeline_initialized:
        try:
            # Add predictions to metrics if available
            if hasattr(self, '_last_predictions'):
                metrics["predictions"] = self._last_predictions
            
            # Add A/B variants if any
            if hasattr(self, 'state') and hasattr(self.state, 'ab_variants'):
                metrics["ab_variants"] = self.state.ab_variants
            
            # Record outcome
            await self.ml_pipeline_integration.record_conversation_outcome(
                conversation_id=conversation_id,
                outcome=outcome,
                metrics=metrics
            )
        except Exception as e:
            logger.error(f"Error recording ML outcome: {e}")


async def get_ml_insights(self, conversation_id: str) -> Dict[str, Any]:
    """
    Get ML insights for a conversation.
    
    Args:
        conversation_id: Conversation ID
        
    Returns:
        ML insights and recommendations
    """
    if hasattr(self, 'ml_pipeline_integration') and self._ml_pipeline_initialized:
        try:
            return await self.ml_pipeline_integration.get_ml_insights_for_conversation(
                conversation_id=conversation_id
            )
        except Exception as e:
            logger.error(f"Error getting ML insights: {e}")
            return {"error": str(e)}
    else:
        return {"error": "ML pipeline not initialized"}


# Integration instructions
INTEGRATION_GUIDE = """
ML Pipeline Integration Guide for Orchestrator
============================================

1. Import the patch:
   ```python
   from src.services.conversation.orchestrator_ml_patch import MLPipelineOrchestratorPatch
   ```

2. Apply to your orchestrator class:
   ```python
   @MLPipelineOrchestratorPatch.apply_patch
   class VoiceOrchestrator(...):
       ...
   ```

3. Capture predictions in your orchestrator:
   ```python
   # After making predictions
   predictions = {
       "objections": objection_predictions,
       "needs": needs_predictions,
       "conversion": conversion_predictions
   }
   await self._capture_ml_predictions(predictions)
   ```

4. Record outcomes when conversation ends:
   ```python
   await self._record_ml_outcome(
       conversation_id=state.conversation_id,
       outcome="completed",  # or "abandoned", "transferred", etc.
       metrics={
           "duration_seconds": duration,
           "message_count": len(state.messages),
           "conversion_value": 2700  # if converted
       }
   )
   ```

5. Get ML insights:
   ```python
   insights = await self.get_ml_insights(conversation_id)
   ```

The ML pipeline will automatically:
- Store all predictions
- Run A/B tests
- Detect patterns
- Process feedback
- Update models
- Generate insights
"""


def get_integration_guide() -> str:
    """Get the integration guide."""
    return INTEGRATION_GUIDE