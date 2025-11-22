#!/bin/bash
# Deployment script to fix static files issue on server

echo "================================"
echo "Trabaholink Deployment Script"
echo "================================"

# Navigate to project directory
cd /root/Trabaholink || exit 1

# Pull latest changes
echo "Pulling latest changes from GitHub..."
git pull origin main

# Check if docker-compose.yml has nginx service
if grep -q "nginx:" docker-compose.yml; then
    echo "✓ Nginx service found in docker-compose.yml"
else
    echo "✗ ERROR: Nginx service not found in docker-compose.yml"
    echo "Please ensure git pull completed successfully"
    exit 1
fi

# Stop all containers
echo "Stopping containers..."
docker compose down

# Remove old containers (clean slate)
echo "Removing old containers..."
docker compose rm -f

# Start services with build
echo "Starting services (this may take a few minutes)..."
docker compose up -d --build

# Wait for services to start
echo "Waiting for services to initialize..."
sleep 10

# Check container status
echo ""
echo "Container Status:"
docker compose ps

# Check nginx logs
echo ""
echo "Nginx Logs:"
docker compose logs nginx | tail -20

# Check if static files are accessible
echo ""
echo "Checking static files in nginx container..."
docker compose exec -T nginx ls -la /app/staticfiles/ | head -10

echo ""
echo "================================"
echo "Deployment Complete!"
echo "================================"
echo "Access your site at: http://114.29.239.240/"
echo ""
