import logging
from typing import Optional, List

import requests
from app.external_api.services.price_service import PriceService


logger = logging.getLogger(__name__)


class SmartPriceUpdater:
    """Класс для умного обновления цен"""

    _strategies = {
        'top': '_fetch_top_coins',
        'active': '_fetch_active_coins',
        'all': '_fetch_all_coins',
        'used': '_fetch_used_coins',
        'auto': '_fetch_smart_coins',
    }

    def __init__(self, client):
        self._client = client
        self._validate_client(client)

    @staticmethod
    def _validate_client(client):
        if not hasattr(client, 'get_prices'):
            raise ValueError('Метод "get_prices" не найден в клиенте')

    @property
    def description(self):
        return """
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

        """

    @property
    def exemple_params(self):
        return {
            'strategy': 'used',
            'limit': 100
        }

    def __call__(self, strategy: str = 'used', limit: Optional[int] = None, **kwargs) -> dict:
        """
        Умное обновление цен с различными стратегиями
        
        Args:
            strategy: Название стратегии выбора монет
            limit: Ограничение на количество монет

        Returns:
            Результат запуска задачи обновления цен
        """

        logger.info(f'Старт умного обновления цен со стратегией: {strategy}')

        if strategy not in self._strategies:
            logger.warning(f'Неизвестная стратегия "{strategy}", возврат к "used"')
            strategy = 'used'

        try:
            # Получаем список ID согласно стратегии
            fetch_method_name = self._strategies[strategy]
            fetch_method = getattr(self, fetch_method_name)
            ticker_ids = fetch_method(limit)

            if not ticker_ids:
                logger.warning(f'Не получено тикеров для стратегии: {strategy}')
                return {'status': 'error', 'message': 'Нет тикеров для обновления'}

            # Получаем цены от клиента API
            price_list = self._client.get_prices(ticker_ids=ticker_ids)

            # Сохраняем цены в базу данных
            price_service = PriceService()
            save_result = price_service.save_prices(price_list)

            return {
                'status': 'success',
                'data': {
                    'requested_count': len(ticker_ids),
                    'received_count': len(price_list),
                    'updated_count': save_result.get('updated', 0),
                },
                'message': f'Обновлено {save_result.get('updated', 0)} цен'
            }

        except Exception as e:
            logger.error(f"Ошибка умного обновления цен: {e}")
            return {'status': 'error', 'message': str(e)}

    def _fetch_top_coins(self, limit: Optional[int] = None) -> List[str]:
        """Получить топ-N монет по капитализации"""
        ids = []
        return ids[:limit] if limit else ids

    def _fetch_active_coins(self, limit: Optional[int] = None) -> List[str]:
        """Получить активно торгуемые монеты"""
        ids = []
        return ids[:limit] if limit else ids

    def _fetch_all_coins(self, limit: Optional[int] = None) -> List[str]:
        """Получить все монеты"""
        ids = []
        return ids[:limit] if limit else ids

    def _fetch_smart_coins(self, limit: Optional[int] = None) -> List[str]:
        """Умный выбор монет для обновления"""
        ids = []
        return ids[:limit] if limit else ids

    def _fetch_used_coins(self, limit: Optional[int] = None) -> List[str]:
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

            # ToDo обрабатывать разные рынки
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
