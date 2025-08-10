"""
OpenAI Client Integration with Circuit Breaker.

This module provides a centralized OpenAI client with circuit breaker protection
to handle API failures gracefully.
"""

import os
from typing import Optional, Dict, Any, List
from functools import lru_cache
import logging
from openai import AsyncOpenAI, OpenAI
import asyncio

from src.config import settings
from src.services.circuit_breaker_service import circuit_breaker, get_circuit_breaker, CircuitBreakerConfig
from src.utils.structured_logging import StructuredLogger
from src.utils.metrics import track_external_api_call, openai_tokens_used_total
from src.services.ngx_cache_manager import NGXCacheManager

logger = StructuredLogger.get_logger(__name__)


class OpenAIClientWrapper:
    """
    Wrapper for OpenAI client with circuit breaker protection.
    
    Features:
    - Automatic circuit breaker on API calls
    - Token usage tracking
    - Response caching for resilience
    - Fallback strategies for different call types
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI client wrapper.
        
        Args:
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY from environment.
        """
        self.api_key = api_key or settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
        
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY")
            
        if not self.api_key:
            raise ValueError("OpenAI API key not found in settings or environment")
            
        # Initialize clients
        self.async_client = AsyncOpenAI(api_key=self.api_key)
        self.sync_client = OpenAI(api_key=self.api_key)
        
        # Initialize cache manager
        self._cache: Optional[NGXCacheManager] = None
        self._cache_initialized = False
        
        # Default model settings
        self.default_model = settings.openai_model if hasattr(settings, 'openai_model') else "gpt-4o"
        self.default_temperature = settings.openai_temperature if hasattr(settings, 'openai_temperature') else 0.85
        self.default_max_tokens = settings.openai_max_tokens if hasattr(settings, 'openai_max_tokens') else 2500
        self.default_presence_penalty = settings.openai_presence_penalty if hasattr(settings, 'openai_presence_penalty') else -0.2
        self.default_frequency_penalty = settings.openai_frequency_penalty if hasattr(settings, 'openai_frequency_penalty') else 0.3
        self.default_top_p = settings.openai_top_p if hasattr(settings, 'openai_top_p') else 0.95
        
        logger.info(
            f"OpenAI client initialized with model {self.default_model}",
            extra={
                "model": self.default_model,
                "temperature": self.default_temperature,
                "max_tokens": self.default_max_tokens
            }
        )
    
    async def _ensure_cache_initialized(self):
        """Ensure cache is initialized."""
        if not self._cache_initialized:
            try:
                from src.core.dependencies import get_ngx_cache
                self._cache = await get_ngx_cache()
                self._cache_initialized = True
            except Exception as e:
                logger.warning(f"Could not initialize cache: {e}")
                self._cache = None
                self._cache_initialized = True
    
    @circuit_breaker(
        "openai_chat_completions",
        failure_threshold=5,
        recovery_timeout=60,
        max_retries=3
    )
    async def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create chat completion with circuit breaker protection.
        
        Args:
            messages: List of message dictionaries
            model: Model to use (defaults to configured model)
            temperature: Temperature setting
            max_tokens: Maximum tokens in response
            **kwargs: Additional OpenAI API parameters
            
        Returns:
            Chat completion response
        """
        # Use defaults if not provided
        model = model or self.default_model
        temperature = temperature if temperature is not None else self.default_temperature
        max_tokens = max_tokens or self.default_max_tokens
        
        # Extract empathy parameters from kwargs or use defaults
        presence_penalty = kwargs.pop('presence_penalty', self.default_presence_penalty)
        frequency_penalty = kwargs.pop('frequency_penalty', self.default_frequency_penalty)
        top_p = kwargs.pop('top_p', self.default_top_p)
        
        # Generate cache key for this request
        cache_key = self._generate_chat_cache_key(messages, model, temperature)
        
        # Check cache first
        await self._ensure_cache_initialized()
        if self._cache and cache_key:
            cached_response = await self._cache.get_conversation(cache_key)
            if cached_response:
                logger.debug("Using cached chat completion response")
                return cached_response
        
        # Make API call with metrics tracking
        # TODO: Fix track_external_api_call to be async context manager
        # async with track_external_api_call("openai", "chat.completions"):
        try:
            response = await self.async_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
                top_p=top_p,
                **kwargs
            )
            
            # Convert response to dict for caching
            response_dict = {
                "id": response.id,
                "model": response.model,
                "choices": [
                    {
                        "index": choice.index,
                        "message": {
                            "role": choice.message.role,
                            "content": choice.message.content
                        },
                        "finish_reason": choice.finish_reason
                    }
                    for choice in response.choices
                ],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None
            }
            
            # Track token usage
            if response.usage:
                openai_tokens_used_total.labels(
                    model=model,
                    type="prompt"
                ).inc(response.usage.prompt_tokens)
                openai_tokens_used_total.labels(
                    model=model,
                    type="completion"
                ).inc(response.usage.completion_tokens)
            
            # Cache successful response
            if self._cache and cache_key:
                await self._cache.set_conversation(cache_key, response_dict, ttl=300)
            
            return response_dict
            
        except Exception as e:
            logger.error(
                f"OpenAI API error: {str(e)}",
                extra={
                    "error_type": type(e).__name__,
                    "model": model,
                    "message_count": len(messages)
                },
                exc_info=True
            )
            
            # Try fallback from cache if available
            if self._cache and cache_key:
                fallback = await self._cache.get_conversation(f"{cache_key}_fallback")
                if fallback:
                    logger.info("Using fallback response from cache")
                    return fallback
            
            # Generate static fallback
            return self._generate_fallback_response(messages, str(e))
    
    def _generate_chat_cache_key(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float
    ) -> str:
        """Generate cache key for chat completion request."""
        # Use last user message as key component
        last_user_msg = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")[:100]  # First 100 chars
                break
        
        if not last_user_msg:
            return None
            
        # Create deterministic key
        import hashlib
        key_data = f"{model}:{temperature}:{last_user_msg}"
        return f"openai_chat_{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def _generate_fallback_response(self, messages: List[Dict[str, str]], error: str) -> Dict[str, Any]:
        """Generate fallback response when API fails."""
        # Analyze the context to provide appropriate fallback
        last_user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "").lower()
                break
        
        # Context-aware fallback messages
        if any(word in last_user_message for word in ["precio", "costo", "inversión", "cuánto"]):
            fallback_content = (
                "Disculpa, estoy teniendo dificultades técnicas en este momento. "
                "Te puedo compartir que nuestros programas tienen diferentes opciones de inversión "
                "que se adaptan a cada caso particular. ¿Te gustaría que agendemos una llamada "
                "para discutir los detalles cuando se restablezca la conexión?"
            )
        elif any(word in last_user_message for word in ["programa", "incluye", "beneficio", "qué es"]):
            fallback_content = (
                "Perdón, estoy experimentando una interrupción temporal. "
                "NGX ofrece programas personalizados de optimización de salud y rendimiento "
                "con enfoque científico. ¿Podríamos continuar esta conversación en unos momentos "
                "o prefieres que te contacte por otro medio?"
            )
        else:
            fallback_content = (
                "Lo siento, estoy teniendo problemas técnicos para procesar tu mensaje. "
                "¿Podrías reformular tu pregunta o intentarlo en unos momentos? "
                "Tu consulta es importante para nosotros."
            )
        
        return {
            "id": "fallback_response",
            "model": "fallback",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": fallback_content
                },
                "finish_reason": "error_fallback"
            }],
            "usage": None,
            "_fallback": True,
            "_error": error
        }
    
    @circuit_breaker(
        "openai_embeddings",
        failure_threshold=10,
        recovery_timeout=30,
        max_retries=2
    )
    async def create_embedding(
        self,
        input_text: str,
        model: str = "text-embedding-ada-002"
    ) -> List[float]:
        """
        Create text embedding with circuit breaker protection.
        
        Args:
            input_text: Text to embed
            model: Embedding model to use
            
        Returns:
            Embedding vector
        """
        # TODO: Fix track_external_api_call to be async context manager
        # async with track_external_api_call("openai", "embeddings"):
        try:
            response = await self.async_client.embeddings.create(
                model=model,
                input=input_text
            )
            
            # Track token usage
            if response.usage:
                openai_tokens_used_total.labels(
                    model=model,
                    type="embedding"
                ).inc(response.usage.total_tokens)
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"OpenAI embeddings error: {str(e)}", exc_info=True)
            # Return zero vector as fallback
            return [0.0] * 1536  # Default embedding size for ada-002
    
    async def close(self):
        """Close the client and cleanup resources."""
        try:
            await self.async_client.close()
        except Exception as e:
            logger.error(f"Error closing OpenAI client: {e}")


# Singleton instance
_openai_client: Optional[OpenAIClientWrapper] = None


def get_openai_client() -> OpenAIClientWrapper:
    """
    Get singleton OpenAI client instance.
    
    Returns:
        OpenAI client wrapper with circuit breaker protection
    """
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAIClientWrapper()
    return _openai_client


async def close_openai_client():
    """Close and cleanup OpenAI client."""
    global _openai_client
    if _openai_client:
        await _openai_client.close()
        _openai_client = None