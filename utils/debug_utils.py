"""
Debug Utilities for FreeFace Email Service

This module provides debugging helpers and utilities to enhance logging
throughout the email service. These tools help track execution flow,
measure performance, and provide detailed context for troubleshooting.

Usage:
    from utils.debug_utils import log_function_call, log_timing, debug_context

    @log_function_call
    async def my_function(param1, param2):
        '''Function calls will be logged with parameters'''
        pass

    with log_timing("database_query"):
        '''Code execution time will be logged'''
        result = await db.query(...)
"""

import functools
import inspect
import logging
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional


def get_logger_for_module(module_name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    This ensures consistent logger naming across the application.
    """
    return logging.getLogger(module_name)


def log_function_call(func: Callable) -> Callable:
    """
    Decorator to log function calls with parameters at DEBUG level.

    Logs:
    - Function name
    - Input parameters (sanitized for sensitive data)
    - Return value (for sync functions)
    - Execution time

    Usage:
        @log_function_call
        async def send_email(recipient, subject):
            ...
    """
    logger = logging.getLogger(func.__module__)

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        # Get function signature for parameter names
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Sanitize sensitive parameters
        sanitized_args = _sanitize_params(bound_args.arguments)

        logger.debug("→ Calling %s(%s)", func.__name__, _format_params(sanitized_args))

        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time

            logger.debug("← %s completed in %.3fs", func.__name__, elapsed)
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error("✗ %s failed after %.3fs: %s", func.__name__, elapsed, e, exc_info=True)
            raise

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        # Get function signature
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        sanitized_args = _sanitize_params(bound_args.arguments)

        logger.debug("→ Calling %s(%s)", func.__name__, _format_params(sanitized_args))

        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time

            logger.debug("← %s completed in %.3fs", func.__name__, elapsed)
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error("✗ %s failed after %.3fs: %s", func.__name__, elapsed, e, exc_info=True)
            raise

    # Return appropriate wrapper based on function type
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


@contextmanager
def log_timing(operation_name: str, logger: Optional[logging.Logger] = None):
    """
    Context manager to log execution time of code blocks.

    Usage:
        with log_timing("redis_query", logger):
            result = await redis.get(key)

    Args:
        operation_name: Name of the operation being timed
        logger: Optional logger instance (uses root logger if not provided)
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    logger.debug("⏱ Starting: %s", operation_name)
    start_time = time.time()

    try:
        yield
        elapsed = time.time() - start_time
        logger.debug("✓ %s completed in %.3fs", operation_name, elapsed)
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error("✗ %s failed after %.3fs: %s", operation_name, elapsed, e, exc_info=True)
        raise


@contextmanager
def debug_context(
    context_name: str, context_data: Dict[str, Any], logger: Optional[logging.Logger] = None
):
    """
    Context manager to log entry/exit with contextual data.

    Useful for tracking state changes and operation flow.

    Usage:
        with debug_context("email_processing", {"job_id": job.job_id, "priority": job.priority}):
            await process_email(job)

    Args:
        context_name: Name of the context/operation
        context_data: Dictionary of contextual data to log
        logger: Optional logger instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    sanitized_data = _sanitize_params(context_data)

    logger.debug("▼ Entering %s: %s", context_name, _format_params(sanitized_data))

    try:
        yield
        logger.debug("▲ Exiting %s: SUCCESS", context_name)
    except Exception as e:
        logger.error("▲ Exiting %s: FAILED - %s", context_name, e, exc_info=True)
        raise


def log_state_change(
    logger: logging.Logger,
    entity: str,
    old_state: Any,
    new_state: Any,
    context: Optional[Dict] = None,
):
    """
    Log a state change with context.

    Useful for tracking job status changes, connection states, etc.

    Usage:
        log_state_change(logger, "job", old_status, new_status, {"job_id": job.job_id})

    Args:
        logger: Logger instance
        entity: Name of the entity changing state
        old_state: Previous state
        new_state: New state
        context: Optional contextual information
    """
    context_str = ""
    if context:
        sanitized = _sanitize_params(context)
        context_str = f" [{_format_params(sanitized)}]"

    logger.debug("State change: %s %s → %s%s", entity, old_state, new_state, context_str)


def log_data_structure(logger: logging.Logger, name: str, data: Any, max_depth: int = 3):
    """
    Log a data structure (dict, list, object) in a readable format.

    Useful for debugging complex data structures at DEBUG level.

    Usage:
        log_data_structure(logger, "email_job", job.dict())

    Args:
        logger: Logger instance
        name: Name/description of the data
        data: Data structure to log
        max_depth: Maximum nesting depth to log
    """
    try:
        import json

        # Try to convert to JSON for nice formatting
        if hasattr(data, "dict"):
            # Pydantic model
            data_dict = data.dict()
        elif hasattr(data, "__dict__"):
            # Regular object
            data_dict = data.__dict__
        else:
            data_dict = data

        sanitized = _sanitize_params(data_dict) if isinstance(data_dict, dict) else data_dict
        formatted = json.dumps(sanitized, indent=2, default=str)

        logger.debug("%s:\n%s", name, formatted)
    except Exception as e:
        # Fallback to repr if JSON fails
        logger.debug("%s: %s", name, repr(data)[:500])  # Limit to 500 chars


def _sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize parameters to avoid logging sensitive data.

    Redacts fields like: password, api_key, secret, token, credential
    """
    sensitive_keys = {"password", "api_key", "secret", "token", "credential", "auth"}

    sanitized = {}
    for key, value in params.items():
        key_lower = str(key).lower()

        # Check if key contains sensitive words
        is_sensitive = any(sensitive in key_lower for sensitive in sensitive_keys)

        if is_sensitive:
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            # Recursively sanitize nested dicts
            sanitized[key] = _sanitize_params(value)
        elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
            # Sanitize list of dicts
            sanitized[key] = [
                _sanitize_params(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            # Truncate very long values
            if isinstance(value, str) and len(value) > 200:
                sanitized[key] = value[:200] + "...[truncated]"
            else:
                sanitized[key] = value

    return sanitized


def _format_params(params: Dict[str, Any]) -> str:
    """
    Format parameters for logging in a compact, readable way.
    """
    if not params:
        return ""

    formatted_parts = []
    for key, value in params.items():
        # Skip 'self' parameter
        if key == "self":
            continue

        if isinstance(value, str):
            formatted_parts.append(f"{key}='{value}'")
        elif isinstance(value, (list, tuple)) and len(value) > 3:
            formatted_parts.append(f"{key}=[{len(value)} items]")
        elif isinstance(value, dict) and len(value) > 3:
            formatted_parts.append(f"{key}={{{len(value)} keys}}")
        else:
            formatted_parts.append(f"{key}={value}")

    return ", ".join(formatted_parts)


def log_redis_operation(
    logger: logging.Logger, operation: str, key: str, details: Optional[Dict] = None
):
    """
    Log Redis operation for debugging queue and caching issues.

    Usage:
        log_redis_operation(logger, "XADD", "email:queue:high", {"job_id": job.job_id})

    Args:
        logger: Logger instance
        operation: Redis command (GET, SET, XADD, etc.)
        key: Redis key being operated on
        details: Optional additional details
    """
    details_str = ""
    if details:
        sanitized = _sanitize_params(details)
        details_str = f" {_format_params(sanitized)}"

    logger.debug("Redis %s: %s%s", operation, key, details_str)


def log_provider_operation(logger: logging.Logger, provider: str, operation: str, details: Dict):
    """
    Log email provider operation for debugging delivery issues.

    Usage:
        log_provider_operation(logger, "smtp", "connect", {"host": "smtp.gmail.com"})

    Args:
        logger: Logger instance
        provider: Provider name (smtp, sendgrid, etc.)
        operation: Operation name (connect, send, etc.)
        details: Operation details
    """
    sanitized = _sanitize_params(details)
    logger.debug("Provider [%s] %s: %s", provider, operation, _format_params(sanitized))
