#!/bin/bash
# ACAS Pro - SSL Certificate Auto-Renewal
# Run via cron: 0 2 * * * /path/to/ssl_renew.sh

set -e

DOMAIN="${ACAS_DOMAIN:-localhost}"
EMAIL="${ACAS_ADMIN_EMAIL:-admin@example.com}"
CERT_DIR="/etc/nginx/ssl"
NGINX_BIN="${NGINX_BIN:-/usr/sbin/nginx}"
LOG_FILE="/var/log/acas/ssl-renew.log"

# Logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")"

log "Starting SSL certificate renewal check..."

# Check if using Let's Encrypt or self-signed
if [ -f "$CERT_DIR/letsencrypt.flag" ]; then
    # Let's Encrypt renewal
    log "Using Let's Encrypt certificates"
    
    if command -v certbot &> /dev/null; then
        certbot renew --quiet --deploy-hook "systemctl reload nginx"
        log "Let's Encrypt renewal completed"
    else
        log "ERROR: certbot not found"
        exit 1
    fi
else
    # Self-signed certificate - check expiration
    log "Using self-signed certificates"
    
    CERT_FILE="$CERT_DIR/cert.pem"
    if [ -f "$CERT_FILE" ]; then
        # Check expiration (30 days warning)
        EXPIRY=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f2)
        EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
        NOW_EPOCH=$(date +%s)
        DAYS_UNTIL_EXPIRY=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
        
        log "Certificate expires in $DAYS_UNTIL_EXPIRY days"
        
        if [ $DAYS_UNTIL_EXPIRY -lt 30 ]; then
            log "WARNING: Certificate expires soon, regenerating..."
            
            # Backup old cert
            BACKUP_DIR="$CERT_DIR/backup/$(date +%Y%m%d)"
            mkdir -p "$BACKUP_DIR"
            cp "$CERT_DIR"/*.pem "$BACKUP_DIR/" 2>/dev/null || true
            
            # Generate new self-signed cert
            openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
                -keyout "$CERT_DIR/key.pem" \
                -out "$CERT_DIR/cert.pem" \
                -subj "/CN=$DOMAIN/O=ACAS Pro/C=CN" \
                -addext "subjectAltName=DNS:$DOMAIN,DNS:*.$DOMAIN,IP:127.0.0.1,IP:::1"
            
            # Reload nginx
            $NGINX_BIN -s reload
            log "Certificate regenerated and nginx reloaded"
        else
            log "Certificate valid, no action needed"
        fi
    else
        log "ERROR: Certificate file not found"
        exit 1
    fi
fi

# Verify certificate
log "Verifying certificate..."
if openssl x509 -checkend 86400 -noout -in "$CERT_DIR/cert.pem"; then
    log "Certificate valid for at least 24 hours"
else
    log "ERROR: Certificate verification failed"
    exit 1
fi

log "SSL renewal check completed"
