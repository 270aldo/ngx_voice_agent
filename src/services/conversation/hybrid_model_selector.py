"""
Hybrid model selector for optimal performance.

Uses gpt-3.5-turbo for fast responses and gpt-4o for complex queries.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class HybridModelSelector:
    """
    Selects the appropriate model based on query complexity and context.
    
    Strategy:
    - Simple greetings/acknowledgments: gpt-3.5-turbo
    - Price objections: gpt-4o (need high empathy)
    - Complex questions: gpt-4o (need accuracy)
    - Follow-ups: gpt-3.5-turbo (context already established)
    """
    
    # Keywords that require gpt-4o for better handling
    COMPLEX_KEYWORDS = [
        # Price/financial concerns
        "precio", "costo", "caro", "dinero", "inversión", "presupuesto",
        # Skepticism/trust issues
        "garantía", "funciona", "prueba", "confianza", "duda",
        # Technical questions
        "cómo funciona", "técnico", "científico", "estudios",
        # Emotional/health issues
        "depresión", "ansiedad", "enfermedad", "médico", "dolor"
    ]
    
    # Simple responses that can use gpt-3.5-turbo
    SIMPLE_PATTERNS = [
        # Greetings
        "hola", "buenos días", "buenas tardes",
        # Simple acknowledgments
        "ok", "sí", "no", "gracias", "entiendo",
        # Basic questions
        "qué es ngx", "información", "cuéntame"
    ]
    
    @classmethod
    def select_model(
        cls,
        message: str,
        context: Dict[str, Any],
        conversation_length: int = 0
    ) -> Dict[str, Any]:
        """
        Select the appropriate model and parameters.
        
        Returns dict with:
        - model: The model to use
        - reason: Why this model was selected
        - params: Optimized parameters for the model
        """
        message_lower = message.lower().strip()
        
        # First message or emotional state: use gpt-4o
        if conversation_length <= 1 or context.get("emotional_state") in ["anxious", "frustrated", "skeptical"]:
            return {
                "model": "gpt-4o",
                "reason": "first_impression_or_emotional",
                "params": {
                    "temperature": 0.85,
                    "max_tokens": 400,
                    "presence_penalty": -0.2,
                    "frequency_penalty": 0.3
                }
            }
        
        # Check for complex keywords that need gpt-4o
        if any(keyword in message_lower for keyword in cls.COMPLEX_KEYWORDS):
            return {
                "model": "gpt-4o",
                "reason": "complex_topic",
                "params": {
                    "temperature": 0.85,
                    "max_tokens": 400,
                    "presence_penalty": -0.2,
                    "frequency_penalty": 0.3
                }
            }
        
        # Check for simple patterns that can use gpt-3.5-turbo
        if any(pattern in message_lower for pattern in cls.SIMPLE_PATTERNS):
            return {
                "model": "gpt-3.5-turbo",
                "reason": "simple_query",
                "params": {
                    "temperature": 0.8,
                    "max_tokens": 300,  # Even shorter for simple responses
                    "presence_penalty": 0,
                    "frequency_penalty": 0.3
                }
            }
        
        # Short messages (< 20 chars) in ongoing conversation: use gpt-3.5-turbo
        if len(message) < 20 and conversation_length > 3:
            return {
                "model": "gpt-3.5-turbo",
                "reason": "short_followup",
                "params": {
                    "temperature": 0.8,
                    "max_tokens": 250,
                    "presence_penalty": 0,
                    "frequency_penalty": 0.3
                }
            }
        
        # Default: use gpt-3.5-turbo for better performance
        return {
            "model": "gpt-3.5-turbo",
            "reason": "default_fast",
            "params": {
                "temperature": 0.8,
                "max_tokens": 350,
                "presence_penalty": -0.1,
                "frequency_penalty": 0.3
            }
        }
    
    @classmethod
    def get_model_info(cls, model: str) -> Dict[str, Any]:
        """Get information about a model."""
        model_info = {
            "gpt-4o": {
                "avg_latency_ms": 2500,
                "cost_per_1k_tokens": 0.03,
                "quality_score": 10
            },
            "gpt-3.5-turbo": {
                "avg_latency_ms": 800,
                "cost_per_1k_tokens": 0.002,
                "quality_score": 8
            }
        }
        
        return model_info.get(model, model_info["gpt-3.5-turbo"])