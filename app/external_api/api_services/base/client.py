from typing import Optional, Dict
from abc import ABC
import logging
import time

import requests

from app.models import ApiRequestLog
from app.external_api.services.rate_limiter import RateLimiter
from app.dependencies import get_sync_db


logger = logging.getLogger(__name__)


class ExternalApiClientBase(ABC):
    """Базовый класс для всех клиентов API"""
    BASE_URL = ''
    TIMEOUT = 30

    def __init__(self, service_name: str):
        self._session = None
        self._rate_limiter = None
        self.logs = []
        self.service_name = service_name

    @property
    def session(self):
        if not self._session:
            self._session = requests.Session()
            self._session.headers.update({
                'User-Agent': 'Crypto-Tracker/1.0',
                'Accept': 'application/json'
            })
        return self._session

    @property
    def rate_limiter(self):
        if not self._rate_limiter:
            self._rate_limiter = RateLimiter(self.service_name)
        return self._rate_limiter

    def make_request(self, method: str = 'GET', endpoint: str = '',
                     params: Optional[Dict] = None, data: Optional[Dict] = None,
                     json_data: Optional[Dict] = None, headers: Optional[Dict] = None,
                     timeout: Optional[int] = None) -> Dict:
        """
        Выполнить запрос с учетом rate limiting
        Возвращает результат или вызывает исключение
        """
        start_time = time.time()

        try:
            # Подготавливаем запрос
            url = f"{self.BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"

            # Выполняем запрос с ожиданием при лимитах
            logger.debug('Выполнить запрос к %s', url)
            with self.rate_limiter.limit_context(timeout=30):
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    headers=headers,
                    json=json_data,
                    timeout=timeout or self.TIMEOUT
                )

            response_time = time.time() - start_time

            # Логируем запрос
            self.log_request(
                service_name=self.service_name,
                endpoint=endpoint,
                method=method,
                status_code=response.status_code,
                response_time=response_time,
                was_successful=response.ok,
                error_message=None if response.ok else response.text,
                parameters=params or {},
            )

            if not response.ok:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            self.log_request(
                service_name=self.service_name,
                endpoint=endpoint,
                method=method,
                status_code=None,
                response_time=response_time,
                was_successful=False,
                error_message=str(e),
                parameters=params or {}
            )
            raise

    def log_request(self, service_name: str, endpoint: str, method: str = 'GET',
                    status_code: Optional[int] = None, response_time: Optional[float] = None,
                    was_successful: bool = True, error_message: Optional[str] = None,
                    parameters: Optional[Dict] = None, task_id: Optional[str] = None,
                    ):
        """Записать лог запроса"""
        log = ApiRequestLog(
            service_name=service_name,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time=response_time,
            was_successful=was_successful,
            error_message=error_message,
            request_params=parameters,
            task_id=task_id,
        )
        self.logs.append(log)
        return log

    def _save_logs(self):
        if self.logs:
            with get_sync_db() as db:
                db.add_all(self.logs)
                self.logs = []

    def save_state(self):
        """Сохранить состояние"""
        try:
            self._save_logs()
            if self.rate_limiter and hasattr(self.rate_limiter, 'save_state'):
                self.rate_limiter.save_state()

        except Exception as e:
            logger.error(f"Ошибка при сохранении состояния: {e}")
