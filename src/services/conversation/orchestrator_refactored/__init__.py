"""
Refactored Conversation Orchestrator Module

This module contains the refactored conversation orchestrator split into
focused, single-responsibility classes for better maintainability and testability.
"""

from .conversation_manager import ConversationManager
from .message_processor import MessageProcessor
from .integration_handler import IntegrationHandler
from .response_builder import ResponseBuilder
from .metrics_collector import MetricsCollector
from .orchestrator_facade import ConversationOrchestratorFacade

# Export the main facade as ConversationOrchestrator for backward compatibility
ConversationOrchestrator = ConversationOrchestratorFacade

__all__ = [
    'ConversationManager',
    'MessageProcessor',
    'IntegrationHandler',
    'ResponseBuilder',
    'MetricsCollector',
    'ConversationOrchestrator',
    'ConversationOrchestratorFacade'
]