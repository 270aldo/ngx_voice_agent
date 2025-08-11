# NGX Voice Sales Agent - Load Testing Guide

This directory contains load testing configurations and scripts for the NGX Voice Sales Agent API.

## 🎯 Objective

Validate that the system can handle **100+ concurrent users** with acceptable performance.

## 📋 Prerequisites

1. NGX Voice Sales Agent API running on `http://localhost:8000`
2. Python 3.8+ installed
3. Docker (optional, for containerized testing)

## 🚀 Quick Start

### Option 1: Local Testing

1. Install dependencies:
   ```bash
   ./run_load_tests.sh --install
   ```

2. Run a quick test:
   ```bash
   ./run_load_tests.sh quick
   ```

3. Run full test suite:
   ```bash
   ./run_load_tests.sh all
   ```

### Option 2: Docker Testing

1. Start Locust cluster:
   ```bash
   docker-compose up -d
   ```

2. Open Locust UI: http://localhost:8089

3. Configure test:
   - Number of users: 100
   - Spawn rate: 10
   - Host: (should be pre-configured)

4. Start swarming!

## 📊 Test Scenarios

### 1. **Baseline Test** (10 users)
- Purpose: Establish baseline metrics
- Duration: 2 minutes
- Expected: <200ms response time

### 2. **Standard Load** (50 users)
- Purpose: Normal operating conditions
- Duration: 5 minutes
- Expected: <500ms p95 response time

### 3. **Target Load** (100 users) ⭐
- Purpose: Meet requirement
- Duration: 10 minutes
- Expected: <1s p95 response time

### 4. **Stress Test** (200 users)
- Purpose: Find breaking point
- Duration: 5 minutes
- Expected: Identify system limits

## 📈 Key Metrics

### Response Times
- **p50**: 50th percentile (median)
- **p95**: 95th percentile
- **p99**: 99th percentile

### Performance Targets
- ✅ Response time p95 < 1 second
- ✅ Error rate < 1%
- ✅ Throughput > 50 RPS

### Resource Usage
- CPU < 80%
- Memory < 4GB
- No memory leaks

## 🔍 Analyzing Results

### 1. HTML Reports
Check `results/*/report.html` for visual analysis.

### 2. CSV Data
Raw data in `results/*/results_*.csv` files.

### 3. Key Questions
- Are response times acceptable?
- Is the error rate low?
- Does performance degrade over time?
- Are there memory leaks?

## 🛠️ Troubleshooting

### High Error Rate
- Check API logs for errors
- Verify database connections
- Monitor Redis cache

### Slow Response Times
- Check CPU/Memory usage
- Review database query performance
- Verify caching is working

### Connection Errors
- Ensure API is running
- Check firewall/network settings
- Verify correct host configuration

## 📝 Load Test Scenarios Explained

### User Behavior Simulation

The load tests simulate realistic user behavior:

1. **Start Conversation** (10% weight)
   - New users starting sales conversations
   
2. **Send Message** (20% weight)
   - Most frequent action - users chatting
   
3. **Get State** (5% weight)
   - Checking conversation progress
   
4. **Get Recommendations** (3% weight)
   - Viewing program suggestions
   
5. **Calculate ROI** (2% weight)
   - Running ROI calculations
   
6. **End Conversation** (1% weight)
   - Completing conversations

### Think Time
- Users wait 1-3 seconds between actions
- Simulates real human interaction patterns

## 🏆 Success Criteria

The system passes load testing if:

- [x] Handles 100 concurrent users
- [x] p95 response time < 1 second
- [x] Error rate < 1%
- [x] No crashes or memory leaks
- [x] Consistent performance over time

## 📄 Additional Scripts

### Monitor During Tests
```bash
# Watch API logs
docker logs -f ngx_closeragent-app-1

# Monitor system resources
htop

# Check Redis
redis-cli monitor
```

### Generate Custom Reports
```python
# analyze_results.py
import pandas as pd
import matplotlib.pyplot as plt

# Load CSV data
df = pd.read_csv('results/target_*/results_stats.csv')

# Plot response times
df[['Name', 'Average Response Time']].plot(kind='bar')
plt.savefig('response_times.png')
```

## 🔗 Resources

- [Locust Documentation](https://docs.locust.io/)
- [Performance Testing Best Practices](https://www.nginx.com/blog/performance-testing-best-practices/)
- [NGX API Documentation](/docs)