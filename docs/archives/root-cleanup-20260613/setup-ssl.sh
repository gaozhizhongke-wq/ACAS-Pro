#!/bin/bash
# ACAS Pro SSL Certificate Setup
# Supports: Let's Encrypt (production) + Self-signed (development)

set -e

SSL_DIR="$(dirname "$0")/ssl"
ENVIRONMENT="${ENVIRONMENT:-development}"
DOMAIN="${DOMAIN:-localhost}"

echo "=== ACAS Pro SSL Certificate Setup ==="
echo "Environment: $ENVIRONMENT"
echo "Domain: $DOMAIN"
echo ""

# Create SSL directory
mkdir -p "$SSL_DIR"

if [ "$ENVIRONMENT" = "production" ]; then
    echo "🔒 Production: Using Let's Encrypt"
    
    # Check if certbot is installed
    if ! command -v certbot &> /dev/null; then
        echo "Installing certbot..."
        if command -v apt-get &> /dev/null; then
            apt-get update && apt-get install -y certbot
        elif command -v yum &> /dev/null; then
            yum install -y certbot
        else
            echo "❌ Please install certbot manually"
            exit 1
        fi
    fi
    
    # Generate certificate
    certbot certonly \
        --standalone \
        --agree-tos \
        --non-interactive \
        --email ${ADMIN_EMAIL:-admin@acas.pro} \
        -d "$DOMAIN"
    
    # Copy certificates
    cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$SSL_DIR/cert.pem"
    cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$SSL_DIR/key.pem"
    
    # Setup auto-renewal
    echo "0 3 * * * root certbot renew --quiet" | tee /etc/cron.d/certbot-renewal
    
    echo "✅ Let's Encrypt certificate installed"
    echo "📅 Auto-renewal: Daily at 3:00 AM"
    
else
    echo "🔧 Development: Using self-signed certificate"
    
    # Generate self-signed certificate
    openssl req -x509 \
        -nodes \
        -days 365 \
        -newkey rsa:2048 \
        -keyout "$SSL_DIR/key.pem" \
        -out "$SSL_DIR/cert.pem" \
        -subj "/C=CN/ST=Beijing/L=Beijing/O=ACAS Pro/CN=$DOMAIN" \
        -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost,IP:127.0.0.1"
    
    echo "✅ Self-signed certificate generated (365 days)"
    echo "⚠️  Browsers will show security warning - this is normal for development"
fi

# Set permissions
chmod 600 "$SSL_DIR/key.pem"
chmod 644 "$SSL_DIR/cert.pem"

echo ""
echo "📁 Certificate location: $SSL_DIR"
echo "🔐 Key: $SSL_DIR/key.pem"
echo "📄 Cert: $SSL_DIR/cert.pem"
echo ""
echo "🚀 Next steps:"
echo "   1. Update docker-compose.yml with your domain"
echo "   2. Run: docker-compose up -d nginx"
echo "   3. Test: curl -k https://localhost/api/health"
