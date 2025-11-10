"""
Trace ID Middleware (formerly Request ID Middleware)

Generates and propagates unique trace IDs for distributed tracing and observability.
The trace ID is:
- Generated for each incoming request (or extracted from X-Trace-ID/X-Request-ID header)
- Added to all log messages during the request lifecycle
- Returned in the response headers (X-Trace-ID) for client-side correlation
- Used for correlation across microservices in the observability stack

This is CRITICAL for debugging issues in production when you have multiple
workers and need to trace a specific request through all components.
Aligns with Activity App observability stack requirements.
"""

import logging
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique trace ID to each request.

    The trace ID is:
    1. Extracted from X-Trace-ID header (or X-Request-ID for backwards compatibility)
    2. Generated as UUID4 if not provided
    3. Stored in request.state.trace_id for use by other middleware and handlers
    4. Added to response headers as X-Trace-ID (and X-Request-ID for compatibility)
    5. Bound to structured logging context for automatic inclusion in all logs

    Best Practice: All logs within the request will automatically include this trace_id
    for easy correlation and troubleshooting across the entire observability stack.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and inject trace ID

        Args:
            request: Incoming FastAPI request
            call_next: Next middleware/route handler

        Returns:
            Response with X-Trace-ID and X-Request-ID headers
        """
        # Extract trace ID from headers (try X-Trace-ID first, then X-Request-ID for backwards compatibility)
        trace_id = request.headers.get("x-trace-id") or request.headers.get("x-request-id")

        if not trace_id:
            # Generate new UUID4 for this request (observability stack requirement)
            trace_id = str(uuid.uuid4())
            logger.debug("Generated new trace ID: %s", trace_id)
        else:
            logger.debug("Using client-provided trace ID: %s", trace_id)

        # Store in request state for access by other middleware and handlers
        request.state.trace_id = trace_id
        request.state.request_id = trace_id  # Backwards compatibility

        # Bind trace_id to structured logging context
        # This ensures ALL logs within this request automatically include trace_id
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        try:
            # Process request
            response = await call_next(request)

            # Add trace ID to response headers for client correlation
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Request-ID"] = trace_id  # Backwards compatibility

            return response

        finally:
            # Clear context to prevent leaking to next request
            structlog.contextvars.clear_contextvars()
