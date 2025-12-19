import redis
import os


redis_client = None


def get_sync_redis() -> redis.Redis:
    global redis_client

    if redis_client is None:
        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
    return redis_client
