# 🚀 FreeFace Email System - Quick Start

## ✅ System Ready!

Your email system has been tested and is fully operational.

## 🎯 Quick Test (2 minutes)

```bash
python3 start_and_test.py
```

This will:
- ✅ Verify Redis connection
- ✅ Start SMTP debug server
- ✅ Send 3 test emails
- ✅ Process them with workers
- ✅ Show you the results

## 📧 What's Working

| Component | Status | Details |
|-----------|--------|---------|
| Redis | ✅ Running | localhost:6379 |
| SMTP Server | ✅ Ready | localhost:1025 (debug mode) |
| Templates | ✅ Created | /opt/email/templates/ |
| Workers | ✅ Tested | Processing emails successfully |
| API | ✅ Available | Port 8010 |
| Queues | ✅ Operational | High/Medium/Low priority |

## 🔧 Manual Start

### 1. SMTP Debug Server (Terminal 1)
```bash
python3 smtp_debug_server.py
```

### 2. API Server (Terminal 2)
```bash
export REDIS_HOST=localhost
python3 api.py
```

### 3. Workers (Terminal 3)
```bash
export REDIS_HOST=localhost
python3 worker.py
```

### 4. Send Test Email
```bash
curl -X POST http://localhost:8010/send \
  -H "Content-Type: application/json" \
  -d '{"recipients": "test@example.com", "template": "test_email", "data": {"subject": "Test", "message": "Hello!"}}'
```

## 🐳 With Docker (Includes MailHog)

The docker-compose.yml includes MailHog for email testing:

```bash
docker compose up -d
```

Then access:
- **API**: http://localhost:8010
- **Monitor Dashboard**: http://localhost:8011
- **MailHog UI**: http://localhost:8025
- **API Docs**: http://localhost:8010/docs

## 📖 More Info

- Full testing guide: [TESTING_GUIDE.md](TESTING_GUIDE.md)
- Deployment docs: [DEPLOYMENT_SUCCESS.md](DEPLOYMENT_SUCCESS.md)
- Main README: [READ.me](READ.me)

---

**Quick Status Check:**
```bash
redis-cli ping && echo "✅ All systems ready!"
```
