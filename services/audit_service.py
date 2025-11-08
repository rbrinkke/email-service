# File: services/audit_service.py
# Service Audit Trail and Metrics Tracking
# Provides Redis-based audit logging for service-to-service calls

import logging
from datetime import datetime, date
from typing import Dict, Optional
import json

logger = logging.getLogger(__name__)


class ServiceAuditTrail:
    """
    Audit trail and metrics tracking for service calls

    Stores audit information in Redis:
    - Which service called which endpoint
    - When the call occurred
    - Job IDs associated with service calls
    - Per-service metrics (calls, emails sent)

    Redis key patterns:
    - service:audit:{job_id} - Audit record for specific job
    - service:calls:{service}:{date} - Sorted set of calls by service
    - service:metrics:{service}:total_calls - Total calls counter
    - service:metrics:{service}:total_emails - Total emails counter
    - service:metrics:{service}:{endpoint} - Per-endpoint call counter
    """

    def __init__(self, redis_client=None):
        """
        Initialize audit trail

        Args:
            redis_client: Redis client instance (optional, can be set later)
        """
        self.redis_client = redis_client
        self.enabled = True  # Can be disabled for testing

    def set_redis_client(self, redis_client):
        """
        Set Redis client (for lazy initialization)

        Args:
            redis_client: Redis client instance
        """
        self.redis_client = redis_client

    async def log_service_call(
        self,
        service_name: str,
        endpoint: str,
        job_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Log a service call to Redis audit trail

        Args:
            service_name: Name of the calling service
            endpoint: API endpoint that was called
            job_id: Email job ID (if applicable)
            metadata: Additional metadata (recipients, template, etc.)

        Example:
            await audit.log_service_call(
                service_name="main-app",
                endpoint="/send",
                job_id="job_abc123",
                metadata={"template": "welcome", "recipient_count": 1}
            )
        """
        if not self.enabled or not self.redis_client:
            logger.debug("Audit logging disabled or Redis not available")
            return

        try:
            timestamp = datetime.utcnow()
            today = date.today().isoformat()

            # Create audit record
            audit_record = {
                "service": service_name,
                "endpoint": endpoint,
                "timestamp": timestamp.isoformat(),
                "job_id": job_id,
                **(metadata or {})
            }

            # Store audit record for this job (if job_id provided)
            if job_id:
                await self._store_job_audit(job_id, audit_record)

            # Add to service's call log (sorted by timestamp)
            await self._log_service_call_timeline(service_name, today, timestamp, endpoint)

            # Increment metrics counters
            await self._increment_metrics(service_name, endpoint, metadata)

            logger.debug(
                f"Audit logged: service={service_name}, endpoint={endpoint}, "
                f"job_id={job_id}"
            )

        except Exception as e:
            # Never let audit logging break the main flow
            logger.error(f"Failed to log audit trail: {e}", exc_info=True)

    async def _store_job_audit(self, job_id: str, audit_record: Dict):
        """
        Store audit record for a specific job

        Args:
            job_id: Email job ID
            audit_record: Audit information
        """
        key = f"service:audit:{job_id}"

        # Store as Redis hash
        await self.redis_client.client.hset(
            key,
            mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                    for k, v in audit_record.items()}
        )

        # Set TTL: keep audit records for 30 days
        await self.redis_client.client.expire(key, 30 * 24 * 60 * 60)

    async def _log_service_call_timeline(
        self,
        service_name: str,
        today: str,
        timestamp: datetime,
        endpoint: str
    ):
        """
        Add call to service's timeline (sorted set)

        Args:
            service_name: Service name
            today: Date string (YYYY-MM-DD)
            timestamp: Call timestamp
            endpoint: Endpoint called
        """
        key = f"service:calls:{service_name}:{today}"

        # Store in sorted set (score = timestamp, value = endpoint)
        score = timestamp.timestamp()
        value = f"{timestamp.isoformat()}|{endpoint}"

        await self.redis_client.client.zadd(key, {value: score})

        # Set TTL: keep daily call logs for 90 days
        await self.redis_client.client.expire(key, 90 * 24 * 60 * 60)

    async def _increment_metrics(
        self,
        service_name: str,
        endpoint: str,
        metadata: Optional[Dict]
    ):
        """
        Increment service metrics counters

        Args:
            service_name: Service name
            endpoint: Endpoint called
            metadata: Call metadata
        """
        # Total calls for this service
        await self.redis_client.client.incr(
            f"service:metrics:{service_name}:total_calls"
        )

        # Calls per endpoint
        await self.redis_client.client.incr(
            f"service:metrics:{service_name}:{endpoint}"
        )

        # If this was an email send, increment email counter
        if metadata and metadata.get('recipient_count'):
            recipient_count = metadata['recipient_count']
            await self.redis_client.client.incrby(
                f"service:metrics:{service_name}:total_emails",
                recipient_count
            )

    async def get_job_audit(self, job_id: str) -> Optional[Dict]:
        """
        Get audit record for a specific job

        Args:
            job_id: Email job ID

        Returns:
            Audit record dict or None if not found

        Example:
            {
                "service": "main-app",
                "endpoint": "/send",
                "timestamp": "2025-11-08T14:30:00",
                "template": "welcome"
            }
        """
        if not self.redis_client:
            return None

        try:
            key = f"service:audit:{job_id}"
            record = await self.redis_client.client.hgetall(key)

            if not record:
                return None

            # Parse JSON values
            parsed = {}
            for k, v in record.items():
                try:
                    parsed[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    parsed[k] = v

            return parsed

        except Exception as e:
            logger.error(f"Failed to get job audit: {e}")
            return None

    async def get_service_metrics(self, service_name: str) -> Dict:
        """
        Get metrics for a specific service

        Args:
            service_name: Service name

        Returns:
            Dict with service metrics

        Example:
            {
                "total_calls": 1247,
                "total_emails": 5623,
                "calls_today": 45,
                "endpoints": {
                    "/send": 800,
                    "/send/welcome": 300,
                    "/send/password-reset": 100
                }
            }
        """
        if not self.redis_client:
            return {}

        try:
            today = date.today().isoformat()

            # Get total counters
            total_calls = await self.redis_client.client.get(
                f"service:metrics:{service_name}:total_calls"
            )
            total_emails = await self.redis_client.client.get(
                f"service:metrics:{service_name}:total_emails"
            )

            # Get today's calls
            calls_today_key = f"service:calls:{service_name}:{today}"
            calls_today = await self.redis_client.client.zcard(calls_today_key)

            # Get per-endpoint metrics
            pattern = f"service:metrics:{service_name}:/*"
            endpoint_keys = []

            # Scan for endpoint metric keys
            cursor = 0
            while True:
                cursor, keys = await self.redis_client.client.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                endpoint_keys.extend(keys)
                if cursor == 0:
                    break

            # Get endpoint counts
            endpoints = {}
            for key in endpoint_keys:
                # Extract endpoint from key
                # service:metrics:main-app:/send -> /send
                endpoint = key.split(':', 3)[-1]

                # Skip non-endpoint metrics
                if endpoint in ('total_calls', 'total_emails'):
                    continue

                count = await self.redis_client.client.get(key)
                endpoints[endpoint] = int(count) if count else 0

            return {
                "total_calls": int(total_calls) if total_calls else 0,
                "total_emails": int(total_emails) if total_emails else 0,
                "calls_today": calls_today,
                "endpoints": endpoints
            }

        except Exception as e:
            logger.error(f"Failed to get service metrics: {e}")
            return {}

    async def get_all_services_metrics(self) -> Dict[str, Dict]:
        """
        Get metrics for all services

        Returns:
            Dict mapping service name to metrics

        Example:
            {
                "main-app": {"total_calls": 1247, ...},
                "user-service": {"total_calls": 523, ...}
            }
        """
        if not self.redis_client:
            return {}

        try:
            # Find all services with metrics
            pattern = "service:metrics:*:total_calls"
            service_names = set()

            cursor = 0
            while True:
                cursor, keys = await self.redis_client.client.scan(
                    cursor,
                    match=pattern,
                    count=100
                )

                for key in keys:
                    # Extract service name
                    # service:metrics:main-app:total_calls -> main-app
                    parts = key.split(':')
                    if len(parts) >= 3:
                        service_names.add(parts[2])

                if cursor == 0:
                    break

            # Get metrics for each service
            all_metrics = {}
            for service_name in service_names:
                metrics = await self.get_service_metrics(service_name)
                if metrics:
                    all_metrics[service_name] = metrics

            return all_metrics

        except Exception as e:
            logger.error(f"Failed to get all services metrics: {e}")
            return {}


# Global audit trail instance
# Will be initialized with Redis client when available
audit_trail = ServiceAuditTrail()
