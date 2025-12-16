"""
Модуль административного API.
Предоставляет endpoints для управления системой.
"""

from fastapi import APIRouter

from app.api.admin.endpoints import api_services, tasks


# Создание основного роутера
admin_router = APIRouter(prefix="/admin", tags=["admin"])


# Включение всех endpoints
admin_router.include_router(api_services.router)
admin_router.include_router(tasks.router)


# Экспорт
__all__ = ["admin_router"]
