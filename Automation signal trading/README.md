# Trading Signal Agent

AI-assisted signal bot untuk Binance USDT-M futures. V1 mengirim signal Telegram dan mencatat paper trade; tidak mengeksekusi order real.

## Fitur

- Universe top 50 Binance USDT-M perpetual berdasarkan quote volume 24 jam, difilter lagi dengan likuiditas dan spread.
- Analisis 4H dengan EMA 20/50/200, RSI, MACD, ATR, volume spike, support/resistance.
- RSS news gratis sebagai konfirmasi/veto.
- Signal LONG/SHORT dengan entry zone, SL, TP1/TP2/TP3, R:R, confidence.
- Paper trading SQLite: pending, open, expired, closed, PnL berbasis R.
- Telegram dry-run untuk testing.

Market data dan charting v1 sepenuhnya memakai public Binance USD-M Futures API. Indikator dihitung lokal dari candle OHLCV Binance, bukan dari API indikator eksternal.

## Quick Start

```powershell
Copy-Item .env.example .env
# edit .env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_DRY_RUN=false
python -m venv .venv
.venv\Scripts\pip install -e .[dev]
.venv\Scripts\python -m trading_signal_agent scan-once
```

Docker:

```bash
cp .env.example .env
docker compose up -d --build
```

## Commands

```bash
trading-signal-agent scan-once
trading-signal-agent run
trading-signal-agent report
```

## Disclaimer

Signal ini untuk riset dan paper trading. Bukan nasihat finansial dan bukan jaminan profit.
