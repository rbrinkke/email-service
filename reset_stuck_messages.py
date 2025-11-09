#!/usr/bin/env python3
"""Reset stuck messages by acknowledging and re-queuing them"""

import asyncio
import json
import os

from email_system import EmailConfig, EmailJob, RedisEmailClient


async def reset_stuck_messages():
    config = EmailConfig(
        redis_host=os.getenv("REDIS_HOST", "redis-email"),
        redis_port=int(os.getenv("REDIS_PORT", 6379)),
    )

    client = RedisEmailClient(config)
    await client.connect()

    priorities = ["high", "medium", "low"]

    for priority in priorities:
        stream_key = f"email:queue:{priority}"
        group_name = "email_workers"

        print(f"\n--- Checking {priority.upper()} priority queue ---")

        try:
            # Get pending messages
            pending_summary = await client.redis.xpending(stream_key, group_name)

            if pending_summary and pending_summary.get("pending", 0) > 0:
                print(f"Found {pending_summary['pending']} pending messages")

                # Get detailed pending messages
                pending_details = await client.redis.xpending_range(
                    stream_key, group_name, min="-", max="+", count=100
                )

                for msg in pending_details:
                    msg_id = msg["message_id"]
                    consumer = msg["consumer"]
                    idle_time = msg["time_since_delivered"]

                    # If message has been idle for more than 5 minutes, reset it
                    if idle_time > 300000:  # 5 minutes in milliseconds
                        print(f"\nResetting stuck message {msg_id}:")
                        print(f"  Consumer: {consumer}")
                        print(f"  Idle: {idle_time/1000/60:.1f} minutes")

                        # Claim the message
                        claimed = await client.redis.xclaim(
                            stream_key,
                            group_name,
                            "reset_worker",
                            min_idle_time=0,
                            message_ids=[msg_id],
                        )

                        if claimed:
                            # Acknowledge and delete the message
                            await client.redis.xack(stream_key, group_name, msg_id)
                            await client.redis.xdel(stream_key, msg_id)

                            # Re-queue the job
                            for msg_id, fields in claimed:
                                if "job" in fields:
                                    job_data = json.loads(fields["job"])
                                    job = EmailJob.parse_obj(job_data)

                                    # Reset retry count
                                    job.retry_count = 0
                                    job.stream_id = None

                                    # Re-enqueue
                                    new_id = await client.enqueue_email(job)
                                    print(f"  ✓ Re-queued as {new_id}")
                        else:
                            print(f"  ✗ Failed to claim message")

        except Exception as e:
            print(f"Error processing {priority} queue: {e}")

    await client.redis.close()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(reset_stuck_messages())
