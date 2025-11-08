# File: api.py
# FastAPI Email Service API

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Union

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, EmailStr

from config.logging_config import setup_logging
from email_system import EmailConfig, EmailPriority, EmailProvider, EmailService
from services.auth_service import ServiceIdentity, authenticator
from services.audit_service import audit_trail

# Configure logging using centralized configuration
# This sets up Docker-compatible logging (stdout/stderr only)
# Respects LOG_LEVEL, ENVIRONMENT, and other logging env vars
setup_logging()

# Get logger for this module
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FreeFace Email Service API",
    description="High-performance email delivery system with priority queues and rate limiting",
    version="1.0.0",
)

# Initialize email service
config = EmailConfig(redis_host=os.getenv("REDIS_HOST", "10.10.1.21"), redis_port=int(os.getenv("REDIS_PORT", 6379)))
email_service = EmailService(config)


# Authentication Dependency
async def verify_service_token(
    x_service_token: Optional[str] = Header(
        None,
        description="Service authentication token (format: st_<env>_<random>)",
        example="st_live_abc123def456..."
    )
) -> ServiceIdentity:
    """
    FastAPI dependency for service-to-service authentication

    Verifies the X-Service-Token header and returns service identity.
    Used as a dependency on protected endpoints.

    Args:
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
    return await authenticator.verify_token(x_service_token)


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
    request: EmailRequest,
    service: ServiceIdentity = Depends(verify_service_token)
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
        logger.info(f"Email send request from service: {service.name}")

        job_id = await email_service.send_email(
            recipients=request.recipients,
            template=request.template,
            data=request.data,
            priority=request.priority,
            provider=request.provider,
            scheduled_at=request.scheduled_at,
        )

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
                "recipient_count": recipient_count
            }
        )

        logger.info(f"Email queued by service '{service.name}': job_id={job_id}")
        return EmailResponse(job_id=job_id, status="queued", message="Email successfully queued for delivery")

    except Exception as e:
        logger.error(f"Email send error (service: {service.name}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/send/welcome")
async def send_welcome_email(
    user_email: EmailStr,
    user_name: str,
    verification_token: str,
    service: ServiceIdentity = Depends(verify_service_token)
):
    """
    Send welcome email to new user

    **Authentication:** Requires valid service token via X-Service-Token header
    """
    logger.info(f"Welcome email request from service: {service.name} for {user_email}")

    job_id = await email_service.send_email(
        recipients=user_email,
        template="user_welcome",
        data={"name": user_name, "verification_link": f"https://freeface.com/verify/{verification_token}"},
        priority=EmailPriority.HIGH,
    )

    # Log to audit trail
    await audit_trail.log_service_call(
        service_name=service.name,
        endpoint="/send/welcome",
        job_id=job_id,
        metadata={"template": "user_welcome", "recipient_count": 1}
    )

    logger.info(f"Welcome email queued by service '{service.name}': job_id={job_id}")
    return EmailResponse(job_id=job_id, status="queued", message="Welcome email queued")


@app.post("/send/password-reset")
async def send_password_reset(
    user_email: EmailStr,
    reset_token: str,
    service: ServiceIdentity = Depends(verify_service_token)
):
    """
    Send password reset email

    **Authentication:** Requires valid service token via X-Service-Token header
    """
    logger.info(f"Password reset email request from service: {service.name} for {user_email}")

    job_id = await email_service.send_email(
        recipients=user_email,
        template="password_reset",
        data={"reset_link": f"https://freeface.com/reset/{reset_token}"},
        priority=EmailPriority.HIGH,
    )

    # Log to audit trail
    await audit_trail.log_service_call(
        service_name=service.name,
        endpoint="/send/password-reset",
        job_id=job_id,
        metadata={"template": "password_reset", "recipient_count": 1}
    )

    logger.info(f"Password reset email queued by service '{service.name}': job_id={job_id}")
    return EmailResponse(job_id=job_id, status="queued", message="Password reset email queued")


@app.post("/send/group-notification")
async def send_group_notification(
    group_id: str,
    template: str,
    data: Dict,
    priority: EmailPriority = EmailPriority.MEDIUM,
    service: ServiceIdentity = Depends(verify_service_token)
):
    """
    Send notification to group members

    **Authentication:** Requires valid service token via X-Service-Token header
    """
    logger.info(f"Group notification request from service: {service.name} for group {group_id}")

    job_id = await email_service.send_email(
        recipients=f"group:{group_id}", template=template, data=data, priority=priority
    )

    # Log to audit trail
    await audit_trail.log_service_call(
        service_name=service.name,
        endpoint="/send/group-notification",
        job_id=job_id,
        metadata={
            "template": template,
            "group_id": group_id,
            "priority": priority.value
        }
    )

    logger.info(f"Group notification queued by service '{service.name}': group={group_id}, job_id={job_id}")
    return EmailResponse(job_id=job_id, status="queued", message=f"Group notification queued for {group_id}")


@app.get("/stats", response_model=StatsResponse)
async def get_stats(service: ServiceIdentity = Depends(verify_service_token)):
    """
    Get email system statistics

    **Authentication:** Requires valid service token via X-Service-Token header
    """
    try:
        logger.debug(f"Stats request from service: {service.name}")

        # Log to audit trail (no job_id for stats calls)
        await audit_trail.log_service_call(
            service_name=service.name,
            endpoint="/stats",
            job_id=None,
            metadata={}
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
        logger.error(f"Stats error (service: {service.name}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """
    Health check endpoint

    **Authentication:** NO authentication required (public endpoint for monitoring)

    This endpoint must remain publicly accessible for:
    - Docker healthchecks
    - Load balancer health monitoring
    - Service discovery systems
    """
    try:
        # Test Redis connection
        stats = await email_service.get_stats()
        return {
            "status": "healthy",
            "redis": "connected",
            "queues": {
                "high": stats.get("queue_high", 0),
                "medium": stats.get("queue_medium", 0),
                "low": stats.get("queue_low", 0),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")
