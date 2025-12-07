from typing import Optional, Any, Dict, Generator, List, Callable
from decimal import Decimal
import time
import logging
import requests

from ..base_market_client import BaseMarketClient
from app.core.config import MarketType, MarketTickerPrefix


logger = logging.getLogger(__name__)


class CoinGeckoClient(BaseMarketClient):
    """
    Клиент для CoinGecko API v3
    
    Документация: https://www.coingecko.com/api/documentation
    """

    BASE_URL = 'https://api.coingecko.com/api/v3'
    RATE_LIMIT = 10  # запросов в минуту (для бесплатного плана)
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # секунды
    MAX_URL_LENGTH = 2048
    API_KEY = None

    def __init__(self):
        super().__init__()
        self._last_request_time = 0
        self.session = requests.Session()

        # Настройка сессии
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'MarketDataService/1.0'
        })

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Базовый метод для выполнения запросов с ретраями и rate limiting"""

        # Превышен лимит запросов
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < 60 / self.RATE_LIMIT:
            time.sleep(60 / self.RATE_LIMIT - time_since_last)

        url = f'{self.BASE_URL}/{endpoint}'

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    timeout=30
                )

                self._last_request_time = time.time()

                # Проверка статуса ответа
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(
                        f'Превышен лимит запросов к CoinGecko API. '
                        f'Повтор через {retry_after} секунд. '
                        f'Попытка {attempt + 1}/{self.MAX_RETRIES}'
                    )
                    time.sleep(retry_after)
                    continue

                if response.status_code == 403 and self.API_KEY:
                    logger.error(
                        'Неверный или отсутствующий API ключ для CoinGecko. '
                        'Проверьте корректность ключа в настройках'
                    )
                    raise ValueError('Invalid CoinGecko API key')

                response.raise_for_status()

                logger.debug(f'Запрос {endpoint} выполнен успешно, статус: {response.status_code}')

                return response.json()

            except (requests.RequestException, requests.ConnectionError) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    raise

        raise Exception(f"Ошибка запроса. Попыток: {self.MAX_RETRIES}")

    def _get_url_for_chunks_to_get_prices(self):
        return f'{self.BASE_URL}/simple/price?vs_currencies=usd&ids='

    def _calculate_safe_chunks_to_get_prices(self, ticker_ids):
        """Рассчитать количество чанков с учетом ограничения длины URL"""
        if not ticker_ids:
            return 0

        # Базовый URL для запроса цен
        url = self._get_url_for_chunks_to_get_prices()
        base_length = len(url)

        # Расчет с учетом средней длины ID
        avg_id_length = sum(len(ticker) for ticker in ticker_ids) / len(ticker_ids)
        max_ids_per_chunk = max(1, (self.MAX_URL_LENGTH - base_length) // (avg_id_length + 1))

        return (len(ticker_ids) + max_ids_per_chunk - 1) // max_ids_per_chunk

    def _generate_safe_chunks_to_get_prices(
        self,
        ids: List[str],
    ) -> Generator[List[str], None, None]:
        """
        Генератор, который создает безопасные чанки с учетом длины URL.
        
        Args:
            ids: Список ID тикеров
            
        Yields:
            Список ID тикеров для текущего чанка
        """
        current_chunk = []
        url = self._get_url_for_chunks_to_get_prices()
        current_length = len(url)

        for coin_id in ids:
            # Вычисляем длину добавления нового ID
            addition_length = len(coin_id) + 1  # +1 для запятой

            new_length = current_length + addition_length

            if new_length <= self.MAX_URL_LENGTH:
                current_chunk.append(coin_id)
                current_length = new_length
            else:
                # Возвращаем текущий чанк и начинаем новый
                if current_chunk:
                    yield current_chunk

                current_chunk = [coin_id]
                current_length = len(url) + 1 + len(coin_id)

        # Возвращаем последний чанк
        if current_chunk:
            yield current_chunk

    def get_prices(
        self,
        ticker_ids: List[str],
        progress_callback: Optional[Callable]  = None
    ) -> Dict[str, Decimal]:
        """
        Получить текущие цены для списка ID тикеров
        
        Args:
            ticker_ids: Список CoinGecko ID (например: ['bitcoin', 'ethereum'])
            progress_callback: Функция обратного вызова для отслеживания прогресса
        
        Returns:
            Словарь с ценами в формате {тикер: цена}
        """

        if not ticker_ids:
            return {}

        total_chunks = self._calculate_safe_chunks_to_get_prices(ticker_ids)
        failed_chunks = []
        all_results = {}

        # Обновляем прогресс если передан progress_callback
        if progress_callback:
            progress_callback(0, total_chunks, 'Начало загрузки цен CoinGecko')

        # Получаем генератор безопасных чанков
        chunks = self._generate_safe_chunks_to_get_prices(ticker_ids)

        for i, chunk in enumerate(chunks, 1):
            try:
                logger.info(f'Обработка чанка {i}/{total_chunks} ({len(chunk)} монет)')

                # Обновляем прогресс
                if progress_callback:
                    progress_callback(i, total_chunks, 'Обработка чанка загрузки цен CoinGecko')

                # Делаем запрос к API
                data = self._make_request(
                    'GET',
                    'simple/price',
                    params={
                        'vs_currencies': 'usd',
                        'ids': ','.join(chunk)
                    }
                )

                all_results.update(data)

            except Exception as e:
                logger.error(
                    f'Неожиданная ошибка при обработке чанка {i}: {e}\n'
                    f'Размер чанка: {len(chunk)} элементов\n'
                    f'Элементы чанка: {chunk[:5]}{"..." if len(chunk) > 5 else ""}'
                )
                failed_chunks.append({'chunk': i, 'ids': chunk, 'error': str(e)})
                continue

        logger.info(
            f'Пакетное обновление цен завершено. '
            f'Успешно: {len(all_results)}, '
            f'Ошибки: {len(failed_chunks)}, '
            f'Всего тикеров: {len(ticker_ids)}'
        )

        if failed_chunks:
            logger.warning(
                f'Есть ошибки в следующих чанках: '
                f'{[fc["chunk"] for fc in failed_chunks]}'
            )

        # Формируем результат с префиксами
        price_list = {}
        for ticker_id, price_info in all_results.items():
            usd_price = price_info.get('usd')
            if usd_price is not None:
                price_list[f'{MarketTickerPrefix.CRYPTO}{ticker_id}'] = Decimal(usd_price)

        return price_list
