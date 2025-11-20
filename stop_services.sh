#!/bin/bash

# Stop All Services Script

echo "🛑 Stopping all services..."
echo ""

# Stop Celery
echo "1️⃣ Stopping Celery workers..."
pkill -f "celery -A Trabaholink worker"
sleep 1

if pgrep -f "celery -A Trabaholink worker" > /dev/null; then
    echo "⚠️  Force killing Celery..."
    pkill -9 -f "celery -A Trabaholink worker"
    sleep 1
fi

if pgrep -f "celery -A Trabaholink worker" > /dev/null; then
    echo "❌ Failed to stop Celery"
else
    echo "✅ Celery stopped"
fi
echo ""

# Stop Django (if running on port 8000)
echo "2️⃣ Stopping Django server..."
if lsof -i:8000 > /dev/null 2>&1; then
    kill $(lsof -t -i:8000) 2>/dev/null
    sleep 1
    if lsof -i:8000 > /dev/null 2>&1; then
        echo "❌ Failed to stop Django"
    else
        echo "✅ Django stopped"
    fi
else
    echo "ℹ️  Django not running"
fi
echo ""

# Note: We don't stop Redis as it might be used by other projects
echo "ℹ️  Redis left running (may be used by other projects)"
echo "   To stop Redis manually: redis-cli shutdown"
echo ""

echo "✅ Services stopped!"
