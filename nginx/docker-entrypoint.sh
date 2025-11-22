#!/bin/sh
set -e

echo "Starting Nginx entrypoint..."

# Set default values for environment variables
export DOMAIN_NAME="${DOMAIN_NAME:-localhost}"

# Check if SSL certificates exist
if [ ! -f /etc/nginx/ssl/cert.pem ] || [ ! -f /etc/nginx/ssl/key.pem ]; then
    echo "WARNING: SSL certificates not found at /etc/nginx/ssl/"
    echo "Nginx will use the template configuration. Ensure SSL paths are correct."
fi

# Substitute environment variables in template
echo "Processing nginx configuration template..."
envsubst '${DOMAIN_NAME}' < /etc/nginx/templates/nginx.conf.template > /etc/nginx/conf.d/default.conf

# Test nginx configuration
echo "Testing Nginx configuration..."
nginx -t

echo "Starting Nginx..."
exec "$@"
