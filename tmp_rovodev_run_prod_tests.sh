#!/bin/bash
# Script to run Playwright system tests on Production VPS

echo "========================================"
echo "Trabaholink Production System Test"
echo "========================================"
echo ""

# Production URL
PROD_URL="http://114.29.239.240:8000"  # Update if different

echo "Testing Production Server: $PROD_URL"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install playwright if not installed
echo "Checking Playwright installation..."
pip show playwright > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Installing Playwright..."
    pip install playwright
    echo "Installing Chromium browser..."
    playwright install chromium
else
    echo "✓ Playwright already installed"
fi

# Update the BASE_URL in the test file
echo "Configuring tests for production..."
cp tmp_rovodev_system_test.py tmp_rovodev_system_test_prod.py
sed -i.bak "s|BASE_URL = \".*\"|BASE_URL = \"$PROD_URL\"|" tmp_rovodev_system_test_prod.py

# Run the tests
echo ""
echo "========================================"
echo "Running Production Tests..."
echo "========================================"
echo ""
python tmp_rovodev_system_test_prod.py

# Cleanup
rm -f tmp_rovodev_system_test_prod.py tmp_rovodev_system_test_prod.py.bak

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
    echo "To view the report, run:"
    echo "  python3 -m http.server 8888"
    echo ""
    echo "Then open in your browser:"
    echo "  http://localhost:8888/$REPORT_FILE"
    echo ""
    echo "Or copy the report to view locally:"
    echo "  scp root@vmi2966753.contaboserver.net:~/Trabaholink/$REPORT_FILE ."
    echo ""
fi
