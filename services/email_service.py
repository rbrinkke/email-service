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
from utils.debug_utils import log_timing, debug_context, log_state_change, log_data_structure

logger = logging.getLogger(__name__)


class EmailService:
    """Main email service interface"""

    def __init__(self, config: EmailConfig):
        self.config = config
        self.redis_client = RedisEmailClient(config)
        self.workers = []

        logger.debug(f"EmailService initialized with config: redis={config.redis_host}:{config.redis_port}")

    async def initialize(self):
        """Initialize the email service"""
        logger.debug("Initializing email service - connecting to Redis...")

        with log_timing("redis_connection", logger):
            await self.redis_client.connect()

        logger.info("Email service initialized and connected to Redis")
        logger.debug(f"Redis connection established: {self.config.redis_host}:{self.config.redis_port}")

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

        # Log the incoming request at DEBUG level
        logger.debug(
            f"send_email called: recipients={recipients}, template={template}, "
            f"priority={priority.value}, provider={provider.value}, "
            f"scheduled={scheduled_at is not None}"
        )

        # Expand group recipients
        with log_timing(f"expand_recipients_{recipients if isinstance(recipients, str) else 'list'}", logger):
            recipients = await self._expand_recipients(recipients)

        logger.debug(f"Recipients expanded to {len(recipients)} email(s)")

        # Create email job
        job = EmailJob(
            to=recipients, template=template, data=data, priority=priority, provider=provider, scheduled_at=scheduled_at
        )

        logger.debug(f"Email job created: {job.job_id}")

        # Log job details at DEBUG level
        if logger.isEnabledFor(logging.DEBUG):
            log_data_structure(logger, f"EmailJob {job.job_id}", job)

        # Queue the job
        if scheduled_at and scheduled_at > datetime.utcnow():
            # Schedule for later
            logger.debug(f"Scheduling email {job.job_id} for {scheduled_at}")
            await self._schedule_email(job)
            logger.info(f"Email scheduled: {job.job_id}, delivery at: {scheduled_at}")
        else:
            # Queue immediately
            logger.debug(f"Queueing email {job.job_id} to {priority.value} queue")

            with log_timing(f"enqueue_{priority.value}", logger):
                stream_id = await self.redis_client.enqueue_email(job)

            logger.debug(f"Email queued with stream_id: {stream_id}")
            logger.info(f"Email queued: {job.job_id}, priority: {priority.value}, recipients: {len(job.to)}")

        return job.job_id

    async def _expand_recipients(self, recipients: Union[str, List[str]]) -> List[str]:
        """Expand group identifiers to email addresses"""
        if isinstance(recipients, list):
            # Already a list of emails
            logger.debug(f"Recipients already a list of {len(recipients)} email(s)")
            return recipients

        if recipients.startswith("group:"):
            # Expand group to member emails
            group_id = recipients[6:]  # Remove "group:" prefix

            logger.debug(f"Expanding group: {group_id}")

            with log_timing(f"redis_lrange_group_{group_id}", logger):
                member_emails = await self.redis_client.redis.lrange(f"group:{group_id}:emails", 0, -1)

            logger.debug(f"Group {group_id} has {len(member_emails)} member(s)")

            # Remove excluded members
            with log_timing(f"redis_lrange_excluded_{group_id}", logger):
                excluded = await self.redis_client.redis.lrange(f"group:{group_id}:excluded", 0, -1)

            if excluded:
                logger.debug(f"Group {group_id} has {len(excluded)} excluded member(s)")
                filtered = [email for email in member_emails if email not in excluded]
                logger.debug(f"After filtering: {len(filtered)} recipient(s)")
                return filtered

            return member_emails

        logger.debug(f"Single recipient: {recipients}")
        return [recipients]  # Single email

    async def _schedule_email(self, job: EmailJob):
        """Schedule email for future delivery"""
        timestamp = int(job.scheduled_at.timestamp())

        logger.debug(f"Scheduling job {job.job_id} for timestamp {timestamp} ({job.scheduled_at})")

        with log_timing(f"redis_zadd_scheduled_{job.job_id}", logger):
            await self.redis_client.redis.zadd("email:scheduled", {job.job_id: timestamp})

        with log_timing(f"redis_set_job_{job.job_id}", logger):
            await self.redis_client.redis.set(f"email:job:{job.job_id}", job.json(), ex=86400 * 7)

        logger.debug(f"Job {job.job_id} scheduled successfully")

    async def start_workers(self, worker_count: int = 3):
        """Start email workers"""
        logger.info(f"Starting {worker_count} email worker(s)...")

        for i in range(worker_count):
            worker_id = f"worker_{i}"

            logger.debug(f"Creating worker: {worker_id}")

            worker = EmailWorker(worker_id, self.config, self.redis_client)
            task = asyncio.create_task(worker.start())
            self.workers.append((worker, task))

            logger.debug(f"Worker task created for {worker_id}")
            logger.info(f"Created worker task for {worker_id}")

        logger.info(f"Started {worker_count} email workers")
        logger.debug(f"Active workers: {[w.worker_id for w, _ in self.workers]}")

    async def get_stats(self) -> Dict:
        """Get email system statistics"""
        logger.debug("Fetching email system statistics from Redis")

        with log_timing("get_stats", logger):
            stats = await self.redis_client.get_stats()

        logger.debug(f"Stats retrieved: {stats}")

        return stats

    async def shutdown(self):
        """Shutdown email service"""
        logger.info("Shutting down email service...")

        # Stop workers
        logger.debug(f"Stopping {len(self.workers)} worker(s)...")

        for worker, task in self.workers:
            logger.debug(f"Stopping worker: {worker.worker_id}")
            worker.running = False
            task.cancel()

        logger.info("All workers stopped")

        # Close Redis connection
        if self.redis_client.redis:
            logger.debug("Closing Redis connection...")
            await self.redis_client.redis.close()
            logger.info("Redis connection closed")

        logger.info("Email service shutdown complete")
