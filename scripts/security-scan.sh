#!/bin/bash
# Security scanning script using Trivy

set -e

echo "🔐 Security Scanning Script"
echo "==========================="
echo ""

# Check if trivy is installed
if ! command -v trivy &> /dev/null; then
    echo "📦 Trivy is not installed. Installing..."
    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
fi

echo "🔍 Scanning Docker images for vulnerabilities..."
echo ""

# Scan the main application image
IMAGE_NAME="trabaholink:latest"

echo "Scanning image: $IMAGE_NAME"
echo ""

# Run Trivy scan
trivy image --severity HIGH,CRITICAL "$IMAGE_NAME"

echo ""
echo "📊 Scan Results Summary:"
trivy image --severity HIGH,CRITICAL --format json "$IMAGE_NAME" > trivy-results.json

HIGH_COUNT=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="HIGH")] | length' trivy-results.json)
CRITICAL_COUNT=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' trivy-results.json)

echo "   High:     $HIGH_COUNT"
echo "   Critical: $CRITICAL_COUNT"
echo ""

if [ "$CRITICAL_COUNT" -gt 0 ]; then
    echo "❌ CRITICAL vulnerabilities found! Please address them before deploying."
    exit 1
elif [ "$HIGH_COUNT" -gt 5 ]; then
    echo "⚠️  Multiple HIGH vulnerabilities found. Consider addressing them."
else
    echo "✅ Security scan passed!"
fi

echo ""
echo "📄 Full results saved to: trivy-results.json"
