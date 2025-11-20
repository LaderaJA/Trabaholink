#!/bin/bash
# Generate self-signed SSL certificate for development/testing
# For production, use Let's Encrypt instead

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSL_DIR="$SCRIPT_DIR/../nginx/ssl"

echo "🔐 Generating Self-Signed SSL Certificate"
echo "=========================================="
echo ""

# Create SSL directory if it doesn't exist
mkdir -p "$SSL_DIR"

# Prompt for domain name
read -p "Enter domain name (default: localhost): " DOMAIN
DOMAIN=${DOMAIN:-localhost}

echo ""
echo "Generating certificate for: $DOMAIN"
echo ""

# Generate private key and certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SSL_DIR/key.pem" \
    -out "$SSL_DIR/cert.pem" \
    -subj "/C=PH/ST=Metro Manila/L=Manila/O=Trabaholink/OU=IT/CN=$DOMAIN"

# Set proper permissions
chmod 600 "$SSL_DIR/key.pem"
chmod 644 "$SSL_DIR/cert.pem"

echo ""
echo "✅ SSL certificate generated successfully!"
echo ""
echo "📁 Files created:"
echo "   Certificate: $SSL_DIR/cert.pem"
echo "   Private Key: $SSL_DIR/key.pem"
echo ""
echo "⚠️  WARNING: This is a self-signed certificate for development only."
echo "   For production, use Let's Encrypt with the setup-letsencrypt.sh script."
echo ""
echo "🚀 You can now start the production stack with:"
echo "   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
