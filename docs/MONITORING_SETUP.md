# Configuración de Monitoreo con Prometheus y Grafana

## Descripción General

Esta guía describe cómo configurar Prometheus y Grafana para monitorear el NGX Voice Sales Agent en producción.

## Arquitectura de Monitoreo

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│   NGX Agent     │────▶│  Prometheus  │────▶│   Grafana   │
│   (Métricas)    │     │  (Storage)   │     │ (Dashboard) │
└─────────────────┘     └──────────────┘     └─────────────┘
```

## 1. Configuración de Prometheus

### 1.1 Docker Compose para Prometheus

```yaml
# docker/monitoring/docker-compose.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: ngx_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: ngx_grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    restart: unless-stopped
    depends_on:
      - prometheus

volumes:
  prometheus_data:
  grafana_data:
```

### 1.2 Configuración de Prometheus

```yaml
# docker/monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'ngx-agent'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: '/metrics'
    
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
```

## 2. Instrumentación del Código Python

### 2.1 Instalar Dependencias

```bash
pip install prometheus-client
```

### 2.2 Agregar Métricas al Código

```python
# src/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time

# Contadores
conversation_total = Counter(
    'ngx_conversations_total', 
    'Total number of conversations',
    ['status', 'tier']
)

prediction_total = Counter(
    'ngx_predictions_total',
    'Total number of predictions',
    ['model_type', 'status']
)

api_requests_total = Counter(
    'ngx_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

# Histogramas
response_time = Histogram(
    'ngx_response_time_seconds',
    'Response time in seconds',
    ['endpoint']
)

prediction_confidence = Histogram(
    'ngx_prediction_confidence',
    'Prediction confidence scores',
    ['model_type'],
    buckets=(0.1, 0.3, 0.5, 0.7, 0.9, 0.95, 0.99)
)

# Gauges
active_conversations = Gauge(
    'ngx_active_conversations',
    'Number of active conversations'
)

model_accuracy = Gauge(
    'ngx_model_accuracy',
    'Current model accuracy',
    ['model_name']
)
```

### 2.3 Endpoint de Métricas

```python
# src/api/routers/monitoring.py
from fastapi import APIRouter
from prometheus_client import generate_latest
from starlette.responses import Response

router = APIRouter(tags=["monitoring"])

@router.get("/metrics")
async def metrics():
    """Endpoint para Prometheus scraping."""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

## 3. Dashboards de Grafana

### 3.1 Dashboard Principal

```json
{
  "dashboard": {
    "title": "NGX Voice Sales Agent",
    "panels": [
      {
        "title": "Conversaciones Totales",
        "targets": [
          {
            "expr": "sum(rate(ngx_conversations_total[5m])) by (status)"
          }
        ]
      },
      {
        "title": "Tiempo de Respuesta API",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(ngx_response_time_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Precisión de Modelos",
        "targets": [
          {
            "expr": "ngx_model_accuracy"
          }
        ]
      }
    ]
  }
}
```

## 4. Alertas

### 4.1 Reglas de Alerta en Prometheus

```yaml
# docker/monitoring/alerts.yml
groups:
  - name: ngx_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(ngx_api_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Alta tasa de errores en API"
          description: "Más del 5% de requests están fallando"
          
      - alert: LowModelAccuracy
        expr: ngx_model_accuracy < 0.7
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Baja precisión en modelo {{ $labels.model_name }}"
          
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(ngx_response_time_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Tiempo de respuesta alto"
```

## 5. Implementación en el Código

### 5.1 Middleware de Monitoreo

```python
# src/api/middleware/monitoring.py
from fastapi import Request
import time
from src.monitoring.metrics import api_requests_total, response_time

async def monitoring_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    # Registrar métricas
    duration = time.time() - start_time
    api_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    response_time.labels(
        endpoint=request.url.path
    ).observe(duration)
    
    return response
```

## 6. Scripts de Despliegue

### 6.1 Script de Inicio

```bash
#!/bin/bash
# scripts/start_monitoring.sh

echo "Starting monitoring stack..."

cd docker/monitoring

# Crear red si no existe
docker network create ngx_network 2>/dev/null || true

# Iniciar servicios
docker-compose up -d

echo "Monitoring stack started!"
echo "Prometheus: http://localhost:9090"
echo "Grafana: http://localhost:3000 (admin/admin)"
```

## 7. Métricas Clave a Monitorear

### 7.1 Métricas de Negocio
- Tasa de conversión
- Tiempo promedio de conversación
- Distribución de tiers detectados
- ROI proyectado vs real

### 7.2 Métricas Técnicas
- Latencia de API (p50, p95, p99)
- Tasa de errores
- Uso de CPU/Memoria
- Conexiones a base de datos

### 7.3 Métricas de ML
- Precisión de modelos
- Confianza de predicciones
- Drift de datos
- Tiempo de inferencia

## 8. Mejores Prácticas

1. **Retención de Datos**: Configurar 15 días en Prometheus
2. **Backups**: Hacer backup de dashboards de Grafana
3. **Seguridad**: Usar autenticación en Grafana
4. **Escalabilidad**: Considerar Prometheus federation para múltiples instancias

## 9. Troubleshooting

### Problema: Métricas no aparecen
```bash
# Verificar que el endpoint funciona
curl http://localhost:8000/metrics

# Verificar targets en Prometheus
http://localhost:9090/targets
```

### Problema: Grafana no conecta
```bash
# Verificar red Docker
docker network inspect ngx_network

# Verificar logs
docker logs ngx_grafana
```