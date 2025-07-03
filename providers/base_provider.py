# File: /opt/freeface/email/providers/base_provider.py
# FreeFace Email System - Base Email Provider
# Base class for all email providers with circuit breaker protection

from typing import Dict
from ..workers.circuit_breaker import CircuitBreaker
from ..models.email_models import EmailJob
from ..redis.redis_client import RedisEmailClient

class EmailProviderBase:
    """Base class for email providers"""
    
    def __init__(self, name: str, config: Dict, redis_client: RedisEmailClient):
        self.name = name
        self.config = config
        self.redis_client = redis_client
        self.circuit_breaker = CircuitBreaker()
    
    async def send_email(self, job: EmailJob) -> bool:
        """Send email with circuit breaker protection"""
        if not self.circuit_breaker.can_execute():
            raise Exception(f"Circuit breaker OPEN for {self.name}")
        
        try:
            # Check rate limit
            if not await self.redis_client.check_rate_limit(self.name, len(job.to)):
                raise Exception(f"Rate limit exceeded for {self.name}")
            
            # Send email
            success = await self._send_email_impl(job)
            
            if success:
                self.circuit_breaker.record_success()
            else:
                self.circuit_breaker.record_failure()
            
            return success
            
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise
    
    async def _send_email_impl(self, job: EmailJob) -> bool:
        """Provider-specific implementation"""
        raise NotImplementedError
