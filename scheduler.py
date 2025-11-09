# File: scheduler.py
# Scheduled Email Processor

import asyncio
import logging
import os
import time

from config.logging_config import setup_logging
from email_system import EmailConfig, EmailJob, EmailService

# Configure logging using centralized configuration
# This sets up Docker-compatible logging (stdout/stderr only)
# Respects LOG_LEVEL, ENVIRONMENT, and other logging env vars
setup_logging()

# Get logger for this module
logger = logging.getLogger(__name__)


class EmailScheduler:
    """Process scheduled emails and move them to immediate queues"""

    def __init__(self):
        self.config = EmailConfig(
            redis_host=os.getenv("REDIS_HOST", "10.10.1.21"),
            redis_port=int(os.getenv("REDIS_PORT", 6379)),
        )
        self.email_service = EmailService(self.config)
        self.interval = int(os.getenv("SCHEDULE_INTERVAL", 60))  # Check every 60 seconds
        self.running = True

    async def start(self):
        """Start the scheduler"""
        await self.email_service.initialize()
        logger.info("Email scheduler started")

        while self.running:
            try:
                await self.process_scheduled_emails()
                await asyncio.sleep(self.interval)
            except Exception as e:
                logger.error("Scheduler error: %s", e)
                await asyncio.sleep(self.interval)

    async def process_scheduled_emails(self):
        """Process emails scheduled for delivery"""
        current_time = int(time.time())

        # Get emails ready for delivery
        redis = self.email_service.redis_client.redis
        scheduled_jobs = await redis.zrangebyscore(
            "email:scheduled", 0, current_time, withscores=True
        )

        processed = 0
        for job_id, timestamp in scheduled_jobs:
            try:
                # Get job data
                job_data = await redis.get(f"email:job:{job_id}")
                if not job_data:
                    # Job expired or already processed
                    await redis.zrem("email:scheduled", job_id)
                    continue

                # Parse job
                job = EmailJob.parse_raw(job_data)

                # Queue for immediate processing
                await self.email_service.redis_client.enqueue_email(job)

                # Remove from scheduled queue
                await redis.zrem("email:scheduled", job_id)
                await redis.delete(f"email:job:{job_id}")

                processed += 1
                logger.info("Scheduled email %s queued for delivery", job_id)

            except Exception as e:
                logger.error("Error processing scheduled job %s: %s", job_id, e)

        if processed > 0:
            logger.info("Processed %s scheduled emails", processed)


async def main():
    scheduler = EmailScheduler()
    await scheduler.start()


if __name__ == "__main__":
    asyncio.run(main())
