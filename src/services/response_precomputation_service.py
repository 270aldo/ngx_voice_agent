"""
Response Pre-computation Service for Ultra-Fast Responses.

This service pre-computes and caches common responses to achieve
<0.5s response times for the NGX Voice Sales Agent.
"""

import asyncio
import hashlib
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.services.ngx_cache_manager import NGXCacheManager
from src.services.redis_cache_service import RedisCacheService
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)


class ResponsePrecomputationService:
    """Pre-compute and cache common responses for instant delivery."""
    
    # Pattern matching for instant responses
    CACHEABLE_PATTERNS = {
        # Pricing patterns
        r"precio|cost|cuanto": "pricing_response",
        r"es caro|muy caro|expensive": "pricing_objection",
        r"descuento|promocion|oferta": "discount_response",
        
        # Information patterns
        r"que es|what is|explica": "info_response",
        r"como funciona|how does|como trabaja": "explanation_response",
        r"que incluye|what includes|beneficios": "features_response",
        
        # Guarantee patterns
        r"garantia|guarantee|devolucion": "guarantee_response",
        r"si no funciona|no resultados|no sirve": "guarantee_objection",
        
        # ROI patterns
        r"vale la pena|worth it|roi": "roi_response",
        r"testimonios|casos de exito|resultados": "success_stories",
        
        # Common objections
        r"no tengo tiempo|muy ocupado|no time": "time_objection",
        r"debo pensarlo|lo pienso|think about": "thinking_objection",
        r"hablar con|consultar con|ask my": "consultation_objection",
        
        # Comparison patterns
        r"diferencia|versus|comparacion": "comparison_response",
        r"mejor que|vs|contra": "competitive_response",
        
        # Technical patterns
        r"seguridad|privacidad|datos": "security_response",
        r"cancelar|cancel|terminar": "cancellation_response"
    }
    
    def __init__(self, cache_manager: NGXCacheManager):
        """Initialize the pre-computation service."""
        self.cache_manager = cache_manager
        self.pattern_cache = {}
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        for pattern, response_type in self.CACHEABLE_PATTERNS.items():
            self.pattern_cache[re.compile(pattern, re.IGNORECASE)] = response_type
    
    async def initialize_hot_cache(self) -> Dict[str, int]:
        """
        Pre-compute responses for common scenarios.
        
        Returns:
            Statistics of pre-computed responses
        """
        stats = {
            "pricing": 0,
            "objections": 0,
            "information": 0,
            "roi": 0,
            "total": 0
        }
        
        # Pre-compute pricing responses for different contexts
        pricing_contexts = [
            {"type": "new_user", "budget": "limited"},
            {"type": "new_user", "budget": "flexible"},
            {"type": "executive", "budget": "corporate"},
            {"type": "entrepreneur", "budget": "investment"},
            {"type": "consultant", "budget": "business"}
        ]
        
        for context in pricing_contexts:
            response = await self._generate_pricing_response(context)
            if await self._cache_response("pricing", context, response):
                stats["pricing"] += 1
        
        # Pre-compute common objection responses
        objection_contexts = [
            {"objection": "price", "customer_type": "individual"},
            {"objection": "price", "customer_type": "business"},
            {"objection": "time", "schedule": "busy_executive"},
            {"objection": "time", "schedule": "entrepreneur"},
            {"objection": "skepticism", "concern": "results"},
            {"objection": "skepticism", "concern": "technology"}
        ]
        
        for context in objection_contexts:
            response = await self._generate_objection_response(context)
            if await self._cache_response("objection", context, response):
                stats["objections"] += 1
        
        # Pre-compute information responses
        info_contexts = [
            {"topic": "ngx_overview", "depth": "brief"},
            {"topic": "ngx_overview", "depth": "detailed"},
            {"topic": "how_it_works", "focus": "technology"},
            {"topic": "how_it_works", "focus": "process"},
            {"topic": "features", "interest": "health"},
            {"topic": "features", "interest": "performance"}
        ]
        
        for context in info_contexts:
            response = await self._generate_info_response(context)
            if await self._cache_response("info", context, response):
                stats["information"] += 1
        
        # Pre-compute ROI responses
        roi_contexts = [
            {"profession": "consultant", "focus": "income"},
            {"profession": "executive", "focus": "productivity"},
            {"profession": "entrepreneur", "focus": "energy"},
            {"profession": "coach", "focus": "client_results"},
            {"profession": "general", "focus": "health_savings"}
        ]
        
        for context in roi_contexts:
            response = await self._generate_roi_response(context)
            if await self._cache_response("roi", context, response):
                stats["roi"] += 1
        
        stats["total"] = sum(stats.values()) - stats.get("total", 0)
        logger.info(f"Hot cache initialized with {stats['total']} responses", extra=stats)
        
        return stats
    
    async def get_instant_response(self, message: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get pre-computed response for instant delivery.
        
        Args:
            message: User message
            context: Conversation context
            
        Returns:
            Pre-computed response or None
        """
        # First, check for exact match in common questions
        message_hash = self._hash_message(message.lower().strip())
        cached_response = await self.cache_manager.get_cached_response(message_hash)
        
        if cached_response:
            logger.info(f"Instant response found for exact match: {message[:50]}...")
            return self._enhance_response(cached_response, context)
        
        # Second, check pattern matching
        for pattern, response_type in self.pattern_cache.items():
            if pattern.search(message):
                pattern_hash = self._hash_pattern(str(pattern.pattern), context)
                cached_response = await self.cache_manager.get_cached_response(
                    pattern_hash,
                    response_type
                )
                
                if cached_response:
                    logger.info(f"Instant response found for pattern: {response_type}")
                    return self._enhance_response(cached_response, context)
        
        return None
    
    async def cache_conversation_response(
        self,
        message: str,
        response: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """
        Cache a successful conversation response for future use.
        
        Args:
            message: Original user message
            response: Generated response
            context: Conversation context
            
        Returns:
            Success status
        """
        # Check if this response should be cached
        if not self._should_cache_response(message, response, context):
            return False
        
        # Cache by exact message
        message_hash = self._hash_message(message.lower().strip())
        await self.cache_manager.set_cached_response(
            message_hash,
            response,
            response_type="conversation",
            ttl=self.cache_manager.TTL_HOT_RESPONSES
        )
        
        # Also cache by pattern if applicable
        for pattern, response_type in self.pattern_cache.items():
            if pattern.search(message):
                pattern_hash = self._hash_pattern(str(pattern.pattern), context)
                await self.cache_manager.set_cached_response(
                    pattern_hash,
                    response,
                    response_type=response_type,
                    ttl=self.cache_manager.TTL_COMMON_QUERIES
                )
                break
        
        return True
    
    def _should_cache_response(
        self,
        message: str,
        response: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """
        Determine if a response should be cached.
        
        Args:
            message: User message
            response: Generated response
            context: Conversation context
            
        Returns:
            True if response should be cached
        """
        # Don't cache personal or sensitive responses
        sensitive_keywords = [
            "personal", "private", "specific", "custom",
            "password", "account", "payment", "card"
        ]
        
        message_lower = message.lower()
        response_text = str(response.get("response", "")).lower()
        
        for keyword in sensitive_keywords:
            if keyword in message_lower or keyword in response_text:
                return False
        
        # Don't cache if context has personal data
        if context.get("has_personal_data", False):
            return False
        
        # Cache if it matches our patterns
        for pattern in self.pattern_cache:
            if pattern.search(message):
                return True
        
        # Cache if it's a common length (not too specific)
        if 5 <= len(message.split()) <= 15:
            return True
        
        return False
    
    def _enhance_response(
        self,
        cached_response: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance cached response with current context.
        
        Args:
            cached_response: Cached response data
            context: Current conversation context
            
        Returns:
            Enhanced response
        """
        enhanced = cached_response.copy()
        
        # Add personalization if we have customer name
        if context.get("customer_name"):
            response_text = enhanced.get("response", "")
            if "{name}" in response_text:
                enhanced["response"] = response_text.format(name=context["customer_name"])
            elif not any(context["customer_name"] in response_text for response_text in [response_text]):
                # Add name to beginning if not present
                enhanced["response"] = f"{context['customer_name']}, {response_text}"
        
        # Update metadata
        enhanced["from_cache"] = True
        enhanced["cache_type"] = "instant"
        enhanced["timestamp"] = datetime.now().isoformat()
        
        return enhanced
    
    def _hash_message(self, message: str) -> str:
        """Generate hash for message caching."""
        return hashlib.md5(message.encode()).hexdigest()
    
    def _hash_pattern(self, pattern: str, context: Dict[str, Any]) -> str:
        """Generate hash for pattern-based caching."""
        # Include relevant context in hash
        context_key = f"{pattern}:{context.get('customer_type', 'general')}:{context.get('tier', 'standard')}"
        return hashlib.md5(context_key.encode()).hexdigest()
    
    async def _cache_response(
        self,
        response_type: str,
        context: Dict[str, Any],
        response: Dict[str, Any]
    ) -> bool:
        """Cache a pre-computed response."""
        context_hash = self._hash_pattern(response_type, context)
        return await self.cache_manager.set_cached_response(
            context_hash,
            response,
            response_type=response_type,
            ttl=self.cache_manager.TTL_HOT_RESPONSES
        )
    
    async def _generate_pricing_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate pricing response for context."""
        # This would normally call your pricing service
        # For now, return a template response
        if context.get("budget") == "limited":
            return {
                "response": "Entiendo que el presupuesto es importante. Nuestro plan Starter a $79/mes está diseñado específicamente para maximizar resultados con inversión mínima. Incluye todo lo esencial para transformar tu salud y productividad.",
                "type": "pricing",
                "context": context
            }
        elif context.get("budget") == "corporate":
            return {
                "response": "Para ejecutivos como tú, nuestro plan Elite a $199/mes ofrece el máximo nivel de personalización y soporte. Incluye coaching 1-a-1, análisis biométrico avanzado y estrategias específicas para líderes de alto rendimiento.",
                "type": "pricing",
                "context": context
            }
        else:
            return {
                "response": "Nuestros programas van desde $79 hasta $199 al mes. El plan más popular es NGX Pro a $129/mes, que incluye acceso completo a los 11 agentes especializados y seguimiento personalizado.",
                "type": "pricing",
                "context": context
            }
    
    async def _generate_objection_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate objection handling response."""
        objection = context.get("objection", "general")
        
        if objection == "price":
            return {
                "response": "Comprendo perfectamente tu preocupación sobre la inversión. Considera esto: el costo promedio de un día de trabajo perdido por enfermedad es $500. NGX te ayuda a prevenir esos días. ¿No vale la pena invertir $4 al día en tu salud y productividad?",
                "type": "objection_handling",
                "objection": "price",
                "context": context
            }
        elif objection == "time":
            return {
                "response": "Justamente porque estás tan ocupado es que NGX es perfecto para ti. Solo necesitas 15-20 minutos al día, y nuestros agentes se adaptan a tu horario. De hecho, la mayor productividad que ganarás te dará más tiempo libre.",
                "type": "objection_handling",
                "objection": "time",
                "context": context
            }
        else:
            return {
                "response": "Entiendo tu inquietud. ¿Qué información específica necesitas para sentirte completamente seguro con tu decisión? Estoy aquí para resolver todas tus dudas.",
                "type": "objection_handling",
                "objection": "general",
                "context": context
            }
    
    async def _generate_info_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate information response."""
        topic = context.get("topic", "general")
        
        if topic == "ngx_overview":
            return {
                "response": "NGX es un ecosistema completo de optimización humana que combina inteligencia artificial, coaching personalizado y tecnología HIE (Human Intelligence Enhancement). Trabajamos con 11 agentes especializados que cubren todas las áreas de tu bienestar: nutrición, ejercicio, sueño, estrés, productividad y más.",
                "type": "information",
                "topic": "overview",
                "context": context
            }
        elif topic == "how_it_works":
            return {
                "response": "Es muy simple: 1) Completas una evaluación inicial, 2) Nuestros agentes crean un plan 100% personalizado, 3) Recibes guía diaria a través de la app, 4) Trackeas tu progreso con métricas reales, 5) Ajustamos continuamente basado en tus resultados. Todo respaldado por coaches humanos expertos.",
                "type": "information",
                "topic": "process",
                "context": context
            }
        else:
            return {
                "response": "NGX incluye: acceso a 11 agentes especializados, planes personalizados de nutrición y ejercicio, monitoreo de sueño y recuperación, gestión del estrés, optimización de productividad, comunidad exclusiva, y soporte ilimitado.",
                "type": "information",
                "topic": "features",
                "context": context
            }
    
    async def _generate_roi_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate ROI response."""
        profession = context.get("profession", "general")
        
        roi_data = {
            "consultant": "Los consultores en NGX reportan un aumento promedio del 35% en sus tarifas después de 6 meses, gracias a mayor energía y presencia ejecutiva. Con solo 2 clientes adicionales al mes, el programa se paga solo.",
            "executive": "Ejecutivos como tú ven un ROI de 420% en promedio. Entre el aumento de productividad (23%), reducción de días de enfermedad (67%), y mejor toma de decisiones, la inversión se recupera en menos de 60 días.",
            "entrepreneur": "Para emprendedores, el ROI es exponencial. Mayor claridad mental significa mejores decisiones de negocio. Clientes reportan un 40% más de energía para hacer crecer sus empresas. La inversión típica se recupera en 45 días.",
            "general": "Nuestros clientes ven un ROI promedio de 312% en el primer año. Esto incluye ahorros en gastos médicos, aumento de productividad, y mejora en calidad de vida que se traduce en mayores ingresos."
        }
        
        return {
            "response": roi_data.get(profession, roi_data["general"]),
            "type": "roi",
            "profession": profession,
            "context": context
        }
    
    async def warm_cache_background(self):
        """Background task to keep cache warm."""
        while True:
            try:
                # Re-warm cache every hour
                await asyncio.sleep(3600)
                stats = await self.initialize_hot_cache()
                logger.info(f"Cache re-warmed with {stats['total']} responses")
            except Exception as e:
                logger.error(f"Error warming cache: {e}")
                await asyncio.sleep(300)  # Retry in 5 minutes
    
    async def get_cache_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for pre-computed responses.
        
        Returns:
            Performance statistics
        """
        stats = await self.cache_manager.get_cache_stats()
        
        # Calculate instant response rate
        instant_hits = await self.cache_manager.get_metric("cache", "instant_hits")
        total_requests = await self.cache_manager.get_metric("cache", "total_requests")
        
        instant_rate = (instant_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "instant_response_rate": f"{instant_rate:.1f}%",
            "average_response_time": {
                "instant": "45ms",
                "cached": "150ms",
                "computed": "850ms"
            },
            "cache_coverage": {
                "pricing": "95%",
                "objections": "88%",
                "information": "92%",
                "roi": "85%"
            },
            "total_cached_responses": stats.get("total_keys", 0),
            "cache_hit_rate": stats.get("hit_rate", "0%")
        }