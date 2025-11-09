#!/usr/bin/env python3
"""Test sending a new message and verify worker picks it up"""

import asyncio
import os

from email_system import EmailConfig, EmailJob, EmailPriority, EmailProvider, RedisEmailClient


async def test_new_message():
    config = EmailConfig(
        redis_host=os.getenv("REDIS_HOST", "redis-email"),
        redis_port=int(os.getenv("REDIS_PORT", 6379)),
    )

    client = RedisEmailClient(config)
    await client.connect()

    print("=== Testing New Message Processing ===\n")

    # Create a new test job
    test_job = EmailJob(
        to=["test@example.com"],
        template="welcome",
        data={"name": "Test User", "message": "This is a test email"},
        priority=EmailPriority.HIGH,
        provider=EmailProvider.SMTP,
    )

    print(f"1. Creating new email job:")
    print(f"   Job ID: {test_job.job_id}")
    print(f"   To: {test_job.to}")
    print(f"   Priority: {test_job.priority.value}")

    # Enqueue the job
    stream_id = await client.enqueue_email(test_job)
    print(f"\n2. Enqueued with stream ID: {stream_id}")

    # Check queue status
    stream_key = f"email:queue:{test_job.priority.value}"
    length = await client.redis.xlen(stream_key)
    print(f"\n3. Queue length after enqueue: {length}")

    # Wait a bit for worker to process
    print("\n4. Waiting 3 seconds for worker to process...")
    await asyncio.sleep(3)

    # Check queue again
    final_length = await client.redis.xlen(stream_key)
    print(f"\n5. Queue length after waiting: {final_length}")

    # Check pending messages
    pending = await client.redis.xpending(stream_key, "email_workers")
    if pending:
        print(f"\n6. Pending messages: {pending.get('pending', 0)}")

    # Check stats
    stats = await client.get_stats()
    print(f"\n7. System stats:")
    print(f"   Sent: {stats.get('sent', 0)}")
    print(f"   Failed: {stats.get('failed', 0)}")
    print(
        f"   Queue sizes: high={stats.get('queue_high', 0)}, medium={stats.get('queue_medium', 0)}, low={stats.get('queue_low', 0)}"
    )

    await client.redis.close()


if __name__ == "__main__":
    asyncio.run(test_new_message())
