# File: api.py
# FastAPI Email Service API

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Union

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, EmailStr

from config.logging_config import setup_logging
from config.structured_logging import setup_structured_logging, get_logger as get_struct_logger
from email_system import EmailConfig, EmailPriority, EmailProvider, EmailService
from middleware import (
    AccessLoggingMiddleware,
    ExceptionHandlerMiddleware,
    RequestIDMiddleware,
    PrometheusMetricsMiddleware,
    record_email_queued,
    get_metrics,
    get_metrics_content_type,
)
from services.audit_service import audit_trail
from services.auth_service import ServiceIdentity, authenticator

# Configure logging using centralized configuration
# This sets up Docker-compatible logging (stdout/stderr only)
# Respects LOG_LEVEL, ENVIRONMENT, and other logging env vars
setup_logging()

# Setup structured logging (JSON in production, pretty console in development)
# This is CRITICAL for production observability and debugging
setup_structured_logging()

# Get loggers - use both stdlib and structlog
logger = logging.getLogger(__name__)
struct_logger = get_struct_logger(__name__)

app = FastAPI(
    title="FreeFace Email Service API",
    description="High-performance email delivery system with priority queues and rate limiting",
    version="1.0.0",
)

# Add middleware in correct order (CRITICAL: order matters!)
# 1. Exception handler (LAST - catches everything)
# 2. Access logging (logs all requests)
# 3. Prometheus metrics (collects metrics for all requests)
# 4. Request ID / Trace ID (FIRST - generates ID for correlation)

# Determine if we're in development mode
is_development = os.getenv("ENVIRONMENT", "development") == "development"

app.add_middleware(
    ExceptionHandlerMiddleware,
    include_traceback_in_response=is_development  # Only in development!
)
app.add_middleware(
    AccessLoggingMiddleware,
    log_body=is_development,  # Only log bodies in development!
    max_body_length=1000
)
app.add_middleware(PrometheusMetricsMiddleware)
app.add_middleware(RequestIDMiddleware)

logger.info(
    "Middleware configured: RequestID/TraceID, Prometheus, AccessLogging, ExceptionHandler (development_mode=%s)",
    is_development
)

# Initialize email service
config = EmailConfig(
    redis_host=os.getenv("REDIS_HOST", "10.10.1.21"), redis_port=int(os.getenv("REDIS_PORT", 6379))
)
email_service = EmailService(config)


# Authentication Dependency
async def verify_service_token(
    request: Request,
    x_service_token: Optional[str] = Header(
        None,
        description="Service authentication token (format: st_<env>_<random>)",
        example="st_live_abc123def456...",
    )
) -> ServiceIdentity:
    """
    FastAPI dependency for service-to-service authentication

    Verifies the X-Service-Token header and returns service identity.
    Used as a dependency on protected endpoints.

    Args:
        request: FastAPI request (for storing service name in state)
        x_service_token: Service token from X-Service-Token header

    Returns:
        ServiceIdentity with authenticated service details

    Raises:
        HTTPException(401): If token is invalid or missing

    Example:
        @app.post("/send", dependencies=[Depends(verify_service_token)])
        async def send_email(...):
            # This endpoint is now protected
    """
    identity = await authenticator.verify_token(x_service_token)

    # Store service name in request state for access logging middleware
    request.state.service_name = identity.name

    return identity


# Request/Response Models
class EmailRequest(BaseModel):
    recipients: Union[str, List[EmailStr]]
    template: str
    data: Dict = {}
    priority: EmailPriority = EmailPriority.MEDIUM
    provider: EmailProvider = EmailProvider.SMTP
    scheduled_at: Optional[datetime] = None


class EmailResponse(BaseModel):
    job_id: str
    status: str
    message: str


class StatsResponse(BaseModel):
    queue_high: int
    queue_medium: int
    queue_low: int
    sent_today: int
    failed_today: int
    rate_limits: Dict[str, Dict[str, str]]


@app.on_event("startup")
async def startup_event():
    """Initialize the email service on startup"""
    await email_service.initialize()

    # Initialize audit trail with Redis client
    audit_trail.set_redis_client(email_service.redis_client)
    logger.info("Audit trail initialized")

    logger.info("Email API service started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await email_service.shutdown()
    logger.info("Email API service stopped")


@app.post("/send", response_model=EmailResponse)
async def send_email(
    request: EmailRequest, service: ServiceIdentity = Depends(verify_service_token)
):
    """
    Send email via the email system

    **Authentication:** Requires valid service token via X-Service-Token header

    - **recipients**: Email address(es) or group identifier (e.g., "group:hiking_123")
    - **template**: Template name to use
    - **data**: Dynamic data for template
    - **priority**: high/medium/low (affects queue order)
    - **provider**: sendgrid/mailgun/aws_ses/smtp
    - **scheduled_at**: Schedule for future delivery (optional)
    """
    try:
        logger.info("Email send request from service: %s", service.name)

        job_id = await email_service.send_email(
            recipients=request.recipients,
            template=request.template,
            data=request.data,
            priority=request.priority,
            provider=request.provider,
            scheduled_at=request.scheduled_at,
        )

        # Record Prometheus metric
        record_email_queued(template=request.template, priority=request.priority.value)

        # Log to audit trail
        recipient_count = len(request.recipients) if isinstance(request.recipients, list) else 1
        await audit_trail.log_service_call(
            service_name=service.name,
            endpoint="/send",
            job_id=job_id,
            metadata={
                "template": request.template,
                "priority": request.priority.value,
                "provider": request.provider.value,
                "recipient_count": recipient_count,
            },
        )

        logger.info("Email queued by service '%s': job_id=%s", service.name, job_id)
        return EmailResponse(
            job_id=job_id, status="queued", message="Email successfully queued for delivery"
        )

    except Exception as e:
        # Log exception with full context
        logger.error(
            "Email send error (service: %s): %s",
            service.name,
            e,
            exc_info=True,  # Include full traceback
            extra={
                "service_name": service.name,
                "template": request.template,
                "priority": request.priority.value,
                "error_type": type(e).__name__,
            }
        )

        # Also log with structlog for structured output
        struct_logger.error(
            "email_send_failed",
            service_name=service.name,
            template=request.template,
            priority=request.priority.value,
            error_type=type(e).__name__,
            error=str(e),
            exc_info=True
        )

        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/send/welcome")
async def send_welcome_email(
    user_email: EmailStr,
    user_name: str,
    verification_token: str,
    service: ServiceIdentity = Depends(verify_service_token),
):
    """
    Send welcome email to new user

    **Authentication:** Requires valid service token via X-Service-Token header
    """
    logger.info("Welcome email request from service: %s for %s", service.name, user_email)

    job_id = await email_service.send_email(
        recipients=user_email,
        template="user_welcome",
        data={
            "name": user_name,
            "verification_link": f"https://freeface.com/verify/{verification_token}",
        },
        priority=EmailPriority.HIGH,
    )

    # Record Prometheus metric
    record_email_queued(template="user_welcome", priority="high")

    # Log to audit trail
    await audit_trail.log_service_call(
        service_name=service.name,
        endpoint="/send/welcome",
        job_id=job_id,
        metadata={"template": "user_welcome", "recipient_count": 1},
    )

    logger.info("Welcome email queued by service '%s': job_id=%s", service.name, job_id)
    return EmailResponse(job_id=job_id, status="queued", message="Welcome email queued")


@app.post("/send/password-reset")
async def send_password_reset(
    user_email: EmailStr, reset_token: str, service: ServiceIdentity = Depends(verify_service_token)
):
    """
    Send password reset email

    **Authentication:** Requires valid service token via X-Service-Token header
    """
    logger.info("Password reset email request from service: %s for %s", service.name, user_email)

    job_id = await email_service.send_email(
        recipients=user_email,
        template="password_reset",
        data={"reset_link": f"https://freeface.com/reset/{reset_token}"},
        priority=EmailPriority.HIGH,
    )

    # Record Prometheus metric
    record_email_queued(template="password_reset", priority="high")

    # Log to audit trail
    await audit_trail.log_service_call(
        service_name=service.name,
        endpoint="/send/password-reset",
        job_id=job_id,
        metadata={"template": "password_reset", "recipient_count": 1},
    )

    logger.info("Password reset email queued by service '%s': job_id=%s", service.name, job_id)
    return EmailResponse(job_id=job_id, status="queued", message="Password reset email queued")


@app.post("/send/group-notification")
async def send_group_notification(
    group_id: str,
    template: str,
    data: Dict,
    priority: EmailPriority = EmailPriority.MEDIUM,
    service: ServiceIdentity = Depends(verify_service_token),
):
    """
    Send notification to group members

    **Authentication:** Requires valid service token via X-Service-Token header
    """
    logger.info("Group notification request from service: %s for group %s", service.name, group_id)

    job_id = await email_service.send_email(
        recipients=f"group:{group_id}", template=template, data=data, priority=priority
    )

    # Record Prometheus metric
    record_email_queued(template=template, priority=priority.value)

    # Log to audit trail
    await audit_trail.log_service_call(
        service_name=service.name,
        endpoint="/send/group-notification",
        job_id=job_id,
        metadata={"template": template, "group_id": group_id, "priority": priority.value},
    )

    logger.info(
        "Group notification queued by service '%s': group=%s, job_id=%s",
        service.name,
        group_id,
        job_id,
    )
    return EmailResponse(
        job_id=job_id, status="queued", message=f"Group notification queued for {group_id}"
    )


@app.get("/stats", response_model=StatsResponse)
async def get_stats(service: ServiceIdentity = Depends(verify_service_token)):
    """
    Get email system statistics

    **Authentication:** Requires valid service token via X-Service-Token header
    """
    try:
        logger.debug("Stats request from service: %s", service.name)

        # Log to audit trail (no job_id for stats calls)
        await audit_trail.log_service_call(
            service_name=service.name, endpoint="/stats", job_id=None, metadata={}
        )

        stats = await email_service.get_stats()

        return StatsResponse(
            queue_high=int(stats.get("queue_high", 0)),
            queue_medium=int(stats.get("queue_medium", 0)),
            queue_low=int(stats.get("queue_low", 0)),
            sent_today=int(stats.get("sent", 0)),
            failed_today=int(stats.get("failed", 0)),
            rate_limits={
                provider: {
                    "tokens": stats.get(f"rate_{provider}_tokens", "unknown"),
                    "limit": str(config.rate_limits[provider]["bucket_size"]),
                }
                for provider in config.rate_limits.keys()
            },
        )

    except Exception as e:
        # Log exception with full context
        logger.error(
            "Stats retrieval error (service: %s): %s",
            service.name,
            e,
            exc_info=True,  # Include full traceback
            extra={
                "service_name": service.name,
                "error_type": type(e).__name__,
            }
        )

        # Also log with structlog
        struct_logger.error(
            "stats_retrieval_failed",
            service_name=service.name,
            error_type=type(e).__name__,
            error=str(e),
            exc_info=True
        )

        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint

    **Authentication:** NO authentication required (public endpoint for Prometheus scraping)

    Returns metrics in Prometheus exposition format for the observability stack.
    This endpoint is automatically discovered and scraped by Prometheus.

    Metrics include:
    - http_requests_total: Total HTTP requests by endpoint, method, status
    - http_request_duration_seconds: Request latency histogram
    - http_requests_active: Currently active requests
    - email_jobs_queued_total: Email jobs queued by template and priority
    - email_service_info: Service metadata
    """
    from fastapi.responses import Response
    return Response(content=get_metrics(), media_type=get_metrics_content_type())


@app.get("/live")
async def liveness_check():
    """
    Liveness check endpoint (shallow health check)

    **Authentication:** NO authentication required (public endpoint for monitoring)

    Returns a simple alive status without checking dependencies.
    This is ideal for Kubernetes liveness probes and basic uptime monitoring.
    Use /health for readiness checks that verify Redis connectivity.
    """
    return {"status": "alive"}


@app.get("/health")
async def health_check():
    """
    Health/readiness check endpoint (deep health check)

    **Authentication:** NO authentication required (public endpoint for monitoring)

    This endpoint must remain publicly accessible for:
    - Docker healthchecks
    - Load balancer health monitoring
    - Service discovery systems
    - Kubernetes readiness probes
    - Activity App observability stack

    Checks Redis connectivity and queue status.
    Returns structured response with timestamp and service name for observability.
    """
    try:
        # Test Redis connection
        stats = await email_service.get_stats()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "email-api",
            "dependencies": {
                "redis": "connected"
            },
            "queues": {
                "high": stats.get("queue_high", 0),
                "medium": stats.get("queue_medium", 0),
                "low": stats.get("queue_low", 0),
            },
        }
    except Exception as e:
        # Log health check failure
        logger.error(
            "Health check failed: %s",
            e,
            exc_info=True,
            extra={"error_type": type(e).__name__}
        )

        struct_logger.error(
            "health_check_failed",
            error_type=type(e).__name__,
            error=str(e),
            exc_info=True
        )

        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}") from e
