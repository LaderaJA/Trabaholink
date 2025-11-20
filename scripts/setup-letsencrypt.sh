#!/bin/bash
# Setup Let's Encrypt SSL certificate for production
# This script initializes Certbot and obtains SSL certificates

set -e

echo "🔐 Let's Encrypt SSL Certificate Setup"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  This script should be run as root or with sudo"
    echo "   Try: sudo $0"
    exit 1
fi

# Prompt for domain and email
read -p "Enter your domain name (e.g., trabaholink.com): " DOMAIN
read -p "Enter your email address: " EMAIL

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "❌ Domain and email are required!"
    exit 1
fi

echo ""
echo "Domain: $DOMAIN"
echo "Email: $EMAIL"
echo ""
read -p "Is this correct? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Aborted."
    exit 1
fi

# Create required directories
mkdir -p ./certbot/conf
mkdir -p ./certbot/www

# Check if certificates already exist
if [ -d "./certbot/conf/live/$DOMAIN" ]; then
    echo ""
    echo "⚠️  Certificates already exist for $DOMAIN"
    read -p "Do you want to renew them? (y/n): " RENEW
    
    if [ "$RENEW" = "y" ]; then
        docker-compose run --rm certbot renew
    fi
else
    echo ""
    echo "📥 Obtaining SSL certificate from Let's Encrypt..."
    echo ""
    
    # Get certificate from Let's Encrypt
    docker-compose run --rm certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        -d "$DOMAIN" \
        -d "www.$DOMAIN"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ SSL certificate obtained successfully!"
        echo ""
        
        # Create symbolic links for Nginx
        mkdir -p ./nginx/ssl
        ln -sf "../../certbot/conf/live/$DOMAIN/fullchain.pem" ./nginx/ssl/cert.pem
        ln -sf "../../certbot/conf/live/$DOMAIN/privkey.pem" ./nginx/ssl/key.pem
        
        echo "📁 Certificates linked to nginx/ssl/"
        echo ""
        echo "🔄 Restarting Nginx to apply new certificates..."
        docker-compose restart nginx
        
        echo ""
        echo "✅ Setup complete!"
        echo ""
        echo "📋 Your certificates will auto-renew every 12 hours."
        echo "🌐 Your site should now be accessible at: https://$DOMAIN"
    else
        echo ""
        echo "❌ Failed to obtain SSL certificate."
        echo "   Please check:"
        echo "   1. Your domain DNS is pointing to this server"
        echo "   2. Ports 80 and 443 are open"
        echo "   3. Nginx is running and accessible"
    fi
fi

echo ""
echo "📚 Certificate management commands:"
echo "   Renew:  docker-compose run --rm certbot renew"
echo "   Revoke: docker-compose run --rm certbot revoke --cert-path /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
