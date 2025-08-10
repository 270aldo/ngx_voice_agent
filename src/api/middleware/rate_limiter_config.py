"""
Rate limiting configuration for different API endpoints.

This module provides granular rate limiting configurations for different
types of API endpoints to ensure fair usage and protect against abuse.
"""

from typing import Dict, Tuple
from dataclasses import dataclass
from src.core.constants import TimeConstants, APIConstants, SecurityConstants


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int
    burst_size: int
    block_duration_seconds: int = TimeConstants.MINUTE


# Rate limit configurations by endpoint pattern
RATE_LIMIT_CONFIGS: Dict[str, RateLimitConfig] = {
    # Authentication endpoints - more restrictive
    "/api/auth/login": RateLimitConfig(
        requests_per_minute=SecurityConstants.MAX_LOGIN_ATTEMPTS,
        burst_size=10,
        block_duration_seconds=TimeConstants.CACHE_DEFAULT_TTL  # 5 minutes
    ),
    "/api/auth/register": RateLimitConfig(
        requests_per_minute=3,
        burst_size=5,
        block_duration_seconds=TimeConstants.CACHE_LONG_TTL  # 10 minutes
    ),
    
    # Conversation endpoints - increased for load testing
    "/api/conversation/start": RateLimitConfig(
        requests_per_minute=10000,  # Increased for load testing
        burst_size=20000,
        block_duration_seconds=TimeConstants.MINUTE
    ),
    "/conversations/start": RateLimitConfig(
        requests_per_minute=10000,  # Increased for load testing
        burst_size=20000,
        block_duration_seconds=TimeConstants.MINUTE
    ),
    "/api/conversation/respond": RateLimitConfig(
        requests_per_minute=TimeConstants.DEFAULT_TIMEOUT,
        burst_size=50,
        block_duration_seconds=TimeConstants.MINUTE
    ),
    
    # Analytics endpoints - higher limits for dashboards
    "/api/analytics": RateLimitConfig(
        requests_per_minute=APIConstants.RATE_LIMIT_PER_MINUTE,
        burst_size=APIConstants.MAX_PAGE_SIZE,
        block_duration_seconds=TimeConstants.DEFAULT_TIMEOUT
    ),
    
    # Predictive model endpoints - moderate limits
    "/api/predictive": RateLimitConfig(
        requests_per_minute=APIConstants.DEFAULT_PAGE_SIZE,
        burst_size=40,
        block_duration_seconds=TimeConstants.MINUTE
    ),
    
    # Health check - very high limits
    "/health": RateLimitConfig(
        requests_per_minute=TimeConstants.CACHE_LONG_TTL,
        burst_size=APIConstants.RATE_LIMIT_PER_HOUR,
        block_duration_seconds=10
    ),
    
    # Default for all other endpoints
    "default": RateLimitConfig(
        requests_per_minute=APIConstants.MAX_PAGE_SIZE,
        burst_size=200,
        block_duration_seconds=TimeConstants.MINUTE
    )
}


def get_rate_limit_config(path: str) -> RateLimitConfig:
    """
    Get rate limit configuration for a given path.
    
    Args:
        path: The API endpoint path
        
    Returns:
        RateLimitConfig for the endpoint
    """
    # Check exact matches first
    if path in RATE_LIMIT_CONFIGS:
        return RATE_LIMIT_CONFIGS[path]
    
    # Check prefix matches
    for pattern, config in RATE_LIMIT_CONFIGS.items():
        if pattern != "default" and path.startswith(pattern):
            return config
    
    # Return default
    return RATE_LIMIT_CONFIGS["default"]


# IP-based exceptions (for internal services, monitoring, etc.)
RATE_LIMIT_EXCEPTIONS = {
    "127.0.0.1",      # Localhost
    "::1",            # IPv6 localhost
    "10.0.0.0/8",     # Private network
    "172.16.0.0/12",  # Private network
    "192.168.0.0/16", # Private network
}


def is_ip_exempt(ip_address: str) -> bool:
    """
    Check if an IP address is exempt from rate limiting.
    
    Args:
        ip_address: The IP address to check
        
    Returns:
        True if exempt, False otherwise
    """
    import ipaddress
    
    try:
        ip = ipaddress.ip_address(ip_address)
        
        # Check exact matches
        if str(ip) in RATE_LIMIT_EXCEPTIONS:
            return True
        
        # Check network ranges
        for exempt in RATE_LIMIT_EXCEPTIONS:
            if "/" in exempt:
                try:
                    network = ipaddress.ip_network(exempt)
                    if ip in network:
                        return True
                except ValueError:
                    continue
        
        return False
    except ValueError:
        return False


# Custom rate limit headers
RATE_LIMIT_HEADERS = {
    "limit": "X-RateLimit-Limit",
    "remaining": "X-RateLimit-Remaining",
    "reset": "X-RateLimit-Reset",
    "retry_after": "Retry-After"
}