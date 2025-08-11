# Circuit Breakers for External APIs

## Overview

The NGX Voice Sales Agent implements circuit breakers for all external API integrations to ensure system resilience and graceful degradation when external services are unavailable.

## Architecture

### Core Components

1. **NGXCircuitBreaker**: Generic circuit breaker implementation
2. **CircuitBreakerManager**: Centralized management of all circuit breakers
3. **API Client Wrappers**: OpenAI and ElevenLabs clients with built-in circuit breakers

### Circuit Breaker States

```
CLOSED → OPEN → HALF_OPEN → CLOSED
```

- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Service is failing, requests fail immediately
- **HALF_OPEN**: Testing if service has recovered

## Implementation

### 1. Generic Circuit Breaker Service

Location: `src/services/circuit_breaker_service.py`

```python
# Configuration
config = CircuitBreakerConfig(
    name="service_name",
    failure_threshold=5,      # Failures before opening
    recovery_timeout=60,      # Seconds before testing recovery
    max_retries=3,           # Retry attempts
    cache_on_failure=True    # Use cache when circuit open
)

# Usage
breaker = NGXCircuitBreaker(config)
result = await breaker.call(async_function, *args, **kwargs)
```

### 2. OpenAI Integration

Location: `src/integrations/openai_client.py`

**Features:**
- Automatic circuit breaker on all API calls
- Token usage tracking
- Context-aware fallback responses
- Response caching for resilience

**Configuration:**
- Failure threshold: 5 failures
- Recovery timeout: 60 seconds
- Max retries: 3 attempts
- Cache TTL: 300 seconds

**Fallback Strategies:**
```python
# Price-related queries
"Disculpa, estoy teniendo dificultades técnicas..."

# Program information queries
"NGX ofrece programas personalizados..."

# General queries
"Lo siento, estoy teniendo problemas técnicos..."
```

### 3. ElevenLabs Integration

Location: `src/integrations/elevenlabs_client.py`

**Features:**
- Circuit breaker for voice synthesis
- Audio caching for quick fallback
- Mock mode for development
- Fallback to cached audio or silence

**Configuration:**
- Failure threshold: 3 failures
- Recovery timeout: 30 seconds
- Max retries: 2 attempts
- Cache limit: 100 audio clips

**Fallback Strategies:**
1. Return cached audio for same voice type
2. Return silence MP3 if no cache available
3. Mock mode returns placeholder audio

## Usage Examples

### Using Decorator

```python
from src.services.circuit_breaker_service import circuit_breaker

@circuit_breaker(
    "my_service",
    failure_threshold=5,
    recovery_timeout=60,
    fallback_result={"status": "unavailable"}
)
async def call_external_api():
    # API call implementation
    pass
```

### Direct Usage

```python
from src.integrations.openai_client import get_openai_client

client = get_openai_client()
response = await client.create_chat_completion(
    messages=[{"role": "user", "content": "Hello"}],
    model="gpt-4"
)
```

### Getting Circuit Breaker Status

```python
from src.services.circuit_breaker_service import get_circuit_breaker

breaker = get_circuit_breaker("openai")
metrics = breaker.get_metrics()

print(f"State: {metrics['state']}")
print(f"Success rate: {metrics['success_rate']}")
print(f"Failed calls: {metrics['failed_calls']}")
```

## Monitoring

### Metrics Available

Each circuit breaker tracks:
- Total calls
- Successful calls
- Failed calls
- Fallback calls
- Success rate
- State changes
- Last failure/success time

### Health Check Endpoint

```python
GET /metrics/circuit-breakers

Response:
{
    "healthy": true,
    "total_breakers": 3,
    "healthy_breakers": 3,
    "open_circuits": [],
    "metrics": {
        "openai": {
            "state": "closed",
            "success_rate": 0.98,
            ...
        }
    }
}
```

### Prometheus Metrics

- `openai_api_calls_total{endpoint,status}`
- `openai_api_duration_seconds{endpoint}`
- `openai_tokens_used_total{model,type}`
- `elevenlabs_api_calls_total{endpoint,status}`
- `elevenlabs_api_duration_seconds{endpoint}`

## Configuration

### Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=2000

# ElevenLabs
ELEVENLABS_API_KEY=your-api-key
```

### Custom Circuit Breaker Configuration

```python
# In CircuitBreakerManager._create_default_configs()
"custom_service": CircuitBreakerConfig(
    name="custom_service",
    failure_threshold=10,
    recovery_timeout=120,
    expected_exception=CustomException,
    exclude_exceptions=[TimeoutError],
    max_retries=5,
    cache_on_failure=True,
    cache_ttl=600
)
```

## Testing

### Unit Tests

Location: `tests/unit/services/test_circuit_breaker_service.py`

```bash
# Run circuit breaker tests
pytest tests/unit/services/test_circuit_breaker_service.py -v

# Run API client tests
pytest tests/unit/integrations/test_openai_client.py -v
pytest tests/unit/integrations/test_elevenlabs_client.py -v
```

### Integration Tests

Test circuit breakers with actual API failures:

```python
# Simulate API failure
mock_api.side_effect = Exception("Service unavailable")

# Verify circuit opens
for i in range(failure_threshold):
    result = await client.call_api()
    assert result == fallback_value

# Verify circuit is open
assert breaker.get_state() == CircuitState.OPEN
```

## Best Practices

1. **Set Appropriate Thresholds**
   - OpenAI: Higher threshold (5) due to importance
   - ElevenLabs: Lower threshold (3) for faster fallback
   - Database: Higher threshold (10) for resilience

2. **Implement Meaningful Fallbacks**
   - Context-aware responses for chat
   - Cached audio for voice synthesis
   - Default values for configuration

3. **Monitor Circuit States**
   - Alert on open circuits
   - Track failure patterns
   - Review recovery times

4. **Test Fallback Scenarios**
   - Regularly test with API failures
   - Verify fallback quality
   - Ensure user experience maintained

## Troubleshooting

### Circuit Stuck Open

```python
# Manual reset
breaker = get_circuit_breaker("service_name")
breaker.reset()
```

### Check Circuit State

```python
# Get detailed metrics
manager = CircuitBreakerManager()
health = manager.get_health_status()
print(json.dumps(health, indent=2))
```

### Debug Logging

```python
# Enable debug logging
import logging
logging.getLogger("src.services.circuit_breaker_service").setLevel(logging.DEBUG)
```

## Future Enhancements

1. **Distributed Circuit Breakers**
   - Redis-based state storage
   - Synchronized across instances

2. **Advanced Fallback Strategies**
   - ML-based response generation
   - Predictive fallback selection

3. **Circuit Breaker Analytics**
   - Failure pattern analysis
   - Automated threshold tuning

4. **Integration with Service Mesh**
   - Istio/Envoy integration
   - Network-level circuit breaking