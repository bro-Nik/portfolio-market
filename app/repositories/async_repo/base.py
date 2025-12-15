from typing import TypeVar, Generic, Type, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel


ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: int) -> Optional[ModelType]:
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: Optional[int] = None) -> List[ModelType]:
        query = select(self.model).offset(skip)
        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        db_obj = self.model(**obj_in.dict())
        self.db.add(db_obj)
        return db_obj

    async def delete(self, id: int):
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        db_obj = result.scalar_one_or_none()

        if db_obj:
            await self.db.delete(db_obj)
