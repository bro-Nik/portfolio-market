from typing import Dict, Any
from datetime import datetime, timezone
import logging

from sqlalchemy import case, update

from app.models import Ticker
from app.database import SyncSessionLocal


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

        batch_size: int = 500
        db = SyncSessionLocal()

        try:
            if not price_data:
                return {'status': 'warning', 'message': 'Нет ценовых данных'}

            current_time = datetime.now(timezone.utc)

            updated_total = 0
            ticker_ids = list(price_data.keys())

            # Обрабатываем батчами
            for i in range(0, len(ticker_ids), batch_size):
                batch_ids = ticker_ids[i:i + batch_size]
                batch_data = {id: price_data[id] for id in batch_ids}

                # Создаем CASE выражение для батча
                when_conditions = []
                for ticker_id, price in batch_data.items():
                    when_conditions.append((Ticker.id == ticker_id, price))

                case_expr = case(
                    *when_conditions,
                    else_=Ticker.price
                )

                # UPDATE запрос
                stmt = (
                    update(Ticker)
                    .where(Ticker.id.in_(batch_ids))
                    .values(
                        price=case_expr,
                        updated_at=current_time
                    )
                    .execution_options(synchronize_session=False)
                )

                result = db.execute(stmt)
                updated_total += result.rowcount

            db.commit()

            logger.error(f'Обновлено цен: {updated_total}')

            return {
                "status": "success",
                "updated": updated_total,
                "total": len(price_data),
            }

        except Exception as e:
            db.rollback()
            logger.error(f'Ошибка в save_prices: {e}')
            return {'status': 'error', 'message': str(e)}
        finally:
            db.close()
