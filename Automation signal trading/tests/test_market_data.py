from pathlib import Path

from trading_signal_agent.config import Settings
from trading_signal_agent.market_data import MarketDataClient, is_tradable
from trading_signal_agent.models import FuturesSymbol


def test_tradable_filter_requires_active_volume_and_spread() -> None:
    symbol = FuturesSymbol(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        status="TRADING",
        contract_type="PERPETUAL",
        quote_volume=100_000_000,
        bid_price=100,
        ask_price=100.05,
    )
    assert is_tradable(symbol, min_volume=50_000_000, max_spread_bps=15)


def test_tradable_filter_rejects_wide_spread() -> None:
    symbol = FuturesSymbol(
        symbol="ALTUSDT",
        base_asset="ALT",
        quote_asset="USDT",
        status="TRADING",
        contract_type="PERPETUAL",
        quote_volume=100_000_000,
        bid_price=100,
        ask_price=102,
    )
    assert not is_tradable(symbol, min_volume=50_000_000, max_spread_bps=15)


def test_binance_only_top_symbols_are_sorted_filtered_and_limited() -> None:
    client = MarketDataClient(settings(), http=FixtureHttp())
    symbols = client.tradable_top_symbols()
    assert [item.symbol for item in symbols] == ["ETHUSDT", "BTCUSDT"]


class FixtureHttp:
    def get_json(self, url: str, headers: dict[str, str] | None = None) -> object:
        assert "coingecko" not in url.lower()
        if url.endswith("/fapi/v1/exchangeInfo"):
            return {
                "symbols": [
                    {"symbol": "BTCUSDT", "baseAsset": "BTC", "quoteAsset": "USDT", "status": "TRADING", "contractType": "PERPETUAL"},
                    {"symbol": "ETHUSDT", "baseAsset": "ETH", "quoteAsset": "USDT", "status": "TRADING", "contractType": "PERPETUAL"},
                    {"symbol": "XRPUSDT", "baseAsset": "XRP", "quoteAsset": "USDT", "status": "BREAK", "contractType": "PERPETUAL"},
                    {"symbol": "BTCDOMUSDT", "baseAsset": "BTCDOM", "quoteAsset": "USDT", "status": "TRADING", "contractType": "CURRENT_QUARTER"},
                    {"symbol": "BNBUSDC", "baseAsset": "BNB", "quoteAsset": "USDC", "status": "TRADING", "contractType": "PERPETUAL"},
                ]
            }
        if url.endswith("/fapi/v1/ticker/24hr"):
            return [
                {"symbol": "BTCUSDT", "quoteVolume": "100000000"},
                {"symbol": "ETHUSDT", "quoteVolume": "200000000"},
                {"symbol": "XRPUSDT", "quoteVolume": "300000000"},
                {"symbol": "BTCDOMUSDT", "quoteVolume": "400000000"},
                {"symbol": "BNBUSDC", "quoteVolume": "500000000"},
            ]
        if url.endswith("/fapi/v1/ticker/bookTicker"):
            return [
                {"symbol": "BTCUSDT", "bidPrice": "100", "askPrice": "100.05"},
                {"symbol": "ETHUSDT", "bidPrice": "200", "askPrice": "200.05"},
                {"symbol": "XRPUSDT", "bidPrice": "1", "askPrice": "1.001"},
                {"symbol": "BTCDOMUSDT", "bidPrice": "10", "askPrice": "10.01"},
                {"symbol": "BNBUSDC", "bidPrice": "500", "askPrice": "500.1"},
            ]
        raise AssertionError(url)


def settings() -> Settings:
    return Settings(
        telegram_bot_token="",
        telegram_chat_id="",
        telegram_dry_run=True,
        top_symbol_limit=2,
        min_quote_volume_usdt=50_000_000,
        max_spread_bps=15,
        timeframe="4h",
        confirmation_timeframe="1d",
        confidence_threshold=70,
        scan_interval_minutes=240,
        entry_zone_atr_multiplier=0.15,
        stop_atr_multiplier=1.5,
        rss_feeds=[],
        database_path=Path(":memory:"),
    )
