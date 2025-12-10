import time
from typing import Optional
import logging
import uuid
from contextlib import contextmanager

import redis
from redis.exceptions import RedisError


logger = logging.getLogger(__name__)


class QueueBlocker:
    """Сервис синхронизации задач с блокировкой"""

    DEFAULT_POLL_INTERVAL = 30.0
    DEFAULT_LOCK_TTL = 1800

    def __init__(
        self,
        redis_client: redis.Redis,
        service_key: str,
        poll_interval: float = DEFAULT_POLL_INTERVAL
    ):
        """
        Args:
            redis_client: Клиент Redis
            service_key: Уникальный идентификатор сервиса/задачи
            poll_interval: Интервал опроса в секундах при ожидании блокировки
        """
        self.redis = redis_client
        self.service_key = service_key
        self.lock_key = f'lock.api.{service_key}'
        self.owner_id = str(uuid.uuid4())  # Уникальный ID владельца
        self.poll_interval = poll_interval

    def acquire_lock(
        self,
        lock_ttl: int = DEFAULT_LOCK_TTL,
        timeout: Optional[int] = None,
    ) -> bool:
        """
        Получить блокировку для сервиса
        
        Args:
            lock_ttl: Время жизни блокировки в секундах
            timeout: Максимальное время ожидания
            
        Returns:
            bool: Успешно ли получена блокировка
        """
        try:
            return self._acquire_with_wait(lock_ttl, timeout)

        except RedisError as e:
            logger.error('Ошибка Redis при получении блокировки для %s: %s', self.service_key, e)
            return False
        except Exception as e:
            logger.error('Неожиданная ошибка при получении блокировки для %s: %s', self.service_key, e)
            return False

    def _acquire(self, lock_ttl: int) -> bool:
        """Попытаться получить блокировку"""
        acquired = self.redis.set(
            self.lock_key,
            self.owner_id,
            ex=lock_ttl,
            nx=True  # Только если не существует
        )

        if acquired:
            logger.debug('Блокировка %s получена владельцем %s', self.service_key, self.owner_id)
            return True

        # Проверяем текущего владельца для логирования
        current_owner = self.redis.get(self.lock_key)
        if current_owner:
            logger.debug('Блокировка %s занята владельцем %s', self.service_key, current_owner.decode())

        return False

    def _acquire_with_wait(
        self,
        lock_ttl: int,
        timeout: Optional[int],
    ) -> bool:
        """Получить блокировку с ожиданием"""
        start_time = time.time()

        while True:
            # Пытаемся получить блокировку
            if self._acquire(lock_ttl):
                return True

            # Проверяем таймаут ожидания
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    logger.warning('Таймаут ожидания блокировки "%s" (%d сек)', self.service_key, timeout)
                    return False

            # Ждем перед следующей попыткой
            time.sleep(self.poll_interval)

    def release_lock(self) -> bool:
        """Освободить блокировку (только если мы владелец)"""
        try:
            # Lua script для атомарной проверки владельца
            lua_script = """
            if redis.call("GET", KEYS[1]) == ARGV[1] then
                return redis.call("DEL", KEYS[1])
            else
                return 0
            end
            """

            result = self.redis.eval(lua_script, 1, self.lock_key, self.owner_id)
            released = result == 1

            if released:
                logger.debug('Блокировка для %s освобождена владельцем %s', self.service_key, self.owner_id)
            else:
                current_owner = self.redis.get(self.lock_key)
                if current_owner:
                    logger.warning(
                        'Не удалось освободить блокировку %s: '
                        'принадлежит другому владельцу %s',
                        self.service_key, current_owner.decode()
                    )
                else:
                    logger.debug('Блокировка %s уже истекла или была освобождена', self.service_key)

            return released

        except RedisError as e:
            logger.error('Ошибка Redis при освобождении блокировки %s: %s', self.service_key, e)
            return False
        except Exception as e:
            logger.error('Неожиданная ошибка при освобождении блокировки %s: %s', self.service_key, e)
            return False

    @contextmanager
    def lock(
        self,
        lock_ttl: int = DEFAULT_LOCK_TTL,
        timeout: Optional[int] = None,
    ):
        """
        Контекстный менеджер для блокировки
        
        Args:
            lock_ttl: Время жизни блокировки
            timeout: Максимальное время ожидания
            
        Yields:
            None
            
        Raises:
            TimeoutError: Если не удалось получить блокировку
        """
        acquired = False

        try:
            acquired = self.acquire_lock(
                lock_ttl=lock_ttl,
                timeout=timeout,
            )

            if not acquired:
                error_msg = f'Не удалось получить блокировку для сервиса {self.service_key} (таймаут: {timeout} сек)'
                logger.error(error_msg)
                raise TimeoutError(error_msg)

            yield

        finally:
            if acquired:
                self.release_lock()
