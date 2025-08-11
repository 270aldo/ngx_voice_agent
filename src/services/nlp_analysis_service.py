"""
NLP Analysis Service - Consolidated natural language processing and intent analysis functionality.

This service consolidates functionality from:
- intent_analysis_service.py
- enhanced_intent_analysis_service.py
- contextual_intent_service.py
- entity_recognition_service.py
- keyword_extraction_service.py
- nlp_integration_service.py
- question_classification_service.py

Provides:
- Unified intent analysis and classification
- Entity recognition and extraction
- Contextual understanding
- Keyword and key phrase extraction
- Question classification
- Sentiment analysis integration
- Multi-language support
"""

import logging
import re
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict, Counter

from src.models.conversation import ConversationState, CustomerData
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)


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
class Entity:
    """Named entity result."""
    text: str
    entity_type: EntityType
    confidence: float
    start_pos: int
    end_pos: int
    normalized_value: Optional[str] = None
    context: Optional[str] = None


@dataclass
class KeywordResult:
    """Keyword extraction result."""
    keyword: str
    importance: float
    frequency: int
    category: Optional[str] = None
    context: List[str] = field(default_factory=list)


@dataclass
class QuestionAnalysis:
    """Question analysis result."""
    question_type: QuestionType
    confidence: float
    topic: Optional[str] = None
    urgency: float = 0.5
    complexity: float = 0.5


@dataclass
class NLPAnalysisResult:
    """Complete NLP analysis result."""
    intent_result: IntentResult
    entities: List[Entity]
    keywords: List[KeywordResult]
    question_analysis: Optional[QuestionAnalysis] = None
    sentiment_score: float = 0.0
    language: str = "spanish"
    processing_time_ms: float = 0.0


class NLPAnalysisService:
    """
    Unified NLP analysis service for comprehensive text understanding.
    
    Features:
    - Intent detection and classification
    - Named entity recognition
    - Keyword and key phrase extraction
    - Question type classification
    - Contextual understanding
    - Multi-language support
    - Real-time processing
    """
    
    def __init__(self):
        """Initialize NLP analysis service."""
        self.intent_patterns = self._initialize_intent_patterns()
        self.entity_patterns = self._initialize_entity_patterns()
        self.keyword_categories = self._initialize_keyword_categories()
        self.question_patterns = self._initialize_question_patterns()
        self.context_memory: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.language_patterns = self._initialize_language_patterns()
        
        logger.info("NLPAnalysisService initialized")
    
    def _initialize_intent_patterns(self) -> Dict[IntentType, Dict[str, Any]]:
        """Initialize intent detection patterns."""
        return {
            IntentType.PRICING_INQUIRY: {
                "keywords": ["precio", "costo", "cuanto", "vale", "precios", "tarifas", "inversión"],
                "phrases": ["cuánto cuesta", "qué precio", "cuál es el costo", "precio de", "cuánto vale"],
                "patterns": [
                    r"cu[aá]nto\s+(cuesta|vale|es)",
                    r"qu[eé]\s+precio",
                    r"cu[aá]l\s+es\s+el\s+costo",
                    r"precio\s+de",
                    r"tarifas?\s+de"
                ],
                "confidence_boost": 0.3
            },
            IntentType.FEATURE_QUESTION: {
                "keywords": ["funciona", "características", "qué hace", "cómo", "capacidades", "opciones"],
                "phrases": ["qué hace", "cómo funciona", "qué incluye", "características de", "opciones de"],
                "patterns": [
                    r"qu[eé]\s+hace",
                    r"c[oó]mo\s+funciona",
                    r"qu[eé]\s+incluye",
                    r"caracter[ií]sticas\s+de",
                    r"opciones\s+de"
                ],
                "confidence_boost": 0.2
            },
            IntentType.DEMO_REQUEST: {
                "keywords": ["demo", "demostración", "ver", "mostrar", "prueba", "ejemplo"],
                "phrases": ["quiero ver", "puedes mostrar", "demo de", "demostración", "ver en acción"],
                "patterns": [
                    r"quiero\s+ver",
                    r"puedes?\s+mostrar",
                    r"demo\s+de",
                    r"demostraci[oó]n",
                    r"ver\s+en\s+acci[oó]n",
                    r"probar"
                ],
                "confidence_boost": 0.4
            },
            IntentType.OBJECTION_RAISING: {
                "keywords": ["pero", "sin embargo", "no creo", "dudo", "problema", "preocupa"],
                "phrases": ["pero yo", "sin embargo", "no creo que", "me preocupa", "el problema es"],
                "patterns": [
                    r"pero\s+yo",
                    r"sin\s+embargo",
                    r"no\s+creo\s+que",
                    r"me\s+preocupa",
                    r"el\s+problema\s+es",
                    r"no\s+estoy\s+seguro"
                ],
                "confidence_boost": 0.25
            },
            IntentType.CLOSING_SIGNAL: {
                "keywords": ["quiero", "necesito", "cuando", "empezar", "contratar", "comprar"],
                "phrases": ["quiero empezar", "cuándo podemos", "necesito esto", "vamos a hacerlo", "me interesa"],
                "patterns": [
                    r"quiero\s+empezar",
                    r"cu[aá]ndo\s+podemos",
                    r"necesito\s+esto",
                    r"vamos\s+a\s+hacerlo",
                    r"me\s+interesa",
                    r"cu[aá]ndo\s+empiezo"
                ],
                "confidence_boost": 0.5
            },
            IntentType.STALLING: {
                "keywords": ["después", "luego", "pensarlo", "consultar", "tiempo", "decidir"],
                "phrases": ["lo voy a pensar", "después te digo", "necesito tiempo", "voy a consultar"],
                "patterns": [
                    r"lo\s+voy\s+a\s+pensar",
                    r"despu[eé]s\s+te\s+digo",
                    r"necesito\s+tiempo",
                    r"voy\s+a\s+consultar",
                    r"d[eé]jame\s+pensarlo"
                ],
                "confidence_boost": 0.3
            }
        }
    
    def _initialize_entity_patterns(self) -> Dict[EntityType, Dict[str, Any]]:
        """Initialize entity recognition patterns."""
        return {
            EntityType.PRICE: {
                "patterns": [
                    r"(\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
                    r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*d[oó]lares?)",
                    r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*pesos)",
                    r"(\d+\s*mil\s*pesos)",
                    r"(\d+k)"
                ]
            },
            EntityType.PERCENTAGE: {
                "patterns": [
                    r"(\d+(?:\.\d+)?%)",
                    r"(\d+(?:\.\d+)?\s*por\s*ciento)"
                ]
            },
            EntityType.DATE: {
                "patterns": [
                    r"(\d{1,2}\/\d{1,2}\/\d{2,4})",
                    r"(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})",
                    r"(hoy|mañana|ayer)",
                    r"(la\s+pr[oó]xima\s+semana)",
                    r"(el\s+pr[oó]ximo\s+mes)"
                ]
            },
            EntityType.TIME: {
                "patterns": [
                    r"(\d{1,2}:\d{2}(?:\s*[ap]m)?)",
                    r"(en\s+la\s+mañana)",
                    r"(en\s+la\s+tarde)",
                    r"(en\s+la\s+noche)",
                    r"(ahora\s+mismo)"
                ]
            },
            EntityType.EMAIL: {
                "patterns": [
                    r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
                ]
            },
            EntityType.PHONE: {
                "patterns": [
                    r"(\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})",
                    r"(\d{10})",
                    r"(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})"
                ]
            },
            EntityType.PRODUCT: {
                "keywords": ["NGX", "AGENTS", "GENESIS", "CLOSER", "BLOG", "LEADS", "ACADEMY"],
                "patterns": [
                    r"(NGX\s+\w+)",
                    r"(AGENTS\s+\w+)",
                    r"(sistema\s+NGX)"
                ]
            }
        }
    
    def _initialize_keyword_categories(self) -> Dict[str, List[str]]:
        """Initialize keyword categories for extraction."""
        return {
            "business": [
                "gimnasio", "gym", "negocio", "empresa", "clientes", "miembros", "ventas",
                "ingresos", "crecimiento", "automatización", "eficiencia"
            ],
            "technology": [
                "sistema", "software", "IA", "inteligencia artificial", "automatización",
                "bot", "chatbot", "API", "integración", "plataforma"
            ],
            "features": [
                "seguimiento", "análisis", "reportes", "métricas", "dashboard",
                "notificaciones", "recordatorios", "personalización"
            ],
            "pain_points": [
                "problema", "dificultad", "complicado", "difícil", "frustrante",
                "tiempo", "manual", "repetitivo", "costoso"
            ],
            "emotions": [
                "emocionado", "interesado", "preocupado", "dudoso", "confiado",
                "skeptico", "ansioso", "feliz", "satisfecho"
            ]
        }
    
    def _initialize_question_patterns(self) -> Dict[QuestionType, List[str]]:
        """Initialize question classification patterns."""
        return {
            QuestionType.YES_NO: [
                r"^¿?(puedes?|puede|es|está|tienen?|hay|funciona|sirve)",
                r"¿verdad\?",
                r"¿no\?",
                r"¿cierto\?"
            ],
            QuestionType.WHAT: [
                r"^¿?qué\s",
                r"^¿?cuáles?\s",
                r"^¿?cuál\s"
            ],
            QuestionType.HOW: [
                r"^¿?cómo\s",
                r"^¿?de\s+qué\s+manera",
                r"^¿?de\s+qué\s+forma"
            ],
            QuestionType.WHY: [
                r"^¿?por\s+qué\s",
                r"^¿?para\s+qué\s",
                r"^¿?cuál\s+es\s+la\s+razón"
            ],
            QuestionType.WHEN: [
                r"^¿?cuándo\s",
                r"^¿?a\s+qué\s+hora",
                r"^¿?en\s+qué\s+momento"
            ],
            QuestionType.WHERE: [
                r"^¿?dónde\s",
                r"^¿?en\s+dónde",
                r"^¿?adónde"
            ],
            QuestionType.HOW_MUCH: [
                r"^¿?cuánto\s+(cuesta|vale|es)",
                r"^¿?qué\s+precio",
                r"^¿?cuál\s+es\s+el\s+costo"
            ],
            QuestionType.HOW_MANY: [
                r"^¿?cuántos?\s",
                r"^¿?qué\s+cantidad"
            ]
        }
    
    def _initialize_language_patterns(self) -> Dict[str, List[str]]:
        """Initialize language detection patterns."""
        return {
            "spanish": [
                "que", "con", "para", "por", "como", "más", "muy", "puede", "hacer",
                "tiene", "esto", "todo", "bien", "bueno", "gracias", "hola"
            ],
            "english": [
                "the", "and", "for", "with", "this", "that", "have", "can", "will",
                "would", "could", "should", "good", "great", "thank", "hello"
            ]
        }
    
    async def analyze_text(
        self,
        text: str,
        conversation_context: Optional[Dict[str, Any]] = None,
        customer_id: Optional[str] = None
    ) -> NLPAnalysisResult:
        """
        Perform comprehensive NLP analysis on text.
        
        Args:
            text: Text to analyze
            conversation_context: Current conversation context
            customer_id: Customer ID for context memory
            
        Returns:
            Complete NLP analysis result
        """
        start_time = datetime.now()
        
        # Language detection
        language = self._detect_language(text)
        
        # Intent analysis
        intent_result = await self._analyze_intent(text, conversation_context)
        
        # Entity recognition
        entities = await self._extract_entities(text)
        
        # Keyword extraction
        keywords = await self._extract_keywords(text)
        
        # Question analysis (if text contains questions)
        question_analysis = None
        if self._is_question(text):
            question_analysis = await self._analyze_question(text)
        
        # Basic sentiment analysis
        sentiment_score = self._analyze_sentiment(text)
        
        # Update context memory
        if customer_id:
            self._update_context_memory(customer_id, text, intent_result, entities)
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        result = NLPAnalysisResult(
            intent_result=intent_result,
            entities=entities,
            keywords=keywords,
            question_analysis=question_analysis,
            sentiment_score=sentiment_score,
            language=language,
            processing_time_ms=processing_time
        )
        
        logger.info(f"NLP analysis completed in {processing_time:.1f}ms: {intent_result.intent}")
        return result
    
    def _detect_language(self, text: str) -> str:
        """Detect text language."""
        text_lower = text.lower()
        
        spanish_count = sum(1 for word in self.language_patterns["spanish"] if word in text_lower)
        english_count = sum(1 for word in self.language_patterns["english"] if word in text_lower)
        
        return "english" if english_count > spanish_count else "spanish"
    
    async def _analyze_intent(
        self,
        text: str,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> IntentResult:
        """Analyze customer intent from text."""
        text_lower = text.lower()
        intent_scores: Dict[IntentType, float] = {}
        
        # Analyze against each intent pattern
        for intent_type, patterns in self.intent_patterns.items():
            score = 0.0
            reasoning = []
            
            # Keyword matching
            keyword_matches = sum(1 for keyword in patterns["keywords"] if keyword in text_lower)
            if keyword_matches > 0:
                score += keyword_matches * 0.2
                reasoning.append(f"Found {keyword_matches} relevant keywords")
            
            # Phrase matching
            phrase_matches = sum(1 for phrase in patterns["phrases"] if phrase in text_lower)
            if phrase_matches > 0:
                score += phrase_matches * 0.3
                reasoning.append(f"Matched {phrase_matches} key phrases")
            
            # Pattern matching (regex)
            pattern_matches = sum(1 for pattern in patterns["patterns"] if re.search(pattern, text_lower))
            if pattern_matches > 0:
                score += pattern_matches * 0.4
                reasoning.append(f"Matched {pattern_matches} patterns")
            
            # Apply confidence boost
            if score > 0:
                score += patterns["confidence_boost"]
            
            # Context boost
            if conversation_context:
                context_boost = self._calculate_context_boost(intent_type, conversation_context)
                score += context_boost
                if context_boost > 0:
                    reasoning.append(f"Context boost applied (+{context_boost:.2f})")
            
            if score > 0:
                intent_scores[intent_type] = min(score, 1.0)
                intent_scores[f"{intent_type}_reasoning"] = reasoning
        
        # Determine primary intent
        if intent_scores:
            primary_intent = max(
                (k for k in intent_scores.keys() if not k.endswith("_reasoning")),
                key=lambda x: intent_scores[x]
            )
            confidence = intent_scores[primary_intent]
            reasoning = intent_scores.get(f"{primary_intent}_reasoning", [])
        else:
            primary_intent = IntentType.INFORMATION_SEEKING  # Default
            confidence = 0.3
            reasoning = ["No specific intent patterns detected, defaulting to information seeking"]
        
        # Find sub-intents (other high-scoring intents)
        sub_intents = [
            intent for intent, score in intent_scores.items()
            if not intent.endswith("_reasoning") and intent != primary_intent and score > 0.4
        ]
        
        return IntentResult(
            intent=primary_intent,
            confidence=confidence,
            reasoning=reasoning,
            sub_intents=sub_intents
        )
    
    def _calculate_context_boost(
        self,
        intent_type: IntentType,
        conversation_context: Dict[str, Any]
    ) -> float:
        """Calculate context-based boost for intent confidence."""
        boost = 0.0
        
        stage = conversation_context.get("stage", "discovery")
        previous_intents = conversation_context.get("previous_intents", [])
        
        # Stage-based boosts
        stage_boosts = {
            IntentType.PRICING_INQUIRY: {"presentation": 0.2, "closing": 0.3},
            IntentType.DEMO_REQUEST: {"discovery": 0.2, "presentation": 0.1},
            IntentType.CLOSING_SIGNAL: {"closing": 0.3, "negotiation": 0.2},
            IntentType.OBJECTION_RAISING: {"presentation": 0.2, "closing": 0.3},
            IntentType.STALLING: {"closing": 0.2, "negotiation": 0.3}
        }
        
        if intent_type in stage_boosts and stage in stage_boosts[intent_type]:
            boost += stage_boosts[intent_type][stage]
        
        # Sequential intent boosts
        if previous_intents:
            last_intent = previous_intents[-1] if previous_intents else None
            
            # Common intent progressions
            progressions = {
                IntentType.INFORMATION_SEEKING: [IntentType.FEATURE_QUESTION, IntentType.PRICING_INQUIRY],
                IntentType.FEATURE_QUESTION: [IntentType.DEMO_REQUEST, IntentType.PRICING_INQUIRY],
                IntentType.PRICING_INQUIRY: [IntentType.OBJECTION_RAISING, IntentType.CLOSING_SIGNAL],
                IntentType.DEMO_REQUEST: [IntentType.PRICING_INQUIRY, IntentType.CLOSING_SIGNAL]
            }
            
            if last_intent in progressions and intent_type in progressions[last_intent]:
                boost += 0.15
        
        return boost
    
    async def _extract_entities(self, text: str) -> List[Entity]:
        """Extract named entities from text."""
        entities = []
        
        for entity_type, config in self.entity_patterns.items():
            # Pattern-based extraction
            if "patterns" in config:
                for pattern in config["patterns"]:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        entity = Entity(
                            text=match.group(1) if match.groups() else match.group(0),
                            entity_type=entity_type,
                            confidence=0.8,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            normalized_value=self._normalize_entity_value(
                                match.group(1) if match.groups() else match.group(0),
                                entity_type
                            )
                        )
                        entities.append(entity)
            
            # Keyword-based extraction
            if "keywords" in config:
                text_lower = text.lower()
                for keyword in config["keywords"]:
                    if keyword.lower() in text_lower:
                        start_pos = text_lower.index(keyword.lower())
                        entity = Entity(
                            text=keyword,
                            entity_type=entity_type,
                            confidence=0.6,
                            start_pos=start_pos,
                            end_pos=start_pos + len(keyword)
                        )
                        entities.append(entity)
        
        # Remove duplicates and sort by position
        unique_entities = []
        seen_positions = set()
        
        for entity in sorted(entities, key=lambda x: x.start_pos):
            pos_key = (entity.start_pos, entity.end_pos, entity.entity_type)
            if pos_key not in seen_positions:
                unique_entities.append(entity)
                seen_positions.add(pos_key)
        
        logger.debug(f"Extracted {len(unique_entities)} entities")
        return unique_entities
    
    def _normalize_entity_value(self, value: str, entity_type: EntityType) -> Optional[str]:
        """Normalize entity values for consistent representation."""
        if entity_type == EntityType.PRICE:
            # Extract numeric value from price
            numeric_match = re.search(r'([\d,]+(?:\.\d{2})?)', value)
            if numeric_match:
                return numeric_match.group(1).replace(',', '')
        
        elif entity_type == EntityType.PERCENTAGE:
            # Extract numeric percentage
            numeric_match = re.search(r'(\d+(?:\.\d+)?)', value)
            if numeric_match:
                return numeric_match.group(1)
        
        elif entity_type == EntityType.EMAIL:
            return value.lower()
        
        elif entity_type == EntityType.PHONE:
            # Normalize phone number format
            digits = re.sub(r'[^\d]', '', value)
            if len(digits) == 10:
                return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
            return digits
        
        return value
    
    async def _extract_keywords(self, text: str) -> List[KeywordResult]:
        """Extract keywords and categorize them by importance."""
        text_lower = text.lower()
        keywords = []
        
        # Extract keywords by category
        for category, category_keywords in self.keyword_categories.items():
            for keyword in category_keywords:
                if keyword.lower() in text_lower:
                    # Count frequency
                    frequency = text_lower.count(keyword.lower())
                    
                    # Calculate importance based on category and frequency
                    category_weights = {
                        "business": 0.9,
                        "technology": 0.8,
                        "features": 0.7,
                        "pain_points": 0.8,
                        "emotions": 0.6
                    }
                    
                    importance = category_weights.get(category, 0.5) * min(1.0, frequency / 2.0)
                    
                    keywords.append(KeywordResult(
                        keyword=keyword,
                        importance=importance,
                        frequency=frequency,
                        category=category,
                        context=self._extract_keyword_context(text, keyword)
                    ))
        
        # Sort by importance and return top keywords
        keywords.sort(key=lambda x: x.importance, reverse=True)
        return keywords[:10]  # Return top 10 keywords
    
    def _extract_keyword_context(self, text: str, keyword: str) -> List[str]:
        """Extract context around keywords."""
        contexts = []
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        start = 0
        while True:
            pos = text_lower.find(keyword_lower, start)
            if pos == -1:
                break
            
            # Extract context (20 characters before and after)
            context_start = max(0, pos - 20)
            context_end = min(len(text), pos + len(keyword) + 20)
            context = text[context_start:context_end].strip()
            
            if context not in contexts:
                contexts.append(context)
            
            start = pos + 1
        
        return contexts
    
    def _is_question(self, text: str) -> bool:
        """Determine if text contains questions."""
        return bool(re.search(r'[¿?]|^(qué|cómo|cuándo|dónde|por qué|para qué|cuál|cuánto)', text, re.IGNORECASE))
    
    async def _analyze_question(self, text: str) -> QuestionAnalysis:
        """Analyze question type and characteristics."""
        text_lower = text.lower().strip()
        
        # Determine question type
        question_type = QuestionType.WHAT  # Default
        confidence = 0.3
        
        for q_type, patterns in self.question_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    question_type = q_type
                    confidence = 0.8
                    break
            if confidence > 0.5:
                break
        
        # Determine topic
        topic = None
        topic_keywords = {
            "pricing": ["precio", "costo", "cuánto", "vale", "tarifas"],
            "features": ["funciona", "hace", "características", "opciones"],
            "process": ["cómo", "proceso", "pasos", "manera"],
            "timing": ["cuándo", "tiempo", "momento", "fecha"],
            "support": ["ayuda", "soporte", "problema", "error"]
        }
        
        for topic_name, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topic = topic_name
                break
        
        # Calculate urgency and complexity
        urgency_indicators = ["urgente", "ya", "ahora", "rápido", "inmediato"]
        urgency = min(1.0, sum(1 for indicator in urgency_indicators if indicator in text_lower) * 0.3)
        
        complexity_indicators = ["complicado", "difícil", "complejo", "detallado", "técnico"]
        complexity = min(1.0, 0.5 + sum(1 for indicator in complexity_indicators if indicator in text_lower) * 0.2)
        
        return QuestionAnalysis(
            question_type=question_type,
            confidence=confidence,
            topic=topic,
            urgency=urgency,
            complexity=complexity
        )
    
    def _analyze_sentiment(self, text: str) -> float:
        """Basic sentiment analysis (-1 to 1)."""
        positive_words = [
            "bueno", "excelente", "perfecto", "genial", "fantástico", "increíble",
            "me gusta", "interesante", "útil", "fácil", "rápido"
        ]
        
        negative_words = [
            "malo", "terrible", "horrible", "difícil", "complicado", "caro",
            "no me gusta", "problema", "error", "lento", "confuso"
        ]
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        # Normalize to -1 to 1 scale
        total_words = len(text.split())
        if total_words == 0:
            return 0.0
        
        sentiment = (positive_count - negative_count) / max(total_words, 1)
        return max(-1.0, min(1.0, sentiment * 5))  # Scale and clamp
    
    def _update_context_memory(
        self,
        customer_id: str,
        text: str,
        intent_result: IntentResult,
        entities: List[Entity]
    ) -> None:
        """Update context memory for customer."""
        context_entry = {
            "timestamp": datetime.now().isoformat(),
            "text": text[:200],  # Store first 200 characters
            "intent": intent_result.intent.value,
            "confidence": intent_result.confidence,
            "entities": [
                {"type": e.entity_type.value, "text": e.text}
                for e in entities[:5]  # Store top 5 entities
            ]
        }
        
        self.context_memory[customer_id].append(context_entry)
        
        # Keep only last 10 context entries
        self.context_memory[customer_id] = self.context_memory[customer_id][-10:]
    
    async def get_context_summary(self, customer_id: str) -> Dict[str, Any]:
        """Get conversation context summary for customer."""
        if customer_id not in self.context_memory:
            return {"message": "No context available"}
        
        contexts = self.context_memory[customer_id]
        
        # Analyze patterns
        intent_counts = Counter(ctx["intent"] for ctx in contexts)
        entity_counts = Counter(
            entity["type"] for ctx in contexts
            for entity in ctx["entities"]
        )
        
        avg_confidence = sum(ctx["confidence"] for ctx in contexts) / len(contexts)
        
        return {
            "total_interactions": len(contexts),
            "most_common_intents": dict(intent_counts.most_common(3)),
            "most_common_entities": dict(entity_counts.most_common(3)),
            "average_confidence": round(avg_confidence, 3),
            "conversation_span_minutes": (
                datetime.fromisoformat(contexts[-1]["timestamp"]) -
                datetime.fromisoformat(contexts[0]["timestamp"])
            ).total_seconds() / 60 if len(contexts) > 1 else 0
        }
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        return {
            "intent_patterns": len(self.intent_patterns),
            "entity_types": len(self.entity_patterns),
            "keyword_categories": len(self.keyword_categories),
            "question_types": len(self.question_patterns),
            "customers_in_memory": len(self.context_memory),
            "total_context_entries": sum(len(contexts) for contexts in self.context_memory.values()),
            "supported_languages": list(self.language_patterns.keys())
        }