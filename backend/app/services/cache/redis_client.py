import json
from typing import Any

import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import logger


class RedisCacheService:
    def __init__(self):
        self._client: redis.Redis | None = None

    async def get_client(self) -> redis.Redis | None:
        if self._client is None:
            try:
                self._client = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                )
                await self._client.ping()
            except Exception as e:
                logger.warning(f"Redis connection failed, caching disabled: {e!s}")
                self._client = None
        return self._client

    async def get_cached_bill(self, sha256_hash: str) -> dict[str, Any] | None:
        client = await self.get_client()
        if client is None:
            return None
        try:
            cached_data = await client.get(f"bill:sha256:{sha256_hash}")
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Failed to read from Redis cache: {e!s}")
        return None

    async def set_cached_bill(self, sha256_hash: str, data: dict[str, Any], ttl_seconds: int = 86400) -> bool:
        client = await self.get_client()
        if client is None:
            return False
        try:
            await client.setex(
                f"bill:sha256:{sha256_hash}",
                ttl_seconds,
                json.dumps(data),
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to write to Redis cache: {e!s}")
            return False

    async def delete_cached_bill(self, sha256_hash: str) -> bool:
        client = await self.get_client()
        if client is None:
            return False
        try:
            await client.delete(f"bill:sha256:{sha256_hash}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete from Redis cache: {e!s}")
            return False

    async def clear_all(self) -> bool:
        client = await self.get_client()
        if client is None:
            return False
        try:
            keys = await client.keys("bill:sha256:*")
            if keys:
                await client.delete(*keys)
            return True
        except Exception as e:
            logger.warning(f"Failed to clear Redis cache: {e!s}")
            return False


cache_service = RedisCacheService()
