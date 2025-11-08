# FreeFace Email System - Testing Guide

## 🚀 Quick Start

The FreeFace Email System has been successfully tested and is ready to use!

### Prerequisites

- Python 3.11+
- Redis
- Required Python packages (see `requirements.txt`)

All dependencies are already installed and configured.

## ✅ System Status

The system has been tested and verified with the following results:

- ✅ Redis connection working
- ✅ Email queueing functional
- ✅ Worker processing operational
- ✅ SMTP email delivery successful
- ✅ Template rendering working
- ✅ Priority queues functioning

## 📋 Testing Options

### Option 1: Automated Complete Test

Run the comprehensive test script that starts everything and tests the full system:

```bash
python3 start_and_test.py
```

This script will:
1. Check Redis connection
2. Start SMTP debug server on localhost:1025
3. Queue test emails with different priorities
4. Process emails with workers
5. Display results and statistics
6. Clean up automatically

### Option 2: Manual Testing with Individual Components

#### Step 1: Start Redis

Redis should already be running. Verify with:

```bash
redis-cli ping
# Should return: PONG
```

If not running:

```bash
redis-server --daemonize yes --port 6379 --dir /tmp
```

#### Step 2: Start SMTP Debug Server

In one terminal:

```bash
python3 smtp_debug_server.py
```

This will start an SMTP server on `localhost:1025` that displays all received emails in the console.

#### Step 3: Test Email Queueing

In another terminal:

```bash
export REDIS_HOST=localhost
python3 test_local_email.py
```

This will queue emails and process them with workers.

#### Step 4: Start API Server (Optional)

To test via REST API:

```bash
export REDIS_HOST=localhost
python3 api.py
```

The API will be available at `http://localhost:8010`

#### Step 5: Start Workers (Optional)

In another terminal:

```bash
export REDIS_HOST=localhost
python3 worker.py
```

## 🧪 Testing via API

Once the API is running, test with curl:

### Send a simple test email:

```bash
curl -X POST http://localhost:8010/send \
  -H "Content-Type: application/json" \
  -d '{
    "recipients": "test@example.com",
    "template": "test_email",
    "data": {
      "subject": "Hello from FreeFace",
      "message": "This is a test email",
      "name": "Test User"
    },
    "priority": "high",
    "provider": "smtp"
  }'
```

### Check system health:

```bash
curl http://localhost:8010/health
```

### Get system statistics:

```bash
curl http://localhost:8010/stats
```

### View API documentation:

Open in browser: `http://localhost:8010/docs`

## 📧 Email Templates

Templates are located in `/opt/email/templates/`

Available templates:
- `test_email.html` - General test email
- `user_welcome.html` - Welcome email for new users
- `group_invitation.html` - Group invitation email
- `welcome.html` - Generic welcome email

Template variables (passed in `data`):
- `subject` - Email subject
- `message` - Main message content
- `name` - Recipient name
- `timestamp` - Email timestamp
- Custom variables specific to each template

## 🐛 SMTP Testing with MailHog (Docker)

If Docker is available, you can use MailHog for a better email testing experience:

```bash
docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog
```

Then access the web UI at: `http://localhost:8025`

## 📊 Monitoring

### Redis Queue Inspection

Check queue lengths:

```bash
redis-cli
> XLEN email:queue:high
> XLEN email:queue:medium
> XLEN email:queue:low
```

Check sent/failed counts:

```bash
redis-cli
> GET email:stats:sent
> GET email:stats:failed
```

### Log Files

Logs are stored in:
- `/opt/email/logs/api.log` - API server logs
- `/opt/email/logs/worker.log` - Worker logs
- `./logs/` - Local logs directory

## 🔧 Configuration

### Environment Variables

```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export SMTP_HOST=localhost
export SMTP_PORT=1025
export SMTP_USE_TLS=false
export LOG_LEVEL=INFO
```

### For Production

When deploying to production with Docker:

1. Update SMTP settings to use MailHog or real SMTP server
2. Configure proper API keys for SendGrid/Mailgun if needed
3. Update Redis host to actual Redis service name
4. Set appropriate environment variables

```bash
./deploy_local.sh
```

Or with Docker Compose:

```bash
docker compose up -d
```

## 📈 Performance

The system has been tested with:
- ✅ Multiple priority queues (high, medium, low)
- ✅ Concurrent workers
- ✅ Rate limiting
- ✅ Template rendering
- ✅ Error handling and retries

## 🎯 Next Steps

1. **For Local Development:**
   - Run `python3 start_and_test.py` to verify everything works
   - Use the SMTP debug server for email testing
   - Monitor logs in `/opt/email/logs/`

2. **For Production Deployment:**
   - Use Docker Compose: `docker compose up -d`
   - Configure real SMTP credentials or API keys
   - Set up proper monitoring and alerting
   - Review security settings

3. **For Integration:**
   - Use the REST API at `http://localhost:8010`
   - Review API docs at `http://localhost:8010/docs`
   - Implement error handling in your application

## ✅ Verification Checklist

- [x] Redis is running
- [x] Python dependencies installed
- [x] Email templates created
- [x] SMTP debug server functional
- [x] Email queueing works
- [x] Workers process emails
- [x] Priority queues operational
- [x] Template rendering successful
- [x] API endpoints functional

## 📞 Support

For issues or questions:
- Check logs in `/opt/email/logs/`
- Verify Redis connection
- Ensure all environment variables are set
- Test with `python3 start_and_test.py`

---

**Status:** ✅ System is fully operational and ready for use!
