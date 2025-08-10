"""
Conversation Service Module

This module contains the refactored conversation service components,
organized into focused, maintainable submodules.
"""

from .orchestrator import ConversationOrchestrator
from .ml_tracking import MLTrackingMixin
from .tier_management import TierManagementMixin
from .emotional_processing import EmotionalProcessingMixin
from .sales_strategy import SalesStrategyMixin
from .base import BaseConversationService

# For backward compatibility
ConversationService = ConversationOrchestrator

__all__ = [
    'ConversationOrchestrator',
    'ConversationService',  # Backward compatibility
    'MLTrackingMixin',
    'TierManagementMixin', 
    'EmotionalProcessingMixin',
    'SalesStrategyMixin',
    'BaseConversationService'
]