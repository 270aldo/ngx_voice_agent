"""
Interfaces and protocols for dependency inversion and avoiding circular imports.
"""

from .cache_interfaces import CacheInterface, CacheableService
from .service_interfaces import (
    PredictiveServiceInterface,
    QualificationServiceInterface,
    ConversationServiceInterface,
    DecisionEngineInterface
)

__all__ = [
    "CacheInterface",
    "CacheableService",
    "PredictiveServiceInterface",
    "QualificationServiceInterface",
    "ConversationServiceInterface",
    "DecisionEngineInterface"
]