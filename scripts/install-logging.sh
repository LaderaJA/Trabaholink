#!/bin/bash
# Install logging stack (Loki + Promtail)

set -e

echo "📝 Installing Logging Stack"
echo "==========================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."

cd "$PROJECT_DIR"

# Check if logging is already running
if docker-compose ps | grep -q "loki"; then
    echo "⚠️  Logging stack is already running!"
    read -p "Do you want to restart it? (y/n): " RESTART
    if [ "$RESTART" != "y" ]; then
        echo "Aborted."
        exit 0
    fi
    echo "Stopping existing logging stack..."
    docker-compose -f docker-compose.yml -f docker-compose.logging.yml down
fi

echo ""
echo "🔨 Starting logging stack..."
echo ""

# Start with logging
docker-compose -f docker-compose.yml -f docker-compose.logging.yml up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
if docker-compose ps | grep -E "loki|promtail" | grep -q "Up"; then
    echo ""
    echo "✅ Logging stack is running!"
    echo ""
    echo "🌐 Access Points:"
    echo "   Loki API:  http://localhost:3100"
    echo ""
    echo "📊 View Logs in Grafana:"
    echo "   1. Open Grafana: http://localhost:3000"
    echo "   2. Go to Configuration → Data Sources"
    echo "   3. Add Loki data source:"
    echo "      - URL: http://loki:3100"
    echo "   4. Go to Explore"
    echo "   5. Select Loki data source"
    echo "   6. Use LogQL queries like:"
    echo "      {container=\"trabaholink_web\"}"
    echo "      {service=\"web\"} |= \"error\""
    echo ""
    echo "📝 Log Query Examples:"
    echo "   All web logs:        {container=\"trabaholink_web\"}"
    echo "   Error logs:          {container=\"trabaholink_web\"} |= \"ERROR\""
    echo "   Database logs:       {container=\"trabaholink_db\"}"
    echo "   Last hour errors:    {service=\"web\"} |= \"error\" [1h]"
    echo ""
    echo "🛠️  Useful Commands:"
    echo "   Stop:     docker-compose -f docker-compose.yml -f docker-compose.logging.yml down"
    echo "   Restart:  docker-compose restart loki promtail"
    echo "   Logs:     docker-compose logs -f loki promtail"
else
    echo ""
    echo "❌ Failed to start logging stack!"
    echo "   Check logs: docker-compose logs loki promtail"
    exit 1
fi

echo ""
echo "✅ Installation complete!"
