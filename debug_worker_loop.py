#!/usr/bin/env python3
import asyncio
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def test_worker():
    print("Starting test...")

    try:
        from email_system import EmailConfig, EmailService

        print("Imports successful")

        config = EmailConfig(
            redis_host=os.getenv("REDIS_HOST", "10.10.1.21"),
            redis_port=int(os.getenv("REDIS_PORT", 6379)),
        )
        print(f"Config created: redis_host={config.redis_host}")

        service = EmailService(config)
        print("Service created")

        await service.initialize()
        print("Service initialized")

        print("Starting workers...")
        await service.start_workers(1)
        print("Workers started")

        # Wait a bit to see if stats are logged
        print("Waiting for stats logs...")
        await asyncio.sleep(70)  # Wait for more than 60 seconds

    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_worker())
