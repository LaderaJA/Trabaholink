#!/bin/bash
# Install monitoring stack (Prometheus + Grafana)

set -e

echo "📊 Installing Monitoring Stack"
echo "=============================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."

cd "$PROJECT_DIR"

# Check if monitoring is already running
if docker-compose ps | grep -q "prometheus"; then
    echo "⚠️  Monitoring stack is already running!"
    read -p "Do you want to restart it? (y/n): " RESTART
    if [ "$RESTART" != "y" ]; then
        echo "Aborted."
        exit 0
    fi
    echo "Stopping existing monitoring stack..."
    docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml down
fi

echo ""
echo "🔨 Starting monitoring stack..."
echo ""

# Start with monitoring
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 15

# Check if services are running
if docker-compose ps | grep -E "prometheus|grafana" | grep -q "Up"; then
    echo ""
    echo "✅ Monitoring stack is running!"
    echo ""
    echo "🌐 Access Points:"
    echo "   Prometheus:  http://localhost:9090"
    echo "   Grafana:     http://localhost:3000"
    echo "   Node Exp:    http://localhost:9100/metrics"
    echo "   cAdvisor:    http://localhost:8080"
    echo ""
    echo "🔐 Grafana Login:"
    echo "   Username: admin"
    echo "   Password: admin (change on first login!)"
    echo ""
    echo "📊 Grafana Setup:"
    echo "   1. Login to Grafana"
    echo "   2. Data source (Prometheus) is auto-configured"
    echo "   3. Import dashboards from grafana.com:"
    echo "      - 1860: Node Exporter Full"
    echo "      - 893:  Docker & System Monitoring"
    echo "      - 3662: Prometheus"
    echo ""
    echo "📈 Prometheus Targets:"
    echo "   Check all targets are 'UP' at: http://localhost:9090/targets"
    echo ""
    echo "🛠️  Useful Commands:"
    echo "   Stop:     docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml down"
    echo "   Restart:  docker-compose restart prometheus grafana"
    echo "   Logs:     docker-compose logs -f prometheus grafana"
else
    echo ""
    echo "❌ Failed to start monitoring stack!"
    echo "   Check logs: docker-compose logs prometheus grafana"
    exit 1
fi

echo ""
echo "✅ Installation complete!"
