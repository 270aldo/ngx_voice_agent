# HTTP Response Caching System

## Overview

The HTTP caching system provides intelligent response caching for the NGX Voice Sales Agent API, significantly improving performance and reducing load on backend services. It implements industry-standard caching strategies with advanced features like cache tagging, conditional requests, and stale-while-revalidate support.

## Architecture

### Components

1. **HTTPCacheMiddleware** - FastAPI middleware for automatic response caching
2. **HTTPCacheService** - Advanced cache service with sophisticated features
3. **Cache Management API** - Endpoints for monitoring and managing cache
4. **Cache Response Decorator** - Function-level caching for specific endpoints

### Cache Flow

```
Request → Cache Middleware → Check Cache → Cache Hit? 
                                              ↓ Yes → Return Cached Response
                                              ↓ No
                                         Process Request → Cache Response → Return Response
```

## Features

### 1. Automatic Response Caching
- GET requests automatically cached based on URL patterns
- Configurable TTL per endpoint type
- Cache key generation includes query parameters and headers

### 2. Cache Invalidation
- **Tag-based invalidation**: Group related cache entries
- **Pattern-based invalidation**: Invalidate by URL patterns
- **Automatic invalidation**: Write operations trigger related cache clearing

### 3. Conditional Requests
- **ETag support**: Efficient validation using content hashes
- **Last-Modified**: Time-based validation
- **304 Not Modified**: Reduces bandwidth for unchanged content

### 4. Advanced Strategies
- **Stale-While-Revalidate**: Serve stale content while updating in background
- **Compression**: Automatic compression for large responses
- **Partial Caching**: Cache parts of responses (ESI-style)

## Configuration

### Default Cache Configurations

```python
# Analytics endpoints - 5 minutes
"/api/analytics/.*": CacheConfig(ttl_seconds=300)

# ML drift status - 1 minute
"/api/ml/drift/status/.*": CacheConfig(ttl_seconds=60)

# Summary endpoints - 10 minutes
"/api/.*/summary.*": CacheConfig(ttl_seconds=600)

# Health checks - 30 seconds
"/api/health.*": CacheConfig(ttl_seconds=30)

# Don't cache predictions or conversations
"/api/predictive/.*": None
"/api/conversation/.*": None
```

### Cache Headers

Responses include standard cache headers:
- `Cache-Control`: Directives for caches
- `ETag`: Entity tag for validation
- `Last-Modified`: Last modification time
- `X-Cache`: HIT or MISS indicator
- `X-Cache-Age`: Age of cached content

## Usage

### 1. Automatic Caching (Middleware)

The middleware automatically caches eligible responses:

```python
# Automatically cached by middleware
GET /api/analytics/aggregate?days=7

# Response headers
Cache-Control: public, max-age=300
ETag: "a3f5c9d8..."
X-Cache: MISS (first request)
X-Cache: HIT (subsequent requests)
```

### 2. Decorator-based Caching

For fine-grained control, use the cache decorator:

```python
from src.api.middleware.http_cache_middleware import cache_response

@router.get("/expensive-operation")
@cache_response(ttl_seconds=600)
async def expensive_endpoint():
    # Expensive computation
    return compute_result()

# With custom cache key
@router.get("/user/{user_id}/profile")
@cache_response(
    ttl_seconds=300,
    cache_key_func=lambda user_id: f"user_profile:{user_id}"
)
async def get_user_profile(user_id: str):
    return fetch_user_profile(user_id)

# Conditional caching
@router.get("/data")
@cache_response(
    ttl_seconds=300,
    condition_func=lambda result: result.get("cacheable", True)
)
async def get_data():
    return fetch_data()
```

### 3. Cache Service Usage

For advanced caching needs:

```python
from src.services.http_cache_service import HTTPCacheService, CacheStrategy

cache_service = HTTPCacheService()

# Set with tags
await cache_service.set(
    key="analytics:daily:2024-01-15",
    value=analytics_data,
    ttl_seconds=3600,
    tags=["analytics", "daily", "2024-01"]
)

# Get with stale-while-revalidate
value, is_stale = await cache_service.get(
    key="analytics:daily:2024-01-15",
    strategy=CacheStrategy.STALE_WHILE_REVALIDATE,
    revalidate_func=fetch_fresh_analytics
)

# Invalidate by tag
await cache_service.invalidate_by_tag("analytics")
```

## Cache Management API

### View Statistics
```http
GET /api/cache/stats
Authorization: Bearer {token}

Response:
{
  "total_entries": 1250,
  "total_size_mb": 45.3,
  "hit_rate": "78.5%",
  "compression_ratio": "0.65",
  "tags_count": 25
}
```

### Invalidate Cache
```http
# By key
POST /api/cache/invalidate/key/{cache_key}

# By tag
POST /api/cache/invalidate/tag/{tag}

# By pattern
POST /api/cache/invalidate/pattern?pattern=/api/analytics/*
```

### Configure Cache
```http
PUT /api/cache/config
{
  "default_ttl_seconds": 600,
  "compression_threshold_bytes": 2048,
  "enable_compression": true
}
```

## Performance Optimization

### 1. Cache Key Design
- Include all parameters that affect response
- Use consistent key formats
- Avoid overly specific keys that reduce hit rate

### 2. TTL Strategy
- Shorter TTL for frequently changing data
- Longer TTL for stable data
- Use stale-while-revalidate for best UX

### 3. Cache Tags
- Tag related content for bulk invalidation
- Use hierarchical tags (e.g., "user:123", "user:123:profile")
- Limit tags per entry to prevent overhead

### 4. Compression
- Automatically compresses responses > 1KB
- Only applied if compression saves > 10% space
- Transparent decompression on retrieval

## Monitoring

### Key Metrics
- **Hit Rate**: Percentage of requests served from cache
- **Response Time**: Average time to serve cached vs fresh
- **Cache Size**: Total memory/storage used
- **Invalidation Rate**: Frequency of cache clears

### Performance Dashboard
```http
GET /api/cache/performance

{
  "service_metrics": {
    "hit_rate": "78.5%",
    "avg_response_time_ms": 12.3
  },
  "middleware_metrics": {
    "total_requests": 50000,
    "hits": 39250,
    "misses": 10750
  },
  "recommendations": [
    "Increase TTL for /api/analytics/trends",
    "Add caching to /api/ml/models endpoint"
  ]
}
```

## Best Practices

### 1. Cache Appropriately
- ✅ Cache read-heavy, stable data
- ✅ Cache expensive computations
- ❌ Don't cache user-specific sensitive data
- ❌ Don't cache real-time data

### 2. Invalidation Strategy
- Use tags for related content
- Invalidate on write operations
- Consider time-based expiry vs event-based

### 3. Conditional Requests
- Support ETags for bandwidth savings
- Implement If-Modified-Since checks
- Return 304 when content unchanged

### 4. Error Handling
- Cache successful responses only
- Don't cache error responses
- Implement circuit breaker for cache failures

## Troubleshooting

### Low Hit Rate
1. Check cache key generation
2. Verify TTL is appropriate
3. Look for unnecessary cache invalidations
4. Consider request patterns

### High Memory Usage
1. Review cache entry sizes
2. Enable compression
3. Reduce TTL for large entries
4. Implement cache eviction policies

### Stale Data Issues
1. Verify invalidation logic
2. Check cache tags are correct
3. Review TTL settings
4. Monitor write operations

## Advanced Features

### Stale-While-Revalidate
```python
# Serve stale content immediately while fetching fresh
value, is_stale = await cache_service.get(
    key="expensive_data",
    strategy=CacheStrategy.STALE_WHILE_REVALIDATE,
    revalidate_func=fetch_fresh_data
)

if is_stale:
    # Add warning header
    response.headers["Warning"] = "110 - Response is stale"
```

### Cache Warming
```python
# Pre-populate cache with critical data
await cache_service.warm_cache(
    warm_func=fetch_analytics_batch,
    keys=["analytics:2024-01-15", "analytics:2024-01-16"]
)
```

### Distributed Cache (Future)
- Redis backend support
- Cache synchronization across instances
- Pub/sub for invalidation events

## Security Considerations

1. **Cache Poisoning**: Validate cache keys to prevent injection
2. **Information Leakage**: Don't cache sensitive data
3. **User Isolation**: Include user context in cache keys
4. **GDPR Compliance**: Implement cache data deletion for users

## Migration Guide

### Adding Caching to Existing Endpoints

1. Identify cacheable endpoints (GET, stable data)
2. Add cache decorator or configure middleware pattern
3. Implement proper cache invalidation
4. Monitor hit rates and adjust TTL
5. Add cache tags for related content

Example migration:
```python
# Before
@router.get("/report")
async def get_report():
    return generate_report()

# After
@router.get("/report")
@cache_response(
    ttl_seconds=1800,  # 30 minutes
    tags=["reports", "analytics"]
)
async def get_report():
    return generate_report()

# Add invalidation on update
@router.post("/data/update")
async def update_data():
    result = perform_update()
    await cache_service.invalidate_by_tag("reports")
    return result
```