from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Dict

from ..core.config import MarketType


class BaseMarketClient(ABC):
    def __init__(self):
        self.session = None
        self._last_request_time = 0

    @abstractmethod
    def get_prices(self, ticker_ids: List[str]) -> Dict[str, Decimal]:
        pass
