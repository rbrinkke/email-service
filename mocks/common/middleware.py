# File: mocks/common/middleware.py
# Middleware for mock servers (logging, delay simulation, etc.)

import asyncio
import logging
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all incoming requests and responses

    Logs:
    - Request method, path, query params
    - Response status code
    - Request duration
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details"""
        start_time = time.time()

        # Log incoming request
        logger.info(
            "Request: %s %s %s",
            request.method,
            request.url.path,
            f"?{request.url.query}" if request.url.query else ""
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log response
        logger.info(
            "Response: %s %s - Status: %d - Duration: %.3fs",
            request.method,
            request.url.path,
            response.status_code,
            duration
        )

        return response


class ResponseDelayMiddleware(BaseHTTPMiddleware):
    """
    Add artificial delay to responses for network simulation

    Supports:
    - Global delay configuration
    - Per-request delay via query parameter (?delay_ms=1000)
    """

    def __init__(self, app: FastAPI, default_delay_ms: int = 0):
        """
        Initialize delay middleware

        Args:
            app: FastAPI application
            default_delay_ms: Default delay in milliseconds
        """
        super().__init__(app)
        self.default_delay_ms = default_delay_ms

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with delay"""
        # Check for per-request delay parameter
        delay_ms = request.query_params.get("delay_ms", self.default_delay_ms)

        try:
            delay_ms = int(delay_ms)
        except (ValueError, TypeError):
            delay_ms = self.default_delay_ms

        # Apply delay before processing request
        if delay_ms > 0:
            logger.debug("Simulating network delay: %dms", delay_ms)
            await asyncio.sleep(delay_ms / 1000.0)

        return await call_next(request)


def add_mock_middleware(
    app: FastAPI,
    enable_logging: bool = True,
    enable_delay: bool = True,
    default_delay_ms: int = 0
):
    """
    Add standard middleware to mock server

    Args:
        app: FastAPI application
        enable_logging: Enable request/response logging
        enable_delay: Enable response delay simulation
        default_delay_ms: Default delay in milliseconds
    """
    if enable_logging:
        app.add_middleware(RequestLoggingMiddleware)
        logger.info("Request logging middleware enabled")

    if enable_delay:
        app.add_middleware(ResponseDelayMiddleware, default_delay_ms=default_delay_ms)
        logger.info("Response delay middleware enabled (default: %dms)", default_delay_ms)
