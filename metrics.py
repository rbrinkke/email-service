"""
Email Service Metrics Module

Provides comprehensive Prometheus metrics for email service observability.
Implements best practices: RED method, proper labeling, histogram buckets.

Metrics Categories:
- HTTP: Automatic FastAPI instrumentation (rate, errors, duration)
- Email: Domain-specific email delivery metrics
- Queue: Redis queue depth and processing metrics
- Provider: SMTP/API provider health and performance
- Worker: Worker pool health and throughput
"""

import time
from functools import wraps
from typing import Callable, Optional

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    Summary,
)

# ============================================================================
# Service Info
# ============================================================================

email_service_info = Info(
    "email_service",
    "Email service version and configuration information"
)

# ============================================================================
# Email Delivery Metrics (Core Business Logic)
# ============================================================================

# Total emails processed by status
emails_total = Counter(
    "email_service_emails_total",
    "Total number of emails processed",
    ["status", "priority", "provider"]
)

# Email delivery duration (full lifecycle: queue → send → confirm)
email_delivery_duration = Histogram(
    "email_service_delivery_duration_seconds",
    "Email delivery duration from queue to completion",
    ["priority", "provider", "status"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

# Email send duration (just the SMTP/API call)
email_send_duration = Histogram(
    "email_service_send_duration_seconds",
    "Duration of email send operation (SMTP/API call only)",
    ["provider", "status"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

# Email size distribution
email_size_bytes = Histogram(
    "email_service_email_size_bytes",
    "Size of email messages in bytes",
    ["priority"],
    buckets=[1024, 10240, 51200, 102400, 512000, 1048576, 5242880]  # 1KB to 5MB
)

# ============================================================================
# Queue Metrics (Redis Operations)
# ============================================================================

# Current queue depth per priority
queue_depth = Gauge(
    "email_service_queue_depth",
    "Current number of emails in queue",
    ["priority", "queue_type"]  # queue_type: pending, processing, dlq
)

# Queue operations
queue_operations_total = Counter(
    "email_service_queue_operations_total",
    "Total queue operations",
    ["operation", "queue", "status"]  # operation: enqueue, dequeue, retry
)

# Queue wait time (time in queue before processing)
queue_wait_duration = Histogram(
    "email_service_queue_wait_duration_seconds",
    "Time email spent in queue before processing",
    ["priority"],
    buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600]  # 1s to 1h
)

# Dead Letter Queue metrics
dlq_size = Gauge(
    "email_service_dlq_size",
    "Number of emails in Dead Letter Queue",
    ["reason"]  # reason: max_retries, invalid_format, provider_reject
)

# ============================================================================
# Provider Metrics (SMTP/API Health)
# ============================================================================

# Provider availability
provider_available = Gauge(
    "email_service_provider_available",
    "Provider availability (1=up, 0=down)",
    ["provider", "type"]  # type: smtp, api
)

# Provider response time
provider_response_time = Summary(
    "email_service_provider_response_seconds",
    "Provider response time",
    ["provider", "operation"]  # operation: connect, send, confirm
)

# Provider errors
provider_errors_total = Counter(
    "email_service_provider_errors_total",
    "Total provider errors",
    ["provider", "error_type", "is_retriable"]
)

# Provider rate limiting
provider_rate_limit_hits = Counter(
    "email_service_provider_rate_limit_hits_total",
    "Number of times provider rate limit was hit",
    ["provider"]
)

# Provider connection pool
provider_connections = Gauge(
    "email_service_provider_connections",
    "Current provider connections",
    ["provider", "state"]  # state: active, idle, waiting
)

# ============================================================================
# Worker Metrics (Worker Pool Health)
# ============================================================================

# Active workers
workers_active = Gauge(
    "email_service_workers_active",
    "Number of active workers"
)

# Worker status
worker_status = Gauge(
    "email_service_worker_status",
    "Worker status (1=healthy, 0=unhealthy)",
    ["worker_id"]
)

# Worker task processing
worker_tasks_total = Counter(
    "email_service_worker_tasks_total",
    "Total tasks processed by workers",
    ["worker_id", "status"]
)

# Worker processing time
worker_processing_time = Histogram(
    "email_service_worker_processing_seconds",
    "Worker task processing time",
    ["worker_id"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

# Worker restarts
worker_restarts_total = Counter(
    "email_service_worker_restarts_total",
    "Total worker restarts",
    ["worker_id", "reason"]
)

# ============================================================================
# Redis Metrics (Connection Health)
# ============================================================================

# Redis connection status
redis_connected = Gauge(
    "email_service_redis_connected",
    "Redis connection status (1=connected, 0=disconnected)"
)

# Redis operations
redis_operations_total = Counter(
    "email_service_redis_operations_total",
    "Total Redis operations",
    ["operation", "status"]  # operation: get, set, rpush, lpop, etc.
)

# Redis operation duration
redis_operation_duration = Histogram(
    "email_service_redis_operation_duration_seconds",
    "Redis operation duration",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Redis pool stats
redis_pool_connections = Gauge(
    "email_service_redis_pool_connections",
    "Redis connection pool size",
    ["state"]  # state: active, idle, available
)

# ============================================================================
# API Metrics (HTTP Layer - complementing FastAPI instrumentator)
# ============================================================================

# API authentication
api_auth_attempts_total = Counter(
    "email_service_api_auth_attempts_total",
    "Total API authentication attempts",
    ["service_name", "status"]
)

# API rate limiting
api_rate_limit_exceeded_total = Counter(
    "email_service_api_rate_limit_exceeded_total",
    "Total API rate limit exceeded events",
    ["service_name", "endpoint"]
)

# ============================================================================
# System Metrics (Resource Usage)
# ============================================================================

# Memory usage estimation (application-level)
memory_usage_bytes = Gauge(
    "email_service_memory_usage_bytes",
    "Estimated memory usage",
    ["component"]  # component: queue_cache, templates, connections
)

# Active connections
active_connections = Gauge(
    "email_service_active_connections",
    "Number of active connections",
    ["type"]  # type: redis, smtp, http
)

# ============================================================================
# Decorator Utilities for Easy Instrumentation
# ============================================================================

def track_email_delivery(priority: str, provider: str):
    """
    Decorator to track email delivery metrics

    Usage:
        @track_email_delivery(priority="high", provider="sendgrid")
        async def send_email(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                emails_total.labels(
                    status=status,
                    priority=priority,
                    provider=provider
                ).inc()
                email_delivery_duration.labels(
                    priority=priority,
                    provider=provider,
                    status=status
                ).observe(duration)

        return wrapper
    return decorator


def track_queue_operation(operation: str, queue: str):
    """
    Decorator to track queue operations

    Usage:
        @track_queue_operation(operation="enqueue", queue="high")
        async def enqueue_email(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                status = "error"
                raise
            finally:
                queue_operations_total.labels(
                    operation=operation,
                    queue=queue,
                    status=status
                ).inc()

        return wrapper
    return decorator


def track_provider_call(provider: str, operation: str = "send"):
    """
    Decorator to track provider API/SMTP calls

    Usage:
        @track_provider_call(provider="sendgrid", operation="send")
        async def send_via_sendgrid(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                error_type = type(e).__name__
                is_retriable = "timeout" in error_type.lower() or "connection" in error_type.lower()

                provider_errors_total.labels(
                    provider=provider,
                    error_type=error_type,
                    is_retriable=str(is_retriable)
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                provider_response_time.labels(
                    provider=provider,
                    operation=operation
                ).observe(duration)

        return wrapper
    return decorator


# ============================================================================
# Metrics Initialization
# ============================================================================

def initialize_metrics(service_version: str = "1.0.0", environment: str = "production"):
    """
    Initialize service info metrics

    Call this once at application startup
    """
    email_service_info.info({
        "version": service_version,
        "environment": environment,
        "metrics_version": "1.0.0"
    })

    # Set initial gauges
    redis_connected.set(0)
    workers_active.set(0)

    # Initialize provider availability (unknown state)
    for provider in ["sendgrid", "mailgun", "smtp"]:
        provider_available.labels(provider=provider, type="api").set(0)
