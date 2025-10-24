from typing import Optional

from sqlalchemy import String, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Ticker(Base):
    __tablename__ = "ticker"

    id: Mapped[str] = mapped_column(String(256), primary_key=True)
    name: Mapped[str] = mapped_column(String(1024))
    symbol: Mapped[str] = mapped_column(String(124))
    image: Mapped[Optional[str]] = mapped_column(String(1024))
    market_cap_rank: Mapped[Optional[int]] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    market: Mapped[str] = mapped_column(String(32))
