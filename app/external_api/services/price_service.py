from typing import Dict, Any
from datetime import datetime, timezone
import logging

from app.dependencies import get_sync_db
from app.repositories.sync_repo.ticker import TickerRepository


logger = logging.getLogger(__name__)


class PriceService:
    def save_prices(self, price_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Сохраняет цены.
        
        Args:
            price_data: Словарь {ticker_id: price}
            
        Returns:
            Результат операции
        """

        logger.info('Старт сервиса обновления цен. Пришло %s цен', len(price_data))
        batch_size: int = 500

        try:
            if not price_data:
                logger.warning('Нет ценовых данных')
                return {'status': 'warning', 'message': 'Нет ценовых данных'}

            current_time = datetime.now(timezone.utc)

            updated_total = 0
            ticker_ids = list(price_data.keys())

            with get_sync_db() as db:
                ticker_repo = TickerRepository(db)

                # Обрабатываем батчами
                for i in range(0, len(ticker_ids), batch_size):
                    batch_ids = ticker_ids[i:i + batch_size]
                    batch_data = {id: price_data[id] for id in batch_ids}

                    result = ticker_repo.batch_update_ticker_prices(batch_ids, batch_data, current_time)
                    updated_total += result.rowcount

            logger.info('Завершение сервиса обновления цен. Обновлено цен: %s', updated_total)

            return {
                "status": "success",
                "updated": updated_total,
                "total": len(price_data),
            }

        except Exception as e:
            logger.error('Ошибка в save_prices: %s', e)
            return {'status': 'error', 'message': str(e)}
