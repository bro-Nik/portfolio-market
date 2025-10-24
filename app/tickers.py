from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from typing import List, Optional
from pydantic import BaseModel

from app.dependencies.auth import get_current_user, User
from app import models, database

router = APIRouter(prefix="/api/tickers", tags=["tickers"])


class TickerResponse(BaseModel):
    """Модель ответа для тикера"""
    id: str
    name: str
    symbol: str
    image: Optional[str] = None
    market_cap_rank: Optional[int] = None
    price: float
    market: str

    class Config:
        from_attributes = True


class TickerSearchResponse(BaseModel):
    """Модель ответа для поиска тикеров"""
    data: List[TickerResponse]
    has_more: bool


class AssetPricesResponse(BaseModel):
    """Модель ответа для цен активов"""
    prices: dict[str, float]


@router.get("", response_model=TickerSearchResponse)
async def search_tickers(
    search: Optional[str] = Query(None, description="Поиск по названию или символу"),
    market: Optional[str] = Query(None, description="Фильтр по рынку"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    db: AsyncSession = Depends(database.get_db)
) -> TickerSearchResponse:
    """
    Поиск тикеров с пагинацией и фильтрацией
    """
    # Базовые запросы
    query = select(models.Ticker)
    count_query = select(func.count()).select_from(models.Ticker)

    # Собираем условия
    where_conditions = []

    # Применяем поиск если указан
    if search:
        search_term = f"%{search}%"
        where_conditions.append(
            or_(
                models.Ticker.name.ilike(search_term),
                models.Ticker.symbol.ilike(search_term)
            )
        )

    # Применяем фильтр по рынку если указан
    if market:
        where_conditions.append(models.Ticker.market == market)

    # Применяем условия если они есть
    if where_conditions:
        query = query.where(*where_conditions)
        count_query = count_query.where(*where_conditions)

    # Получаем общее количество
    total_count_result = await db.execute(count_query)
    total_count = total_count_result.scalar_one()

    # Вычисляем смещение
    offset = (page - 1) * page_size

    # Получаем данные с пагинацией
    query = query.order_by(
        models.Ticker.market_cap_rank.asc().nulls_last(),
        models.Ticker.symbol.asc()
    ).offset(offset).limit(page_size + 1)  # Берем на один элемент больше для проверки has_more

    result = await db.execute(query)
    tickers = result.scalars().all()

    # Проверяем есть ли следующая страница
    has_more = len(tickers) > page_size
    if has_more:
        tickers = tickers[:-1]  # Убираем лишний элемент

    return TickerSearchResponse(
        data=tickers,
        has_more=has_more
    )


@router.post("/prices", response_model=AssetPricesResponse)
async def get_assets_prices(
    asset_ids: List[str],
    db: AsyncSession = Depends(database.get_db)
) -> AssetPricesResponse:
    """
    Возвращает текущие цены для списка активов
    """
    if not asset_ids:
        return AssetPricesResponse(prices={})

    result = await db.execute(
        select(models.Ticker)
        .where(models.Ticker.id.in_(asset_ids))
    )
    tickers = result.scalars().all()

    prices = {
        ticker.id: ticker.price
        for ticker in tickers
    }

    return AssetPricesResponse(prices=prices)
