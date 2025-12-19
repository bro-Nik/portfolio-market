from typing import Any
import logging

from app.external_api.services.task_service import TaskService
from app.external_api.management.registry import registry


logger = logging.getLogger(__name__)


class ApiManager:
    """Менеджер для работы с внешними API"""

    def __init__(self, service_name: str):
        self.service = registry.get_service(service_name)
        if not self.service:
            raise ValueError(f'API сервис "{service_name}" не найден')

        self.task_service = TaskService()


    def execute(self, method_name: str, *args, **kwargs) -> Any:
        """Выполнить метод API"""
        if not self.service:
            return

        logger.info('Выполнение метода %s для %s', method_name, self.service.name)

        # Сообщаем сервису задач о начале
        self.task_service.task_started(kwargs.get('db_task_id', ''))

        try:
            # Выполняем метод
            result = self.service.execute(method_name, *args, **kwargs)

            # Сообщаем сервису задач о завершении
            self.task_service.task_completed(kwargs.get('db_task_id', ''))

            return result

        except Exception as e:
            logger.error(f'Ошибка при выполнении метода {method_name}: {e}')
            raise

        finally:
            # Принудительно сохраняем все состояние
            self.save_state()

    def save_state(self):
        """Финальное сохранение состояния"""
        if self.service and hasattr(self.service, 'save_state'):
            try:
                self.service.save_state()
            except Exception as e:
                logger.error(f"Ошибка при сохранении состояния: {e}")
