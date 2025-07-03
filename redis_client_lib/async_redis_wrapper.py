# Wrapper for Redis to handle async operations with sync client
import asyncio
from typing import Any, Optional

# Import the actual redis package
import redis
from redis_client_lib.custom_redis_connection import CustomConnectionPool

class AsyncRedisWrapper:
    """Wrapper to use sync Redis client in async context"""
    
    def __init__(self, host: str, port: int, db: int, password: Optional[str] = None, decode_responses: bool = True):
        # Use custom connection pool to handle CLIENT SETINFO issues
        pool = CustomConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=decode_responses
        )
        self._redis = redis.Redis(connection_pool=pool)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._redis.close()
    
    def __getattr__(self, name):
        """Wrap Redis methods to be async-compatible"""
        attr = getattr(self._redis, name)
        if callable(attr):
            async def async_wrapper(*args, **kwargs):
                loop = asyncio.get_event_loop()
                # run_in_executor doesn't support kwargs, so we need to use a lambda
                return await loop.run_in_executor(None, lambda: attr(*args, **kwargs))
            return async_wrapper
        return attr
    
    async def script_load(self, script: str) -> str:
        """Load a Lua script"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._redis.script_load, script)
    
    async def evalsha(self, sha: str, numkeys: int, *keys_and_args) -> Any:
        """Execute a Lua script by SHA"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._redis.evalsha, sha, numkeys, *keys_and_args)
    
    async def xgroup_create(self, name: str, groupname: str, id: str = '0', mkstream: bool = False) -> Any:
        """Create a consumer group"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._redis.xgroup_create(name, groupname, id, mkstream=mkstream))
    
    async def xreadgroup(self, groupname: str, consumername: str, streams: dict, count: int = None, block: int = None) -> Any:
        """Read from a stream as part of a consumer group"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._redis.xreadgroup(groupname, consumername, streams, count=count, block=block))
    
    async def xack(self, name: str, groupname: str, *ids) -> Any:
        """Acknowledge messages"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._redis.xack, name, groupname, *ids)
    
    async def xdel(self, name: str, *ids) -> Any:
        """Delete messages"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._redis.xdel, name, *ids)
    
    async def hincrby(self, name: str, key: str, amount: int = 1) -> Any:
        """Increment hash field"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._redis.hincrby, name, key, amount)
    
    async def zrangebyscore(self, name: str, min: float, max: float, start: int = None, num: int = None, withscores: bool = False, score_cast_func: callable = float) -> Any:
        """Return a range of values from the sorted set"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._redis.zrangebyscore(name, min, max, start, num, withscores, score_cast_func))