from datetime import datetime, timedelta, timezone

from trading_signal_agent.config import Settings
from trading_signal_agent.models import Candle
from trading_signal_agent.signal_engine import generate_signal


def make_trend(count: int, start: float, step: float) -> list[Candle]:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    for idx in range(count):
        close = start + (idx * step)
        candles.append(
            Candle(
                open_time=base + timedelta(hours=4 * idx),
                open=close - step,
                high=close + 2,
                low=close - 2,
                close=close,
                volume=1000 + (500 if idx == count - 1 else idx),
                close_time=base + timedelta(hours=4 * idx + 4),
            )
        )
    return candles


def settings() -> Settings:
    return Settings(
        telegram_bot_token="",
        telegram_chat_id="",
        telegram_dry_run=True,
        top_symbol_limit=50,
        min_quote_volume_usdt=1,
        max_spread_bps=15,
        timeframe="4h",
        confirmation_timeframe="1d",
        confidence_threshold=60,
        scan_interval_minutes=240,
        entry_zone_atr_multiplier=0.15,
        stop_atr_multiplier=1.5,
        rss_feeds=[],
        database_path=__import__("pathlib").Path(":memory:"),
    )


def test_generates_long_signal_with_multi_tp() -> None:
    signal = generate_signal("BTCUSDT", "BTC", make_trend(230, 100, 1), make_trend(230, 100, 2), [], settings())
    assert signal is not None
    assert signal.direction == "LONG"
    assert signal.tp1 < signal.tp2 < signal.tp3
    assert signal.stop_loss < signal.entry_low
    assert signal.confidence >= 60
