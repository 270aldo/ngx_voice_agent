#!/bin/bash
# Script de despliegue completo para producción
# NGX Voice Sales Agent

set -e

echo "🚀 NGX Voice Sales Agent - Production Deployment"
echo "================================================"

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Funciones de utilidad
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Variables
DEPLOYMENT_MODE=${1:-full}  # full, app-only, monitoring-only
ENVIRONMENT=${2:-production}

# Verificar prerrequisitos
check_requirements() {
    log_info "Verificando prerrequisitos..."
    
    # Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker no está instalado"
        exit 1
    fi
    
    # Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose no está instalado"
        exit 1
    fi
    
    # Archivos de configuración
    if [ ! -f ".env.production" ]; then
        log_error ".env.production no encontrado"
        log_warning "Copia env.example a .env.production y configura las variables"
        exit 1
    fi
    
    log_success "Todos los prerrequisitos cumplidos"
}

# Validar configuración
validate_config() {
    log_info "Validando configuración..."
    
    # Ejecutar script de validación
    if [ -f "docker/validate.sh" ]; then
        bash docker/validate.sh
        if [ $? -ne 0 ]; then
            log_error "La validación de Docker falló"
            exit 1
        fi
    fi
    
    log_success "Configuración validada"
}

# Construir imágenes
build_images() {
    log_info "Construyendo imágenes de producción..."
    
    # Build de la aplicación
    bash docker/build.sh production
    if [ $? -ne 0 ]; then
        log_error "Error al construir imagen de producción"
        exit 1
    fi
    
    log_success "Imágenes construidas exitosamente"
}

# Realizar backup antes del despliegue
backup_data() {
    log_info "Realizando backup de datos..."
    
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup de volúmenes Docker si existen
    if docker volume ls | grep -q "ngx-logs"; then
        docker run --rm -v ngx-logs:/data -v $(pwd)/$BACKUP_DIR:/backup alpine tar -czf /backup/logs.tar.gz -C /data .
        log_success "Backup de logs realizado"
    fi
    
    if docker volume ls | grep -q "redis-data"; then
        docker run --rm -v redis-data:/data -v $(pwd)/$BACKUP_DIR:/backup alpine tar -czf /backup/redis.tar.gz -C /data .
        log_success "Backup de Redis realizado"
    fi
    
    log_success "Backup completado en $BACKUP_DIR"
}

# Desplegar aplicación
deploy_app() {
    log_info "Desplegando aplicación principal..."
    
    # Detener servicios existentes
    docker-compose -f docker/docker-compose.production.yml down
    
    # Iniciar servicios
    docker-compose -f docker/docker-compose.production.yml up -d
    
    # Esperar a que los servicios estén listos
    log_info "Esperando a que los servicios estén listos..."
    sleep 10
    
    # Verificar salud
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "Aplicación desplegada y saludable"
    else
        log_error "La aplicación no responde correctamente"
        docker-compose -f docker/docker-compose.production.yml logs --tail=50
        exit 1
    fi
}

# Desplegar monitoreo
deploy_monitoring() {
    log_info "Desplegando stack de monitoreo..."
    
    # Crear red externa si no existe
    docker network create ngx-network 2>/dev/null || true
    
    # Desplegar servicios de monitoreo
    docker-compose -f monitoring/docker-compose.monitoring.yml up -d
    
    # Esperar a que Grafana esté listo
    log_info "Esperando a que Grafana esté listo..."
    sleep 20
    
    # Verificar servicios
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        log_success "Grafana disponible en http://localhost:3000"
    else
        log_warning "Grafana aún no está listo"
    fi
    
    if curl -f http://localhost:9090 > /dev/null 2>&1; then
        log_success "Prometheus disponible en http://localhost:9090"
    else
        log_warning "Prometheus aún no está listo"
    fi
}

# Configurar SSL
configure_ssl() {
    log_info "Configurando SSL..."
    
    # Verificar si ya existen certificados
    if [ -f "docker/nginx/ssl/fullchain.pem" ] && [ -f "docker/nginx/ssl/privkey.pem" ]; then
        log_success "Certificados SSL ya configurados"
    else
        log_warning "Certificados SSL no encontrados"
        log_info "Para producción, coloca tus certificados en:"
        log_info "  - docker/nginx/ssl/fullchain.pem"
        log_info "  - docker/nginx/ssl/privkey.pem"
        log_info "O usa Let's Encrypt con certbot"
    fi
}

# Ejecutar tests de humo
run_smoke_tests() {
    log_info "Ejecutando tests de humo..."
    
    # Test de endpoints principales
    ENDPOINTS=(
        "http://localhost:8000/health"
        "http://localhost:8000/docs"
        "http://localhost:9090/api/v1/query?query=up"
        "http://localhost:3000/api/health"
    )
    
    for endpoint in "${ENDPOINTS[@]}"; do
        if curl -f "$endpoint" > /dev/null 2>&1; then
            log_success "Endpoint OK: $endpoint"
        else
            log_warning "Endpoint no disponible: $endpoint"
        fi
    done
}

# Mostrar estado final
show_status() {
    echo ""
    echo "======================================="
    echo "📊 Estado del Despliegue"
    echo "======================================="
    echo ""
    
    # Servicios principales
    docker-compose -f docker/docker-compose.production.yml ps
    
    echo ""
    echo "======================================="
    echo "🔗 URLs de Acceso"
    echo "======================================="
    echo ""
    echo "🌐 Aplicación: http://localhost (Nginx)"
    echo "🚀 API Directa: http://localhost:8000"
    echo "📊 Grafana: http://localhost:3000 (admin/admin)"
    echo "📈 Prometheus: http://localhost:9090"
    echo "🔔 Alertmanager: http://localhost:9093"
    echo ""
    echo "======================================="
    echo "📝 Próximos Pasos"
    echo "======================================="
    echo ""
    echo "1. Configurar certificados SSL para HTTPS"
    echo "2. Cambiar contraseñas por defecto en Grafana"
    echo "3. Configurar alertas en Alertmanager"
    echo "4. Revisar logs: docker-compose -f docker/docker-compose.production.yml logs -f"
    echo "5. Ejecutar tests de carga: cd load-testing && python scripts/run_load_tests.py"
}

# Función principal
main() {
    echo ""
    log_info "Modo de despliegue: $DEPLOYMENT_MODE"
    log_info "Entorno: $ENVIRONMENT"
    echo ""
    
    # Verificar requisitos
    check_requirements
    
    # Validar configuración
    validate_config
    
    case $DEPLOYMENT_MODE in
        "full")
            # Despliegue completo
            build_images
            backup_data
            deploy_app
            deploy_monitoring
            configure_ssl
            run_smoke_tests
            ;;
        "app-only")
            # Solo aplicación
            build_images
            backup_data
            deploy_app
            run_smoke_tests
            ;;
        "monitoring-only")
            # Solo monitoreo
            deploy_monitoring
            ;;
        *)
            log_error "Modo de despliegue no válido: $DEPLOYMENT_MODE"
            echo "Uso: $0 [full|app-only|monitoring-only] [production|staging]"
            exit 1
            ;;
    esac
    
    # Mostrar estado final
    show_status
    
    log_success "¡Despliegue completado exitosamente!"
}

# Ejecutar
main