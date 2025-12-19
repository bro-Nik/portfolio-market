from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from .base import BaseRepository


class ApiServiceRepository(BaseRepository[models.ApiService, schemas.ApiServiceCreate, schemas.ApiServiceUpdate]):
    def __init__(self, db: AsyncSession):
        super().__init__(models.ApiService, db)
