# File: worker.py
# Standalone Email Worker Process

import asyncio
import logging
import os
import signal

from config.logging_config import setup_logging
from email_system import EmailConfig, EmailService

# Configure logging using centralized configuration
# This sets up Docker-compatible logging (stdout/stderr only)
# Respects LOG_LEVEL, ENVIRONMENT, and other logging env vars
setup_logging()

# Get logger for this module
logger = logging.getLogger(__name__)


class EmailWorkerProcess:
    def __init__(self):
        self.config = EmailConfig(
            redis_host=os.getenv("REDIS_HOST", "10.10.1.21"),
            redis_port=int(os.getenv("REDIS_PORT", 6379)),
            worker_concurrency=int(os.getenv("WORKER_CONCURRENCY", 100)),
            batch_size=int(os.getenv("BATCH_SIZE", 50)),
        )
        self.email_service = EmailService(self.config)
        self.worker_id = os.getenv("WORKER_ID", "worker_1")
        self.running = True

    async def start(self):
        """Start the worker process"""
        # Initialize email service
        await self.email_service.initialize()

        # Start single worker
        await self.email_service.start_workers(worker_count=1)

        logger.info("Email worker %s started successfully", self.worker_id)

        # Keep running until shutdown
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down worker %s", self.worker_id)
        self.running = False
        await self.email_service.shutdown()

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Received signal %s", signum)
        self.running = False


async def main():
    worker = EmailWorkerProcess()

    # Register signal handlers
    signal.signal(signal.SIGTERM, worker.signal_handler)
    signal.signal(signal.SIGINT, worker.signal_handler)

    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
