from datetime import date, datetime
from typing import Any

import orjson
from loguru import logger
from pydantic import BaseModel
from redis.asyncio import Redis

from core.settings import settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis

    if _redis is None:
        _redis = Redis.from_url(
            settings.REDIS_URL,
        )

    return _redis


def _debug(message: str) -> None:
    if settings.REDIS_CACHE_DEBUG:
        logger.debug(message)


def cache_key(*parts: str) -> str:
    prefix = settings.REDIS_PREFIX

    normalized = [str(part).strip().replace(":", "_") for part in parts]

    return ":".join([prefix, *normalized])


async def cache_get(key: str) -> Any | None:
    try:
        redis = get_redis()

        raw = await redis.get(key)

        if raw is None:
            _debug(f"[CACHE MISS] {key}")
            return None

        _debug(f"[CACHE HIT] {key}")
        return orjson.loads(raw)

    except Exception:
        logger.exception(f"Redis GET failed: {key}")
        return None


async def cache_mget(
    keys: list[str],
) -> dict[str, Any | None]:

    if not keys:
        return {}

    try:
        redis = get_redis()

        raws = await redis.mget(keys)

        result = {}

        for key, raw in zip(keys, raws):
            if raw is None:
                result[key] = None
            else:
                result[key] = orjson.loads(raw)

        _debug(f"[CACHE MGET] {len(keys)} keys: {', '.join(keys)}")

        return result

    except Exception:
        logger.exception("Redis MGET failed")

        return {key: None for key in keys}


async def cache_set(
    key: str,
    value: Any,
    ttl_seconds: int = 60,
) -> None:
    try:
        redis = get_redis()

        value = serialize_cache_value(value)

        await redis.set(
            key,
            orjson.dumps(value),
            ex=ttl_seconds,
        )

        _debug(f"[CACHE SET] {key} (ttl={ttl_seconds}s)")

    except Exception:
        logger.exception(f"Redis SET failed: {key}")


async def cache_mset(
    items: dict[str, Any],
    ttl_seconds: int = 60,
) -> None:
    try:
        redis = get_redis()

        async with redis.pipeline() as pipe:
            for key, value in items.items():
                value = serialize_cache_value(value)

                pipe.set(
                    key,
                    orjson.dumps(value),
                    ex=ttl_seconds,
                )

            await pipe.execute()

        _debug(f"[CACHE MSET] {len(items)} keys: {', '.join(items.keys())}")

    except Exception:
        logger.exception("Redis MSET failed")


async def cache_delete(*keys: str) -> None:
    try:
        redis = get_redis()

        await redis.delete(*keys)

        _debug(f"[CACHE DELETE] {keys}")

    except Exception:
        logger.exception(f"Redis DELETE failed: {keys}")


def serialize_cache_value(value: Any) -> Any:

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")

    if isinstance(value, dict):
        return {k: serialize_cache_value(v) for k, v in value.items()}

    if isinstance(value, list):
        return [serialize_cache_value(v) for v in value]

    if isinstance(value, tuple):
        return [serialize_cache_value(v) for v in value]

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    return value
