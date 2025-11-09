#!/usr/bin/env python3
"""Check pending messages in detail"""

import asyncio
import json
import os

from email_system import EmailConfig, RedisEmailClient


async def check_pending():
    config = EmailConfig(
        redis_host=os.getenv("REDIS_HOST", "redis-email"),
        redis_port=int(os.getenv("REDIS_PORT", 6379)),
    )

    client = RedisEmailClient(config)
    await client.connect()

    stream_key = "email:queue:high"
    group_name = "email_workers"

    print(f"Checking pending messages in {stream_key} for group {group_name}\n")

    # Get detailed pending info
    try:
        # Get pending summary
        pending_summary = await client.redis.xpending(stream_key, group_name)
        print(f"Pending summary: {pending_summary}")

        if (
            pending_summary and pending_summary.get("pending", 0) > 0
        ):  # If there are pending messages
            # Get detailed pending messages
            pending_details = await client.redis.xpending_range(
                stream_key, group_name, min="-", max="+", count=10
            )

            print(f"\nPending messages ({len(pending_details)} found):")
            for msg in pending_details:
                print(f"\n  Message ID: {msg['message_id']}")
                print(f"  Consumer: {msg['consumer']}")
                print(
                    f"  Idle time: {msg['time_since_delivered']}ms ({msg['time_since_delivered']/1000/60:.1f} minutes)"
                )
                print(f"  Delivery count: {msg['times_delivered']}")

                # Try to claim this message
                print(f"\n  Attempting to claim message...")
                claimed = await client.redis.xclaim(
                    stream_key,
                    group_name,
                    "debug_claimer",
                    min_idle_time=0,  # Claim immediately
                    message_ids=[msg["message_id"]],
                )

                if claimed:
                    print(f"  ✓ Successfully claimed message!")
                    for msg_id, fields in claimed:
                        if "job" in fields:
                            job_data = json.loads(fields["job"])
                            print(f"    Job ID: {job_data.get('job_id')}")
                            print(f"    Status: {job_data.get('status')}")
                            print(f"    To: {job_data.get('to')}")
                else:
                    print(f"  ✗ Failed to claim message")

        # Also check what consumers exist
        print("\n\nChecking consumers in the group:")
        consumers = await client.redis.xinfo_consumers(stream_key, group_name)
        for consumer in consumers:
            print(f"\n  Consumer: {consumer['name']}")
            print(f"  Pending: {consumer['pending']}")
            print(f"  Idle: {consumer['idle']}ms ({consumer['idle']/1000/60:.1f} minutes)")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()

    await client.redis.close()


if __name__ == "__main__":
    asyncio.run(check_pending())
