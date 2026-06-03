#!/bin/bash
# ACAS Pro Performance Test Script
# Usage: ./performance-test.sh [users] [duration]

USERS="${1:-100}"
DURATION="${2:-60}"
HOST="${3:-http://localhost:5000}"

echo "=== ACAS Pro Performance Test ==="
echo "Users: $USERS"
echo "Duration: ${DURATION}s"
echo "Host: $HOST"
echo ""

# Check if Locust is installed
if ! command -v locust &> /dev/null; then
    echo "Installing Locust..."
    pip install locust
fi

# Check if server is running
echo "Checking server health..."
if ! curl -s "$HOST/api/health" > /dev/null; then
    echo "❌ Server not running at $HOST"
    echo "Start server first: docker-compose up -d app"
    exit 1
fi

echo "✅ Server is running"
echo ""

# Run Locust test
echo "Starting Locust test..."
locust \
    -f locustfile.py \
    --host "$HOST" \
    -u "$USERS" \
    -r "$((USERS / 10))" \
    -t "${DURATION}s" \
    --headless \
    --csv "results/acas_pro_${USERS}users_${DURATION}s" \
    --html "results/report_${USERS}users_${DURATION}s.html"

echo ""
echo "=== Test Complete ==="
echo "Results saved to: results/"
echo ""
echo "Key metrics:"
echo "  - RPS (Requests/sec)"
echo "  - Response time (p50, p95, p99)"
echo "  - Error rate"
echo "  - Failure count"
