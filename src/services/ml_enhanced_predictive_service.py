"""
ML Enhanced Predictive Service for NGX Voice Sales Agent.

This service integrates the ML models with the existing predictive services infrastructure,
providing a seamless upgrade path that maintains compatibility.
"""

import logging
from typing import Dict, List, Any, Optional

from src.services.objection_prediction_service import ObjectionPredictionService
from src.services.needs_prediction_service import NeedsPredictionService
from src.services.conversion_prediction_service import ConversionPredictionService
from src.services.training.ml_prediction_service import MLPredictionService

logger = logging.getLogger(__name__)

class MLEnhancedPredictiveService:
    """
    Enhanced predictive service that combines ML models with existing services.
    """
    
    def __init__(self, objection_service: ObjectionPredictionService,
                 needs_service: NeedsPredictionService,
                 conversion_service: ConversionPredictionService):
        """
        Initialize the enhanced predictive service.
        
        Args:
            objection_service: Existing objection prediction service
            needs_service: Existing needs prediction service
            conversion_service: Existing conversion prediction service
        """
        self.objection_service = objection_service
        self.needs_service = needs_service
        self.conversion_service = conversion_service
        
        # Initialize ML service
        self.ml_service = MLPredictionService()
        self.use_ml = True  # Flag to enable/disable ML
        
    async def predict_objections(self, conversation_id: str,
                               messages: List[Dict[str, Any]],
                               customer_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Predict objections using ML models with fallback to rule-based system.
        
        Args:
            conversation_id: ID of the conversation
            messages: Conversation messages
            customer_profile: Customer profile information
            
        Returns:
            Objection predictions with confidence scores
        """
        try:
            # Try ML prediction first if enabled
            if self.use_ml and self.ml_service.models_loaded:
                ml_result = await self.ml_service.predict_objections(messages, customer_profile)
                
                if "error" not in ml_result and ml_result.get("confidence", 0) > 0.6:
                    # Use ML result if confidence is high
                    logger.info(f"Using ML prediction for objections (confidence: {ml_result['confidence']:.2f})")
                    
                    # Store prediction in database using existing service
                    if ml_result.get("primary_objection"):
                        await self.objection_service.record_actual_objection(
                            conversation_id=conversation_id,
                            objection_type=ml_result["primary_objection"],
                            objection_text=messages[-1]["content"] if messages else ""
                        )
                    
                    return ml_result
            
            # Fallback to rule-based system
            logger.info("Using rule-based objection prediction")
            return await self.objection_service.predict_objections(
                conversation_id, messages, customer_profile
            )
            
        except Exception as e:
            logger.error(f"Error in enhanced objection prediction: {e}")
            # Always fallback to rule-based on error
            return await self.objection_service.predict_objections(
                conversation_id, messages, customer_profile
            )
    
    async def predict_needs(self, conversation_id: str,
                          messages: List[Dict[str, Any]],
                          customer_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Predict customer needs using ML models with fallback.
        
        Args:
            conversation_id: ID of the conversation
            messages: Conversation messages
            customer_profile: Customer profile information
            
        Returns:
            Needs predictions with recommendations
        """
        try:
            # Try ML prediction first
            if self.use_ml and self.ml_service.models_loaded:
                ml_result = await self.ml_service.predict_needs(messages, customer_profile)
                
                if "error" not in ml_result and ml_result.get("confidence", 0) > 0.5:
                    logger.info(f"Using ML prediction for needs (confidence: {ml_result['confidence']:.2f})")
                    
                    # Enhance with existing service's domain knowledge
                    enhanced_result = ml_result.copy()
                    
                    # Add response templates from existing service
                    if ml_result.get("primary_need"):
                        templates = await self.needs_service._get_response_templates(
                            ml_result["primary_need"]
                        )
                        enhanced_result["response_templates"] = templates
                    
                    # Store in database
                    if ml_result.get("primary_need"):
                        await self.needs_service.record_identified_need(
                            conversation_id=conversation_id,
                            need_category=ml_result["primary_need"],
                            need_details={"ml_predicted": True, "confidence": ml_result["confidence"]}
                        )
                    
                    return enhanced_result
            
            # Fallback to rule-based system
            logger.info("Using rule-based needs prediction")
            return await self.needs_service.predict_needs(
                conversation_id, messages, customer_profile
            )
            
        except Exception as e:
            logger.error(f"Error in enhanced needs prediction: {e}")
            return await self.needs_service.predict_needs(
                conversation_id, messages, customer_profile
            )
    
    async def predict_conversion(self, conversation_id: str,
                               messages: List[Dict[str, Any]],
                               customer_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Predict conversion probability using ML models with fallback.
        
        Args:
            conversation_id: ID of the conversation
            messages: Conversation messages
            customer_profile: Customer profile information
            
        Returns:
            Conversion predictions with strategies
        """
        try:
            # Try ML prediction first
            if self.use_ml and self.ml_service.models_loaded:
                ml_result = await self.ml_service.predict_conversion(messages, customer_profile)
                
                if "error" not in ml_result:
                    logger.info(f"Using ML prediction for conversion (probability: {ml_result['probability']:.2f})")
                    
                    # Combine with rule-based insights
                    rule_result = await self.conversion_service.predict_conversion_probability(
                        conversation_id, messages, customer_profile
                    )
                    
                    # Weighted average of ML and rule-based predictions
                    ml_weight = 0.7  # Give more weight to ML
                    rule_weight = 0.3
                    
                    combined_probability = (
                        ml_result["probability"] * ml_weight +
                        rule_result.get("probability", 0.5) * rule_weight
                    )
                    
                    # Determine final level
                    if combined_probability >= 0.7:
                        level = "high"
                    elif combined_probability >= 0.4:
                        level = "medium"
                    else:
                        level = "low"
                    
                    # Combine strategies from both systems
                    combined_result = {
                        "will_convert": combined_probability > 0.6,
                        "probability": combined_probability,
                        "conversion_level": level,
                        "ml_probability": ml_result["probability"],
                        "rule_probability": rule_result.get("probability", 0.5),
                        "positive_signals": ml_result.get("positive_signals", 0),
                        "engagement_score": ml_result.get("engagement_score", 0),
                        "recommended_strategies": ml_result.get("recommended_strategies", []),
                        "next_action": ml_result.get("next_action", ""),
                        "urgency_level": ml_result.get("urgency_level", "medium"),
                        "buying_signals": rule_result.get("buying_signals", []),
                        "risk_factors": rule_result.get("risk_factors", [])
                    }
                    
                    # Store prediction
                    await self.conversion_service.predictive_model_service.store_prediction(
                        model_name="ml_enhanced_conversion",
                        conversation_id=conversation_id,
                        prediction_type="conversion",
                        prediction_data=combined_result,
                        confidence=combined_probability
                    )
                    
                    return combined_result
            
            # Fallback to rule-based system
            logger.info("Using rule-based conversion prediction")
            return await self.conversion_service.predict_conversion_probability(
                conversation_id, messages, customer_profile
            )
            
        except Exception as e:
            logger.error(f"Error in enhanced conversion prediction: {e}")
            return await self.conversion_service.predict_conversion_probability(
                conversation_id, messages, customer_profile
            )
    
    async def get_unified_insights(self, conversation_id: str,
                                 messages: List[Dict[str, Any]],
                                 customer_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get unified insights combining all predictive models.
        
        Args:
            conversation_id: ID of the conversation
            messages: Conversation messages
            customer_profile: Customer profile information
            
        Returns:
            Comprehensive insights from all models
        """
        try:
            # Run all predictions in parallel
            objections_task = self.predict_objections(conversation_id, messages, customer_profile)
            needs_task = self.predict_needs(conversation_id, messages, customer_profile)
            conversion_task = self.predict_conversion(conversation_id, messages, customer_profile)
            
            # Wait for all results
            objections = await objections_task
            needs = await needs_task
            conversion = await conversion_task
            
            # Determine conversation phase
            message_count = len(messages)
            if message_count < 3:
                phase = "discovery"
            elif message_count < 8:
                phase = "evaluation"
            elif conversion["probability"] > 0.7:
                phase = "closing"
            else:
                phase = "nurturing"
            
            # Generate unified recommendation
            if objections.get("primary_objection"):
                primary_focus = "address_objection"
                recommended_action = objections.get("objections", [{}])[0].get(
                    "suggested_responses", ["Address the customer's concern"]
                )[0]
            elif needs.get("primary_need") and phase == "discovery":
                primary_focus = "explore_needs"
                recommended_action = f"Deep dive into their {needs['primary_need']} requirements"
            elif conversion["probability"] > 0.7:
                primary_focus = "close_deal"
                recommended_action = conversion.get("next_action", "Move to close the deal")
            else:
                primary_focus = "build_value"
                recommended_action = "Continue building value and trust"
            
            return {
                "conversation_phase": phase,
                "objections": objections,
                "needs": needs,
                "conversion": conversion,
                "primary_focus": primary_focus,
                "recommended_action": recommended_action,
                "confidence_score": (
                    objections.get("confidence", 0) * 0.3 +
                    needs.get("confidence", 0) * 0.2 +
                    conversion.get("probability", 0) * 0.5
                ),
                "ml_models_active": self.ml_service.models_loaded,
                "insights_generated_at": logger.name
            }
            
        except Exception as e:
            logger.error(f"Error generating unified insights: {e}")
            return {
                "error": str(e),
                "conversation_phase": "unknown",
                "ml_models_active": False
            }
    
    def toggle_ml(self, enable: bool) -> None:
        """Enable or disable ML predictions."""
        self.use_ml = enable
        logger.info(f"ML predictions {'enabled' if enable else 'disabled'}")