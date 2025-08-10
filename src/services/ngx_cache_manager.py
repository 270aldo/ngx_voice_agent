"""
NGX-specific cache manager for frequently accessed data.

This module provides caching strategies for various NGX data types
to optimize performance and reduce database load.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import hashlib

from src.services.redis_cache_service import RedisCacheService, cached
from src.utils.structured_logging import StructuredLogger
from src.models.conversation import ConversationState, CustomerData
from src.models.learning_models import LearnedModel

logger = StructuredLogger.get_logger(__name__)


class NGXCacheManager:
    """
    Cache manager for NGX-specific data.
    
    Handles caching for:
    - Conversation states
    - Customer profiles
    - ML model predictions
    - Tier detection results
    - Program recommendations
    - ROI calculations
    - Agent configurations
    """
    
    # Cache TTLs (in seconds) - AGGRESSIVE CACHING FOR <0.5s RESPONSE TIME
    TTL_CONVERSATION = 7200  # 2 hours (was 60 minutes)
    TTL_CUSTOMER = 10800  # 3 hours (was 2)
    TTL_PREDICTION = 3600  # 1 hour (was 30 minutes)
    TTL_TIER = 7200  # 2 hours (was 60 minutes)
    TTL_PROGRAM = 14400  # 4 hours (was 2)
    TTL_ROI = 7200  # 2 hours (was 60 minutes) - ROI doesn't change often
    TTL_CONFIG = 21600  # 6 hours (was 4)
    TTL_KNOWLEDGE = 259200  # 72 hours (was 48)
    TTL_PROMPT = 7200  # 2 hours - NEW: Cache optimized prompts
    TTL_RESPONSE = 3600  # 1 hour - NEW: Cache common responses
    TTL_EMOTIONAL = 1800  # 30 minutes - NEW: Cache emotional profiles
    # NEW: Ultra-fast hot responses
    TTL_HOT_RESPONSES = 10800  # 3 hours
    TTL_COMMON_QUERIES = 14400  # 4 hours
    
    def __init__(self, cache_service: RedisCacheService):
        """
        Initialize cache manager.
        
        Args:
            cache_service: Redis cache service instance
        """
        self.cache = cache_service
        self._init_cache_keys()
    
    def _init_cache_keys(self):
        """Initialize cache key prefixes."""
        self.keys = {
            "conversation": "conv",
            "customer": "cust",
            "prediction": "pred",
            "tier": "tier",
            "program": "prog",
            "roi": "roi",
            "config": "conf",
            "knowledge": "know",
            "metrics": "metr",
            "experiment": "exp"
        }
    
    # Conversation Caching
    
    async def get_conversation(self, conversation_id: str) -> Optional[ConversationState]:
        """
        Get conversation state from cache.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Conversation state or None
        """
        key = f"{self.keys['conversation']}:{conversation_id}"
        data = await self.cache.get(key)
        
        if data:
            try:
                return ConversationState(**data)
            except Exception as e:
                logger.error(f"Error deserializing conversation: {e}")
                await self.cache.delete(key)
        
        return None
    
    async def set_conversation(
        self,
        conversation_id: str,
        state: ConversationState,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache conversation state.
        
        Args:
            conversation_id: Conversation ID
            state: Conversation state
            ttl: Custom TTL
            
        Returns:
            Success status
        """
        key = f"{self.keys['conversation']}:{conversation_id}"
        data = state.model_dump()
        
        return await self.cache.set(
            key,
            data,
            ttl=ttl or self.TTL_CONVERSATION
        )
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation from cache."""
        key = f"{self.keys['conversation']}:{conversation_id}"
        return await self.cache.delete(key)
    
    # Customer Caching
    
    async def get_customer(self, customer_id: str) -> Optional[CustomerData]:
        """
        Get customer data from cache.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Customer data or None
        """
        key = f"{self.keys['customer']}:{customer_id}"
        data = await self.cache.get(key)
        
        if data:
            try:
                return CustomerData(**data)
            except Exception as e:
                logger.error(f"Error deserializing customer: {e}")
                await self.cache.delete(key)
        
        return None
    
    async def set_customer(
        self,
        customer_id: str,
        customer: CustomerData,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache customer data.
        
        Args:
            customer_id: Customer ID
            customer: Customer data
            ttl: Custom TTL
            
        Returns:
            Success status
        """
        key = f"{self.keys['customer']}:{customer_id}"
        data = customer.model_dump()
        
        return await self.cache.set(
            key,
            data,
            ttl=ttl or self.TTL_CUSTOMER
        )
    
    # ML Predictions Caching
    
    async def get_prediction(
        self,
        model_type: str,
        input_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get ML prediction from cache.
        
        Args:
            model_type: Type of ML model
            input_hash: Hash of input features
            
        Returns:
            Prediction result or None
        """
        key = f"{self.keys['prediction']}:{model_type}:{input_hash}"
        return await self.cache.get(key)
    
    async def set_prediction(
        self,
        model_type: str,
        input_hash: str,
        prediction: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache ML prediction.
        
        Args:
            model_type: Type of ML model
            input_hash: Hash of input features
            prediction: Prediction result
            ttl: Custom TTL
            
        Returns:
            Success status
        """
        key = f"{self.keys['prediction']}:{model_type}:{input_hash}"
        return await self.cache.set(
            key,
            prediction,
            ttl=ttl or self.TTL_PREDICTION
        )
    
    # Tier Detection Caching
    
    async def get_tier_detection(
        self,
        customer_id: str,
        context_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get tier detection result from cache.
        
        Args:
            customer_id: Customer ID
            context_hash: Hash of detection context
            
        Returns:
            Tier detection result or None
        """
        key = f"{self.keys['tier']}:{customer_id}:{context_hash}"
        return await self.cache.get(key)
    
    async def set_tier_detection(
        self,
        customer_id: str,
        context_hash: str,
        result: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache tier detection result.
        
        Args:
            customer_id: Customer ID
            context_hash: Hash of detection context
            result: Detection result
            ttl: Custom TTL
            
        Returns:
            Success status
        """
        key = f"{self.keys['tier']}:{customer_id}:{context_hash}"
        return await self.cache.set(
            key,
            result,
            ttl=ttl or self.TTL_TIER
        )
    
    # Program Recommendations Caching
    
    async def get_program_recommendations(
        self,
        customer_profile_hash: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get program recommendations from cache.
        
        Args:
            customer_profile_hash: Hash of customer profile
            
        Returns:
            Recommendations or None
        """
        key = f"{self.keys['program']}:rec:{customer_profile_hash}"
        return await self.cache.get(key)
    
    async def set_program_recommendations(
        self,
        customer_profile_hash: str,
        recommendations: List[Dict[str, Any]],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache program recommendations.
        
        Args:
            customer_profile_hash: Hash of customer profile
            recommendations: List of recommendations
            ttl: Custom TTL
            
        Returns:
            Success status
        """
        key = f"{self.keys['program']}:rec:{customer_profile_hash}"
        return await self.cache.set(
            key,
            recommendations,
            ttl=ttl or self.TTL_PROGRAM
        )
    
    # ROI Calculations Caching
    
    async def get_roi_calculation(
        self,
        profession: str,
        metrics_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get ROI calculation from cache.
        
        Args:
            profession: Customer profession
            metrics_hash: Hash of calculation inputs
            
        Returns:
            ROI calculation or None
        """
        key = f"{self.keys['roi']}:{profession}:{metrics_hash}"
        return await self.cache.get(key)
    
    async def set_roi_calculation(
        self,
        profession: str,
        metrics_hash: str,
        calculation: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache ROI calculation.
        
        Args:
            profession: Customer profession
            metrics_hash: Hash of calculation inputs
            calculation: ROI calculation result
            ttl: Custom TTL
            
        Returns:
            Success status
        """
        key = f"{self.keys['roi']}:{profession}:{metrics_hash}"
        return await self.cache.set(
            key,
            calculation,
            ttl=ttl or self.TTL_ROI
        )
    
    # Configuration Caching
    
    async def get_agent_config(self, config_type: str) -> Optional[Dict[str, Any]]:
        """
        Get agent configuration from cache.
        
        Args:
            config_type: Type of configuration
            
        Returns:
            Configuration or None
        """
        key = f"{self.keys['config']}:agent:{config_type}"
        return await self.cache.get(key)
    
    async def set_agent_config(
        self,
        config_type: str,
        config: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache agent configuration.
        
        Args:
            config_type: Type of configuration
            config: Configuration data
            ttl: Custom TTL
            
        Returns:
            Success status
        """
        key = f"{self.keys['config']}:agent:{config_type}"
        return await self.cache.set(
            key,
            config,
            ttl=ttl or self.TTL_CONFIG
        )
    
    # Knowledge Base Caching
    
    async def get_knowledge(self, knowledge_type: str) -> Optional[Dict[str, Any]]:
        """
        Get knowledge base data from cache.
        
        Args:
            knowledge_type: Type of knowledge (pricing, programs, etc.)
            
        Returns:
            Knowledge data or None
        """
        key = f"{self.keys['knowledge']}:{knowledge_type}"
        return await self.cache.get(key)
    
    async def set_knowledge(
        self,
        knowledge_type: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache knowledge base data.
        
        Args:
            knowledge_type: Type of knowledge
            data: Knowledge data
            ttl: Custom TTL
            
        Returns:
            Success status
        """
        key = f"{self.keys['knowledge']}:{knowledge_type}"
        return await self.cache.set(
            key,
            data,
            ttl=ttl or self.TTL_KNOWLEDGE
        )
    
    # Metrics and Analytics Caching
    
    async def increment_metric(
        self,
        metric_type: str,
        metric_name: str,
        amount: int = 1
    ) -> Optional[int]:
        """
        Increment a metric counter.
        
        Args:
            metric_type: Type of metric
            metric_name: Metric name
            amount: Increment amount
            
        Returns:
            New counter value
        """
        key = f"{self.keys['metrics']}:{metric_type}:{metric_name}"
        return await self.cache.increment(key, amount)
    
    async def get_metric(
        self,
        metric_type: str,
        metric_name: str
    ) -> int:
        """
        Get metric value.
        
        Args:
            metric_type: Type of metric
            metric_name: Metric name
            
        Returns:
            Metric value
        """
        key = f"{self.keys['metrics']}:{metric_type}:{metric_name}"
        value = await self.cache.get(key)
        return int(value) if value else 0
    
    # Experiment Results Caching
    
    async def get_experiment_result(
        self,
        experiment_id: str,
        variant: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get A/B test experiment result from cache.
        
        Args:
            experiment_id: Experiment ID
            variant: Experiment variant
            
        Returns:
            Experiment result or None
        """
        key = f"{self.keys['experiment']}:{experiment_id}:{variant}"
        return await self.cache.get(key)
    
    async def set_experiment_result(
        self,
        experiment_id: str,
        variant: str,
        result: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache A/B test experiment result.
        
        Args:
            experiment_id: Experiment ID
            variant: Experiment variant
            result: Experiment result
            ttl: Custom TTL
            
        Returns:
            Success status
        """
        key = f"{self.keys['experiment']}:{experiment_id}:{variant}"
        return await self.cache.set(
            key,
            result,
            ttl=ttl or self.TTL_PREDICTION
        )
    
    # Batch Operations
    
    async def get_conversations_batch(
        self,
        conversation_ids: List[str]
    ) -> Dict[str, ConversationState]:
        """
        Get multiple conversations at once.
        
        Args:
            conversation_ids: List of conversation IDs
            
        Returns:
            Dict of conversation states
        """
        keys = [f"{self.keys['conversation']}:{cid}" for cid in conversation_ids]
        data = await self.cache.get_many(keys)
        
        results = {}
        for cid, key in zip(conversation_ids, keys):
            if key in data:
                try:
                    results[cid] = ConversationState(**data[key])
                except Exception as e:
                    logger.error(f"Error deserializing conversation {cid}: {e}")
        
        return results
    
    # NEW: Prompt and Response Caching for Performance
    
    async def get_cached_prompt(
        self,
        context_hash: str,
        prompt_type: str = "main"
    ) -> Optional[str]:
        """
        Get cached optimized prompt.
        
        Args:
            context_hash: Hash of conversation context
            prompt_type: Type of prompt (main, empathy, sales)
            
        Returns:
            Cached prompt or None
        """
        key = f"prompt:{prompt_type}:{context_hash}"
        return await self.cache.get(key)
    
    async def set_cached_prompt(
        self,
        context_hash: str,
        prompt: str,
        prompt_type: str = "main",
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache an optimized prompt.
        
        Args:
            context_hash: Hash of conversation context
            prompt: Optimized prompt
            prompt_type: Type of prompt
            ttl: Custom TTL
            
        Returns:
            Success status
        """
        key = f"prompt:{prompt_type}:{context_hash}"
        return await self.cache.set(
            key,
            prompt,
            ttl=ttl or self.TTL_PROMPT
        )
    
    async def get_cached_response(
        self,
        message_hash: str,
        response_type: str = "general"
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response for common questions.
        
        Args:
            message_hash: Hash of user message
            response_type: Type of response
            
        Returns:
            Cached response or None
        """
        key = f"response:{response_type}:{message_hash}"
        return await self.cache.get(key)
    
    async def set_cached_response(
        self,
        message_hash: str,
        response: Dict[str, Any],
        response_type: str = "general",
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache a response for common questions.
        
        Args:
            message_hash: Hash of user message
            response: Response data
            response_type: Type of response
            ttl: Custom TTL
            
        Returns:
            Success status
        """
        key = f"response:{response_type}:{message_hash}"
        return await self.cache.set(
            key,
            response,
            ttl=ttl or self.TTL_RESPONSE
        )
    
    async def get_cached_emotional_profile(
        self,
        customer_id: str,
        message_count: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached emotional profile.
        
        Args:
            customer_id: Customer ID
            message_count: Number of messages in conversation
            
        Returns:
            Cached emotional profile or None
        """
        key = f"emotional:{customer_id}:{message_count}"
        return await self.cache.get(key)
    
    async def set_cached_emotional_profile(
        self,
        customer_id: str,
        message_count: int,
        profile: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache emotional profile.
        
        Args:
            customer_id: Customer ID
            message_count: Number of messages in conversation
            profile: Emotional profile data
            ttl: Custom TTL
            
        Returns:
            Success status
        """
        key = f"emotional:{customer_id}:{message_count}"
        return await self.cache.set(
            key,
            profile,
            ttl=ttl or self.TTL_EMOTIONAL
        )
    
    async def preload_common_responses(self) -> int:
        """
        Preload cache with common responses for instant replies.
        
        Returns:
            Number of responses cached
        """
        common_questions = {
            # Pricing questions
            "precio": {
                "response": "Nuestros programas van desde $79 hasta $199 al mes, dependiendo de tus objetivos específicos.",
                "type": "pricing"
            },
            "cuanto cuesta": {
                "response": "Los programas de NGX tienen diferentes precios según tus necesidades: NGX Starter ($79/mes), NGX Pro ($129/mes) y NGX Elite ($199/mes).",
                "type": "pricing"
            },
            "es caro": {
                "response": "Entiendo tu preocupación. Considera que es una inversión en tu salud y productividad que puede ahorrarte miles en costos médicos y aumentar tus ingresos significativamente.",
                "type": "pricing"
            },
            # Information questions
            "que es ngx": {
                "response": "NGX es un ecosistema de optimización humana que combina tecnología HIE con coaching personalizado.",
                "type": "info"
            },
            "como funciona": {
                "response": "Trabajamos con un sistema de 11 agentes especializados que se adaptan a tus necesidades únicas.",
                "type": "explanation"
            },
            "que incluye": {
                "response": "Incluye acceso a 11 agentes especializados, planes personalizados, seguimiento biométrico, comunidad exclusiva y soporte 24/7.",
                "type": "features"
            },
            # Guarantee questions
            "garantia": {
                "response": "Ofrecemos garantía de satisfacción de 30 días. Si no ves resultados, te devolvemos tu dinero.",
                "type": "guarantee"
            },
            "si no funciona": {
                "response": "Tienes nuestra garantía de 30 días. Además, nuestro 95% de tasa de retención demuestra que funciona para casi todos.",
                "type": "guarantee"
            },
            # ROI questions
            "vale la pena": {
                "response": "Absolutamente. Nuestros clientes reportan un ROI promedio de 312% en el primer año, entre mayor productividad y menores gastos médicos.",
                "type": "roi"
            },
            "beneficios": {
                "response": "Los beneficios incluyen: +40% energía, -60% estrés, mejor sueño, mayor claridad mental, y un aumento promedio de 23% en productividad.",
                "type": "benefits"
            },
            # Common objections
            "no tengo tiempo": {
                "response": "Justamente por eso necesitas NGX. Solo requiere 15-20 minutos al día y te ahorrará horas de baja productividad.",
                "type": "objection"
            },
            "debo pensarlo": {
                "response": "Por supuesto, es una decisión importante. ¿Qué información adicional necesitas para tomar la mejor decisión?",
                "type": "objection"
            }
        }
        
        count = 0
        for question, data in common_questions.items():
            question_hash = hashlib.md5(question.encode()).hexdigest()
            success = await self.set_cached_response(
                question_hash,
                data,
                response_type=data["type"]
            )
            if success:
                count += 1
        
        return count
    
    async def warm_cache(self) -> Dict[str, int]:
        """
        Warm up cache with frequently accessed data.
        
        Returns:
            Statistics of warmed entries
        """
        stats = {
            "knowledge": 0,
            "config": 0,
            "responses": 0,
            "total": 0
        }
        
        try:
            # Cache knowledge base data
            from src.knowledge.ngx_consultant_knowledge import NGXConsultantKnowledge
            knowledge = NGXConsultantKnowledge()
            
            # Cache pricing info
            await self.set_knowledge("pricing", {
                "tiers": {prog: data.pricing_tiers for prog, data in knowledge.ngx_programs.items()},
                "programs": knowledge.ngx_programs
            })
            stats["knowledge"] += 1
            
            # Cache program details
            for program_name, program_data in knowledge.ngx_programs.items():
                await self.set_knowledge(
                    f"program:{program_name}",
                    program_data
                )
                stats["knowledge"] += 1
            
            # Cache agent configurations
            config_types = ["prompts", "personality", "voice", "behavior"]
            for config_type in config_types:
                # This would load from your config files
                await self.set_agent_config(config_type, {
                    "type": config_type,
                    "loaded_at": datetime.now().isoformat()
                })
                stats["config"] += 1
            
            # Preload common responses for instant replies
            responses_cached = await self.preload_common_responses()
            stats["responses"] = responses_cached
            
            stats["total"] = sum(stats.values())
            logger.info(f"Cache warmed with {stats['total']} entries", extra=stats)
            
        except Exception as e:
            logger.error(f"Error warming cache: {e}")
        
        return stats
    
    async def clear_expired(self) -> int:
        """
        Clear expired cache entries.
        
        Returns:
            Number of entries cleared
        """
        # Redis handles TTL automatically, but we can clear specific patterns
        patterns = [
            f"{self.keys['prediction']}:*",
            f"{self.keys['roi']}:*"
        ]
        
        total_cleared = 0
        for pattern in patterns:
            # This would scan and delete old entries
            # Implementation depends on your needs
            pass
        
        return total_cleared
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Cache statistics
        """
        stats = await self.cache.get_stats()
        
        # Add NGX-specific stats
        ngx_stats = {}
        for key_type, prefix in self.keys.items():
            count_key = f"stats:count:{prefix}"
            ngx_stats[f"{key_type}_count"] = await self.get_metric("stats", f"count:{prefix}")
        
        return {
            **stats,
            "ngx_stats": ngx_stats,
            "cache_keys": list(self.keys.keys())
        }


# Caching decorators for common operations

def cache_conversation(ttl: Optional[int] = None):
    """Decorator to cache conversation operations."""
    def decorator(func):
        async def wrapper(self, conversation_id: str, *args, **kwargs):
            # Try cache first
            cache_manager = getattr(self, '_cache_manager', None)
            if cache_manager:
                cached_state = await cache_manager.get_conversation(conversation_id)
                if cached_state:
                    return cached_state
            
            # Execute function
            result = await func(self, conversation_id, *args, **kwargs)
            
            # Cache result
            if cache_manager and result:
                await cache_manager.set_conversation(conversation_id, result, ttl=ttl)
            
            return result
        return wrapper
    return decorator


def cache_customer(ttl: Optional[int] = None):
    """Decorator to cache customer operations."""
    def decorator(func):
        async def wrapper(self, customer_id: str, *args, **kwargs):
            # Try cache first
            cache_manager = getattr(self, '_cache_manager', None)
            if cache_manager:
                cached_customer = await cache_manager.get_customer(customer_id)
                if cached_customer:
                    return cached_customer
            
            # Execute function
            result = await func(self, customer_id, *args, **kwargs)
            
            # Cache result
            if cache_manager and result:
                await cache_manager.set_customer(customer_id, result, ttl=ttl)
            
            return result
        return wrapper
    return decorator


def invalidate_conversation_cache(conversation_id: str):
    """Decorator to invalidate conversation cache after update."""
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            # Execute function
            result = await func(self, *args, **kwargs)
            
            # Invalidate cache
            cache_manager = getattr(self, '_cache_manager', None)
            if cache_manager:
                await cache_manager.delete_conversation(conversation_id)
            
            return result
        return wrapper
    return decorator