# 🔐 Service Authentication Guide

Complete guide for service-to-service authentication in the FreeFace Email Service.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Setup Guide](#setup-guide)
4. [Token Format](#token-format)
5. [Configuration](#configuration)
6. [Audit Trail & Metrics](#audit-trail--metrics)
7. [Token Rotation](#token-rotation)
8. [Security Best Practices](#security-best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The FreeFace Email Service uses **service tokens** for service-to-service authentication. This provides:

✅ **Security:** Only authorized services can send emails
✅ **Audit Trail:** Track which service sent which email
✅ **Metrics:** Per-service usage statistics
✅ **Accountability:** Know who's using the email system
✅ **Rate Limiting:** (Future) Per-service quotas

### Authentication Flow

```
┌─────────────────┐                    ┌──────────────────┐
│   Your Service  │                    │  Email Service   │
│   (main-app)    │                    │   (email-api)    │
└────────┬────────┘                    └────────┬─────────┘
         │                                      │
         │  POST /send                          │
         │  X-Service-Token: st_dev_abc123...   │
         │ ──────────────────────────────────>  │
         │                                      │
         │        1. Verify token               │
         │        2. Identify service           │
         │        3. Log audit trail            │
         │        4. Process request            │
         │                                      │
         │  { "job_id": "job_xyz" }             │
         │  <────────────────────────────────── │
         │                                      │
```

---

## Architecture

### Components

1. **ServiceAuthenticator** (`services/auth_service.py`)
   - Token verification (constant-time comparison)
   - Service identification
   - Token format validation

2. **ServiceAuditTrail** (`services/audit_service.py`)
   - Audit logging to Redis
   - Per-service metrics tracking
   - Call timeline storage

3. **FastAPI Dependency** (`api.py`)
   - `verify_service_token()` dependency
   - Applied to protected endpoints
   - Returns ServiceIdentity

### Data Flow

```
Request with Token
    │
    ├──> ServiceAuthenticator.verify_token()
    │    │
    │    ├──> Validate token format
    │    ├──> Constant-time comparison
    │    └──> Return ServiceIdentity
    │
    ├──> Endpoint Handler
    │    │
    │    ├──> Process business logic
    │    └──> Generate job_id
    │
    └──> ServiceAuditTrail.log_service_call()
         │
         ├──> Store audit record in Redis
         ├──> Increment metrics counters
         └──> Update call timeline
```

---

## Setup Guide

### Step 1: Generate Service Tokens

For each service that needs to call the email API:

```bash
# Generate token for your service
python scripts/generate_service_token.py --service main-app --env dev

# Output:
# ======================================================================
#   SERVICE TOKEN GENERATED
# ======================================================================
#
# Token:       st_dev_a1b2c3d4e5f6789012345678901234567890abcd
# Environment: dev
# Valid:       ✓ Yes
#
# HOW TO USE:
# 1. Add to .env file:
#    SERVICE_TOKEN_MAIN_APP=st_dev_a1b2c3d4e5f6789012345678901234567890abcd
```

### Step 2: Configure Email Service

Add tokens to email service's `.env` file:

```bash
# Email Service .env

# Enable authentication
SERVICE_AUTH_ENABLED=true
SERVICE_TOKEN_PREFIX=st_dev_

# Service tokens (one per calling service)
SERVICE_TOKEN_MAIN_APP=st_dev_a1b2c3d4e5f6789012345678901234567890abcd
SERVICE_TOKEN_USER_SERVICE=st_dev_1111111111111111111111111111111111111111
SERVICE_TOKEN_NOTIFICATION=st_dev_2222222222222222222222222222222222222222
```

### Step 3: Configure Calling Service

Add token to your service's `.env` file:

```bash
# Your Service .env

# Email service configuration
EMAIL_SERVICE_URL=http://email-api:8010
SERVICE_TOKEN_YOUR_APP=st_dev_a1b2c3d4e5f6789012345678901234567890abcd
```

### Step 4: Use in Your Code

```python
import httpx
import os

EMAIL_SERVICE_URL = os.getenv("EMAIL_SERVICE_URL")
SERVICE_TOKEN = os.getenv("SERVICE_TOKEN_YOUR_APP")

async with httpx.AsyncClient() as client:
    response = await client.post(
        f"{EMAIL_SERVICE_URL}/send",
        headers={"X-Service-Token": SERVICE_TOKEN},
        json={
            "recipients": "user@example.com",
            "template": "welcome",
            "data": {"name": "John"}
        }
    )

    result = response.json()
    print(f"Email queued: {result['job_id']}")
```

---

## Token Format

### Structure

```
st_<environment>_<40_hex_chars>
│  │             │
│  │             └─ Random part (160 bits entropy)
│  └─────────────── Environment identifier
└────────────────── Service Token prefix
```

### Examples

```
st_dev_a1b2c3d4e5f6789012345678901234567890abcd       # Development
st_staging_x9y8z7w6v5u4t3s2r1q0p9o8n7m6l5k4j3i2h1g0   # Staging
st_live_9f8e7d6c5b4a39281f0e9d8c7b6a59483f2e1d0c    # Production
```

### Token Properties

| Property | Value | Description |
|----------|-------|-------------|
| **Prefix** | `st_` | Service Token identifier |
| **Environment** | `dev`, `staging`, `live` | Environment tag |
| **Random Part** | 40 hex chars | 160 bits of entropy |
| **Total Length** | ~50 characters | Full token length |
| **Character Set** | `[a-f0-9_]` | URL-safe hex + underscore |

### Security Features

1. **Cryptographically Secure Random**
   - Uses Python's `secrets` module
   - Not predictable or brute-forceable

2. **Constant-Time Comparison**
   - Uses `hmac.compare_digest()`
   - Prevents timing attacks

3. **Prefix Validation**
   - Prevents accidental use of wrong secrets
   - Easy to identify in logs/errors

4. **Environment Tagging**
   - Prevents dev tokens in production
   - Clear environment identification

---

## Configuration

### Environment Variables

#### Email Service Configuration

```bash
# Required
SERVICE_AUTH_ENABLED=true                    # Enable authentication
SERVICE_TOKEN_PREFIX=st_dev_                 # Token prefix
SERVICE_TOKEN_<NAME>=st_dev_abc123...        # Service tokens

# Optional
# (None currently - future features may add options)
```

#### Calling Service Configuration

```bash
# Required
SERVICE_TOKEN_YOUR_APP=st_dev_abc123...      # Your service's token
EMAIL_SERVICE_URL=http://email-api:8010      # Email service URL

# Optional
EMAIL_SERVICE_TIMEOUT=30                     # Request timeout (seconds)
```

### Disabling Authentication (Development Only)

For local testing without tokens:

```bash
# Email Service .env
SERVICE_AUTH_ENABLED=false
```

**⚠️ WARNING:** Never disable authentication in production!

---

## Audit Trail & Metrics

### Audit Records

Every authenticated API call is logged to Redis with:

- **Service name** - Which service made the call
- **Endpoint** - Which API endpoint was called
- **Timestamp** - When the call occurred
- **Job ID** - Email job identifier (if applicable)
- **Metadata** - Additional context (template, recipients, etc.)

### Redis Keys

```redis
# Audit record for specific job
service:audit:{job_id}
> HGETALL service:audit:job_abc123
1) "service" -> "main-app"
2) "endpoint" -> "/send"
3) "timestamp" -> "2025-11-08T14:30:00"
4) "template" -> "welcome"
5) "recipient_count" -> "1"

# Service call timeline (sorted by time)
service:calls:{service}:{date}
> ZRANGE service:calls:main-app:2025-11-08 0 -1
1) "2025-11-08T10:15:00|/send"
2) "2025-11-08T10:16:00|/send/welcome"
3) "2025-11-08T10:17:00|/stats"

# Metrics counters
service:metrics:{service}:total_calls       # Total API calls
service:metrics:{service}:total_emails      # Total emails sent
service:metrics:{service}:{endpoint}        # Calls per endpoint
```

### Query Examples

#### Who sent job X?

```python
from services.audit_service import audit_trail

audit = await audit_trail.get_job_audit("job_abc123")
print(f"Sent by: {audit['service']}")
# Output: Sent by: main-app
```

#### Service metrics

```python
metrics = await audit_trail.get_service_metrics("main-app")
print(f"Total calls: {metrics['total_calls']}")
print(f"Total emails: {metrics['total_emails']}")
print(f"Calls today: {metrics['calls_today']}")
print(f"Per endpoint: {metrics['endpoints']}")

# Output:
# Total calls: 1247
# Total emails: 5623
# Calls today: 45
# Per endpoint: {'/send': 800, '/send/welcome': 300, ...}
```

#### All services metrics

```python
all_metrics = await audit_trail.get_all_services_metrics()
for service, metrics in all_metrics.items():
    print(f"{service}: {metrics['total_emails']} emails")

# Output:
# main-app: 45623 emails
# user-service: 12034 emails
# notification: 8901 emails
```

### Retention Periods

| Data Type | Retention | Reason |
|-----------|-----------|--------|
| Audit records | 30 days | Compliance & debugging |
| Daily call logs | 90 days | Usage analysis |
| Metrics counters | Permanent | Historical tracking |

---

## Token Rotation

### Why Rotate Tokens?

- **Security best practice** - Limit exposure window
- **Compliance** - Meet security requirements
- **Compromise mitigation** - Invalidate leaked tokens

### Zero-Downtime Rotation Process

The system supports **multiple valid tokens per service** for seamless rotation:

#### Step 1: Generate New Token

```bash
python scripts/generate_service_token.py --service main-app --env live
```

#### Step 2: Add Secondary Token to Email Service

```bash
# Email Service .env
SERVICE_TOKEN_MAIN_APP_PRIMARY=st_live_NEW_TOKEN_HERE...
SERVICE_TOKEN_MAIN_APP_SECONDARY=st_live_OLD_TOKEN_HERE...   # Keep old token active
```

Both tokens are now valid.

#### Step 3: Update Calling Service

```bash
# Your Service .env
SERVICE_TOKEN_YOUR_APP=st_live_NEW_TOKEN_HERE...
```

#### Step 4: Deploy Calling Service

Deploy your service with the new token. No downtime!

#### Step 5: Grace Period

Wait 24-48 hours to ensure all instances are updated.

#### Step 6: Remove Old Token

```bash
# Email Service .env
SERVICE_TOKEN_MAIN_APP=st_live_NEW_TOKEN_HERE...
# Remove _SECONDARY line
```

### Rotation Schedule

| Environment | Rotation Frequency | Reason |
|-------------|-------------------|--------|
| Development | 180 days | Low risk |
| Staging | 90 days | Medium risk |
| Production | 90 days | High security requirement |

---

## Security Best Practices

### ✅ DO

1. **Store tokens securely**
   - Environment variables
   - Secret management systems (Vault, AWS Secrets Manager)
   - Never in source code

2. **Use different tokens per environment**
   - Development: `st_dev_...`
   - Staging: `st_staging_...`
   - Production: `st_live_...`

3. **Rotate tokens regularly**
   - Production: Every 90 days
   - Development: Every 180 days

4. **Monitor authentication failures**
   - Set up alerts for 401 errors
   - Investigate suspicious patterns

5. **Use HTTPS in production**
   - Encrypt tokens in transit
   - Prevent MITM attacks

6. **Limit token exposure**
   - Don't log full tokens
   - Redact in error messages
   - Use prefix for identification

### ❌ DON'T

1. **Never commit tokens to git**
   - Use `.env` files (`.gitignored`)
   - Use environment variables

2. **Never share tokens between services**
   - Each service = unique token
   - Enables accountability

3. **Never disable auth in production**
   - Security requirement
   - Compliance mandate

4. **Never log full tokens**
   - Log prefix only: `st_dev_abc...`
   - Prevents accidental exposure

5. **Never use HTTP in production**
   - Always use HTTPS
   - Encrypt sensitive data

6. **Never ignore auth errors**
   - 401 = misconfiguration or attack
   - Investigate immediately

---

## Troubleshooting

### Problem: 401 Authentication Required

```json
{
  "error": "authentication_required",
  "message": "Service token required. Provide X-Service-Token header."
}
```

**Solutions:**
1. Check header name is `X-Service-Token` (case-sensitive)
2. Verify token is being sent in request
3. Check environment variable is set

### Problem: 401 Invalid Token

```json
{
  "error": "invalid_token",
  "message": "Service token not recognized."
}
```

**Solutions:**
1. Verify token is configured in email service's `.env`
2. Check token matches exactly (no extra spaces)
3. Ensure `SERVICE_AUTH_ENABLED=true`
4. Check token prefix matches `SERVICE_TOKEN_PREFIX`

### Problem: 401 Invalid Token Format

```json
{
  "error": "invalid_token_format",
  "message": "Service token must start with 'st_dev_'"
}
```

**Solutions:**
1. Check token starts with correct prefix
2. Verify token format: `st_<env>_<40_hex_chars>`
3. Generate new token if corrupted

### Problem: Health Check Failing

**Issue:** `/health` endpoint returning 401

**Solution:** Health check should NOT require authentication. This is a bug if it does.

```python
# /health endpoint should remain public
@app.get("/health")
async def health_check():
    # NO authentication dependency here!
    ...
```

### Problem: Audit Trail Not Working

**Issue:** No audit records in Redis

**Solutions:**
1. Check Redis connection is working
2. Verify `audit_trail.set_redis_client()` was called
3. Check Redis logs for errors
4. Verify audit logging is enabled

### Debugging Tips

#### Enable Debug Logging

```bash
# Email Service .env
LOG_LEVEL=DEBUG
```

#### Check Configured Services

```python
from services.auth_service import authenticator

info = authenticator.get_service_info()
print(f"Enabled: {info['enabled']}")
print(f"Services: {info['services']}")
# Output:
# Enabled: True
# Services: ['main-app', 'user-service', 'notification']
```

#### Validate Token Format

```bash
python scripts/generate_service_token.py --validate st_dev_abc123...

# Output:
# ✓ Token is valid: st_dev_abc123...
```

---

## API Reference

### Protected Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/send` | POST | Send email |
| `/send/welcome` | POST | Send welcome email |
| `/send/password-reset` | POST | Send password reset |
| `/send/group-notification` | POST | Send group notification |
| `/stats` | GET | Get statistics |

### Public Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (no auth) |

### Request Header

```http
X-Service-Token: st_dev_abc123...
```

### Response Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Request completed |
| 401 | Unauthorized | Check token |
| 500 | Server Error | Check logs |

---

## Support & Resources

- **Integration Examples:** See `INTEGRATION_EXAMPLES.md`
- **Token Generator:** `scripts/generate_service_token.py`
- **Audit Queries:** See audit trail section above
- **Logs:** `docker-compose logs email-api`

---

**Last Updated:** 2025-11-08
**Version:** 1.0.0
**Maintained by:** FreeFace Engineering Team
