"""
Service interfaces for dependency inversion and avoiding circular imports.
"""

from typing import Dict, List, Any, Optional, Protocol
from abc import abstractmethod


class PredictiveServiceInterface(Protocol):
    """Interface for predictive services."""
    
    @abstractmethod
    async def predict(self, *args, **kwargs) -> Dict[str, Any]:
        """Make a prediction."""
        ...
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        ...


class QualificationServiceInterface(Protocol):
    """Interface for lead qualification services."""
    
    @abstractmethod
    async def qualify_lead(
        self,
        conversation_history: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Qualify a lead based on conversation."""
        ...
    
    @abstractmethod
    def calculate_lead_score(self, *args, **kwargs) -> float:
        """Calculate lead score."""
        ...


class ConversationServiceInterface(Protocol):
    """Interface for conversation services."""
    
    @abstractmethod
    async def process_message(
        self,
        message: str,
        conversation_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Process a conversation message."""
        ...
    
    @abstractmethod
    async def get_conversation_state(
        self,
        conversation_id: str
    ) -> Dict[str, Any]:
        """Get current conversation state."""
        ...


class DecisionEngineInterface(Protocol):
    """Interface for decision engine services."""
    
    @abstractmethod
    async def make_decision(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a decision based on conversation state."""
        ...
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        ...