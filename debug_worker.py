#!/usr/bin/env python3
"""Enhanced worker with debug logging"""

import asyncio
import logging
import os
import signal

from email_system import EmailConfig, EmailService

# Configure very verbose logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Patch the EmailWorker to add debug logging
from workers.email_worker import EmailWorker

original_process_emails = EmailWorker._process_emails


async def debug_process_emails(self):
    """Patched version with debug logging"""
    while self.running:
        try:
            logging.debug(f"Worker {self.worker_id}: Attempting to dequeue emails...")

            # Dequeue emails with priority
            jobs = await self.redis_client.dequeue_email(
                consumer_group="email_workers",
                consumer_name=self.worker_id,
                count=self.config.batch_size,
            )

            if not jobs:
                logging.debug(f"Worker {self.worker_id}: No jobs found, sleeping...")
                await asyncio.sleep(0.1)
                continue

            logging.info(f"Worker {self.worker_id}: Dequeued {len(jobs)} jobs!")

            # Process jobs concurrently
            tasks = []
            for job in jobs:
                task = asyncio.create_task(self._process_single_email(job))
                tasks.append(task)

            # Wait for batch completion
            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logging.error(f"Worker {self.worker_id}: Batch processing error: {e}", exc_info=True)
            await asyncio.sleep(1)


# Apply the patch
EmailWorker._process_emails = debug_process_emails


class DebugEmailWorkerProcess:
    def __init__(self):
        self.config = EmailConfig(
            redis_host=os.getenv("REDIS_HOST", "redis-email"),
            redis_port=int(os.getenv("REDIS_PORT", 6379)),
            worker_concurrency=int(os.getenv("WORKER_CONCURRENCY", 100)),
            batch_size=int(os.getenv("BATCH_SIZE", 50)),
        )
        self.email_service = EmailService(self.config)
        self.worker_id = "debug_worker"
        self.running = True

    async def start(self):
        """Start the worker process"""
        # Initialize email service
        await self.email_service.initialize()

        # Start single worker
        await self.email_service.start_workers(worker_count=1)

        logging.info(f"Debug worker started successfully")

        # Keep running until shutdown
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logging.info("Received shutdown signal")
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Graceful shutdown"""
        logging.info(f"Shutting down debug worker")
        self.running = False
        await self.email_service.shutdown()


async def main():
    worker = DebugEmailWorkerProcess()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
