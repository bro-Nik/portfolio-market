import os
from enum import Enum


class MarketType(str, Enum):
    CRYPTO = 'crypto'
    STOCK = 'stock'
    CURRENCY = 'currency'


class MarketTickerPrefix(str, Enum):
    CRYPTO = 'cr-'
    STOCK = 'st-'
    CURRENCY = 'cu-'


class Settings:
    JWT_SECRET: str = os.getenv("JWT_SECRET", '')
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", '')


settings = Settings()
