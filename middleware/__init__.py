"""
Middleware Module for FreeFace Email Service

This module contains all middleware for the FastAPI application:
- Structured access logging with trace ID correlation
- Exception handling and logging
- Request/response body logging (debug mode)
- Prometheus metrics collection for observability stack
"""

from .access_logging import AccessLoggingMiddleware
from .exception_handler import ExceptionHandlerMiddleware
from .request_id import RequestIDMiddleware
from .prometheus_metrics import (
    PrometheusMetricsMiddleware,
    record_email_queued,
    get_metrics,
    get_metrics_content_type,
)

__all__ = [
    "AccessLoggingMiddleware",
    "ExceptionHandlerMiddleware",
    "RequestIDMiddleware",
    "PrometheusMetricsMiddleware",
    "record_email_queued",
    "get_metrics",
    "get_metrics_content_type",
]
