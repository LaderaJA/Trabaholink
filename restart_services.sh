#!/bin/bash

# Restart Services Script
# This script restarts Celery to load new code changes

echo "🔄 Restarting Services to Load New Changes..."
echo ""

# Kill existing Celery workers
echo "1️⃣ Stopping Celery workers..."
pkill -f "celery -A Trabaholink worker"
sleep 2

# Verify Celery is stopped
if pgrep -f "celery -A Trabaholink worker" > /dev/null; then
    echo "⚠️  Force killing Celery..."
    pkill -9 -f "celery -A Trabaholink worker"
    sleep 1
fi

echo "✅ Celery stopped"
echo ""

# Start Celery in background
echo "2️⃣ Starting Celery worker..."

# Use virtual environment Python if available
if [ -f "../.venv/bin/python" ]; then
    echo "   Using virtual environment Python"
    nohup ../.venv/bin/python -m celery -A Trabaholink worker -l info > celery.log 2>&1 &
elif [ -f ".venv/bin/python" ]; then
    echo "   Using virtual environment Python"
    nohup .venv/bin/python -m celery -A Trabaholink worker -l info > celery.log 2>&1 &
elif [ -f "venv/bin/python" ]; then
    echo "   Using virtual environment Python"
    nohup venv/bin/python -m celery -A Trabaholink worker -l info > celery.log 2>&1 &
else
    echo "   Using system Python"
    nohup python3 -m celery -A Trabaholink worker -l info > celery.log 2>&1 &
fi
sleep 3

# Check if Celery started
if pgrep -f "celery -A Trabaholink worker" > /dev/null; then
    echo "✅ Celery worker started successfully"
    echo "📋 Check celery.log for worker output"
else
    echo "❌ Failed to start Celery worker"
    echo "💡 Check celery.log for errors"
    echo "💡 Try running manually: python3 -m celery -A Trabaholink worker -l info"
    exit 1
fi

echo ""
echo "✅ All services restarted!"
echo ""
echo "📝 Next steps:"
echo "   1. Submit a new verification or re-process an existing one"
echo "   2. Check admin dashboard to see the new OCR display"
echo "   3. Monitor celery.log for any errors"
echo ""
echo "💡 To view Celery logs: tail -f celery.log"
