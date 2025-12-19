from typing import List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, Integer, desc


from app import models, schemas
from .base import BaseRepository


class ApiServiceRepository(BaseRepository[models.ApiService, schemas.ApiServiceCreate, schemas.ApiServiceUpdate]):
    def __init__(self, db: AsyncSession):
        super().__init__(models.ApiService, db)

    async def get_all(
        self,
        skip: int = 0,
        limit: Optional[int] = None,
        active_only: bool = False
    ) -> List[models.ApiService]:
        query = select(self.model)
        if active_only:
            query = query.where(self.model.is_active == True)

        query = query.offset(skip)

        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_name(self, name: str) -> Optional[models.ApiService]:
        result = await self.db.execute(
            select(self.model).where(self.model.name == name)
        )
        return result.scalar_one_or_none()

    async def get_logs_to_stats(self, service_id: int, last_time: datetime):
        """Получить статистику по сервису"""
        query = select(
            func.count(models.ApiRequestLog.id).label('total'),
            func.sum(func.cast(models.ApiRequestLog.was_successful, Integer)).label('successful'),
            func.avg(models.ApiRequestLog.response_time).label('avg_response_time')
        ).where(
            models.ApiRequestLog.service_id == service_id,
            models.ApiRequestLog.created_at >= last_time
        )

        result = await self.db.execute(query)
        return result.first()

    async def get_logs(self, service_id: int, last_time: datetime, limit: int = 100):
        """Получить логи по сервису"""
        query = select(models.ApiRequestLog).where(
            models.ApiRequestLog.service_id == service_id,
            models.ApiRequestLog.created_at >= last_time
        ).order_by(desc(models.ApiRequestLog.created_at))

        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()
