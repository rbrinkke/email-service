#!/usr/bin/env python3
import redis
import os

# Test Redis connection
print("Testing Redis connection...")

try:
    # Get Redis host from environment or use default
    redis_host = os.environ.get('REDIS_HOST', 'redis-email')
    redis_port = int(os.environ.get('REDIS_PORT', '6379'))
    
    print(f"Connecting to Redis at {redis_host}:{redis_port}")
    
    # Create connection
    r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    
    # Test connection
    response = r.ping()
    print(f"Redis PING response: {response}")
    
    # Set a test key
    r.set('test_key', 'test_value')
    value = r.get('test_key')
    print(f"Test key value: {value}")
    
    # Delete test key
    r.delete('test_key')
    
    print("Redis connection successful!")
    
except Exception as e:
    print(f"Redis connection failed: {e}")
    import traceback
    traceback.print_exc()