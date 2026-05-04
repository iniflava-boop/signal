from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlencode

from .config import Settings
from .http import HttpClient
from .models import Candle, FuturesSymbol


BINANCE_FAPI = "https://fapi.binance.com"


class MarketDataClient:
    def __init__(self, settings: Settings, http: HttpClient | None = None) -> None:
        self.settings = settings
        self.http = http or HttpClient()

    def binance_usdt_perpetuals(self) -> dict[str, FuturesSymbol]:
        exchange_info = self.http.get_json(f"{BINANCE_FAPI}/fapi/v1/exchangeInfo")
        tickers = self.http.get_json(f"{BINANCE_FAPI}/fapi/v1/ticker/24hr")
        books = self.http.get_json(f"{BINANCE_FAPI}/fapi/v1/ticker/bookTicker")
        if not isinstance(exchange_info, dict) or not isinstance(tickers, list):
            raise RuntimeError("Unexpected Binance response")

        by_symbol_volume = {
            str(row["symbol"]): float(row.get("quoteVolume") or 0) for row in tickers
        }
        by_symbol_book = {
            str(row["symbol"]): row for row in books if isinstance(row, dict)
        }
        result: dict[str, FuturesSymbol] = {}
        for item in exchange_info.get("symbols", []):
            if item.get("quoteAsset") != "USDT":
                continue
            if item.get("contractType") != "PERPETUAL":
                continue
            symbol = str(item["symbol"])
            book = by_symbol_book.get(symbol, {})
            bid = _optional_float(book.get("bidPrice"))
            ask = _optional_float(book.get("askPrice"))
            result[symbol] = FuturesSymbol(
                symbol=symbol,
                base_asset=str(item["baseAsset"]).upper(),
                quote_asset="USDT",
                status=str(item.get("status", "")),
                contract_type=str(item.get("contractType", "")),
                quote_volume=by_symbol_volume.get(symbol, 0),
                bid_price=bid,
                ask_price=ask,
            )
        return result

    def tradable_top_symbols(self) -> list[FuturesSymbol]:
        futures = self.binance_usdt_perpetuals()
        symbols = [
            item
            for item in futures.values()
            if is_tradable(item, self.settings.min_quote_volume_usdt, self.settings.max_spread_bps)
        ]
        return sorted(symbols, key=lambda item: item.quote_volume, reverse=True)[: self.settings.top_symbol_limit]

    def klines(self, symbol: str, interval: str, limit: int = 300) -> list[Candle]:
        params = urlencode({"symbol": symbol, "interval": interval, "limit": limit})
        payload = self.http.get_json(f"{BINANCE_FAPI}/fapi/v1/klines?{params}")
        if not isinstance(payload, list):
            raise RuntimeError("Unexpected kline response")
        return [_parse_kline(row) for row in payload]


def is_tradable(symbol: FuturesSymbol, min_volume: float, max_spread_bps: float) -> bool:
    if symbol.status != "TRADING":
        return False
    if symbol.quote_volume < min_volume:
        return False
    spread = symbol.spread_bps
    if spread is not None and spread > max_spread_bps:
        return False
    return True


def _parse_kline(row: list[object]) -> Candle:
    return Candle(
        open_time=datetime.fromtimestamp(int(row[0]) / 1000, tz=timezone.utc),
        open=float(row[1]),
        high=float(row[2]),
        low=float(row[3]),
        close=float(row[4]),
        volume=float(row[5]),
        close_time=datetime.fromtimestamp(int(row[6]) / 1000, tz=timezone.utc),
    )


def _optional_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
