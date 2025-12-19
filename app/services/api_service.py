from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from app.external_api.management.registry import ExternalApiRegistry
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.repositories.async_repo.api_service import ApiServiceRepository


class ApiService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.api_repo = ApiServiceRepository(db)

    async def get_services(self, skip: int = 0, limit: Optional[int] = None, active_only: bool = False):
        return await self.api_repo.get_all(skip, limit, active_only)

    async def get_service(self, service_id: int):
        return await self.api_repo.get(service_id)

    async def create_service(self, service_data: schemas.ApiServiceCreate):
        """Создать API сервис с бизнес-логикой"""
        try:
            # Проверка на уникальность имени
            existing = await self.api_repo.get_by_name(service_data.name)
            if existing:
                raise ValueError(f"Service with name '{service_data.name}' already exists")

            # Дополнительная логика
            if service_data.requests_per_minute > 1000:
                raise ValueError("Too many requests per minute")

            # Создание
            service = await self.api_repo.create(service_data)

            await self.db.commit()
            await self.db.refresh(service)
            return service

        except Exception as e:
            await self.db.rollback()
            raise

    async def update_service(self, service_id: int, service_data: schemas.ApiServiceUpdate):
        """Создать API сервис с бизнес-логикой"""
        try:
            # Дополнительная логика
            if service_data.requests_per_minute and service_data.requests_per_minute > 1000:
                raise ValueError("Too many requests per minute")

            # Маскируем API ключ при обновлении
            if 'api_key' in service_data and service_data['api_key'] == '***':
                del service_data['api_key']

            # Обновление
            service = await self.api_repo.update(service_id, service_data)

            await self.db.commit()
            await self.db.refresh(service)
            return service

        except Exception as e:
            await self.db.rollback()
            raise

    async def delete_service(self, service_id: int):
        try:
            await self.api_repo.delete(service_id)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise

    async def reset_counters(self, service_id: int):
        service = await self.api_repo.get(service_id)
        if not service:
            return None

        try:
            if service:
                now = datetime.utcnow()
                service.minute_counter = 0
                service.hour_counter = 0
                service.day_counter = 0
                service.month_counter = 0
                service.last_minute_reset = now
                service.last_hour_reset = now
                service.last_day_reset = now
                service.last_month_reset = now
                service.updated_at = now

                await self.db.commit()
                await self.db.refresh(service)

        except Exception as e:
            await self.db.rollback()
            raise

        return service

    async def get_stats(self, service_id: int) -> Dict[str, Any]:
        """Получить статистику по сервису"""
        service = await self.api_repo.get(service_id)
        if not service:
            return {}

        # Запросы за последние 24 часа
        day_ago = datetime.utcnow() - timedelta(days=10)
        logs = await self.api_repo.get_logs_to_stats(service_id, day_ago)

        # Расчет процентов использования
        minute_percent = (service.minute_counter / service.requests_per_minute * 100) if service.requests_per_minute else 0
        hour_percent = (service.hour_counter / service.requests_per_hour * 100) if service.requests_per_hour else 0
        day_percent = (service.day_counter / service.requests_per_day * 100) if service.requests_per_day else 0

        return {
            'service_name': service.name,
            'requests_today': logs.total or 0,
            'successful_today': logs.successful or 0,
            'failed_today': (logs.total or 0) - (logs.successful or 0),
            'avg_response_time': round(logs.avg_response_time or 0, 2),
            'minute_counter': service.minute_counter,
            'minute_limit': service.requests_per_minute,
            'hour_counter': service.hour_counter,
            'hour_limit': service.requests_per_hour,
            'day_counter': service.day_counter,
            'day_limit': service.requests_per_day,
            'month_counter': service.month_counter,
            'month_limit': service.requests_per_month,
            'pending_in_queue': 0,
            'utilization_percent': {
                'minute': round(minute_percent, 2),
                'hour': round(hour_percent, 2),
                'day': round(day_percent, 2),
            }
        }

    async def get_logs(
        self,
        service_id: int,
        hours: int = 24,
        limit: Optional[int] = 100
    ):

        last_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        logs = await self.api_repo.get_logs(service_id, last_time=last_time, limit=limit)
        return logs

    async def get_services_with_methods(self) -> List[Dict[str, Any]]:
        result = []
        services = await self.get_services(active_only=True)
        for service in services:
            methods = ExternalApiRegistry.get_service_methods(service.name)
            methods_list = []
            if methods:
                for method_name, method in methods.items():
                    methods_list.append(method_name)
            if methods:
                info = {
                    'id': service.id,
                    'name': service.display_name or service.name,
                    'methods': methods_list
                }
                result.append(info)
        return result
