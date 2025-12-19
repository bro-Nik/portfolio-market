from typing import Generator, AsyncGenerator
from contextlib import contextmanager, asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.database import AsyncSessionLocal, SyncSessionLocal


@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Асинхронный контекстный менеджер для сессии БД."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency для получения асинхронной сессии БД."""
    async with get_async_db() as session:
        yield session


@contextmanager
def get_sync_db() -> Generator[Session, None, None]:
    """Синхронный контекстный менеджер для сессии БД."""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
