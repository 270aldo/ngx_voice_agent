#!/bin/bash

# Deploy NGX Voice Sales Agent Monitoring Stack
# This script sets up Prometheus, Grafana, and supporting services

set -e

echo "🚀 Deploying NGX Voice Sales Agent Monitoring Stack"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating monitoring directories..."
mkdir -p alertmanager/templates
mkdir -p loki
mkdir -p promtail

# Set environment variables
export REDIS_PASSWORD=${REDIS_PASSWORD:-"ngx-redis-password"}
export GRAFANA_USER=${GRAFANA_USER:-"admin"}
export GRAFANA_PASSWORD=${GRAFANA_PASSWORD:-"ngx-admin-2024"}

# Create external network if it doesn't exist
echo "🌐 Creating Docker network..."
docker network create ngx-network 2>/dev/null || echo "Network already exists"

# Pull all images first
echo "📥 Pulling Docker images..."
docker-compose -f docker-compose.monitoring.yml pull

# Start monitoring stack
echo "🚀 Starting monitoring services..."
docker-compose -f docker-compose.monitoring.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check Prometheus
if curl -s http://localhost:9090/-/healthy > /dev/null; then
    echo "✅ Prometheus is healthy"
else
    echo "❌ Prometheus is not responding"
fi

# Check Grafana
if curl -s http://localhost:3000/api/health > /dev/null; then
    echo "✅ Grafana is healthy"
else
    echo "❌ Grafana is not responding"
fi

# Check Node Exporter
if curl -s http://localhost:9100/metrics > /dev/null; then
    echo "✅ Node Exporter is healthy"
else
    echo "❌ Node Exporter is not responding"
fi

# Check Alertmanager
if curl -s http://localhost:9093/-/healthy > /dev/null; then
    echo "✅ Alertmanager is healthy"
else
    echo "❌ Alertmanager is not responding"
fi

echo ""
echo "🎉 Monitoring stack deployment complete!"
echo ""
echo "📊 Access your monitoring tools:"
echo "   - Grafana: http://localhost:3000"
echo "     Username: ${GRAFANA_USER}"
echo "     Password: ${GRAFANA_PASSWORD}"
echo ""
echo "   - Prometheus: http://localhost:9090"
echo "   - Alertmanager: http://localhost:9093"
echo ""
echo "📈 Next steps:"
echo "   1. Log in to Grafana and explore the NGX dashboard"
echo "   2. Configure alert notification channels in Alertmanager"
echo "   3. Update your NGX API to expose metrics endpoint"
echo ""
echo "🛑 To stop monitoring: docker-compose -f docker-compose.monitoring.yml down"
echo "📊 To view logs: docker-compose -f docker-compose.monitoring.yml logs -f"