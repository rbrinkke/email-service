#!/usr/bin/env python3
# File: mocks/webhook_receiver/webhook_receiver_mock.py
# Webhook Receiver Mock Server - Catch-all for testing webhooks

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Request
from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.base_mock import BaseMockServer
from common.middleware import add_mock_middleware
from common.mock_data_generator import MockDataGenerator


class WebhookRecord(BaseModel):
    """Webhook request record"""
    id: str
    timestamp: str
    method: str
    path: str
    headers: Dict[str, str]
    query_params: Dict[str, str]
    body: Optional[Any] = None
    content_type: Optional[str] = None


class WebhookReceiverMock(BaseMockServer):
    """
    Webhook Receiver Mock Server

    A catch-all webhook receiver for testing webhook integrations.

    Features:
    - Accepts webhooks at any path
    - Records all webhook requests
    - View webhook history via API
    - Configurable responses
    - No authentication required (testing only!)

    Endpoints:
    - POST /webhooks/*           - Receive webhook (any path)
    - GET  /webhooks/history     - View received webhooks
    - DELETE /webhooks/history   - Clear webhook history
    - GET  /health               - Health check

    Usage:
        # Send webhook
        curl -X POST http://localhost:8004/webhooks/sendgrid \\
          -H "Content-Type: application/json" \\
          -d '{"event": "delivered", "email": "user@example.com"}'

        # View history
        curl http://localhost:8004/webhooks/history
    """

    def __init__(self):
        """Initialize webhook receiver mock"""
        super().__init__(
            title="Webhook Receiver Mock",
            description="Catch-all webhook receiver for testing",
            version="1.0.0"
        )

        # Initialize utilities
        self.data_generator = MockDataGenerator()

        # In-memory storage for received webhooks
        self.webhook_history: List[WebhookRecord] = []

        # Add middleware
        add_mock_middleware(self.app, enable_logging=True, enable_delay=False)

        # Setup routes
        self._setup_routes()

        self.logger.info("Webhook receiver mock initialized")

    def _setup_routes(self):
        """Setup API routes"""

        @self.app.post("/webhooks/{path:path}")
        @self.app.put("/webhooks/{path:path}")
        @self.app.patch("/webhooks/{path:path}")
        async def receive_webhook(path: str, request: Request):
            """
            Receive webhook at any path

            Accepts POST, PUT, or PATCH requests and stores the webhook data.

            **Path Parameters:**
            - path: Any webhook path (e.g., /webhooks/sendgrid, /webhooks/stripe)

            **Returns:**
            - 200 OK with webhook ID

            All received webhooks are stored and can be viewed at /webhooks/history
            """
            self.logger.info("Webhook received: %s %s", request.method, path)

            # Extract headers
            headers = dict(request.headers)

            # Extract query params
            query_params = dict(request.query_params)

            # Get body
            content_type = request.headers.get("content-type", "")
            try:
                if "application/json" in content_type:
                    body = await request.json()
                elif "application/x-www-form-urlencoded" in content_type:
                    body = dict(await request.form())
                else:
                    body_bytes = await request.body()
                    body = body_bytes.decode("utf-8") if body_bytes else None
            except Exception as e:
                self.logger.warning("Error parsing webhook body: %s", e)
                body = None

            # Create record
            record = WebhookRecord(
                id=self.data_generator.generate_uuid(),
                timestamp=datetime.utcnow().isoformat() + "Z",
                method=request.method,
                path=f"/webhooks/{path}",
                headers=headers,
                query_params=query_params,
                body=body,
                content_type=content_type
            )

            # Store webhook
            self.webhook_history.append(record)

            self.logger.info(
                "Webhook stored: %s (total: %d)",
                record.id,
                len(self.webhook_history)
            )

            # Return success
            return {
                "status": "received",
                "webhook_id": record.id,
                "timestamp": record.timestamp,
                "message": "Webhook received successfully"
            }

        @self.app.get("/webhooks/history")
        async def get_webhook_history(
            limit: int = 100,
            offset: int = 0
        ):
            """
            Get webhook history

            Returns list of received webhooks with pagination.

            **Query Parameters:**
            - limit: Maximum webhooks to return (default: 100)
            - offset: Number of webhooks to skip (default: 0)
            """
            self.logger.info("Get webhook history (limit=%d, offset=%d)", limit, offset)

            # Get paginated history (newest first)
            history = list(reversed(self.webhook_history))
            paginated = history[offset:offset + limit]

            return {
                "webhooks": [w.model_dump() for w in paginated],
                "total": len(self.webhook_history),
                "limit": limit,
                "offset": offset
            }

        @self.app.get("/webhooks/history/{webhook_id}")
        async def get_webhook_by_id(webhook_id: str):
            """
            Get specific webhook by ID

            **Path Parameters:**
            - webhook_id: Webhook UUID
            """
            self.logger.info("Get webhook: %s", webhook_id)

            for webhook in self.webhook_history:
                if webhook.id == webhook_id:
                    return webhook.model_dump()

            from common.error_simulator import ErrorSimulator
            error_sim = ErrorSimulator()
            error_sim.raise_not_found("webhook", webhook_id)

        @self.app.delete("/webhooks/history")
        async def clear_webhook_history():
            """
            Clear all webhook history

            Deletes all stored webhook records.
            """
            count = len(self.webhook_history)
            self.webhook_history.clear()

            self.logger.info("Webhook history cleared (%d records deleted)", count)

            return {
                "status": "cleared",
                "deleted_count": count,
                "message": f"Cleared {count} webhook records"
            }

        @self.app.get("/webhooks/stats")
        async def get_webhook_stats():
            """
            Get webhook statistics

            Returns statistics about received webhooks.
            """
            self.logger.info("Get webhook stats")

            # Count by method
            method_counts = {}
            path_counts = {}

            for webhook in self.webhook_history:
                method_counts[webhook.method] = method_counts.get(webhook.method, 0) + 1
                path_counts[webhook.path] = path_counts.get(webhook.path, 0) + 1

            return {
                "total_webhooks": len(self.webhook_history),
                "by_method": method_counts,
                "by_path": path_counts,
                "oldest": self.webhook_history[0].timestamp if self.webhook_history else None,
                "newest": self.webhook_history[-1].timestamp if self.webhook_history else None
            }


def main():
    """Run the mock server"""
    import os

    mock = WebhookReceiverMock()

    # Allow port override via environment
    port = int(os.getenv("MOCK_PORT", "8004"))

    mock.run(port=port)


if __name__ == "__main__":
    main()
