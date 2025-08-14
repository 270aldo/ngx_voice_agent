"""
Consolidated NLP Analysis Service - Unified natural language processing for NGX Voice Agent.

This service consolidates all NLP functionality into a single, high-performance service:
- Intent analysis and classification
- Entity recognition and extraction
- Sentiment analysis
- Keyword extraction
- Question classification  
- Context understanding
- Language detection
- Text summarization

Designed for production use with enterprise-grade features:
- Async processing pipeline
- Multi-model ensemble
- Caching for performance
- Batch processing support
- Real-time analysis
- Language model integration
"""

import asyncio
import json
import logging
import re
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from contextlib import asynccontextmanager

# Import numpy with fallback
try:
    import numpy as np
except ImportError:
    # Fallback implementation for numpy functions
    class NumpyFallback:
        def mean(self, data):
            return sum(data) / len(data) if data else 0
        def array(self, data):
            return list(data)
    np = NumpyFallback()

# Optional NLP dependencies
try:
    import spacy
except ImportError:
    spacy = None

try:
    from textblob import TextBlob
except ImportError:
    TextBlob = None

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk.chunk import ne_chunk
    from nltk.tag import pos_tag
except ImportError:
    nltk = None
    stopwords = None
    word_tokenize = None
    sent_tokenize = None
    ne_chunk = None
    pos_tag = None

from src.config.settings import get_settings
from src.integrations.supabase.resilient_client import ResilientSupabaseClient
from src.models.conversation import ConversationState, CustomerData
from src.utils.structured_logging import StructuredLogger

settings = get_settings()
logger = StructuredLogger.get_logger(__name__)


class NLPError(Exception):
    """Base exception for NLP service errors."""
    pass


class IntentType(str, Enum):
    """Customer intent types."""
    INFORMATION_SEEKING = "information_seeking"
    PRICING_INQUIRY = "pricing_inquiry"
    FEATURE_QUESTION = "feature_question"
    DEMO_REQUEST = "demo_request"
    OBJECTION_RAISING = "objection_raising"
    COMPARISON_REQUEST = "comparison_request"
    TECHNICAL_SUPPORT = "technical_support"
    SCHEDULING = "scheduling"
    NEGOTIATION = "negotiation"
    CLOSING_SIGNAL = "closing_signal"
    STALLING = "stalling"
    GOODBYE = "goodbye"
    GREETING = "greeting"
    CLARIFICATION = "clarification"
    COMPLAINT = "complaint"
    UNKNOWN = "unknown"


class EntityType(str, Enum):
    """Named entity types."""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    PRODUCT = "product"
    FEATURE = "feature"
    PRICE = "price"
    DATE = "date"
    TIME = "time"
    DURATION = "duration"
    PERCENTAGE = "percentage"
    CURRENCY = "currency"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    TECHNOLOGY = "technology"
    COMPETITOR = "competitor"


class SentimentType(str, Enum):
    """Sentiment classification."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class QuestionType(str, Enum):
    """Question classification types."""
    YES_NO = "yes_no"
    WHAT = "what"
    HOW = "how"
    WHY = "why"
    WHEN = "when"
    WHERE = "where"
    WHO = "who"
    WHICH = "which"
    HOW_MUCH = "how_much"
    HOW_MANY = "how_many"
    RHETORICAL = "rhetorical"


@dataclass
class IntentResult:
    """Intent analysis result."""
    intent: IntentType
    confidence: float
    reasoning: List[str]
    context_factors: List[str] = field(default_factory=list)
    sub_intents: List[IntentType] = field(default_factory=list)


@dataclass
class EntityResult:
    """Entity recognition result."""
    text: str
    entity_type: EntityType
    confidence: float
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SentimentResult:
    """Sentiment analysis result."""
    sentiment: SentimentType
    polarity: float  # -1 to 1
    subjectivity: float  # 0 to 1
    confidence: float
    emotion_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class KeywordResult:
    """Keyword extraction result."""
    keyword: str
    relevance_score: float
    frequency: int
    context: List[str] = field(default_factory=list)


@dataclass
class QuestionResult:
    """Question classification result."""
    question_type: QuestionType
    confidence: float
    intent_signals: List[str] = field(default_factory=list)


@dataclass
class NLPAnalysisResult:
    """Comprehensive NLP analysis result."""
    intent: IntentResult
    entities: List[EntityResult]
    sentiment: SentimentResult
    keywords: List[KeywordResult]
    questions: List[QuestionResult]
    language: str
    text_summary: str
    complexity_score: float
    engagement_signals: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class ConsolidatedNLPAnalysisService:
    """
    Consolidated NLP analysis service with enterprise features.
    
    Features:
    - Multi-model ensemble for accuracy
    - Async processing pipeline
    - Intelligent caching
    - Batch processing support
    - Context-aware analysis
    - Real-time streaming support
    """
    
    def __init__(self, supabase_client: Optional[ResilientSupabaseClient] = None):
        self.supabase_client = supabase_client
        
        # NLP Models
        self.spacy_model = None
        self.nltk_initialized = False
        
        # Analysis cache
        self.analysis_cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Pattern libraries
        self.intent_patterns = self._initialize_intent_patterns()
        self.entity_patterns = self._initialize_entity_patterns()
        self.sentiment_modifiers = self._initialize_sentiment_modifiers()
        self.keyword_stopwords = set()
        
        # Performance tracking
        self.analysis_times = deque(maxlen=100)
        self.error_count = 0
        
        # Async initialization
        self._initialized = False
        self._initializing = False
        self._initialization_lock = asyncio.Lock()
        
        logger.info("Consolidated NLP Analysis Service initialized")
    
    async def initialize(self) -> None:
        """Initialize NLP models and resources."""
        async with self._initialization_lock:
            if self._initialized or self._initializing:
                return
            
            self._initializing = True
            try:
                await self._load_spacy_model()
                await self._initialize_nltk()
                await self._load_custom_models()
                self._initialized = True
                logger.info("NLP service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize NLP service: {e}")
                raise
            finally:
                self._initializing = False
    
    async def _load_spacy_model(self) -> None:
        """Load spaCy language model."""
        if spacy is None:
            logger.warning("spaCy not available - some NLP features will be limited")
            return
            
        try:
            # Try to load English model
            try:
                self.spacy_model = spacy.load("en_core_web_sm")
                logger.info("Loaded spaCy en_core_web_sm model")
            except OSError:
                # Fallback to blank model
                self.spacy_model = spacy.blank("en")
                logger.warning("Using blank spaCy model - install en_core_web_sm for better results")
        except Exception as e:
            logger.warning(f"Failed to load spaCy model: {e}")
    
    async def _initialize_nltk(self) -> None:
        """Initialize NLTK resources."""
        if nltk is None or stopwords is None:
            logger.warning("NLTK not available - using basic text processing")
            self.keyword_stopwords = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'])
            return
            
        try:
            # Download required NLTK data
            required_data = ['punkt', 'stopwords', 'averaged_perceptron_tagger', 'maxent_ne_chunker', 'words']
            
            for data in required_data:
                try:
                    nltk.data.find(f'tokenizers/{data}')
                except LookupError:
                    try:
                        nltk.download(data, quiet=True)
                    except Exception:
                        logger.warning(f"Could not download NLTK data: {data}")
            
            # Initialize stopwords
            try:
                self.keyword_stopwords = set(stopwords.words('english'))
            except Exception:
                self.keyword_stopwords = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'])
            
            self.nltk_initialized = True
            logger.info("NLTK resources initialized")
        except Exception as e:
            logger.warning(f"NLTK initialization failed: {e}")
            self.keyword_stopwords = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'])
    
    async def _load_custom_models(self) -> None:
        """Load custom domain-specific models."""
        # Load NGX-specific patterns and vocabularies
        self._load_ngx_vocabulary()
        self._load_sales_patterns()
        logger.info("Custom NLP models loaded")
    
    def _initialize_intent_patterns(self) -> Dict[IntentType, Dict[str, Any]]:
        """Initialize intent recognition patterns."""
        return {
            IntentType.PRICING_INQUIRY: {
                "keywords": ["price", "cost", "pricing", "expensive", "cheap", "fee", "charge", "budget", "afford"],
                "phrases": ["how much", "what does it cost", "pricing information", "what's the price"],
                "patterns": [r"\$\d+", r"cost.*\?", r"price.*\?", r"expensive.*\?"]
            },
            IntentType.DEMO_REQUEST: {
                "keywords": ["demo", "demonstration", "show", "see", "preview", "trial", "test"],
                "phrases": ["can i see", "show me", "demo please", "live demo", "can we try"],
                "patterns": [r"demo.*\?", r"show.*how", r"can.*see"]
            },
            IntentType.FEATURE_QUESTION: {
                "keywords": ["feature", "functionality", "capability", "does it", "can it", "support"],
                "phrases": ["what features", "does it have", "can it do", "is there a way"],
                "patterns": [r"does.*support", r"can.*do", r"what.*feature"]
            },
            IntentType.OBJECTION_RAISING: {
                "keywords": ["but", "however", "concerned", "worried", "problem", "issue", "difficult"],
                "phrases": ["i'm not sure", "i'm concerned", "the problem is", "but what about"],
                "patterns": [r"but.*", r"however.*", r"problem.*", r"concern.*"]
            },
            IntentType.COMPARISON_REQUEST: {
                "keywords": ["compare", "versus", "alternative", "competitor", "different", "other"],
                "phrases": ["compared to", "vs", "what about", "how does it compare", "alternatives"],
                "patterns": [r"vs.*", r"compared.*to", r"alternative.*"]
            },
            IntentType.SCHEDULING: {
                "keywords": ["schedule", "meeting", "call", "appointment", "when", "time", "available"],
                "phrases": ["schedule a call", "set up a meeting", "when can we", "are you available"],
                "patterns": [r"schedule.*", r"meeting.*", r"when.*available"]
            },
            IntentType.CLOSING_SIGNAL: {
                "keywords": ["buy", "purchase", "proceed", "move forward", "next steps", "contract", "sign"],
                "phrases": ["let's do it", "move forward", "next steps", "ready to buy", "sign up"],
                "patterns": [r"let.*do", r"move.*forward", r"ready.*"]
            }
        }
    
    def _initialize_entity_patterns(self) -> Dict[EntityType, Dict[str, Any]]:
        """Initialize entity recognition patterns."""
        return {
            EntityType.PRICE: {
                "patterns": [
                    r'\$[\d,]+(?:\.\d{2})?',
                    r'\d+\s*(?:dollars?|usd|€|euros?|£|pounds?)',
                    r'[\d,]+\s*(?:per|/)\s*(?:month|year|user|license)'
                ]
            },
            EntityType.EMAIL: {
                "patterns": [r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b']
            },
            EntityType.PHONE: {
                "patterns": [
                    r'\b\d{3}-\d{3}-\d{4}\b',
                    r'\b\(\d{3}\)\s*\d{3}-\d{4}\b',
                    r'\b\d{10}\b'
                ]
            },
            EntityType.URL: {
                "patterns": [r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?']
            },
            EntityType.COMPETITOR: {
                "keywords": [
                    "salesforce", "hubspot", "pipedrive", "zoho", "freshworks",
                    "microsoft dynamics", "insightly", "monday.com", "clickfunnels"
                ]
            },
            EntityType.TECHNOLOGY: {
                "keywords": [
                    "api", "integration", "crm", "erp", "saas", "cloud",
                    "mobile app", "web app", "dashboard", "analytics", "ai", "ml"
                ]
            }
        }
    
    def _initialize_sentiment_modifiers(self) -> Dict[str, float]:
        """Initialize sentiment modifiers."""
        return {
            # Intensifiers
            "very": 1.3, "extremely": 1.5, "incredibly": 1.4, "absolutely": 1.3,
            "really": 1.2, "quite": 1.1, "fairly": 1.1, "pretty": 1.1,
            
            # Diminishers
            "slightly": 0.5, "somewhat": 0.6, "rather": 0.8, "kind of": 0.7,
            "sort of": 0.7, "a bit": 0.6, "a little": 0.6,
            
            # Negations
            "not": -1.0, "never": -1.0, "no": -1.0, "nothing": -1.0,
            "nobody": -1.0, "nowhere": -1.0, "neither": -1.0, "nor": -1.0
        }
    
    def _load_ngx_vocabulary(self) -> None:
        """Load NGX-specific vocabulary and terms."""
        self.ngx_terms = {
            "products": [
                "ngx agents", "ngx blog", "ngx social", "ngx ads", "ngx email",
                "ngx sms", "ngx calendar", "ngx crm", "ngx analytics"
            ],
            "features": [
                "ai assistant", "voice agent", "automated scheduling", "lead qualification",
                "conversation analytics", "multi-channel marketing", "campaign optimization"
            ],
            "pain_points": [
                "lead generation", "client acquisition", "time management", "follow-up",
                "scheduling conflicts", "manual processes", "conversion rates"
            ]
        }
    
    def _load_sales_patterns(self) -> None:
        """Load sales-specific patterns and phrases."""
        self.sales_patterns = {
            "buying_signals": [
                "when can we start", "what's the next step", "how do we proceed",
                "what's included", "contract", "agreement", "move forward"
            ],
            "hesitation_signals": [
                "i need to think", "let me consider", "i'm not sure", "maybe later",
                "i need approval", "budget concerns", "timing isn't right"
            ],
            "urgency_indicators": [
                "as soon as possible", "urgent", "immediately", "right away",
                "time sensitive", "deadline", "by when"
            ]
        }
    
    async def analyze_text(
        self, 
        text: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None
    ) -> NLPAnalysisResult:
        """Perform comprehensive NLP analysis on text."""
        await self.initialize()
        
        start_time = datetime.now()
        
        try:
            # Check cache
            cache_key = f"analysis_{hash(text)}_{hash(str(context) if context else '')}"
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result
            
            # Parallel analysis tasks
            analysis_tasks = [
                self._analyze_intent(text, context),
                self._extract_entities(text),
                self._analyze_sentiment(text),
                self._extract_keywords(text),
                self._classify_questions(text),
                self._detect_language(text),
                self._summarize_text(text),
                self._calculate_complexity(text),
                self._detect_engagement_signals(text)
            ]
            
            # Run analyses concurrently
            results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            # Handle any exceptions and create final result
            intent = results[0] if not isinstance(results[0], Exception) else IntentResult(
                intent=IntentType.UNKNOWN, confidence=0.0, reasoning=["Analysis failed"]
            )
            entities = results[1] if not isinstance(results[1], Exception) else []
            sentiment = results[2] if not isinstance(results[2], Exception) else SentimentResult(
                sentiment=SentimentType.NEUTRAL, polarity=0.0, subjectivity=0.0, confidence=0.0
            )
            keywords = results[3] if not isinstance(results[3], Exception) else []
            questions = results[4] if not isinstance(results[4], Exception) else []
            language = results[5] if not isinstance(results[5], Exception) else "en"
            text_summary = results[6] if not isinstance(results[6], Exception) else text[:100]
            complexity_score = results[7] if not isinstance(results[7], Exception) else 0.5
            engagement_signals = results[8] if not isinstance(results[8], Exception) else []
            
            # Create comprehensive result
            analysis_result = NLPAnalysisResult(
                intent=intent,
                entities=entities,
                sentiment=sentiment,
                keywords=keywords,
                questions=questions,
                language=language,
                text_summary=text_summary,
                complexity_score=complexity_score,
                engagement_signals=engagement_signals
            )
            
            # Cache result
            self._cache_result(cache_key, analysis_result)
            
            # Store analysis if conversation_id provided
            if conversation_id:
                await self._store_analysis(conversation_id, analysis_result)
            
            # Update performance metrics
            self._update_performance_metrics(start_time)
            
            return analysis_result
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"NLP analysis failed: {e}")
            raise NLPError(f"Analysis failed: {e}")
    
    async def analyze_batch(
        self,
        texts: List[str],
        contexts: Optional[List[Dict[str, Any]]] = None,
        conversation_ids: Optional[List[str]] = None
    ) -> List[NLPAnalysisResult]:
        """Analyze multiple texts efficiently in batch."""
        await self.initialize()
        
        if contexts is None:
            contexts = [None] * len(texts)
        if conversation_ids is None:
            conversation_ids = [None] * len(texts)
        
        # Process in smaller batches to avoid overwhelming the system
        batch_size = 10
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_contexts = contexts[i:i + batch_size]
            batch_conv_ids = conversation_ids[i:i + batch_size]
            
            # Analyze batch concurrently
            batch_tasks = [
                self.analyze_text(text, context, conv_id)
                for text, context, conv_id in zip(batch_texts, batch_contexts, batch_conv_ids)
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle exceptions
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch analysis failed: {result}")
                    # Create error result
                    error_result = NLPAnalysisResult(
                        intent=IntentResult(intent=IntentType.UNKNOWN, confidence=0.0, reasoning=["Analysis failed"]),
                        entities=[],
                        sentiment=SentimentResult(sentiment=SentimentType.NEUTRAL, polarity=0.0, subjectivity=0.0, confidence=0.0),
                        keywords=[],
                        questions=[],
                        language="en",
                        text_summary="Analysis failed",
                        complexity_score=0.0,
                        engagement_signals=[]
                    )
                    results.append(error_result)
                else:
                    results.append(result)
        
        return results
    
    async def _analyze_intent(
        self, 
        text: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> IntentResult:
        """Analyze customer intent from text."""
        text_lower = text.lower()
        intent_scores = defaultdict(float)
        reasoning = []
        
        # Pattern-based intent detection
        for intent_type, patterns in self.intent_patterns.items():
            score = 0.0
            
            # Check keywords
            for keyword in patterns.get("keywords", []):
                if keyword in text_lower:
                    score += 0.3
                    reasoning.append(f"Found keyword '{keyword}' for {intent_type.value}")
            
            # Check phrases
            for phrase in patterns.get("phrases", []):
                if phrase in text_lower:
                    score += 0.5
                    reasoning.append(f"Found phrase '{phrase}' for {intent_type.value}")
            
            # Check regex patterns
            for pattern in patterns.get("patterns", []):
                if re.search(pattern, text_lower):
                    score += 0.4
                    reasoning.append(f"Matched pattern for {intent_type.value}")
            
            intent_scores[intent_type] = score
        
        # Context-based adjustments
        if context:
            conversation_stage = context.get("stage", "discovery")
            if conversation_stage == "closing" and IntentType.CLOSING_SIGNAL in intent_scores:
                intent_scores[IntentType.CLOSING_SIGNAL] *= 1.5
            elif conversation_stage == "demo" and IntentType.DEMO_REQUEST in intent_scores:
                intent_scores[IntentType.DEMO_REQUEST] *= 1.3
        
        # Determine primary intent
        if intent_scores:
            primary_intent = max(intent_scores.items(), key=lambda x: x[1])
            confidence = min(1.0, primary_intent[1])
            
            # Find sub-intents (other high-scoring intents)
            sub_intents = [
                intent for intent, score in intent_scores.items()
                if score > 0.3 and intent != primary_intent[0]
            ]
            
            return IntentResult(
                intent=primary_intent[0],
                confidence=confidence,
                reasoning=reasoning[:3],  # Top 3 reasons
                sub_intents=sub_intents
            )
        else:
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                reasoning=["No intent patterns matched"]
            )
    
    async def _extract_entities(self, text: str) -> List[EntityResult]:
        """Extract named entities from text."""
        entities = []
        
        # Pattern-based entity extraction
        for entity_type, config in self.entity_patterns.items():
            # Regex patterns
            for pattern in config.get("patterns", []):
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entities.append(EntityResult(
                        text=match.group(),
                        entity_type=entity_type,
                        confidence=0.8,
                        start_pos=match.start(),
                        end_pos=match.end()
                    ))
            
            # Keyword-based entities
            for keyword in config.get("keywords", []):
                if keyword.lower() in text.lower():
                    start_pos = text.lower().find(keyword.lower())
                    entities.append(EntityResult(
                        text=keyword,
                        entity_type=entity_type,
                        confidence=0.7,
                        start_pos=start_pos,
                        end_pos=start_pos + len(keyword)
                    ))
        
        # spaCy-based entity extraction (if available)
        if self.spacy_model:
            try:
                doc = self.spacy_model(text)
                for ent in doc.ents:
                    # Map spaCy labels to our entity types
                    entity_type = self._map_spacy_entity_type(ent.label_)
                    if entity_type:
                        entities.append(EntityResult(
                            text=ent.text,
                            entity_type=entity_type,
                            confidence=0.9,
                            start_pos=ent.start_char,
                            end_pos=ent.end_char,
                            metadata={"spacy_label": ent.label_}
                        ))
            except Exception as e:
                logger.warning(f"spaCy entity extraction failed: {e}")
        
        # Remove duplicates and sort by confidence
        unique_entities = {}
        for entity in entities:
            key = (entity.text.lower(), entity.entity_type)
            if key not in unique_entities or entity.confidence > unique_entities[key].confidence:
                unique_entities[key] = entity
        
        return sorted(unique_entities.values(), key=lambda x: x.confidence, reverse=True)
    
    def _map_spacy_entity_type(self, spacy_label: str) -> Optional[EntityType]:
        """Map spaCy entity labels to our EntityType enum."""
        mapping = {
            "PERSON": EntityType.PERSON,
            "ORG": EntityType.ORGANIZATION,
            "GPE": EntityType.LOCATION,
            "LOC": EntityType.LOCATION,
            "DATE": EntityType.DATE,
            "TIME": EntityType.TIME,
            "MONEY": EntityType.PRICE,
            "PERCENT": EntityType.PERCENTAGE,
            "PRODUCT": EntityType.PRODUCT,
        }
        return mapping.get(spacy_label)
    
    async def _analyze_sentiment(self, text: str) -> SentimentResult:
        """Analyze sentiment of text using multiple approaches."""
        try:
            if TextBlob is not None:
                # TextBlob sentiment analysis
                blob = TextBlob(text)
                polarity = blob.sentiment.polarity  # -1 to 1
                subjectivity = blob.sentiment.subjectivity  # 0 to 1
            else:
                # Fallback sentiment analysis using keyword matching
                polarity, subjectivity = self._fallback_sentiment_analysis(text)
            
            # Determine sentiment category
            if polarity > 0.1:
                sentiment = SentimentType.POSITIVE
            elif polarity < -0.1:
                sentiment = SentimentType.NEGATIVE
            else:
                sentiment = SentimentType.NEUTRAL
            
            # Calculate confidence based on polarity strength
            confidence = abs(polarity) if abs(polarity) > 0.1 else 0.5
            
            # Apply sentiment modifiers
            modified_polarity = self._apply_sentiment_modifiers(text, polarity)
            
            # Basic emotion detection
            emotion_scores = self._detect_emotions(text)
            
            return SentimentResult(
                sentiment=sentiment,
                polarity=modified_polarity,
                subjectivity=subjectivity,
                confidence=confidence,
                emotion_scores=emotion_scores
            )
            
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            return SentimentResult(
                sentiment=SentimentType.NEUTRAL,
                polarity=0.0,
                subjectivity=0.0,
                confidence=0.0
            )
    
    def _apply_sentiment_modifiers(self, text: str, base_polarity: float) -> float:
        """Apply sentiment modifiers like intensifiers and negations."""
        words = text.lower().split()
        modified_polarity = base_polarity
        
        for i, word in enumerate(words):
            if word in self.sentiment_modifiers:
                modifier = self.sentiment_modifiers[word]
                
                # Apply modifier based on type
                if modifier < 0:  # Negation
                    modified_polarity *= modifier
                else:  # Intensifier or diminisher
                    modified_polarity *= modifier
                
                # Don't let it exceed bounds
                modified_polarity = max(-1.0, min(1.0, modified_polarity))
        
        return modified_polarity
    
    def _detect_emotions(self, text: str) -> Dict[str, float]:
        """Basic emotion detection using keyword patterns."""
        emotion_keywords = {
            "joy": ["happy", "excited", "pleased", "delighted", "satisfied", "great"],
            "anger": ["angry", "frustrated", "annoyed", "upset", "mad", "irritated"],
            "fear": ["worried", "concerned", "anxious", "scared", "afraid", "nervous"],
            "sadness": ["sad", "disappointed", "unhappy", "discouraged", "down"],
            "surprise": ["surprised", "amazed", "shocked", "unexpected", "wow"],
            "trust": ["confident", "sure", "certain", "reliable", "trustworthy"]
        }
        
        text_lower = text.lower()
        emotion_scores = {}
        
        for emotion, keywords in emotion_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            emotion_scores[emotion] = min(1.0, score / len(keywords))
        
        return emotion_scores
    
    def _fallback_sentiment_analysis(self, text: str) -> Tuple[float, float]:
        """Fallback sentiment analysis using keyword matching."""
        positive_words = ["good", "great", "excellent", "amazing", "perfect", "love", "happy", "satisfied", "wonderful", "fantastic"]
        negative_words = ["bad", "terrible", "awful", "hate", "horrible", "disappointed", "frustrated", "angry", "poor", "worst"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total_words = len(text_lower.split())
        
        if positive_count + negative_count == 0:
            return 0.0, 0.5  # Neutral polarity, medium subjectivity
        
        # Calculate polarity (-1 to 1)
        polarity = (positive_count - negative_count) / max(1, positive_count + negative_count)
        polarity = max(-1.0, min(1.0, polarity))
        
        # Calculate subjectivity (0 to 1)
        subjectivity = (positive_count + negative_count) / max(1, total_words)
        subjectivity = max(0.0, min(1.0, subjectivity))
        
        return polarity, subjectivity
    
    async def _extract_keywords(self, text: str) -> List[KeywordResult]:
        """Extract relevant keywords and key phrases."""
        try:
            # Tokenize and clean text
            if self.nltk_initialized and word_tokenize is not None:
                tokens = word_tokenize(text.lower())
                tokens = [token for token in tokens if token.isalpha() and token not in self.keyword_stopwords]
            else:
                # Simple tokenization fallback
                tokens = [word.lower() for word in re.findall(r'\b[a-z]+\b', text.lower())
                         if word not in self.keyword_stopwords]
            
            # Count frequency
            word_freq = Counter(tokens)
            
            # Calculate relevance scores
            keywords = []
            for word, freq in word_freq.most_common(10):  # Top 10 keywords
                # Calculate relevance based on frequency and NGX domain relevance
                relevance_score = freq / len(tokens)  # Basic TF
                
                # Boost NGX-relevant terms
                if self._is_ngx_relevant(word):
                    relevance_score *= 2.0
                
                # Boost sales-relevant terms
                if self._is_sales_relevant(word):
                    relevance_score *= 1.5
                
                keywords.append(KeywordResult(
                    keyword=word,
                    relevance_score=min(1.0, relevance_score),
                    frequency=freq,
                    context=self._get_keyword_context(word, text)
                ))
            
            return sorted(keywords, key=lambda x: x.relevance_score, reverse=True)
            
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}")
            return []
    
    def _is_ngx_relevant(self, word: str) -> bool:
        """Check if word is relevant to NGX domain."""
        ngx_words = set()
        for category in self.ngx_terms.values():
            ngx_words.update([term.lower().replace(' ', '') for term in category])
        return word in ngx_words
    
    def _is_sales_relevant(self, word: str) -> bool:
        """Check if word is relevant to sales domain."""
        sales_words = {"price", "cost", "buy", "purchase", "demo", "feature", "benefit",
                      "solution", "problem", "need", "budget", "contract", "deal"}
        return word in sales_words
    
    def _get_keyword_context(self, keyword: str, text: str, window: int = 5) -> List[str]:
        """Get context sentences containing the keyword."""
        sentences = re.split(r'[.!?]+', text)
        context = []
        
        for sentence in sentences:
            if keyword.lower() in sentence.lower():
                context.append(sentence.strip())
                if len(context) >= 3:  # Limit context
                    break
        
        return context
    
    async def _classify_questions(self, text: str) -> List[QuestionResult]:
        """Classify questions in the text."""
        questions = []
        
        # Find sentences that are questions
        question_sentences = [s.strip() for s in re.split(r'[.!]+', text) if s.strip().endswith('?')]
        
        for question in question_sentences:
            question_lower = question.lower()
            
            # Classify question type
            if any(word in question_lower for word in ['is', 'are', 'can', 'do', 'does', 'will', 'would']):
                if not any(wh in question_lower for wh in ['what', 'how', 'when', 'where', 'who', 'why', 'which']):
                    q_type = QuestionType.YES_NO
                else:
                    q_type = self._classify_wh_question(question_lower)
            else:
                q_type = self._classify_wh_question(question_lower)
            
            # Detect intent signals
            intent_signals = []
            if any(word in question_lower for word in ['price', 'cost', 'much']):
                intent_signals.append("pricing_interest")
            if any(word in question_lower for word in ['demo', 'show', 'see']):
                intent_signals.append("demo_interest")
            if any(word in question_lower for word in ['feature', 'capability', 'can it']):
                intent_signals.append("feature_interest")
            
            confidence = 0.8 if q_type != QuestionType.RHETORICAL else 0.5
            
            questions.append(QuestionResult(
                question_type=q_type,
                confidence=confidence,
                intent_signals=intent_signals
            ))
        
        return questions
    
    def _classify_wh_question(self, question: str) -> QuestionType:
        """Classify WH-questions."""
        if question.startswith(('what', 'what\'s')):
            return QuestionType.WHAT
        elif question.startswith('how much') or 'how much' in question:
            return QuestionType.HOW_MUCH
        elif question.startswith('how many') or 'how many' in question:
            return QuestionType.HOW_MANY
        elif question.startswith('how'):
            return QuestionType.HOW
        elif question.startswith('why'):
            return QuestionType.WHY
        elif question.startswith('when'):
            return QuestionType.WHEN
        elif question.startswith('where'):
            return QuestionType.WHERE
        elif question.startswith('who'):
            return QuestionType.WHO
        elif question.startswith('which'):
            return QuestionType.WHICH
        else:
            return QuestionType.RHETORICAL
    
    async def _detect_language(self, text: str) -> str:
        """Detect the language of the text."""
        try:
            if TextBlob is not None:
                # Simple language detection using TextBlob
                blob = TextBlob(text)
                return blob.detect_language()
            else:
                # Simple heuristic language detection
                return self._fallback_language_detection(text)
        except Exception:
            # Default to English
            return "en"
    
    def _fallback_language_detection(self, text: str) -> str:
        """Simple heuristic language detection."""
        # Spanish indicators
        spanish_words = ["sí", "no", "es", "la", "el", "que", "de", "un", "una", "con", "por", "para"]
        spanish_count = sum(1 for word in spanish_words if word in text.lower())
        
        # French indicators  
        french_words = ["oui", "non", "est", "le", "la", "que", "de", "un", "une", "avec", "pour", "dans"]
        french_count = sum(1 for word in french_words if word in text.lower())
        
        if spanish_count > 0:
            return "es"
        elif french_count > 0:
            return "fr"
        else:
            return "en"
    
    async def _summarize_text(self, text: str) -> str:
        """Create a brief summary of the text."""
        # Simple extractive summarization
        if self.nltk_initialized and sent_tokenize is not None:
            sentences = sent_tokenize(text)
        else:
            sentences = re.split(r'[.!?]+', text)
        
        if len(sentences) <= 2:
            return text
        
        # Get first and most informative sentence
        summary_sentences = []
        
        # Always include first sentence
        if sentences:
            summary_sentences.append(sentences[0].strip())
        
        # Find sentence with most keywords
        if len(sentences) > 1:
            keyword_counts = []
            for sentence in sentences[1:]:
                # Count important words
                important_words = ['price', 'feature', 'demo', 'cost', 'benefit', 'solution', 'problem']
                count = sum(1 for word in important_words if word in sentence.lower())
                keyword_counts.append((sentence, count))
            
            if keyword_counts:
                best_sentence = max(keyword_counts, key=lambda x: x[1])[0].strip()
                if best_sentence not in summary_sentences:
                    summary_sentences.append(best_sentence)
        
        summary = '. '.join(summary_sentences)
        return summary if len(summary) <= 200 else summary[:197] + "..."
    
    async def _calculate_complexity(self, text: str) -> float:
        """Calculate text complexity score (0-1)."""
        if not text.strip():
            return 0.0
        
        # Factors for complexity
        word_count = len(text.split())
        sentence_count = len(re.split(r'[.!?]+', text))
        avg_sentence_length = word_count / max(1, sentence_count)
        
        # Long words (> 6 characters)
        long_words = [word for word in text.split() if len(word) > 6]
        long_word_ratio = len(long_words) / max(1, word_count)
        
        # Technical terms
        technical_terms = 0
        for word in text.lower().split():
            if word in ['api', 'integration', 'crm', 'analytics', 'automation', 'optimization']:
                technical_terms += 1
        technical_ratio = technical_terms / max(1, word_count)
        
        # Combine factors
        complexity = (
            min(1.0, avg_sentence_length / 20) * 0.4 +  # Sentence length factor
            long_word_ratio * 0.3 +                     # Long word factor
            technical_ratio * 0.3                       # Technical term factor
        )
        
        return min(1.0, complexity)
    
    async def _detect_engagement_signals(self, text: str) -> List[str]:
        """Detect signals of customer engagement."""
        signals = []
        text_lower = text.lower()
        
        # Check for engagement patterns
        if any(phrase in text_lower for phrase in self.sales_patterns["buying_signals"]):
            signals.append("buying_signals_detected")
        
        if any(phrase in text_lower for phrase in self.sales_patterns["urgency_indicators"]):
            signals.append("urgency_expressed")
        
        if any(phrase in text_lower for phrase in self.sales_patterns["hesitation_signals"]):
            signals.append("hesitation_detected")
        
        # Question engagement
        question_count = text.count('?')
        if question_count > 0:
            signals.append(f"questions_asked_{question_count}")
        
        # Specific interests
        if any(term in text_lower for term in ["demo", "trial", "test"]):
            signals.append("demo_interest")
        
        if any(term in text_lower for term in ["price", "cost", "pricing"]):
            signals.append("pricing_interest")
        
        if any(term in text_lower for term in ["feature", "capability", "functionality"]):
            signals.append("feature_interest")
        
        # Emotional engagement
        exclamation_count = text.count('!')
        if exclamation_count > 0:
            signals.append("emotional_engagement")
        
        return signals
    
    def _get_from_cache(self, cache_key: str) -> Optional[NLPAnalysisResult]:
        """Get analysis from cache if valid."""
        if cache_key in self.analysis_cache:
            cached_entry = self.analysis_cache[cache_key]
            if datetime.now().timestamp() - cached_entry['timestamp'] < self.cache_ttl:
                return cached_entry['result']
            else:
                del self.analysis_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: NLPAnalysisResult) -> None:
        """Cache analysis result."""
        self.analysis_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now().timestamp()
        }
    
    async def _store_analysis(
        self,
        conversation_id: str,
        result: NLPAnalysisResult
    ) -> None:
        """Store analysis results for future reference."""
        if not self.supabase_client:
            return
        
        try:
            await self.supabase_client.table("nlp_analysis").insert({
                "conversation_id": conversation_id,
                "intent": result.intent.intent.value,
                "intent_confidence": result.intent.confidence,
                "sentiment": result.sentiment.sentiment.value,
                "sentiment_polarity": result.sentiment.polarity,
                "entities": [asdict(entity) for entity in result.entities],
                "keywords": [asdict(keyword) for keyword in result.keywords],
                "language": result.language,
                "complexity_score": result.complexity_score,
                "engagement_signals": result.engagement_signals,
                "created_at": result.timestamp.isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Failed to store NLP analysis: {e}")
    
    def _update_performance_metrics(self, start_time: datetime) -> None:
        """Update performance tracking metrics."""
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        self.analysis_times.append(processing_time)
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return {
            "avg_processing_time_ms": np.mean(list(self.analysis_times)) if self.analysis_times else 0,
            "error_count": self.error_count,
            "cache_size": len(self.analysis_cache),
            "initialized": self._initialized,
            "models_loaded": {
                "spacy": self.spacy_model is not None,
                "nltk": self.nltk_initialized
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check."""
        metrics = await self.get_performance_metrics()
        
        health_status = {
            "status": "healthy",
            "initialized": self._initialized,
            "timestamp": datetime.now().isoformat(),
            "performance": metrics
        }
        
        # Check for issues
        issues = []
        if not self._initialized:
            issues.append("Service not initialized")
        if not self.spacy_model and not self.nltk_initialized:
            issues.append("No NLP models available")
        if self.error_count > 10:
            issues.append(f"High error count: {self.error_count}")
        
        if issues:
            health_status["status"] = "degraded" if len(issues) == 1 else "unhealthy"
            health_status["issues"] = issues
        
        return health_status
    
    async def cleanup(self) -> None:
        """Cleanup resources when shutting down."""
        logger.info("Cleaning up Consolidated NLP Analysis Service")
        
        # Clear caches
        self.analysis_cache.clear()
        
        # Reset state
        self._initialized = False
        
        logger.info("NLP service cleanup completed")