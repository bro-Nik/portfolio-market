from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from app import schemas
from app.services.api_service import ApiService
from ..dependencies import get_api_service


router = APIRouter(prefix="/api-services", tags=["api-services"])


@router.get("/", response_model=List[schemas.ApiServiceResponse])
async def get_services(
    skip: int = 0,
    limit: Optional[int] = None,
    active_only: bool = False,
    api_service: ApiService = Depends(get_api_service)
) ->List[schemas.ApiServiceResponse]:
    """Получить список API сервисов"""
    services = await api_service.get_services(skip=skip, limit=limit, active_only=active_only)
    return [schemas.ApiServiceResponse.from_orm(service) for service in services]


@router.post("/", response_model=schemas.ApiServiceResponse)
async def create_service(
    service_data: schemas.ApiServiceCreate,
    api_service: ApiService = Depends(get_api_service)
) -> schemas.ApiServiceResponse:
    """Создать новый API сервис"""
    service = await api_service.create_service(service_data)
    return schemas.ApiServiceResponse.from_orm(service)


@router.put("/{service_id}", response_model=schemas.ApiServiceResponse)
async def update_service(
    service_id: int,
    service_data: schemas.ApiServiceUpdate,
    api_service: ApiService = Depends(get_api_service)
) -> schemas.ApiServiceResponse:
    """Обновить API сервис"""

    service = await api_service.update_service(service_id, service_data)
    if not service:
        raise HTTPException(status_code=404, detail="API сервис не найден")
    return schemas.ApiServiceResponse.from_orm(service)


@router.get("/{service_id}", response_model=schemas.ApiServiceResponse)
async def get_service(
    service_id: int,
    api_service: ApiService = Depends(get_api_service)
) -> schemas.ApiServiceResponse:
    """Получить информацию об API сервисе"""
    service = await api_service.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="API сервис не найден")
    return schemas.ApiServiceResponse.from_orm(service)


@router.delete("/{service_id}")
async def delete_service(
    service_id: int,
    api_service: ApiService = Depends(get_api_service)
) -> dict:
    """Удалить API сервис"""
    await api_service.delete_service(service_id)
    return {"message": "API сервис удален"}


@router.post("/{service_id}/reset-counters")
async def reset_counters(
    service_id: int,
    api_service: ApiService = Depends(get_api_service)
) -> dict:
    """Сбросить счетчики API сервиса"""
    service = await api_service.reset_counters(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="API сервис не найден")
    return {"message": "Счетчики сброшены"}


@router.get("/{service_id}/stats")
async def get_service_stats(
    service_id: int,
    api_service: ApiService = Depends(get_api_service)
) -> dict:
    """Получить статистику использования API сервиса"""
    stats = await api_service.get_stats(service_id)
    if not stats:
        raise HTTPException(status_code=404, detail="API сервис не найден")
    return stats


@router.get("/{service_id}/logs")
async def get_service_logs(
    service_id: int,
    hours: int = 24,
    limit: int = 100,
    api_service: ApiService = Depends(get_api_service)
):
    """Получить логи запросов API сервиса"""
    logs = await api_service.get_logs(service_id, hours=hours, limit=limit)
    return logs


@router.get("/presets/default")
def get_default_presets():
    """Получить предустановки для популярных API сервисов"""
    return {
        "presets": [
            {
                "name": "coingecko",
                "display_name": "CoinGecko",
                "description": "Криптовалютные данные и цены",
                "base_url": "https://api.coingecko.com/api/v3",
                "requests_per_minute": 30,
                "requests_per_hour": 100,
                "requests_per_day": 10000,
                "requests_per_month": 100000,
                "timeout": 30,
                "api_key_note": "Ключ не обязателен для бесплатного тарифа"
            },
            {
                "name": "binance",
                "display_name": "Binance",
                "description": "Данные криптобиржи Binance",
                "base_url": "https://api.binance.com/api/v3",
                "requests_per_minute": 1200,
                "requests_per_hour": 72000,
                "requests_per_day": 1000000,
                "requests_per_month": 10000000,
                "timeout": 10,
                "api_key_note": "Требуется API ключ от Binance"
            },
            {
                "name": "coinmarketcap",
                "display_name": "CoinMarketCap",
                "description": "Данные криптовалютного рынка",
                "base_url": "https://pro-api.coinmarketcap.com/v1",
                "requests_per_minute": 30,
                "requests_per_hour": 333,
                "requests_per_day": 10000,
                "requests_per_month": 300000,
                "timeout": 30,
                "api_key_note": "Требуется API ключ"
            },
            {
                "name": "alphavantage",
                "display_name": "Alpha Vantage",
                "description": "Данные фондового рынка",
                "base_url": "https://www.alphavantage.co/query",
                "requests_per_minute": 5,
                "requests_per_hour": 30,
                "requests_per_day": 500,
                "requests_per_month": 15000,
                "timeout": 30,
                "api_key_note": "Требуется бесплатный API ключ"
            },
            {
                "name": "twelvedata",
                "display_name": "Twelve Data",
                "description": "Финансовые данные (акции, forex, крипто)",
                "base_url": "https://api.twelvedata.com",
                "requests_per_minute": 8,
                "requests_per_hour": 800,
                "requests_per_day": 800,
                "requests_per_month": 24000,
                "timeout": 30,
                "api_key_note": "Требуется API ключ"
            }
        ]
    }
