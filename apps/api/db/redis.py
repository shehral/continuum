import redis.asyncio as redis

from config import get_settings

redis_client = None


async def init_redis():
    global redis_client
    settings = get_settings()

    redis_client = redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )

    # Test connection
    await redis_client.ping()


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()


def get_redis():
    return redis_client
