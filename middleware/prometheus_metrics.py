"""
Prometheus Metrics Middleware

Provides comprehensive Prometheus metrics for the email service API.
Integrates with the Activity App observability stack for centralized monitoring.

Metrics exposed:
- http_requests_total: Counter for total HTTP requests by endpoint, method, status
- http_request_duration_seconds: Histogram for request latency
- http_requests_active: Gauge for currently active requests
- email_jobs_queued_total: Counter for emails queued
- email_service_info: Info metric with service metadata

All metrics include 'service' label set to 'email-api' for proper identification
in the observability stack.
"""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Service name constant (must match docker-compose service name)
SERVICE_NAME = "email-api"

# Define Prometheus metrics
# These will be automatically scraped by Prometheus via the /metrics endpoint

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['service', 'endpoint', 'method', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['service', 'endpoint', 'method'],
    # Buckets optimized for API response times
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

http_requests_active = Gauge(
    'http_requests_active',
    'Active HTTP requests',
    ['service']
)

# Email-specific metrics
email_jobs_queued_total = Counter(
    'email_jobs_queued_total',
    'Total email jobs queued',
    ['service', 'template', 'priority']
)

# Service info metric
email_service_info = Info(
    'email_service',
    'Email service information'
)

# Set service info
email_service_info.info({
    'service': SERVICE_NAME,
    'version': '1.0.0',
    'framework': 'fastapi',
})


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware that collects Prometheus metrics for all HTTP requests.

    Automatically tracks:
    - Request counts by endpoint, method, and status code
    - Request duration histograms
    - Active request gauge
    - Service metadata

    The /metrics endpoint is excluded from tracking to avoid noise.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and collect metrics

        Args:
            request: Incoming FastAPI request
            call_next: Next middleware/route handler

        Returns:
            Response with metrics collected
        """
        # Skip metrics collection for the /metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        # Increment active requests
        http_requests_active.labels(service=SERVICE_NAME).inc()

        # Record start time
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Record metrics
            http_requests_total.labels(
                service=SERVICE_NAME,
                endpoint=request.url.path,
                method=request.method,
                status=response.status_code
            ).inc()

            http_request_duration_seconds.labels(
                service=SERVICE_NAME,
                endpoint=request.url.path,
                method=request.method
            ).observe(duration)

            return response

        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time

            http_requests_total.labels(
                service=SERVICE_NAME,
                endpoint=request.url.path,
                method=request.method,
                status=500  # Internal server error
            ).inc()

            http_request_duration_seconds.labels(
                service=SERVICE_NAME,
                endpoint=request.url.path,
                method=request.method
            ).observe(duration)

            raise

        finally:
            # Decrement active requests
            http_requests_active.labels(service=SERVICE_NAME).dec()


def record_email_queued(template: str, priority: str):
    """
    Record an email being queued.

    Args:
        template: Email template name
        priority: Email priority (high, medium, low)

    Usage:
        from middleware.prometheus_metrics import record_email_queued
        record_email_queued("welcome", "high")
    """
    email_jobs_queued_total.labels(
        service=SERVICE_NAME,
        template=template,
        priority=priority
    ).inc()


def get_metrics() -> bytes:
    """
    Get current metrics in Prometheus exposition format.

    Returns:
        Bytes containing metrics in Prometheus format

    Usage:
        Used by the /metrics endpoint to expose metrics to Prometheus
    """
    return generate_latest()


def get_metrics_content_type() -> str:
    """
    Get the content type for Prometheus metrics.

    Returns:
        Content type string for Prometheus metrics
    """
    return CONTENT_TYPE_LATEST
