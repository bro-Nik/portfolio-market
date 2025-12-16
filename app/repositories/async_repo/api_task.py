from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select 
from sqlalchemy.orm import joinedload

from app import models, schemas
from .base import BaseRepository


class ApiTaskRepository(BaseRepository[models.ScheduledTask, schemas.TaskCreate, schemas.TaskUpdate]):
    def __init__(self, db: AsyncSession):
        super().__init__(models.ScheduledTask, db)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[models.ScheduledTask]:
        query = (
            select(models.ScheduledTask)
            .options(joinedload(models.ScheduledTask.api_service))
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.scalars().all()
