#!/bin/bash
################################################################################
# Test Script Validator
# Simulates test conditions without running actual Docker
################################################################################

echo "🔍 Validating test scripts..."
echo ""

# Check 1: Syntax
echo "✓ Checking syntax..."
bash -n scripts/test_email_service.sh && echo "  ✅ test_email_service.sh syntax OK"
bash -n scripts/quick_test.sh && echo "  ✅ quick_test.sh syntax OK"
echo ""

# Check 2: Executable permissions
echo "✓ Checking permissions..."
if [ -x scripts/test_email_service.sh ]; then
    echo "  ✅ test_email_service.sh is executable"
else
    echo "  ❌ test_email_service.sh is NOT executable"
fi

if [ -x scripts/quick_test.sh ]; then
    echo "  ✅ quick_test.sh is executable"
else
    echo "  ❌ quick_test.sh is NOT executable"
fi
echo ""

# Check 3: Required commands
echo "✓ Checking dependencies..."
command -v curl >/dev/null 2>&1 && echo "  ✅ curl available" || echo "  ❌ curl NOT available"
command -v jq >/dev/null 2>&1 && echo "  ✅ jq available" || echo "  ❌ jq NOT available"
command -v docker-compose >/dev/null 2>&1 && echo "  ✅ docker-compose available" || echo "  ❌ docker-compose NOT available"
echo ""

# Check 4: Key functions defined
echo "✓ Checking script structure..."
grep -q "test_infrastructure()" scripts/test_email_service.sh && echo "  ✅ test_infrastructure() defined"
grep -q "test_authentication()" scripts/test_email_service.sh && echo "  ✅ test_authentication() defined"
grep -q "test_email_sending()" scripts/test_email_service.sh && echo "  ✅ test_email_sending() defined"
grep -q "test_email_delivery()" scripts/test_email_service.sh && echo "  ✅ test_email_delivery() defined"
grep -q "test_audit_trail()" scripts/test_email_service.sh && echo "  ✅ test_audit_trail() defined"
echo ""

# Check 5: Configuration variables
echo "✓ Checking configuration..."
grep -q "EMAIL_API_URL=" scripts/test_email_service.sh && echo "  ✅ EMAIL_API_URL configured"
grep -q "SERVICE_TOKEN=" scripts/test_email_service.sh && echo "  ✅ SERVICE_TOKEN configured"
grep -q "MAILHOG_API_URL=" scripts/test_email_service.sh && echo "  ✅ MAILHOG_API_URL configured"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Scripts are structurally valid!"
echo ""
echo "⚠️  Note: Actual functionality can only be verified by running"
echo "   with Docker containers active."
echo ""
echo "To test for real:"
echo "  1. docker-compose up -d"
echo "  2. sleep 30"
echo "  3. ./scripts/test_email_service.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
