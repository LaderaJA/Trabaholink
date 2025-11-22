#!/bin/sh
set -e

echo "Starting Nginx entrypoint..."

# Set default values for environment variables
export DOMAIN_NAME="${DOMAIN_NAME:-localhost}"

# Remove any existing config files first to avoid duplicates                                                        
 rm -f /etc/nginx/conf.d/default.conf                                                                               
                                                                                                                     
# Use development config if SSL certificates don't exist                                                            
  if [ ! -f /etc/nginx/ssl/cert.pem ] || [ ! -f /etc/nginx/ssl/key.pem ]; then 
      echo "SSL certificates not found. Using development configuration (HTTP only)..."
      cp /etc/nginx/conf.d/nginx.dev.conf /etc/nginx/conf.d/default.conf
      rm -f /etc/nginx/conf.d/nginx.dev.conf /etc/nginx/conf.d/nginx.conf
  else
      echo "SSL certificates found. Using production configuration (HTTPS)..."
      # Substitute environment variables in template
      envsubst '${DOMAIN_NAME}' < /etc/nginx/templates/nginx.conf.template > /etc/nginx/conf.d/default.conf
      rm -f /etc/nginx/conf.d/nginx.dev.conf /etc/nginx/conf.d/nginx.conf
  fi 

# Test nginx configuration
echo "Testing Nginx configuration..."
nginx -t

echo "Starting Nginx..."
exec "$@"
