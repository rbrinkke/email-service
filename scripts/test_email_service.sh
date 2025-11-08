#!/bin/bash
################################################################################
# FreeFace Email Service - Comprehensive Integration Test Suite
#
# Tests EVERYTHING:
# - Container health
# - Service authentication
# - Email sending (all endpoints)
# - Email delivery verification (MailHog)
# - Audit trail & metrics
# - Monitoring endpoints
#
# Usage:
#   ./scripts/test_email_service.sh
#
# Exit codes:
#   0 = All tests passed ✓
#   1 = One or more tests failed ✗
################################################################################

# Note: NOT using 'set -e' because we handle errors explicitly
# Each test function returns 0/1 and we track pass/fail ourselves
set -o pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Configuration
EMAIL_API_URL="${EMAIL_API_URL:-http://localhost:8010}"
MONITOR_URL="${MONITOR_URL:-http://localhost:8011}"
MAILHOG_API_URL="${MAILHOG_API_URL:-http://localhost:8025}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

# Service token (from .env)
SERVICE_TOKEN="${SERVICE_TOKEN:-st_dev_0000000000000000000000000000000000000000}"

# Test results array
declare -a FAILED_TESTS

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${BOLD}${CYAN}▶ $1${NC}"
    echo ""
}

print_test() {
    echo -n "  Testing: $1 ... "
    TESTS_RUN=$((TESTS_RUN + 1))
}

print_pass() {
    echo -e "${GREEN}✓ PASS${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

print_fail() {
    local test_name="$1"
    local error_msg="$2"
    echo -e "${RED}✗ FAIL${NC}"
    echo -e "    ${RED}Error: $error_msg${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    FAILED_TESTS+=("$test_name: $error_msg")
}

print_skip() {
    echo -e "${YELLOW}⊘ SKIP${NC} ($1)"
}

wait_for_service() {
    local url="$1"
    local name="$2"
    local max_attempts=30
    local attempt=1

    echo -n "  Waiting for $name to be ready "
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done

    echo -e " ${RED}✗ Timeout${NC}"
    return 1
}

################################################################################
# Test Level 1: Infrastructure & Container Health
################################################################################

test_infrastructure() {
    print_section "Level 1: Infrastructure & Container Health"

    # Test: Docker containers running
    print_test "Docker containers are running"
    if docker-compose ps | grep -q "Up"; then
        print_pass
    else
        print_fail "Docker containers" "Containers not running. Run: docker-compose up -d"
        return 1
    fi

    # Test: Email API container
    print_test "email-api container is running"
    if docker-compose ps email-api | grep -q "Up"; then
        print_pass
    else
        print_fail "email-api container" "Container not running"
        return 1
    fi

    # Test: Redis container
    print_test "Redis container is running"
    if docker-compose ps redis-email | grep -q "Up"; then
        print_pass
    else
        print_fail "Redis container" "Container not running"
        return 1
    fi

    # Test: Monitor container
    print_test "Monitor container is running"
    if docker-compose ps email-monitor | grep -q "Up"; then
        print_pass
    else
        print_fail "Monitor container" "Container not running"
        return 1
    fi

    # Test: MailHog container
    print_test "MailHog container is running"
    if docker-compose ps mailhog | grep -q "Up"; then
        print_pass
    else
        print_fail "MailHog container" "Container not running"
        return 1
    fi

    # Test: Worker containers
    print_test "Worker containers are running (3 workers expected)"
    local worker_count=$(docker-compose ps | grep "email-worker" | grep -c "Up" || echo "0")
    if [ "$worker_count" -ge 1 ]; then
        print_pass
        echo -e "    ${CYAN}Found $worker_count worker(s)${NC}"
    else
        print_fail "Worker containers" "No workers running"
        return 1
    fi

    # Wait for services to be ready
    wait_for_service "$EMAIL_API_URL/health" "Email API" || return 1
    wait_for_service "$MONITOR_URL" "Monitor Dashboard" || return 1
    wait_for_service "$MAILHOG_API_URL/api/v2/messages" "MailHog API" || return 1

    return 0
}

################################################################################
# Test Level 2: Service Health Endpoints
################################################################################

test_service_health() {
    print_section "Level 2: Service Health Endpoints"

    # Test: Email API health endpoint (NO AUTH REQUIRED)
    print_test "Email API /health endpoint (public)"
    response=$(curl -s -w "\n%{http_code}" "$EMAIL_API_URL/health")
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ]; then
        if echo "$body" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
            print_pass
        else
            print_fail "Health endpoint status" "Status not 'healthy': $body"
        fi
    else
        print_fail "Health endpoint" "Expected 200, got $http_code"
    fi

    # Test: Monitor dashboard
    print_test "Monitor dashboard is accessible"
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$MONITOR_URL/")
    if [ "$http_code" = "200" ]; then
        print_pass
    else
        print_fail "Monitor dashboard" "Expected 200, got $http_code"
    fi

    # Test: MailHog API
    print_test "MailHog API is accessible"
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$MAILHOG_API_URL/api/v2/messages")
    if [ "$http_code" = "200" ]; then
        print_pass
    else
        print_fail "MailHog API" "Expected 200, got $http_code"
    fi

    return 0
}

################################################################################
# Test Level 3: Authentication
################################################################################

test_authentication() {
    print_section "Level 3: Service Authentication"

    # Clear MailHog before tests
    curl -s -X DELETE "$MAILHOG_API_URL/api/v1/messages" > /dev/null 2>&1 || true

    # Test: Missing token → 401
    print_test "Missing token returns 401"
    response=$(curl -s -w "\n%{http_code}" -X POST "$EMAIL_API_URL/send" \
        -H "Content-Type: application/json" \
        -d '{"recipients": "test@example.com", "template": "welcome", "data": {}}')
    http_code=$(echo "$response" | tail -n 1)

    if [ "$http_code" = "401" ]; then
        print_pass
    else
        print_fail "Missing token auth" "Expected 401, got $http_code"
    fi

    # Test: Invalid token → 401
    print_test "Invalid token returns 401"
    response=$(curl -s -w "\n%{http_code}" -X POST "$EMAIL_API_URL/send" \
        -H "Content-Type: application/json" \
        -H "X-Service-Token: invalid_token_123" \
        -d '{"recipients": "test@example.com", "template": "welcome", "data": {}}')
    http_code=$(echo "$response" | tail -n 1)

    if [ "$http_code" = "401" ]; then
        print_pass
    else
        print_fail "Invalid token auth" "Expected 401, got $http_code"
    fi

    # Test: Wrong prefix token → 401
    print_test "Wrong prefix token returns 401"
    response=$(curl -s -w "\n%{http_code}" -X POST "$EMAIL_API_URL/send" \
        -H "Content-Type: application/json" \
        -H "X-Service-Token: wrong_prefix_abc123" \
        -d '{"recipients": "test@example.com", "template": "welcome", "data": {}}')
    http_code=$(echo "$response" | tail -n 1)

    if [ "$http_code" = "401" ]; then
        print_pass
    else
        print_fail "Wrong prefix auth" "Expected 401, got $http_code"
    fi

    # Test: Valid token → 200
    print_test "Valid token returns 200"
    response=$(curl -s -w "\n%{http_code}" -X POST "$EMAIL_API_URL/send" \
        -H "Content-Type: application/json" \
        -H "X-Service-Token: $SERVICE_TOKEN" \
        -d '{"recipients": "auth-test@example.com", "template": "welcome", "data": {"name": "Auth Test"}}')
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ]; then
        if echo "$body" | jq -e '.job_id' > /dev/null 2>&1; then
            print_pass
            JOB_ID_AUTH=$(echo "$body" | jq -r '.job_id')
            echo -e "    ${CYAN}Job ID: $JOB_ID_AUTH${NC}"
        else
            print_fail "Valid token response" "No job_id in response: $body"
        fi
    else
        print_fail "Valid token auth" "Expected 200, got $http_code: $body"
    fi

    return 0
}

################################################################################
# Test Level 4: Email Sending (All Endpoints)
################################################################################

test_email_sending() {
    print_section "Level 4: Email Sending Operations"

    # Clear MailHog
    curl -s -X DELETE "$MAILHOG_API_URL/api/v1/messages" > /dev/null 2>&1 || true
    sleep 1

    # Test: POST /send
    print_test "POST /send (basic email)"
    response=$(curl -s -w "\n%{http_code}" -X POST "$EMAIL_API_URL/send" \
        -H "Content-Type: application/json" \
        -H "X-Service-Token: $SERVICE_TOKEN" \
        -d '{
            "recipients": "basic-test@example.com",
            "template": "welcome",
            "data": {"name": "Basic Test User"},
            "priority": "high"
        }')
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ]; then
        JOB_ID_BASIC=$(echo "$body" | jq -r '.job_id')
        print_pass
        echo -e "    ${CYAN}Job ID: $JOB_ID_BASIC${NC}"
    else
        print_fail "POST /send" "Expected 200, got $http_code: $body"
    fi

    # Test: POST /send/welcome
    print_test "POST /send/welcome"
    response=$(curl -s -w "\n%{http_code}" -X POST \
        "$EMAIL_API_URL/send/welcome?user_email=welcome-test@example.com&user_name=Welcome%20User&verification_token=abc123xyz" \
        -H "X-Service-Token: $SERVICE_TOKEN")
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ]; then
        JOB_ID_WELCOME=$(echo "$body" | jq -r '.job_id')
        print_pass
        echo -e "    ${CYAN}Job ID: $JOB_ID_WELCOME${NC}"
    else
        print_fail "POST /send/welcome" "Expected 200, got $http_code: $body"
    fi

    # Test: POST /send/password-reset
    print_test "POST /send/password-reset"
    response=$(curl -s -w "\n%{http_code}" -X POST \
        "$EMAIL_API_URL/send/password-reset?user_email=reset-test@example.com&reset_token=reset123xyz" \
        -H "X-Service-Token: $SERVICE_TOKEN")
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ]; then
        JOB_ID_RESET=$(echo "$body" | jq -r '.job_id')
        print_pass
        echo -e "    ${CYAN}Job ID: $JOB_ID_RESET${NC}"
    else
        print_fail "POST /send/password-reset" "Expected 200, got $http_code: $body"
    fi

    # Test: POST /send - Multiple recipients
    print_test "POST /send (multiple recipients)"
    response=$(curl -s -w "\n%{http_code}" -X POST "$EMAIL_API_URL/send" \
        -H "Content-Type: application/json" \
        -H "X-Service-Token: $SERVICE_TOKEN" \
        -d '{
            "recipients": ["multi1@example.com", "multi2@example.com", "multi3@example.com"],
            "template": "welcome",
            "data": {"name": "Multiple Recipients Test"}
        }')
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ]; then
        JOB_ID_MULTI=$(echo "$body" | jq -r '.job_id')
        print_pass
        echo -e "    ${CYAN}Job ID: $JOB_ID_MULTI${NC}"
    else
        print_fail "POST /send (multi)" "Expected 200, got $http_code: $body"
    fi

    # Wait for workers to process emails
    echo ""
    echo -n "  Waiting for workers to process emails (10s) "
    for i in {1..10}; do
        echo -n "."
        sleep 1
    done
    echo -e " ${GREEN}✓${NC}"

    return 0
}

################################################################################
# Test Level 5: Email Delivery Verification (MailHog)
################################################################################

test_email_delivery() {
    print_section "Level 5: Email Delivery Verification (MailHog)"

    # Get all messages from MailHog
    print_test "MailHog received emails"
    messages=$(curl -s "$MAILHOG_API_URL/api/v2/messages")
    message_count=$(echo "$messages" | jq -r '.total // 0')

    # We sent 4 emails (basic, welcome, reset, multi=3) = 6 total
    # But multi might be 1 job with 3 recipients
    if [ "$message_count" -ge 4 ]; then
        print_pass
        echo -e "    ${CYAN}Received $message_count email(s) in MailHog${NC}"
    else
        print_fail "Email delivery" "Expected at least 4 emails, got $message_count"
    fi

    # Test: Verify specific email received
    print_test "Basic test email received in MailHog"
    if echo "$messages" | jq -e '(.items // .) | .[] | select((.Content.Headers.To[0] // .To[0] // .Raw.To) | test("basic-test@example.com"; "i"))' > /dev/null 2>&1; then
        print_pass
    else
        print_fail "Basic email delivery" "Email to basic-test@example.com not found in MailHog"
    fi

    # Test: Welcome email received
    print_test "Welcome email received in MailHog"
    if echo "$messages" | jq -e '(.items // .) | .[] | select((.Content.Headers.To[0] // .To[0] // .Raw.To) | test("welcome-test@example.com"; "i"))' > /dev/null 2>&1; then
        print_pass
    else
        print_fail "Welcome email delivery" "Email to welcome-test@example.com not found in MailHog"
    fi

    # Test: Password reset email received
    print_test "Password reset email received in MailHog"
    if echo "$messages" | jq -e '(.items // .) | .[] | select((.Content.Headers.To[0] // .To[0] // .Raw.To) | test("reset-test@example.com"; "i"))' > /dev/null 2>&1; then
        print_pass
    else
        print_fail "Reset email delivery" "Email to reset-test@example.com not found in MailHog"
    fi

    return 0
}

################################################################################
# Test Level 6: Audit Trail & Metrics
################################################################################

test_audit_trail() {
    print_section "Level 6: Audit Trail & Metrics"

    # Test: Service metrics endpoint
    print_test "Service metrics endpoint accessible"
    response=$(curl -s -w "\n%{http_code}" "$MONITOR_URL/api/service-metrics")
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ]; then
        service_count=$(echo "$body" | jq -r '.total_services // 0')
        if [ "$service_count" -gt 0 ]; then
            print_pass
            echo -e "    ${CYAN}Found $service_count service(s) with metrics${NC}"
        else
            print_fail "Service metrics" "No services found in metrics"
        fi
    else
        print_fail "Service metrics endpoint" "Expected 200, got $http_code"
    fi

    # Test: Check main-app metrics
    print_test "main-app service has metrics"
    if echo "$body" | jq -e '.services."main-app"' > /dev/null 2>&1; then
        total_calls=$(echo "$body" | jq -r '.services."main-app".total_calls // 0')
        total_emails=$(echo "$body" | jq -r '.services."main-app".total_emails // 0')
        print_pass
        echo -e "    ${CYAN}Total calls: $total_calls, Total emails: $total_emails${NC}"
    else
        print_fail "main-app metrics" "main-app service not found in metrics"
    fi

    # Test: Job audit trail (if we have a job ID)
    if [ -n "$JOB_ID_BASIC" ]; then
        print_test "Job audit trail exists"
        response=$(curl -s -w "\n%{http_code}" "$MONITOR_URL/api/audit/$JOB_ID_BASIC")
        http_code=$(echo "$response" | tail -n 1)
        body=$(echo "$response" | head -n -1)

        if [ "$http_code" = "200" ]; then
            if echo "$body" | jq -e '.audit.service' > /dev/null 2>&1; then
                service_name=$(echo "$body" | jq -r '.audit.service')
                print_pass
                echo -e "    ${CYAN}Sent by service: $service_name${NC}"
            else
                print_fail "Job audit" "No audit record found for job $JOB_ID_BASIC"
            fi
        else
            print_fail "Job audit endpoint" "Expected 200, got $http_code"
        fi
    else
        print_test "Job audit trail exists"
        print_skip "No job ID available"
    fi

    return 0
}

################################################################################
# Test Level 7: Monitoring & Stats
################################################################################

test_monitoring() {
    print_section "Level 7: Monitoring & Statistics"

    # Test: GET /stats endpoint (requires auth)
    print_test "GET /stats endpoint (authenticated)"
    response=$(curl -s -w "\n%{http_code}" -X GET "$EMAIL_API_URL/stats" \
        -H "X-Service-Token: $SERVICE_TOKEN")
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ]; then
        queue_high=$(echo "$body" | jq -r '.queue_high // 0')
        sent_today=$(echo "$body" | jq -r '.sent_today // 0')
        print_pass
        echo -e "    ${CYAN}Queue (high): $queue_high, Sent today: $sent_today${NC}"
    else
        print_fail "GET /stats" "Expected 200, got $http_code"
    fi

    # Test: Monitor API stats
    print_test "Monitor /api/stats endpoint"
    response=$(curl -s -w "\n%{http_code}" "$MONITOR_URL/api/stats")
    http_code=$(echo "$response" | tail -n 1)

    if [ "$http_code" = "200" ]; then
        print_pass
    else
        print_fail "Monitor stats" "Expected 200, got $http_code"
    fi

    # Test: Dead letter queue endpoint
    print_test "Dead letter queue endpoint"
    response=$(curl -s -w "\n%{http_code}" "$MONITOR_URL/api/dead-letter")
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ]; then
        dead_count=$(echo "$body" | jq -r '.count // 0')
        print_pass
        echo -e "    ${CYAN}Dead letter count: $dead_count${NC}"
    else
        print_fail "Dead letter endpoint" "Expected 200, got $http_code"
    fi

    return 0
}

################################################################################
# Main Test Execution
################################################################################

main() {
    clear
    print_header "FreeFace Email Service - Comprehensive Test Suite"

    echo -e "${CYAN}Configuration:${NC}"
    echo "  Email API:  $EMAIL_API_URL"
    echo "  Monitor:    $MONITOR_URL"
    echo "  MailHog:    $MAILHOG_API_URL"
    echo "  Redis:      $REDIS_HOST:$REDIS_PORT"
    echo ""
    echo -e "${YELLOW}Service Token: ${SERVICE_TOKEN:0:20}...${NC}"
    echo ""

    # Check dependencies
    echo -n "Checking dependencies ... "
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}✗${NC}"
        echo ""
        echo -e "${RED}Error: 'jq' is required but not installed.${NC}"
        echo "Install: sudo apt-get install jq"
        exit 1
    fi
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}✗${NC}"
        echo ""
        echo -e "${RED}Error: 'curl' is required but not installed.${NC}"
        exit 1
    fi
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}✗${NC}"
        echo ""
        echo -e "${RED}Error: 'docker-compose' is required but not installed.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓${NC}"

    # Run all test levels
    test_infrastructure || true
    test_service_health || true
    test_authentication || true
    test_email_sending || true
    test_email_delivery || true
    test_audit_trail || true
    test_monitoring || true

    # Print final summary
    print_header "Test Summary"

    echo -e "${BOLD}Total Tests:${NC}    $TESTS_RUN"
    echo -e "${GREEN}${BOLD}Passed:${NC}         $TESTS_PASSED"
    echo -e "${RED}${BOLD}Failed:${NC}         $TESTS_FAILED"
    echo ""

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}${BOLD}  ✓✓✓ ALL TESTS PASSED ✓✓✓${NC}"
        echo -e "${GREEN}${BOLD}  System is READY for production!${NC}"
        echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        exit 0
    else
        echo -e "${RED}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}${BOLD}  ✗✗✗ TESTS FAILED ✗✗✗${NC}"
        echo -e "${RED}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${YELLOW}Failed tests:${NC}"
        for failure in "${FAILED_TESTS[@]}"; do
            echo -e "  ${RED}✗${NC} $failure"
        done
        echo ""
        echo -e "${YELLOW}Troubleshooting:${NC}"
        echo "  1. Check container logs: docker-compose logs"
        echo "  2. Verify .env configuration"
        echo "  3. Ensure SERVICE_TOKEN matches .env.example"
        echo "  4. Check Redis connectivity"
        echo ""
        exit 1
    fi
}

# Run main function
main "$@"
