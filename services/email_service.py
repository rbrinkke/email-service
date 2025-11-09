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
from utils.debug_utils import debug_context, log_data_structure, log_state_change, log_timing
from workers.email_worker import EmailWorker

logger = logging.getLogger(__name__)


class EmailService:
    """Main email service interface"""

    def __init__(self, config: EmailConfig):
        self.config = config
        self.redis_client = RedisEmailClient(config)
        self.workers = []

        logger.debug(
            "EmailService initialized with config: redis=%s:%s", config.redis_host, config.redis_port
        )

    async def initialize(self):
        """Initialize the email service"""
        logger.debug("Initializing email service - connecting to Redis...")

        with log_timing("redis_connection", logger):
            await self.redis_client.connect()

        logger.info("Email service initialized and connected to Redis")
        logger.debug(
            "Redis connection established: %s:%s", self.config.redis_host, self.config.redis_port
        )

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
            "send_email called: recipients=%s, template=%s, priority=%s, provider=%s, scheduled=%s",
            recipients, template, priority.value, provider.value, scheduled_at is not None
        )

        # Expand group recipients
        with log_timing(
            f"expand_recipients_{recipients if isinstance(recipients, str) else 'list'}", logger
        ):
            recipients = await self._expand_recipients(recipients)

        logger.debug("Recipients expanded to %s email(s)", len(recipients))

        # Create email job
        job = EmailJob(
            to=recipients,
            template=template,
            data=data,
            priority=priority,
            provider=provider,
            scheduled_at=scheduled_at,
        )

        logger.debug("Email job created: %s", job.job_id)

        # Log job details at DEBUG level
        if logger.isEnabledFor(logging.DEBUG):
            log_data_structure(logger, "EmailJob %s" % job.job_id, job)

        # Queue the job
        if scheduled_at and scheduled_at > datetime.utcnow():
            # Schedule for later
            logger.debug("Scheduling email %s for %s", job.job_id, scheduled_at)
            await self._schedule_email(job)
            logger.info("Email scheduled: %s, delivery at: %s", job.job_id, scheduled_at)
        else:
            # Queue immediately
            logger.debug("Queueing email %s to %s queue", job.job_id, priority.value)

            with log_timing(f"enqueue_{priority.value}", logger):
                stream_id = await self.redis_client.enqueue_email(job)

            logger.debug("Email queued with stream_id: %s", stream_id)
            logger.info(
                "Email queued: %s, priority: %s, recipients: %s", job.job_id, priority.value, len(job.to)
            )

        return job.job_id

    async def _expand_recipients(self, recipients: Union[str, List[str]]) -> List[str]:
        """Expand group identifiers to email addresses"""
        if isinstance(recipients, list):
            # Already a list of emails
            logger.debug("Recipients already a list of %s email(s)", len(recipients))
            return recipients

        if recipients.startswith("group:"):
            # Expand group to member emails
            group_id = recipients[6:]  # Remove "group:" prefix

            logger.debug("Expanding group: %s", group_id)

            with log_timing(f"redis_lrange_group_{group_id}", logger):
                member_emails = await self.redis_client.redis.lrange(
                    f"group:{group_id}:emails", 0, -1
                )

            logger.debug("Group %s has %s member(s)", group_id, len(member_emails))

            # Remove excluded members
            with log_timing(f"redis_lrange_excluded_{group_id}", logger):
                excluded = await self.redis_client.redis.lrange(f"group:{group_id}:excluded", 0, -1)

            if excluded:
                logger.debug("Group %s has %s excluded member(s)", group_id, len(excluded))
                filtered = [email for email in member_emails if email not in excluded]
                logger.debug("After filtering: %s recipient(s)", len(filtered))
                return filtered

            return member_emails

        logger.debug("Single recipient: %s", recipients)
        return [recipients]  # Single email

    async def _schedule_email(self, job: EmailJob):
        """Schedule email for future delivery"""
        timestamp = int(job.scheduled_at.timestamp())

        logger.debug("Scheduling job %s for timestamp %s (%s)", job.job_id, timestamp, job.scheduled_at)

        with log_timing(f"redis_zadd_scheduled_{job.job_id}", logger):
            await self.redis_client.redis.zadd("email:scheduled", {job.job_id: timestamp})

        with log_timing(f"redis_set_job_{job.job_id}", logger):
            await self.redis_client.redis.set(f"email:job:{job.job_id}", job.json(), ex=86400 * 7)

        logger.debug("Job %s scheduled successfully", job.job_id)

    async def start_workers(self, worker_count: int = 3):
        """Start email workers"""
        logger.info("Starting %s email worker(s)...", worker_count)

        for i in range(worker_count):
            worker_id = f"worker_{i}"

            logger.debug("Creating worker: %s", worker_id)

            worker = EmailWorker(worker_id, self.config, self.redis_client)
            task = asyncio.create_task(worker.start())
            self.workers.append((worker, task))

            logger.debug("Worker task created for %s", worker_id)
            logger.info("Created worker task for %s", worker_id)

        logger.info("Started %s email workers", worker_count)
        logger.debug("Active workers: %s", [w.worker_id for w, _ in self.workers])

    async def get_stats(self) -> Dict:
        """Get email system statistics"""
        logger.debug("Fetching email system statistics from Redis")

        with log_timing("get_stats", logger):
            stats = await self.redis_client.get_stats()

        logger.debug("Stats retrieved: %s", stats)

        return stats

    async def shutdown(self):
        """Shutdown email service"""
        logger.info("Shutting down email service...")

        # Stop workers
        logger.debug("Stopping %s worker(s)...", len(self.workers))

        for worker, task in self.workers:
            logger.debug("Stopping worker: %s", worker.worker_id)
            worker.running = False
            task.cancel()

        logger.info("All workers stopped")

        # Close Redis connection
        if self.redis_client.redis:
            logger.debug("Closing Redis connection...")
            await self.redis_client.redis.close()
            logger.info("Redis connection closed")

        logger.info("Email service shutdown complete")
