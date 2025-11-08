#!/bin/bash
################################################################################
# FreeFace Email Service - Quick Health Check
#
# Fast validation that core system is working
# Use this for quick checks during development
#
# Usage:
#   ./scripts/quick_test.sh
#
# Exit codes:
#   0 = System healthy ✓
#   1 = System has issues ✗
################################################################################

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
EMAIL_API_URL="${EMAIL_API_URL:-http://localhost:8010}"
SERVICE_TOKEN="${SERVICE_TOKEN:-st_dev_0000000000000000000000000000000000000000}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  FreeFace Email Service - Quick Health Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check 1: Containers running
echo -n "✓ Checking containers ... "
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "  Run: docker-compose up -d"
    exit 1
fi

# Check 2: Health endpoint
echo -n "✓ Checking health endpoint ... "
http_code=$(curl -s -o /dev/null -w "%{http_code}" "$EMAIL_API_URL/health")
if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAIL (HTTP $http_code)${NC}"
    exit 1
fi

# Check 3: Send test email
echo -n "✓ Sending test email ... "
response=$(curl -s -w "\n%{http_code}" -X POST "$EMAIL_API_URL/send" \
    -H "Content-Type: application/json" \
    -H "X-Service-Token: $SERVICE_TOKEN" \
    -d '{"recipients": "quicktest@example.com", "template": "welcome", "data": {"name": "Quick Test"}}')
http_code=$(echo "$response" | tail -n 1)

if [ "$http_code" = "200" ]; then
    job_id=$(echo "$response" | head -n -1 | jq -r '.job_id')
    echo -e "${GREEN}OK${NC} (Job: $job_id)"
else
    echo -e "${RED}FAIL (HTTP $http_code)${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✓ System is HEALTHY${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "For comprehensive tests, run: ./scripts/test_email_service.sh"
echo ""

exit 0
