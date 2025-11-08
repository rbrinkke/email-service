# 🔍 FreeFace Email Service - Complete Debug Capabilities

## Overzicht

Dit document beschrijft de **volledige debug logging capabilities** die nu beschikbaar zijn in de FreeFace Email Service. Deze implementatie gaat ver voorbij basis logging en biedt de diepgaande inzichten die nodig zijn voor effectieve troubleshooting in productie.

**Laatste Update:** 2025-11-08
**Versie:** Enhanced Logging v2.0 (Fase 1 & 2 + Enhanced Debug)

---

## 🎯 Wat is er Nieuw? (Enhanced Debug)

Naast de **Fase 1 & 2** implementatie (Docker-native logging + dictConfig), hebben we nu:

### ✅ Debug Utilities Framework
- **Module:** `utils/debug_utils.py`
- **Capabilities:**
  - Function call logging met parameters
  - Automatic timing measurement
  - Context-aware logging
  - State change tracking
  - Redis operation logging
  - Provider operation logging

### ✅ Enhanced Service Layer Logging
- **Module:** `services/email_service.py`
- **Nieuwe Logs:**
  - Elk API call met parameters
  - Timing van elke operatie
  - Group expansion details
  - Queue assignment tracking
  - Job creation with full data structure
  - Worker management lifecycle

### ✅ Enhanced SMTP Provider Logging
- **Module:** `providers/smtp_provider.py`
- **Nieuwe Logs:**
  - Template loading and rendering
  - SMTP connection establishment
  - Authentication flow
  - Per-recipient send status
  - Detailed error information with stack traces
  - SMTP conversation logging

---

## 📋 Beschikbare Debug Logs per Component

### 1. **API Layer (api.py)**

**Startup:**
```
2025-11-08 12:00:00 - [config.logging_config] - INFO - Logging configured - Environment: development, Level: DEBUG
2025-11-08 12:00:01 - [api] - INFO - Email API service started
```

**Request Processing:**
```
2025-11-08 12:01:00 - [services.email_service] - DEBUG - send_email called: recipients=test@example.com, template=welcome, priority=high, provider=smtp, scheduled=False
2025-11-08 12:01:00 - [services.email_service] - DEBUG - ⏱ Starting: expand_recipients_test@example.com
2025-11-08 12:01:00 - [services.email_service] - DEBUG - Single recipient: test@example.com
2025-11-08 12:01:00 - [services.email_service] - DEBUG - ✓ expand_recipients_test@example.com completed in 0.001s
2025-11-08 12:01:00 - [services.email_service] - DEBUG - Recipients expanded to 1 email(s)
2025-11-08 12:01:00 - [services.email_service] - DEBUG - Email job created: abc123-def456
2025-11-08 12:01:00 - [services.email_service] - DEBUG - EmailJob abc123-def456:
{
  "job_id": "abc123-def456",
  "to": ["test@example.com"],
  "template": "welcome",
  "priority": "high",
  "provider": "smtp",
  "data": {"subject": "Welcome!", "name": "John"}
}
2025-11-08 12:01:00 - [services.email_service] - DEBUG - Queueing email abc123-def456 to high queue
2025-11-08 12:01:00 - [services.email_service] - DEBUG - ⏱ Starting: enqueue_high
2025-11-08 12:01:00 - [services.email_service] - DEBUG - ✓ enqueue_high completed in 0.003s
2025-11-08 12:01:00 - [services.email_service] - INFO - Email queued: abc123-def456, priority: high, recipients: 1
```

---

### 2. **Email Service Layer (services/email_service.py)**

**Initialization:**
```
2025-11-08 12:00:00 - [services.email_service] - DEBUG - EmailService initialized with config: redis=redis-email:6379
2025-11-08 12:00:00 - [services.email_service] - DEBUG - Initializing email service - connecting to Redis...
2025-11-08 12:00:00 - [services.email_service] - DEBUG - ⏱ Starting: redis_connection
2025-11-08 12:00:01 - [services.email_service] - DEBUG - ✓ redis_connection completed in 0.145s
2025-11-08 12:00:01 - [services.email_service] - INFO - Email service initialized and connected to Redis
2025-11-08 12:00:01 - [services.email_service] - DEBUG - Redis connection established: redis-email:6379
```

**Group Expansion (DEBUG):**
```
2025-11-08 12:01:00 - [services.email_service] - DEBUG - Expanding group: newsletter_subscribers
2025-11-08 12:01:00 - [services.email_service] - DEBUG - ⏱ Starting: redis_lrange_group_newsletter_subscribers
2025-11-08 12:01:00 - [services.email_service] - DEBUG - ✓ redis_lrange_group_newsletter_subscribers completed in 0.002s
2025-11-08 12:01:00 - [services.email_service] - DEBUG - Group newsletter_subscribers has 245 member(s)
2025-11-08 12:01:00 - [services.email_service] - DEBUG - ⏱ Starting: redis_lrange_excluded_newsletter_subscribers
2025-11-08 12:01:00 - [services.email_service] - DEBUG - ✓ redis_lrange_excluded_newsletter_subscribers completed in 0.001s
2025-11-08 12:01:00 - [services.email_service] - DEBUG - Group newsletter_subscribers has 3 excluded member(s)
2025-11-08 12:01:00 - [services.email_service] - DEBUG - After filtering: 242 recipient(s)
```

**Worker Management:**
```
2025-11-08 12:00:01 - [services.email_service] - INFO - Starting 3 email worker(s)...
2025-11-08 12:00:01 - [services.email_service] - DEBUG - Creating worker: worker_0
2025-11-08 12:00:01 - [services.email_service] - DEBUG - Worker task created for worker_0
2025-11-08 12:00:01 - [services.email_service] - INFO - Created worker task for worker_0
...
2025-11-08 12:00:01 - [services.email_service] - INFO - Started 3 email workers
2025-11-08 12:00:01 - [services.email_service] - DEBUG - Active workers: ['worker_0', 'worker_1', 'worker_2']
```

---

### 3. **SMTP Provider (providers/smtp_provider.py)**

**Provider Initialization:**
```
2025-11-08 12:00:00 - [providers.smtp_provider] - DEBUG - SMTP Provider initialized: host=mailhog, port=1025, use_tls=false
2025-11-08 12:00:00 - [providers.smtp_provider] - DEBUG - Loading email templates from: /opt/email/templates
2025-11-08 12:00:00 - [providers.smtp_provider] - INFO - SMTP Provider ready: mailhog:1025
```

**Email Processing (VERBOSE DEBUG):**
```
2025-11-08 12:01:01 - [providers.smtp_provider] - DEBUG - SMTP: Processing job abc123-def456 for 1 recipient(s)
2025-11-08 12:01:01 - [providers.smtp_provider] - DEBUG - SMTP: Email from=noreply@freeface.com, subject='Welcome to FreeFace!'
2025-11-08 12:01:01 - [providers.smtp_provider] - DEBUG - SMTP: Attempting to load template 'welcome.html'
2025-11-08 12:01:01 - [providers.smtp_provider] - DEBUG - ⏱ Starting: template_render_welcome
2025-11-08 12:01:01 - [providers.smtp_provider] - DEBUG - SMTP: Template 'welcome.html' loaded successfully
2025-11-08 12:01:01 - [providers.smtp_provider] - DEBUG - SMTP: Rendering template with 2 data key(s)
2025-11-08 12:01:01 - [providers.smtp_provider] - DEBUG - SMTP: Template rendered successfully, content length: 1245 chars
2025-11-08 12:01:01 - [providers.smtp_provider] - DEBUG - ✓ template_render_welcome completed in 0.012s
2025-11-08 12:01:01 - [providers.smtp_provider] - DEBUG - SMTP: MIME message constructed
2025-11-08 12:01:01 - [providers.smtp_provider] - DEBUG - SMTP: Connecting to mailhog:1025 (TLS=False)
2025-11-08 12:01:01 - [providers.smtp_provider] - DEBUG - Provider [smtp] connect: host='mailhog', port='1025', use_tls=False, recipients=1
2025-11-08 12:01:01 - [providers.smtp_provider] - DEBUG - ⏱ Starting: smtp_send_job_abc123-def456
2025-11-08 12:01:01 - [providers.smtp_provider] - DEBUG - SMTP: Connection established
2025-11-08 12:01:01 - [providers.smtp_provider] - DEBUG - SMTP: Skipping authentication (localhost/debug server)
2025-11-08 12:01:01 - [providers.smtp_provider] - DEBUG - SMTP: Sending to test@example.com
2025-11-08 12:01:01 - [providers.smtp_provider] - DEBUG - ⏱ Starting: smtp_send_to_test@example.com
2025-11-08 12:01:02 - [providers.smtp_provider] - DEBUG - ✓ smtp_send_to_test@example.com completed in 0.145s
2025-11-08 12:01:02 - [providers.smtp_provider] - DEBUG - SMTP: Successfully sent to test@example.com (1/1)
2025-11-08 12:01:02 - [providers.smtp_provider] - DEBUG - ✓ smtp_send_job_abc123-def456 completed in 0.156s
2025-11-08 12:01:02 - [providers.smtp_provider] - INFO - SMTP: Job abc123-def456 sent successfully to 1 recipient(s)
2025-11-08 12:01:02 - [providers.smtp_provider] - DEBUG - Provider [smtp] send_complete: job_id='abc123-def456', recipients_sent=1, template='welcome'
```

**Template Errors (WARNING with fallback):**
```
2025-11-08 12:01:00 - [providers.smtp_provider] - WARNING - SMTP: Template 'nonexistent.html' not found or render error: TemplateNotFound: nonexistent.html. Using fallback HTML.
2025-11-08 12:01:00 - [providers.smtp_provider] - DEBUG - SMTP: Fallback HTML created, length: 87 chars
```

**SMTP Errors (with stack trace):**
```
2025-11-08 12:01:00 - [providers.smtp_provider] - ERROR - SMTP error for job abc123: SMTPConnectError: Could not connect to mailhog:1025
Traceback (most recent call last):
  File "/opt/email/providers/smtp_provider.py", line 115, in _send_email_impl
    async with aiosmtplib.SMTP(...) as smtp:
  ...
aiosmtplib.errors.SMTPConnectError: Could not connect to mailhog:1025
2025-11-08 12:01:00 - [providers.smtp_provider] - DEBUG - Provider [smtp] send_failed: job_id='abc123', error_type='SMTPConnectError', error='Could not connect to mailhog:1025'
```

---

### 4. **Worker Processes (workers/email_worker.py)**

**Worker Lifecycle:**
```
2025-11-08 12:00:01 - [workers.email_worker] - INFO - Initializing providers for worker worker_0
2025-11-08 12:00:01 - [workers.email_worker] - INFO - Email worker worker_0 started, creating tasks...
2025-11-08 12:00:01 - [workers.email_worker] - INFO - Worker worker_0 created 3 tasks, starting main loop
```

**Job Processing:**
```
2025-11-08 12:01:01 - [workers.email_worker] - INFO - Email sent successfully: abc123-def456
```

**Stats Reporting (every minute):**
```
2025-11-08 12:02:00 - [workers.email_worker] - INFO - Worker worker_0 stats: processed=15, sent=14, failed=1, rate=0.25/sec
```

---

## 🛠️ Debug Utilities API

### 1. **log_timing(operation_name, logger)**

Automatically measures and logs execution time:

```python
from utils.debug_utils import log_timing

with log_timing("database_query", logger):
    result = await db.query(...)

# Logs:
# DEBUG: ⏱ Starting: database_query
# DEBUG: ✓ database_query completed in 0.045s
```

### 2. **debug_context(context_name, context_data, logger)**

Logs entry/exit of code blocks with context:

```python
from utils.debug_utils import debug_context

with debug_context("email_processing", {"job_id": job.job_id, "priority": "high"}):
    await process_email(job)

# Logs:
# DEBUG: ▼ Entering email_processing: job_id='abc123', priority='high'
# DEBUG: ▲ Exiting email_processing: SUCCESS
```

### 3. **log_state_change(logger, entity, old_state, new_state, context)**

Tracks state transitions:

```python
from utils.debug_utils import log_state_change

log_state_change(logger, "job", "pending", "processing", {"job_id": job.job_id})

# Logs:
# DEBUG: State change: job pending → processing [job_id='abc123']
```

### 4. **log_data_structure(logger, name, data)**

Pretty-prints complex data structures:

```python
from utils.debug_utils import log_data_structure

log_data_structure(logger, "email_job", job.dict())

# Logs formatted JSON of the entire data structure
```

### 5. **log_provider_operation(logger, provider, operation, details)**

Tracks provider operations:

```python
from utils.debug_utils import log_provider_operation

log_provider_operation(logger, "smtp", "connect", {"host": "smtp.gmail.com", "port": 587})

# Logs:
# DEBUG: Provider [smtp] connect: host='smtp.gmail.com', port='587'
```

### 6. **log_redis_operation(logger, operation, key, details)**

Tracks Redis operations:

```python
from utils.debug_utils import log_redis_operation

log_redis_operation(logger, "XADD", "email:queue:high", {"job_id": job.job_id})

# Logs:
# DEBUG: Redis XADD: email:queue:high job_id='abc123'
```

---

## 🔐 Security: Automatic Sensitive Data Sanitization

Alle debug utilities **sanitizen automatisch** gevoelige data:

**Gevoelige velden die worden geredacteerd:**
- `password`
- `api_key`
- `secret`
- `token`
- `credential`
- `auth`

**Voorbeeld:**
```python
log_data_structure(logger, "config", {
    "host": "smtp.gmail.com",
    "password": "SuperSecret123",
    "api_key": "sk_live_abc123"
})

# Logs:
# config:
# {
#   "host": "smtp.gmail.com",
#   "password": "***REDACTED***",
#   "api_key": "***REDACTED***"
# }
```

---

## 📊 Complete Debug Flow Voorbeeld

Wanneer je een email verstuurt met `LOG_LEVEL=DEBUG`, zie je **exact** deze flow:

```
1. API Request arrives
   └─ [services.email_service] DEBUG: send_email called: recipients=test@example.com, template=welcome, ...

2. Recipients expanded
   └─ [services.email_service] DEBUG: Starting: expand_recipients
   └─ [services.email_service] DEBUG: Single recipient: test@example.com
   └─ [services.email_service] DEBUG: Completed in 0.001s

3. Job created
   └─ [services.email_service] DEBUG: Email job created: abc123
   └─ [services.email_service] DEBUG: EmailJob abc123: {full JSON}

4. Job queued
   └─ [services.email_service] DEBUG: Queueing email abc123 to high queue
   └─ [services.email_service] DEBUG: Starting: enqueue_high
   └─ [services.email_service] DEBUG: Completed in 0.003s
   └─ [services.email_service] INFO: Email queued: abc123, priority: high, recipients: 1

5. Worker picks up job
   └─ [workers.email_worker] INFO: Email sent successfully: abc123

6. SMTP Provider processes
   └─ [providers.smtp_provider] DEBUG: SMTP: Processing job abc123 for 1 recipient(s)
   └─ [providers.smtp_provider] DEBUG: SMTP: Attempting to load template 'welcome.html'
   └─ [providers.smtp_provider] DEBUG: Starting: template_render_welcome
   └─ [providers.smtp_provider] DEBUG: Template loaded successfully
   └─ [providers.smtp_provider] DEBUG: Completed in 0.012s
   └─ [providers.smtp_provider] DEBUG: SMTP: Connecting to mailhog:1025
   └─ [providers.smtp_provider] DEBUG: Provider [smtp] connect: host='mailhog', port='1025'
   └─ [providers.smtp_provider] DEBUG: Starting: smtp_send_job_abc123
   └─ [providers.smtp_provider] DEBUG: SMTP: Connection established
   └─ [providers.smtp_provider] DEBUG: SMTP: Sending to test@example.com
   └─ [providers.smtp_provider] DEBUG: Starting: smtp_send_to_test@example.com
   └─ [providers.smtp_provider] DEBUG: Completed in 0.145s
   └─ [providers.smtp_provider] DEBUG: SMTP: Successfully sent to test@example.com (1/1)
   └─ [providers.smtp_provider] DEBUG: Completed in 0.156s
   └─ [providers.smtp_provider] INFO: SMTP: Job abc123 sent successfully to 1 recipient(s)
   └─ [providers.smtp_provider] DEBUG: Provider [smtp] send_complete: job_id='abc123', recipients_sent=1
```

**Dit geeft je:**
- ✅ Exacte timing van elke stap
- ✅ Alle parameters en data
- ✅ Template loading en rendering details
- ✅ SMTP connection en authentication flow
- ✅ Per-recipient send status
- ✅ Total processing time

**Alles wat je nodig hebt om problemen te diagnosticeren!**

---

## 🎯 Gebruik Scenarios

### Scenario 1: "Email komt niet aan"

**Set:** `LOG_LEVEL=DEBUG`

**Check logs voor:**
1. ✅ Job creation: `Email job created: {job_id}`
2. ✅ Queueing: `Email queued: {job_id}, priority: high`
3. ✅ Worker pickup: `Email sent successfully: {job_id}`
4. ✅ SMTP details: `SMTP: Successfully sent to {email}`

**Als email NIET aankomt maar logs tonen SUCCESS:**
→ Check MailHog/SMTP server logs, niet email service

**Als logs stoppen bij queueing:**
→ Workers draaien niet of Redis connection issue

### Scenario 2: "Emails zijn traag"

**Set:** `LOG_LEVEL=DEBUG`

**Check timing logs:**
```
⏱ Starting: template_render_welcome
✓ template_render_welcome completed in 0.012s  ← Snel!

⏱ Starting: smtp_send_job_abc123
✓ smtp_send_job_abc123 completed in 2.456s  ← TRAAG!
```

**Diagnose:** SMTP server is traag, niet de applicatie

### Scenario 3: "Template rendering fails"

**Set:** `LOG_LEVEL=DEBUG`

**Check:**
```
WARNING - SMTP: Template 'mytemplate.html' not found or render error: TemplateNotFound
DEBUG - SMTP: Fallback HTML created
```

**Diagnose:** Template bestand ontbreekt of heeft syntax error

### Scenario 4: "Group expansion werkt niet"

**Set:** `LOG_LEVEL=DEBUG`

**Check:**
```
DEBUG - Expanding group: newsletter_subscribers
DEBUG - Group newsletter_subscribers has 0 member(s)  ← PROBLEEM!
```

**Diagnose:** Redis key `group:newsletter_subscribers:emails` is leeg

---

## 📈 Performance Impact

**LOG_LEVEL=DEBUG:**
- Extra CPU: ~2-5% (logging overhead)
- Extra memory: ~10-20 MB (log buffers)
- Log volume: ~500-1000 lines/min per worker

**Production Recommendation:**
- Normal: `LOG_LEVEL=INFO`
- Troubleshooting: `LOG_LEVEL=DEBUG` (tijdelijk)
- High-traffic: `LOG_LEVEL=WARNING`

---

## 🚀 Quick Start

### Enable Full Debug Logging

```bash
# In .env
LOG_LEVEL=DEBUG
ENVIRONMENT=development

# Rebuild and start
docker-compose down
docker-compose build
docker-compose up
```

### View Logs

```bash
# All services with timestamps
docker-compose logs -f --timestamps

# Specific service
docker logs -f freeface-email-api

# Follow only DEBUG logs
docker logs -f freeface-email-api 2>&1 | grep DEBUG

# Follow SMTP provider logs
docker logs -f freeface-email-worker-1 2>&1 | grep "SMTP:"
```

### Test Email Send

```bash
curl -X POST http://localhost:8010/send \
  -H "Content-Type: application/json" \
  -d '{
    "recipients": "test@example.com",
    "template": "welcome",
    "data": {
      "subject": "Test Email",
      "name": "John Doe"
    },
    "priority": "high"
  }'
```

**Check logs** - Je ziet de complete flow!

---

## 📝 Summary

**Wat hebben we nu?**

✅ **Fase 1 & 2:** Docker-native logging + dictConfig
✅ **Enhanced Debug:** Utilities framework voor diepgaande debugging
✅ **Service Layer:** Volledige request/response/timing logging
✅ **SMTP Provider:** Complete conversation logging
✅ **Automatic:** Timing measurement voor alle operaties
✅ **Security:** Automatic sanitization van gevoelige data
✅ **Production-Ready:** Minimal overhead, maximum insight

**Voor de programmeur:**

Je krijgt **exact** de informatie die je nodig hebt om:
- 🔍 Trace een email van API call tot delivery
- ⏱️ Identify performance bottlenecks
- 🐛 Debug template rendering issues
- 🔌 Troubleshoot SMTP connection problems
- 📊 Monitor queue operations
- 🚨 Diagnose failures with full context

**Dit is wat echte debugging moet zijn!** 🎯

---

*Voor implementatie details, zie:*
- `LOGGING_GUIDE.md` - Basis logging configuratie
- `CHANGELOG_LOGGING.md` - Volledige changelog
- `utils/debug_utils.py` - Debug utilities source code
