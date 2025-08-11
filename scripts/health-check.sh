#!/bin/bash
# Script de monitoreo de salud del sistema

set -e

# Configuración
API_URL=${API_URL:-"http://localhost:8000"}
TIMEOUT=5

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🏥 NGX Voice Sales Agent - Health Check"
echo "======================================="
echo ""
echo "Verificando: $API_URL"
echo ""

# Función para verificar endpoint
check_endpoint() {
    local endpoint=$1
    local expected_status=$2
    local description=$3
    
    echo -n "Verificando $description... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" -m $TIMEOUT "$API_URL$endpoint" 2>/dev/null || echo "000")
    
    if [ "$response" = "$expected_status" ]; then
        echo -e "${GREEN}✓${NC} OK (HTTP $response)"
        return 0
    elif [ "$response" = "000" ]; then
        echo -e "${RED}✗${NC} Sin respuesta (timeout o error de conexión)"
        return 1
    else
        echo -e "${YELLOW}⚠${NC} HTTP $response (esperado: $expected_status)"
        return 1
    fi
}

# Verificar endpoints principales
echo "1. Endpoints de salud:"
echo "----------------------"
check_endpoint "/health" "200" "Health endpoint"
check_endpoint "/docs" "200" "API Documentation"

echo ""
echo "2. Servicios Docker:"
echo "--------------------"

# Verificar contenedores Docker
if command -v docker &> /dev/null; then
    # Verificar si hay contenedores NGX corriendo
    containers=$(docker ps --filter "name=ngx" --format "table {{.Names}}\t{{.Status}}" | tail -n +2)
    
    if [ -z "$containers" ]; then
        echo -e "${YELLOW}⚠${NC} No hay contenedores NGX en ejecución"
    else
        echo -e "${GREEN}Contenedores activos:${NC}"
        echo "$containers" | while IFS= read -r line; do
            echo "  $line"
        done
    fi
else
    echo -e "${YELLOW}⚠${NC} Docker no disponible"
fi

echo ""
echo "3. Uso de recursos:"
echo "-------------------"

if command -v docker &> /dev/null && [ -n "$(docker ps -q --filter name=ngx)" ]; then
    # Obtener estadísticas de Docker
    echo "Estadísticas de contenedores:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" $(docker ps -q --filter name=ngx)
else
    echo -e "${YELLOW}⚠${NC} No se pueden obtener estadísticas"
fi

echo ""
echo "4. Logs recientes:"
echo "------------------"

if [ -d "logs" ] && [ "$(ls -A logs)" ]; then
    echo "Últimas líneas de logs:"
    # Mostrar últimas 5 líneas del log más reciente
    latest_log=$(ls -t logs/*.log 2>/dev/null | head -1)
    if [ -n "$latest_log" ]; then
        echo "Archivo: $latest_log"
        tail -5 "$latest_log" | sed 's/^/  /'
    else
        echo -e "${YELLOW}⚠${NC} No se encontraron archivos de log"
    fi
else
    echo -e "${YELLOW}⚠${NC} Directorio de logs vacío o no existe"
fi

echo ""
echo "5. Conectividad externa:"
echo "------------------------"

# Verificar conectividad a servicios externos
echo -n "OpenAI API... "
if curl -s -m $TIMEOUT https://api.openai.com/v1 >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Accesible"
else
    echo -e "${RED}✗${NC} No accesible"
fi

echo -n "Supabase... "
if [ -n "$SUPABASE_URL" ]; then
    if curl -s -m $TIMEOUT "$SUPABASE_URL/rest/v1/" >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Accesible"
    else
        echo -e "${RED}✗${NC} No accesible"
    fi
else
    echo -e "${YELLOW}⚠${NC} SUPABASE_URL no configurado"
fi

echo ""
echo "======================================="
echo "Health check completado $(date '+%Y-%m-%d %H:%M:%S')"

# Retornar código de error si algo falló
if [ $? -ne 0 ]; then
    exit 1
fi