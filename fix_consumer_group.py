#!/usr/bin/env python3
"""Fix consumer group by properly handling stuck messages"""

import asyncio
import json
import os
from email_system import EmailConfig, RedisEmailClient

async def fix_consumer_group():
    config = EmailConfig(
        redis_host=os.getenv('REDIS_HOST', 'redis-email'),
        redis_port=int(os.getenv('REDIS_PORT', 6379))
    )
    
    client = RedisEmailClient(config)
    await client.connect()
    
    stream_key = "email:queue:high"
    group_name = "email_workers"
    
    print("=== Fixing Consumer Group ===\n")
    
    # 1. Check current state
    print("1. Current state:")
    length = await client.redis.xlen(stream_key)
    print(f"   Stream length: {length}")
    
    groups = await client.redis.xinfo_groups(stream_key)
    print(f"   Consumer groups: {len(groups)}")
    
    # 2. Check pending messages
    print("\n2. Checking pending messages:")
    pending_summary = await client.redis.xpending(stream_key, group_name)
    print(f"   Pending summary: {pending_summary}")
    
    if pending_summary and pending_summary.get('pending', 0) > 0:
        # Get all pending messages
        pending_details = await client.redis.xpending_range(
            stream_key, group_name,
            min='-', max='+',
            count=1000
        )
        
        print(f"   Found {len(pending_details)} pending messages")
        
        # 3. Acknowledge all pending messages to clear them
        print("\n3. Acknowledging all pending messages:")
        for msg in pending_details:
            msg_id = msg['message_id']
            consumer = msg['consumer']
            
            print(f"   Acknowledging {msg_id} from {consumer}...")
            try:
                await client.redis.xack(stream_key, group_name, msg_id)
                print(f"   ✓ Acknowledged")
            except Exception as e:
                print(f"   ✗ Error: {e}")
    
    # 4. Check messages in stream that haven't been delivered
    print("\n4. Checking undelivered messages in stream:")
    
    # Get the last delivered ID for the consumer group
    group_info = None
    for g in groups:
        if g['name'] == group_name:
            group_info = g
            break
    
    if group_info:
        last_delivered = group_info.get('last-delivered-id', '0-0')
        print(f"   Last delivered ID: {last_delivered}")
        
        # Read messages after the last delivered ID
        undelivered = await client.redis.xrange(stream_key, f"({last_delivered}", '+')
        print(f"   Undelivered messages: {len(undelivered)}")
        
        if undelivered:
            print("\n   First few undelivered messages:")
            for i, (msg_id, fields) in enumerate(undelivered[:3]):
                print(f"     {msg_id}: {fields.get('job', '')[:100]}...")
    
    # 5. Final state
    print("\n5. Final state:")
    final_length = await client.redis.xlen(stream_key)
    print(f"   Stream length: {final_length}")
    
    final_pending = await client.redis.xpending(stream_key, group_name)
    print(f"   Pending count: {final_pending.get('pending', 0) if final_pending else 0}")
    
    await client.redis.close()
    print("\nDone!")

if __name__ == "__main__":
    asyncio.run(fix_consumer_group())