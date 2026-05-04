from datetime import datetime, timedelta, timezone

from trading_signal_agent.indicators import atr, ema, rsi, snapshot, support_resistance
from trading_signal_agent.models import Candle


def make_candles(count: int, start: float = 100.0, step: float = 1.0) -> list[Candle]:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    for idx in range(count):
        close = start + (idx * step)
        candles.append(
            Candle(
                open_time=base + timedelta(hours=4 * idx),
                open=close - 0.5,
                high=close + 1,
                low=close - 1,
                close=close,
                volume=1000 + idx,
                close_time=base + timedelta(hours=4 * idx + 4),
            )
        )
    return candles


def test_indicators_are_calculated() -> None:
    candles = make_candles(220)
    snap = snapshot(candles)
    assert snap.ema20 > snap.ema50 > snap.ema200
    assert snap.rsi14 > 50
    assert snap.atr14 > 0
    assert snap.volume_ratio > 0


def test_support_resistance_uses_current_price_window() -> None:
    candles = make_candles(80)
    support, resistance = support_resistance(candles, lookback=60)
    assert support <= candles[-1].close
    assert resistance >= candles[-1].close


def test_low_level_indicator_shapes() -> None:
    values = [float(i) for i in range(1, 40)]
    assert len(ema(values, 20)) == len(values)
    assert len(rsi(values, 14)) == len(values)
    assert len(atr(make_candles(40), 14)) == 40
