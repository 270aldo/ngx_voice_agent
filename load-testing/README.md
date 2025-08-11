# Load Testing for NGX Voice Sales Agent

## Overview

This directory contains comprehensive load testing tools for the NGX Voice Sales Agent system. The tests validate system performance, scalability, and reliability under various load conditions.

## Quick Start

### 1. Install Dependencies

```bash
cd load-testing
pip install -r requirements.txt
```

### 2. Run Basic Load Test

```bash
# Run all test scenarios
python scripts/run_load_tests.py --host http://localhost:8000

# Run specific scenarios
python scripts/run_load_tests.py --host http://localhost:8000 --scenarios baseline normal peak
```

### 3. Monitor Performance (in another terminal)

```bash
python scripts/monitor_performance.py --host http://localhost:8000 --load-test
```

### 4. Generate Report

```bash
python scripts/generate_report.py results/[timestamp]
```

## Test Scenarios

### Standard Load Patterns

1. **Baseline** (10 users, 2 users/sec)
   - Light load for baseline metrics
   - Duration: 2 minutes

2. **Normal** (50 users, 5 users/sec)
   - Expected daily traffic
   - Duration: 5 minutes

3. **Peak** (100 users, 10 users/sec)
   - Peak hour simulation
   - Duration: 5 minutes

4. **Stress** (200 users, 20 users/sec)
   - Beyond expected capacity
   - Duration: 5 minutes

### Advanced Load Patterns

5. **Spike** (Custom shape)
   - Sudden traffic surge simulation
   - 10 → 50 → 200 users
   - Duration: 6 minutes

6. **Step** (Gradual increase)
   - Find system breaking point
   - +20 users every minute
   - Duration: 10 minutes

7. **Realistic** (Daily pattern)
   - Simulates 12-hour traffic pattern
   - Morning ramp, lunch spike, evening decline
   - Duration: 12 minutes

## User Behavior Simulation

### NGXVoiceSalesUser (Standard)
- Realistic conversation flow
- Complete sales funnel simulation
- Multi-language support (Spanish/Mexican)
- Dynamic phase progression

### StressTestUser
- Rapid-fire messages
- Concurrent operations
- Complex queries
- Circuit breaker testing

### CacheStressUser
- Cache hit/miss patterns
- Cache invalidation testing
- Performance validation

### CircuitBreakerTestUser
- Failure injection
- Circuit breaker validation
- Fallback testing

## Metrics Collected

### Performance Metrics
- Response times (avg, median, p95, p99)
- Throughput (requests/second)
- Error rates and types
- Concurrent user capacity

### System Metrics
- CPU usage
- Memory usage
- Active connections
- Cache hit rates
- Circuit breaker states

### Business Metrics
- Conversation completion rates
- Phase progression analysis
- Tier detection accuracy
- ROI calculation performance

## Running Advanced Tests

### Circuit Breaker Stress Test

```bash
locust -f scenarios/stress_test_scenario.py \
       --host http://localhost:8000 \
       --users 100 \
       --spawn-rate 10 \
       --run-time 5m \
       --class CircuitBreakerTestUser
```

### Cache Performance Test

```bash
locust -f scenarios/stress_test_scenario.py \
       --host http://localhost:8000 \
       --users 50 \
       --spawn-rate 5 \
       --run-time 10m \
       --class CacheStressUser
```

### Custom Load Shape

```bash
locust -f scenarios/stress_test_scenario.py \
       --host http://localhost:8000 \
       --class-picker
```

## Monitoring and Analysis

### Real-time Monitoring

The performance monitor displays:
- Live metrics dashboard
- Alert notifications
- Circuit breaker status
- Performance trends

### Report Generation

Generated reports include:
- **HTML Report**: Visual dashboard with charts
- **JSON Report**: Raw data for further analysis
- **Visualizations**: Performance graphs and heatmaps

### Key Performance Indicators

1. **Response Time SLA**
   - Average: < 200ms
   - P95: < 1000ms
   - P99: < 3000ms

2. **Error Rate SLA**
   - < 1% under normal load
   - < 5% under peak load

3. **Throughput Targets**
   - Minimum: 50 req/s
   - Target: 100 req/s
   - Stretch: 200 req/s

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure the application is running
   - Check the host URL
   - Verify firewall settings

2. **High Error Rates**
   - Check application logs
   - Verify database connections
   - Review circuit breaker states

3. **Poor Performance**
   - Check Redis cache status
   - Review database query performance
   - Analyze CPU/Memory usage

### Debug Mode

```bash
# Run with debug logging
locust -f locustfile.py \
       --host http://localhost:8000 \
       --loglevel DEBUG
```

## Best Practices

1. **Before Testing**
   - Ensure clean database state
   - Warm up caches
   - Check system resources

2. **During Testing**
   - Monitor system metrics
   - Watch for anomalies
   - Document observations

3. **After Testing**
   - Generate reports immediately
   - Analyze bottlenecks
   - Plan optimizations

## Integration with CI/CD

### GitHub Actions Example

```yaml
- name: Run Load Tests
  run: |
    cd load-testing
    pip install -r requirements.txt
    python scripts/run_load_tests.py \
      --host ${{ env.TEST_HOST }} \
      --scenarios baseline normal peak
    
- name: Upload Results
  uses: actions/upload-artifact@v3
  with:
    name: load-test-results
    path: load-testing/results/
```

## Performance Optimization Tips

Based on load testing results:

1. **Database Optimization**
   - Add indexes for frequent queries
   - Optimize connection pooling
   - Consider read replicas

2. **Caching Strategy**
   - Increase cache TTLs
   - Implement cache warming
   - Use cache-aside pattern

3. **Application Tuning**
   - Optimize async operations
   - Reduce serialization overhead
   - Implement request batching

4. **Infrastructure Scaling**
   - Horizontal scaling for API servers
   - Redis cluster for cache
   - Load balancer configuration