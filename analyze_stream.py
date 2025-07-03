#!/usr/bin/env python3
"""Analyze the stream contents in detail"""

import asyncio
import json
import os
from email_system import EmailConfig, RedisEmailClient

async def analyze_stream():
    config = EmailConfig(
        redis_host=os.getenv('REDIS_HOST', 'redis-email'),
        redis_port=int(os.getenv('REDIS_PORT', 6379))
    )
    
    client = RedisEmailClient(config)
    await client.connect()
    
    stream_key = "email:queue:high"
    group_name = "email_workers"
    
    print("=== Stream Analysis ===\n")
    
    # Get all messages in the stream
    all_messages = await client.redis.xrange(stream_key, '-', '+')
    print(f"Total messages in stream: {len(all_messages)}")
    
    # Get consumer group info
    groups = await client.redis.xinfo_groups(stream_key)
    group_info = None
    for g in groups:
        if g['name'] == group_name:
            group_info = g
            break
    
    if group_info:
        last_delivered = group_info.get('last-delivered-id', '0-0')
        print(f"Consumer group last-delivered-id: {last_delivered}")
    
    print("\nMessages in stream:")
    for msg_id, fields in all_messages:
        print(f"\n  Message ID: {msg_id}")
        
        # Compare with last-delivered-id
        if group_info:
            if msg_id <= last_delivered:
                print(f"  Status: ALREADY DELIVERED (ID <= {last_delivered})")
            else:
                print(f"  Status: NOT YET DELIVERED (ID > {last_delivered})")
        
        if 'job' in fields:
            try:
                job_data = json.loads(fields['job'])
                print(f"  Job ID: {job_data.get('job_id')}")
                print(f"  Status: {job_data.get('status')}")
                print(f"  Created: {job_data.get('created_at')}")
            except:
                print(f"  Raw job data: {fields['job'][:100]}...")
    
    # Now let's delete the already-delivered message
    if all_messages and group_info:
        for msg_id, _ in all_messages:
            if msg_id <= last_delivered:
                print(f"\nDeleting already-delivered message {msg_id}...")
                await client.redis.xdel(stream_key, msg_id)
                print("✓ Deleted")
    
    # Final check
    final_length = await client.redis.xlen(stream_key)
    print(f"\nFinal stream length: {final_length}")
    
    await client.redis.close()

if __name__ == "__main__":
    asyncio.run(analyze_stream())