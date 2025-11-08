# File: /opt/freeface/email/services/email_service.py
# FreeFace Email System - Email Service
# Main email service interface

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

from config.email_config import EmailConfig
from models.email_models import EmailJob, EmailPriority, EmailProvider
from redis_client_lib.redis_client import RedisEmailClient
from workers.email_worker import EmailWorker


class EmailService:
    """Main email service interface"""

    def __init__(self, config: EmailConfig):
        self.config = config
        self.redis_client = RedisEmailClient(config)
        self.workers = []

    async def initialize(self):
        """Initialize the email service"""
        await self.redis_client.connect()
        logging.info("Email service initialized")

    async def send_email(
        self,
        recipients: Union[str, List[str]],
        template: str,
        data: Dict = None,
        priority: EmailPriority = EmailPriority.MEDIUM,
        provider: EmailProvider = EmailProvider.SMTP,
        scheduled_at: Optional[datetime] = None,
    ) -> str:
        """
        Send email - Main API function

        Args:
            recipients: Email address(es) or group identifier
            template: Template name
            data: Template data
            priority: Email priority (high/medium/low)
            provider: Email provider to use
            scheduled_at: When to send (None = immediate)

        Returns:
            Job ID for tracking
        """
        if data is None:
            data = {}

        # Expand group recipients
        recipients = await self._expand_recipients(recipients)

        # Create email job
        job = EmailJob(
            to=recipients, template=template, data=data, priority=priority, provider=provider, scheduled_at=scheduled_at
        )

        # Queue the job
        if scheduled_at and scheduled_at > datetime.utcnow():
            # Schedule for later
            await self._schedule_email(job)
        else:
            # Queue immediately
            await self.redis_client.enqueue_email(job)

        logging.info(f"Email queued: {job.job_id}, priority: {priority}, recipients: {len(job.to)}")
        return job.job_id

    async def _expand_recipients(self, recipients: Union[str, List[str]]) -> List[str]:
        """Expand group identifiers to email addresses"""
        if isinstance(recipients, list):
            # Already a list of emails
            return recipients

        if recipients.startswith("group:"):
            # Expand group to member emails
            group_id = recipients[6:]  # Remove "group:" prefix
            member_emails = await self.redis_client.redis.lrange(f"group:{group_id}:emails", 0, -1)

            # Remove excluded members
            excluded = await self.redis_client.redis.lrange(f"group:{group_id}:excluded", 0, -1)
            return [email for email in member_emails if email not in excluded]

        return [recipients]  # Single email

    async def _schedule_email(self, job: EmailJob):
        """Schedule email for future delivery"""
        timestamp = int(job.scheduled_at.timestamp())
        await self.redis_client.redis.zadd("email:scheduled", {job.job_id: timestamp})
        await self.redis_client.redis.set(f"email:job:{job.job_id}", job.json(), ex=86400 * 7)

    async def start_workers(self, worker_count: int = 3):
        """Start email workers"""
        for i in range(worker_count):
            worker = EmailWorker(f"worker_{i}", self.config, self.redis_client)
            task = asyncio.create_task(worker.start())
            self.workers.append((worker, task))
            logging.info(f"Created worker task for worker_{i}")

        logging.info(f"Started {worker_count} email workers")

    async def get_stats(self) -> Dict:
        """Get email system statistics"""
        return await self.redis_client.get_stats()

    async def shutdown(self):
        """Shutdown email service"""
        logging.info("Shutting down email service...")

        # Stop workers
        for worker, task in self.workers:
            worker.running = False
            task.cancel()

        # Close Redis connection
        if self.redis_client.redis:
            await self.redis_client.redis.close()
