from typing import List, Optional
import logging
import requests

from app.celery import celery
from app.services.price_service import PriceService
from app.external_api.coingeko.client import CoinGeckoClient
from app.database import SyncSessionLocal


logger = logging.getLogger(__name__)


def update_task_progress(
    task,
    current: Optional[int] = None,
    total: Optional[int] = None,
    status: Optional[str] = None
) -> None:
    """
    Обновить прогресс Celery задачи
    
    Args:
        task: Celery задача
        current: Текущий прогресс
        total: Общее количество шагов
        status: Текстовое описание статуса
    """
    meta = {}
    if current is not None:
        meta['current'] = current
    if total is not None:
        meta['total'] = total
    if status is not None:
        meta['status'] = status

    # Для отладки
    logger.debug(f'Обновление прогресса задачи: {meta}')

    # Обновляем прогресс задачи
    task.update_state(state='PROGRESS', meta=meta)


@celery.task(bind=True)
def update_prices_coingecko(self, ticker_ids: List[str]):
    """
    Пакетное обновление цен из CoinGecko API
    
    Args:
        ticker_ids: Список ID тикеров для обновления
        
    Returns:
        Словарь с результатами выполнения задачи
    """
    logger.info(f'Старт обновление цен CoinGecko для {len(ticker_ids)} тикеров')

    try:
        db_session = SyncSessionLocal()

        def update_progress(current, total, status):
            """Внутренняя функция для обновления прогресса"""
            update_task_progress(self, current, total, status)

        # Получаем цены из CoinGecko
        client = CoinGeckoClient()
        price_list = client.get_prices(ticker_ids, update_progress)

        # Сохраняем цены в базу данных
        price_service = PriceService(db_session)
        save_result = price_service.save_prices(price_list)

        logger.info(f'Закончено обновление цен CoinGecko. Обновлено {len(price_list)} тикеров')

        return {
            "status": "completed",
            "updated_tickers": len(price_list),
            "data": price_list if price_list else None,
            "db_result": save_result if save_result else None
        }

    except Exception as e:
        logger.error(f'Ошибка обновления цен CoinGecko: {e}')
        return {
            "status": "error",
            "message": str(e),
            "updated_tickers": 0
        }


@celery.task(bind=True)
def smart_price_update(self, strategy: str = 'used', limit: int = None):
    """
    Умное обновление цен с различными стратегиями
    
    Стратегии:
    - 'top': только топ-N монет по капитализации
    - 'active': только активно торгуемые монеты
    - 'all': все монеты
    - 'used': используемые пользователями монеты
    - 'auto': автоматический выбор стратегии

    Args:
        strategy: Название стратегии выбора монет
        limit: Ограничение на количество монет

    Returns:
        Результат запуска задачи обновления цен
    """

    strategies = {
        'top': fetch_top_coins,
        'active': fetch_active_coins,
        'all': fetch_all_coins,
        'used': fetch_used_coins,
        'auto': fetch_smart_coins,
    }

    if strategy not in strategies:
        logger.warning(f'Неизвестная стратегия "{strategy}", возврат к "auto"')
        strategy = 'auto'

    logger.info(f'Старт умного обновления цен со стратегией: {strategy}')

    try:
        # Получаем список ID согласно стратегии
        ticker_ids = strategies[strategy](limit)

        if not ticker_ids:
            logger.warning(f'Не получено тикеров для стратегии: {strategy}')
            return {'status': 'error', 'message': 'Нет тикеров для обновления'}

        # Запускаем обновление
        return update_prices_coingecko.delay(ticker_ids)

    except Exception as e:
        logger.error(f"Ошибка умного обновления цен: {e}")
        return {"status": "error", "message": str(e)}


def fetch_top_coins(limit: int = 100) -> List[str]:
    """Получить топ-N монет по капитализации"""
    coins = []
    return coins[:limit]


def fetch_active_coins(limit: int = 500) -> List[str]:
    """Получить активно торгуемые монеты"""
    coins = []
    return coins[:limit]


def fetch_all_coins(limit: int = None) -> List[str]:
    """Получить все монеты"""
    coins = []
    return coins[:limit]


def fetch_smart_coins(limit: int = 1000) -> List[str]:
    """Умный выбор монет для обновления"""
    coins = []
    return coins[:limit]


def fetch_used_coins(limit: int = None) -> List[str]:
    """
    Получить список монет, используемых пользователями
    
    Args:
        limit: Максимальное количество возвращаемых монет
        
    Returns:
        Список уникальных ID монет без префикса
    """
    try:
        url = 'http://backend:8000/api/admin/all_used_tickers'
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Обрабатываем только криптовалютные тикеры (с префиксом 'cr-')
        prefix = 'cr-'
        ticker_ids = [id.removeprefix(prefix) for id in data if id.startswith(prefix)]

        # Убираем дубликаты
        unique_ids = list(set(ticker_ids))

        logger.info(f'Получено {len(unique_ids)} уникальных использованных тикеров')

        return unique_ids[:limit] if limit else unique_ids

    except requests.RequestException as e:
        logger.error(f"Ошибка получения используемых тикеров: {e}")
        return []
    except Exception as e:
        logger.error(f"Неизвестная ошибка получения используемых тикеров: {e}")
        return []
