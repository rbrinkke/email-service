# File: api.py
# FastAPI Email Service API

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Union
from datetime import datetime
import logging
import os
from email_system import EmailService, EmailConfig, EmailPriority, EmailProvider

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/email/logs/api.log'),
        logging.StreamHandler()
    ]
)

app = FastAPI(
    title="FreeFace Email Service API",
    description="High-performance email delivery system with priority queues and rate limiting",
    version="1.0.0"
)

# Initialize email service
config = EmailConfig(
    redis_host=os.getenv('REDIS_HOST', '10.10.1.21'),
    redis_port=int(os.getenv('REDIS_PORT', 6379))
)
email_service = EmailService(config)

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
    logging.info("Email API service started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await email_service.shutdown()
    logging.info("Email API service stopped")

@app.post("/send", response_model=EmailResponse)
async def send_email(request: EmailRequest):
    """
    Send email via the email system
    
    - **recipients**: Email address(es) or group identifier (e.g., "group:hiking_123")
    - **template**: Template name to use
    - **data**: Dynamic data for template
    - **priority**: high/medium/low (affects queue order)
    - **provider**: sendgrid/mailgun/aws_ses/smtp
    - **scheduled_at**: Schedule for future delivery (optional)
    """
    try:
        job_id = await email_service.send_email(
            recipients=request.recipients,
            template=request.template,
            data=request.data,
            priority=request.priority,
            provider=request.provider,
            scheduled_at=request.scheduled_at
        )
        
        return EmailResponse(
            job_id=job_id,
            status="queued",
            message="Email successfully queued for delivery"
        )
    
    except Exception as e:
        logging.error(f"Email send error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send/welcome")
async def send_welcome_email(user_email: EmailStr, user_name: str, verification_token: str):
    """Send welcome email to new user"""
    job_id = await email_service.send_email(
        recipients=user_email,
        template="user_welcome",
        data={
            "name": user_name,
            "verification_link": f"https://freeface.com/verify/{verification_token}"
        },
        priority=EmailPriority.HIGH
    )
    
    return EmailResponse(
        job_id=job_id,
        status="queued",
        message="Welcome email queued"
    )

@app.post("/send/password-reset")
async def send_password_reset(user_email: EmailStr, reset_token: str):
    """Send password reset email"""
    job_id = await email_service.send_email(
        recipients=user_email,
        template="password_reset",
        data={
            "reset_link": f"https://freeface.com/reset/{reset_token}"
        },
        priority=EmailPriority.HIGH
    )
    
    return EmailResponse(
        job_id=job_id,
        status="queued",
        message="Password reset email queued"
    )

@app.post("/send/group-notification")
async def send_group_notification(
    group_id: str, 
    template: str, 
    data: Dict,
    priority: EmailPriority = EmailPriority.MEDIUM
):
    """Send notification to group members"""
    job_id = await email_service.send_email(
        recipients=f"group:{group_id}",
        template=template,
        data=data,
        priority=priority
    )
    
    return EmailResponse(
        job_id=job_id,
        status="queued",
        message=f"Group notification queued for {group_id}"
    )

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get email system statistics"""
    try:
        stats = await email_service.get_stats()
        
        return StatsResponse(
            queue_high=int(stats.get('queue_high', 0)),
            queue_medium=int(stats.get('queue_medium', 0)),
            queue_low=int(stats.get('queue_low', 0)),
            sent_today=int(stats.get('sent', 0)),
            failed_today=int(stats.get('failed', 0)),
            rate_limits={
                provider: {
                    "tokens": stats.get(f'rate_{provider}_tokens', 'unknown'),
                    "limit": str(config.rate_limits[provider]["bucket_size"])
                }
                for provider in config.rate_limits.keys()
            }
        )
    
    except Exception as e:
        logging.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Redis connection
        stats = await email_service.get_stats()
        return {
            "status": "healthy",
            "redis": "connected",
            "queues": {
                "high": stats.get('queue_high', 0),
                "medium": stats.get('queue_medium', 0),
                "low": stats.get('queue_low', 0)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")
