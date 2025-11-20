#!/bin/bash
# Performance testing script using Apache Bench

set -e

echo "⚡ Performance Testing Script"
echo "============================"
echo ""

# Check if ab (Apache Bench) is installed
if ! command -v ab &> /dev/null; then
    echo "❌ Apache Bench (ab) is not installed!"
    echo "   Install: sudo apt-get install apache2-utils"
    exit 1
fi

# Get target URL
read -p "Enter target URL (default: http://localhost:8000/): " TARGET_URL
TARGET_URL=${TARGET_URL:-http://localhost:8000/}

# Test parameters
read -p "Number of requests (default: 1000): " NUM_REQUESTS
NUM_REQUESTS=${NUM_REQUESTS:-1000}

read -p "Concurrency level (default: 10): " CONCURRENCY
CONCURRENCY=${CONCURRENCY:-10}

echo ""
echo "🎯 Test Configuration:"
echo "   URL:         $TARGET_URL"
echo "   Requests:    $NUM_REQUESTS"
echo "   Concurrency: $CONCURRENCY"
echo ""
read -p "Start test? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "🚀 Running performance test..."
echo ""

# Run Apache Bench
ab -n "$NUM_REQUESTS" -c "$CONCURRENCY" -g performance-results.tsv "$TARGET_URL"

echo ""
echo "📊 Results saved to: performance-results.tsv"
echo ""
echo "✅ Test complete!"
