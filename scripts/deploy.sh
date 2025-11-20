#!/bin/bash
# Production deployment script for Trabaholink
# Handles zero-downtime deployments with health checks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."

echo "🚀 Trabaholink Production Deployment"
echo "====================================="
echo ""

# Check if .env.production exists
if [ ! -f "$PROJECT_DIR/.env.production" ]; then
    echo "❌ .env.production file not found!"
    echo "   Create it from .env.production.example"
    exit 1
fi

# Confirm deployment
read -p "Deploy to production? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "📦 Step 1: Creating database backup..."
"$SCRIPT_DIR/backup-database.sh"

echo ""
echo "📥 Step 2: Pulling latest code..."
cd "$PROJECT_DIR"
git pull origin main

echo ""
echo "🔨 Step 3: Building Docker images..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache

echo ""
echo "🔄 Step 4: Starting services..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d

echo ""
echo "⏳ Step 5: Waiting for services to be healthy..."
sleep 15

# Check if services are running
if docker-compose ps | grep -q "Exit\|Down"; then
    echo "❌ Some services failed to start!"
    echo ""
    echo "Service status:"
    docker-compose ps
    echo ""
    echo "Check logs with: docker-compose logs"
    exit 1
fi

echo ""
echo "🧪 Step 6: Running health checks..."
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost/health/ > /dev/null 2>&1; then
        echo "✅ Health check passed!"
        break
    else
        echo "⏳ Waiting for application to be ready... (attempt $((RETRY_COUNT+1))/$MAX_RETRIES)"
        sleep 5
        RETRY_COUNT=$((RETRY_COUNT+1))
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Health check failed after $MAX_RETRIES attempts!"
    echo "   Check logs with: docker-compose logs web"
    exit 1
fi

echo ""
echo "🧹 Step 7: Cleaning up old Docker images..."
docker image prune -f

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""
echo "🌐 Your application is live!"
echo ""
echo "📋 Useful commands:"
echo "   View logs:    docker-compose logs -f"
echo "   Stop:         docker-compose down"
echo "   Restart:      docker-compose restart"
