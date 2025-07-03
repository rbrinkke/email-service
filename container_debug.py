#!/usr/bin/env python3
"""Debug script to run inside the worker container"""

import asyncio
import json
import os
from email_system import EmailConfig, RedisEmailClient

async def debug_in_container():
    print("=== Container Redis Debug ===\n")
    
    # Create config with container environment
    config = EmailConfig(
        redis_host=os.getenv('REDIS_HOST', 'redis-email'),
        redis_port=int(os.getenv('REDIS_PORT', 6379))
    )
    
    print(f"Connecting to Redis at {config.redis_host}:{config.redis_port}")
    
    # Create Redis client
    client = RedisEmailClient(config)
    await client.connect()
    
    print("Connected successfully!\n")
    
    # Check all priority queues
    priorities = ['high', 'medium', 'low']
    
    for priority in priorities:
        stream_key = f"email:queue:{priority}"
        print(f"\n--- {priority.upper()} Priority Queue ---")
        
        try:
            # Check stream length
            length = await client.redis.xlen(stream_key)
            print(f"Stream length: {length}")
            
            if length > 0:
                # Get consumer groups
                groups = await client.redis.xinfo_groups(stream_key)
                print(f"Consumer groups: {len(groups)}")
                
                for group in groups:
                    print(f"\n  Group: {group['name']}")
                    print(f"  Pending: {group['pending']}")
                    print(f"  Consumers: {group['consumers']}")
                    print(f"  Last-delivered-id: {group['last-delivered-id']}")
                    
                    # Try to read a message
                    print(f"\n  Attempting to read from group '{group['name']}' as 'debug_consumer'...")
                    messages = await client.redis.xreadgroup(
                        group['name'], 'debug_consumer',
                        {stream_key: '>'},
                        count=1,
                        block=100
                    )
                    
                    if messages:
                        print(f"  ✓ Successfully read {len(messages)} message(s)")
                        for stream, msgs in messages:
                            for msg_id, fields in msgs:
                                print(f"    Message ID: {msg_id}")
                                if 'job' in fields:
                                    job_data = json.loads(fields['job'])
                                    print(f"    Job ID: {job_data.get('job_id')}")
                    else:
                        print("  ✗ No messages available to read")
                        
                # Check last message in stream
                messages = await client.redis.xrevrange(stream_key, count=1)
                if messages:
                    msg_id, fields = messages[0]
                    print(f"\n  Last message in stream:")
                    print(f"  ID: {msg_id}")
                    if 'job' in fields:
                        job_data = json.loads(fields['job'])
                        print(f"  Job ID: {job_data.get('job_id')}")
                        print(f"  Status: {job_data.get('status')}")
                        
        except Exception as e:
            print(f"Error: {e}")
    
    # Test dequeue_email method
    print("\n\n--- Testing dequeue_email method ---")
    try:
        jobs = await client.dequeue_email(
            consumer_group="email_workers",
            consumer_name="debug_test",
            count=1
        )
        if jobs:
            print(f"✓ Successfully dequeued {len(jobs)} job(s)")
            for job in jobs:
                print(f"  Job ID: {job.job_id}")
                print(f"  Status: {job.status}")
        else:
            print("✗ No jobs dequeued")
    except Exception as e:
        print(f"Error during dequeue: {e}")
        import traceback
        traceback.print_exc()
    
    await client.redis.close()

if __name__ == "__main__":
    asyncio.run(debug_in_container())