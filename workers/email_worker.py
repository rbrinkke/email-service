# File: /opt/freeface/email/workers/email_worker.py
# FreeFace Email System - Email Worker
# High-performance async email worker

import asyncio
import logging
from datetime import datetime
from typing import Dict

from config.email_config import EmailConfig
from models.email_models import EmailJob, EmailStatus
from providers.sendgrid_provider import SendGridProvider
from providers.smtp_provider import SMTPProvider
from redis_client_lib.redis_client import RedisEmailClient


class EmailWorker:
    """High-performance async email worker"""

    def __init__(self, worker_id: str, config: EmailConfig, redis_client: RedisEmailClient):
        self.worker_id = worker_id
        self.config = config
        self.redis_client = redis_client
        self.providers = {}
        self.running = False
        self.stats = {"processed": 0, "sent": 0, "failed": 0, "started_at": None}

    async def initialize_providers(self):
        """Initialize email providers"""
        for provider_name, provider_config in self.config.providers.items():
            if provider_name == "sendgrid":
                self.providers[provider_name] = SendGridProvider(provider_config, self.redis_client)
            elif provider_name == "smtp":
                self.providers[provider_name] = SMTPProvider(provider_config, self.redis_client)
            # Add other providers as needed

    async def start(self):
        """Start the email worker"""
        try:
            logging.info(f"Initializing providers for worker {self.worker_id}")
            await self.initialize_providers()
            self.running = True
            self.stats["started_at"] = datetime.utcnow()

            logging.info(f"Email worker {self.worker_id} started, creating tasks...")

            # Start concurrent tasks
            tasks = [
                asyncio.create_task(self._process_emails()),
                asyncio.create_task(self._process_retries()),
                asyncio.create_task(self._report_stats()),
            ]

            logging.info(f"Worker {self.worker_id} created {len(tasks)} tasks, starting main loop")

            try:
                await asyncio.gather(*tasks)
            except Exception as e:
                logging.error(f"Worker {self.worker_id} error: {e}")
                import traceback

                logging.error(traceback.format_exc())
        except Exception as e:
            logging.error(f"Worker {self.worker_id} startup error: {e}")
            import traceback

            logging.error(traceback.format_exc())
        finally:
            self.running = False

    async def _process_emails(self):
        """Main email processing loop"""
        while self.running:
            try:
                # Dequeue emails with priority
                jobs = await self.redis_client.dequeue_email(
                    consumer_group="email_workers",
                    consumer_name=self.worker_id,
                    count=self.config.batch_size,
                )

                if not jobs:
                    await asyncio.sleep(0.1)  # Short sleep if no work
                    continue

                # Process jobs concurrently
                tasks = []
                for job in jobs:
                    task = asyncio.create_task(self._process_single_email(job))
                    tasks.append(task)

                # Wait for batch completion
                await asyncio.gather(*tasks, return_exceptions=True)

            except Exception as e:
                logging.error(f"Batch processing error: {e}")
                await asyncio.sleep(1)

    async def _process_single_email(self, job: EmailJob):
        """Process a single email job"""
        try:
            self.stats["processed"] += 1

            # Update job status
            job.status = EmailStatus.SENDING

            # Get provider
            provider = self.providers.get(job.provider.value)
            if not provider:
                raise Exception(f"Provider {job.provider.value} not available")

            # Send email
            success = await provider.send_email(job)

            if success:
                job.status = EmailStatus.SENT
                self.stats["sent"] += 1
                logging.info(f"Email sent successfully: {job.job_id}")
            else:
                job.status = EmailStatus.FAILED
                self.stats["failed"] += 1
                logging.warning(f"Email failed: {job.job_id}")

            # Acknowledge processing
            await self.redis_client.ack_email(job, success)

        except Exception as e:
            job.status = EmailStatus.FAILED
            job.error_message = str(e)
            self.stats["failed"] += 1

            logging.error(f"Email processing error {job.job_id}: {e}")
            await self.redis_client.ack_email(job, False)

    async def _process_retries(self):
        """Process retry queue periodically"""
        while self.running:
            try:
                await self.redis_client.process_retry_queue()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logging.error(f"Retry processing error: {e}")
                await asyncio.sleep(60)

    async def _report_stats(self):
        """Report worker statistics"""
        logging.info(f"Stats reporter started for worker {self.worker_id}")
        while self.running:
            try:
                uptime = datetime.utcnow() - self.stats["started_at"]
                rate = self.stats["processed"] / max(1, uptime.total_seconds())

                logging.info(
                    f"Worker {self.worker_id} stats: "
                    f"processed={self.stats['processed']}, "
                    f"sent={self.stats['sent']}, "
                    f"failed={self.stats['failed']}, "
                    f"rate={rate:.2f}/sec"
                )

                await asyncio.sleep(60)  # Report every minute
            except Exception as e:
                logging.error(f"Stats reporting error: {e}")
                import traceback

                logging.error(traceback.format_exc())
                await asyncio.sleep(60)
