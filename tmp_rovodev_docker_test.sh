#!/bin/bash
# Script to run Playwright system tests using Docker container

echo "========================================"
echo "Trabaholink Production System Test"
echo "========================================"
echo ""

PROD_URL="http://194.233.72.74:8000"

echo "Testing Production Server: $PROD_URL"
echo ""

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker is not running or not accessible"
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Install python3-venv if needed (for non-Docker fallback)
if ! dpkg -l | grep -q python3-venv; then
    echo "Installing python3-venv..."
    apt-get update -qq && apt-get install -y python3-venv python3-pip
fi

# Create a temporary container with Playwright
echo "Setting up test environment in Docker..."
docker run --rm \
    --network="host" \
    -v "$(pwd)":/workspace \
    -w /workspace \
    mcr.microsoft.com/playwright/python:v1.48.0-jammy \
    bash -c "
        echo 'Installing dependencies...'
        pip install playwright -q
        
        echo ''
        echo '========================================'
        echo 'Running Production Tests...'
        echo '========================================'
        echo ''
        
        python3 tmp_rovodev_system_test.py
        
        echo ''
        echo 'Tests complete!'
    "

# Find the generated report
REPORT_FILE=$(ls -t tmp_rovodev_test_report_*.html 2>/dev/null | head -1)

if [ -n "$REPORT_FILE" ]; then
    echo ""
    echo "========================================"
    echo "✅ Production Tests Complete!"
    echo "========================================"
    echo ""
    echo "📄 Report: $REPORT_FILE"
    echo ""
    echo "To view the report:"
    echo ""
    echo "1. Start a web server:"
    echo "   python3 -m http.server 8888"
    echo ""
    echo "2. Open in browser:"
    echo "   http://194.233.72.74:8888/$REPORT_FILE"
    echo ""
    echo "3. Or download to local machine:"
    echo "   scp root@194.233.72.74:~/Trabaholink/$REPORT_FILE ~/Desktop/"
    echo ""
    
    # List all generated files
    echo "Generated files:"
    ls -lh tmp_rovodev_test_report_*.html tmp_rovodev_screenshot_*.png 2>/dev/null | awk '{print "  - " $9 " (" $5 ")"}'
    echo ""
fi
