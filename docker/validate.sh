#!/bin/bash
# Script para validar la configuración de Docker

set -e

echo "🔍 Validando configuración de Docker para NGX Voice Sales Agent"
echo "============================================================="

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Funciones de utilidad
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    VALIDATION_FAILED=1
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

VALIDATION_FAILED=0

echo ""
echo "1. Verificando prerrequisitos..."
echo "--------------------------------"

# Verificar Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    check_pass "Docker instalado: v$DOCKER_VERSION"
else
    check_fail "Docker no está instalado"
fi

# Verificar Docker Compose
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)
    check_pass "Docker Compose instalado: v$COMPOSE_VERSION"
else
    check_fail "Docker Compose no está instalado"
fi

# Verificar que Docker está corriendo
if docker info &> /dev/null; then
    check_pass "Docker daemon está corriendo"
else
    check_fail "Docker daemon no está corriendo"
fi

echo ""
echo "2. Verificando archivos de configuración..."
echo "------------------------------------------"

# Verificar archivos Docker
FILES_TO_CHECK=(
    "docker/Dockerfile"
    "docker/Dockerfile.production"
    "docker/docker-compose.yml"
    "docker/docker-compose.production.yml"
    "docker/nginx/nginx.conf"
    ".dockerignore"
)

for file in "${FILES_TO_CHECK[@]}"; do
    if [ -f "$file" ]; then
        check_pass "Archivo existe: $file"
    else
        check_fail "Archivo faltante: $file"
    fi
done

echo ""
echo "3. Verificando configuración de entorno..."
echo "------------------------------------------"

# Verificar .env
if [ -f ".env" ]; then
    check_pass "Archivo .env existe"
    
    # Verificar variables requeridas
    REQUIRED_VARS=(
        "OPENAI_API_KEY"
        "ELEVENLABS_API_KEY"
        "SUPABASE_URL"
        "SUPABASE_ANON_KEY"
    )
    
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^$var=" .env && ! grep -q "^$var=$" .env && ! grep -q "^$var=your_" .env; then
            check_pass "Variable configurada: $var"
        else
            check_warn "Variable no configurada o con valor por defecto: $var"
        fi
    done
else
    check_fail "Archivo .env no existe"
    check_warn "Copia env.example a .env y configura las variables"
fi

# Verificar .env.production
if [ -f ".env.production" ]; then
    check_pass "Archivo .env.production existe"
else
    check_warn "Archivo .env.production no existe (necesario para producción)"
fi

echo ""
echo "4. Verificando estructura del proyecto..."
echo "-----------------------------------------"

# Verificar directorios requeridos
REQUIRED_DIRS=(
    "src"
    "src/api"
    "src/services"
    "configs"
    "logs"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        check_pass "Directorio existe: $dir"
    else
        check_fail "Directorio faltante: $dir"
        if [ "$dir" = "logs" ]; then
            mkdir -p logs
            check_warn "Directorio logs creado"
        fi
    fi
done

echo ""
echo "5. Verificando requisitos Python..."
echo "-----------------------------------"

if [ -f "requirements.txt" ]; then
    check_pass "requirements.txt existe"
    
    # Verificar principales dependencias
    MAIN_DEPS=(
        "fastapi"
        "uvicorn"
        "openai"
        "elevenlabs"
        "supabase"
    )
    
    for dep in "${MAIN_DEPS[@]}"; do
        if grep -q "^$dep" requirements.txt; then
            check_pass "Dependencia listada: $dep"
        else
            check_fail "Dependencia faltante: $dep"
        fi
    done
else
    check_fail "requirements.txt no existe"
fi

echo ""
echo "6. Intentando construir imagen de desarrollo..."
echo "-----------------------------------------------"

# Intentar build de desarrollo
if docker build -f docker/Dockerfile -t ngx-agent:dev-test . > /dev/null 2>&1; then
    check_pass "Build de desarrollo exitoso"
    
    # Verificar tamaño de imagen
    IMAGE_SIZE=$(docker images ngx-agent:dev-test --format "{{.Size}}")
    check_pass "Tamaño de imagen: $IMAGE_SIZE"
    
    # Limpiar imagen de prueba
    docker rmi ngx-agent:dev-test > /dev/null 2>&1
else
    check_fail "Build de desarrollo falló"
    check_warn "Ejecuta './docker/build.sh development' para ver detalles"
fi

echo ""
echo "7. Verificando puertos..."
echo "-------------------------"

# Verificar si el puerto 8000 está disponible
if ! lsof -i:8000 &> /dev/null; then
    check_pass "Puerto 8000 disponible"
else
    check_warn "Puerto 8000 en uso"
fi

# Verificar si el puerto 80 está disponible (para nginx)
if ! lsof -i:80 &> /dev/null; then
    check_pass "Puerto 80 disponible"
else
    check_warn "Puerto 80 en uso (puede requerir sudo para nginx)"
fi

echo ""
echo "8. Recomendaciones finales..."
echo "------------------------------"

if [ $VALIDATION_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Validación completada exitosamente!${NC}"
    echo ""
    echo "Próximos pasos:"
    echo "1. Construir imagen de desarrollo: ./docker/build.sh development"
    echo "2. Ejecutar en desarrollo: docker-compose -f docker/docker-compose.yml up"
    echo "3. Para producción: ./docker/build.sh production"
else
    echo -e "${RED}❌ La validación encontró problemas${NC}"
    echo ""
    echo "Por favor revisa los errores arriba y:"
    echo "1. Instala las dependencias faltantes"
    echo "2. Crea los archivos de configuración necesarios"
    echo "3. Configura las variables de entorno"
fi

echo ""
echo "Para más información, consulta docs/DOCKER_DEPLOYMENT.md"