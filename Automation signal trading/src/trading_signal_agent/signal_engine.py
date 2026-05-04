from __future__ import annotations

from .config import Settings
from .indicators import snapshot
from .models import Candle, Direction, NewsItem, Signal
from .news import summarize_news


def generate_signal(
    symbol: str,
    base_asset: str,
    candles_4h: list[Candle],
    candles_1d: list[Candle],
    news_items: list[NewsItem],
    settings: Settings,
) -> Signal | None:
    if len(candles_4h) < 210 or len(candles_1d) < 210:
        return None

    current = candles_4h[-1].close
    four_h = snapshot(candles_4h)
    one_d = snapshot(candles_1d)
    news_score, news_summary = summarize_news(news_items)
    direction, score, reasons = _score_direction(current, four_h, one_d)

    if direction == Direction.NO_TRADE:
        return None
    if direction == Direction.LONG and news_score <= -2:
        return None
    if direction == Direction.SHORT and news_score >= 2:
        return None

    score += max(min(news_score * 3, 6), -6)
    confidence = max(0, min(100, score))
    if confidence < settings.confidence_threshold:
        return None

    entry_low, entry_high, stop_loss, tp1, tp2, tp3 = _levels(
        direction=direction,
        current=current,
        support=four_h.support,
        resistance=four_h.resistance,
        atr=four_h.atr14,
        entry_atr_multiplier=settings.entry_zone_atr_multiplier,
        stop_atr_multiplier=settings.stop_atr_multiplier,
    )
    return Signal(
        symbol=symbol,
        base_asset=base_asset,
        direction=direction,
        timeframe=settings.timeframe,
        entry_low=entry_low,
        entry_high=entry_high,
        stop_loss=stop_loss,
        tp1=tp1,
        tp2=tp2,
        tp3=tp3,
        confidence=confidence,
        reasons=reasons,
        news_summary=news_summary,
    )


def _score_direction(current: float, four_h, one_d) -> tuple[Direction, int, list[str]]:
    long_score = 0
    short_score = 0
    long_reasons: list[str] = []
    short_reasons: list[str] = []

    if four_h.ema20 > four_h.ema50 > four_h.ema200:
        long_score += 25
        long_reasons.append("4H EMA trend bullish")
    if four_h.ema20 < four_h.ema50 < four_h.ema200:
        short_score += 25
        short_reasons.append("4H EMA trend bearish")
    if one_d.ema20 > one_d.ema50:
        long_score += 15
        long_reasons.append("1D confirmation bullish")
    if one_d.ema20 < one_d.ema50:
        short_score += 15
        short_reasons.append("1D confirmation bearish")
    if 50 <= four_h.rsi14 <= 68:
        long_score += 15
        long_reasons.append(f"RSI healthy at {four_h.rsi14:.1f}")
    if 32 <= four_h.rsi14 <= 50:
        short_score += 15
        short_reasons.append(f"RSI bearish/weak at {four_h.rsi14:.1f}")
    if four_h.macd > four_h.macd_signal:
        long_score += 12
        long_reasons.append("MACD above signal")
    if four_h.macd < four_h.macd_signal:
        short_score += 12
        short_reasons.append("MACD below signal")
    if four_h.volume_ratio >= 1.2:
        long_score += 8
        short_score += 8
        long_reasons.append("Volume expansion")
        short_reasons.append("Volume expansion")
    if current > four_h.resistance:
        long_score += 15
        long_reasons.append("Breakout above resistance")
    if current < four_h.support:
        short_score += 15
        short_reasons.append("Breakdown below support")

    if abs(long_score - short_score) < 15:
        return Direction.NO_TRADE, max(long_score, short_score), []
    if long_score > short_score:
        return Direction.LONG, long_score, long_reasons
    return Direction.SHORT, short_score, short_reasons


def _levels(
    direction: Direction,
    current: float,
    support: float,
    resistance: float,
    atr: float,
    entry_atr_multiplier: float,
    stop_atr_multiplier: float,
) -> tuple[float, float, float, float, float, float]:
    zone = atr * entry_atr_multiplier
    if direction == Direction.LONG:
        entry_low = current - zone
        entry_high = current + zone
        structure_stop = support - (atr * 0.1)
        atr_stop = current - (atr * stop_atr_multiplier)
        stop_loss = min(structure_stop, atr_stop)
        risk = current - stop_loss
        tp1 = current + risk
        tp2 = current + (risk * 2)
        tp3 = max(resistance, current + (risk * 2.5))
        return entry_low, entry_high, stop_loss, tp1, tp2, tp3

    entry_low = current - zone
    entry_high = current + zone
    structure_stop = resistance + (atr * 0.1)
    atr_stop = current + (atr * stop_atr_multiplier)
    stop_loss = max(structure_stop, atr_stop)
    risk = stop_loss - current
    tp1 = current - risk
    tp2 = current - (risk * 2)
    tp3 = min(support, current - (risk * 2.5))
    return entry_low, entry_high, stop_loss, tp1, tp2, tp3
