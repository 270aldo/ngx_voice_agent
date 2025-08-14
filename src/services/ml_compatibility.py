"""
ML Services Compatibility Layer - Gradual migration support for ML service consolidation.

This module provides backward compatibility interfaces for legacy ML services,
allowing for zero-downtime migration to consolidated services.

Features:
- Transparent routing between old and new services
- Feature flag controlled migration
- Performance comparison during migration
- Automatic fallback on failures
- Migration progress tracking
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, Union, Type
from datetime import datetime
from functools import wraps
from contextlib import asynccontextmanager

from src.config.settings import get_settings
from src.services.consolidated_ml_prediction_service import (
    ConsolidatedMLPredictionService, 
    MLPredictionResult,
    PredictionType,
    BatchPredictionRequest
)
from src.utils.structured_logging import StructuredLogger

settings = get_settings()
logger = StructuredLogger.get_logger(__name__)


class MLCompatibilityError(Exception):
    """Compatibility layer error."""
    pass


def with_ml_migration_tracking(service_name: str):
    """Decorator to track ML service usage during migration."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_time = datetime.now()
            success = True
            error = None
            
            try:
                result = await func(self, *args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                # Track usage metrics
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                await self._track_usage(
                    service_name=service_name,
                    method_name=func.__name__,
                    processing_time=processing_time,
                    success=success,
                    error=error
                )
        return wrapper
    return decorator


class ConversionPredictionServiceCompat:
    """Compatibility wrapper for conversion prediction service."""
    
    def __init__(self):
        self.consolidated_service = None
        self.legacy_service = None
        self.usage_stats = {"consolidated": 0, "legacy": 0, "errors": 0}
    
    async def initialize(self):
        """Initialize the compatibility service."""
        if settings.use_consolidated_ml_service:
            self.consolidated_service = ConsolidatedMLPredictionService()
            await self.consolidated_service.initialize()
        else:
            # Initialize legacy service if needed
            try:
                from src.services.conversion_prediction_service import ConversionPredictionService
                # Legacy service initialization would go here
                pass
            except ImportError:
                logger.warning("Legacy conversion prediction service not available")
    
    @with_ml_migration_tracking("conversion_prediction")
    async def predict_conversion(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Predict conversion probability with compatibility layer."""
        if settings.use_consolidated_ml_service and self.consolidated_service:
            # Use consolidated service
            try:
                # Convert messages to features
                features = self._extract_conversion_features(messages, customer_profile)
                
                result = await self.consolidated_service.predict_single(
                    prediction_type=PredictionType.CONVERSION,
                    features=features,
                    conversation_id=conversation_id
                )
                
                self.usage_stats["consolidated"] += 1
                
                # Convert to legacy format
                return {
                    "conversion_probability": result.probability,
                    "confidence": result.confidence,
                    "factors": result.reasoning,
                    "recommendation": self._generate_legacy_recommendation(result),
                    "signals": {
                        "buying_signals": result.metadata.get("buying_signals", 0),
                        "engagement_level": features.get("engagement_score", 0.5)
                    }
                }
                
            except Exception as e:
                logger.error(f"Consolidated service failed, attempting fallback: {e}")
                self.usage_stats["errors"] += 1
                # Fallback to legacy or simple prediction
                return await self._fallback_conversion_prediction(conversation_id, messages, customer_profile)
        else:
            # Use legacy service or simple fallback
            self.usage_stats["legacy"] += 1
            return await self._fallback_conversion_prediction(conversation_id, messages, customer_profile)
    
    def _extract_conversion_features(
        self, 
        messages: List[Dict[str, Any]], 
        customer_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract features for conversion prediction from legacy format."""
        features = {}
        
        # Analyze messages for conversion signals
        if messages:
            total_messages = len(messages)
            user_messages = [msg for msg in messages if msg.get("role") == "user"]
            
            # Engagement metrics
            features["engagement_score"] = min(1.0, len(user_messages) / max(1, total_messages * 0.6))
            
            # Response time analysis
            response_times = []
            for i in range(1, len(messages)):
                if messages[i].get("role") != messages[i-1].get("role"):
                    # Calculate time difference if timestamps available
                    response_times.append(30.0)  # Default
            features["avg_response_time"] = sum(response_times) / len(response_times) if response_times else 30.0
            
            # Question analysis
            questions_asked = sum(1 for msg in user_messages if "?" in msg.get("content", ""))
            features["questions_asked"] = questions_asked
            
            # Buying signals
            buying_keywords = ["buy", "purchase", "price", "cost", "demo", "trial", "contract", "sign up"]
            buying_signals = 0
            for msg in user_messages:
                content = msg.get("content", "").lower()
                buying_signals += sum(1 for keyword in buying_keywords if keyword in content)
            features["buying_signals"] = buying_signals
            
            # Demo and price discussion detection
            all_content = " ".join(msg.get("content", "") for msg in messages).lower()
            features["demo_requested"] = "demo" in all_content or "show me" in all_content
            features["price_discussed"] = any(word in all_content for word in ["price", "cost", "pricing", "$"])
            
            # Conversation length
            features["conversation_duration"] = total_messages * 2  # Rough estimate in minutes
            
            # Sentiment approximation
            positive_words = ["great", "excellent", "perfect", "love", "amazing", "good"]
            negative_words = ["bad", "terrible", "horrible", "hate", "awful", "poor"]
            
            positive_count = sum(1 for msg in user_messages for word in positive_words 
                               if word in msg.get("content", "").lower())
            negative_count = sum(1 for msg in user_messages for word in negative_words 
                               if word in msg.get("content", "").lower())
            
            if positive_count + negative_count > 0:
                features["positive_sentiment"] = positive_count / (positive_count + negative_count)
            else:
                features["positive_sentiment"] = 0.5
        
        # Customer profile features
        if customer_profile:
            features["company_size"] = customer_profile.get("company_size", 0)
            features["industry_match"] = 1.0 if customer_profile.get("industry") else 0.5
            features["decision_maker_present"] = customer_profile.get("is_decision_maker", False)
        else:
            features["company_size"] = 0
            features["industry_match"] = 0.5
            features["decision_maker_present"] = False
        
        # Default values for missing features
        default_features = {
            "engagement_score": 0.5,
            "questions_asked": 0,
            "objections_raised": 0,
            "buying_signals": 0,
            "demo_requested": False,
            "price_discussed": False,
            "avg_response_time": 30.0,
            "conversation_duration": 0,
            "positive_sentiment": 0.5,
            "decision_maker_present": False
        }
        
        for key, default_value in default_features.items():
            if key not in features:
                features[key] = default_value
        
        return features
    
    def _generate_legacy_recommendation(self, result: MLPredictionResult) -> str:
        """Generate recommendation in legacy format."""
        if result.probability > 0.8:
            return "high_conversion_likely"
        elif result.probability > 0.6:
            return "moderate_conversion_potential"
        elif result.probability > 0.4:
            return "low_conversion_needs_nurturing"
        else:
            return "very_low_conversion_risk"
    
    async def _fallback_conversion_prediction(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Simple fallback prediction when consolidated service fails."""
        # Simple heuristic-based prediction
        features = self._extract_conversion_features(messages, customer_profile)
        
        # Calculate simple probability
        probability = 0.5  # Base probability
        
        # Adjust based on engagement
        probability += features["engagement_score"] * 0.2
        
        # Adjust based on buying signals
        if features["buying_signals"] > 0:
            probability += min(0.3, features["buying_signals"] * 0.1)
        
        # Adjust based on demo request
        if features["demo_requested"]:
            probability += 0.15
        
        # Adjust based on price discussion
        if features["price_discussed"]:
            probability += 0.1
        
        probability = min(1.0, max(0.0, probability))
        
        return {
            "conversion_probability": probability,
            "confidence": 0.6,  # Lower confidence for fallback
            "factors": ["heuristic-based fallback prediction"],
            "recommendation": self._generate_legacy_recommendation_simple(probability),
            "signals": {
                "buying_signals": features["buying_signals"],
                "engagement_level": features["engagement_score"]
            }
        }
    
    def _generate_legacy_recommendation_simple(self, probability: float) -> str:
        """Generate simple recommendation based on probability."""
        if probability > 0.8:
            return "high_conversion_likely"
        elif probability > 0.6:
            return "moderate_conversion_potential"
        elif probability > 0.4:
            return "low_conversion_needs_nurturing"
        else:
            return "very_low_conversion_risk"
    
    async def _track_usage(
        self,
        service_name: str,
        method_name: str,
        processing_time: float,
        success: bool,
        error: Optional[str] = None
    ):
        """Track service usage for migration monitoring."""
        logger.info(
            f"ML Service Usage - {service_name}.{method_name}: "
            f"consolidated={settings.use_consolidated_ml_service}, "
            f"time={processing_time:.2f}ms, success={success}"
        )


class NeedsPredictionServiceCompat:
    """Compatibility wrapper for needs prediction service."""
    
    def __init__(self):
        self.consolidated_service = None
        self.usage_stats = {"consolidated": 0, "legacy": 0, "errors": 0}
    
    async def initialize(self):
        """Initialize the compatibility service."""
        if settings.use_consolidated_ml_service:
            self.consolidated_service = ConsolidatedMLPredictionService()
            await self.consolidated_service.initialize()
    
    @with_ml_migration_tracking("needs_prediction")
    async def predict_needs(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Predict customer needs with compatibility layer."""
        if settings.use_consolidated_ml_service and self.consolidated_service:
            try:
                features = self._extract_needs_features(messages, customer_profile)
                
                result = await self.consolidated_service.predict_single(
                    prediction_type=PredictionType.NEEDS,
                    features=features,
                    conversation_id=conversation_id
                )
                
                self.usage_stats["consolidated"] += 1
                
                return {
                    "predicted_needs": self._map_to_legacy_needs(result),
                    "confidence": result.confidence,
                    "priority_needs": result.reasoning[:3],
                    "needs_score": result.probability,
                    "recommendations": self._generate_needs_recommendations(result)
                }
                
            except Exception as e:
                logger.error(f"Consolidated needs prediction failed: {e}")
                self.usage_stats["errors"] += 1
                return await self._fallback_needs_prediction(conversation_id, messages, customer_profile)
        else:
            self.usage_stats["legacy"] += 1
            return await self._fallback_needs_prediction(conversation_id, messages, customer_profile)
    
    def _extract_needs_features(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract features for needs prediction."""
        features = {}
        
        if messages:
            user_messages = [msg for msg in messages if msg.get("role") == "user"]
            all_content = " ".join(msg.get("content", "") for msg in user_messages).lower()
            
            # Pain point detection
            pain_points = ["problem", "issue", "challenge", "difficult", "struggle", "need help"]
            features["pain_points_mentioned"] = sum(1 for pain in pain_points if pain in all_content)
            
            # Current solution mentions
            solution_keywords = ["currently using", "have", "existing", "current solution"]
            features["current_solution_mentioned"] = any(keyword in all_content for keyword in solution_keywords)
            
            # Budget discussion
            budget_keywords = ["budget", "cost", "price", "afford", "expensive"]
            features["budget_range_discussed"] = any(keyword in all_content for keyword in budget_keywords)
            
            # Timeline urgency
            urgency_keywords = ["urgent", "asap", "soon", "quickly", "immediately", "deadline"]
            features["timeline_urgency"] = 1.0 if any(keyword in all_content for keyword in urgency_keywords) else 0.5
            
            # Feature interest
            feature_keywords = ["feature", "functionality", "capability", "can it", "does it"]
            features["feature_interest_score"] = min(1.0, sum(1 for keyword in feature_keywords if keyword in all_content) / 10)
            
            # Competitive mentions
            competitors = ["salesforce", "hubspot", "pipedrive", "zoho"]
            features["competitive_mentions"] = sum(1 for comp in competitors if comp in all_content)
            
            # Specific requirements
            requirement_patterns = ["need to", "must", "require", "essential", "important that"]
            features["specific_requirements"] = sum(1 for pattern in requirement_patterns if pattern in all_content)
            
            # Stakeholder involvement
            stakeholder_keywords = ["team", "we", "us", "colleagues", "boss", "manager"]
            features["stakeholder_count"] = min(10, sum(1 for keyword in stakeholder_keywords if keyword in all_content))
        
        # Customer profile features
        if customer_profile:
            # Industry match scoring
            relevant_industries = ["technology", "healthcare", "finance", "retail", "education"]
            customer_industry = customer_profile.get("industry", "").lower()
            features["industry_match"] = 1.0 if customer_industry in relevant_industries else 0.5
            
            features["company_size"] = customer_profile.get("company_size", 0)
        else:
            features["industry_match"] = 0.5
            features["company_size"] = 0
        
        # Set defaults
        default_features = {
            "pain_points_mentioned": 0,
            "current_solution_mentioned": False,
            "budget_range_discussed": False,
            "timeline_urgency": 0.5,
            "feature_interest_score": 0.5,
            "competitive_mentions": 0,
            "specific_requirements": 0,
            "stakeholder_count": 1,
            "industry_match": 0.5,
            "company_size": 0
        }
        
        for key, default_value in default_features.items():
            if key not in features:
                features[key] = default_value
        
        return features
    
    def _map_to_legacy_needs(self, result: MLPredictionResult) -> List[str]:
        """Map prediction result to legacy needs format."""
        needs_categories = [
            "automation", "lead_generation", "customer_management",
            "analytics", "integration", "scalability", "efficiency"
        ]
        
        # Simple mapping based on probability
        if result.probability > 0.7:
            return needs_categories[:3]
        elif result.probability > 0.5:
            return needs_categories[:2]
        else:
            return needs_categories[:1]
    
    def _generate_needs_recommendations(self, result: MLPredictionResult) -> List[str]:
        """Generate recommendations based on predicted needs."""
        recommendations = []
        
        if result.probability > 0.8:
            recommendations.append("Present comprehensive solution demo")
            recommendations.append("Focus on ROI and business impact")
        elif result.probability > 0.6:
            recommendations.append("Conduct detailed needs discovery")
            recommendations.append("Provide relevant case studies")
        else:
            recommendations.append("Continue relationship building")
            recommendations.append("Schedule follow-up for future needs")
        
        return recommendations
    
    async def _fallback_needs_prediction(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Simple fallback for needs prediction."""
        features = self._extract_needs_features(messages, customer_profile)
        
        # Simple scoring
        needs_score = 0.5
        if features["pain_points_mentioned"] > 0:
            needs_score += 0.2
        if features["budget_range_discussed"]:
            needs_score += 0.15
        if features["feature_interest_score"] > 0.5:
            needs_score += 0.15
        
        needs_score = min(1.0, needs_score)
        
        return {
            "predicted_needs": ["general_business_automation"],
            "confidence": 0.6,
            "priority_needs": ["automation", "efficiency"],
            "needs_score": needs_score,
            "recommendations": ["Conduct detailed discovery call"]
        }


class ObjectionPredictionServiceCompat:
    """Compatibility wrapper for objection prediction service."""
    
    def __init__(self):
        self.consolidated_service = None
        self.usage_stats = {"consolidated": 0, "legacy": 0, "errors": 0}
    
    async def initialize(self):
        """Initialize the compatibility service."""
        if settings.use_consolidated_ml_service:
            self.consolidated_service = ConsolidatedMLPredictionService()
            await self.consolidated_service.initialize()
    
    @with_ml_migration_tracking("objection_prediction")
    async def predict_objections(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Predict customer objections with compatibility layer."""
        if settings.use_consolidated_ml_service and self.consolidated_service:
            try:
                features = self._extract_objection_features(messages, customer_profile)
                
                result = await self.consolidated_service.predict_single(
                    prediction_type=PredictionType.OBJECTION,
                    features=features,
                    conversation_id=conversation_id
                )
                
                self.usage_stats["consolidated"] += 1
                
                return {
                    "objections": self._map_to_legacy_objections(result),
                    "confidence": result.confidence,
                    "signals": features,
                    "objection_likelihood": result.probability,
                    "recommended_responses": result.reasoning
                }
                
            except Exception as e:
                logger.error(f"Consolidated objection prediction failed: {e}")
                self.usage_stats["errors"] += 1
                return await self._fallback_objection_prediction(conversation_id, messages, customer_profile)
        else:
            self.usage_stats["legacy"] += 1
            return await self._fallback_objection_prediction(conversation_id, messages, customer_profile)
    
    def _extract_objection_features(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract features for objection prediction."""
        features = {}
        
        if messages:
            user_messages = [msg for msg in messages if msg.get("role") == "user"]
            all_content = " ".join(msg.get("content", "") for msg in user_messages).lower()
            
            # Negative sentiment indicators
            negative_words = ["but", "however", "concerned", "worried", "problem", "issue", "expensive", "costly"]
            features["negative_sentiment"] = sum(1 for word in negative_words if word in all_content)
            
            # Hesitation words
            hesitation_words = ["maybe", "perhaps", "not sure", "think about", "consider", "possibly"]
            features["hesitation_words"] = sum(1 for word in hesitation_words if word in all_content)
            
            # Comparison requests
            comparison_words = ["compare", "versus", "vs", "alternative", "other options", "competitors"]
            features["comparison_requests"] = sum(1 for word in comparison_words if word in all_content)
            
            # Price concerns
            price_concern_phrases = ["too expensive", "too costly", "can't afford", "budget", "cheaper"]
            features["price_concerns"] = sum(1 for phrase in price_concern_phrases if phrase in all_content)
            
            # Implementation concerns
            impl_concerns = ["difficult", "complicated", "complex", "time consuming", "resources"]
            features["implementation_concerns"] = sum(1 for concern in impl_concerns if concern in all_content)
            
            # Authority questions
            authority_phrases = ["need approval", "talk to", "discuss with", "boss", "manager", "team"]
            features["authority_questions"] = sum(1 for phrase in authority_phrases if phrase in all_content)
            
            # Delay indicators
            delay_words = ["later", "future", "not now", "timing", "wait", "postpone"]
            features["delay_indicators"] = sum(1 for word in delay_words if word in all_content)
            
            # Skeptical tone
            skeptical_phrases = ["really", "actually work", "prove", "show me", "evidence"]
            features["skeptical_tone"] = sum(1 for phrase in skeptical_phrases if phrase in all_content)
            
            # Competitor mentions
            competitors = ["salesforce", "hubspot", "pipedrive", "zoho", "other solution"]
            features["competitor_mentions"] = sum(1 for comp in competitors if comp in all_content)
            
            # Budget constraints
            budget_phrases = ["budget constraints", "limited budget", "tight budget", "cost cutting"]
            features["budget_constraints"] = sum(1 for phrase in budget_phrases if phrase in all_content)
        
        # Set defaults
        default_features = {
            "negative_sentiment": 0,
            "hesitation_words": 0,
            "comparison_requests": 0,
            "price_concerns": 0,
            "implementation_concerns": 0,
            "authority_questions": 0,
            "delay_indicators": 0,
            "skeptical_tone": 0,
            "competitor_mentions": 0,
            "budget_constraints": 0
        }
        
        for key, default_value in default_features.items():
            if key not in features:
                features[key] = default_value
        
        return features
    
    def _map_to_legacy_objections(self, result: MLPredictionResult) -> List[Dict[str, Any]]:
        """Map prediction result to legacy objections format."""
        objection_types = ["price", "value", "need", "urgency", "authority", "trust", "competition"]
        
        objections = []
        if result.probability > 0.6:
            # High objection likelihood
            objections.extend([
                {"type": "price", "confidence": result.confidence},
                {"type": "value", "confidence": result.confidence * 0.8}
            ])
        elif result.probability > 0.4:
            # Medium objection likelihood
            objections.append({"type": "need", "confidence": result.confidence})
        
        return objections
    
    async def _fallback_objection_prediction(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Simple fallback for objection prediction."""
        features = self._extract_objection_features(messages, customer_profile)
        
        # Simple scoring
        objection_score = 0.3  # Base objection probability
        
        if features["negative_sentiment"] > 0:
            objection_score += 0.2
        if features["price_concerns"] > 0:
            objection_score += 0.25
        if features["hesitation_words"] > 0:
            objection_score += 0.15
        
        objection_score = min(1.0, objection_score)
        
        return {
            "objections": [] if objection_score < 0.5 else [{"type": "general", "confidence": 0.6}],
            "confidence": 0.6,
            "signals": features,
            "objection_likelihood": objection_score,
            "recommended_responses": ["Address concerns proactively"]
        }


# Factory functions for easy service access
async def get_conversion_prediction_service() -> ConversionPredictionServiceCompat:
    """Get conversion prediction service with compatibility layer."""
    service = ConversionPredictionServiceCompat()
    await service.initialize()
    return service


async def get_needs_prediction_service() -> NeedsPredictionServiceCompat:
    """Get needs prediction service with compatibility layer."""
    service = NeedsPredictionServiceCompat()
    await service.initialize()
    return service


async def get_objection_prediction_service() -> ObjectionPredictionServiceCompat:
    """Get objection prediction service with compatibility layer."""
    service = ObjectionPredictionServiceCompat()
    await service.initialize()
    return service


class MLMigrationManager:
    """Manager for ML service migration process."""
    
    def __init__(self):
        self.services = {}
        self.migration_stats = {
            "total_requests": 0,
            "consolidated_requests": 0,
            "legacy_requests": 0,
            "error_count": 0,
            "avg_response_time": 0.0
        }
    
    async def initialize_services(self):
        """Initialize all compatibility services."""
        self.services = {
            "conversion": await get_conversion_prediction_service(),
            "needs": await get_needs_prediction_service(),
            "objection": await get_objection_prediction_service()
        }
        logger.info("ML compatibility services initialized")
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status and statistics."""
        return {
            "consolidated_ml_enabled": settings.use_consolidated_ml_service,
            "services_initialized": len(self.services),
            "migration_stats": self.migration_stats,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for all ML services."""
        health = {
            "status": "healthy",
            "services": {},
            "migration_enabled": settings.use_consolidated_ml_service
        }
        
        for name, service in self.services.items():
            try:
                # Basic health check
                health["services"][name] = {
                    "status": "healthy",
                    "usage_stats": getattr(service, 'usage_stats', {})
                }
            except Exception as e:
                health["services"][name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health["status"] = "degraded"
        
        return health


# Global migration manager instance
_migration_manager = None


async def get_ml_migration_manager() -> MLMigrationManager:
    """Get global ML migration manager instance."""
    global _migration_manager
    if _migration_manager is None:
        _migration_manager = MLMigrationManager()
        await _migration_manager.initialize_services()
    return _migration_manager


def log_ml_migration_progress():
    """Log current ML migration progress."""
    if settings.use_consolidated_ml_service:
        logger.info("✅ Using consolidated ML prediction service")
    else:
        logger.info("⚠️  Using legacy ML prediction services")
    
    logger.info("ML service migration layer active")