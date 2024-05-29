from typing import Optional

import redis

from logger import get_logger

logger = get_logger(__name__)


class RedisClient:
    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._client: Optional[redis.Redis] = None

    def initialize(self):
        self._client = redis.from_url(self._redis_url)

    def get_client(self) -> redis.Redis:
        if not self._client:
            self.initialize()
        return self._client

    def set(self, key: str, value: str):
        client = self.get_client()
        client.set(key, value)

    def get(self, key: str) -> Optional[str]:
        client = self.get_client()
        value = client.get(key)
        return value.decode("utf-8") if value else None

    def delete(self, key: str):
        client = self.get_client()
        client.delete(key)
