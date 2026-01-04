#!/bin/bash
# Script to run tests using the existing web container (no extra installs needed)

echo "========================================"
echo "Trabaholink Production System Test"
echo "========================================"
echo ""

PROD_URL="http://194.233.72.74:8000"

echo "Testing Production Server: $PROD_URL"
echo ""

# Check if docker-compose is running
if ! ./dc.sh ps | grep -q "web"; then
    echo "❌ Web container is not running"
    echo "Start it with: ./dc.sh up -d"
    exit 1
fi

echo "✓ Web container is running"
echo ""

# Install playwright in the web container (only first time)
echo "Setting up Playwright in web container..."
./dc.sh exec web bash -c "
    pip list | grep -q playwright || pip install playwright
    playwright --version > /dev/null 2>&1 || playwright install chromium
"

echo ""
echo "========================================"
echo "Running Production Tests..."
echo "========================================"
echo ""

# Run the tests from inside the web container
./dc.sh exec web python tmp_rovodev_system_test.py

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
    echo "   scp root@vmi2966753.contaboserver.net:~/Trabaholink/$REPORT_FILE ~/Desktop/"
    echo ""
    
    # List all generated files
    echo "Generated files:"
    ls -lh tmp_rovodev_test_report_*.html tmp_rovodev_screenshot_*.png 2>/dev/null | awk '{print "  - " $9 " (" $5 ")"}'
    echo ""
fi
