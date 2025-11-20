#!/bin/bash
# Monitoring script for Trabaholink services
# Displays real-time status and resource usage

set -e

echo "📊 Trabaholink Service Monitor"
echo "=============================="
echo ""

# Check if services are running
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ No services are running!"
    echo "   Start with: docker-compose up -d"
    exit 1
fi

while true; do
    clear
    echo "📊 Trabaholink Service Monitor - $(date '+%Y-%m-%d %H:%M:%S')"
    echo "================================================================"
    echo ""
    
    echo "🐳 Service Status:"
    docker-compose ps
    echo ""
    
    echo "💻 Resource Usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
        $(docker-compose ps -q)
    echo ""
    
    echo "🔍 Health Checks:"
    
    # Web application health
    if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
        echo "✅ Web Application: Healthy"
    else
        echo "❌ Web Application: Unhealthy"
    fi
    
    # Database health
    if docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; then
        echo "✅ PostgreSQL: Healthy"
    else
        echo "❌ PostgreSQL: Unhealthy"
    fi
    
    # Redis health
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis: Healthy"
    else
        echo "❌ Redis: Unhealthy"
    fi
    
    echo ""
    echo "📝 Recent Logs (last 10 lines):"
    echo "--------------------------------"
    docker-compose logs --tail=10 web 2>/dev/null | tail -5
    echo ""
    
    echo "Press Ctrl+C to exit"
    sleep 5
done
