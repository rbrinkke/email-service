#!/usr/bin/env python3
"""Debug script to check Redis queue status and consumer groups"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import redis as redis_module
import json

# Connect to Redis
r = redis_module.Redis(host='10.10.1.21', port=6379, decode_responses=True)

print("=== Redis Email Queue Debug Info ===\n")

# Check all priority queues
priorities = ['high', 'medium', 'low']

for priority in priorities:
    stream_key = f"email:queue:{priority}"
    
    print(f"\n--- {priority.upper()} Priority Queue ---")
    
    # Check stream length
    try:
        length = r.xlen(stream_key)
        print(f"Stream length: {length}")
    except redis.ResponseError as e:
        print(f"Stream doesn't exist or error: {e}")
        continue
    
    # Check consumer groups
    try:
        groups = r.xinfo_groups(stream_key)
        print(f"Consumer groups: {len(groups)}")
        
        for group in groups:
            print(f"\n  Group: {group['name']}")
            print(f"  Consumers: {group['consumers']}")
            print(f"  Pending: {group['pending']}")
            print(f"  Last delivered ID: {group['last-delivered-id']}")
            
            # Check pending messages
            if group['pending'] > 0:
                try:
                    pending = r.xpending(stream_key, group['name'])
                    print(f"  Pending summary: {pending}")
                    
                    # Get detailed pending info
                    detailed = r.xpending_range(stream_key, group['name'], '-', '+', 10)
                    print(f"  Pending messages (first 10):")
                    for msg in detailed:
                        print(f"    ID: {msg['message_id']}, Consumer: {msg['consumer']}, Idle: {msg['time_since_delivered']}ms")
                except Exception as e:
                    print(f"  Error getting pending info: {e}")
            
            # Check consumers
            try:
                consumers = r.xinfo_consumers(stream_key, group['name'])
                if consumers:
                    print(f"  Active consumers:")
                    for consumer in consumers:
                        print(f"    Name: {consumer['name']}, Pending: {consumer['pending']}, Idle: {consumer['idle']}ms")
            except Exception as e:
                print(f"  Error getting consumer info: {e}")
                
    except redis.ResponseError as e:
        print(f"No consumer groups or error: {e}")
    
    # Show last few messages in the stream
    if length > 0:
        try:
            messages = r.xrevrange(stream_key, count=3)
            print(f"\n  Last 3 messages in stream:")
            for msg_id, fields in messages:
                print(f"    ID: {msg_id}")
                if 'job' in fields:
                    try:
                        job_data = json.loads(fields['job'])
                        print(f"    Job ID: {job_data.get('job_id', 'N/A')}")
                        print(f"    Status: {job_data.get('status', 'N/A')}")
                        print(f"    To: {job_data.get('to', 'N/A')}")
                    except:
                        print(f"    Raw data: {fields}")
        except Exception as e:
            print(f"  Error reading messages: {e}")

# Check retry queue
print("\n\n--- Retry Queue ---")
try:
    retry_count = r.zcard("email:retry")
    print(f"Retry queue size: {retry_count}")
    
    if retry_count > 0:
        retries = r.zrange("email:retry", 0, 4, withscores=True)
        print("First 5 retry jobs:")
        for job_id, score in retries:
            print(f"  Job: {job_id}, Retry time: {score}")
except Exception as e:
    print(f"Error checking retry queue: {e}")

# Check dead letter queue
print("\n--- Dead Letter Queue ---")
try:
    dl_count = r.llen("email:dead_letter")
    print(f"Dead letter queue size: {dl_count}")
except Exception as e:
    print(f"Error checking dead letter queue: {e}")

# Check stats
print("\n--- Email Stats ---")
try:
    stats = r.hgetall("email:stats:daily")
    for key, value in stats.items():
        print(f"{key}: {value}")
except Exception as e:
    print(f"Error getting stats: {e}")