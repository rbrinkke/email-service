# File: worker.py
# Standalone Email Worker Process

import asyncio
import logging
import os
import signal
from email_system import EmailService, EmailConfig

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

class EmailWorkerProcess:
    def __init__(self):
        self.config = EmailConfig(
            redis_host=os.getenv('REDIS_HOST', '10.10.1.21'),
            redis_port=int(os.getenv('REDIS_PORT', 6379)),
            worker_concurrency=int(os.getenv('WORKER_CONCURRENCY', 100)),
            batch_size=int(os.getenv('BATCH_SIZE', 50))
        )
        self.email_service = EmailService(self.config)
        self.worker_id = os.getenv('WORKER_ID', 'worker_1')
        self.running = True
        
    async def start(self):
        """Start the worker process"""
        # Initialize email service
        await self.email_service.initialize()
        
        # Start single worker
        await self.email_service.start_workers(worker_count=1)
        
        logging.info(f"Email worker {self.worker_id} started successfully")
        
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
        logging.info(f"Shutting down worker {self.worker_id}")
        self.running = False
        await self.email_service.shutdown()
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logging.info(f"Received signal {signum}")
        self.running = False

async def main():
    worker = EmailWorkerProcess()
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, worker.signal_handler)
    signal.signal(signal.SIGINT, worker.signal_handler)
    
    await worker.start()

if __name__ == "__main__":
    asyncio.run(main())
