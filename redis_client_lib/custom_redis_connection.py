# Custom Redis connection that disables CLIENT SETINFO
import redis
from redis.connection import Connection


class CustomConnection(Connection):
    """Custom Redis connection that skips CLIENT SETINFO"""

    def on_connect(self):
        """Initialize the connection without CLIENT SETINFO"""
        super().on_connect()
        # Skip the CLIENT SETINFO command that's causing issues
        # Just set client name if needed
        if self.client_name:
            self.send_command("CLIENT", "SETNAME", self.client_name)


class CustomConnectionPool(redis.ConnectionPool):
    """Custom connection pool using our custom connection class"""

    def __init__(self, connection_class=CustomConnection, **kwargs):
        super().__init__(connection_class=connection_class, **kwargs)
