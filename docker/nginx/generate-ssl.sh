#!/bin/bash
# Script para generar certificados SSL autofirmados (solo para desarrollo/staging)

set -e

echo "🔐 Generando certificados SSL autofirmados para desarrollo..."

# Directorio de SSL
SSL_DIR="./ssl"
mkdir -p $SSL_DIR

# Configuración
DOMAIN=${1:-localhost}
DAYS=365
COUNTRY="US"
STATE="California"
LOCALITY="San Francisco"
ORGANIZATION="NGX AI"
ORGANIZATIONAL_UNIT="Development"
EMAIL="dev@ngx.ai"

# Generar clave privada
echo "Generando clave privada..."
openssl genrsa -out $SSL_DIR/privkey.pem 2048

# Generar certificado autofirmado
echo "Generando certificado autofirmado..."
openssl req -new -x509 -key $SSL_DIR/privkey.pem -out $SSL_DIR/fullchain.pem -days $DAYS \
    -subj "/C=$COUNTRY/ST=$STATE/L=$LOCALITY/O=$ORGANIZATION/OU=$ORGANIZATIONAL_UNIT/CN=$DOMAIN/emailAddress=$EMAIL"

# Verificar certificado
echo ""
echo "✅ Certificados generados exitosamente:"
echo "  - Clave privada: $SSL_DIR/privkey.pem"
echo "  - Certificado: $SSL_DIR/fullchain.pem"
echo ""
echo "📋 Información del certificado:"
openssl x509 -in $SSL_DIR/fullchain.pem -text -noout | grep -E "(Subject:|Not Before:|Not After:)"

echo ""
echo "⚠️  ADVERTENCIA: Estos certificados son autofirmados y solo deben usarse para desarrollo/staging."
echo "Para producción, use certificados válidos de Let's Encrypt o su CA preferida."