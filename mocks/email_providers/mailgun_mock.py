#!/usr/bin/env python3
# File: mocks/email_providers/mailgun_mock.py
# Mailgun API Mock Server

import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import Depends, Header, HTTPException, status, Form
from pydantic import BaseModel, Field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.base_mock import BaseMockServer
from common.error_simulator import ErrorSimulator
from common.middleware import add_mock_middleware
from common.mock_data_generator import MockDataGenerator


class MailgunSendResponse(BaseModel):
    """Mailgun send response"""
    id: str = Field(..., description="Message ID")
    message: str = Field("Queued. Thank you.", description="Status message")


class MailgunEvent(BaseModel):
    """Mailgun event"""
    event: str
    timestamp: float
    id: str
    recipient: str
    message_id: str


class MailgunAPIMock(BaseMockServer):
    """
    Mock server for Mailgun Email API

    Simulates Mailgun's Messages API endpoints.

    Endpoints:
    - POST /{domain}/messages         - Send email
    - GET  /{domain}/events           - Get events
    - GET  /v3/domains                - List domains
    - GET  /health                    - Health check

    Features:
    - Basic auth with API key
    - Message tracking
    - Event logging
    - Multi-domain support
    - Full OpenAPI documentation at /docs
    """

    def __init__(self):
        """Initialize Mailgun API mock server"""
        super().__init__(
            title="Mailgun API Mock",
            description="Mock server for Mailgun Email API",
            version="1.0.0"
        )

        # Initialize utilities
        self.data_generator = MockDataGenerator(seed=200)
        self.error_simulator = ErrorSimulator()

        # In-memory storage
        self.sent_messages: Dict[str, Dict] = {}
        self.events: List[MailgunEvent] = []

        # Valid API keys (format: "api:<key>")
        self.valid_api_keys = {
            "api:test-mailgun-key-12345": "test-account",
            "api:mock-mailgun-key-abcde": "mock-account"
        }

        # Valid domains
        self.valid_domains = [
            "sandbox123.mailgun.org",
            "mg.example.com",
            "mail.freeface.com"
        ]

        # Add middleware
        add_mock_middleware(self.app, enable_logging=True, enable_delay=True)

        # Setup routes
        self._setup_routes()

        self.logger.info("Mailgun API mock initialized")

    def _verify_api_key(self, authorization: Optional[str] = Header(None)) -> str:
        """
        Verify Mailgun API key (Basic Auth)

        Args:
            authorization: Basic auth from Authorization header

        Returns:
            Account name if valid

        Raises:
            HTTPException: If API key is invalid
        """
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header. Use Basic Auth with api:<key>"
            )

        # Mailgun uses Basic auth with "api" as username
        import base64

        if not authorization.startswith("Basic "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Use Basic Auth with api:<key>"
            )

        try:
            encoded = authorization.replace("Basic ", "")
            decoded = base64.b64decode(encoded).decode("utf-8")

            if decoded not in self.valid_api_keys:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key"
                )

            account = self.valid_api_keys[decoded]
            self.logger.debug("API key verified for account: %s", account)
            return account

        except Exception as e:
            self.logger.warning("Auth error: %s", e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )

    def _setup_routes(self):
        """Setup API routes"""

        @self.app.post("/{domain}/messages", response_model=MailgunSendResponse)
        async def send_email(
            domain: str,
            from_: str = Form(..., alias="from"),
            to: str = Form(...),
            subject: str = Form(...),
            text: Optional[str] = Form(None),
            html: Optional[str] = Form(None),
            account: str = Depends(self._verify_api_key),
            _error_check=Depends(self.check_error_simulation)
        ):
            """
            Send an email via Mailgun

            **Authentication:** Basic Auth with api:<key>

            **Valid API Keys for Testing:**
            - api:test-mailgun-key-12345
            - api:mock-mailgun-key-abcde

            **Valid Domains:**
            - sandbox123.mailgun.org
            - mg.example.com
            - mail.freeface.com

            **Error Simulation:**
            - ?simulate_error=400 - Bad request
            - ?simulate_error=401 - Invalid API key
            - ?simulate_error=404 - Domain not found
            """
            self.logger.info("Send email: domain=%s, from=%s, to=%s", domain, from_, to)

            # Validate domain
            if domain not in self.valid_domains:
                self.error_simulator.raise_not_found("domain", domain)

            # Generate message ID
            message_id = f"<{uuid.uuid4().hex}@{domain}>"

            # Store message
            message_data = {
                "id": message_id,
                "domain": domain,
                "from": from_,
                "to": to,
                "subject": subject,
                "status": "queued",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

            self.sent_messages[message_id] = message_data

            # Generate event
            event = MailgunEvent(
                event="accepted",
                timestamp=datetime.utcnow().timestamp(),
                id=f"evt_{uuid.uuid4().hex[:16]}",
                recipient=to,
                message_id=message_id
            )
            self.events.append(event)

            self.logger.info("Email queued: %s", message_id)

            return MailgunSendResponse(
                id=message_id,
                message="Queued. Thank you."
            )

        @self.app.get("/{domain}/events")
        async def get_events(
            domain: str,
            account: str = Depends(self._verify_api_key),
            _error_check=Depends(self.check_error_simulation)
        ):
            """
            Get email events for domain

            **Authentication:** Basic Auth with api:<key>
            """
            self.logger.info("Get events for domain: %s", domain)

            # Filter events by domain
            domain_events = [
                event for event in self.events
                if event.message_id.endswith(f"@{domain}>")
            ]

            return {
                "items": [event.model_dump() for event in domain_events],
                "paging": {
                    "next": None,
                    "previous": None
                }
            }

        @self.app.get("/v3/domains")
        async def list_domains(
            account: str = Depends(self._verify_api_key),
            _error_check=Depends(self.check_error_simulation)
        ):
            """
            List configured domains

            **Authentication:** Basic Auth with api:<key>
            """
            self.logger.info("List domains for account: %s", account)

            domains = [
                {
                    "name": domain,
                    "state": "active",
                    "created_at": self.data_generator.generate_timestamp(days_ago=365),
                    "type": "sandbox" if "sandbox" in domain else "custom"
                }
                for domain in self.valid_domains
            ]

            return {
                "total_count": len(domains),
                "items": domains
            }


def main():
    """Run the mock server"""
    import os

    mock = MailgunAPIMock()

    # Allow port override via environment
    port = int(os.getenv("MOCK_PORT", "8003"))

    mock.run(port=port)


if __name__ == "__main__":
    main()
