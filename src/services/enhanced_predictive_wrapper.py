"""
Enhanced Predictive Wrapper for NGX Voice Sales Agent.

This module wraps the predictive services to ensure they always return
meaningful results by integrating fallback predictions when ML models
are not yet trained or return empty results.
"""

from typing import Dict, List, Any, Optional
import logging

from src.services.objection_prediction_service import ObjectionPredictionService
from src.services.needs_prediction_service import NeedsPredictionService
from src.services.conversion_prediction_service import ConversionPredictionService
from src.services.fallback_predictor import FallbackPredictor

logger = logging.getLogger(__name__)

class EnhancedPredictiveWrapper:
    """
    Wrapper that enhances predictive services with fallback mechanisms.
    
    This ensures that the system always provides predictions, even when
    ML models are still being trained or lack sufficient data.
    """
    
    def __init__(self,
                 objection_service: ObjectionPredictionService,
                 needs_service: NeedsPredictionService,
                 conversion_service: ConversionPredictionService):
        """
        Initialize the enhanced wrapper with predictive services.
        
        Args:
            objection_service: Objection prediction service
            needs_service: Needs prediction service
            conversion_service: Conversion prediction service
        """
        self.objection_service = objection_service
        self.needs_service = needs_service
        self.conversion_service = conversion_service
        self.fallback_predictor = FallbackPredictor()
        
    async def predict_objections(self, conversation_id: str,
                               messages: List[Dict[str, Any]],
                               customer_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Predict objections with fallback support.
        
        Args:
            conversation_id: ID of the conversation
            messages: Conversation messages
            customer_profile: Customer profile data
            
        Returns:
            Objection predictions with fallback if needed
        """
        try:
            # Ensure messages have correct format
            formatted_messages = self._format_messages(messages)
            
            # Try ML-based prediction first
            ml_result = await self.objection_service.predict_objections(
                conversation_id, formatted_messages, customer_profile
            )
            
            # Check if ML prediction returned meaningful results
            if ml_result.get("objections") and len(ml_result["objections"]) > 0:
                logger.info(f"ML objection prediction successful for conversation {conversation_id}")
                return ml_result
                
            # Use fallback predictor if ML returns empty results
            logger.info(f"Using fallback objection prediction for conversation {conversation_id}")
            fallback_result = self.fallback_predictor.predict_objections(formatted_messages)
            
            # Merge with ML result structure
            return {
                "objections": fallback_result.get("objections", []),
                "confidence": fallback_result.get("confidence", 0.5),
                "signals": fallback_result.get("signals", {}),
                "source": "fallback"
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced objection prediction: {e}")
            # Return fallback prediction on any error
            try:
                formatted_messages = self._format_messages(messages)
                return self.fallback_predictor.predict_objections(formatted_messages)
            except Exception as fallback_error:
                logger.error(f"Fallback prediction also failed: {fallback_error}")
                return {"objections": [], "confidence": 0.0, "signals": {}, "error": str(e)}
                
    async def predict_needs(self, conversation_id: str,
                          messages: List[Dict[str, Any]],
                          customer_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Predict needs with fallback support.
        
        Args:
            conversation_id: ID of the conversation
            messages: Conversation messages
            customer_profile: Customer profile data
            
        Returns:
            Needs predictions with fallback if needed
        """
        try:
            # Ensure messages have correct format
            formatted_messages = self._format_messages(messages)
            
            # Try ML-based prediction first
            ml_result = await self.needs_service.predict_needs(
                conversation_id, formatted_messages, customer_profile
            )
            
            # Check if ML prediction returned meaningful results
            if ml_result.get("needs") and len(ml_result["needs"]) > 0:
                logger.info(f"ML needs prediction successful for conversation {conversation_id}")
                return ml_result
                
            # Use fallback predictor if ML returns empty results
            logger.info(f"Using fallback needs prediction for conversation {conversation_id}")
            fallback_result = self.fallback_predictor.predict_needs(formatted_messages)
            
            # Merge with ML result structure
            return {
                "needs": fallback_result.get("needs", []),
                "confidence": fallback_result.get("confidence", 0.5),
                "features": fallback_result.get("features", {}),
                "source": "fallback"
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced needs prediction: {e}")
            # Return fallback prediction on any error
            try:
                formatted_messages = self._format_messages(messages)
                return self.fallback_predictor.predict_needs(formatted_messages)
            except Exception as fallback_error:
                logger.error(f"Fallback needs prediction failed: {fallback_error}")
                return {"needs": [], "confidence": 0.0, "features": {}, "error": str(e)}
                
    async def predict_conversion(self, conversation_id: str,
                               messages: List[Dict[str, Any]],
                               customer_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Predict conversion probability with fallback support.
        
        Args:
            conversation_id: ID of the conversation
            messages: Conversation messages
            customer_profile: Customer profile data
            
        Returns:
            Conversion predictions with fallback if needed
        """
        try:
            # Ensure messages have correct format
            formatted_messages = self._format_messages(messages)
            
            # Try ML-based prediction first
            ml_result = await self.conversion_service.predict_conversion(
                conversation_id, formatted_messages, customer_profile
            )
            
            # Check if ML prediction returned meaningful results
            if ml_result.get("probability", 0) > 0 and ml_result.get("recommendations"):
                logger.info(f"ML conversion prediction successful for conversation {conversation_id}")
                return ml_result
                
            # Use fallback predictor if ML returns empty results
            logger.info(f"Using fallback conversion prediction for conversation {conversation_id}")
            fallback_result = self.fallback_predictor.predict_conversion(formatted_messages)
            
            # Merge with ML result structure
            return {
                "probability": fallback_result.get("probability", 0.0),
                "confidence": fallback_result.get("confidence", 0.5),
                "category": fallback_result.get("category", "low"),
                "signals": fallback_result.get("signals", {}),
                "recommendations": fallback_result.get("recommendations", []),
                "source": "fallback"
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced conversion prediction: {e}")
            # Return fallback prediction on any error
            try:
                formatted_messages = self._format_messages(messages)
                return self.fallback_predictor.predict_conversion(formatted_messages)
            except Exception as fallback_error:
                logger.error(f"Fallback conversion prediction failed: {fallback_error}")
                return {
                    "probability": 0.0,
                    "confidence": 0.0,
                    "category": "low",
                    "signals": {},
                    "recommendations": [],
                    "error": str(e)
                }
                
    def _format_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format messages to ensure they have the correct structure.
        
        Args:
            messages: Raw messages from conversation
            
        Returns:
            Formatted messages with role and content fields
        """
        formatted = []
        
        for msg in messages:
            # Handle different message formats
            if isinstance(msg, dict):
                # Ensure role field exists
                role = msg.get("role", "")
                
                # Map various role names to standard ones
                if role in ["user", "human", "cliente"]:
                    role = "customer"
                elif role in ["assistant", "agent", "bot"]:
                    role = "assistant"
                elif not role:
                    # Try to infer role from other fields
                    if msg.get("is_user") or msg.get("from_user"):
                        role = "customer"
                    else:
                        role = "assistant"
                        
                # Ensure content field exists
                content = msg.get("content", msg.get("text", msg.get("message", "")))
                
                formatted.append({
                    "role": role,
                    "content": str(content),
                    "timestamp": msg.get("timestamp", msg.get("created_at", ""))
                })
            elif isinstance(msg, str):
                # Handle plain string messages (assume customer)
                formatted.append({
                    "role": "customer",
                    "content": msg,
                    "timestamp": ""
                })
                
        return formatted
        
    async def get_unified_predictions(self, conversation_id: str,
                                    messages: List[Dict[str, Any]],
                                    customer_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get all predictions in a unified response.
        
        Args:
            conversation_id: ID of the conversation
            messages: Conversation messages
            customer_profile: Customer profile data
            
        Returns:
            Unified prediction results from all services
        """
        try:
            # Run all predictions in parallel for efficiency
            import asyncio
            
            objection_task = self.predict_objections(conversation_id, messages, customer_profile)
            needs_task = self.predict_needs(conversation_id, messages, customer_profile)
            conversion_task = self.predict_conversion(conversation_id, messages, customer_profile)
            
            results = await asyncio.gather(
                objection_task,
                needs_task,
                conversion_task,
                return_exceptions=True
            )
            
            # Process results
            objection_result = results[0] if not isinstance(results[0], Exception) else {"objections": [], "error": str(results[0])}
            needs_result = results[1] if not isinstance(results[1], Exception) else {"needs": [], "error": str(results[1])}
            conversion_result = results[2] if not isinstance(results[2], Exception) else {"probability": 0.0, "error": str(results[2])}
            
            # Generate action recommendations based on all predictions
            recommended_actions = self._generate_unified_recommendations(
                objection_result,
                needs_result,
                conversion_result
            )
            
            return {
                "conversation_id": conversation_id,
                "objections_predicted": objection_result.get("objections", []),
                "needs_detected": needs_result.get("needs", []),
                "conversion_probability": conversion_result.get("probability", 0.0),
                "conversion_category": conversion_result.get("category", "low"),
                "recommended_actions": recommended_actions,
                "prediction_sources": {
                    "objections": objection_result.get("source", "ml"),
                    "needs": needs_result.get("source", "ml"),
                    "conversion": conversion_result.get("source", "ml")
                }
            }
            
        except Exception as e:
            logger.error(f"Error in unified predictions: {e}")
            return {
                "conversation_id": conversation_id,
                "objections_predicted": [],
                "needs_detected": [],
                "conversion_probability": 0.0,
                "conversion_category": "low",
                "recommended_actions": [],
                "error": str(e)
            }
            
    def _generate_unified_recommendations(self,
                                        objection_result: Dict[str, Any],
                                        needs_result: Dict[str, Any],
                                        conversion_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate unified action recommendations based on all predictions.
        
        Args:
            objection_result: Objection prediction results
            needs_result: Needs prediction results
            conversion_result: Conversion prediction results
            
        Returns:
            List of recommended actions
        """
        recommendations = []
        
        # Add conversion-based recommendations (highest priority)
        if conversion_result.get("recommendations"):
            recommendations.extend(conversion_result["recommendations"])
            
        # Add objection-handling recommendations
        for objection in objection_result.get("objections", [])[:2]:  # Top 2 objections
            if objection.get("confidence", 0) > 0.6:
                recommendations.append({
                    "action": f"handle_objection_{objection['type']}",
                    "description": f"Address {objection['type']} objection",
                    "priority": "high",
                    "suggested_response": objection.get("suggested_responses", [""])[0]
                })
                
        # Add need-fulfillment recommendations
        for need in needs_result.get("needs", [])[:2]:  # Top 2 needs
            if need.get("confidence", 0) > 0.5:
                actions = need.get("suggested_actions", [])
                if actions:
                    recommendations.append({
                        "action": f"fulfill_need_{need['category']}",
                        "description": f"Address {need['category']} need",
                        "priority": actions[0].get("priority", "medium"),
                        "specific_action": actions[0].get("action", "")
                    })
                    
        # Remove duplicates and sort by priority
        seen_actions = set()
        unique_recommendations = []
        
        for rec in recommendations:
            action = rec.get("action", "")
            if action not in seen_actions:
                seen_actions.add(action)
                unique_recommendations.append(rec)
                
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        unique_recommendations.sort(
            key=lambda x: priority_order.get(x.get("priority", "medium"), 1)
        )
        
        return unique_recommendations[:5]  # Return top 5 recommendations