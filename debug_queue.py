#!/usr/bin/env python3
"""Debug Redis queue using project's async Redis wrapper"""

import asyncio
import json
from redis_client_lib.async_redis_wrapper import AsyncRedisWrapper

async def debug_queue():
    # Create Redis connection
    redis = AsyncRedisWrapper(
        host='10.10.1.21',
        port=6379,
        db=0,
        decode_responses=True
    )
    
    print("=== Redis Email Queue Debug Info ===\n")
    
    # Check all priority queues
    priorities = ['high', 'medium', 'low']
    
    for priority in priorities:
        stream_key = f"email:queue:{priority}"
        
        print(f"\n--- {priority.upper()} Priority Queue ---")
        
        # Check stream length
        try:
            length = await redis.xlen(stream_key)
            print(f"Stream length: {length}")
            
            if length > 0:
                # Get stream info
                try:
                    info = await redis.xinfo_stream(stream_key)
                    print(f"Stream info: entries={info.get('length')}, groups={info.get('groups')}")
                except Exception as e:
                    print(f"Could not get stream info: {e}")
                
                # Try to read last message
                try:
                    messages = await redis.xrevrange(stream_key, count=1)
                    if messages:
                        msg_id, fields = messages[0]
                        print(f"Last message ID: {msg_id}")
                        if 'job' in fields:
                            job_data = json.loads(fields['job'])
                            print(f"Job ID: {job_data.get('job_id')}")
                            print(f"Status: {job_data.get('status')}")
                except Exception as e:
                    print(f"Error reading messages: {e}")
                
                # Check consumer groups
                try:
                    groups = await redis.xinfo_groups(stream_key)
                    print(f"\nConsumer groups found: {len(groups)}")
                    
                    for group in groups:
                        print(f"\n  Group name: {group.get('name')}")
                        print(f"  Consumers: {group.get('consumers')}")
                        print(f"  Pending: {group.get('pending')}")
                        print(f"  Last-delivered-id: {group.get('last-delivered-id')}")
                        
                        # Check if there are consumers
                        if group.get('consumers', 0) == 0:
                            print("  ⚠️  NO ACTIVE CONSUMERS IN THIS GROUP!")
                        
                        # Check pending messages
                        if group.get('pending', 0) > 0:
                            try:
                                # Get pending summary
                                pending_info = await redis.xpending(stream_key, group['name'])
                                print(f"  Pending summary: {pending_info}")
                            except Exception as e:
                                print(f"  Error checking pending: {e}")
                                
                except Exception as e:
                    print(f"Error checking consumer groups: {e}")
                    
        except Exception as e:
            print(f"Stream doesn't exist or error: {e}")
    
    # Close connection
    await redis.close()

if __name__ == "__main__":
    asyncio.run(debug_queue())