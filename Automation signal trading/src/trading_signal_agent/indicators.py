from __future__ import annotations

from statistics import mean

from .models import Candle, IndicatorSnapshot


def ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2 / (period + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append((value * alpha) + (result[-1] * (1 - alpha)))
    return result


def rsi(values: list[float], period: int = 14) -> list[float]:
    if len(values) < period + 1:
        return [50.0 for _ in values]
    gains = [0.0]
    losses = [0.0]
    for prev, current in zip(values, values[1:]):
        change = current - prev
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))

    result = [50.0 for _ in values]
    avg_gain = mean(gains[1 : period + 1])
    avg_loss = mean(losses[1 : period + 1])
    result[period] = _rsi_from_avgs(avg_gain, avg_loss)
    for idx in range(period + 1, len(values)):
        avg_gain = ((avg_gain * (period - 1)) + gains[idx]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[idx]) / period
        result[idx] = _rsi_from_avgs(avg_gain, avg_loss)
    return result


def macd(values: list[float]) -> tuple[list[float], list[float]]:
    ema12 = ema(values, 12)
    ema26 = ema(values, 26)
    line = [fast - slow for fast, slow in zip(ema12, ema26)]
    signal = ema(line, 9)
    return line, signal


def atr(candles: list[Candle], period: int = 14) -> list[float]:
    if not candles:
        return []
    true_ranges = [candles[0].high - candles[0].low]
    for prev, current in zip(candles, candles[1:]):
        true_ranges.append(
            max(
                current.high - current.low,
                abs(current.high - prev.close),
                abs(current.low - prev.close),
            )
        )
    if len(true_ranges) < period:
        return true_ranges
    result = [mean(true_ranges[:period]) for _ in range(period)]
    current_atr = result[-1]
    for tr in true_ranges[period:]:
        current_atr = ((current_atr * (period - 1)) + tr) / period
        result.append(current_atr)
    return result


def support_resistance(candles: list[Candle], lookback: int = 60) -> tuple[float, float]:
    window = candles[-lookback:] if len(candles) >= lookback else candles
    if not window:
        return 0.0, 0.0
    close = candles[-1].close
    lows = sorted({c.low for c in window if c.low <= close})
    highs = sorted({c.high for c in window if c.high >= close})
    support = lows[-1] if lows else min(c.low for c in window)
    resistance = highs[0] if highs else max(c.high for c in window)
    return support, resistance


def snapshot(candles: list[Candle]) -> IndicatorSnapshot:
    if len(candles) < 210:
        raise ValueError("Need at least 210 candles for EMA200-based analysis")
    closes = [c.close for c in candles]
    volumes = [c.volume for c in candles]
    macd_line, macd_signal = macd(closes)
    support, resistance = support_resistance(candles)
    avg_volume = mean(volumes[-21:-1]) if len(volumes) > 21 else mean(volumes)
    volume_ratio = candles[-1].volume / avg_volume if avg_volume > 0 else 1.0
    return IndicatorSnapshot(
        ema20=ema(closes, 20)[-1],
        ema50=ema(closes, 50)[-1],
        ema200=ema(closes, 200)[-1],
        rsi14=rsi(closes, 14)[-1],
        macd=macd_line[-1],
        macd_signal=macd_signal[-1],
        atr14=atr(candles, 14)[-1],
        volume_ratio=volume_ratio,
        support=support,
        resistance=resistance,
    )


def _rsi_from_avgs(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
