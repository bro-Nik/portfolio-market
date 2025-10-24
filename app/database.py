from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os


DATABASE_URL = os.getenv("DATABASE_URL")
Base = declarative_base()

# Создание асинхронного движка
engine = create_async_engine(DATABASE_URL)

# Настройка асинхронной сессии
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """Dependency для получения асинхронной сессии БД.
    
    Yields:
        AsyncSession: Асинхронная сессия для работы с БД
        
    Example:
        @app.get("/items/")
        async def read_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
