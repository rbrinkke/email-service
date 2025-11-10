"""
Structured Logging Configuration with structlog

This module provides production-grade structured (JSON) logging that is:
- Machine-readable for log aggregators (Datadog, CloudWatch, ELK, etc.)
- Human-readable in development
- Compatible with existing Python logging
- Includes automatic context (request_id, service_name, etc.)

WHY STRUCTURED LOGGING IS CRITICAL:
===============================
1. Log Aggregation: JSON logs can be parsed and indexed by Datadog, CloudWatch, etc.
2. Filtering: Easily filter by request_id, service_name, error_type, etc.
3. Alerting: Set up alerts based on structured fields (e.g., status_code >= 500)
4. Cost Efficiency: Structured logs compress better and are more efficient to store
5. Debugging: Trace a single request through all services using request_id

Based on best practices from the expert FastAPI + Uvicorn logging guide.
"""

import logging
import sys

import structlog

from .logging_config import get_environment, get_log_level


def setup_structured_logging(enable_json: bool = None):
    """
    Setup structlog for structured logging throughout the application.

    This configures structlog to:
    1. Work with Python's standard logging module
    2. Output JSON in production (machine-readable)
    3. Output colored, pretty logs in development (human-readable)
    4. Include context processors for automatic field injection

    Args:
        enable_json: Force JSON output (default: based on ENVIRONMENT variable)
                    production/staging = JSON, development = pretty console

    Usage:
        # At application startup (before any logging):
        from config.structured_logging import setup_structured_logging
        setup_structured_logging()

        # Then use structlog instead of logging:
        import structlog
        logger = structlog.get_logger(__name__)
        logger.info("user_logged_in", user_id=123, email="user@example.com")

        # Output (production/JSON):
        # {"event": "user_logged_in", "user_id": 123, "email": "user@example.com",
        #  "timestamp": "2025-11-10T14:30:00Z", "level": "info", "logger": "api"}

        # Output (development/console):
        # 2025-11-10 14:30:00 [info     ] user_logged_in    user_id=123 email=user@example.com
    """

    # Determine if we should use JSON format
    if enable_json is None:
        environment = get_environment()
        # Use JSON in production/staging, pretty console in development
        enable_json = environment in ["production", "staging"]

    # Configure structlog processors
    # These run in order and transform/enrich log records
    processors = [
        # CRITICAL: Merge context vars (trace_id, user_id, etc.) into log records
        # This makes trace_id automatically appear in every log message
        structlog.contextvars.merge_contextvars,
        # Add log level to event dict
        structlog.stdlib.add_log_level,
        # Add logger name to event dict (service name)
        structlog.stdlib.add_logger_name,
        # Add timestamp in ISO format with timezone (observability stack requirement)
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Add stack info for exceptions
        structlog.processors.StackInfoRenderer(),
        # Format exceptions properly
        structlog.processors.format_exc_info,
        # Decode unicode
        structlog.processors.UnicodeDecoder(),
    ]

    # Add appropriate renderer based on environment
    if enable_json:
        # Production: JSON renderer for log aggregators
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Development: Pretty console renderer with colors
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.RichTracebackFormatter(),
            )
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        # Use LoggerFactory to integrate with stdlib logging
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Wrap logger to add bind() and other methods
        wrapper_class=structlog.stdlib.BoundLogger,
        # Cache loggers for performance
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use structlog's ProcessorFormatter
    # This ensures logs from third-party libraries also get structured
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer() if enable_json
        else structlog.dev.ConsoleRenderer(colors=True),
    )

    # Update all existing handlers to use structured formatter
    root_logger = logging.getLogger()

    for handler in root_logger.handlers:
        handler.setFormatter(formatter)

    # Log configuration info
    logger = structlog.get_logger(__name__)
    logger.info(
        "structured_logging_configured",
        format="json" if enable_json else "console",
        environment=get_environment(),
        log_level=get_log_level(),
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    This is a convenience wrapper around structlog.get_logger() that ensures
    the logger name is set correctly.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Bound logger instance

    Usage:
        logger = get_logger(__name__)
        logger.info("event_name", key1="value1", key2="value2")
    """
    return structlog.get_logger(name)


def bind_context(**kwargs):
    """
    Bind context to the current thread/async context.

    This context will be automatically included in all log messages
    within this context.

    Args:
        **kwargs: Key-value pairs to bind (e.g., request_id, user_id)

    Usage:
        # In middleware or request handler:
        bind_context(request_id=request_id, service_name=service_name)

        # All subsequent logs will include these fields automatically:
        logger.info("processing_request")  # Includes request_id and service_name
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context():
    """
    Clear all bound context.

    Should be called at the end of request processing to avoid
    context leaking between requests.
    """
    structlog.contextvars.clear_contextvars()


def unbind_context(*keys):
    """
    Remove specific keys from bound context.

    Args:
        *keys: Keys to remove from context
    """
    structlog.contextvars.unbind_contextvars(*keys)


# Example usage and output documentation
"""
EXAMPLE USAGE:
=============

# Setup (in main.py or api.py startup):
from config.structured_logging import setup_structured_logging
setup_structured_logging()

# Get logger:
import structlog
logger = structlog.get_logger(__name__)

# Basic logging:
logger.info("user_registered", user_id=123, email="user@example.com")

# With bound context (in middleware):
from config.structured_logging import bind_context, clear_context

bind_context(request_id="abc123", service_name="email-api")
logger.info("processing_email", job_id="job_456")
clear_context()

# Error logging with exception:
try:
    raise ValueError("Invalid email")
except Exception as e:
    logger.error("email_validation_failed", error=str(e), exc_info=True)


JSON OUTPUT (production):
=========================
{
  "event": "user_registered",
  "user_id": 123,
  "email": "user@example.com",
  "timestamp": "2025-11-10T14:30:00.123456Z",
  "level": "info",
  "logger": "services.email_service"
}

{
  "event": "processing_email",
  "job_id": "job_456",
  "request_id": "abc123",
  "service_name": "email-api",
  "timestamp": "2025-11-10T14:30:01.456789Z",
  "level": "info",
  "logger": "services.email_service"
}


CONSOLE OUTPUT (development):
==============================
2025-11-10 14:30:00 [info     ] user_registered        user_id=123 email=user@example.com
2025-11-10 14:30:01 [info     ] processing_email       job_id=job_456 request_id=abc123 service_name=email-api
"""
