# File: services/auth_service.py
# Service-to-Service Authentication System
# Provides token-based authentication with audit trail and metrics tracking

import hmac
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Set

from fastapi import HTTPException

logger = logging.getLogger(__name__)


@dataclass
class ServiceIdentity:
    """
    Represents an authenticated service identity

    Attributes:
        name: Human-readable service name (e.g., 'main-app', 'user-service')
        token: The token used for authentication (for logging purposes)
        authenticated_at: Timestamp when authentication occurred
        permissions: Set of allowed operations (future use)
    """
    name: str
    token: str
    authenticated_at: datetime
    permissions: Set[str] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = set()


class ServiceAuthenticator:
    """
    Service-to-service authentication manager

    This class handles:
    - Token verification with timing-attack prevention
    - Service identification (which token belongs to which service)
    - Authentication logging and monitoring
    - Token rotation support (multiple valid tokens per service)

    Environment Variables:
        SERVICE_AUTH_ENABLED: Enable/disable authentication (default: true)
        SERVICE_TOKEN_PREFIX: Required token prefix (default: st_)
        SERVICE_TOKEN_<NAME>: Service token for <NAME> service

    Example:
        SERVICE_AUTH_ENABLED=true
        SERVICE_TOKEN_PREFIX=st_live_
        SERVICE_TOKEN_MAIN_APP=st_live_abc123...
        SERVICE_TOKEN_USER_SERVICE=st_live_def456...
    """

    def __init__(self):
        """Initialize the service authenticator"""
        # Check if authentication is enabled
        self.enabled = os.getenv('SERVICE_AUTH_ENABLED', 'true').lower() == 'true'

        # Token prefix for validation
        self.token_prefix = os.getenv('SERVICE_TOKEN_PREFIX', 'st_')

        # Load service tokens from environment
        self.service_tokens = self._load_service_tokens()

        # Reverse mapping: token -> service name (for quick lookup)
        self.token_to_service = {}
        for service_name, tokens in self.service_tokens.items():
            for token in tokens:
                self.token_to_service[token] = service_name

        # Log initialization
        if self.enabled:
            logger.info(f"Service authentication ENABLED: {len(self.service_tokens)} services configured")
            logger.debug(f"Configured services: {', '.join(self.service_tokens.keys())}")
        else:
            logger.warning("Service authentication DISABLED - all requests will be accepted")

    def _load_service_tokens(self) -> Dict[str, list]:
        """
        Load service tokens from environment variables

        Looks for variables matching pattern: SERVICE_TOKEN_<NAME>
        Also supports: SERVICE_TOKEN_<NAME>_PRIMARY, SERVICE_TOKEN_<NAME>_SECONDARY
        (for token rotation)

        Returns:
            Dict mapping service name to list of valid tokens

        Example:
            {
                'main-app': ['st_live_abc123...'],
                'user-service': ['st_live_def456...', 'st_live_old789...']
            }
        """
        tokens = {}

        # Scan environment for SERVICE_TOKEN_* variables
        for env_key, env_value in os.environ.items():
            if not env_key.startswith('SERVICE_TOKEN_'):
                continue

            # Skip if it's the PREFIX variable
            if env_key == 'SERVICE_TOKEN_PREFIX':
                continue

            # Extract service name from env key
            # SERVICE_TOKEN_MAIN_APP -> main-app
            # SERVICE_TOKEN_USER_SERVICE_PRIMARY -> user-service
            parts = env_key.replace('SERVICE_TOKEN_', '').split('_')

            # Remove _PRIMARY, _SECONDARY suffixes if present
            if parts[-1] in ('PRIMARY', 'SECONDARY', 'BACKUP'):
                parts = parts[:-1]

            # Convert to lowercase, join with hyphens
            service_name = '-'.join(parts).lower()

            # Validate token format
            if not env_value.startswith(self.token_prefix):
                logger.warning(
                    f"Token for service '{service_name}' does not start with "
                    f"required prefix '{self.token_prefix}' - skipping"
                )
                continue

            # Add token to service's token list
            if service_name not in tokens:
                tokens[service_name] = []

            tokens[service_name].append(env_value)
            logger.debug(f"Loaded token for service: {service_name}")

        if not tokens and self.enabled:
            logger.error(
                "SERVICE_AUTH_ENABLED=true but NO service tokens configured! "
                "Add SERVICE_TOKEN_<NAME>=<token> to environment."
            )

        return tokens

    async def verify_token(self, token: str) -> ServiceIdentity:
        """
        Verify a service token and return service identity

        Args:
            token: The service token to verify

        Returns:
            ServiceIdentity object with service details

        Raises:
            HTTPException(401): If token is invalid or missing

        Security:
            - Uses constant-time comparison to prevent timing attacks
            - Validates token prefix to prevent accidents
            - Logs all authentication attempts (success and failure)
        """
        # If authentication is disabled, return dummy identity
        if not self.enabled:
            logger.debug("Authentication disabled - allowing request without token")
            return ServiceIdentity(
                name="unauthenticated",
                token="none",
                authenticated_at=datetime.utcnow()
            )

        # Check token is provided
        if not token:
            logger.warning("Authentication failed: No token provided")
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "authentication_required",
                    "message": "Service token required. Provide X-Service-Token header.",
                    "docs": "See SERVICE_AUTHENTICATION.md for integration guide"
                }
            )

        # Validate token prefix (prevents accidents with wrong secrets)
        if not token.startswith(self.token_prefix):
            logger.warning(
                f"Authentication failed: Invalid token prefix "
                f"(expected '{self.token_prefix}', got '{token[:10]}...')"
            )
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_token_format",
                    "message": f"Service token must start with '{self.token_prefix}'",
                    "provided_prefix": token[:len(self.token_prefix)] if len(token) >= len(self.token_prefix) else token
                }
            )

        # Verify token using constant-time comparison
        service_name = self._verify_token_constant_time(token)

        if not service_name:
            # Token is valid format but not recognized
            logger.warning(
                f"Authentication failed: Unrecognized token "
                f"(prefix: {token[:15]}...)"
            )
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_token",
                    "message": "Service token not recognized. Check token is correct and service is configured.",
                }
            )

        # Authentication successful
        logger.info(f"Service authenticated: {service_name}")
        logger.debug(f"Token used: {token[:20]}...")

        return ServiceIdentity(
            name=service_name,
            token=token,
            authenticated_at=datetime.utcnow()
        )

    def _verify_token_constant_time(self, provided_token: str) -> Optional[str]:
        """
        Verify token using constant-time comparison

        This prevents timing attacks where an attacker could deduce
        the correct token by measuring response times.

        Args:
            provided_token: The token to verify

        Returns:
            Service name if token is valid, None otherwise

        Note:
            Uses hmac.compare_digest() which is designed to prevent
            timing analysis by comparing in constant time.
        """
        for expected_token, service_name in self.token_to_service.items():
            if hmac.compare_digest(provided_token, expected_token):
                return service_name

        return None

    def get_configured_services(self) -> list:
        """
        Get list of all configured service names

        Returns:
            List of service names (strings)

        Example:
            ['main-app', 'user-service', 'notification-service']
        """
        return list(self.service_tokens.keys())

    def is_service_configured(self, service_name: str) -> bool:
        """
        Check if a service is configured

        Args:
            service_name: Service name to check

        Returns:
            True if service has at least one valid token configured
        """
        return service_name in self.service_tokens

    def get_service_info(self) -> dict:
        """
        Get information about configured services

        Returns:
            Dict with service configuration details

        Example:
            {
                'enabled': True,
                'token_prefix': 'st_live_',
                'services_count': 3,
                'services': ['main-app', 'user-service', 'notification-service']
            }
        """
        return {
            'enabled': self.enabled,
            'token_prefix': self.token_prefix,
            'services_count': len(self.service_tokens),
            'services': self.get_configured_services()
        }


# Global authenticator instance
# Initialized once when module is imported
authenticator = ServiceAuthenticator()
