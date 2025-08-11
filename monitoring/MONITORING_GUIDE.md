# NGX Voice Sales Agent - Monitoring Guide

## Overview

This guide covers the complete monitoring stack for NGX Voice Sales Agent, including metrics collection, visualization, alerting, and log aggregation.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   NGX API       │────▶│   Prometheus    │────▶│    Grafana      │
│  (metrics)      │     │ (metrics store) │     │ (visualization) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                           │
                               ▼                           │
                        ┌─────────────────┐               │
                        │  Alertmanager   │               │
                        │    (alerts)     │               │
                        └─────────────────┘               │
                                                          │
┌─────────────────┐     ┌─────────────────┐              │
│   Application   │────▶│      Loki       │◀─────────────┘
│     Logs        │     │  (log store)    │
└─────────────────┘     └─────────────────┘
```

## Quick Start

### 1. Deploy Monitoring Stack

```bash
cd monitoring
./deploy-monitoring.sh
```

### 2. Access Services

- **Grafana**: http://localhost:3000 (admin/ngx-admin-2024)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093
- **Loki**: http://localhost:3100

## Metrics Collection

### Application Metrics

The NGX API exposes metrics at `/metrics` endpoint:

```python
# Example metrics exposed
http_requests_total{method="POST",endpoint="/api/conversation/start",status="200"} 1234
http_request_duration_seconds{method="POST",endpoint="/api/conversation/start",quantile="0.95"} 0.123
conversation_active_total 45
ml_prediction_duration_seconds{model="objection_prediction",quantile="0.95"} 0.089
cache_hit_ratio 0.85
```

### System Metrics

Node Exporter collects system-level metrics:
- CPU usage
- Memory usage
- Disk I/O
- Network traffic

### Redis Metrics

Redis Exporter provides:
- Cache hit/miss ratio
- Memory usage
- Command statistics
- Connection count

## Dashboards

### 1. NGX Voice Agent Overview

Main dashboard showing:
- API health status
- Response time percentiles (p50, p95, p99)
- Error rates
- Request rate
- Active conversations
- System resources

### 2. ML Performance Dashboard

Dedicated dashboard for ML metrics:
- Prediction latency
- Model accuracy
- A/B test results
- Conversion predictions

### 3. Business Metrics Dashboard

Business KPIs:
- Conversion rates
- Drop-off rates
- Tier distribution
- ROI calculations

## Alert Configuration

### Critical Alerts (Immediate)

1. **API Down**
   - Condition: API unreachable for 2 minutes
   - Action: Page on-call engineer

2. **High Error Rate**
   - Condition: Error rate > 1% for 5 minutes
   - Action: Notify ops team

3. **Redis Down**
   - Condition: Redis unreachable for 1 minute
   - Action: Page on-call engineer

### Warning Alerts (Batched)

1. **High Response Time**
   - Condition: p95 > 1 second for 5 minutes
   - Action: Email warning

2. **High CPU/Memory**
   - Condition: > 80% for 10 minutes
   - Action: Email warning

3. **Low Cache Hit Rate**
   - Condition: < 80% for 15 minutes
   - Action: Email warning

### Business Alerts (Daily)

1. **Low Conversion Rate**
   - Condition: < 2% for 2 hours
   - Action: Daily summary

2. **High Drop Rate**
   - Condition: > 30% for 1 hour
   - Action: Daily summary

## Alert Channels

### Email Configuration

Update `alertmanager/config.yml`:
```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'your-email@gmail.com'
  smtp_auth_username: 'your-email@gmail.com'
  smtp_auth_password: 'your-app-password'
```

### Slack Integration

1. Create Slack webhook
2. Update `.env.monitoring`:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### PagerDuty Integration

Add to `alertmanager/config.yml`:
```yaml
receivers:
- name: 'pagerduty-critical'
  pagerduty_configs:
  - service_key: 'YOUR-PAGERDUTY-SERVICE-KEY'
```

## Custom Metrics

### Adding New Metrics

1. In your Python code:
```python
from prometheus_client import Counter, Histogram, Gauge

# Counter for events
conversion_counter = Counter(
    'conversation_conversions_total',
    'Total number of successful conversions',
    ['tier', 'archetype']
)

# Histogram for durations
prediction_histogram = Histogram(
    'ml_prediction_duration_seconds',
    'ML prediction duration',
    ['model_type']
)

# Gauge for current values
active_conversations = Gauge(
    'conversation_active_total',
    'Currently active conversations'
)
```

2. Update metrics:
```python
# Increment counter
conversion_counter.labels(tier='hybrid_coaching', archetype='prime').inc()

# Record duration
with prediction_histogram.labels(model_type='objection').time():
    # ML prediction code
    pass

# Set gauge value
active_conversations.set(45)
```

## Log Collection

### Application Logs

Configure your app to write structured logs:
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "conversation_started",
    conversation_id=conv_id,
    customer_id=customer_id,
    tier="agents_access"
)
```

### Log Queries in Grafana

Example queries:
```
# All errors in last hour
{job="ngx-api"} |= "ERROR"

# Conversation metrics
{job="ngx-api"} |= "conversation_started" | json | tier="hybrid_coaching"

# Performance logs
{job="ngx-api"} |= "ml_prediction" | json | duration > 100
```

## Performance Optimization

### 1. Metric Cardinality

Keep cardinality low:
```python
# Bad - high cardinality
http_requests_total{user_id="12345", session_id="abc123"}

# Good - low cardinality
http_requests_total{method="POST", endpoint="/api/conversation", status="200"}
```

### 2. Retention Policies

Configure in `prometheus.yml`:
```yaml
global:
  external_labels:
    monitor: 'ngx-monitor'
storage:
  tsdb:
    retention.time: 30d
    retention.size: 10GB
```

### 3. Recording Rules

Pre-compute expensive queries:
```yaml
groups:
- name: ngx_recording_rules
  interval: 30s
  rules:
  - record: instance:http_requests:rate5m
    expr: rate(http_requests_total[5m])
```

## Troubleshooting

### Common Issues

1. **Prometheus Can't Scrape Metrics**
   - Check network connectivity
   - Verify metrics endpoint is accessible
   - Check authentication if enabled

2. **Grafana Dashboard Empty**
   - Verify Prometheus datasource
   - Check time range selection
   - Validate PromQL queries

3. **Alerts Not Firing**
   - Check Alertmanager logs
   - Verify alert rules syntax
   - Test webhook endpoints

### Debug Commands

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Test alert routing
amtool --alertmanager.url=http://localhost:9093 check-config

# Validate Prometheus config
promtool check config prometheus.yml

# View Grafana logs
docker logs ngx-grafana

# Test metric endpoint
curl http://localhost:8000/metrics
```

## Backup and Recovery

### Prometheus Data

Backup:
```bash
docker exec ngx-prometheus promtool tsdb snapshot /prometheus
docker cp ngx-prometheus:/prometheus/snapshots ./backups/
```

Restore:
```bash
docker cp ./backups/snapshot-xxx ngx-prometheus:/prometheus/
docker restart ngx-prometheus
```

### Grafana Dashboards

Export:
```bash
# Via API
curl -X GET http://admin:password@localhost:3000/api/dashboards/db/ngx-voice-agent
```

Import:
```bash
# Via UI or API
curl -X POST http://admin:password@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @dashboard.json
```

## Maintenance

### Weekly Tasks

1. Review alert noise ratio
2. Check disk usage for metrics storage
3. Update dashboard based on feedback
4. Review and tune alert thresholds

### Monthly Tasks

1. Analyze metrics cardinality
2. Clean up unused metrics
3. Update retention policies
4. Performance review of queries

## Integration with CI/CD

### Deployment Metrics

Add to your deployment pipeline:
```bash
# Record deployment
curl -X POST http://localhost:9090/api/v1/prom/api/v1/admin/tsdb/create-blocks \
  -d 'deployment_info{version="1.2.3",environment="production"} 1'
```

### SLO Monitoring

Define SLOs:
```yaml
- record: slo:availability
  expr: sum(rate(http_requests_total{status!~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

- alert: SLOViolation
  expr: slo:availability < 0.99
  for: 5m
```

## Security

### 1. Enable Authentication

Prometheus:
```yaml
# prometheus.yml
basic_auth_users:
  admin: $2b$12$hashed_password
```

Grafana:
```ini
# grafana.ini
[auth.anonymous]
enabled = false

[auth.basic]
enabled = true
```

### 2. Use HTTPS

Configure reverse proxy:
```nginx
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location /grafana/ {
        proxy_pass http://localhost:3000/;
    }
}
```

### 3. Network Isolation

Use Docker networks:
```yaml
networks:
  monitoring:
    internal: true
  public:
    external: true
```

## Cost Optimization

### 1. Metric Sampling

Reduce collection frequency for non-critical metrics:
```yaml
scrape_configs:
  - job_name: 'low-priority'
    scrape_interval: 5m
    static_configs:
      - targets: ['low-priority-service:9090']
```

### 2. Downsampling

Use recording rules for historical data:
```yaml
- record: http_requests:rate1h
  expr: avg_over_time(http_requests:rate5m[1h])
```

### 3. Selective Persistence

Only store business-critical metrics long-term:
```yaml
metric_relabel_configs:
  - source_labels: [__name__]
    regex: 'debug_.*'
    action: drop
```

## Additional Resources

- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Tutorial](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Alert Runbooks](./runbooks/)