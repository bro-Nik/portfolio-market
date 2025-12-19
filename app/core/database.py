import os

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


# Конфигурация базы данных
ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL")
if not ASYNC_DATABASE_URL:
    raise ValueError("ASYNC_DATABASE_URL environment variable is not set")

SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL")
if not SYNC_DATABASE_URL:
    raise ValueError("SYNC_DATABASE_URL environment variable is not set")


DB_ECHO = os.getenv("DB_ECHO", 'false').lower() in ('true', '1')
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))


# Создание асинхронного движка
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    echo=DB_ECHO,
    future=True
)

# Настройка асинхронной сессии
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Создание синхронного движка
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    echo=DB_ECHO,
    future=True

)

# Настройка синхронной сессии
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
