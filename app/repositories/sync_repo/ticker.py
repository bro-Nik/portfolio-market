from sqlalchemy.orm import Session
from sqlalchemy import case, update

from app import models


class TickerRepository:
    def __init__(self, db: Session):
        self.db = db

    def batch_update_ticker_prices(self, batch_ids, batch_data, current_time):
        # Создаем CASE выражение для батча
        when_conditions = []
        for ticker_id, price in batch_data.items():
            when_conditions.append((models.Ticker.id == ticker_id, price))

        case_expr = case(
            *when_conditions,
            else_=models.Ticker.price
        )

        # UPDATE запрос
        stmt = (
            update(models.Ticker)
            .where(models.Ticker.id.in_(batch_ids))
            .values(
                price=case_expr,
                updated_at=current_time
            )
            .execution_options(synchronize_session=False)
        )

        result = self.db.execute(stmt)
        return result
