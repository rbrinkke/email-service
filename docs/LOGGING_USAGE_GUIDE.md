# 📖 Logging Usage Guide - Practical Examples

## 🎯 Quick Reference

```python
# Import
from config.structured_logging import get_logger
logger = get_logger(__name__)

# Basic logging
logger.info("user_registered", user_id=123, email="user@example.com")
logger.warning("rate_limit_reached", service="smtp", limit=100)
logger.error("email_failed", job_id="job_123", error="Connection timeout", exc_info=True)

# With timing
from utils.debug_utils import log_timing
with log_timing("database_query", logger):
    result = await db.query(...)
```

---

## 📋 Common Logging Patterns

### 1. **Service Operations**

```python
# services/email_service.py
import structlog
from config.structured_logging import get_logger

logger = get_logger(__name__)

async def send_email(self, recipients, template, **kwargs):
    """Send email with comprehensive logging"""

    # Log operation start
    logger.info(
        "email_send_started",
        recipients=len(recipients) if isinstance(recipients, list) else 1,
        template=template,
        priority=kwargs.get('priority', 'medium')
    )

    try:
        # Perform operation
        with log_timing(f"send_email_{template}", logger):
            job_id = await self._send_email_impl(...)

        # Log success
        logger.info(
            "email_send_success",
            job_id=job_id,
            recipients=len(recipients),
            template=template
        )

        return job_id

    except Exception as e:
        # Log failure with FULL context
        logger.error(
            "email_send_failed",
            template=template,
            recipients=len(recipients),
            error_type=type(e).__name__,
            error=str(e),
            exc_info=True  # Include stack trace!
        )
        raise
```

---

### 2. **API Endpoint Logging**

```python
# api.py
from config.structured_logging import get_logger

logger = get_logger(__name__)
struct_logger = get_logger(__name__)  # Can use same name

@app.post("/send")
async def send_email(
    request: EmailRequest,
    service: ServiceIdentity = Depends(verify_service_token)
):
    """Send email endpoint with structured logging"""

    # Access logging is AUTOMATIC via middleware
    # But you can add business logic logging:

    logger.info(
        "email_request_received",
        service_name=service.name,
        template=request.template,
        priority=request.priority.value,
        recipient_count=len(request.recipients) if isinstance(request.recipients, list) else 1
    )

    try:
        job_id = await email_service.send_email(...)

        # Log business event
        struct_logger.info(
            "email_queued_successfully",
            job_id=job_id,
            service_name=service.name,
            template=request.template
        )

        return EmailResponse(job_id=job_id, status="queued")

    except RateLimitError as e:
        # Specific error handling
        logger.warning(
            "rate_limit_exceeded",
            service_name=service.name,
            limit=e.limit,
            current=e.current
        )
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    except Exception as e:
        # Generic error handling
        logger.error(
            "email_request_failed",
            service_name=service.name,
            template=request.template,
            error_type=type(e).__name__,
            error=str(e),
            exc_info=True
        )

        struct_logger.error(
            "email_request_exception",
            service_name=service.name,
            error_type=type(e).__name__,
            exc_info=True
        )

        raise HTTPException(status_code=500, detail=str(e)) from e
```

---

### 3. **Worker Processing**

```python
# workers/email_worker.py
from config.structured_logging import get_logger
from utils.debug_utils import log_timing, debug_context

logger = get_logger(__name__)

async def process_email(self, job: EmailJob):
    """Process email job with detailed logging"""

    # Use debug context for automatic field injection
    with debug_context(
        "email_processing",
        {"job_id": job.job_id, "worker_id": self.worker_id},
        logger
    ):
        logger.info(
            "processing_email_job",
            job_id=job.job_id,
            priority=job.priority.value,
            recipients=len(job.to),
            template=job.template,
            provider=job.provider.value
        )

        try:
            # Rate limiting check
            with log_timing(f"rate_limit_check_{job.provider}", logger):
                can_send = await self.check_rate_limit(job.provider)

            if not can_send:
                logger.warning(
                    "rate_limit_hit",
                    job_id=job.job_id,
                    provider=job.provider.value
                )
                return False

            # Send via provider
            with log_timing(f"provider_send_{job.provider}", logger):
                success = await self.provider.send(job)

            if success:
                logger.info(
                    "email_sent_successfully",
                    job_id=job.job_id,
                    provider=job.provider.value,
                    recipients=len(job.to)
                )
                self.stats["sent"] += 1
            else:
                logger.warning(
                    "email_send_failed",
                    job_id=job.job_id,
                    provider=job.provider.value
                )
                self.stats["failed"] += 1

            return success

        except SMTPException as e:
            # Provider-specific errors
            logger.error(
                "smtp_error",
                job_id=job.job_id,
                error_code=e.smtp_code,
                error_message=e.smtp_error,
                exc_info=True
            )
            raise

        except Exception as e:
            # Unexpected errors
            logger.error(
                "unexpected_error_processing_email",
                job_id=job.job_id,
                worker_id=self.worker_id,
                error_type=type(e).__name__,
                error=str(e),
                exc_info=True
            )
            raise
```

---

### 4. **Provider Operations**

```python
# providers/smtp_provider.py
from config.structured_logging import get_logger
from utils.debug_utils import log_provider_operation, log_timing

logger = get_logger(__name__)

async def send_email(self, job: EmailJob) -> bool:
    """Send email via SMTP with detailed logging"""

    logger.debug(
        "smtp_send_started",
        job_id=job.job_id,
        recipients=len(job.to),
        template=job.template,
        host=self.config['host'],
        port=self.config['port']
    )

    try:
        # Template rendering
        with log_timing(f"template_render_{job.template}", logger):
            html_content = await self.render_template(job.template, job.data)

        logger.debug(
            "template_rendered",
            job_id=job.job_id,
            template=job.template,
            content_size=len(html_content)
        )

        # SMTP connection
        log_provider_operation(
            logger,
            "smtp",
            "connect",
            {
                "host": self.config['host'],
                "port": self.config['port'],
                "use_tls": self.config.get('use_tls', True)
            }
        )

        with log_timing(f"smtp_send_{job.job_id}", logger):
            async with aiosmtplib.SMTP(
                hostname=self.config['host'],
                port=self.config['port']
            ) as smtp:
                # Send to each recipient
                for email in job.to:
                    logger.debug("sending_to_recipient", job_id=job.job_id, recipient=email)
                    await smtp.send_message(message)

        # Success
        logger.info(
            "smtp_send_complete",
            job_id=job.job_id,
            recipients_sent=len(job.to),
            template=job.template
        )

        log_provider_operation(
            logger,
            "smtp",
            "send_complete",
            {
                "job_id": job.job_id,
                "recipients_sent": len(job.to)
            }
        )

        return True

    except aiosmtplib.SMTPException as e:
        # SMTP-specific error
        logger.error(
            "smtp_error",
            job_id=job.job_id,
            error_type=type(e).__name__,
            smtp_code=getattr(e, 'smtp_code', None),
            smtp_error=getattr(e, 'smtp_error', None),
            error=str(e),
            exc_info=True
        )

        log_provider_operation(
            logger,
            "smtp",
            "send_failed",
            {
                "job_id": job.job_id,
                "error_type": type(e).__name__,
                "error": str(e)
            }
        )

        return False

    except Exception as e:
        # General error
        logger.error(
            "smtp_unexpected_error",
            job_id=job.job_id,
            error_type=type(e).__name__,
            error=str(e),
            exc_info=True
        )
        return False
```

---

### 5. **Redis Operations**

```python
# redis_client_lib/redis_client.py
from config.structured_logging import get_logger
from utils.debug_utils import log_redis_operation, log_timing

logger = get_logger(__name__)

async def enqueue_email(self, job: EmailJob) -> str:
    """Enqueue email with Redis operation logging"""

    stream_key = f"email:queue:{job.priority.value}"

    logger.debug(
        "enqueue_email_started",
        job_id=job.job_id,
        priority=job.priority.value,
        stream_key=stream_key
    )

    # Log Redis operation
    log_redis_operation(
        logger,
        "XADD",
        stream_key,
        {"job_id": job.job_id}
    )

    try:
        with log_timing("redis_xadd", logger):
            stream_id = await self.redis.xadd(
                stream_key,
                {"job": job.json()}
            )

        logger.info(
            "email_enqueued",
            job_id=job.job_id,
            stream_id=stream_id,
            priority=job.priority.value
        )

        return stream_id

    except redis.RedisError as e:
        logger.error(
            "redis_enqueue_failed",
            job_id=job.job_id,
            stream_key=stream_key,
            error_type=type(e).__name__,
            error=str(e),
            exc_info=True
        )
        raise
```

---

### 6. **State Changes**

```python
from utils.debug_utils import log_state_change

# Log status transitions
old_status = job.status
job.status = EmailStatus.SENDING

log_state_change(
    logger,
    "job_status",
    old_status.value,
    job.status.value,
    {"job_id": job.job_id}
)

# Output: "State change: job_status QUEUED → SENDING [job_id=job_123]"
```

---

### 7. **Performance Monitoring**

```python
from utils.debug_utils import log_timing

# Timing critical operations
with log_timing("database_query", logger):
    results = await db.query(...)

with log_timing("external_api_call", logger):
    response = await httpx.get(...)

# Automatic slow operation warnings
# If > 1 second: logs WARNING automatically
```

---

## 🔍 Debugging Scenarios

### Scenario 1: Trace a Single Request

**Problem**: User reports email not received.

**Solution**:
```bash
# 1. Get request_id from API response or logs
request_id="abc-123-def-456"

# 2. Filter all logs for this request
docker logs freeface-email-api | grep "$request_id"

# Output shows complete flow:
# - API received request
# - Email queued
# - Worker picked up job
# - SMTP sent email
# - Success/failure
```

**With structured logs (JSON)**:
```bash
# Datadog query
request_id:abc-123-def-456

# CloudWatch Insights
fields @timestamp, event, level
| filter request_id = "abc-123-def-456"
| sort @timestamp asc
```

---

### Scenario 2: Find Slow Operations

```bash
# Find all slow requests
docker logs freeface-email-api | grep "SLOW"

# With structured logs
# Filter: duration_ms > 1000
```

```python
# In code: Automatic detection
if duration_ms > 1000:
    logger.warning(
        "SLOW OPERATION",
        operation="send_email",
        duration_ms=duration_ms,
        job_id=job.job_id
    )
```

---

### Scenario 3: Debug Provider Issues

```bash
# All SMTP errors
docker logs freeface-email-api | grep "smtp_error"

# Specific job
docker logs freeface-email-api | grep "job_123"
```

**Logs show**:
```json
{
  "event": "smtp_error",
  "job_id": "job_123",
  "error_type": "SMTPAuthenticationError",
  "smtp_code": 535,
  "smtp_error": "Authentication failed",
  "traceback": "..."
}
```

---

### Scenario 4: Monitor Service Usage

```bash
# Which services are calling us?
docker logs freeface-email-api | grep "service_name" | sort | uniq -c

# Service-specific logs
docker logs freeface-email-api | grep "service_name=main-app"
```

---

## 🎚️ Environment Variables

### Production

```bash
# .env.production
ENVIRONMENT=production
LOG_LEVEL=INFO  # Less verbose
LOG_FORMAT=json  # Structured output

# Silence third-party noise
LOGGER_LEVEL_REDIS=WARNING
LOGGER_LEVEL_HTTPX=WARNING
LOGGER_LEVEL_ASYNCIO=ERROR
```

### Development

```bash
# .env.development
ENVIRONMENT=development
LOG_LEVEL=DEBUG  # Verbose
LOG_FORMAT=console  # Pretty output

# Enable request body logging (DEBUG ONLY!)
# Handled automatically by middleware based on ENVIRONMENT
```

### Debugging Specific Component

```bash
# Debug only email service
LOGGER_LEVEL_SERVICES_EMAIL_SERVICE=DEBUG
LOGGER_LEVEL_SERVICES_FREEFACE_INTEGRATION=DEBUG

# Debug only SMTP provider
LOGGER_LEVEL_PROVIDERS_SMTP_PROVIDER=DEBUG
```

---

## 🚨 Alert Examples

### Datadog Alerts

```javascript
// High error rate
count:logs{service:email-api level:error} > 10

// Slow requests
avg:duration_ms{service:email-api} > 1000

// Uncaught exceptions
count:logs{service:email-api event:"UNCAUGHT EXCEPTION"} > 0

// Health check failures
count:logs{service:email-api event:health_check_failed} > 0
```

### CloudWatch Alarms

```sql
-- Error rate alarm
fields @timestamp
| filter level = "error"
| stats count() as error_count by bin(5m)
| filter error_count > 10

-- Slow request alarm
fields @timestamp, duration_ms
| filter duration_ms > 1000
| stats count() as slow_count by bin(5m)
```

---

## ✅ Logging Checklist

Gebruik deze checklist bij het schrijven van nieuwe code:

### ✅ For Every Function/Method:
- [ ] Import logger: `logger = get_logger(__name__)`
- [ ] Log function entry (DEBUG): `logger.debug("function_started", param1=value1)`
- [ ] Log function success (INFO): `logger.info("function_completed", result=...)`
- [ ] Log function errors (ERROR): `logger.error(..., exc_info=True)`

### ✅ For API Endpoints:
- [ ] Middleware handles access logging (automatic)
- [ ] Log business events (INFO): `logger.info("user_registered", ...)`
- [ ] Log errors with context (ERROR + exc_info=True)
- [ ] Include service_name in logs

### ✅ For Workers:
- [ ] Log job start (INFO): `logger.info("processing_job", job_id=...)`
- [ ] Log job completion (INFO): `logger.info("job_completed", ...)`
- [ ] Log job failure (ERROR): `logger.error(..., exc_info=True)`
- [ ] Log performance metrics (duration, throughput)

### ✅ For Providers:
- [ ] Log provider operations (DEBUG): `log_provider_operation(...)`
- [ ] Log connection events (INFO)
- [ ] Log send success/failure (INFO/ERROR)
- [ ] Log provider-specific errors with codes

### ✅ For Redis Operations:
- [ ] Log Redis operations (DEBUG): `log_redis_operation(...)`
- [ ] Log Redis errors (ERROR + exc_info=True)
- [ ] Use timing for slow operations

---

## 📊 Example Log Output

### JSON (Production)

```json
{
  "event": "email_send_success",
  "job_id": "job_abc123",
  "recipients": 5,
  "template": "welcome",
  "duration_ms": 145.2,
  "provider": "smtp",
  "request_id": "req_xyz789",
  "service_name": "main-app",
  "timestamp": "2025-11-10T14:30:00.123Z",
  "level": "info",
  "logger": "services.email_service"
}
```

### Console (Development)

```
2025-11-10 14:30:00 [info     ] email_send_success    job_id=job_abc123 recipients=5 template=welcome duration_ms=145.2 provider=smtp request_id=req_xyz789 service_name=main-app
```

---

## 🎓 Summary

**Key Takeaways**:

1. **Always use structured logging**: `logger.info("event_name", field=value)`
2. **Always include exc_info=True** for exceptions
3. **Use timing utilities** for performance monitoring
4. **Log with context**: request_id, job_id, service_name
5. **Use appropriate log levels**: DEBUG < INFO < WARNING < ERROR
6. **Filter third-party noise** in production

**Result**: **Production-grade observability** that makes debugging **10x faster**! 🚀
