#!/usr/bin/env python3
"""Test the complete worker flow to identify issues"""

import asyncio
import json
import logging
import os

from email_system import EmailConfig, EmailJob, EmailPriority, EmailProvider, RedisEmailClient

# Set up logging
logging.basicConfig(level=logging.DEBUG)


async def test_worker_flow():
    config = EmailConfig(
        redis_host=os.getenv("REDIS_HOST", "redis-email"),
        redis_port=int(os.getenv("REDIS_PORT", 6379)),
    )

    client = RedisEmailClient(config)
    await client.connect()

    print("=== Testing Worker Flow ===\n")

    # 1. Create a test email job
    print("1. Creating test email job...")
    test_job = EmailJob(
        to=["test@example.com"],
        template="test_template",
        data={"name": "Test User"},
        priority=EmailPriority.HIGH,
        provider=EmailProvider.SMTP,
    )

    # 2. Enqueue the job
    print("2. Enqueueing job...")
    stream_id = await client.enqueue_email(test_job)
    print(f"   Enqueued with stream ID: {stream_id}")

    # 3. Check queue length
    stream_key = f"email:queue:{test_job.priority.value}"
    length = await client.redis.xlen(stream_key)
    print(f"   Queue length after enqueue: {length}")

    # 4. Try to dequeue like a worker would
    print("\n3. Attempting to dequeue (simulating worker)...")
    try:
        jobs = await client.dequeue_email(
            consumer_group="email_workers", consumer_name="test_worker", count=1
        )

        if jobs:
            print(f"   ✓ Successfully dequeued {len(jobs)} job(s)")
            for job in jobs:
                print(f"     Job ID: {job.job_id}")
                print(f"     Stream ID: {job.stream_id}")
                print(f"     Status: {job.status}")

                # Acknowledge the job
                print("\n4. Acknowledging job...")
                await client.ack_email(job, success=True)
                print("   ✓ Job acknowledged")
        else:
            print("   ✗ No jobs dequeued!")

            # Check if there are pending messages
            print("\n   Checking for pending messages...")
            pending = await client.redis.xpending(stream_key, "email_workers")
            print(f"   Pending info: {pending}")

    except Exception as e:
        print(f"   ✗ Error during dequeue: {e}")
        import traceback

        traceback.print_exc()

    # 5. Final queue state
    print("\n5. Final queue state:")
    final_length = await client.redis.xlen(stream_key)
    print(f"   Queue length: {final_length}")

    # Check stats
    stats = await client.get_stats()
    print(f"   Stats: {stats}")

    await client.redis.close()


if __name__ == "__main__":
    asyncio.run(test_worker_flow())
