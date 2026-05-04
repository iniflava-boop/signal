from __future__ import annotations

from .config import Settings
from .http import HttpClient
from .models import Direction, Signal


class TelegramNotifier:
    def __init__(self, settings: Settings, http: HttpClient | None = None) -> None:
        self.settings = settings
        self.http = http or HttpClient()

    def send_signal(self, signal: Signal) -> None:
        message = format_signal_message(signal)
        if self.settings.telegram_dry_run:
            print(message)
            return
        if not self.settings.telegram_bot_token or not self.settings.telegram_chat_id:
            raise RuntimeError("Telegram token/chat ID is required when TELEGRAM_DRY_RUN=false")
        url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage"
        self.http.post_json(
            url,
            {
                "chat_id": self.settings.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )


def format_signal_message(signal: Signal) -> str:
    arrow = "LONG" if signal.direction == Direction.LONG else "SHORT"
    reasons = "\n".join(f"- {reason}" for reason in signal.reasons[:5])
    return (
        f"<b>{signal.symbol} {arrow} Signal</b>\n"
        f"Timeframe: {signal.timeframe}\n"
        f"Confidence: {signal.confidence}/100\n"
        f"Entry zone: {signal.entry_low:.6g} - {signal.entry_high:.6g}\n"
        f"Stop loss: {signal.stop_loss:.6g}\n"
        f"TP1: {signal.tp1:.6g}\n"
        f"TP2: {signal.tp2:.6g}\n"
        f"TP3: {signal.tp3:.6g}\n"
        f"R:R to TP3: {signal.rr_to_tp3:.2f}\n"
        f"Created: {signal.created_at.isoformat()}\n\n"
        f"<b>Technical reasons</b>\n{reasons}\n\n"
        f"<b>News</b>\n{signal.news_summary}\n\n"
        "For research and paper trading only. Not financial advice."
    )
