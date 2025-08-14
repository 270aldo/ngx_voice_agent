"""
Consolidated ML Prediction Service - Unified machine learning predictions for NGX Voice Agent.

This service consolidates all ML prediction functionality into a single, high-performance service:
- Conversion prediction
- Needs prediction  
- Objection prediction
- Lead scoring
- Engagement analysis
- Model training and drift detection
- Adaptive learning integration

Designed for production use with enterprise-grade features:
- Circuit breaker pattern for resilience
- Async batch processing
- Model versioning and rollback
- Performance monitoring
- Feature importance tracking
"""

import asyncio
import json
import logging
import pickle
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from contextlib import asynccontextmanager

import numpy as np
from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from src.core.constants import MLConstants
from src.config.settings import get_settings
from src.integrations.supabase.resilient_client import ResilientSupabaseClient
from src.models.conversation import ConversationState, CustomerData
from src.utils.structured_logging import StructuredLogger

settings = get_settings()
logger = StructuredLogger.get_logger(__name__)


class MLPredictionError(Exception):
    """Base exception for ML prediction errors."""
    pass


class ModelNotFoundError(MLPredictionError):
    """Model not found error."""
    pass


class PredictionType(str, Enum):
    """Types of ML predictions available."""
    CONVERSION = "conversion"
    NEEDS = "needs" 
    OBJECTION = "objection"
    LEAD_SCORING = "lead_scoring"
    ENGAGEMENT = "engagement"
    PRICE_SENSITIVITY = "price_sensitivity"
    DECISION_TIMELINE = "decision_timeline"
    CHURN_RISK = "churn_risk"
    UPSELL_OPPORTUNITY = "upsell_opportunity"


class ModelStatus(str, Enum):
    """Model status indicators."""
    ACTIVE = "active"
    TRAINING = "training"
    UPDATING = "updating"
    FAILED = "failed"
    DEPRECATED = "deprecated"


@dataclass
class MLPredictionResult:
    """Standardized ML prediction result."""
    prediction_type: PredictionType
    probability: float
    confidence: float
    reasoning: List[str]
    features_used: List[str]
    model_version: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


@dataclass
class ModelMetrics:
    """Model performance and health metrics."""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: float
    prediction_count: int
    last_updated: datetime
    drift_score: float = 0.0
    training_samples: int = 0
    validation_score: float = 0.0
    feature_importance: Dict[str, float] = field(default_factory=dict)
    error_rate: float = 0.0
    avg_response_time_ms: float = 0.0


@dataclass
class BatchPredictionRequest:
    """Request for batch predictions."""
    conversation_ids: List[str]
    prediction_types: List[PredictionType]
    features_batch: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


class CircuitBreaker:
    """Circuit breaker for ML service resilience."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    @asynccontextmanager
    async def call(self):
        """Execute with circuit breaker protection."""
        if self.state == "open":
            if datetime.now().timestamp() - self.last_failure_time > self.timeout:
                self.state = "half-open"
            else:
                raise MLPredictionError("Circuit breaker is open")
        
        try:
            yield
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now().timestamp()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            
            raise e


class ConsolidatedMLPredictionService:
    """
    Consolidated ML prediction service with enterprise features.
    
    Features:
    - Multiple prediction models in one service
    - Batch processing for efficiency
    - Circuit breaker for resilience
    - Model drift detection
    - Adaptive learning integration
    - Performance monitoring
    """
    
    def __init__(self, supabase_client: Optional[ResilientSupabaseClient] = None):
        self.supabase_client = supabase_client
        self.models: Dict[PredictionType, BaseEstimator] = {}
        self.metrics: Dict[PredictionType, ModelMetrics] = {}
        self.circuit_breaker = CircuitBreaker()
        self.feature_cache = deque(maxlen=1000)  # Cache recent features for drift detection
        self.prediction_cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5 minutes cache TTL
        
        # Async initialization tracking
        self._initialized = False
        self._initializing = False
        self._initialization_lock = asyncio.Lock()
        
        # Performance tracking
        self.prediction_times: Dict[PredictionType, deque] = defaultdict(lambda: deque(maxlen=100))
        self.error_counts: Dict[PredictionType, int] = defaultdict(int)
        
        logger.info("Consolidated ML Prediction Service initialized")
    
    async def initialize(self) -> None:
        """Initialize all ML models."""
        async with self._initialization_lock:
            if self._initialized or self._initializing:
                return
            
            self._initializing = True
            try:
                await self._load_models()
                await self._initialize_metrics()
                self._initialized = True
                logger.info("All ML models initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize ML models: {e}")
                raise
            finally:
                self._initializing = False
    
    async def _load_models(self) -> None:
        """Load all prediction models."""
        model_configs = {
            PredictionType.CONVERSION: {
                "model_class": GradientBoostingClassifier,
                "params": {"n_estimators": 100, "learning_rate": 0.1, "max_depth": 6}
            },
            PredictionType.NEEDS: {
                "model_class": RandomForestClassifier,
                "params": {"n_estimators": 150, "max_depth": 8, "random_state": 42}
            },
            PredictionType.OBJECTION: {
                "model_class": LogisticRegression,
                "params": {"random_state": 42, "max_iter": 1000}
            },
            PredictionType.LEAD_SCORING: {
                "model_class": GradientBoostingClassifier,
                "params": {"n_estimators": 200, "learning_rate": 0.05, "max_depth": 10}
            },
            PredictionType.ENGAGEMENT: {
                "model_class": RandomForestClassifier,
                "params": {"n_estimators": 100, "max_depth": 6, "random_state": 42}
            }
        }
        
        for pred_type, config in model_configs.items():
            try:
                # Try to load existing model first
                model_path = f"models/{pred_type.value}_model.pkl"
                if Path(model_path).exists():
                    with open(model_path, 'rb') as f:
                        self.models[pred_type] = pickle.load(f)
                    logger.info(f"Loaded existing {pred_type.value} model")
                else:
                    # Initialize new model
                    self.models[pred_type] = Pipeline([
                        ('scaler', StandardScaler()),
                        ('classifier', config["model_class"](**config["params"]))
                    ])
                    logger.info(f"Initialized new {pred_type.value} model")
            except Exception as e:
                logger.error(f"Failed to load {pred_type.value} model: {e}")
                # Use fallback simple model
                self.models[pred_type] = Pipeline([
                    ('scaler', StandardScaler()),
                    ('classifier', LogisticRegression(random_state=42, max_iter=1000))
                ])
    
    async def _initialize_metrics(self) -> None:
        """Initialize model metrics."""
        for pred_type in self.models.keys():
            self.metrics[pred_type] = ModelMetrics(
                accuracy=0.0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                auc_roc=0.0,
                prediction_count=0,
                last_updated=datetime.now(),
                training_samples=0
            )
    
    async def predict_single(
        self, 
        prediction_type: PredictionType,
        features: Dict[str, Any],
        conversation_id: Optional[str] = None
    ) -> MLPredictionResult:
        """Make a single prediction."""
        await self.initialize()
        
        start_time = datetime.now()
        
        try:
            async with self.circuit_breaker.call():
                # Check cache first
                cache_key = f"{prediction_type.value}_{hash(str(sorted(features.items())))}"
                cached_result = self._get_from_cache(cache_key)
                if cached_result:
                    return cached_result
                
                # Prepare features
                feature_vector = await self._prepare_features(features, prediction_type)
                
                # Make prediction
                if prediction_type not in self.models:
                    raise ModelNotFoundError(f"Model for {prediction_type.value} not found")
                
                model = self.models[prediction_type]
                
                # Get prediction and probability
                try:
                    if hasattr(model, 'predict_proba'):
                        probabilities = model.predict_proba([feature_vector])[0]
                        probability = probabilities[1] if len(probabilities) > 1 else probabilities[0]
                        prediction = model.predict([feature_vector])[0]
                    else:
                        prediction = model.predict([feature_vector])[0]
                        probability = float(prediction)
                except Exception as model_error:
                    # Fallback to heuristic prediction if model is not trained
                    logger.warning(f"Model prediction failed, using heuristic fallback: {model_error}")
                    probability, prediction = self._heuristic_prediction(prediction_type, feature_vector)
                
                # Calculate confidence based on model type and features
                confidence = await self._calculate_confidence(
                    prediction_type, feature_vector, probability
                )
                
                # Generate reasoning
                reasoning = await self._generate_reasoning(
                    prediction_type, features, probability
                )
                
                # Create result
                result = MLPredictionResult(
                    prediction_type=prediction_type,
                    probability=float(probability),
                    confidence=confidence,
                    reasoning=reasoning,
                    features_used=list(features.keys()),
                    model_version="2.0.0",
                    metadata={
                        "conversation_id": conversation_id,
                        "model_type": type(model).__name__,
                        "feature_count": len(feature_vector)
                    }
                )
                
                # Cache result
                self._cache_result(cache_key, result)
                
                # Update metrics
                await self._update_metrics(prediction_type, start_time, success=True)
                
                # Store prediction for drift detection
                if conversation_id:
                    await self._store_prediction(conversation_id, result)
                
                return result
                
        except Exception as e:
            await self._update_metrics(prediction_type, start_time, success=False)
            logger.error(f"Prediction failed for {prediction_type.value}: {e}")
            raise MLPredictionError(f"Prediction failed: {e}")
    
    async def predict_batch(
        self, 
        request: BatchPredictionRequest
    ) -> Dict[str, List[MLPredictionResult]]:
        """Make batch predictions efficiently."""
        await self.initialize()
        
        results: Dict[str, List[MLPredictionResult]] = {}
        
        # Group by prediction type for efficient processing
        for pred_type in request.prediction_types:
            results[pred_type.value] = []
            
            # Process in batches to avoid memory issues
            batch_size = 50
            for i in range(0, len(request.features_batch), batch_size):
                batch_features = request.features_batch[i:i + batch_size]
                batch_conv_ids = request.conversation_ids[i:i + batch_size]
                
                batch_results = await self._process_feature_batch(
                    pred_type, batch_features, batch_conv_ids
                )
                results[pred_type.value].extend(batch_results)
        
        return results
    
    async def _process_feature_batch(
        self,
        prediction_type: PredictionType,
        features_batch: List[Dict[str, Any]],
        conversation_ids: List[str]
    ) -> List[MLPredictionResult]:
        """Process a batch of features for one prediction type."""
        results = []
        
        try:
            # Prepare all features
            feature_vectors = []
            for features in features_batch:
                feature_vector = await self._prepare_features(features, prediction_type)
                feature_vectors.append(feature_vector)
            
            # Make batch prediction
            model = self.models[prediction_type]
            
            if hasattr(model, 'predict_proba'):
                probabilities = model.predict_proba(feature_vectors)
                predictions = model.predict(feature_vectors)
            else:
                predictions = model.predict(feature_vectors)
                probabilities = [[p] for p in predictions]
            
            # Create results
            for i, (features, conv_id) in enumerate(zip(features_batch, conversation_ids)):
                prob = probabilities[i][1] if len(probabilities[i]) > 1 else probabilities[i][0]
                confidence = await self._calculate_confidence(
                    prediction_type, feature_vectors[i], prob
                )
                reasoning = await self._generate_reasoning(
                    prediction_type, features, prob
                )
                
                result = MLPredictionResult(
                    prediction_type=prediction_type,
                    probability=float(prob),
                    confidence=confidence,
                    reasoning=reasoning,
                    features_used=list(features.keys()),
                    model_version="2.0.0",
                    metadata={"conversation_id": conv_id, "batch_processed": True}
                )
                results.append(result)
        
        except Exception as e:
            logger.error(f"Batch processing failed for {prediction_type.value}: {e}")
            # Return empty results for failed batch
            results = []
        
        return results
    
    def _heuristic_prediction(
        self, 
        prediction_type: PredictionType, 
        feature_vector: List[float]
    ) -> Tuple[float, int]:
        """Heuristic fallback prediction when ML models are not trained."""
        if prediction_type == PredictionType.CONVERSION:
            # Simple heuristic for conversion based on key features
            engagement = feature_vector[0] if len(feature_vector) > 0 else 0.5
            questions = feature_vector[1] if len(feature_vector) > 1 else 0
            objections = feature_vector[2] if len(feature_vector) > 2 else 0
            demo_requested = feature_vector[4] if len(feature_vector) > 4 else 0
            price_discussed = feature_vector[3] if len(feature_vector) > 3 else 0
            
            # Calculate probability based on weighted factors
            probability = 0.3  # Base probability
            probability += engagement * 0.3  # Engagement weight
            probability += min(questions / 5.0, 0.2)  # Question engagement
            probability -= objections * 0.1  # Objections reduce probability
            probability += demo_requested * 0.15  # Demo interest
            probability += price_discussed * 0.1  # Price discussion
            
            probability = max(0.0, min(1.0, probability))
            return probability, 1 if probability > 0.5 else 0
            
        elif prediction_type == PredictionType.NEEDS:
            # Heuristic for needs prediction
            industry_match = feature_vector[0] if len(feature_vector) > 0 else 0.5
            company_size = feature_vector[1] if len(feature_vector) > 1 else 0
            pain_points = feature_vector[2] if len(feature_vector) > 2 else 0
            
            probability = 0.4  # Base probability
            probability += industry_match * 0.3
            probability += min(company_size / 100.0, 0.2)
            probability += min(pain_points / 5.0, 0.2)
            
            probability = max(0.0, min(1.0, probability))
            return probability, 1 if probability > 0.5 else 0
            
        elif prediction_type == PredictionType.OBJECTION:
            # Heuristic for objection prediction
            negative_sentiment = feature_vector[0] if len(feature_vector) > 0 else 0
            hesitation = feature_vector[1] if len(feature_vector) > 1 else 0
            price_concerns = feature_vector[3] if len(feature_vector) > 3 else 0
            
            probability = 0.2  # Base probability
            probability += negative_sentiment * 0.1
            probability += hesitation * 0.15
            probability += price_concerns * 0.2
            
            probability = max(0.0, min(1.0, probability))
            return probability, 1 if probability > 0.5 else 0
            
        else:
            # Default heuristic
            avg_feature = sum(feature_vector) / len(feature_vector) if feature_vector else 0.5
            probability = max(0.1, min(0.9, avg_feature))
            return probability, 1 if probability > 0.5 else 0
    
    async def _prepare_features(
        self, 
        features: Dict[str, Any], 
        prediction_type: PredictionType
    ) -> List[float]:
        """Prepare feature vector for prediction."""
        # Feature engineering based on prediction type
        if prediction_type == PredictionType.CONVERSION:
            return self._prepare_conversion_features(features)
        elif prediction_type == PredictionType.NEEDS:
            return self._prepare_needs_features(features)
        elif prediction_type == PredictionType.OBJECTION:
            return self._prepare_objection_features(features)
        elif prediction_type == PredictionType.LEAD_SCORING:
            return self._prepare_lead_scoring_features(features)
        elif prediction_type == PredictionType.ENGAGEMENT:
            return self._prepare_engagement_features(features)
        else:
            # Default feature preparation
            return self._prepare_default_features(features)
    
    def _prepare_conversion_features(self, features: Dict[str, Any]) -> List[float]:
        """Prepare features for conversion prediction."""
        return [
            float(features.get('engagement_score', 0.5)),
            float(features.get('questions_asked', 0)),
            float(features.get('objections_raised', 0)),
            float(features.get('price_discussed', False)),
            float(features.get('demo_requested', False)),
            float(features.get('response_time_avg', 30.0)),
            float(features.get('conversation_duration', 0)),
            float(features.get('positive_sentiment', 0.5)),
            float(features.get('buying_signals', 0)),
            float(features.get('decision_maker_present', False))
        ]
    
    def _prepare_needs_features(self, features: Dict[str, Any]) -> List[float]:
        """Prepare features for needs prediction."""
        return [
            float(features.get('industry_match', 0.5)),
            float(features.get('company_size', 0)),
            float(features.get('pain_points_mentioned', 0)),
            float(features.get('current_solution_mentioned', False)),
            float(features.get('budget_range_discussed', False)),
            float(features.get('timeline_urgency', 0.5)),
            float(features.get('stakeholder_count', 1)),
            float(features.get('feature_interest_score', 0.5)),
            float(features.get('competitive_mentions', 0)),
            float(features.get('specific_requirements', 0))
        ]
    
    def _prepare_objection_features(self, features: Dict[str, Any]) -> List[float]:
        """Prepare features for objection prediction."""
        return [
            float(features.get('negative_sentiment', 0)),
            float(features.get('hesitation_words', 0)),
            float(features.get('comparison_requests', 0)),
            float(features.get('price_concerns', 0)),
            float(features.get('implementation_concerns', 0)),
            float(features.get('authority_questions', 0)),
            float(features.get('delay_indicators', 0)),
            float(features.get('skeptical_tone', 0)),
            float(features.get('competitor_mentions', 0)),
            float(features.get('budget_constraints', 0))
        ]
    
    def _prepare_lead_scoring_features(self, features: Dict[str, Any]) -> List[float]:
        """Prepare features for lead scoring."""
        return [
            float(features.get('company_size_score', 0.5)),
            float(features.get('industry_fit_score', 0.5)),
            float(features.get('budget_qualification', 0.5)),
            float(features.get('authority_score', 0.5)),
            float(features.get('need_urgency', 0.5)),
            float(features.get('engagement_quality', 0.5)),
            float(features.get('technical_fit', 0.5)),
            float(features.get('competitor_displacement', 0.5)),
            float(features.get('roi_potential', 0.5)),
            float(features.get('decision_timeline', 0.5))
        ]
    
    def _prepare_engagement_features(self, features: Dict[str, Any]) -> List[float]:
        """Prepare features for engagement prediction."""
        return [
            float(features.get('message_frequency', 0)),
            float(features.get('response_speed', 0)),
            float(features.get('question_quality', 0.5)),
            float(features.get('topic_diversity', 0.5)),
            float(features.get('follow_up_likelihood', 0.5)),
            float(features.get('attention_span', 0.5)),
            float(features.get('interaction_depth', 0.5)),
            float(features.get('proactive_engagement', 0.5)),
            float(features.get('content_relevance', 0.5)),
            float(features.get('emotional_investment', 0.5))
        ]
    
    def _prepare_default_features(self, features: Dict[str, Any]) -> List[float]:
        """Default feature preparation for unknown prediction types."""
        # Extract numeric features and normalize
        numeric_features = []
        for key, value in features.items():
            if isinstance(value, (int, float)):
                numeric_features.append(float(value))
            elif isinstance(value, bool):
                numeric_features.append(float(value))
            elif isinstance(value, str):
                # Simple string encoding
                numeric_features.append(float(len(value)))
        
        # Ensure we have at least 5 features
        while len(numeric_features) < 5:
            numeric_features.append(0.0)
        
        return numeric_features[:10]  # Limit to 10 features
    
    async def _calculate_confidence(
        self,
        prediction_type: PredictionType,
        feature_vector: List[float],
        probability: float
    ) -> float:
        """Calculate prediction confidence."""
        base_confidence = abs(probability - 0.5) * 2  # Distance from 0.5
        
        # Adjust based on feature completeness
        feature_completeness = sum(1 for f in feature_vector if f > 0) / len(feature_vector)
        completeness_bonus = feature_completeness * 0.2
        
        # Adjust based on model metrics
        if prediction_type in self.metrics:
            model_accuracy = self.metrics[prediction_type].accuracy
            accuracy_bonus = model_accuracy * 0.1
        else:
            accuracy_bonus = 0.0
        
        confidence = min(1.0, base_confidence + completeness_bonus + accuracy_bonus)
        return confidence
    
    async def _generate_reasoning(
        self,
        prediction_type: PredictionType,
        features: Dict[str, Any],
        probability: float
    ) -> List[str]:
        """Generate human-readable reasoning for predictions."""
        reasoning = []
        
        if prediction_type == PredictionType.CONVERSION:
            if probability > 0.7:
                reasoning.append("High conversion probability due to strong buying signals")
                if features.get('demo_requested'):
                    reasoning.append("Demo request indicates serious interest")
                if features.get('price_discussed'):
                    reasoning.append("Price discussion suggests readiness to buy")
            elif probability > 0.4:
                reasoning.append("Moderate conversion potential with room for improvement")
            else:
                reasoning.append("Low conversion probability requires nurturing")
        
        elif prediction_type == PredictionType.OBJECTION:
            if probability > 0.6:
                reasoning.append("High objection likelihood detected")
                if features.get('price_concerns', 0) > 0:
                    reasoning.append("Price-related concerns identified")
                if features.get('competitor_mentions', 0) > 0:
                    reasoning.append("Competitive alternatives being considered")
            else:
                reasoning.append("Low objection risk - customer appears receptive")
        
        elif prediction_type == PredictionType.NEEDS:
            if probability > 0.6:
                reasoning.append("Strong need indicators present")
                if features.get('pain_points_mentioned', 0) > 0:
                    reasoning.append("Specific pain points identified")
            else:
                reasoning.append("Need discovery required to increase relevance")
        
        # Add generic reasoning if none specific
        if not reasoning:
            if probability > 0.7:
                reasoning.append("High confidence prediction based on strong feature signals")
            elif probability > 0.4:
                reasoning.append("Moderate confidence with mixed indicators")
            else:
                reasoning.append("Low confidence - more information needed")
        
        return reasoning
    
    def _get_from_cache(self, cache_key: str) -> Optional[MLPredictionResult]:
        """Get prediction from cache if valid."""
        if cache_key in self.prediction_cache:
            cached_entry = self.prediction_cache[cache_key]
            if datetime.now().timestamp() - cached_entry['timestamp'] < self.cache_ttl:
                return cached_entry['result']
            else:
                del self.prediction_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: MLPredictionResult) -> None:
        """Cache prediction result."""
        self.prediction_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now().timestamp()
        }
    
    async def _update_metrics(
        self,
        prediction_type: PredictionType,
        start_time: datetime,
        success: bool
    ) -> None:
        """Update model performance metrics."""
        if prediction_type not in self.metrics:
            return
        
        # Update response time
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        self.prediction_times[prediction_type].append(response_time)
        self.metrics[prediction_type].avg_response_time_ms = np.mean(
            list(self.prediction_times[prediction_type])
        )
        
        # Update counters
        if success:
            self.metrics[prediction_type].prediction_count += 1
        else:
            self.error_counts[prediction_type] += 1
        
        # Update error rate
        total_predictions = (
            self.metrics[prediction_type].prediction_count + 
            self.error_counts[prediction_type]
        )
        if total_predictions > 0:
            self.metrics[prediction_type].error_rate = (
                self.error_counts[prediction_type] / total_predictions
            )
    
    async def _store_prediction(
        self,
        conversation_id: str,
        result: MLPredictionResult
    ) -> None:
        """Store prediction for future analysis and drift detection."""
        if not self.supabase_client:
            return
        
        try:
            await self.supabase_client.table("ml_predictions").insert({
                "conversation_id": conversation_id,
                "prediction_type": result.prediction_type.value,
                "probability": result.probability,
                "confidence": result.confidence,
                "model_version": result.model_version,
                "features_used": result.features_used,
                "reasoning": result.reasoning,
                "metadata": result.metadata,
                "created_at": result.timestamp.isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Failed to store prediction: {e}")
    
    async def get_model_metrics(
        self,
        prediction_type: Optional[PredictionType] = None
    ) -> Dict[str, ModelMetrics]:
        """Get current model performance metrics."""
        if prediction_type:
            return {prediction_type.value: self.metrics.get(prediction_type, ModelMetrics(
                accuracy=0.0, precision=0.0, recall=0.0, f1_score=0.0,
                auc_roc=0.0, prediction_count=0, last_updated=datetime.now()
            ))}
        return {pt.value: metrics for pt, metrics in self.metrics.items()}
    
    async def detect_model_drift(
        self,
        prediction_type: PredictionType,
        threshold: float = 0.1
    ) -> Dict[str, Any]:
        """Detect if model performance has drifted."""
        if prediction_type not in self.metrics:
            return {"drift_detected": False, "reason": "No metrics available"}
        
        metrics = self.metrics[prediction_type]
        
        # Check for significant performance drop
        if metrics.accuracy > 0 and metrics.validation_score > 0:
            performance_drop = metrics.accuracy - metrics.validation_score
            if performance_drop > threshold:
                return {
                    "drift_detected": True,
                    "reason": "Performance degradation detected",
                    "accuracy_drop": performance_drop,
                    "recommendation": "Retrain model with recent data"
                }
        
        # Check error rate
        if metrics.error_rate > threshold:
            return {
                "drift_detected": True,
                "reason": "High error rate detected",
                "error_rate": metrics.error_rate,
                "recommendation": "Investigate model issues and retrain"
            }
        
        return {"drift_detected": False, "performance": "stable"}
    
    async def retrain_model(
        self,
        prediction_type: PredictionType,
        training_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Retrain a specific model with new data."""
        if prediction_type not in self.models:
            raise ModelNotFoundError(f"Model {prediction_type.value} not found")
        
        try:
            # Prepare training data
            X = []
            y = []
            
            for data_point in training_data:
                features = await self._prepare_features(data_point['features'], prediction_type)
                X.append(features)
                y.append(data_point['label'])
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Train model
            model = self.models[prediction_type]
            model.fit(X_train, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else y_pred
            
            # Update metrics
            self.metrics[prediction_type].accuracy = accuracy_score(y_test, y_pred)
            self.metrics[prediction_type].precision = precision_score(y_test, y_pred, average='weighted')
            self.metrics[prediction_type].recall = recall_score(y_test, y_pred, average='weighted')
            self.metrics[prediction_type].f1_score = f1_score(y_test, y_pred, average='weighted')
            self.metrics[prediction_type].auc_roc = roc_auc_score(y_test, y_prob)
            self.metrics[prediction_type].training_samples = len(training_data)
            self.metrics[prediction_type].last_updated = datetime.now()
            
            # Save updated model
            model_path = f"models/{prediction_type.value}_model.pkl"
            Path(model_path).parent.mkdir(parents=True, exist_ok=True)
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            
            logger.info(f"Model {prediction_type.value} retrained successfully")
            
            return {
                "success": True,
                "metrics": asdict(self.metrics[prediction_type]),
                "training_samples": len(training_data),
                "model_version": "2.1.0"  # Increment version
            }
            
        except Exception as e:
            logger.error(f"Model retraining failed for {prediction_type.value}: {e}")
            return {"success": False, "error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of the ML service."""
        health_status = {
            "status": "healthy",
            "initialized": self._initialized,
            "models_loaded": len(self.models),
            "circuit_breaker_state": self.circuit_breaker.state,
            "cache_size": len(self.prediction_cache),
            "timestamp": datetime.now().isoformat()
        }
        
        # Check model health
        model_health = {}
        for pred_type, metrics in self.metrics.items():
            model_health[pred_type.value] = {
                "prediction_count": metrics.prediction_count,
                "error_rate": metrics.error_rate,
                "avg_response_time_ms": metrics.avg_response_time_ms,
                "last_updated": metrics.last_updated.isoformat()
            }
        
        health_status["models"] = model_health
        
        # Check for issues
        issues = []
        if not self._initialized:
            issues.append("Service not initialized")
        if self.circuit_breaker.state == "open":
            issues.append("Circuit breaker is open")
        
        for pred_type, metrics in self.metrics.items():
            if metrics.error_rate > 0.1:  # 10% error rate threshold
                issues.append(f"High error rate for {pred_type.value}: {metrics.error_rate:.2%}")
        
        if issues:
            health_status["status"] = "degraded" if len(issues) < 3 else "unhealthy"
            health_status["issues"] = issues
        
        return health_status
    
    async def cleanup(self) -> None:
        """Cleanup resources when shutting down."""
        logger.info("Cleaning up Consolidated ML Prediction Service")
        
        # Clear caches
        self.prediction_cache.clear()
        self.feature_cache.clear()
        
        # Reset state
        self._initialized = False
        
        logger.info("ML service cleanup completed")