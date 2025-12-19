from typing import Optional, Dict, Generator, List, Callable
from decimal import Decimal
import logging

from app.core.config import MarketTickerPrefix
from app.external_api.api_services.base.client import ExternalApiClientBase


logger = logging.getLogger(__name__)


class CoingeckoClient(ExternalApiClientBase):
    """
    Клиент для CoinGecko API v3
    
    Документация: https://www.coingecko.com/api/documentation
    """

    BASE_URL = 'https://api.coingecko.com/api/v3'
    TIMEOUT = 30
    MAX_URL_LENGTH = 2048

    def _get_url_for_chunks_to_get_prices(self) -> str:
        return f'{self.BASE_URL}/simple/price?vs_currencies=usd&ids='

    def _calculate_safe_chunks_to_get_prices(self, ticker_ids) -> int:
        """Рассчитать количество чанков с учетом ограничения длины URL"""
        if not ticker_ids:
            return 0

        # Базовый URL для запроса цен
        url = self._get_url_for_chunks_to_get_prices()
        base_length = len(url)

        # Расчет с учетом средней длины ID
        avg_id_length = sum(len(ticker) for ticker in ticker_ids) / len(ticker_ids)
        max_ids_per_chunk = max(1, (self.MAX_URL_LENGTH - base_length) // (avg_id_length + 1))

        return int((len(ticker_ids) + max_ids_per_chunk - 1) // max_ids_per_chunk)

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
                data = self.make_request(
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
            f'Пакетное оплучение цен завершено. '
            f'Получено цен: {len(all_results)}, '
            f'Ошибки: {len(failed_chunks)}, '
            f'Было запрошено: {len(ticker_ids)}'
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
