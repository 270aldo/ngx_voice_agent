"""
Conversation Context - Shared state object for pipeline processing.
Part of the ConversationOrchestrator refactoring to break down the god class.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.models.conversation import ConversationState, Message
from src.models.platform_context import PlatformContext


@dataclass
class ProcessingMetadata:
    """Metadata collected during message processing."""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    # Analysis results
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    detected_objections: List[str] = field(default_factory=list)
    detected_needs: List[str] = field(default_factory=list)
    emotional_state: Optional[str] = None
    sentiment_score: Optional[float] = None
    
    # ML predictions
    conversion_probability: Optional[float] = None
    recommended_action: Optional[str] = None
    decision_confidence: Optional[float] = None
    
    # Processing flags
    requires_human_transfer: bool = False
    is_price_objection: bool = False
    is_greeting: bool = False
    cache_hit: bool = False
    
    # Response details
    response_strategy: Optional[str] = None
    personalization_applied: bool = False
    ab_test_variant: Optional[str] = None
    
    # Timing metrics
    processing_times: Dict[str, float] = field(default_factory=dict)
    
    def add_timing(self, stage: str, duration: float):
        """Add timing for a processing stage."""
        self.processing_times[stage] = duration
    
    def get_total_duration(self) -> float:
        """Get total processing duration."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


@dataclass
class ConversationContext:
    """
    Shared context object passed through processing pipeline.
    
    This object carries all the state and metadata needed by different
    pipeline stages, avoiding tight coupling between components.
    """
    
    # Core state
    state: ConversationState
    platform_context: Optional[PlatformContext] = None
    
    # Current message being processed
    current_message: Optional[str] = None
    audio_data: Optional[bytes] = None
    
    # Processing metadata
    metadata: ProcessingMetadata = field(default_factory=ProcessingMetadata)
    
    # Service results cache (to avoid re-computation)
    service_results: Dict[str, Any] = field(default_factory=dict)
    
    # Response being built
    response_text: Optional[str] = None
    response_audio: Optional[bytes] = None
    suggested_responses: List[str] = field(default_factory=list)
    
    # Pipeline control
    skip_remaining_stages: bool = False
    error_occurred: bool = False
    error_message: Optional[str] = None
    
    @property
    def conversation_id(self) -> str:
        """Get conversation ID."""
        return self.state.conversation_id
    
    @property
    def customer_name(self) -> str:
        """Get customer name."""
        return self.state.customer.name
    
    @property
    def messages(self) -> List[Message]:
        """Get conversation messages."""
        return self.state.messages
    
    @property
    def current_phase(self) -> str:
        """Get current conversation phase."""
        return self.state.phase
    
    @property
    def program_type(self) -> str:
        """Get program type."""
        return self.state.program_type
    
    def add_service_result(self, service_name: str, result: Any):
        """
        Cache a service result to avoid re-computation.
        
        Args:
            service_name: Name of the service
            result: Result to cache
        """
        self.service_results[service_name] = result
    
    def get_service_result(self, service_name: str) -> Optional[Any]:
        """
        Get cached service result.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Cached result or None
        """
        return self.service_results.get(service_name)
    
    def has_service_result(self, service_name: str) -> bool:
        """Check if service result is cached."""
        return service_name in self.service_results
    
    def mark_error(self, error_message: str):
        """Mark that an error occurred during processing."""
        self.error_occurred = True
        self.error_message = error_message
    
    def should_skip_remaining(self) -> bool:
        """Check if remaining pipeline stages should be skipped."""
        return self.skip_remaining_stages or self.error_occurred
    
    def get_message_history(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get message history in a format suitable for AI models.
        
        Args:
            limit: Optional limit on number of messages
            
        Returns:
            List of message dictionaries
        """
        messages = []
        
        for msg in self.state.messages[-limit:] if limit else self.state.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp
            })
        
        # Add current message if available
        if self.current_message and self.current_message.strip():
            messages.append({
                "role": "user",
                "content": self.current_message,
                "timestamp": datetime.now().isoformat()
            })
        
        return messages
    
    def get_context_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the context for logging/debugging.
        
        Returns:
            Context summary dictionary
        """
        return {
            "conversation_id": self.conversation_id,
            "customer_name": self.customer_name,
            "phase": self.current_phase,
            "program_type": self.program_type,
            "message_count": len(self.messages),
            "current_message": self.current_message[:100] if self.current_message else None,
            "has_audio": self.audio_data is not None,
            "metadata": {
                "intent": self.metadata.intent,
                "emotional_state": self.metadata.emotional_state,
                "conversion_probability": self.metadata.conversion_probability,
                "requires_human_transfer": self.metadata.requires_human_transfer,
                "processing_times": self.metadata.processing_times
            },
            "error": self.error_message if self.error_occurred else None
        }
    
    def finalize(self):
        """Finalize context after processing."""
        self.metadata.end_time = datetime.now()
        
        # Log processing summary
        import logging
        logger = logging.getLogger(__name__)
        
        total_duration = self.metadata.get_total_duration()
        logger.info(
            f"Processed message for {self.conversation_id} in {total_duration:.2f}s",
            extra=self.get_context_summary()
        )