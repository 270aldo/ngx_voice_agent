"""
WebSocket Configuration for High Concurrency

Optimized settings for handling 500+ concurrent WebSocket connections.
"""

from typing import Final


class WebSocketConfig:
    """WebSocket configuration optimized for beta testing."""
    
    # Connection limits
    MAX_CONNECTIONS_PER_USER: Final[int] = 3
    MAX_CONNECTIONS_PER_ORG: Final[int] = 100
    MAX_TOTAL_CONNECTIONS: Final[int] = 1000  # Increased for beta
    
    # Connection pooling
    CONNECTION_POOL_SIZE: Final[int] = 500  # Target 500+ concurrent
    CONNECTION_POOL_OVERFLOW: Final[int] = 100  # Buffer for spikes
    
    # Timeouts (in seconds)
    PING_INTERVAL: Final[int] = 30
    PING_TIMEOUT: Final[int] = 10
    CONNECTION_TIMEOUT: Final[int] = 60
    IDLE_TIMEOUT: Final[int] = 300  # 5 minutes
    
    # Message limits
    MAX_MESSAGE_SIZE: Final[int] = 65536  # 64KB
    MAX_MESSAGES_PER_SECOND: Final[int] = 10
    MESSAGE_QUEUE_SIZE: Final[int] = 100
    
    # Rate limiting for WebSocket
    WS_RATE_LIMIT_CONNECTIONS_PER_HOUR: Final[int] = 100
    WS_RATE_LIMIT_MESSAGES_PER_MINUTE: Final[int] = 60
    
    # Performance optimization
    USE_COMPRESSION: Final[bool] = True
    COMPRESSION_LEVEL: Final[int] = 6  # 1-9, higher = better compression
    BATCH_BROADCAST_SIZE: Final[int] = 50  # Batch broadcasts for efficiency
    
    # Memory management
    CONNECTION_CLEANUP_INTERVAL: Final[int] = 60  # Cleanup dead connections
    MAX_MEMORY_PER_CONNECTION_MB: Final[float] = 1.0
    
    # Monitoring
    ENABLE_CONNECTION_MONITORING: Final[bool] = True
    METRICS_COLLECTION_INTERVAL: Final[int] = 30
    LOG_SLOW_MESSAGES: Final[bool] = True
    SLOW_MESSAGE_THRESHOLD_MS: Final[int] = 100
    
    @classmethod
    def get_connection_limit_for_user(cls, user_role: str) -> int:
        """Get connection limit based on user role."""
        role_limits = {
            "admin": 10,
            "premium": 5,
            "standard": 3,
            "trial": 1
        }
        return role_limits.get(user_role, cls.MAX_CONNECTIONS_PER_USER)
    
    @classmethod
    def calculate_buffer_size(cls, expected_connections: int) -> int:
        """Calculate optimal buffer size for expected connections."""
        # Rule of thumb: 20% buffer for connection spikes
        return int(expected_connections * 1.2)
    
    @classmethod
    def get_ping_settings(cls) -> dict:
        """Get ping/pong settings for connection health."""
        return {
            "ping_interval": cls.PING_INTERVAL,
            "ping_timeout": cls.PING_TIMEOUT,
            "max_failures": 3
        }


# Export configuration
websocket_config = WebSocketConfig()