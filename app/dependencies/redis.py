from app.core import redis


def get_sync_redis():
    """Получение синхронного Redis клиента для Celery"""
    return redis.get_sync_redis()
