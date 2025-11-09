# File: mocks/common/error_simulator.py
# Configurable error simulation for testing error handling

import random
from datetime import datetime
from typing import Dict, Optional

from fastapi import HTTPException


class ErrorSimulator:
    """
    Simulate various error conditions for testing

    Supports:
    - HTTP error codes (4xx, 5xx)
    - Random error injection
    - Rate limiting errors
    - Timeout simulation
    - Network errors

    Usage:
        simulator = ErrorSimulator(error_rate=0.1)  # 10% error rate
        simulator.maybe_raise_error()  # Randomly raises error
        simulator.raise_not_found("User not found")
        simulator.raise_rate_limit()
    """

    def __init__(self, error_rate: float = 0.0):
        """
        Initialize error simulator

        Args:
            error_rate: Probability of random error (0.0 to 1.0)
        """
        self.error_rate = error_rate

    def maybe_raise_error(self):
        """
        Randomly raise an error based on configured error_rate

        Raises:
            HTTPException: Random 5xx error if triggered
        """
        if self.error_rate > 0 and random.random() < self.error_rate:
            error_code = random.choice([500, 502, 503])
            raise HTTPException(
                status_code=error_code,
                detail=self._error_detail(
                    error=f"random_error_{error_code}",
                    message=f"Randomly simulated {error_code} error"
                )
            )

    def raise_bad_request(self, message: str, details: Optional[Dict] = None):
        """
        Raise 400 Bad Request error

        Args:
            message: Error message
            details: Optional additional details
        """
        raise HTTPException(
            status_code=400,
            detail=self._error_detail(
                error="bad_request",
                message=message,
                details=details
            )
        )

    def raise_unauthorized(self, message: str = "Authentication required"):
        """
        Raise 401 Unauthorized error

        Args:
            message: Error message
        """
        raise HTTPException(
            status_code=401,
            detail=self._error_detail(
                error="unauthorized",
                message=message
            )
        )

    def raise_forbidden(self, message: str = "Access forbidden"):
        """
        Raise 403 Forbidden error

        Args:
            message: Error message
        """
        raise HTTPException(
            status_code=403,
            detail=self._error_detail(
                error="forbidden",
                message=message
            )
        )

    def raise_not_found(self, resource: str, resource_id: str):
        """
        Raise 404 Not Found error

        Args:
            resource: Resource type (e.g., "user", "group")
            resource_id: Resource identifier
        """
        raise HTTPException(
            status_code=404,
            detail=self._error_detail(
                error="not_found",
                message=f"{resource.title()} not found",
                details={"resource": resource, "id": resource_id}
            )
        )

    def raise_conflict(self, message: str, details: Optional[Dict] = None):
        """
        Raise 409 Conflict error

        Args:
            message: Error message
            details: Optional additional details
        """
        raise HTTPException(
            status_code=409,
            detail=self._error_detail(
                error="conflict",
                message=message,
                details=details
            )
        )

    def raise_validation_error(self, message: str, field: str):
        """
        Raise 422 Validation error

        Args:
            message: Error message
            field: Field that failed validation
        """
        raise HTTPException(
            status_code=422,
            detail=self._error_detail(
                error="validation_error",
                message=message,
                details={"field": field}
            )
        )

    def raise_rate_limit(
        self,
        limit: int = 100,
        window: str = "1 hour",
        retry_after: int = 3600
    ):
        """
        Raise 429 Too Many Requests error

        Args:
            limit: Rate limit threshold
            window: Time window
            retry_after: Seconds until retry
        """
        raise HTTPException(
            status_code=429,
            detail=self._error_detail(
                error="rate_limit_exceeded",
                message=f"Rate limit exceeded: {limit} requests per {window}",
                details={
                    "limit": limit,
                    "window": window,
                    "retry_after": retry_after
                }
            ),
            headers={"Retry-After": str(retry_after)}
        )

    def raise_internal_error(self, message: str = "Internal server error"):
        """
        Raise 500 Internal Server Error

        Args:
            message: Error message
        """
        raise HTTPException(
            status_code=500,
            detail=self._error_detail(
                error="internal_error",
                message=message
            )
        )

    def raise_service_unavailable(
        self,
        message: str = "Service temporarily unavailable",
        retry_after: int = 60
    ):
        """
        Raise 503 Service Unavailable error

        Args:
            message: Error message
            retry_after: Seconds until retry
        """
        raise HTTPException(
            status_code=503,
            detail=self._error_detail(
                error="service_unavailable",
                message=message,
                details={"retry_after": retry_after}
            ),
            headers={"Retry-After": str(retry_after)}
        )

    def _error_detail(
        self,
        error: str,
        message: str,
        details: Optional[Dict] = None
    ) -> Dict:
        """
        Create standardized error detail following RFC 7807

        Args:
            error: Error code/type
            message: Human-readable message
            details: Optional additional details

        Returns:
            Error detail dict
        """
        detail = {
            "error": error,
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        if details:
            detail["details"] = details

        return detail
