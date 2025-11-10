"""
Request ID Middleware

Generates and propagates unique request IDs for distributed tracing.
The request ID is:
- Generated for each incoming request (or extracted from X-Request-ID header)
- Added to all log messages during the request lifecycle
- Returned in the response headers for client-side correlation

This is CRITICAL for debugging issues in production when you have multiple
workers and need to trace a specific request through all components.
"""

import logging
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique request ID to each request.

    The request ID is:
    1. Extracted from X-Request-ID header if provided by client
    2. Generated as UUID if not provided
    3. Stored in request.state.request_id for use by other middleware
    4. Added to response headers as X-Request-ID

    Best Practice: All logs within the request should include this request_id
    for easy correlation and troubleshooting.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and inject request ID

        Args:
            request: Incoming FastAPI request
            call_next: Next middleware/route handler

        Returns:
            Response with X-Request-ID header
        """
        # Extract or generate request ID
        request_id = request.headers.get("x-request-id")

        if not request_id:
            # Generate new UUID for this request
            request_id = str(uuid.uuid4())
            logger.debug("Generated new request ID: %s", request_id)
        else:
            logger.debug("Using client-provided request ID: %s", request_id)

        # Store in request state for access by other middleware and handlers
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers for client correlation
        response.headers["X-Request-ID"] = request_id

        return response
