import threading
import time
import random
import json
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta, timezone
import logging
from contextlib import contextmanager

from app.core.redis import get_celery_redis
from app.dependencies import get_sync_db
from app.external_api.services.api_service import ExternalApiService


logger = logging.getLogger(__name__)


class RateLimiter:
    """Гибридный rate limiter с атомарными операциями"""

    def __init__(
        self,
        service_name: str,
        sync_interval: int = 100
    ):
        self.redis = get_celery_redis()
        self.service_name = service_name
        self.sync_interval = sync_interval

        # Базовый ключ для Redis
        self.redis_key_base = f'ratelimit:{service_name}'

        # Лок для потокобезопасности
        self._lock = threading.RLock()

        # Загружаем конфигурацию
        self._config = self._load_config()


    def _load_config(self) -> Dict:
        """Загрузить конфигурацию из Redis или БД"""
        redis_config_key = f'{self.redis_key_base}:config'
        redis_config = self.redis.get(redis_config_key)

        if redis_config:
            logger.info('Загружен конфиг из кэша для сервиса %s', self.service_name)
            try:
                logger.info(json.loads(redis_config))
                return json.loads(redis_config)
            except json.JSONDecodeError:
                logger.warning('Невалидный конфиг в Redis для сервиса %s', self.service_name)

        # Загружаем из БД
        with get_sync_db() as db:
            api_service = ExternalApiService(db)
            service = api_service.get_service(name=self.service_name)

        if not service:
            raise ValueError(f'Сервис "{self.service_name}" не найден')

        config = {
            'limits': {
                'minute': service.requests_per_minute or 0,
                'hour': service.requests_per_hour or 0,
                'day': service.requests_per_day or 0,
                'month': service.requests_per_month or 0,
            },
            'reset_times': {
                'minute': service.last_minute_reset.isoformat() if service.last_minute_reset else None,
                'hour': service.last_hour_reset.isoformat() if service.last_hour_reset else None,
                'day': service.last_day_reset.isoformat() if service.last_day_reset else None,
                'month': service.last_month_reset.isoformat() if service.last_month_reset else None,
            }
        }

        # Сохраняем в Redis
        self.update_redis(config)

        logger.info('Загружен конфиг из БД для сервиса %s', self.service_name)
        logger.info(config)

        return config

    def update_redis(self, config = None):
        key = f'{self.redis_key_base}:config'
        config = config if config else self._config
        if config:
            self.redis.set(key, json.dumps(config))
            logger.info('Обновлен конфиг в кэше для сервиса %s', self.service_name)

    def _get_ttl(self, period: str) -> int:
        """Получить TTL для периода в секундах"""
        ttl_map = {
            'minute': 60,
            'hour': 3600,
            'day': 86400,
            'month': 2592000,  # 30 дней
        }
        return ttl_map.get(period, 60)

    def _get_next_reset(self, period: str, current_time: datetime) -> datetime:
        """Получить время следующего сброса"""
        if period == 'minute':
            return current_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
        if period == 'hour':
            return current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        if period == 'day':
            return current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        if period == 'month':
            # Первый день следующего месяца
            if current_time.month == 12:
                return datetime(current_time.year + 1, 1, 1)
            return datetime(current_time.year, current_time.month + 1, 1)

        return current_time + timedelta(seconds=60)

    def _atomic_check_and_increment(self) -> Tuple[bool, Optional[float]]:
        """Атомарно проверить лимиты и увеличить счетчики"""
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Проверяем, нужно ли сбросить счетчики на основе времени
        self._check_and_reset_counters(now)

        wait_times = []
        for period in ['minute', 'hour', 'day', 'month']:
            limit = self._config['limits'][period]

            if limit <= 0:
                continue

            key = f'{self.redis_key_base}:{period}:count'
            count = self.redis.get(key)
            current = int(count) if count else 0

            if current >= limit:  # Проверяем ДО инкремента
                next_reset = self._get_next_reset(period, now)
                wait_time = (next_reset - now).total_seconds()
                if wait_time > 0:
                    wait_times.append(wait_time)

                    logger.warning(
                        'Достигнут лимит %s для сервиса %s: %s/%s, ожидание %sс',
                        period, self.service_name, current, limit, wait_time
                    )

        if wait_times:
            return False, max(wait_times)

        pipeline = self.redis.pipeline()
        for period in ['minute', 'hour', 'day', 'month']:
            limit = self._config['limits'][period]
            if limit <= 0:
                continue

            key = f'{self.redis_key_base}:{period}:count'
            pipeline.incr(key)
            pipeline.expire(key, self._get_ttl(period))

        key = f'{self.redis_key_base}:total:count'
        pipeline.incr(key)

        pipeline.execute()

        # Периодическая синхронизация с БД
        if random.random() < (1 / self.sync_interval):
            self._sync_to_db_async()

        logger.debug('Запрос разрешен для сервиса %s', self.service_name)

        return True, 0

    def _check_and_reset_counters(self, now: datetime):
        """Проверить и сбросить счетчики если нужно"""
        updated = False
        for period in ['minute', 'hour', 'day', 'month']:
            reset_time_str = self._config['reset_times'][period]
            if not reset_time_str:
                continue

            try:
                last_reset = datetime.fromisoformat(reset_time_str)
                next_reset = self._get_next_reset(period, last_reset)


                if now >= next_reset:
                    # Сбрасываем счетчик в Redis
                    key = f'{self.redis_key_base}:{period}:count'
                    self.redis.delete(key)

                    # Обновляем время сброса в конфиге
                    self._config['reset_times'][period] = now.isoformat()

                    logger.info('Сброшен счетчик %s для сервиса %s', period, self.service_name)
                    logger.info(f'Сброс счетчика {period} для сервиса {self.service_name}. Последний: {last_reset}. Следующий: {next_reset}')

                    updated = True

            except (ValueError, TypeError) as e:
                logger.warning('Ошибка парсинга времени сброса для %s: %s', period, e)

        if updated:
            self.update_redis()

    def acquire(self, timeout: Optional[int] = None) -> bool:
        """Попытаться получить доступ (атомарно)"""
        start_time = time.time()

        while True:
            with self._lock:
                can_proceed, wait_time = self._atomic_check_and_increment()

            if can_proceed:
                return True

            if timeout is None:
                logger.info('Запрос отклонен (без таймаута) для сервиса %s', self.service_name)
                return False

            elapsed = time.time() - start_time
            remaining = timeout - elapsed

            if wait_time > remaining or remaining <= 0:
                logger.info('Таймаут ожидания для сервиса %s', self.service_name)
                return False

            # Спим, но не больше секунды за раз
            sleep_time = min(wait_time, 1.0, remaining)
            if sleep_time > 0:
                logger.debug('Ожидание %sс для сервиса %s', sleep_time, self.service_name)
                time.sleep(sleep_time)

    @contextmanager
    def limit_context(self, timeout: int = 30):
        """Безопасный контекстный менеджер"""
        acquired = self.acquire(timeout)
        if not acquired:
            raise TimeoutError(f'Таймаут rate limit после {timeout} секунд')

        try:
            yield
        except Exception:
            pass
        finally:
            pass

    def _sync_to_db_async(self):
        """Асинхронная синхронизация с БД"""
        try:
            # Собираем данные из Redis
            counts = {}
            for period in ['minute', 'hour', 'day', 'month']:
                key = f'{self.redis_key_base}:{period}:count'
                count = self.redis.get(key)
                counts[period] = int(count) if count else 0

            # Сохраняем в БД в фоне
            threading.Thread(
                target=self._save_to_db,
                args=(counts,),
                daemon=True
            ).start()
        except Exception as e:
            logger.error('Ошибка синхронизации с БД для сервиса %s: %s', self.service_name, e)

    def _save_to_db(self, counts: Dict):
        """Сохранить счетчики в БД"""
        try:
            with get_sync_db() as db:
                # Блокируем запись для этого сервиса
                api_service = ExternalApiService(db)
                service = api_service.get_service_whith_lock(name=self.service_name)

                if not service:
                    logger.error('Сервис %s не найден в БД', self.service_name)
                    return

                # Обновляем счетчики
                service.minute_counter = counts.get('minute', 0)
                service.hour_counter = counts.get('hour', 0)
                service.day_counter = counts.get('day', 0)
                service.month_counter = counts.get('month', 0)
                service.total_requests = counts.get('total', 0)

                logger.debug('Синхронизированы счетчики в БД для сервиса %s', self.service_name)

        except Exception as e:
            logger.error('Ошибка сохранения в БД для сервиса %s: %s', self.service_name, e)

    def get_usage(self) -> Dict:
        """Получить текущее использование"""
        usage = {}
        for period in ['minute', 'hour', 'day', 'month']:
            key = f'{self.redis_key_base}:{period}:count'
            count = self.redis.get(key)
            usage[period] = {
                'used': int(count) if count else 0,
                'limit': self._config['limits'][period],
                'remaining': max(0, self._config['limits'][period] - (int(count) if count else 0))
            }
        return usage

    def save_state(self):
        """Для сохранения извне"""
        self._sync_to_db_async()
