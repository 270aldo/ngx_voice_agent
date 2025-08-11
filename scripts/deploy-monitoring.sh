#!/bin/bash
# Script para desplegar el stack de monitoreo

set -e

echo "📊 Desplegando Stack de Monitoreo NGX"
echo "===================================="

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Funciones
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Verificar que estamos en el directorio correcto
if [ ! -f "requirements.txt" ]; then
    print_error "Error: Debe ejecutar este script desde la raíz del proyecto"
    exit 1
fi

echo ""
echo "1. Verificando prerrequisitos..."
echo "--------------------------------"

# Verificar Docker
if ! docker info &> /dev/null; then
    print_error "Docker no está corriendo. Por favor inicie Docker."
    exit 1
fi
print_success "Docker está corriendo"

# Verificar red NGX
if docker network ls | grep -q "ngx-network"; then
    print_success "Red ngx-network existe"
else
    print_info "Creando red ngx-network..."
    docker network create ngx-network
    print_success "Red ngx-network creada"
fi

echo ""
echo "2. Configurando directorios..."
echo "------------------------------"

# Crear directorios necesarios
DIRS=(
    "monitoring/loki"
    "monitoring/promtail"
    "monitoring/grafana/dashboards"
    "monitoring/prometheus/data"
    "monitoring/grafana/data"
)

for dir in "${DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_success "Directorio creado: $dir"
    fi
done

echo ""
echo "3. Configurando archivos..."
echo "---------------------------"

# Crear configuración básica de Loki si no existe
if [ ! -f "monitoring/loki/config.yml" ]; then
    cat > monitoring/loki/config.yml << 'EOF'
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  reject_old_samples: true
  reject_old_samples_max_age: 168h

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: false
  retention_period: 0s
EOF
    print_success "Configuración de Loki creada"
fi

# Crear configuración de Promtail si no existe
if [ ! -f "monitoring/promtail/config.yml" ]; then
    cat > monitoring/promtail/config.yml << 'EOF'
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: ngx-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: ngx-voice-agent
          __path__: /app/logs/*.log
EOF
    print_success "Configuración de Promtail creada"
fi

echo ""
echo "4. Configurando permisos..."
echo "---------------------------"

# Configurar permisos para Grafana
chmod -R 777 monitoring/grafana/data 2>/dev/null || true
print_success "Permisos configurados"

echo ""
echo "5. Desplegando servicios..."
echo "---------------------------"

# Cambiar al directorio de monitoreo
cd monitoring

# Verificar si ya hay servicios corriendo
if docker-compose ps 2>/dev/null | grep -q "Up"; then
    print_warning "Servicios de monitoreo ya están corriendo"
    read -p "¿Desea reiniciar los servicios? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose -f docker-compose.monitoring.yml down
        print_success "Servicios detenidos"
    else
        print_info "Manteniendo servicios actuales"
        cd ..
        exit 0
    fi
fi

# Desplegar servicios
print_info "Iniciando servicios de monitoreo..."
if docker-compose -f docker-compose.monitoring.yml up -d; then
    print_success "Servicios de monitoreo iniciados"
else
    print_error "Error al iniciar servicios"
    cd ..
    exit 1
fi

# Volver al directorio raíz
cd ..

echo ""
echo "6. Esperando a que los servicios estén listos..."
echo "------------------------------------------------"

# Función para verificar servicio
check_service() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "Verificando $service... "
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Listo"
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    echo -e "${RED}✗${NC} Timeout"
    return 1
}

# Verificar servicios
check_service "Prometheus" "http://localhost:9090/-/ready"
check_service "Grafana" "http://localhost:3000/api/health"
check_service "Alertmanager" "http://localhost:9093/-/ready"

echo ""
echo "7. Configurando dashboards..."
echo "-----------------------------"

# Importar dashboards adicionales si es necesario
print_info "Los dashboards se cargarán automáticamente desde la configuración"

echo ""
echo "========================================"
echo "✅ Stack de Monitoreo Desplegado"
echo "========================================"
echo ""
echo "📊 URLs de acceso:"
echo "  - Grafana: http://localhost:3000"
echo "    Usuario: admin"
echo "    Contraseña: admin (cambiar en primer login)"
echo ""
echo "  - Prometheus: http://localhost:9090"
echo "  - Alertmanager: http://localhost:9093"
echo ""
echo "📈 Dashboards disponibles:"
echo "  - NGX Voice Agent - Overview"
echo "  - NGX Voice Agent - ML Performance"
echo "  - NGX Voice Agent - Business Metrics"
echo ""
echo "🔧 Comandos útiles:"
echo "  - Ver logs: docker-compose -f monitoring/docker-compose.monitoring.yml logs -f"
echo "  - Detener: docker-compose -f monitoring/docker-compose.monitoring.yml down"
echo "  - Reiniciar: docker-compose -f monitoring/docker-compose.monitoring.yml restart"
echo ""
echo "📚 Documentación: docs/MONITORING_SETUP.md"