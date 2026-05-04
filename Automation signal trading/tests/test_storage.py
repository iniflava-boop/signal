from datetime import datetime, timedelta, timezone

from trading_signal_agent.models import Candle, Direction, Signal, TradeStatus
from trading_signal_agent.storage import SignalStore


def candle(low: float, high: float, close: float) -> Candle:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return Candle(now, close, high, low, close, 1000, now + timedelta(hours=4))


def test_paper_trade_fill_and_tp(tmp_path) -> None:
    store = SignalStore(tmp_path / "signals.sqlite3")
    store.init()
    store.save_signal(
        Signal(
            symbol="BTCUSDT",
            base_asset="BTC",
            direction=Direction.LONG,
            timeframe="4h",
            entry_low=99,
            entry_high=101,
            stop_loss=95,
            tp1=105,
            tp2=110,
            tp3=115,
            confidence=80,
        )
    )
    store.update_with_candle("BTCUSDT", candle(100, 116, 112))
    report = store.report()
    assert report["closed_trades"] == 1
    assert report["total_r"] == 3


def test_paper_trade_expires(tmp_path) -> None:
    store = SignalStore(tmp_path / "signals.sqlite3")
    store.init()
    store.save_signal(
        Signal(
            symbol="BTCUSDT",
            base_asset="BTC",
            direction=Direction.SHORT,
            timeframe="4h",
            entry_low=99,
            entry_high=101,
            stop_loss=105,
            tp1=95,
            tp2=90,
            tp3=85,
            confidence=80,
        )
    )
    store.update_with_candle("BTCUSDT", candle(110, 120, 115), expiry_candles=2)
    store.update_with_candle("BTCUSDT", candle(110, 120, 115), expiry_candles=2)
    store.update_with_candle("BTCUSDT", candle(110, 120, 115), expiry_candles=2)
    with store.connect() as db:
        row = db.execute("SELECT status FROM signals").fetchone()
    assert row["status"] == TradeStatus.EXPIRED.value
