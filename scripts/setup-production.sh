#!/bin/bash
# Script de configuración automatizada para producción

set -e

echo "🚀 NGX Voice Sales Agent - Production Setup"
echo "=========================================="

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Funciones de utilidad
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
if command -v docker &> /dev/null; then
    print_success "Docker instalado"
else
    print_error "Docker no está instalado"
    exit 1
fi

# Verificar openssl para certificados
if command -v openssl &> /dev/null; then
    print_success "OpenSSL instalado"
else
    print_error "OpenSSL no está instalado (necesario para certificados SSL)"
    exit 1
fi

echo ""
echo "2. Configurando variables de entorno..."
echo "---------------------------------------"

# Crear .env.production si no existe
if [ ! -f ".env.production" ]; then
    print_info "Creando archivo .env.production desde template..."
    cp .env.production.example .env.production
    print_warning "Por favor edite .env.production con sus valores de producción"
    
    # Preguntar si desea editar ahora
    read -p "¿Desea editar .env.production ahora? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} .env.production
    fi
else
    print_success "Archivo .env.production existe"
fi

echo ""
echo "3. Configurando certificados SSL..."
echo "-----------------------------------"

SSL_DIR="docker/nginx/ssl"
if [ ! -f "$SSL_DIR/fullchain.pem" ] || [ ! -f "$SSL_DIR/privkey.pem" ]; then
    print_warning "No se encontraron certificados SSL"
    read -p "¿Desea generar certificados autofirmados para staging? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd docker/nginx
        ./generate-ssl.sh
        cd ../..
        print_success "Certificados SSL generados"
    else
        print_warning "Recuerde configurar certificados SSL válidos para producción"
    fi
else
    print_success "Certificados SSL encontrados"
fi

echo ""
echo "4. Configurando secretos..."
echo "---------------------------"

# Función para generar secretos seguros
generate_secret() {
    openssl rand -base64 32
}

# Verificar JWT_SECRET
if grep -q "^JWT_SECRET=your_secure_jwt_secret_here" .env.production; then
    print_warning "JWT_SECRET no configurado, generando uno nuevo..."
    NEW_SECRET=$(generate_secret)
    sed -i.bak "s/JWT_SECRET=your_secure_jwt_secret_here/JWT_SECRET=$NEW_SECRET/" .env.production
    print_success "JWT_SECRET generado y configurado"
fi

# Verificar REDIS_PASSWORD
if grep -q "^REDIS_PASSWORD=your_redis_password_here" .env.production; then
    print_warning "REDIS_PASSWORD no configurado, generando uno nuevo..."
    NEW_PASSWORD=$(generate_secret)
    sed -i.bak "s/REDIS_PASSWORD=your_redis_password_here/REDIS_PASSWORD=$NEW_PASSWORD/" .env.production
    print_success "REDIS_PASSWORD generado y configurado"
fi

echo ""
echo "5. Creando directorios necesarios..."
echo "------------------------------------"

# Crear directorios para volúmenes
DIRS=("logs" "tmp" "data")
for dir in "${DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_success "Directorio creado: $dir"
    else
        print_success "Directorio existe: $dir"
    fi
done

echo ""
echo "6. Configurando permisos..."
echo "---------------------------"

# Configurar permisos para logs
chmod 755 logs
print_success "Permisos configurados para logs"

echo ""
echo "7. Validando configuración..."
echo "------------------------------"

# Verificar variables críticas en .env.production
CRITICAL_VARS=(
    "OPENAI_API_KEY"
    "ELEVENLABS_API_KEY"
    "SUPABASE_URL"
    "SUPABASE_ANON_KEY"
    "SUPABASE_SERVICE_KEY"
)

MISSING_VARS=()
for var in "${CRITICAL_VARS[@]}"; do
    if grep -q "^$var=" .env.production && ! grep -q "^$var=your_" .env.production && ! grep -q "^$var=$" .env.production; then
        print_success "$var configurado"
    else
        print_error "$var NO configurado"
        MISSING_VARS+=("$var")
    fi
done

echo ""
echo "8. Construyendo imagen de producción..."
echo "---------------------------------------"

if [ ${#MISSING_VARS[@]} -eq 0 ]; then
    print_info "Construyendo imagen Docker de producción..."
    if docker build -f docker/Dockerfile.production -t ngx-voice-sales-agent:latest . ; then
        print_success "Imagen de producción construida exitosamente"
        
        # Mostrar información de la imagen
        echo ""
        print_info "Información de la imagen:"
        docker images ngx-voice-sales-agent:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
    else
        print_error "Error al construir imagen de producción"
        exit 1
    fi
else
    print_warning "No se puede construir la imagen sin las variables críticas configuradas"
fi

echo ""
echo "9. Configuración de firewall (opcional)..."
echo "------------------------------------------"

print_info "Puertos requeridos:"
echo "  - 80 (HTTP)"
echo "  - 443 (HTTPS)"
echo "  - 8000 (API - solo interno)"
echo "  - 9090 (Prometheus - solo interno)"

echo ""
echo "10. Resumen y próximos pasos..."
echo "--------------------------------"

if [ ${#MISSING_VARS[@]} -eq 0 ]; then
    print_success "¡Configuración de producción completada!"
    echo ""
    echo "Para iniciar el sistema en producción:"
    echo "  docker-compose -f docker/docker-compose.production.yml up -d"
    echo ""
    echo "Para ver los logs:"
    echo "  docker-compose -f docker/docker-compose.production.yml logs -f"
else
    print_warning "Configuración incompleta"
    echo ""
    echo "Por favor configure las siguientes variables en .env.production:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Luego ejecute este script nuevamente."
fi

echo ""
echo "📚 Documentación adicional:"
echo "  - docs/DOCKER_DEPLOYMENT.md"
echo "  - docs/MONITORING_SETUP.md"
echo ""

# Limpiar archivos de respaldo
rm -f .env.production.bak 2>/dev/null || true

print_success "Script completado"