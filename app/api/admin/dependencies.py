from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.api_service import ApiService


async def get_api_service(db: AsyncSession = Depends(get_db)) -> ApiService:
    return ApiService(db)
