"""
Custom Exception Types

Specific exception types to replace generic Exception handlers.
"""


class NGXBaseException(Exception):
    """Base exception for all NGX custom exceptions."""
    pass


class ServiceInitializationError(NGXBaseException):
    """Raised when a service fails to initialize."""
    pass


class ConversationError(NGXBaseException):
    """Base exception for conversation-related errors."""
    pass


class MessageProcessingError(ConversationError):
    """Raised when message processing fails."""
    pass


class ConversationNotFoundError(ConversationError):
    """Raised when a conversation is not found."""
    pass


class ConversationStateError(ConversationError):
    """Raised when conversation state is invalid."""
    pass


class IntegrationError(NGXBaseException):
    """Base exception for integration errors."""
    pass


class OpenAIError(IntegrationError):
    """Raised when OpenAI API calls fail."""
    pass


class ElevenLabsError(IntegrationError):
    """Raised when ElevenLabs API calls fail."""
    pass


class SupabaseError(IntegrationError):
    """Raised when Supabase operations fail."""
    pass


class DatabaseError(NGXBaseException):
    """Base exception for database operations."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""
    pass


class DatabaseQueryError(DatabaseError):
    """Raised when database query fails."""
    pass


class ValidationError(NGXBaseException):
    """Raised when input validation fails."""
    pass


class AuthenticationError(NGXBaseException):
    """Raised when authentication fails."""
    pass


class AuthorizationError(NGXBaseException):
    """Raised when authorization fails."""
    pass


class RateLimitError(NGXBaseException):
    """Raised when rate limit is exceeded."""
    pass


class WebSocketError(NGXBaseException):
    """Base exception for WebSocket errors."""
    pass


class WebSocketConnectionError(WebSocketError):
    """Raised when WebSocket connection fails."""
    pass


class WebSocketMessageError(WebSocketError):
    """Raised when WebSocket message handling fails."""
    pass


class CacheError(NGXBaseException):
    """Base exception for cache operations."""
    pass


class CacheReadError(CacheError):
    """Raised when cache read fails."""
    pass


class CacheWriteError(CacheError):
    """Raised when cache write fails."""
    pass


class MLPredictionError(NGXBaseException):
    """Raised when ML prediction fails."""
    pass


class PatternRecognitionError(NGXBaseException):
    """Raised when pattern recognition fails."""
    pass


class ConfigurationError(NGXBaseException):
    """Raised when configuration is invalid."""
    pass


class TimeoutError(NGXBaseException):
    """Raised when an operation times out."""
    pass


class ResourceExhaustedError(NGXBaseException):
    """Raised when a resource is exhausted."""
    pass


class NetworkError(NGXBaseException):
    """Raised when network operations fail."""
    pass


class SerializationError(NGXBaseException):
    """Raised when serialization/deserialization fails."""
    pass


# Export all exception types
__all__ = [
    'NGXBaseException',
    'ServiceInitializationError',
    'ConversationError',
    'MessageProcessingError',
    'ConversationNotFoundError',
    'ConversationStateError',
    'IntegrationError',
    'OpenAIError',
    'ElevenLabsError',
    'SupabaseError',
    'DatabaseError',
    'DatabaseConnectionError',
    'DatabaseQueryError',
    'ValidationError',
    'AuthenticationError',
    'AuthorizationError',
    'RateLimitError',
    'WebSocketError',
    'WebSocketConnectionError',
    'WebSocketMessageError',
    'CacheError',
    'CacheReadError',
    'CacheWriteError',
    'MLPredictionError',
    'PatternRecognitionError',
    'ConfigurationError',
    'TimeoutError',
    'ResourceExhaustedError',
    'NetworkError',
    'SerializationError'
]