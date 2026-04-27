import os
import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# TTL Constants
TTL_SYMPTOMS = 600       # 10 min
TTL_TRENDS = 3600        # 1 hour
TTL_VISITS = 600         # 10 min

_redis_client: Optional[redis.Redis] = None


async def get_redis() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.ping()
            return _redis_client
        except Exception:
            _redis_client = None

    try:
        _redis_client = redis.from_url(
            REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
        await _redis_client.ping()
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        _redis_client = None
        return None


async def cache_get(key: str) -> Any:
    try:
        client = await get_redis()
        if client is None:
            return None
        data = await client.get(key)
        if data is None:
            return None
        return json.loads(data)
    except Exception as e:
        logger.warning(f"Cache get failed for {key}: {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int) -> None:
    try:
        client = await get_redis()
        if client is None:
            return
        await client.setex(key, ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.warning(f"Cache set failed for {key}: {e}")


async def cache_delete(key: str) -> None:
    try:
        client = await get_redis()
        if client is None:
            return
        await client.delete(key)
    except Exception as e:
        logger.warning(f"Cache delete failed for {key}: {e}")


async def cache_delete_pattern(pattern: str) -> None:
    try:
        client = await get_redis()
        if client is None:
            return
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)
    except Exception as e:
        logger.warning(f"Cache delete pattern failed for {pattern}: {e}")


# Key builders
def key_symptoms(user_id: str, days: int) -> str:
    return f"meditrack:health:{user_id}:symptoms:{days}d"


def key_trends(user_id: str) -> str:
    return f"meditrack:health:{user_id}:trends"


def key_visits(user_id: str) -> str:
    return f"meditrack:health:{user_id}:visits"


def key_upcoming(user_id: str) -> str:
    return f"meditrack:health:{user_id}:visits:upcoming"


# Pattern builders
def pattern_health(user_id: str) -> str:
    return f"meditrack:health:{user_id}:*"


def pattern_ai(user_id: str) -> str:
    return f"meditrack:ai:{user_id}:*"
