#!/bin/bash
# Script para construir y probar las imágenes Docker

set -e

echo "🚀 NGX Voice Sales Agent - Docker Build Script"
echo "============================================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir con color
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Verificar que estamos en el directorio correcto
if [ ! -f "requirements.txt" ]; then
    print_error "Error: Debe ejecutar este script desde la raíz del proyecto"
    exit 1
fi

# Opción de build
BUILD_TYPE=${1:-development}

echo ""
echo "Build Type: $BUILD_TYPE"
echo ""

# Build de desarrollo
if [ "$BUILD_TYPE" = "development" ]; then
    print_status "Construyendo imagen de desarrollo..."
    docker build -f docker/Dockerfile -t ngx-agent:dev .
    
    if [ $? -eq 0 ]; then
        print_status "Imagen de desarrollo construida exitosamente"
        echo ""
        echo "Para ejecutar en modo desarrollo:"
        echo "  docker-compose -f docker/docker-compose.yml up"
    else
        print_error "Error al construir imagen de desarrollo"
        exit 1
    fi

# Build de producción
elif [ "$BUILD_TYPE" = "production" ]; then
    print_status "Construyendo imagen de producción..."
    
    # Verificar que existe .env.production
    if [ ! -f ".env.production" ]; then
        print_warning "No se encontró .env.production, creando desde .env.example..."
        cp env.example .env.production
        print_warning "Por favor configure .env.production con valores de producción"
    fi
    
    # Build con multi-stage
    docker build -f docker/Dockerfile.production -t ngx-voice-sales-agent:latest .
    
    if [ $? -eq 0 ]; then
        print_status "Imagen de producción construida exitosamente"
        
        # Mostrar información de la imagen
        echo ""
        echo "📊 Información de la imagen:"
        docker images ngx-voice-sales-agent:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
        
        echo ""
        echo "Para ejecutar en modo producción:"
        echo "  docker-compose -f docker/docker-compose.production.yml up -d"
    else
        print_error "Error al construir imagen de producción"
        exit 1
    fi

# Test de la imagen
elif [ "$BUILD_TYPE" = "test" ]; then
    print_status "Ejecutando tests en contenedor..."
    
    # Build imagen de test
    docker build -f docker/Dockerfile -t ngx-agent:test .
    
    # Ejecutar tests
    docker run --rm \
        -v $(pwd):/app \
        -e PYTHONPATH=/app \
        --entrypoint pytest \
        ngx-agent:test \
        tests/unit -v
    
    if [ $? -eq 0 ]; then
        print_status "Tests ejecutados exitosamente"
    else
        print_error "Los tests fallaron"
        exit 1
    fi

# Análisis de seguridad
elif [ "$BUILD_TYPE" = "security" ]; then
    print_status "Ejecutando análisis de seguridad..."
    
    # Verificar si trivy está instalado
    if ! command -v trivy &> /dev/null; then
        print_warning "Trivy no está instalado. Instalando..."
        brew install aquasecurity/trivy/trivy || {
            print_error "No se pudo instalar Trivy"
            exit 1
        }
    fi
    
    # Escanear imagen
    print_status "Escaneando imagen de producción..."
    trivy image ngx-voice-sales-agent:latest
    
else
    print_error "Tipo de build no válido: $BUILD_TYPE"
    echo "Uso: ./docker/build.sh [development|production|test|security]"
    exit 1
fi

echo ""
print_status "¡Build completado!"