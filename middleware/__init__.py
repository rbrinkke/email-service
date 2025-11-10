"""
Middleware Module for FreeFace Email Service

This module contains all middleware for the FastAPI application:
- Structured access logging with request ID correlation
- Exception handling and logging
- Request/response body logging (debug mode)
"""

from .access_logging import AccessLoggingMiddleware
from .exception_handler import ExceptionHandlerMiddleware
from .request_id import RequestIDMiddleware

__all__ = [
    "AccessLoggingMiddleware",
    "ExceptionHandlerMiddleware",
    "RequestIDMiddleware",
]
