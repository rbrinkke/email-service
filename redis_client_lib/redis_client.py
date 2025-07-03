# File: /opt/freeface/email/redis/redis_client.py
# FreeFace Email System - Redis Client
# Advanced Redis client for email operations using Streams and Lua scripts

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional

import redis
from .async_redis_wrapper import AsyncRedisWrapper

from config.email_config import EmailConfig
from models.email_models import EmailJob, EmailPriority, EmailStatus

class RedisEmailClient:
    """Advanced Redis client for email operations using Streams and Lua scripts"""
    
    def __init__(self, config: EmailConfig):
        self.config = config
        self.redis = None
        self._lua_scripts = {}
        
    async def connect(self):
        """Initialize Redis connection and load Lua scripts"""
        self.redis = AsyncRedisWrapper(
            host=self.config.redis_host,
            port=self.config.redis_port,
            db=self.config.redis_db,
            password=self.config.redis_password,
            decode_responses=True
        )
        
        # Load Lua scripts for atomic operations
        await self._load_lua_scripts()
        
    async def _load_lua_scripts(self):
        """Load optimized Lua scripts for atomic operations"""
        
        # Token bucket rate limiting script
        token_bucket_script = """
        local key = KEYS[1]
        local bucket_size = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local tokens_requested = tonumber(ARGV[3])
        local current_time = tonumber(ARGV[4])
        
        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1]) or bucket_size
        local last_refill = tonumber(bucket[2]) or current_time
        
        -- Calculate tokens to add based on time elapsed
        local time_elapsed = current_time - last_refill
        local tokens_to_add = math.floor(time_elapsed * refill_rate / 60)
        
        if tokens_to_add > 0 then
            tokens = math.min(bucket_size, tokens + tokens_to_add)
            last_refill = current_time
        end
        
        -- Check if we can consume the requested tokens
        if tokens >= tokens_requested then
            tokens = tokens - tokens_requested
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', last_refill)
            redis.call('EXPIRE', key, 3600)
            return 1  -- Success
        else
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', last_refill)
            redis.call('EXPIRE', key, 3600)
            return 0  -- Rate limited
        end
        """
        
        # Priority queue enqueue script
        enqueue_script = """
        local stream_key = KEYS[1]
        local dedup_key = KEYS[2]
        local job_id = ARGV[1]
        local job_data = ARGV[2]
        
        -- Check for duplicate
        if redis.call('SISMEMBER', dedup_key, job_id) == 1 then
            return 0  -- Already queued
        end
        
        -- Atomic enqueue
        redis.call('SADD', dedup_key, job_id)
        redis.call('EXPIRE', dedup_key, 3600)  -- 1 hour dedup window
        
        local stream_id = redis.call('XADD', stream_key, '*', 'job', job_data)
        return stream_id
        """
        
        # Register scripts
        self._lua_scripts['token_bucket'] = await self.redis.script_load(token_bucket_script)
        self._lua_scripts['enqueue'] = await self.redis.script_load(enqueue_script)
        
    async def check_rate_limit(self, provider: str, tokens_needed: int = 1) -> bool:
        """Check rate limit using token bucket algorithm"""
        limits = self.config.rate_limits.get(provider, {"bucket_size": 100, "refill_rate": 20})
        
        result = await self.redis.evalsha(
            self._lua_scripts['token_bucket'],
            1,  # Number of keys
            f"rate_limit:{provider}",  # Key
            limits["bucket_size"],     # Bucket size
            limits["refill_rate"],     # Refill rate per minute
            tokens_needed,             # Tokens requested
            int(time.time())          # Current time
        )
        
        return bool(result)
    
    async def enqueue_email(self, job: EmailJob) -> str:
        """Enqueue email job with deduplication"""
        stream_key = f"email:queue:{job.priority.value}"
        dedup_key = f"email:dedup"
        
        job_data = job.json()
        
        stream_id = await self.redis.evalsha(
            self._lua_scripts['enqueue'],
            2,  # Number of keys
            stream_key,
            dedup_key,
            job.job_id,
            job_data
        )
        
        return stream_id
    
    async def dequeue_email(self, consumer_group: str, consumer_name: str, count: int = 1) -> List[EmailJob]:
        """Dequeue emails with priority (HIGH -> MEDIUM -> LOW)"""
        priorities = [EmailPriority.HIGH, EmailPriority.MEDIUM, EmailPriority.LOW]
        
        for priority in priorities:
            stream_key = f"email:queue:{priority.value}"
            
            # Create consumer group if it doesn't exist
            try:
                await self.redis.xgroup_create(stream_key, consumer_group, id='0', mkstream=True)
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
            
            # Read from stream
            messages = await self.redis.xreadgroup(
                consumer_group, consumer_name,
                {stream_key: '>'},
                count=count,
                block=100  # 100ms timeout
            )
            
            if messages:
                jobs = []
                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        job_data = json.loads(fields['job'])
                        job = EmailJob.parse_obj(job_data)
                        job.stream_id = msg_id
                        jobs.append(job)
                return jobs
        
        return []  # No messages available
    
    async def ack_email(self, job: EmailJob, success: bool = True):
        """Acknowledge email processing"""
        stream_key = f"email:queue:{job.priority.value}"
        
        if success:
            # Remove from stream
            await self.redis.xack(stream_key, "email_workers", job.stream_id)
            await self.redis.xdel(stream_key, job.stream_id)
            
            # Log success
            await self.redis.hincrby("email:stats:daily", "sent", 1)
        else:
            # Handle retry or dead letter
            job.retry_count += 1
            
            if job.retry_count >= self.config.retry_attempts:
                # Move to dead letter queue
                await self._move_to_dead_letter(job)
                await self.redis.xack(stream_key, "email_workers", job.stream_id)
                await self.redis.xdel(stream_key, job.stream_id)
            else:
                # Retry later (exponential backoff)
                delay = min(300, 10 * (2 ** job.retry_count))  # Max 5 minutes
                retry_time = int(time.time() + delay)
                
                await self.redis.zadd("email:retry", {job.job_id: retry_time})
                await self.redis.xack(stream_key, "email_workers", job.stream_id)
                await self.redis.xdel(stream_key, job.stream_id)
            
            # Log failure
            await self.redis.hincrby("email:stats:daily", "failed", 1)
    
    async def _move_to_dead_letter(self, job: EmailJob):
        """Move failed job to dead letter queue"""
        job.status = EmailStatus.DEAD_LETTER
        await self.redis.lpush("email:dead_letter", job.json())
        await self.redis.expire("email:dead_letter", self.config.dead_letter_ttl)
    
    async def process_retry_queue(self):
        """Process retry queue for scheduled retries"""
        current_time = int(time.time())
        
        # Get jobs ready for retry
        retry_jobs = await self.redis.zrangebyscore(
            "email:retry", 0, current_time, withscores=True
        )
        
        for job_id, _ in retry_jobs:
            # Remove from retry queue
            await self.redis.zrem("email:retry", job_id)
            
            # Re-queue the job (would need job data stored separately)
            # This is simplified - in production, store full job data
            logging.info(f"Retrying job {job_id}")
    
    async def get_stats(self) -> Dict:
        """Get email system statistics"""
        stats = await self.redis.hgetall("email:stats:daily")
        
        # Queue lengths
        for priority in EmailPriority:
            stream_key = f"email:queue:{priority.value}"
            length = await self.redis.xlen(stream_key)
            stats[f"queue_{priority.value}"] = length
        
        # Rate limit status
        for provider in self.config.rate_limits:
            bucket = await self.redis.hmget(f"rate_limit:{provider}", "tokens", "last_refill")
            if bucket[0]:
                stats[f"rate_{provider}_tokens"] = bucket[0]
        
        return stats
