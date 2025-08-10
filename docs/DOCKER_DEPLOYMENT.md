# NGX Voice Sales Agent - Docker Deployment Guide

## Overview
This guide covers the complete Docker deployment process for the NGX Voice Sales Agent, from development to production.

## Prerequisites

- Docker Desktop 4.0+ or Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 10GB disk space

## Project Structure

```
docker/
├── Dockerfile                    # Development Dockerfile
├── Dockerfile.production        # Optimized production Dockerfile
├── docker-compose.yml           # Development compose configuration
├── docker-compose.production.yml # Production compose with nginx, redis
├── nginx/
│   └── nginx.conf              # Nginx reverse proxy configuration
├── build.sh                    # Build helper script
└── validate.sh                 # Validation script
```

## Quick Start

### 1. Development Environment

```bash
# Validate Docker setup
./docker/validate.sh

# Build development image
./docker/build.sh development

# Run with docker-compose
docker-compose -f docker/docker-compose.yml up

# Or run directly
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e ELEVENLABS_API_KEY=$ELEVENLABS_API_KEY \
  -e SUPABASE_URL=$SUPABASE_URL \
  -e SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY \
  ngx-agent:dev
```

### 2. Production Environment

```bash
# Create production environment file
cp .env.production.example .env.production
# Edit .env.production with your values

# Build production image
./docker/build.sh production

# Deploy with docker-compose
docker-compose -f docker/docker-compose.production.yml up -d

# Check logs
docker-compose -f docker/docker-compose.production.yml logs -f
```

## Environment Configuration

### Required Environment Variables

```env
# API Keys
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# Security
JWT_SECRET=your-secure-secret-here
JWT_ALGORITHM=HS256

# Application
ENV=production
APP_PORT=8000
LOG_LEVEL=info
```

### Optional Environment Variables

```env
# Redis (for caching)
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=your-redis-password

# Performance
WORKER_COUNT=4
CONNECTION_POOL_SIZE=20

# Monitoring
SENTRY_DSN=https://...
PROMETHEUS_ENABLED=true
```

## Production Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│    Nginx    │────▶│  NGX Agent  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                     │
                           ▼                     ▼
                    ┌─────────────┐      ┌─────────────┐
                    │    Redis    │      │  Supabase   │
                    └─────────────┘      └─────────────┘
```

## Docker Image Details

### Development Image
- Base: `python:3.10-slim`
- Size: ~1.5GB
- Features: Hot reload, debug logging
- Use: Local development only

### Production Image
- Base: `python:3.10-slim` (multi-stage)
- Size: ~800MB (optimized)
- Features: Non-root user, health checks, security hardening
- Use: Staging and production deployments

## Health Checks

The application provides health check endpoints:

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health check (authenticated)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/health/detailed
```

## Scaling Considerations

### Horizontal Scaling
```yaml
# docker-compose.production.yml
services:
  ngx-agent:
    deploy:
      replicas: 3
```

### Resource Limits
```yaml
services:
  ngx-agent:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Monitoring

### Logs
```bash
# View all logs
docker-compose -f docker/docker-compose.production.yml logs

# Follow specific service
docker-compose -f docker/docker-compose.production.yml logs -f ngx-agent

# Export logs
docker logs ngx-agent-prod > ngx-agent.log
```

### Metrics
- Prometheus endpoint: `http://localhost:9090/metrics`
- Grafana dashboards: `http://localhost:3000`

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Find process using port
   lsof -i:8000
   # Kill process
   kill -9 <PID>
   ```

2. **Build failures**
   ```bash
   # Clean Docker cache
   docker system prune -af
   # Rebuild without cache
   docker build --no-cache -f docker/Dockerfile .
   ```

3. **Container won't start**
   ```bash
   # Check logs
   docker logs ngx-agent-prod
   # Interactive debug
   docker run -it --entrypoint /bin/bash ngx-agent:latest
   ```

4. **Environment variables not loading**
   ```bash
   # Verify env file
   docker run --env-file .env.production ngx-agent:latest env
   ```

## Security Best Practices

1. **Never commit secrets**
   - Use `.env` files (gitignored)
   - Use Docker secrets in swarm mode
   - Use cloud secret managers (AWS Secrets Manager, etc.)

2. **Run as non-root user**
   - Production Dockerfile creates and uses `ngxapp` user
   - Ensures container security

3. **Network isolation**
   - Use custom Docker networks
   - Limit exposed ports

4. **Regular updates**
   ```bash
   # Update base images
   docker pull python:3.10-slim
   # Rebuild with latest security patches
   ./docker/build.sh production
   ```

## Deployment Checklist

- [ ] Environment variables configured
- [ ] SSL certificates in place
- [ ] Database migrations run
- [ ] Health checks passing
- [ ] Monitoring configured
- [ ] Backup strategy implemented
- [ ] Load testing completed
- [ ] Security scan passed
- [ ] Documentation updated

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Build and push Docker image
  run: |
    docker build -f docker/Dockerfile.production -t ngx-agent:${{ github.sha }} .
    docker tag ngx-agent:${{ github.sha }} ngx-agent:latest
    docker push ngx-agent:${{ github.sha }}
    docker push ngx-agent:latest
```

### GitLab CI Example
```yaml
build:
  stage: build
  script:
    - docker build -f docker/Dockerfile.production -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
```

## Support

For issues or questions:
1. Check logs: `docker logs ngx-agent-prod`
2. Review this guide
3. Contact the development team

---

Last updated: 2025-07-21