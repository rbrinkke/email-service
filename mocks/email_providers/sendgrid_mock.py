#!/usr/bin/env python3
# File: mocks/email_providers/sendgrid_mock.py
# SendGrid API Mock Server

import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.base_mock import BaseMockServer
from common.error_simulator import ErrorSimulator
from common.middleware import add_mock_middleware
from common.mock_data_generator import MockDataGenerator


# Pydantic Models for SendGrid API
class EmailAddress(BaseModel):
    """Email address model"""
    email: EmailStr
    name: Optional[str] = None


class EmailContent(BaseModel):
    """Email content model"""
    type: str = Field(..., description="Content type (text/plain, text/html)")
    value: str = Field(..., description="Content value")


class Personalization(BaseModel):
    """Email personalization"""
    to: List[EmailAddress] = Field(..., description="Recipients")
    cc: Optional[List[EmailAddress]] = None
    bcc: Optional[List[EmailAddress]] = None
    subject: Optional[str] = None
    substitutions: Optional[Dict[str, str]] = None


class SendEmailRequest(BaseModel):
    """SendGrid send email request"""
    personalizations: List[Personalization] = Field(..., description="Personalizations")
    from_: EmailAddress = Field(..., alias="from", description="Sender")
    subject: str = Field(..., description="Email subject")
    content: List[EmailContent] = Field(..., description="Email content")
    reply_to: Optional[EmailAddress] = None


class SendEmailResponse(BaseModel):
    """SendGrid send email response"""
    message_id: str = Field(..., description="Message ID")
    status: str = Field("queued", description="Status")


class EmailStats(BaseModel):
    """Email statistics"""
    date: str
    stats: List[Dict] = Field(default_factory=list)


class WebhookEvent(BaseModel):
    """SendGrid webhook event"""
    email: str
    timestamp: int
    event: str
    category: Optional[List[str]] = None
    sg_event_id: str
    sg_message_id: str


class SendGridAPIMock(BaseMockServer):
    """
    Mock server for SendGrid Email API

    Simulates SendGrid's v3 Mail Send API endpoints.

    Endpoints:
    - POST /v3/mail/send              - Send email
    - GET  /v3/stats                  - Get email stats
    - POST /v3/webhooks/test          - Test webhook delivery
    - GET  /v3/messages               - List sent messages
    - GET  /health                    - Health check

    Features:
    - API key authentication
    - Message tracking
    - Statistics simulation
    - Webhook event simulation
    - Full OpenAPI documentation at /docs
    """

    def __init__(self):
        """Initialize SendGrid API mock server"""
        super().__init__(
            title="SendGrid API Mock",
            description="Mock server for SendGrid Email API v3",
            version="3.0.0"
        )

        # Initialize utilities
        self.data_generator = MockDataGenerator(seed=100)
        self.error_simulator = ErrorSimulator()

        # In-memory storage
        self.sent_messages: Dict[str, Dict] = {}
        self.webhook_events: List[WebhookEvent] = []

        # Valid API keys for testing
        self.valid_api_keys = {
            "SG.test_key_1234567890": "test-account",
            "SG.mock_key_abcdefghij": "mock-account"
        }

        # Add middleware
        add_mock_middleware(self.app, enable_logging=True, enable_delay=True)

        # Setup routes
        self._setup_routes()

        self.logger.info("SendGrid API mock initialized with %d valid API keys", len(self.valid_api_keys))

    def _verify_api_key(self, authorization: Optional[str] = Header(None)) -> str:
        """
        Verify SendGrid API key

        Args:
            authorization: Bearer token from Authorization header

        Returns:
            Account name if valid

        Raises:
            HTTPException: If API key is invalid
        """
        if not authorization:
            self.logger.warning("Missing Authorization header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "unauthorized",
                    "message": "Missing Authorization header. Provide: Authorization: Bearer <api_key>"
                }
            )

        # Extract Bearer token
        if not authorization.startswith("Bearer "):
            self.logger.warning("Invalid Authorization format")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "invalid_auth_format",
                    "message": "Authorization must be: Bearer <api_key>"
                }
            )

        api_key = authorization.replace("Bearer ", "")

        # Validate API key
        if api_key not in self.valid_api_keys:
            self.logger.warning("Invalid API key: %s...", api_key[:10])
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "invalid_api_key",
                    "message": "API key is invalid or expired"
                }
            )

        account = self.valid_api_keys[api_key]
        self.logger.debug("API key verified for account: %s", account)
        return account

    def _setup_routes(self):
        """Setup API routes"""

        @self.app.post("/v3/mail/send", response_model=SendEmailResponse, status_code=status.HTTP_202_ACCEPTED)
        async def send_email(
            request: SendEmailRequest,
            account: str = Depends(self._verify_api_key),
            _error_check=Depends(self.check_error_simulation)
        ):
            """
            Send an email via SendGrid

            **Authentication:** Requires Authorization header with Bearer token

            **Request Body:** SendGrid v3 Mail Send format

            **Error Simulation:**
            - ?simulate_error=400 - Bad request
            - ?simulate_error=401 - Invalid API key
            - ?simulate_error=429 - Rate limit exceeded
            - ?simulate_error=500 - Server error

            **Valid API Keys for Testing:**
            - SG.test_key_1234567890
            - SG.mock_key_abcdefghij
            """
            self.logger.info("Send email request from account: %s", account)

            # Generate message ID
            message_id = f"msg_{uuid.uuid4().hex}"

            # Store message
            recipients = []
            for personalization in request.personalizations:
                recipients.extend([r.email for r in personalization.to])

            message_data = {
                "message_id": message_id,
                "account": account,
                "from": request.from_.email,
                "recipients": recipients,
                "subject": request.subject,
                "status": "queued",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

            self.sent_messages[message_id] = message_data

            # Generate webhook event
            for recipient in recipients[:1]:  # Just first recipient for simplicity
                event = WebhookEvent(
                    email=recipient,
                    timestamp=int(datetime.utcnow().timestamp()),
                    event="processed",
                    category=["mock"],
                    sg_event_id=f"evt_{uuid.uuid4().hex[:16]}",
                    sg_message_id=message_id
                )
                self.webhook_events.append(event)

            self.logger.info("Email queued: %s (%d recipients)", message_id, len(recipients))

            return SendEmailResponse(
                message_id=message_id,
                status="queued"
            )

        @self.app.get("/v3/stats")
        async def get_stats(
            account: str = Depends(self._verify_api_key),
            _error_check=Depends(self.check_error_simulation)
        ):
            """
            Get email statistics

            **Authentication:** Requires Authorization header with Bearer token

            Returns aggregated email statistics.
            """
            self.logger.info("Get stats request from account: %s", account)

            # Calculate stats from sent messages
            total_sent = len(self.sent_messages)
            total_delivered = int(total_sent * 0.95)  # 95% delivery rate
            total_bounced = total_sent - total_delivered

            stats = {
                "stats": [
                    {
                        "date": datetime.utcnow().strftime("%Y-%m-%d"),
                        "stats": [
                            {
                                "metrics": {
                                    "blocks": 0,
                                    "bounce_drops": 0,
                                    "bounces": total_bounced,
                                    "clicks": int(total_sent * 0.2),
                                    "deferred": 0,
                                    "delivered": total_delivered,
                                    "invalid_emails": 0,
                                    "opens": int(total_sent * 0.4),
                                    "processed": total_sent,
                                    "requests": total_sent,
                                    "spam_report_drops": 0,
                                    "spam_reports": 0,
                                    "unique_clicks": int(total_sent * 0.15),
                                    "unique_opens": int(total_sent * 0.3),
                                    "unsubscribe_drops": 0,
                                    "unsubscribes": 0,
                                }
                            }
                        ]
                    }
                ]
            }

            return stats

        @self.app.get("/v3/messages")
        async def list_messages(
            account: str = Depends(self._verify_api_key),
            _error_check=Depends(self.check_error_simulation)
        ):
            """
            List sent messages

            **Authentication:** Requires Authorization header with Bearer token

            Returns list of sent messages (mock endpoint).
            """
            self.logger.info("List messages request from account: %s", account)

            return {
                "messages": list(self.sent_messages.values()),
                "total": len(self.sent_messages)
            }

        @self.app.get("/v3/webhooks/events")
        async def get_webhook_events(
            account: str = Depends(self._verify_api_key),
            _error_check=Depends(self.check_error_simulation)
        ):
            """
            Get webhook events

            **Authentication:** Requires Authorization header with Bearer token

            Returns recent webhook events.
            """
            self.logger.info("Get webhook events from account: %s", account)

            return {
                "events": [event.model_dump() for event in self.webhook_events[-100:]],
                "total": len(self.webhook_events)
            }


def main():
    """Run the mock server"""
    import os

    mock = SendGridAPIMock()

    # Allow port override via environment
    port = int(os.getenv("MOCK_PORT", "8002"))

    mock.run(port=port)


if __name__ == "__main__":
    main()
