"""
Structured Access Logging Middleware

This middleware replaces uvicorn.access logs with structured JSON logs
that include:
- Request ID for correlation
- HTTP method, path, query params
- Response status code and size
- Request duration (performance monitoring)
- Client IP and User-Agent
- Service authentication info (which service made the call)

This is ESSENTIAL for:
- Production debugging and troubleshooting
- Performance monitoring and optimization
- Security auditing and compliance
- Integration with log aggregation tools (Datadog, CloudWatch, etc.)

Based on best practices from the expert FastAPI logging guide.
"""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("api.access")


class AccessLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all HTTP requests in structured format with full context.

    This middleware should be one of the FIRST in the chain (after RequestIDMiddleware)
    to ensure accurate timing measurements.

    Log Format (JSON when using structlog, structured dict otherwise):
    {
        "event": "http_request",
        "request_id": "uuid",
        "method": "POST",
        "path": "/send",
        "query_params": "?priority=high",
        "status_code": 200,
        "duration_ms": 145.2,
        "client_ip": "10.0.1.5",
        "user_agent": "python-requests/2.28",
        "service_name": "main-app",  # From authentication
        "request_size": 1024,
        "response_size": 256
    }
    """

    def __init__(self, app, log_body: bool = False, max_body_length: int = 1000):
        """
        Initialize access logging middleware

        Args:
            app: FastAPI application
            log_body: Whether to log request/response bodies (USE ONLY IN DEBUG!)
            max_body_length: Maximum body length to log (prevent huge logs)
        """
        super().__init__(app)
        self.log_body = log_body
        self.max_body_length = max_body_length

        if self.log_body:
            logger.warning(
                "Request/response body logging is ENABLED - "
                "This should ONLY be used in development/debug environments!"
            )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log access information

        Args:
            request: Incoming FastAPI request
            call_next: Next middleware/route handler

        Returns:
            Response from handler
        """
        # Start timing
        start_time = time.time()

        # Extract request ID (set by RequestIDMiddleware)
        request_id = getattr(request.state, "request_id", "unknown")

        # Extract client information
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Extract authentication info (set by auth middleware)
        service_name = getattr(request.state, "service_name", None)

        # Build request context for logging
        request_context = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.url.query) if request.url.query else None,
            "client_ip": client_ip,
            "user_agent": user_agent,
        }

        # Add service name if authenticated
        if service_name:
            request_context["service_name"] = service_name

        # Optionally log request body (DEBUG ONLY!)
        if self.log_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if len(body) <= self.max_body_length:
                    request_context["request_body"] = body.decode("utf-8", errors="replace")
                else:
                    request_context["request_body"] = (
                        f"[Body too large: {len(body)} bytes, truncated]"
                    )
            except Exception as e:
                logger.debug("Failed to read request body: %s", e)

        # Log incoming request at DEBUG level
        logger.debug(
            "HTTP Request: %s %s [request_id=%s]",
            request.method,
            request.url.path,
            request_id,
            extra=request_context
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Build response context
            response_context = {
                **request_context,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            }

            # Add response size if available
            if "content-length" in response.headers:
                response_context["response_size"] = int(response.headers["content-length"])

            # Log completed request at INFO level
            # Use different log levels based on status code
            if response.status_code >= 500:
                log_level = logging.ERROR
                log_message = "HTTP Request FAILED (5xx)"
            elif response.status_code >= 400:
                log_level = logging.WARNING
                log_message = "HTTP Request ERROR (4xx)"
            else:
                log_level = logging.INFO
                log_message = "HTTP Request"

            logger.log(
                log_level,
                "%s: %s %s - %d [%.2fms] [request_id=%s]",
                log_message,
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                request_id,
                extra=response_context
            )

            # Log slow requests at WARNING level
            if duration_ms > 1000:  # Slower than 1 second
                logger.warning(
                    "SLOW REQUEST detected: %s %s took %.2fms [request_id=%s]",
                    request.method,
                    request.url.path,
                    duration_ms,
                    request_id,
                    extra=response_context
                )

            return response

        except Exception as e:
            # Log exception during request processing
            duration_ms = (time.time() - start_time) * 1000

            error_context = {
                **request_context,
                "duration_ms": round(duration_ms, 2),
                "error_type": type(e).__name__,
                "error_message": str(e),
            }

            logger.error(
                "HTTP Request EXCEPTION: %s %s - %s after %.2fms [request_id=%s]",
                request.method,
                request.url.path,
                type(e).__name__,
                duration_ms,
                request_id,
                exc_info=True,  # Include full traceback
                extra=error_context
            )

            # Re-raise to let exception middleware handle it
            raise
