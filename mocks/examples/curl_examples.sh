#!/bin/bash
# File: mocks/examples/curl_examples.sh
# cURL examples for testing mock servers

echo "=================================================="
echo "Mock Server cURL Examples"
echo "=================================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Base URLs
FREEFACE_API="http://localhost:8001"
SENDGRID_API="http://localhost:8002"
MAILGUN_API="http://localhost:8003"
WEBHOOK_API="http://localhost:8004"

# API Keys
SENDGRID_KEY="SG.test_key_1234567890"
MAILGUN_KEY="api:test-mailgun-key-12345"
MAILGUN_DOMAIN="sandbox123.mailgun.org"

echo ""
echo -e "${BLUE}=== FreeFace API Examples ===${NC}"
echo ""

echo -e "${GREEN}1. Health Check${NC}"
curl -s "$FREEFACE_API/health" | jq
echo ""

echo -e "${GREEN}2. List Users (first 5)${NC}"
curl -s "$FREEFACE_API/api/v1/users?page=1&per_page=5" | jq
echo ""

echo -e "${GREEN}3. List Groups${NC}"
curl -s "$FREEFACE_API/api/v1/groups?page=1&per_page=3" | jq
echo ""

echo -e "${GREEN}4. Resolve Multiple Users${NC}"
curl -s -X POST "$FREEFACE_API/api/v1/users/resolve" \
  -H "Content-Type: application/json" \
  -d '{
    "user_ids": ["test-id-1", "test-id-2"]
  }' | jq
echo ""

echo -e "${GREEN}5. Simulate Error (404)${NC}"
curl -s "$FREEFACE_API/api/v1/users/invalid-id?simulate_error=404" | jq
echo ""

echo -e "${GREEN}6. Test Response Delay (1 second)${NC}"
echo "Sending request with 1 second delay..."
time curl -s "$FREEFACE_API/api/v1/users?delay_ms=1000&per_page=1" | jq -r '.data[0].email // "No data"'
echo ""

echo ""
echo -e "${BLUE}=== SendGrid API Examples ===${NC}"
echo ""

echo -e "${GREEN}1. Health Check${NC}"
curl -s "$SENDGRID_API/health" | jq
echo ""

echo -e "${GREEN}2. Send Email${NC}"
curl -s -X POST "$SENDGRID_API/v3/mail/send" \
  -H "Authorization: Bearer $SENDGRID_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "personalizations": [
      {
        "to": [
          {"email": "user@example.com", "name": "Test User"}
        ]
      }
    ],
    "from": {
      "email": "sender@freeface.com",
      "name": "FreeFace"
    },
    "subject": "Test Email from cURL",
    "content": [
      {
        "type": "text/plain",
        "value": "This is a test email sent via cURL!"
      }
    ]
  }' | jq
echo ""

echo -e "${GREEN}3. Get Email Statistics${NC}"
curl -s "$SENDGRID_API/v3/stats" \
  -H "Authorization: Bearer $SENDGRID_KEY" | jq
echo ""

echo -e "${GREEN}4. List Sent Messages${NC}"
curl -s "$SENDGRID_API/v3/messages" \
  -H "Authorization: Bearer $SENDGRID_KEY" | jq
echo ""

echo -e "${GREEN}5. Test Invalid API Key${NC}"
curl -s -X POST "$SENDGRID_API/v3/mail/send" \
  -H "Authorization: Bearer invalid-key" \
  -H "Content-Type: application/json" \
  -d '{"personalizations":[{"to":[{"email":"test@example.com"}]}],"from":{"email":"sender@example.com"},"subject":"Test","content":[{"type":"text/plain","value":"Test"}]}' | jq
echo ""

echo ""
echo -e "${BLUE}=== Mailgun API Examples ===${NC}"
echo ""

echo -e "${GREEN}1. Health Check${NC}"
curl -s "$MAILGUN_API/health" | jq
echo ""

echo -e "${GREEN}2. Send Email${NC}"
curl -s -X POST "$MAILGUN_API/$MAILGUN_DOMAIN/messages" \
  -u "$MAILGUN_KEY" \
  -F "from=sender@freeface.com" \
  -F "to=user@example.com" \
  -F "subject=Test Email from Mailgun" \
  -F "text=This is a test email sent via Mailgun mock!" | jq
echo ""

echo -e "${GREEN}3. Get Email Events${NC}"
curl -s "$MAILGUN_API/$MAILGUN_DOMAIN/events" \
  -u "$MAILGUN_KEY" | jq
echo ""

echo -e "${GREEN}4. List Domains${NC}"
curl -s "$MAILGUN_API/v3/domains" \
  -u "$MAILGUN_KEY" | jq
echo ""

echo ""
echo -e "${BLUE}=== Webhook Receiver Examples ===${NC}"
echo ""

echo -e "${GREEN}1. Health Check${NC}"
curl -s "$WEBHOOK_API/health" | jq
echo ""

echo -e "${GREEN}2. Clear Webhook History${NC}"
curl -s -X DELETE "$WEBHOOK_API/webhooks/history" | jq
echo ""

echo -e "${GREEN}3. Send Test Webhooks${NC}"
curl -s -X POST "$WEBHOOK_API/webhooks/sendgrid" \
  -H "Content-Type: application/json" \
  -d '{"event":"delivered","email":"user1@example.com","timestamp":1234567890}' | jq
echo ""

curl -s -X POST "$WEBHOOK_API/webhooks/mailgun" \
  -H "Content-Type: application/json" \
  -d '{"event":"opened","email":"user2@example.com","timestamp":1234567891}' | jq
echo ""

curl -s -X POST "$WEBHOOK_API/webhooks/custom" \
  -H "Content-Type: application/json" \
  -d '{"event":"clicked","email":"user3@example.com","timestamp":1234567892}' | jq
echo ""

echo -e "${GREEN}4. Get Webhook History${NC}"
curl -s "$WEBHOOK_API/webhooks/history?limit=10" | jq
echo ""

echo -e "${GREEN}5. Get Webhook Statistics${NC}"
curl -s "$WEBHOOK_API/webhooks/stats" | jq
echo ""

echo "=================================================="
echo -e "${GREEN}✅ All examples completed!${NC}"
echo "=================================================="
echo ""
echo "View interactive API docs:"
echo "  FreeFace API:  $FREEFACE_API/docs"
echo "  SendGrid API:  $SENDGRID_API/docs"
echo "  Mailgun API:   $MAILGUN_API/docs"
echo "  Webhook API:   $WEBHOOK_API/docs"
echo ""
