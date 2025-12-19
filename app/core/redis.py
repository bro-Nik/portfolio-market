from typing import Optional
import redis
import os


_celery_client: Optional[redis.Redis] = None


def get_celery_redis() -> redis.Redis:
    """Для Celery (broker и backend)"""
    global _celery_client

    if _celery_client is None:
        _celery_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=0,
            decode_responses=False,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
    return _celery_client
