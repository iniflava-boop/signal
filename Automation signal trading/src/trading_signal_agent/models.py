from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


class Direction(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    NO_TRADE = "NO_TRADE"


class TradeStatus(StrEnum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class FuturesSymbol:
    symbol: str
    base_asset: str
    quote_asset: str
    status: str
    contract_type: str
    quote_volume: float
    bid_price: float | None = None
    ask_price: float | None = None

    @property
    def spread_bps(self) -> float | None:
        if self.bid_price is None or self.ask_price is None:
            return None
        mid = (self.bid_price + self.ask_price) / 2
        if mid <= 0:
            return None
        return ((self.ask_price - self.bid_price) / mid) * 10_000


@dataclass(frozen=True)
class Candle:
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: datetime


@dataclass(frozen=True)
class IndicatorSnapshot:
    ema20: float
    ema50: float
    ema200: float
    rsi14: float
    macd: float
    macd_signal: float
    atr14: float
    volume_ratio: float
    support: float
    resistance: float


@dataclass(frozen=True)
class NewsItem:
    title: str
    url: str
    published_at: datetime
    source: str
    sentiment: int = 0


@dataclass(frozen=True)
class Signal:
    symbol: str
    base_asset: str
    direction: Direction
    timeframe: str
    entry_low: float
    entry_high: float
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    confidence: int
    reasons: list[str] = field(default_factory=list)
    news_summary: str = "No major relevant RSS news found."
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def entry_mid(self) -> float:
        return (self.entry_low + self.entry_high) / 2

    @property
    def risk(self) -> float:
        return abs(self.entry_mid - self.stop_loss)

    @property
    def reward_to_tp3(self) -> float:
        return abs(self.tp3 - self.entry_mid)

    @property
    def rr_to_tp3(self) -> float:
        if self.risk == 0:
            return 0
        return self.reward_to_tp3 / self.risk


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
