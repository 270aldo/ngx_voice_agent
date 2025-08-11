#!/bin/bash

# NGX Voice Sales Agent - SSL Certificate Setup
# This script sets up SSL certificates using Let's Encrypt or self-signed certificates

set -e

echo "🔐 NGX Voice Sales Agent - SSL Setup"
echo "===================================="

# Configuration
DOMAIN=${DOMAIN:-"api.ngx.ai"}
EMAIL=${EMAIL:-"ssl@ngx.ai"}
SSL_DIR="./nginx/ssl"
CERTBOT_DIR="./certbot"

# Check if running as root (required for certbot)
if [[ $EUID -ne 0 ]] && [[ "$1" != "--self-signed" ]]; then
   echo "❌ This script must be run as root for Let's Encrypt certificates"
   echo "   Or use: ./setup-ssl.sh --self-signed for development"
   exit 1
fi

# Create SSL directory
mkdir -p "$SSL_DIR"

# Function to generate self-signed certificate
generate_self_signed() {
    echo "🔨 Generating self-signed certificate for development..."
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/privkey.pem" \
        -out "$SSL_DIR/fullchain.pem" \
        -subj "/C=US/ST=State/L=City/O=NGX/CN=$DOMAIN"
    
    echo "✅ Self-signed certificate generated"
    echo "⚠️  WARNING: This certificate is for development only!"
}

# Function to setup Let's Encrypt
setup_letsencrypt() {
    echo "🔒 Setting up Let's Encrypt certificate for $DOMAIN..."
    
    # Install certbot if not present
    if ! command -v certbot &> /dev/null; then
        echo "📦 Installing certbot..."
        if command -v apt-get &> /dev/null; then
            apt-get update
            apt-get install -y certbot
        elif command -v yum &> /dev/null; then
            yum install -y certbot
        else
            echo "❌ Cannot install certbot. Please install manually."
            exit 1
        fi
    fi
    
    # Stop nginx if running
    docker-compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true
    
    # Create certbot directories
    mkdir -p "$CERTBOT_DIR/www"
    mkdir -p "$CERTBOT_DIR/conf"
    
    # Get certificate
    certbot certonly \
        --standalone \
        --preferred-challenges http \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        --force-renewal \
        -d "$DOMAIN" \
        --cert-path "$SSL_DIR/cert.pem" \
        --key-path "$SSL_DIR/privkey.pem" \
        --fullchain-path "$SSL_DIR/fullchain.pem"
    
    # Set permissions
    chmod 644 "$SSL_DIR/fullchain.pem"
    chmod 600 "$SSL_DIR/privkey.pem"
    
    echo "✅ Let's Encrypt certificate obtained successfully"
    
    # Setup auto-renewal
    setup_auto_renewal
}

# Function to setup auto-renewal
setup_auto_renewal() {
    echo "⏰ Setting up automatic certificate renewal..."
    
    # Create renewal script
    cat > "$SSL_DIR/renew-cert.sh" << 'EOF'
#!/bin/bash
certbot renew --quiet --no-self-upgrade --post-hook "docker-compose -f /app/docker-compose.prod.yml restart nginx"
EOF
    
    chmod +x "$SSL_DIR/renew-cert.sh"
    
    # Add cron job
    if ! crontab -l 2>/dev/null | grep -q "renew-cert.sh"; then
        (crontab -l 2>/dev/null; echo "0 0,12 * * * $PWD/$SSL_DIR/renew-cert.sh >> /var/log/letsencrypt/renewal.log 2>&1") | crontab -
        echo "✅ Cron job added for automatic renewal"
    fi
}

# Function to verify SSL setup
verify_ssl() {
    echo "🔍 Verifying SSL certificate..."
    
    if [[ -f "$SSL_DIR/fullchain.pem" ]] && [[ -f "$SSL_DIR/privkey.pem" ]]; then
        # Check certificate details
        openssl x509 -in "$SSL_DIR/fullchain.pem" -text -noout | grep -E "(Subject:|Not After)"
        echo "✅ SSL certificate files found and valid"
    else
        echo "❌ SSL certificate files not found!"
        exit 1
    fi
}

# Function to generate Diffie-Hellman parameters
generate_dhparam() {
    echo "🔐 Generating Diffie-Hellman parameters (this may take a while)..."
    
    if [[ ! -f "$SSL_DIR/dhparam.pem" ]]; then
        openssl dhparam -out "$SSL_DIR/dhparam.pem" 2048
        echo "✅ DH parameters generated"
    else
        echo "ℹ️  DH parameters already exist"
    fi
}

# Main execution
if [[ "$1" == "--self-signed" ]]; then
    generate_self_signed
else
    setup_letsencrypt
fi

# Always generate DH params
generate_dhparam

# Verify setup
verify_ssl

echo ""
echo "🎉 SSL setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Update your DNS to point $DOMAIN to this server"
echo "   2. Start the production stack: docker-compose -f docker-compose.prod.yml up -d"
echo "   3. Verify HTTPS access: https://$DOMAIN/health"
echo ""

if [[ "$1" == "--self-signed" ]]; then
    echo "⚠️  Remember: Self-signed certificates will show security warnings in browsers"
    echo "   For production, run this script without --self-signed flag"
fi