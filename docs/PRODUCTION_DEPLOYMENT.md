# Production Deployment Guide - NGX Voice Sales Agent

## Overview

This guide provides comprehensive instructions for deploying the NGX Voice Sales Agent to production, including Docker configuration, monitoring setup, and best practices.

## Prerequisites

- Docker 20.10+ and Docker Compose 1.29+
- 4GB+ RAM, 2+ CPU cores
- SSL certificates for HTTPS
- Domain name configured
- Production environment variables

## Quick Start

```bash
# 1. Configure production environment
cp env.example .env.production
# Edit .env.production with production values

# 2. Run deployment script
chmod +x scripts/deploy-production.sh
./scripts/deploy-production.sh full production

# 3. Access services
# - Application: https://your-domain.com
# - Grafana: https://your-domain.com:3000
# - API Docs: https://your-domain.com/docs
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│     Nginx       │────▶│   NGX Agent     │────▶│     Redis       │
│   (Reverse      │     │   (FastAPI)     │     │    (Cache)      │
│    Proxy)       │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                        │
         │                       │                        │
         ▼                       ▼                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Prometheus    │────▶│    Grafana      │     │   Supabase      │
│   (Metrics)     │     │ (Dashboards)    │     │   (Database)    │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Deployment Steps

### 1. Environment Configuration

Create `.env.production` with required variables:

```bash
# Application
ENV=production
PORT=8000
LOG_LEVEL=info

# Security
JWT_SECRET=<strong-random-secret>
ENCRYPTION_KEY=<32-byte-key>

# External APIs
OPENAI_API_KEY=<your-key>
ELEVENLABS_API_KEY=<your-key>

# Database
SUPABASE_URL=<your-supabase-url>
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-key>

# Redis
REDIS_URL=redis://redis:6379
REDIS_PASSWORD=<strong-password>

# Monitoring
GRAFANA_USER=admin
GRAFANA_PASSWORD=<strong-password>
```

### 2. SSL Configuration

#### Option A: Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt-get install certbot

# Generate certificates
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem docker/nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem docker/nginx/ssl/
```

#### Option B: Custom Certificates

Place your certificates in:
- `docker/nginx/ssl/fullchain.pem`
- `docker/nginx/ssl/privkey.pem`

### 3. Build and Deploy

```bash
# Validate configuration
./docker/validate.sh

# Build production images
./docker/build.sh production

# Deploy all services
docker-compose -f docker/docker-compose.production.yml up -d

# Deploy monitoring stack
docker-compose -f monitoring/docker-compose.monitoring.yml up -d
```

### 4. Post-Deployment

#### A. Verify Health

```bash
# Check application health
curl https://your-domain.com/health

# Check all services
docker-compose -f docker/docker-compose.production.yml ps
docker-compose -f monitoring/docker-compose.monitoring.yml ps
```

#### B. Configure Grafana

1. Access Grafana at `https://your-domain.com:3000`
2. Login with configured credentials
3. Import dashboards from `monitoring/grafana/dashboards/`
4. Configure alert channels

#### C. Set Up Backups

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup Redis
docker exec ngx-redis redis-cli BGSAVE
docker cp ngx-redis:/data/dump.rdb "$BACKUP_DIR/"

# Backup logs
docker cp ngx-agent-prod:/app/logs "$BACKUP_DIR/"

# Compress
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"
EOF

# Schedule with cron
crontab -e
# Add: 0 2 * * * /path/to/backup.sh
```

## Monitoring

### Key Metrics

1. **Application Metrics**
   - Response time (p95 < 1s)
   - Error rate (< 1%)
   - Active conversations
   - Cache hit rate (> 80%)

2. **System Metrics**
   - CPU usage (< 80%)
   - Memory usage (< 85%)
   - Disk usage (< 90%)
   - Network I/O

3. **Business Metrics**
   - Conversion rate
   - Tier detection accuracy
   - API usage by endpoint
   - Circuit breaker status

### Dashboards

Access pre-configured dashboards:
- **NGX Overview**: Overall system health
- **API Performance**: Endpoint-specific metrics
- **Cache Analytics**: Redis performance
- **Circuit Breakers**: External API resilience

### Alerts

Pre-configured alerts include:
- High error rate (> 5%)
- Slow response time (p95 > 3s)
- Circuit breaker open
- Low cache hit rate (< 50%)
- High resource usage

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.production.yml
services:
  ngx-agent:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
```

### Load Balancing

Nginx automatically load balances between replicas using least connections.

### Redis Cluster

For high availability:

```yaml
services:
  redis-master:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    
  redis-replica:
    image: redis:7-alpine
    command: redis-server --slaveof redis-master 6379
```

## Security Best Practices

1. **Network Security**
   - Use Docker networks for isolation
   - Expose only necessary ports
   - Configure firewall rules

2. **Application Security**
   - Regular security updates
   - Rotate secrets quarterly
   - Enable audit logging
   - Use least privilege principle

3. **Data Security**
   - Encrypt data at rest
   - Use SSL/TLS for all connections
   - Regular backups with encryption
   - GDPR compliance measures

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

```bash
# Check logs
docker-compose -f docker/docker-compose.production.yml logs ngx-agent

# Common causes:
# - Missing environment variables
# - Database connection issues
# - Port conflicts
```

#### 2. High Memory Usage

```bash
# Check memory usage
docker stats

# Optimize:
# - Adjust worker count
# - Increase swap space
# - Scale horizontally
```

#### 3. Slow Response Times

```bash
# Check metrics
curl http://localhost:9090/api/v1/query?query=http_request_duration_seconds

# Common causes:
# - Database queries
# - External API latency
# - Insufficient caching
```

### Debug Mode

```bash
# Enable debug logging
docker-compose -f docker/docker-compose.production.yml \
  exec ngx-agent \
  sed -i 's/LOG_LEVEL=info/LOG_LEVEL=debug/' /app/.env

# Restart service
docker-compose -f docker/docker-compose.production.yml restart ngx-agent
```

## Maintenance

### Regular Tasks

1. **Daily**
   - Monitor dashboards
   - Check error logs
   - Verify backups

2. **Weekly**
   - Review metrics trends
   - Update dependencies
   - Test disaster recovery

3. **Monthly**
   - Security patches
   - Performance optimization
   - Capacity planning

### Updates

```bash
# 1. Backup current state
./scripts/backup-production.sh

# 2. Pull latest changes
git pull origin main

# 3. Build new images
./docker/build.sh production

# 4. Deploy with zero downtime
docker-compose -f docker/docker-compose.production.yml up -d --no-deps --scale ngx-agent=2 ngx-agent
docker-compose -f docker/docker-compose.production.yml up -d --no-deps ngx-agent

# 5. Verify health
./scripts/health-check.sh
```

## Disaster Recovery

### Backup Strategy

- **Redis**: Daily snapshots
- **Logs**: Weekly archives
- **Configuration**: Version controlled
- **Retention**: 30 days

### Recovery Procedure

```bash
# 1. Stop services
docker-compose -f docker/docker-compose.production.yml down

# 2. Restore data
tar -xzf /backups/backup-20240723.tar.gz
docker cp backup/redis/dump.rdb ngx-redis:/data/

# 3. Restart services
docker-compose -f docker/docker-compose.production.yml up -d

# 4. Verify restoration
./scripts/verify-restoration.sh
```

## Performance Optimization

### 1. Application Level

```python
# Optimize worker count
uvicorn src.api.main:app --workers 4 --loop uvloop

# Enable response compression
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### 2. Database Level

```sql
-- Add indexes
CREATE INDEX idx_conversations_customer_id ON conversations(customer_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at);

-- Optimize queries
EXPLAIN ANALYZE SELECT * FROM conversations WHERE ...;
```

### 3. Caching Strategy

```yaml
# Increase cache sizes
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

## Support

### Monitoring Endpoints

- Health Check: `GET /health`
- Metrics: `GET /metrics`
- Cache Stats: `GET /cache/stats`
- Circuit Breakers: `GET /metrics/circuit-breakers`

### Logs Location

- Application: `/app/logs/app.log`
- Nginx: `/var/log/nginx/`
- Redis: `docker logs ngx-redis`

### Getting Help

1. Check documentation: `docs/`
2. Review logs: `docker-compose logs -f`
3. Monitor dashboards: Grafana
4. Contact support: support@ngx.com

## Checklist

Before going live:

- [ ] SSL certificates configured
- [ ] Production environment variables set
- [ ] Monitoring dashboards accessible
- [ ] Alerts configured
- [ ] Backups automated
- [ ] Load testing completed
- [ ] Security scan passed
- [ ] Documentation updated
- [ ] Team trained
- [ ] Support procedures defined