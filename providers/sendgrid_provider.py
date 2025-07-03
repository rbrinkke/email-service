# File: /opt/freeface/email/providers/sendgrid_provider.py
# FreeFace Email System - SendGrid Provider
# SendGrid email provider using HTTP API

import asyncio
from typing import Dict, Optional

import aiohttp
import backoff

from .base_provider import EmailProviderBase
from models.email_models import EmailJob
from redis_client_lib.redis_client import RedisEmailClient

class SendGridProvider(EmailProviderBase):
    """SendGrid email provider using HTTP API"""
    
    def __init__(self, config: Dict, redis_client: RedisEmailClient):
        super().__init__("sendgrid", config, redis_client)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    'Authorization': f'Bearer {self.config["api_key"]}',
                    'Content-Type': 'application/json'
                }
            )
        return self.session
    
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=30
    )
    async def _send_email_impl(self, job: EmailJob) -> bool:
        """Send email via SendGrid API"""
        session = await self._get_session()
        
        # Prepare SendGrid payload
        personalizations = []
        for email in job.to:
            personalizations.append({
                "to": [{"email": email}],
                "dynamic_template_data": job.data
            })
        
        payload = {
            "personalizations": personalizations,
            "from": {"email": self.config["from_email"]},
            "template_id": job.template  # Assuming SendGrid template ID
        }
        
        async with session.post(self.config["api_url"], json=payload) as response:
            if response.status == 202:
                return True
            else:
                error_text = await response.text()
                raise Exception(f"SendGrid error {response.status}: {error_text}")
