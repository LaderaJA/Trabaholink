# Nginx Dockerfile with envsubst support for environment variables
FROM nginx:1.25-alpine

# Install envsubst for environment variable substitution
RUN apk add --no-cache gettext

# Remove default nginx config
RUN rm -f /etc/nginx/conf.d/default.conf

# Create directory for Let's Encrypt challenges
RUN mkdir -p /var/www/certbot

# Expose ports
EXPOSE 80 443

# Use default nginx entrypoint and command
# Config will be mounted via volumes
