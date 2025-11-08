# 🧪 Email Service Testing Guide

Complete guide for testing the FreeFace Email Service with automated test suites.

## Table of Contents

1. [Test Scripts Overview](#test-scripts-overview)
2. [Quick Test](#quick-test)
3. [Comprehensive Test Suite](#comprehensive-test-suite)
4. [Manual Testing](#manual-testing)
5. [Troubleshooting Test Failures](#troubleshooting-test-failures)

---

## Test Scripts Overview

We provide two test scripts for different scenarios:

| Script | Use Case | Duration | Tests |
|--------|----------|----------|-------|
| `quick_test.sh` | Fast health check | ~5 seconds | 3 basic tests |
| `test_email_service.sh` | Full system validation | ~30 seconds | 30+ comprehensive tests |

---

## Quick Test

### Purpose

Fast validation that the core system is working. Use this during development for quick checks.

### Usage

```bash
./scripts/quick_test.sh
```

### What It Tests

1. ✅ **Docker containers** are running
2. ✅ **Health endpoint** is accessible
3. ✅ **Email sending** works with authentication

### Example Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FreeFace Email Service - Quick Health Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Checking containers ... OK
✓ Checking health endpoint ... OK
✓ Sending test email ... OK (Job: job_abc123)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ System is HEALTHY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### When to Use

- After starting containers
- Before deploying changes
- Quick sanity check during development
- CI/CD pipeline quick validation

---

## Comprehensive Test Suite

### Purpose

Full system validation testing ALL components, endpoints, and features. Use this before production deployment.

### Usage

```bash
./scripts/test_email_service.sh
```

### What It Tests

The comprehensive suite runs **7 levels of tests**:

#### Level 1: Infrastructure & Container Health
- Docker containers running (API, Redis, Monitor, MailHog, Workers)
- Network connectivity
- Service readiness

#### Level 2: Service Health Endpoints
- Email API `/health` endpoint
- Monitor dashboard accessibility
- MailHog API accessibility

#### Level 3: Service Authentication
- Missing token → 401 ❌
- Invalid token → 401 ❌
- Wrong prefix token → 401 ❌
- Valid token → 200 ✅

#### Level 4: Email Sending Operations
- `POST /send` - Basic email
- `POST /send/welcome` - Welcome email
- `POST /send/password-reset` - Password reset
- `POST /send` - Multiple recipients
- Job IDs returned

#### Level 5: Email Delivery Verification
- MailHog received emails
- Correct recipients
- Email count verification
- Content validation

#### Level 6: Audit Trail & Metrics
- Service metrics endpoint
- Per-service statistics
- Job audit records
- Redis data persistence

#### Level 7: Monitoring & Statistics
- `GET /stats` endpoint (authenticated)
- Monitor API endpoints
- Dead letter queue
- Rate limits status

### Example Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FreeFace Email Service - Comprehensive Test Suite
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Configuration:
  Email API:  http://localhost:8010
  Monitor:    http://localhost:8011
  MailHog:    http://localhost:8025
  Redis:      localhost:6379

Service Token: st_dev_000000000000...

Checking dependencies ... ✓

▶ Level 1: Infrastructure & Container Health

  Testing: Docker containers are running ... ✓ PASS
  Testing: email-api container is running ... ✓ PASS
  Testing: Redis container is running ... ✓ PASS
  Testing: Monitor container is running ... ✓ PASS
  Testing: MailHog container is running ... ✓ PASS
  Testing: Worker containers are running (3 workers expected) ... ✓ PASS
    Found 3 worker(s)
  Waiting for Email API to be ready .......... ✓
  Waiting for Monitor Dashboard to be ready . ✓
  Waiting for MailHog API to be ready . ✓

▶ Level 2: Service Health Endpoints

  Testing: Email API /health endpoint (public) ... ✓ PASS
  Testing: Monitor dashboard is accessible ... ✓ PASS
  Testing: MailHog API is accessible ... ✓ PASS

▶ Level 3: Service Authentication

  Testing: Missing token returns 401 ... ✓ PASS
  Testing: Invalid token returns 401 ... ✓ PASS
  Testing: Wrong prefix token returns 401 ... ✓ PASS
  Testing: Valid token returns 200 ... ✓ PASS
    Job ID: job_abc123xyz

▶ Level 4: Email Sending Operations

  Testing: POST /send (basic email) ... ✓ PASS
    Job ID: job_def456
  Testing: POST /send/welcome ... ✓ PASS
    Job ID: job_ghi789
  Testing: POST /send/password-reset ... ✓ PASS
    Job ID: job_jkl012
  Testing: POST /send (multiple recipients) ... ✓ PASS
    Job ID: job_mno345

  Waiting for workers to process emails (10s) .......... ✓

▶ Level 5: Email Delivery Verification (MailHog)

  Testing: MailHog received emails ... ✓ PASS
    Received 6 email(s) in MailHog
  Testing: Basic test email received in MailHog ... ✓ PASS
  Testing: Welcome email received in MailHog ... ✓ PASS
  Testing: Password reset email received in MailHog ... ✓ PASS

▶ Level 6: Audit Trail & Metrics

  Testing: Service metrics endpoint accessible ... ✓ PASS
    Found 1 service(s) with metrics
  Testing: main-app service has metrics ... ✓ PASS
    Total calls: 5, Total emails: 6
  Testing: Job audit trail exists ... ✓ PASS
    Sent by service: main-app

▶ Level 7: Monitoring & Statistics

  Testing: GET /stats endpoint (authenticated) ... ✓ PASS
    Queue (high): 0, Sent today: 6
  Testing: Monitor /api/stats endpoint ... ✓ PASS
  Testing: Dead letter queue endpoint ... ✓ PASS
    Dead letter count: 0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Test Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Tests:    30
Passed:         30
Failed:         0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓✓✓ ALL TESTS PASSED ✓✓✓
  System is READY for production!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### When to Use

- Before production deployment
- After major code changes
- Weekly regression testing
- CI/CD full validation
- Before creating pull requests

---

## Manual Testing

### Prerequisites

```bash
# Start services
docker-compose up -d

# Wait for services to be ready (~30 seconds)
docker-compose logs -f email-api

# Verify containers
docker-compose ps
```

### Test 1: Health Check (No Auth)

```bash
curl http://localhost:8010/health

# Expected:
# {
#   "status": "healthy",
#   "redis": "connected",
#   "queues": {
#     "high": 0,
#     "medium": 0,
#     "low": 0
#   }
# }
```

### Test 2: Authentication Required

```bash
# Missing token → 401
curl -X POST http://localhost:8010/send \
  -H "Content-Type: application/json" \
  -d '{"recipients": "test@example.com", "template": "welcome", "data": {}}'

# Expected: 401 Unauthorized
```

### Test 3: Send Email (With Auth)

```bash
# Get token from .env
export SERVICE_TOKEN=$(grep SERVICE_TOKEN_MAIN_APP .env | cut -d= -f2)

# Send email
curl -X POST http://localhost:8010/send \
  -H "Content-Type: application/json" \
  -H "X-Service-Token: $SERVICE_TOKEN" \
  -d '{
    "recipients": "test@example.com",
    "template": "welcome",
    "data": {"name": "Test User"}
  }'

# Expected: {"job_id": "job_...", "status": "queued", ...}
```

### Test 4: Verify Email in MailHog

```bash
# Open browser
open http://localhost:8025

# Or use API
curl http://localhost:8025/api/v2/messages | jq

# Check email received
```

### Test 5: Check Audit Trail

```bash
# Get job ID from previous test
JOB_ID="job_abc123..."

# Check audit
curl http://localhost:8011/api/audit/$JOB_ID | jq

# Expected:
# {
#   "job_id": "job_abc123...",
#   "audit": {
#     "service": "main-app",
#     "endpoint": "/send",
#     "timestamp": "2025-11-08T...",
#     "template": "welcome"
#   }
# }
```

### Test 6: Check Service Metrics

```bash
curl http://localhost:8011/api/service-metrics | jq

# Expected:
# {
#   "services": {
#     "main-app": {
#       "total_calls": 5,
#       "total_emails": 5,
#       "calls_today": 5,
#       "endpoints": {
#         "/send": 3,
#         "/send/welcome": 1,
#         "/stats": 1
#       }
#     }
#   }
# }
```

---

## Troubleshooting Test Failures

### Containers Not Running

**Symptom:** Test fails at "Docker containers are running"

**Solution:**
```bash
# Start containers
docker-compose up -d

# Check status
docker-compose ps

# Check logs
docker-compose logs
```

### Health Check Failing

**Symptom:** Test fails at "Email API /health endpoint"

**Solution:**
```bash
# Check API logs
docker-compose logs email-api

# Verify Redis connection
docker-compose exec redis-email redis-cli ping

# Restart API
docker-compose restart email-api
```

### Authentication Failing

**Symptom:** Valid token returns 401

**Solutions:**

1. **Check token in .env:**
   ```bash
   grep SERVICE_TOKEN_MAIN_APP .env
   # Should match test script token
   ```

2. **Check authentication is enabled:**
   ```bash
   grep SERVICE_AUTH_ENABLED .env
   # Should be 'true'
   ```

3. **Restart containers:**
   ```bash
   docker-compose restart email-api
   ```

### Emails Not Delivered

**Symptom:** MailHog doesn't receive emails

**Solutions:**

1. **Check workers are running:**
   ```bash
   docker-compose ps | grep worker
   # Should see 3 workers
   ```

2. **Check worker logs:**
   ```bash
   docker-compose logs email-worker-1
   # Look for processing messages
   ```

3. **Check MailHog:**
   ```bash
   curl http://localhost:8025/api/v2/messages
   # Should return emails
   ```

4. **Wait longer:**
   ```bash
   # Workers may need time to process
   sleep 10
   curl http://localhost:8025/api/v2/messages
   ```

### Audit Trail Missing

**Symptom:** No audit records in Redis

**Solutions:**

1. **Check Redis connection:**
   ```bash
   docker-compose exec redis-email redis-cli ping
   # Should return PONG
   ```

2. **Check audit service initialized:**
   ```bash
   docker-compose logs email-api | grep "Audit trail"
   # Should see "Audit trail initialized"
   ```

3. **Manually check Redis:**
   ```bash
   docker-compose exec redis-email redis-cli KEYS "service:*"
   # Should see audit keys
   ```

### Service Metrics Not Found

**Symptom:** No services in metrics response

**Solution:**
```bash
# Send a test email first to create metrics
curl -X POST http://localhost:8010/send \
  -H "Content-Type: application/json" \
  -H "X-Service-Token: $SERVICE_TOKEN" \
  -d '{"recipients": "test@example.com", "template": "welcome", "data": {}}'

# Then check metrics
curl http://localhost:8011/api/service-metrics
```

---

## Environment Variables

Test scripts use these environment variables (with defaults):

```bash
# Email API URL
EMAIL_API_URL=http://localhost:8010

# Monitor URL
MONITOR_URL=http://localhost:8011

# MailHog URL
MAILHOG_API_URL=http://localhost:8025

# Redis connection
REDIS_HOST=localhost
REDIS_PORT=6379

# Service token
SERVICE_TOKEN=st_dev_0000000000000000000000000000000000000000
```

### Custom Configuration

```bash
# Use different URLs
EMAIL_API_URL=http://custom-host:8010 ./scripts/test_email_service.sh

# Use different token
SERVICE_TOKEN=st_dev_abc123... ./scripts/quick_test.sh
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Email Service Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Start services
        run: docker-compose up -d

      - name: Wait for services
        run: sleep 30

      - name: Run comprehensive tests
        run: ./scripts/test_email_service.sh

      - name: Show logs on failure
        if: failure()
        run: docker-compose logs
```

### Jenkins Example

```groovy
pipeline {
    agent any

    stages {
        stage('Test') {
            steps {
                sh 'docker-compose up -d'
                sh 'sleep 30'
                sh './scripts/test_email_service.sh'
            }
        }
    }

    post {
        failure {
            sh 'docker-compose logs'
        }
        always {
            sh 'docker-compose down'
        }
    }
}
```

---

## Dependencies

Test scripts require:

- `bash` - Shell interpreter
- `curl` - HTTP client
- `jq` - JSON processor
- `docker-compose` - Container orchestration

### Install Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y curl jq docker-compose
```

**macOS:**
```bash
brew install curl jq docker-compose
```

---

## Best Practices

1. **Run Quick Test Often**
   - After code changes
   - Before commits
   - During development

2. **Run Comprehensive Test Before:**
   - Production deployments
   - Pull requests
   - Major releases

3. **Monitor Test Results**
   - Track pass/fail rates
   - Investigate failures immediately
   - Update tests as system evolves

4. **Keep Tests Updated**
   - Add tests for new features
   - Update expected values
   - Remove obsolete tests

---

## Support

- **Test Script Issues:** Check `scripts/test_email_service.sh` source
- **Service Issues:** See `docs/SERVICE_AUTHENTICATION.md`
- **Integration:** See `docs/INTEGRATION_EXAMPLES.md`
- **Logs:** `docker-compose logs`

---

**Last Updated:** 2025-11-08
**Version:** 1.0.0
