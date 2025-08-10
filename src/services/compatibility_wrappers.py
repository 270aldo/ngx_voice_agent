"""
Compatibility Wrappers for Service Methods

This module provides compatibility wrappers to fix method name mismatches
between different parts of the codebase without breaking existing functionality.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ServiceCompatibilityMixin:
    """
    Mixin that provides compatibility wrappers for service methods.
    
    This allows the codebase to use both old and new method names
    during the transition period.
    """
    
    async def analyze_emotional_state(self, message_text: str = None, **kwargs) -> Dict[str, Any]:
        """
        Wrapper for _analyze_emotional_state that handles different parameter formats.
        
        This method provides compatibility for calls expecting different parameter names.
        """
        if hasattr(self, '_analyze_emotional_state'):
            # Extract parameters from kwargs
            state = kwargs.get('state')
            context = kwargs.get('context')
            
            # If message_text is passed as a kwarg
            if not message_text and 'message_text' in kwargs:
                message_text = kwargs['message_text']
            
            # Call the actual method
            if message_text and state:
                return await self._analyze_emotional_state(message_text, state, context)
            else:
                logger.error("Missing required parameters for analyze_emotional_state")
                return {
                    "primary_emotion": "neutral",
                    "emotional_intensity": 0.5,
                    "error": "Missing parameters"
                }
        else:
            logger.error("_analyze_emotional_state method not found")
            return {
                "primary_emotion": "neutral",
                "emotional_intensity": 0.5,
                "error": "Method not implemented"
            }
    
    async def generate_empathic_response(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Wrapper for _generate_empathic_response (note: empathic vs empathetic).
        
        This provides compatibility for the typo in method name.
        """
        if hasattr(self, '_generate_empathic_response'):
            return await self._generate_empathic_response(*args, **kwargs)
        elif hasattr(self, '_generate_empathetic_response'):
            return await self._generate_empathetic_response(*args, **kwargs)
        else:
            logger.error("No empathic/empathetic response method found")
            return {
                "response_adjustments": {},
                "empathy_score": 0.5,
                "error": "Method not implemented"
            }
    
    async def generate_empathetic_response(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Wrapper for _generate_empathetic_response that redirects to empathic.
        """
        return await self.generate_empathic_response(*args, **kwargs)
    
    async def detect_tier(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Wrapper for _detect_optimal_tier (old name: detect_tier).
        
        This provides backward compatibility for the old method name.
        """
        if hasattr(self, '_detect_optimal_tier'):
            # If called with positional args, map them
            if args:
                if len(args) >= 2:
                    return await self._detect_optimal_tier(args[0], args[1])
                else:
                    logger.error("Insufficient arguments for detect_tier")
            # If called with kwargs
            elif 'message_text' in kwargs and 'state' in kwargs:
                return await self._detect_optimal_tier(
                    kwargs['message_text'], 
                    kwargs['state']
                )
            else:
                logger.error("Missing required parameters for detect_tier")
                return {
                    "tier": "AGENTS ACCESS",
                    "confidence": 0.5,
                    "error": "Missing parameters"
                }
        else:
            logger.error("_detect_optimal_tier method not found")
            return {
                "tier": "AGENTS ACCESS",
                "confidence": 0.5,
                "error": "Method not implemented"
            }
    
    async def detect_optimal_tier(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Wrapper that redirects to the internal _detect_optimal_tier method.
        """
        if hasattr(self, '_detect_optimal_tier'):
            return await self._detect_optimal_tier(*args, **kwargs)
        else:
            return await self.detect_tier(*args, **kwargs)


class EmpathyEngineServiceCompat:
    """
    Compatibility wrapper for EmpathyEngineService to fix method name issues.
    """
    
    def __init__(self, empathy_service=None):
        self.empathy_service = empathy_service
    
    async def generate_empathic_response(self, *args, **kwargs):
        """Redirect to the correct method name."""
        if self.empathy_service and hasattr(self.empathy_service, 'generate_empathetic_response'):
            return await self.empathy_service.generate_empathetic_response(*args, **kwargs)
        elif self.empathy_service and hasattr(self.empathy_service, '_generate_empathic_response'):
            return await self.empathy_service._generate_empathic_response(*args, **kwargs)
        else:
            logger.warning("EmpathyEngineService method not found, returning default")
            return {
                "response_adjustments": {
                    "tone": "warm",
                    "empathy_level": "medium"
                },
                "empathy_phrases": [],
                "emotional_validation": "I understand how you feel."
            }


class TierDetectionServiceCompat:
    """
    Compatibility wrapper for TierDetectionService to fix method name issues.
    """
    
    def __init__(self, tier_service=None):
        self.tier_service = tier_service
    
    async def detect_tier(self, *args, **kwargs):
        """Redirect to the correct method name."""
        if self.tier_service and hasattr(self.tier_service, 'detect_optimal_tier'):
            return await self.tier_service.detect_optimal_tier(*args, **kwargs)
        elif self.tier_service and hasattr(self.tier_service, '_detect_optimal_tier'):
            return await self.tier_service._detect_optimal_tier(*args, **kwargs)
        else:
            logger.warning("TierDetectionService method not found, returning default")
            return {
                "tier": "AGENTS ACCESS",
                "confidence": 0.7,
                "reasoning": "Default tier due to method not found"
            }


# Export a function to patch existing services
def patch_service_compatibility(service_instance):
    """
    Dynamically add compatibility methods to a service instance.
    
    Args:
        service_instance: The service instance to patch
        
    Returns:
        The patched service instance
    """
    # Add all compatibility methods
    for method_name in dir(ServiceCompatibilityMixin):
        if not method_name.startswith('_'):
            method = getattr(ServiceCompatibilityMixin, method_name)
            if callable(method):
                setattr(service_instance, method_name, method.__get__(service_instance, type(service_instance)))
    
    return service_instance