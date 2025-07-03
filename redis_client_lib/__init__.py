# Make redis directory a package
from .redis_client import RedisEmailClient

__all__ = ['RedisEmailClient']