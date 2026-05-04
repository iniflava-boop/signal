from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def _float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value else default


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_chat_id: str
    telegram_dry_run: bool
    top_symbol_limit: int
    min_quote_volume_usdt: float
    max_spread_bps: float
    timeframe: str
    confirmation_timeframe: str
    confidence_threshold: int
    scan_interval_minutes: int
    entry_zone_atr_multiplier: float
    stop_atr_multiplier: float
    rss_feeds: list[str]
    database_path: Path

    @classmethod
    def from_env(cls) -> "Settings":
        feeds = [
            feed.strip()
            for feed in os.getenv("RSS_FEEDS", "").split(",")
            if feed.strip()
        ]
        return cls(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            telegram_dry_run=_bool(os.getenv("TELEGRAM_DRY_RUN"), True),
            top_symbol_limit=_int("TOP_SYMBOL_LIMIT", 50),
            min_quote_volume_usdt=_float("MIN_QUOTE_VOLUME_USDT", 50_000_000),
            max_spread_bps=_float("MAX_SPREAD_BPS", 15),
            timeframe=os.getenv("TIMEFRAME", "4h"),
            confirmation_timeframe=os.getenv("CONFIRMATION_TIMEFRAME", "1d"),
            confidence_threshold=_int("CONFIDENCE_THRESHOLD", 70),
            scan_interval_minutes=_int("SCAN_INTERVAL_MINUTES", 240),
            entry_zone_atr_multiplier=_float("ENTRY_ZONE_ATR_MULTIPLIER", 0.15),
            stop_atr_multiplier=_float("STOP_ATR_MULTIPLIER", 1.5),
            rss_feeds=feeds,
            database_path=Path(os.getenv("DATABASE_PATH", "data/signals.sqlite3")),
        )
