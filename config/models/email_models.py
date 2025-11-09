# File: /opt/freeface/email/models/email_models.py
# FreeFace Email System - Data Models
# Contains all email-related data models and enums

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, EmailStr, Field, validator


class EmailPriority(str, Enum):
    HIGH = "high"  # Password resets, 2FA codes (URGENT!)
    MEDIUM = "medium"  # Group invites, confirmations (NORMAL)
    LOW = "low"  # Newsletters, marketing (CAN WAIT)


class EmailProvider(str, Enum):
    SENDGRID = "sendgrid"
    MAILGUN = "mailgun"
    AWS_SES = "aws_ses"
    SMTP = "smtp"


class EmailStatus(str, Enum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    RETRY = "retry"
    DEAD_LETTER = "dead_letter"


class EmailJob(BaseModel):
    """Email job model with validation"""

    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    to: Union[EmailStr, List[EmailStr]]
    template: str
    data: Dict = Field(default_factory=dict)
    priority: EmailPriority = EmailPriority.MEDIUM
    provider: EmailProvider = EmailProvider.SENDGRID
    status: EmailStatus = EmailStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    stream_id: Optional[str] = None  # Redis stream message ID

    @validator("to")
    def validate_recipients(cls, v):
        if isinstance(v, str):
            return [v]
        if len(v) > 100:  # Batch limit
            raise ValueError("Too many recipients in single job")
        return v

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
