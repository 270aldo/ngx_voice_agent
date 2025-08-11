"""
Cache warmer for common questions to improve response times.
"""
import asyncio
import logging
from typing import List, Dict, Any
from src.services.conversation.response_cache import response_cache
from src.integrations.openai_client import get_openai_client
from src.conversation.prompts.optimized_prompts import OPTIMIZED_SYSTEM_PROMPT, EMPATHY_PROMPTS
from src.config.empathy_config import EmpathyConfig

logger = logging.getLogger(__name__)


class CacheWarmer:
    """Pre-generates responses for common questions."""
    
    # Common questions by category
    COMMON_QUESTIONS = {
        "price": [
            "¿Cuánto cuesta el programa?",
            "¿Cuál es el precio?",
            "¿Es muy caro?",
            "¿Cuánto vale NGX?",
            "¿Qué precio tiene?"
        ],
        "time": [
            "¿Cuánto tiempo toma?",
            "No tengo tiempo",
            "¿Requiere mucho tiempo?",
            "Me preocupa no tener tiempo"
        ],
        "skepticism": [
            "¿Cómo sé que funciona?",
            "¿Qué garantías hay?",
            "He probado otras cosas",
            "¿Por qué es diferente?"
        ],
        "general": [
            "¿Cómo funciona NGX?",
            "¿Qué es NGX?",
            "¿Cómo me puede ayudar?",
            "Estoy cansado todo el tiempo"
        ]
    }
    
    def __init__(self):
        self.openai_client = get_openai_client()
        
    async def warm_cache(self) -> Dict[str, int]:
        """Warm cache with common questions."""
        logger.info("Starting cache warming...")
        
        stats = {
            "total": 0,
            "success": 0,
            "failed": 0
        }
        
        # Process each category
        for category, questions in self.COMMON_QUESTIONS.items():
            for question in questions:
                # Generate for different contexts
                contexts = self._generate_contexts(category)
                
                for context in contexts:
                    try:
                        # Generate response
                        response = await self._generate_response(question, context)
                        
                        # Cache it
                        response_cache.set(question, context, response)
                        
                        stats["success"] += 1
                        logger.info(f"Cached: {question[:30]}... in context {context['emotional_state']}")
                        
                    except Exception as e:
                        stats["failed"] += 1
                        logger.error(f"Failed to cache {question}: {e}")
                    
                    stats["total"] += 1
                    
                    # Small delay to avoid rate limits
                    await asyncio.sleep(0.1)
        
        logger.info(f"Cache warming complete: {stats}")
        return stats
    
    def _generate_contexts(self, category: str) -> List[Dict[str, Any]]:
        """Generate different contexts for a category."""
        base_contexts = [
            {
                "emotional_state": "neutral",
                "has_price_concern": category == "price",
                "conversation_phase": "exploration"
            },
            {
                "emotional_state": "anxious",
                "has_price_concern": category == "price",
                "conversation_phase": "exploration"
            }
        ]
        
        if category == "skepticism":
            base_contexts.append({
                "emotional_state": "skeptical",
                "has_price_concern": False,
                "conversation_phase": "objection_handling"
            })
        
        return base_contexts
    
    async def _generate_response(self, question: str, context: Dict[str, Any]) -> str:
        """Generate a response using optimized settings."""
        # Build compact prompt
        system_prompt = OPTIMIZED_SYSTEM_PROMPT.format(
            age_range="35-45",
            initial_interests=['optimización', 'rendimiento']
        )
        
        # Get optimized parameters
        empathy_context = "price_objection" if context["has_price_concern"] else "general"
        model_params = EmpathyConfig.get_context_params(empathy_context)
        
        # Generate response
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
        
        response_dict = await self.openai_client.create_chat_completion(
            messages=messages,
            **model_params
        )
        
        if response_dict and response_dict.get('choices'):
            return response_dict['choices'][0]['message']['content']
        
        return "Gracias por tu pregunta. ¿Podrías contarme más sobre tu situación?"


# Global warmer instance
cache_warmer = CacheWarmer()