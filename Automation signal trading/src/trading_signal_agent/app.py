from __future__ import annotations

import argparse
import time

from .config import Settings
from .market_data import MarketDataClient
from .news import RssNewsClient, relevant_news
from .signal_engine import generate_signal
from .storage import SignalStore
from .telegram import TelegramNotifier


class SignalAgent:
    def __init__(
        self,
        settings: Settings,
        market_data: MarketDataClient | None = None,
        news_client: RssNewsClient | None = None,
        store: SignalStore | None = None,
        notifier: TelegramNotifier | None = None,
    ) -> None:
        self.settings = settings
        self.market_data = market_data or MarketDataClient(settings)
        self.news_client = news_client or RssNewsClient(settings.rss_feeds)
        self.store = store or SignalStore(settings.database_path)
        self.notifier = notifier or TelegramNotifier(settings)

    def scan_once(self) -> int:
        self.store.init()
        symbols = self.market_data.tradable_top_symbols()
        news_items = self.news_client.fetch_recent()
        sent = 0
        for item in symbols:
            candles_4h = self.market_data.klines(item.symbol, self.settings.timeframe, limit=300)
            candles_1d = self.market_data.klines(item.symbol, self.settings.confirmation_timeframe, limit=300)
            if candles_4h:
                self.store.update_with_candle(item.symbol, candles_4h[-1])
            if self.store.has_active_signal(item.symbol):
                continue
            signal = generate_signal(
                symbol=item.symbol,
                base_asset=item.base_asset,
                candles_4h=candles_4h,
                candles_1d=candles_1d,
                news_items=relevant_news(news_items, item.base_asset),
                settings=self.settings,
            )
            if signal is None:
                continue
            self.store.save_signal(signal)
            self.notifier.send_signal(signal)
            sent += 1
        return sent

    def run_forever(self) -> None:
        while True:
            try:
                sent = self.scan_once()
                print(f"scan complete, sent {sent} signal(s)")
            except Exception as exc:
                print(f"scan failed: {exc}")
            time.sleep(self.settings.scan_interval_minutes * 60)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Crypto futures Telegram signal agent")
    parser.add_argument("command", choices=["scan-once", "run", "report"], nargs="?", default="scan-once")
    args = parser.parse_args(argv)
    settings = Settings.from_env()
    agent = SignalAgent(settings)

    if args.command == "run":
        agent.run_forever()
    elif args.command == "report":
        agent.store.init()
        report = agent.store.report()
        print(
            "Paper report: "
            f"closed={report['closed_trades']}, "
            f"win_rate={report['win_rate']:.2%}, "
            f"avg_r={report['average_r']:.2f}, "
            f"total_r={report['total_r']:.2f}, "
            f"active={report['open_or_pending']}"
        )
    else:
        sent = agent.scan_once()
        print(f"sent {sent} signal(s)")
