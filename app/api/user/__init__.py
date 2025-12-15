"""
Модуль пользовательского API.
Предоставляет endpoints для маркет данных.
"""

from fastapi import APIRouter

from app.api.user.endpoints import tickers


# Создание основного роутера
user_router = APIRouter(prefix="/api", tags=["user"])


# Включение всех endpoints
user_router.include_router(tickers.router)


# Экспорт
__all__ = ["user_router"]
