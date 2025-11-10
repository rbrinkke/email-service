"""
Exception Handler Middleware

Catches and logs all uncaught exceptions in the API.

This is CRITICAL for production monitoring because:
1. Ensures NO exception goes unlogged
2. Provides full stack traces for debugging
3. Returns consistent error responses to clients
4. Prevents sensitive error details from leaking to clients

Based on best practices from expert FastAPI security guidelines.
"""

import logging
import traceback
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("api.exceptions")


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """
    Catch and log all uncaught exceptions.

    This middleware should be one of the LAST in the chain to catch
    exceptions from all other middleware and route handlers.

    Benefits:
    - All exceptions are logged with full context
    - Consistent error responses to clients
    - Stack traces for debugging
    - Request ID correlation for troubleshooting
    """

    def __init__(self, app, include_traceback_in_response: bool = False):
        """
        Initialize exception handler middleware

        Args:
            app: FastAPI application
            include_traceback_in_response: Include traceback in response (DEBUG ONLY!)
        """
        super().__init__(app)
        self.include_traceback_in_response = include_traceback_in_response

        if self.include_traceback_in_response:
            logger.warning(
                "Traceback in response is ENABLED - "
                "This should ONLY be used in development environments!"
            )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and catch any uncaught exceptions

        Args:
            request: Incoming FastAPI request
            call_next: Next middleware/route handler

        Returns:
            Response from handler or error response
        """
        try:
            # Process request normally
            response = await call_next(request)
            return response

        except Exception as e:
            # Get request context for logging
            request_id = getattr(request.state, "request_id", "unknown")
            service_name = getattr(request.state, "service_name", "unknown")

            # Get full traceback
            tb = traceback.format_exc()

            # Build error context
            error_context = {
                "request_id": request_id,
                "service_name": service_name,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.url.query) if request.url.query else None,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": tb,
            }

            # Log the exception with full context
            logger.error(
                "UNCAUGHT EXCEPTION in API: %s %s - %s: %s [request_id=%s]",
                request.method,
                request.url.path,
                type(e).__name__,
                str(e),
                request_id,
                exc_info=True,  # Include full traceback in logs
                extra=error_context
            )

            # Build error response
            error_response = {
                "error": "internal_server_error",
                "message": "An unexpected error occurred. Please contact support with the request ID.",
                "request_id": request_id,
            }

            # Optionally include traceback in response (DEVELOPMENT ONLY!)
            if self.include_traceback_in_response:
                error_response["traceback"] = tb
                error_response["error_type"] = type(e).__name__
                error_response["error_details"] = str(e)

            # Return 500 error response
            return JSONResponse(
                status_code=500,
                content=error_response
            )
