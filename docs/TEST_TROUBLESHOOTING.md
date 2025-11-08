# 🔧 Test Script Troubleshooting Guide

Quick fixes for common issues when running test scripts for the first time.

## Common Issues & Solutions

### Issue 1: "jq: command not found"

**Error:**
```bash
./scripts/test_email_service.sh: line 123: jq: command not found
```

**Fix:**
```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y jq

# macOS
brew install jq

# Verify
jq --version
```

---

### Issue 2: "docker-compose: command not found"

**Error:**
```bash
docker-compose: command not found
```

**Fix:**
```bash
# Install docker-compose
sudo apt-get install docker-compose

# Or use docker compose (newer syntax)
# Edit scripts and replace:
# docker-compose → docker compose
```

---

### Issue 3: Containers not starting

**Error:**
```
✗ FAIL Docker containers are running
```

**Fix:**
```bash
# Start containers
docker-compose up -d

# Wait for startup
sleep 30

# Verify
docker-compose ps

# Check logs if still failing
docker-compose logs
```

---

### Issue 4: Health endpoint timeout

**Error:**
```
Waiting for Email API to be ready ................ ✗ Timeout
```

**Possible Causes & Fixes:**

**A. Container not ready yet**
```bash
# Wait longer (containers may be slow on first start)
sleep 60

# Check if container is actually running
docker-compose ps email-api

# Check logs
docker-compose logs email-api
```

**B. Port not exposed**
```bash
# Verify ports in docker-compose.yml
grep -A 3 "email-api:" docker-compose.yml

# Should see:
# ports:
#   - "8010:8010"
```

**C. Redis not connected**
```bash
# Check Redis is running
docker-compose ps redis-email

# Test Redis connection
docker-compose exec redis-email redis-cli ping
# Should return: PONG
```

---

### Issue 5: 401 Unauthorized with valid token

**Error:**
```
✗ FAIL Valid token returns 401
```

**Possible Causes & Fixes:**

**A. Token not in .env**
```bash
# Check if token exists in .env
grep SERVICE_TOKEN_MAIN_APP .env

# If missing, add it:
echo "SERVICE_TOKEN_MAIN_APP=st_dev_0000000000000000000000000000000000000000" >> .env

# Restart containers
docker-compose restart email-api
```

**B. Authentication disabled**
```bash
# Check if auth is enabled
grep SERVICE_AUTH_ENABLED .env

# Should be:
SERVICE_AUTH_ENABLED=true

# If false or missing, fix it:
echo "SERVICE_AUTH_ENABLED=true" >> .env

# Restart
docker-compose restart email-api
```

**C. Token prefix mismatch**
```bash
# Check prefix in .env
grep SERVICE_TOKEN_PREFIX .env

# Should be:
SERVICE_TOKEN_PREFIX=st_dev_

# Test script uses:
SERVICE_TOKEN=st_dev_0000000000000000000000000000000000000000
```

---

### Issue 6: MailHog not receiving emails

**Error:**
```
✗ FAIL MailHog received emails
Expected at least 4 emails, got 0
```

**Possible Causes & Fixes:**

**A. Workers not running**
```bash
# Check worker containers
docker-compose ps | grep worker

# Should see 3 workers running

# If not, start them:
docker-compose up -d email-worker-1 email-worker-2 email-worker-3
```

**B. Workers not processing (check logs)**
```bash
# Check worker logs
docker-compose logs email-worker-1 | tail -20

# Should see processing messages like:
# "Processing job job_abc123..."
# "Email sent successfully"

# If errors, check SMTP config
```

**C. Need more time**
```bash
# Script waits 10 seconds - may need more
# Edit test_email_service.sh line ~500:

# Change from:
for i in {1..10}; do

# To:
for i in {1..20}; do
```

**D. MailHog not running**
```bash
# Check MailHog container
docker-compose ps mailhog

# If not running:
docker-compose up -d mailhog

# Test MailHog UI
curl http://localhost:8025/api/v2/messages
```

---

### Issue 7: Audit trail not found

**Error:**
```
✗ FAIL Job audit trail exists
No audit record found for job job_abc123
```

**Possible Causes & Fixes:**

**A. Redis not persisting data**
```bash
# Check Redis is running
docker-compose exec redis-email redis-cli ping

# Check if keys exist
docker-compose exec redis-email redis-cli KEYS "service:*"

# If empty, audit service may not be initialized
docker-compose logs email-api | grep "Audit trail initialized"
```

**B. Audit service not initialized**
```bash
# Check API logs for initialization
docker-compose logs email-api | grep "Audit trail"

# Should see:
# "Audit trail initialized"

# If not, restart API:
docker-compose restart email-api
```

---

### Issue 8: Service metrics not found

**Error:**
```
✗ FAIL main-app service has metrics
main-app service not found in metrics
```

**Fix:**
```bash
# Metrics are created when emails are sent
# Run a quick test email first:

curl -X POST http://localhost:8010/send \
  -H "Content-Type: application/json" \
  -H "X-Service-Token: st_dev_0000000000000000000000000000000000000000" \
  -d '{"recipients": "test@example.com", "template": "welcome", "data": {}}'

# Wait a moment
sleep 2

# Then check metrics
curl http://localhost:8011/api/service-metrics

# Should now show main-app
```

---

### Issue 9: JSON parse errors

**Error:**
```bash
parse error: Invalid numeric literal at line 1, column 5
```

**Possible Causes & Fixes:**

**A. API returned HTML instead of JSON**
```bash
# Check what API actually returns:
curl -v http://localhost:8010/health

# If you see HTML, API is returning error page
# Check API logs:
docker-compose logs email-api
```

**B. Response format changed**
```bash
# Get raw response to debug:
response=$(curl -s http://localhost:8010/send \
  -H "X-Service-Token: $SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"recipients": "test@example.com", "template": "welcome", "data": {}}')

echo "$response"

# Should be valid JSON
echo "$response" | jq .
```

---

### Issue 10: Script hangs / never completes

**Possible Causes & Fixes:**

**A. Infinite loop waiting for service**
```bash
# Kill script: Ctrl+C

# Manually check service
curl http://localhost:8010/health

# If service never responds, check:
docker-compose logs email-api

# Look for startup errors
```

**B. Network issues**
```bash
# Check Docker network
docker network ls

# Check containers are on same network
docker network inspect email-service_email_network
```

---

## Quick Fixes Checklist

Before running tests, verify:

- [ ] Docker daemon is running: `docker ps`
- [ ] Compose file exists: `ls docker-compose.yml`
- [ ] .env file configured: `ls .env` (copy from .env.example if missing)
- [ ] Service token in .env: `grep SERVICE_TOKEN_MAIN_APP .env`
- [ ] Auth enabled: `grep SERVICE_AUTH_ENABLED .env`
- [ ] Dependencies installed: `command -v jq && command -v curl`
- [ ] Containers running: `docker-compose ps`
- [ ] Wait 30+ seconds after start: `sleep 30`

---

## Debug Mode

Run test script with debug output:

```bash
# Enable bash debug mode
bash -x ./scripts/test_email_service.sh

# Or add to script temporarily:
# Add after shebang:
set -x  # Print commands as they execute
```

---

## Manual Verification

If automated tests fail, verify manually:

```bash
# 1. Health check
curl http://localhost:8010/health

# 2. Send test email
curl -X POST http://localhost:8010/send \
  -H "Content-Type: application/json" \
  -H "X-Service-Token: st_dev_0000000000000000000000000000000000000000" \
  -d '{"recipients": "test@example.com", "template": "welcome", "data": {"name": "Test"}}'

# 3. Check MailHog
curl http://localhost:8025/api/v2/messages | jq

# 4. Check metrics
curl http://localhost:8011/api/service-metrics | jq

# 5. Check Redis
docker-compose exec redis-email redis-cli KEYS "*" | head -10
```

---

## Getting Help

If tests still fail:

1. **Collect logs:**
   ```bash
   docker-compose logs > logs.txt
   ```

2. **Check specific service:**
   ```bash
   docker-compose logs email-api > api-logs.txt
   docker-compose logs email-worker-1 > worker-logs.txt
   ```

3. **Verify configuration:**
   ```bash
   cat .env
   ```

4. **Check documentation:**
   - `docs/TESTING_GUIDE.md`
   - `docs/SERVICE_AUTHENTICATION.md`

---

## Known Limitations

- **First run may be slower:** Docker pulls images, builds containers
- **MailHog timing:** Workers may need 15-30s to process (not 10s)
- **macOS DNS:** May need to use `host.docker.internal` instead of `localhost`
- **Windows:** May need WSL2 for proper Docker integration

---

**Last Updated:** 2025-11-08
**Version:** 1.0.0
