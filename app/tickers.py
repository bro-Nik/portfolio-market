from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from typing import List, Optional
from pydantic import BaseModel

from app.dependencies.auth import get_current_user, User
from app import models, database


router = APIRouter(prefix="/api/tickers", tags=["tickers"])
BASE_IMAGES_URL = '/market/static/images/tickers'


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


class AssetImagesResponse(BaseModel):
    """Модель ответа для картинок активов"""
    images: dict[str, str]


class AssetInfoResponse(BaseModel):
    """Модель ответа для информации о активове"""
    info: dict[str, dict]


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
    tickers = await _get_tickers_by_ids(asset_ids, db)

    prices = {
        ticker.id: ticker.price
        for ticker in tickers
    }

    return AssetPricesResponse(prices=prices)


@router.post('/images', response_model=AssetImagesResponse)
async def get_assets_images(
    asset_ids: List[str],
    db: AsyncSession = Depends(database.get_db)
) -> AssetImagesResponse:
    """
    Возвращает URL изображений для списка активов
    """
    tickers = await _get_tickers_by_ids(asset_ids, db)

    size = 24
    images = {t.id: f'{BASE_IMAGES_URL}/{t.market}/{size}/{t.image}' for t in tickers}

    return AssetImagesResponse(images=images)


@router.post('/info', response_model=AssetInfoResponse)
async def get_assets_info(
    asset_ids: List[str],
    db: AsyncSession = Depends(database.get_db)
) -> AssetInfoResponse:
    """
    Возвращает информацию о тикерах для списка активов
    """
    tickers = await _get_tickers_by_ids(asset_ids, db)

    info = {}
    for ticker in tickers:
        ticker_data = {
            'image': f'{BASE_IMAGES_URL}/{ticker.market}/24/{ticker.image}',
            'name': ticker.name,
            'symbol': ticker.symbol,
        }
        info[ticker.id] = ticker_data

    return AssetInfoResponse(info=info)


async def _get_tickers_by_ids(
    asset_ids: List[str],
    db: AsyncSession
) -> List[models.Ticker]:
    """Общая функция для получения тикеров по списку ID"""
    if not asset_ids:
        return []
    
    result = await db.execute(
        select(models.Ticker).where(models.Ticker.id.in_(asset_ids))
    )
    return result.scalars().all()
