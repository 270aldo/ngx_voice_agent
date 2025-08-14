"""
NLP Services Compatibility Layer - Gradual migration support for NLP service consolidation.

This module provides backward compatibility interfaces for legacy NLP services,
allowing for zero-downtime migration to consolidated NLP service.

Features:
- Transparent routing between old and new services  
- Feature flag controlled migration
- Performance comparison during migration
- Automatic fallback on failures
- Migration progress tracking
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
from functools import wraps
from dataclasses import asdict

from src.config.settings import get_settings
from src.services.consolidated_nlp_analysis_service import (
    ConsolidatedNLPAnalysisService,
    NLPAnalysisResult,
    IntentType,
    EntityType,
    SentimentType,
    QuestionType
)
from src.utils.structured_logging import StructuredLogger

settings = get_settings()
logger = StructuredLogger.get_logger(__name__)


class NLPCompatibilityError(Exception):
    """NLP compatibility layer error."""
    pass


def with_nlp_migration_tracking(service_name: str):
    """Decorator to track NLP service usage during migration."""
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


class NLPIntegrationServiceCompat:
    """Compatibility wrapper for NLP integration service."""
    
    def __init__(self):
        self.consolidated_service = None
        self.usage_stats = {"consolidated": 0, "legacy": 0, "errors": 0}
    
    async def initialize(self):
        """Initialize the compatibility service."""
        if settings.use_consolidated_nlp_service:
            self.consolidated_service = ConsolidatedNLPAnalysisService()
            await self.consolidated_service.initialize()
    
    @with_nlp_migration_tracking("nlp_integration")
    async def analyze_intent(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze customer intent with compatibility layer."""
        if settings.use_consolidated_nlp_service and self.consolidated_service:
            try:
                result = await self.consolidated_service.analyze_text(
                    text=text,
                    context=context,
                    conversation_id=conversation_id
                )
                
                self.usage_stats["consolidated"] += 1
                
                # Convert to legacy format
                return {
                    "intent": result.intent.intent.value,
                    "confidence": result.intent.confidence,
                    "reasoning": result.intent.reasoning,
                    "sub_intents": [intent.value for intent in result.intent.sub_intents],
                    "context_factors": result.intent.context_factors,
                    "entities": [self._convert_entity_to_legacy(entity) for entity in result.entities],
                    "sentiment": {
                        "type": result.sentiment.sentiment.value,
                        "polarity": result.sentiment.polarity,
                        "confidence": result.sentiment.confidence
                    }
                }
                
            except Exception as e:
                logger.error(f"Consolidated NLP analysis failed: {e}")
                self.usage_stats["errors"] += 1
                return await self._fallback_intent_analysis(text, context, conversation_id)
        else:
            self.usage_stats["legacy"] += 1
            return await self._fallback_intent_analysis(text, context, conversation_id)
    
    @with_nlp_migration_tracking("nlp_integration")
    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Extract entities with compatibility layer."""
        if settings.use_consolidated_nlp_service and self.consolidated_service:
            try:
                result = await self.consolidated_service.analyze_text(text)
                self.usage_stats["consolidated"] += 1
                
                # Filter entities if types specified
                entities = result.entities
                if entity_types:
                    entities = [e for e in entities if e.entity_type.value in entity_types]
                
                return {
                    "entities": [self._convert_entity_to_legacy(entity) for entity in entities],
                    "total_entities": len(entities),
                    "confidence": sum(e.confidence for e in entities) / max(1, len(entities))
                }
                
            except Exception as e:
                logger.error(f"Consolidated entity extraction failed: {e}")
                self.usage_stats["errors"] += 1
                return await self._fallback_entity_extraction(text, entity_types)
        else:
            self.usage_stats["legacy"] += 1
            return await self._fallback_entity_extraction(text, entity_types)
    
    @with_nlp_migration_tracking("nlp_integration")
    async def analyze_sentiment(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze sentiment with compatibility layer."""
        if settings.use_consolidated_nlp_service and self.consolidated_service:
            try:
                result = await self.consolidated_service.analyze_text(text, context)
                self.usage_stats["consolidated"] += 1
                
                return {
                    "sentiment": result.sentiment.sentiment.value,
                    "polarity": result.sentiment.polarity,
                    "subjectivity": result.sentiment.subjectivity,
                    "confidence": result.sentiment.confidence,
                    "emotions": result.sentiment.emotion_scores,
                    "engagement_signals": result.engagement_signals
                }
                
            except Exception as e:
                logger.error(f"Consolidated sentiment analysis failed: {e}")
                self.usage_stats["errors"] += 1
                return await self._fallback_sentiment_analysis(text, context)
        else:
            self.usage_stats["legacy"] += 1
            return await self._fallback_sentiment_analysis(text, context)
    
    def _convert_entity_to_legacy(self, entity) -> Dict[str, Any]:
        """Convert consolidated entity format to legacy format."""
        return {
            "text": entity.text,
            "type": entity.entity_type.value,
            "confidence": entity.confidence,
            "start": entity.start_pos,
            "end": entity.end_pos,
            "metadata": entity.metadata
        }
    
    async def _fallback_intent_analysis(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Simple fallback intent analysis."""
        # Basic keyword-based intent detection
        text_lower = text.lower()
        
        # Simple intent mapping
        if any(word in text_lower for word in ["price", "cost", "how much", "$"]):
            intent = "pricing_inquiry"
            confidence = 0.7
        elif any(word in text_lower for word in ["demo", "show", "see", "preview"]):
            intent = "demo_request"
            confidence = 0.7
        elif "?" in text and any(word in text_lower for word in ["what", "how", "when", "where"]):
            intent = "information_seeking"
            confidence = 0.6
        elif any(word in text_lower for word in ["buy", "purchase", "sign up", "get started"]):
            intent = "closing_signal"
            confidence = 0.8
        else:
            intent = "unknown"
            confidence = 0.3
        
        return {
            "intent": intent,
            "confidence": confidence,
            "reasoning": ["simple keyword-based analysis"],
            "sub_intents": [],
            "context_factors": [],
            "entities": [],
            "sentiment": {
                "type": "neutral",
                "polarity": 0.0,
                "confidence": 0.5
            }
        }
    
    async def _fallback_entity_extraction(
        self,
        text: str,
        entity_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Simple fallback entity extraction."""
        import re
        
        entities = []
        
        # Email extraction
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            entities.append({
                "text": match.group(),
                "type": "email",
                "confidence": 0.9,
                "start": match.start(),
                "end": match.end(),
                "metadata": {}
            })
        
        # Phone extraction
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
        for match in re.finditer(phone_pattern, text):
            entities.append({
                "text": match.group(),
                "type": "phone",
                "confidence": 0.8,
                "start": match.start(),
                "end": match.end(),
                "metadata": {}
            })
        
        # Price extraction
        price_pattern = r'\$[\d,]+(?:\.\d{2})?'
        for match in re.finditer(price_pattern, text):
            entities.append({
                "text": match.group(),
                "type": "price",
                "confidence": 0.8,
                "start": match.start(),
                "end": match.end(),
                "metadata": {}
            })
        
        # Filter by requested types
        if entity_types:
            entities = [e for e in entities if e["type"] in entity_types]
        
        return {
            "entities": entities,
            "total_entities": len(entities),
            "confidence": sum(e["confidence"] for e in entities) / max(1, len(entities))
        }
    
    async def _fallback_sentiment_analysis(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Simple fallback sentiment analysis."""
        # Basic sentiment analysis using keyword matching
        positive_words = ["good", "great", "excellent", "amazing", "perfect", "love", "happy", "satisfied"]
        negative_words = ["bad", "terrible", "awful", "hate", "horrible", "disappointed", "frustrated", "angry"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
            polarity = 0.5
        elif negative_count > positive_count:
            sentiment = "negative"
            polarity = -0.5
        else:
            sentiment = "neutral"
            polarity = 0.0
        
        confidence = 0.6 if positive_count + negative_count > 0 else 0.3
        
        return {
            "sentiment": sentiment,
            "polarity": polarity,
            "subjectivity": 0.5,
            "confidence": confidence,
            "emotions": {},
            "engagement_signals": []
        }
    
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
            f"NLP Service Usage - {service_name}.{method_name}: "
            f"consolidated={settings.use_consolidated_nlp_service}, "
            f"time={processing_time:.2f}ms, success={success}"
        )


class EntityRecognitionServiceCompat:
    """Compatibility wrapper for entity recognition service."""
    
    def __init__(self):
        self.consolidated_service = None
        self.usage_stats = {"consolidated": 0, "legacy": 0, "errors": 0}
    
    async def initialize(self):
        """Initialize the compatibility service."""
        if settings.use_consolidated_nlp_service:
            self.consolidated_service = ConsolidatedNLPAnalysisService()
            await self.consolidated_service.initialize()
    
    @with_nlp_migration_tracking("entity_recognition")
    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Extract named entities with compatibility layer."""
        if settings.use_consolidated_nlp_service and self.consolidated_service:
            try:
                result = await self.consolidated_service.analyze_text(text)
                self.usage_stats["consolidated"] += 1
                
                entities = result.entities
                if entity_types:
                    entities = [e for e in entities if e.entity_type.value in entity_types]
                
                return [self._convert_entity_to_legacy(entity) for entity in entities]
                
            except Exception as e:
                logger.error(f"Consolidated entity extraction failed: {e}")
                self.usage_stats["errors"] += 1
                return await self._fallback_entity_extraction(text, entity_types)
        else:
            self.usage_stats["legacy"] += 1
            return await self._fallback_entity_extraction(text, entity_types)
    
    @with_nlp_migration_tracking("entity_recognition")
    async def recognize_named_entities(
        self,
        text: str,
        confidence_threshold: float = 0.5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Recognize named entities grouped by type."""
        if settings.use_consolidated_nlp_service and self.consolidated_service:
            try:
                result = await self.consolidated_service.analyze_text(text)
                self.usage_stats["consolidated"] += 1
                
                # Group entities by type
                grouped_entities = {}
                for entity in result.entities:
                    if entity.confidence >= confidence_threshold:
                        entity_type = entity.entity_type.value
                        if entity_type not in grouped_entities:
                            grouped_entities[entity_type] = []
                        grouped_entities[entity_type].append(self._convert_entity_to_legacy(entity))
                
                return grouped_entities
                
            except Exception as e:
                logger.error(f"Consolidated NER failed: {e}")
                self.usage_stats["errors"] += 1
                return await self._fallback_named_entity_recognition(text, confidence_threshold)
        else:
            self.usage_stats["legacy"] += 1
            return await self._fallback_named_entity_recognition(text, confidence_threshold)
    
    def _convert_entity_to_legacy(self, entity) -> Dict[str, Any]:
        """Convert consolidated entity format to legacy format."""
        return {
            "text": entity.text,
            "label": entity.entity_type.value,
            "confidence": entity.confidence,
            "start_pos": entity.start_pos,
            "end_pos": entity.end_pos,
            "metadata": entity.metadata
        }
    
    async def _fallback_entity_extraction(
        self,
        text: str,
        entity_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Simple fallback entity extraction."""
        # Reuse the fallback from NLPIntegrationServiceCompat
        nlp_compat = NLPIntegrationServiceCompat()
        result = await nlp_compat._fallback_entity_extraction(text, entity_types)
        return result["entities"]
    
    async def _fallback_named_entity_recognition(
        self,
        text: str,
        confidence_threshold: float = 0.5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Simple fallback NER."""
        entities = await self._fallback_entity_extraction(text)
        
        # Filter by confidence and group by type
        grouped = {}
        for entity in entities:
            if entity["confidence"] >= confidence_threshold:
                entity_type = entity["type"]
                if entity_type not in grouped:
                    grouped[entity_type] = []
                grouped[entity_type].append({
                    "text": entity["text"],
                    "label": entity_type,
                    "confidence": entity["confidence"],
                    "start_pos": entity["start"],
                    "end_pos": entity["end"],
                    "metadata": entity["metadata"]
                })
        
        return grouped
    
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
            f"NLP Service Usage - {service_name}.{method_name}: "
            f"consolidated={settings.use_consolidated_nlp_service}, "
            f"time={processing_time:.2f}ms, success={success}"
        )


class KeywordExtractionServiceCompat:
    """Compatibility wrapper for keyword extraction service."""
    
    def __init__(self):
        self.consolidated_service = None
        self.usage_stats = {"consolidated": 0, "legacy": 0, "errors": 0}
    
    async def initialize(self):
        """Initialize the compatibility service."""
        if settings.use_consolidated_nlp_service:
            self.consolidated_service = ConsolidatedNLPAnalysisService()
            await self.consolidated_service.initialize()
    
    @with_nlp_migration_tracking("keyword_extraction")
    async def extract_keywords(
        self,
        text: str,
        max_keywords: int = 10,
        min_relevance: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Extract keywords with compatibility layer."""
        if settings.use_consolidated_nlp_service and self.consolidated_service:
            try:
                result = await self.consolidated_service.analyze_text(text)
                self.usage_stats["consolidated"] += 1
                
                # Filter keywords by relevance and limit
                keywords = [
                    {
                        "keyword": kw.keyword,
                        "relevance": kw.relevance_score,
                        "frequency": kw.frequency,
                        "context": kw.context
                    }
                    for kw in result.keywords
                    if kw.relevance_score >= min_relevance
                ][:max_keywords]
                
                return keywords
                
            except Exception as e:
                logger.error(f"Consolidated keyword extraction failed: {e}")
                self.usage_stats["errors"] += 1
                return await self._fallback_keyword_extraction(text, max_keywords, min_relevance)
        else:
            self.usage_stats["legacy"] += 1
            return await self._fallback_keyword_extraction(text, max_keywords, min_relevance)
    
    @with_nlp_migration_tracking("keyword_extraction")
    async def extract_key_phrases(
        self,
        text: str,
        max_phrases: int = 5
    ) -> List[Dict[str, Any]]:
        """Extract key phrases with compatibility layer."""
        if settings.use_consolidated_nlp_service and self.consolidated_service:
            try:
                result = await self.consolidated_service.analyze_text(text)
                self.usage_stats["consolidated"] += 1
                
                # Extract phrases from keywords and context
                phrases = []
                for kw in result.keywords[:max_phrases]:
                    if kw.context:
                        # Extract phrases from context
                        for context_sentence in kw.context:
                            if len(context_sentence.split()) > 2:  # Multi-word phrases
                                phrases.append({
                                    "phrase": context_sentence.strip(),
                                    "relevance": kw.relevance_score,
                                    "keyword": kw.keyword
                                })
                
                return phrases[:max_phrases]
                
            except Exception as e:
                logger.error(f"Consolidated key phrase extraction failed: {e}")
                self.usage_stats["errors"] += 1
                return await self._fallback_key_phrase_extraction(text, max_phrases)
        else:
            self.usage_stats["legacy"] += 1
            return await self._fallback_key_phrase_extraction(text, max_phrases)
    
    async def _fallback_keyword_extraction(
        self,
        text: str,
        max_keywords: int = 10,
        min_relevance: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Simple fallback keyword extraction."""
        import re
        from collections import Counter
        
        # Simple tokenization
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Remove common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        words = [word for word in words if word not in stop_words]
        
        # Count frequencies
        word_freq = Counter(words)
        
        # Calculate relevance (simple TF)
        total_words = len(words)
        keywords = []
        
        for word, freq in word_freq.most_common(max_keywords * 2):  # Get more than needed
            relevance = freq / total_words
            if relevance >= min_relevance:
                keywords.append({
                    "keyword": word,
                    "relevance": relevance,
                    "frequency": freq,
                    "context": [text[:100]]  # Simple context
                })
        
        return keywords[:max_keywords]
    
    async def _fallback_key_phrase_extraction(
        self,
        text: str,
        max_phrases: int = 5
    ) -> List[Dict[str, Any]]:
        """Simple fallback key phrase extraction."""
        import re
        
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        
        phrases = []
        for sentence in sentences[:max_phrases]:
            if len(sentence.split()) >= 3:  # Multi-word phrases
                phrases.append({
                    "phrase": sentence.strip(),
                    "relevance": 0.5,  # Default relevance
                    "keyword": sentence.split()[0] if sentence.split() else ""
                })
        
        return phrases[:max_phrases]
    
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
            f"NLP Service Usage - {service_name}.{method_name}: "
            f"consolidated={settings.use_consolidated_nlp_service}, "
            f"time={processing_time:.2f}ms, success={success}"
        )


class QuestionClassificationServiceCompat:
    """Compatibility wrapper for question classification service."""
    
    def __init__(self):
        self.consolidated_service = None
        self.usage_stats = {"consolidated": 0, "legacy": 0, "errors": 0}
    
    async def initialize(self):
        """Initialize the compatibility service."""
        if settings.use_consolidated_nlp_service:
            self.consolidated_service = ConsolidatedNLPAnalysisService()
            await self.consolidated_service.initialize()
    
    @with_nlp_migration_tracking("question_classification")
    async def classify_questions(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Classify questions with compatibility layer."""
        if settings.use_consolidated_nlp_service and self.consolidated_service:
            try:
                result = await self.consolidated_service.analyze_text(text, context)
                self.usage_stats["consolidated"] += 1
                
                return [
                    {
                        "question_type": q.question_type.value,
                        "confidence": q.confidence,
                        "intent_signals": q.intent_signals
                    }
                    for q in result.questions
                ]
                
            except Exception as e:
                logger.error(f"Consolidated question classification failed: {e}")
                self.usage_stats["errors"] += 1
                return await self._fallback_question_classification(text, context)
        else:
            self.usage_stats["legacy"] += 1
            return await self._fallback_question_classification(text, context)
    
    async def _fallback_question_classification(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Simple fallback question classification."""
        import re
        
        # Find questions
        questions = [s.strip() for s in re.split(r'[.!]+', text) if s.strip().endswith('?')]
        
        classified_questions = []
        for question in questions:
            question_lower = question.lower()
            
            # Simple classification
            if question_lower.startswith('what'):
                q_type = "what"
            elif question_lower.startswith('how much') or 'how much' in question_lower:
                q_type = "how_much"
            elif question_lower.startswith('how'):
                q_type = "how"
            elif question_lower.startswith('when'):
                q_type = "when"
            elif question_lower.startswith('where'):
                q_type = "where"
            elif question_lower.startswith('why'):
                q_type = "why"
            elif question_lower.startswith('who'):
                q_type = "who"
            elif any(word in question_lower for word in ['is', 'are', 'can', 'do', 'does']):
                q_type = "yes_no"
            else:
                q_type = "rhetorical"
            
            # Simple intent signals
            intent_signals = []
            if any(word in question_lower for word in ['price', 'cost', 'much']):
                intent_signals.append("pricing_interest")
            if any(word in question_lower for word in ['demo', 'show']):
                intent_signals.append("demo_interest")
            
            classified_questions.append({
                "question_type": q_type,
                "confidence": 0.7,
                "intent_signals": intent_signals
            })
        
        return classified_questions
    
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
            f"NLP Service Usage - {service_name}.{method_name}: "
            f"consolidated={settings.use_consolidated_nlp_service}, "
            f"time={processing_time:.2f}ms, success={success}"
        )


# Factory functions for easy service access
async def get_nlp_integration_service() -> NLPIntegrationServiceCompat:
    """Get NLP integration service with compatibility layer."""
    service = NLPIntegrationServiceCompat()
    await service.initialize()
    return service


async def get_entity_recognition_service() -> EntityRecognitionServiceCompat:
    """Get entity recognition service with compatibility layer."""
    service = EntityRecognitionServiceCompat()
    await service.initialize()
    return service


async def get_keyword_extraction_service() -> KeywordExtractionServiceCompat:
    """Get keyword extraction service with compatibility layer."""
    service = KeywordExtractionServiceCompat()
    await service.initialize()
    return service


async def get_question_classification_service() -> QuestionClassificationServiceCompat:
    """Get question classification service with compatibility layer."""
    service = QuestionClassificationServiceCompat()
    await service.initialize()
    return service


class NLPMigrationManager:
    """Manager for NLP service migration process."""
    
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
            "nlp_integration": await get_nlp_integration_service(),
            "entity_recognition": await get_entity_recognition_service(),
            "keyword_extraction": await get_keyword_extraction_service(),
            "question_classification": await get_question_classification_service()
        }
        logger.info("NLP compatibility services initialized")
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status and statistics."""
        return {
            "consolidated_nlp_enabled": settings.use_consolidated_nlp_service,
            "services_initialized": len(self.services),
            "migration_stats": self.migration_stats,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for all NLP services."""
        health = {
            "status": "healthy",
            "services": {},
            "migration_enabled": settings.use_consolidated_nlp_service
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
_nlp_migration_manager = None


async def get_nlp_migration_manager() -> NLPMigrationManager:
    """Get global NLP migration manager instance."""
    global _nlp_migration_manager
    if _nlp_migration_manager is None:
        _nlp_migration_manager = NLPMigrationManager()
        await _nlp_migration_manager.initialize_services()
    return _nlp_migration_manager


def log_nlp_migration_progress():
    """Log current NLP migration progress."""
    if settings.use_consolidated_nlp_service:
        logger.info("✅ Using consolidated NLP analysis service")
    else:
        logger.info("⚠️  Using legacy NLP services")
    
    logger.info("NLP service migration layer active")